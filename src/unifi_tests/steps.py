"""Named test steps: they show up in the console log and in the HTML report,
so a failure reads as 'failed in step 3: Logout' rather than a bare traceback."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from unifi_tests.metrics import metrics

log = logging.getLogger("unifi.steps")


@contextmanager
def step(title: str) -> Iterator[None]:
    log.info("STEP: %s", title)
    start = time.perf_counter()
    try:
        yield
    except BaseException as exc:
        log.error("STEP FAILED: %s", title)
        exc.add_note(f"Failed in step: {title}")
        raise
    metrics.record("step", title, time.perf_counter() - start)
