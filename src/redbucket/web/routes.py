"""HTML 路由。只读路径 SSR；写操作由页面调 /api/v1/。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.templating import Jinja2Templates

from redbucket.api.deps import bearer_token
from redbucket.catalog_const import HARNESSES
from redbucket.errors import AppError
from redbucket.web.i18n import page_lang, stamp_lang, ui_bundle

WEB = APIRouter()
TEMPLATES: Jinja2Templates | None = None


def format_short_date(stamp: str | None) -> str:
    if not stamp:
        return ""
    text = str(stamp).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return text


def bind_templates(templates: Jinja2Templates) -> None:
    global TEMPLATES
    TEMPLATES = templates
    TEMPLATES.env.filters["short_date"] = format_short_date


def _render(request: Request, name: str, context: dict) -> HTMLResponse:
    if TEMPLATES is None:
        raise RuntimeError("templates not bound")
    lang = page_lang(request)
    packed = dict(context)
    packed["lang"] = lang
    packed["ui"] = ui_bundle(lang)
    packed["origin"] = _core(request).settings.public_origin
    response = TEMPLATES.TemplateResponse(request, name, packed)
    return stamp_lang(request, response)


def _core(request: Request):
    return request.app.state.core


def _viewer(request: Request):
    core = _core(request)
    token = bearer_token(request)
    return core.optional_user(token)


def _not_found(request: Request) -> HTMLResponse:
    if TEMPLATES is None:
        raise RuntimeError("templates not bound")
    lang = page_lang(request)
    response = TEMPLATES.TemplateResponse(
        request,
        "not_found.html",
        {
            "lang": lang,
            "ui": ui_bundle(lang),
            "origin": _core(request).settings.public_origin,
        },
        status_code=404,
    )
    return stamp_lang(request, response)


def _safe_bucket(request: Request, username: str, bucket: str):
    core = _core(request)
    try:
        return core.get_bucket(username, bucket, _viewer(request))
    except AppError:
        return None


@WEB.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return _render(request, "home.html", {})


@WEB.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return _render(request, "login.html", {})


@WEB.get("/register", response_class=HTMLResponse)
def register_page(request: Request) -> HTMLResponse:
    return _render(request, "register.html", {})


@WEB.get("/new", response_class=HTMLResponse)
def new_bucket_page(request: Request) -> HTMLResponse:
    return _render(request, "new_bucket.html", {})


@WEB.get("/link", response_class=HTMLResponse)
def link_page(request: Request) -> HTMLResponse:
    """Where the agent's link lands. A code typed here goes to /link/CODE."""
    typed = (request.query_params.get("code") or "").strip().upper()
    if typed:
        return RedirectResponse(f"/link/{typed}", status_code=303)
    return _render(request, "link.html", {})


@WEB.get("/link/{user_code}", response_class=HTMLResponse)
def link_decide_page(user_code: str, request: Request) -> HTMLResponse:
    core = _core(request)
    try:
        core.device_pending(user_code)
    except AppError:
        return _not_found(request)
    return _render(
        request,
        "link_decide.html",
        {"user_code": user_code.strip().upper()},
    )


@WEB.get("/{username}", response_class=HTMLResponse)
def user_page(username: str, request: Request) -> HTMLResponse:
    core = _core(request)
    try:
        profile = core.public_profile(username)
    except AppError:
        return _not_found(request)
    listing = core.list_buckets(username, _viewer(request), 1, 100)
    return _render(
        request,
        "user.html",
        {"profile": profile, "buckets": listing["items"]},
    )


