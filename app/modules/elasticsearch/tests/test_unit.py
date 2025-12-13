import importlib
import sys
from datetime import datetime
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.modules.elasticsearch import services as es_services
from app.modules.elasticsearch import utils as es_utils


@pytest.fixture(autouse=True)
def _patch_repository_and_sleep(monkeypatch):
    monkeypatch.setattr(es_services, "ElasticsearchRepository", lambda: object())
    monkeypatch.setattr(es_services.time, "sleep", lambda *_args, **_kwargs: None)


@pytest.fixture(autouse=True)
def es_exceptions(monkeypatch):
    class SimpleBadRequestError(Exception):
        def __init__(self, info=None):
            super().__init__("bad request")
            self.info = info or {"error": "bad-request"}

    class SimpleApiError(Exception):
        def __init__(self, info=None):
            super().__init__("api error")
            self.info = info or {"error": "api-error"}

    class SimpleNotFoundError(Exception):
        pass

    class SimpleConnectionError(Exception):
        pass

    monkeypatch.setattr(es_services, "BadRequestError", SimpleBadRequestError)
    monkeypatch.setattr(es_services, "ApiError", SimpleApiError)
    monkeypatch.setattr(es_services, "NotFoundError", SimpleNotFoundError)
    monkeypatch.setattr(es_services, "ConnectionError", SimpleConnectionError)

    return SimpleNamespace(
        BadRequestError=SimpleBadRequestError,
        ApiError=SimpleApiError,
        NotFoundError=SimpleNotFoundError,
        ConnectionError=SimpleConnectionError,
    )


def make_service(es_client=None):
    service = object.__new__(es_services.ElasticsearchService)
    service.es = es_client or MagicMock()
    service.index_name = "test-index"
    service.retry_attempts = 1
    service.retry_delay = 0
    return service


@pytest.mark.parametrize(
    "invalid_name",
    [123, "", "invalid#", "UPPER", "-prefixed"],
)
def test_service_init_validation_errors(monkeypatch, invalid_name):
    monkeypatch.setattr(es_services, "Elasticsearch", lambda *a, **k: MagicMock())

    with pytest.raises(ValueError):
        es_services.ElasticsearchService(host="http://fake", index_name=invalid_name)


def test_service_init_wait_failure(monkeypatch, es_exceptions):
    monkeypatch.setattr(es_services, "Elasticsearch", lambda *a, **k: MagicMock())
    monkeypatch.setattr(
        es_services.ElasticsearchService,
        "wait_for_elasticsearch",
        lambda self, **_: False,
    )
    monkeypatch.setattr(
        es_services.ElasticsearchService,
        "create_index_if_not_exists",
        lambda self: None,
    )

    with pytest.raises(es_exceptions.ConnectionError):
        es_services.ElasticsearchService(host="http://fake", index_name="validindex")


def test_service_init_logs_when_index_creation_fails(monkeypatch):
    es_client = MagicMock()
    es_client.ping.return_value = True
    monkeypatch.setattr(es_services, "Elasticsearch", lambda *a, **k: es_client)
    monkeypatch.setattr(
        es_services.ElasticsearchService,
        "wait_for_elasticsearch",
        lambda self, **_: True,
    )

    def raise_creation(self):
        raise RuntimeError("boom")

    monkeypatch.setattr(es_services.ElasticsearchService, "create_index_if_not_exists", raise_creation)

    logger = MagicMock()
    fake_app = SimpleNamespace(config={}, logger=logger)
    monkeypatch.setattr(es_services, "current_app", fake_app)

    es_services.ElasticsearchService(host="http://fake", index_name="validindex")

    logger.exception.assert_called_once()


def test_service_init_warns_when_no_app_context(monkeypatch, capsys):
    es_client = MagicMock()
    es_client.ping.return_value = True
    monkeypatch.setattr(es_services, "Elasticsearch", lambda *a, **k: es_client)
    monkeypatch.setattr(
        es_services.ElasticsearchService,
        "wait_for_elasticsearch",
        lambda self, **_: True,
    )

    def raise_creation(self):
        raise RuntimeError("boom")

    monkeypatch.setattr(es_services.ElasticsearchService, "create_index_if_not_exists", raise_creation)

    class NoApp:
        def __getattr__(self, _):
            raise RuntimeError("no app context")

    monkeypatch.setattr(es_services, "current_app", NoApp())

    es_services.ElasticsearchService(host="http://fake", index_name="validindex")

    captured = capsys.readouterr()
    assert "[WARN]" in captured.out


