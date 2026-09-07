from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hydra_engine.documents.frontmatter_blocks import markdown_frontmatter, parse_yaml
from hydra_engine.knowledge import migration_v2


def _legacy(root: Path, *, expansion: str = "") -> None:
    package = root / ".hydra-framework/repo/knowledge/knowledge-packages/demo"
    units = package / "units"
    units.mkdir(parents=True)
    (package / "routing.yaml").write_text(
        "schema: hydra-framework.package-routing.v2\n"
        "hydra_id: hydra://knowledge-slice/demo/routing\n"
        "uid: 11111111-1111-4111-8111-111111111111\n"
        "schema_version: 3\nkind: knowledge-slice\npackage: demo\ntitle: Demo\nstatus: active\n"
        "scope: base-seed\nowners:\n  team: demo\n"
        "relations:\n  - hydra://knowledge-package/demo\nprovenance:\n  sources: []\n"
        "keywords: demo, migrate\n"
        "routes:\n  use:\n    use_when:\n      - use demo migration\n"
        "    priority_units:\n      - hydra://knowledge-unit/demo/guide\n",
        encoding="utf-8",
    )
    (package / "overview.md").write_text(
        "---\nhydra_id: hydra://knowledge-package/demo\nuid: 22222222-2222-4222-8222-222222222222\n"
        "schema_version: 3\nkind: knowledge-package\ntitle: Demo\nstatus: active\nscope: base-seed\n"
        "owners:\n  team: demo\nrelations: []\nprovenance:\n  sources: []\n---\n# Demo\n\n[Routing](routing.yaml)\n",
        encoding="utf-8",
    )
    (package / "state.md").write_text("# State\n", encoding="utf-8")
    (units / "guide.md").write_text(
        "---\nhydra_id: hydra://knowledge-unit/demo/guide\nuid: 33333333-3333-4333-8333-333333333333\n"
        "schema_version: 3\nkind: knowledge-unit\ntitle: Guide\nstatus: active\nscope: base-seed\n"
        "owners:\n  team: demo\nrelations:\n  - hydra://knowledge-package/demo\n"
        "provenance:\n  sources: []\nunit_kind: note\nquestion: What is demo?\n"
        "reads:\n  - scripts/demo.py\n  - scripts/demo.py\nrequires: []\n"
        + expansion
        + "---\n# Guide\n",
        encoding="utf-8",
    )
    external = root / "AGENTS.md"
    external.write_text(
        "Read .hydra-framework/repo/knowledge/knowledge-packages/demo/overview.md, hydra://knowledge-package/demo, and demo:use.\n",
        encoding="utf-8",
    )
    templates = root / ".hydra-framework/repo/knowledge/knowledge-packages/templates"
    templates.mkdir()
    (templates / "routing.yaml").write_text("schema: hydra-framework.package-routing.v2\n", encoding="utf-8")
    (templates / "overview.md").write_text("[Routing](routing.yaml) for a package.\n", encoding="utf-8")
    script = templates / "scripts/check.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    (templates.parent / "README.md").write_text("# Knowledge Packages\n", encoding="utf-8")
    sidecar = root / ".hydra-framework/repo/object-sidecars.yaml"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(
        "package-template-routing:\n"
        "  hydra_id: hydra://knowledge-template/package/routing\n"
        "  path: .hydra-framework/repo/knowledge/knowledge-packages/templates/routing.yaml\n",
        encoding="utf-8",
    )


