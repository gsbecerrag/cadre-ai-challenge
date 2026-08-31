"""The `--stub` gate on the case-driven half of seam S5.

The Eval Cases are driven through the whole application, one Turn at a time. That is fast and
free — the stub `ModelProvider` is the only provider these tests ever reach — but it is a suite
of its own rather than a unit test, so it is opt-in: `make eval-stub` and CI pass `--stub`, and
a bare `pytest` (an editor's run-on-save, a developer narrowing in on one module) skips it with
a line saying where the real run lives.
"""

from collections.abc import Iterable

import pytest

STUB_OPTION = "--stub"
SKIP_REASON = (
    "needs --stub: `make eval-stub` runs the deterministic Eval Cases against the stub "
    "provider; `make eval` runs the whole suite against the real one."
)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        STUB_OPTION,
        action="store_true",
        default=False,
        help=(
            "Drive the Eval Cases through the application with the stub ModelProvider. "
            "No key, no network, no spend."
        ),
    )


def pytest_collection_modifyitems(config: pytest.Config, items: Iterable[pytest.Item]) -> None:
    if config.getoption(STUB_OPTION):
        return
    skip = pytest.mark.skip(reason=SKIP_REASON)
    for item in items:
        if item.get_closest_marker("evals") is not None:
            item.add_marker(skip)
