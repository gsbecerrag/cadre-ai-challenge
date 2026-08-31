"""Where a finished eval run is published, behind a seam so the runner does not care.

The suite is meant to land in Langfuse as a dataset run, next to the production Traces of the
same Assistant (ADR-0008). Ticket 06 has since brought the Langfuse client (`core/adapters/
langfuse_tracer.py`), and `make eval` already produces a real Trace per Turn through it — so
what is missing is only the upload, and it is a bigger piece of work than it looks.

The v3 shape this seam was written against (`dataset_item.link(trace, run_name)`) does not
exist in the installed SDK: langfuse 4.x replaces it with `DatasetClient.run_experiment`, which
runs the task itself and grades it inline. Our runner already ran the suite and holds a
`Scorecard`, so the upload has to go the other way round — upsert the dataset and one item per
Eval Case id, then link each case's existing Trace to a named run through
`client.api.dataset_run_items.create`, then attach one score per metric. That is a paid `make
eval` run to verify, which is why it is not landing on the back of ticket 12 (see the report).

What exists meanwhile is the seam and its no-op. `build_sink` returns `NullEvalSink` and says so
out loud when Langfuse keys are configured, so a run never fails and never silently pretends to
have uploaded. `LangfuseEvalSink` is the marked place the upload goes; it raises rather than
half-working, and nothing constructs it yet.
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
    "Uploading an eval run as a Langfuse dataset run is not implemented. The suite's Turns are "
    "already traced; what is missing is the dataset, one item per Eval Case, a run per "
    "scorecard and a score per metric. Until then `make eval` writes its report to "
    "evals/reports/ and nothing is uploaded."
)


class EvalSink(Protocol):
    """Publishes one finished run of the evaluation suite."""

    def publish(self, scorecard: "Scorecard") -> None: ...


class NullEvalSink:
    """Publishes nowhere. The report on disk is the record of the run."""

    def publish(self, scorecard: "Scorecard") -> None:
        logger.info("Eval run not published", extra={"cases": len(scorecard.cases)})


class LangfuseEvalSink:
    """The Langfuse dataset run — the marked place, still unwritten.

    Left unconstructed rather than half-written: an upload that creates the dataset and then
    fails to link the run is worse than no upload, because the project then holds a run that
    looks like a suite nobody passed.
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
