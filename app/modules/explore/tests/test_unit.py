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
