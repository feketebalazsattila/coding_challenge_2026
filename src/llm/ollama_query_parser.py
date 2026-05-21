from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import ValidationError

from llm.base import QueryParsingError
from query_processing import ParsedMovieQuery

QUERY_PARSER_SYSTEM_PROMPT = """
You are a query parser for a movie REST API.

Your task is to convert the user's natural language message into a structured
movie query object.

Important rules:
- Do not answer the user's question.
- Do not generate SQL.
- Do not invent movie titles, directors, actors, genres, years, or ratings.
- Only extract filters that are explicitly stated or strongly implied.
- Return only a JSON object that matches the provided schema.
- Do not include markdown, explanations, or comments.

Intent rules:
- Use "movie_lookup" when the user asks about one specific movie.
- Use "recommend_movies" when the user asks for recommendations.
- Use "search_movies" for general movie search requests.
- Use "search_by_director" when the user asks for movies by a director.
- Use "search_by_actor" when the user asks for movies with a specific actor.
- Use "top_rated" when the user asks for best, top, or highest-rated movies.
- Use "unknown" if the request is not movie-related or cannot be understood.

Rating rules:
- If the user asks for "best", "top", "highest rated", or "high rated",
  set min_rating to 4.0 and sort_by to "rating_desc".

Limit rules:
- If the user asks for a specific number of movies, use that as limit.
- Otherwise use limit 5.
- Limit must be between 1 and 20.

Clarification rules:
- If the query is too vague to retrieve useful movies, set needs_clarification to true.
- If needs_clarification is true, provide a short clarification_question.
"""


class OllamaQueryParser:
    """
    Parses natural language movie questions into ParsedMovieQuery using Ollama.

    This class performs the first LLM call in the application pipeline.

    It does not generate SQL.
    It does not retrieve movies.
    It only converts the user message into a validated ParsedMovieQuery object.
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def parse(self, message: str) -> ParsedMovieQuery:
        if not message.strip():
            raise QueryParsingError("Cannot parse an empty user message.")

        schema = ParsedMovieQuery.model_json_schema()

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self._build_system_prompt(schema),
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0.0,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()

            content = self._extract_message_content(response.json())
            return ParsedMovieQuery.model_validate_json(content)

        except httpx.HTTPError as exc:
            raise QueryParsingError("Ollama query parser request failed.") from exc

        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise QueryParsingError(
                "Ollama returned an unexpected response format."
            ) from exc

        except ValidationError as exc:
            raise QueryParsingError(
                "Ollama returned JSON that does not match ParsedMovieQuery."
            ) from exc

    def _build_system_prompt(self, schema: dict[str, Any]) -> str:
        return (
            QUERY_PARSER_SYSTEM_PROMPT
            + "\n\nJSON schema to follow:\n"
            + json.dumps(schema, indent=2)
        )

    def _extract_message_content(self, response_json: dict[str, Any]) -> str:
        content = response_json["message"]["content"]

        if not isinstance(content, str) or not content.strip():
            raise QueryParsingError("Ollama returned an empty query parser response.")

        return content
