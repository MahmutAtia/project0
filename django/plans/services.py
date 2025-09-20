from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from datetime import timedelta, datetime
from typing import Optional, Dict, Tuple
import uuid
import logging
from decimal import Decimal
from django.utils.timezone import make_aware
from django.conf import settings
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


def get_polar_client():
    from polar_sdk import Polar

    return Polar(access_token=settings.POLAR_API_KEY)


class PlanService:
    """Service for plan-related operations"""

    @staticmethod
    def get_user_plan(user: User) -> Optional[Plan]:
        """Get the current plan for a user"""
        try:
            subscription = UserSubscription.objects.get(user=user, status="active")

            # Check if subscription is expired
            if subscription.is_expired:
                subscription.status = "revoked"  # Use revoked instead of expired
                subscription.save()
                return None

            return subscription.plan
        except UserSubscription.DoesNotExist:
            return None


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

    def __init__(self):
        # Remove the polar_sdk import from here
        pass

    def get_subscription_info(self, user):
        # Use lazy loading
        polar = get_polar_client()
        # ...rest of method...


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
                subscription.status = "revoked"  # Use revoked instead of expired
                subscription.save()
                return None

            # Check if subscription was canceled but still in grace period
            if (
                hasattr(subscription, "canceled_at")
                and subscription.canceled_at
                and not getattr(subscription, "auto_renew", True)
            ):
                # If still within the current period, it's still active
                if subscription.end_date and timezone.now() <= subscription.end_date:
                    return subscription
                else:
                    # Period has ended, mark as revoked
                    subscription.status = "revoked"  # Use revoked instead of expired
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
                UserSubscription.objects.filter(
                    user=user,
                    plan=plan_to_activate,
                    status__in=["canceled", "revoked"]  # Use revoked instead of expired
                )
                .order_by("-end_date")
                .first()
            )

            if not last_canceled_sub or not last_canceled_sub.end_date:
                return {"success": False, "message": "No previous subscription found."}

            # Check if the subscription ended within the grace period
            grace_period_end = last_canceled_sub.end_date + timedelta(
                days=REACTIVATION_GRACE_PERIOD_DAYS
            )

            if timezone.now() <= grace_period_end:
                # Just mark as reactivatable - actual reactivation happens via Polar checkout
                return {"success": True, "subscription": last_canceled_sub}
            else:
                return {"success": False, "message": "Reactivation period has expired."}

        except Exception as e:
            return {"success": False, "message": str(e)}

    @staticmethod
    def handle_polar_webhook_event(event_type: str, user_id: str, polar_subscription_data: dict):
        """
        Handle different types of Polar webhook events for subscriptions.
        """
        print(f"\n--- [DEBUG] handle_polar_webhook_event called ---")
        print(f"--- [DEBUG] Event Type: {event_type}")
        print(f"--- [DEBUG] User ID: {user_id}")
        print(f"--- [DEBUG] Incoming Polar Data: {polar_subscription_data}")

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            print(f"--- [DEBUG] Found user: {user.username} (ID: {user.id})")

            polar_product_id = polar_subscription_data.get("product_id")
            plan = Plan.objects.get(polar_product_id=polar_product_id)
            print(f"--- [DEBUG] Found plan: {plan.name} (Polar Product ID: {polar_product_id})")

            from django.utils.dateparse import parse_datetime
            from datetime import datetime

            def safe_parse_datetime(date_value):
                if date_value is None:
                    return None
                return date_value if isinstance(date_value, datetime) else parse_datetime(date_value)

            def get_status_value(raw_status):
                if hasattr(raw_status, 'value'):
                    return raw_status.value
                return str(raw_status)

            start_date = safe_parse_datetime(polar_subscription_data.get("current_period_start"))
            end_date = safe_parse_datetime(polar_subscription_data.get("current_period_end"))
            print(f"--- [DEBUG] Parsed Start Date: {start_date}")
            print(f"--- [DEBUG] Parsed End Date: {end_date}")

            subscription_defaults = {
                "user": user,
                "plan": plan,
                "start_date": start_date,
                "end_date": end_date,
                "polar_customer_id": polar_subscription_data.get("customer", {}).get("id")
            }

            print(f"--- [DEBUG] Initial subscription_defaults: {subscription_defaults}")

            if event_type in ["subscription.created", "subscription.active"]:
                print(f"--- [DEBUG] Event logic: {event_type}")
                subscription_defaults.update({
                    "status": "active",
                    "auto_renew": True,
                    "canceled_at": None,
                })
            elif event_type == "subscription.updated":
                print("--- [DEBUG] Event logic: subscription.updated")
                auto_renew = not polar_subscription_data.get("cancel_at_period_end", False)
                canceled_at = safe_parse_datetime(polar_subscription_data.get("canceled_at"))
                polar_status = get_status_value(polar_subscription_data.get("status"))
                print(f"--- [DEBUG] Polar status: {polar_status}, auto_renew: {auto_renew}, canceled_at: {canceled_at}")

                final_status = "active"
                if polar_status in ["canceled", "expired"]:
                    final_status = "revoked"
                elif polar_status in ["past_due", "unpaid"]:
                    final_status = "pending"

                print(f"--- [DEBUG] Final status for update: {final_status}")
                subscription_defaults.update({
                    "status": final_status,
                    "auto_renew": auto_renew,
                    "canceled_at": canceled_at,
                })
            elif event_type == "subscription.canceled":
                print("--- [DEBUG] Event logic: subscription.canceled")
                canceled_at = safe_parse_datetime(polar_subscription_data.get("canceled_at"))
                subscription_defaults.update({
                    "status": "active",
                    "auto_renew": False,
                    "canceled_at": canceled_at,
                })
            elif event_type == "subscription.uncanceled":
                print("--- [DEBUG] Event logic: subscription.uncanceled")
                subscription_defaults.update({
                    "status": "active",
                    "auto_renew": True,
                    "canceled_at": None,
                })
            elif event_type == "subscription.revoked":
                print("--- [DEBUG] Event logic: subscription.revoked")
                canceled_at = safe_parse_datetime(polar_subscription_data.get("canceled_at"))
                subscription_defaults.update({
                    "status": "revoked",
                    "auto_renew": False,
                    "canceled_at": canceled_at,
                })

            print(f"--- [DEBUG] Final subscription_defaults before DB save: {subscription_defaults}")

            # Use user object to find and update the subscription, ensuring only one exists.
            # This correctly handles the transition from a free plan (no polar_id) to a paid one.
            subscription, created = UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    **subscription_defaults,
                    "polar_subscription_id": polar_subscription_data["id"],
                },
            )

            action = "created" if created else "updated"
            print(f"--- [SUCCESS] Subscription {action} for user {user.username} from Polar webhook event: {event_type}")

            return subscription

        except User.DoesNotExist:
            print(f"--- [ERROR] User with ID {user_id} not found for Polar webhook.")
        except Plan.DoesNotExist:
            print(f"--- [ERROR] Plan with Polar Product ID {polar_product_id} not found.")
        except Exception as e:
            print(f"--- [ERROR] An unexpected error occurred in handle_polar_webhook_event for event {event_type}: {e}")
        return None

    # Keep the old method for backward compatibility, but make it use the new one
    @staticmethod
    def sync_subscription_from_polar(user_id, polar_subscription_data):
        """
        Legacy method - redirects to handle_polar_webhook_event with 'updated' type
        """
        return SubscriptionService.handle_polar_webhook_event("subscription.updated", user_id, polar_subscription_data)

