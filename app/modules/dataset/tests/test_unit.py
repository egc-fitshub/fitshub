import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from flask_login import current_user

from app import db
from app.modules.auth.models import User
from app.modules.auth.services import AuthenticationService
from app.modules.community.models import Community, CommunityDataSet, CommunityDataSetStatus
from app.modules.conftest import login, logout
from app.modules.dataset import repositories, services
from app.modules.dataset.models import Author, DataSet, DSDownloadRecord, DSMetaData, PublicationType
from app.modules.profile.models import UserProfile

TEST_FITS_GITHUB_REPO_USER = "egc-fitshub"
TEST_FITS_GITHUB_REPO_NAME_WITH_FILES = "fits_test"
NOT_EXISTING_GITHUB_REPO_NAME = "this_does_not_exist"
TEST_FITS_GITHUB_REPO_NAME_WITHOUT_FILES = "fitshub"


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extiende el test_client para añadir un usuario y un dataset
    con un DOI específico para probar los badges.
    """
    with test_client.application.app_context():
        service = AuthenticationService()
        user_test = service.create_with_profile(
            name="User", surname="Badge", email="user_badge@example.com", password="test1234"
        )
        user_test.profile.enabled_two_factor = False
        db.session.add(user_test)
        db.session.commit()

        meta_test = DSMetaData(
            title="Mi Dataset de Prueba",
            dataset_doi="http://localhost:5000/doi/10.1234/test-doi",
            description="Una descripción de prueba, requerida por el modelo.",
            publication_type="other",
            tags="test",
        )
        db.session.add(meta_test)
        db.session.commit()

        dataset_test = DataSet(
            user_id=user_test.id,
            ds_meta_data_id=meta_test.id,
        )
        db.session.add(dataset_test)
        db.session.commit()

    yield test_client


def test_github_upload_with_fits(test_client):
    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    response = test_client.post(
        f"/dataset/github/fetch?user={TEST_FITS_GITHUB_REPO_USER}&repo={TEST_FITS_GITHUB_REPO_NAME_WITH_FILES}"
    )

    if response.status_code == 429 or response.status_code == 403:
        assert response.json["error"] == "GitHub is temporarily blocking too many requests. Please try again later."
        return

    assert response.status_code == 200

    json = response.json
    assert json["message"] == "Github files uploaded successfully"

    file_path = current_user.temp_folder()

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_github_upload_without_fits(test_client):
    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    response = test_client.post(
        f"/dataset/github/fetch?user={TEST_FITS_GITHUB_REPO_USER}&repo={TEST_FITS_GITHUB_REPO_NAME_WITHOUT_FILES}"
    )

    if response.status_code == 429 or response.status_code == 403:
        assert response.json["error"] == "GitHub is temporarily blocking too many requests. Please try again later."
        return

    assert response.status_code == 200

    json = response.json
    assert len(json["filenames"]) == 0

    file_path = current_user.temp_folder()

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_github_upload_no_repo(test_client):
    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    response = test_client.post("/dataset/github/fetch")

    assert response.status_code == 400

    json = response.json
    assert json["error"] == "User or repo not specified"

    file_path = current_user.temp_folder()

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_github_upload_not_existing_repo(test_client):
    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    response = test_client.post(
        f"/dataset/github/fetch?user={TEST_FITS_GITHUB_REPO_USER}&repo={NOT_EXISTING_GITHUB_REPO_NAME}"
    )

    if response.status_code == 429 or response.status_code == 403:
        assert response.json["error"] == "GitHub is temporarily blocking too many requests. Please try again later."
        return

    assert response.status_code == 404

    json = response.json
    assert json["error"] == "The FITS file or the repository does not exist."

    file_path = current_user.temp_folder()

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_zip_upload_single_fits(test_client):
    filename = "one_fits.zip"
    fits_names = ["file1.fits"]

    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    with open(os.path.join("app/modules/dataset/zip_examples", filename), mode="rb") as f:
        data = dict(file=(BytesIO(f.read()), filename))

    response = test_client.post("/dataset/file/upload/zip", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    json = response.json
    assert json["message"] == "ZIP uploaded successfully"
    assert all([fits_name in json["filenames"] for fits_name in fits_names])

    # Remove temp folder
    file_path = current_user.temp_folder()

    for fits_name in fits_names:
        assert os.path.exists(os.path.join(file_path, fits_name))

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_zip_upload_multiple_fits(test_client):
    filename = "multiple_fits.zip"
    fits_names = ["file1.fits", "file2.fits"]

    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    with open(os.path.join("app/modules/dataset/zip_examples", filename), mode="rb") as f:
        data = dict(file=(BytesIO(f.read()), filename))

    response = test_client.post("/dataset/file/upload/zip", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    json = response.json
    assert json["message"] == "ZIP uploaded successfully"
    assert all([fits_name in json["filenames"] for fits_name in fits_names])

    # Remove temp folder
    file_path = current_user.temp_folder()

    for fits_name in fits_names:
        assert os.path.exists(os.path.join(file_path, fits_name))

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_zip_upload_no_fits(test_client):
    filename = "not_fits.zip"

    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    with open(os.path.join("app/modules/dataset/zip_examples", filename), mode="rb") as f:
        data = dict(file=(BytesIO(f.read()), filename))

    response = test_client.post("/dataset/file/upload/zip", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    json = response.json
    assert json["message"] == "ZIP uploaded successfully"
    assert len(json["filenames"]) == 0

    # Remove temp folder
    file_path = current_user.temp_folder()

    assert len(os.listdir(file_path)) == 1

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_zip_upload_fits_in_folder(test_client):
    filename = "fits_in_folder.zip"
    fits_names = ["file1.fits", "file2.fits"]

    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    with open(os.path.join("app/modules/dataset/zip_examples", filename), mode="rb") as f:
        data = dict(file=(BytesIO(f.read()), filename))

    response = test_client.post("/dataset/file/upload/zip", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    json = response.json
    assert json["message"] == "ZIP uploaded successfully"
    assert all([fits_name in json["filenames"] for fits_name in fits_names])

    # Remove temp folder
    file_path = current_user.temp_folder()

    for fits_name in fits_names:
        assert os.path.exists(os.path.join(file_path, fits_name))

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_zip_upload_fits_in_folder_repeated_name(test_client):
    filename = "fits_in_folder_repeated_name.zip"
    fits_names = ["file1.fits", "file2.fits", "file1 (1).fits"]

    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    with open(os.path.join("app/modules/dataset/zip_examples", filename), mode="rb") as f:
        data = dict(file=(BytesIO(f.read()), filename))

    response = test_client.post("/dataset/file/upload/zip", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    json = response.json
    assert json["message"] == "ZIP uploaded successfully"
    assert all([fits_name in json["filenames"] for fits_name in fits_names])

    # Remove temp folder
    file_path = current_user.temp_folder()

    for fits_name in fits_names:
        assert os.path.exists(os.path.join(file_path, fits_name))

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_zip_upload_multiple_files_repeated_name(test_client):
    filename_1 = "one_fits.zip"
    filename_2 = "multiple_fits.zip"

    fits_names_1 = ["file1.fits"]
    fits_names_2 = ["file1 (1).fits", "file2.fits"]

    fits_names = fits_names_1 + fits_names_2

    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    with open(os.path.join("app/modules/dataset/zip_examples", filename_1), mode="rb") as f:
        data = dict(file=(BytesIO(f.read()), filename_1))

    response = test_client.post("/dataset/file/upload/zip", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    json = response.json
    assert json["message"] == "ZIP uploaded successfully"
    assert all([fits_name in json["filenames"] for fits_name in fits_names_1])

    with open(os.path.join("app/modules/dataset/zip_examples", filename_2), mode="rb") as f:
        data = dict(file=(BytesIO(f.read()), filename_2))

    response = test_client.post("/dataset/file/upload/zip", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    json = response.json
    assert json["message"] == "ZIP uploaded successfully"
    assert all([fits_name in json["filenames"] for fits_name in fits_names_2])

    # Remove temp folder
    file_path = current_user.temp_folder()

    for fits_name in fits_names:
        assert os.path.exists(os.path.join(file_path, fits_name))

    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)

    logout(test_client)


def test_zip_upload_non_zip_file(test_client):
    filename = "file1.fits"

    login_response = login(test_client, "user_badge@example.com", "test1234")
    assert login_response.status_code == 200

    with open(os.path.join("app/modules/dataset/fits_examples", filename), mode="rb") as f:
        data = dict(file=(BytesIO(f.read()), filename))

    response = test_client.post("/dataset/file/upload/zip", data=data, content_type="multipart/form-data")
    assert response.status_code == 400

    json = response.json
    assert json["message"] == "No valid file"

    logout(test_client)


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
    assert obtained_ds.download_counter == 0


def test_download_counter_increments(test_client, sample_metadata):
    ds_test = services.DataSetService().create(user_id=1, ds_meta_data_id=sample_metadata.id)

    services.DataSetService().update_download_counter(ds_test.id)
    obtained_ds = repositories.DataSetRepository().get_by_id(ds_test.id)
    assert obtained_ds.download_counter == 1


def test_multiple_download_counter_increments(test_client, sample_metadata):
    ds_test = services.DataSetService().create(user_id=1, ds_meta_data_id=sample_metadata.id)

    for _ in range(0, 5):
        services.DataSetService().update_download_counter(ds_test.id)
    obtained_ds = repositories.DataSetRepository().get_by_id(ds_test.id)
    assert obtained_ds.download_counter == 5


def test_download_counter_not_negative(test_client, sample_metadata):
    with pytest.raises(ValueError):
        services.DataSetService().create(user_id=1, ds_meta_data_id=sample_metadata.id, download_counter=-1)


def test_download_counter_set_to_zero(test_client, sample_metadata):
    with pytest.raises(ValueError):
        services.DataSetService().create(user_id=1, ds_meta_data_id=sample_metadata.id, download_counter=8)


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


@pytest.fixture(scope="module")
def test_client_for_communities(test_client):
    """
    Añadir comunidades a test client
    """
    with test_client.application.app_context():
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=unique_email, password="password")
        db.session.add(user)
        db.session.flush()

        profile = UserProfile(
            user_id=user.id,
            name="Test",
            surname="User",
            affiliation="Test University",
            orcid="0000-0000-0000-0001",
        )
        db.session.add(profile)

        community1 = Community(name="Satélites", description="Sistemas de Satélites")
        community2 = Community(name="Planetas Enanos", description="Variedad de Planetas Enanos")
        community3 = Community(name="Planetas", description="Planetas")
        db.session.add_all([community1, community2, community3])
        db.session.flush()

        ref_metadata = DSMetaData(
            title="Reference Dataset",
            description="Test reference dataset",
            publication_type=PublicationType.NONE,
            tags="planets,space",
        )
        db.session.add(ref_metadata)
        db.session.flush()

        ref_dataset = DataSet(user_id=user.id, ds_meta_data_id=ref_metadata.id)
        db.session.add(ref_dataset)
        db.session.flush()

        assoc1 = CommunityDataSet(
            community_id=community1.id,
            dataset_id=ref_dataset.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        assoc2 = CommunityDataSet(
            community_id=community2.id,
            dataset_id=ref_dataset.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        db.session.add_all([assoc1, assoc2])

        candidate1_metadata = DSMetaData(
            title="Candidate 1 - Two Shared Communities",
            description="Test candidate 1",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/test1",
            tags="planet",
        )
        db.session.add(candidate1_metadata)
        db.session.flush()

        candidate1 = DataSet(user_id=user.id, ds_meta_data_id=candidate1_metadata.id)
        db.session.add(candidate1)
        db.session.flush()

        c1_assoc1 = CommunityDataSet(
            community_id=community1.id,
            dataset_id=candidate1.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        c1_assoc2 = CommunityDataSet(
            community_id=community2.id,
            dataset_id=candidate1.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        db.session.add_all([c1_assoc1, c1_assoc2])

        candidate2_metadata = DSMetaData(
            title="Candidate 2 - One Shared Community",
            description="Test candidate 2",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/test2",
            tags="data",
        )
        db.session.add(candidate2_metadata)
        db.session.flush()

        candidate2 = DataSet(user_id=user.id, ds_meta_data_id=candidate2_metadata.id)
        db.session.add(candidate2)
        db.session.flush()

        c2_assoc = CommunityDataSet(
            community_id=community1.id,
            dataset_id=candidate2.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        db.session.add(c2_assoc)

        candidate3_metadata = DSMetaData(
            title="Candidate 3 - No Shared Communities",
            description="Test candidate 3",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/test3",
            tags="other",
        )
        db.session.add(candidate3_metadata)
        db.session.flush()

        candidate3 = DataSet(user_id=user.id, ds_meta_data_id=candidate3_metadata.id)
        db.session.add(candidate3)
        db.session.flush()

        c3_assoc = CommunityDataSet(
            community_id=community3.id,
            dataset_id=candidate3.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        db.session.add(c3_assoc)

        db.session.commit()

    yield test_client


def test_recommendations_with_pending_communities(test_client):
    """
    Test con comunidades pendientes no cuentan en recomendaciones.
    """
    with test_client.application.app_context():
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=unique_email, password="password")
        db.session.add(user)
        db.session.flush()

        profile = UserProfile(user_id=user.id, name="Test", surname="User")
        db.session.add(profile)

        community = Community(name="Pending Test Community", description="Test")
        db.session.add(community)
        db.session.flush()

        ref_metadata = DSMetaData(
            title="Ref Dataset Rejected Test",
            description="Test",
            publication_type=PublicationType.NONE,
            tags="test",
        )
        db.session.add(ref_metadata)
        db.session.flush()

        ref_dataset = DataSet(user_id=user.id, ds_meta_data_id=ref_metadata.id)
        db.session.add(ref_dataset)
        db.session.flush()

        ref_assoc = CommunityDataSet(
            community_id=community.id,
            dataset_id=ref_dataset.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        db.session.add(ref_assoc)

        candidate_metadata = DSMetaData(
            title="Candidate with Pending Community",
            description="Test",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/pending",
            tags="test",
        )
        db.session.add(candidate_metadata)
        db.session.flush()

        candidate = DataSet(user_id=user.id, ds_meta_data_id=candidate_metadata.id)
        db.session.add(candidate)
        db.session.flush()

        pending_assoc = CommunityDataSet(
            community_id=community.id,
            dataset_id=candidate.id,
            status=CommunityDataSetStatus.PENDING,
        )
        db.session.add(pending_assoc)
        db.session.commit()

        repo = repositories.DataSetRepository()
        recommendations = repo.recommended_datasets(ref_dataset.id, limit=10)

        candidate_in_recommendations = any(rec.id == candidate.id for rec in recommendations)
        assert not candidate_in_recommendations or recommendations[0].id != candidate.id, (
            "Pending community associations should not boost recommendation score"
        )


def test_recommendations_with_rejected_communities(test_client):
    """
    Test con comunidades rechazadas no cuentan en recomendaciones.
    """
    with test_client.application.app_context():
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=unique_email, password="password")
        db.session.add(user)
        db.session.flush()

        profile = UserProfile(user_id=user.id, name="Test", surname="User")
        db.session.add(profile)

        community = Community(name="Rejected Test Community", description="Test")
        db.session.add(community)
        db.session.flush()

        ref_metadata = DSMetaData(
            title="Ref Dataset Rejected Test",
            description="Test",
            publication_type=PublicationType.NONE,
            tags="test",
        )
        db.session.add(ref_metadata)
        db.session.flush()

        ref_dataset = DataSet(user_id=user.id, ds_meta_data_id=ref_metadata.id)
        db.session.add(ref_dataset)
        db.session.flush()

        ref_assoc = CommunityDataSet(
            community_id=community.id,
            dataset_id=ref_dataset.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        db.session.add(ref_assoc)

        candidate_metadata = DSMetaData(
            title="Candidate with Rejected Community",
            description="Test",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/rejected",
            tags="test",
        )
        db.session.add(candidate_metadata)
        db.session.flush()

        candidate = DataSet(user_id=user.id, ds_meta_data_id=candidate_metadata.id)
        db.session.add(candidate)
        db.session.flush()

        rejected_assoc = CommunityDataSet(
            community_id=community.id,
            dataset_id=candidate.id,
            status=CommunityDataSetStatus.REJECTED,
        )
        db.session.add(rejected_assoc)
        db.session.commit()

        repo = repositories.DataSetRepository()
        recommendations = repo.recommended_datasets(ref_dataset.id, limit=10)

        candidate_in_recommendations = any(rec.id == candidate.id for rec in recommendations)
        assert not candidate_in_recommendations or recommendations[0].id != candidate.id, (
            "Rejected community associations should not boost recommendation score"
        )


def test_recommendations_combined_scoring(test_client):
    """
    Test todos los factores (comunidad, tags y autores) en la puntuación.
    """
    with test_client.application.app_context():
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=unique_email, password="password")
        db.session.add(user)
        db.session.flush()

        profile = UserProfile(user_id=user.id, name="Test", surname="User")
        db.session.add(profile)

        community = Community(name="Combined Test Community", description="Test")
        db.session.add(community)
        db.session.flush()

        ref_metadata = DSMetaData(
            title="Combined Scoring Reference",
            description="Test",
            publication_type=PublicationType.NONE,
            tags="machine learning,ai",
        )
        db.session.add(ref_metadata)
        db.session.flush()

        ref_author = Author(
            name="John Doe",
            affiliation="University",
            ds_meta_data_id=ref_metadata.id,
        )
        db.session.add(ref_author)

        ref_dataset = DataSet(user_id=user.id, ds_meta_data_id=ref_metadata.id)
        db.session.add(ref_dataset)
        db.session.flush()

        ref_assoc = CommunityDataSet(
            community_id=community.id,
            dataset_id=ref_dataset.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        db.session.add(ref_assoc)

        candidate1_metadata = DSMetaData(
            title="All Factors Match",
            description="Test",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/all",
            tags="machine learning,ai,deep learning",
        )
        db.session.add(candidate1_metadata)
        db.session.flush()

        candidate1_author = Author(
            name="John Doe",
            affiliation="University",
            ds_meta_data_id=candidate1_metadata.id,
        )
        db.session.add(candidate1_author)

        candidate1 = DataSet(user_id=user.id, ds_meta_data_id=candidate1_metadata.id)
        db.session.add(candidate1)
        db.session.flush()

        c1_assoc = CommunityDataSet(
            community_id=community.id,
            dataset_id=candidate1.id,
            status=CommunityDataSetStatus.ACCEPTED,
        )
        db.session.add(c1_assoc)

        candidate2_metadata = DSMetaData(
            title="Only Tags Match",
            description="Test",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/tags",
            tags="machine learning",
        )
        db.session.add(candidate2_metadata)
        db.session.flush()

        candidate2 = DataSet(user_id=user.id, ds_meta_data_id=candidate2_metadata.id)
        db.session.add(candidate2)
        db.session.flush()

        db.session.commit()

        repo = repositories.DataSetRepository()
        recommendations = repo.recommended_datasets(ref_dataset.id, limit=10)

        assert len(recommendations) >= 2, "Should have recommendations"
        assert recommendations[0].id == candidate1.id, "Dataset matching all factors should rank highest"


def test_recommendations_no_doi_excluded(test_client):
    """
    Test Datasets sin DOI son excluidos de las recomendaciones.
    """
    with test_client.application.app_context():
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=unique_email, password="password")
        db.session.add(user)
        db.session.flush()

        profile = UserProfile(user_id=user.id, name="Test", surname="User")
        db.session.add(profile)

        ref_metadata = DSMetaData(
            title="DOI Test Reference",
            description="Test",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/ref",
            tags="test",
        )
        db.session.add(ref_metadata)
        db.session.flush()

        ref_dataset = DataSet(user_id=user.id, ds_meta_data_id=ref_metadata.id)
        db.session.add(ref_dataset)
        db.session.flush()

        no_doi_metadata = DSMetaData(
            title="No DOI Dataset",
            description="Test",
            publication_type=PublicationType.NONE,
            tags="test",
        )
        db.session.add(no_doi_metadata)
        db.session.flush()

        no_doi_dataset = DataSet(user_id=user.id, ds_meta_data_id=no_doi_metadata.id)
        db.session.add(no_doi_dataset)

        db.session.commit()

        repo = repositories.DataSetRepository()
        recommendations = repo.recommended_datasets(ref_dataset.id, limit=10)

        no_doi_in_recommendations = any(rec.id == no_doi_dataset.id for rec in recommendations)
        assert not no_doi_in_recommendations, "Datasets without DOI should be excluded from recommendations"


def test_recommendations_empty_when_no_candidates(test_client):
    with test_client.application.app_context():
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=unique_email, password="password")
        db.session.add(user)
        db.session.flush()

        profile = UserProfile(user_id=user.id, name="Test", surname="User")
        db.session.add(profile)

        ref_metadata = DSMetaData(
            title="Dataset sin recomendaciones",
            description="Test",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/noRecom",
            tags="noRecom",
        )
        db.session.add(ref_metadata)
        db.session.flush()

        ref_dataset = DataSet(user_id=user.id, ds_meta_data_id=ref_metadata.id)
        db.session.add(ref_dataset)

        db.session.commit()

        repo = repositories.DataSetRepository()
        recommendations = repo.recommended_datasets(ref_dataset.id, limit=10)

        assert len(recommendations) == 0, "Should return empty list when no valid candidates exist"
