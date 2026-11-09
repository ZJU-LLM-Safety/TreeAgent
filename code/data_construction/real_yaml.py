"""Prepare and verify two source-backed YAML inspection examples.

Each example pairs a complete supporting document with its original lookup
question and answer. Validation reads local source files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from treeagent.native_tree import _parser


SELECTION = (
    ("openapi-converter", "For GET /badge in Swagger2OpenAPI Converter, what is the response 301 description?",
     "Mermade-openapi-webconverter-LICENSE.txt",
     "https://github.com/Mermade/openapi-webconverter/blob/main/LICENSE", "BSD-3-Clause"),
    ("mtaa", "For GET /{country} in Mtaa API Documentation, what is the operation ID?",
     "Mtaa-API-LICENSE.txt",
     "https://github.com/HackEAC/mtaaAPI/blob/main/LICENSE", "MIT"),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()


def lookup(text: str, parts: list[str]) -> str:
    """Read a mapping-only scalar path through the existing YAML CST parser."""
    raw = text.encode()
    root = _parser("yaml").parse(raw).root_node
    if root.has_error:
        raise ValueError("malformed real YAML")
    documents = [n for n in root.named_children if n.type == "document"]
    if len(documents) != 1:
        raise ValueError("expected one complete YAML document")

    def unwrap(node):
        while node.type in {"document", "block_node", "flow_node"}:
            children = [c for c in node.named_children if c.type != "comment"]
            if len(children) != 1:
                raise ValueError("unsupported YAML wrapper")
            node = children[0]
        return node

    def scalar(node):
        node = unwrap(node)
        value = raw[node.start_byte:node.end_byte].decode()
        if node.type == "double_quote_scalar":
            return json.loads(value)
        if node.type == "single_quote_scalar":
            return value[1:-1].replace("''", "'")
        if node.type == "plain_scalar":
            return value
        raise ValueError("unsupported scalar in real YAML lookup")

    node = documents[0]
    for part in parts:
        node = unwrap(node)
        if node.type not in {"block_mapping", "flow_mapping"}:
            raise ValueError("lookup must traverse mappings")
        matches = []
        for entry in node.named_children:
            key = entry.child_by_field_name("key")
            if key is not None and scalar(key) == part:
                matches.append(entry.child_by_field_name("value"))
        if len(matches) != 1 or matches[0] is None:
            raise ValueError("missing or ambiguous YAML key")
        node = matches[0]
    return scalar(node)


def prepare(row_file: Path, source_store: Path, source_manifest: Path, root: Path) -> None:
    originals = [(line, json.loads(line)) for line in row_file.read_bytes().splitlines(keepends=True)]
    sources = {s["source_id"]: s for s in map(json.loads, source_manifest.read_text().splitlines())}
    entries, records = [], []
    for slug, question, license_file, license_url, repository_license in SELECTION:
        line, row = next((line, row) for line, row in originals if row["question"] == question)
        spec = row["gold_spec"]
        if spec["op"] != "yaml_path_value":
            raise ValueError("expected single-document lookup")
        index = spec["doc_index"]
        source_hash = row["source_refs"][index]["sha256"]
        payload = (source_store / "yaml" / source_hash).read_bytes()
        if digest(payload) != source_hash:
            raise ValueError("source hash mismatch")
        provenance = sources[row["metadata"]["context_source_ids"][index]]
        if "mit" not in provenance["declared_license_name"].lower():
            raise ValueError("selected document must declare MIT")
        relative = f"data/yaml/native/{slug}.yaml"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        license_path = f"third_party_licenses/{license_file}"
        record = {
            "uid": f"yaml_real_source_{slug}", "context_format": "yaml",
            "context": payload.decode(), "question": question,
            "answer": row["answer"], "gold_answer": row["gold_answer"],
            "task_subtype": row["task_subtype"], "metric_type": row["metric_type"],
            "gold_spec": {**spec, "doc_index": 0},
            "metadata": {"synthetic_fixture": False, "full_benchmark_row": False,
                         "length_bucket_claim": None,
                         "transform": "retain_complete_support_document_omit_other_documents",
                         "source_content_modified": False},
        }
        if lookup(record["context"], spec["path_parts"]) != record["gold_answer"]:
            raise ValueError("source-backed answer replay failed")
        record_bytes = encoded(record)
        records.append(record_bytes)
        entries.append({
            "uid": record["uid"], "source_path": relative, "source_sha256": source_hash,
            "api_title": provenance["api_title"],
            "apis_guru_download_url": provenance["apis_guru_download_url"],
            "origin_urls": provenance["origin_urls"],
            "raw_acquisition_sha256": provenance["raw_file_sha256"],
            "source_representation": "complete_semantic_compact_document_from_benchmark_store",
            "declared_document_license": provenance["declared_license_name"],
            "declared_license_url": provenance["declared_license_url"],
            "upstream_repository_license": repository_license,
            "license_evidence_url": license_url, "license_path": license_path,
            "license_sha256": digest((root / license_path).read_bytes()),
            "benchmark_row_sha256": digest(line), "benchmark_file_sha256": digest(row_file.read_bytes()),
            "original_support_document_index": index,
            "original_context_document_count": len(row["source_refs"]),
            "example_line_sha256": digest(record_bytes),
        })
    (root / "data/yaml/real_examples.jsonl").write_bytes(b"".join(records))
    (root / "manifests/real_yaml_examples.json").write_bytes(encoded({
        "schema": "real_yaml_source_examples_v1", "examples": entries,
        "scope": "Two complete supporting YAML documents paired with their original questions and answers.",
    }))
    validate(root)


def validate(root: Path) -> dict:
    manifest = json.loads((root / "manifests/real_yaml_examples.json").read_text())
    lines = (root / "data/yaml/real_examples.jsonl").read_bytes().splitlines(keepends=True)
    entries = manifest["examples"]
    if manifest["schema"] != "real_yaml_source_examples_v1" or len(entries) != 2 or len(lines) != 2:
        raise ValueError("unexpected real YAML example inventory")
    expected_files = set()
    for line, entry, selection in zip(lines, entries, SELECTION):
        slug, question, license_file, license_url, repository_license = selection
        expected_path = f"data/yaml/native/{slug}.yaml"
        if entry["source_path"] != expected_path or entry["license_path"] != f"third_party_licenses/{license_file}":
            raise ValueError("unexpected real YAML artifact path")
        expected_files.add((root / expected_path).resolve())
        row = json.loads(line)
        payload = (root / expected_path).read_bytes()
        if digest(line) != entry["example_line_sha256"] or digest(payload) != entry["source_sha256"]:
            raise ValueError("real YAML checksum mismatch")
        if digest((root / entry["license_path"]).read_bytes()) != entry["license_sha256"]:
            raise ValueError("real YAML license checksum mismatch")
        if row["context"].encode() != payload or row["uid"] != entry["uid"]:
            raise ValueError("real YAML source/example mismatch")
        metadata = row["metadata"]
        if metadata["synthetic_fixture"] is not False or metadata["full_benchmark_row"] is not False or metadata["length_bucket_claim"] is not None:
            raise ValueError("incorrect real YAML scope disclosure")
        if row["question"] != question or row["gold_spec"]["doc_index"] != 0:
            raise ValueError("unexpected real YAML question or document index")
        if entry["license_evidence_url"] != license_url or entry["upstream_repository_license"] != repository_license:
            raise ValueError("unexpected license declaration")
        answer = lookup(row["context"], row["gold_spec"]["path_parts"])
        if answer != row["gold_answer"] or answer != row["answer"]:
            raise ValueError("real YAML reference answer mismatch")
    actual = {p.resolve() for p in (root / "data/yaml/native").rglob('*') if p.is_file()}
    if actual != expected_files:
        raise ValueError("unexpected native YAML files")
    return {"real_yaml_documents": len(entries), "source_backed_questions_replayed": len(lines)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--row-file", type=Path)
    parser.add_argument("--source-store", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    args = parser.parse_args()
    if any((args.row_file, args.source_store, args.source_manifest)):
        if not all((args.row_file, args.source_store, args.source_manifest)):
            parser.error("preparation requires all three source arguments")
        prepare(args.row_file, args.source_store, args.source_manifest, args.package_root)
    print(json.dumps(validate(args.package_root), indent=2))


if __name__ == "__main__":
    main()
