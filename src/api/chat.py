from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from llm.base import LLMProviderError
from llm.ollama_answer_generator import OllamaAnswerGenerator
from llm.ollama_query_parser import OllamaQueryParser
from retrieval import MovieRetriever
from service import MovieAgentResponse, MovieAgentService

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/chat", tags=["chat"])

settings = get_settings()


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        description="Natural language movie question from the user.",
        examples=["Recommend high rated action movies after 2010"],
    )


def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    database_path = settings.database.path
    if not database_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Database file not found: {database_path.resolve()}",
        )

    connection = sqlite3.connect(
        database_path,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row

    try:
        yield connection
    finally:
        connection.close()


@router.post("", response_model=MovieAgentResponse)
async def chat(
    request: ChatRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
) -> MovieAgentResponse:
    logger.info(
        "Received chat request. message_length=%s",
        len(request.message),
    )

    service = MovieAgentService(
        query_parser=OllamaQueryParser(
            model=settings.ollama.model,
            base_url=settings.ollama.base_url,
            timeout_seconds=settings.ollama.timeout_seconds,
        ),
        retriever=MovieRetriever(connection),
        answer_generator=OllamaAnswerGenerator(
            model=settings.ollama.model,
            base_url=settings.ollama.base_url,
            timeout_seconds=settings.ollama.timeout_seconds,
        ),
    )

    try:
        response = await service.answer(request.message)

        logger.info(
            "Chat request completed. intent=%s movie_count=%s",
            response.parsed_query.intent,
            len(response.movies),
        )

        return response

    except LLMProviderError as exc:
        logger.exception("LLM provider failed.")
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except sqlite3.Error as exc:
        logger.exception("Database query failed.")
        raise HTTPException(
            status_code=500,
            detail="Database query failed.",
        ) from exc
