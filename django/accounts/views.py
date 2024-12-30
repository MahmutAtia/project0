import logging
import requests
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client, OAuth2Error
from rest_framework import status
from rest_framework.response import Response

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