"""Process-wide lock serializing every call into a native ML inference
library in this service — torch/sentence-transformers (dense
embeddings, reranking), fastembed's ONNX runtime (sparse embeddings),
and paddleocr.

Origin: indexing (US-008..US-013) discovered that running paddle's and
torch's native inference engines concurrently in separate threads of
the same process reliably deadlocks the whole worker — no crash, no
exception, the process just stops responding to anything, including
unauthenticated health checks. Retrieval (Epic 4) and chat (Epic 5)
hit the same class of failure once a chat request and a second
concurrent request (another chat, a search, anything touching a
model) overlapped: the *entire* service went unresponsive, confirmed
by a plain ``GET /`` hanging past its timeout.

The exact safe/unsafe pairings were never narrowed down beyond "two
native engines running at once in this process" — rather than prove
which specific combinations are actually safe, every code path that
touches a model acquires this one lock. That serializes throughput
(the whole service processes one model-touching request at a time)
in exchange for never silently hanging the whole process again. A
future fix (running OCR in its own subprocess, or verifying these
libraries' thread-safety guarantees together) could relax this.

Deliberately excludes the LLM call in chat (``app/chat/llm.py``) —
that's a plain HTTP client (google-genai), not a native inference
engine, so concurrent chat *generation* (as opposed to the retrieval
step that precedes it) is not serialized by this lock.
"""

from __future__ import annotations

import threading

MODEL_LOCK = threading.Lock()
