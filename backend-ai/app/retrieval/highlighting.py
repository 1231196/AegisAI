"""Highlighted excerpts (US-019).

Naive but effective, with no external NLP dependency: split the chunk
into sentences, score each individually by how many distinct query
terms it contains, then take a small window *centered* on the single
best-matching sentence (one sentence of context on either side,
clipped to the text's bounds) and wrap matched terms in ``<mark>``
tags. Good enough for "show me why this chunk matched" — not intended
as a general-purpose summariser.

Centering on the best sentence rather than sliding a fixed window
left-to-right avoids drifting the excerpt toward irrelevant text when
two windows happen to tie on total match count (e.g. a lone strong
match sitting in the middle of the chunk) — the sentence with the
match is always inside the window, not just the window with the
highest count.
"""

from __future__ import annotations

import re

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"\w+")
_CONTEXT_SENTENCES = 1  # sentences of context on each side of the best match
_FALLBACK_EXCERPT_CHARS = 300


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _WORD_RE.findall(text) if len(t) > 2}


def build_excerpt(query: str, text: str) -> str:
    text = text.strip()
    query_terms = _tokenize(query)
    if not query_terms or not text:
        return _highlight(text[:_FALLBACK_EXCERPT_CHARS], query_terms)

    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if not sentences:
        return _highlight(text[:_FALLBACK_EXCERPT_CHARS], query_terms)

    scores = [len(_tokenize(s) & query_terms) for s in sentences]
    best_index = max(range(len(sentences)), key=lambda i: scores[i])

    window_start = max(0, best_index - _CONTEXT_SENTENCES)
    window_end = min(len(sentences), best_index + _CONTEXT_SENTENCES + 1)
    window = sentences[window_start:window_end]
    return _highlight(" ".join(window), query_terms)


def _highlight(text: str, query_terms: set[str]) -> str:
    if not query_terms:
        return text

    def _wrap(match: re.Match) -> str:
        word = match.group(0)
        return f"<mark>{word}</mark>" if word.lower() in query_terms else word

    return _WORD_RE.sub(_wrap, text)