class MigrationV2Tests(unittest.TestCase):
    def test_dry_run_is_deterministic_and_records_contract_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _legacy(root)
            first = migration_v2.build_plan(root, checkpoint_commit="abc")
            second = migration_v2.build_plan(root, checkpoint_commit="abc")
            self.assertEqual(first.manifest, second.manifest)
            self.assertEqual(first.manifest["status"], "planned")
            self.assertEqual(first.manifest["unresolved"], [])
            self.assertEqual(len(first.manifest["preserved_uids"]), 3)
            self.assertEqual(
                first.manifest["binding_candidates"],
                [{"source": ".hydra-framework/repo/knowledge/spaces/demo/units/guide.md", "path": "scripts/demo.py", "confidence": "candidate-only"}],
            )
            self.assertTrue(any(row["to"] == "hydra://knowledge-route/demo/use" for row in first.manifest["route_rewrites"]))
            self.assertTrue(any(row["path"] == "AGENTS.md" for row in first.manifest["reference_rewrites"]))

    def test_ambiguous_unit_expansion_is_unresolved_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _legacy(root, expansion="expand_when:\n  - when: legacy event\n    read:\n      - hydra://knowledge-unit/demo/other\n")
            plan = migration_v2.build_plan(root, checkpoint_commit="abc")
            self.assertEqual(plan.manifest["confidence"], "requires-review")
            self.assertIn("expand_when requires one owning route", plan.manifest["unresolved"][0])

    def test_apply_requires_exact_approval_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _legacy(root)
            plan = migration_v2.build_plan(root, checkpoint_commit="abc")
            with self.assertRaisesRegex(migration_v2.MigrationError, "not explicitly approved"):
                migration_v2.apply_reviewed_plan(root, plan.manifest)
            reviewed = dict(plan.manifest)
            reviewed["review"] = {
                "approved": True,
                "approved_digest": plan.manifest["plan_digest"],
                "reviewer": "fixture-reviewer",
                "evidence": "Reviewed every move and UID mapping.",
            }
            with mock.patch("hydra_engine.knowledge.migration_git.require_clean"):
                applied = migration_v2.apply_reviewed_plan(root, reviewed)
            self.assertEqual(applied.manifest["plan_digest"], plan.manifest["plan_digest"])
            self.assertFalse((root / ".hydra-framework/repo/knowledge/knowledge-packages/demo").exists())
            space = parse_yaml(root / ".hydra-framework/repo/knowledge/spaces/demo/space.yaml", root, required=True)
            self.assertEqual(space["uid"], "11111111-1111-4111-8111-111111111111")
            self.assertEqual(space["hydra_id"], "hydra://knowledge-space/demo")
            unit = markdown_frontmatter(root / ".hydra-framework/repo/knowledge/spaces/demo/units/guide.md", root)
            self.assertEqual(unit["uid"], "33333333-3333-4333-8333-333333333333")
            self.assertEqual(unit["relations"], [{"type": "relates-to", "target": "hydra://knowledge-space/demo"}])
            self.assertIn("knowledge/spaces/demo", (root / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("hydra://knowledge-route/demo/use", (root / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("[Routing](space.yaml)", (root / ".hydra-framework/repo/knowledge/spaces/demo/overview.md").read_text(encoding="utf-8"))
            self.assertTrue((root / ".hydra-framework/repo/knowledge/templates/space/space.yaml.template").is_file())
            self.assertEqual(
                (root / ".hydra-framework/repo/knowledge/templates/space/scripts/check.sh").stat().st_mode & 0o777,
                0o755,
            )
            sidecar = (root / ".hydra-framework/repo/object-sidecars.yaml").read_text(encoding="utf-8")
            self.assertIn("hydra://knowledge-template/space/routing", sidecar)
            self.assertIn("knowledge/templates/space/space.yaml.template", sidecar)
            self.assertFalse((root / ".hydra-framework/repo/knowledge/knowledge-packages").exists())
            again = migration_v2.build_plan(root, checkpoint_commit="abc")
            self.assertEqual(again.manifest["status"], "already-v3")
            self.assertEqual(again.manifest["writes"], [])

    def test_apply_rejects_changed_plan_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _legacy(root)
            plan = migration_v2.build_plan(root, checkpoint_commit="abc")
            reviewed = dict(plan.manifest)
            reviewed["review"] = {
                "approved": True, "approved_digest": plan.manifest["plan_digest"],
                "reviewer": "fixture", "evidence": "reviewed",
            }
            (root / "AGENTS.md").write_text("changed\n", encoding="utf-8")
            with mock.patch("hydra_engine.knowledge.migration_git.require_clean"):
                with self.assertRaisesRegex(migration_v2.MigrationError, "plan changed after review"):
                    migration_v2.apply_reviewed_plan(root, reviewed)
            self.assertTrue((root / ".hydra-framework/repo/knowledge/knowledge-packages/demo/routing.yaml").exists())

    def test_apply_rejects_tampered_review_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _legacy(root)
            plan = migration_v2.build_plan(root, checkpoint_commit="abc")
            reviewed = dict(plan.manifest)
            reviewed["confidence"] = "tampered"
            reviewed["review"] = {
                "approved": True,
                "approved_digest": plan.manifest["plan_digest"],
                "reviewer": "fixture",
                "evidence": "reviewed",
            }
            with self.assertRaisesRegex(migration_v2.MigrationError, "payload digest mismatch"):
                migration_v2.apply_reviewed_plan(root, reviewed)


if __name__ == "__main__":
    unittest.main()
