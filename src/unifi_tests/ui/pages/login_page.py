from __future__ import annotations

from playwright.sync_api import expect

from unifi_tests.config import Credentials
from unifi_tests.mfa import current_totp
from unifi_tests.ui.pages.base import BasePage


class LoginPage(BasePage):
    path = "/login"

    @property
    def username(self):
        return self.page.get_by_label("Email or Username")

    @property
    def password(self):
        return self.page.get_by_label("Password")

    @property
    def sign_in(self):
        return self.page.get_by_role("button", name="Sign In")

    @property
    def mfa_screen(self):
        # UI account with MFA: second screen "App Authentication"
        return self.page.get_by_text("App Authentication", exact=True)

    @property
    def mfa_digits(self):
        # Six separate one-digit boxes; focus jumps to the next box after each digit
        return self.page.locator("input[inputmode='numeric']")

    def expect_loaded(self) -> LoginPage:
        expect(self.sign_in).to_be_visible()
        return self

    def login(self, credentials: Credentials) -> None:
        self.expect_loaded()
        self.username.fill(credentials.username)
        self.password.fill(credentials.password)
        self.sign_in.click()
        if credentials.totp_secret:
            self.enter_mfa_code(current_totp(credentials.totp_secret))

    def enter_mfa_code(self, code: str) -> None:
        expect(self.mfa_screen).to_be_visible()
        expect(self.mfa_digits).to_have_count(len(code))
        self.mfa_digits.first.click()
        # Typed key by key, like a user, so the boxes advance and the form submits itself
        self.page.keyboard.type(code, delay=80)
