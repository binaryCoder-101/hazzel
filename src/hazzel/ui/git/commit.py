"""Commit message suggest/approve flow and diff review."""

from rich.text import Text

from .. import _state as _st
from .._state import DIM_COLOR, HAZZEL_COLOR, SUCCESS_COLOR
from .. import input as _ui_input
from .. import stream as _ui_stream

def show_git_commit(result):
    text = Text()
    if "cancelled" in result.lower() or "nothing" in result.lower():
        text.append("  ○ ", style=f"bold {DIM_COLOR}")
        text.append(result, style="dim")
    else:
        text.append("  ✓ ", style=f"bold {SUCCESS_COLOR}")
        text.append(result, style="bold white")
    _st.console.print(text)
    _st.console.print()


def show_review(markdown, files, staged=False, fallback=False):
    total_add = sum(f.get("added", 0) for f in files or [])
    total_del = sum(f.get("deleted", 0) for f in files or [])
    _ui_input.rule()
    title = Text()
    title.append("  Diff review", style="bold white")
    title.append(f"  ·  {len(files)} file(s)", style=DIM_COLOR)
    if files:
        title.append(f"  ·  +{total_add} −{total_del}", style=SUCCESS_COLOR)
    title.append("  ·  staged" if staged else "  ·  unstaged", style=DIM_COLOR)
    if fallback:
        title.append("  ·  offline heuristics", style=DIM_COLOR)
    _st.console.print(title)
    _st.console.print()
    if markdown and markdown.strip():
        from hazzel.formatter import print_response

        print_response(_st.console, markdown)
    _st.console.print(Text("  Read-only — nothing changed. /commit when ready.", style=DIM_COLOR))
    _ui_input.rule()


def show_git_suggest(message, fallback=False):
    _ui_input.rule()
    title = Text()
    title.append("  Suggested message", style="bold white")
    if fallback:
        title.append("  ·  offline draft", style=DIM_COLOR)
    _st.console.print(title)
    row = Text()
    row.append("  ❯ ", style=f"bold {HAZZEL_COLOR}")
    row.append(message, style="bold white")
    _st.console.print(row)
    _st.console.print(Text("  [y] commit · [e] edit · [n] cancel", style=DIM_COLOR))
    _ui_input.rule()


def prompt_suggest_action():
    was_active = _ui_stream._pause_loader()
    try:
        answer = input("  Accept? [y/e/n]: ")
    except (EOFError, KeyboardInterrupt):
        return "n"
    finally:
        _ui_stream._resume_loader(was_active)
    clean = _ui_input._ANSI_RE.sub("", answer or "").strip().lower()
    if clean in ("y", "yes", ""):
        return "y"
    if clean in ("e", "edit"):
        return "e"
    return "n"


def prompt_suggest_edit(initial):
    was_active = _ui_stream._pause_loader()
    try:
        answer = input(f"  Message [{initial}]: ")
    except (EOFError, KeyboardInterrupt):
        return None
    finally:
        _ui_stream._resume_loader(was_active)
    clean = _ui_input._ANSI_RE.sub("", answer or "").strip()
    return clean or initial
