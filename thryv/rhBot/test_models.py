from http.client import responses

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Interview


# Model Test
class InterviewModelTestCase(TestCase):
    def setUp(self):
        # test user
        self.user = User.objects.create_user(username="testuser", password="password123")

        #  interview instance
        self.interview = Interview.objects.create(
            interview_id="Int12345",
            user=self.user,
            job_description="software engineer",
            questions=[
                "Can you start by telling us a little about yourself and why you're interested in this Software Engineer position?",
                "How did you become interested in programming, and what sparked your passion for Python and Django?",
                "Can you explain the difference between a monolithic architecture and a microservices architecture? How would you decide which one to use for a given project?",
            ],
            conversation_history={
                "role": "assistant",
                "content": "1. Can you start by telling us a little about yourself and why you're interested in this Software Engineer position?"
            },
            status="ongoing"
        )

    def test_interview_creation(self):

        interview = Interview.objects.get(interview_id="Int12345")
        self.assertEqual(interview.user.username, "testuser")
        self.assertEqual(interview.job_description, "software engineer")
        self.assertEqual(interview.status, "ongoing")


# API Test Case (Integration Tests)

class InterviewAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client.login(username="testuser", password="password123")

        self.interview = Interview.objects.create(
            interview_id="int12345",
            user=self.user,
            job_description="Software Engineer",
            conversation_history={},
            status="ongoing"
        )
    def test_get_interview(self):
        response = self.client.get(f"/api/interviews/{self.interview.interview_id}/")
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertEqual(response.data["job_description"], "Software Engineer")
        self.assertEqual(response.data["status"], "ongoing")

    def test_create_interview(self):
        payload = {
            "job_description": "Software Engineer position requiring knowledge of springboot and java.",
            "user_id": self.user.id
        }
        response = self.client.post("/api/start-interview/",payload)
        print(response.data)
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertIsNotNone(response.data['current_question'])
        self.assertNotEqual(response.data['current_question'], "")
        self.assertEqual(response.data["status"], "ongoing")

