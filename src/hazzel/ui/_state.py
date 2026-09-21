"""Shared mutable state for the ``hazzel.ui`` package.

Single home for the objects every UI module touches: the rich console,
color tokens, and the spinner/stream/turn flags. Import this module — never
``hazzel.ui`` itself — to avoid import cycles.
"""

import os

from rich.console import Console


def is_no_color() -> bool:
    """Check if NO_COLOR environment variable is set and non-empty (https://no-color.org/)."""
    val = os.getenv("NO_COLOR")
    return bool(val)


class HazzelConsole(Console):
    """Rich Console that dynamically honors the NO_COLOR environment variable."""

    @property
    def no_color(self) -> bool:
        if is_no_color():
            return True
        return getattr(self, "_custom_no_color", False)

    @no_color.setter
    def no_color(self, value: bool) -> None:
        self._custom_no_color = bool(value)

    @property
    def _color_system(self):
        if self.no_color:
            return None
        return getattr(self, "_real_color_system", None)

    @_color_system.setter
    def _color_system(self, val):
        self._real_color_system = val


console = HazzelConsole()

_loader = None

HAZZEL_COLOR = "#ec8500"
USER_COLOR = "#8ab4f8"
SUCCESS_COLOR = "#8fb08f"
ERROR_COLOR = "#c97676"
DIM_COLOR = "dim"

_stream_buffer = ""
_stream_started = None
_stream_first_at = None
_stream_tokens = 0
_stream_last_paint = 0.0
_reason_buffer: list = []
_thinking_streamed = False
_thinking_was_live = False

_tool_rows: list = []
_turn_started = None

_quiet = False
_print_mode = False
_auto_approve = False
