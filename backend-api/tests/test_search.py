"""Tests for the knowledge-base search endpoint (Epic 4 / US-015..US-019).

The outbound call to backend-ai (``run_search``) is monkeypatched —
this suite verifies backend-api's own contract (permission gating, org
scoping derived from the caller rather than client input, request
validation, error translation) without touching the real hybrid
search/rerank pipeline, matching how ``test_documents.py`` avoids
depending on infra outside this process.
"""

from __future__ import annotations

import pytest
from conftest import DEMO_ORG_ID, make_user
from fastapi.testclient import TestClient

from app.documents.ai_client import SearchServiceError
from app.main import app

client = TestClient(app)

_CANNED_RESULT = {
    "query": "payment failure",
    "results": [
        {
            "document_id": "doc-1",
            "filename": "Payments Guide.pdf",
            "page_number": 3,
            "chunk_index": 0,
            "text": "Full chunk text about payment failures.",
            "excerpt": "Full chunk text about <mark>payment</mark> failures.",
            "score": 0.87,
            "rerank_score": 0.95,
        }
    ],
    "retrieved_count": 42,
    "reranked_count": 42,
}


def _admin_headers(login_as):
    return login_as("demo", "testpassword")[0]


@pytest.fixture
def customer_user():
    make_user(
        username="alice",
        password="alicepass1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )


def _customer_headers(login_as):
    return login_as("alice", "alicepass1")[0]


def test_admin_can_search(login_as, monkeypatch):
    captured = {}

    def _fake_run_search(**kwargs):
        captured.update(kwargs)
        return _CANNED_RESULT

    monkeypatch.setattr("app.search.router.run_search", _fake_run_search)

    headers = _admin_headers(login_as)
    response = client.post("/search", json={"query": "payment failure"}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "payment failure"
    assert len(body["results"]) == 1
    assert body["results"][0]["filename"] == "Payments Guide.pdf"
    assert body["results"][0]["page_number"] == 3
    assert captured["organization_id"] == DEMO_ORG_ID
    assert captured["query"] == "payment failure"


def test_search_is_scoped_to_callers_own_organization(login_as, monkeypatch):
    """The request body has no organization_id field at all — this
    locks in that the caller can't search another tenant's content."""
    captured = {}
    monkeypatch.setattr(
        "app.search.router.run_search",
        lambda **kwargs: captured.update(kwargs) or _CANNED_RESULT,
    )

    headers = _admin_headers(login_as)
    client.post(
        "/search",
        json={"query": "test", "organization_id": "some-other-org"},
        headers=headers,
    )

    # Even if a client tries to smuggle an organization_id into the
    # body, SearchRequest doesn't define that field, so it's ignored —
    # the org always comes from the authenticated caller.
    assert captured["organization_id"] == DEMO_ORG_ID


def test_customer_cannot_search(customer_user, login_as):
    headers = _customer_headers(login_as)
    response = client.post("/search", json={"query": "test"}, headers=headers)
    assert response.status_code == 403


def test_empty_query_returns_422(login_as):
    headers = _admin_headers(login_as)
    response = client.post("/search", json={"query": ""}, headers=headers)
    assert response.status_code == 422


def test_final_k_below_minimum_returns_422(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/search", json={"query": "test", "final_k": 3}, headers=headers
    )
    assert response.status_code == 422


def test_final_k_above_maximum_returns_422(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/search", json={"query": "test", "final_k": 25}, headers=headers
    )
    assert response.status_code == 422


def test_search_service_unreachable_returns_502(login_as, monkeypatch):
    def _raise(**kwargs):
        raise SearchServiceError("connection refused")

    monkeypatch.setattr("app.search.router.run_search", _raise)

    headers = _admin_headers(login_as)
    response = client.post("/search", json={"query": "test"}, headers=headers)
    assert response.status_code == 502
