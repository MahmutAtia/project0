from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from datetime import timedelta, datetime
from typing import Optional, Dict, Tuple
import uuid
import logging
from decimal import Decimal
from django.utils.timezone import make_aware
from polar_sdk import Polar
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
                # If still within the current period, it's still active
                if subscription.end_date and timezone.now() <= subscription.end_date:
                    return subscription
                else:
                    # Period has ended, mark as expired
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

    @staticmethod
    def handle_polar_webhook_event(event_type: str, user_id: str, polar_subscription_data: dict):
        """
        Handle different types of Polar webhook events for subscriptions.
        """
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            user = User.objects.get(id=user_id)
            
            # Get the product ID from the subscription data
            polar_product_id = polar_subscription_data.get("product_id")
            plan = Plan.objects.get(polar_product_id=polar_product_id)

            # Parse the datetime strings
            from django.utils.dateparse import parse_datetime
            start_date = parse_datetime(polar_subscription_data["current_period_start"])
            end_date = parse_datetime(polar_subscription_data["current_period_end"])

            # Base subscription data
            subscription_defaults = {
                "user": user,
                "plan": plan,
                "start_date": start_date,
                "end_date": end_date,
            }

            # Handle different event types
            if event_type == "subscription.created":
                subscription_defaults.update({
                    "status": "active",
                    "auto_renew": True,
                    "canceled_at": None,
                })
                
            elif event_type == "subscription.active":
                subscription_defaults.update({
                    "status": "active",
                    "auto_renew": True,
                    "canceled_at": None,
                })
                
            elif event_type == "subscription.updated":
                # Handle general updates
                auto_renew = not polar_subscription_data.get("cancel_at_period_end", False)
                canceled_at = None
                if polar_subscription_data.get("canceled_at"):
                    canceled_at = parse_datetime(polar_subscription_data["canceled_at"])
                    
                subscription_defaults.update({
                    "status": polar_subscription_data.get("status", "active"),
                    "auto_renew": auto_renew,
                    "canceled_at": canceled_at,
                })
                
            elif event_type == "subscription.canceled":
                # Subscription is canceled but user keeps access until period end
                canceled_at = None
                if polar_subscription_data.get("canceled_at"):
                    canceled_at = parse_datetime(polar_subscription_data["canceled_at"])
                    
                subscription_defaults.update({
                    "status": "active",  # Still active until period end
                    "auto_renew": False,
                    "canceled_at": canceled_at,
                })
                
            elif event_type == "subscription.uncanceled":
                # Subscription is reactivated
                subscription_defaults.update({
                    "status": "active",
                    "auto_renew": True,
                    "canceled_at": None,
                })
                
            elif event_type == "subscription.revoked":
                # User loses access immediately
                canceled_at = None
                if polar_subscription_data.get("canceled_at"):
                    canceled_at = parse_datetime(polar_subscription_data["canceled_at"])
                    
                subscription_defaults.update({
                    "status": "revoked",  # or "canceled" - choose based on your model
                    "auto_renew": False,
                    "canceled_at": canceled_at,
                })

            # Create or update subscription
            subscription, created = UserSubscription.objects.update_or_create(
                polar_subscription_id=polar_subscription_data["id"],
                defaults=subscription_defaults,
            )

            action = "created" if created else "updated"
            print(f"Subscription {action} for user {user.username} from Polar webhook event: {event_type}")

            return subscription

        except User.DoesNotExist:
            print(f"User with ID {user_id} not found for Polar webhook.")
        except Plan.DoesNotExist:
            print(f"Plan with Polar Product ID {polar_product_id} not found.")
        except Exception as e:
            print(f"Error handling Polar webhook event {event_type}: {e}")
        return None

    # Keep the old method for backward compatibility, but make it use the new one
    @staticmethod
    def sync_subscription_from_polar(user_id, polar_subscription_data):
        """
        Legacy method - redirects to handle_polar_webhook_event with 'updated' type
        """
        return SubscriptionService.handle_polar_webhook_event("subscription.updated", user_id, polar_subscription_data)

    @staticmethod
    def cancel_subscription(user, immediate=False):
        """
        Cancels a user's subscription via the Polar API.
        Polar only supports cancellation at the end of the period.
        """
        try:
            subscription = UserSubscription.objects.get(user=user, status="active")
            if not subscription.polar_subscription_id:
                return {"success": False, "message": "Subscription provider ID not found."}

            polar = polar_sdk.Client(token=settings.POLAR_API_KEY)
            polar.subscriptions.cancel(subscription.polar_subscription_id)

            # Polar will send a webhook to update the status, but we can update it locally too
            subscription.auto_renew = False
            subscription.canceled_at = datetime.now()
            subscription.save()

            return {
                "success": True,
                "message": "Subscription scheduled for cancellation at the end of the period."
            }
        except UserSubscription.DoesNotExist:
            return {"success": False, "message": "No active subscription found."}
        except Exception as e:
            logger.error(f"Error canceling Polar subscription for user {user.id}: {e}")
            return {"success": False, "message": str(e)}

    # ... other existing service methods ...
