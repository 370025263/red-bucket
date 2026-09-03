"""列表外壳与错误信封。"""
from __future__ import annotations


def page_envelope(
    items: list,
    page: int,
    per_page: int,
    total: int,
    extra: dict | None = None,
) -> dict:
    has_more = page * per_page < total
    body = {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "has_more": has_more,
        "next_cursor": str(page + 1) if has_more else None,
    }
    if extra:
        body.update(extra)
    return body


def slice_page(items: list, page: int, per_page: int) -> dict:
    total = len(items)
    start = (page - 1) * per_page
    return page_envelope(
        items[start : start + per_page],
        page,
        per_page,
        total,
    )


def error_body(code: str, message: str, details: list | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details if details is not None else [],
        }
    }
