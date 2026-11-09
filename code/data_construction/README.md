# Sample preparation and validation

The package contains 62 JSONL records:

| Collection | Records | Purpose |
|---|---:|---|
| JSON API examples | 8 | Eight tasks across seven source groups |
| HTML examples | 9 | WebSRC task and structural examples |
| YAML source examples | 2 | OpenAPI lookup questions with supporting documents |
| JavaScript examples | 9 | Static structured-state questions |
| JSON regression fixtures | 25 | Task, sectioning, and privacy checks |
| YAML synthetic fixtures | 9 | Schema and task checks |

Run all sample checks from the package root:

```bash
PYTHONPATH=code python3 -m data_construction.validate_subset
```

API examples preserve complete source inputs and answers, paired with the revised
natural-language questions and mandatory instructions from the source package. Their
manifest lists per-input and per-document hashes and public endpoints. Validation
checks byte coverage, JSON parsing, answer slots, and task/source-group coverage.

`prepare_subset.py` extracts the task fixtures from a local source snapshot:

```bash
PYTHONPATH=code python3 -m data_construction.prepare_subset \
  --release-root /path/to/source/snapshot \
  --output-root /path/to/package
```

Selection takes the first record per task at the declared extraction slot and
an additional record for structural inspection. JSON contributes training and
development extraction slots as well. HTML selection excludes email addresses.
Format labels are normalized. `privacy.sanitize_json_row` replaces review and
business-reference fields with synthetic placeholders while preserving protected
answer evidence. Source and package hashes are recorded separately.
`sample_revisions.revise_sample` sets price-query wording, HTML record units,
synthetic-YAML output instructions and the JavaScript numeric metric.
Rows and manifest entries identify these revisions with `sample_revision`.
Length metadata describes the source snapshot. `manifests/sample_revisions.json` records the
packaged revision history, including earlier and revised line hashes.
`manifests/release_inventory.json` lists the source snapshot files used to
extract the regression fixtures. Its `subset_manifest` field links to
`manifests/representative_subset.json`. File paths are relative to the source
snapshot root. API source examples have their own document manifest,
`manifests/json_source_examples.json`.

YAML regression fixtures are generated from task schemas. The two OpenAPI source
examples are extracted by `real_yaml.py`, retaining complete supporting documents
and rebasing their answer document indices to zero:

```bash
PYTHONPATH=code python3 -m data_construction.real_yaml \
  --row-file /path/to/yaml_test_8k.jsonl \
  --source-store /path/to/sources \
  --source-manifest /path/to/source_manifest.jsonl
```

Run extraction with the upstream license notices present under
`third_party_licenses/`. The validator checks document, question, and license
hashes and replays both answer paths.

## Review inputs

Generate or verify the human-readable review guide and public inputs:

```bash
PYTHONPATH=code python3 -m data_construction.review_examples
PYTHONPATH=code python3 -m data_construction.review_examples --check
```

The exports under `examples/review/` cover all 62 examples.
Each `public_input.json` uses an explicit field
allowlist. Only `instructions`, `input`, and `question` form `prompt.txt`;
gold answers, gold programs and evidence locations are excluded. String input
bytes are preserved, including multi-document separators. Object-valued JSON
fixtures are compactly serialized from the packaged object. Answers are listed
separately in `ANSWERS.md`. Keep the exported instructions when integrating any
memory host; native memory/control procedures still belong to that host.
