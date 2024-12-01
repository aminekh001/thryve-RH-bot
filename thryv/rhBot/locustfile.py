from http.client import responses

from locust import HttpLocust, between, task, HttpUser


class InterviewApiUser(HttpUser):
    wait_time =  between(1,5)
    interview_id = None


    @task
    def start_interview(self):
        payload={
            "job_description": "Data Scientist",
            "user_id": 2
        }

        response= self.client.post("/api/start-interview/",json=payload)
        print(response.status_code,response.json())
        if response.status_code == 200:
            self.interview_id = response.json().get("interview_id")

    @task
    def get_interview(self):
        if self.interview_id:
            print(f"Fetching Interview with ID: {self.interview_id}")
            response = self.client.get(f"/api/interviews/{self.interview_id}/")
            print(f"Get Interview Response: {response.status_code}, {response.json()}")
        else:
            print("No interview_id available, skipping get_interview task.")