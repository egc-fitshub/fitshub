import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import (
    DataSet,
    DSMetaData,
    PublicationType,
)
from app.modules.dataset.services import DataSetService
from app.modules.fitsmodel.models import FMMetaData, FitsModel
from app.modules.hubfile.models import Hubfile


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

        dataset_test = DataSet(
            user_id=user_test.id,
            ds_meta_data_id=meta_test.id,
        )
        db.session.add(dataset_test)
        db.session.commit()

    yield test_client


def test_generate_json_badge_data(test_client):
    response = test_client.get("/dataset/1/badge.json")

    assert response.status_code == 200, "El endpoint /badge.json falló."
    assert response.mimetype == "application/json", (
        "El endpoint no devolvió JSON."
    )
    data = response.json

    assert data["schemaVersion"] == 1
    assert data["color"] == "blue"

    assert data["label"] == "10.1234/test-doi"

    assert data["message"] == "0"


def test_update_dsmetadata_indexes_dataset(monkeypatch, test_client):
    calls = {"dataset": [], "hubfile": []}

    def fake_index_dataset(dataset):
        calls["dataset"].append(dataset.id)

    def fake_index_hubfile(hubfile):
        calls["hubfile"].append(hubfile.id)

    monkeypatch.setattr(
        "app.modules.elasticsearch.utils.index_dataset",
        fake_index_dataset,
    )
    monkeypatch.setattr(
        "app.modules.elasticsearch.utils.index_hubfile",
        fake_index_hubfile,
    )

    with test_client.application.app_context():
        user = User.query.first()

        ds_meta = DSMetaData(
            title="Dataset indexing test",
            description="Descripción",
            publication_type=PublicationType.OTHER,
        )
        db.session.add(ds_meta)
        db.session.commit()

        dataset = DataSet(user_id=user.id, ds_meta_data_id=ds_meta.id)
        db.session.add(dataset)
        db.session.commit()

        fm_meta = FMMetaData(
            fits_filename="model.fits",
            title="FM",
            description="FM descripción",
            publication_type=PublicationType.OTHER,
        )
        db.session.add(fm_meta)
        db.session.commit()

        fits_model = FitsModel(
            data_set_id=dataset.id,
            fm_meta_data_id=fm_meta.id,
        )
        db.session.add(fits_model)
        db.session.commit()

        hubfile = Hubfile(
            name="model.fits",
            checksum="abc123",
            size=42,
            fits_model_id=fits_model.id,
        )
        db.session.add(hubfile)
        db.session.commit()

        service = DataSetService()
        service.update_dsmetadata(ds_meta.id, dataset_doi="10.9999/indexed")

        assert calls["dataset"] == [dataset.id]
        assert calls["hubfile"] == [hubfile.id]
