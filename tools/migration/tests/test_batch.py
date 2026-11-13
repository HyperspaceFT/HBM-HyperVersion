import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import batch
import migration

JAVA = 'src/main/java/com/hbm/'
MANIFEST = '''batch = "b1"
previous = "p0"
task_book = "migration/GOALB1.md"
source_head = "{source_head}"
start_head = "{start_head}"
snapshot = "migration/baselines/review-x.json"
records = ["migration/LOG.md", "migration/features.json"]
names_package = ["migration/LOG.md"]
gametests_new = ["src/main/java/com/hbm/gametest/NewTests.java"]
{extra}
[carried]
{carried}
[groups]
machine = ["src/main/java/com/hbm/B.java", "src/generated/resources/*model_b*"]
'''
HAS_BIRTHTIME = hasattr(os.stat_result, 'st_birthtime')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.source, self.root = base / 'source', base / 'target'
        self.write(self.source / 'src/A.java', 'class A {}\n')
        self.commit(self.source)
        self.write(self.root / '.gitignore', 'build/\nmigration/\n')
        self.write(self.root / 'gradle.properties', 'mod_id=mod\nmod_version=1\n')
        self.write(self.root / JAVA / 'A.java', 'class A {}\n')
        self.write(self.root / JAVA / 'gametest/OldTests.java', 'class OldTests {\n    @GameTest(template = "x")\n    void a() {}\n}\n')
        self.write(self.root / batch.ZH, json.dumps({'k': '甲'}, ensure_ascii=False))
        self.write(self.root / batch.EN, json.dumps({'k': 'A'}))
        self.write(self.root / batch.STAMP, '{}')
        self.commit(self.root)
        self.source_head = migration.git(self.source, 'rev-parse', 'HEAD')
        self.start_head = migration.git(self.root, 'rev-parse', 'HEAD')
        feature = {'id': 'all', 'status': 'partial-unverified', 'source_paths': ['src/A.java'], 'target_paths': [JAVA + 'A.java'],
                   'target_watch': ['src/*', 'gradle.properties'], 'dependencies': [], 'evidence': [], 'acceptance': []}
        self.write_json('migration/features.json', {'schema_version': 1, 'features': [feature]})
        self.write_json(batch.ZH_MAP, {'entries': {'k': {'kind': 'local'}}})
        self.write(self.root / 'migration/LOG.md', 'log\n')
        self.write(self.root / 'migration/GOALB1.md', '# B1\n')
        self.write_json('migration/baselines/review-x.json', {'schema_version': 1, 'kind': 'observed-snapshot-not-parity-acceptance',
                                                              'source': {'commit': self.source_head, 'dirty_status': ''}})
        # The previous package p0: built from the committed tree, with a start that is that tree.
        self.build()
        release = self.root / 'build/migration/releases/p0'
        release.mkdir(parents=True)
        jar = release / 'mod-1-p0.jar'
        jar.write_bytes((self.root / 'build/libs/mod-1.jar').read_bytes())
        self.write_json('build/migration/p0/baseline.json', {'files': batch.tree_hashes(self.root)})
        self.write_json('build/migration/releases/p0/release.json', {'sha256': sha(jar), 'actual_start': 'build/migration/p0/baseline.json',
                                                                    'changed_files': [], 'audits': {}})
        (release / 'SHA256SUMS.txt').write_bytes(f'{sha(jar)}  {jar.name}\n'.encode('ascii'))

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))

    def write_json(self, relative, value):
        self.write(self.root / relative, json.dumps(value, ensure_ascii=False, indent=1) + '\n')

    def commit(self, repo):
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        migration.git(repo, 'add', '.')
        migration.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')

    def manifest(self, carried='', extra=''):
        self.write(self.root / 'migration/b1-batch.toml', MANIFEST.format(source_head=self.source_head, start_head=self.start_head, carried=carried, extra=extra))
        return batch.Batch(self.root, self.source, 'b1')

    def build(self):
        """What runData and build leave: the stamp, the compiled classes, the processed resources and the JAR."""
        root, old = self.root, time.time() - 30
        java = sorted((root / batch.SRC).rglob('*.java'))
        generated = sorted(p for p in (root / batch.GENERATED).rglob('*') if p.is_file() and p.name != '.migration-stamp.json')
        stamp = {'inputs': {p.relative_to(root).as_posix(): batch.stamp_sha(p) for p in java if 'gametest' not in p.parts},
                 'generated': {p.relative_to(root / batch.GENERATED).as_posix(): batch.stamp_sha(p) for p in generated}}
        self.write_json(batch.STAMP, stamp)
        for tree in ('build/classes', 'build/resources'):
            for path in sorted((root / tree).rglob('*'), reverse=True):
                path.unlink() if path.is_file() else path.rmdir()
        entries = {'META-INF/MANIFEST.MF': b'Manifest-Version: 1.0\n'}
        for path in java:
            name = path.relative_to(root / batch.SRC).with_suffix('.class').as_posix()
            entries[name] = b'CLASS:' + path.read_bytes()
            self.write(root / 'build/classes/java/main' / name, '')
            (root / 'build/classes/java/main' / name).write_bytes(entries[name])
        for tree in (batch.RES, batch.GENERATED):
            for path in sorted(p for p in (root / tree).rglob('*') if p.is_file() and p.name != '.migration-stamp.json'):
                name = path.relative_to(root / tree).as_posix()
                entries[name] = path.read_bytes()
                self.write(root / 'build/resources/main' / name, '')
                (root / 'build/resources/main' / name).write_bytes(entries[name])
        (root / 'build/libs').mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(root / 'build/libs/mod-1.jar', 'w') as jar:
            for name, data in entries.items():
                jar.writestr(name, data)
        for tree in ('src',):
            for path in (root / tree).rglob('*'):
                os.utime(path, (old, old))

    def evidence(self, item, tests):
        final = item.final
        final.mkdir(parents=True, exist_ok=True)
        names = batch.required_chain(item, False)
        (final / 'chain-exits.txt').write_text(''.join(f'{name}=0\n' for name in names), encoding='utf-8')
        (final / 'chain-done.txt').write_text('done\n', encoding='utf-8')
        for _, log, _, _ in batch.chain_steps(item, False):
            (final / log).write_text('BUILD SUCCESSFUL\n', encoding='utf-8')
        (final / 'gametest.log').unlink()
        (final / 'gametest.log').write_text(f'[hbm-b1] wires passed\nAll {tests} required tests passed\nBUILD SUCCESSFUL\n', encoding='utf-8')
        for _, _, output in batch.RECORD_STEPS:
            if output:
                (final / output).write_text(json.dumps({'findings': [], 'summary': {'error': 0, 'warning': 0}}), encoding='utf-8')
        (final / 'jar.sha256').write_text(f'{sha(item.jar)}  build/libs/mod-1.jar\n', encoding='utf-8')

    def run_step(self, function, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = function(*args)
        return code, output.getvalue()

    def deliver(self, item):
        """The batch's own changes: a new class, a new GameTest class, a generated model, one language key and the records."""
        self.write(self.root / JAVA / 'B.java', 'class B {}\n')
        self.write(self.root / JAVA / 'gametest/NewTests.java',
                   'class NewTests {\n    String TAG = "[hbm-b1]";\n    @GameTest(template = "x")\n    void wires() { passed("wires"); }\n}\n')
        self.write(self.root / batch.GENERATED / 'assets/hbmsntm/models/model_b.json', '{}')
        self.write(self.root / batch.ZH, json.dumps({'k': '甲', 'n': '乙'}, ensure_ascii=False))
        self.write(self.root / batch.EN, json.dumps({'k': 'A', 'n': 'B'}))
        self.write_json(batch.ZH_MAP, {'entries': {'k': {'kind': 'local'}, 'n': {'kind': 'local'}}})
        self.write(self.root / 'migration/LOG.md', f'{item.release_name} delivered\nlog\n')
        self.write(self.root / 'migration/GOALB1.md', '# B1\n\n## 交付记录\n')
        features = json.loads((self.root / 'migration/features.json').read_text(encoding='utf-8'))
        features['features'][0]['evidence'].append('migration/GOALB1.md')
        self.write_json('migration/features.json', features)

    def test_freeze_needs_every_change_since_the_previous_package_attributed(self):
        self.write(self.root / JAVA / 'A.java', 'class A { int fixed; }\n')
        code, output = self.run_step(batch.cmd_freeze, self.manifest(), False)
        self.assertEqual(1, code)
        self.assertIn(JAVA + 'A.java', json.loads(output)['delta_against_previous_delivery'])
        self.assertFalse((self.root / 'build/migration/b1/baseline.json').exists())
        item = self.manifest(carried=f'"small fix" = ["{JAVA}A.java"]')
        code, _ = self.run_step(batch.cmd_freeze, item, False)
        self.assertEqual(0, code)
        base = json.loads((item.out / 'baseline.json').read_text(encoding='utf-8'))
        self.assertEqual([JAVA + 'A.java'], sorted(base['carried']['hashes']))
        self.assertIn(JAVA + 'A.java', base['copied'])
        self.assertEqual(b'class A { int fixed; }\n', (item.start_files / JAVA / 'A.java').read_bytes())
        with self.assertRaises(migration.MigrationError):
            self.run_step(batch.cmd_freeze, item, False)

    @unittest.skipUnless(HAS_BIRTHTIME, 'the GameTest log check needs a file creation time')
    def test_package_owns_every_change_and_attributes_the_jar_delta(self):
        self.write(self.root / JAVA / 'A.java', 'class A { int fixed; }\n')
        item = self.manifest(carried=f'"small fix" = ["{JAVA}A.java"]')
        self.assertEqual(0, self.run_step(batch.cmd_freeze, item, False)[0])
        self.deliver(item)
        self.write(self.root / JAVA / 'Stray.java', 'class Stray {}\n')
        self.build()
        self.evidence(item, 2)
        code, output = self.run_step(batch.cmd_package, item, True, None)
        self.assertEqual(1, code)
        self.assertIn('FAILURE: paths changed since the start that the manifest does not own', output)
        self.assertIn('Stray.java', output)
        self.assertFalse(item.release.exists())
        with self.assertRaises(migration.MigrationError):
            self.run_step(batch.cmd_package, item, False, None)

        (self.root / JAVA / 'Stray.java').unlink()
        self.build()
        self.evidence(item, 2)
        code, output = self.run_step(batch.cmd_package, item, True, None)
        self.assertEqual((0, True), (code, 'Check passed; nothing written. Pending: none. Failures: none' in output), output)
        self.assertEqual(0, self.run_step(batch.cmd_package, item, False, None)[0])
        receipt = json.loads((item.release / 'release.json').read_text(encoding='utf-8'))
        self.assertEqual(sha(item.jar), receipt['sha256'])
        self.assertEqual(f'{receipt["sha256"]}  mod-1-b1.jar\n', (item.release / 'SHA256SUMS.txt').read_text(encoding='ascii'))
        owners = {name: entry['owners'] for name, entry in receipt['jar_delta_owners'].items()}
        self.assertEqual(['b1'], owners['com/hbm/B.class'])
        self.assertEqual(['carried'], owners['com/hbm/A.class'])
        self.assertEqual(['b1'], owners['assets/hbmsntm/models/model_b.json'])
        self.assertEqual({JAVA + 'gametest/NewTests.java': 1}, receipt['gametest']['added_tests_by_file'])
        self.assertEqual(['n'], receipt['language']['delta']['en_us']['added'])
        kinds = {change['path']: change['group'] for change in receipt['changed_files']}
        self.assertEqual('production-new', kinds[JAVA + 'B.java'])
        self.assertEqual('gametest-new', kinds[JAVA + 'gametest/NewTests.java'])
        self.assertNotIn(JAVA + 'A.java', kinds)

        code, output = self.run_step(batch.cmd_verify_delivery, item)
        self.assertEqual((0, []), (code, json.loads(output.split('\nPaths changed')[0])['changed_after_the_package']))
        self.write(self.root / JAVA / 'B.java', 'class B { int later; }\n')
        _, output = self.run_step(batch.cmd_verify_delivery, item)
        self.assertEqual([JAVA + 'B.java'], json.loads(output.split('\nPaths changed')[0])['changed_after_the_package'])

    def test_changed_existing_gametest_needs_a_reason_in_the_manifest(self):
        item = self.manifest()
        self.assertEqual(0, self.run_step(batch.cmd_freeze, item, False)[0])
        self.write(self.root / JAVA / 'gametest/OldTests.java', 'class OldTests {\n    @GameTest(template = "y")\n    void a() {}\n}\n')
        _, output = self.run_step(batch.cmd_package, item, True, None)
        self.assertIn('gametest/OldTests.java', output.split('FAILURE: paths changed since the start')[1].splitlines()[0])
        item = self.manifest(extra=f'[gametests_changed]\n"{JAVA}gametest/OldTests.java" = "template renamed"\n')
        _, output = self.run_step(batch.cmd_package, item, True, None)
        self.assertNotIn('FAILURE: paths changed since the start', output)
        with self.assertRaises(migration.MigrationError):
            self.manifest(extra=f'[gametests_changed]\n"{JAVA}gametest/OldTests.java" = ""\n')

    def test_modified_file_keeps_its_line_ending_style(self):
        item = self.manifest()
        self.assertEqual(0, self.run_step(batch.cmd_freeze, item, False)[0])
        self.write(self.root / 'migration/LOG.md', 'b1\r\nlog\n')
        _, output = self.run_step(batch.cmd_package, item, True, None)
        self.assertIn('FAILURE: line endings differ from the start style: migration/LOG.md', output)

    def test_imported_asset_keeps_the_original_crlf(self):
        item = self.manifest()
        self.assertEqual(0, self.run_step(batch.cmd_freeze, item, False)[0])
        source = 'src/main/resources/assets/hbm/textures/blocks/belt.png.mcmeta'
        target = 'src/main/resources/assets/hbmsntm/textures/block/belt.png.mcmeta'
        (self.source / source).parent.mkdir(parents=True, exist_ok=True)
        (self.source / source).write_bytes(b'{\r\n"animation": {}\r\n}')
        (self.root / target).parent.mkdir(parents=True, exist_ok=True)
        (self.root / target).write_bytes(b'{\r\n"animation": {}\r\n}')
        self.write(self.root / 'migration/b1-resource-ownership.json',
                   json.dumps({'imported_assets': [{'source_path': source, 'target_path': target}]}))
        self.write(self.root / 'migration/notes.mcmeta', '{\r\n}\n')
        _, output = self.run_step(batch.cmd_package, item, True, None)
        eol = [line for line in output.splitlines() if 'line endings differ' in line]
        self.assertTrue(eol and 'migration/notes.mcmeta' in eol[0], output)
        self.assertNotIn('belt.png.mcmeta', eol[0])

    def test_chain_order_tail_reruns_and_gradle_failure(self):
        item = self.manifest()
        self.assertEqual(0, self.run_step(batch.cmd_freeze, item, False)[0])
        calls = []

        def runner(command, log, cwd):
            calls.append(log.name)
            log.write_text('', encoding='utf-8')
            return 0

        with patch.object(batch, 'run_logged', runner):
            self.assertEqual(0, self.run_step(batch.cmd_chain, item, 'runData')[0])
        suites = [f'suite-{name}.log' for name, _ in batch.EVERGREEN_SUITES]
        self.assertEqual(['rundata.log', 'gametest.log', 'build.log', 'localization.log', 'resources-audit.log', 'packaged-resources.log', 'validate.log'] + suites, calls)
        self.assertEqual(batch.required_chain(item, False), list(batch.read_exits(item.final / 'chain-exits.txt')))
        self.assertTrue((item.final / 'chain-done.txt').is_file())
        self.assertEqual(sha(item.jar), (item.final / 'jar.sha256').read_text(encoding='utf-8').split()[0])

        calls.clear()
        with patch.object(batch, 'run_logged', runner):
            self.assertEqual(0, self.run_step(batch.cmd_chain, item, 'records')[0])
        self.assertEqual(['localization.log', 'resources-audit.log', 'packaged-resources.log', 'validate.log'], calls)
        self.assertEqual(batch.required_chain(item, False), list(batch.read_exits(item.final / 'chain-exits.txt')))

        calls.clear()
        with patch.object(batch, 'run_logged', lambda command, log, cwd: calls.append(log.name) or (1 if log.name == 'gametest.log' else 0)):
            self.assertEqual(1, self.run_step(batch.cmd_chain, item, 'runData')[0])
        self.assertEqual(['rundata.log', 'gametest.log'], calls)
        self.assertFalse((item.final / 'chain-done.txt').exists())
        self.assertEqual({'runData': '0', 'gametest': '1'}, batch.read_exits(item.final / 'chain-exits.txt'))

    def test_chain_and_compare_refuse_a_work_dir_migration_py_cannot_write_to(self):
        self.manifest()
        outside = batch.Batch(self.root, self.source, 'b1', work_dir=Path(self.temp.name) / 'elsewhere')
        calls = []
        with patch.object(batch, 'run_logged', lambda command, log, cwd: calls.append(log.name) or 0):
            for step in ((batch.cmd_chain, 'runData'), (batch.cmd_compare,)):
                with self.assertRaises(migration.MigrationError):
                    self.run_step(step[0], outside, *step[1:])
        self.assertEqual([], calls)
        self.assertFalse(outside.out.exists())

    def test_example_manifest_is_valid(self):
        manifest = batch.load_manifest(Path(batch.TOOLS) / 'batch.example.toml', 'goal31a')
        self.assertEqual('goal30c', manifest['previous'])
        self.assertEqual(sorted(batch.MANIFEST_DEFAULTS), sorted(set(manifest) - set(batch.MANIFEST_REQUIRED)))

    def test_manifest_rejects_unknown_keys_and_patterns_outside_groups(self):
        with self.assertRaises(migration.MigrationError):
            self.manifest(extra='recrods = []\n')
        with self.assertRaises(migration.MigrationError):
            self.manifest(carried='"fix" = ["src/*"]')


if __name__ == '__main__':
    unittest.main()
