

from rest_framework import serializers
from django.contrib.auth import get_user_model  # Use get_user_model for flexibility
from .models import Resume

User = get_user_model() # this is important

# class ResumeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Resume
#         fields = ['id', 'user', 'name', 'data', 'created_at', 'updated_at']
#         extra_kwargs = {'user': {'write_only': True}}

#     def create(self, validated_data):
#         user = self.context['request'].user  # Get the authenticated user from the request
#         user = User.objects.first() # get the first user
#         print(user)
#         resume = Resume.objects.create(user=user, **validated_data) # create resume with user
#         return resume

# from rest_framework import serializers
# from .models import Resume

# class ResumeSerializer(serializers.ModelSerializer):
#     user = serializers.HiddenField(default=serializers.CurrentUserDefault())

#     class Meta:
#         model = Resume
#         fields = '__all__'


from rest_framework import serializers
from .models import Resume
from django.contrib.auth import get_user_model

User = get_user_model()

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = '__all__'
        extra_kwargs = {'user': {'required': False}}  # Make user field optional in requests

    def create(self, validated_data):
        # Get the first user from the database

        # Add user to validated_data and create resume
        return Resume.objects.create(**validated_data)