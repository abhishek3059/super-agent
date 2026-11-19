"""Local Ollama model behind the planner seam (agent-backend design, section 10 item 7).

Reuses local_adapter's request builder and remote-model refusal, so the same model the voice loop uses
plans the job. `is_local` is True only when that check passes; any doubt is False and admission then
refuses personal data. The reply is untrusted: planner.py validates it. Every failure is a ModelError.
"""
from __future__ import annotations

import json

from .planner import MAX_REPLY_CHARS, ModelError

TIMEOUT_S = 25  # inside the 30 s step deadline in policy.Limits


class OllamaPlanner:
    @property
    def is_local(self) -> bool:
        from . import local_adapter  # lazy: local_adapter imports delegation, which imports planner

        try:
            local_adapter._refuse_remote_model(local_adapter.local_model())
            return True
        except Exception:
            return False

    def _text(self, prompt: str, json_reply: bool) -> str:
        from . import local_adapter

        if type(prompt) is not str:
            raise ModelError("malformed")
        try:
            request = local_adapter._chat_request([{"role": "user", "content": prompt}], tools=False,
                                                  stream=False, json_reply=json_reply)
            with local_adapter._DIRECT.open(request, timeout=TIMEOUT_S) as response:
                text = json.loads(response.read())["message"]["content"]
        except Exception as error:
            timed_out = isinstance(error, TimeoutError) or "timed out" in str(error).lower()
            raise ModelError("timeout" if timed_out else "unavailable") from None
        if type(text) is not str or not text.strip() or len(text) > MAX_REPLY_CHARS:
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
