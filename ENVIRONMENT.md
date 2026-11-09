# Environment

Use Python 3.10 or newer and Bash. Install the parser versions in
`requirements.txt` if needed:

```bash
python3 -m pip install -r requirements.txt
bash run_checks.sh
```

Checks use local files and CPU execution. JSON parsing and scoring use the Python
standard library. The CLI uses a deterministic character tokenizer. To measure
sections with a model tokenizer, install Transformers and provide its local path:

```bash
python3 scripts/check_formats.py --tokenizer /path/to/local/tokenizer
```

Tokenizer loading uses `local_files_only=True` and `trust_remote_code=False`.
The Python API accepts the tokenizer supplied by the model integration.
