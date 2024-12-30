from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        user_model = get_user_model()
        user_email = sociallogin.user.email.lower()
        if user_model.objects.filter(email=user_email).exists():
            existing_user = user_model.objects.get(email=user_email)
            sociallogin.connect(request, existing_user)