def test_wait_for_elasticsearch_success():
    client = MagicMock()
    client.ping.side_effect = [False, True]
    service = make_service(client)

    assert service.wait_for_elasticsearch(retries=3, delay=0) is True
    assert client.ping.call_count == 2


def test_wait_for_elasticsearch_returns_false(es_exceptions):
    client = MagicMock()
    client.ping.side_effect = es_exceptions.ConnectionError("down")
    service = make_service(client)

    assert service.wait_for_elasticsearch(retries=2, delay=0) is False


def test_create_index_creates_when_missing():
    client = MagicMock()
    client.indices.exists.return_value = False
    service = make_service(client)

    service.create_index_if_not_exists()

    client.indices.create.assert_called_once()


def test_create_index_skips_when_exists():
    client = MagicMock()
    client.indices.exists.return_value = True
    service = make_service(client)

    service.create_index_if_not_exists()

    client.indices.create.assert_not_called()


@pytest.mark.parametrize("exception_name", ["BadRequestError", "ApiError"])
def test_create_index_raises_specific_errors(exception_name, es_exceptions):
    client = MagicMock()
    exception_type = getattr(es_exceptions, exception_name)
    client.indices.exists.side_effect = exception_type()
    service = make_service(client)

    with pytest.raises(exception_type):
        service.create_index_if_not_exists()


def test_create_index_raises_generic_error():
    client = MagicMock()
    client.indices.exists.side_effect = RuntimeError("unexpected")
    service = make_service(client)

    with pytest.raises(RuntimeError):
        service.create_index_if_not_exists()


def test_index_document_success():
    client = MagicMock()
    service = make_service(client)

    service.index_document("doc", {"foo": "bar"})

    client.index.assert_called_once_with(index="test-index", id="doc", document={"foo": "bar"})


def test_index_document_logs_and_raises():
    client = MagicMock()
    client.index.side_effect = RuntimeError("fail")
    service = make_service(client)

    with pytest.raises(RuntimeError):
        service.index_document("doc", {})


def test_delete_document_not_found(es_exceptions):
    client = MagicMock()
    client.delete.side_effect = es_exceptions.NotFoundError("nope")
    service = make_service(client)

    service.delete_document("doc")

    client.delete.assert_called_once()


def test_delete_document_other_errors():
    client = MagicMock()
    client.delete.side_effect = RuntimeError("fail")
    service = make_service(client)

    with pytest.raises(RuntimeError):
        service.delete_document("doc")


def test_search_builds_filters_and_formats_hits():
    client = MagicMock()
    hit_source = {
        "created_at": "2024-01-01T12:00:00",
        "total_size_in_bytes": 2048,
    }
    client.search.return_value = {"hits": {"hits": [{"_source": hit_source}], "total": {"value": 1}}}
    service = make_service(client)

    results, total = service.search(
        query="text",
        publication_type="Article",
        sorting="oldest",
        tags=["science"],
        date_from="2024-01-01",
        date_to="2024-01-31",
        page=2,
        size=5,
    )

    assert total == 1
    assert results[0]["created_at"] == "01 Jan 2024, 12:00"
    assert results[0]["total_size_in_human_format"].endswith("KB")

    call_kwargs = client.search.call_args.kwargs
    assert call_kwargs["from_"] == 5
    body = call_kwargs["body"]
    must = body["query"]["bool"]["must"]
    filter_clauses = body["query"]["bool"]["filter"]

    assert must
    bool_clause = must[0]["bool"]
    should_clauses = bool_clause["should"]
    assert bool_clause["minimum_should_match"] == 1
    assert any("multi_match" in clause for clause in should_clauses)
    nested_clause = next(clause["nested"] for clause in should_clauses if "nested" in clause)
    assert nested_clause["path"] == "authors"
    assert any("term" in clause for clause in filter_clauses)
    assert any("terms" in clause for clause in filter_clauses)
    assert any("range" in clause for clause in filter_clauses)
    assert body["sort"][0]["created_at"]["order"] == "asc"


