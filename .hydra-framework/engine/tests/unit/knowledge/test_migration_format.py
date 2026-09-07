import unittest
from pathlib import Path

from hydra_engine.documents.yaml_documents import parse_yaml_text
from hydra_engine.knowledge.migration_format import emit_yaml


class MigrationFormatTests(unittest.TestCase):
    def test_nested_mapping_lists_round_trip(self):
        value = {"routes": {"deploy": {"expand_when": [{"when_paths": ["@app/src/**"], "read": ["hydra://knowledge-unit/a/b"]}]}}}
        path = Path(__file__)
        self.assertEqual(parse_yaml_text(emit_yaml(value), path, path.parent), value)


if __name__ == "__main__":
    unittest.main()
