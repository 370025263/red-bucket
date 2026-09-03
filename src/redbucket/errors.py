"""稳定错误码。没有静默兜底：调用方必须处理 AppError。"""
from __future__ import annotations


class AppError(Exception):
    """面向 API 的失败。status 是 HTTP 状态。"""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: list[dict] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details if details is not None else []


def unauthorized() -> AppError:
    return AppError(401, "unauthorized", "unauthorized")


def not_found() -> AppError:
    return AppError(404, "not_found", "not found")


def forbidden(message: str = "forbidden") -> AppError:
    return AppError(403, "forbidden", message)


def conflict(code: str, message: str) -> AppError:
    return AppError(409, code, message)


def validation_failed(details: list[dict]) -> AppError:
    return AppError(422, "validation_failed", "validation failed", details)


def bucket_quota_exceeded(limit: int, current: int) -> AppError:
    return AppError(
        403,
        "bucket_quota_exceeded",
        "bucket quota exceeded",
        [{"limit": limit, "current": current}],
    )


def bucket_storage_exceeded(usage_bytes: int, limit_bytes: int) -> AppError:
    return AppError(
        413,
        "bucket_storage_exceeded",
        "bucket storage exceeded",
        [{"usage_bytes": usage_bytes, "limit_bytes": limit_bytes}],
    )


def translation_unsupported() -> AppError:
    return AppError(
        501,
        "translation_unsupported",
        "translation pair is not supported",
    )
