from __future__ import annotations

from typing import Any

import httpx

from llm.base import AnswerGenerationError

ANSWER_SYSTEM_PROMPT = """
You are a helpful conversational movie assistant.

Your task is to answer the user's question using only the provided movie
database context.

Important rules:
- Use only the movie data provided in the context.
- Do not invent movies, ratings, directors, actors, genres, or plot details.
- If the context says no matching movies were found, say that clearly.
- If some fields are unknown or missing, do not guess them.
- Keep the answer concise, friendly, and useful.
- When recommending multiple movies, briefly explain why each movie matches the request.
"""


class OllamaAnswerGenerator:
    """
    Generates the final conversational answer using Ollama.

    This class performs the second LLM call in the application pipeline.

    It does not retrieve movies.
    It does not parse user intent.
    It only turns retrieved movie context into a natural language answer.
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

    async def generate(self, question: str, context: str) -> str:
        if not question.strip():
            raise AnswerGenerationError(
                "Cannot generate an answer for an empty question."
            )

        if not context.strip():
            raise AnswerGenerationError(
                "Cannot generate an answer without movie context."
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": ANSWER_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": self._build_user_prompt(
                        question=question,
                        context=context,
                    ),
                },
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()

            return self._extract_message_content(response.json())

        except httpx.TimeoutException as exc:
            raise AnswerGenerationError(
                "Ollama answer generation timed out after "
                f"{self.timeout_seconds} seconds. "
                "The model may be too slow on CPU or the context may be too long."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise AnswerGenerationError(
                f"Ollama answer generation failed with status "
                f"{exc.response.status_code}: {exc.response.text}"
            ) from exc

        except httpx.RequestError as exc:
            raise AnswerGenerationError(
                f"Could not connect to Ollama at {self.base_url}. Original error: {exc}"
            ) from exc

        except (KeyError, TypeError) as exc:
            raise AnswerGenerationError(
                "Ollama returned an unexpected answer response format."
            ) from exc

    def _build_user_prompt(self, question: str, context: str) -> str:
        return f"""
User question:
{question}

Movie database context:
{context}

Write the final answer for the user.
""".strip()

    def _extract_message_content(self, response_json: dict[str, Any]) -> str:
        content = response_json["message"]["content"]

        if not isinstance(content, str) or not content.strip():
            raise AnswerGenerationError(
                "Ollama returned an empty answer generation response."
            )

        return content.strip()
