"""Build a deterministic review ZIP without repository or machine metadata."""
from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

from check_artifact import check

ALLOWED_DIRS = {'code', 'configs', 'data', 'examples', 'expected_outputs',
                'manifests', 'tests', 'third_party_licenses', 'scripts'}
ALLOWED_FILES = {'README.md', 'METHOD_CONTRACT.md', 'ENVIRONMENT.md', 'VALIDATION.md',
                 'LICENSE', 'LICENSES.md', 'PRIVACY.md', 'run_checks.sh', '.gitignore', 'requirements.txt'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output == root or root in output.parents:
        raise SystemExit('Write the archive outside the source directory.')
    paths = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in {'.git', '__pycache__', '.pytest_cache'} for part in relative.parts):
            continue
        if path.is_symlink():
            raise SystemExit(f'Refusing symbolic link: {relative}')
        if not path.is_file() or path.name == 'SHA256SUMS':
            continue
        if (len(relative.parts) == 1 and relative.name in ALLOWED_FILES
                or len(relative.parts) > 1 and relative.parts[0] in ALLOWED_DIRS):
            paths.append(path)
        else:
            raise SystemExit(f'Unexpected file: {relative}')
    manifest = root / 'SHA256SUMS'
    manifest.write_text(''.join(
        f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}\n'
        for p in paths
    ))
    check(root, [])
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(paths + [manifest]):
            info = zipfile.ZipInfo('treeagent-anonymous/' + path.relative_to(root).as_posix(),
                                   date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    print(f'Wrote {len(paths) + 1} files; SHA-256 {hashlib.sha256(output.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
