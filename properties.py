from __future__ import annotations

from suggestions import DIRECTIVE_SECTIONS


COMMON_FIELDS = [
    "Description",
    "ExecStart",
    "ExecReload",
    "ExecStop",
    "WorkingDirectory",
    "User",
    "Group",
    "Environment",
    "Restart",
    "WantedBy",
]


def section_for_key(key: str) -> str:
    return DIRECTIVE_SECTIONS.get(key, "Service")
