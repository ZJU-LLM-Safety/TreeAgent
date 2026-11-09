# Data provenance and privacy transformations

The API examples in `data/json/source_examples.jsonl` retain complete public
source documents, questions, and answers. Their manifest records API endpoints
and source hashes. OpenAPI, HTML, and JavaScript examples preserve upstream
attribution and license notices.

The 25 records in `data/json/regression_fixtures.jsonl` derive from
ComplexFuncBench and apply `review_privacy_placeholders_v1`:

- Individual review objects retain their keys and scalar types; identifying
  fields and narratives are replaced with synthetic values.
- Opaque offer/search and encoded business references use
  `REDACTED_BUSINESS_REFERENCE_NOT_USABLE`.
- Search-context fields receive synthetic values of the same types.

`code/data_construction/privacy.py` implements the transformation. Each fixture
records its policy, replacement counts, and `whole_record_synthetic: false`.
Source and packaged hashes are retained separately. The transformation preserves
answer evidence, gold programs, and supporting paths. Length and position metadata refer
to the source snapshot; planning checks measure packaged content directly.

The toy documents and nine YAML regression fixtures are generated examples.
