"""Interactive selectors (model, skill) and API-key prompt."""

import sys

from rich.text import Text

from . import _state as _st
from ._state import DIM_COLOR, HAZZEL_COLOR
from . import input as _ui_input

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
