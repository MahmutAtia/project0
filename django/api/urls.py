from django.urls import path
from . import views

urlpatterns = [
    # User Profile and Avatar endpoints
    path("user/profile/", views.user_profile, name="user-profile"),
    path("user/avatar/upload/", views.upload_avatar, name="upload-avatar"),
    path("user/avatar/remove/", views.remove_avatar, name="remove-avatar"),
    path("user/avatar/", views.get_avatar, name="get-avatar"),
    
    # 1. Exact matches first
    path("resumes/", views.ResumeListCreateView.as_view(), name="resume-list-create"),
    path("resumes/generate-pdf/", views.generate_pdf, name="generate-pdf"),

    path(
        "resumes/generate_website/",
        views.generate_personal_website,
        name="generate-resume-website",
    ),
    path(
        "resumes/generate_website_yaml/",
        views.generate_personal_website_bloks,
        name="generate-resume-website-bloks",
    ),


    # document bloks
    path(
        "resumes/document_bloks/<uuid:document_id>/",
        views.get_document_bloks,
        name="get-document-bloks",
    ),
    path(
        "resumes/document/<uuid:document_id>/",
        views.get_document_pdf,
        name="get-document-pdf",
    ),
    path(
        "resumes/document/<uuid:document_id>/word/",
        views.get_document_docx,
        name="get-document-docx",
    ),
    # create_document
    path(
        "resumes/document/create/",
        views.create_document,
        name="create-document",
    ),

    # update_document
    path(
        "resumes/document/<uuid:document_id>/update/",
        views.update_document,
        name="update-document",
    ),
    # editor views here
    path(
        "website-yaml/<uuid:resume_id>/",
        views.get_website_yaml_json,
        name="serve_website_yaml_json",
    ),
    path(
        "website-yaml/update/<uuid:unique_id>/",
        views.update_website_yaml,
        name="save-updates-to-personal-website",
    ),
  
    # 2. Other prefixes with
    path(
        "<uuid:unique_id>/",
        views.serve_personal_website_yaml,
        name="view-personal-website-yaml",
    ),
    # ats checker
    path(
        "resumes/save_generated_resume/",
        views.save_generated_resume,
        name="save-generated-resume",
    ),

    # 4. General parameterized paths under 'resumes/'
    path(
        "resumes/<str:pk>/",
        views.ResumeRetrieveUpdateDestroyView.as_view(),
        name="resume-retrieve-update-destroy",
    ),
   #5. Task management
    path("task-status/<str:task_id>/",
        views.get_task_status,
        name="get_task_status",
    ),
   path("create-task/", views.internal_create_task, name="create-task"),
    path("update-task/", views.internal_update_task, name="update-task"),

]
