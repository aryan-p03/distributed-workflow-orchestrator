from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable, Mapping
from typing import Any, Literal, TypedDict
from urllib.parse import urlparse


class HandlerResult(TypedDict):
    status: Literal["success", "failed"]
    message: str
    data: dict[str, Any]


def dispatch_task_handler(
    *,
    task_type: str,
    task_name: str,
    payload: Mapping[str, object] | None = None,
) -> HandlerResult:
    normalized_type = task_type.strip().lower().replace("-", "_")
    handlers: dict[str, Callable[..., HandlerResult]] = {
        "delay": _handle_delay,
        "url_check": _handle_url_check,
        "csv_process": _handle_csv_process,
        "text_analyze": _handle_text_analyze,
        "text_analysis": _handle_text_analyze,
    }

    handler = handlers.get(normalized_type)
    if handler is None:
        raise ValueError(f"Unsupported task type: {task_type}")

    return handler(task_name=task_name, payload=payload or {})


def _handle_delay(*, task_name: str, payload: Mapping[str, object]) -> HandlerResult:
    seconds = _extract_numeric_seconds(task_name=task_name, payload=payload)
    return {
        "status": "success",
        "message": f"Delay task processed for {seconds} second(s)",
        "data": {"seconds": seconds},
    }


def _handle_url_check(*, task_name: str, payload: Mapping[str, object]) -> HandlerResult:
    raw_url = payload.get("url")
    url = raw_url.strip() if isinstance(raw_url, str) else _extract_url(task_name)
    if not url:
        raise ValueError("URL check task requires a URL in payload['url'] or task name")

    parsed = urlparse(url)
    is_valid = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    return {
        "status": "success",
        "message": "URL validation complete",
        "data": {"url": url, "is_valid": is_valid},
    }


def _handle_csv_process(*, task_name: str, payload: Mapping[str, object]) -> HandlerResult:
    raw_csv = payload.get("csv_text")
    csv_text = raw_csv if isinstance(raw_csv, str) else task_name
    rows = list(csv.reader(io.StringIO(csv_text)))
    row_count = len(rows)
    column_count = max((len(row) for row in rows), default=0)

    return {
        "status": "success",
        "message": "CSV processing complete",
        "data": {
            "row_count": row_count,
            "column_count": column_count,
        },
    }


def _handle_text_analyze(*, task_name: str, payload: Mapping[str, object]) -> HandlerResult:
    raw_text = payload.get("text")
    text = raw_text.strip() if isinstance(raw_text, str) else task_name.strip()
    if not text:
        raise ValueError("Text analysis task requires non-empty text")

    words = [word for word in re.split(r"\s+", text) if word]
    sentence_count = len([segment for segment in re.split(r"[.!?]+", text) if segment.strip()])

    return {
        "status": "success",
        "message": "Text analysis complete",
        "data": {
            "char_count": len(text),
            "word_count": len(words),
            "sentence_count": sentence_count,
        },
    }


def _extract_numeric_seconds(*, task_name: str, payload: Mapping[str, object]) -> int:
    raw_seconds = payload.get("seconds")
    if isinstance(raw_seconds, (int, float)):
        seconds = int(raw_seconds)
    elif isinstance(raw_seconds, str) and raw_seconds.strip().isdigit():
        seconds = int(raw_seconds.strip())
    else:
        match = re.search(r"(\d+)", task_name)
        seconds = int(match.group(1)) if match else 0

    if seconds < 0:
        raise ValueError("Delay seconds must be non-negative")
    return seconds


def _extract_url(task_name: str) -> str | None:
    match = re.search(r"https?://\S+", task_name)
    if match is None:
        return None
    return match.group(0).rstrip(".,;)")
