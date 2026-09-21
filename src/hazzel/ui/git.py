"""Diff, git status/log/review/commit panels, file viewer."""

import re

from rich.text import Text

from . import _state as _st
from ._state import DIM_COLOR, ERROR_COLOR, HAZZEL_COLOR, SUCCESS_COLOR, USER_COLOR
from . import input as _ui_input
from . import stream as _ui_stream
from .messages import _short_detail

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


def show_git_status(branch, body):
    _ui_input.rule()
    title = Text()
    title.append("  Git status", style="bold white")
    title.append(f"  ·  {branch or 'HEAD'}", style=DIM_COLOR)
    _st.console.print(title)
    if not body or body.strip() in ("(clean)", "Clean."):
        _st.console.print(Text("  Clean — nothing to commit.", style=SUCCESS_COLOR))
    else:
        from rich.table import Table  # deferred: only needed when git status has entries

        table = Table(show_header=False, box=None, pad_edge=False, padding=(0, 1, 0, 0))
        table.add_column(overflow="fold", width=4)
        table.add_column(overflow="fold")
        for line in body.splitlines()[:40]:
            if line.startswith("## "):
                continue
            code = line[:2].strip() or "·"
            rest = line[3:] if len(line) > 3 else line
            color = SUCCESS_COLOR if "??" in line[:2] else USER_COLOR if line[:1].strip() else HAZZEL_COLOR
            table.add_row(Text(code, style=f"bold {color}"), Text(rest.strip(), style="white"))
        _st.console.print(table)
        extra = len(body.splitlines()) - 40
        if extra > 0:
            _st.console.print(Text(f"  …{extra} more", style=DIM_COLOR))
    _ui_input.rule()


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


_GIT_STATUS_ICONS = {
    "M": ("M", USER_COLOR),
    "A": ("A", SUCCESS_COLOR),
    "?": ("+", SUCCESS_COLOR),
    "D": ("D", ERROR_COLOR),
    "R": ("R", HAZZEL_COLOR),
}


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


def show_git_file_list(files, staged=False, branch=""):
    total_add = sum(f.get("added", 0) for f in files)
    total_del = sum(f.get("deleted", 0) for f in files)
    _ui_input.rule()
    title = Text()
    title.append("  Changed files", style="bold white")
    title.append(f"  ·  {len(files)}", style=DIM_COLOR)
    if files:
        title.append(f"  ·  +{total_add} −{total_del}", style=SUCCESS_COLOR)
    title.append("  ·  staged" if staged else "  ·  unstaged", style=DIM_COLOR)
    if branch:
        title.append(f"  ·  {branch}", style=DIM_COLOR)
    _st.console.print(title)
    if not files:
        _st.console.print(Text("  No changes.", style=DIM_COLOR))
        _ui_input.rule()
        return
    for i, f in enumerate(files, 1):
        letter, color = _GIT_STATUS_ICONS.get(f.get("status", "M"), ("M", USER_COLOR))
        row = Text()
        row.append(f"{i:>3}  ", style=DIM_COLOR)
        row.append(letter, style=f"bold {color}")
        row.append(f"  {_short_detail(f['path'], limit=64)}", style="white")
        row.append(f"  +{f.get('added', 0)} −{f.get('deleted', 0)}", style=DIM_COLOR)
        _st.console.print(row)
    _st.console.print(Text(f"  Open [1-{len(files)}] · q close", style=DIM_COLOR))
    _ui_input.rule()


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


_LOG_TYPE_COLORS = {
    "feat": SUCCESS_COLOR,
    "fix": ERROR_COLOR,
    "perf": "yellow",
    "docs": USER_COLOR,
    "refactor": USER_COLOR,
    "test": SUCCESS_COLOR,
    "chore": DIM_COLOR,
    "build": DIM_COLOR,
    "ci": DIM_COLOR,
}


_LOG_LINE_RE = re.compile(r"^([0-9a-f]{4,40})\s+(?:\(([^)]*)\)\s+)?(.*)$")


_LOG_SUBJECT_RE = re.compile(r"^([A-Za-z]+)(\([^)]*\))?(:)\s?(.*)$")


def _style_log_refs(refs):
    row = Text()
    for i, seg in enumerate(refs.split(",")):
        seg = seg.strip()
        if not seg:
            continue
        if i:
            row.append(" · ", style=DIM_COLOR)
        if seg == "HEAD" or seg.startswith("HEAD "):
            row.append(seg.replace("->", "→"), style=f"bold {SUCCESS_COLOR}")
        elif seg.startswith("tag:"):
            row.append(seg, style="yellow")
        else:
            row.append(seg.replace("->", "→"), style="white")
    return row


def _style_log_subject(subject):
    row = Text()
    match = _LOG_SUBJECT_RE.match(subject or "")
    if match:
        color = _LOG_TYPE_COLORS.get(match.group(1).lower(), "white")
        row.append(match.group(1) + (match.group(2) or "") + match.group(3), style=f"bold {color}")
        if match.group(4):
            row.append(" " + match.group(4), style="white")
        return row
    row.append(subject or "(empty message)", style="white")
    return row


def show_git_log(body, branch=""):
    lines = [ln for ln in (body or "").splitlines() if ln.strip()][:20]
    _ui_input.rule()
    head = Text()
    head.append("  Recent commits", style="bold white")
    if branch:
        head.append(f"  ·  {branch}", style=DIM_COLOR)
    if lines:
        head.append(f"  ·  {len(lines)}", style=DIM_COLOR)
    _st.console.print(head)
    if not lines:
        _st.console.print(Text("  No commits yet.", style=DIM_COLOR))
        _ui_input.rule()
        return
    for line in lines:
        match = _LOG_LINE_RE.match(line.strip())
        if not match:
            _st.console.print(Text(f"  {line.strip()}", style="dim"))
            continue
        short, refs, subject = match.group(1), (match.group(2) or "").strip(), match.group(3)
        row = Text()
        row.append("  ", style=DIM_COLOR)
        row.append(short, style=f"bold {USER_COLOR}")
        row.append("  ")
        row.append_text(_style_log_subject(subject))
        _st.console.print(row)
        if refs:
            sub = Text()
            sub.append(" " * (len(short) + 4), style=DIM_COLOR)
            sub.append("└─ ", style=DIM_COLOR)
            sub.append_text(_style_log_refs(refs))
            _st.console.print(sub)
    _ui_input.rule()


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
