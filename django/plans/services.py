from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from datetime import timedelta, datetime
from typing import Dict, Optional, Tuple
import uuid
import logging
from decimal import Decimal

from .models import (
    Plan,
    Feature,
    UserSubscription,
    UsageRecord,
    PlanFeatureLimit,
    PlanPayment,
)

logger = logging.getLogger(__name__)

# Define a constant for the reactivation grace period
REACTIVATION_GRACE_PERIOD_DAYS = 7


class PlanService:
    """Service for plan-related operations"""

    @staticmethod
    def get_user_plan(user: User) -> Optional[Plan]:
        """Get the current plan for a user"""
        try:
            subscription = UserSubscription.objects.get(user=user, status="active")

            # Check if subscription is expired
            if subscription.is_expired:
                subscription.status = "expired"
                subscription.save()
                return None

            return subscription.plan
        except UserSubscription.DoesNotExist:
            return None

    @staticmethod
    def create_subscription(
        user: User, plan: Plan, payment: PlanPayment = None
    ) -> UserSubscription:
        """Create a new subscription for a user"""
        from django.utils import timezone

        # Handle existing active subscription
        existing_subscription = UserSubscription.objects.filter(
            user=user, status="active"
        ).first()
        if existing_subscription:
            # If user is subscribing to the same plan, reactivate if recently canceled
            if existing_subscription.plan == plan:
                existing_subscription.status = "active"
                existing_subscription.canceled_at = None
                existing_subscription.auto_renew = True
                existing_subscription.save()

                # Link payment if provided
                if payment:
                    payment.subscription = existing_subscription
                    payment.save()

                return existing_subscription
            else:
                # Cancel existing subscription for different plan
                existing_subscription.status = "canceled"
                existing_subscription.canceled_at = timezone.now()
                existing_subscription.save()

        # Calculate period based on billing period
        start_date = timezone.now()
        if plan.billing_period == "monthly":
            end_date = start_date + timedelta(days=30)
        elif plan.billing_period == "yearly":
            end_date = start_date + timedelta(days=365)
        elif plan.billing_period == "weekly":
            end_date = start_date + timedelta(days=7)
        elif plan.billing_period == "daily":
            end_date = start_date + timedelta(days=1)
        else:
            end_date = start_date + timedelta(days=30)

        # Create new subscription
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            status="active",
            start_date=start_date,
            end_date=end_date,
        )

        # Link payment to subscription if provided
        if payment:
            payment.subscription = subscription
            payment.save()

        return subscription


class PaymentService:
    """Service for payment operations using django-payments"""

    @staticmethod
    def create_payment(user: User, plan: Plan, variant: str = "dummy") -> PlanPayment:
        """Create a payment using django-payments"""
        payment = PlanPayment.objects.create(
            user=user,
            plan=plan,
            variant=variant,
            description=f"{plan.name} Subscription",
            total=plan.price,
            currency="USD",
            billing_email=user.email,
            billing_first_name=user.first_name,
            billing_last_name=user.last_name,
        )
        return payment

    @staticmethod
    def handle_payment_success(payment: PlanPayment) -> UserSubscription:
        """Handle successful payment and create/reactivate subscription"""
        subscription = SubscriptionService.handle_payment_and_subscription(
            user=payment.user, plan=payment.plan, payment=payment
        )

        logger.info(f"Payment {payment.id} successful for user {payment.user.id}")
        return subscription


class UsageService:
    """Service for tracking and checking feature usage"""

    @staticmethod
    def get_current_period_dates(billing_period: str) -> Tuple[datetime, datetime]:
        """Get the current period start and end dates based on billing period"""
        now = timezone.now()

        if billing_period == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif billing_period == "weekly":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        elif billing_period == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)
        elif billing_period == "yearly":
            start = now.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
            end = start.replace(year=now.year + 1)
        else:
            # Default to monthly
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)

        return start, end

    @staticmethod
    def get_current_usage(user: User, feature_code: str) -> int:
        """Get current usage count for a user and feature in the current period"""
        try:
            feature = Feature.objects.get(code=feature_code, is_active=True)
        except Feature.DoesNotExist:
            return 0

        # Get user's current plan to determine billing period
        plan = PlanService.get_user_plan(user)
        if not plan:
            return 0

        # Get current period dates
        start_date, end_date = UsageService.get_current_period_dates(
            plan.billing_period
        )

        # Get usage record for current period
        try:
            usage_record = UsageRecord.objects.get(
                user=user, feature=feature, period_start=start_date
            )
            return usage_record.count
        except UsageRecord.DoesNotExist:
            return 0

    @staticmethod
    def check_feature_limit(user: User, feature_code: str) -> Dict:
        """Check if user can use a feature based on their plan limits"""
        try:
            feature = Feature.objects.get(code=feature_code, is_active=True)
        except Feature.DoesNotExist:
            return {"allowed": True, "message": "Feature not found"}

        # Get user's current plan
        plan = PlanService.get_user_plan(user)
        if not plan:
            return {"allowed": False, "message": "No active subscription found"}

        # Get feature limit for the plan
        try:
            plan_limit = PlanFeatureLimit.objects.get(plan=plan, feature=feature)
        except PlanFeatureLimit.DoesNotExist:
            return {"allowed": False, "message": "Feature not available in your plan"}

        # Check if unlimited
        if plan_limit.limit == -1:
            return {"allowed": True, "remaining": -1}

        # Get current usage
        start_date, end_date = UsageService.get_current_period_dates(
            plan.billing_period
        )
        usage_record, created = UsageRecord.objects.get_or_create(
            user=user,
            feature=feature,
            period_start=start_date,
            defaults={"period_end": end_date, "count": 0},
        )

        remaining = plan_limit.limit - usage_record.count
        allowed = remaining > 0

        return {
            "allowed": allowed,
            "remaining": remaining,
            "limit": plan_limit.limit,
            "used": usage_record.count,
            "message": (
                f"You have {remaining} uses remaining"
                if allowed
                else "Usage limit exceeded"
            ),
        }

    @staticmethod
    def record_feature_usage(user: User, feature_code: str) -> bool:
        """Record usage of a feature"""
        try:
            feature = Feature.objects.get(code=feature_code, is_active=True)
        except Feature.DoesNotExist:
            return False

        plan = PlanService.get_user_plan(user)
        if not plan:
            return False

        start_date, end_date = UsageService.get_current_period_dates(
            plan.billing_period
        )
        usage_record, created = UsageRecord.objects.get_or_create(
            user=user,
            feature=feature,
            period_start=start_date,
            defaults={"period_end": end_date, "count": 0},
        )

        usage_record.count += 1
        usage_record.save()

        logger.info(
            f"Recorded usage for user {user.id}, feature {feature_code}, count: {usage_record.count}"
        )
        return True


