"""Git log panel."""

import re

from rich.text import Text

from .. import _state as _st
from .._state import DIM_COLOR, ERROR_COLOR, SUCCESS_COLOR, USER_COLOR
from .. import input as _ui_input

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
