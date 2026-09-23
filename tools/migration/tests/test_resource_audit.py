import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "resource_audit.py"
spec = importlib.util.spec_from_file_location("resource_audit", MODULE)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class ResourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "src/generated/resources").mkdir(parents=True)

    def put(self, root, name, content):
        file = self.repo / root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content if isinstance(content, bytes) else content.encode())
        return file

    def codes(self, result):
        return [item["code"] for item in result["findings"]]

    def test_missing_generated_and_invalid_json(self):
        (self.repo / "src/generated/resources").rmdir()
        self.put("src/main/resources", "data/hbmsntm/recipe/bad.json", "{")
        result = audit_module.audit_resources(self.repo)
        self.assertIn("generated_missing", self.codes(result))
        self.assertIn("json_invalid", self.codes(result))

    def test_empty_or_metadata_only_generated_is_missing(self):
        self.put("src/generated/resources", ".cache/index", "cache")
        self.put("src/generated/resources", ".migration-stamp.json", "{}")
        result = audit_module.audit_resources(self.repo)
        self.assertIn("generated_missing", self.codes(result))
        self.assertEqual(0, result["coverage"].get("source_files", 0))

    def test_repository_root_data_is_reported_and_parsed(self):
        self.put("data", "minecraft/tags/item/example.json", "{")
        result = audit_module.audit_resources(self.repo)
        self.assertIn("misplaced_root_data", self.codes(result))
        self.assertIn("json_invalid", self.codes(result))
        self.assertEqual(1, result["coverage"]["misplaced_root_data_files"])

    def test_case_sensitive_reference_even_on_windows(self):
        self.put("src/main/resources", "assets/hbmsntm/textures/block/Foo.png", b"png")
        self.put("src/main/resources", "assets/hbmsntm/models/block/x.json",
                 '{"textures":{"all":"hbmsntm:block/foo"}}')
        result = audit_module.audit_resources(self.repo)
        self.assertIn("reference_case_mismatch", self.codes(result))
        self.assertIn("invalid_resource_name", self.codes(result))

    def test_duplicate_identical_and_divergent(self):
        self.put("src/main/resources", "assets/hbmsntm/a.txt", "same")
        self.put("src/generated/resources", "assets/hbmsntm/a.txt", "same")
        self.put("src/main/resources", "data/hbmsntm/a.txt", "old")
        self.put("src/generated/resources", "data/hbmsntm/a.txt", "new")
        result = audit_module.audit_resources(self.repo)
        self.assertIn("duplicate_identical", self.codes(result))
        self.assertIn("duplicate_conflict", self.codes(result))

    def test_dynamic_external_and_vanilla_parent_not_false_missing(self):
        self.put("src/main/resources", "assets/hbmsntm/models/item/test.json",
                 json.dumps({"parent": "item/generated", "textures": {
                     "layer0": "#variable", "layer1": "other:block/stone"}}))
        result = audit_module.audit_resources(self.repo)
        self.assertNotIn("reference_unresolved", self.codes(result))
        self.assertGreater(result["coverage"]["dynamic_or_indirect_refs"], 0)
        self.assertGreater(result["coverage"]["external_refs"], 0)

    def test_unqualified_json_resources_default_to_external_minecraft(self):
        self.put("src/main/resources", "assets/hbmsntm/models/item/test.json",
                 '{"parent":"item/generated","textures":{"layer0":"item/missing"}}')
        self.put("src/main/resources", "assets/hbmsntm/blockstates/test.json",
                 '{"variants":{"":{"model":"block/missing"}}}')
        self.put("src/main/resources", "assets/hbmsntm/sounds.json",
                 '{"effect":{"sounds":["ambient/missing"]}}')
        result = audit_module.audit_resources(self.repo)
        self.assertNotIn("reference_unresolved", self.codes(result))
        self.assertGreaterEqual(result["coverage"]["external_refs"], 4)

    def test_explicit_model_path_is_not_guessed(self):
        self.put("src/main/resources", "assets/hbmsntm/models/test.json", "{}")
        self.put("src/main/resources", "assets/hbmsntm/blockstates/test.json",
                 '{"variants":{"":{"model":"hbmsntm:test"}}}')
        result = audit_module.audit_resources(self.repo)
        self.assertNotIn("reference_unresolved", self.codes(result))

    def test_java_literal_requires_closed_call_and_ignores_comments(self):
        self.put("src/main/java", "com/hbm/Render.java", '''
            // NuclearTechMod.withDefaultNamespace("textures/comment.png")
            /* new HFRWavefrontObject("models/obj/comment.obj") */
            NuclearTechMod.withDefaultNamespace("textures/partial.png" + suffix);
            ResourceLocation.fromNamespaceAndPath("hbmsntm", "textures/other.png" + suffix);
            new HFRWavefrontObject("models/obj/literal.obj");
            ''')
        result = audit_module.audit_resources(self.repo)
        unresolved = [item["reference"] for item in result["findings"]
                      if item["code"] == "reference_unresolved"]
        self.assertEqual(["models/obj/literal.obj"], unresolved)

    def test_literal_obj_and_sound_missing_are_review(self):
        self.put("src/main/java", "com/hbm/Render.java",
                 'new HFRWavefrontObject("models/obj/test.obj");')
        self.put("src/main/resources", "assets/hbmsntm/sounds.json",
                 '{"effect":{"sounds":["hbmsntm:test"]}}')
        result = audit_module.audit_resources(self.repo)
        unresolved = [item for item in result["findings"]
                      if item["code"] == "reference_unresolved"]
        self.assertEqual(2, len(unresolved))
        self.assertTrue(all(item["severity"] == "review" for item in unresolved))

    def test_jar_missing_mismatch_and_identical_duplicate(self):
        self.put("src/main/resources", "assets/hbmsntm/a.txt", "A")
        self.put("src/main/resources", "data/hbmsntm/b.txt", "B")
        self.put("src/main/resources", "assets/hbmsntm/c.txt", "C")
        jar = self.repo / "test.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            archive.writestr("assets/hbmsntm/a.txt", "A")
            archive.writestr("assets/hbmsntm/a.txt", "A")
            archive.writestr("data/hbmsntm/b.txt", "wrong")
        result = audit_module.audit_resources(self.repo, jar)
        self.assertIn("jar_duplicate_identical", self.codes(result))
        self.assertIn("jar_hash_mismatch", self.codes(result))
        self.assertIn("jar_missing", self.codes(result))

    def test_jar_unexpected_resource_and_packaged_metadata(self):
        self.put("src/main/resources", "assets/hbmsntm/expected.txt", "expected")
        jar = self.repo / "test.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            archive.writestr("assets/hbmsntm/expected.txt", "expected")
            archive.writestr("assets/hbmsntm/stale.txt", "stale")
            archive.writestr(".migration-stamp.json", "{}")
            archive.writestr("data/hbmsntm/.cache/index", "cache")
        result = audit_module.audit_resources(self.repo, jar)
        unexpected = [item for item in result["findings"]
                      if item["code"] == "jar_unexpected"]
        self.assertEqual(["assets/hbmsntm/stale.txt"],
                         [item["path"] for item in unexpected])
        self.assertTrue(all(item["severity"] == "error" for item in unexpected))
        self.assertEqual(2, self.codes(result).count("jar_metadata_artifact"))

    def test_audit_does_not_mutate_inputs(self):
        file = self.put("src/main/resources", "assets/hbmsntm/a.txt", "A")
        before = {p.relative_to(self.repo).as_posix(): p.read_bytes()
                  for p in self.repo.rglob("*") if p.is_file()}
        audit_module.audit_resources(self.repo)
        after = {p.relative_to(self.repo).as_posix(): p.read_bytes()
                 for p in self.repo.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(b"A", file.read_bytes())

    def test_chinese_file_without_map_still_runs_localization_audit(self):
        self.put("src/main/resources", "assets/hbmsntm/lang/zh_cn.json", "{}")
        self.assertIn("localization_file_invalid", self.codes(audit_module.audit_resources(self.repo)))

    def test_localization_source_override(self):
        self.put("migration", "localization/zh_cn-map.json",
                 '{"schema_version":1,"source_commit":"x","entries":{}}')
        self.put("src/main/resources", "assets/hbmsntm/lang/zh_cn.json", "{}")
        self.put("src/generated/resources", "assets/hbmsntm/lang/en_us.json", "{}")
        upstream = self.repo / "custom-original"
        for name in ("en_US.lang", "zh_CN.lang"):
            path = upstream / "src/main/resources/assets/hbm/lang" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
        overridden = audit_module.audit_resources(self.repo, localization_source=upstream)
        self.assertNotIn("localization_file_invalid", self.codes(overridden))
        defaulted = audit_module.audit_resources(self.repo)
        self.assertIn("localization_file_invalid", self.codes(defaulted))


if __name__ == "__main__":
    unittest.main()
