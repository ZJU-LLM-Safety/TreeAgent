"""Regressions for sample ambiguity, public-input isolation and exact extraction."""
import json
import tempfile
import unittest
from pathlib import Path

from data_construction.review_examples import public_input, render_prompt, generate, export_files
from data_construction.sample_revisions import revise_sample, EXACT_NUMBER_UID
from data_construction.prepare_subset import synthetic_yaml_rows
from evaluation.metrics import score_prediction_value
from evaluation.replay import score_rows

ROOT = Path(__file__).resolve().parents[1]


class ExactNumberTest(unittest.TestCase):
    def test_tiny_number_and_equivalent_notation(self):
        for prediction in ('1e-12', '0.000000000001', '+1.000e-12'):
            self.assertEqual(score_prediction_value(prediction, '0.000000000001', 'exact_number_match'), 1)
        for prediction in ('0', '0.001', '0.01', '-1e-12', '1.0001e-12',
                           'NaN', 'Infinity', 'true', '[1e-12]', 'value: 1e-12', '1e-12 junk'):
            self.assertEqual(score_prediction_value(prediction, '1e-12', 'exact_number_match'), 0)

    def test_no_float_rounding_and_replay_dispatch(self):
        self.assertEqual(score_prediction_value('9007199254740993', '9007199254740992', 'exact_number_match'), 0)
        result = score_rows([{'prediction': '0', 'gold': '1e-12', 'metric_type': 'exact_number_match'}])
        self.assertEqual(result['fractional_score'], 0)
        # The new sample contract does not change historical approximate metrics.
        self.assertEqual(score_prediction_value('1000.5', '1000', 'approx_number_match'), 1)


class PublicInputTest(unittest.TestCase):
    def test_only_whitelisted_fields_and_lossless_input(self):
        row = {'uid': 'example', 'context': '{"x":1}\r\n{"x":2}\n', 'question': 'Count?',
               'instructions': 'Use all data.', 'gold_answer': 'PRIVATE_GOLD',
               'gold_spec': {'secret': 'PRIVATE_QUERY'}, 'metadata': {'support': 'PRIVATE_PATH'},
               'answer': 'PRIVATE_ANSWER', 'supporting_paths': ['PRIVATE_SUPPORT']}
        public = public_input(row, 'json')
        prompt = render_prompt(public)
        self.assertEqual(public['input'], row['context'])
        self.assertEqual(prompt, 'Instructions\nUse all data.\n\nData\n'+row['context']+'\n\nQuestion\nCount?\n')
        self.assertNotIn('PRIVATE_', json.dumps(public))
        self.assertNotIn('PRIVATE_', prompt)

    def test_yaml_format_rule_reaches_export(self):
        for _, row in synthetic_yaml_rows():
            self.assertEqual(row, revise_sample(row))
            self.assertIn(row['answer_format_instruction'], render_prompt(public_input(row, 'yaml')))
            if row['task_subtype'] in {'multi_record_field_2', 'multi_record_field_4', 'record_multi_field_2', 'record_multi_field_4'}:
                self.assertIn('one value per line', public_input(row, 'yaml')['instructions'])
                self.assertEqual(row['metric_type'], 'ordered_list_str_match')

    def test_all_generated_exports_are_current_and_public(self):
        generate(ROOT, check=True)
        files = export_files(ROOT)
        publics = [json.loads(v) for k,v in files.items() if k.endswith('public_input.json')]
        self.assertEqual(len(publics), 62)
        self.assertEqual(len({r['uid'] for r in publics}), 62)
        for row in publics:
            self.assertFalse({'gold_answer', 'gold_spec', 'answer', 'metadata', 'supporting_paths'} & row.keys())
        target = next(r for r in publics if r['uid'] == EXACT_NUMBER_UID)
        self.assertEqual(target['metric_type'], 'exact_number_match')

    def test_stale_exports_are_rejected(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT/'data', root/'data')
            generate(root)
            target = root/'examples/review/A01/prompt.txt'
            target.write_text('stale question')
            with self.assertRaisesRegex(ValueError, 'stale review export'):
                generate(root, check=True)


if __name__ == '__main__':
    unittest.main()
