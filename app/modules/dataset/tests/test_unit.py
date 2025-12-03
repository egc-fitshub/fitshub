from datetime import datetime, timedelta, timezone

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset import repositories, services
from app.modules.dataset.models import DataSet, DSDownloadRecord, DSMetaData, PublicationType
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extiende el test_client para añadir un usuario y un dataset
    con un DOI específico para probar los badges.
    """
    with test_client.application.app_context():
        user_test = User(email="user_badge@example.com", password="test1234")
        db.session.add(user_test)
        db.session.commit()

        meta_test = DSMetaData(
            title="Mi Dataset de Prueba",
            dataset_doi="http://localhost:5000/doi/10.1234/test-doi",
            description="Una descripción de prueba, requerida por el modelo.",
            publication_type="other",
        )
        db.session.add(meta_test)
        db.session.commit()

        dataset_test = DataSet(user_id=user_test.id, ds_meta_data_id=meta_test.id)
        db.session.add(dataset_test)
        db.session.commit()

    yield test_client


def test_generate_json_badge_data(test_client):
    response = test_client.get("/dataset/1/badge.json")

    assert response.status_code == 200, "El endpoint /badge.json falló."
    assert response.mimetype == "application/json", "El endpoint no devolvió JSON."
    data = response.json

    assert data["schemaVersion"] == 1
    assert data["color"] == "blue"

    assert data["label"] == "10.1234/test-doi"

    assert data["message"] == "0"


@pytest.fixture(scope="module")
def sample_metadata(test_client):
    """Crea metadata de prueba"""
    with test_client.application.app_context():
        ds_test_meta = DSMetaData(
            title="test DSMetaData",
            description="test description",
            publication_type=PublicationType.REPORT,
        )
        db.session.add(ds_test_meta)
        db.session.commit()
        yield ds_test_meta


def test_download_counter_exists(test_client, sample_metadata):
    ds_test = services.DataSetService().create(
        user_id=1,
        ds_meta_data_id=sample_metadata.id,
    )

    obtained_ds = repositories.DataSetRepository().get_by_id(ds_test.id)
    assert hasattr(obtained_ds, "download_counter")
    assert obtained_ds.download_counter == 0


def test_download_counter_increments(test_client, sample_metadata):
    ds_test = services.DataSetService().create(user_id=1, ds_meta_data_id=sample_metadata.id, download_counter=5)

    services.DataSetService().update_download_counter(ds_test.id)
    obtained_ds = repositories.DataSetRepository().get_by_id(ds_test.id)
    assert hasattr(obtained_ds, "download_counter")
    assert obtained_ds.download_counter == 6


@pytest.fixture(scope="module")
def test_client_forTrending(test_client):
    with test_client.application.app_context():
        user1 = User(email="trending_user1@example.com", password="test1234")
        user2 = User(email="trending_user2@example.com", password="test1234")
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()

        profile1 = UserProfile(user_id=user1.id, name="Test", surname="User1")
        profile2 = UserProfile(user_id=user2.id, name="Test", surname="User2")
        db.session.add(profile1)
        db.session.add(profile2)
        db.session.commit()

        metadata1 = DSMetaData(
            title="Popular Dataset",
            description="This dataset is very popular",
            publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
            dataset_doi="10.1234/dataset1",
            tags="trending, popular",
        )
        metadata2 = DSMetaData(
            title="Moderately Popular Dataset",
            description="This dataset is moderately popular",
            publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
            dataset_doi="10.1234/dataset2",
            tags="trending",
        )
        metadata3 = DSMetaData(
            title="Old Downloads Dataset",
            description="This dataset has old downloads",
            publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
            dataset_doi="10.1234/dataset3",
            tags="old",
        )

        db.session.add_all([metadata1, metadata2, metadata3])
        db.session.commit()

        dataset1 = DataSet(user_id=user1.id, ds_meta_data_id=metadata1.id)
        dataset2 = DataSet(user_id=user1.id, ds_meta_data_id=metadata2.id)
        dataset3 = DataSet(user_id=user1.id, ds_meta_data_id=metadata3.id)

        db.session.add_all([dataset1, dataset2, dataset3])
        db.session.commit()

        now = datetime.now(timezone.utc)

        for i in range(5):
            download = DSDownloadRecord(
                dataset_id=dataset1.id,
                user_id=user1.id if i % 2 == 0 else user2.id,
                download_date=now - timedelta(days=i),
                download_cookie=f"cookie_{i}",
            )
            db.session.add(download)

        for i in range(3):
            download = DSDownloadRecord(
                dataset_id=dataset2.id,
                user_id=user2.id,
                download_date=now - timedelta(days=i),
                download_cookie=f"cookie_ds2_{i}",
            )
            db.session.add(download)

        for i in range(2):
            download = DSDownloadRecord(
                dataset_id=dataset3.id,
                user_id=user1.id,
                download_date=now - timedelta(days=i + 1),
                download_cookie=f"cookie_ds3_recent_{i}",
            )
            db.session.add(download)

        for i in range(20):
            download = DSDownloadRecord(
                dataset_id=dataset3.id,
                user_id=user1.id,
                download_date=now - timedelta(days=8 + i),
                download_cookie=f"cookie_ds3_old_{i}",
            )
            db.session.add(download)

        db.session.commit()

    yield test_client


def test_trending_datasets_order(test_client_forTrending):
    with test_client_forTrending.application.app_context():
        trending = services.DataSetService().get_trending_datasets(limit=10, period_days=7)

        download_counts = [count for _, count in trending]

        assert download_counts == sorted(download_counts, reverse=True), (
            "Trending datasets should be ordered by download count (highest first)"
        )


def test_trending_datasets_limit_parameter(test_client):
    with test_client.application.app_context():
        service = services.DataSetService()

        trending = service.get_trending_datasets(limit=2, period_days=7)

        assert len(trending) == 2, "Should return exactly 2 results when limit=2"

        trending = service.get_trending_datasets(limit=1, period_days=7)
        assert len(trending) == 1, "Should return exactly 1 result when limit=1"

        dataset, count = trending[0]
        assert dataset.ds_meta_data.title == "Popular Dataset", "Top result should be the most downloaded dataset"
        assert count == 5, "Top result should have 5 downloads"

        trending_7_days = service.get_trending_datasets(limit=10, period_days=7)
        trending_map_7 = {dataset.ds_meta_data.title: count for dataset, count in trending_7_days}

        trending_30_days = service.get_trending_datasets(limit=10, period_days=30)
        trending_map_30 = {dataset.ds_meta_data.title: count for dataset, count in trending_30_days}

        assert trending_map_7.get("Old Downloads Dataset") == 2, "Should only count recent downloads in 7-day period"
        assert trending_map_30.get("Old Downloads Dataset") == 22, "Should count all downloads in 30-day period"
