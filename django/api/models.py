from django.db import models
from django.db.models import JSONField
from django.contrib.auth.models import User
import uuid


DEFAULT_RESUME_SECTION_KEYS = [
    "personal_information",
    "summary",
    "objective",
    "experience",
    "education",
    "skills",
    "languages",
    "projects",
    "awards_and_recognition",
    "Volunteer_and_social_activities",
    "certifications",
    "interests",
    "references",
    "publications",
    "courses",
    "conferences",
    "speaking_engagements",
    "patents",
    "professional_memberships",
    "military_service",
    "teaching_experience",
    "research_experience",
]


class Resume(models.Model):
    """
    Resume model storing user's resume data as JSON.
    
    The resume JSON structure includes:
    - personal_information: Contact details, profiles, and avatar inclusion preference
    - Various sections: experience, education, skills, etc.
    
    Avatar Inclusion:
    The 'includeAvatarInPDF' field in personal_information controls whether
    the user's avatar should be included in PDF/website generation.
    """
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="resumes"
    )  # Link to the user
    title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="A name for this resume (e.g., 'Software Engineer Resume')",
    )
    resume = JSONField(blank=True, null=True)  # Stores the entire resume data as JSON
    about = models.TextField(
        blank=True, null=True, help_text="A brief description about the resume"
    )
    description = models.TextField(
        blank=True, null=True, help_text="A detailed description about the resume"
    )
    icon = models.CharField(
        max_length=100, blank=True, null=True, help_text="An icon name for this resume"
    )
    is_default = models.BooleanField(
        default=False, help_text="Whether this resume is the default resume"
    )

    job_search_keywords = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Keywords related to job search (e.g., 'Python, Django')",
    )
    sections_sort = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of section keys for the resume structure.",
    )
    hidden_sections = models.JSONField(
        default=list, blank=True, help_text="Empty or hidden sections by user"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ... other fields ...
    generation_task_id = models.CharField(max_length=255, null=True, blank=True, unique=True)


    def __str__(self):
        return f"{self.user.username}'s Resume: {self.title or 'Unnamed'}"

    def save(self, *args, **kwargs):
        is_new = not self.pk  # Check if the instance is being created

        # Ensure only one resume is marked as default
        if self.is_default:
            # Set is_default=False for all other resumes of the same user
            Resume.objects.filter(user=self.user, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)

        # If this is the first resume for the user, set it as default
        if is_new and not Resume.objects.filter(user=self.user).exists():
            self.is_default = True

        if is_new:
            # 1. Initialize sections_sort if it's empty or not provided
            if not self.sections_sort:  # Handles None or empty list from default=list
                self.sections_sort = list(
                    DEFAULT_RESUME_SECTION_KEYS
                )  # Ensure it's a new list instance

            # 2. Initialize hidden_sections by checking empty sections in resume JSON
            if not self.hidden_sections:
                self.hidden_sections = []

            # Check for empty sections in resume JSON and add to hidden_sections
            if self.resume:
                for section_key in DEFAULT_RESUME_SECTION_KEYS:
                    # Check if section exists and is empty/None
                    section_data = self.resume.get(section_key)

                    # empty list or emtpty dict or None
                    if section_data is None or (
                        isinstance(section_data, (list, dict)) and not section_data
                    ):
                        # If section is empty, add to hidden_sections
                        # Only add if it's not already there to avoid duplicates
                        if section_key not in self.hidden_sections:
                            self.hidden_sections.append(section_key)
                    else:
                        # If section has data, remove from hidden if it was there
                        if section_key in self.hidden_sections:
                            self.hidden_sections.remove(section_key)
                
                # Set default avatar inclusion preference for new resumes
                if 'personal_information' in self.resume:
                    if 'includeAvatarInPDF' not in self.resume['personal_information']:
                        self.resume['personal_information']['includeAvatarInPDF'] = False
                elif self.resume:
                    # Create personal_information section if it doesn't exist
                    self.resume['personal_information'] = {'includeAvatarInPDF': False}
        super().save(*args, **kwargs)

    def should_include_avatar_in_pdf(self):
        """
        Check if avatar should be included in PDF generation.
        Returns False by default for privacy and professional document standards.
        """
        if (self.resume and 
            'personal_information' in self.resume and 
            'includeAvatarInPDF' in self.resume['personal_information']):
            return self.resume['personal_information']['includeAvatarInPDF']
        return False  # Default to False for professional documents

    def set_avatar_inclusion_preference(self, include=True):
        """
        Set the avatar inclusion preference for this resume.
        """
        if not self.resume:
            self.resume = {}
        if 'personal_information' not in self.resume:
            self.resume['personal_information'] = {}
        
        self.resume['personal_information']['includeAvatarInPDF'] = include
        self.save()

class GeneratedWebsite(models.Model):
    resume = models.OneToOneField(
        Resume, on_delete=models.CASCADE, related_name="personal_website"
    )
    unique_id = models.CharField(max_length=200, unique=True, editable=False)
    yaml_content = models.TextField(default="")  # Default to an empty string
    json_content = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Website for Resume ID: {self.resume.id}"


class GeneratedDocument(models.Model):
    # we may have multiple documents for a single resume,
    # e.g., cover letter, CV, etc.
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="generated_documents",
        null=True,
        blank=True,
    )
    resume = models.ForeignKey(
        Resume, on_delete=models.CASCADE, related_name="generated_documents"
    )
    unique_id = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    json_content = models.JSONField(default=dict)  # Stores the YAML content
    document_type = models.CharField(
        max_length=50,
        choices=[
            ("cover_letter", "Cover Letter"),
            ("recommendation_letter", "Recommendation Letter"),
            ("motivation_letter", "Motivation Letter"),
        ],
        default="",  # Consider if a default makes sense or if it should be required
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for Resume ID: {self.resume.id}"


# User Profile extension for avatar
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.TextField(
        blank=True, 
        null=True, 
        help_text='Base64 encoded avatar image (max ~2MB compressed)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def save(self, *args, **kwargs):
        # Validate avatar size (rough base64 size check)
        if self.avatar and len(self.avatar) > 3000000:  # ~2.2MB after base64 encoding
            raise ValueError("Avatar image too large. Please use an image smaller than 2MB.")
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_profile(cls, user):
        """Get or create profile for a user"""
        profile, created = cls.objects.get_or_create(user=user)
        return profile
    
    @property
    def avatar_size_kb(self):
        """Get approximate size of avatar in KB"""
        if self.avatar:
            return len(self.avatar) // 1024
        return 0


class BackgroundTask(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILURE = 'FAILURE', 'Failure'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True, related_name='background_tasks')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    result = models.JSONField(null=True, blank=True) # Stores the final generated resume
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        user_identifier = self.user.username if self.user else "Anonymous"
        return f"Task {self.id} for {user_identifier}"