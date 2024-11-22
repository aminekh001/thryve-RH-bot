from django.db import models
from django.contrib.auth.models import User

class Interview(models.Model):
    interview_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_description = models.TextField()
    questions = models.JSONField()
    conversation_history = models.JSONField()
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Interview {self.interview_id} for {self.user.username}"