"""RAG prompt construction (Epic 5).

Builds the message list handed to the LLM: a system message
instructing it to answer from the retrieved context (and say so
plainly when it can't), the conversation history so far, then the new
query as the final message.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.retrieval.schemas import SourceResult

_SYSTEM_TEMPLATE = """You are Aegis AI, an enterprise support assistant. Answer the user's question using ONLY the context below, drawn from the organisation's knowledge base. If the context doesn't contain the answer, say so plainly instead of guessing. When you use a fact from a source, mention its filename (and page number, if given) so the user can verify it.

Context:
{context}"""


def _format_context(sources: list[SourceResult]) -> str:
    if not sources:
        return "(no relevant sources were found for this question)"
    blocks = []
    for i, source in enumerate(sources, start=1):
        location = source.filename
        if source.page_number is not None:
            location += f", page {source.page_number}"
        blocks.append(f"[{i}] {location}\n{source.text}")
    return "\n\n".join(blocks)


def build_messages(
    query: str,
    history: list[dict],
    sources: list[SourceResult],
) -> list[BaseMessage]:
    messages: list[BaseMessage] = [
        SystemMessage(content=_SYSTEM_TEMPLATE.format(context=_format_context(sources)))
    ]
    for turn in history:
        if turn["role"] == "assistant":
            messages.append(AIMessage(content=turn["content"]))
        else:
            messages.append(HumanMessage(content=turn["content"]))
    messages.append(HumanMessage(content=query))
    return messages
