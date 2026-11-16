"""Same scenario as tests/api, driven through the UniFi OS web UI with Playwright."""

from __future__ import annotations

import pytest

from unifi_tests.config import Credentials
from unifi_tests.steps import step

pytestmark = pytest.mark.e2e


def test_admin_creates_local_user_who_can_log_in_ui(
    settings, login_page, console, users_page, local_user_factory
):
    user = local_user_factory()

    auth = "password + MFA" if settings.admin.totp_secret else "password"
    with step(f"1. Admin logs in through the login page ({auth})"):
        login_page.open()
        login_page.login(settings.admin)
        console.expect_logged_in()

    with step("2. Admin creates a local user in Admins & Users"):
        users_page.open()
        users_page.create_local_user(user)
        users_page.expect_user_listed(user)

    with step("3. Admin logs out"):
        console.logout()
        login_page.expect_loaded()

    with step("4. The local user logs in"):
        login_page.login(Credentials(user.username, user.password))
        console.expect_logged_in_as(user.full_name)
