"""请求依赖。"""
from __future__ import annotations

from fastapi import Query, Request

from redbucket.errors import validation_failed
from redbucket.service import RedBucket


def get_app(request: Request) -> RedBucket:
    return request.app.state.core


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    prefix = "bearer "
    if not header.lower().startswith(prefix):
        return None
    return header[7:].strip()


class PageSpec:
    def __init__(
        self,
        request: Request,
        page: int = Query(1),
        per_page: int = Query(30),
    ) -> None:
        if "cursor" in request.query_params:
            raise validation_failed(
                [{"field": "cursor", "issue": "cursor is not supported"}]
            )
        if page < 1:
            raise validation_failed(
                [{"field": "page", "issue": "page must be >= 1"}]
            )
        if per_page > 100:
            raise validation_failed(
                [{"field": "per_page", "issue": "per_page max is 100"}]
            )
        if per_page < 1:
            per_page = 30
        self.page = page
        self.per_page = per_page
