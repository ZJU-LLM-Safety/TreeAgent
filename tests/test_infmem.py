from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from treeagent import build_infmem_retrieval_corpus, build_sections
from treeagent.tokenizers import CharacterTokenizer

ROOT = Path(__file__).resolve().parents[1]


class InfMemCorpusTest(unittest.TestCase):
    def test_native_windows_overlap_and_short_tails(self):
        text = ''.join(chr(33 + i % 90) for i in range(5520))
        chunks = build_infmem_retrieval_corpus(text, CharacterTokenizer())
        expected = [(start, min(start + 500, 5000), 0) for start in range(0, 4801, 400)]
        expected += [(5000, 5500, 1), (5400, 5520, 1)]
        self.assertEqual([(c.token_start, c.token_end, c.raw_window_index) for c in chunks], expected)
        self.assertEqual([c.text for c in chunks], [text[a:b] for a, b, _ in expected])

    def test_same_raw_corpus_survives_different_section_plans(self):
        tokenizer = CharacterTokenizer()
        for name, fmt in [('toy_document.json', 'json'), ('toy_document.html', 'html'),
                          ('toy_document.yaml', 'yaml'), ('toy_document.js', 'javascript')]:
            with self.subTest(fmt=fmt):
                text = (ROOT / 'examples' / name).read_text()
                value = json.loads(text) if fmt == 'json' else text
                flat = build_infmem_retrieval_corpus(text, tokenizer)
                build_sections(value, tokenizer, 32, 'flat', context_format=fmt)
                build_sections(value, tokenizer, 32, 'treeagent', context_format=fmt)
                with patch('treeagent.sectioning.build_sections', side_effect=AssertionError('no structural corpus')):
                    tree = build_infmem_retrieval_corpus(text, tokenizer)
                self.assertEqual(flat, tree)
                self.assertEqual(flat[0].text, text[:500])

    def test_original_json_whitespace_is_not_reserialized(self):
        text = '  {\n  "key" : [ 1,  2 ]\n}\n'
        self.assertEqual(build_infmem_retrieval_corpus(text, CharacterTokenizer())[0].text, text)

    def test_empty_exact_boundary_and_invalid_inputs(self):
        tokenizer = CharacterTokenizer()
        self.assertEqual(build_infmem_retrieval_corpus('', tokenizer), [])
        self.assertEqual(len(build_infmem_retrieval_corpus('a' * 500, tokenizer)), 1)
        with self.assertRaises(TypeError):
            build_infmem_retrieval_corpus({}, tokenizer)
        for bad in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                build_infmem_retrieval_corpus('x', tokenizer, raw_window_tokens=bad)

    def test_shared_corpus_configuration(self):
        current = json.loads((ROOT / 'configs/www_method.json').read_text())['infmem_retrieval']
        self.assertEqual(current['methods'], ['flat', 'treeagent'])
        self.assertEqual(current['chunk_tokens'], 500)
        self.assertFalse(current['structural_retrieval_chunks'])
        self.assertEqual(current['overlap_tokens'], 100)
        self.assertEqual(current['canonical_raw_window_tokens'], 5000)


if __name__ == '__main__':
    unittest.main()
