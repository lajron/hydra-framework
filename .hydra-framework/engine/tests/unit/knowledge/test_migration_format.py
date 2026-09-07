import unittest
from pathlib import Path

from hydra_engine.documents.yaml_documents import parse_yaml_text
from hydra_engine.knowledge.migration_format import emit_yaml, manifest_payload, payload_digest


class MigrationFormatTests(unittest.TestCase):
    def test_nested_mapping_lists_round_trip(self):
        value = {"routes": {"deploy": {"expand_when": [{"when_paths": ["@app/src/**"], "read": ["hydra://knowledge-unit/a/b"]}]}}}
        path = Path(__file__)
        self.assertEqual(parse_yaml_text(emit_yaml(value), path, path.parent), value)

    def test_manifest_digest_excludes_review_envelope(self):
        payload = {"schema": "demo", "writes": []}
        digest = payload_digest(payload)
        manifest = {**payload, "plan_digest": digest, "review": {"approved": True}}
        self.assertEqual(manifest_payload(manifest), payload)
        self.assertEqual(payload_digest(manifest_payload(manifest)), digest)


if __name__ == "__main__":
    unittest.main()
