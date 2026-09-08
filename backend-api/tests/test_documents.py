"""Tests for the Knowledge Base document endpoints (Epic 3 / US-008..US-014).

The outbound calls to backend-ai (``trigger_indexing`` / ``trigger_deletion``)
are monkeypatched — this suite verifies backend-api's own contract
(validation, permissions, tenant isolation, the internal callback auth)
without touching real HTTP/model calls, matching how the rest of the
suite avoids depending on infra outside this process.
"""

from __future__ import annotations

import pytest
from conftest import DEMO_ORG_ID, make_organization, make_user
from fastapi.testclient import TestClient

from app.config import settings
from app.documents.repositories import DocumentRepository
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _stub_ai_client(monkeypatch):
    """Replace the real backend-ai HTTP calls with recording stubs.

    Autouse: no test in this file should ever hit the network, and
    forgetting the patch would surface as a slow/failing test rather
    than a silent false-positive, which is the safer failure mode.
    """
    calls = {"indexing": [], "deletion": []}

    def _fake_trigger_indexing(**kwargs):
        calls["indexing"].append(kwargs)

    def _fake_trigger_deletion(document_id):
        calls["deletion"].append(document_id)
        return True

    monkeypatch.setattr("app.documents.router.trigger_indexing", _fake_trigger_indexing)
    monkeypatch.setattr("app.documents.router.trigger_deletion", _fake_trigger_deletion)
    return calls


def _admin_headers(login_as):
    return login_as("demo", "testpassword")[0]


@pytest.fixture
def support_engineer():
    return make_user(
        username="sam",
        password="sampassword1",
        role="support_engineer",
        organization_id=DEMO_ORG_ID,
    )


def _support_headers(login_as):
    return login_as("sam", "sampassword1")[0]


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


