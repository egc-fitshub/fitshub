from app.modules.dataset.models import DataSet
from core.resources.generic_resource import create_resource
from core.serialisers.serializer import Serializer

file_fields = {"file_id": "id", "file_name": "name", "size": "get_formatted_size"}
file_serializer = Serializer(file_fields)

dataset_fields = {
    "dataset_id": "id",
    "download_counter": "get_download_counter",
    "created": "created_at",
    "name": "name",
    "doi": "get_uvlhub_doi",
    "files": "files",
}

dataset_stats_fields = {
    "dataset_id": "id",
    "download_counter": "get_download_counter",
    "number_of_files": "get_files_count",
    "publication_type": "get_cleaned_publication_type",
    "total_size_in_bytes": "get_file_total_size",
    "total_size_for_human": "get_file_total_size_for_human",
}

dataset_serializer = Serializer(dataset_fields, related_serializers={"files": file_serializer})
dataset_stats_serializer = Serializer(dataset_stats_fields)

DataSetResource = create_resource(DataSet, dataset_serializer)
DataSetStatsResource = create_resource(DataSet, dataset_stats_serializer)


def init_blueprint_api(api):
    """Function to register resources with the provided Flask-RESTful Api instance."""
    api.add_resource(DataSetResource, "/api/v1/datasets/", endpoint="datasets")
    api.add_resource(DataSetResource, "/api/v1/datasets/<int:id>", endpoint="dataset")
    api.add_resource(DataSetStatsResource, "/api/v1/datasets/<int:id>/stats", endpoint="dataset_stats")
