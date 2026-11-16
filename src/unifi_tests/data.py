"""Test data builders. Every test gets its own unique local user, so tests are independent."""

from __future__ import annotations

import secrets
import string
import uuid
from dataclasses import dataclass, field


def _strong_password(length: int = 16) -> str:
    # Guarantee each character class UniFi OS password rules usually require.
    pools = [string.ascii_lowercase, string.ascii_uppercase, string.digits, "!@#%^*-_"]
    chars = [secrets.choice(pool) for pool in pools]
    chars += [secrets.choice("".join(pools)) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


@dataclass
class LocalUser:
    """A local (non UI-account) UniFi OS user."""

    first_name: str
    last_name: str
    username: str
    password: str
    email: str
    id: str | None = field(default=None, compare=False)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"LocalUser(username={self.username!r}, id={self.id!r})"


def new_local_user(password: str | None = None, prefix: str = "qa") -> LocalUser:
    suffix = uuid.uuid4().hex[:8]
    return LocalUser(
        first_name="QA",
        last_name=f"Auto {suffix}",
        username=f"{prefix}_{suffix}",
        password=password or _strong_password(),
        email=f"{prefix}.{suffix}@example.com",
    )
