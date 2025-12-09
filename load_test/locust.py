"""
Locust load testing script for Faction Backend APIs
Tests 2-3 basic APIs with configurable user load (up to 10,000 users)

Usage:
    # Run with web UI (default: http://localhost:8089)
    locust -f locust.py --host=http://localhost:8000

    # Run headless with 10,000 users
    locust -f locust.py --host=http://localhost:8000 --users=10000 --spawn-rate=100 --headless --run-time=10m

    # Generate HTML report with analytics (RECOMMENDED)
    locust -f locust.py --host=http://localhost:8000 --users=10000 --spawn-rate=100 --headless --run-time=10m --html=report.html --csv=results

    # Run with specific host
    locust -f locust.py --host=http://your-server:8000
"""

from locust import HttpUser, task, between
import random


# class FactionAPIUser(HttpUser):
#     """
#     Simulates a user interacting with Faction Backend APIs
#     """
#     wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
#     def on_start(self):
#         """Called when a user starts. Can be used for authentication setup."""
#         # Optional: Set up authentication token here if needed
#         # self.token = self.get_auth_token()
#         # self.client.headers.update({"Authorization": f"Bearer {self.token}"})
#         pass
    
#     @task(3)
#     def get_root_endpoint(self):
#         """
#         Test the root/health check endpoint
#         Weight: 3 (30% of requests)
#         """
#         with self.client.get("/", catch_response=True, name="GET / (Root)") as response:
#             if response.status_code == 200:
#                 response.success()
#             else:
#                 response.failure(f"Expected 200, got {response.status_code}")
    
#     @task(5)
#     def get_questions_qotd(self):
#         """
#         Test the Question of the Day endpoint
#         Weight: 5 (50% of requests) - Most common endpoint
#         """
#         with self.client.get(
#             "/api/v1/questions/qotd",
#             catch_response=True,
#             name="GET /api/v1/questions/qotd"
#         ) as response:
#             if response.status_code == 200:
#                 try:
#                     data = response.json()
#                     if "questions" in data:
#                         response.success()
#                     else:
#                         response.failure("Invalid response format")
#                 except:
#                     response.failure("Failed to parse JSON")
#             elif response.status_code == 404:
#                 response.failure("Endpoint not found")
#             else:
#                 response.failure(f"Expected 200, got {response.status_code}")
    
#     @task(2)
#     def get_questions_list(self):
#         """
#         Test the questions list endpoint with various query parameters
#         Weight: 2 (20% of requests)
#         """
#         # Random query parameters to simulate real usage
#         params = {
#             "skip": random.randint(0, 100),
#             "limit": random.choice([10, 20, 50, 100])
#         }
        
#         # Randomly add optional filters
#         if random.random() < 0.3:  # 30% chance
#             params["difficulty"] = random.randint(1, 5)
        
#         with self.client.get(
#             "/api/v1/questions",
#             params=params,
#             catch_response=True,
#             name="GET /api/v1/questions"
#         ) as response:
#             if response.status_code == 200:
#                 try:
#                     data = response.json()
#                     if "questions" in data or "total" in data:
#                         response.success()
#                     else:
#                         response.failure("Invalid response format")
#                 except:
#                     response.failure("Failed to parse JSON")
#             elif response.status_code == 404:
#                 response.failure("Endpoint not found")
#             else:
#                 response.failure(f"Expected 200, got {response.status_code}")


# Optional: Add a separate user class for authenticated endpoints
class AuthenticatedFactionUser(HttpUser):
    """
    Simulates an authenticated user (if you want to test protected endpoints)
    Requires setting up authentication tokens
    """
    wait_time = between(2, 5)
    
    def on_start(self):
        """Authenticate user and set token"""
        import uuid
        # Generate unique device_id for each user
        device_id = str(uuid.uuid4())
        
        login_response = self.client.post(
             "/api/v1/auth/login",
             json={
                    "phone_number": "+918109285049",  # Include country code
                    "password": "stringst",
                    "device_info": {
                        "device_id": device_id,
                        "device_type": "mobile",
                        "device_model": "Test Device",
                        "os_version": "Android 13"
                    }
             },
             catch_response=True,
             name="POST /api/v1/auth/login"
        )
        
        if login_response.status_code == 200:
            try:
                response_data = login_response.json()
                access_token = response_data.get("access_token")
                if access_token:
                    self.client.headers.update({"Authorization": f"Bearer {access_token}"})
                    login_response.success()
                else:
                    login_response.failure("No access_token in response")
            except Exception as e:
                login_response.failure(f"Failed to parse login response: {str(e)}")
        else:
            login_response.failure(f"Login failed with status {login_response.status_code}: {login_response.text}")
    
    @task
    def get_user_profile(self):
        """Test authenticated endpoint - Get user profile"""
        with self.client.get(
            "/api/v1/users/me",
            catch_response=True,
            name="GET /api/v1/users/me"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "id" in data or "phone_number" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except:
                    response.failure("Failed to parse JSON")
            elif response.status_code == 401:
                response.failure("Unauthorized - token missing or invalid")
            elif response.status_code == 403:
                response.failure("Forbidden - insufficient permissions")
            else:
                response.failure(f"Expected 200, got {response.status_code}: {response.text[:100]}")

