"""Check review contents for private paths, credentials, and manifest integrity."""
from __future__ import annotations

import argparse
import hashlib
import re
import json
import sys
from pathlib import Path

# Third-party authorship notices and upstream dataset/code URLs are retained.
PATTERNS = {
    'private_home': re.compile(r'/(?:data/)?home/[^/\s]+/|' + '/' + r'Users/[^/\s]+/'),
    'ssh_remote': re.compile('git' + r'@[^\s]+:'),
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'access_credential': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|hf_[A-Za-z0-9]{30,})\b'),
}
IGNORED = {'.git', '__pycache__', '.pytest_cache'}


def check(root: Path, forbidden: list[str]) -> None:
    issues = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts):
            continue
        for item in forbidden:
            if item.casefold() in relative.as_posix().casefold():
                issues.append(f'{relative}: supplied identifying term in path')
        if path.is_symlink():
            issues.append(f'{relative}: symbolic link')
            continue
        if not path.is_file():
            continue
        if path.suffix in {'.pyc', '.zip', '.pdf'} or path.name == '.uuid':
            issues.append(f'{relative}: unexpected artifact')
        text = path.read_text(encoding='utf-8')
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                issues.append(f'{relative}: {label}')
        for item in forbidden:
            if item.casefold() in text.casefold():
                issues.append(f'{relative}: supplied identifying term')
    checksums = root / 'SHA256SUMS'
    if checksums.exists():
        declared = set()
        for line in checksums.read_text().splitlines():
            digest, name = line.split('  ', 1)
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts or name in declared:
                raise ValueError('unsafe or duplicate checksum path')
            declared.add(name)
            path = root / relative
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                issues.append(f'{name}: checksum mismatch')
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*')
                  if p.is_file() and p.name != 'SHA256SUMS'
                  and not any(part in IGNORED for part in p.relative_to(root).parts)}
        if actual != declared:
            issues.append('checksum inventory does not match the artifact')
    if issues:
        raise SystemExit('\n'.join(issues))
    sys.path.insert(0, str(root / 'code'))
    from data_construction.privacy import validate_private_fields
    for line in (root / 'data/json/regression_fixtures.jsonl').read_text().splitlines():
        validate_private_fields(json.loads(line))
    from data_construction.real_yaml import validate as validate_real_yaml
    validate_real_yaml(root)
    from data_construction.validate_subset import validate_json_source_examples
    validate_json_source_examples(root)
    from data_construction.review_examples import generate
    generate(root, check=True)
    print('Configured anonymity patterns and artifact integrity checks passed.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--forbid-string', action='append', default=[])
    args = parser.parse_args()
    check(args.root, args.forbid_string)


if __name__ == '__main__':
    main()
