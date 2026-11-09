"""Behavioral regressions from the paper/artifact review."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evaluation.metrics import score_prediction_value
from treeagent import build_sections, parse_json_text, run_memory_agent
from treeagent.planning import choose_budget
from treeagent.sectioning import _tree_sections_for_budget
from treeagent.tokenizers import CharacterTokenizer

ROOT = Path(__file__).resolve().parents[1]
TOKENIZER = CharacterTokenizer()


class ScoringRegressionTest(unittest.TestCase):
    def test_list_signs_are_values_not_bullets(self):
        for metric in ('ordered_list_str_match', 'unordered_list_str_match'):
            for prediction, gold, expected in (
                ('[5]', '[-5]', 0), ('[-5]', '[5]', 0),
                ('[-5]', '[-5]', 1), ('["A"]', '["A-"]', 0),
                ('- -5', '[-5]', 1),
            ):
                with self.subTest(metric=metric, prediction=prediction, gold=gold):
                    self.assertEqual(score_prediction_value(prediction, gold, metric), expected)

    def test_unordered_numeric_tolerance_and_multiplicity(self):
        metric = 'unordered_list_str_match'
        for prediction, gold, expected in (
            ('[1.0]', '[1]', 1), ('[1000.5]', '[1000]', 1),
            ('[1002]', '[1000]', 0), ('[1]', '[1,1]', 0.5),
            ('[1,1]', '[1]', 0.5), ('[1,""]', '[1]', 0.5),
            ('["1000"]', '["USD 1000"]', 0),
            # Matching must reassign an ambiguous first match to attain two.
            ('[1000.5,999.5]', '[1000,1001]', 1),
        ):
            with self.subTest(prediction=prediction, gold=gold):
                self.assertEqual(score_prediction_value(prediction, gold, metric), expected)


class BudgetRegressionTest(unittest.TestCase):
    def test_main_text_tie_rule_includes_earlier_candidates(self):
        value = ['x', 'xxxxx', 'xxxxxxxxx']
        for native in (False, True):
            sections = choose_budget(5, None, 5,
                lambda b: _tree_sections_for_budget(value, TOKENIZER, b), native=native)
            self.assertEqual(sections[0].selected_tree_budget, 5)
            self.assertEqual(len(sections), 6)

    def test_all_formats_keep_best_probe_with_nonmonotone_counts(self):
        counts = {5: 6, 6: 5, 7: 3, 8: 7, 9: 9}
        for native in (False, True):
            sections = choose_budget(5, None, 4,
                lambda b: [SimpleNamespace() for _ in range(counts[b])], native=native)
            self.assertEqual(sections[0].selected_tree_budget, 6)


class JsonDocumentRegressionTest(unittest.TestCase):
    def plan(self, raw, budget, method='treeagent'):
        return build_sections(parse_json_text(raw), TOKENIZER, budget, method,
                              max_tree_budget=budget if method == 'treeagent' else None)

    def test_flat_preserves_documents_without_inventing_array(self):
        raw = ' { "a": [1,2] }\r\n { "a": [3,4] } '
        sections = self.plan(raw, 5, 'flat')
        self.assertEqual(''.join(s.text for s in sections), '{"a":[1,2]}\n{"a":[3,4]}')
        self.assertEqual([s.step_id for s in sections], list(range(1, len(sections)+1)))

    def test_virtual_root_packs_documents_without_serialized_brackets(self):
        raw = '{"a":1}\n{"a":2}\n{"a":3}'
        whole = self.plan(raw, len(raw))
        self.assertEqual([s.text for s in whole], [raw])
        grouped = self.plan(raw, 15)
        self.assertEqual(grouped[0].text, '{"a":1}\n{"a":2}')
        self.assertEqual(grouped[0].sibling_range, (0, 1))
        self.assertEqual(grouped[1].path, '$[2]')
        self.assertEqual(grouped[1].residual_source_indices, [1])

    def test_global_links_and_memory_across_documents(self):
        sections = self.plan('{"a":1111,"b":2222}\n{"a":3333,"b":4444}', 2)
        self.assertEqual([s.path for s in sections], ['$[0].a', '$[0].b', '$[1].a', '$[1].b'])
        self.assertEqual([s.residual_source_indices for s in sections], [[], [1], [], [2, 3]])
        result = run_memory_agent(sections, 'value', TOKENIZER,
            update=lambda q, memory, obs: memory + ' value ' + obs.section.text,
            answer=lambda q, memory: memory)
        for number in ('1111', '2222', '3333', '4444'):
            self.assertIn(number, result.answer)
        self.assertEqual(set(result.history), {1, 2, 3, 4})

    def test_stream_fragments_do_not_repeat_virtual_root_brackets(self):
        sections = self.plan('{"s":"abcdefghijk"}\n{"s":"lmnopqrstuv"}', 6)
        for index, original in enumerate(('abcdefghijk', 'lmnopqrstuv')):
            fragments = [s for s in sections if s.path == f'$[{index}].s']
            self.assertEqual(''.join(json.loads(s.text)['s'] for s in fragments), original)
            self.assertTrue(all(s.content_tokens <= 6 for s in fragments))

    def test_single_document_api_remains_identical(self):
        for value in ({'a': [1,2,3]}, [{'a': 1}, {'b': 2}], 'abc', 42, None):
            raw = json.dumps(value)
            expected = build_sections(value, TOKENIZER, 5, 'treeagent', max_tree_budget=5)
            actual = self.plan(raw, 5)
            self.assertEqual([s.as_record() for s in actual], [s.as_record() for s in expected])

    def test_malformed_trailing_content_is_not_silently_dropped(self):
        for raw in ('', ' \n ', '{}{}', '{}\n{"bad":', '{}\ngarbage', 'NaN'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_json_text(raw)

    def test_packaged_usgs_input_runs_as_one_cli_plan(self):
        rows = [json.loads(line) for line in (ROOT/'data/json/source_examples.jsonl').read_text().splitlines()]
        row = next(row for row in rows if row['provider'] == 'USGS')
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/'input.json', Path(directory)/'plan.json'
            source.write_text(row['input'])
            subprocess.run([sys.executable, '-m', 'treeagent.cli', '--input', str(source),
                            '--output', str(output), '--section-size', '5000'],
                           check=True, cwd=ROOT)
            plan = json.loads(output.read_text())
        self.assertTrue(any(s['path_parts'][:1] == [1] for s in plan['sections']))
        self.assertIn('$', plan['sections'][-1]['closing_paths'])
        self.assertEqual([s['step_id'] for s in plan['sections']], list(range(1, len(plan['sections'])+1)))


if __name__ == '__main__':
    unittest.main()
