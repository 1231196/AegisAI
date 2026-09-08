import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.chat.router import router as chat_router
from app.indexing.router import router as indexing_router
from app.indexing.vector_store import ensure_collection
from app.retrieval.router import router as retrieval_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Boot-time setup: make sure the Qdrant collection exists before
    the first /index request tries to upsert into it."""
    ensure_collection()
    yield


app = FastAPI(title="OpsPilot AI Module", lifespan=lifespan)


@app.get("/")
def root():
    return {
        "service": "backend-ai",
        "status": "ok"
    }


app.include_router(indexing_router)
app.include_router(retrieval_router)
app.include_router(chat_router)
