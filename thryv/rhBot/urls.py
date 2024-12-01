from django.urls import path

from .interviewCrude import InterviewByUserAPIView
from .views import StartInterviewAPIView, ContinueInterviewAPIView, InterviewDetailView
from django.conf import settings
from django.conf.urls.static import static





urlpatterns = [
    path('start-interview/', StartInterviewAPIView.as_view(), name='start-interview'),
    path('continue-interview/', ContinueInterviewAPIView.as_view(), name='continue-interview'),
    path('interviews/user/<int:user_id>/', InterviewByUserAPIView.as_view(),name='get_interviews_by_user'),
    path('interviews/', InterviewByUserAPIView.as_view(), name='create_interview'),
    #path('interviews/<int:interview_id>/', InterviewByUserAPIView.as_view(),name='update_delete_interview'),
    path('interviews/<str:interview_id>/', InterviewDetailView.as_view(), name='interview_detail'),
    # path('end-interview/', EndInterviewAPIView.as_view(), name='end_interview'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
