#!/usr/bin/env bash
set -euo pipefail

package_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${package_root}"
export PYTHONDONTWRITEBYTECODE=1
check_tmp="$(mktemp -d)"
trap 'rm -rf "${check_tmp}"' EXIT

PYTHONPATH=code python3 -m unittest discover -s tests -v
PYTHONPATH=code python3 -m data_construction.validate_subset
PYTHONPATH=code python3 -m data_construction.review_examples --check
PYTHONPATH=code python3 -m treeagent.cli \
  --input examples/toy_document.json \
  --output "${check_tmp}/toy_sections.json" \
  --section-size 72 \
  --max-tree-budget 143
PYTHONPATH=code python3 -m evaluation.replay \
  --input examples/toy_predictions.jsonl \
  --output "${check_tmp}/toy_score_summary.json"

cmp expected_outputs/toy_score_summary.json \
  "${check_tmp}/toy_score_summary.json"
cmp expected_outputs/toy_sections.json \
  "${check_tmp}/toy_sections.json"
for format in html yaml javascript; do
  extension="${format}"
  if [[ "${format}" == javascript ]]; then extension=js; fi
  PYTHONPATH=code python3 -m treeagent.cli \
    --format "${format}" \
    --input "examples/toy_document.${extension}" \
    --output "${check_tmp}/toy_sections_${format}.json" \
    --section-size 32
  cmp "expected_outputs/toy_sections_${format}.json" \
    "${check_tmp}/toy_sections_${format}.json"
done
echo "Four-format deterministic package checks passed."
