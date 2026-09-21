"""Turn cards, tool rows, context meter, history, git views, help/docs/usage, selectors."""

import re
import sys

from rich.text import Text

from . import _state as _st
from ._state import DIM_COLOR, ERROR_COLOR, HAZZEL_COLOR, SUCCESS_COLOR, USER_COLOR, is_no_color
from . import input as _ui_input
from . import stream as _ui_stream


def show_turn_from_trace(user_command, trace, summary):
    return None

def show_turn_card(user_command, tool_rows, summary_lines, model="Hazzel 1.3.2", root="~/hazzel"):
    return None

def show_hazzel_message(message):
    _ui_stream.hide_loader()
    if not message or not message.strip():
        return
    # Deferred import: formatter pulls rich.syntax + pygments (~30ms),
    # only needed once the first assistant message is actually rendered.
    from hazzel.formatter import print_response

    print_response(_st.console, message)

def show_reasoning(reasoning):
    _ui_stream.hide_loader()
    if _st._thinking_was_live:
        _st._thinking_was_live = False
        return
    text = (reasoning or "").strip()
    if not text:
        return
    _st.console.print(Text(text, style="dim"))
    _st.console.print()

def _short_detail(detail: str, limit: int = 62) -> str:
    if not detail:
        return ""
    d = detail.strip()
    if len(d) > limit:
        return d[: limit - 1].rstrip() + "…"
    return d

def _relativize_detail(detail):
    try:
        from pathlib import Path as _Path

        from hazzel import config as _config

        root = _config.PROJECT_ROOT.resolve()
    except Exception:
        return detail
    parts = []
    for tok in str(detail or "").split():
        raw = tok.strip("'\"")
        try:
            candidate = _Path(raw)
        except Exception:
            parts.append(tok)
            continue
        if not candidate.is_absolute():
            parts.append(tok)
            continue
        try:
            parts.append(str(candidate.resolve().relative_to(root)))
        except ValueError:
            parts.append(tok)
        except OSError:
            parts.append(tok)
    return " ".join(parts)

def format_context_plain(used, window):
    try:
        used = max(0, int(used or 0))
    except (TypeError, ValueError):
        used = 0
    try:
        window = int(window or 0)
    except (TypeError, ValueError):
        window = 0
    if window <= 0:
        window = 131072
    if window >= 1_000_000:
        short = f"{window / 1_000_000:.1f}M"
    elif window >= 1000:
        short = f"{window // 1000}k"
    else:
        short = str(window)
    return f"{used / window * 100:.1f}%/{short} (auto)"

def format_context_meter(used, window):
    if is_no_color():
        return format_context_plain(used, window)
    try:
        used = max(0, int(used or 0))
    except (TypeError, ValueError):
        used = 0
    try:
        window = int(window or 0)
    except (TypeError, ValueError):
        window = 0
    if window <= 0:
        window = 131072
    pct = used / window * 100
    if pct < 50:
        color = "\x1b[32m"
    elif pct < 80:
        color = "\x1b[33m"
    else:
        color = "\x1b[31m"
    return f"\x1b[1m{color}{format_context_plain(used, window)}\x1b[0m\x1b[2m"

def _format_elapsed(seconds):
    if seconds is None:
        return ""
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return ""
    if seconds < 0:
        return ""
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"
    return f"{seconds:.1f}s"

_PREVIEW_MAX_LINES = 8
_PREVIEW_MAX_CHARS = 480

