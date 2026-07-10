"""
Cloudflare Workers AI — LangChain BaseChatModel adapter.

Cloudflare Workers AI exposes an OpenAI-compatible chat completions endpoint:

    POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions

This module wraps that endpoint as a ``BaseChatModel`` so it can be dropped
into any LangChain / LangGraph pipeline that accepts a ``BaseChatModel``.

Usage::

    from chatbot.llm_cloudflare import CloudflareWorkersAI

    llm = CloudflareWorkersAI(
        account_id="dfb9d63df5777b67de01527fcf37ce62",
        api_token="cfut_...",
        model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    )
    response = llm.invoke([HumanMessage(content="SELECT 1 in SQL")])
    print(response.content)
"""

from __future__ import annotations

from typing import Any, Iterator, List, Optional, Sequence

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

# Cloudflare Workers AI base URL pattern
_CF_BASE_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"


def _messages_to_cf(messages: Sequence[BaseMessage]) -> list[dict]:
    """Convert LangChain messages to the OpenAI-compatible dict format."""
    result = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        else:
            role = "user"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        result.append({"role": role, "content": content})
    return result


class CloudflareWorkersAI(BaseChatModel):
    """LangChain BaseChatModel backed by Cloudflare Workers AI.

    Attributes:
        account_id: Cloudflare account ID.
        api_token: Cloudflare AI Gateway token (``cfut_...``).
        model: Model name, e.g. ``@cf/meta/llama-3.3-70b-instruct-fp8-fast``.
        temperature: Sampling temperature (0–2). Defaults to 0 for deterministic SQL.
        max_tokens: Maximum tokens in the response. Defaults to 2048.
        timeout: HTTP request timeout in seconds. Defaults to 60.
    """

    account_id: str
    api_token: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 2048
    timeout: float = 60.0

    @property
    def _llm_type(self) -> str:
        return "cloudflare-workers-ai"

    @property
    def _base_url(self) -> str:
        return _CF_BASE_URL.format(account_id=self.account_id)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Call the Cloudflare Workers AI endpoint and return a ChatResult."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _messages_to_cf(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if stop:
            payload["stop"] = stop

        url = f"{self._base_url}/chat/completions"

        try:
            response = httpx.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Cloudflare Workers AI returned HTTP {exc.response.status_code}: "
                f"{exc.response.text}"
            ) from exc
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise RuntimeError(
                f"Cloudflare Workers AI connectivity error: {exc}"
            ) from exc

        data = response.json()

        # Parse OpenAI-compatible response shape
        try:
            content: str = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(
                f"Unexpected Cloudflare Workers AI response shape: {data}"
            ) from exc

        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    # ------------------------------------------------------------------
    # Required abstract method — streaming (basic pass-through)
    # ------------------------------------------------------------------

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Streaming is not used by GlassBot — delegates to _generate."""
        result = self._generate(messages, stop=stop, **kwargs)
        content = result.generations[0].message.content
        yield ChatGenerationChunk(message=AIMessageChunk(content=content))
