import copy
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import migration


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.target = self.root / 'source', self.root / 'target'
        for repo in (self.source, self.target):
            repo.mkdir()
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            (repo / 'src').mkdir()
            (repo / 'src/A.java').write_bytes(b'class A {}\n')
            self.run_git(repo, 'add', '.')
            self.run_git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                         '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        self.manifest = {'schema_version': 1, 'features': [
            {'id': 'press', 'status': 'partial-unverified', 'source_paths': ['src/A.java'],
             'target_paths': ['src/A.java'], 'source_watch': ['src/new/*'], 'dependencies': []}]}

    def run_git(self, repo, *args):
        return migration.git(repo, *args)

    def test_three_way_changes_preserve_assessment_and_baseline(self):
        baseline = migration.snapshot(self.source, self.target, self.manifest)
        original = copy.deepcopy(baseline)
        (self.source / 'src/A.java').write_text('upstream change', encoding='utf-8')
        (self.target / 'src/A.java').write_text('local adaptation', encoding='utf-8')
        result = migration.compare(baseline, self.source, self.target, self.manifest)
        self.assertEqual('both-changed-review-required', result['features'][0]['state'])
        self.assertEqual('partial-unverified', result['features'][0]['assessment'])
        self.assertEqual(original, baseline)
        self.assertEqual('local adaptation', (self.target / 'src/A.java').read_text())

    def test_new_untracked_upstream_content_and_unmapped_files_are_visible(self):
        baseline = migration.snapshot(self.source, self.target, self.manifest)
        (self.source / 'src/new').mkdir()
        (self.source / 'src/new/B.java').write_text('new', encoding='utf-8')
        (self.source / 'src/Outside.java').write_text('outside', encoding='utf-8')
        result = migration.compare(baseline, self.source, self.target, self.manifest)
        self.assertIn('src/new/B.java', result['features'][0]['source'])
        self.assertIn('src/Outside.java', result['unmapped_changes']['source'])

    def test_dependency_lock_changes_are_visible_in_target_comparison(self):
        lock = self.target / 'gradle.lockfile'
        lock.write_text('example:library:1.0=runtimeClasspath\n', encoding='utf-8')
        baseline = migration.snapshot(self.source, self.target, self.manifest)
        lock.write_text('example:library:2.0=runtimeClasspath\n', encoding='utf-8')
        result = migration.compare(baseline, self.source, self.target, self.manifest)
        self.assertIn('gradle.lockfile', result['changes']['target']['modified'])

    def test_removed_mapped_file_is_reported_not_silently_dropped(self):
        baseline = migration.snapshot(self.source, self.target, self.manifest)
        (self.source / 'src/A.java').unlink()
        result = migration.compare(baseline, self.source, self.target, self.manifest)
        self.assertEqual(['src/A.java'], result['changes']['source']['removed'])
        self.assertTrue(result['manifest_missing_files'])

    def test_old_mapping_still_detects_change_after_mapping_edit(self):
        baseline = migration.snapshot(self.source, self.target, self.manifest)
        current = copy.deepcopy(self.manifest)
        current['features'][0]['source_paths'] = []
        (self.source / 'src/A.java').write_text('changed', encoding='utf-8')
        result = migration.compare(baseline, self.source, self.target, current)
        self.assertTrue(result['features'][0]['mapping_changed'])
        self.assertEqual(['src/A.java'], result['features'][0]['source'])

    def test_upstream_change_reaches_dependent_features(self):
        self.manifest['features'].append({'id': 'generator', 'status': 'partial-unverified',
                                          'source_paths': [], 'target_paths': [], 'dependencies': ['press']})
        baseline = migration.snapshot(self.source, self.target, self.manifest)
        (self.source / 'src/A.java').write_text('changed material recipe', encoding='utf-8')
        result = migration.compare(baseline, self.source, self.target, self.manifest)
        self.assertEqual(['press'], result['features'][1]['upstream_changed_dependencies'])

    def test_dirty_snapshot_requires_explicit_opt_in(self):
        (self.source / 'src/A.java').write_text('dirty', encoding='utf-8')
        with self.assertRaises(migration.MigrationError):
            migration.snapshot(self.source, self.target, self.manifest)
        self.assertTrue(migration.snapshot(self.source, self.target, self.manifest, True)['source']['dirty_status'])

    def test_line_endings_not_behavior_change_but_binary_changes_are(self):
        old = migration.fingerprint(self.source / 'src/A.java')
        (self.source / 'src/A.java').write_bytes(b'class A {}\r\n')
        new = migration.fingerprint(self.source / 'src/A.java')
        self.assertEqual(old['sha256'], new['sha256'])
        self.assertNotEqual(old['raw_sha256'], new['raw_sha256'])
        binary = self.source / 'asset.png'
        binary.write_bytes(b'\r\n')
        first = migration.fingerprint(binary)
        binary.write_bytes(b'\n')
        self.assertNotEqual(first['sha256'], migration.fingerprint(binary)['sha256'])

    def test_no_write_outside_report_root_or_over_existing_baseline(self):
        allowed = self.target / 'migration/baselines'
        destination = allowed / 'baseline.json'
        migration.write_json({'schema_version': 1}, destination, allowed, immutable=True)
        with self.assertRaises(FileExistsError):
            migration.write_json({'changed': True}, destination, allowed, immutable=True)
        with self.assertRaises(migration.MigrationError):
            migration.write_json({}, self.source / 'oops.json', allowed)
        self.assertFalse((self.source / 'oops.json').exists())
        self.assertEqual({'schema_version': 1}, json.loads(destination.read_text()))

    def test_paths_and_dependency_cycles_rejected(self):
        for path in ('../source/file', '/absolute', 'C:/file', 'src\\file', 'src/../file'):
            with self.subTest(path=path), self.assertRaises(migration.MigrationError):
                migration.relative_path(path)
        invalid = copy.deepcopy(self.manifest)
        invalid['features'][0]['dependencies'] = ['press']
        with self.assertRaises(migration.MigrationError):
            migration.validate_manifest(invalid, self.source, self.target)

    def test_verified_requires_explicit_review_evidence(self):
        invalid = copy.deepcopy(self.manifest)
        invalid['features'][0]['status'] = 'verified'
        with self.assertRaises(migration.MigrationError):
            migration.validate_manifest(invalid, self.source, self.target)

    def test_asset_candidates_do_not_merge_same_name_different_content(self):
        old = {'src/main/resources/assets/hbm/textures/items/a.png': {'raw_sha256': 'one'}}
        new = {'src/main/resources/assets/hbmsntm/textures/item/a.png': {'raw_sha256': 'two'},
               'src/main/resources/assets/hbmsntm/textures/item/renamed.png': {'raw_sha256': 'one'}}
        row = migration.asset_candidates(old, new)['assets'][0]
        self.assertEqual('same-path-different', row['state'])
        self.assertEqual(['src/main/resources/assets/hbmsntm/textures/item/renamed.png'], row['identical_content_candidates'])

    def test_rename_is_candidate_not_suppression_of_add_remove(self):
        result = migration.changes({'a': {'sha256': 'same'}}, {'b': {'sha256': 'same'}})
        self.assertEqual(['a'], result['removed'])
        self.assertEqual(['b'], result['added'])
        self.assertEqual([{'from': 'a', 'to_candidates': ['b']}], result['same_content_move_candidates'])

    def test_audit_cli_writes_report_and_returns_error_status(self):
        output = self.target / 'build/migration/audit.json'
        result = migration.main(['--source', str(self.source), '--target', str(self.target),
                                 'audit', '--output', str(output)])
        self.assertEqual(1, result)
        report = json.loads(output.read_text())
        self.assertGreater(report['summary']['error'], 0)
        self.assertTrue(any(item['code'] == 'generated_missing' for item in report['findings']))

    def test_concurrent_checkout_edit_rejects_mixed_compare(self):
        baseline = migration.snapshot(self.source, self.target, self.manifest)
        original_inventory = migration.inventory

        def edit_after_scan(repo, **kwargs):
            result = original_inventory(repo, **kwargs)
            if repo == self.source:
                (repo / 'src/A.java').write_text('changed during scan', encoding='utf-8')
            return result

        with patch.object(migration, 'inventory', side_effect=edit_after_scan):
            with self.assertRaisesRegex(migration.MigrationError, 'changed during scan'):
                migration.compare(baseline, self.source, self.target, self.manifest)

    def test_second_edit_to_already_dirty_file_is_detected(self):
        baseline = migration.snapshot(self.source, self.target, self.manifest)
        (self.source / 'src/A.java').write_text('first dirty contents', encoding='utf-8')
        first_state = migration.checkout_state(self.source)
        original_inventory = migration.inventory

        def edit_after_scan(repo, **kwargs):
            result = original_inventory(repo, **kwargs)
            if repo == self.source:
                (repo / 'src/A.java').write_text('second dirty contents', encoding='utf-8')
            return result

        with patch.object(migration, 'inventory', side_effect=edit_after_scan):
            with self.assertRaisesRegex(migration.MigrationError, 'contents changed during scan'):
                migration.compare(baseline, self.source, self.target, self.manifest)
        self.assertEqual(first_state, migration.checkout_state(self.source))


if __name__ == '__main__':
    unittest.main()
