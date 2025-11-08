import logging
import random
import string

from flask import Response, jsonify

from app.modules.fakenodo.repositories import FakenodoRepository
from core.services.BaseService import BaseService

logger = logging.getLogger(__name__)


class FakenodoService(BaseService):
    def __init__(self):
        super().__init__(FakenodoRepository())

    def test_full_connection(self) -> Response:
        """
        Simulate testing connection with FakeNodo.
        """
        logger.info("Simulating connection to FakeNodo...")
        return jsonify(
            {"success": True, "message": "FakeNodo connection test successful."}
        )

    def create_new_deposition(self, title:str, description:str) -> dict:
        """ Simulation of the creation of a new deposition in FakeNODO """
        fake_doi = f"10.5078/{random.choices(string.ascii_lowercase + string.digits, k=8)}"

        deposition = {
            "id": random.randint(1000, 9999),
            "title": title,
            "description": description,
            "doi": fake_doi
        }
        logger.info(f"Created new fake deposition: {deposition}")
        return deposition

    def edit_metadata(self, deposition_id: int, title: str = None, description: str = None) -> dict:
        """ Simulation of editing metadata of a deposition in FakeNODO """
        updated_metadata = {
            "id": deposition_id,
            "title": title,
            "description": description
        }
        logger.info(f"Edited metadata for deposition {deposition_id}: {updated_metadata}")
        return updated_metadata

    def upload_file(self, deposition_id: int, file_name: str) -> dict:
        """ Simulation of uploading a file to a deposition in FakeNODO """
        logger.info(f"Simulating file upload to deposition {deposition_id}...")
        fake_doi = f"10.5078/{random.choices(string.ascii_lowercase + string.digits, k=8)}"

        return {
            "success": True,
            "message": f"File '{file_name}' simulated as uploaded to deposition {deposition_id}",
            "doi": fake_doi,
        }

    def publish_deposition(self, deposition_id: int) -> dict:
        """ Simulation of publishing a deposition in FakeNODO """
        logger.info(f"Simulating publishing deposition {deposition_id}...")
        fake_doi = f"10.5078/{random.choices(string.ascii_lowercase + string.digits, k=8)}"

        return {
            "success": True,
            "message": f"Deposition {deposition_id} simulated as published.",
            "doi": fake_doi,
        }
