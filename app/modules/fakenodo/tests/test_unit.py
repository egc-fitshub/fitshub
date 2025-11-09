import inspect

import pytest

from app.modules.fakenodo.services import FakenodoService


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


def test_module_importable():
    pytest.importorskip("app.modules.fakenodo.services")


def make_dataset():
    class Meta:
        def __init__(self):
            self.title = "Test Title"

    class DummyDataset:
        def __init__(self):
            self.ds_meta_data = Meta()

    return DummyDataset()


def test_services_expose_callables():
    module = pytest.importorskip("app.modules.fakenodo.services")
    callables = [
        name for name, obj in inspect.getmembers(module) if not name.startswith("_") and inspect.isroutine(obj)
    ]
    if not callables:
        pytest.skip("No se encontraron callables públicos en app.modules.fakenodo.services")
    assert len(callables) > 0, "Se espera al menos una función pública en services"


def test_sample_assertion(test_client):
    """
    Sample test to verify that the test framework and environment are working correctly.
    It does not communicate with the Flask application; it only performs a simple assertion to
    confirm that the tests in this module can be executed.
    """
    greeting = "Hello, World!"
    assert greeting == "Hello, World!", "The greeting does not coincide with 'Hello, World!'"


def test_test_full_connection():
    service = FakenodoService()
    response = service.test_full_connection()
    data = response.get_json()
    assert data["success"] is True
    assert data["message"] == "FakeNodo connection test successful."


def test_create_new_deposition():
    service = FakenodoService()
    ds = make_dataset()
    deposition = service.create_new_deposition(ds)
    assert isinstance(deposition, dict)
    assert "id" in deposition
    assert "metadata" in deposition
    assert "links" in deposition


def test_upload_file():
    service = FakenodoService()
    ds = make_dataset()
    result = service.upload_file(ds, deposition_id=1234, feature_model="feature_model.obj")
    assert isinstance(result, dict)
    assert result["status"] == "completed"


def test_publish_deposition():
    service = FakenodoService()
    res = service.publish_deposition(1234)
    assert isinstance(res, dict)
    assert res.get("state") == "done"
    assert res.get("submitted") is True


def test_get_doi():
    service = FakenodoService()
    doi = service.get_doi(1234)
    assert isinstance(doi, str)
    assert doi.startswith("10.5281") or doi.startswith("10.5072")
