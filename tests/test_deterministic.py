from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis.aggregate import macro_by
from evaluation.replay import read_jsonl, score_rows
from treeagent.residual import ResidualMemoryStore
from treeagent.runtime import run_memory_agent
from treeagent.sectioning import (
    JsonSection, build_sections, format_path, _tree_sections_for_budget,
    annotate_residual_links, compact_dumps,
)
from treeagent.tokenizers import CharacterTokenizer

ROOT = Path(__file__).resolve().parents[1]


def plan(value, budget):
    return build_sections(value, CharacterTokenizer(), budget, 'treeagent', max_tree_budget=budget)


def section(step, sources=()):
    return JsonSection('', '', 'treeagent', 'subtree', step_id=step,
                       residual_source_indices=list(sources))


class SectioningTest(unittest.TestCase):
    def test_paths_quote_names_and_preserve_ancestor_chain(self):
        self.assertEqual(format_path(('records', 3, 'display name')), '$.records[3]["display name"]')
        self.assertEqual(format_path(('a.b', 'x"y')), '$["a.b"]["x\\"y"]')

    def test_intact_root_has_empty_path_parts(self):
        sections = plan({'a': 1}, 10)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].path_parts, ())
        self.assertEqual(sections[0].path, '$')
        self.assertIn('$', sections[0].closing_paths)
        self.assertEqual(sections[0].residual_source_indices, [])

    def test_single_subtree_has_own_path_and_no_added_wrappers(self):
        sections = plan({'a': {'x': 1}, 'b': {'x': 2}}, 8)
        self.assertEqual([s.path for s in sections], ['$.a', '$.b'])
        self.assertEqual([s.text for s in sections], ['{"x":1}', '{"x":2}'])
        self.assertTrue(all(s.wrapper_tokens == 0 for s in sections))

    def test_array_and_object_ranges_are_inclusive_child_positions(self):
        for value in ([1, 2, 3, 4], {'a': 1, 'b': 2, 'c': 3, 'd': 'long'}):
            sections = plan(value, 5 if isinstance(value, list) else 13)
            group = sections[0]
            self.assertEqual(group.sibling_range, (0, 1))
            self.assertEqual(group.path_parts, ())
            self.assertEqual(group.path, '$::children[0,1]')
            self.assertNotIn(group.path, group.closing_paths)

    def test_group_keeps_order_and_quoted_keys(self):
        s = plan({'a.b': 1, 'c d': 2, 'tail': 'x' * 30}, 17)[0]
        self.assertEqual(s.sibling_range, (0, 1))
        self.assertEqual(list(json.loads(s.text)), ['a.b', 'c d'])
        self.assertEqual(s.covered_paths, ['$["a.b"]', '$["c d"]'])

    def test_long_string_splits_losslessly_and_retains_leaf_path(self):
        value = 'alpha "beta"\\gamma\n😀 中文' * 3
        sections = plan({'text': value}, 12)
        self.assertGreater(len(sections), 1)
        self.assertEqual(''.join(json.loads(s.content_text) for s in sections), value)
        self.assertTrue(all(json.loads(s.text)['text'] == json.loads(s.content_text) for s in sections))
        self.assertTrue(all(s.path == '$.text' and s.content_tokens <= 12 for s in sections))
        self.assertTrue(all('$.text' not in s.closing_paths for s in sections[:-1]))
        self.assertIn('$.text', sections[-1].closing_paths)
        self.assertTrue(all(s.residual_source_indices == [] for s in sections))

    def test_atomic_overflow_and_minimum_budget(self):
        sections = plan({'number': 123456789, 'text': '\n'}, 2)
        self.assertEqual(json.loads(sections[0].text), 123456789)
        self.assertTrue(sections[0].atomic_overflow)
        self.assertTrue(sections[1].atomic_overflow)
        self.assertEqual(json.loads(sections[1].text), {'text': '\n'})
        tiny = build_sections(True, CharacterTokenizer(), 1, 'treeagent')
        self.assertEqual(tiny[0].tree_budget_max, 1)
        self.assertTrue(tiny[0].atomic_overflow)

    def test_flat_uses_compact_input_tokens(self):
        value = {'a': [1, 2], 'b': '中文'}
        sections = build_sections(value, CharacterTokenizer(), 4, 'flat')
        self.assertEqual(''.join(s.text for s in sections), compact_dumps(value))
        self.assertEqual(len(sections), (len(compact_dumps(value)) + 3) // 4)
        self.assertTrue(all(s.content_tokens <= 4 and not s.path_text for s in sections))

    def test_budget_endpoint_and_invalid_requests(self):
        sections = build_sections(list(range(8)), CharacterTokenizer(), 5, 'treeagent')
        self.assertEqual(sections[0].tree_budget_max, 9)
        for maximum in (0, 4, 10):
            with self.assertRaises(ValueError):
                build_sections([], CharacterTokenizer(), 5, 'treeagent', max_tree_budget=maximum)
        with self.assertRaises(ValueError):
            build_sections([], CharacterTokenizer(), 0, 'flat')
        with self.assertRaises(ValueError):
            build_sections([], CharacterTokenizer(), 5, 'other')
        with self.assertRaises(ValueError):
            build_sections([], CharacterTokenizer(), 5, 'treeagent', max_sections=1)

    def test_candidate_objective_compares_all_visited_even_nonmonotonic(self):
        # 20 characters at C=5 gives four Flat sections. Counts deliberately
        # violate monotonicity: an earlier probe is better than the endpoint.
        counts = {5: 6, 6: 5, 7: 3, 8: 7, 9: 9}
        def fake(value, tokenizer, budget):
            return [section(i + 1) for i in range(counts[budget])]
        from treeagent.sectioning import count_matched_tree_sections
        with patch('treeagent.sectioning._tree_sections_for_budget', side_effect=fake):
            actual = count_matched_tree_sections('x' * 18, CharacterTokenizer(), 5)
        # At equal error prefer count >= Flat, then smaller budget.
        self.assertEqual(actual[0].selected_tree_budget, 6)
        self.assertEqual(actual[0].candidate_budgets, [5, 6, 7, 9])

    def test_candidate_tie_prefers_smaller_budget(self):
        from treeagent.sectioning import count_matched_tree_sections
        with patch('treeagent.sectioning._tree_sections_for_budget',
                   side_effect=lambda value, tokenizer, budget: [section(1)] * 4):
            actual = count_matched_tree_sections('x' * 18, CharacterTokenizer(), 5)
        self.assertEqual(actual[0].selected_tree_budget, 5)

    def test_determinism_and_exact_token_accounting(self):
        value = json.loads((ROOT / 'examples/toy_document.json').read_text())
        first = build_sections(value, CharacterTokenizer(), 72, 'treeagent')
        second = build_sections(value, CharacterTokenizer(), 72, 'treeagent')
        self.assertEqual([s.as_record() for s in first], [s.as_record() for s in second])
        for s in first:
            self.assertEqual(s.content_tokens, len(s.content_text if s.content_text is not None else s.raw_text))
            self.assertEqual(s.total_tokens, len(s.text) + len(s.path_text))


class ResidualLinksTest(unittest.TestCase):
    def test_links_target_parent_final_segment_including_root(self):
        # Each record fits alone. The inner array closes at 3; root closes at 4.
        sections = plan({'rows': [{'name': 'alpha'}, {'name': 'bravo'}, {'name': 'gamma'}],
                         'tail': 'done'}, 18)
        self.assertEqual([s.path for s in sections], ['$.rows[0]', '$.rows[1]', '$.rows[2]', '$.tail'])
        self.assertEqual([s.residual_source_indices for s in sections], [[], [], [1, 2], [3]])
        self.assertIn('$', sections[-1].closing_paths)

    def test_coincident_parent_targets_union_all_links(self):
        sections = plan({'a': {'x': 1111, 'y': 2222}, 'b': {'x': 3333, 'y': 4444}}, 5)
        self.assertEqual([s.residual_source_indices for s in sections], [[], [1], [], [2, 3]])

    def test_grouped_children_deduplicate_saved_index(self):
        sections = plan([1, 2, 3, 4, 5], 5)
        self.assertEqual([s.residual_source_indices for s in sections], [[], [], [1, 2]])
        # Two children end at step 1, but it occurs once in the incoming set.
        self.assertEqual(sections[-1].residual_source_indices.count(1), 1)

    def test_independent_final_index_oracle(self):
        # Each atomic leaf exceeds B; their known DFS order defines ell(v)
        # without consulting the implementation's completion annotations.
        value = {'a': [1111, {'b': 2222, 'c': 3333}], 'd': [4444, 5555]}
        sections = plan(value, 2)
        self.assertEqual(len(sections), 5)
        # Parent a[1] closes at 3: 2->3; a also closes at 3: 1->3.
        # Parent d closes at 5: 4->5; root closes at 5: 3->5.
        self.assertEqual([s.residual_source_indices for s in sections], [[], [], [1, 2], [], [3, 4]])

    def test_store_saves_every_fragment_and_runtime_preserves_callbacks(self):
        sections = plan({'a': 'abcdefghijk', 'b': 123456}, 5)
        seen = []
        def update(question, previous, obs):
            self.assertEqual(question, 'price')
            self.assertEqual(obs.native_context, ('native', obs.section.step_id))
            seen.append((previous, obs.residual))
            return f'price {obs.section.step_id}'
        result = run_memory_agent(sections, 'price', CharacterTokenizer(), update,
                                  lambda q, m: ('answer', q, m),
                                  native_context=lambda s, m: ('native', s.step_id))
        self.assertEqual(len(result.history), len(sections))
        self.assertEqual(result.history[1], 'price 1')
        self.assertEqual(seen[0], ('', ''))
        self.assertEqual(seen[1][0], 'price 1')
        self.assertEqual(result.answer, ('answer', 'price', result.memory))
        self.assertIn(f'price {len(sections)-1}', seen[-1][1])

    def test_ranking_uses_full_span_then_truncates(self):
        store = ResidualMemoryStore(CharacterTokenizer(), top_k=1, item_max_tokens=5)
        store.record(section(1), 'aaaaa keyword keyword.\nkeyword.')
        text, stats = store.render(section(2, [1, 1]), 'keyword keyword')
        self.assertEqual(text, 'aaaaa')
        self.assertEqual(stats['residual_source_indices'], [1])
        self.assertEqual(stats['residual_candidate_spans'], 2)

    def test_no_query_match_or_no_links_produces_empty_context(self):
        store = ResidualMemoryStore(CharacterTokenizer())
        store.record(section(1), 'value 123')
        for sources, query in (([1], 'hotels'), ([], 'value'), ([1], 'the and')):
            self.assertEqual(store.render(section(2, sources), query)[0], '')

    def test_top_k_and_per_span_budget(self):
        store = ResidualMemoryStore(CharacterTokenizer(), top_k=2, item_max_tokens=8)
        store.record(section(1), 'price one.\nprice two.\nprice three.')
        text, stats = store.render(section(2, [1]), 'price')
        self.assertEqual(stats['residual_item_count'], 2)
        self.assertTrue(all(len(line) <= 8 for line in text.splitlines()))

    def test_future_missing_duplicate_out_of_order_states_rejected(self):
        store = ResidualMemoryStore(CharacterTokenizer())
        for current in (section(1, [1]), section(1, [0]), section(2)):
            with self.assertRaises(ValueError):
                store.render(current, 'price')
        store.record(section(1), 'price')
        with self.assertRaises(ValueError):
            store.record(section(1), 'overwritten')
        with self.assertRaises(ValueError):
            store.record(section(3), 'skipped')
        with self.assertRaises(ValueError):
            store.render(section(1), 'price')


class ReplayTest(unittest.TestCase):
    def test_offline_replay_unchanged(self):
        actual = score_rows(read_jsonl(ROOT / 'examples/toy_predictions.jsonl'))
        expected = json.loads((ROOT / 'expected_outputs/toy_score_summary.json').read_text())
        self.assertEqual(actual, expected)

    def test_missing_prediction_scores_zero(self):
        self.assertEqual(score_rows([{'id': 'x', 'gold': 'expected', 'metric_type': 'accuracy_string'}])['fractional_score'], 0)

    def test_macro_aggregation(self):
        actual = macro_by([{'benchmark': 'A', 'score': 1}, {'benchmark': 'A', 'score': 0},
                           {'benchmark': 'B', 'score': 0.5}], ('benchmark',))
        self.assertEqual(actual, [{'benchmark': 'A', 'n': 2, 'mean_score': 0.5},
                                  {'benchmark': 'B', 'n': 1, 'mean_score': 0.5}])


if __name__ == '__main__':
    unittest.main()
