# Packaged examples

These are the complete packaged examples, including source examples and regression fixtures. Each entry separates mandatory instructions from the question and links to the complete input. [Reference answers](ANSWERS.md) are kept separate.

Send only `instructions`, `input`, and `question` to a model. Other public fields identify the sample and evaluation contract. For memory agents, feed the input through the host's sectioning loop while retaining the instructions and question. `prompt.txt` contains the complete task input; the host supplies its memory/control prompts.

String inputs retain their bytes. JSON object fixtures are serialized compactly from their packaged representation.

API examples keep their typed JSON-array protocol. Other collections retain their declared scalar/list metrics; the JavaScript tiny-number example uses `exact_number_match`. See [scoring contracts](../../code/evaluation/README.md).

Sample UIDs identify source examples. A changed question or scoring contract carries `sample_revision`; pin package hashes as well as UIDs when comparing results.

## JSON API examples

A03 requests the GUIDs of four vulnerability records.

### A01 — record_field_lookup

UID: `cq_json_6d5463fc7298de065baec223_16000` · Revision: `source_preserved`

[Source row](../../data/json/source_examples.jsonl#L1) · [Complete input](A01/prompt.txt) · [Public fields](A01/public_input.json) · [Answer](ANSWERS.md#a01)

**Instructions**

```text
Answer using only the supplied data. Return only a JSON array, with one element per requested answer, in the order asked. Include no explanation.

Use all supplied responses. Match strings and identifiers exactly, preserving JSON types and exact numeric values. Missing and null differ: null is present. Do not fill missing values or convert types.

For record lookups, consider only records containing all requested fields.
```

**Question**

What is the first listed work title of the Crossref work with DOI "10.1017/cbo9781139028004.004"?

### A02 — multi_record_field_2

UID: `cq_json_432c48f34335e51285de75c9_16000` · Revision: `source_preserved`

[Source row](../../data/json/source_examples.jsonl#L2) · [Complete input](A02/prompt.txt) · [Public fields](A02/public_input.json) · [Answer](ANSWERS.md#a02)

**Instructions**

```text
Answer using only the supplied data. Return only a JSON array, with one element per requested answer, in the order asked. Include no explanation.

Use all supplied responses. Match strings and identifiers exactly, preserving JSON types and exact numeric values. Missing and null differ: null is present. Do not fill missing values or convert types.

For record lookups, consider only records containing all requested fields.
```

**Question**

For the USGS earthquake events with event IDs "nn00663734" and "ak018e0exqrw", what is the reported location description of each, respectively?

### A03 — multi_record_field_4

UID: `cq_json_1c697d98180582af13549cdd_16000` · Revision: `source_preserved`

[Source row](../../data/json/source_examples.jsonl#L3) · [Complete input](A03/prompt.txt) · [Public fields](A03/public_input.json) · [Answer](ANSWERS.md#a03)

**Instructions**

```text
Answer using only the supplied data. Return only a JSON array, with one element per requested answer, in the order asked. Include no explanation.

Use all supplied responses. Match strings and identifiers exactly, preserving JSON types and exact numeric values. Missing and null differ: null is present. Do not fill missing values or convert types.

For record lookups, consider only records containing all requested fields.
```

**Question**

For the NVD vulnerability records with CVE IDs "CVE-2024-27035", "CVE-2024-27036", "CVE-2024-27037", and "CVE-2024-27038", what is the vulnerability reporting source identifier of each, respectively?

### A04 — record_multi_field_2

UID: `cq_json_e9027cda637cf25c050b8d5f_16000` · Revision: `source_preserved`

[Source row](../../data/json/source_examples.jsonl#L4) · [Complete input](A04/prompt.txt) · [Public fields](A04/public_input.json) · [Answer](ANSWERS.md#a04)

**Instructions**

```text
Answer using only the supplied data. Return only a JSON array, with one element per requested answer, in the order asked. Include no explanation.

Use all supplied responses. Match strings and identifiers exactly, preserving JSON types and exact numeric values. Missing and null differ: null is present. Do not fill missing values or convert types.

For record lookups, consider only records containing all requested fields.
```

**Question**

What are the brief study title and overall recruitment status of the ClinicalTrials.gov study with NCT ID "NCT00001526"?

### A05 — record_multi_field_4

UID: `cq_json_c3d48dabbf5cca1bc3c62316_16000` · Revision: `source_preserved`

[Source row](../../data/json/source_examples.jsonl#L5) · [Complete input](A05/prompt.txt) · [Public fields](A05/public_input.json) · [Answer](ANSWERS.md#a05)

**Instructions**

```text
Answer using only the supplied data. Return only a JSON array, with one element per requested answer, in the order asked. Include no explanation.

Use all supplied responses. Match strings and identifiers exactly, preserving JSON types and exact numeric values. Missing and null differ: null is present. Do not fill missing values or convert types.

For record lookups, consider only records containing all requested fields.
```

**Question**

What are the project title, recipient organization name, recipient organization state, and contact principal-investigator name of the NIH RePORTER project with numeric application ID 10540803?

### A06 — conditional_count

UID: `cq_json_3d9e26a01404926360b45930_16000` · Revision: `source_preserved`

[Source row](../../data/json/source_examples.jsonl#L6) · [Complete input](A06/prompt.txt) · [Public fields](A06/public_input.json) · [Answer](ANSWERS.md#a06)

**Instructions**

```text
Answer using only the supplied data. Return only a JSON array, with one element per requested answer, in the order asked. Include no explanation.

Use all supplied responses. Match strings and identifiers exactly, preserving JSON types and exact numeric values. Missing and null differ: null is present. Do not fill missing values or convert types.
```

**Question**

How many GBIF occurrence records have phylum name equal to "Chordata"?

Count repeated record or entry occurrences separately.

### A07 — groupby_topk_values

UID: `cq_json_bfd7593136832cf7355fe1fe_16000` · Revision: `source_preserved`

[Source row](../../data/json/source_examples.jsonl#L7) · [Complete input](A07/prompt.txt) · [Public fields](A07/public_input.json) · [Answer](ANSWERS.md#a07)

**Instructions**

```text
Answer using only the supplied data. Return only a JSON array, with one element per requested answer, in the order asked. Include no explanation.

Use all supplied responses. Match strings and identifiers exactly, preserving JSON types and exact numeric values. Missing and null differ: null is present. Do not fill missing values or convert types.
```

**Question**

Which three procurement-method details values occur most frequently across all Contracts Finder release records?

Count each record or entry occurrence separately, including repetitions within the same parent.

Return the values in decreasing frequency order; values tied within the top three may exchange their tied positions.

Consider only entries where procurement-method details is present and procurement-method details does not equal null.

### A08 — numeric_extreme

UID: `cq_json_a0cbcc0e6635c83c8fd873dc_16000` · Revision: `source_preserved`

[Source row](../../data/json/source_examples.jsonl#L8) · [Complete input](A08/prompt.txt) · [Public fields](A08/public_input.json) · [Answer](ANSWERS.md#a08)

**Instructions**

```text
Answer using only the supplied data. Return only a JSON array, with one element per requested answer, in the order asked. Include no explanation.

Use all supplied responses. Match strings and identifiers exactly, preserving JSON types and exact numeric values. Missing and null differ: null is present. Do not fill missing values or convert types.

Finite JSON numbers exclude numeric strings, booleans and null. Do not convert units.
```

**Question**

What is the maximum reported award obligation amount in USD among all USAspending contract award records?

Consider only entries where reported award obligation amount in USD is a finite JSON number.

## HTML examples

### H01 — record_field_lookup

UID: `html_websrc_v4_test_8k_record_field_lookup_00000` · Revision: `source_preserved`

[Source row](../../data/html/representative.jsonl#L1) · [Complete input](H01/prompt.txt) · [Public fields](H01/public_input.json) · [Answer](ANSWERS.md#h01)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

On auto site 02 page 0200054, for the column where Engine Type is Twin Turbo Premium Unleaded V-8, what is the Horsepower @ RPM?

### H02 — multi_record_field_2

UID: `html_websrc_v4_test_8k_multi_record_field_2_00000` · Revision: `source_preserved`

[Source row](../../data/html/representative.jsonl#L2) · [Complete input](H02/prompt.txt) · [Public fields](H02/public_input.json) · [Answer](ANSWERS.md#h02)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

Return the FTM for these distinct HTML records. Give one value per line in Q1-to-Q2 order, without Q labels or explanations. Q1: the row where Season is CAREER on sports site 16 page 1600063 Q2: the row where Season is 2015-16 on sports site 16 page 1600074

### H03 — multi_record_field_4

UID: `html_websrc_v4_test_8k_multi_record_field_4_00000` · Revision: `source_preserved`

[Source row](../../data/html/representative.jsonl#L3) · [Complete input](H03/prompt.txt) · [Public fields](H03/public_input.json) · [Answer](ANSWERS.md#h03)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

Return the Runtime for these distinct HTML records. Give one value per line in Q1-to-Q4 order, without Q labels or explanations. Q1: the movie where Title is Won't You Be My Neighbor? on movie site 08 page 0800015 Q2: the movie where Title is Avengers: Infinity War on movie site 08 page 0800042 Q3: the movie where Title is Tokyo Story on movie site 08 page 0800045 Q4: the movie where Title is Love, Simon on movie site 08 page 0800068

### H04 — record_multi_field_2

UID: `html_websrc_v4_test_8k_record_multi_field_2_00000` · Revision: `source_preserved`

[Source row](../../data/html/representative.jsonl#L4) · [Complete input](H04/prompt.txt) · [Public fields](H04/public_input.json) · [Answer](ANSWERS.md#h04)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For the movie where Title is Reservoir Dogs on movie site 08 page 0800067, return these 2 distinct fields. Give one value per line in F1-to-F2 order, without field names or explanations. F1: Certification F2: Release date

### H05 — record_multi_field_4

UID: `html_websrc_v4_test_8k_record_multi_field_4_00001` · Revision: `source_preserved`

[Source row](../../data/html/representative.jsonl#L5) · [Complete input](H05/prompt.txt) · [Public fields](H05/public_input.json) · [Answer](ANSWERS.md#h05)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For the row where Season is CAREER on sports site 16 page 1600081, return these 4 distinct fields. Give one value per line in F1-to-F4 order, without field names or explanations. F1: 3P% F2: FT% F3: 3PA F4: 3PM

### H06 — conditional_count

UID: `html_websrc_v4_test_8k_conditional_count_00002` · Revision: `sample_contract_v2`

[Source row](../../data/html/representative.jsonl#L6) · [Complete input](H06/prompt.txt) · [Public fields](H06/public_input.json) · [Answer](ANSWERS.md#h06)

**Instructions**

```text
Answer using only the supplied data.

only the integer count
```

**Question**

Across the movie records in the supplied HTML documents, how many have a displayed Release year equal to "(2019)"? Count each movie record separately.

### H07 — groupby_topk_values

UID: `html_websrc_v4_test_8k_groupby_topk_values_00000` · Revision: `sample_contract_v2`

[Source row](../../data/html/representative.jsonl#L7) · [Complete input](H07/prompt.txt) · [Public fields](H07/public_input.json) · [Answer](ANSWERS.md#h07)

**Instructions**

```text
Answer using only the supplied data.

one value per line; do not include counts or explanations
```

**Question**

Across the vehicle columns in the supplied HTML comparison tables, which three distinct Destination values occur most frequently? Count each vehicle column separately.

### H08 — numeric_extreme

UID: `html_websrc_v4_test_8k_numeric_extreme_00000` · Revision: `sample_contract_v2`

[Source row](../../data/html/representative.jsonl#L8) · [Complete input](H08/prompt.txt) · [Public fields](H08/public_input.json) · [Answer](ANSWERS.md#h08)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

Across the vehicle columns in the supplied HTML comparison tables, what is the smallest numeric amount shown in the Destination field?

### H09 — record_field_lookup

UID: `html_websrc_v4_test_128k_record_field_lookup_00027` · Revision: `source_preserved`

[Source row](../../data/html/representative.jsonl#L9) · [Complete input](H09/prompt.txt) · [Public fields](H09/public_input.json) · [Answer](ANSWERS.md#h09)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

On auto site 02 page 0200064, for the column where Horsepower @ RPM is 248 @ 5200, what is the MSRP?

## JavaScript examples

### J01 — record_field_lookup

UID: `jss_fa44adc4e1adbd232869` · Revision: `source_preserved`

[Source row](../../data/javascript/representative.jsonl#L1) · [Complete input](J01/prompt.txt) · [Public fields](J01/public_input.json) · [Answer](ANSWERS.md#j01)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

In state jssstate_ee0b8c64c6e9308329c3 (source state label "mx_hash_int_1"), record whose name is "mx_hash_int_1", return its type property value. Answer with only the value.

### J02 — multi_record_field_2

UID: `jss_aa4f3c5ac4b49e2ca5ce` · Revision: `source_preserved`

[Source row](../../data/javascript/representative.jsonl#L2) · [Complete input](J02/prompt.txt) · [Public fields](J02/public_input.json) · [Answer](ANSWERS.md#j02)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the order requested
```

**Question**

Return the fixable property value for these JSS records in the listed order: (1) state jssstate_1a9da3bda5f1333a2047 (source state label "module.exports.meta"), record whose type is "suggestion"; (2) state jssstate_39c28b46a9133fde7bf7 (source state label "module.exports.meta"), record whose type is "layout". Answer with one value per line and no labels.

### J03 — multi_record_field_4

UID: `jss_1e1d3c48f4d5636a8edf` · Revision: `source_preserved`

[Source row](../../data/javascript/representative.jsonl#L3) · [Complete input](J03/prompt.txt) · [Public fields](J03/public_input.json) · [Answer](ANSWERS.md#j03)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the order requested
```

**Question**

Return the option property value for these JSS records in the listed order: (1) state jssstate_b960f8646f65e74b5e6d (source state label "optionator.options"), record whose type is "path::String"; (2) state jssstate_697a29324e3df33644b3 (source state label "optionator.options"), record whose type is "Boolean"; (3) state jssstate_bdb059208486bd101c72 (source state label "optionator.options"), record whose type is "Int|String"; (4) state jssstate_fd14003beaa211b5a478 (source state label "optionator.options"), record whose type is "Object". Answer with one value per line and no labels.

### J04 — record_multi_field_2

UID: `jss_35092b94d900020aa50b` · Revision: `source_preserved`

[Source row](../../data/javascript/representative.jsonl#L4) · [Complete input](J04/prompt.txt) · [Public fields](J04/public_input.json) · [Answer](ANSWERS.md#j04)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the order requested
```

**Question**

In state jssstate_bea74732900eeedf0619 (source state label "module.exports.meta"), object at property path module.exports.meta.messages, return these property values in the listed order: rejectedClosingSpace, missingOpeningSpace. Answer with one value per line and no labels.

### J05 — record_multi_field_4

UID: `jss_2ef34e0ac4184373d863` · Revision: `source_preserved`

[Source row](../../data/javascript/representative.jsonl#L5) · [Complete input](J05/prompt.txt) · [Public fields](J05/public_input.json) · [Answer](ANSWERS.md#j05)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the order requested
```

**Question**

In state jssstate_c14523dc6ddedddea935 (source state label "extendFlat.lightposition"), object at property path extendFlat.lightposition.y, return these property values in the listed order: max, valType, min, dflt. Answer with one value per line and no labels.

### J06 — conditional_count

UID: `jss_7bdf57b8f3fc05bb6bb6` · Revision: `source_preserved`

[Source row](../../data/javascript/representative.jsonl#L6) · [Complete input](J06/prompt.txt) · [Public fields](J06/public_input.json) · [Answer](ANSWERS.md#j06)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

Within collection module.exports.meta.schema.items.properties in state jssstate_da03b1f43d0a7af9b314, how many records have type equal to "string"? Answer with only the count.

### J07 — groupby_topk_values

UID: `jss_fc74a47982cbb428c5a3` · Revision: `source_preserved`

[Source row](../../data/javascript/representative.jsonl#L7) · [Complete input](J07/prompt.txt) · [Public fields](J07/public_input.json) · [Answer](ANSWERS.md#j07)

**Instructions**

```text
Answer using only the supplied data.

one value per line, without counts
```

**Question**

Across these explicitly named JSS collections, considering all entries together, return the three most frequent type values: OPTIONS_SCHEMA.properties in state jssstate_f0acc522d1ff0c66e939; mx_worley_noise_vec3_style_0.inputs in state jssstate_5d2ad22fc2f12c6c5758. Answer with one value per line and no counts.

### J08 — numeric_extreme

UID: `jss_2aac94a0d72f00388c30` · Revision: `sample_contract_v2`

[Source row](../../data/javascript/representative.jsonl#L8) · [Complete input](J08/prompt.txt) · [Public fields](J08/public_input.json) · [Answer](ANSWERS.md#j08)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

Among the dflt property values of these JSS records, return the minimum: (1) state jssstate_c14523dc6ddedddea935 (source state label "extendFlat.lightposition"), object at property path extendFlat.lightposition.x; (2) state jssstate_56d39f8051f9040af94b (source state label "module.exports.line"), object at property path module.exports.line.width; (3) state jssstate_b7ad8de247378a444430 (source state label "extendFlat"), object at property path extendFlat.vertexnormalsepsilon; (4) state jssstate_7cbc982746b4b2608829 (source state label "module.exports.line"), object at property path module.exports.line.width. Answer with only the value.

### J09 — record_field_lookup

UID: `jss_9687b71ee7b2ba696316` · Revision: `source_preserved`

[Source row](../../data/javascript/representative.jsonl#L9) · [Complete input](J09/prompt.txt) · [Public fields](J09/public_input.json) · [Answer](ANSWERS.md#j09)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

In state jssstate_ee0b8c64c6e9308329c3 (source state label "mx_hash_int_1"), record whose name is "mx_hash_int_1", return its type property value. Answer with only the value.

## YAML source examples

### Y01 — record_field_lookup

UID: `yaml_real_source_openapi-converter` · Revision: `source_preserved`

[Source row](../../data/yaml/real_examples.jsonl#L1) · [Complete input](Y01/prompt.txt) · [Public fields](Y01/public_input.json) · [Answer](ANSWERS.md#y01)

**Instructions**

```text
Answer using only the supplied data.

Return only the requested value, without explanations.
```

**Question**

For GET /badge in Swagger2OpenAPI Converter, what is the response 301 description?

### Y02 — record_field_lookup

UID: `yaml_real_source_mtaa` · Revision: `source_preserved`

[Source row](../../data/yaml/real_examples.jsonl#L2) · [Complete input](Y02/prompt.txt) · [Public fields](Y02/public_input.json) · [Answer](ANSWERS.md#y02)

**Instructions**

```text
Answer using only the supplied data.

Return only the requested value, without explanations.
```

**Question**

For GET /{country} in Mtaa API Documentation, what is the operation ID?

## JSON regression fixtures

### R01 — record_field_lookup

UID: `json_subset_test_8k_record_field_lookup_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L1) · [Complete input](R01/prompt.txt) · [Public fields](R01/public_input.json) · [Answer](ANSWERS.md#r01)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

What is the free cancellation policy of product PRv2A2z8xpqy?

### R02 — multi_record_field_2

UID: `json_subset_test_8k_multi_record_field_2_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L2) · [Complete input](R02/prompt.txt) · [Public fields](R02/public_input.json) · [Answer](ANSWERS.md#r02)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For flight legs 8801 and 9492, return the departure airport code of each flight leg.

### R03 — multi_record_field_4

UID: `json_subset_test_8k_multi_record_field_4_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L3) · [Complete input](R03/prompt.txt) · [Public fields](R03/public_input.json) · [Answer](ANSWERS.md#r03)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For flight legs 327, 603, 1030, and 9099, return the flight leg duration of each flight leg.

### R04 — record_multi_field_2

UID: `json_subset_test_8k_record_multi_field_2_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L4) · [Complete input](R04/prompt.txt) · [Public fields](R04/public_input.json) · [Answer](ANSWERS.md#r04)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For hotel 1865491, return the search result position, ranking position.

### R05 — record_multi_field_4

UID: `json_subset_test_8k_record_multi_field_4_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L5) · [Complete input](R05/prompt.txt) · [Public fields](R05/public_input.json) · [Answer](ANSWERS.md#r05)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For room 59354301_371922173_3_2_0, return the child capacity, adult capacity, all-inclusive room price, gross room price.

### R06 — conditional_count

UID: `json_subset_test_8k_conditional_count_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L6) · [Complete input](R06/prompt.txt) · [Public fields](R06/public_input.json) · [Answer](ANSWERS.md#r06)

**Instructions**

```text
Answer using only the supplied data.

only the integer count
```

**Question**

How many flight legs have arrival country code CA?

### R07 — groupby_topk_values

UID: `json_subset_test_8k_groupby_topk_values_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L7) · [Complete input](R07/prompt.txt) · [Public fields](R07/public_input.json) · [Answer](ANSWERS.md#r07)

**Instructions**

```text
Answer using only the supplied data.

one value per line
```

**Question**

What are the 3 most common marketing carrier values among all flight legs?

### R08 — numeric_extreme

UID: `json_subset_test_8k_numeric_extreme_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L8) · [Complete input](R08/prompt.txt) · [Public fields](R08/public_input.json) · [Answer](ANSWERS.md#r08)

**Instructions**

```text
Answer using only the supplied data.

only the number
```

**Question**

What is the minimum review count among all hotels?

### R09 — record_field_lookup

UID: `json_subset_test_128k_record_field_lookup_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L9) · [Complete input](R09/prompt.txt) · [Public fields](R09/public_input.json) · [Answer](ANSWERS.md#r09)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

What is the search result position of hotel 10975?

### R10 — record_field_lookup

UID: `json_subset_train_32k_record_field_lookup_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L10) · [Complete input](R10/prompt.txt) · [Public fields](R10/public_input.json) · [Answer](ANSWERS.md#r10)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

What is the category of product PRn1YKbvZmdu?

### R11 — multi_record_field_2

UID: `json_subset_train_32k_multi_record_field_2_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L11) · [Complete input](R11/prompt.txt) · [Public fields](R11/public_input.json) · [Answer](ANSWERS.md#r11)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For flight legs 2208 and 7648, return the arrival city of each flight leg.

### R12 — multi_record_field_4

UID: `json_subset_train_32k_multi_record_field_4_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L12) · [Complete input](R12/prompt.txt) · [Public fields](R12/public_input.json) · [Answer](ANSWERS.md#r12)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For flight legs 258, 9612, 7648, and 5826, return the arrival city of each flight leg.

### R13 — record_multi_field_2

UID: `json_subset_train_32k_record_multi_field_2_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L13) · [Complete input](R13/prompt.txt) · [Public fields](R13/public_input.json) · [Answer](ANSWERS.md#r13)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For flight leg 662, return the departure country, arrival airport code.

### R14 — record_multi_field_4

UID: `json_subset_train_32k_record_multi_field_4_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L14) · [Complete input](R14/prompt.txt) · [Public fields](R14/public_input.json) · [Answer](ANSWERS.md#r14)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For product PRuYCCVyFX3d, return the free cancellation policy, rating total, public price, average rating.

### R15 — conditional_count

UID: `json_subset_train_32k_conditional_count_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L15) · [Complete input](R15/prompt.txt) · [Public fields](R15/public_input.json) · [Answer](ANSWERS.md#r15)

**Instructions**

```text
Answer using only the supplied data.

only the integer count
```

**Question**

How many flight legs have departure country code US?

### R16 — groupby_topk_values

UID: `json_subset_train_32k_groupby_topk_values_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L16) · [Complete input](R16/prompt.txt) · [Public fields](R16/public_input.json) · [Answer](ANSWERS.md#r16)

**Instructions**

```text
Answer using only the supplied data.

one value per line
```

**Question**

What are the 3 most common vehicle type values among all taxi options?

### R17 — numeric_extreme

UID: `json_subset_train_32k_numeric_extreme_000000` · Revision: `sample_contract_v2`

[Source row](../../data/json/regression_fixtures.jsonl#L17) · [Complete input](R17/prompt.txt) · [Public fields](R17/public_input.json) · [Answer](ANSWERS.md#r17)

**Instructions**

```text
Answer using only the supplied data.

only the number
```

**Question**

Across all supplied car-rental records, what is the lowest listed rental price in USD? Return only the numerical value; do not convert currencies.

### R18 — record_field_lookup

UID: `json_subset_dev_32k_record_field_lookup_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L18) · [Complete input](R18/prompt.txt) · [Public fields](R18/public_input.json) · [Answer](ANSWERS.md#r18)

**Instructions**

```text
Answer using only the supplied data.

only the value
```

**Question**

What is the departure country of flight leg 2118?

### R19 — multi_record_field_2

UID: `json_subset_dev_32k_multi_record_field_2_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L19) · [Complete input](R19/prompt.txt) · [Public fields](R19/public_input.json) · [Answer](ANSWERS.md#r19)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For taxi options 26898 and 19309, return the vehicle type of each taxi option.

### R20 — multi_record_field_4

UID: `json_subset_dev_32k_multi_record_field_4_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L20) · [Complete input](R20/prompt.txt) · [Public fields](R20/public_input.json) · [Answer](ANSWERS.md#r20)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For cars 453412138, 765089186, 765089336, and 691867331, return the condition rating of each car.

### R21 — record_multi_field_2

UID: `json_subset_dev_32k_record_multi_field_2_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L21) · [Complete input](R21/prompt.txt) · [Public fields](R21/public_input.json) · [Answer](ANSWERS.md#r21)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For flight leg 517, return the departure country code, departure city.

### R22 — record_multi_field_4

UID: `json_subset_dev_32k_record_multi_field_4_000000` · Revision: `sample_contract_v2`

[Source row](../../data/json/regression_fixtures.jsonl#L22) · [Complete input](R22/prompt.txt) · [Public fields](R22/public_input.json) · [Answer](ANSWERS.md#r22)

**Instructions**

```text
Answer using only the supplied data.

one value per line, in the same order as the IDs or fields in the question; do not include IDs, field names, or explanations
```

**Question**

For car 372903916, return its drive-away price in USD, cleanliness rating, listed rental price in USD, and base-currency deposit in INR, in that order. Give one value per line without labels or explanations; do not convert currencies.

### R23 — conditional_count

UID: `json_subset_dev_32k_conditional_count_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L23) · [Complete input](R23/prompt.txt) · [Public fields](R23/public_input.json) · [Answer](ANSWERS.md#r23)

**Instructions**

```text
Answer using only the supplied data.

only the integer count
```

**Question**

How many cars have value-for-money rating of at least 8.1?

### R24 — groupby_topk_values

UID: `json_subset_dev_32k_groupby_topk_values_000000` · Revision: `source_preserved`

[Source row](../../data/json/regression_fixtures.jsonl#L24) · [Complete input](R24/prompt.txt) · [Public fields](R24/public_input.json) · [Answer](ANSWERS.md#r24)

**Instructions**

```text
Answer using only the supplied data.

one value per line
```

**Question**

What are the 3 most common departure country values among all flight legs?

### R25 — numeric_extreme

UID: `json_subset_dev_32k_numeric_extreme_000000` · Revision: `sample_contract_v2`

[Source row](../../data/json/regression_fixtures.jsonl#L25) · [Complete input](R25/prompt.txt) · [Public fields](R25/public_input.json) · [Answer](ANSWERS.md#r25)

**Instructions**

```text
Answer using only the supplied data.

only the number
```

**Question**

Across all supplied car-rental records, what is the lowest listed rental price in USD? Return only the numerical value; do not convert currencies.

## Synthetic YAML fixtures

Generated OpenAPI fixtures for task and structure checks. S09 repeats S01's lookup for structural inspection.

### S01 — record_field_lookup

UID: `yaml_synthetic_fixture_00_record_field_lookup` · Revision: `sample_contract_v2`

[Source row](../../data/yaml/synthetic_fixtures.jsonl#L1) · [Complete input](S01/prompt.txt) · [Public fields](S01/public_input.json) · [Answer](ANSWERS.md#s01)

**Instructions**

```text
Answer using only the supplied data.

Return only the value.
```

**Question**

For the limit parameter in Synthetic Alpha Inventory API, what is the required flag?

### S02 — multi_record_field_2

UID: `yaml_synthetic_fixture_01_multi_record_field_2` · Revision: `sample_contract_v2`

[Source row](../../data/yaml/synthetic_fixtures.jsonl#L2) · [Complete input](S02/prompt.txt) · [Public fields](S02/public_input.json) · [Answer](ANSWERS.md#s02)

**Instructions**

```text
Answer using only the supplied data.

Give one value per line, in the order requested, without labels or explanations.
```

**Question**

Return the schema maximum for the limit parameter in Synthetic Alpha Inventory API and Synthetic Bravo Inventory API, in that order.

### S03 — multi_record_field_4

UID: `yaml_synthetic_fixture_02_multi_record_field_4` · Revision: `sample_contract_v2`

[Source row](../../data/yaml/synthetic_fixtures.jsonl#L3) · [Complete input](S03/prompt.txt) · [Public fields](S03/public_input.json) · [Answer](ANSWERS.md#s03)

**Instructions**

```text
Answer using only the supplied data.

Give one value per line, in the order requested, without labels or explanations.
```

**Question**

Return the schema maximum for the limit parameter in the Alpha, Bravo, Charlie, and Delta inventory APIs, in that order.

### S04 — record_multi_field_2

UID: `yaml_synthetic_fixture_03_record_multi_field_2` · Revision: `sample_contract_v2`

[Source row](../../data/yaml/synthetic_fixtures.jsonl#L4) · [Complete input](S04/prompt.txt) · [Public fields](S04/public_input.json) · [Answer](ANSWERS.md#s04)

**Instructions**

```text
Answer using only the supplied data.

Give one value per line, in the order requested, without labels or explanations.
```

**Question**

For the limit parameter in Synthetic Alpha Inventory API, return its location and schema format.

### S05 — record_multi_field_4

UID: `yaml_synthetic_fixture_04_record_multi_field_4` · Revision: `sample_contract_v2`

[Source row](../../data/yaml/synthetic_fixtures.jsonl#L5) · [Complete input](S05/prompt.txt) · [Public fields](S05/public_input.json) · [Answer](ANSWERS.md#s05)

**Instructions**

```text
Answer using only the supplied data.

Give one value per line, in the order requested, without labels or explanations.
```

**Question**

For the limit parameter in Synthetic Alpha Inventory API, return description, format, required, and type.

### S06 — conditional_count

UID: `yaml_synthetic_fixture_05_conditional_count` · Revision: `sample_contract_v2`

[Source row](../../data/yaml/synthetic_fixtures.jsonl#L6) · [Complete input](S06/prompt.txt) · [Public fields](S06/public_input.json) · [Answer](ANSWERS.md#s06)

**Instructions**

```text
Answer using only the supplied data.

Return only the numerical value.
```

**Question**

How many parameter records have schema format int32?

### S07 — groupby_topk_values

UID: `yaml_synthetic_fixture_06_groupby_topk_values` · Revision: `sample_contract_v2`

[Source row](../../data/yaml/synthetic_fixtures.jsonl#L7) · [Complete input](S07/prompt.txt) · [Public fields](S07/public_input.json) · [Answer](ANSWERS.md#s07)

**Instructions**

```text
Answer using only the supplied data.

Return one value per line without counts or explanations.
```

**Question**

Which three parameter locations occur most often?

### S08 — numeric_extreme

UID: `yaml_synthetic_fixture_07_numeric_extreme` · Revision: `sample_contract_v2`

[Source row](../../data/yaml/synthetic_fixtures.jsonl#L8) · [Complete input](S08/prompt.txt) · [Public fields](S08/public_input.json) · [Answer](ANSWERS.md#s08)

**Instructions**

```text
Answer using only the supplied data.

Return only the numerical value.
```

**Question**

Among parameters named limit, what is the largest schema maximum?

### S09 — record_field_lookup

UID: `yaml_synthetic_fixture_08_structure` · Revision: `sample_contract_v2`

[Source row](../../data/yaml/synthetic_fixtures.jsonl#L9) · [Complete input](S09/prompt.txt) · [Public fields](S09/public_input.json) · [Answer](ANSWERS.md#s09)

**Instructions**

```text
Answer using only the supplied data.

Return only the value.
```

**Question**

For the limit parameter in Synthetic Alpha Inventory API, what is the required flag?