class SubscriptionService:
    """Service for subscription lifecycle management"""

    @staticmethod
    def get_active_subscription(user: User) -> Optional[UserSubscription]:
        """Get user's current active subscription with proper expiry check"""
        from django.utils import timezone

        subscription = UserSubscription.objects.filter(
            user=user, status="active"
        ).first()

        if subscription:
            # Check if subscription is actually expired
            if subscription.end_date and timezone.now() > subscription.end_date:
                subscription.status = "expired"
                subscription.save()
                return None

            # Check if subscription was canceled but still in grace period
            if (
                hasattr(subscription, "canceled_at")
                and subscription.canceled_at
                and not getattr(subscription, "auto_renew", True)
            ):
                if subscription.end_date and timezone.now() > subscription.end_date:
                    subscription.status = "expired"
                    subscription.save()
                    return None

        return subscription

    @staticmethod
    def reactivate_subscription(user, plan_to_activate):
        """
        Finds and reactivates a recently canceled subscription for the user
        if it's for the same plan and within a grace period.
        """
        try:
            # Find the most recently canceled subscription for the target plan
            last_canceled_sub = (
                UserSubscription.objects.filter(user=user, plan=plan_to_activate)
                .exclude(status="active")
                .order_by("-end_date")
                .first()
            )

            if not last_canceled_sub:
                return {"success": False, "message": "No previous subscription found."}

            # --- FIX: Ensure end_date is not None before comparison ---
            if last_canceled_sub.end_date is None:
                return {"success": False, "message": "Subscription has no end date."}

            # Check if the subscription ended within the grace period
            grace_period_end = last_canceled_sub.end_date + timedelta(
                days=REACTIVATION_GRACE_PERIOD_DAYS
            )

            if timezone.now() <= grace_period_end:
                # Reactivate the subscription
                last_canceled_sub.status = "active"
                last_canceled_sub.auto_renew = True
                last_canceled_sub.canceled_at = None
                # Optionally extend the end_date if needed, or reset it based on plan
                # For simplicity, we'll just reactivate it here.
                last_canceled_sub.save()
                return {"success": True, "subscription": last_canceled_sub}
            else:
                return {
                    "success": False,
                    "message": "Reactivation period has expired.",
                }

        except UserSubscription.DoesNotExist:
            return {"success": False, "message": "No subscription history found."}
        except Exception as e:
            # Log the exception e
            return {"success": False, "message": str(e)}

    @staticmethod
    def cancel_subscription(user, immediate=False):
        """Cancels the user's active subscription."""
        from django.utils import timezone

        subscription = SubscriptionService.get_active_subscription(user)
        if not subscription:
            return {"success": False, "message": "No active subscription found"}

        if immediate:
            # Immediate cancellation
            subscription.status = "canceled"
            subscription.end_date = timezone.now()
            if hasattr(subscription, "canceled_at"):
                subscription.canceled_at = timezone.now()
            if hasattr(subscription, "auto_renew"):
                subscription.auto_renew = False
        else:
            # Cancel at end of billing period (grace period)
            if hasattr(subscription, "auto_renew"):
                subscription.auto_renew = False
            if hasattr(subscription, "canceled_at"):
                subscription.canceled_at = timezone.now()
            # Keep status as 'active' but mark as non-renewing

        subscription.save()

        return {
            "success": True,
            "message": (
                "Subscription canceled successfully"
                if immediate
                else "Subscription will end at the current billing period"
            ),
            "immediate": immediate,
            "ends_at": subscription.end_date,
            "grace_period": not immediate,
        }

    @staticmethod
    def handle_payment_and_subscription(
        user: User, plan: Plan, payment: PlanPayment
    ) -> UserSubscription:
        """Handle payment success and subscription creation/reactivation"""

        # First try to reactivate recent subscription
        reactivation_result = SubscriptionService.reactivate_subscription(user, plan)

        if reactivation_result["success"]:
            subscription = reactivation_result["subscription"]
            payment.subscription = subscription
            payment.save()
            return subscription

        # Create new subscription
        return PlanService.create_subscription(user, plan, payment)
