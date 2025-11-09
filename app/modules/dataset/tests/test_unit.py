import pytest

from app import db
from app.modules.dataset import repositories, services
from app.modules.dataset.models import DSMetaData, PublicationType


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
