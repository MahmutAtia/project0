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
        # --- DEBUG ---
        print(f"\n--- [DEBUG] handle_polar_webhook_event called ---")
        print(f"--- [DEBUG] Event Type: {event_type}")
        print(f"--- [DEBUG] User ID: {user_id}")
        print(f"--- [DEBUG] Incoming Polar Data: {polar_subscription_data}")
        # --- END DEBUG ---

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            user = User.objects.get(id=user_id)
            # --- DEBUG ---
            print(f"--- [DEBUG] Successfully found user: {user.username} (ID: {user.id})")
            # --- END DEBUG ---
            
            # Get the product ID from the subscription data
            polar_product_id = polar_subscription_data.get("product_id")
            plan = Plan.objects.get(polar_product_id=polar_product_id)
            # --- DEBUG ---
            print(f"--- [DEBUG] Successfully found plan: {plan.name} (Matching Polar Product ID: {polar_product_id})")
            # --- END DEBUG ---

            # --- Helper function for safe parsing ---
            from django.utils.dateparse import parse_datetime
            from datetime import datetime

            def safe_parse_datetime(date_value):
                if date_value is None:
                    return None
                # The SDK can return datetime objects, so we handle both strings and datetimes
                return date_value if isinstance(date_value, datetime) else parse_datetime(date_value)

            # Parse the datetime strings safely
            start_date = safe_parse_datetime(polar_subscription_data.get("current_period_start"))
            end_date = safe_parse_datetime(polar_subscription_data.get("current_period_end"))

            # --- DEBUG ---
            print(f"--- [DEBUG] Parsed Start Date: {start_date}")
            print(f"--- [DEBUG] Parsed End Date: {end_date}")
            # --- END DEBUG ---

            # Base subscription data
            subscription_defaults = {
                "user": user,
                "plan": plan,
                "start_date": start_date,
                "end_date": end_date,
            }

            # Handle different event types
            if event_type == "subscription.created":
                # --- DEBUG ---
                print("--- [DEBUG] Matched event logic: subscription.created")
                # --- END DEBUG ---
                subscription_defaults.update({
                    "status": "active",
                    "auto_renew": True,
                    "canceled_at": None,
                })
                
            elif event_type == "subscription.active":
                # --- DEBUG ---
                print("--- [DEBUG] Matched event logic: subscription.active")
                # --- END DEBUG ---
                subscription_defaults.update({
                    "status": "active",
                    "auto_renew": True,
                    "canceled_at": None,
                })
                
            elif event_type == "subscription.updated":
                # --- DEBUG ---
                print("--- [DEBUG] Matched event logic: subscription.updated")
                # --- END DEBUG ---
                # Handle general updates
                auto_renew = not polar_subscription_data.get("cancel_at_period_end", False)
                canceled_at = safe_parse_datetime(polar_subscription_data.get("canceled_at"))
                    
                subscription_defaults.update({
                    "status": str(polar_subscription_data.get("status", "active")),
                    "auto_renew": auto_renew,
                    "canceled_at": canceled_at,
                })
                
            elif event_type == "subscription.canceled":
                # --- DEBUG ---
                print("--- [DEBUG] Matched event logic: subscription.canceled")
                # --- END DEBUG ---
                # Subscription is canceled but user keeps access until period end
                canceled_at = safe_parse_datetime(polar_subscription_data.get("canceled_at"))
                    
                subscription_defaults.update({
                    "status": "active",  # Still active until period end
                    "auto_renew": False,
                    "canceled_at": canceled_at,
                })
                
            elif event_type == "subscription.uncanceled":
                # --- DEBUG ---
                print("--- [DEBUG] Matched event logic: subscription.uncanceled")
                # --- END DEBUG ---
                # Subscription is reactivated
                subscription_defaults.update({
                    "status": "active",
                    "auto_renew": True,
                    "canceled_at": None,
                })
                
            elif event_type == "subscription.revoked":
                # --- DEBUG ---
                print("--- [DEBUG] Matched event logic: subscription.revoked")
                # --- END DEBUG ---
                # User loses access immediately
                canceled_at = safe_parse_datetime(polar_subscription_data.get("canceled_at"))
                    
                subscription_defaults.update({
                    "status": "revoked",  # Keep as revoked exactly as Polar sends
                    "auto_renew": False,
                    "canceled_at": canceled_at,
                })

            # --- DEBUG ---
            print(f"--- [DEBUG] Final data to be saved (defaults): {subscription_defaults}")
            # --- END DEBUG ---

            # Create or update subscription
            subscription, created = UserSubscription.objects.update_or_create(
                polar_subscription_id=polar_subscription_data["id"],
                defaults=subscription_defaults,
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

