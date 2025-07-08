import logging
import requests
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client, OAuth2Error
from rest_framework import status
from rest_framework.response import Response
from plans.models import Feature
from plans.services import UsageService, PlanService
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions


logger = logging.getLogger(__name__)


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://127.0.0.1:3000/api/auth/callback/google"
    client_class = OAuth2Client

    # def post(self, request, *args, **kwargs):
    #     try:
    #         access_token = request.data.get('access_token')
    #         if not access_token:
    #             return Response(
    #                 {"error": "No access token provided"},
    #                 status=status.HTTP_400_BAD_REQUEST
    #             )

    #         # Verify token with Google
    #         response = requests.get(
    #             'https://www.googleapis.com/oauth2/v3/userinfo',
    #             headers={'Authorization': f'Bearer {access_token}'}
    #         )

    #         if response.status_code != 200:
    #             logger.error(f"Google API Error: {response.text}")
    #             return Response(
    #                 {"error": "Invalid access token"},
    #                 status=status.HTTP_400_BAD_REQUEST
    #             )

    #         # Add verified user info to request
    #         request.data['user_info'] = response.json()
    #         return super().post(request, *args, **kwargs)

    #     except OAuth2Error as e:
    #         logger.error(f"OAuth2Error: {str(e)}")
    #         logger.error(f"Request data: {request.data}")
    #         return Response(
    #             {"error": str(e)},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #     except Exception as e:
    #         logger.exception("Unexpected error in Google login")
    #         return Response(
    #             {"error": "Authentication failed"},
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #         )


# Add this new view at the end of your existing views
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def verify_and_check_limits(request):
    """Verify token and check feature limits for FastAPI"""
    try:
        feature = request.GET.get("feature", "resume_generation")
        user = request.user

        logger.info(f"Verifying limits for user {user.id}, feature: {feature}")

        # Get user's current plan
        plan = PlanService.get_user_plan(user)
        logger.info(f"User plan: {plan}")

        if not plan:
            # No active subscription - return minimal limits
            logger.warning(f"No active subscription found for user {user.id}")
            return Response(
                {"error": "No active subscription found"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Get feature object
        try:
            feature_obj = Feature.objects.get(code=feature, is_active=True)
            logger.info(f"Feature object found: {feature_obj}")
        except Feature.DoesNotExist:
            logger.error(f"Feature '{feature}' not found")
            return Response(
                {"error": f"Feature '{feature}' not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get current usage using your existing service
        current_usage = UsageService.get_current_usage(user, feature)
        logger.info(f"Current usage: {current_usage}")

        # Get limit from plan
        try:
            plan_limit = plan.feature_limits.get(feature=feature_obj)
            limit = plan_limit.limit
            logger.info(f"Plan limit: {limit}")
        except Exception as e:
            logger.error(f"Error getting plan limit: {e}")
            limit = 0

        # Calculate remaining
        if limit == -1:  # Unlimited
            remaining = -1
            can_use = True
        else:
            remaining = max(0, limit - current_usage)
            can_use = remaining > 0

        if not can_use and limit != -1:
            logger.warning(f"Feature limit exceeded for user {user.id}")
            return Response(
                {"error": "Feature limit exceeded"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        response_data = {
            "user_id": user.id,
            "remaining_uses": remaining,
            "user_email": user.email,
            "feature": feature,
            "current_usage": current_usage,
            "limit": limit,
        }
        logger.info(f"Returning successful response: {response_data}")

        return Response(response_data)

    except Exception as e:
        logger.exception(f"Unexpected error in verify_and_check_limits: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
