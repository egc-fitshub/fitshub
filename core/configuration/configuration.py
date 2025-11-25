import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.getenv("WORKING_DIR", os.getcwd())


def uploads_folder_name():
    return os.getenv("UPLOADS_DIR", "uploads")


def photo_upload_folder_name():
    return os.path.join(BASE_DIR, "app", "static", "img", "photos")


def get_app_version():
    version_file_path = os.path.join(os.getenv("WORKING_DIR", ""), ".version")
    try:
        with open(version_file_path, "r") as file:
            return file.readline().strip()
    except FileNotFoundError:
        return "unknown"


def is_develop():
    return os.getenv("FLASK_ENV") == "development"


def is_production():
    return os.getenv("FLASK_ENV") == "production"
