# Answer scoring

`evaluation.replay` scores extracted predictions using the matching rule in
each record's `metric_type`. Run this command from the package root:

```bash
PYTHONPATH=code python3 -m evaluation.replay \
  --input examples/toy_predictions.jsonl \
  --output /tmp/toy_score_summary.json
```

Each input line is a JSON object with these fields:

| Field | Value |
|---|---|
| `id` | Optional example identifier |
| `prediction` | Extracted answer string; missing or null means an empty answer |
| `gold` | Reference answer string |
| `metric_type` | One of the matching rules below |

| Matching rule | Answer format and behavior |
|---|---|
| `accuracy_string` | A single value; normalize case and surrounding formatting, with numeric tolerance as a fallback |
| `exact_number_match` | A complete finite decimal scalar; compare exactly, accepting equivalent scientific notation |
| `approx_number_match` | A numeric scalar, such as `"3"`; tolerance is `max(0.01, 0.001 * abs(gold))` |
| `ordered_list_str_match` | A JSON array encoded as a string, or one value per line; match corresponding positions |
| `unordered_list_str_match` | A JSON array encoded as a string, or comma/newline-separated values; maximum one-to-one matching with multiplicity and numerical tolerance |

For example:

```json
{"id":"count","prediction":"3","gold":"3","metric_type":"approx_number_match"}
{"id":"two-fields","prediction":"[\"a\",\"\"]","gold":"[\"a\"]","metric_type":"ordered_list_str_match"}
```

These rows score `1.0` and `0.5`. Empty list slots count toward length and retain
their positions. An empty slot cannot match a value. Empty answers receive zero.
The output contains each example's score and the mean over the supplied rows.
Signs are retained: `[5]` does not match `[-5]`. Numeric list values use the
same tolerance as scalar answers, including in unordered lists.
Use `analysis.macro_by` to group rows for the paper's task/length aggregation.

## Exact numeric matching

The JavaScript numeric-extreme sample `jss_2aac94a0d72f00388c30` opts into
`exact_number_match`. Its minimum is `1e-12`: `0.000000000001` is equivalent,
but `0`, `0.001` and `0.01` are incorrect. A decimal parser avoids floating-point
rounding and rejects prose, units, arrays, booleans and non-finite values.
Pass the extracted scalar answer, without a host-specific answer wrapper.

## API source examples

`data/json/source_examples.jsonl` stores source documents and questions for
inspection. Each row keeps its source `answer_protocol`, `public_required_slots`,
and `gold_answer`. These answers are typed JSON arrays; the mandatory
`instructions` and questions specify exact matching and frequency-tie rules.
Both text fields must accompany the input when querying a model.
The command in `data/json/README.md`
parses the source documents and answers while preserving those types.

Replay records use the extracted-answer schema above and the paper's matching
rules. `metric_type` selects the rule for each record. Source `answer_protocol`
and replay `metric_type` describe separate scoring contracts.
