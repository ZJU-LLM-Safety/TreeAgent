"""Create deterministic JSON/HTML/YAML/JavaScript TreeAgent sections from a local input file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .sectioning import build_sections, section_stats, parse_json_text
from .tokenizers import CharacterTokenizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=["json", "html", "yaml", "javascript"], default="json")
    parser.add_argument("--method", choices=["flat", "treeagent"], default="treeagent")
    parser.add_argument("--section-size", type=int, default=72)
    parser.add_argument("--max-tree-budget", type=int, default=None)
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    value = parse_json_text(text) if args.format == "json" else text
    sections = build_sections(
        value=value,
        tokenizer=CharacterTokenizer(),
        section_size=args.section_size,
        method=args.method,
        context_format=args.format,
        max_tree_budget=args.max_tree_budget,
    )
    payload = {
        "mode": "deterministic_character_tokenizer_check",
        "formal_model_tokenizer": False,
        "stats": section_stats(sections),
        "sections": [section.as_record() for section in sections],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
