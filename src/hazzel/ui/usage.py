"""Token-usage panels."""

import sys

from rich.text import Text

from . import _state as _st
from . import input as _ui_input
from .messages import format_context_plain

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
