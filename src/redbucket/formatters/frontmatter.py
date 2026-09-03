"""确定性 YAML-like frontmatter。不用外部 YAML 库。"""
from __future__ import annotations

BLOCK_CHOMP = ("", "-", "+")
END_OF_HEADER = "\x00"


class FrontmatterError(ValueError):
    pass


def split_frontmatter(text: str) -> tuple[str, str]:
    """切出 frontmatter 原文与正文，不解析字段。"""
    if not text.startswith("---"):
        raise FrontmatterError("missing frontmatter")
    rest = text[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    marker = "\n---"
    closer = rest.find(marker)
    if closer < 0:
        raise FrontmatterError("unclosed frontmatter")
    header = rest[:closer]
    body = rest[closer + len(marker) :]
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    return header, body


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    header, body = split_frontmatter(text)
    fields: dict[str, str] = {}
    pending: str | None = None
    pending_lines: list[str] = []
    folded = False
    # 末行哨兵：不缩进、无冒号，用来收尾最后一个多行值。
    for line in header.splitlines() + [END_OF_HEADER]:
        if pending is not None:
            if not line.strip() or line.startswith((" ", "\t")):
                pending_lines.append(line.strip())
                continue
            if folded:
                joined = " ".join(part for part in pending_lines if part)
            else:
                joined = "\n".join(pending_lines)
            fields[pending] = joined.strip()
            pending = None
            pending_lines = []
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        if raw[:1] in ("|", ">") and raw[1:] in BLOCK_CHOMP:
            pending = key
            pending_lines = []
            folded = raw[0] == ">"
        else:
            # 纯量也可能续行到下一条缩进行，先挂起再收尾。
            pending = key
            pending_lines = [raw]
            folded = True
    return fields, body


def dump_frontmatter(fields: dict[str, str], body: str) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if "\n" in value:
            lines.append(f"{key}: |")
            for part in value.splitlines():
                lines.append(f"  {part}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    header = "\n".join(lines) + "\n"
    if not body:
        return header
    if not body.endswith("\n"):
        return header + body + "\n"
    return header + body
