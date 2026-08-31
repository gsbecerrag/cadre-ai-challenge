"""The Walkthrough destination catalogue, and the prompt that names it — seam S2.

The catalogue is the whole reason `show_walkthrough` cannot send a Visitor to an invented page:
the Assistant picks an id, and the link it resolves to is written here, in code. These tests
hold that table against the two things it has to agree with — the demo Portal's own routes and
the published contact URL in the Knowledge Base — because both live in other people's files.
"""

import re
from datetime import date
from pathlib import Path

from core.adapters.knowledge_files import FileKnowledgeSource
from core.adapters.stub_demo_script import demo_fallback, demo_scripts
from core.knowledge import compile_knowledge_base
from core.prompt import build_system_prompt
from core.provider import ToolCall
from core.tools import default_tools
from core.tools.show_walkthrough import DEFINITION
from core.tools.walkthroughs import (
    CONTACT_FORM_URL,
    WALKTHROUGH_DESTINATIONS,
    resolve_destination,
)

WEB_SOURCE = Path(__file__).resolve().parents[2] / "web" / "src"
ROUTE_TABLE = WEB_SOURCE / "routes.tsx"
PORTAL_SOURCE = WEB_SOURCE / "portal"

# `{ path: 'tools', element: <ToolsPage /> }` and `{ index: true, element: <DashboardPage /> }`
PORTAL_ROUTE = re.compile(r"\{ (?:path: '([^']+)'|index: (true)), element: <(\w+) /> \}")
PORTAL_LAYOUT = re.compile(r"path: '/portal',\s*element: <(\w+) />")
KNOWLEDGE_BLOCK = "[services#what-cadre-does] What Cadre does\nCadre AI is a consultancy."


def test_every_destination_in_the_catalogue_resolves_to_the_link_the_card_shows() -> None:
    for destination_id, destination in WALKTHROUGH_DESTINATIONS.items():
        assert resolve_destination(destination_id) is destination
        assert destination.id == destination_id
        assert destination.label, destination_id
        assert destination.href, destination_id


def test_a_destination_the_assistant_invents_does_not_resolve() -> None:
    """The model fills the id in, and a model can put anything there. Nothing outside the
    table becomes a link — the tool rejects it and the Turn carries on."""
    assert resolve_destination("portal.billing") is None
    assert resolve_destination("") is None


def portal_routes() -> dict[str, tuple[str, ...]]:
    """Every demo Portal route, read off the app's own route table, with the components that
    render on it: the shared layout, and that route's page."""
    source = ROUTE_TABLE.read_text(encoding="utf-8")
    layout = PORTAL_LAYOUT.search(source)
    assert layout, "the route table no longer mounts a layout at /portal"

    _, _, children = source.partition("path: '/portal',")
    routes: dict[str, tuple[str, ...]] = {}
    for path, index, component in PORTAL_ROUTE.findall(children):
        routes["/portal" if index else f"/portal/{path}"] = (layout.group(1), component)
    return routes


def test_every_portal_destination_names_a_page_the_demo_portal_actually_renders() -> None:
    """A Walkthrough Card that opens a route nobody serves, or scrolls to an anchor that route
    does not render, is the invented page this tool exists to prevent. Both halves come from
    the demo Portal itself (ticket 07) rather than being retyped here — and the anchor is
    checked against the components that render on *that* route, so pointing `/portal/tools` at
    the Agents table fails rather than passing on a repository-wide grep."""
    routes = portal_routes()
    portal_destinations = [
        destination for destination in WALKTHROUGH_DESTINATIONS.values() if not destination.external
    ]

    assert portal_destinations, "the catalogue has no Portal destination, so this proves nothing"
    for destination in portal_destinations:
        route, _, fragment = destination.href.partition("#")
        assert route in routes, (
            f"{destination.id} links to {route}, which the route table has no page for"
        )
        rendered = "".join(
            (PORTAL_SOURCE / f"{component}.tsx").read_text(encoding="utf-8")
            for component in routes[route]
        )
        assert f'id="{fragment}"' in rendered, (
            f"{destination.id} scrolls to #{fragment}, which nothing on {route} renders"
        )


def test_the_maturity_index_walkthrough_lands_on_the_published_contact_form() -> None:
    """Getting scored on the AI Maturity Index starts with a Strategist: there is no self-serve
    page, so the destination is the contact form Cadre actually publishes."""
    get_scored = resolve_destination("maturity.get-scored")
    contact_form = resolve_destination("contact.form")

    assert get_scored is not None and contact_form is not None
    assert get_scored.href == contact_form.href == CONTACT_FORM_URL
    assert get_scored.external is True


def test_the_contact_form_link_is_one_the_knowledge_base_publishes() -> None:
    """The one URL in the catalogue that is not ours has to be a published one."""
    bodies = "\n".join(
        section.body for section in compile_knowledge_base(FileKnowledgeSource().documents())
    )

    assert CONTACT_FORM_URL in bodies


def test_the_tools_block_describes_the_show_walkthrough_tool_as_it_is_actually_defined() -> None:
    """The prompt tells the Assistant how to call the tool and which destinations exist; the
    definition tells the provider. They drift silently, so both are pinned to the definition
    and the catalogue rather than retyped."""
    tools = dict(build_system_prompt(KNOWLEDGE_BLOCK, today=date(2026, 8, 30)).cached_sections)[
        "tools"
    ]

    assert DEFINITION.name in tools
    for argument in DEFINITION.parameters["properties"]:
        assert argument in tools, argument
    for destination_id in WALKTHROUGH_DESTINATIONS:
        assert destination_id in tools, destination_id


def test_every_tool_call_in_the_demo_script_is_one_the_registry_accepts() -> None:
    """`make dev` and every review of it run on this script. A destination that no longer
    resolves, or a step count the tool rejects, would show the reviewer a Turn with the card
    silently missing from it — the tool's own recovery path hides the mistake."""
    registry = default_tools()
    calls = [
        event
        for script in [*demo_scripts().values(), demo_fallback()]
        for response in script
        for event in response
        if isinstance(event, ToolCall)
    ]

    assert calls, "the demo script calls no tool, so this guard proves nothing"
    for call in calls:
        outcome = registry.run(call)
        assert outcome.events, f"{call.id} produced no card: {outcome.result}"
