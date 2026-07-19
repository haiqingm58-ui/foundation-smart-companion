from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import ROOT_DIR, Settings
from ..models import KnowledgeChunk


@lru_cache(maxsize=1)
def textbook_chunks() -> list[dict[str, Any]]:
    path = ROOT_DIR / "server" / "data" / "knowledge" / "chunks.json"
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        {
            "id": row.get("id"), "sourceType": "textbook", "heading": row.get("heading_path") or "基础工程教材",
            "text": row.get("text") or "", "chapter": (row.get("heading_path") or "").split(" > ")[0] or None,
            "page": None, "line": row.get("source_line"),
        }
        for row in rows
        if len((row.get("text") or "").strip()) >= 12
    ]


@lru_cache(maxsize=1)
def standard_chunks() -> list[dict[str, Any]]:
    path = ROOT_DIR / "server" / "data" / "knowledge" / "standards.json"
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        {
            "id": f"standard:{row['code']}", "sourceType": "standard",
            "heading": f"{row['title']}（{row['code']}）", "text": row["text"],
            "chapter": row.get("chapter"), "page": None, "line": None,
        }
        for row in rows
    ]


def terms(text: str) -> list[str]:
    compact = re.sub(r"\s+", "", text.lower())
    result = set(re.findall(r"[a-z][a-z0-9_-]{1,30}|\d+(?:\.\d+)?", compact))
    for size in (2, 3, 4, 5, 6):
        result.update(compact[index : index + size] for index in range(max(0, len(compact) - size + 1)))
    return [item for item in result if item]


def score(query: str, heading: str, text: str) -> float:
    query_terms = terms(query)
    haystack = f"{heading}\n{text}".lower()
    if not query_terms:
        return 0
    matched = [term for term in query_terms if term in haystack]
    heading_bonus = sum(2 for term in matched if term in heading.lower())
    return sum(len(term) for term in matched) + heading_bonus


def search(session: Session, query: str, mode: str, limit: int = 5) -> list[dict[str, Any]]:
    database_rows = session.scalars(select(KnowledgeChunk)).all()
    rows = textbook_chunks() + standard_chunks() + [
        {"id": row.id, "sourceType": row.source_type, "heading": row.heading, "text": row.text, "chapter": row.chapter, "page": row.page, "line": None}
        for row in database_rows
    ]
    if mode == "教材问答":
        rows = [row for row in rows if row["sourceType"] == "textbook"]
    elif mode == "规范问答":
        rows = [row for row in rows if row["sourceType"] in {"standard", "regulation"}]
    ranked = sorted(((score(query, row["heading"], row["text"]), row) for row in rows), key=lambda item: item[0], reverse=True)
    return [{**row, "score": value} for value, row in ranked[:limit] if value > 0]


def local_answer(question: str, sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "当前知识库没有检索到足够可靠的依据。建议更换关键词，或请指导老师补充相关教材与规范资料。"
    top = sources[0]
    excerpt = re.sub(r"\s+", " ", top["text"]).strip()[:420]
    return f"根据《基础工程》知识库，{excerpt}\n\n参考位置：{top['heading']}。建议结合该章节的公式适用条件和例题继续核对。"


def _chat_content(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()


def call_llm(settings: Settings, question: str, mode: str, sources: list[dict[str, Any]]) -> str | None:
    if not settings.llm_api_url or not settings.llm_api_key or not sources:
        return None
    context = "\n\n".join(f"[{index + 1}] {item['heading']}\n{item['text'][:900]}" for index, item in enumerate(sources))
    payload = json.dumps(
        {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": "你是基础工程课程助教。只能依据给定资料回答，必须标注引用编号；资料不足时明确说明。"},
                {"role": "user", "content": f"模式：{mode}\n问题：{question}\n\n资料：\n{context}"},
            ],
            "temperature": 0.2,
            "stream": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        settings.llm_api_url,
        data=payload,
        headers={"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
        return _chat_content(data)
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return None
