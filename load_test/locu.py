from locust import HttpUser, task, constant
import random


class QuickstartUser(HttpUser):
        wait_time = constant(0)
        host = "http://localhost:8000/"

        
        @task    
        def on_start(self):
            self.client.post("/login", {"username":"foo", "password":"bar"})
