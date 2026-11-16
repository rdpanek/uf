from __future__ import annotations

from playwright.sync_api import Page

from unifi_tests.metrics import metrics

# Navigation Timing of the last full page load, measured by the browser itself
_LOAD_TIME_JS = """() => {
  const nav = performance.getEntriesByType("navigation")[0];
  return nav ? nav.loadEventEnd - nav.startTime : null;
}"""


class BasePage:
    """Common behaviour for all UniFi OS pages. Selectors live in the page objects only."""

    path = "/"
    name = "page"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")

    def open(self) -> BasePage:
        self.page.goto(f"{self.base_url}{self.path}", wait_until="load")
        load_ms = self.page.evaluate(_LOAD_TIME_JS)
        if load_ms:
            metrics.record("event", f"page load: {self.name}", load_ms / 1000)
        return self
