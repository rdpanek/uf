"""Multi-factor authentication helpers (TOTP from an authenticator-app secret)."""

from __future__ import annotations

import logging
import time

import pyotp

log = logging.getLogger("unifi.mfa")

# A TOTP code is accepted only once (replay protection), so remember the last time step
# used per secret and never send the same code twice.
_last_used_step: dict[str, int] = {}

MIN_SECONDS_LEFT = 5


def current_totp(secret: str) -> str:
    """Return a fresh TOTP code that was not used before and will not expire in transit.

    Waits for the next 30 s window when the current one is about to expire or its code
    was already used by a previous login.
    """
    secret = secret.replace(" ", "").upper()
    totp = pyotp.TOTP(secret)
    while True:
        now = time.time()
        step = int(now // totp.interval)
        seconds_left = totp.interval - (now % totp.interval)
        if step != _last_used_step.get(secret) and seconds_left >= MIN_SECONDS_LEFT:
            _last_used_step[secret] = step
            return totp.at(now)
        log.info("waiting %.0f s for a fresh MFA code", seconds_left)
        time.sleep(seconds_left + 0.5)
