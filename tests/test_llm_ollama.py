from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from llm.base import AnswerGenerationError, QueryParsingError
from llm.ollama_answer_generator import OllamaAnswerGenerator
from llm.ollama_query_parser import OllamaQueryParser
from query_processing import QueryIntent, SortBy


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str = "OK") -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://ollama.test/api/chat")
            response = httpx.Response(
                self.status_code,
                request=request,
                text=self.text,
            )
            raise httpx.HTTPStatusError(
                "error response",
                request=request,
                response=response,
            )


class FakeAsyncClient:
    posts: list[dict] = []
    response: FakeResponse | None = None
    error: Exception | None = None
    timeout: float | None = None

    def __init__(self, timeout: float) -> None:
        type(self).timeout = timeout

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, json: dict) -> FakeResponse:
        type(self).posts.append({"url": url, "json": json})
        if type(self).error is not None:
            raise type(self).error
        if type(self).response is None:
            raise AssertionError("FakeAsyncClient.response was not configured.")
        return type(self).response


@pytest.fixture(autouse=True)
def reset_fake_async_client(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.posts = []
    FakeAsyncClient.response = None
    FakeAsyncClient.error = None
    FakeAsyncClient.timeout = None
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)


def test_query_parser_posts_schema_and_validates_response() -> None:
    content = {
        "intent": "recommend_movies",
        "genres": ["Action"],
        "year_from": 2010,
        "min_rating": 4.0,
        "sort_by": "rating_desc",
        "limit": 3,
        "confidence": 0.9,
    }
    FakeAsyncClient.response = FakeResponse(
        {"message": {"content": json.dumps(content)}}
    )
    parser = OllamaQueryParser(
        model="test-model",
        base_url="http://ollama.test/",
        timeout_seconds=12.5,
    )

    parsed = asyncio.run(parser.parse("Recommend 3 top action movies after 2010"))

    assert parsed.intent == QueryIntent.RECOMMEND_MOVIES
    assert parsed.genres == ["Action"]
    assert parsed.year_from == 2010
    assert parsed.min_rating == 4.0
    assert parsed.sort_by == SortBy.RATING_DESC
    assert parsed.limit == 3
    assert FakeAsyncClient.timeout == 12.5
    assert FakeAsyncClient.posts[0]["url"] == "http://ollama.test/api/chat"

    payload = FakeAsyncClient.posts[0]["json"]
    assert payload["model"] == "test-model"
    assert payload["stream"] is False
    assert payload["options"] == {"temperature": 0.0}
    assert payload["format"]["title"] == "ParsedMovieQuery"
    assert payload["messages"][1] == {
        "role": "user",
        "content": "Recommend 3 top action movies after 2010",
    }


def test_query_parser_rejects_invalid_llm_json() -> None:
    FakeAsyncClient.response = FakeResponse(
        {"message": {"content": json.dumps({"intent": "not_an_intent"})}}
    )
    parser = OllamaQueryParser(
        model="test-model",
        base_url="http://ollama.test",
        timeout_seconds=60.0,
    )

    with pytest.raises(QueryParsingError, match="does not match ParsedMovieQuery"):
        asyncio.run(parser.parse("Find movies"))


def test_query_parser_rejects_empty_message_without_calling_ollama() -> None:
    parser = OllamaQueryParser(
        model="test-model",
        base_url="http://ollama.test",
        timeout_seconds=60.0,
    )

    with pytest.raises(QueryParsingError, match="empty user message"):
        asyncio.run(parser.parse("   "))

    assert FakeAsyncClient.posts == []


def test_answer_generator_posts_prompt_and_returns_stripped_content() -> None:
    FakeAsyncClient.response = FakeResponse(
        {"message": {"content": "  Try The Matrix for stylish sci-fi action.  "}}
    )
    generator = OllamaAnswerGenerator(
        model="answer-model",
        base_url="http://ollama.test/",
        timeout_seconds=8.0,
    )

    answer = asyncio.run(
        generator.generate(
            question="What should I watch?",
            context="The Matrix | 1999 | Action, Sci-Fi | Rating 8.7",
        )
    )

    assert answer == "Try The Matrix for stylish sci-fi action."
    assert FakeAsyncClient.timeout == 8.0
    assert FakeAsyncClient.posts[0]["url"] == "http://ollama.test/api/chat"

    payload = FakeAsyncClient.posts[0]["json"]
    assert payload["model"] == "answer-model"
    assert payload["stream"] is False
    assert payload["options"] == {"temperature": 0.3}
    assert payload["messages"][1]["role"] == "user"
    assert "What should I watch?" in payload["messages"][1]["content"]
    assert "The Matrix | 1999" in payload["messages"][1]["content"]


def test_answer_generator_wraps_http_status_errors() -> None:
    FakeAsyncClient.response = FakeResponse(
        {"error": "missing model"},
        status_code=404,
        text="model not found",
    )
    generator = OllamaAnswerGenerator(
        model="answer-model",
        base_url="http://ollama.test",
        timeout_seconds=60.0,
    )

    with pytest.raises(AnswerGenerationError, match="failed with status 404"):
        asyncio.run(generator.generate("Recommend a movie", "Movie context"))


def test_answer_generator_rejects_empty_context_without_calling_ollama() -> None:
    generator = OllamaAnswerGenerator(
        model="answer-model",
        base_url="http://ollama.test",
        timeout_seconds=60.0,
    )

    with pytest.raises(AnswerGenerationError, match="without movie context"):
        asyncio.run(generator.generate("Recommend a movie", "   "))

    assert FakeAsyncClient.posts == []
