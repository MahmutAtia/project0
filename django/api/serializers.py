from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Resume, GeneratedDocument, GeneratedWebsite, UserProfile
import io
import yaml

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile with avatar support"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'avatar']
        read_only_fields = ['id', 'username', 'email']
    
    def validate_avatar(self, value):
        """Validate base64 avatar image"""
        if value:
            # Basic validation for base64 image
            if not value.startswith('data:image/'):
                raise serializers.ValidationError("Avatar must be a valid base64 image data URL")
            
            # Check file size (approximate, base64 is ~33% larger than binary)
            import base64
            try:
                # Extract base64 data after comma
                header, data = value.split(',', 1)
                decoded = base64.b64decode(data)
                # Limit to 5MB
                if len(decoded) > 5 * 1024 * 1024:
                    raise serializers.ValidationError("Avatar image is too large. Maximum size is 5MB")
            except Exception:
                raise serializers.ValidationError("Invalid base64 image format")
        
        return value
    
    def update(self, instance, validated_data):
        # Handle nested user data
        user_data = {}
        if 'user' in validated_data:
            user_data = validated_data.pop('user')
        
        # Update user fields
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        
        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedDocument
        fields = [
            "unique_id",  # Keep the UUID
            "json_content",  # Assuming your JSON field is named
            "created_at",
            "document_type",
            # Add any other fields from GeneratedDocument you want to expose
        ]


class ResumeSerializer(serializers.ModelSerializer):
    # user = serializers.ReadOnlyField(source='user.username') # Option 1: Display username
    user = serializers.PrimaryKeyRelatedField(
        read_only=True
    )  # Option 2: Display user ID (default for FK)
    resume = serializers.CharField(required=False, allow_blank=True) # Make it a writable field
    generated_documents_data = serializers.SerializerMethodField(
        read_only=True
    )  # New field
    personal_website_uuid = serializers.SerializerMethodField(
        read_only=True
    )  # New field

    class Meta:
        model = Resume
        fields = [
            "id",
            "user",
            "title",
            "resume",
            "about",
            "description",
            "icon",
            "is_default",
            "job_search_keywords",
            "sections_sort",
            "hidden_sections",
            "created_at",
            "updated_at",
            "generated_documents_data",  # New field
            "personal_website_uuid",  # New field
        ]
        # 'user' is read-only as it's set by the view during creation.

    def to_representation(self, instance):
        """
        Convert the `resume` YAML string from the model into a Python object for the JSON response.
        """
        ret = super().to_representation(instance)
        resume_yaml_string = instance.resume
        if resume_yaml_string:
            try:
                ret['resume'] = yaml.safe_load(resume_yaml_string)
            except yaml.YAMLError:
                ret['resume'] = None # Or some error indicator
        else:
            ret['resume'] = None
        return ret

    def to_internal_value(self, data):
        """
        Convert the incoming `resume` object/string into a YAML string to be saved in the database.
        """
        resume_data = data.get('resume')
        if resume_data and isinstance(resume_data, dict):
            # If 'resume' is an object, convert it to a YAML string
            try:
                string_stream = io.StringIO()
                yaml.dump(resume_data, string_stream, sort_keys=False, default_flow_style=False)
                data['resume'] = string_stream.getvalue()
            except Exception as e:
                raise serializers.ValidationError({"resume": f"Could not serialize resume object to YAML: {e}"})

        # The incoming request from FastAPI sends the resume as a string already.
        # If it were an object, we would dump it to YAML here.
        # This method ensures the field is correctly processed.
        return super().to_internal_value(data)


    def get_generated_documents_data(self, obj: Resume):  # Renamed method
        """
        Returns a list of serialized data for all GeneratedDocument instances
        related to this Resume.
        """
        if hasattr(obj, "generated_documents"):  # Check if prefetch_related was used
            documents = obj.generated_documents.all()
            # Pass context if your GeneratedDocumentSerializer needs it (e.g., for request-aware fields)
            # For simple serialization, context might not be strictly necessary here.
            # serializer_context = {'request': self.context.get('request')} if self.context.get('request') else {}
            return GeneratedDocumentSerializer(
                documents, many=True, context=self.context
            ).data
        return []

    def get_personal_website_uuid(self, obj: Resume):
        """
        Returns the unique_id of the GeneratedWebsite related to this Resume,
        if one exists.
        """
        try:
            # The related name from Resume to GeneratedWebsite is 'personal_website'
            if hasattr(obj, "personal_website") and obj.personal_website:
                return obj.personal_website.unique_id
        except (
            GeneratedWebsite.DoesNotExist
        ):  # Should be caught by hasattr check if prefetch_related is used
            pass
        except AttributeError:  # Should be caught by hasattr check
            pass
        return None

    # The create method in the view (perform_create) will handle setting the user.
    # So, the default create method of ModelSerializer is generally fine.
    # If you had a custom create here, ensure it correctly handles the user from context if needed.
    # The existing create method in your file is not ideal as it doesn't use the request user.
    # It's better to rely on the view's perform_create.


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile with avatar support"""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "avatar"]
        read_only_fields = ["id", "username"]

    def validate_avatar(self, value):
        """Validate base64 avatar image"""
        if value:
            # Basic validation for base64 image
            if not value.startswith("data:image/"):
                raise serializers.ValidationError("Avatar must be a valid base64 image data URL")

            # Check file size (approximate, base64 is ~33% larger than binary)
            import base64

            try:
                # Extract base64 data after comma
                header, data = value.split(",", 1)
                decoded = base64.b64decode(data)
                # Limit to 5MB
                if len(decoded) > 5 * 1024 * 1024:
                    raise serializers.ValidationError("Avatar image is too large. Maximum size is 5MB")
            except Exception:
                raise serializers.ValidationError("Invalid base64 image format")

        return value
