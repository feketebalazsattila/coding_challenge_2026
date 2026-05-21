from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.chat import router as chat_router
from config import get_settings
from logging_config import setup_logging

settings = get_settings()
setup_logging(
    log_level=settings.logging.level,
    log_file=settings.logging.file,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Movie Agent API is starting.")
    yield
    logger.info("Movie Agent API is stopping.")


app = FastAPI(
    title=settings.app.title,
    lifespan=lifespan,
)

app.include_router(chat_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.app.root_message}
