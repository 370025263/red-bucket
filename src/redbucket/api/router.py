"""43 个 catalog 端点。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from redbucket.api.deps import PageSpec, bearer_token, get_app
from redbucket.api.schemas import (
    CreateAssetIn,
    CreateBucketIn,
    CreateCommentIn,
    CreateCopyIn,
    CreateIssueIn,
    CreatePullIn,
    DeviceDecideIn,
    DevicePollIn,
    DeviceStartIn,
    EmptyIn,
    LoginIn,
    LogoutIn,
    PatchBucketIn,
    PatchIssueIn,
    PatchMeIn,
    RegisterIn,
    file_dicts,
)
from redbucket.service import RedBucket

API = APIRouter(prefix="/api/v1")


def _core(request: Request) -> RedBucket:
    return get_app(request)


def _viewer(request: Request, core: RedBucket):
    token = bearer_token(request)
    return core.optional_user(token)


def _created(body: dict, location: str) -> JSONResponse:
    return JSONResponse(
        status_code=201,
        content=body,
        headers={"Location": location},
    )


def _lossy_headers(lossy: bool) -> dict[str, str]:
    return {"X-Red-Bucket-Lossy": "true" if lossy else "false"}


@API.post("/auth/register")
def register(payload: RegisterIn, request: Request) -> JSONResponse:
    core = _core(request)
    body = core.register(payload.username, payload.email, payload.password)
    return _created(body, f"/api/v1/users/{body['username']}")


@API.post("/auth/login")
def login(payload: LoginIn, request: Request) -> dict:
    return _core(request).login(payload.email, payload.password)


@API.post("/auth/logout", status_code=204)
def logout(request: Request, payload: LogoutIn | None = None) -> Response:
    del payload
    token = bearer_token(request)
    _core(request).logout(token or "")
    return Response(status_code=204)


@API.post("/auth/device", status_code=201)
def device_start(payload: DeviceStartIn, request: Request) -> dict:
    return _core(request).start_device(payload.client)


@API.post("/auth/device/token")
def device_token(payload: DevicePollIn, request: Request) -> dict:
    return _core(request).poll_device(payload.device_code)


@API.get("/auth/device/{user_code}")
def device_show(user_code: str, request: Request) -> dict:
    return _core(request).device_pending(user_code)


@API.post("/auth/device/{user_code}/decision")
def device_decision(
    user_code: str,
    payload: DeviceDecideIn,
    request: Request,
) -> dict:
    core = _core(request)
    viewer = core.optional_user(bearer_token(request))
    return core.decide_device(user_code, viewer, payload.approve)


@API.get("/users/me")
def users_me(request: Request) -> dict:
    token = bearer_token(request)
    return _core(request).me(token or "")


@API.patch("/users/me")
def patch_me(payload: PatchMeIn, request: Request) -> dict:
    token = bearer_token(request)
    return _core(request).patch_me(token or "", payload.username)


@API.get("/users/{username}")
def public_user(username: str, request: Request) -> dict:
    return _core(request).public_profile(username)


@API.get("/users/{username}/buckets")
def list_buckets(
    username: str,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
) -> dict:
    core = _core(request)
    return core.list_buckets(
        username,
        _viewer(request, core),
        paging.page,
        paging.per_page,
    )


@API.post("/users/{username}/buckets")
def create_bucket(
    username: str,
    payload: CreateBucketIn,
    request: Request,
) -> JSONResponse:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    body = core.create_bucket(
        username,
        viewer,
        payload.name,
        payload.visibility,
        payload.description,
        payload.template,
    )
    loc = f"/api/v1/users/{username}/buckets/{body['name']}"
    return _created(body, loc)


@API.get("/users/{username}/buckets/{bucket}")
def get_bucket(username: str, bucket: str, request: Request) -> dict:
    core = _core(request)
    return core.get_bucket(username, bucket, _viewer(request, core))


@API.patch("/users/{username}/buckets/{bucket}")
def patch_bucket(
    username: str,
    bucket: str,
    payload: PatchBucketIn,
    request: Request,
) -> dict:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    return core.patch_bucket(
        username,
        bucket,
        viewer,
        payload.visibility,
        payload.description,
    )


@API.delete("/users/{username}/buckets/{bucket}", status_code=204)
def delete_bucket(username: str, bucket: str, request: Request) -> Response:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    core.delete_bucket(username, bucket, viewer)
    return Response(status_code=204)


@API.get("/templates")
def templates(
    request: Request,
    paging: Annotated[PageSpec, Depends()],
) -> dict:
    return _core(request).templates_page(paging.page, paging.per_page)


@API.get("/templates/{name}")
def template_one(name: str, request: Request) -> dict:
    return _core(request).template_one(name)


@API.get("/users/{username}/buckets/{bucket}/assets")
def list_assets(
    username: str,
    bucket: str,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
    type: str | None = None,
    source_harness: str | None = None,
) -> dict:
    core = _core(request)
    return core.list_assets(
        username,
        bucket,
        _viewer(request, core),
        paging.page,
        paging.per_page,
        type,
        source_harness,
    )


@API.post("/users/{username}/buckets/{bucket}/assets")
def create_asset(
    username: str,
    bucket: str,
    payload: CreateAssetIn,
    request: Request,
) -> JSONResponse:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    body = core.create_asset(
        username,
        bucket,
        viewer,
        payload.type,
        payload.source_harness,
        payload.path,
        file_dicts(payload.files),
    )
    loc = (
        f"/api/v1/users/{username}/buckets/{bucket}"
        f"/assets/{body['id']}"
    )
    return _created(body, loc)


@API.get("/users/{username}/buckets/{bucket}/assets/{asset_id}")
def get_asset(
    username: str,
    bucket: str,
    asset_id: int,
    request: Request,
) -> dict:
    core = _core(request)
    return core.get_asset(
        username,
        bucket,
        asset_id,
        _viewer(request, core),
    )


@API.delete(
    "/users/{username}/buckets/{bucket}/assets/{asset_id}",
    status_code=204,
)
def delete_asset(
    username: str,
    bucket: str,
    asset_id: int,
    request: Request,
) -> Response:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    core.delete_asset(username, bucket, asset_id, viewer)
    return Response(status_code=204)


@API.get("/users/{username}/buckets/{bucket}/assets/{asset_id}/raw")
def raw_asset(
    username: str,
    bucket: str,
    asset_id: int,
    request: Request,
    commit: str | None = None,
) -> Response:
    core = _core(request)
    payload, media = core.raw_asset(
        username,
        bucket,
        asset_id,
        _viewer(request, core),
        commit,
    )
    return Response(content=payload, media_type=media)


@API.get("/users/{username}/buckets/{bucket}/tree")
def tree_root(
    username: str,
    bucket: str,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
    commit: str | None = None,
) -> dict:
    core = _core(request)
    return core.tree_page(
        username,
        bucket,
        _viewer(request, core),
        paging.page,
        paging.per_page,
        "",
        commit,
    )


@API.get("/users/{username}/buckets/{bucket}/tree/{path:path}")
def tree_path(
    username: str,
    bucket: str,
    path: str,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
    commit: str | None = None,
) -> dict:
    core = _core(request)
    return core.tree_page(
        username,
        bucket,
        _viewer(request, core),
        paging.page,
        paging.per_page,
        path,
        commit,
    )


@API.get("/users/{username}/buckets/{bucket}/blob/{path:path}")
def blob_path(
    username: str,
    bucket: str,
    path: str,
    request: Request,
    commit: str | None = None,
    encoding: str | None = None,
) -> dict:
    core = _core(request)
    return core.blob(
        username,
        bucket,
        _viewer(request, core),
        path,
        commit,
        encoding,
    )


@API.get("/users/{username}/buckets/{bucket}/commits")
def list_commits(
    username: str,
    bucket: str,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
) -> dict:
    core = _core(request)
    return core.list_commits(
        username,
        bucket,
        _viewer(request, core),
        paging.page,
        paging.per_page,
    )


@API.get("/users/{username}/buckets/{bucket}/commits/{sha}")
def get_commit(
    username: str,
    bucket: str,
    sha: str,
    request: Request,
) -> dict:
    core = _core(request)
    return core.get_commit(username, bucket, sha, _viewer(request, core))


@API.get("/translation-matrix")
def translation_matrix(
    request: Request,
    paging: Annotated[PageSpec, Depends()],
    asset_type: str | None = None,
    source: str | None = None,
    target: str | None = None,
) -> dict:
    return _core(request).matrix_page(
        paging.page,
        paging.per_page,
        asset_type,
        source,
        target,
    )


@API.get("/users/{username}/buckets/{bucket}/translated")
def translated_bucket(
    username: str,
    bucket: str,
    request: Request,
    target: str | None = None,
    commit: str | None = None,
    strict: str | None = None,
    meta: str | None = None,
) -> Response:
    core = _core(request)
    result = core.translated_bucket(
        username,
        bucket,
        _viewer(request, core),
        target or "",
        commit,
        strict in ("1", "true"),
        meta in ("1", "true"),
    )
    headers = _lossy_headers(result["lossy"])
    if result["kind"] == "meta":
        return JSONResponse(content=result["body"], headers=headers)
    return Response(
        content=result["payload"],
        media_type=result["media"],
        headers=headers,
    )


@API.get("/users/{username}/buckets/{bucket}/assets/{asset_id}/translated")
def translated_asset(
    username: str,
    bucket: str,
    asset_id: int,
    request: Request,
    target: str | None = None,
    commit: str | None = None,
    meta: str | None = None,
) -> Response:
    core = _core(request)
    result = core.translated_asset(
        username,
        bucket,
        asset_id,
        _viewer(request, core),
        target or "",
        commit,
        meta in ("1", "true"),
    )
    headers = _lossy_headers(result["lossy"])
    if result["kind"] == "meta":
        rel = request.url.path
        query = f"target={target or ''}"
        if commit:
            query += f"&commit={commit}"
        headers["Link"] = f"<{rel}?{query}>; rel=contents"
        return JSONResponse(content=result["body"], headers=headers)
    return Response(
        content=result["payload"],
        media_type=result["media"],
        headers=headers,
    )


@API.get("/users/{username}/buckets/{bucket}/install-script")
def install_script(
    username: str,
    bucket: str,
    request: Request,
    target: str | None = None,
) -> Response:
    core = _core(request)
    body = core.install_script(
        username,
        bucket,
        _viewer(request, core),
        target or "",
    )
    accept = request.headers.get("accept", "")
    if "text/plain" in accept:
        return PlainTextResponse(body["script"])
    return JSONResponse(content=body)


@API.get("/users/{username}/buckets/{bucket}/copies")
def list_copies(
    username: str,
    bucket: str,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
) -> dict:
    core = _core(request)
    return core.list_copies(
        username,
        bucket,
        _viewer(request, core),
        paging.page,
        paging.per_page,
    )


@API.post("/users/{username}/buckets/{bucket}/copies")
def create_copy(
    username: str,
    bucket: str,
    payload: CreateCopyIn,
    request: Request,
) -> JSONResponse:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    body = core.create_copy(
        username,
        bucket,
        viewer,
        payload.source_username,
        payload.source_bucket,
        payload.source_asset_id,
        payload.dest_path,
    )
    loc = (
        f"/api/v1/users/{username}/buckets/{bucket}"
        f"/copies/{body['id']}"
    )
    return _created(body, loc)


@API.get("/users/{username}/buckets/{bucket}/copies/{copy_id}")
def get_copy(
    username: str,
    bucket: str,
    copy_id: int,
    request: Request,
) -> dict:
    core = _core(request)
    return core.get_copy(
        username,
        bucket,
        copy_id,
        _viewer(request, core),
    )


@API.get("/users/{username}/buckets/{bucket}/issues")
def list_issues(
    username: str,
    bucket: str,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
    state: str | None = None,
) -> dict:
    core = _core(request)
    return core.list_issues(
        username,
        bucket,
        _viewer(request, core),
        paging.page,
        paging.per_page,
        state,
    )


@API.post("/users/{username}/buckets/{bucket}/issues")
def create_issue(
    username: str,
    bucket: str,
    payload: CreateIssueIn,
    request: Request,
) -> JSONResponse:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    body = core.create_issue(
        username,
        bucket,
        viewer,
        payload.title,
        payload.body,
    )
    loc = (
        f"/api/v1/users/{username}/buckets/{bucket}"
        f"/issues/{body['number']}"
    )
    return _created(body, loc)


@API.get("/users/{username}/buckets/{bucket}/issues/{number}")
def get_issue(
    username: str,
    bucket: str,
    number: int,
    request: Request,
) -> dict:
    core = _core(request)
    return core.get_issue(
        username,
        bucket,
        number,
        _viewer(request, core),
    )


@API.patch("/users/{username}/buckets/{bucket}/issues/{number}")
def patch_issue(
    username: str,
    bucket: str,
    number: int,
    payload: PatchIssueIn,
    request: Request,
) -> dict:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    return core.close_issue(
        username,
        bucket,
        number,
        viewer,
        payload.state,
    )


@API.get("/users/{username}/buckets/{bucket}/issues/{number}/comments")
def list_comments(
    username: str,
    bucket: str,
    number: int,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
) -> dict:
    core = _core(request)
    return core.list_comments(
        username,
        bucket,
        number,
        _viewer(request, core),
        paging.page,
        paging.per_page,
    )


@API.post("/users/{username}/buckets/{bucket}/issues/{number}/comments")
def create_comment(
    username: str,
    bucket: str,
    number: int,
    payload: CreateCommentIn,
    request: Request,
) -> JSONResponse:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    body = core.create_comment(
        username,
        bucket,
        number,
        viewer,
        payload.body,
    )
    loc = (
        f"/api/v1/users/{username}/buckets/{bucket}"
        f"/issues/{number}/comments/{body['id']}"
    )
    return _created(body, loc)


@API.get(
    "/users/{username}/buckets/{bucket}/issues/{number}/comments/{comment_id}"
)
def get_comment(
    username: str,
    bucket: str,
    number: int,
    comment_id: int,
    request: Request,
) -> dict:
    core = _core(request)
    return core.get_comment(
        username,
        bucket,
        number,
        comment_id,
        _viewer(request, core),
    )


@API.get("/users/{username}/buckets/{bucket}/pulls")
def list_pulls(
    username: str,
    bucket: str,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
    state: str | None = None,
) -> dict:
    core = _core(request)
    return core.list_pulls(
        username,
        bucket,
        _viewer(request, core),
        paging.page,
        paging.per_page,
        state,
    )


@API.post("/users/{username}/buckets/{bucket}/pulls")
def create_pull(
    username: str,
    bucket: str,
    payload: CreatePullIn,
    request: Request,
) -> JSONResponse:
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    body = core.create_pull(
        username,
        bucket,
        viewer,
        payload.title,
        payload.body,
        file_dicts(payload.files),
    )
    loc = (
        f"/api/v1/users/{username}/buckets/{bucket}"
        f"/pulls/{body['number']}"
    )
    return _created(body, loc)


@API.get("/users/{username}/buckets/{bucket}/pulls/{number}")
def get_pull(
    username: str,
    bucket: str,
    number: int,
    request: Request,
) -> dict:
    core = _core(request)
    return core.get_pull(username, bucket, number, _viewer(request, core))


@API.get("/users/{username}/buckets/{bucket}/pulls/{number}/files")
def pull_files(
    username: str,
    bucket: str,
    number: int,
    request: Request,
    paging: Annotated[PageSpec, Depends()],
) -> dict:
    core = _core(request)
    return core.pull_files_page(
        username,
        bucket,
        number,
        _viewer(request, core),
        paging.page,
        paging.per_page,
    )


@API.post("/users/{username}/buckets/{bucket}/pulls/{number}/merge")
def merge_pull(
    username: str,
    bucket: str,
    number: int,
    request: Request,
    payload: EmptyIn | None = None,
) -> dict:
    del payload
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    return core.merge_pull(username, bucket, number, viewer)


@API.post("/users/{username}/buckets/{bucket}/pulls/{number}/reject")
def reject_pull(
    username: str,
    bucket: str,
    number: int,
    request: Request,
    payload: EmptyIn | None = None,
) -> dict:
    del payload
    core = _core(request)
    token = bearer_token(request)
    viewer = core.auth_user(token)
    return core.reject_pull(username, bucket, number, viewer)
