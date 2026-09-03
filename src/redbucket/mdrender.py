"""Markdown 渲染：frontmatter 出键值表，正文走 markdown-it。"""
from __future__ import annotations

from html import escape

from markdown_it import MarkdownIt

from redbucket.formatters.frontmatter import (
    FrontmatterError,
    parse_frontmatter,
    split_frontmatter,
)


def render_markdown(text: str) -> str:
    parser = MarkdownIt("commonmark", {"html": False})
    if text.split("\n", 1)[0].strip() != "---":
        return parser.render(text)
    try:
        fields, body = parse_frontmatter(text)
    except FrontmatterError:
        return parser.render(text)
    rows = "".join(
        '<tr><th scope="row">{}</th><td>{}</td></tr>'.format(
            escape(key), escape(value)
        )
        for key, value in fields.items()
        if key
    )
    if rows:
        head = f'<table class="frontmatter"><tbody>{rows}</tbody></table>\n'
    else:
        header, _ = split_frontmatter(text)
        head = (
            '<pre class="frontmatter-raw"><code>'
            f"{escape(header)}</code></pre>\n"
        )
    return head + parser.render(body)
