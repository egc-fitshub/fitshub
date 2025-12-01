import os
import shutil
from io import BytesIO

import pytest
from flask_login import current_user

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.dataset import repositories, services
from app.modules.dataset.models import DataSet, DSMetaData, PublicationType


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
            tags="test",
        )
        db.session.add(meta_test)
        db.session.commit()

        dataset_test = DataSet(user_id=user_test.id, ds_meta_data_id=meta_test.id)
        db.session.add(dataset_test)
        db.session.commit()

    yield test_client


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

    assert len(os.listdir(file_path)) == 0

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
    assert hasattr(obtained_ds, "download_counter")
    assert obtained_ds.download_counter == 0


def test_download_counter_increments(test_client, sample_metadata):
    ds_test = services.DataSetService().create(user_id=1, ds_meta_data_id=sample_metadata.id, download_counter=5)

    services.DataSetService().update_download_counter(ds_test.id)
    obtained_ds = repositories.DataSetRepository().get_by_id(ds_test.id)
    assert hasattr(obtained_ds, "download_counter")
    assert obtained_ds.download_counter == 6
