import os
import random
from io import BytesIO

from locust import HttpUser, TaskSet, events, task

from app import create_app
from app.modules.dataset import services
from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token

dataset_ids = []
TEST_FITS_GITHUB_REPO_USER = "egc-fitshub"
TEST_FITS_GITHUB_REPO_NAME_WITH_FILES = "fits_test"
NOT_EXISTING_GITHUB_REPO_NAME = "this_does_not_exist"
TEST_FITS_GITHUB_REPO_NAME_WITHOUT_FILES = "fitshub"


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
        csrf_token = get_csrf_token(response)

        login_data = {
            "email": "user@example.com",
            "password": "1234",
            "csrf_token": csrf_token,
        }
        self.client.post("/login", data=login_data)

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
                print(response)
            else:
                response.success()

    @task
    def fetch_github_repo(self):
        with self.client.post(
            f"/dataset/github/fetch?user={TEST_FITS_GITHUB_REPO_USER}&repo={TEST_FITS_GITHUB_REPO_NAME_WITH_FILES}",
            catch_response=True,
        ) as response:
            json = response.json()
            if json["status"] != 200 and json["status"] != 403 and json["status"] != 429:
                response.failure(f"Failed: {json['details']}")
            else:
                response.success()

    @task
    def fetch_non_existing_github_repo(self):
        with self.client.post(
            f"/dataset/github/fetch?user={TEST_FITS_GITHUB_REPO_USER}&repo={NOT_EXISTING_GITHUB_REPO_NAME}",
            catch_response=True,
        ) as response:
            json = response.json()
            if json["status"] != 404 and json["status"] != 403 and json["status"] != 429:
                response.failure(f"Failed: {json['details']}")
            else:
                response.success()

    @task
    def fetch_no_github_repo(self):
        with self.client.post(
            "/dataset/github/fetch",
            catch_response=True,
        ) as response:
            json = response.json()
            if json["status"] != 400 and json["status"] != 403 and json["status"] != 429:
                response.failure(f"Failed: {json['details']}")
            else:
                response.success()

    @task
    def upload_zip(self):
        with open(os.path.join("app/modules/dataset/zip_examples", "one_fits.zip"), mode="rb") as f:
            with self.client.post(
                "/dataset/file/upload/zip",
                catch_response=True,
                files={"file": ("one_fits.zip", BytesIO(f.read()))},
                allow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed: {response.text}")
                else:
                    response.success()

    @task
    def upload_non_zip_file(self):
        with open(os.path.join("app/modules/dataset/fits_examples", "file1.fits"), mode="rb") as f:
            with self.client.post(
                "/dataset/file/upload/zip",
                catch_response=True,
                files={"file": ("file1.fits", BytesIO(f.read()))},
                allow_redirects=False,
            ) as response:
                if response.status_code != 400:
                    response.failure(f"Failed: {response.text}")
                else:
                    response.success()

    @task
    def upload_no_zip(self):
        with self.client.post("/dataset/file/upload/zip", catch_response=True, allow_redirects=False) as response:
            if response.status_code != 400:
                response.failure(f"Failed: {response.text}")
            else:
                response.success()


class DatasetUser(HttpUser):
    tasks = [DatasetBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
