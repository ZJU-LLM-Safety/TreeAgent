from types import SimpleNamespace
import json
import unittest

from evaluation.metrics import score_prediction_value
from treeagent.planning import choose_budget
from treeagent.sectioning import build_sections
from treeagent.tokenizers import CharacterTokenizer


class UnifiedBudgetTest(unittest.TestCase):
    def choose(self, counts, target):
        calls = []
        def construct(budget):
            calls.append(budget)
            return [SimpleNamespace() for _ in range(counts[budget])]
        result = choose_budget(10, 19, target, construct, native=True)
        self.assertEqual(len(calls), len(set(calls)))
        return result[0], calls

    def test_equal_counts_prefer_base_for_all_formats(self):
        result, calls = self.choose({b: 3 for b in range(10, 20)}, 4)
        self.assertEqual(result.selected_tree_budget, 10)
        self.assertIn(19, calls)

    def test_unreachable_target_selects_best_evaluated_budget(self):
        result, _ = self.choose({b: 4 if b < 15 else 3 for b in range(10, 20)}, 1)
        self.assertEqual(result.selected_tree_budget, 17)

    def test_transition_tie_prefers_count_above_target(self):
        result, _ = self.choose({b: 5 if b < 15 else 3 for b in range(10, 20)}, 4)
        self.assertEqual(result.selected_tree_budget, 10)

    def test_transition_compares_its_predecessor(self):
        result, _ = self.choose({b: 7 if b < 15 else 3 for b in range(10, 20)}, 4)
        self.assertEqual(result.selected_tree_budget, 15)


class JsonFragmentTest(unittest.TestCase):
    def plan(self, value, budget):
        return build_sections(value, CharacterTokenizer(), budget, 'treeagent', max_tree_budget=budget)

    def test_natural_boundary_and_enclosing_structure(self):
        original = 'abcdefgh ijklmnop qrst'
        sections = self.plan({'outer': [{'description': original}]}, 12)
        self.assertEqual(json.loads(sections[0].content_text), 'abcdefgh ')
        decoded = [json.loads(s.text)['outer'][0]['description'] for s in sections]
        self.assertEqual(''.join(decoded), original)
        for s in sections:
            self.assertEqual(s.path, '$.outer[0].description')
            self.assertEqual(s.text, s.wrapper_prefix + s.content_text + s.wrapper_suffix)
            self.assertEqual(s.content_tokens, len(s.content_text))
            self.assertEqual(s.wrapper_tokens, len(s.wrapper_prefix) + len(s.wrapper_suffix))
            self.assertEqual(s.total_tokens, len(s.text) + len(s.path_text))
            self.assertLessEqual(s.content_tokens, 12)

    def test_surrogate_pairs_and_escapes_remain_whole(self):
        for value in ['a😀b\\c\n"d' * 3, 'a\ud83d\ude00b' * 3]:
            sections = self.plan({'text': value}, 5)
            fragments = [s.content_text for s in sections]
            # Compare serialized code points for explicitly supplied surrogate pairs.
            payloads = [s.text[len(s.wrapper_prefix):-len(s.wrapper_suffix)] for s in sections]
            self.assertEqual(payloads, fragments)
            self.assertEqual(''.join(json.loads(s) for s in fragments), value)
            for s in fragments:
                decoded = json.loads(s)
                self.assertFalse(decoded and 0xD800 <= ord(decoded[-1]) <= 0xDBFF)
                self.assertFalse(decoded and 0xDC00 <= ord(decoded[0]) <= 0xDFFF)


class AnswerValidityTest(unittest.TestCase):
    def test_rejects_numbers_embedded_in_invalid_answers(self):
        for answer in ['not 42', '42 or 43', 'perhaps 42', '[42', '42]', 'NaN', 'Infinity', '42/']:
            with self.subTest(answer=answer):
                self.assertEqual(score_prediction_value(answer, '42', 'approx_number_match'), 0.0)

    def test_scalar_formats_and_tolerance(self):
        for answer in ['42', '42.01', '4.2e1', 'forty-two', 'Answer: 42', '`42`']:
            self.assertEqual(score_prediction_value(answer, '42', 'approx_number_match'), 1.0)
        self.assertEqual(score_prediction_value('42.1', '42', 'approx_number_match'), 0.0)
        self.assertEqual(score_prediction_value('USD 1,000', 'USD 1000', 'approx_number_match'), 1.0)
        self.assertEqual(score_prediction_value('1000', 'USD 1000', 'approx_number_match'), 0.0)

    def test_empty_and_malformed_answers_score_zero(self):
        for metric in ['accuracy_string', 'approx_number_match', 'ordered_list_str_match', 'unordered_list_str_match']:
            self.assertEqual(score_prediction_value('', '', metric), 0.0)
        for answer in ['[]', '["a",]', '["a"', '[["a"]]']:
            self.assertEqual(score_prediction_value(answer, '["a"]', 'ordered_list_str_match'), 0.0)

    def test_order_and_partial_credit_are_preserved(self):
        self.assertEqual(score_prediction_value('["A","wrong"]', '["a","b"]', 'ordered_list_str_match'), 0.5)
        self.assertEqual(score_prediction_value('["b","a"]', '["a","b"]', 'ordered_list_str_match'), 0.0)
        self.assertEqual(score_prediction_value('["b","a"]', '["a","b"]', 'unordered_list_str_match'), 1.0)

    def test_empty_slots_count_toward_prediction_length(self):
        for metric in ['ordered_list_str_match', 'unordered_list_str_match']:
            self.assertEqual(score_prediction_value('["a", ""]', '["a"]', metric), 0.5)
            self.assertEqual(score_prediction_value('["a", "   "]', '["a"]', metric), 0.5)

    def test_empty_slots_preserve_ordered_positions(self):
        self.assertEqual(score_prediction_value('["", "a", "b"]', '["a", "b"]', 'ordered_list_str_match'), 0.0)
        self.assertEqual(score_prediction_value('["a", "", "b"]', '["a", "b"]', 'ordered_list_str_match'), 1 / 3)

    def test_empty_slots_preserve_unordered_multiplicity(self):
        self.assertEqual(score_prediction_value('["a", "", "a"]', '["a", "a"]', 'unordered_list_str_match'), 2 / 3)

    def test_empty_values_cannot_match_each_other(self):
        from evaluation.metrics import ordered_list_str_score, unordered_list_str_score
        for scorer in (ordered_list_str_score, unordered_list_str_score):
            self.assertEqual(scorer('[]', '[]'), 0.0)
            self.assertEqual(scorer('[""]', '[""]'), 0.0)
            self.assertEqual(scorer('["a", ""]', '["a", ""]'), 0.5)

    def test_delimited_answers_preserve_internal_empty_slots(self):
        self.assertEqual(score_prediction_value('a,,b', 'a,b', 'unordered_list_str_match'), 2 / 3)
        self.assertEqual(score_prediction_value('a\n\nb', 'a\nb', 'ordered_list_str_match'), 1 / 3)


if __name__ == '__main__':
    unittest.main()
