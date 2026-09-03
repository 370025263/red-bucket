"""Site chrome strings. Product language only; no API catalog.

Keys must not match dict methods (copy, update, get, items, ...).
Jinja {{ ui.copy }} would print the method, not the label.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import Response

LANGS = ("en", "zh")
LANG_COOKIE = "rb_lang"
LANG_YEAR = 31536000

EN_NEW_HINT = (
    "A user/bucket for skills, MCP, instructions, "
    "subagents, or plugins."
)
ZH_NEW_HINT = (
    "一个 user/bucket，用来放 skill、MCP、instructions、"
    "subagent 或 plugin。"
)

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "home": "Home",
        "login": "Login",
        "link_title": "Connect an agent",
        "link_hint": (
            "Type the code your agent showed you. It is two groups "
            "of four, like BQ7K-2M4X."
        ),
        "link_code": "Code",
        "link_continue": "Continue",
        "link_expiry": "Codes last ten minutes.",
        "link_ask": "Let this agent act as you?",
        "link_ask_sub": (
            "Something running on your machine asked to sign in as you."
        ),
        "link_signin": (
            "Sign in first, then you get one more screen to approve "
            "or refuse it."
        ),
        "link_client": "Asked by",
        "link_as": "Signing in as",
        "link_grants": (
            "It will be able to create and delete your buckets, upload "
            "and remove assets, change public or private, and post as "
            "you. It cannot read your password or change your email."
        ),
        "link_warn": (
            "Only approve this if you just asked an agent to sign "
            "you in."
        ),
        "link_approve": "Authorize",
        "link_deny": "Refuse",
        "link_done": (
            "Done. Go back to your agent — it has the token now."
        ),
        "link_refused": "Refused. Nothing was shared.",
        "register": "Register",
        "new_bucket": "New bucket",
        "logout": "Logout",
        "hero_a": "There are many agent hubs",
        "hero_b": "but this one",
        "hero_em": "translates",
        "hero_sub": (
            "A user/bucket hub for skills, MCP, instructions, "
            "subagents, and plugins. Fetch in Claude, Codex, "
            "Agents, or OpenClaw."
        ),
        "ring_label": "Translates between",
        "story1_h": "Why red-bucket?",
        "story1_p": (
            "Author an asset once in the harness you already use. "
            "When another developer or agent pulls it, red-bucket "
            "translates it at fetch time into their format — "
            "deterministic, lossless where the pair supports it, "
            "and explicit whenever something is dropped."
        ),
        "story2_h": "Three ways to consume",
        "story2_a": (
            "copy: pull an asset into a bucket of your own, "
            "with its provenance recorded."
        ),
        "story2_b": (
            "install-script: a self-contained Node program that "
            "fetches the translated assets and unpacks them."
        ),
        "story2_c": (
            "translated fetch: read target-harness bytes straight "
            "into your own toolchain."
        ),
        "story3_h": "Open a bucket",
        "story3_p": (
            "Create a user/bucket, upload your skills, and let any "
            "agent consume them natively in Claude, Codex, Agents, "
            "or OpenClaw. Private buckets stay invisible to "
            "everyone but you."
        ),
        "browse_src": "or browse the source on GitHub",
        "sign_in": "Sign in",
        "sign_in_hint": "Sign in to manage your buckets.",
        "create_account": "Create account",
        "create_hint": "Create an account to publish buckets.",
        "email": "Email",
        "password": "Password",
        "username": "Username",
        "new_here": "New to red-bucket?",
        "have_account": "Already have an account?",
        "new_title": "New bucket",
        "new_hint": EN_NEW_HINT,
        "bucket_name": "Name",
        "visibility": "Visibility",
        "template": "Template",
        "description": "Description",
        "optional": "optional",
        "create": "Create",
        "not_found": "Not found",
        "not_found_hint": "This page does not exist.",
        "back_home": "Back home",
        "tab_code": "Code",
        "tab_issues": "Issues",
        "tab_pulls": "Pull requests",
        "tab_settings": "Settings",
        "about": "About",
        "install": "Install",
        "cta_start": "Create your bucket",
        "cta_alt": "Already have an account?",
        "cta_hero": "Create your bucket now",
        "hero_note": (
            "Without a bucket, it does not survive the trip."
        ),
        "hero_alt": (
            "Three houses labelled claude, codex and agents "
            "stand at the corners of a triangle, with a marked "
            "route along each edge. Small figures walk the "
            "circuit carrying red buckets of assets, stepping "
            "in and out of the door of each house."
        ),
        "way_guide_title": "Give this to your agent",
        "way_guide_hint": (
            "One markdown file. It tells your agent how to install "
            "this bucket in whatever harness it is running, and "
            "offers to set up the red-bucket skill while it is there."
        ),
        "way_guide_open": "Read it",
        "copy_btn": "Copy",
        "copied": "Copied",
        "no_desc": "No description",
        "usage": "Usage",
        "no_assets": "No assets yet",
        "harness_mix": "Harness mix",
        "empty_dir": "This directory is empty.",
        "empty_owner_hint": "Add a README or upload an asset.",
        "readme_hint": "Add a README.md to this directory.",
        "upload": "Upload",
        "add_asset": "Add asset",
        "add_asset_hint": (
            "Write it once in the harness you use. red-bucket "
            "converts it for the others on fetch."
        ),
        "asset_type": "Type",
        "source_harness": "Source harness",
        "asset_path": "Path",
        "main_file": "Main file",
        "content": "Content",
        "commits_word": "commits",
        "no_commits": "No commits yet.",
        "back_dir": "Back to directory",
        "binary_file": "This file is not text; fetch it to read it.",
        "changed_paths": "Changed paths",
        "comments": "Comments",
        "no_comments": "No comments yet.",
        "add_comment": "Add a comment",
        "comment_btn": "Comment",
        "comment_label": "Comment",
        "proposed_files": "Proposed files",
        "merge_btn": "Merge pull request",
        "reject_btn": "Reject",
        "joined": "Joined",
        "public_buckets": "Public buckets",
        "no_public": "No public buckets.",
        "no_issues": "No issues.",
        "no_pulls": "No pull requests.",
        "join_hint": "Sign in to take part.",
        "open_issue": "Open an issue",
        "open_pull": "Open a pull request",
        "title": "Title",
        "body": "Body",
        "file_path": "File path",
        "submit_issue": "Submit issue",
        "submit_pull": "Submit pull request",
        "save": "Save",
        "saved": "Saved",
        "delete_bucket": "Delete this bucket",
        "danger": "Danger",
        "danger_hint": "Deleting a bucket cannot be undone.",
        "confirm_delete": "Type the bucket name to delete it:",
        "general": "General",
        "pw_hint": "at least 8 characters",
    },
    "zh": {
        "home": "首页",
        "login": "登录",
        "link_title": "连接一个 agent",
        "link_hint": "把 agent 给你的那个码填进来，形如 BQ7K-2M4X。",
        "link_code": "验证码",
        "link_continue": "继续",
        "link_expiry": "验证码十分钟内有效。",
        "link_ask": "允许这个 agent 以你的身份操作？",
        "link_ask_sub": "你机器上有个程序请求以你的身份登录。",
        "link_signin": "先登录，然后还会再问你一次要不要同意。",
        "link_client": "请求方",
        "link_as": "登录身份",
        "link_grants": (
            "它将可以建桶删桶、上传和删除资产、改公开或私有、"
            "以你的名义发言。它读不到你的密码，也改不了你的邮箱。"
        ),
        "link_warn": "只有在你刚刚让 agent 登录时才点同意。",
        "link_approve": "同意",
        "link_deny": "拒绝",
        "link_done": "好了，回到你的 agent，令牌已经给它了。",
        "link_refused": "已拒绝，什么都没有给出去。",
        "register": "注册",
        "new_bucket": "新建",
        "logout": "退出",
        "hero_a": "智能体枢纽很多",
        "hero_b": "但这一份会",
        "hero_em": "翻译",
        "hero_sub": (
            "用 user/bucket 放 skill、MCP、instructions、"
            "subagent 和 plugin。取用时按 Claude、Codex、"
            "Agents、OpenClaw 翻译。"
        ),
        "ring_label": "在这几家之间互转",
        "story1_h": "为什么用 red-bucket？",
        "story1_p": (
            "资产按你自己惯用的那一家写一次就行。别人或别的"
            "智能体来取的时候，red-bucket 在取用那一刻把它转成"
            "对方的格式：结果确定，能对上的原样保留，对不上的"
            "明确标出来。"
        ),
        "story2_h": "三种取用方式",
        "story2_a": "把别人的资产复制进自己的桶，来源可追。",
        "story2_b": "一段自包含的 Node 程序，把转好的资产装到本机。",
        "story2_c": "直接取目标那一家的字节，接进自己的工具链。",
        "story3_h": "开一个桶",
        "story3_p": (
            "建一个 user/bucket，把自己的 skill 传上去，"
            "任何智能体都能在 Claude、Codex、Agents 或 OpenClaw "
            "里原生取用。私有桶只有你自己看得见。"
        ),
        "browse_src": "或到 GitHub 看源码",
        "sign_in": "登录",
        "sign_in_hint": "登录后管理自己的桶。",
        "create_account": "注册",
        "create_hint": "注册后即可发布桶。",
        "email": "邮箱",
        "password": "密码",
        "username": "用户名",
        "new_here": "还没有账号？",
        "have_account": "已经有账号？",
        "new_title": "新建桶",
        "new_hint": ZH_NEW_HINT,
        "bucket_name": "名称",
        "visibility": "可见性",
        "template": "模板",
        "description": "说明",
        "optional": "选填",
        "create": "创建",
        "not_found": "Not found",
        "not_found_hint": "没有这个页面。",
        "back_home": "回首页",
        "tab_code": "代码",
        "tab_issues": "议题",
        "tab_pulls": "拉取请求",
        "tab_settings": "设置",
        "about": "关于",
        "install": "安装",
        "cta_start": "建一个自己的桶",
        "cta_alt": "已经有账号？",
        "cta_hero": "现在就建一个自己的桶",
        "hero_note": "没有桶，东西到不了下一家。",
        "hero_alt": (
            "claude、codex、agents 三间房子立在一个三角形的三个角上，"
            "每条边都是一条画出来的路。小人拎着装满资产的红桶"
            "沿着这圈路走，从每个门里进去再出来。"
        ),
        "way_guide_title": "把这个丢给你的 agent",
        "way_guide_hint": (
            "一个 markdown 文件。它会告诉 agent 怎么把这个桶装进"
            "它当前那一家，顺便问你要不要把 red-bucket skill "
            "也装上。"
        ),
        "way_guide_open": "看看内容",
        "copy_btn": "复制",
        "copied": "已复制",
        "no_desc": "暂无说明",
        "usage": "用量",
        "no_assets": "还没有资产",
        "harness_mix": "Harness mix",
        "empty_dir": "这个目录是空的。",
        "empty_owner_hint": "加一个 README，或者上传一份资产。",
        "readme_hint": "给这个目录加一个 README.md。",
        "upload": "上传",
        "add_asset": "添加资产",
        "add_asset_hint": "按你自己那一家写，别人来取的时候自动转。",
        "asset_type": "类型",
        "source_harness": "源",
        "asset_path": "路径",
        "main_file": "主文件",
        "content": "内容",
        "commits_word": "次提交",
        "no_commits": "还没有提交。",
        "back_dir": "回上一级",
        "binary_file": "这个文件不是文本，取下来再看。",
        "changed_paths": "改动的路径",
        "comments": "评论",
        "no_comments": "还没有评论。",
        "add_comment": "写一条评论",
        "comment_btn": "发表",
        "comment_label": "评论",
        "proposed_files": "提议的文件",
        "merge_btn": "合并",
        "reject_btn": "拒绝",
        "joined": "加入于",
        "public_buckets": "公开的桶",
        "no_public": "还没有公开的桶。",
        "no_issues": "还没有议题。",
        "no_pulls": "还没有拉取请求。",
        "join_hint": "登录后可以参与。",
        "open_issue": "开一个议题",
        "open_pull": "开一个拉取请求",
        "title": "标题",
        "body": "正文",
        "file_path": "文件路径",
        "submit_issue": "提交议题",
        "submit_pull": "提交拉取请求",
        "save": "保存",
        "saved": "已保存",
        "delete_bucket": "删除这个桶",
        "danger": "危险操作",
        "danger_hint": "删除后无法恢复。",
        "confirm_delete": "输入桶名以确认删除：",
        "general": "一般",
        "pw_hint": "至少 8 个字符",
    },
}


def page_lang(request: Request) -> str:
    """Explicit choice wins, then the cookie, then the browser."""
    query = request.query_params.get("lang")
    if query in LANGS:
        return query
    cookie = request.cookies.get(LANG_COOKIE)
    if cookie in LANGS:
        return cookie
    header = request.headers.get("accept-language", "")
    for chunk in header.split(","):
        tag = chunk.split(";")[0].strip().lower()
        if tag.startswith("zh"):
            return "zh"
        if tag[:2] in LANGS:
            return tag[:2]
    return "en"


def ui_bundle(lang: str) -> dict[str, str]:
    return STRINGS[lang if lang in LANGS else "en"]


def stamp_lang(request: Request, response: Response) -> Response:
    response.headers.append("vary", "Accept-Language")
    picked = request.query_params.get("lang")
    if picked in LANGS:
        response.set_cookie(
            LANG_COOKIE,
            picked,
            max_age=LANG_YEAR,
            path="/",
            samesite="lax",
            secure=request.url.scheme == "https",
        )
    return response
