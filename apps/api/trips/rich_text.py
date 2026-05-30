from __future__ import annotations

from copy import deepcopy
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

TRIP_RICH_TEXT_EMPTY_DOCUMENT = {"type": "doc", "content": []}

ALLOWED_BLOCK_TYPES = {"paragraph", "heading", "bullet_list", "ordered_list", "callout"}
ALLOWED_MARK_TYPES = {"bold", "italic", "link"}
ALLOWED_LINK_SCHEMES = {"http", "https", "mailto", "tel"}
MAX_TRIP_RICH_TEXT_CHARACTERS = 12000


def default_trip_rich_text() -> dict:
    return deepcopy(TRIP_RICH_TEXT_EMPTY_DOCUMENT)


def sanitize_trip_rich_text(value) -> dict:
    if value in (None, ""):
        return default_trip_rich_text()
    if not isinstance(value, dict) or value.get("type") != "doc":
        raise ValidationError("Trip Rich Text must be a structured document.")

    content = value.get("content", [])
    if not isinstance(content, list):
        raise ValidationError("Trip Rich Text content must be a list.")

    blocks = []
    for raw_block in content:
        block = _sanitize_block(raw_block)
        if block is not None:
            blocks.append(block)

    sanitized = {"type": "doc", "content": blocks}
    if len(trip_rich_text_plain_text(sanitized)) > MAX_TRIP_RICH_TEXT_CHARACTERS:
        raise ValidationError(
            f"Trip Rich Text cannot exceed {MAX_TRIP_RICH_TEXT_CHARACTERS} characters."
        )
    return sanitized


def is_trip_rich_text_empty(value) -> bool:
    try:
        sanitized = sanitize_trip_rich_text(value)
    except ValidationError:
        return True
    return trip_rich_text_plain_text(sanitized).strip() == ""


def trip_rich_text_plain_text(value) -> str:
    if not isinstance(value, dict):
        return ""
    text_parts: list[str] = []

    def visit(node):
        if not isinstance(node, dict):
            return
        node_type = node.get("type")
        if node_type == "text":
            text = node.get("text")
            if isinstance(text, str):
                text_parts.append(text)
            return
        for child in node.get("content", []) if isinstance(node.get("content"), list) else []:
            visit(child)
        if node_type in {"paragraph", "heading", "list_item", "callout"}:
            text_parts.append("\n")

    visit(value)
    return " ".join("".join(text_parts).split())


def _sanitize_block(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    node_type = value.get("type")
    if node_type not in ALLOWED_BLOCK_TYPES:
        return None

    if node_type == "paragraph":
        inline_content = _sanitize_inline_content(value.get("content", []))
        return {"type": "paragraph", "content": inline_content} if inline_content else None

    if node_type == "heading":
        inline_content = _sanitize_inline_content(value.get("content", []))
        if not inline_content:
            return None
        level = value.get("attrs", {}).get("level") if isinstance(value.get("attrs"), dict) else 2
        if level not in (2, 3):
            level = 2
        return {
            "type": "heading",
            "attrs": {"level": level},
            "content": inline_content,
        }

    if node_type in {"bullet_list", "ordered_list"}:
        items = []
        for item in value.get("content", []) if isinstance(value.get("content"), list) else []:
            sanitized_item = _sanitize_list_item(item)
            if sanitized_item is not None:
                items.append(sanitized_item)
        return {"type": node_type, "content": items} if items else None

    if node_type == "callout":
        paragraphs = []
        raw_content = value.get("content", [])
        if isinstance(raw_content, list):
            for child in raw_content:
                paragraph = _sanitize_block(
                    child if isinstance(child, dict) else {"type": "paragraph", "content": []}
                )
                if paragraph is not None and paragraph.get("type") == "paragraph":
                    paragraphs.append(paragraph)
        return {"type": "callout", "content": paragraphs} if paragraphs else None

    return None


def _sanitize_list_item(value) -> dict | None:
    if not isinstance(value, dict) or value.get("type") != "list_item":
        return None
    paragraphs = []
    for child in value.get("content", []) if isinstance(value.get("content"), list) else []:
        paragraph = _sanitize_block(child)
        if paragraph is not None and paragraph.get("type") == "paragraph":
            paragraphs.append(paragraph)
    return {"type": "list_item", "content": paragraphs} if paragraphs else None


def _sanitize_inline_content(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    inline_nodes = []
    for raw_node in value:
        if not isinstance(raw_node, dict) or raw_node.get("type") != "text":
            continue
        text = raw_node.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        node = {"type": "text", "text": text}
        marks = _sanitize_marks(raw_node.get("marks", []))
        if marks:
            node["marks"] = marks
        inline_nodes.append(node)
    return inline_nodes


def _sanitize_marks(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    marks = []
    seen = set()
    for raw_mark in value:
        if not isinstance(raw_mark, dict):
            continue
        mark_type = raw_mark.get("type")
        if mark_type not in ALLOWED_MARK_TYPES:
            continue
        if mark_type in {"bold", "italic"}:
            if mark_type not in seen:
                marks.append({"type": mark_type})
                seen.add(mark_type)
            continue
        if mark_type == "link":
            attrs = raw_mark.get("attrs")
            href = attrs.get("href") if isinstance(attrs, dict) else ""
            if isinstance(href, str) and _is_safe_link(href) and "link" not in seen:
                marks.append({"type": "link", "attrs": {"href": href.strip()}})
                seen.add("link")
    return marks


def _is_safe_link(href: str) -> bool:
    parsed = urlparse(href.strip())
    return parsed.scheme in ALLOWED_LINK_SCHEMES and bool(parsed.netloc or parsed.path)
