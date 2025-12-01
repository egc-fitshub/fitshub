import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask_login import current_user
from sqlalchemy import desc, func

from app.modules.dataset.models import Author, DataSet, DOIMapping, DSDownloadRecord, DSMetaData, DSViewRecord
from core.repositories.BaseRepository import BaseRepository

logger = logging.getLogger(__name__)


class AuthorRepository(BaseRepository):
    def __init__(self):
        super().__init__(Author)


class DSDownloadRecordRepository(BaseRepository):
    def __init__(self):
        super().__init__(DSDownloadRecord)

    def total_dataset_downloads(self) -> int:
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0


class DSMetaDataRepository(BaseRepository):
    def __init__(self):
        super().__init__(DSMetaData)

    def filter_by_doi(self, doi: str) -> Optional[DSMetaData]:
        return self.model.query.filter_by(dataset_doi=doi).first()


class DSViewRecordRepository(BaseRepository):
    def __init__(self):
        super().__init__(DSViewRecord)

    def total_dataset_views(self) -> int:
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0

    def the_record_exists(self, dataset: DataSet, user_cookie: str):
        return self.model.query.filter_by(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset.id,
            view_cookie=user_cookie,
        ).first()

    def create_new_record(self, dataset: DataSet, user_cookie: str) -> DSViewRecord:
        return self.create(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset.id,
            view_date=datetime.now(timezone.utc),
            view_cookie=user_cookie,
        )


class DataSetRepository(BaseRepository):
    def __init__(self):
        super().__init__(DataSet)

    def get_synchronized(self, current_user_id: int) -> DataSet:
        return (
            self.model.query.join(DSMetaData)
            .filter(DataSet.user_id == current_user_id, DSMetaData.dataset_doi.isnot(None))
            .order_by(self.model.created_at.desc())
            .all()
        )

    def get_unsynchronized(self, current_user_id: int) -> DataSet:
        return (
            self.model.query.join(DSMetaData)
            .filter(DataSet.user_id == current_user_id, DSMetaData.dataset_doi.is_(None))
            .order_by(self.model.created_at.desc())
            .all()
        )

    def get_unsynchronized_dataset(self, current_user_id: int, dataset_id: int) -> DataSet:
        return (
            self.model.query.join(DSMetaData)
            .filter(DataSet.user_id == current_user_id, DataSet.id == dataset_id, DSMetaData.dataset_doi.is_(None))
            .first()
        )

    def count_synchronized_datasets(self):
        return self.model.query.join(DSMetaData).filter(DSMetaData.dataset_doi.isnot(None)).count()

    def count_unsynchronized_datasets(self):
        return self.model.query.join(DSMetaData).filter(DSMetaData.dataset_doi.is_(None)).count()

    def latest_synchronized(self):
        return (
            self.model.query.join(DSMetaData)
            .filter(DSMetaData.dataset_doi.isnot(None))
            .order_by(desc(self.model.id))
            .limit(5)
            .all()
        )

    def trending_datasets(self, period_days=7, limit=10):
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)

        return (
            self.session.query(DataSet, func.count(DSDownloadRecord.id).label("download_count"))
            .join(DSDownloadRecord, DataSet.id == DSDownloadRecord.dataset_id)
            .join(DSMetaData, DataSet.ds_meta_data_id == DSMetaData.id)
            .filter(DSDownloadRecord.download_date >= cutoff_date)
            .filter(DSMetaData.dataset_doi.isnot(None))
            .group_by(DataSet.id)
            .order_by(func.count(DSDownloadRecord.id).desc())
            .limit(limit)
            .all()
        )

    def recommended_datasets(self, reference_dataset_id, limit=10):
        ref_dataset = self.get_by_id(reference_dataset_id)
        if not ref_dataset or not ref_dataset.ds_meta_data:
            return []

        ref_tags = set()
        if ref_dataset.ds_meta_data.tags:
            ref_tags = set(tag.strip().lower() for tag in ref_dataset.ds_meta_data.tags.split(",") if tag.strip())

        ref_authors = set(author.id for author in ref_dataset.ds_meta_data.authors)

        all_candidates = (
            self.session.query(DataSet)
            .join(DSMetaData, DataSet.ds_meta_data_id == DSMetaData.id)
            .filter(DataSet.id != reference_dataset_id)
            .filter(DSMetaData.dataset_doi.isnot(None))
            .all()
        )

        classified_datasets = []
        for dataset in all_candidates:
            score = 0.0

            if dataset.ds_meta_data and dataset.ds_meta_data.authors:
                for author in dataset.ds_meta_data.authors:
                    if author.id in ref_authors:
                        score += 1.5

            if dataset.ds_meta_data and dataset.ds_meta_data.tags:
                candidate_tags = set(tag.strip().lower() for tag in dataset.ds_meta_data.tags.split(",") if tag.strip())
                shared_tags_count = len(ref_tags & candidate_tags)
                score += shared_tags_count * 2.0

            if score > 0:
                download_count = (
                    self.session.query(func.count(DSDownloadRecord.id))
                    .filter(DSDownloadRecord.dataset_id == dataset.id)
                    .scalar()
                    or 0
                )
                classified_datasets.append((dataset, score, download_count))

        classified_datasets.sort(key=lambda x: (x[1], x[2]), reverse=True)

        return [ds for ds, _, _ in classified_datasets[:limit]]


class DOIMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__(DOIMapping)

    def get_new_doi(self, old_doi: str) -> str:
        return self.model.query.filter_by(dataset_doi_old=old_doi).first()
