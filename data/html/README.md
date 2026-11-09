# HTML examples

`representative.jsonl` contains nine WebSRC v1.0 examples: one per shared task
and an additional long-context example for structural inspection. Each record
includes its answer, source identifiers, and HTML context. Aggregate
questions specify movie records or vehicle columns as their counting unit.

Selection uses the first eligible record per task and excludes records containing
email addresses. Packaging titles, attributes, and format labels are normalized.
Source attribution and hashes are recorded in `manifests/representative_subset.json`
and `third_party_licenses/WebSRC-NOTICE.txt`. WebSRC declares CC BY 4.0.
