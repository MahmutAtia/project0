from django.urls import path
from . import views

urlpatterns = [
    # 1. Exact matches first
    path('resumes/', views.ResumeListCreateView.as_view(), name='resume-list-create'),
    path('resumes/generate/', views.generate_resume, name='generate-resume'),
    path('resumes/generate-pdf/', views.generate_pdf, name='generate-pdf'),
    path('resumes/generate_website/', views.generate_personal_website, name='generate-resume-website'),
    path('resumes/generate_website_yaml/', views.generate_personal_website_bloks, name='generate-resume-website-bloks'),
    path('resumes/generate_from_job_desc/', views.generate_from_job_desc, name='generate-resume-from-job-desc'),
    path('resumes/edit/', views.generate_resume_section, name='edit-resume'),
    
    # gererate document
    path('resumes/generate_document/', views.generate_document_bloks, name='generate-document'),


    # editor views here
    path('website-yaml/<uuid:resume_id>/', views.get_website_yaml_json, name='serve_website_yaml_json'),
    path('website-yaml/update/<uuid:unique_id>/', views.update_website_yaml, name='save-updates-to-personal-website'),
    path('website-yaml/edit-block/', views.edit_website_block, name='edit_website_block'), # With trailing slash

    # 2. Other prefixes with parameters
    path('website/<uuid:unique_id>/', views.serve_personal_website, name='view-personal-website'),
    path('<uuid:unique_id>/', views.serve_personal_website_yaml, name='view-personal-website-yaml'),

    # 3. Specific parameterized paths under 'resumes/'
    path('resumes/<str:pk>/generate/', views.generate_resume, name='generate-resume-with-pk'),

    # 4. General parameterized paths under 'resumes/'
    path('resumes/<str:pk>/', views.ResumeRetrieveUpdateDestroyView.as_view(), name='resume-retrieve-update-destroy'),
    
    
    # 5. Generate document
    path('resumes/generate_document/', views.generate_document_bloks, name='generate-document'),
    path('resumes/document/<uuid:unique_id>/', views.get_document_pdf, name='view-document'),
    # path('resumes/<str:pk>/document/<uuid:unique_id>/update/', views.update_document, name='update-document'),
    
]