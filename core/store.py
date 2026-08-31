"""The `ConversationStore` seam: a Session's message history, and the Lead it produced.

The API is stateless — every Turn loads the Session and writes it back (ADR-0003) — so this is
the only place conversational state lives. One production implementation (Firestore, ticket 03)
and one test implementation (in memory) sit behind it. Reads are always scoped to one Session
id, which is what keeps one Visitor's conversation out of another's.

A Lead is keyed by its Session too, and lives behind the same seam rather than a second one:
it is written in the middle of a Turn by the `capture_lead` tool, from the same request, on the
same database, under the same Session id. A second Protocol would buy one more thing to wire up
and nothing else.

A Strategist's Availability is here for the same reason and one more: the Assistant reads it
mid-Turn, to decide whether a Live Hand-over may be offered at all (ticket 11), so it is
conversational state on the same database under the same connection. Keying it by the
Strategist's uid rather than a Session is the only difference.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol, get_args

from core.auth import StrategistIdentity
from core.handover import HandoverMode, HandoverRequest, HandoverState, LeadSnapshot
from core.provider import ModelMessage

# The Contact Details a Lead carries, kept raw: a tokenised email is a Lead no Strategist can
# call back (ADR-0006). These are `capture_lead`'s Contact Detail arguments, in the order the
# Console shows them.
CONTACT_DETAIL_NAMES: tuple[str, ...] = ("name", "email", "company", "phone", "role")

# What a Visitor can say about an answer: a thumb, one way or the other.
Rating = Literal["up", "down"]

# How many times a Visitor may change a thumb they have already left. One: a misclick is worth
# correcting, a control being held down is not, and the Triage Agent (ticket 14) runs on the
# document rather than on the stream of edits to it.
MAX_FEEDBACK_CHANGES = 1

# How many Handover Requests the Console asks for at a time. Same reasoning and same number as
# the Leads page: a work list, not the whole history.
DEFAULT_HANDOVER_PAGE = 50

# How many Triage Reports the Console's Triage tab asks for at a time. A reading list rather
# than a work list, and the same page size as the others so one number describes the Console.
DEFAULT_TRIAGE_PAGE = 50

# What the Triage Agent may say went wrong (ADR-0005). Seven values, enumerated in the JSON
# schema of the model call, so a category the Console has no chip for cannot be invented: a
# `kb_gap` is a Knowledge Base that is missing something, `wrong_escalation` an Escalation
# where a Grounded Answer existed, `hallucination` a claim no KB Section carries, `tone` an
# answer that was right and read badly, `pii` personal data mishandled, `bug` the product
# failing, `other` everything the model could not place — including its own malformed answer.
TriageCategory = Literal[
    "kb_gap", "wrong_escalation", "hallucination", "tone", "pii", "bug", "other"
]

# How much the Triage Agent thinks this one costs Cadre. Three values, because a Strategist
# reading a list needs to know what to open first and nothing finer than that is arguable.
TriageSeverity = Literal["low", "medium", "high"]

# The same two vocabularies as values, derived from the types rather than typed out again: the
# model call enumerates them in its JSON schema and the store reads them back defensively, and
# a category added to the type must not be a category the schema forgets to offer.
TRIAGE_CATEGORIES: tuple[TriageCategory, ...] = get_args(TriageCategory)
TRIAGE_SEVERITIES: tuple[TriageSeverity, ...] = get_args(TriageSeverity)

# How many Leads the Console asks for at a time. Comfortably more than a demo produces and
# small enough that the page is one screen of work rather than the whole history.
DEFAULT_LEAD_PAGE = 50


@dataclass(frozen=True)
class Lead:
    """A Visitor who has shared Contact Details, with the Qualification Signals collected.

    One Lead per Session: the Visitor gives their name in one Turn and their phone number three
    Turns later, and both belong to the same person. `signals` holds what the Assistant learned,
    one short phrase per Qualification Signal, and `score` is the count of them present —
    computed in code before the Lead is written, never sent by the model (ADR-0009).
    """

    session_id: str
    name: str = ""
    email: str = ""
    company: str = ""
    phone: str = ""
    role: str = ""
    signals: Mapping[str, str] = field(default_factory=dict)
    score: int = 0
    qualified: bool = False

    @property
    def contact_details(self) -> Mapping[str, str]:
        """The Contact Details that are actually filled in."""
        return {
            name: value
            for name in CONTACT_DETAIL_NAMES
            if (value := str(getattr(self, name, "") or "").strip())
        }


@dataclass(frozen=True)
class Feedback:
    """A Visitor's thumb on one Turn, and the sentence they added to it.

    It is stored with the Session it came from and the Trace of the Turn it judges: the Trace
    is what a Cadre engineer opens to see the answer being complained about, and the Session is
    what says whose thumb it was to press. `comment` has been through the `full` Redaction
    Profile before it gets here — the comment box is a free-text field a Visitor will type
    their email into, and this document is read by the Triage Agent and by Langfuse (ADR-0006).

    `changes` counts the times the Visitor changed their mind, which is what makes one more
    change refusable without reading a history nobody keeps.
    """

    session_id: str
    trace_id: str
    rating: Rating
    comment: str = ""
    changes: int = 0

    @property
    def id(self) -> str:
        """One Feedback per Trace, so the Trace names it.

        A second thumb on the same answer is then an update to this one document rather than a
        second opinion to reconcile, Firestore finds it by id without a query or a composite
        index, and the Triage Report keyed by the Feedback id (ADR-0005) points at the Turn it
        analysed without a join.
        """
        return self.trace_id

    @property
    def changed(self) -> bool:
        """Whether this Feedback replaced an earlier thumb — what the browser locks on."""
        return self.changes > 0


@dataclass(frozen=True)
class TriageReport:
    """The Triage Agent's structured analysis of one thumbs-down (ADR-0005).

    It lives here beside the `Feedback` it was written from rather than in `core.triage`,
    because it is a record this seam stores and reads back, and a type the store imported from
    the handler would put a cycle between the two.

    `id` is the Feedback id, which is the Trace id: a redelivered Firestore event writes the
    same document again instead of a second opinion on the same Turn, which is the whole of
    the handler's idempotency. `evidence` are the Visitor's and the Assistant's own words,
    quoted; the two suggestions are empty when the model had none to make.
    """

    id: str
    session_id: str
    trace_id: str
    category: TriageCategory
    summary: str
    evidence: tuple[str, ...] = ()
    suggested_kb_addition: str = ""
    suggested_eval_case: str = ""
    severity: TriageSeverity = "medium"
    # The model that wrote this report, recorded because the analysis is only as good as the
    # model that made it and the suggestions outlive the model that suggested them.
    model: str = ""
    # Written by the store, so the Console's "newest first" is one clock and not the clock of
    # whichever instance happened to run the Triage Agent.
    created_at: datetime | None = None


def lead_snapshot(lead: Lead) -> LeadSnapshot:
    """The Lead as it stands, copied onto a Handover Request.

    The one place the two shapes are mapped, so a Contact Detail added to the Lead is a field
    a Strategist sees on the request rather than one that silently stops travelling.
    """
    return LeadSnapshot(
        signals=dict(lead.signals),
        score=lead.score,
        qualified=lead.qualified,
        **{name: str(getattr(lead, name, "") or "") for name in CONTACT_DETAIL_NAMES},
    )


class ConversationStore(Protocol):
    """The message history of one Session, the Lead captured from it, and its Feedback."""

    async def load(self, session_id: str) -> tuple[ModelMessage, ...]:
        """Every message in the Session, oldest first. An unknown Session is empty."""
        ...

    async def append(
        self, session_id: str, messages: Sequence[ModelMessage], trace_id: str | None = None
    ) -> None:
        """Add messages to the end of the Session's history.

        `trace_id` is the Trace of the Turn these messages came from, kept on the Assistant's
        own messages. It is what `trace_belongs_to` answers from: a Trace id travels to one
        browser in one `done` event, and without a record of which Session it was streamed to,
        anyone holding one could leave Feedback on somebody else's conversation.
        """
        ...

    async def trace_belongs_to(self, session_id: str, trace_id: str) -> bool:
        """Whether this Session produced that Trace — the only question Feedback asks."""
        ...

    async def get_feedback(self, session_id: str, trace_id: str) -> Feedback | None:
        """This Session's Feedback on that Trace, or `None` if it has not rated it.

        Scoped to the Session like every other read here, even though the Trace id alone
        identifies the document: a Feedback that came back for a Session that did not leave it
        would be somebody else's opinion, presented as this Visitor's own.
        """
        ...

    async def save_feedback(self, feedback: Feedback) -> Feedback:
        """Write the Feedback, replacing what was there, and return what was written.

        The caller decides whether this is a first thumb or a change, because that decision is
        a rule about Visitors and not about databases — and it is the same rule whichever
        implementation of this seam is behind it.
        """
        ...

    async def save_triage_report(self, report: TriageReport) -> TriageReport:
        """Write the Triage Report, replacing what was there, and return what was stored.

        Keyed by the report's own id — the Feedback id — so a Firestore trigger delivered
        twice writes one document twice rather than two documents once (ADR-0005). The
        returned value carries the timestamp the store minted, because the Console orders the
        Triage tab by it.
        """
        ...

    async def list_triage_reports(
        self, limit: int = DEFAULT_TRIAGE_PAGE
    ) -> tuple[TriageReport, ...]:
        """The Console's page of Triage Reports, newest first.

        Not scoped to a Session, for the same reason `list_leads` is not: reading across
        conversations is the point of the Triage tab.
        """
        ...

    async def get_lead(self, session_id: str) -> Lead | None:
        """The Session's Lead, or `None` while the Visitor has shared no Contact Details."""
        ...

    async def upsert_lead(self, session_id: str, lead: Lead) -> Lead:
        """Write the Session's one Lead, replacing what was there, and return what was written.

        The caller merges: it reads the Lead, folds the new Contact Details and Qualification
        Signals into it, counts the score, and writes the whole thing back — so the merge rule
        and the score live in one place instead of once per implementation of this seam.
        """
        ...

    async def list_leads(self, limit: int = DEFAULT_LEAD_PAGE) -> tuple[Lead, ...]:
        """The most recently updated Leads, newest first.

        The one read in this seam that is not scoped to a Session, because the Console's list
        is the one place where crossing Sessions is the point. `limit` is a page, not a
        promise of everything: the Console renders a work list, and an unbounded read of a
        collection that grows with every Visitor is a slow page today and a bill tomorrow.
        """
        ...

    async def set_availability(self, strategist: StrategistIdentity, online: bool) -> None:
        """Record whether this Strategist is available to take a Live Hand-over.

        Keyed by the Strategist's uid, so signing in on a second device moves the same
        presence rather than adding a second Strategist to the count.
        """
        ...

    async def get_availability(self, uid: str) -> bool:
        """Whether this one Strategist is currently online — what their toggle renders as."""
        ...

    async def any_strategist_online(self) -> bool:
        """Availability: whether at least one Strategist is online.

        This is what gates the offer of a Live Hand-over (ticket 11), so it is a question
        about the team and not about whoever has the Console open.
        """
        ...

    async def create_handover(self, request: HandoverRequest) -> HandoverRequest:
        """Write a newly offered Handover Request and return it as stored.

        The returned value carries the timestamps the store minted, because the Console orders
        its queue by them and the caller has no clock the Console agrees with.
        """
        ...

    async def get_handover(self, request_id: str) -> HandoverRequest | None:
        """One Handover Request by id, or `None`.

        The caller checks that the Session owns it. The id is in a URL the Visitor's browser
        posts to, so "found" and "yours" are two questions and only the second is authorisation.
        """
        ...

    async def handover_for_session(self, session_id: str) -> HandoverRequest | None:
        """The Session's Handover Request, if it has one.

        At most one per Session by construction: this is what makes the offer of a Hand-over
        unrepeatable without asking the Assistant to remember anything.
        """
        ...

    async def update_handover(
        self,
        request_id: str,
        state: HandoverState,
        mode: HandoverMode | None = None,
        lead: LeadSnapshot | None = None,
    ) -> HandoverRequest:
        """Move a Handover Request to a state the caller has already validated, and return it.

        The state machine lives in `core.handover`, not here: a store that also decided which
        moves were legal would be a second copy of the rules, in the one place that cannot be
        unit-tested without a database. `mode` and `lead` are written only when given — a
        Callback that later runs out of Strategists is still a Callback, and a Contact Detail
        the Visitor typed after accepting refreshes the snapshot a Strategist reads.
        """
        ...

    async def list_handovers(
        self, mode: HandoverMode | None = None, limit: int = DEFAULT_HANDOVER_PAGE
    ) -> tuple[HandoverRequest, ...]:
        """The Console's page of Handover Requests, newest first.

        `mode` is the filter behind the Callbacks tab: one collection, one type, two views
        (docs/design/README.md ruling).
        """
        ...