def _code_page(
    request: Request,
    username: str,
    bucket: str,
    rel_path: str,
) -> HTMLResponse:
    core = _core(request)
    viewer = _viewer(request)
    try:
        data = core.get_bucket(username, bucket, viewer)
        tree = core.tree_page(
            username,
            bucket,
            viewer,
            1,
            100,
            rel_path,
            None,
        )
    except AppError:
        return _not_found(request)
    readme_html = ""
    readme_path = ""
    for entry in tree["items"]:
        is_readme = entry["name"].lower() == "readme.md"
        if is_readme and entry["entry_type"] == "file":
            blob = core.blob(
                username,
                bucket,
                viewer,
                entry["path"],
                None,
                "text",
            )
            if blob["content_text"]:
                readme_html = core.markdown_html(blob["content_text"])
                readme_path = entry["path"]
            break
    crumbs = []
    if rel_path:
        parts = rel_path.split("/")
        acc = []
        for index, part in enumerate(parts):
            acc.append(part)
            href = None
            if index < len(parts) - 1:
                href = f"/{username}/{bucket}/tree/" + "/".join(acc)
            crumbs.append({"name": part, "href": href})
    return _render(
        request,
        "bucket_code.html",
        {
            "bucket": data,
            "entries": tree["items"],
            "latest_commit": tree.get("latest_commit"),
            "commit_count": tree.get("commit_count", 0),
            "readme_html": readme_html,
            "readme_path": readme_path,
            "crumbs": crumbs,
        },
    )


@WEB.get("/{username}/{bucket}", response_class=HTMLResponse)
def bucket_page(
    username: str,
    bucket: str,
    request: Request,
) -> HTMLResponse:
    return _code_page(request, username, bucket, "")


@WEB.get("/{username}/{bucket}/guide.md", response_class=PlainTextResponse)
def guide_page(
    username: str,
    bucket: str,
    request: Request,
) -> PlainTextResponse:
    """Hand this URL to an agent; it is the whole install story."""
    if TEMPLATES is None:
        raise RuntimeError("templates not bound")
    core = _core(request)
    viewer = _viewer(request)
    data = _safe_bucket(request, username, bucket)
    if data is None:
        return PlainTextResponse("Not found\n", status_code=404)
    listing = core.list_assets(
        username,
        bucket,
        viewer,
        1,
        100,
        None,
        None,
    )
    body = TEMPLATES.get_template("guide.md").render(
        bucket=data,
        assets=listing["items"],
        harnesses=HARNESSES,
        origin=core.settings.public_origin,
    )
    return PlainTextResponse(
        body,
        media_type="text/markdown; charset=utf-8",
    )


@WEB.get("/{username}/{bucket}/tree/{path:path}", response_class=HTMLResponse)
def tree_page(
    username: str,
    bucket: str,
    path: str,
    request: Request,
) -> HTMLResponse:
    return _code_page(request, username, bucket, path)


@WEB.get("/{username}/{bucket}/blob/{path:path}", response_class=HTMLResponse)
def blob_page(
    username: str,
    bucket: str,
    path: str,
    request: Request,
) -> HTMLResponse:
    core = _core(request)
    viewer = _viewer(request)
    data = _safe_bucket(request, username, bucket)
    if data is None:
        return _not_found(request)
    try:
        blob = core.blob(username, bucket, viewer, path, None, None)
    except AppError:
        return _not_found(request)
    html = ""
    if blob["content_text"] and path.lower().endswith(".md"):
        html = core.markdown_html(blob["content_text"])
    parent = "/".join(path.split("/")[:-1])
    return _render(
        request,
        "blob.html",
        {
            "bucket": data,
            "blob": blob,
            "html": html,
            "parent": parent,
            "binary": blob["content_text"] is None,
        },
    )


@WEB.get("/{username}/{bucket}/commits", response_class=HTMLResponse)
def commits_page(
    username: str,
    bucket: str,
    request: Request,
) -> HTMLResponse:
    core = _core(request)
    data = _safe_bucket(request, username, bucket)
    if data is None:
        return _not_found(request)
    listing = core.list_commits(username, bucket, _viewer(request), 1, 100)
    return _render(
        request,
        "commits.html",
        {"bucket": data, "items": listing["items"]},
    )


