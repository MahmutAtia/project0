from django.urls import path
from . import views

urlpatterns = [
    path('resumes/', views.ResumeListCreateView.as_view(), name='resume-list-create'),
    path('resumes/generate/', views.generate_resume, name='generate-resume'),  # Keep this, it might be different from generate-pdf
    path('resumes/generate-pdf/', views.generate_pdf, name='generate-pdf'), # Move this up
    path('resumes/generate_from_job_desc/', views.generate_from_job_desc, name='generate-resume-from-job-desc'),
    path('resumes/edit/', views.generate_resume_section, name='edit-resume'),
    path('resumes/<str:pk>/generate/', views.generate_resume, name='generate-resume'), # Keep this, it might be different from generate-pdf
    path('resumes/<str:pk>/', views.ResumeRetrieveUpdateDestroyView.as_view(), name='resume-retrieve-update-destroy'),
]