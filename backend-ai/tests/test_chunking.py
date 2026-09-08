"""Tests for chunking (US-010): token-budgeted, format-aware splitting."""

from __future__ import annotations

from app.indexing import chunking


def test_chunk_text_returns_single_chunk_for_short_text():
    chunks = chunking.chunk_text("Just a short sentence.", "txt")
    assert chunks == ["Just a short sentence."]


def test_chunk_text_empty_returns_no_chunks():
    assert chunking.chunk_text("   ", "txt") == []


def test_chunk_text_respects_token_budget_and_overlap():
    # ~2800 words of repeated text is comfortably over the 1500-token
    # chunk size, so this must split into multiple chunks. The
    # configured 300-token overlap means adjacent chunks repeat some
    # text, so the combined chunk length must exceed the (non-
    # overlapping) source length.
    paragraph = "The quick brown fox jumps over the lazy dog. " * 400
    chunks = chunking.chunk_text(paragraph, "txt")
    assert len(chunks) > 1
    assert sum(len(c) for c in chunks) > len(paragraph)


def test_markdown_chunking_keeps_sections_together():
    markdown = (
        "# Introduction\n\nShort intro text.\n\n"
        "## Details\n\nMore detailed body text that stays under budget.\n"
    )
    chunks = chunking.chunk_text(markdown, "md")
    assert any("Introduction" in c for c in chunks)
    assert any("Details" in c for c in chunks)


# ---------------------------------------------------------------------------
# chunk_pages (Epic 4 / US-019 source attribution: page number per chunk)
# ---------------------------------------------------------------------------


def test_chunk_pages_tags_each_chunk_with_its_source_page():
    pages = [(1, "First page short text."), (2, "Second page short text.")]
    result = chunking.chunk_pages(pages, "txt")
    assert result == [
        (1, "First page short text."),
        (2, "Second page short text."),
    ]


def test_chunk_pages_never_spans_two_pages():
    # Each page individually is long enough to split into multiple
    # chunks; every resulting chunk must carry only its own page's
    # number — none may straddle the page 1/page 2 boundary.
    long_text = "The quick brown fox jumps over the lazy dog. " * 400
    pages = [(1, long_text), (2, long_text)]
    result = chunking.chunk_pages(pages, "txt")

    page_1_chunks = [text for page, text in result if page == 1]
    page_2_chunks = [text for page, text in result if page == 2]
    assert len(page_1_chunks) > 1
    assert len(page_2_chunks) > 1
    assert all(page in (1, 2) for page, _ in result)


def test_chunk_pages_with_no_page_number_for_non_paginated_formats():
    result = chunking.chunk_pages([(None, "Just a short sentence.")], "txt")
    assert result == [(None, "Just a short sentence.")]
