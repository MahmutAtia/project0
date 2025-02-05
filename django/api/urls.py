from django.urls import path
from . import views

urlpatterns = [
    path('resumes/', views.ResumeListCreateView.as_view(), name='resume-list-create'),
    path('resumes/generate/', views.generate_resume, name='generate-resume'),
    path('resumes/generate_from_job_desc/', views.generate_from_job_desc, name='generate-resume-from-job-desc'),
    path('resumes/edit/', views.generate_resume_section, name='edit-resume'),  # Removed ()
    path('resumes/<str:pk>/', views.ResumeRetrieveUpdateDestroyView.as_view(), name='resume-retrieve-update-destroy'),
   

]