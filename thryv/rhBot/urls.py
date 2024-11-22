from django.urls import path
from .views import StartInterviewAPIView, ContinueInterviewAPIView ,EndInterviewAPIView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('start-interview/', StartInterviewAPIView.as_view(), name='start-interview'),
    path('continue-interview/', ContinueInterviewAPIView.as_view(), name='continue-interview'),
    path('end-interview/', EndInterviewAPIView.as_view(), name='end_interview'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
