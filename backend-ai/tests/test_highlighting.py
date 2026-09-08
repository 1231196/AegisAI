"""Tests for highlighted excerpts (Epic 4 / US-019)."""

from __future__ import annotations

from app.retrieval.highlighting import build_excerpt


def test_build_excerpt_highlights_matched_query_terms():
    text = "Docker Compose is a tool for defining multi-container applications."
    excerpt = build_excerpt("docker compose", text)
    assert "<mark>Docker</mark>" in excerpt
    assert "<mark>Compose</mark>" in excerpt


def test_build_excerpt_is_case_insensitive():
    text = "The PAYMENT gateway rejected the transaction."
    excerpt = build_excerpt("payment gateway", text)
    assert "<mark>PAYMENT</mark>" in excerpt


def test_build_excerpt_picks_best_matching_sentence_window():
    text = (
        "This sentence is about the weather today. "
        "This sentence is about something else entirely. "
        "Docker Compose defines multi-container applications here. "
        "Another unrelated sentence about gardening follows."
    )
    excerpt = build_excerpt("docker compose applications", text)
    assert "<mark>Docker</mark>" in excerpt
    assert "<mark>Compose</mark>" in excerpt
    assert "multi-container" in excerpt
    assert "weather" not in excerpt


def test_build_excerpt_handles_empty_query():
    text = "Some chunk text with no query to match against."
    excerpt = build_excerpt("", text)
    assert "<mark>" not in excerpt
    assert excerpt.startswith("Some chunk text")
