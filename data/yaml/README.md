# YAML OpenAPI examples

`native/openapi-converter.yaml` and `native/mtaa.yaml` contain the complete
supporting OpenAPI documents for Swagger2OpenAPI Converter and Mtaa API,
acquired through APIs.guru. `real_examples.jsonl` pairs them with their lookup
questions and answers. Each context contains its supporting document, with the
answer's document index set to zero.

Source bytes, including upstream attribution, are preserved.
`manifests/real_yaml_examples.json` records source URLs, acquisition and document
hashes, question provenance, and license evidence. Both snapshot documents declare
MIT. The converter repository provides a BSD-3-Clause license file and the Mtaa
repository provides MIT; these notices are included under `third_party_licenses/`.

Validate the source documents and replay answer paths:

```bash
PYTHONPATH=code python3 -m data_construction.real_yaml
PYTHONPATH=code python3 -m treeagent.cli --format yaml \
  --input data/yaml/native/openapi-converter.yaml \
  --output /tmp/real_yaml_sections.json --section-size 512
```

## Synthetic regression fixtures

`synthetic_fixtures.jsonl` contains nine generated OpenAPI fixtures covering the
eight shared tasks and an additional structural case. They carry
`synthetic_fixture: true` and `not_length_materialized: true`. The fixtures
exercise record relationships, schema checks, and deterministic answer validation.
Every synthetic record declares its `metric_type` and `answer_format_instruction`.
Multi-value queries require one value per line in the requested order. Use the
public-input adapter in the top-level README to include these instructions in
model inputs. The additional structural case repeats the first lookup.
