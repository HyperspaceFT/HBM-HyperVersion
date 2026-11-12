import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import migration
import records
from localization import EN, MAP, SOURCE_EN, SOURCE_ZH, ZH

FEATURES = 'migration/features.json'


class RecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.source, self.target = base / 'source', base / 'target'
        self.write(self.source / SOURCE_EN, 'tile.pylon.name=Pylon\ntile.old.name=Old\ntile.only_en.name=English only\n')
        self.write(self.source / SOURCE_ZH, 'tile.pylon.name=电线杆\ntile.old.name=旧\n')
        self.write(self.source / 'src/A.java', 'class A {}\n')
        subprocess.run(['git', 'init', '-q', str(self.source)], check=True)
        migration.git(self.source, 'add', '.')
        migration.git(self.source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        self.head = migration.git(self.source, 'rev-parse', 'HEAD')
        self.write(self.target / 'src/B.java', 'class B {}\n')
        self.write_json(EN, {'b.old': 'Old', 'b.pylon': 'Pylon', 'b.start': 'Wire %s', 'b.wait': 'Later'})
        self.write_json(ZH, {'b.old': '旧'})
        old = {'kind': 'upstream', 'source_en': 'Old', 'source_key': 'tile.old.name', 'source_zh': '旧', 'target_en': 'Old', 'target_zh': '旧'}
        mapping = {'schema_version': 1, 'source_commit': 'x', 'entries': {'b.old': old, 'b.wait': {'kind': 'deferred', 'reason': 'later', 'target_en': 'Later'}}}
        self.write(self.target / MAP, (json.dumps(mapping, ensure_ascii=False, indent=2) + '\n').replace('\n', '\r\n'))
        self.feature = {'id': 'cable', 'status': 'partial-unverified', 'reviewed_source_commit': 'old', 'source_paths': ['src/A.java'],
                        'target_paths': ['src/B.java'], 'source_watch': [], 'target_watch': [], 'dependencies': [], 'evidence': [],
                        'notes': ['G1：first', 'G2：second'], 'acceptance': []}
        self.write_json(FEATURES, {'schema_version': 1, 'features': [self.feature]})

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))

    def write_json(self, relative, value):
        self.write(self.target / relative, json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    def data(self, text):
        path = self.target / 'migration/b1-rows.toml'
        self.write(path, text)
        return path

    def read(self, relative):
        return json.loads((self.target / relative).read_text(encoding='utf-8'))

    def cli(self, *arguments):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = migration.main(['--source', str(self.source), '--target', str(self.target), *arguments])
        return code, out.getvalue(), err.getvalue()

    def test_localization_rows_take_the_original_text_and_keep_each_files_line_endings(self):
        rows = self.data('[upstream]\n"b.pylon" = "tile.pylon.name"\n\n[[local]]\nkey = "b.start"\nzh = "电线 %s"\nreason = "hard-coded in the original"\n')
        report = records.apply_localization(self.source, self.target, rows)
        self.assertEqual((['b.pylon', 'b.start'], [], [ZH, MAP]), (report['added'], report['changed'], report['written']))
        self.assertEqual(['b.wait'], [key for key, entry in self.read(MAP)['entries'].items() if entry['kind'] == 'deferred'])
        self.assertEqual({'b.old': '旧', 'b.pylon': '电线杆', 'b.start': '电线 %s'}, self.read(ZH))
        entries = self.read(MAP)['entries']
        self.assertEqual({'kind': 'upstream', 'source_en': 'Pylon', 'source_key': 'tile.pylon.name', 'source_zh': '电线杆', 'target_en': 'Pylon', 'target_zh': '电线杆'},
                         entries['b.pylon'])
        self.assertEqual({'kind': 'local', 'reason': 'hard-coded in the original', 'target_en': 'Wire %s', 'target_zh': '电线 %s'}, entries['b.start'])
        self.assertEqual(['b.old', 'b.pylon', 'b.start', 'b.wait'], list(entries))
        raw = (self.target / MAP).read_bytes()
        self.assertEqual(raw.count(b'\n'), raw.count(b'\r\n'))
        self.assertNotIn(b'\r\n', (self.target / ZH).read_bytes())
        again = records.apply_localization(self.source, self.target, rows)
        self.assertEqual(([], [], [], 2), (again['added'], again['changed'], again['written'], again['unchanged']))
        code, output, _ = self.cli('localization', '--apply', str(rows))
        self.assertEqual((0, True), (code, '"error": 0' in output), output)

    def test_localization_writes_nothing_when_a_row_is_wrong(self):
        before = {relative: (self.target / relative).read_bytes() for relative in (ZH, MAP)}
        cases = {'[upstream]\n"b.missing" = "tile.pylon.name"\n': 'not in',
                 '[upstream]\n"b.pylon" = "tile.only_en.name"\n': 'has no text',
                 '[upstream]\n"b.pylon" = "tile.pylon.name"\n[[local]]\nkey = "b.pylon"\nzh = "x"\nreason = "y"\n': 'listed twice',
                 '[[local]]\nkey = "b.start"\nzh = "x"\n': 'reason',
                 '[[local]]\nkey = "b.old"\nzh = "老"\nreason = "adapted"\nsource_key = "tile.old.name"\n': 'name the key in `changes`',
                 'remove = ["b.old"]\n': 'still in',
                 '[deferred]\n"b.start" = "later"\n': 'unknown tables'}
        for text, message in cases.items():
            with self.assertRaises(records.RecordError) as raised:
                records.apply_localization(self.source, self.target, self.data(text))
            self.assertIn(message, str(raised.exception))
            self.assertEqual(before, {relative: (self.target / relative).read_bytes() for relative in before})
        code, _, error = self.cli('localization', '--apply', str(self.data('[upstream]\n"b.missing" = "tile.pylon.name"\n')))
        self.assertEqual((2, True), (code, 'b.missing' in error))

    def test_localization_changes_a_named_key_resolves_a_deferral_and_removes_a_dead_key(self):
        self.write_json(EN, {'b.wait': 'Later', 'b.old': 'Old'})
        rows = self.data('changes = ["b.old", "b.wait"]\n\n[[local]]\nkey = "b.old"\nzh = "老"\nreason = "adapted"\nsource_key = "tile.old.name"\n\n'
                         '[[local]]\nkey = "b.wait"\nzh = "稍后"\nreason = "new"\n')
        report = records.apply_localization(self.source, self.target, rows)
        self.assertEqual(['b.old', 'b.wait'], report['changed'])
        self.assertEqual({'kind': 'local', 'reason': 'adapted', 'source_en': 'Old', 'source_key': 'tile.old.name', 'source_zh': '旧', 'target_en': 'Old', 'target_zh': '老'},
                         self.read(MAP)['entries']['b.old'])
        self.assertEqual({'b.old': '老', 'b.wait': '稍后'}, self.read(ZH))
        self.write_json(EN, {'b.wait': 'Later'})
        report = records.apply_localization(self.source, self.target, self.data('remove = ["b.old"]\n'))
        self.assertEqual((['b.old'], ['b.wait'], {'b.wait': '稍后'}), (report['removed'], list(self.read(MAP)['entries']), self.read(ZH)))

    def test_feature_file_adds_a_group_and_changes_another_through_the_command(self):
        rows = self.data('[[new]]\nid = "pylon"\nsource_paths = ["src/A.java"]\ntarget_paths = ["src/B.java"]\ndependencies = ["cable"]\nnotes = ["G3：new"]\n\n'
                         '[[change]]\nid = "cable"\nreviewed_source_commit = "new"\n[change.add]\nnotes = ["G3：third"]\ntarget_watch = ["src/*"]\n'
                         '[change.remove]\nnotes = ["G1：first"]\n[[change.rewrite]]\nfield = "notes"\nstarts = "G2"\ntext = "G2：second, corrected"\n')
        code, output, error = self.cli('feature', '--apply', str(rows))
        self.assertEqual(0, code, error)
        report = json.loads(output)
        self.assertEqual((['pylon'], True, 2), (report['new'], report['written'], report['features']))
        self.assertEqual({'reviewed_source_commit': 1, 'add.notes': 1, 'add.target_watch': 1, 'remove.notes': 1, 'rewrite.notes': 1}, report['changed']['cable'])
        cable, pylon = self.read(FEATURES)['features']
        self.assertEqual((['G2：second, corrected', 'G3：third'], ['src/*'], 'new'), (cable['notes'], cable['target_watch'], cable['reviewed_source_commit']))
        self.assertEqual(list(records.FEATURE_FIELDS), list(pylon))
        self.assertEqual(('partial-unverified', self.head, [], ['G3：new']), (pylon['status'], pylon['reviewed_source_commit'], pylon['acceptance'], pylon['notes']))
        code, output, _ = self.cli('feature', '--apply', str(rows))
        self.assertEqual((0, False, {}, []), (code, json.loads(output)['written'], json.loads(output)['changed'], json.loads(output)['new']))

    def test_feature_file_is_refused_whole_when_a_block_is_wrong(self):
        before = (self.target / FEATURES).read_bytes()
        new = '[[new]]\nid = "{0}"\nsource_paths = ["{1}"]\ntarget_paths = ["src/B.java"]\n'
        cases = {new.format('cable', 'src/A.java'): 'name it in `replace`',
                 new.format('pylon', 'src/Missing.java'): 'maps missing files',
                 new.format('pylon', 'src/A.java') + 'dependencies = ["nothing"]\n': 'unknown dependency',
                 new.format('pylon', 'src/A.java') + 'colour = "red"\n': 'only the fields',
                 '[[change]]\nid = "nothing"\n': 'unknown feature',
                 '[[change]]\nid = "cable"\n[change.add]\ncolour = ["red"]\n': 'holds lists named',
                 '[[change]]\nid = "cable"\n[[change.rewrite]]\nfield = "notes"\nstarts = "G"\ntext = "both"\n': 'exactly one item',
                 '[[change]]\nid = "cable"\nstatus = "done"\n': 'Unknown status',
                 'features = []\n': 'unknown tables'}
        for text, message in cases.items():
            code, _, error = self.cli('feature', '--apply', str(self.data(text)))
            self.assertEqual((2, True), (code, message in error), error)
            self.assertEqual(before, (self.target / FEATURES).read_bytes())
        code, _, error = self.cli('feature', 'cable', '--apply', str(self.data('')))
        self.assertEqual((2, True), (code, 'takes no feature IDs' in error))
        replaced = 'replace = ["cable"]\n' + new.format('cable', 'src/A.java')
        code, output, _ = self.cli('feature', '--apply', str(self.data(replaced)))
        self.assertEqual((0, ['cable'], []), (code, json.loads(output)['replaced'], self.read(FEATURES)['features'][0]['notes']))


if __name__ == '__main__':
    unittest.main()