def _upload(headers, *, filename="notes.txt", content=b"hello knowledge base", content_type="text/plain"):
    return client.post(
        "/documents",
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# US-008 — Upload Documents
# ---------------------------------------------------------------------------


def test_admin_can_upload_supported_types(login_as):
    headers = _admin_headers(login_as)
    for filename, content_type in [
        ("a.pdf", "application/pdf"),
        ("a.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("a.txt", "text/plain"),
        ("a.md", "text/markdown"),
        ("a.csv", "text/csv"),
    ]:
        response = _upload(headers, filename=filename, content=b"some content", content_type=content_type)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "processing"
        assert body["filename"] == filename


def test_upload_rejects_unsupported_extension(login_as):
    headers = _admin_headers(login_as)
    response = _upload(headers, filename="a.exe", content_type="application/octet-stream")
    assert response.status_code == 415


def test_upload_rejects_empty_file(login_as):
    headers = _admin_headers(login_as)
    response = _upload(headers, content=b"")
    assert response.status_code == 400


def test_upload_rejects_oversized_file(login_as, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_bytes", 10)
    headers = _admin_headers(login_as)
    response = _upload(headers, content=b"this is definitely more than 10 bytes")
    assert response.status_code == 413


def test_upload_triggers_indexing_background_job(login_as, _stub_ai_client):
    headers = _admin_headers(login_as)
    response = _upload(headers)
    assert response.status_code == 201
    document_id = response.json()["id"]
    assert len(_stub_ai_client["indexing"]) == 1
    call = _stub_ai_client["indexing"][0]
    assert call["document_id"] == document_id
    assert call["previous_hash"] is None


def test_customer_cannot_upload_document(customer_user, login_as):
    headers = _customer_headers(login_as)
    response = _upload(headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# US-014 — Document Management: list / delete / reindex
# ---------------------------------------------------------------------------


def test_list_documents_scoped_to_own_org(login_as):
    headers = _admin_headers(login_as)
    _upload(headers, filename="mine.txt")

    other_org = make_organization(name="Other Co", slug="other")
    make_user(
        username="foreign-admin",
        password="foreignpass1",
        role="admin",
        organization_id=other_org["id"],
    )
    foreign_headers, _ = login_as("foreign-admin", "foreignpass1")
    _upload(foreign_headers, filename="theirs.txt")

    response = client.get("/documents", headers=headers)
    assert response.status_code == 200
    filenames = [d["filename"] for d in response.json()]
    assert filenames == ["mine.txt"]


def test_support_engineer_can_delete_own_document(support_engineer, login_as):
    headers = _support_headers(login_as)
    upload = _upload(headers, filename="own.txt")
    document_id = upload.json()["id"]

    response = client.delete(f"/documents/{document_id}", headers=headers)
    assert response.status_code == 204
    assert DocumentRepository.get_by_id(document_id) is None


def test_support_engineer_cannot_delete_others_document(support_engineer, login_as):
    admin_headers = _admin_headers(login_as)
    upload = _upload(admin_headers, filename="admins.txt")
    document_id = upload.json()["id"]

    support_headers = _support_headers(login_as)
    response = client.delete(f"/documents/{document_id}", headers=support_headers)
    assert response.status_code == 403
    assert DocumentRepository.get_by_id(document_id) is not None


def test_admin_can_delete_any_org_document(support_engineer, login_as):
    support_headers = _support_headers(login_as)
    upload = _upload(support_headers, filename="staff.txt")
    document_id = upload.json()["id"]

    admin_headers = _admin_headers(login_as)
    response = client.delete(f"/documents/{document_id}", headers=admin_headers)
    assert response.status_code == 204


def test_delete_returns_502_and_deletes_nothing_when_ai_backend_unreachable(login_as, monkeypatch):
    headers = _admin_headers(login_as)
    upload = _upload(headers, filename="stuck.txt")
    document_id = upload.json()["id"]

    monkeypatch.setattr("app.documents.router.trigger_deletion", lambda document_id: False)
    response = client.delete(f"/documents/{document_id}", headers=headers)
    assert response.status_code == 502
    assert DocumentRepository.get_by_id(document_id) is not None


def test_reindex_sets_status_processing_and_passes_previous_hash(login_as, _stub_ai_client):
    headers = _admin_headers(login_as)
    upload = _upload(headers, filename="reindex-me.txt")
    document_id = upload.json()["id"]
    DocumentRepository.mark_indexed(document_id, chunk_count=3, content_hash="abc123")

    response = client.post(f"/documents/{document_id}/reindex", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    reindex_call = _stub_ai_client["indexing"][-1]
    assert reindex_call["previous_hash"] == "abc123"


def test_document_not_found_returns_404(login_as):
    headers = _admin_headers(login_as)
    response = client.get("/documents/does-not-exist", headers=headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Internal callback endpoint — gated by X-Internal-Token, not a user JWT
# ---------------------------------------------------------------------------


def test_internal_status_update_requires_valid_token(login_as):
    headers = _admin_headers(login_as)
    upload = _upload(headers)
    document_id = upload.json()["id"]

    no_token = client.patch(
        f"/internal/documents/{document_id}/status",
        json={"status": "indexed", "chunk_count": 5, "content_hash": "deadbeef"},
    )
    assert no_token.status_code == 401

    wrong_token = client.patch(
        f"/internal/documents/{document_id}/status",
        json={"status": "indexed", "chunk_count": 5, "content_hash": "deadbeef"},
        headers={"X-Internal-Token": "wrong"},
    )
    assert wrong_token.status_code == 401


def test_internal_status_update_marks_indexed(login_as):
    headers = _admin_headers(login_as)
    upload = _upload(headers)
    document_id = upload.json()["id"]

    response = client.patch(
        f"/internal/documents/{document_id}/status",
        json={"status": "indexed", "chunk_count": 7, "content_hash": "deadbeef"},
        headers={"X-Internal-Token": settings.internal_service_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "indexed"
    assert body["chunk_count"] == 7
    assert body["content_hash"] == "deadbeef"
    assert body["indexed_at"] is not None


def test_internal_status_update_unchanged_preserves_chunk_count(login_as):
    """US-013: the 'unchanged, skipped re-embedding' callback omits
    chunk_count — it must NOT reset an already-indexed document back
    to 0 chunks."""
    headers = _admin_headers(login_as)
    upload = _upload(headers)
    document_id = upload.json()["id"]
    DocumentRepository.mark_indexed(document_id, chunk_count=12, content_hash="abc123")

    response = client.patch(
        f"/internal/documents/{document_id}/status",
        json={"status": "indexed", "content_hash": "abc123"},
        headers={"X-Internal-Token": settings.internal_service_token},
    )
    assert response.status_code == 200
    assert response.json()["chunk_count"] == 12


def test_internal_status_update_marks_failed(login_as):
    headers = _admin_headers(login_as)
    upload = _upload(headers)
    document_id = upload.json()["id"]

    response = client.patch(
        f"/internal/documents/{document_id}/status",
        json={"status": "failed", "error_message": "no extractable text"},
        headers={"X-Internal-Token": settings.internal_service_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_message"] == "no extractable text"
