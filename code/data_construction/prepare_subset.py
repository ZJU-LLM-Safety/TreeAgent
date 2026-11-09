#!/usr/bin/env python3
"""Extract deterministic task fixtures from a local source snapshot.

Identifiers and packaging labels use format-based names. JSON records receive
privacy substitutions; YAML regression inputs are generated from task schemas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .privacy import POLICY, sanitize_json_row
from .sample_revisions import revise_sample


TASKS = (
    "record_field_lookup",
    "multi_record_field_2",
    "multi_record_field_4",
    "record_multi_field_2",
    "record_multi_field_4",
    "conditional_count",
    "groupby_topk_values",
    "numeric_extreme",
)
EMAIL_PATTERN = re.compile(
    rb"(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"
    rb"(?![A-Z0-9._%+-])"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def task_name(row: dict[str, Any]) -> str:
    task = row.get("task_subtype") or row.get("canonical_task")
    if task not in TASKS:
        raise ValueError(f"unsupported task subtype: {task!r}")
    return task


def acceptable_row(raw: bytes, *, exclude_email: bool) -> bool:
    return not exclude_email or EMAIL_PATTERN.search(raw) is None


def package_row(
    raw: bytes, row: dict[str, Any], *, family: str,
    normalize_json_identifiers: bool = False,
) -> tuple[bytes, dict[str, Any]]:
    """Normalize labels and sanitize selected JSON demonstration fields.

    Reference answers, tasks, and gold programs are unchanged. Bounded question
    and scoring corrections are applied by sample_revisions.
    Original source hashes remain in the manifest alongside packaged hashes.
    """
    packaged = json.loads(raw)
    if normalize_json_identifiers:
        for key in ("id", "uid"):
            if key in packaged:
                packaged[key] = re.sub(r"^[^_]+_[^_]+_", "json_subset_", packaged[key])
        packaged["dataset_version"] = "subset"
    if family == "html":
        context = packaged["context"]
        context = re.sub(r"(<title>)[^<]* HTML corpus(</title>)",
                         r"\1Structured HTML data\2", context)
        context = re.sub(r"\bdata-[A-Za-z][A-Za-z0-9]*-(corpus|source-id|source-label)\b",
                         r"data-structured-\1", context)
        packaged["context"] = context
        packaged.setdefault("metadata", {})["dataset_family"] = "HTML-WebSRC"
    elif family == "jss":
        context = packaged["context"]
        context = re.sub(r"(?m)^(// @)[A-Za-z][A-Za-z0-9]*-jss-(source|state|file)\b",
                         r"\1structured-javascript-\2", context)
        context = re.sub(r"\b__[A-Za-z][A-Za-z0-9]*_jssstate_",
                         "__structured_javascript_state_", context)
        packaged["context"] = context
        packaged.setdefault("metadata", {})["dataset_family"] = "JavaScript"
    if family == "json":
        packaged = sanitize_json_row(packaged)
    packaged = revise_sample(packaged)
    return canonical_json(packaged), packaged


def first_by_task(
    path: Path, *, exclude_email: bool = False
) -> list[tuple[bytes, dict[str, Any]]]:
    selected: dict[str, tuple[bytes, dict[str, Any]]] = {}
    with path.open("rb") as stream:
        for raw in stream:
            if not raw.strip():
                continue
            if not acceptable_row(raw, exclude_email=exclude_email):
                continue
            row = json.loads(raw)
            task = task_name(row)
            selected.setdefault(task, (raw, row))
            if len(selected) == len(TASKS):
                break
    missing = [task for task in TASKS if task not in selected]
    if missing:
        raise ValueError(f"{path}: missing tasks {missing}")
    return [selected[task] for task in TASKS]


def first_row(
    path: Path, *, exclude_email: bool = False
) -> tuple[bytes, dict[str, Any]]:
    with path.open("rb") as stream:
        for raw in stream:
            if raw.strip() and acceptable_row(raw, exclude_email=exclude_email):
                return raw, json.loads(raw)
    raise ValueError(f"{path}: no eligible JSONL rows")


def write_original_subset(
    *,
    release_root: Path,
    output_root: Path,
    family: str,
    slots: Iterable[tuple[str, Path, str]],
    manifest_rows: list[dict[str, Any]],
    exclude_email: bool = False,
    normalize_json_identifiers: bool = False,
) -> None:
    output_path = output_root / "data" / ("javascript" if family == "jss" else family) / ("regression_fixtures.jsonl" if family == "json" else "representative.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output:
        packaged_line = 0
        for slot, relative_source, mode in slots:
            source_path = release_root / relative_source
            selected = (
                first_by_task(source_path, exclude_email=exclude_email)
                if mode == "all_tasks"
                else [first_row(source_path, exclude_email=exclude_email)]
            )
            for raw, row in selected:
                if not raw.endswith(b"\n"):
                    raise ValueError(
                        f"{source_path}: selected source row lacks a newline and "
                        "cannot be copied exactly into a JSONL file with multiple rows"
                    )
                packaged_raw, packaged_row = package_row(
                    raw,
                    row,
                    normalize_json_identifiers=normalize_json_identifiers,
                    family=family,
                )
                output.write(packaged_raw)
                packaged_line += 1
                manifest_rows.append(
                    {
                        "family": family,
                        "kind": "selected_release_record",
                        "slot": slot,
                        "task": task_name(packaged_row),
                        "uid": packaged_row.get("uid") or packaged_row.get("id"),
                        "split": packaged_row.get("split"),
                        "declared_length_bucket": packaged_row.get("length_bucket"),
                        "source_release_path": relative_source.as_posix(),
                        "source_line_sha256": sha256_bytes(raw),
                        "package_path": output_path.relative_to(output_root).as_posix(),
                        "package_line": packaged_line,
                        "package_line_sha256": sha256_bytes(packaged_raw),
                        "package_transform": "review_format_labels_v1",
                        **({"sample_revision": packaged_row["sample_revision"]}
                           if "sample_revision" in packaged_row else {}),
                        **({"privacy_transform": POLICY} if family == "json" else {}),
                    }
                )


def yaml_document(structural_id: str) -> str:
    records = (
        ("Alpha", "query", "true", "Blue inventory item", "int32", 10),
        ("Bravo", "header", "true", "Green inventory item", "int32", 20),
        ("Charlie", "query", "false", "Red inventory item", "int64", 30),
        ("Delta", "cookie", "true", "Gold inventory item", "int32", 40),
    )
    documents = []
    for label, location, required, description, schema_format, maximum in records:
        documents.append(
            f"""openapi: 3.0.0
