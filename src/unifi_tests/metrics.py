"""Live test metrics pushed to a Prometheus Pushgateway (optional).

Enabled only when UNIFI_PUSHGATEWAY_URL is set; otherwise every call is a no-op, so the
tests run the same with or without the monitoring stack.

One gauge, `unifi_test_duration_seconds`, with labels:
  kind   step (test step), event (UI page load / click until result), api (REST call)
  name   e.g. "3. Admin logs out", "click Sign In -> MFA screen", "POST /api/auth/login"
  test   pytest test name
  run_id one value per test run, so every measurement stays a separate series
  seq    occurrence number when the same name is measured more than once in a test
The whole run is pushed after every measurement (live view) and removed from the
Pushgateway at the end of the run, so finished runs stop repeating their last values.
"""

from __future__ import annotations

import logging
import os
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager

from prometheus_client import CollectorRegistry, Gauge, delete_from_gateway, push_to_gateway

log = logging.getLogger("unifi.metrics")

JOB = "unifi-os-tests"


def _current_test() -> str:
    # pytest sets e.g. "tests/api/test_x.py::test_name (call)"
    raw = os.getenv("PYTEST_CURRENT_TEST", "")
    return raw.split("::")[-1].split(" ")[0] or "session"


class Metrics:
    def __init__(self) -> None:
        self._disabled = False
        self.run_id = time.strftime("%Y%m%d-%H%M%S")
        self.registry = CollectorRegistry()
        self.duration = Gauge(
            "unifi_test_duration_seconds",
            "Duration of a test step, UI event or API call",
            ["kind", "name", "test", "seq"],
            registry=self.registry,
        )
        self._seen: Counter[tuple[str, str, str]] = Counter()

    @property
    def gateway_url(self) -> str | None:
        # Read lazily: .env is loaded by the settings fixture after this module is imported
        return None if self._disabled else (os.getenv("UNIFI_PUSHGATEWAY_URL") or None)

    @property
    def enabled(self) -> bool:
        return bool(self.gateway_url)

    def record(self, kind: str, name: str, seconds: float) -> None:
        test = _current_test()
        log.log(logging.DEBUG if kind == "api" else logging.INFO, "%.3f s  %s", seconds, name)
        if not self.enabled:
            return
        self._seen[(kind, name, test)] += 1
        seq = str(self._seen[(kind, name, test)])
        self.duration.labels(kind=kind, name=name, test=test, seq=seq).set(seconds)
        self._push()

    @contextmanager
    def measure(self, name: str, kind: str = "event") -> Iterator[None]:
        """Time a block, e.g. from a click until the expected result is visible."""
        start = time.perf_counter()
        yield
        self.record(kind, name, time.perf_counter() - start)

    def _push(self) -> None:
        try:
            push_to_gateway(
                self.gateway_url,
                job=JOB,
                registry=self.registry,
                grouping_key={"run_id": self.run_id},
                timeout=2,
            )
        except OSError as exc:  # monitoring must never break a test run
            log.warning("metrics push to %s failed, metrics off: %s", self.gateway_url, exc)
            self._disabled = True

    def finish(self) -> None:
        """Remove this run from the Pushgateway once Prometheus has scraped the last values."""
        if not self.enabled:
            return
        time.sleep(3)  # > Prometheus scrape interval
        try:
            delete_from_gateway(
                self.gateway_url, job=JOB, grouping_key={"run_id": self.run_id}, timeout=2
            )
        except OSError as exc:
            log.warning("metrics cleanup on %s failed: %s", self.gateway_url, exc)


metrics = Metrics()
