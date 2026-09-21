"""Spinner, streaming tokens, turn lifecycle, and quiet/print flags."""

import time

from rich.containers import Renderables
from rich.text import Text

from . import _state as _st


def _live_body(text):
    from rich.spinner import Spinner  # deferred: only needed when loader shows

    parts = []
    if text:
        label = Text(text, style="dim")
        label.append("  ·  ctrl+c to cancel", style="dim italic")
        parts.append(Spinner("dots", text=label))
    parts.extend(_st._tool_rows)
    if not parts:
        parts.append(Text(""))
    return Renderables(parts)

def begin_turn(text="Working…"):
    _st._tool_rows.clear()
    _st._turn_started = time.monotonic()
    show_loader(text)

def show_loader(text="Working…"):
    if _st._print_mode:
        return
    if _st._loader is not None:
        _st._loader.update(_live_body(text))
        return
    from rich.live import Live  # deferred: only needed when loader shows

    try:
        _st._loader = Live(
            _live_body(text),
            console=_st.console,
            refresh_per_second=12,
            transient=True,
        )
        _st._loader.start()
    except OSError:
        pass

def hide_loader():
    if _st._loader is None:
        return
    try:
        _st._loader.stop()
    except OSError:
        pass
    finally:
        _st._loader = None

def _pause_loader():
    was_active = _st._loader is not None
    if was_active:
        hide_loader()
    return was_active

def _resume_loader(was_active, text="Working…"):
    if was_active:
        show_loader(text)

def begin_stream():
    _st._stream_buffer = ""
    _st._stream_started = time.monotonic()
    _st._stream_first_at = None
    _st._stream_tokens = 0
    _st._stream_last_paint = 0.0
    _st._reason_buffer = []
    _st._thinking_streamed = False
    _st._thinking_was_live = False

def push_reasoning_token(token):
    if not token:
        return
    _st._reason_buffer.append(token)
    _st._thinking_streamed = True
    _st._thinking_was_live = True
    now = time.monotonic()
    if _st._loader is None:
        return
    if now - _st._stream_last_paint < 0.1:
        return
    _st._stream_last_paint = now
    text = _render_reasoning("".join(_st._reason_buffer))
    try:
        _st._loader.update(_live_reasoning(text))
    except OSError:
        pass

def _live_reasoning(text):
    from rich.spinner import Spinner  # deferred: only needed when reasoning is live

    spinner = Spinner("dots", text=Text("thinking", style="dim italic"))
    if not text:
        return Renderables([spinner])
    return Renderables([spinner, Text(text, style="dim")])

def _render_reasoning(text, limit=600):
    text = text.strip()
    if not text:
        return ""
    rendered = " ".join(text.split())
    if len(rendered) > limit:
        rendered = rendered[: limit - 1].rstrip() + "…"
    return rendered

def was_thinking_streamed():
    return _st._thinking_was_live

def push_stream_token(token):
    if not token:
        return
    now = time.monotonic()
    if _st._stream_first_at is None:
        _st._stream_first_at = now
    _st._stream_buffer += token
    _st._stream_tokens += 1
    if _st._thinking_streamed:
        _st._thinking_streamed = False
        _st._reason_buffer[:] = []
        if _st._loader is not None:
            try:
                _st._loader.update(_live_body(f"Working… · ttft {now - (_st._stream_started or now):.1f}s · {_st._stream_tokens} tokens"))
                return
            except OSError:
                pass
    if _st._loader is None:
        return
    if now - _st._stream_last_paint < 0.4 and _st._stream_tokens % 25:
        return
    _st._stream_last_paint = now
    try:
        ttft = _st._stream_first_at - (_st._stream_started or _st._stream_first_at)
        _st._loader.update(_live_body(f"Working… · ttft {ttft:.1f}s · {_st._stream_tokens} tokens"))
    except OSError:
        pass

def stream_stats():
    start = _st._stream_started or time.monotonic()
    first = _st._stream_first_at
    return {
        "tokens": _st._stream_tokens,
        "ttft": ((first - start) if first else 0.0),
        "elapsed": time.monotonic() - start,
    }

def end_stream():
    buf = _st._stream_buffer
    _st._stream_buffer = ""
    return buf

def end_turn():
    hide_loader()

def set_quiet(value=True):
    _st._quiet = bool(value)
    return _st._quiet

def is_quiet():
    return _st._quiet

def set_print_mode(value=True):
    _st._print_mode = bool(value)
    return _st._print_mode

def is_print_mode():
    return _st._print_mode

def set_auto_approve(value=True):
    _st._auto_approve = bool(value)
    return _st._auto_approve
