"""Tests for the chat/conversation endpoints (Epic 5 / US-020..US-023).

The outbound streaming call to backend-ai (``stream_chat``) is
monkeypatched to yield canned SSE events — this suite verifies
backend-api's own contract (ownership, permissions, persistence,
auto-titling, SSE pass-through) without a real LLM call, matching how
``test_documents.py``/``test_search.py`` avoid depending on infra
outside this process.
"""

from __future__ import annotations

import json

import pytest
from conftest import DEMO_ORG_ID, make_user
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_CANNED_SOURCE = {
    "document_id": "doc-1",
    "filename": "Guide.pdf",
    "page_number": 2,
    "chunk_index": 0,
    "text": "Relevant chunk text.",
    "excerpt": "Relevant chunk text.",
    "score": 0.9,
    "rerank_score": 0.95,
}


@pytest.fixture(autouse=True)
def _stub_stream_chat(monkeypatch):
    """Replace the real backend-ai streaming call with a canned
    generator yielding the same (event, data) contract."""

    def _fake_stream_chat(*, query, organization_id, history):
        yield "sources", json.dumps({"results": [_CANNED_SOURCE]})
        yield "token", json.dumps({"text": "Hello "})
        yield "token", json.dumps({"text": "world"})
        yield "done", json.dumps({})

    monkeypatch.setattr("app.conversations.router.stream_chat", _fake_stream_chat)


def _admin_headers(login_as):
    return login_as("demo", "testpassword")[0]


@pytest.fixture
def second_user():
    return make_user(
        username="bob", password="bobpassword1", role="admin", organization_id=DEMO_ORG_ID
    )


@pytest.fixture
def customer_user():
    return make_user(
        username="carl",
        password="carlpassword1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )


# ---------------------------------------------------------------------------
# create / list / delete (US-023)
# ---------------------------------------------------------------------------


def test_create_conversation_starts_untitled(login_as):
    headers = _admin_headers(login_as)
    response = client.post("/conversations", headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] is None
    assert body["user_id"]


def test_customer_can_create_conversation(login_as, customer_user):
    """Locks in that the use_chat-OR-chat gate works for the
    customer role too, not just staff."""
    headers = login_as("carl", "carlpassword1")[0]
    response = client.post("/conversations", headers=headers)
    assert response.status_code == 201


def test_list_conversations_only_shows_callers_own(login_as, second_user):
    admin_headers = _admin_headers(login_as)
    client.post("/conversations", headers=admin_headers)

    bob_headers = login_as("bob", "bobpassword1")[0]
    client.post("/conversations", headers=bob_headers)

    admin_list = client.get("/conversations", headers=admin_headers).json()
    bob_list = client.get("/conversations", headers=bob_headers).json()
    assert len(admin_list) == 1
    assert len(bob_list) == 1
    assert admin_list[0]["id"] != bob_list[0]["id"]


def test_delete_conversation(login_as):
    headers = _admin_headers(login_as)
    conv = client.post("/conversations", headers=headers).json()
    response = client.delete(f"/conversations/{conv['id']}", headers=headers)
    assert response.status_code == 204
    assert (
        client.get(f"/conversations/{conv['id']}/messages", headers=headers).status_code
        == 404
    )


def test_cannot_view_another_users_conversation(login_as, second_user):
    admin_headers = _admin_headers(login_as)
    conv = client.post("/conversations", headers=admin_headers).json()

    bob_headers = login_as("bob", "bobpassword1")[0]
    response = client.get(f"/conversations/{conv['id']}/messages", headers=bob_headers)
    assert response.status_code == 404


def test_cannot_delete_another_users_conversation(login_as, second_user):
    admin_headers = _admin_headers(login_as)
    conv = client.post("/conversations", headers=admin_headers).json()

    bob_headers = login_as("bob", "bobpassword1")[0]
    response = client.delete(f"/conversations/{conv['id']}", headers=bob_headers)
    assert response.status_code == 404


def test_message_to_nonexistent_conversation_returns_404(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/conversations/does-not-exist/messages", json={"content": "hi"}, headers=headers
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# send message: streaming + persistence (US-020, US-021, US-022)
# ---------------------------------------------------------------------------


def test_send_message_streams_sse_and_persists_both_messages(login_as):
    headers = _admin_headers(login_as)
    conv = client.post("/conversations", headers=headers).json()

    response = client.post(
        f"/conversations/{conv['id']}/messages",
        json={"content": "What is X?"},
        headers=headers,
    )
    assert response.status_code == 200
    assert "event: sources" in response.text
    assert "event: token" in response.text
    assert "event: done" in response.text

    messages = client.get(f"/conversations/{conv['id']}/messages", headers=headers).json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is X?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello world"
    assert messages[1]["sources_json"] is not None
    assert "Guide.pdf" in messages[1]["sources_json"]


def test_first_message_sets_conversation_title(login_as):
    headers = _admin_headers(login_as)
    conv = client.post("/conversations", headers=headers).json()

    client.post(
        f"/conversations/{conv['id']}/messages",
        json={"content": "A fairly short first question"},
        headers=headers,
    )

    updated = next(
        c for c in client.get("/conversations", headers=headers).json() if c["id"] == conv["id"]
    )
    assert updated["title"] == "A fairly short first question"


def test_second_message_does_not_change_title(login_as):
    headers = _admin_headers(login_as)
    conv = client.post("/conversations", headers=headers).json()

    client.post(
        f"/conversations/{conv['id']}/messages", json={"content": "First"}, headers=headers
    )
    client.post(
        f"/conversations/{conv['id']}/messages", json={"content": "Second"}, headers=headers
    )

    updated = next(
        c for c in client.get("/conversations", headers=headers).json() if c["id"] == conv["id"]
    )
    assert updated["title"] == "First"


def test_empty_message_content_returns_422(login_as):
    headers = _admin_headers(login_as)
    conv = client.post("/conversations", headers=headers).json()
    response = client.post(
        f"/conversations/{conv['id']}/messages", json={"content": ""}, headers=headers
    )
    assert response.status_code == 422
