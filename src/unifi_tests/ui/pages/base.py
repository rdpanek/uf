from __future__ import annotations

from playwright.sync_api import Page


class BasePage:
    """Common behaviour for all UniFi OS pages. Selectors live in the page objects only."""

    path = "/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")

    def open(self) -> BasePage:
        self.page.goto(f"{self.base_url}{self.path}")
        return self
