"""Tests of tools/migration/frozen_check.py (the final chain's frozen-name step)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import batch  # noqa: E402
import frozen_check  # noqa: E402

LIST = """# item tags
[names]
c:ingots/steel
ntm:ingots_copper

[members]
c:ores/iron hbmsntm:ore_gneiss_iron
"""


class FrozenCheckTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'migration/frozen').mkdir(parents=True)
        (self.root / 'migration/frozen/item-tags.txt').write_text(LIST, encoding='utf-8')
        self.tag('c', 'ingots/steel', ['hbmsntm:ingot_steel'])
        self.tag('ntm', 'ingots_copper', ['hbmsntm:ingot_copper'])
        self.tag('c', 'ores/iron', ['hbmsntm:ore_gneiss_iron'])
        self.tag('minecraft', 'logs', ['hbmsntm:pink_log'])  # not a namespace the list covers

    def tag(self, ns, path, values):
        target = self.root / frozen_check.GENERATED_DATA / ns / 'tags/item' / (path + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({'values': values}), encoding='utf-8')

    def problems(self):
        return frozen_check.check(self.root)[1]

    def test_a_matching_tree_passes(self):
        self.assertEqual(self.problems(), [])
        self.assertEqual(frozen_check.main(['--root', str(self.root)]), 0)

    def test_a_renamed_or_removed_name_fails(self):
        (self.root / frozen_check.GENERATED_DATA / 'c/tags/item/ingots/steel.json').rename(
            self.root / frozen_check.GENERATED_DATA / 'c/tags/item/ingots/steel_alloy.json')
        found = self.problems()
        self.assertTrue(any('c:ingots/steel is not generated' in p for p in found), found)
        self.assertTrue(any('c:ingots/steel_alloy is not in the frozen list' in p for p in found), found)

    def test_an_unlisted_new_name_fails_but_new_members_of_a_listed_name_pass(self):
        self.tag('c', 'ingots/steel', ['hbmsntm:ingot_steel', 'hbmsntm:ingot_steel_alt'])
        self.assertEqual(self.problems(), [])
        self.tag('c', 'dusts/iron', ['hbmsntm:powder_iron'])
        self.assertTrue(any('c:dusts/iron is not in the frozen list' in p for p in self.problems()))

    def test_members_of_an_existing_tag_must_match_the_list(self):
        self.tag('c', 'ores/iron', ['hbmsntm:ore_gneiss_iron', 'hbmsntm:ore_other'])
        self.assertTrue(any('does not register' in p and 'hbmsntm:ore_other' in p for p in self.problems()))
        self.tag('c', 'ores/iron', [])
        self.assertTrue(any('no longer holds' in p for p in self.problems()))

    def test_a_list_without_a_checker_or_no_list_fails(self):
        (self.root / 'migration/frozen/nbt-keys.txt').write_text('[ids]\nhbmsntm:x\n', encoding='utf-8')
        self.assertTrue(any('nbt-keys.txt: no checker' in p for p in self.problems()))
        for path in (self.root / 'migration/frozen').iterdir():
            path.unlink()
        self.assertTrue(any('no frozen lists' in p for p in self.problems()))
        self.assertEqual(frozen_check.main(['--root', str(self.root)]), 1)

    def export(self, name, text):
        target = self.root / frozen_check.EXPORT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def test_exported_lists_match_section_by_section(self):
        listed = '# ids\n[minecraft:item]\nhbmsntm:a\nhbmsntm:b\n\n[hbm:fluid_id]\n0001 WATER\n'
        for name in ('registry-ids.txt', 'block-entity-types.txt', 'config-keys.txt'):
            (self.root / 'migration/frozen' / name).write_text(listed, encoding='utf-8')
            self.export(name, '[hbm:fluid_id]\n0001 WATER\n\n[minecraft:item]\nhbmsntm:b\nhbmsntm:a\n')
        self.assertEqual(self.problems(), [])

    def test_an_exported_list_reports_renames_new_names_sections_and_a_missing_export(self):
        (self.root / 'migration/frozen/registry-ids.txt').write_text('[minecraft:item]\nhbmsntm:a\nhbmsntm:a\n\n[minecraft:fluid]\nhbmsntm:f\n', encoding='utf-8')
        found = self.problems()
        self.assertTrue(any('no export' in p and 'frozen_name_export' in p for p in found), found)
        self.export('registry-ids.txt', '[minecraft:item]\nhbmsntm:a2\n\n[minecraft:sound_event]\nhbmsntm:s\n')
        found = self.problems()
        self.assertTrue(any('[minecraft:item] hbmsntm:a is listed but not exported' in p for p in found), found)
        self.assertTrue(any('[minecraft:item] hbmsntm:a2 is exported but not listed' in p for p in found), found)
        self.assertTrue(any('[minecraft:fluid] is not exported any more' in p for p in found), found)
        self.assertTrue(any('exported [minecraft:sound_event] is not in the list' in p for p in found), found)
        self.assertTrue(any("lists ['hbmsntm:a'] more than once" in p for p in found), found)
        self.assertEqual(frozen_check.main(['--root', str(self.root)]), 1)

    def test_a_deleted_list_of_a_known_kind_fails(self):
        self.export('config-keys.txt', '[common]\ngeneral.a\n')
        found = self.problems()
        self.assertTrue(any('config-keys.txt: the list is missing' in p for p in found), found)
        (self.root / 'migration/frozen/config-keys.txt').write_text('[common]\ngeneral.a\n', encoding='utf-8')
        self.assertEqual(self.problems(), [])
        (self.root / 'migration/frozen/item-tags.txt').unlink()
        (self.root / 'migration/frozen/nbt-keys.txt').write_text('', encoding='utf-8')
        found = self.problems()
        self.assertTrue(any('item-tags.txt: the list is missing' in p for p in found), found)

    def test_a_changed_fluid_id_fails(self):
        (self.root / 'migration/frozen/registry-ids.txt').write_text('[hbm:fluid_id]\n0001 WATER\n', encoding='utf-8')
        self.export('registry-ids.txt', '[hbm:fluid_id]\n0002 WATER\n')
        found = self.problems()
        self.assertTrue(any('0001 WATER is listed but not exported' in p for p in found), found)

    def test_the_chain_runs_it_in_the_records_segment(self):
        class Fake:
            root = self.root
            source = self.root
            final = self.root / 'final'
            jar = self.root / 'build/libs/mod-1.jar'
            manifest = {'row_diff': []}

            def rel(self, path):
                return str(path)
        names = [name for name, _, _, kind in batch.chain_steps(Fake(), False)]
        kinds = {name: kind for name, _, _, kind in batch.chain_steps(Fake(), False)}
        self.assertEqual(names.index('frozen'), names.index('validate') + 1)
        self.assertEqual(kinds['frozen'], 'records')
        self.assertLess(names.index('gametest'), names.index('frozen'))


if __name__ == '__main__':
    unittest.main()
