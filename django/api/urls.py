from django.urls import path
from . import views

urlpatterns = [
# Exact matches first
path("resumes/", views.ResumeListCreateView.as_view(), name="resume-list-create"),
path("resumes/generate-pdf/", views.generate_pdf, name="generate-pdf"),
path("resumes/save_generated_website/", views.save_generated_website, name="save-generated-website"),
path("resumes/document/create/", views.create_document, name="create-document"),
path("resumes/document_bloks/<uuid:document_id>/", views.get_document_bloks, name="get-document-bloks"),
path("resumes/document/<uuid:document_id>/", views.get_document_pdf, name="get-document-pdf"),
path("resumes/document/<uuid:document_id>/word/", views.get_document_docx, name="get-document-docx"),
path("resumes/document/<uuid:document_id>/update/", views.update_document, name="update-document"),
path("resumes/save_generated_resume/", views.save_generated_resume, name="save-generated-resume"),

# Website
path("website-yaml/<str:resume_id>/", views.get_website_yaml_json, name="serve_website_yaml_json"),
path("website-yaml/update/<str:unique_id>/", views.update_website_yaml, name="save-updates-to-personal-website"),

# User profile & avatar
path("user/profile/", views.user_profile, name="user-profile"),
path("user/avatar/upload/", views.upload_avatar, name="upload-avatar"),
path("user/avatar/remove/", views.remove_avatar, name="remove-avatar"),
path("user/avatar/", views.get_avatar, name="get-avatar"),

# Generic resume detail (put last!)
path("resumes/<int:pk>/", views.ResumeRetrieveUpdateDestroyView.as_view(), name="resume-detail"),

# Data export and deletion endpoints
path("user/export/", views.export_user_data, name="export-user-data"),
path("user/delete/request/", views.request_account_deletion, name="request-account-deletion"),
path("user/delete/confirm/", views.confirm_account_deletion, name="confirm-account-deletion"),


# Task management
path("task-status/<str:task_id>/", views.get_task_status, name="get_task_status"),
path("create-task/", views.internal_create_task, name="create-task"),
path("update-task/", views.internal_update_task, name="update-task"),

]
