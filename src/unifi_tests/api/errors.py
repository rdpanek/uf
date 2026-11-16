"""Readable API errors: a failing test should say what was called, what came back and why."""

from __future__ import annotations

import json

import requests

_HINTS = {
    401: "Unauthorized: wrong credentials, missing/expired MFA code, or session logged out.",
    403: "Forbidden: missing CSRF token or the user lacks the permission for this call.",
    404: "Not found: the endpoint may differ in this UniFi OS version (see api/endpoints.py).",
    429: "Rate limited: too many login attempts, wait a minute before re-running.",
}

_CODE_HINTS = {
    "AUTHENTICATION_FAILED_INVALID_CREDENTIALS": (
        "Login refused: wrong username/password, or the MFA code was wrong, expired "
        "or already used (each TOTP code works only once)."
    ),
}

_SECRET_KEYS = {"password", "token", "totp", "x-csrf-token"}


def redact(payload: object) -> object:
    if isinstance(payload, dict):
        return {k: "***" if k.lower() in _SECRET_KEYS else redact(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [redact(v) for v in payload]
    return payload


class UniFiError(AssertionError):
    """HTTP 200, but the UniFi envelope says the call failed (code != 1)."""

    def __init__(self, response: requests.Response, body: dict):
        request = response.request
        super().__init__(
            f"{request.method} {request.url}\n"
            f"  UniFi error {body.get('code')} {body.get('codeS')}: {body.get('msg')}\n"
            f"  detail: {body.get('error', '')}"
        )


class ApiError(AssertionError):
    """Unexpected HTTP status. Subclasses AssertionError so pytest shows it as a test failure."""

    def __init__(self, response: requests.Response, expected: int | tuple[int, ...]):
        self.response = response
        self.status = response.status_code
        request = response.request
        try:
            payload = response.json()
            body = json.dumps(redact(payload), indent=2)[:1500]
        except ValueError:
            payload, body = {}, (response.text or "")[:500]
        code = payload.get("code") if isinstance(payload, dict) else None
        hint = _CODE_HINTS.get(code, "") or _HINTS.get(self.status, "")
        super().__init__(
            f"{request.method} {request.url}\n"
            f"  expected status {expected}, got {self.status} {response.reason}\n"
            + (f"  hint: {hint}\n" if hint else "")
            + f"  response body:\n{body}"
        )
