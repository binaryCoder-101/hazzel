"""Git panels — diff, status, log, commit flow, file viewer.

Import from the submodules directly. This package re-exports everything so
``from hazzel.ui.git import show_diff`` keeps working.
"""

# ruff: noqa: F401 — re-export shim.
from .commit import (
    prompt_suggest_action,
    prompt_suggest_edit,
    show_git_commit,
    show_git_suggest,
    show_review,
)
from .diff import (
    _count_diff_marks,
    prompt_diff_selection,
    show_diff,
    show_file_viewer,
    show_git_diff,
    show_git_file_diff,
)
from .log import (
    _LOG_LINE_RE,
    _LOG_SUBJECT_RE,
    _LOG_TYPE_COLORS,
    _style_log_refs,
    _style_log_subject,
    show_git_log,
)
from .status import (
    _GIT_STATUS_ICONS,
    show_git_file_list,
    show_git_status,
)