info:
  title: Synthetic {label} Inventory API
  version: 1.0.0
x-fixture-id: {structural_id}
paths:
  /items:
    get:
      parameters:
        - name: limit
          in: {location}
          required: {required}
          description: {description}
          schema:
            type: integer
            format: {schema_format}
            maximum: {maximum}
"""
        )
    return "---\n".join(documents)


def synthetic_yaml_rows() -> list[tuple[str, dict[str, Any]]]:
    specifications = {
        "record_field_lookup": (
            "For the limit parameter in Synthetic Alpha Inventory API, what is "
            "the required flag?",
            "True",
            {
                "format": "yaml",
                "op": "yaml_path_value",
                "doc_index": 0,
                "path_parts": [
                    "paths",
                    "/items",
                    "get",
                    "parameters",
                    0,
                    "required",
                ],
            },
        ),
        "multi_record_field_2": (
            "Return the schema maximum for the limit parameter in Synthetic Alpha "
            "Inventory API and Synthetic Bravo Inventory API, in that order.",
            ["10", "20"],
            {
                "format": "yaml",
                "op": "multi_answer_text",
                "answers": ["10", "20"],
                "labels": ["Q1", "Q2"],
                "paths": [
                    "$[0].paths['/items'].get.parameters[0].schema.maximum",
                    "$[1].paths['/items'].get.parameters[0].schema.maximum",
                ],
            },
        ),
        "multi_record_field_4": (
            "Return the schema maximum for the limit parameter in the Alpha, "
            "Bravo, Charlie, and Delta inventory APIs, in that order.",
            ["10", "20", "30", "40"],
            {
                "format": "yaml",
                "op": "multi_answer_text",
                "answers": ["10", "20", "30", "40"],
                "labels": ["Q1", "Q2", "Q3", "Q4"],
                "paths": [
                    "$[0].paths['/items'].get.parameters[0].schema.maximum",
                    "$[1].paths['/items'].get.parameters[0].schema.maximum",
                    "$[2].paths['/items'].get.parameters[0].schema.maximum",
                    "$[3].paths['/items'].get.parameters[0].schema.maximum",
                ],
            },
        ),
        "record_multi_field_2": (
            "For the limit parameter in Synthetic Alpha Inventory API, return "
            "its location and schema format.",
            ["query", "int32"],
            {
                "format": "yaml",
                "op": "multi_answer_text",
                "answers": ["query", "int32"],
                "labels": ["F1", "F2"],
                "paths": [
                    "$[0].paths['/items'].get.parameters[0].in",
                    "$[0].paths['/items'].get.parameters[0].schema.format",
                ],
            },
        ),
        "record_multi_field_4": (
            "For the limit parameter in Synthetic Alpha Inventory API, return "
            "description, format, required, and type.",
            ["Blue inventory item", "int32", "True", "integer"],
            {
                "format": "yaml",
                "op": "multi_answer_text",
                "answers": ["Blue inventory item", "int32", "True", "integer"],
                "labels": ["F1", "F2", "F3", "F4"],
                "paths": [
                    "$[0].paths['/items'].get.parameters[0].description",
                    "$[0].paths['/items'].get.parameters[0].schema.format",
                    "$[0].paths['/items'].get.parameters[0].required",
                    "$[0].paths['/items'].get.parameters[0].schema.type",
                ],
            },
        ),
        "conditional_count": (
            "How many parameter records have schema format int32?",
            "3",
            {
                "format": "yaml",
                "op": "openapi_semantic_conditional_count",
                "record_type": "openapi_parameter",
                "field_key": "schema_format",
                "predicate_value": "int32",
                "agg": None,
                "record_filter_field": None,
                "record_filter_value": None,
                "additional_record_filters": [],
                "top_k": None,
            },
        ),
        "groupby_topk_values": (
            "Which three parameter locations occur most often?",
            ["query", "header", "cookie"],
            {
                "format": "yaml",
                "op": "openapi_semantic_topk_values",
                "record_type": "openapi_parameter",
                "field_key": "parameter_location",
                "predicate_value": None,
                "agg": None,
                "record_filter_field": None,
                "record_filter_value": None,
                "additional_record_filters": [],
                "top_k": 3,
            },
        ),
        "numeric_extreme": (
            "Among parameters named limit, what is the largest schema maximum?",
            "40",
            {
                "format": "yaml",
                "op": "openapi_semantic_numeric_extreme",
                "record_type": "openapi_parameter",
                "field_key": "schema_maximum",
                "predicate_value": None,
                "agg": "max",
                "record_filter_field": "parameter_name",
                "record_filter_value": "limit",
                "additional_record_filters": [],
                "top_k": None,
            },
        ),
    }
    output = []
    for index, task in enumerate(TASKS):
        question, answer, gold_spec = specifications[task]
        answers = answer if isinstance(answer, list) else [answer]
        output.append(
            (
                f"test/8k/{task}",
                {
                    "uid": f"yaml_synthetic_fixture_{index:02d}_{task}",
                    "dataset_version": "supplement_synthetic_fixture_v1",
                    "split": "fixture",
                    "length_bucket": "synthetic",
                    "representative_slot": f"test/8k/{task}",
                    "task_type": (
                        "AGGREGATION"
                        if task in {
                            "conditional_count",
                            "groupby_topk_values",
                            "numeric_extreme",
                        }
                        else "EXTRACTIVE"
                    ),
                    "task_subtype": task,
                    "canonical_task": task,
                    "context_format": "yaml",
                    "context": yaml_document(str(index)),
                    "question": question,
                    "answer": "\n".join(answers),
                    "answers": answers,
                    "structured_answer": answer,
                    "gold_answer": "\n".join(answers),
                    "gold_spec": gold_spec,
                    "answer_contract_version": "ordered_values_v2",
                    "answer_format": "value_only",
                    "metadata": {
                        "synthetic_fixture": True,
                        "not_length_materialized": True,
                        "redistribution_reason": (
                            "Real selected OpenAPI contexts were withheld because "
                            "their per-source licenses were unspecified."
                        ),
                    },
                },
            )
        )
    structural = dict(output[0][1])
    structural["uid"] = "yaml_synthetic_fixture_08_structure"
    structural["representative_slot"] = "test/128k/structure"
    structural["context"] = yaml_document("structure")
    structural["metadata"] = dict(structural["metadata"])
    structural["metadata"]["structural_example"] = True
    output.append(("test/128k/structure", structural))
    return [(slot, revise_sample(row)) for slot, row in output]


def write_yaml_fixtures(
    output_root: Path, manifest_rows: list[dict[str, Any]]
) -> None:
    output_path = output_root / "data" / "yaml" / "synthetic_fixtures.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output:
        for line_number, (slot, row) in enumerate(synthetic_yaml_rows(), start=1):
            raw = canonical_json(row)
            output.write(raw)
            manifest_rows.append(
                {
                    "family": "yaml",
                    "kind": "synthetic_fixture",
                    "slot": slot,
                    "task": row["task_subtype"],
                    "uid": row["uid"],
                    "split": "fixture",
                    "declared_length_bucket": "synthetic",
                    "source_release_path": None,
                    "source_line_sha256": None,
                    "package_path": output_path.relative_to(output_root).as_posix(),
                    "package_line": line_number,
                    "package_line_sha256": sha256_bytes(raw),
                    "sample_revision": row["sample_revision"],
                }
            )


def sanitized_release_manifest(release_root: Path) -> dict[str, Any]:
    source = json.loads((release_root / "manifest.json").read_text(encoding="utf-8"))
    files = []
    for item in source["files"]:
        clean = {key: value for key, value in item.items() if key != "source"}
        files.append(clean)
    return {
        "schema_version": "supplement_release_inventory_v1",
        "source_manifest_schema_version": source.get("schema_version"),
        "inventory_scope": "regression_fixture_source_snapshot_file_inventory",
        "subset_manifest": "manifests/representative_subset.json",
        "answer_contract_version": source.get("answer_contract_version"),
        "answer_representation": source.get("answer_representation"),
        "layout": source.get("layout"),
        "families": source.get("families"),
        "totals": source.get("totals"),
        "files": files,
        "note": (
            "Paths are relative to the source snapshot root."
        ),
    }


def build(release_root: Path, output_root: Path) -> None:
    manifest_rows: list[dict[str, Any]] = []
    write_original_subset(
        release_root=release_root,
        output_root=output_root,
        family="json",
        slots=(
            (
                "test/8k/shared_tasks",
                Path("json/test/json_test_8k.jsonl"),
                "all_tasks",
            ),
            ("test/128k/structure", Path("json/test/json_test_128k.jsonl"), "first"),
            (
                "train/32k/shared_tasks",
                Path("json/train/json_train_32k.jsonl"),
                "all_tasks",
            ),
            (
                "dev/32k/shared_tasks",
                Path("json/dev/json_dev_32k.jsonl"),
                "all_tasks",
            ),
        ),
        manifest_rows=manifest_rows,
        normalize_json_identifiers=True,
    )
    for family in ("html", "jss"):
        write_original_subset(
            release_root=release_root,
            output_root=output_root,
            family=family,
            slots=(
                (
                    "test/8k/shared_tasks",
                    Path(f"{family}/test/{family}_test_8k.jsonl"),
                    "all_tasks",
                ),
                (
                    "test/128k/structure",
                    Path(f"{family}/test/{family}_test_128k.jsonl")
                    if family == "html"
                    else Path("jss/test/jss_test_128k_part00.jsonl"),
                    "first",
                ),
            ),
            manifest_rows=manifest_rows,
            exclude_email=(family == "html"),
        )
    write_yaml_fixtures(output_root, manifest_rows)

    manifests = output_root / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    inventory = sanitized_release_manifest(release_root)
    (manifests / "release_inventory.json").write_bytes(canonical_json(inventory))

    counts: dict[str, dict[str, int]] = {}
    for row in manifest_rows:
        family_counts = counts.setdefault(
            row["family"], {"selected_release_record": 0, "synthetic_fixture": 0}
        )
        family_counts[row["kind"]] += 1
    subset_manifest = {
        "schema_version": "supplement_subset_manifest_v1",
        "selection_rule": (
            "First release row in each declared task slot; HTML selection uses "
            "the first row without an email address. The first eligible row of "
            "the 128K bucket is the structural example. YAML slots are "
            "deterministic synthetic fixtures and are not length-materialized."
        ),
        "source_metadata_note": (
            "Review labels are normalized to JSON, HTML, YAML, and JavaScript. "
            "JSON machine identifiers and HTML/JavaScript packaging labels are "
            "normalized; answers and gold programs are unchanged. Selected questions "
            "and scoring contracts have explicit sample_revision fields. "
            "JSON review and business-reference fields use synthetic placeholders; "
            "length and position metadata describe the source snapshot only. "
            "Original source and packaged line hashes are recorded separately."
        ),
        "counts": counts,
        "total_records": len(manifest_rows),
        "records": manifest_rows,
    }
    (manifests / "representative_subset.json").write_bytes(
        canonical_json(subset_manifest)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-root",
        type=Path,
        required=True,
        help="Path containing manifest.json and json/html/yaml/jss directories.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Package root receiving data/ and manifests/.",
    )
    args = parser.parse_args()
    build(args.release_root.resolve(), args.output_root.resolve())


if __name__ == "__main__":
    main()
