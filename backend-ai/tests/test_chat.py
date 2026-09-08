"""Tests for RAG chat (Epic 5 / US-020..US-023).

The real LLM and retrieval pipeline are monkeypatched — this suite
verifies prompt construction and SSE event framing, not model output.
Real generation is exercised in the plan's manual end-to-end
verification once a live GOOGLE_API_KEY is available.
"""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.chat import service as chat_service
from app.chat.prompt import build_messages
from app.chat.schemas import ChatMessage, ChatRequest
from app.chat.service import stream_chat_response
from app.retrieval.schemas import SearchResponse, SourceResult

# ---------------------------------------------------------------------------
# build_messages (prompt construction)
# ---------------------------------------------------------------------------


def _source(filename="Guide.pdf", page=3, text="Relevant chunk text."):
    return SourceResult(
        document_id="doc-1",
        filename=filename,
        page_number=page,
        chunk_index=0,
        text=text,
        excerpt=text,
        score=0.9,
        rerank_score=0.95,
    )


def test_build_messages_starts_with_system_message_containing_context():
    messages = build_messages("What is X?", [], [_source()])
    assert isinstance(messages[0], SystemMessage)
    assert "Guide.pdf" in messages[0].content
    assert "page 3" in messages[0].content
    assert "Relevant chunk text." in messages[0].content


def test_build_messages_notes_when_no_sources_found():
    messages = build_messages("What is X?", [], [])
    assert "no relevant sources" in messages[0].content.lower()


def test_build_messages_preserves_history_roles_in_order():
    history = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
    ]
    messages = build_messages("Follow-up question", history, [_source()])

    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "First question"
    assert isinstance(messages[2], AIMessage)
    assert messages[2].content == "First answer"


def test_build_messages_appends_new_query_as_final_human_message():
    messages = build_messages("Follow-up question", [], [_source()])
    assert isinstance(messages[-1], HumanMessage)
    assert messages[-1].content == "Follow-up question"


# ---------------------------------------------------------------------------
# stream_chat_response (SSE framing)
# ---------------------------------------------------------------------------


class _FakeChunk:
    def __init__(self, content: str):
        self.content = content


class _FakeModel:
    def __init__(self, chunks: list[str]):
        self._chunks = chunks

    def stream(self, _messages):
        for text in self._chunks:
            yield _FakeChunk(text)


def _parse_sse(raw_chunks: list[bytes]) -> list[tuple[str, dict]]:
    events = []
    for raw in raw_chunks:
        text = raw.decode("utf-8")
        lines = text.strip("\n").split("\n")
        event = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append((event, data))
    return events


def test_stream_chat_response_emits_sources_then_tokens_then_done(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "run_search",
        lambda _request: SearchResponse(
            query="hi", results=[_source()], retrieved_count=1, reranked_count=1
        ),
    )
    monkeypatch.setattr(
        chat_service, "get_chat_model", lambda: _FakeModel(["Hello", " world"])
    )

    request = ChatRequest(query="hi", organization_id="org-1", history=[])
    raw_chunks = list(stream_chat_response(request))
    events = _parse_sse(raw_chunks)

    assert [e for e, _ in events] == ["sources", "token", "token", "done"]

    sources_event = events[0][1]
    assert sources_event["results"][0]["filename"] == "Guide.pdf"

    assert events[1][1] == {"text": "Hello"}
    assert events[2][1] == {"text": " world"}
    assert events[3][1] == {}


def test_stream_chat_response_skips_empty_token_chunks(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "run_search",
        lambda _request: SearchResponse(
            query="hi", results=[], retrieved_count=0, reranked_count=0
        ),
    )
    monkeypatch.setattr(chat_service, "get_chat_model", lambda: _FakeModel(["", "Only this"]))

    request = ChatRequest(
        query="hi",
        organization_id="org-1",
        history=[ChatMessage(role="user", content="earlier turn")],
    )
    events = _parse_sse(list(stream_chat_response(request)))

    token_events = [data for event, data in events if event == "token"]
    assert token_events == [{"text": "Only this"}]
