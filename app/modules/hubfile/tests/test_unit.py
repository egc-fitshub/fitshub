import base64
import os
import shutil

import numpy as np
import pytest
from astropy.io import fits

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import DataSet, DSMetaData, PublicationType
from app.modules.fitsmodel.models import FitsModel
from app.modules.hubfile.models import Hubfile, HubfileDownloadRecord, HubfileViewRecord
from app.modules.hubfile.routes import (
    get_image_from_fits_headers,
    parse_fits_headers,
)
from app.modules.hubfile.services import HubfileService


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


@pytest.fixture(scope="module")
def sample_hubfile(test_client):
    user = User(email="test_hubfile@example.com", password="password")
    db.session.add(user)
    db.session.commit()

    ds_meta = DSMetaData(title="Test Dataset", description="Desc", publication_type=PublicationType.OTHER)
    db.session.add(ds_meta)
    db.session.commit()

    dataset = DataSet(user_id=user.id, ds_meta_data_id=ds_meta.id)
    db.session.add(dataset)
    db.session.commit()

    fits_model = FitsModel(data_set_id=dataset.id)
    db.session.add(fits_model)
    db.session.commit()

    hubfile = Hubfile(name="test_file.fits", checksum="123", size=100, fits_model_id=fits_model.id)
    db.session.add(hubfile)
    db.session.commit()

    base_path = os.path.dirname(test_client.application.root_path)
    dir_path = os.path.join(base_path, f"uploads/user_{user.id}/dataset_{dataset.id}/")
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, "test_file.fits")

    # Create a valid FITS file
    data = np.arange(100).reshape((10, 10)).astype(np.float32)
    hdu = fits.PrimaryHDU(data)
    hdu.writeto(file_path)

    yield hubfile

    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


def test_sample_assertion(test_client):
    """
    Sample test to verify that the test framework and environment are working correctly.
    It does not communicate with the Flask application; it only performs a simple assertion to
    confirm that the tests in this module can be executed.
    """
    greeting = "Hello, World!"
    assert greeting == "Hello, World!", "The greeting does not coincide with 'Hello, World!'"


def test_parse_fits_headers(test_client):
    """
    Test that parse_fits_headers correctly reads and parses FITS headers from a file.
    """
    text = parse_fits_headers("app/modules/dataset/fits_examples/file1.fits")

    assert "SIMPLE" in text
    assert text.count("XTENSION") == 4
    assert text.count("IMAGE") == 3
    assert text.count("BINTABLE") == 1


def test_get_image_from_fits_headers_generates_png(tmp_path):
    """
    Create a small 2D FITS file, call the backend function and verify
    it returns a base64 encoded PNG image.
    """
    data = np.arange(16).reshape((4, 4)).astype(np.float32)
    hdu = fits.PrimaryHDU(data)
    file_path = tmp_path / "test_image.fits"
    hdu.writeto(file_path)

    image_b64 = get_image_from_fits_headers(str(file_path))
    assert isinstance(image_b64, str)
    decoded = base64.b64decode(image_b64)

    assert decoded.startswith(b"\x89PNG\r\n\x1a\n")


def test_get_image_from_fits_headers_invalid_file_raises():
    with pytest.raises(Exception):
        get_image_from_fits_headers("nonexistent_file.fits")


def test_download_file_no_cookie(test_client, sample_hubfile):
    response = test_client.get(f"/file/download/{sample_hubfile.id}")
    assert response.status_code == 200
    assert "file_download_cookie" in response.headers.get("Set-Cookie", "")

    with test_client.application.app_context():
        record = HubfileDownloadRecord.query.filter_by(file_id=sample_hubfile.id).first()
        assert record is not None
        assert record.download_cookie is not None


def test_download_file_no_existing_record(test_client):
    response = test_client.get("/file/download/9999")
    assert response.status_code == 404


def test_download_file_with_cookie(test_client, sample_hubfile):
    response1 = test_client.get(f"/file/download/{sample_hubfile.id}")
    cookie = response1.headers.get("Set-Cookie").split("=")[1].split(";")[0]

    test_client.set_cookie("file_download_cookie", cookie)
    response2 = test_client.get(f"/file/download/{sample_hubfile.id}")
    assert response2.status_code == 200

    with test_client.application.app_context():
        records = HubfileDownloadRecord.query.filter_by(file_id=sample_hubfile.id, download_cookie=cookie).all()
        assert len(records) == 1


def test_view_file_success(test_client, sample_hubfile):
    response = test_client.get(f"/file/view/{sample_hubfile.id}")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert "content" in json_data
    assert "image" in json_data
    assert "view_cookie" in response.headers.get("Set-Cookie", "")


def test_view_file_not_found(test_client):
    response = test_client.get("/file/view/9999")
    assert response.status_code == 404


def test_view_file_with_cookie(test_client, sample_hubfile):
    test_client.delete_cookie("view_cookie")

    response1 = test_client.get(f"/file/view/{sample_hubfile.id}")
    assert response1.status_code == 200
    cookie = response1.headers.get("Set-Cookie").split("=")[1].split(";")[0]

    test_client.set_cookie("view_cookie", cookie)
    response2 = test_client.get(f"/file/view/{sample_hubfile.id}")
    assert response2.status_code == 200

    with test_client.application.app_context():
        records = HubfileViewRecord.query.filter_by(file_id=sample_hubfile.id, view_cookie=cookie).all()
        assert len(records) == 1


def test_service_get_owner_user_by_hubfile(test_client, sample_hubfile):
    service = HubfileService()
    user = service.get_owner_user_by_hubfile(sample_hubfile)
    assert user is not None
    assert user.email == "test_hubfile@example.com"


def test_service_get_dataset_by_hubfile(test_client, sample_hubfile):
    service = HubfileService()
    dataset = service.get_dataset_by_hubfile(sample_hubfile)
    assert dataset is not None
    assert dataset.ds_meta_data.title == "Test Dataset"


def test_service_get_path_by_hubfile(test_client, sample_hubfile, monkeypatch):
    # Mock WORKING_DIR to ensure consistent path construction
    monkeypatch.setenv("WORKING_DIR", "/tmp/fitshub")

    service = HubfileService()
    path = service.get_path_by_hubfile(sample_hubfile)

    user_id = sample_hubfile.fits_model.data_set.user_id
    dataset_id = sample_hubfile.fits_model.data_set_id
    filename = sample_hubfile.name
    expected_path = f"/tmp/fitshub/uploads/user_{user_id}/dataset_{dataset_id}/{filename}"
    assert path == expected_path
