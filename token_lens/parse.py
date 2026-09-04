"""Parse trace JSON into typed message records.

Supports a few common trace shapes used by LLM observability tooling, with a
flexible fallback for arbitrary payloads.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .types import MessageRecord, ZoneKind


_TOOL_SCHEMA_HINTS = (
    "tool",
    "function",
    "schema",
    "parameters",
    "tools",
    "functions",
    "tool_calls",
)
_RAG_HINTS = (
    "rag",
    "retrieval",
    "context_docs",
    "search_results",
    "knowledge",
    "documents",
    "source_documents",
)
_FEW_SHOT_HINTS = (
    "few_shot",
    "examples",
    "demonstrations",
    "shots",
)
_SYSTEM_HINTS = (
    "system",
    "instruction",
    "instructions",
    "system_prompt",
    "preamble",
)
_HISTORY_HINTS = (
    "history",
    "conversation",
    "chat_history",
    "past_messages",
    "previous",
)


def _classify_key(key: str) -> ZoneKind | None:
    k = key.lower()
    for hint in _TOOL_SCHEMA_HINTS:
        if hint in k:
            return ZoneKind.TOOL_SCHEMA
    for hint in _RAG_HINTS:
        if hint in k:
            return ZoneKind.RAG
    for hint in _FEW_SHOT_HINTS:
        if hint in k:
            return ZoneKind.FEW_SHOT
    for hint in _SYSTEM_HINTS:
        if hint in k:
            return ZoneKind.SYSTEM
    for hint in _HISTORY_HINTS:
        if hint in k:
            return ZoneKind.HISTORY
    return None


def _zone_for_role(role: str) -> ZoneKind:
    r = role.lower()
    if r in ("system", "developer"):
        return ZoneKind.SYSTEM
    if r in ("user", "human"):
        return ZoneKind.USER
    if r in ("assistant", "ai", "model"):
        return ZoneKind.ASSISTANT
    if r in ("tool", "function"):
        return ZoneKind.TOOL_SCHEMA
    return ZoneKind.UNKNOWN


def _to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(_to_text(item["content"]))
                elif "input" in item:
                    parts.append(_to_text(item["input"]))
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def _looks_like_messages_list(node: Any) -> bool:
    if not isinstance(node, list) or not node:
        return False
    if not all(isinstance(x, dict) for x in node):
        return False
    return any(("role" in x and ("content" in x or "parts" in x)) for x in node)


def _walk(obj: Any, path: str, out: list[MessageRecord]) -> None:
    """Recursive walker that emits MessageRecord objects from a trace dict."""

    if isinstance(obj, dict):
        # 1. Inline message: {role, content}
        if "role" in obj and ("content" in obj or "parts" in obj):
            role = str(obj.get("role", "user"))
            content = _to_text(obj.get("content") or obj.get("parts"))
            out.append(
                MessageRecord(
                    index=len(out),
                    role=role,
                    content=content,
                    zone=_zone_for_role(role),
                    source=path or "root",
                )
            )
            return

        # 2. Keyed message list: {messages: [{role, content}, ...]}
        for key, val in obj.items():
            child_path = f"{path}.{key}" if path else key
            if isinstance(val, list) and val and all(
                isinstance(x, dict) and "role" in x for x in val
            ):
                zone_hint = _classify_key(key)
                for i, m in enumerate(val):
                    role = str(m.get("role", "user"))
                    content = _to_text(m.get("content") or m.get("parts"))
                    zone = zone_hint or _zone_for_role(role)
                    out.append(
                        MessageRecord(
                            index=len(out),
                            role=role,
                            content=content,
                            zone=zone,
                            source=f"{child_path}[{i}]",
                            metadata={"origin_key": key},
                        )
                    )
                continue

            # 3. RAG doc list: {context_docs: [{text, ...}, ...]}
            if (
                isinstance(val, list)
                and val
                and all(isinstance(x, dict) for x in val)
                and _classify_key(key) == ZoneKind.RAG
            ):
                for i, d in enumerate(val):
                    text = _to_text(
                        d.get("text")
                        or d.get("content")
                        or d.get("page_content")
                        or d.get("chunk")
                    )
                    out.append(
                        MessageRecord(
                            index=len(out),
                            role="document",
                            content=text,
                            zone=ZoneKind.RAG,
                            source=f"{child_path}[{i}]",
                            metadata={"origin_key": key, **d} if isinstance(d, dict) else {},
                        )
                    )
                continue

            # 4. Tool/function schema list
            if (
                _classify_key(key) == ZoneKind.TOOL_SCHEMA
                and isinstance(val, (list, dict))
            ):
                text = json.dumps(val, ensure_ascii=False)
                out.append(
                    MessageRecord(
                        index=len(out),
                        role="tool_schema",
                        content=text,
                        zone=ZoneKind.TOOL_SCHEMA,
                        source=child_path,
                        metadata={"origin_key": key},
                    )
                )
                continue

            # 5. Few-shot examples (list of {input, output})
            if (
                _classify_key(key) == ZoneKind.FEW_SHOT
                and isinstance(val, list)
                and val
                and all(isinstance(x, dict) for x in val)
            ):
                for i, ex in enumerate(val):
                    text = _to_text(ex.get("input")) + "\n" + _to_text(ex.get("output"))
                    out.append(
                        MessageRecord(
                            index=len(out),
                            role="example",
                            content=text.strip(),
                            zone=ZoneKind.FEW_SHOT,
                            source=f"{child_path}[{i}]",
                            metadata={"origin_key": key, **ex} if isinstance(ex, dict) else {},
                        )
                    )
                continue

            # 6. Generic dict value -> recurse
            _walk(val, child_path, out)

    elif isinstance(obj, list):
        if _looks_like_messages_list(obj):
            for i, m in enumerate(obj):
                role = str(m.get("role", "user"))
                content = _to_text(m.get("content") or m.get("parts"))
                out.append(
                    MessageRecord(
                        index=len(out),
                        role=role,
                        content=content,
                        zone=_zone_for_role(role),
                        source=f"{path or 'list'}[{i}]",
                    )
                )
            return
        for i, item in enumerate(obj):
            _walk(item, f"{path}[{i}]", out)


def parse_trace(data: Any) -> list[MessageRecord]:
    """Walk an arbitrary trace structure and return ordered message records."""

    out: list[MessageRecord] = []
    _walk(data, "", out)
    # Reindex defensively
    for i, m in enumerate(out):
        m.index = i
    return out


def load_trace(path: str | Path) -> Any:
    """Load JSON trace from disk."""

    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return json.loads(text)


# Re-export for callers
__all__ = ["parse_trace", "load_trace", "_classify_key", "_zone_for_role", "_to_text"]
