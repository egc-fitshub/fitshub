import logging
import random

from flask import Response, jsonify

from core.services.BaseService import BaseService

logger = logging.getLogger(__name__)


class FakenodoService(BaseService):
    def __init__(self):
        super().__init__(None)

    def test_full_connection(self) -> Response:
        """
        Simulate testing connection with FakeNodo.
        """
        logger.info("Simulating connection to FakeNodo...")
        return jsonify({"success": True, "message": "FakeNodo connection test successful."})

    def create_new_deposition(self, dataset) -> dict:
        """
        Simulates the creation of a new deposition, returning a structure
        similar to Zenodo's API response.
        """
        logger.info(f"Simulating new deposition for dataset: {dataset.ds_meta_data.title}")
        deposition_id = random.randint(100000, 999999)
        concept_rec_id = random.randint(100000, 999999)

        return {
            "conceptrecid": concept_rec_id,
            "id": deposition_id,
            "metadata": {"prereserve_doi": {"doi": f"10.5072/fakenodo.{concept_rec_id}"}},
            "links": {"bucket": f"http://localhost/api/files/{deposition_id}"},
        }

    def upload_file(self, dataset, deposition_id: int, fits_model) -> dict:
        """Simulates uploading a file to a deposition."""
        logger.info(f"Simulating upload of file '{fits_model}' to deposition '{deposition_id}'")

        return {"status": "completed"}

    def publish_deposition(self, deposition_id: int) -> dict:
        """Simulates publishing a deposition."""
        logger.info(f"Simulating publishing of deposition '{deposition_id}'")

        return {"state": "done", "submitted": True}

    def get_doi(self, deposition_id: int) -> str:
        """Simulates retrieving the final DOI for a deposition."""

        doi = f"10.5281/fakenodo.{random.randint(1000000, 9999999)}"
        logger.info(f"Simulating DOI retrieval for deposition '{deposition_id}': {doi}")
        return doi
