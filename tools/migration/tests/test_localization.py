import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "localization.py"
spec = importlib.util.spec_from_file_location("localization", MODULE)
localization = importlib.util.module_from_spec(spec)
spec.loader.exec_module(localization)


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source, self.target = root / "source", root / "target"
        self.source.mkdir()
        self.target.mkdir()
        self.mapping = {
            "schema_version": 1, "source_commit": "abc123", "entries": {
                "item.hbmsntm.old": {"kind": "upstream", "target_en": "Old %s",
                                      "target_zh": "旧 %s", "source_key": "item.old.name",
                                      "source_en": "Old %s", "source_zh": "旧 %s"},
                "item.hbmsntm.new": {"kind": "local", "target_en": "New",
                                      "target_zh": "新", "reason": "NEO-specific item"},
                "item.hbmsntm.later": {"kind": "deferred", "target_en": "Later",
                                        "reason": "Needs terminology review"}}}
        self.english = {key: entry["target_en"] for key, entry in self.mapping["entries"].items()}
        self.chinese = {key: entry["target_zh"] for key, entry in self.mapping["entries"].items()
                        if entry["kind"] != "deferred"}
        self.write(self.source, localization.SOURCE_EN, "item.old.name=Old %s\n")
        self.write(self.source, localization.SOURCE_ZH, "item.old.name=旧 %s\n")
        self.save()

    def write(self, root, relative, text):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def save(self):
        for relative, value in ((localization.MAP, self.mapping),
                                (localization.EN, self.english),
                                (localization.ZH, self.chinese)):
            self.write(self.target, relative, json.dumps(value, ensure_ascii=False))

    def audit(self):
        return localization.audit_localization(self.source, self.target)

    def codes(self):
        return [f["code"] for f in self.audit()["findings"]]

    def test_good_mapping_and_deliberate_deferral(self):
        result = self.audit()
        self.assertEqual(0, result["summary"]["error"])
        self.assertEqual(["item.hbmsntm.later"], result["deferred_keys"])
        self.assertEqual(2, result["coverage"]["translated_keys"])
        self.assertEqual(1, self.codes().count("localization_deferred"))

    def test_new_key_and_changed_existing_english(self):
        self.english["item.hbmsntm.extra"] = "Extra"
        self.english["item.hbmsntm.old"] = "Changed"
        self.save()
        self.assertIn("localization_unmapped_key", self.codes())
        self.assertIn("localization_target_english_stale", self.codes())

    def test_changed_chinese_and_upstream_values(self):
        self.chinese["item.hbmsntm.new"] = "新版"
        self.save()
        self.write(self.source, localization.SOURCE_EN, "item.old.name=Changed\n")
        self.write(self.source, localization.SOURCE_ZH, "item.old.name=改变\n")
        codes = self.codes()
        self.assertIn("localization_target_chinese_stale", codes)
        self.assertEqual(2, codes.count("localization_upstream_stale"))

    def test_duplicate_json_keys_rejected(self):
        self.write(self.target, localization.ZH, '{"x":"one","x":"two"}')
        self.assertIn("localization_file_invalid", self.codes())
        self.write(self.target, localization.MAP, '{"schema_version":1,"schema_version":1}')
        self.assertEqual(2, self.codes().count("localization_file_invalid"))

    def test_missing_files_and_malformed_schema(self):
        (self.target / localization.ZH).unlink()
        (self.source / localization.SOURCE_EN).unlink()
        self.mapping["entries"]["item.hbmsntm.new"].pop("reason")
        self.save()
        (self.target / localization.ZH).unlink()
        codes = self.codes()
        self.assertIn("localization_file_invalid", codes)
        self.assertIn("localization_schema_invalid", codes)

    def test_malformed_kind_is_reported_not_raised(self):
        for malformed in ([], {}, None):
            self.mapping["entries"]["item.hbmsntm.new"]["kind"] = malformed
            self.save()
            self.assertIn("localization_schema_invalid", self.codes())

    def test_placeholders_indexed_reordering_and_errors(self):
        entry = self.mapping["entries"]["item.hbmsntm.old"]
        entry["target_en"] = "%1$s %2$d %1$s %% 100% complete"
        entry["target_zh"] = "%2$d %1$s %1$s %% 100% complete"
        self.english["item.hbmsntm.old"] = entry["target_en"]
        self.chinese["item.hbmsntm.old"] = entry["target_zh"]
        self.save()
        self.assertNotIn("localization_placeholder_mismatch", self.codes())
        self.assertNotIn("localization_split_marker_review", self.codes())
        for bad in ("%1$s %2$s %1$s", "%1$s %2$d", "%1$s %2$d %3$s"):
            entry["target_zh"] = bad
            self.chinese["item.hbmsntm.old"] = bad
            self.save()
            self.assertIn("localization_placeholder_mismatch", self.codes())

    def test_escaped_percent_and_adjacent_numeric_format(self):
        entry = self.mapping["entries"]["item.hbmsntm.new"]
        entry["target_en"] = "Heater at 50%%; 0%d ticks"
        entry["target_zh"] = "加热到 50%%；0%d 刻"
        self.english["item.hbmsntm.new"] = entry["target_en"]
        self.chinese["item.hbmsntm.new"] = entry["target_zh"]
        self.save()
        self.assertNotIn("localization_placeholder_mismatch", self.codes())
        entry["target_zh"] = "加热到 50%；0%d 刻"
        self.chinese["item.hbmsntm.new"] = entry["target_zh"]
        self.save()
        self.assertIn("localization_placeholder_mismatch", self.codes())
        entry["target_zh"] = "加热到 50%%；0 刻"
        self.chinese["item.hbmsntm.new"] = entry["target_zh"]
        self.save()
        self.assertIn("localization_placeholder_mismatch", self.codes())

    def test_orphans_deferred_conflict_and_upstream_duplicates(self):
        self.chinese["item.hbmsntm.later"] = "later"
        self.chinese["orphan"] = "orphan"
        self.mapping["entries"]["orphan.map"] = {"kind": "deferred", "target_en": "orphan",
                                                  "reason": "old"}
        self.save()
        self.write(self.source, localization.SOURCE_EN,
                   "item.old.name=Previous\nitem.old.name=Old %s\n")
        codes = self.codes()
        self.assertIn("localization_orphan_chinese_key", codes)
        self.assertIn("localization_orphan_map_key", codes)
        self.assertIn("localization_deferred_present", codes)
        self.assertIn("localization_source_duplicate_conflict", codes)

    def test_local_upstream_provenance_and_partial_trio(self):
        entry = self.mapping["entries"]["item.hbmsntm.new"]
        entry.update(source_key="item.new.name", source_en="New upstream", source_zh="新源文")
        self.write(self.source, localization.SOURCE_EN,
                   "item.old.name=Old %s\nitem.new.name=New upstream\n")
        self.write(self.source, localization.SOURCE_ZH,
                   "item.old.name=旧 %s\nitem.new.name=新源文\n")
        self.save()
        self.assertEqual(0, self.audit()["summary"]["error"])
        self.write(self.source, localization.SOURCE_ZH,
                   "item.old.name=旧 %s\nitem.new.name=上游更新\n")
        self.assertIn("localization_upstream_stale", self.codes())
        entry.pop("source_en")
        self.save()
        self.assertIn("localization_schema_invalid", self.codes())

    def test_upstream_adaptation_must_be_local(self):
        self.mapping["entries"]["item.hbmsntm.old"]["target_zh"] = "有意改写 %s"
        self.chinese["item.hbmsntm.old"] = "有意改写 %s"
        self.save()
        self.assertIn("localization_upstream_translation_adapted", self.codes())

    def test_read_only(self):
        before = {p: p.read_bytes() for root in (self.source, self.target)
                  for p in root.rglob("*") if p.is_file()}
        self.audit()
        self.assertEqual(before, {p: p.read_bytes() for p in before})


if __name__ == "__main__":
    unittest.main()
