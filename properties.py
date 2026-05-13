from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class PropertyRow:
    key: str
    value: str
    section: str


def section_for_key(key: str) -> str:
    return DIRECTIVE_SECTIONS.get(key, "Service")


def ordered_rows(fields: dict[str, str]) -> list[PropertyRow]:
    return [PropertyRow(key=key, value=fields.get(key, ""), section=section_for_key(key)) for key in COMMON_FIELDS]
