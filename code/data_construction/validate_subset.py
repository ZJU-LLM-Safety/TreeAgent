#!/usr/bin/env python3
"""Validate the representative benchmark records and their manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from .privacy import POLICY, validate_private_fields
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
TASK_SET = set(TASKS)
REQUIRED_FIELDS = {
    "uid",
    "split",
    "length_bucket",
    "task_type",
    "task_subtype",
    "context",
    "question",
    "gold_spec",
    "answer",
    "gold_answer",
    "answer_contract_version",
}
EXPECTED_COUNTS = {
    "json": {"selected_release_record": 25, "synthetic_fixture": 0},
    "html": {"selected_release_record": 9, "synthetic_fixture": 0},
    "yaml": {"selected_release_record": 0, "synthetic_fixture": 9},
    "jss": {"selected_release_record": 9, "synthetic_fixture": 0},
}
EXPECTED_INVENTORY_TOTALS = {
    "files": 269,
    "bytes": 15_101_344_756,
    "physical_rows": 48_800,
    "expected_unique_rows": 29_200,
}
EXPECTED_FAMILY_INVENTORY = {
    "json": {
        "files": 13,
        "bytes": 11_072_335_308,
        "physical_rows": 39_200,
        "expected_unique_rows": 19_600,
        "splits": ["train", "dev", "test"],
    },
    "html": {
        "files": 81,
        "bytes": 2_133_455_331,
        "physical_rows": 3_200,
        "expected_unique_rows": 3_200,
        "splits": ["test"],
    },
    "yaml": {
        "files": 81,
        "bytes": 60_544_516,
        "physical_rows": 3_200,
        "expected_unique_rows": 3_200,
        "splits": ["test"],
    },
    "jss": {
        "files": 94,
        "bytes": 1_835_009_601,
        "physical_rows": 3_200,
        "expected_unique_rows": 3_200,
        "splits": ["test"],
    },
}
FAMILY_PATHS = {
    "json": "data/json/regression_fixtures.jsonl",
    "html": "data/html/representative.jsonl",
    "yaml": "data/yaml/synthetic_fixtures.jsonl",
    "jss": "data/javascript/representative.jsonl",
}
EXPECTED_SOURCE_PATHS = {
    ("json", "test/8k/shared_tasks"): "json/test/json_test_8k.jsonl",
    ("json", "test/128k/structure"): "json/test/json_test_128k.jsonl",
    ("json", "train/32k/shared_tasks"): "json/train/json_train_32k.jsonl",
    ("json", "dev/32k/shared_tasks"): "json/dev/json_dev_32k.jsonl",
    ("html", "test/8k/shared_tasks"): "html/test/html_test_8k.jsonl",
    ("html", "test/128k/structure"): "html/test/html_test_128k.jsonl",
    ("jss", "test/8k/shared_tasks"): "jss/test/jss_test_8k.jsonl",
    ("jss", "test/128k/structure"): "jss/test/jss_test_128k_part00.jsonl",
}
EMAIL_PATTERN = re.compile(
    rb"(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"
    rb"(?![A-Z0-9._%+-])"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_jsonl(path: Path) -> list[tuple[bytes, dict[str, Any]]]:
    output = []
    with path.open("rb") as stream:
        for line_number, raw in enumerate(stream, start=1):
            if not raw.strip():
                raise ValueError(f"{path}:{line_number}: blank line")
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from error
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: row must be an object")
            output.append((raw, row))
    return output


def expected_layout() -> Counter[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []

    def add(
        family: str,
        kind: str,
        slot: str,
        task: str,
        split: str,
        length: str,
    ) -> None:
        rows.append(
            (family, kind, slot, task, split, length, FAMILY_PATHS[family])
        )

    for task in TASKS:
        add(
            "json",
            "selected_release_record",
            "test/8k/shared_tasks",
            task,
            "test",
            "8k",
        )
        add(
            "html",
            "selected_release_record",
            "test/8k/shared_tasks",
            task,
            "test",
            "8k",
        )
        add(
            "jss",
            "selected_release_record",
            "test/8k/shared_tasks",
            task,
            "test",
            "8k",
        )
        add(
            "yaml",
            "synthetic_fixture",
            f"test/8k/{task}",
            task,
            "fixture",
            "synthetic",
        )
        add(
            "json",
            "selected_release_record",
            "train/32k/shared_tasks",
            task,
            "train",
            "32k",
        )
        add(
            "json",
            "selected_release_record",
            "dev/32k/shared_tasks",
            task,
            "dev",
            "32k",
        )
    for family, kind, split, length in (
        ("json", "selected_release_record", "test", "128k"),
        ("html", "selected_release_record", "test", "128k"),
        ("jss", "selected_release_record", "test", "128k"),
        ("yaml", "synthetic_fixture", "fixture", "synthetic"),
    ):
        add(
            family,
            kind,
            "test/128k/structure",
            "record_field_lookup",
            split,
            length,
        )
    return Counter(rows)


def layout_key(entry: dict[str, Any]) -> tuple[Any, ...]:
    return (
        entry.get("family"),
        entry.get("kind"),
        entry.get("slot"),
        entry.get("task"),
        entry.get("split"),
        entry.get("declared_length_bucket"),
        entry.get("package_path"),
    )


def rendered_answer(row: dict[str, Any]) -> str:
    answers = row.get("answers")
    if isinstance(answers, list):
        joined = "\n".join(str(value) for value in answers)
        if joined != str(row["answer"]):
            raise ValueError(f"{row['uid']}: answers list disagrees with answer")
    if str(row["answer"]) != str(row["gold_answer"]):
        raise ValueError(f"{row['uid']}: answer disagrees with gold answer")
    return str(row["answer"])


def parse_yaml_fixture(context: str) -> list[list[dict[str, Any]]]:
    documents: list[list[dict[str, Any]]] = []
    for raw_document in context.split("---\n"):
        if not raw_document.strip():
            continue
        parameters: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for raw_line in raw_document.splitlines():
            line = raw_line.strip()
            if line.startswith("- name:"):
                current = {"name": line.split(":", 1)[1].strip(), "schema": {}}
                parameters.append(current)
                continue
            if current is None or ":" not in line:
                continue
            key, raw_value = (part.strip() for part in line.split(":", 1))
            if key in {"in", "description"}:
                current[key] = raw_value
            elif key == "required":
                current[key] = raw_value.lower() == "true"
            elif key in {"type", "format"}:
                current["schema"][key] = raw_value
            elif key == "maximum":
                current["schema"][key] = int(raw_value)
        documents.append(parameters)
    if len(documents) != 4 or any(len(parameters) != 1 for parameters in documents):
        raise ValueError(
            "synthetic YAML fixture must contain four source documents with one "
            "parameter record each"
        )
    return documents


def yaml_lookup(documents: list[list[dict[str, Any]]], path: str) -> Any:
    match = re.search(
        r"^\$\[(\d+)\].*parameters\[(\d+)\]"
        r"(?:\.schema)?\.(description|format|in|maximum|required|type)$",
        path,
    )
    if not match:
        raise ValueError(f"unsupported synthetic YAML path: {path}")
    document_index = int(match.group(1))
    parameter_index = int(match.group(2))
    key = match.group(3)
    record = documents[document_index][parameter_index]
    if key in {"format", "maximum", "type"}:
        return record["schema"][key]
    return record[key]


def replay_yaml_fixture(row: dict[str, Any]) -> str:
    documents = parse_yaml_fixture(str(row["context"]))
    parameters = [document[0] for document in documents]
    spec = row["gold_spec"]
    operation = spec.get("op")
    if operation == "yaml_path_value":
        document_index = int(spec["doc_index"])
        parameter_index = int(spec["path_parts"][-2])
        value = documents[document_index][parameter_index][
            str(spec["path_parts"][-1])
        ]
    elif operation == "multi_answer_text":
        document_indices = [
            int(re.match(r"^\$\[(\d+)\]", path).group(1))
            for path in spec["paths"]
        ]
        if (
            str(row["task_subtype"]).startswith("multi_record_field_")
            and len(document_indices) != len(set(document_indices))
        ):
            raise ValueError(
                "synthetic multi-record fixture must use distinct source documents"
            )
        value = [yaml_lookup(documents, path) for path in spec["paths"]]
    elif operation == "openapi_semantic_conditional_count":
        target = spec["predicate_value"]
        value = sum(record["schema"]["format"] == target for record in parameters)
    elif operation == "openapi_semantic_topk_values":
        values = [record["in"] for record in parameters]
        counts = Counter(values)
        first = {item: values.index(item) for item in counts}
        value = [
            item
            for item, _ in sorted(
                counts.items(), key=lambda pair: (-pair[1], first[pair[0]])
            )[: int(spec["top_k"])]
        ]
    elif operation == "openapi_semantic_numeric_extreme":
        if spec.get("record_filter_field") != "parameter_name":
            raise ValueError("numeric fixture must constrain a parameter name")
        parameter_name = spec.get("record_filter_value")
        values = [
            record["schema"]["maximum"]
            for record in parameters
            if record["name"] == parameter_name
        ]
        if len(values) < 2:
            raise ValueError(
                "numeric fixture must compare repeated same-name parameters"
            )
        value = max(values) if spec["agg"] == "max" else min(values)
    else:
        raise ValueError(f"unsupported synthetic YAML operation: {operation}")
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value)


def validate_inventory(inventory: dict[str, Any]) -> None:
    if inventory.get("schema_version") != "supplement_release_inventory_v1":
        raise ValueError("unexpected benchmark inventory schema")
    if inventory.get("inventory_scope") != "regression_fixture_source_snapshot_file_inventory":
        raise ValueError("unexpected benchmark inventory scope")
    if inventory.get("subset_manifest") != "manifests/representative_subset.json":
        raise ValueError("unexpected source inventory subset link")
    if inventory.get("answer_contract_version") != "ordered_values_v2":
        raise ValueError("unexpected inventory answer contract")
    if inventory.get("answer_representation") != "value_only":
        raise ValueError("unexpected inventory answer representation")
    if inventory.get("totals") != EXPECTED_INVENTORY_TOTALS:
        raise ValueError("benchmark inventory totals do not match the release")
    if inventory.get("families") != EXPECTED_FAMILY_INVENTORY:
        raise ValueError("benchmark family inventory does not match the release")

    files = inventory.get("files")
    if not isinstance(files, list):
        raise ValueError("benchmark inventory files must be a list")
    paths: set[str] = set()
    computed = {
        family: {"files": 0, "bytes": 0, "physical_rows": 0}
        for family in EXPECTED_FAMILY_INVENTORY
    }
    for item in files:
        if "source" in item:
            raise ValueError("benchmark inventory contains a local source path")
        path = item.get("path")
        if not isinstance(path, str):
            raise ValueError("benchmark inventory path must be a string")
        pure_path = PurePosixPath(path)
        if pure_path.is_absolute() or ".." in pure_path.parts:
            raise ValueError(f"unsafe benchmark inventory path: {path}")
        if path in paths:
            raise ValueError(f"duplicate benchmark inventory path: {path}")
        paths.add(path)
        family = item.get("family")
        if family not in computed or pure_path.parts[0] != family:
            raise ValueError(f"invalid family for benchmark path: {path}")
        if item.get("split") not in EXPECTED_FAMILY_INVENTORY[family]["splits"]:
            raise ValueError(f"invalid split for benchmark path: {path}")
        if not SHA256_PATTERN.fullmatch(str(item.get("sha256", ""))):
            raise ValueError(f"invalid SHA-256 for benchmark path: {path}")
        for key in ("bytes", "rows"):
            if not isinstance(item.get(key), int) or item[key] < 0:
                raise ValueError(f"invalid {key} for benchmark path: {path}")
        computed[family]["files"] += 1
        computed[family]["bytes"] += item["bytes"]
        computed[family]["physical_rows"] += item["rows"]
    for family, actual in computed.items():
        expected = EXPECTED_FAMILY_INVENTORY[family]
        for key, value in actual.items():
            if value != expected[key]:
                raise ValueError(
                    f"{family}: computed inventory {key} {value} != {expected[key]}"
                )
    if len(files) != EXPECTED_INVENTORY_TOTALS["files"]:
        raise ValueError("benchmark inventory file count is inconsistent")


def validate(package_root: Path) -> dict[str, Any]:
    manifest_path = package_root / "manifests" / "representative_subset.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "supplement_subset_manifest_v1":
        raise ValueError("unexpected subset manifest schema")
    expected = manifest.get("records")
    if not isinstance(expected, list):
        raise ValueError("subset manifest records must be a list")
    if manifest.get("total_records") != len(expected):
        raise ValueError("subset manifest total_records is inconsistent")

    declared_layout = Counter(layout_key(entry) for entry in expected)
    if declared_layout != expected_layout():
        raise ValueError("subset manifest does not match the declared slot layout")

    by_path: dict[str, list[dict[str, Any]]] = {}
    for entry in expected:
        by_path.setdefault(entry["package_path"], []).append(entry)
    actual_data_paths = {
        path.relative_to(package_root).as_posix()
        for path in (package_root / "data").glob("*/*.jsonl")
    }
    if actual_data_paths != set(by_path) | {"data/yaml/real_examples.jsonl", "data/json/source_examples.jsonl"}:
        raise ValueError("packaged JSONL files do not match the subset manifest")

    seen_uids: set[str] = set()
    family_tasks: dict[str, set[str]] = {}
    computed_counts = {
        family: {"selected_release_record": 0, "synthetic_fixture": 0}
        for family in EXPECTED_COUNTS
    }
    for relative_path, entries in by_path.items():
        path = package_root / relative_path
        rows = read_jsonl(path)
        if len(rows) != len(entries):
            raise ValueError(
                f"{relative_path}: {len(rows)} rows, manifest declares {len(entries)}"
            )
        family_from_path = next(
            family for family, family_path in FAMILY_PATHS.items()
            if family_path == relative_path
        )
        for index, ((raw, row), entry) in enumerate(zip(rows, entries), start=1):
            missing = REQUIRED_FIELDS - row.keys()
            if missing:
                raise ValueError(f"{relative_path}:{index}: missing {sorted(missing)}")
            if entry["family"] != family_from_path:
                raise ValueError(f"{relative_path}:{index}: family mismatch")
            if row["uid"] != entry["uid"]:
                raise ValueError(f"{relative_path}:{index}: UID mismatch")
            if entry["package_line"] != index:
                raise ValueError(f"{relative_path}:{index}: line number mismatch")
            if sha256(raw) != entry["package_line_sha256"]:
                raise ValueError(f"{relative_path}:{index}: line hash mismatch")
            if row["uid"] in seen_uids:
                raise ValueError(f"duplicate UID: {row['uid']}")
            seen_uids.add(row["uid"])
            task = row["task_subtype"]
            if task not in TASK_SET:
                raise ValueError(f"{relative_path}:{index}: unknown task {task!r}")
            for row_key, entry_key in (
                ("task_subtype", "task"),
                ("split", "split"),
                ("length_bucket", "declared_length_bucket"),
            ):
                if row[row_key] != entry[entry_key]:
                    raise ValueError(
                        f"{relative_path}:{index}: {row_key} disagrees with manifest"
                    )
            if row["answer_contract_version"] != "ordered_values_v2":
                raise ValueError(f"{relative_path}:{index}: wrong answer contract")
            answer = rendered_answer(row)
            if revise_sample(row) != row:
                raise ValueError(f'{relative_path}:{index}: missing sample contract revision')
            if row.get('sample_revision') != entry.get('sample_revision'):
                raise ValueError(f'{relative_path}:{index}: sample revision mismatch')
            family_tasks.setdefault(entry["family"], set()).add(task)
            kind = entry["kind"]
            if kind not in computed_counts[entry["family"]]:
                raise ValueError(f"{relative_path}:{index}: unknown record kind")
            computed_counts[entry["family"]][kind] += 1
            metadata = row.get("metadata", {})
            if kind == "synthetic_fixture":
                if entry["family"] != "yaml":
                    raise ValueError("only YAML records may be synthetic fixtures")
                if not metadata.get("synthetic_fixture"):
                    raise ValueError(f"{relative_path}:{index}: missing synthetic flag")
                if not metadata.get("not_length_materialized"):
                    raise ValueError(
                        f"{relative_path}:{index}: fixture must disclaim length"
                    )
                if row.get("context_format") != "yaml":
                    raise ValueError(f"{relative_path}:{index}: wrong fixture format")
                if row.get("representative_slot") != entry["slot"]:
                    raise ValueError(f"{relative_path}:{index}: fixture slot mismatch")
                if replay_yaml_fixture(row) != answer:
                    raise ValueError(
                        f"{relative_path}:{index}: fixture reference answer mismatch"
                    )
                if entry["source_release_path"] is not None:
                    raise ValueError(f"{relative_path}:{index}: fixture has source path")
                if entry["source_line_sha256"] is not None:
                    raise ValueError(f"{relative_path}:{index}: fixture has source hash")
            else:
                expected_source = EXPECTED_SOURCE_PATHS.get(
                    (entry["family"], entry["slot"])
                )
                if entry.get("source_release_path") != expected_source:
                    raise ValueError(f"{relative_path}:{index}: source path mismatch")
                if entry.get("package_transform") != "review_format_labels_v1":
                    raise ValueError(f"{relative_path}:{index}: missing review-label transform")
                if entry["family"] == "json":
                    if entry.get("privacy_transform") != POLICY:
                        raise ValueError("JSON manifest lacks privacy transform")
                    validate_private_fields(row)
                if not SHA256_PATTERN.fullmatch(str(entry.get("source_line_sha256", ""))):
                    raise ValueError(f"{relative_path}:{index}: invalid original source hash")
                if entry["family"] == "html" and EMAIL_PATTERN.search(raw):
                    raise ValueError(
                        f"{relative_path}:{index}: HTML row contains an email address"
                    )

    if manifest.get("counts") != computed_counts:
        raise ValueError("subset manifest counts are inconsistent")
    if computed_counts != EXPECTED_COUNTS:
        raise ValueError(f"unexpected record counts: {computed_counts}")
    for family in EXPECTED_COUNTS:
        if family_tasks.get(family) != TASK_SET:
            missing = TASK_SET - family_tasks.get(family, set())
            raise ValueError(
                f"{family}: incomplete shared task coverage; missing {missing}"
            )
    if len(seen_uids) != 52:
        raise ValueError(f"expected 52 unique records, found {len(seen_uids)}")

    inventory = json.loads(
        (package_root / "manifests" / "release_inventory.json").read_text(
            encoding="utf-8"
        )
    )
    validate_inventory(inventory)

    from .real_yaml import validate as validate_real_yaml
    real_yaml_summary = validate_real_yaml(package_root)

    return {
        **real_yaml_summary,
        **validate_json_source_examples(package_root),
        "records": len(seen_uids),
        "selected_release_records": sum(
            counts["selected_release_record"] for counts in computed_counts.values()
        ),
        "synthetic_yaml_fixtures": computed_counts["yaml"]["synthetic_fixture"],
        "families": sorted(family_tasks),
        "tasks_per_family": len(TASKS),
        "release_files": len(inventory["files"]),
        "release_bytes": inventory["totals"]["bytes"],
    }


def validate_json_source_examples(package_root: Path) -> dict:
    manifest = json.loads((package_root / 'manifests/json_source_examples.json').read_text())
    lines = (package_root / 'data/json/source_examples.jsonl').read_bytes().splitlines(keepends=True)
    if len(lines) != 8 or manifest['record_count'] != 8 or len(manifest['records']) != 8:
        raise ValueError('JSON source example count mismatch')
    tasks, groups, uids = set(), set(), set()
    document_count = 0
    for line, entry in zip(lines, manifest['records']):
        row = json.loads(line)
        if hashlib.sha256(line).hexdigest() != entry['package_line_sha256']:
            raise ValueError('JSON source example line hash mismatch')
        for key in ('uid', 'provider', 'task', 'input_sha256'):
            if row[key] != entry[key]:
                raise ValueError('JSON source example metadata mismatch')
        raw = row['input'].encode('utf-8')
        if hashlib.sha256(raw).hexdigest() != row['input_sha256']:
            raise ValueError('JSON source input hash mismatch')
        position = 0
        for index, document in enumerate(entry['documents']):
            if index:
                if raw[position:position + 1] != b'\n':
                    raise ValueError('JSON document separator mismatch')
                position += 1
            body = raw[position:position + document['utf8_bytes']]
            position += document['utf8_bytes']
            if hashlib.sha256(body).hexdigest() != document['sha256']:
                raise ValueError('JSON source document hash mismatch')
            json.loads(body)
            document_count += 1
        if position != len(raw) or not entry['documents']:
            raise ValueError('JSON source document coverage mismatch')
        answer = json.loads(row['gold_answer'])
        if not isinstance(answer, list) or len(answer) != row['public_required_slots']:
            raise ValueError('JSON source answer slots mismatch')
        tasks.add(row['task']); groups.add(entry['provider_group']); uids.add(row['uid'])
    if tasks != TASK_SET or len(groups) != 7 or len(uids) != 8:
        raise ValueError('JSON source task/provider coverage mismatch')
    return {'json_source_examples': len(lines), 'json_source_documents': document_count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args()
    summary = validate(args.package_root.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
