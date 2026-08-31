"""`GET /api/console/triage` — seam S1, the Triage tab's first paint and its fallback.

The Console reads Triage Reports twice over, exactly as it reads Leads (ADR-0010): once from
here, so the first paint needs no Firestore client and no rules evaluation, and then live from
Firestore through a browser listener. The allowlist is enforced on both paths, and the refusal
tests in `test_console.py` cover this route with every other one — they are derived from the
router, so this endpoint was behind the door the moment it was registered.

What is left to check here is the shape a Strategist reads: newest first, every field of the
report, and the Trace id the "Open trace in Langfuse" link is built from.
"""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_console import (  # noqa: F401
    ALLOWED_EMAILS,
    ANGEL_TOKEN,
    as_strategist,
    verifier,
)
from core.adapters.fake_verifier import ScriptedTokenVerifier
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.stub_provider import StubModelProvider
from core.config import Settings
from core.store import TriageReport

FIRST_REPORT = TriageReport(
    id="trace-0001",
    session_id="session-0001",
    trace_id="trace-0001",
    category="kb_gap",
    summary="A Visitor asked for SOC 2 documentation and the Escalation had nothing to cite.",
    evidence=("Do you have SOC 2?", "It just said it couldn't confirm anything."),
    suggested_kb_addition="Add the data-security commitments to security#commitments.",
    suggested_eval_case='trap: "Do you have SOC 2?" -> escalate + cite security#commitments',
    severity="medium",
    model="anthropic/claude-sonnet-5",
)

SECOND_REPORT = TriageReport(
    id="trace-0002",
    session_id="session-0002",
    trace_id="trace-0002",
    category="wrong_escalation",
    summary="An existing client asked about Portal access and was sent to the contact form.",
    evidence=("I'm already a client — the contact form loops me back to sales.",),
    suggested_kb_addition="Clarify portal#access: existing clients go through their Cadre team.",
    suggested_eval_case='in-kb: "How do I log into the portal?" -> cite portal#access',
    severity="high",
    model="anthropic/claude-sonnet-5",
)


@pytest.fixture
def triaged_client(
    settings: Settings,
    web_dist: Path,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    verifier: ScriptedTokenVerifier,  # noqa: F811
) -> Iterator[TestClient]:
    asyncio.run(store.save_triage_report(FIRST_REPORT))
    asyncio.run(store.save_triage_report(SECOND_REPORT))
    app = create_app(
        settings=settings.model_copy(update={"admin_allowed_emails": ALLOWED_EMAILS}),
        web_dist=web_dist,
        provider=provider,
        store=store,
        verifier=verifier,
    )
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def test_the_triage_tab_reads_every_report_newest_first(triaged_client: TestClient) -> None:
    response = triaged_client.get("/api/console/triage", headers=as_strategist(ANGEL_TOKEN))

    assert response.status_code == 200
    reports = response.json()["reports"]
    # Newest first, because the Triage tab is a reading list and the newest thumbs-down is the
    # one a Strategist has not seen (docs/design §3.3).
    assert [report["id"] for report in reports] == ["trace-0002", "trace-0001"]
    newest = reports[0]
    assert newest["category"] == "wrong_escalation"
    assert newest["severity"] == "high"
    assert newest["summary"] == SECOND_REPORT.summary
    assert newest["evidence"] == list(SECOND_REPORT.evidence)
    assert newest["suggested_kb_addition"] == SECOND_REPORT.suggested_kb_addition
    assert newest["suggested_eval_case"] == SECOND_REPORT.suggested_eval_case
    assert newest["model"] == SECOND_REPORT.model
    # The link the card carries: "Open trace in Langfuse ↗" is built from this id.
    assert newest["trace_id"] == "trace-0002"
    # ISO 8601, so the browser renders a time it cannot misread as seconds or milliseconds.
    assert newest["created_at"] is not None
