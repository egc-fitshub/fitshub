import random

from locust import HttpUser, TaskSet, events, task

from app import create_app
from app.modules.dataset import services
from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token

dataset_ids = []


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global dataset_ids
    app = create_app()
    with app.app_context():
        datasets = services.DataSetService().latest_synchronized()
        dataset_ids = [ds.id for ds in datasets]
        print(f"Loaded {len(dataset_ids)} dataset IDs from database")


class DatasetBehavior(TaskSet):
    def on_start(self):
        self.dataset()

    @task
    def dataset(self):
        response = self.client.get("/dataset/upload")
        get_csrf_token(response)

    @task
    def ensure_generation_json_badge_data(self):
        if not dataset_ids:
            print("No dataset IDs available")
            return

        url_name = "/dataset/[id]/badge.json"
        dataset_id = random.choice(dataset_ids)

        with self.client.get(f"/dataset/{dataset_id}/badge.json", name=url_name, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Failed for ID {dataset_id}: {response.status_code}")
            else:
                response.success()


class DatasetUser(HttpUser):
    tasks = [DatasetBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
