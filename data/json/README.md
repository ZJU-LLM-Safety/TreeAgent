# JSON API examples

`source_examples.jsonl` contains eight examples spanning the eight task types
and seven source groups: USGS, NVD, NIH (RePORTER and ClinicalTrials.gov), GBIF,
Crossref, Contracts Finder, and USAspending.

Each row includes `provider`, `task`, `question`, mandatory `instructions`, the complete `input`,
`public_required_slots`, `answer_protocol`, `gold_answer`, and `input_sha256`.
Questions and instructions use the natural-language source version.
UIDs identify the question/instructions pairs; the manifest records source UIDs.
`gold_answer` is a JSON
array encoded as a string; keep it separate from model prompts.

An `input` contains one or more complete JSON response documents separated by
one newline. `manifests/json_source_examples.json` records each document's byte
length, SHA-256 hash, and API endpoint, in input order. The USGS example contains
two documents. The sectioning CLI accepts the complete multi-document input.
It plans all documents together under a virtual root with global section indices
and memory links. Source inputs retain the API's original whitespace and field
ordering; sectioning compactly serializes each document and joins them with a
newline without adding an outer JSON array.

To run a complete source example, first save its `input` as a text file:

```bash
python3 - <<'PY'
import json
from pathlib import Path
rows = [json.loads(line) for line in Path("data/json/source_examples.jsonl").read_text().splitlines()]
row = next(row for row in rows if row["provider"] == "USGS")
Path("/tmp/usgs_input.json").write_text(row["input"], encoding="utf-8")
PY
PYTHONPATH=code python3 -m treeagent.cli --input /tmp/usgs_input.json \
  --output /tmp/usgs_sections.json --section-size 5000
```

The CLI uses the deterministic character tokenizer. Model integrations use
`build_sections(parse_json_text(raw_text), model_tokenizer, 5000, "treeagent")`.
Process the resulting sections in one memory-agent run. Pass both the mandatory
instructions and question through the agent's question argument:

```python
agent_question = row["instructions"] + "\n\nQuestion\n" + row["question"]
```

The observations supply the input sections. Do not pass `gold_answer` to the model.

Run this command from the package root. It reads the two-document USGS example
and parses its answer as a typed JSON array:

```bash
python3 - <<'PY'
import json
from pathlib import Path

examples = [json.loads(line) for line in
            Path("data/json/source_examples.jsonl").read_text().splitlines()]
manifest = json.loads(Path("manifests/json_source_examples.json").read_text())
example_index = 1
row = examples[example_index]
entry = manifest["records"][example_index]
raw = row["input"].encode("utf-8")
documents = []
offset = 0
for index, document in enumerate(entry["documents"]):
    if index:
        assert raw[offset:offset + 1] == b"\n"
        offset += 1
    end = offset + document["utf8_bytes"]
    documents.append(json.loads(raw[offset:end]))
    offset = end
assert offset == len(raw)
answer = json.loads(row["gold_answer"])
print("Provider:", row["provider"])
print("Documents:", len(documents))
print("Instructions:", row["instructions"])
print("Question:", row["question"])
print("Answer protocol:", row["answer_protocol"])
print("Answer:", answer)
PY
```

`documents` contains the parsed response objects. `answer_protocol` describes
the source answer contract, including JSON types. For the paper's extracted
answer scoring, see `code/evaluation/README.md` for input fields, matching rules,
and a runnable command.

## Task regression fixtures

`regression_fixtures.jsonl` contains 25 ComplexFuncBench-derived records for task,
sectioning, and privacy regression checks. Price questions specify the rental
price and deposit fields with their USD/INR currencies.
Selected review and business-reference fields use synthetic
placeholders defined in `PRIVACY.md`. Source length and position metadata describe
the source records; planning checks measure the packaged inputs directly.
`manifests/representative_subset.json` records their extraction slots and hashes.
