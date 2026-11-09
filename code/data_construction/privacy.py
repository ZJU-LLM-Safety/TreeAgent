"""Deterministic privacy transform for the selected JSON demonstration records.

Apply the field substitutions defined by review_privacy_placeholders_v1.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
import zlib
from collections import Counter
from typing import Any

POLICY = "review_privacy_placeholders_v1"
PLACEHOLDER = "SYNTHETIC_REVIEW_VALUE"
BUSINESS_PLACEHOLDER = "REDACTED_BUSINESS_REFERENCE_NOT_USABLE"
BUSINESS_KEYS = {"token", "offertoken", "offerreference", "searchkey"}
PROTECTED = {"question", "input", "answer", "answers", "gold_answer", "gold_spec",
             "gold_program", "structured_answer", "supporting_paths", "task_type",
             "task_subtype", "metric_type", "answer_format", "answer_format_instruction"}


def encoded_business_value(value: str) -> bool:
    """Recognize bounded base64 JSON or gzip URL/JSON; never execute or fetch it."""
    if not 32 <= len(value) <= 65536 or not re.fullmatch(r"[A-Za-z0-9_+/=-]+", value):
        return False
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        if raw.startswith(b"\x1f\x8b"):
            inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
            raw = inflater.decompress(raw, 16385)
            if len(raw) > 16384 or not inflater.eof:
                # An opaque compressed value is unnecessary in these examples.
                return True
        text = raw.decode("utf-8").strip()
        if text.startswith(("https://", "http://")):
            return True
        if text.startswith(("{", "[")):
            return isinstance(json.loads(text), (dict, list))
    except (ValueError, UnicodeError, binascii.Error, zlib.error):
        return False
    return False


def synthetic_shape(value: Any) -> Any:
    """Keep containers and scalar types while removing all original leaf values."""
    if isinstance(value, dict):
        return {key: synthetic_shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [synthetic_shape(item) for item in value]
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return type(value)(0)
    if isinstance(value, str):
        return PLACEHOLDER
    return None


def scrub(value: Any, counts: Counter, key: str = "") -> Any:
    normalized = key.replace("_", "").lower()
    if normalized == "searchcontext":
        replacement = synthetic_shape(value)
        counts["search_contexts"] += int(replacement != value)
        return replacement
    if isinstance(value, dict):
        reviewer = (isinstance(value.get("author"), dict)
                    and "user_id" in value["author"])
        short_review = (isinstance(value.get("user"), dict)
                        and "name" in value["user"] and "numericRating" in value)
        if reviewer or short_review:
            replacement = synthetic_shape(value)
            counts["review_records"] += int(replacement != value)
            return replacement
        return {k: scrub(v, counts, k) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(item, counts, key) for item in value]
    if isinstance(value, str) and value != BUSINESS_PLACEHOLDER:
        if normalized in BUSINESS_KEYS or encoded_business_value(value):
            counts["business_references"] += 1
            return BUSINESS_PLACEHOLDER
    return value


def sanitize_json_row(row: dict[str, Any]) -> dict[str, Any]:
    counts = Counter()
    result = scrub(row, counts)
    for key in PROTECTED:
        if result.get(key) != row.get(key):
            raise ValueError(f"privacy transform would change protected QA field: {key}")
    existing = row.get("metadata", {}).get("privacy_transform")
    if existing and any(counts.values()):
        raise ValueError("record declares privacy transform but contains unsanitized values")
    result.setdefault("metadata", {})["privacy_transform"] = existing or {
        "policy": POLICY,
        "origin": "public_source_record_with_selected_synthetic_replacements",
        "whole_record_synthetic": False,
        "replacement_counts": dict(sorted(counts.items())),
        "length_and_position_metadata": "source_snapshot",
        "use": "regression_fixture",
    }
    return result


def validate_private_fields(row: dict[str, Any]) -> None:
    notice = row.get("metadata", {}).get("privacy_transform", {})
    if notice.get("policy") != POLICY or notice.get("whole_record_synthetic") is not False:
        raise ValueError("JSON record must declare its source-derived privacy transform")
    counts = Counter()
    scrub(row, counts)
    if any(counts.values()):
        raise ValueError("JSON record contains unsanitized review or business-reference fields")
