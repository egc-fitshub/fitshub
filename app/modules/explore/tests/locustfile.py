from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing


class ExploreBehavior(TaskSet):
    def on_start(self):
        self.index()

    @task
    def index(self):
        response = self.client.get("/explore")

        if response.status_code != 200:
            print(f"Explore index failed: {response.status_code}")


class APISearchBehavior(TaskSet):
    @task
    def search_basic_query(self):
        response = self.client.get(
            "/api/v1/search",
            params={"q": "machine learning", "size": 10},
            name="/api/v1/search [basic]",
        )
        if response.status_code != 200:
            print(f"API search basic query failed: {response.status_code}")

    @task
    def search_with_filters(self):
        response = self.client.get(
            "/api/v1/search",
            params={
                "q": "software engineering",
                "publication_type": "article",
                "sorting": "oldest",
                "size": 20,
            },
            name="/api/v1/search [filtered]",
        )
        if response.status_code != 200:
            print(f"API search with filters failed: {response.status_code}")

    @task
    def search_with_tags(self):
        response = self.client.get(
            "/api/v1/search",
            params={
                "q": "data analysis",
                "tags": "python,statistics,visualization",
                "size": 15,
            },
            name="/api/v1/search [tags]",
        )
        if response.status_code != 200:
            print(f"API search with tags failed: {response.status_code}")

    @task
    def search_with_date_range(self):
        response = self.client.get(
            "/api/v1/search",
            params={
                "q": "artificial intelligence",
                "date_from": "2023-01-01",
                "date_to": "2024-12-31",
                "size": 10,
            },
            name="/api/v1/search [date range]",
        )
        if response.status_code != 200:
            print(f"API search with date range failed: {response.status_code}")

    @task
    def search_with_community(self):
        response = self.client.get(
            "/api/v1/search",
            params={"q": "neural networks", "community": "1", "size": 10},
            name="/api/v1/search [community]",
        )
        if response.status_code != 200:
            print(f"API search with community failed: {response.status_code}")

    @task
    def search_combined_filters(self):
        response = self.client.get(
            "/api/v1/search",
            params={
                "q": "computer vision",
                "publication_type": "conferencepaper",
                "sorting": "newest",
                "tags": "image,recognition",
                "date_from": "2024-01-01",
                "page": 1,
                "size": 20,
            },
            name="/api/v1/search [combined]",
        )
        if response.status_code != 200:
            print(f"API search with combined filters failed: {response.status_code}")

    @task
    def search_empty_query(self):
        response = self.client.get(
            "/api/v1/search",
            params={"size": 10},
            name="/api/v1/search [empty]",
        )
        if response.status_code != 200:
            print(f"API search empty query failed: {response.status_code}")


class ExploreUser(HttpUser):
    tasks = [ExploreBehavior, APISearchBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
