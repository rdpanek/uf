"""Shared fixtures for API and E2E tests."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator

import pytest

from unifi_tests.api.client import UniFiOSClient
from unifi_tests.config import ConfigError, Settings
from unifi_tests.data import LocalUser, new_local_user

log = logging.getLogger("unifi.fixtures")


@pytest.fixture(scope="session")
def settings() -> Settings:
    try:
        return Settings.from_env()
    except ConfigError as exc:
        pytest.exit(str(exc), returncode=2)


@pytest.fixture
def api(settings: Settings) -> UniFiOSClient:
    """A fresh, not-logged-in API client (one per test, no shared cookies)."""
    return UniFiOSClient(settings.base_url, verify_tls=settings.verify_tls)


@pytest.fixture(scope="session")
def cleanup_admin(settings: Settings) -> Iterator[UniFiOSClient]:
    """One admin session for the whole run, used only for cleanup.

    Logging in once saves MFA codes (each code can be used only once) and avoids rate limits.
    """
    admin = UniFiOSClient(settings.base_url, verify_tls=settings.verify_tls)
    yield admin
    if admin.is_authenticated():
        admin.logout()


@pytest.fixture
def local_user_factory(
    settings: Settings, cleanup_admin: UniFiOSClient
) -> Iterator[Callable[[], LocalUser]]:
    """Build unique local users and delete every one of them after the test,
    whatever the test outcome (cleanup goes through its own admin session)."""
    created: list[LocalUser] = []

    def factory() -> LocalUser:
        user = new_local_user(password=settings.local_user_password)
        created.append(user)
        return user

    yield factory

    if not created:
        return
    try:
        if not cleanup_admin.is_authenticated():
            cleanup_admin.login(settings.admin)
        for user in created:
            # UI-created users have no id yet, look them up by username
            user_id = user.id or cleanup_admin.find_user_id(user.username)
            if user_id:
                cleanup_admin.delete_user(user_id)
                log.info("cleanup: deleted %s", user)
    except Exception as exc:  # cleanup must never hide the real test result
        log.warning("cleanup failed for %s: %s", created, exc)
