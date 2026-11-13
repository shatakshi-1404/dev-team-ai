"""Call the LLM and validate the structured output; retry once with the validation error."""

from __future__ import annotations

import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.provider import LLMProvider

log = logging.getLogger("devteam.agents")
T = TypeVar("T", bound=BaseModel)


class AgentOutputError(Exception):
    pass


def untrusted(text: str) -> str:
    """Wrap untrusted data so the model can tell it apart from instructions."""
    return "<untrusted>\n" + text.replace("</untrusted>", "</ untrusted>") + "\n</untrusted>"


def run_agent(llm: LLMProvider, system: str, user: str, model: type[T]) -> T:
    schema = json.dumps(model.model_json_schema())
    full_system = f"{system}\n\nReturn JSON matching this JSON Schema exactly:\n{schema}"
    prompt = user
    last_error = ""
    for attempt in range(2):
        raw = llm.complete_json(full_system, prompt)
        try:
            return model.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)[:1500]
            log.warning("agent output invalid", extra={"attempt": attempt, "model": model.__name__})
            prompt = f"{user}\n\nYour previous reply was invalid: {last_error}\nReturn corrected JSON only."
    raise AgentOutputError(f"{model.__name__}: model did not return valid structured output ({last_error[:300]})")
