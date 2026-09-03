"""翻译中间表示。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CanonicalDoc:
    name: str
    description: str
    body: str
    extras: dict[str, str] = field(default_factory=dict)
    aux_files: dict[str, bytes] = field(default_factory=dict)
    source_main: str = ""


@dataclass
class CanonicalMcp:
    name: str
    transport: str
    command: str = ""
    args_text: str = ""
    url: str = ""
    extras: dict[str, str] = field(default_factory=dict)
    raw_kind: str = "json"


@dataclass
class TranslatedTree:
    files: dict[str, bytes]
    lossy: bool
    notes: str
    filename: str
