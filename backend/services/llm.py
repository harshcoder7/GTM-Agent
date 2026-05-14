"""OpenAI wrapper — reads the API key from runtime_config (UI-set) on every
call so updates take effect immediately without a backend restart.
"""
from __future__ import annotations
from typing import Type, TypeVar, AsyncIterator
from pydantic import BaseModel
from openai import AsyncOpenAI
from config import settings
from services import runtime_config

T = TypeVar("T", bound=BaseModel)


def _client() -> AsyncOpenAI:
    key = runtime_config.openai_api_key()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not configured (set it in /settings or .env)")
    return AsyncOpenAI(api_key=key)


async def chat(system: str, user: str, *, model: str | None = None, temperature: float = 0.3) -> str:
    resp = await _client().chat.completions.create(
        model=model or settings.openai_fast_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


async def chat_stream(system: str, user: str, *, model: str | None = None, temperature: float = 0.5) -> AsyncIterator[str]:
    stream = await _client().chat.completions.create(
        model=model or settings.openai_reasoning_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def structured(system: str, user: str, schema: Type[T], *, model: str | None = None, temperature: float = 0.2) -> T:
    resp = await _client().beta.chat.completions.parse(
        model=model or settings.openai_fast_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format=schema,
        temperature=temperature,
    )
    parsed = resp.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("LLM returned no parsed object")
    return parsed
