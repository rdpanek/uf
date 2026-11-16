"""Thin, typed client for the UniFi OS Server REST API.

Design:
- one requests.Session per logged-in identity (cookie TOKEN + rotating CSRF header handled here),
- every call checks the HTTP status AND the UniFi envelope code, and raises a readable error,
- tests talk in domain terms (login, create_local_user, logout), never in raw HTTP.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
import urllib3

from unifi_tests.api import endpoints
from unifi_tests.api.errors import ApiError, UniFiError, redact
from unifi_tests.config import Credentials
from unifi_tests.data import LocalUser
from unifi_tests.metrics import metrics
from unifi_tests.mfa import current_totp

log = logging.getLogger("unifi.api")

_ID_IN_PATH = re.compile(r"/[0-9a-f]{8}-[0-9a-f-]{27,}")
CSRF_HEADERS = ("x-updated-csrf-token", "x-csrf-token")
SUPER_ADMIN = "super_administrator"


class UniFiOSClient:
    def __init__(self, base_url: str, verify_tls: bool = False, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Passed explicitly on every call: with REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE set in the
        # environment, requests would otherwise override Session.verify=False.
        self.verify_tls = verify_tls
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if not verify_tls:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ------------------------------------------------------------------ transport
    def _request(
        self,
        method: str,
        path: str,
        expected: int | tuple[int, ...] = 200,
        **kwargs: Any,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        if "json" in kwargs:
            log.info("%s %s %s", method, path, redact(kwargs["json"]))
        else:
            log.info("%s %s", method, path)
        response = self.session.request(
            method, url, timeout=self.timeout, verify=self.verify_tls, **kwargs
        )
        self._remember_csrf(response)
        log.info("  -> %s %s", response.status_code, response.reason)
        # ids replaced so all calls of one endpoint end up in one metric series
        metrics.record(
            "api", f"{method} {_ID_IN_PATH.sub('/{id}', path)}", response.elapsed.total_seconds()
        )
        allowed = expected if isinstance(expected, tuple) else (expected,)
        if response.status_code not in allowed:
            raise ApiError(response, expected)
        return response

    def _users_api(self, method: str, path: str, **kwargs: Any) -> Any:
        """Call the Users app API and unwrap its {code, codeS, msg, data} envelope."""
        response = self._request(method, path, **kwargs)
        body = response.json()
        if body.get("code") != 1:
            raise UniFiError(response, body)
        return body.get("data")

    def _remember_csrf(self, response: requests.Response) -> None:
        # UniFi OS rotates the CSRF token; every state-changing call must send the latest one.
        for header in CSRF_HEADERS:
            token = response.headers.get(header)
            if token:
                self.session.headers["X-CSRF-Token"] = token
                return

    # ------------------------------------------------------------------ auth
    def login(self, credentials: Credentials) -> dict[str, Any]:
        """Log in with username/password and, if configured, a TOTP code (MFA)."""
        payload: dict[str, Any] = {
            "username": credentials.username,
            "password": credentials.password,
            "rememberMe": False,
        }
        if credentials.totp_secret:
            payload["token"] = current_totp(credentials.totp_secret)
        return self._request("POST", endpoints.LOGIN, json=payload).json()

    def login_expecting_failure(self, credentials: Credentials) -> dict[str, Any]:
        payload = {"username": credentials.username, "password": credentials.password}
        response = self._request("POST", endpoints.LOGIN, expected=(400, 401, 403), json=payload)
        return response.json()

    def logout(self) -> None:
        self._request("POST", endpoints.LOGOUT, expected=(200, 204))
        self.session.headers.pop("X-CSRF-Token", None)

    def current_user(self) -> dict[str, Any]:
        return self._request("GET", endpoints.CURRENT_USER).json()

    def is_authenticated(self) -> bool:
        response = self.session.get(
            f"{self.base_url}{endpoints.CURRENT_USER}", timeout=self.timeout, verify=self.verify_tls
        )
        return response.status_code == 200

    # ------------------------------------------------------------------ users
    def role_id(self, system_key: str = SUPER_ADMIN) -> str:
        roles = self._users_api("GET", endpoints.ROLES)
        for role in roles:
            if role.get("system_key") == system_key:
                return role["unique_id"]
        available = ", ".join(str(r.get("system_key") or r.get("name")) for r in roles)
        raise AssertionError(f"role {system_key!r} not found, available: {available}")

    def create_local_user(self, user: LocalUser, role: str = SUPER_ADMIN) -> LocalUser:
        """Create a local-access-only user and store its id on the object.

        UniFi OS allows a local (username + password) account only for users with an
        admin role ("only admin could have local account"), so a role is always assigned.
        """
        payload = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "password": user.password,
            "role_id": self.role_id(role),
        }
        data = self._users_api("POST", endpoints.USER_CREATE, json=payload)
        user.id = data["unique_id"]
        log.info("created local user %s (id=%s)", user.username, user.id)
        return user

    def find_user_id(self, username: str) -> str | None:
        for item in self._users_api("GET", endpoints.USERS):
            if item.get("username") == username:
                return item["unique_id"]
        return None

    def delete_user(self, user_id: str) -> None:
        """Active administrators cannot be deleted, so deactivate first, then delete."""
        path = endpoints.USER.format(user_id=user_id)
        self._users_api("PUT", path, json={"status": "DEACTIVATED"})
        self._users_api("DELETE", path)
