"""Regressions against the original-subtree budget in the manuscript."""
import unittest

from treeagent.native_source import source_sections_for_budget, walk
from treeagent.native_tree import parse_native_tree
from treeagent.tokenizers import CharacterTokenizer


class NativeContentBudgetTest(unittest.TestCase):
    def test_long_ancestor_does_not_split_fitting_subtree(self):
        examples = [
            ('html', '<div data-note="' + 'x' * 80 + '"><p>abcdefghij</p></div>', '<p>abcdefghij</p>'),
            ('yaml', 'long_' + 'x' * 80 + ':\n  value: abcdefghij\n', 'value: abcdefghij'),
            ('javascript', 'const long_' + 'x' * 80 + '={value:"abcdefghij"};', 'value:"abcdefghij"'),
        ]
        for fmt, text, content in examples:
            with self.subTest(fmt=fmt):
                sections = source_sections_for_budget(text, fmt, CharacterTokenizer(), 20)
                self.assertEqual(len(sections), 1)
                section = sections[0]
                self.assertEqual(section.content_text, content)
                self.assertEqual(section.content_tokens, len(content))
                self.assertFalse(section.atomic_overflow)
                self.assertEqual(section.text, text)
                self.assertEqual(section.wrapper_tokens, len(text) - len(content))

    def test_fitting_property_uses_original_parser_intervals(self):
        examples = {
            'html': '<article class="' + 'x' * 80 + '"><p>alpha</p><p>beta</p></article>',
            'yaml': 'long_' + 'x' * 80 + ':\n  first: alpha\n  second: beta\n',
            'javascript': 'const long_' + 'x' * 80 + '={first:"alpha",second:"beta"};',
        }
        for fmt, text in examples.items():
            raw = text.encode()
            root = parse_native_tree(text, fmt)
            for budget in (10, 16, 20, 32):
                sections = source_sections_for_budget(text, fmt, CharacterTokenizer(), budget)
                for node in walk(root):
                    if len(raw[node.start:node.end].decode()) <= budget:
                        touching = [s for s in sections
                                    if s.source_byte_start < node.end and s.source_byte_end > node.start]
                        self.assertEqual(len(touching), 1, (fmt, budget, node.path))

    def test_unicode_wrapper_accounting_and_source_coordinates(self):
        text = '<div title="' + '中文😀' * 30 + '"><p>okay</p></div>'
        sections = source_sections_for_budget(text, 'html', CharacterTokenizer(), 20)
        self.assertEqual(len(sections), 1)
        section = sections[0]
        self.assertEqual(section.content_text, '<p>okay</p>')
        raw = text.encode()
        self.assertEqual(raw[section.content_byte_start:section.content_byte_end].decode(), section.content_text)
        self.assertEqual(section.wrapper_prefix + section.content_text + section.wrapper_suffix, text)
        self.assertEqual(section.total_tokens, len(text) + len(section.path_text))

    def test_large_atomic_leaf_still_reports_content_overflow(self):
        content = '<script>' + 'let x=1;' * 20 + '</script>'
        text = '<div data-note="' + 'x' * 80 + '">' + content + '</div>'
        sections = source_sections_for_budget(text, 'html', CharacterTokenizer(), 20)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].content_text, 'let x=1;' * 20)
        self.assertEqual(sections[0].text, text)
        self.assertTrue(sections[0].atomic_overflow)


if __name__ == '__main__':
    unittest.main()
