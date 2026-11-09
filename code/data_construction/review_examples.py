"""Export all packaged examples for inspection, with answers kept separate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

COLLECTIONS = (
    ('A', 'json/source_examples.jsonl', 'JSON API examples'),
    ('H', 'html/representative.jsonl', 'HTML examples'),
    ('J', 'javascript/representative.jsonl', 'JavaScript examples'),
    ('Y', 'yaml/real_examples.jsonl', 'YAML source examples'),
    ('R', 'json/regression_fixtures.jsonl', 'JSON regression fixtures'),
    ('S', 'yaml/synthetic_fixtures.jsonl', 'Synthetic YAML fixtures'),
)


def public_input(row: dict, context_format: str) -> dict:
    """An allowlist; evaluation metadata never becomes model input."""
    raw = row['input'] if 'input' in row else row['context']
    if not isinstance(raw, str):
        raw = json.dumps(raw, ensure_ascii=False, separators=(',', ':'))
    instructions = row.get('instructions')
    if not instructions:
        instructions = 'Answer using only the supplied data.\n\n' + row.get(
            'answer_format_instruction', 'Return only the requested value, without explanations.')
    record = {
        'uid': row['uid'], 'context_format': context_format,
        'instructions': instructions, 'question': row['question'], 'input': raw,
        'task': row.get('task', row.get('task_subtype')),
        'input_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        'sample_revision': row.get('sample_revision', 'source_preserved'),
    }
    for key in ('public_required_slots', 'answer_protocol', 'metric_type'):
        if key in row:
            record[key] = row[key]
    return record


def render_prompt(record: dict) -> str:
    return ('Instructions\n' + record['instructions'] + '\n\nData\n' + record['input']
            + '\n\nQuestion\n' + record['question'] + '\n')


def export_files(root: Path) -> dict[str, bytes]:
    """Derive every output from current packaged rows; no hand-maintained copies."""
    files = {}
    index = ['# Packaged examples\n',
        'These are the complete packaged examples, including source examples and regression fixtures. '
        'Each entry separates mandatory instructions from the question and links to the complete input. '
        '[Reference answers](ANSWERS.md) are kept separate.\n',
        'Send only `instructions`, `input`, and `question` to a model. Other public fields identify '
        'the sample and evaluation contract. For memory agents, feed the input through the host\'s '
        'sectioning loop while retaining the instructions and question. `prompt.txt` contains the '
        'complete task input; the host supplies its memory/control prompts.\n',
        'String inputs retain their bytes. JSON object fixtures are serialized compactly from their '
        'packaged representation.\n',
        'API examples keep their typed JSON-array protocol. Other collections retain their declared '
        'scalar/list metrics; the JavaScript tiny-number example uses `exact_number_match`. '
        'See [scoring contracts](../../code/evaluation/README.md).\n',
        'Sample UIDs identify source examples. A changed question or scoring contract carries '
        '`sample_revision`; pin package hashes as well as UIDs when comparing results.\n']
    answers = ['# Reference answers\n', 'Evaluation only. Do not append this file to model inputs.\n']
    seen = set()
    for prefix, relative, title in COLLECTIONS:
        index.append(f'## {title}\n')
        if prefix == 'A':
            index.append('A03 requests the GUIDs of four vulnerability records.\n')
        if prefix == 'S':
            index.append('Generated OpenAPI fixtures for task and structure checks. '
                         'S09 repeats S01\'s lookup for structural inspection.\n')
        for number, line in enumerate((root / 'data' / relative).read_bytes().splitlines(), 1):
            row = json.loads(line)
            if row['uid'] in seen:
                raise ValueError('duplicate sample UID')
            seen.add(row['uid'])
            label = f'{prefix}{number:02d}'
            public = public_input(row, relative.split('/')[0])
            files[f'{label}/public_input.json'] = (json.dumps(public, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
            files[f'{label}/prompt.txt'] = render_prompt(public).encode('utf-8')
            index.extend([f'### {label} — {public["task"]}\n',
                f'UID: `{row["uid"]}` · Revision: `{public["sample_revision"]}`\n',
                f'[Source row](../../data/{relative}#L{number}) · '
                f'[Complete input]({label}/prompt.txt) · [Public fields]({label}/public_input.json) · '
                f'[Answer](ANSWERS.md#{label.lower()})\n',
                '**Instructions**\n\n```text\n'+public['instructions']+'\n```\n',
                '**Question**\n\n'+public['question']+'\n'])
            answers.extend([f'## {label}\n', f'UID: `{row["uid"]}`\n',
                            '```text\n'+row['gold_answer']+'\n```\n'])
    files['README.md'] = ('\n'.join(index)+'\n').encode('utf-8')
    files['ANSWERS.md'] = ('\n'.join(answers)+'\n').encode('utf-8')
    return files


def generate(root: Path, *, check: bool = False) -> int:
    destination = root / 'examples' / 'review'
    files = export_files(root)
    if check:
        actual = {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
        if actual != set(files):
            raise ValueError('review export inventory mismatch; regenerate exports')
        for name, content in files.items():
            if (destination / name).read_bytes() != content:
                raise ValueError(f'stale review export: {name}')
    else:
        for name, content in files.items():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    count = generate(args.package_root, check=args.check)
    print(f'Review exports {"verified" if args.check else "written"}: {count} files')


if __name__ == '__main__':
    main()
