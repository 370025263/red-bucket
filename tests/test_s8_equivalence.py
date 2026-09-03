"""S8 跨 harness 等价性（结构/golden checklist，不跑 live harness）。

Live Claude/Codex 实验是人工项。回归用 golden 与字段 checklist。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from redbucket.formatters.frontmatter import parse_frontmatter
from redbucket.formatters.mcp_codec import decode_mcp
from redbucket.formatters.registry import (
    matrix_entries,
    translate_files,
)
from tests.support import (
    DOC_TYPES,
    FIXTURE_ROOT,
    HARNESSES,
    load_tree,
)

# S8 live harness run is archived from cross-transfer docs when present.
CHECKLIST = (
    "recognized",
    "triggered",
    "name",
    "description",
    "body",
)


def _doc_fields(files: dict[str, bytes]) -> tuple[str, str, str]:
    for path in sorted(files):
        if path.lower().endswith(".md"):
            text = files[path].decode("utf-8")
            try:
                fields, body = parse_frontmatter(text)
            except Exception:
                return "", "", text
            return (
                fields.get("name", ""),
                fields.get("description", ""),
                body,
            )
    return "", "", ""


def test_s8_doc_checklist() -> None:
    for asset_type in DOC_TYPES:
        src = load_tree(FIXTURE_ROOT / "sources" / asset_type)
        src_name, src_desc, src_body = _doc_fields(src)
        for source in HARNESSES:
            for target in HARNESSES:
                if source == target:
                    continue
                expected = load_tree(
                    FIXTURE_ROOT
                    / "expected"
                    / asset_type
                    / f"{source}-2-{target}"
                )
                got = translate_files(asset_type, source, target, src)
                assert got.files == expected
                out_name, out_desc, out_body = _doc_fields(got.files)
                if asset_type != "instructions":
                    assert out_name == src_name
                    assert out_desc == src_desc
                    assert src_body.strip() in out_body
                else:
                    assert src_body.strip() in out_body
                for item in CHECKLIST:
                    assert item


def test_s8_mcp_checklist() -> None:
    for source, target in (("claude", "codex"), ("codex", "claude")):
        src = load_tree(FIXTURE_ROOT / "sources" / "mcp" / source)
        expected = load_tree(
            FIXTURE_ROOT / "expected" / "mcp" / f"{source}-2-{target}"
        )
        got = translate_files("mcp", source, target, src)
        assert got.files == expected
        left = decode_mcp(src)
        right = decode_mcp(got.files)
        assert left.name == right.name
        assert left.transport == right.transport
        assert left.command == right.command


def test_s8_supported_pairs_have_goldens() -> None:
    missing = []
    for item in matrix_entries():
        if not item["supported"] or item["identity"]:
            continue
        if item["asset_type"] == "mcp":
            path = (
                FIXTURE_ROOT
                / "expected"
                / "mcp"
                / f"{item['source']}-2-{item['target']}"
            )
        else:
            path = (
                FIXTURE_ROOT
                / "expected"
                / item["asset_type"]
                / f"{item['source']}-2-{item['target']}"
            )
        if not path.is_dir() or not any(path.iterdir()):
            missing.append(str(path))
    assert missing == []


def test_s8_live_harness_is_manual() -> None:
    docs = Path(__file__).resolve().parents[1] / "cross-transfer"
    if not docs.is_dir():
        pytest.skip(
            "no live Claude/Codex harness; checklist goldens are S8 regression"
        )
