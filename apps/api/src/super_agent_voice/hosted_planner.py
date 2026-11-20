"""Provider-neutral hosted planner behind the planner seam: any OpenAI-compatible chat-completions endpoint.

Cloud model: `is_local` is False, so admission refuses personal data for it. The key is read from the
environment per call and goes only in the Authorization header. Every failure is a ModelError with a fixed
code, never provider text, the key or the prompt.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from .planner import MAX_REPLY_CHARS, ModelError

# Approved recipients only: recipients approved in DEC-24 (docs/approvals/r-a2-cloud-personal-data.md).
# A new host needs a maintainer decision and a code change.
ALLOWED_HOSTS = ("api.openai.com", "integrate.api.nvidia.com")
ATTEMPT_TIMEOUT_S = 20  # per attempt
MAX_RETRIES = 2  # timeout, 429 and 5xx only
BACKOFF_S = (1, 2)  # fixed and short
# Worst case 3 * 20 + 1 + 2 = 63 s, inside the 75 s step deadline in policy.Limits with 12 s of margin.
# A proxy would see the key and the prompt, so the request never uses one.
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # a followed redirect would resend the key to a host outside the allowlist; the 3xx becomes an HTTPError


_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


def _config() -> tuple[str, str, str]:
    """(url, model, key) from the environment, or ModelError('unavailable')."""
    base = os.environ.get("SUPER_AGENT_PLANNER_BASE_URL", "")
    model = os.environ.get("SUPER_AGENT_PLANNER_MODEL", "")
    key_env = os.environ.get("SUPER_AGENT_PLANNER_KEY_ENV", "")
    key = os.environ.get(key_env, "") if key_env else ""
    try:
        parts = urllib.parse.urlsplit(base)
        ok = (parts.scheme == "https" and parts.hostname in ALLOWED_HOSTS and parts.port in (None, 443) and parts.username is None
              and parts.password is None and not parts.query and not parts.fragment)
    except ValueError:
        ok = False
    if not ok or not model or not key or not key.isascii() or not key.isprintable():
        raise ModelError("unavailable")
    return base.rstrip("/") + "/chat/completions", model, key


class HostedPlanner:
    @property
    def is_local(self) -> bool:
        return False

    def _text(self, prompt: str, json_mode: bool) -> str:
        if type(prompt) is not str:
            raise ModelError("malformed")
        url, model, key = _config()
        body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        request = urllib.request.Request(
            url, json.dumps(body).encode(), {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        code = "unavailable"
        for attempt in range(MAX_RETRIES + 1):
            if attempt:
                time.sleep(BACKOFF_S[attempt - 1])
            try:
                with _DIRECT.open(request, timeout=ATTEMPT_TIMEOUT_S) as response:
                    raw = response.read(MAX_REPLY_CHARS * 4 + 4096)  # bytes cap: a worst-case char is 4 UTF-8 bytes
                break
            except urllib.error.HTTPError as error:
                code = "unavailable"
                if error.code != 429 and error.code < 500:
                    raise ModelError("unavailable") from None
            except TimeoutError:
                code = "timeout"
            except Exception as error:  # URLError wraps a socket timeout in .reason
                code = "timeout" if isinstance(getattr(error, "reason", None), TimeoutError) else "unavailable"
        else:
            raise ModelError(code)
        try:
            text = json.loads(raw)["choices"][0]["message"]["content"]
        except Exception:
            raise ModelError("malformed") from None
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
