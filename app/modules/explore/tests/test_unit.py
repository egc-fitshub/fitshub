import pytest
from elasticsearch import ConnectionError as ESConnectionError
from flask import template_rendered

from app.modules.dataset.models import PublicationType

ES_SERVICE_PATH = "app.modules.elasticsearch.services.ElasticsearchService"
API_SEARCH_URL = "/api/v1/search"


@pytest.fixture
def captured_templates(test_app):
    """Capture rendered templates to inspect the injected context."""

    recorded = []

    def record(sender, template, context, **extra):  # pragma: no cover - hook
        recorded.append((template, context))

    template_rendered.connect(record, test_app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, test_app)


def test_index_injects_publication_type_choices(
    test_client,
    captured_templates,
):
    response = test_client.get("/explore")

    assert response.status_code == 200
    assert len(captured_templates) == 1

    _, context = captured_templates[0]
    choices = context["publication_type_choices"]

    assert len(choices) == len(PublicationType)
    conference = next(choice for choice in choices if choice[0] == PublicationType.CONFERENCE_PAPER.value)
    assert conference == (
        PublicationType.CONFERENCE_PAPER.value,
        "Conference Paper",
    )


def test_api_search_success_with_filters(monkeypatch, test_client):
    captured_kwargs = {}

    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):
            captured_kwargs.update(kwargs)
            return ([{"id": 7}], 99)

    monkeypatch.setattr(ES_SERVICE_PATH, DummyService)

    response = test_client.get(
        API_SEARCH_URL,
        query_string={
            "q": "galaxy",
            "publication_type": "article",
            "sorting": "oldest",
            "tags": "tag1, tag2,,",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "page": 3,
            "size": 5,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "results": [{"id": 7}],
        "total": 99,
        "page": 3,
        "size": 5,
    }

    assert captured_kwargs == {
        "query": "galaxy",
        "publication_type": "article",
        "sorting": "oldest",
        "tags": ["tag1", "tag2"],
        "date_from": "2024-01-01",
        "date_to": "2024-01-31",
        "page": 3,
        "size": 5,
    }


def test_api_search_defaults_without_parameters(monkeypatch, test_client):
    captured_kwargs = {}

    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):
            captured_kwargs.update(kwargs)
            return ([], 0)

    monkeypatch.setattr(ES_SERVICE_PATH, DummyService)

    response = test_client.get(API_SEARCH_URL)

    assert response.status_code == 200
    assert response.get_json() == {
        "results": [],
        "total": 0,
        "page": 1,
        "size": 10,
    }

    assert captured_kwargs == {
        "query": "",
        "publication_type": None,
        "sorting": "newest",
        "tags": [],
        "date_from": None,
        "date_to": None,
        "page": 1,
        "size": 10,
    }


def test_api_search_handles_init_connection_error(monkeypatch, test_client):
    class BrokenService:
        def __init__(self, *args, **kwargs):
            raise ESConnectionError("cannot connect")

    monkeypatch.setattr(ES_SERVICE_PATH, BrokenService)

    response = test_client.get(API_SEARCH_URL)

    assert response.status_code == 503
    data = response.get_json()
    assert data["error"] == "Search service unavailable"
    assert "details" in data


def test_api_search_handles_connection_error_on_search(
    monkeypatch,
    test_client,
):
    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):
            raise ESConnectionError("timeout")

    monkeypatch.setattr(ES_SERVICE_PATH, DummyService)

    response = test_client.get(API_SEARCH_URL)

    assert response.status_code == 503
    data = response.get_json()
    assert data["error"] == "Search service unavailable"
    assert "details" in data


def test_api_search_handles_invalid_parameters(monkeypatch, test_client):
    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):
            raise ValueError("invalid sorting")

    monkeypatch.setattr(ES_SERVICE_PATH, DummyService)

    response = test_client.get(API_SEARCH_URL)

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid sorting"}


def test_api_search_handles_unexpected_error(monkeypatch, test_client):
    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(ES_SERVICE_PATH, DummyService)

    response = test_client.get(API_SEARCH_URL)

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected search error"}


def test_api_search_filters_by_community(monkeypatch, test_client):
    captured_kwargs = {}

    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):
            captured_kwargs.update(kwargs)
            return ([{"id": 1}, {"id": 2}, {"id": 3}], 3)

    monkeypatch.setattr(ES_SERVICE_PATH, DummyService)

    class MockQuery:
        def filter_by(self, **kwargs):
            self.kwargs = kwargs
            return self

        def first(self):
            if self.kwargs.get("dataset_id") in [1, 3]:
                return object()
            return None

    monkeypatch.setattr("app.modules.explore.routes.CommunityDataSet.query", MockQuery())

    response = test_client.get(
        API_SEARCH_URL,
        query_string={
            "q": "test",
            "community": "5",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()

    assert len(payload["results"]) == 2
    assert payload["results"][0]["id"] == 1
    assert payload["results"][1]["id"] == 3
    assert payload["total"] == 2
    assert payload["page"] == 1
    assert payload["size"] == 10


def test_api_search_no_community_returns_all_results(monkeypatch, test_client):
    captured_kwargs = {}

    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):
            captured_kwargs.update(kwargs)
            return ([{"id": 1}, {"id": 2}, {"id": 3}], 3)

    monkeypatch.setattr(ES_SERVICE_PATH, DummyService)

    response = test_client.get(
        API_SEARCH_URL,
        query_string={
            "q": "test",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()

    assert len(payload["results"]) == 3
    assert payload["total"] == 3


def test_api_search_community_no_matching_datasets(monkeypatch, test_client):
    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):
            return ([{"id": 1}, {"id": 2}], 2)

    monkeypatch.setattr(ES_SERVICE_PATH, DummyService)

    class MockQuery:
        def filter_by(self, **kwargs):
            return self

        def first(self):
            return None

    monkeypatch.setattr("app.modules.explore.routes.CommunityDataSet.query", MockQuery())

    response = test_client.get(
        API_SEARCH_URL,
        query_string={
            "community": "99",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["results"] == []
    assert payload["total"] == 0
