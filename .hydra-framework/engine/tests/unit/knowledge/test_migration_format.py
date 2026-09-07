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


    def test_nested_mappings_and_lists_survive_a_round_trip(self):
        """A sequence item whose first key held a map used to vanish silently."""
        for value in (
            {"checks": [{"config": {"a": "1", "b": "2"}, "name": "x"}]},
            {"routes": [{"tags": ["x", "y"], "name": "r"}]},
            {"nested": [{"outer": {"inner": {"deep": "1"}}}]},
        ):
            text = emit_yaml(value)
            self.assertEqual(parse_yaml_text(text, "emitted", Path(".")), value)

    def test_none_emits_a_yaml_null_rather_than_the_string_none(self):
        self.assertEqual(emit_yaml({"k": None}), "k: null\n")


if __name__ == "__main__":
    unittest.main()
