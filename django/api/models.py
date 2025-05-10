from django.db import models
from django.db.models import JSONField
import uuid
class Resume(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='resumes')  # Link to the user
    title = models.CharField(max_length=100, blank=True, null=True, help_text="A name for this resume (e.g., 'Software Engineer Resume')")
    resume = JSONField(blank=True, null=True)  # Stores the entire resume data as JSON
    about = models.TextField(blank=True, null=True, help_text="A brief description about the resume")
    description = models.TextField(blank=True, null=True, help_text="A detailed description about the resume")
    icon = models.CharField(max_length=100, blank=True, null=True, help_text="An icon name for this resume")
    is_default = models.BooleanField(default=False, help_text="Whether this resume is the default resume")
    other_docs = models.JSONField(blank=True, null=True, help_text="Any attachments related to this resume (e.g., cover letter)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Resume: {self.title or 'Unnamed'}"
class GeneratedWebsite(models.Model):
    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, related_name='personal_website')
    unique_id = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    yaml_content = models.TextField(default="")  # Default to an empty string
    json_content = models.JSONField(default=dict, blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Website for Resume ID: {self.resume.id}"
    
class GeneratedDocument(models.Model):
    # we may have multiple documents for a single resume, 
    # e.g., cover letter, CV, etc.
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='generated_documents', null=True, blank=True)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='generated_documents')
    unique_id = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    json_content = models.JSONField(default=dict)  # Stores the YAML content
    document_type = models.CharField(max_length=50,         choices=[
            ("cover_letter", "Cover Letter"),
            ("recommendation_letter", "Recommendation Letter"),
            ("motivation_letter", "Motivation Letter"),
        ],
        default="" # Consider if a default makes sense or if it should be required
    )
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Document for Resume ID: {self.resume.id}"