def _format_result_preview(result, max_lines=_PREVIEW_MAX_LINES, max_chars=_PREVIEW_MAX_CHARS):
    if not result:
        return "(no output)"
    text = str(result)
    lines = text.splitlines()
    # Drop trailing blanks so the suffix count is meaningful.
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return "(no output)"

    if len(lines) <= max_lines:
        head = "\n".join(lines)
        if len(head) <= max_chars:
            return head

    # Truncate by line count, then fold overly long lines so the preview
    # never blows out the terminal width horizontally.
    head_lines = []
    for line in lines[:max_lines]:
        line = line[: max_chars // 2]
        head_lines.append(line)
    out = "\n".join(head_lines)
    remaining = len(lines) - len(head_lines)
    return out + f"\n…{remaining} more lines"

def show_tool(tool_name, detail="", success=True, exit_code=None, cached=False,
              elapsed=None, result=None):
    if _st._quiet:
        return
    icon = "●" if success else "!"
    limit = 45 if exit_code is not None else 62
    text = Text()
    text.append("  ", style=DIM_COLOR)
    if cached:
        text.append(f"{icon} ", style=DIM_COLOR)
        text.append(str(tool_name).ljust(12), style=DIM_COLOR)
    else:
        text.append(f"{icon} ", style=HAZZEL_COLOR if success else ERROR_COLOR)
        text.append(str(tool_name).ljust(12), style="white" if success else ERROR_COLOR)
    short = _short_detail(_relativize_detail(detail), limit=limit)
    if short:
        text.append(f" {short}", style="#9aa4b2")
    meta = _format_elapsed(elapsed)
    if cached:
        meta = (meta + " · " if meta else "") + "cached"
    if meta:
        text.append(f"  · {meta}", style=DIM_COLOR)
    if exit_code is not None and not success:
        text.append(f"  · exit {exit_code}", style=DIM_COLOR)

    preview_rows = None
    if result is not None and not _st._quiet:
        preview = _format_result_preview(result)
        if preview:
            preview_rows = _split_preview_rows(preview)

    if _st._loader is not None:
        _st._tool_rows.append(text)
        while len(_st._tool_rows) > _ui_input._MAX_TOOL_ROWS:
            _st._tool_rows.pop(0)
        _st._loader.update(_ui_stream._live_body(None))
    else:
        _st.console.print(text)

    if preview_rows is not None:
        for row in preview_rows:
            if _st._loader is not None:
                _st._tool_rows.append(row)
            else:
                _st.console.print(row)
        if _st._loader is not None:
            while len(_st._tool_rows) > _ui_input._MAX_TOOL_ROWS:
                _st._tool_rows.pop(0)
            _st._loader.update(_ui_stream._live_body(None))

def _split_preview_rows(preview):
    rows = []
    for i, line in enumerate(preview.splitlines()):
        t = Text()
        if i == 0:
            t.append("  " + chr(0x23BF) + " ", style="#7d8799")
        else:
            t.append("  " + chr(0x2502) + " ", style="#5b6472")
        t.append(line, style="#c5cdd9")
        rows.append(t)
    return rows

def show_user_command(command):
    text = Text()
    text.append("❯ ", style="dim")
    text.append(command.strip(), style="white")
    _st.console.print(text)

def show_history(messages):
    items = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") not in ("user", "assistant"):
            continue
        content = msg.get("content") or ""
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
            content = "\n".join(parts)
        if not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        items.append((msg["role"], content))
    if not items:
        return
    if len(items) >= 2 and items[-2][0] == "user" and items[-1][0] == "assistant":
        items = items[-2:]
    else:
        items = items[-1:]
    for role, content in items:
        if role == "user":
            _ui_input.rule()
            text = Text()
            text.append("❯ ", style="bold")
            text.append(content, style="white")
            _st.console.print(text)
            _ui_input.rule()
            _st.console.print()
        else:
            show_hazzel_message(content)
            _st.console.print()

def show_error(message):
    text = Text()
    text.append("  ! ", style=ERROR_COLOR)
    text.append(message, style=ERROR_COLOR)
    _st.console.print(text)

def confirm(prompt):
    if _st._print_mode:
        return _st._auto_approve
    was_active = _ui_stream._pause_loader()
    try:
        answer = input(f"\n{prompt} [y/N]: ")
    except (EOFError, KeyboardInterrupt):
        return False
    finally:
        _ui_stream._resume_loader(was_active)
    clean = _ui_input._ANSI_RE.sub("", answer or "").strip().lower()
    return clean in {"y", "yes"}

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

def show_undo(restored):
    if not restored:
        _st.console.print(Text("  Nothing to undo.", style=DIM_COLOR))
        _st.console.print()
        return
    for key, action in restored:
        text = Text()
        text.append("  ✓ ", style=SUCCESS_COLOR)
        text.append(f"{action} ", style="white")
        text.append(_short_detail(key), style=DIM_COLOR)
        _st.console.print(text)
    _st.console.print()

def prompt_goal_criteria():
    was_active = _ui_stream._pause_loader()
    try:
        answer = input("  Done looks like what? [Enter to skip]: ")
    except (EOFError, KeyboardInterrupt):
        return ""
    finally:
        _ui_stream._resume_loader(was_active)
    return _ui_input._ANSI_RE.sub("", answer or "").strip()

def show_model_selected(display_name, provider_display):
    text = Text()
    text.append("  ✓ ", style=SUCCESS_COLOR)
    text.append(display_name, style="white")
    text.append(f" ({provider_display})", style=DIM_COLOR)
    _st.console.print(text)
    _st.console.print()

def show_cleared():
    text = Text()
    text.append("  ○ ", style=DIM_COLOR)
    text.append("Conversation cleared", style="dim")
    _st.console.print(text)
    _st.console.print()

_HELP_INTRO = (
    "Hazzel — inspects, edits, and runs your code, right from your terminal."
)

_HELP_SECTIONS = [
    ("Shortcuts", [
        ("/", "commands · live filter", "Esc", "clear input"),
        ("Tab", "accept highlighted item", "Ctrl+U", "clear input"),
        ("↑/↓", "navigate commands", "Ctrl+V", "paste"),
        ("Ctrl+C", "quit"),
    ]),
    ("Commands", [
        ("/model", "switch model & provider"),
        ("/think", "deeper reasoning on/off"),
        ("/plan", "read-only plan, approve first"),
        ("/goal", "objective + acceptance"),
        ("/help", "this overview"),
        ("/docs", "full usage guide"),
        ("/clear", "reset conversation + usage"),
        ("/summary", "summarize last implementation"),
        ("/export", "save transcript [file.md]"),
        ("/copy", "copy last reply [code]"),
        ("/init", "generate AGENTS.md map"),
        ("/skills", "pick + attach a skill"),
        ("/mcp", "list + use MCP servers"),
        ("/retry", "re-run last message"),
        ("/jobs", "background jobs [id|kill id]"),
        ("/usage", "show token usage"),
        ("/undo", "undo last file change"),
        ("/logout", "clear saved API keys"),
        ("/exit", "quit"),
    ]),
    ("Git", [
        ("/status", "working-tree status"),
        ("/diff", "changed files + full diff [--staged]"),
        ("/review", "read-only review of the uncommitted diff"),
        ("/commit", "suggest message + approval"),
        ("/log", "recent commits"),
    ]),
]

_HELP_FOOT = "Models  ·  Groq · OpenAI · Mistral · Anthropic · Gemini · DeepSeek · OpenRouter · Ollama  —  /model to switch"

_STAR_LINE = "If Hazzel helps, star us: github.com/mukundzha/hazzel"

def _help_table(rows):
    from rich.table import Table  # deferred: only needed when help is shown

    ncols = max((len(row) for row in rows), default=2)
    table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
        padding=(0, 3, 0, 0),
    )
    for _ in range(ncols):
        table.add_column(overflow="fold")
    for row in rows:
        cells = []
        for j in range(ncols):
            cell = row[j] if j < len(row) else ""
            cells.append(Text(cell, style=("white" if j % 2 == 0 else "dim")))
        table.add_row(*cells)
    return table

