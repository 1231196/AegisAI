"""Chunking (US-010): format-aware, token-budgeted splitting.

Markdown gets a header-aware pass first — split on ``#``/``##``/``###``
so each chunk stays inside one logical section — with the token-budget
splitter then applied within any section that's still oversized.
Every other format goes straight through the token-budget splitter.

1500 tokens/chunk with 300 tokens overlap (20%) — the concrete pick
within the "1200-1800 tokens, 15-25% overlap" range.
"""

from __future__ import annotations

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.config import settings
from app.indexing.parsers import PageText

_HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def _token_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=settings.chunk_size_tokens,
        chunk_overlap=settings.chunk_overlap_tokens,
    )


def chunk_text(text: str, file_type: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    splitter = _token_splitter()

    if file_type == "md":
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=_HEADERS_TO_SPLIT_ON,
            strip_headers=False,
        )
        sections = header_splitter.split_text(text)
        if not sections:
            return splitter.split_text(text)
        chunks: list[str] = []
        for section in sections:
            chunks.extend(splitter.split_text(section.page_content))
        return chunks

    return splitter.split_text(text)


def chunk_pages(pages: list[PageText], file_type: str) -> list[tuple[int | None, str]]:
    """Chunk each page independently and tag each resulting chunk with
    its source page number (Epic 4 / US-019 source attribution).

    Chunking per-page rather than over the whole joined document means
    a chunk can never span two pages — exact page attribution, at the
    (usually negligible) cost of occasionally splitting a paragraph
    that straddles a page break slightly earlier than the token
    budget would otherwise call for.
    """
    result: list[tuple[int | None, str]] = []
    for page_number, text in pages:
        for chunk in chunk_text(text, file_type):
            result.append((page_number, chunk))
    return result
