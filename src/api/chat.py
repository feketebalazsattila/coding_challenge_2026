from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from llm.base import LLMProviderError
from llm.ollama_answer_generator import OllamaAnswerGenerator
from llm.ollama_query_parser import OllamaQueryParser
from retrieval import MovieRetriever
from service import MovieAgentResponse, MovieAgentService


router = APIRouter(prefix="/chat", tags=["chat"])


DATABASE_PATH = Path("data/movies.sqlite")
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:e2b"


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        description="Natural language movie question from the user.",
        examples=["Recommend high rated action movies after 2010"],
    )


def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    if not DATABASE_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Database file not found: {DATABASE_PATH.resolve()}",
        )

    connection = sqlite3.connect(
        DATABASE_PATH,
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
    service = MovieAgentService(
        query_parser=OllamaQueryParser(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            timeout_seconds=300.0
        ),
        retriever=MovieRetriever(connection),
        answer_generator=OllamaAnswerGenerator(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            timeout_seconds=300.0
        ),
    )

    try:
        return await service.answer(request.message)

    except LLMProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=500,
            detail="Database query failed.",
        ) from exc