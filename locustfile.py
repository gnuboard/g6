# locustfile.py
from locust import HttpUser, task, between, TaskSet


class UserBehavior(TaskSet):
    @task(1)
    def home(self):
        self.client.get('')


class LocustUser(HttpUser):
    host = "http://127.0.0.1:8000"
    tasks = [UserBehavior]
    wait_time = between(1, 4)
