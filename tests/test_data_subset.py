from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from data_construction.validate_subset import validate


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class DataSubsetTest(unittest.TestCase):
    def test_representative_subset_and_manifests(self) -> None:
        summary = validate(PACKAGE_ROOT)
        self.assertEqual(summary["records"], 52)
        self.assertEqual(summary["selected_release_records"], 43)
        self.assertEqual(summary["synthetic_yaml_fixtures"], 9)
        self.assertEqual(summary["real_yaml_documents"], 2)
        self.assertEqual(summary["json_source_examples"], 8)
        self.assertEqual(summary["json_source_documents"], 9)
        self.assertEqual(summary["families"], ["html", "json", "jss", "yaml"])
        self.assertEqual(summary["tasks_per_family"], 8)

    def test_rejects_changed_source_input_after_line_hash_refresh(self):
        from data_construction.validate_subset import validate_json_source_examples
        temporary, root = self.temporary_package()
        with temporary:
            data_path = root / 'data/json/source_examples.jsonl'
            lines = data_path.read_bytes().splitlines(keepends=True)
            row = json.loads(lines[0])
            row['input'] += ' '
            lines[0] = (json.dumps(row) + '\n').encode()
            data_path.write_bytes(b''.join(lines))
            manifest_path = root / 'manifests/json_source_examples.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['records'][0]['package_line_sha256'] = hashlib.sha256(lines[0]).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'input hash mismatch'):
                validate_json_source_examples(root)

    def temporary_package(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(PACKAGE_ROOT / "data", root / "data")
        shutil.copytree(PACKAGE_ROOT / "manifests", root / "manifests")
        shutil.copytree(PACKAGE_ROOT / "third_party_licenses", root / "third_party_licenses")
        return temporary, root

    def test_rejects_declared_record_count_mismatch(self) -> None:
        temporary, root = self.temporary_package()
        with temporary:
            path = root / "manifests" / "representative_subset.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["total_records"] = 51
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "total_records"):
                validate(root)

    def test_rejects_manifest_field_mismatch(self) -> None:
        temporary, root = self.temporary_package()
        with temporary:
            path = root / "manifests" / "representative_subset.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["records"][0]["split"] = "dev"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "slot layout"):
                validate(root)

    def test_rejects_source_path_mismatch(self) -> None:
        temporary, root = self.temporary_package()
        with temporary:
            path = root / "manifests" / "representative_subset.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["records"][0]["source_release_path"] = (
                "json/test/json_test_16k.jsonl"
            )
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source path mismatch"):
                validate(root)

    def test_rejects_inventory_total_mismatch(self) -> None:
        temporary, root = self.temporary_package()
        with temporary:
            path = root / "manifests" / "release_inventory.json"
            inventory = json.loads(path.read_text(encoding="utf-8"))
            inventory["totals"]["bytes"] -= 1
            path.write_text(json.dumps(inventory), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inventory totals"):
                validate(root)

    def test_rejects_incorrect_yaml_reference_answer(self) -> None:
        temporary, root = self.temporary_package()
        with temporary:
            data_path = root / "data" / "yaml" / "synthetic_fixtures.jsonl"
            rows = data_path.read_bytes().splitlines(keepends=True)
            row = json.loads(rows[0])
            row["answer"] = "False"
            row["gold_answer"] = "False"
            row["answers"] = ["False"]
            row["structured_answer"] = "False"
            rows[0] = (
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            data_path.write_bytes(b"".join(rows))

            manifest_path = root / "manifests" / "representative_subset.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["records"][43]["package_line_sha256"] = hashlib.sha256(
                rows[0]
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reference answer mismatch"):
                validate(root)

    def test_rejects_yaml_multi_record_same_document(self) -> None:
        temporary, root = self.temporary_package()
        with temporary:
            data_path = root / "data" / "yaml" / "synthetic_fixtures.jsonl"
            rows = data_path.read_bytes().splitlines(keepends=True)
            row = json.loads(rows[1])
            row["gold_spec"]["paths"][1] = row["gold_spec"]["paths"][0]
            rows[1] = (
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            data_path.write_bytes(b"".join(rows))

            manifest_path = root / "manifests" / "representative_subset.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["records"][44]["package_line_sha256"] = hashlib.sha256(
                rows[1]
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "distinct source documents"):
                validate(root)

    def test_rejects_yaml_numeric_without_same_name_constraint(self) -> None:
        temporary, root = self.temporary_package()
        with temporary:
            data_path = root / "data" / "yaml" / "synthetic_fixtures.jsonl"
            rows = data_path.read_bytes().splitlines(keepends=True)
            row = json.loads(rows[7])
            row["gold_spec"]["record_filter_field"] = None
            rows[7] = (
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            data_path.write_bytes(b"".join(rows))

            manifest_path = root / "manifests" / "representative_subset.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["records"][50]["package_line_sha256"] = hashlib.sha256(
                rows[7]
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "constrain a parameter name"):
                validate(root)

    def test_rejects_html_email_address(self) -> None:
        temporary, root = self.temporary_package()
        with temporary:
            data_path = root / "data" / "html" / "representative.jsonl"
            rows = data_path.read_bytes().splitlines(keepends=True)
            row = json.loads(rows[0])
            test_email = "contact" + chr(64) + "example.org"
            row["context"] += "\n" + test_email
            rows[0] = (
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            ).encode("utf-8")
            data_path.write_bytes(b"".join(rows))

            digest = hashlib.sha256(rows[0]).hexdigest()
            manifest_path = root / "manifests" / "representative_subset.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry = manifest["records"][25]
            entry["package_line_sha256"] = digest
            entry["source_line_sha256"] = digest
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "email address"):
                validate(root)


if __name__ == "__main__":
    unittest.main()
