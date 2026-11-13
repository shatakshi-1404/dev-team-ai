"""LLM provider interface. Groq (via LangChain) is the default; the app starts without a key."""

from __future__ import annotations

from typing import Protocol

from app.config import get_settings


class LLMNotConfigured(Exception):
    """Raised when an LLM call is attempted without a configured provider/key."""


class LLMProvider(Protocol):
    def complete_json(self, system: str, user: str) -> str: ...


class GroqProvider:
    def complete_json(self, system: str, user: str) -> str:
        s = get_settings()
        if not s.llm_configured:
            raise LLMNotConfigured("GROQ_API_KEY is not set. Add it to backend/.env and restart the backend.")
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            model=s.groq_model,
            api_key=s.groq_api_key,
            temperature=s.llm_temperature,
            timeout=s.llm_timeout_seconds,
            max_retries=2,
        )
        llm = llm.bind(response_format={"type": "json_object"})
        msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return msg.content if isinstance(msg.content, str) else str(msg.content)


def get_provider() -> LLMProvider:
    name = get_settings().llm_provider.lower()
    if name == "groq":
        return GroqProvider()
    raise LLMNotConfigured(f"Unsupported LLM_PROVIDER '{name}'. Only 'groq' is implemented.")
