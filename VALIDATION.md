# Validation

Run the complete CPU check suite:

```bash
bash run_checks.sh
python3 scripts/check_formats.py --all-records
python3 scripts/check_artifact.py
```

The unit suite covers:

- Four-format parsing, fitting-subtree preservation, inclusive sibling ranges,
  source coverage, and content/wrapper token accounting.
- The shared four-format budget search, including all evaluated candidates,
  nonmonotone counts and deterministic ties from the main paper.
- Complete multi-document JSON input, virtual-root grouping, cross-document
  memory links, fragment wrappers and backward-compatible single-document plans.
- JSON fragment reconstruction, enclosing syntax, natural boundaries, Unicode
  and escape handling, and atomic overflow.
- Parent-child final-section links, root targets, coincident targets, source
  deduplication, and saving memory after every update. Independent tree/source
  endpoint checks verify the residual graph.
- Full-span ranking followed by selection and clipping; shared InfMem raw-text
  chunks, overlap, window boundaries, and raw coordinates.
- Valid scalar answers, signed values, numerical tolerance in ordered and unordered
  lists, maximum one-to-one matching, invalid-answer rejection and offline replay.
- Sample manifests, source hashes, YAML answer paths, and privacy transformations.
- Exact decimal matching for the tiny-number sample, rejecting incorrect near-zero
  answers while accepting equivalent scientific notation.
- All review exports regenerated in memory and compared byte-for-byte; public-input
  allowlists and mandatory output instructions are checked independently of gold.

`run_checks.sh` also compares the four CLI plans and offline score summary with
`expected_outputs/`. The all-record check builds plans for all 62 records,
including eight API examples containing nine complete source documents.
The source-example validator checks complete input hashes, each document's bytes,
answer slot counts, and coverage of eight tasks and seven source groups.

The default planning checks use `CharacterTokenizer`. To run with a local model
tokenizer:

```bash
python3 scripts/check_formats.py --all-records --tokenizer /path/to/local/tokenizer
```

`check_artifact.py` checks file inventories, SHA-256 hashes, configured private-path
and credential patterns, supplied identifying terms, privacy transformations,
and source examples. `build_archive.py` runs these checks and writes the ZIP.