@WEB.get("/{username}/{bucket}/commit/{sha}", response_class=HTMLResponse)
def commit_page(
    username: str,
    bucket: str,
    sha: str,
    request: Request,
) -> HTMLResponse:
    core = _core(request)
    data = _safe_bucket(request, username, bucket)
    if data is None:
        return _not_found(request)
    try:
        detail = core.get_commit(username, bucket, sha, _viewer(request))
    except AppError:
        return _not_found(request)
    return _render(
        request,
        "commit.html",
        {"bucket": data, "commit": detail},
    )


@WEB.get("/{username}/{bucket}/issues", response_class=HTMLResponse)
def issues_page(
    username: str,
    bucket: str,
    request: Request,
) -> HTMLResponse:
    core = _core(request)
    data = _safe_bucket(request, username, bucket)
    if data is None:
        return _not_found(request)
    listing = core.list_issues(
        username,
        bucket,
        _viewer(request),
        1,
        100,
        None,
    )
    return _render(
        request,
        "issues.html",
        {"bucket": data, "items": listing["items"]},
    )


@WEB.get("/{username}/{bucket}/issues/{number}", response_class=HTMLResponse)
def issue_page(
    username: str,
    bucket: str,
    number: int,
    request: Request,
) -> HTMLResponse:
    core = _core(request)
    data = _safe_bucket(request, username, bucket)
    if data is None:
        return _not_found(request)
    try:
        issue = core.get_issue(username, bucket, number, _viewer(request))
        comments = core.list_comments(
            username,
            bucket,
            number,
            _viewer(request),
            1,
            100,
        )
    except AppError:
        return _not_found(request)
    return _render(
        request,
        "issue.html",
        {
            "bucket": data,
            "issue": issue,
            "comments": [
                dict(item, body_html=core.markdown_html(item["body"] or ""))
                for item in comments["items"]
            ],
            "body_html": core.markdown_html(issue["body"] or ""),
        },
    )


@WEB.get("/{username}/{bucket}/pulls", response_class=HTMLResponse)
def pulls_page(
    username: str,
    bucket: str,
    request: Request,
) -> HTMLResponse:
    core = _core(request)
    data = _safe_bucket(request, username, bucket)
    if data is None:
        return _not_found(request)
    listing = core.list_pulls(
        username,
        bucket,
        _viewer(request),
        1,
        100,
        None,
    )
    return _render(
        request,
        "pulls.html",
        {"bucket": data, "items": listing["items"]},
    )


@WEB.get("/{username}/{bucket}/pulls/{number}", response_class=HTMLResponse)
def pull_page(
    username: str,
    bucket: str,
    number: int,
    request: Request,
) -> HTMLResponse:
    core = _core(request)
    data = _safe_bucket(request, username, bucket)
    if data is None:
        return _not_found(request)
    try:
        pull = core.get_pull(username, bucket, number, _viewer(request))
    except AppError:
        return _not_found(request)
    return _render(
        request,
        "pull.html",
        {
            "bucket": data,
            "pull": pull,
            "body_html": core.markdown_html(pull["body"] or ""),
        },
    )


@WEB.get("/{username}/{bucket}/settings", response_class=HTMLResponse)
def settings_page(
    username: str,
    bucket: str,
    request: Request,
) -> HTMLResponse:
    data = _safe_bucket(request, username, bucket)
    if data is None:
        return _not_found(request)
    viewer = _viewer(request)
    if viewer is not None and viewer["username"] != data["username"]:
        return _not_found(request)
    if viewer is None:
        safe_data = {
            "username": data["username"],
            "name": data["name"],
            "full_name": data["full_name"],
            "visibility": data["visibility"],
            "open_issues_count": data["open_issues_count"],
            "open_pulls_count": data["open_pulls_count"],
            "usage_bytes": 0,
            "limit_bytes": data["limit_bytes"],
            "description": "",
        }
        return _render(request, "settings.html", {"bucket": safe_data})
    return _render(request, "settings.html", {"bucket": data})
