"""CPU checks over packaged records for all four executable formats."""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
from treeagent.sectioning import build_sections, TokenCounter, parse_json_text
from treeagent.tokenizers import CharacterTokenizer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tokenizer', help='Existing local tokenizer directory; requires Transformers')
    parser.add_argument('--all-records', action='store_true')
    parser.add_argument('--section-size', type=int, default=512)
    args = parser.parse_args()
    if args.tokenizer:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True,
                                                  trust_remote_code=False)
    else:
        tokenizer = CharacterTokenizer()
    counter = TokenCounter(tokenizer)
    summary = {'tokenizer_class': type(tokenizer).__name__, 'model_inference': False, 'formats': {}}
    for family, fmt in [('json', 'json'), ('html', 'html'),
                        ('yaml', 'yaml'), ('javascript', 'javascript')]:
        rows = [json.loads(line) for p in sorted((ROOT / 'data' / family).glob('*.jsonl'))
                for line in p.read_text().splitlines() if line.strip()]
        if not args.all_records:
            rows = rows[:1]
        total_sections = total_links = overflows = fitting_subtrees = wrapper_tokens = 0
        for row in rows:
            context = row['context'] if 'context' in row else row['input']
            value = parse_json_text(context) if fmt == 'json' and isinstance(context, str) else context
            sections = build_sections(value, tokenizer, args.section_size, 'treeagent', context_format=fmt)
            assert sections, (fmt, row['uid'])
            if fmt != 'json':
                assert ''.join(s.text for s in sections) == context
                from treeagent.native_tree import parse_native_tree
                from treeagent.native_source import walk
                raw = context.encode('utf-8')
                ends = [s.source_byte_end for s in sections]
                for node in walk(parse_native_tree(context, fmt)):
                    if node.start < node.end and counter.count(raw[node.start:node.end].decode()) <= sections[0].selected_tree_budget:
                        assert bisect_right(ends, node.start) == bisect_left(ends, node.end), (fmt, node.path)
                        fitting_subtrees += 1
            for section in sections:
                content = section.content_text if section.content_text is not None else section.text
                assert section.content_tokens == counter.count(content)
                if fmt != 'json' or section.section_type == 'text_span':
                    assert section.wrapper_prefix + content + section.wrapper_suffix == section.text
                    assert section.wrapper_tokens == counter.count(section.wrapper_prefix) + counter.count(section.wrapper_suffix)
                    assert section.total_tokens == counter.count(section.text) + counter.count(section.path_text)
                assert section.content_tokens <= section.selected_tree_budget or section.atomic_overflow
                assert all(i < section.step_id for i in section.residual_source_indices)
                assert len(set(section.residual_source_indices)) == len(section.residual_source_indices)
                total_links += len(section.residual_source_indices)
                overflows += int(section.atomic_overflow)
                wrapper_tokens += section.wrapper_tokens
            total_sections += len(sections)
        summary['formats'][fmt] = {'records': len(rows), 'sections': total_sections,
                                   'residual_links': total_links, 'atomic_overflow_sections': overflows,
                                   'fitting_original_subtrees_checked': fitting_subtrees,
                                   'wrapper_tokens': wrapper_tokens}
    from data_construction.validate_subset import validate_json_source_examples
    summary['source_input_checks'] = validate_json_source_examples(ROOT)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
