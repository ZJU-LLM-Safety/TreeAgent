# JavaScript examples

`representative.jsonl` contains nine static JavaScript examples: one per shared
task and an additional long-context example for structural inspection.
Each record includes its question, answer, gold program, and source identifiers.
The numeric-extreme example uses `exact_number_match` to compare its minimum
`1e-12` exactly, accepting equivalent decimal and scientific notation.
Packaging source markers and binding prefixes use format-based names.

The records cover static object and array state. Source is parsed without
execution. The six upstream repositories use MIT licenses; their notices and
source manifest are under `third_party_licenses/`. Packaged row hashes are in
`manifests/representative_subset.json`.
