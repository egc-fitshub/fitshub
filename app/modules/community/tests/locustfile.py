from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing


class AuthBehavior(TaskSet):
    @task
    def ensure_logged_out(self):
        self.client.get("/logout")

    @task
    def login(self):
        credentials = [
            ("user1@example.com", "1234"),
        ]

        for email, pwd in credentials:
            data = {"email": email, "password": pwd}

            post = self.client.post("/login", data=data, allow_redirects=True)
            if post.status_code == 200 and ("Invalid credentials" not in post.text):
                return


class CommunityBehavior(TaskSet):
    def on_start(self):
        self.community_id = 1
        self.dataset_id = 1

    @task
    def index(self):
        resp = self.client.get("/community")
        if resp.status_code != 200:
            print(f"Community index failed: {resp.status_code}")

    @task
    def my_communities(self):
        resp = self.client.get("/my_communities")
        if resp.status_code not in (200, 302):
            print(f"my_communities failed: {resp.status_code}")

    @task
    def view_community(self):
        resp = self.client.get(f"/community/{self.community_id}")
        if resp.status_code not in (200, 302):
            print(f"get_community failed: {resp.status_code}")

    @task
    def create_community(self):
        resp = self.client.get("/community/create")
        if resp.status_code != 200:
            return
        data = {"name": "Locust Test Community", "description": "Created by locust test"}

        post = self.client.post("/community/create", data=data, allow_redirects=True)
        if post.status_code not in (200, 302):
            print(f"create_community failed: {post.status_code}")

    @task
    def update_community(self):
        resp = self.client.get(f"/community/{self.community_id}/update")
        if resp.status_code != 200:
            return
        data = {"name": "Updated by Locust", "description": "Updated by locust test"}

        post = self.client.post(f"/community/{self.community_id}/update", data=data, allow_redirects=True)
        if post.status_code not in (200, 302):
            print(f"update_community failed: {post.status_code}")

    @task
    def view_curators(self):
        resp = self.client.get(f"/community/{self.community_id}/curators")
        if resp.status_code not in (200, 302):
            print(f"view_curators failed: {resp.status_code}")

    @task
    def add_curator(self):
        resp = self.client.get(f"/community/{self.community_id}/curators")
        if resp.status_code != 200:
            return
        data = {}
        data["curator_ids"] = ["2"]

        post = self.client.post(f"/community/{self.community_id}/add_curators", data=data, allow_redirects=True)
        if post.status_code not in (200, 302):
            print(f"add_curator failed: {post.status_code}")

    @task
    def review_pending(self):
        resp = self.client.get(f"/community/{self.community_id}/review")
        if resp.status_code not in (200, 302):
            print(f"review_pending failed: {resp.status_code}")

    @task
    def approve_reject(self):
        approve = self.client.post(
            f"/community/{self.community_id}/approve/{self.dataset_id}", data={}, allow_redirects=True
        )
        if approve.status_code not in (200, 302):
            print(f"approve failed: {approve.status_code}")

        reject = self.client.post(
            f"/community/{self.community_id}/reject/{self.dataset_id}", data={}, allow_redirects=True
        )
        if reject.status_code not in (200, 302):
            print(f"reject failed: {reject.status_code}")


class CommunityUser(HttpUser):
    tasks = [AuthBehavior, CommunityBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
