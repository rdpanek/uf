from __future__ import annotations

from playwright.sync_api import expect

from unifi_tests.data import LocalUser
from unifi_tests.ui.pages.base import BasePage


class UsersPage(BasePage):
    """UniFi OS > Admins & Users (lives under the Network application)."""

    path = "/network/default/admins/users"

    @property
    def create_new(self):
        return self.page.get_by_role("button", name="Create New")

    def expect_loaded(self) -> UsersPage:
        expect(self.create_new).to_be_visible(timeout=30_000)
        return self

    def create_local_user(self, user: LocalUser) -> None:
        self.expect_loaded()
        self.create_new.click()
        self.page.get_by_text("Create New User", exact=True).click()

        # The side panel is a <section> titled "Create New User"
        form = self.page.locator("section").filter(has_text="Create New User").last
        form.get_by_label("First Name").fill(user.first_name)
        form.get_by_label("Last Name").fill(user.last_name)
        # Only admins may have a local (username + password) account in UniFi OS.
        # Ticking "Admin" reveals "Restrict to Local Access Only"; ticking that one reveals
        # Username and Password. (On a console without a UI account it is pre-checked and locked.)
        form.locator("#use-admin").check()
        local_only = form.get_by_role("checkbox", name="Restrict to Local Access Only")
        if not local_only.is_checked():
            local_only.check()
        expect(local_only).to_be_checked()
        # Username/Password have no <label for>; the real inputs are the autocomplete=off ones
        # (the others are hidden decoys against browser autofill).
        form.locator("input[type=text][autocomplete=off]").fill(user.username)
        form.locator("input[type=password][autocomplete=off]").fill(user.password)
        form.get_by_role("button", name="Create", exact=True).click()

    def expect_user_listed(self, user: LocalUser) -> None:
        expect(self.page.get_by_text(user.full_name, exact=True)).to_be_visible()