def test_search_ignores_invalid_dates():
    client = MagicMock()
    client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}
    service = make_service(client)

    service.search(query=None, date_from="bad", date_to="also-bad")

    body = client.search.call_args.kwargs["body"]
    assert body["query"]["bool"]["filter"] == []


def test_search_handles_not_found(monkeypatch, es_exceptions):
    client = MagicMock()
    client.search.side_effect = es_exceptions.NotFoundError("missing")
    service = make_service(client)
    service.create_index_if_not_exists = MagicMock()

    results, total = service.search(query="any")

    assert (results, total) == ([], 0)
    service.create_index_if_not_exists.assert_called_once()


def test_search_reraises_other_errors():
    client = MagicMock()
    client.search.side_effect = RuntimeError("boom")
    service = make_service(client)

    with pytest.raises(RuntimeError):
        service.search(query="text")


def test_format_hit_handles_invalid_date_and_size():
    service = make_service(MagicMock())
    hit = {"_source": {"created_at": "not-a-date", "total_size_in_bytes": 0}}

    formatted = service._format_hit(hit)

    assert formatted["created_at"] == "not-a-date"
    assert formatted["total_size_in_human_format"] == "0 B"


def test_human_readable_size_handles_bounds():
    service = make_service(MagicMock())

    assert service._human_readable_size(None) == ""
    assert service._human_readable_size(0) == "0 B"
    assert service._human_readable_size(2048).endswith("KB")


def test_indexing_service_indexes_all_entities():
    logger = MagicMock()
    indexed = {"datasets": [], "hubfiles": []}

    def index_dataset(dataset):
        indexed["datasets"].append(dataset.id)

    def index_hubfile(hubfile):
        indexed["hubfiles"].append(hubfile.id)

    service = es_services.IndexingService(index_dataset, index_hubfile, logger)

    dataset = SimpleNamespace(id=1)
    hubfile1 = SimpleNamespace(id=10)
    hubfile2 = SimpleNamespace(id=11)

    fm_with_hubfiles = SimpleNamespace(hubfiles=[hubfile1])
    fm_with_files = SimpleNamespace(hubfiles=None, files=[hubfile2])

    service.index_dataset_and_hubfiles(dataset, [fm_with_hubfiles, fm_with_files])

    assert indexed["datasets"] == [1]
    assert indexed["hubfiles"] == [10, 11]
    assert logger.info.call_count == 3


def test_indexing_service_logs_and_reraises_errors():
    logger = MagicMock()

    def failing_index_dataset(_):
        raise RuntimeError("boom")

    service = es_services.IndexingService(failing_index_dataset, lambda _: None, logger)

    with pytest.raises(RuntimeError):
        service.index_dataset_and_hubfiles(SimpleNamespace(id=1), [])

    logger.exception.assert_called_once()


def test_init_search_index_success(monkeypatch):
    created = {}

    class DummyService:
        def __init__(self):
            created["instance"] = self

        def create_index_if_not_exists(self):
            created["called"] = True

    monkeypatch.setattr(es_services, "ElasticsearchService", DummyService)

    es_utils.init_search_index()

    assert created.get("called") is True


