"""Git status and changed-files list."""

from rich.text import Text

from .. import _state as _st
from .._state import DIM_COLOR, ERROR_COLOR, HAZZEL_COLOR, SUCCESS_COLOR, USER_COLOR
from .. import input as _ui_input
from ..messages import _short_detail

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


_GIT_STATUS_ICONS = {
    "M": ("M", USER_COLOR),
    "A": ("A", SUCCESS_COLOR),
    "?": ("+", SUCCESS_COLOR),
    "D": ("D", ERROR_COLOR),
    "R": ("R", HAZZEL_COLOR),
}


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
