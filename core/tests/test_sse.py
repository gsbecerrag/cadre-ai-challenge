"""Server-Sent Events framing — seam S2."""

from core.events import error_event, text_event
from core.sse import format_sse_event


def test_an_event_is_one_named_frame_with_a_single_json_data_line() -> None:
    frame = format_sse_event(text_event("Cadre AI is a consultancy"))

    assert frame == 'event: text\ndata: {"delta":"Cadre AI is a consultancy"}\n\n'


def test_a_blank_line_inside_a_delta_cannot_end_the_frame_early() -> None:
    """The Assistant's answers contain bullet lists; an unescaped blank line would split one
    delta into two frames and the browser would drop everything after it."""
    frame = format_sse_event(text_event("Four core services:\n\n- AI Strategy"))

    assert frame.count("\n\n") == 1
    assert frame.endswith("\n\n")


def test_non_ascii_is_framed_as_itself() -> None:
    """The Assistant answers in the Visitor's language; the response is UTF-8."""
    frame = format_sse_event(error_event("Algo salió mal."))

    assert frame == 'event: error\ndata: {"message":"Algo salió mal."}\n\n'