def show_help():
    _print_help_inline()

def _doc_line(line):
    text = Text()
    for i, part in enumerate(re.split(r"(`[^`]+`)", line)):
        if not part:
            continue
        if part.startswith("`") and part.endswith("`") and len(part) > 2:
            text.append(part[1:-1], style="white")
            continue
        pos = 0
        for m in re.finditer(r"/[a-z]+|@\S+", part):
            if m.start() > pos:
                text.append(part[pos:m.start()], style="dim" if i == 0 and m.start() == 0 else "white")
            tok = m.group(0)
            text.append(tok, style="white" if tok.startswith("/") else USER_COLOR)
            pos = m.end()
        text.append(part[pos:], style="white" if pos else ("dim" if line.startswith("/") else "white"))
    return text

def show_docs():
    from hazzel.docs import get_sections

    sections = get_sections()
    _ui_input.rule()
    head = Text()
    head.append("  Hazzel docs", style="white")
    head.append(f"  ·  {len(sections)} sections", style=DIM_COLOR)
    _st.console.print(head)
    _ui_input.rule()
    for i, (title, lines) in enumerate(sections):
        _st.console.print()
        sec = Text()
        sec.append(f"  {i + 1:02d}  ", style=DIM_COLOR)
        sec.append(title, style="white")
        _st.console.print(sec)
        for line in lines:
            row = Text()
            row.append("       ", style=DIM_COLOR)
            row.append_text(_doc_line(line))
            _st.console.print(row)
    _st.console.print()
    _ui_input.rule()

def _print_help_inline():
    _st.console.print()
    _st.console.print(Text(_HELP_INTRO, style="white"))
    for title, rows in _HELP_SECTIONS:
        _st.console.print()
        _st.console.print(Text(title.lower(), style="dim"))
        _st.console.print(_help_table(rows))
    _st.console.print()
    _st.console.print(Text(_HELP_FOOT, style="dim"))
    _st.console.print(Text(f"  {_STAR_LINE}", style="dim"))
    _st.console.print()

