"""Score saved prediction fixtures without model inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .metrics import score_prediction_value


def score_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = []
    for index, row in enumerate(rows):
        missing = {"gold", "metric_type"} - set(row)
        if missing:
            raise ValueError(f"row {index} is missing: {', '.join(sorted(missing))}")
        prediction = row.get("prediction")
        if prediction is None:
            prediction = ""
        score = score_prediction_value(
            str(prediction), str(row["gold"]), str(row["metric_type"])
        )
        scored.append(
            {
                "id": str(row.get("id", index)),
                "score": score,
            }
        )
    total = len(scored)
    return {
        "num_examples": total,
        "fractional_score": (
            sum(item["score"] for item in scored) / total if total else 0.0
        ),
        "examples": scored,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number} is not a JSON object")
            rows.append(value)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score_rows(read_jsonl(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
