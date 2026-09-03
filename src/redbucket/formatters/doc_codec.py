"""skill / plugin / subagent / instructions 的编解码。"""
from __future__ import annotations

from redbucket.formatters.frontmatter import (
    FrontmatterError,
    dump_frontmatter,
    parse_frontmatter,
)
from redbucket.formatters.models import CanonicalDoc, TranslatedTree
from redbucket.formatters.textutil import (
    basename_of,
    decode_utf8,
    find_named,
    first_markdown,
)

NOTES_HEADER = "## Compatibility notes"


def _ordered_fields(doc: CanonicalDoc) -> dict[str, str]:
    fields = {"name": doc.name, "description": doc.description}
    for key in sorted(doc.extras):
        fields[key] = doc.extras[key]
    return fields


def decode_doc(
    files: dict[str, bytes],
    mains: tuple[str, ...],
) -> CanonicalDoc:
    found = find_named(files, mains)
    if found is None:
        found_md = first_markdown(files)
        if found_md is None:
            raise FrontmatterError("main file missing")
        path, text = found_md
    else:
        path, payload = found
        text = decode_utf8(payload)
    fields, body = parse_frontmatter(text)
    extras = {
        key: value
        for key, value in fields.items()
        if key not in ("name", "description")
    }
    aux: dict[str, bytes] = {}
    for aux_path, content in files.items():
        if aux_path != path:
            aux[basename_of(aux_path)] = content
    return CanonicalDoc(
        name=fields.get("name", ""),
        description=fields.get("description", ""),
        body=body,
        extras=extras,
        aux_files=aux,
        source_main=basename_of(path),
    )


def encode_doc(doc: CanonicalDoc, main_name: str) -> TranslatedTree:
    notes_lines: list[str] = []
    body = doc.body
    lossy = False
    if doc.extras:
        lossy = True
        notes_lines.append("Unmapped source fields:")
        for key in sorted(doc.extras):
            notes_lines.append(f"- {key}: {doc.extras[key]}")
        if NOTES_HEADER not in body:
            body = body.rstrip() + "\n\n" + NOTES_HEADER + "\n"
            for key in sorted(doc.extras):
                body += f"- {key}: {doc.extras[key]}\n"
    core = CanonicalDoc(
        name=doc.name,
        description=doc.description,
        body=body,
        extras={},
    )
    text = dump_frontmatter(_ordered_fields(core), core.body)
    files: dict[str, bytes] = {main_name: text.encode("utf-8")}
    for aux_name, content in sorted(doc.aux_files.items()):
        if aux_name == main_name:
            continue
        files[aux_name] = content
    return TranslatedTree(
        files=files,
        lossy=lossy,
        notes="\n".join(notes_lines),
        filename=main_name,
    )


def decode_instructions(files: dict[str, bytes]) -> CanonicalDoc:
    found = first_markdown(files)
    if found is None:
        raise FrontmatterError("instructions markdown missing")
    path, text = found
    name = basename_of(path)
    return CanonicalDoc(
        name=name,
        description="",
        body=text,
        source_main=name,
    )


def encode_instructions(doc: CanonicalDoc, main_name: str) -> TranslatedTree:
    body = doc.body
    if not body.endswith("\n"):
        body += "\n"
    files = {main_name: body.encode("utf-8")}
    for aux_name, content in sorted(doc.aux_files.items()):
        files[aux_name] = content
    return TranslatedTree(
        files=files,
        lossy=False,
        notes="",
        filename=main_name,
    )
