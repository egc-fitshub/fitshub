from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token
import random


class DatasetBehavior(TaskSet):
    def on_start(self):
        self.dataset()

    @task
    def dataset(self):
        response = self.client.get("/dataset/upload")
        get_csrf_token(response)
    @task

    def ensure_generation_json_badge_data(self):
        dataset_id = random.randint(1, 3)
        url_name = "/dataset/[id]/badge.json" 
        with self.client.get(f"/dataset/{dataset_id}/badge.json", name=url_name) as response:
            if response.status_code != 200:
                response.failure(f"Failed for ID {dataset_id}: {response.status_code}")


class DatasetUser(HttpUser):
    tasks = [DatasetBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
