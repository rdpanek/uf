from __future__ import annotations

from playwright.sync_api import expect

from unifi_tests.ui.pages.base import BasePage


class ConsolePage(BasePage):
    """Any page of the logged-in UniFi OS console: header with the profile (avatar) button."""

    path = "/"

    @property
    def profile_button(self):
        # Last button in the top banner is the avatar; its accessible name is the user's name
        return self.page.get_by_role("banner").get_by_role("button").last

    @property
    def profile_menu(self):
        sign_out = self.page.get_by_role("link", name="Sign Out")
        return self.page.get_by_role("dialog").filter(has=sign_out)

    def expect_logged_in(self) -> ConsolePage:
        expect(self.profile_button).to_be_visible(timeout=30_000)
        return self

    def expect_logged_in_as(self, display_name: str) -> ConsolePage:
        self.expect_logged_in()
        self.profile_button.click()
        expect(self.profile_menu.get_by_role("heading", name=display_name)).to_be_visible()
        self.page.keyboard.press("Escape")
        return self

    def logout(self) -> None:
        self.profile_button.click()
        self.profile_menu.get_by_role("link", name="Sign Out").click()
