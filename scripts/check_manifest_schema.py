"""Independent JSON Schema verification of the checked-in public manifest.

CI-only development utility. Does not load or run any formatter, codec or secret.
"""
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT / 'docs/specs/manifest-v1.schema.json').read_text(encoding='utf-8'))
manifest = json.loads((ROOT / 'manifests/formats-v1.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(schema)
Draft202012Validator(schema).validate(manifest)
formats = manifest['formats']
assert len({f['formatId'] for f in formats}) == len(formats), 'Duplicate format IDs'
for entry in formats:
    assert entry['maxInputBytes'] >= entry['minInputBytes'], entry['formatId']
    if entry['maturity'] == 'planned':
        assert entry['adapter'] is None, entry['formatId']
    if entry['sensitivity'] != 'public-only':
        raise AssertionError(f"Illegal format sensitivity: {entry['formatId']}")
print(f'Validated {len(formats)} manifest entries against JSON Schema')
