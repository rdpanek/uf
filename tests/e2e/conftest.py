"""Playwright settings for the UniFi OS web UI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from unifi_tests.ui.pages import ConsolePage, LoginPage, UsersPage

REPORTS = Path("reports")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, settings):
    args = {
        **browser_context_args,
        "base_url": settings.base_url,
        "ignore_https_errors": not settings.verify_tls,  # self-signed certificate
        "viewport": {"width": 1440, "height": 900},
    }
    if os.getenv("UNIFI_RECORD_HAR", "").lower() in {"1", "true", "yes"}:
        # Opt-in: records the UI's API calls (documents the API, helps when UniFi changes it).
        # The HAR contains request bodies incl. credentials, so it is off by default.
        REPORTS.mkdir(exist_ok=True)
        args["record_har_path"] = str(REPORTS / "network.har")
        args["record_har_url_filter"] = "**/api/**"
        args["record_har_content"] = "omit"
    return args


@pytest.fixture
def login_page(page, settings) -> LoginPage:
    return LoginPage(page, settings.base_url)


@pytest.fixture
def console(page, settings) -> ConsolePage:
    return ConsolePage(page, settings.base_url)


@pytest.fixture
def users_page(page, settings) -> UsersPage:
    return UsersPage(page, settings.base_url)
