"""Gemini text model behind the planner seam (agent-backend design, section 10 item 7).

Cloud model: `is_local` is False and read-only, so admission refuses it for personal data. The key and the
prompt never reach an exception message or a log. Every failure is a ModelError with a fixed code.
"""
from __future__ import annotations

import json

from .planner import MAX_REPLY_CHARS, ModelError

TIMEOUT_S = 20  # inside the 30 s step deadline in policy.Limits, so the model call fails before the step does
_BASE_URL = "https://generativelanguage.googleapis.com"  # Developer API, never Vertex (same as gemini_adapter)


def _sdk_client(api_key: str):
    from google import genai  # load only when a real call is made
    from google.genai import types

    return genai.Client(api_key=api_key, enterprise=False, http_options=types.HttpOptions(base_url=_BASE_URL))


class GeminiPlanner:
    def __init__(self, api_key: str, model: str, client=None):
        if not isinstance(api_key, str) or not api_key or not isinstance(model, str) or not model:
            raise ModelError("unavailable")
        self._model = model
        try:
            self._client = client if client is not None else _sdk_client(api_key)
        except Exception:
            raise ModelError("unavailable") from None

    @property
    def is_local(self) -> bool:
        return False

    def _text(self, prompt: str, json_mode: bool) -> str:
        if type(prompt) is not str:
            raise ModelError("malformed")
        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                response_mime_type="application/json" if json_mode else "text/plain",
                http_options=types.HttpOptions(timeout=TIMEOUT_S * 1000),  # milliseconds
            )
            text = self._client.models.generate_content(model=self._model, contents=prompt, config=config).text
        except Exception as error:
            timed_out = isinstance(error, TimeoutError) or "Timeout" in type(error).__name__
            raise ModelError("timeout" if timed_out else "unavailable") from None
        if type(text) is not str or not text.strip() or len(text) > MAX_REPLY_CHARS:  # blocked, empty or oversized
            raise ModelError("malformed")
        return text

    def complete(self, prompt: str) -> object:
        try:
            return json.loads(self._text(prompt, True))
        except ModelError:
            raise
        except Exception:  # ValueError, RecursionError
            raise ModelError("malformed") from None

    def complete_text(self, prompt: str) -> object:
        return self._text(prompt, False)
