import logging

from app.modules.community.models import CommunityDataSetStatus

logger = logging.getLogger(__name__)


def init_search_index():
    try:
        from app.modules.elasticsearch.services import ElasticsearchService

        search = ElasticsearchService()

        search.create_index_if_not_exists()
    except Exception as e:
        print(f"[ERROR init_search_index] {e}")
        raise


def _accepted_community_ids(dataset):
    if not dataset:
        return []
    associations = getattr(dataset, "community_associations", None)
    if associations is None:
        return []
    if hasattr(associations, "all"):
        associations = associations.all()
    return [
        assoc.community_id
        for assoc in associations
        if getattr(assoc, "status", None) == CommunityDataSetStatus.ACCEPTED
    ]


def index_dataset(dataset):
    from app.modules.elasticsearch.services import ElasticsearchService

    search = ElasticsearchService()

    if not dataset.ds_meta_data.dataset_doi:
        print(f"[SKIP] Dataset {dataset.id} has no dataset_doi. Skipping indexing.")
        return

    doc = {
        "type": "dataset",
        "id": dataset.id,
        "community_ids": _accepted_community_ids(dataset),
        "title": dataset.ds_meta_data.title,
        "description": dataset.ds_meta_data.description,
        "publication_doi": dataset.ds_meta_data.publication_doi,
        "dataset_doi": dataset.ds_meta_data.dataset_doi,
        "url": dataset.get_fitshub_doi(),
        "authors": [
            {
                "name": a.name,
                "affiliation": getattr(a, "affiliation", None),
                "orcid": getattr(a, "orcid", None),
            }
            for a in dataset.ds_meta_data.authors
        ],
        "tags": ([t.strip() for t in dataset.ds_meta_data.tags.split(",")] if dataset.ds_meta_data.tags else []),
        "publication_type": (
            dataset.ds_meta_data.publication_type.value if dataset.ds_meta_data.publication_type else None
        ),
        "publication_type_label": dataset.get_cleaned_publication_type(),
        "content": (
            f"{dataset.ds_meta_data.title} "
            f"{dataset.ds_meta_data.description} "
            f"{dataset.ds_meta_data.publication_doi} "
            f"{' '.join(a.name for a in dataset.ds_meta_data.authors)}"
        ),
        "created_at": dataset.created_at.isoformat(),
        "total_size_in_bytes": dataset.get_file_total_size(),
        "files_count": dataset.get_files_count(),
    }

    search.index_document(doc_id=f"dataset-{dataset.id}", data=doc)

    logger.info(f"[SEARCH] Dataset {dataset.id} indexed with DOI: {dataset.ds_meta_data.dataset_doi}")


def index_hubfile(hubfile):
    from app.modules.elasticsearch.services import ElasticsearchService

    search = ElasticsearchService()

    dataset = hubfile.fits_model.data_set if hubfile.fits_model else None

    if not dataset or not dataset.ds_meta_data.dataset_doi:
        print(f"[SKIP] Hubfile {hubfile.id} skipped (no dataset or dataset has no DOI).")
        return

    doc = {
        "type": "hubfile",
        "id": hubfile.id,
        "filename": hubfile.name,
        "content": hubfile.name,
        "fits_model_id": hubfile.fits_model_id,
        "dataset_id": dataset.id,
        "community_ids": _accepted_community_ids(dataset),
        "dataset_doi": dataset.get_fitshub_doi(),
        "dataset_title": dataset.ds_meta_data.title,
        "checksum": hubfile.checksum,
        "size_in_bytes": hubfile.size,
        "size_in_human_format": hubfile.get_formatted_size(),
    }

    search.index_document(doc_id=f"hubfile-{hubfile.id}", data=doc)

    logger.info(f"[SEARCH] Hubfile {hubfile.id} indexed in dataset: {dataset.id}")


def reindex_all():
    from app.modules.dataset.models import DataSet
    from app.modules.hubfile.models import Hubfile

    datasets = DataSet.query.all()
    hubfiles = Hubfile.query.all()

    print(f"[REINDEX] Reindexing {len(datasets)} datasets and {len(hubfiles)} hubfiles...")

    for dataset in datasets:
        index_dataset(dataset)

    for hubfile in hubfiles:
        index_hubfile(hubfile)

    print("[REINDEX] Reindexing completed.")
