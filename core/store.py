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
from typing import Literal, Protocol

from core.auth import StrategistIdentity
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
