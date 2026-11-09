"""Four-format checks with independently specified hierarchy and byte invariants."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from treeagent.native_tree import parse_native_tree
from treeagent.native_source import walk, source_sections_for_budget
from treeagent.runtime import run_memory_agent
from treeagent.sectioning import build_sections
from treeagent.tokenizers import CharacterTokenizer

ROOT = Path(__file__).resolve().parents[1]
TOKENIZER = CharacterTokenizer()
SAMPLES = {
    'html': '<main><section><b>1111</b><i>2222</i></section><section><b>3333</b><i>4444</i></section></main>',
    'yaml': 'a:\n  x: 1111\n  y: 2222\nb:\n  x: 3333\n  y: 4444\n',
    'javascript': 'const a={x:1111,y:2222}; const b={x:3333,y:4444};',
}
BUDGETS = {'html': 15, 'yaml': 14, 'javascript': 8}


def plan(text, fmt, budget, maximum=None):
    return build_sections(text, TOKENIZER, budget, 'treeagent', context_format=fmt,
                          max_tree_budget=budget if maximum is None else maximum)


class NativeFormatTest(unittest.TestCase):
    def assert_source_contract(self, text, sections, budget):
        self.assertEqual(''.join(s.text for s in sections), text)
        self.assertEqual(''.join(s.raw_text for s in sections), text)
        raw = text.encode('utf-8')
        cursor = 0
        for s in sections:
            self.assertEqual(s.source_byte_start, cursor)
            self.assertEqual(raw[s.source_byte_start:s.source_byte_end].decode(), s.text)
            self.assertEqual(raw[s.content_byte_start:s.content_byte_end].decode(), s.content_text)
            self.assertEqual(s.wrapper_prefix + s.content_text + s.wrapper_suffix, s.text)
            self.assertEqual(s.content_tokens, len(s.content_text))
            self.assertEqual(s.total_tokens, len(s.text) + len(s.path_text))
            self.assertEqual(s.wrapper_tokens, len(s.wrapper_prefix) + len(s.wrapper_suffix))
            self.assertTrue(s.content_tokens <= budget or s.atomic_overflow)
            self.assertEqual(s.atomic_overflow, s.content_tokens > budget)
            self.assertTrue(all(i < s.step_id for i in s.residual_source_indices))
            cursor = s.source_byte_end
        self.assertEqual(cursor, len(raw))

    def test_native_sources_preserve_every_byte_and_separate_wrapper_counts(self):
        for fmt, text in SAMPLES.items():
            for budget in (8, BUDGETS[fmt], 200):
                with self.subTest(fmt=fmt, budget=budget):
                    self.assert_source_contract(text, plan(text, fmt, budget), budget)

    def test_all_formats_union_nested_and_root_final_segment_links(self):
        for fmt, text in SAMPLES.items():
            with self.subTest(fmt=fmt):
                sections = plan(text, fmt, BUDGETS[fmt])
                self.assertEqual(len(sections), 4)
                self.assertEqual([s.residual_source_indices for s in sections], [[], [1], [], [2, 3]])
                # The last segment ends at least two parent levels plus its own node.
                self.assertGreaterEqual(len(sections[-1].closing_paths), 3)

    def test_fitting_native_subtrees_are_never_partitioned(self):
        for fmt, text in SAMPLES.items():
            budget = BUDGETS[fmt]
            original = parse_native_tree(text, fmt)
            sections = plan(text, fmt, budget)
            for node in walk(original):
                if len(text.encode()[node.start:node.end].decode()) <= budget:
                    containing = [s for s in sections
                                  if s.source_byte_start <= node.start and s.source_byte_end >= node.end]
                    self.assertEqual(len(containing), 1, (fmt, node.path))

    def test_group_paths_use_inclusive_positions_of_actual_children(self):
        examples = {'html': ('<p>A</p><p>B</p><p>C</p>', 16),
                    'yaml': ('a: 1\nb: 2\nc: 3\n', 9),
                    'javascript': ('a();b();c();', 8)}
        for fmt, (text, budget) in examples.items():
            with self.subTest(fmt=fmt):
                sections = plan(text, fmt, budget)
                self.assertEqual(sections[0].sibling_range, (0, 1))
                self.assertEqual(sections[0].path_parts, ())
                self.assertTrue(sections[0].path.endswith('::children[0,1]'))
                self.assertEqual(sections[-1].residual_source_indices, [1])

    def test_native_budget_selection_and_source_contract(self):
        for fmt, text in SAMPLES.items():
            sections = build_sections(text, TOKENIZER, 20, 'treeagent', context_format=fmt)
            first = sections[0]
            self.assertEqual(first.tree_budget_max, 39)
            target = (len(text) + 19) // 20
            counts = {b: len(source_sections_for_budget(text, fmt, TOKENIZER, b)) for b in range(20, 40)}
            expected = min(first.candidate_budgets,
                           key=lambda b: (abs(counts[b] - target), counts[b] < target, b))
            self.assertEqual(first.selected_tree_budget, expected)
            self.assert_source_contract(text, sections, expected)

    def test_native_runtime_retrieves_from_both_levels_and_saves_every_step(self):
        for fmt, text in SAMPLES.items():
            sections = plan(text, fmt, BUDGETS[fmt])
            observed = []
            def update(question, previous, observation):
                observed.append(observation)
                return f'price at step {observation.section.step_id}'
            result = run_memory_agent(sections, 'price', TOKENIZER, update, lambda q, m: m,
                                      native_context=lambda s, m: ('native', s.step_id))
            self.assertEqual(set(result.history), {1, 2, 3, 4})
            self.assertEqual(observed[-1].native_context, ('native', 4))
            self.assertIn('price at step 2', observed[-1].residual)
            self.assertIn('price at step 3', observed[-1].residual)
            self.assertNotIn('price at step 1', observed[-1].residual)
            self.assertNotIn('price at step 4', observed[-1].residual)

    def test_flat_uses_same_original_source_and_no_structural_metadata(self):
        for fmt, text in SAMPLES.items():
            sections = build_sections(text, TOKENIZER, 15, 'flat', context_format=fmt)
            self.assertEqual(''.join(s.text for s in sections), text)
            self.assertTrue(all(not s.path_text and not s.residual_source_indices for s in sections))
            self.assertEqual(len(sections), (len(text) + 14) // 15)

    def test_html_entity_and_unicode_boundaries(self):
        text = '<p>' + ('中文😀 &amp; &#x1f600; text ' * 20) + '</p>'
        sections = plan(text, 'html', 32)
        self.assert_source_contract(text, sections, 32)
        self.assertGreater(len(sections), 2)
        for section in sections:
            tail = section.text.rsplit('&', 1)[-1]
            if '&' in section.text:
                self.assertIn(';', tail)
        # Entities are their own native nodes; the enclosing element closes last.
        self.assertTrue(all('/p[1]' not in s.closing_paths for s in sections[:-1]))
        self.assertIn('/p[1]', sections[-1].closing_paths)

    def test_html_plain_text_leaf_closes_only_after_final_fragment(self):
        text = '<p>' + '中文 text ' * 50 + '</p>'
        sections = plan(text, 'html', 32)
        self.assert_source_contract(text, sections, 32)
        self.assertEqual(len({s.path for s in sections}), 1)
        self.assertTrue(all('/p[1]/text[1]' not in s.closing_paths for s in sections[:-1]))
        self.assertIn('/p[1]/text[1]', sections[-1].closing_paths)

    def test_residual_graph_matches_original_parser_byte_endpoint_oracle(self):
        for fmt, text in SAMPLES.items():
            original = parse_native_tree(text, fmt)
            for budget in (8, 20, 40):
                sections = plan(text, fmt, budget)
                final = {n.path: next(s.step_id for s in sections
                                     if s.source_byte_start <= n.end - 1 < s.source_byte_end)
                         for n in walk(original)}
                expected = {s.step_id: set() for s in sections}
                for node in walk(original):
                    if node.parent and final[node.path] < final[node.parent.path]:
                        expected[final[node.parent.path]].add(final[node.path])
                for s in sections:
                    self.assertEqual(set(s.residual_source_indices), expected[s.step_id], (fmt, budget))

    def test_html_optional_end_tags_and_void_nodes(self):
        text = '<ul><li>alpha<li>beta</ul><p>one<br>two'
        root = parse_native_tree(text, 'html')
        ul = root.children[0]
        self.assertEqual([n.kind for n in ul.children], ['li', 'li'])
        sections = plan(text, 'html', 16)
        self.assert_source_contract(text, sections, 16)
        self.assertNotIn('</li>', ''.join(s.text for s in sections))

    def test_html_script_and_comment_remain_atomic(self):
        for text in ('<script>' + 'let x=1;' * 20 + '</script>', '<!-- ' + 'words ' * 30 + '-->'):
            sections = plan(text, 'html', 20)
            self.assertEqual(len(sections), 1)
            self.assertTrue(sections[0].atomic_overflow)
            self.assertEqual(sections[0].text, text)

    def test_yaml_stream_aliases_and_duplicate_keys_preserve_source(self):
        text = '---\na: &base {x: 1}\nb: *base\na: 2\n---\na: 3\nb: 4\n'
        root = parse_native_tree(text, 'yaml')
        self.assertEqual(len(root.children), 2)
        paths = [n.path for n in walk(root)]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(any('#occurrence[2]' in path for path in paths))
        sections = plan(text, 'yaml', 18)
        self.assert_source_contract(text, sections, 18)
        self.assertTrue(any('*base' in s.text for s in sections))
        self.assertIn(root.path, sections[-1].closing_paths)

    def test_yaml_block_scalar_quoted_values_and_typed_scalars_are_atomic(self):
        for text in ('text: |+\n  one two three four five six\n\n',
                     'text: "one two three four five six"\n', 'value: !!str 1234567890123\n'):
            sections = plan(text, 'yaml', 8)
            self.assertEqual(len(sections), 1)
            self.assertTrue(sections[0].atomic_overflow)
            self.assertEqual(sections[0].text, text)

    def test_yaml_plain_text_fragments_share_leaf_path(self):
        text = 'text: ' + 'alpha beta gamma ' * 20 + '\n'
        sections = plan(text, 'yaml', 30)
        self.assert_source_contract(text, sections, 30)
        self.assertEqual(len({s.path for s in sections}), 1)
        self.assertTrue(all(not s.closing_paths for s in sections[:-1]))

    def test_javascript_multiple_bindings_and_sparse_arrays(self):
        text = 'const first={a:1111}, second={b:2222,c:3333};'
        root = parse_native_tree(text, 'javascript')
        declaration = root.children[0]
        self.assertEqual(len(declaration.children), 2)
        self.assertEqual(text[declaration.children[1].start:declaration.children[1].end],
                         'second={b:2222,c:3333}')
        self.assert_source_contract(text, plan(text, 'javascript', 18), 18)
        sparse = 'const items=[1,,3];'
        sections = plan(sparse, 'javascript', 8)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].text, sparse)
        self.assertTrue(sections[0].atomic_overflow)

    def test_javascript_escapes_preserved_and_templates_with_substitution_atomic(self):
        payload = r'alpha\uD83D\uDE00\n\x41beta' * 15
        text = 'const text="' + payload + '";'
        sections = plan(text, 'javascript', 30)
        self.assert_source_contract(text, sections, 30)
        for s in sections:
            self.assertFalse(s.text.endswith('\\'))
            self.assertFalse(s.text.endswith('\\uD83D'))
        template = 'const text=`' + 'content ' * 20 + '${value}`;'
        sections = plan(template, 'javascript', 20)
        self.assertEqual(len(sections), 1)
        self.assertTrue(sections[0].atomic_overflow)

    def test_javascript_source_markers_are_nodes_not_string_matches(self):
        text = '// @structured-javascript-file {"id":"a"}\nconst a={x:1,y:2};\n' + \
               '// @structured-javascript-file {"id":"b"}\nconst b={x:3,y:4};\n'
        root = parse_native_tree(text, 'javascript')
        self.assertEqual(root.kind, 'source_forest')
        self.assertEqual([n.path for n in root.children], ['/source[0]', '/source[1]'])
        sections = plan(text, 'javascript', 24)
        self.assert_source_contract(text, sections, 24)
        self.assertTrue(any(i < sections[-1].step_id for i in sections[-1].residual_source_indices))
        embedded = 'const text=`// @structured-javascript-file {"id":"fake"}`;'
        self.assertEqual(parse_native_tree(embedded, 'javascript').kind, 'program')

    def test_malformed_yaml_and_javascript_rejected(self):
        for fmt, text in (('yaml', 'a: [1, 2'), ('javascript', 'const x = {')):
            with self.assertRaises(ValueError):
                plan(text, fmt, 30)

    def test_empty_and_whitespace_sources(self):
        for fmt in SAMPLES:
            self.assertEqual(plan('', fmt, 10), [])
            self.assert_source_contract(' \n\t', plan(' \n\t', fmt, 10), 10)

    def test_representative_data_executes_all_four_formats(self):
        for family, fmt in [('json', 'json'), ('html', 'html'),
                            ('yaml', 'yaml'), ('javascript', 'javascript')]:
            with self.subTest(fmt=fmt):
                path = next(p for p in (ROOT / 'data' / family).glob('*.jsonl')
                            if p.name != 'source_examples.jsonl')
                row = json.loads(path.read_text().splitlines()[0])
                context = row['context']
                value = json.loads(context) if fmt == 'json' and isinstance(context, str) else context
                sections = build_sections(value, TOKENIZER, 512, 'treeagent', context_format=fmt)
                self.assertTrue(sections)
                if fmt != 'json':
                    self.assert_source_contract(context, sections, sections[0].selected_tree_budget)
                self.assertTrue(all(s.tree_budget_max == 1023 for s in sections))


if __name__ == '__main__':
    unittest.main()
