from django.urls import path
from .views import ResumeUploadView

urlpatterns = [
    path('v1/resumes/upload/', ResumeUploadView.as_view(), name='resume-upload'),
]
