# Licenses and third-party notices

## Code and generated fixtures

Package code, toy documents under `examples/`, and the generated YAML fixtures
in `data/yaml/synthetic_fixtures.jsonl` use Apache License 2.0; see `LICENSE`.
Source data retain their respective upstream terms and attribution.

## JSON API examples

`data/json/source_examples.jsonl` contains complete API responses from USGS,
NVD, NIH RePORTER, ClinicalTrials.gov, GBIF, Crossref, Contracts Finder, and
USAspending. Public API endpoints and document hashes appear in
`manifests/json_source_examples.json`. Source license, publisher, institution,
identifier, and attribution fields are retained in each input. GBIF occurrence
records retain their individual `license`, `datasetKey`, and publisher fields,
including CC0, CC BY, and CC BY-NC declarations where present.

## JSON regression fixtures

The 25 fixtures in `data/json/regression_fixtures.jsonl` derive from
ComplexFuncBench, whose dataset card declares Apache License 2.0. Review and
business-reference fields use the substitutions documented in `PRIVACY.md`.
The extraction manifest records source and packaged hashes.

## HTML examples

The nine HTML examples derive from WebSRC v1.0 (`X-LANCE/WebSRC_v1.0`), which
uses CC BY 4.0. Attribution: Chen et al., *WebSRC: A Dataset for Web-Based
Structural Reading Comprehension*, EMNLP 2021. Source identifiers are retained;
packaging labels are normalized. The notice is in
`third_party_licenses/WebSRC-NOTICE.txt`.
License: https://creativecommons.org/licenses/by/4.0/legalcode.

## YAML source examples

The Swagger2OpenAPI Converter and Mtaa API documents originate from APIs.guru.
Both snapshot documents declare MIT in `info.license`. The converter repository
provides BSD-3-Clause and the Mtaa repository provides MIT. The manifest records
both snapshot declarations and repository license evidence. Included notices:

- `third_party_licenses/Mermade-openapi-webconverter-LICENSE.txt`
- `third_party_licenses/Mtaa-API-LICENSE.txt`

Documents retain source bytes and attribution; each question context contains
its complete supporting document.

## JavaScript examples

The nine JavaScript examples derive from ESLint, webpack, three.js, Plotly.js,
Babel, and Lodash under MIT licenses. Source identifiers, questions, and answers
are retained; packaging markers and binding prefixes are normalized. Verified
notices and the source manifest are included under `third_party_licenses/`.
