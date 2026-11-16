"""Scenario: admin creates a local user, logs out, and the new user can log in (REST API)."""

from __future__ import annotations

import pytest

from unifi_tests.config import Credentials
from unifi_tests.steps import step

pytestmark = pytest.mark.api


def test_admin_creates_local_user_who_can_log_in(api, settings, local_user_factory):
    user = local_user_factory()

    auth = "password + MFA" if settings.admin.totp_secret else "password"
    with step(f"1. Admin logs in ({auth})"):
        admin_info = api.login(settings.admin)
        assert api.is_authenticated(), f"admin session not established: {admin_info}"

    with step("2. Admin creates a local user"):
        api.create_local_user(user)
        assert user.id, "create user response did not contain an id"

    with step("3. Admin logs out"):
        api.logout()
        assert not api.is_authenticated(), "session is still valid after logout"

    with step("4. The local user logs in"):
        api.login(Credentials(user.username, user.password))
        me = api.current_user()
        assert me.get("username") == user.username, (
            f"logged in as {me.get('username')!r}, expected {user.username!r}"
        )


def test_local_user_with_wrong_password_is_rejected(api, settings, local_user_factory):
    """Negative check that the positive test above really proves something."""
    user = local_user_factory()

    with step("Admin creates a local user and logs out"):
        api.login(settings.admin)
        api.create_local_user(user)
        api.logout()

    with step("Login with a wrong password is refused"):
        error = api.login_expecting_failure(Credentials(user.username, user.password + "x"))
        assert error.get("code") == "AUTHENTICATION_FAILED_INVALID_CREDENTIALS", error
        assert not api.is_authenticated()
