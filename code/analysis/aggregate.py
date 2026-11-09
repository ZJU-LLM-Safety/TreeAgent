"""Aggregate already-scored rows with explicit macro averaging."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def macro_by(
    rows: Iterable[dict[str, Any]], group_fields: tuple[str, ...]
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row[field]) for field in group_fields)
        groups[key].append(float(row["score"]))
    output = []
    for key in sorted(groups):
        scores = groups[key]
        output.append(
            {
                **dict(zip(group_fields, key)),
                "n": len(scores),
                "mean_score": sum(scores) / len(scores),
            }
        )
    return output