def test_init_search_index_propagates_errors(monkeypatch):
    class DummyService:
        def __init__(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(es_services, "ElasticsearchService", DummyService)

    with pytest.raises(RuntimeError):
        es_utils.init_search_index()


def test_index_dataset_skips_without_doi(monkeypatch):
    class DummyService:
        def __init__(self):
            self.index_document = MagicMock()

    monkeypatch.setattr(es_services, "ElasticsearchService", DummyService)

    dataset = SimpleNamespace(id=1, ds_meta_data=SimpleNamespace(dataset_doi=None))

    es_utils.index_dataset(dataset)


def test_index_dataset_indexes_payload(monkeypatch):
    recorded = {}

    class DummyService:
        def __init__(self):
            pass

        def index_document(self, doc_id, data):
            recorded["doc_id"] = doc_id
            recorded["data"] = data

    monkeypatch.setattr(es_services, "ElasticsearchService", DummyService)

    authors = [SimpleNamespace(name="Alice", affiliation="Uni", orcid="0000")]
    metadata = SimpleNamespace(
        title="Dataset",
        description="Desc",
        publication_doi="10.1234/pub",
        dataset_doi="10.1234/dataset",
        publication_type=SimpleNamespace(value="article"),
        tags="science, data",
        authors=authors,
    )

    dataset = SimpleNamespace(
        id=42,
        ds_meta_data=metadata,
        created_at=datetime(2024, 1, 1),
        get_fitshub_doi=lambda: "doi",
        get_file_total_size=lambda: 2048,
        get_files_count=lambda: 3,
        get_cleaned_publication_type=lambda: "Article",
    )

    es_utils.index_dataset(dataset)

    assert recorded["doc_id"] == "dataset-42"
    assert recorded["data"]["authors"][0]["name"] == "Alice"
    assert recorded["data"]["tags"] == ["science", "data"]


def test_index_hubfile_skips_without_dataset(monkeypatch):
    class DummyService:
        def __init__(self):
            self.index_document = MagicMock()

    monkeypatch.setattr(es_services, "ElasticsearchService", DummyService)

    hubfile = SimpleNamespace(id=1, fits_model=None)

    es_utils.index_hubfile(hubfile)


def test_index_hubfile_indexes_payload(monkeypatch):
    recorded = {}

    class DummyService:
        def __init__(self):
            pass

        def index_document(self, doc_id, data):
            recorded["doc_id"] = doc_id
            recorded["data"] = data

    monkeypatch.setattr(es_services, "ElasticsearchService", DummyService)

    dataset = SimpleNamespace(
        id=7,
        ds_meta_data=SimpleNamespace(title="Dataset", dataset_doi="10.1/doi"),
        get_fitshub_doi=lambda: "fitshub-doi",
    )
    hubfile = SimpleNamespace(
        id=3,
        name="file.fits",
        fits_model=SimpleNamespace(data_set=dataset),
        fits_model_id=5,
        checksum="abc",
        size=1024,
        get_formatted_size=lambda: "1 KB",
    )

    es_utils.index_hubfile(hubfile)

    assert recorded["doc_id"] == "hubfile-3"
    assert recorded["data"]["dataset_id"] == 7
    assert recorded["data"]["size_in_human_format"] == "1 KB"


def test_reindex_all_invokes_helpers(monkeypatch):
    datasets = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    hubfiles = [SimpleNamespace(id=3)]

    class DummyQuery:
        def __init__(self, sequence):
            self._sequence = sequence

        def all(self):
            return self._sequence

    dataset_module = ModuleType("app.modules.dataset.models")
    dataset_module.DataSet = SimpleNamespace(query=DummyQuery(datasets))
    hubfile_module = ModuleType("app.modules.hubfile.models")
    hubfile_module.Hubfile = SimpleNamespace(query=DummyQuery(hubfiles))

    dataset_pkg = importlib.import_module("app.modules.dataset")
    hubfile_pkg = importlib.import_module("app.modules.hubfile")

    monkeypatch.setitem(sys.modules, "app.modules.dataset.models", dataset_module)
    monkeypatch.setitem(sys.modules, "app.modules.hubfile.models", hubfile_module)
    monkeypatch.setattr(dataset_pkg, "models", dataset_module, raising=False)
    monkeypatch.setattr(hubfile_pkg, "models", hubfile_module, raising=False)

    calls = []
    monkeypatch.setattr(es_utils, "index_dataset", lambda d: calls.append(("dataset", d.id)))
    monkeypatch.setattr(es_utils, "index_hubfile", lambda h: calls.append(("hubfile", h.id)))

    es_utils.reindex_all()

    assert ("dataset", 1) in calls and ("dataset", 2) in calls
    assert ("hubfile", 3) in calls
