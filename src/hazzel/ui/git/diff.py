"""Diff views, file diff, diff-selection prompt, file viewer."""

from rich.text import Text

from .. import _state as _st
from .._state import DIM_COLOR, ERROR_COLOR, SUCCESS_COLOR, USER_COLOR
from .. import input as _ui_input
from .. import stream as _ui_stream

def show_diff(diff):
    if _st._print_mode:
        return
    was_active = _ui_stream._pause_loader()
    try:
        _ui_input.rule()
        lines = (diff or "").splitlines()
        for line in lines[:_ui_input.MAX_DIFF_DISPLAY_LINES]:
            if line.startswith("@@"):
                _st.console.print(Text(f"  {line}", style=USER_COLOR))
            elif line.startswith("+") and not line.startswith("+++"):
                _st.console.print(Text(f"  {line}", style=SUCCESS_COLOR))
            elif line.startswith("-") and not line.startswith("---"):
                _st.console.print(Text(f"  {line}", style=ERROR_COLOR))
            else:
                _st.console.print(Text(f"  {line}", style=DIM_COLOR))
        if len(lines) > _ui_input.MAX_DIFF_DISPLAY_LINES:
            _st.console.print(Text(f"  …{len(lines) - _ui_input.MAX_DIFF_DISPLAY_LINES} more lines capped for display", style=DIM_COLOR))
        _ui_input.rule()
    finally:
        _ui_stream._resume_loader(was_active)


def show_git_diff(body, staged=False):
    # Legacy single-shot diff view; the /diff flow uses the file browser
    # (show_git_file_list + show_git_file_diff) instead.
    _ui_input.rule()
    title = Text()
    title.append("  Git diff", style="bold white")
    title.append("  ·  staged" if staged else "  ·  unstaged", style=DIM_COLOR)
    _st.console.print(title)
    if not body or body.strip() in ("No changes.", "(clean)"):
        _st.console.print(Text("  No changes.", style=DIM_COLOR))
        _ui_input.rule()
        return
    added, deleted = _count_diff_marks(body)
    if added or deleted:
        _st.console.print(Text(f"  +{added} −{deleted}", style=DIM_COLOR))
    show_diff(body[:12000])
    _ui_input.rule()


def _count_diff_marks(body):
    added = deleted = 0
    for line in (body or "").splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            deleted += 1
    return added, deleted


def show_git_file_diff(path, body, staged=False, position=""):
    title = Text()
    title.append(f"  ❯ {position}{path}" if position else f"  ❯ {path}", style="bold white")
    title.append("  ·  staged" if staged else "  ·  unstaged", style=DIM_COLOR)
    added, deleted = _count_diff_marks(body)
    if added or deleted:
        title.append(f"  ·  +{added} −{deleted}", style=SUCCESS_COLOR)
    _st.console.print(title)
    show_diff(body)
    _st.console.print()


def prompt_diff_selection(count):
    was_active = _ui_stream._pause_loader()
    try:
        answer = input(f"  Open file [1-{count} / q]: ")
    except (EOFError, KeyboardInterrupt):
        return None
    finally:
        _ui_stream._resume_loader(was_active)
    clean = _ui_input._ANSI_RE.sub("", answer or "").strip().lower()
    if not clean or clean in ("q", "quit", "exit", "n"):
        return None
    try:
        n = int(clean)
        if 1 <= n <= count:
            return n - 1
    except ValueError:
        pass
    return "invalid"


def show_file_viewer(display_path, body, total_lines, shown_lines):
    if _st._print_mode:
        return
    _ui_stream.end_turn()
    _ui_input.rule()
    _st.console.print(Text(f"  {display_path}  ·  {total_lines} lines", style="dim"))
    for number, line in enumerate(body.splitlines(), 1):
        row = Text()
        row.append(f"{number:6d}  ", style="dim")
        row.append(line[:500])
        _st.console.print(row)
    if shown_lines < total_lines:
        _st.console.print(Text(f"  …{total_lines - shown_lines} more lines capped for display", style="dim"))
    _ui_input.rule()
