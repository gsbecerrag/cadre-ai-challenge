"""Where a finished eval run is published, behind a seam so the runner does not care.

The suite is meant to land in Langfuse as a dataset run, next to the production Traces of the
same Assistant (ADR-0008). Langfuse arrives with ticket 06, which has not merged, so the SDK is
deliberately not a dependency of this ticket: adding it here would put a second, competing
Langfuse client in the repository for whoever lands 06 to reconcile.

What exists instead is the seam and its no-op. `build_sink` returns `NullEvalSink` today and
says so out loud when Langfuse keys are configured, so a run never fails and never silently
pretends to have uploaded. `LangfuseEvalSink` is the marked place the upload goes; it raises
rather than half-working, and nothing constructs it yet.
"""

import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol

from core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover — the type is only needed for the signature
    from evals.runner import Scorecard

logger = get_logger("evals.sink")

LANGFUSE_VARIABLES = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")

NOT_YET = (
    "Uploading an eval run as a Langfuse dataset run lands with ticket 06 (Langfuse traces "
    "with cost), which owns the Langfuse client. Until it merges, `make eval` writes its "
    "report to evals/reports/ and nothing is uploaded."
)


class EvalSink(Protocol):
    """Publishes one finished run of the evaluation suite."""

    def publish(self, scorecard: "Scorecard") -> None: ...


class NullEvalSink:
    """Publishes nowhere. The report on disk is the record of the run."""

    def publish(self, scorecard: "Scorecard") -> None:
        logger.info("Eval run not published", extra={"cases": len(scorecard.cases)})


class LangfuseEvalSink:
    """The Langfuse dataset run — a placeholder until ticket 06 brings the client.

    Left unconstructed rather than written against an SDK this ticket may not add: a dataset
    run needs the same credentials, host and flush semantics as the production Trace exporter,
    and two of those in one repository is one too many.
    """

    def publish(self, scorecard: "Scorecard") -> None:
        raise NotImplementedError(NOT_YET)


def build_sink(environ: Mapping[str, str] | None = None) -> EvalSink:
    """The sink for this run. Always the no-op today; loud about it when keys are present."""
    present = os.environ if environ is None else environ
    if all(present.get(name, "").strip() for name in LANGFUSE_VARIABLES):
        logger.warning("Langfuse keys are set but the dataset run is not implemented yet")
    else:
        logger.info("No Langfuse keys; skipping the dataset run")
    return NullEvalSink()