def _show_help_tab():
    fd = sys.stdin.fileno()
    try:
        import termios
        import tty
        import select
        old = termios.tcgetattr(fd)
        sys.stdout.write("\x1b[?1049h\x1b[H\x1b[2J\x1b[?25l")
        sys.stdout.flush()
        try:
            tty.setraw(fd)
            attrs = termios.tcgetattr(fd)
            attrs[1] |= termios.OPOST | termios.ONLCR
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            termios.tcflush(fd, termios.TCIFLUSH)
            _st.console.print()
            _st.console.print(Text(_HELP_INTRO, style="white"))
            for title, rows in _HELP_SECTIONS:
                _st.console.print()
                _st.console.print(Text(title.lower(), style="dim"))
                _st.console.print(_help_table(rows))
            _st.console.print()
            _st.console.print(Text(_HELP_FOOT, style="dim"))
            _st.console.print()
            _st.console.print(Text("esc to cancel", style="dim"))
            _st.console.print()
            sys.stdout.flush()
            while True:
                ch = _ui_input._read_key(fd)
                if not ch:
                    continue
                if ch in ("\x03", "q", "Q"):
                    break
                if ch == "\x1b":
                    if select.select([fd], [], [], 0.05)[0]:
                        ch2 = _ui_input._read_key(fd)
                        if ch2 == "\x1b":
                            break
                        if ch2 in ("[", "O"):
                            while select.select([fd], [], [], 0.03)[0]:
                                _ui_input._read_key(fd)
                    else:
                        break
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except OSError:
                pass
            sys.stdout.write("\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()
    except (OSError, ImportError):
        pass

def show_usage(session, last=None, context=None):
    if sys.stdin.isatty():
        _show_usage_tab(session, last, context)
    else:
        _print_usage_inline(session, last, context)

def _usage_body(session, last=None, context=None):
    from hazzel.pricing import format_usd
    from hazzel.tokens import format_count
    sent = int(session.get("input") or 0)
    received = int(session.get("output") or 0)
    cached = int(session.get("cached") or 0)
    calls = int(session.get("calls") or 0)
    total = sent + received

    header = Text()
    header.append("usage", style="white")
    header.append("  ·  tokens used this conversation", style="dim")
    yield header
    yield Text("")

    if not calls:
        yield Text("  No usage yet — ask Hazzel to read, edit, or run something.", style="dim")
        return

    hero = Text()
    hero.append("  ", style="dim")
    hero.append(f"{total:,}", style="white")
    hero.append(f"  tokens · {calls} call{'s' if calls != 1 else ''}", style="dim")
    yield hero
    cost_line = Text()
    cost_line.append("  cost  ", style="dim")
    if session.get("unknown"):
        cost_line.append(f"{format_usd(session.get('cost'))} across priced calls", style="white")
        cost_line.append(f" · {session['unknown']} call{'s' if session['unknown'] != 1 else ''} unknown pricing", style="dim")
    else:
        cost_line.append(format_usd(session.get("cost")), style="white")
    yield cost_line
    if context:
        try:
            ctx = Text()
            ctx.append("  context  ", style="dim")
            ctx.append(format_context_plain(context[0], context[1]), style="white")
            yield ctx
        except Exception:
            pass
    yield Text("")

    from rich.table import Table  # deferred: only needed when usage body renders

    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", style="dim", width=10)
    table.add_column(justify="right", style="white", width=10)
    table.add_column(justify="left", style="dim")

    table.add_row("↑ sent", format_count(sent), "to the model")
    table.add_row("↓ received", format_count(received), "generated back")
    if cached:
        table.add_row("◇ cached", format_count(cached), "reused · cheaper")
    yield table
    if last and last.get("calls"):
        last_total = (last.get("input") or 0) + (last.get("output") or 0)
        suffix = " · estimated" if last.get("estimated") else ""
        last_line = Text()
        last_line.append("  last turn  ", style="dim")
        last_line.append(f"{format_count(last_total)} tokens{suffix}", style="white")
        yield Text("")
        yield last_line
    elif session.get("estimated"):
        yield Text("  ~ estimated, not billed", style="dim")

def _print_usage_inline(session, last=None, context=None):
    _st.console.print()
    for line in _usage_body(session, last, context):
        _st.console.print(line)
    _st.console.print()
    foot = Text()
    foot.append(" esc ", style="reverse")
    foot.append("  dismiss", style="dim")
    _st.console.print(foot)
    _st.console.print()

def _show_usage_tab(session, last=None, context=None):
    fd = sys.stdin.fileno()
    try:
        import termios
        import tty
        import select
        old = termios.tcgetattr(fd)
        sys.stdout.write("\x1b[?1049h\x1b[H\x1b[2J\x1b[?25l")
        sys.stdout.flush()
        try:
            tty.setraw(fd)
            attrs = termios.tcgetattr(fd)
            attrs[1] |= termios.OPOST | termios.ONLCR
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            termios.tcflush(fd, termios.TCIFLUSH)
            _st.console.print()
            for line in _usage_body(session, last, context):
                _st.console.print(line)
            _st.console.print()
            foot = Text()
            foot.append(" esc ", style="reverse")
            foot.append("  dismiss", style="dim")
            _st.console.print(foot)
            _st.console.print()
            sys.stdout.flush()
            while True:
                ch = _ui_input._read_key(fd)
                if not ch:
                    continue
                if ch in ("\x03", "q", "Q"):
                    break
                if ch == "\x1b":
                    if select.select([fd], [], [], 0.05)[0]:
                        ch2 = _ui_input._read_key(fd)
                        if ch2 == "\x1b":
                            break
                        if ch2 in ("[", "O"):
                            while select.select([fd], [], [], 0.03)[0]:
                                _ui_input._read_key(fd)
                    else:
                        break
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except OSError:
                pass
            sys.stdout.write("\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()
    except (OSError, ImportError):
        _print_usage_inline(session, last, context)

def show_turn_usage(session):
    if not session or not session.get("calls"):
        return
    from hazzel.pricing import format_usd
    from hazzel.tokens import format_count
    total = session.get("input", 0) + session.get("output", 0)
    line = Text()
    line.append("  ", style="dim")
    line.append(f"{format_count(total)} tokens", style="dim")
    cost = session.get("cost")
    if cost is None and session.get("unknown"):
        line.append("  ·  unpriced", style="dim")
    else:
        line.append(f"  ·  {format_usd(cost)} session", style="dim")
        if session.get("unknown"):
            line.append("  ·  +unpriced", style="dim")
    if session.get("estimated"):
        line.append("  ·  ~est", style="dim")
    _st.console.print(line)

def show_budget_warning(lines):
    if isinstance(lines, str):
        lines = [lines]
    for line in lines or []:
        warn = Text()
        warn.append("  budget  ", style="yellow")
        warn.append(str(line), style="yellow")
        _st.console.print(warn)

def show_usage_range(name, totals):
    from hazzel.pricing import format_usd
    from hazzel.tokens import format_count
    _st.console.print()
    head = Text()
    head.append(f"usage · {name}", style="white")
    _st.console.print(head)
    _st.console.print()
    if not totals or not totals.get("calls"):
        _st.console.print(Text("  Nothing logged in this window yet.", style="dim"))
        _st.console.print()
        return
    total = totals.get("input", 0) + totals.get("output", 0)
    _st.console.print(Text(f"  {format_count(total)} tokens · {totals['calls']} calls · {totals.get('sessions', 0)} sessions", style="white"))
    cost = Text()
    cost.append("  cost  ", style="dim")
    cost.append(format_usd(totals.get("cost")), style="white")
    if totals.get("unknown"):
        cost.append(f" · {totals['unknown']} calls unknown pricing", style="dim")
    _st.console.print(cost)
    _st.console.print()

def show_by_model(groups):
    from hazzel.pricing import format_usd
    from hazzel.tokens import format_count
    _st.console.print()
    head = Text()
    head.append("usage · by model", style="white")
    _st.console.print(head)
    _st.console.print()
    if not groups:
        _st.console.print(Text("  Nothing logged yet.", style="dim"))
        _st.console.print()
        return
    from rich.table import Table  # deferred: only needed when model usage table renders

    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left", style="white")
    table.add_column(justify="right", style="dim", width=10)
    table.add_column(justify="right", style="white", width=10)
    table.add_column(justify="right", style="dim", width=12)
    for (provider, model), agg in sorted(groups.items(), key=lambda kv: kv[1].get("cost", 0), reverse=True):
        total = agg.get("input", 0) + agg.get("output", 0)
        cost = format_usd(agg.get("cost")) if not agg.get("unknown") else f"{format_usd(agg.get('cost'))} +?"
        table.add_row(f"{provider}/{model}", format_count(total), f"{agg.get('calls', 0)} calls", cost)
    _st.console.print(table)
    _st.console.print()

def show_summary(summary, trace=None):
    if not summary:
        show_error("No implementation yet — run a task first.")
        _st.console.print("  Try asking Hazzel to inspect, create, or edit files.", style="dim")
        _st.console.print()
        return
    _ui_input.rule()
    title = Text()
    title.append("  summary", style="white")
    title.append("  ·  last implementation", style="dim")
    _st.console.print(title)
    _st.console.print()
    if trace:
        for t in trace:
            if not t.get("success"):
                continue
            name = t.get("tool", "")
            detail = t.get("detail") or ""
            line = Text()
            line.append("    – ", style="dim")
            line.append(name, style="white")
            if detail:
                line.append(f"  {detail}", style="dim")
            _st.console.print(line)
        _st.console.print()
    from hazzel.formatter import print_response  # deferred: pygments chain (~30ms)

    print_response(_st.console, summary)
    _st.console.print()

def show_copied(msg="Copied to clipboard."):
    _st.console.print()
    line = Text()
    line.append("  ", style="dim")
    line.append(msg, style="white")
    _st.console.print(line)
    _st.console.print()

def show_export(path):
    _st.console.print()
    line = Text()
    line.append("  Exported to ", style="dim")
    line.append(str(path), style="white")
    _st.console.print(line)
    _st.console.print()

def show_skills(skills):
    _ui_input.rule()
    title = Text()
    title.append("  skills", style="white")
    title.append(f"  ·  {len(skills or [])} installed", style=DIM_COLOR)
    _st.console.print(title)
    if not skills:
        _st.console.print(Text("  No skills installed.", style=DIM_COLOR))
        _st.console.print(Text("  Add one at .hazzel/skills/<name>/SKILL.md (frontmatter: name, description).", style=DIM_COLOR))
    else:
        for s in skills:
            row = Text()
            row.append("  ❯ ", style=DIM_COLOR)
            row.append(s.get("name", ""), style="white")
            row.append(f"  ·  {s.get('source', '')}", style=DIM_COLOR)
            _st.console.print(row)
            desc = (s.get("description") or "no description").strip()
            if desc:
                _st.console.print(Text(f"     {desc[:140]}", style=DIM_COLOR))
        _st.console.print(Text("  /skills to pick · /skills <name> to preview", style=DIM_COLOR))
    _ui_input.rule()

def show_skill_detail(name, body):
    _ui_input.rule()
    title = Text()
    title.append(f"  skill: {name}", style="white")
    _st.console.print(title)
    for line in (body or "").splitlines()[:60]:
        _st.console.print(Text(f"  {line[:160]}", style="white" if line.strip() else DIM_COLOR))
    if len((body or "").splitlines()) > 60:
        _st.console.print(Text(f"  …{len(body.splitlines()) - 60} more lines", style=DIM_COLOR))
    _ui_input.rule()

def show_logout():
    text = Text()
    text.append("  ○ ", style=DIM_COLOR)
    text.append("Saved API keys cleared", style="dim")
    _st.console.print(text)
    _st.console.print("  Run /model to set a new key.", style="dim")
    _st.console.print()

def select_model(catalog, current_id=None):
    idx = 0
    for i, m in enumerate(catalog):
        if m["id"] == current_id:
            idx = i
            break
    if sys.stdin.isatty():
        try:
            import termios
            import tty
            import select
            max_len = max(len(m["display_name"]) for m in catalog)
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            selected = idx
            rendered = 0
            try:
                tty.setraw(fd)
                termios.tcflush(fd, termios.TCIFLUSH)
                sys.stdout.write("\x1b[?25l")
                sys.stdout.flush()
                while True:
                    title = "  \x1b[2mSelect model\x1b[0m"
                    lines = []
                    lines.append("")
                    lines.append(title)
                    lines.append("")
                    visible = 5
                    total = len(catalog)
                    start = max(0, min(selected - visible // 2, total - visible))
                    end = min(total, start + visible)
                    if end - start < visible:
                        start = max(0, end - visible)
                    for idx in range(start, end):
                        m = catalog[idx]
                        mid = m["id"]
                        prov = f"[{m['provider'].lower()}]"
                        is_cur = m["id"] == current_id
                        is_sel = idx == selected
                        base = f"{mid} {prov}"
                        if is_cur:
                            base += " · current"
                        if is_sel:
                            base += " ✓" if is_cur else ""
                            lines.append(f"  \x1b[1m\x1b[97m❯ {base}\x1b[0m")
                        else:
                            lines.append(f"    \x1b[2m{base}\x1b[0m")
                    lines.append("")
                    lines.append(f"  \x1b[2m({selected + 1}/{total})\x1b[0m")
                    lines.append("")
                    cur_name = catalog[selected]["display_name"]
                    lines.append(f"  \x1b[2mModel Name: {cur_name}\x1b[0m")
                    lines.append("")
                    lines.append("  \x1b[2m↑↓ navigate · Enter confirm · Esc cancel\x1b[0m")
                    lines.append("")
                    out = "\r\n".join(lines)
                    redraw = "\r\n".join("\x1b[2K\r" + line for line in lines)
                    nlines = out.count("\r\n")
                    if rendered == 0:
                        sys.stdout.write(out)
                    else:
                        sys.stdout.write(f"\x1b[{rendered}A")
                        sys.stdout.write(redraw)
                    sys.stdout.flush()
                    rendered = nlines
                    ch = _ui_input._read_key(fd)
                    if ch == "\x03":
                        sys.stdout.write(f"\x1b[{rendered}A")
                        sys.stdout.write("\x1b[J")
                        return None
                    if ch == "\x1b":
                        if select.select([fd], [], [], 0.04)[0]:
                            ch2 = _ui_input._read_key(fd)
                            if ch2 in ("[", "O"):
                                if select.select([fd], [], [], 0.02)[0]:
                                    ch3 = _ui_input._read_key(fd)
                                    if ch3 == "A":
                                        selected = (selected - 1) % len(catalog)
                                        continue
                                    if ch3 == "B":
                                        selected = (selected + 1) % len(catalog)
                                        continue
                            elif ch2 == "\x1b":
                                sys.stdout.write(f"\x1b[{rendered}A")
                                sys.stdout.write("\x1b[J")
                                return None
                        else:
                            sys.stdout.write(f"\x1b[{rendered}A")
                            sys.stdout.write("\x1b[J")
                            return None
                    elif ch in ("\r", "\n"):
                        sys.stdout.write(f"\x1b[{rendered}A")
                        sys.stdout.write("\x1b[J")
                        return catalog[selected]
                    elif ch in ("k", "K"):
                        selected = (selected - 1) % len(catalog)
                        continue
                    elif ch in ("j", "J"):
                        selected = (selected + 1) % len(catalog)
                        continue
                    elif ch.isdigit() and ch != "0":
                        n = int(ch) - 1
                        if 0 <= n < len(catalog):
                            selected = n
                            continue
                        if ch == "8" and len(catalog) >= 8:
                            selected = 7
                            continue
            except (KeyboardInterrupt, EOFError):
                try:
                    sys.stdout.write(f"\x1b[{rendered}A")
                    sys.stdout.write("\x1b[J")
                except OSError:
                    sys.stdout.write("\r\n")
                return None
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
                except OSError:
                    pass
                sys.stdout.write("\x1b[?25h\x1b[?12h")
                sys.stdout.flush()
        except (OSError, ImportError):
            pass
    _st.console.print()
    _st.console.print("  Select model", style="dim")
    _st.console.print()
    max_len = max(len(m["display_name"]) for m in catalog)
    for i, m in enumerate(catalog):
        pad = m["display_name"].ljust(max_len)
        text = Text()
        text.append("  ")
        if i == idx:
            text.append("❯ ", style="white")
            text.append(f"{i+1}. ", style="dim")
            text.append(pad, style="white")
        else:
            text.append("  ")
            text.append(f"{i+1}. ", style="dim")
            text.append(pad, style="white")
        text.append(f"  ({m['provider_display']})", style="dim")
        _st.console.print(text)
    _st.console.print()
    _st.console.print("  Enter number · Esc cancel", style="dim")
    _st.console.print()
    try:
        raw = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        _st.console.print()
        return None
    if not raw:
        return None
    try:
        n = int(raw) - 1
        if 0 <= n < len(catalog):
            return catalog[n]
    except ValueError:
        for m in catalog:
            if m["display_name"].lower() == raw.lower() or m["id"] == raw:
                return m
    return None

def select_skill(skills):
    skills = list(skills or [])
    if not skills:
        _st.console.print()
        _st.console.print(Text("  No skills installed.", style=DIM_COLOR))
        _st.console.print(Text("  Add one at .hazzel/skills/<name>/SKILL.md (frontmatter: name, description).", style=DIM_COLOR))
        _st.console.print()
        return None
    if sys.stdin.isatty():
        try:
            import termios
            import tty
            import select
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            selected = 0
            rendered = 0
            try:
                tty.setraw(fd)
                termios.tcflush(fd, termios.TCIFLUSH)
                sys.stdout.write("\x1b[?25l")
                sys.stdout.flush()
                while True:
                    lines = []
                    lines.append("")
                    lines.append("  \x1b[2mSelect skill\x1b[0m")
                    lines.append("")
                    visible = 8
                    total = len(skills)
                    start = max(0, min(selected - visible // 2, total - visible))
                    end = min(total, start + visible)
                    if end - start < visible:
                        start = max(0, end - visible)
                    for idx in range(start, end):
                        name = skills[idx].get("name", "")
                        if idx == selected:
                            lines.append(f"  \x1b[1m\x1b[97m❯ {name}\x1b[0m")
                        else:
                            lines.append(f"    \x1b[2m{name}\x1b[0m")
                    lines.append("")
                    lines.append(f"  \x1b[2m({selected + 1}/{total})\x1b[0m")
                    lines.append("")
                    lines.append("  \x1b[2m↑↓ navigate · Enter select · Esc cancel\x1b[0m")
                    lines.append("")
                    out = "\r\n".join(lines)
                    redraw = "\r\n".join("\x1b[2K\r" + line for line in lines)
                    nlines = out.count("\r\n")
                    if rendered == 0:
                        sys.stdout.write(out)
                    else:
                        sys.stdout.write(f"\x1b[{rendered}A")
                        sys.stdout.write(redraw)
                    sys.stdout.flush()
                    rendered = nlines
                    ch = _ui_input._read_key(fd)
                    if ch == "\x03":
                        sys.stdout.write(f"\x1b[{rendered}A")
                        sys.stdout.write("\x1b[J")
                        return None
                    if ch == "\x1b":
                        if select.select([fd], [], [], 0.04)[0]:
                            ch2 = _ui_input._read_key(fd)
                            if ch2 in ("[", "O"):
                                if select.select([fd], [], [], 0.02)[0]:
                                    ch3 = _ui_input._read_key(fd)
                                    if ch3 == "A":
                                        selected = (selected - 1) % len(skills)
                                        continue
                                    if ch3 == "B":
                                        selected = (selected + 1) % len(skills)
                                        continue
                            elif ch2 == "\x1b":
                                sys.stdout.write(f"\x1b[{rendered}A")
                                sys.stdout.write("\x1b[J")
                                return None
                        else:
                            sys.stdout.write(f"\x1b[{rendered}A")
                            sys.stdout.write("\x1b[J")
                            return None
                    elif ch in ("\r", "\n"):
                        sys.stdout.write(f"\x1b[{rendered}A")
                        sys.stdout.write("\x1b[J")
                        return skills[selected]
                    elif ch in ("k", "K"):
                        selected = (selected - 1) % len(skills)
                        continue
                    elif ch in ("j", "J"):
                        selected = (selected + 1) % len(skills)
                        continue
                    elif ch.isdigit() and ch != "0":
                        n = int(ch) - 1
                        if 0 <= n < len(skills):
                            selected = n
                            continue
            except (KeyboardInterrupt, EOFError):
                try:
                    sys.stdout.write(f"\x1b[{rendered}A")
                    sys.stdout.write("\x1b[J")
                except OSError:
                    sys.stdout.write("\r\n")
                return None
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
                except OSError:
                    pass
                sys.stdout.write("\x1b[?25h\x1b[?12h")
                sys.stdout.flush()
        except (OSError, ImportError):
            pass
    _st.console.print()
    _st.console.print(Text("  Select skill", style="dim"))
    _st.console.print()
    for i, s in enumerate(skills):
        text = Text()
        text.append("  ")
        if i == 0:
            text.append("❯ ", style=f"bold {HAZZEL_COLOR}")
        else:
            text.append("  ", style=DIM_COLOR)
        text.append(f"{i + 1}. ", style="dim")
        text.append(s.get("name", ""), style="bold bright_white")
        _st.console.print(text)
    _st.console.print()
    _st.console.print(Text("  Enter number · empty cancel", style="dim"))
    _st.console.print()
    try:
        raw = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        _st.console.print()
        return None
    if not raw:
        return None
    try:
        n = int(raw) - 1
        if 0 <= n < len(skills):
            return skills[n]
    except ValueError:
        for s in skills:
            if s.get("name", "").lower() == raw.lower():
                return s
    return None

def _mask_key(key):
    if not key or len(key) <= 8:
        return "••••"
    return "•" * 8 + key[-4:]

def prompt_api_key(existing=None):
    if existing and existing.strip():
        _st.console.print(f"  API Key: {_mask_key(existing.strip())} (press Enter to keep)", style="dim")
        _st.console.print("  API Key: ", end="")
    else:
        _st.console.print("  API Key: ", end="")
    sys.stdout.flush()
    if sys.stdin.isatty():
        try:
            import termios
            import tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            key = ""
            try:
                tty.setraw(fd)
                termios.tcflush(fd, termios.TCIFLUSH)
                while True:
                    ch = _ui_input._read_key(fd)
                    if ch in ("\r", "\n"):
                        sys.stdout.write("\r\n")
                        break
                    if ch == "\x03":
                        raise KeyboardInterrupt
                    if ch in ("\x7f", "\x08"):
                        if key:
                            key = key[:-1]
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                        continue
                    if ch == "\x1b":
                        continue
                    if ch == "\x15":
                        while key:
                            key = key[:-1]
                            sys.stdout.write("\b \b")
                        sys.stdout.flush()
                        continue
                    if ch and ch.isprintable():
                        key += ch
                        sys.stdout.write("•")
                        sys.stdout.flush()
            except KeyboardInterrupt:
                sys.stdout.write("\r\n")
                return None
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
                except OSError:
                    pass
                sys.stdout.write("\x1b[?25h\x1b[?12h")
                sys.stdout.flush()
            return key
        except (OSError, ImportError):
            pass
    try:
        import getpass
        val = getpass.getpass("")
        _st.console.print()
        return val
    except (EOFError, KeyboardInterrupt):
        _st.console.print()
        return None
    except OSError:
        try:
            val = input()
            return val
        except (EOFError, KeyboardInterrupt):
            return None
        except OSError:
            return ""
