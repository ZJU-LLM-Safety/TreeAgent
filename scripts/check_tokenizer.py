"""Optional local-only tokenizer smoke check; requires Transformers."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
from treeagent.sectioning import build_sections


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tokenizer', required=True, help='Existing local tokenizer directory')
    args = parser.parse_args()
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True,
                                              trust_remote_code=False)
    text = ('Quoted "text", Unicode 中文😀, newline\n and slash\\. ' * 800)
    sections = build_sections({'text': text}, tokenizer, 128, 'treeagent')
    assert ''.join(json.loads(s.content_text) for s in sections) == text
    for s in sections:
        count = len(tokenizer.encode(s.content_text, add_special_tokens=False))
        assert count == s.content_tokens
        assert count <= s.selected_tree_budget or s.atomic_overflow
        assert all(i < s.step_id for i in s.residual_source_indices)
    row = json.loads((ROOT / 'data/json/regression_fixtures.jsonl').read_text().splitlines()[0])
    context = row['context']
    value = json.loads(context) if isinstance(context, str) else context
    data_sections = build_sections(value, tokenizer, 128, 'treeagent')
    assert data_sections
    for s in data_sections:
        content = s.content_text if s.content_text is not None else s.text
        assert s.content_tokens == len(tokenizer.encode(content, add_special_tokens=False))
        assert s.content_tokens <= s.selected_tree_budget or s.atomic_overflow
        assert all(i < s.step_id for i in s.residual_source_indices)
    print(json.dumps({'tokenizer_class': type(tokenizer).__name__,
                      'long_string_sections': len(sections),
                      'representative_json_sections': len(data_sections),
                      'model_inference': False}, indent=2))


if __name__ == '__main__':
    main()
