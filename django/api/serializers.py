from rest_framework import serializers
from django.contrib.auth import get_user_model  # Use get_user_model for flexibility
from .models import Resume

User = get_user_model()  # this is important


from rest_framework import serializers
from .models import Resume
from django.contrib.auth import get_user_model

User = get_user_model()

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Resume, GeneratedDocument, GeneratedWebsite  # Import related models

User = get_user_model()


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
