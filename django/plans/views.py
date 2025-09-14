from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
from decimal import Decimal
from polar_sdk import Polar
from django.conf import settings
from django.urls import reverse
from polar_sdk.webhooks import validate_event, WebhookVerificationError


from .models import Plan, UserSubscription, PlanPayment, Feature, UsageRecord
from .serializers import (
    PlanSerializer,
    UserSubscriptionSerializer,
    PlanPaymentSerializer,
)
from .services import PlanService, UsageService, SubscriptionService  

class PlanListView(ListView):
    model = Plan
    template_name = "plans/plan_list.html"
    context_object_name = "plans"

    def get_queryset(self):
        return Plan.objects.filter(is_active=True).order_by("price")


@api_view(["GET"])
def get_plans(request):
    """API endpoint to get all active plans"""
    plans = (
        Plan.objects.filter(is_active=True)
        .prefetch_related("feature_limits__feature")
        .order_by("price")
    )
    serializer = PlanSerializer(plans, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancel user's current subscription - this will be handled by Polar"""
    try:
        subscription = SubscriptionService.get_active_subscription(request.user)
        if not subscription:
            return Response({"error": "No active subscription found"}, status=status.HTTP_404_NOT_FOUND)

        if not subscription.polar_subscription_id:
            return Response({"error": "Cannot cancel: Subscription not linked to payment provider"}, status=status.HTTP_400_BAD_REQUEST)

        # Use Polar SDK to cancel subscription
        with Polar(access_token=settings.POLAR_API_KEY, server="sandbox") as polar:
            polar.subscriptions.cancel(subscription.polar_subscription_id)

        return Response({
            "success": True,
            "message": "Subscription will be canceled at the end of the current period. You'll receive a confirmation email shortly."
        })

    except Exception as e:
        return Response({"error": f"Failed to cancel subscription: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_subscription(request):
    """Get current user's subscription details with proper status"""
    subscription = SubscriptionService.get_active_subscription(request.user)

    if subscription:
        # Use the serializer instead of manual construction
        plan_serializer = PlanSerializer(subscription.plan)

        is_canceling = (
            subscription.is_in_grace_period
            if hasattr(subscription, "is_in_grace_period")
            else (subscription.canceled_at is not None and not subscription.auto_renew)
        )

        return Response(
            {
                "has_subscription": True,
                "plan": plan_serializer.data,  # Use serialized data
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "is_active": subscription.status == "active",
                "auto_renew": subscription.auto_renew,
                "canceled_at": subscription.canceled_at,
                "is_canceling": is_canceling,
                "days_remaining": (
                    subscription.days_remaining
                    if hasattr(subscription, "days_remaining")
                    else 0
                ),
                "status": subscription.status,
            }
        )
    else:
        return Response({"has_subscription": False, "plan": None})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_usage_stats(request):
    """Get user's current usage statistics"""
    user = request.user
    plan = PlanService.get_user_plan(user)

    if not plan:
        return Response(
            {"error": "No active subscription found"}, status=status.HTTP_404_NOT_FOUND
        )

    features = Feature.objects.filter(is_active=True)
    usage_stats = []

    # Get current period dates
    start_date, end_date = UsageService.get_current_period_dates(plan.billing_period)

    for feature in features:
        # Get the feature limit for this plan
        try:
            plan_limit = plan.feature_limits.get(feature=feature)
            limit = plan_limit.limit
        except:
            limit = 0

        # Get current usage for this period
        try:
            usage_record = UsageRecord.objects.get(
                user=user, feature=feature, period_start=start_date
            )
            used = usage_record.count
        except UsageRecord.DoesNotExist:
            used = 0

        # Calculate remaining
        if limit == -1:  # Unlimited
            remaining = -1
            unlimited = True
        else:
            remaining = max(0, limit - used)
            unlimited = False

        usage_stats.append(
            {
                "feature": feature.name,
                "feature_code": feature.code,
                "used": used,
                "limit": limit,
                "remaining": remaining,
                "unlimited": unlimited,
            }
        )

    return Response(
        {
            "plan": plan.name,
            "usage_stats": usage_stats,
            "current_period": {"start": start_date, "end": end_date},
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_payment_history(request):
    """Get user's payment history"""
    payments = PlanPayment.objects.filter(user=request.user).order_by("-created")
    serializer = PlanPaymentSerializer(payments, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_polar_checkout_session(request):
    """Create a Polar checkout session for a given plan."""
    plan_id = request.data.get("plan_id")
    user = request.user
    if not plan_id:
        return Response({"error": "plan_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        plan = Plan.objects.get(id=plan_id, is_active=True)
    except Plan.DoesNotExist:
        return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)

    # # Check for existing active subscription to same plan
    # existing_subscription = SubscriptionService.get_active_subscription(request.user)
    # if existing_subscription and existing_subscription.plan.id == plan_id:
    #         return Response(
    #         {
    #             "success": True,
    #             "message": "You are already subscribed to this plan",
    #             "subscription_id": existing_subscription.id,
    #             "already_subscribed": True,
    #         }
    #     )
        
    # # For ANY plan (free or paid), first try to reactivate recent subscription
    # reactivation_result = SubscriptionService.reactivate_subscription(
    #     request.user, plan
    # )

    # if reactivation_result["success"]:
    #     return Response(
    #         {
    #             "success": True,
    #             "message": f"{plan.name} reactivated successfully! No new payment required.",
    #             "subscription_id": reactivation_result["subscription"].id,
    #             "reactivated": True,
    #         }
    #     )
    
    # For paid and free plans, ensure Polar product ID is set
    if not plan.polar_product_id:
        return Response({"error": "Plan is not configured for Polar payments"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with Polar(
            access_token=settings.POLAR_API_KEY,
            server="sandbox" 
        ) as polar:

            # Create the checkout session
            checkout_session = polar.checkouts.create(
              request = {
                    "products": [plan.polar_product_id],
                    # "discount": {
                    #     "type": "fixed",
                    #     "amount": 200,        # e.g. $2 off
                    #     "currency": "USD"
                    # },
                    
                    # "attached_custom_fields": [
                    #     {
                    #         "custom_field_id": "cf_123",
                   
                    #         "required": True,
                    #         "order": 1
                    #     }
                      "customer_metadata": {
                        "user_id": str(user.id),   # ✅ Include your user ID here
                    },
                    "customer_name": user.get_full_name() or user.username,
                    "customer_email": user.email,
                    "success_url": f"http://{settings.PAYMENT_HOST}/main/plans/",
                    "embed_origin": f"http://{settings.PAYMENT_HOST}",
                    # ],
                    # You might need success_url and cancel_url
                    # "success_url": "https://your-site.com/success",
                    # "cancel_url": "https://your-site.com/cancel",
                }
            )

            return Response({
                "checkout_url": checkout_session.url,
                "checkout_id": checkout_session.id
            })
    except Exception as e:
        return Response({"error": f"Failed to create checkout session: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





@csrf_exempt
@api_view(["POST"])
def polar_webhook(request):
    """Handle incoming webhooks from Polar using the official SDK for validation."""
    try:
        # Validate the event using the Polar SDK
        # This handles signature verification and payload parsing
        event = validate_event(
            body=request.body,
            headers=request.headers,
            secret=settings.POLAR_WEBHOOK_SECRET,
        )
        event_type = event.TYPE
        payload = event.data

        print(f"Processing event type: {event_type}")

        # Handle all subscription event types
        subscription_events = [
            "subscription.created",
            "subscription.active",
            "subscription.updated",
            "subscription.canceled",
            "subscription.uncanceled",
            "subscription.revoked",
        ]

        if event_type in subscription_events:
            # The 'payload' from validate_event is the 'data' object in the webhook
            subscription_data = payload.dict()
            metadata = subscription_data.get("customer", {}).get("metadata", {})
            user_id = metadata.get("user_id")

            if user_id:
                print(f"Processing {event_type} for user_id: {user_id}")
                SubscriptionService.handle_polar_webhook_event(
                    event_type, user_id, subscription_data
                )
            else:
                print("No user_id found in webhook metadata")
        
        # Acknowledge receipt of the webhook, even if we don't process it.
        return Response({"status": "success", "message": f"Event '{event_type}' received."}, status=status.HTTP_202_ACCEPTED)

    except WebhookVerificationError as e:
        print(f"Webhook verification failed: {e}")
        return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Test endpoint for recording usage manually
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def test_usage_recording(request):
    """Test endpoint to record usage manually"""
    feature_code = request.data.get("feature_code")
    if not feature_code:
        return Response({"error": "feature_code required"})

    success = UsageService.record_feature_usage(request.user, feature_code)

    if success:
        return Response({"message": f"Usage recorded for {feature_code}"})
    else:
        return Response({"error": "Failed to record usage"})
