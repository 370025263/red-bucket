"""请求体。响应用 catalog 字段的 dict。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IgnoreExtra(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RegisterIn(IgnoreExtra):
    username: str
    email: str
    password: str


class LoginIn(IgnoreExtra):
    email: str
    password: str


class LogoutIn(IgnoreExtra):
    pass


class DeviceStartIn(IgnoreExtra):
    client: str = ""


class DevicePollIn(IgnoreExtra):
    device_code: str


class DeviceDecideIn(IgnoreExtra):
    approve: bool


class PatchMeIn(IgnoreExtra):
    username: str


class CreateBucketIn(IgnoreExtra):
    name: str
    visibility: str = "private"
    description: str = ""
    template: str | None = None


class PatchBucketIn(IgnoreExtra):
    visibility: str | None = None
    description: str | None = None


class FileIn(IgnoreExtra):
    path: str
    content_text: str | None = None
    content_base64: str | None = None
    delete: bool = False


class CreateAssetIn(IgnoreExtra):
    type: str
    source_harness: str
    path: str
    files: list[FileIn]


class CreateCopyIn(IgnoreExtra):
    source_username: str
    source_bucket: str
    source_asset_id: int
    dest_path: str | None = None


class CreateIssueIn(IgnoreExtra):
    title: str
    body: str = ""


class PatchIssueIn(IgnoreExtra):
    state: str


class CreateCommentIn(IgnoreExtra):
    body: str


class CreatePullIn(IgnoreExtra):
    title: str
    body: str = ""
    files: list[FileIn] = Field(default_factory=list)


class EmptyIn(IgnoreExtra):
    pass


def file_dicts(items: list[FileIn]) -> list[dict]:
    return [item.model_dump() for item in items]
