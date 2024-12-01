from django.test import TestCase
from django.contrib.auth.models import  User
from  .models import Interview

class InterviewModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser",password="password123")


        self.interview = Interview.objects.create(
            interview_id="Int12345",
            user=self.user,
            job_description="software engeineer",
            questions={"1. Can you start by telling us a little about yourself and why you're interested in this Software Engineer position?",
                        "2. How did you become interested in programming, and what sparked your passion for Python and Django?",
                        "3. Can you explain the difference between a monolithic architecture and a microservices architecture? How would you decide which one to use for a given project?"},
            conversation_history={"role\": \"assistant\", \"content\":\"1. Can you start by telling us a little about yourself and why you're interested in this Software Engineer position?\""},
            status="ongoing"
        )

        def  test_interview_cretion(self):
          interview = Interview.objects.get(interview_id="Int12345")
          self.assertEqual(interview.user.username, "testuser")
          self.assertEqual(interview.job_description, "software engeineer")
          self.assertEqual(interview.status, "ongoing")

