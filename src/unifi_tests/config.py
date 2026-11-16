"""Test configuration loaded from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when a required setting is missing, with a hint how to fix it."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing environment variable {name}. "
            "Copy .env.example to .env and fill it in (see README, section Configuration)."
        )
    return value


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str
    totp_secret: str | None = None

    def __repr__(self) -> str:  # never leak secrets into logs or reports
        totp = "set" if self.totp_secret else "none"
        return f"Credentials(username={self.username!r}, password=***, totp={totp})"


@dataclass(frozen=True)
class Settings:
    base_url: str
    admin: Credentials
    local_user_password: str | None
    verify_tls: bool

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        return cls(
            base_url=_required("UNIFI_BASE_URL").rstrip("/"),
            admin=Credentials(
                username=_required("UNIFI_ADMIN_USERNAME"),
                password=_required("UNIFI_ADMIN_PASSWORD"),
                totp_secret=os.getenv("UNIFI_ADMIN_TOTP_SECRET") or None,
            ),
            local_user_password=os.getenv("UNIFI_LOCAL_USER_PASSWORD") or None,
            verify_tls=_flag("UNIFI_VERIFY_TLS", default=False),
        )
