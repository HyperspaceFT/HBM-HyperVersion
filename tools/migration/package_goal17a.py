"""Package Goal17A against its frozen start while preserving all earlier releases."""
from pathlib import Path
import difflib
import json
import shutil
import subprocess
import zipfile

from verify_goal17a_resources import (
    ASSETS, EXPECTED_INPUTS, GENERATED_CHANGED, GENERATED_NEW, JAVA, OPTIONAL_INPUTS,
    OUT, ROOT, SOURCE, read, sha, verify,
)


RELEASE = ROOT / 'build/migration/releases/goal17a'
JAR = ROOT / 'build/libs/hbmsntm-198A.jar'
PREVIOUS = ROOT / 'build/migration/releases/goal16b/hbmsntm-198A-goal16b.jar'
REPORTS = [
    'migration/GOAL17A.md',
    'migration/GOAL17A-ACCEPTANCE.md',
    'migration/goal17a-static-review.md',
    'build/migration/goal17a/verification.json',
]
RECORDS = {
    'migration/GOAL17A.md',
    'migration/GOAL17A-ACCEPTANCE.md',
    'migration/goal17a-static-review.md',
    'migration/goal17a-materials-review.json',
    'migration/goal17a-finite-accounting.json',
    'migration/goal17a-resource-ownership.json',
    'migration/goal17a-localization-review.json',
    'migration/README.md',
    'migration/UPSTREAM-REVIEWS.md',
    'migration/features.json',
    'migration/LOCALIZATION.md',
    'migration/localization/zh_cn-map.json',
    'migration/RESOURCE-OWNERSHIP.md',
    'tools/migration/verify_goal17a_acquisition.py',
    'tools/migration/goal17a_regression/acquisition_stubs.py',
    'tools/migration/goal17a_regression/Goal17AAcquisitionRegression.java',
    'tools/migration/goal17a_regression/README.md',
    'tools/migration/verify_goal17a_resources.py',
    'tools/migration/package_goal17a.py',
    'src/generated/resources/.migration-stamp.json',
}
AUDITS = ('localization-audit.json', 'resources-audit.json', 'packaged-resources.json')
JAVA_INPUTS = {'src/main/java/' + name + '.java' for name in JAVA}
ASSET_INPUTS = {target for _, target in ASSETS}
ZH_INPUT = 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'
ALLOWED_INPUTS = JAVA_INPUTS | ASSET_INPUTS | {ZH_INPUT}
ALLOWED_CHANGED_INPUTS = ALLOWED_INPUTS
REQUIRED_CHANGED_INPUTS = ALLOWED_CHANGED_INPUTS - OPTIONAL_INPUTS
GENERATED_RESOURCE_PATHS = GENERATED_NEW | GENERATED_CHANGED


def git(repo, *args):
    return subprocess.check_output(
        ['git', '-c', 'safe.directory=' + repo.as_posix(), *args], cwd=repo
    ).decode('utf-8')


def changed_class(name):
    return any(
        name == source + '.class'
        or (name.startswith(source + '$') and name.endswith('.class'))
        for source in JAVA
    )


def resolve_path(value, default_root=ROOT):
    value = str(value).replace('\\', '/')
    path = Path(value)
    if path.is_absolute():
        return path
    if value.startswith(('src/', 'tools/', 'build/', 'migration/', '.gradle/')):
        return ROOT / value
    return default_root / value


def resolve_verified_file(value, default_root=ROOT):
    name = str(value).replace('\\', '/')
    candidates = [resolve_path(name, default_root)]
    if not name.startswith(('src/', 'tools/', 'build/', 'migration/', '.gradle/')):
        candidates.extend((ROOT / 'src/main/java' / name, ROOT / name))
    return next((path for path in candidates if path.is_file()), candidates[0])


def verify_hash_map(values, label, default_root=ROOT):
    assert isinstance(values, dict) and values, 'Missing hash map: ' + label
    for name, digest in values.items():
        path = resolve_verified_file(name, default_root)
        assert isinstance(digest, str) and len(digest) == 64, (label, name, digest)
        assert path.is_file() and sha(path) == digest, f'Changed verified input: {label}: {name}'


def verify_source_report(path):
    record = read(path)
    source_maps = []
    for key in (
        'source_sha256', 'source_hashes', 'production_sha256', 'source_inputs_sha256',
        'extracted_input_sha256', 'extracted_source_sha256', 'compiled_input_sha256',
    ):
        values = record.get(key)
        if isinstance(values, dict) and values:
            verify_hash_map(values, str(path) + ':' + key)
            source_maps.append(key)
    for world_name, world in record.get('worlds', {}).items():
        if not isinstance(world, dict):
            continue
        for key in ('production_sha256', 'source_sha256', 'source_hashes'):
            values = world.get(key)
            if isinstance(values, dict) and values:
                verify_hash_map(values, f'{path}:worlds.{world_name}.{key}')
                source_maps.append(f'worlds.{world_name}.{key}')
    assert source_maps, f'Missing final source provenance: {path}'

    for key in ('fixture_sha256', 'fixtures_sha256', 'adapter_sha256', 'imported_generator_sha256',
                'cache_sha256', 'java_sha256', 'generated_input_sha256'):
        values = record.get(key)
        if isinstance(values, dict) and values:
            verify_hash_map(values, str(path) + ':' + key)
    if isinstance(record.get('fixture_sha256'), str):
        fixture = ROOT / 'tools/migration/goal17a_regression/Goal17AAcquisitionRegression.java'
        assert sha(fixture) == record['fixture_sha256'], f'Changed checked fixture: {path}'

    cached = record.get('cached_inputs', record.get('cache'))
    if cached is not None or 'acquisition' in path.parts:
        assert isinstance(cached, dict), f'Malformed cached input evidence: {path}'
        for name in ('java', 'javac', 'gson'):
            digest = cached.get(name + '_sha256')
            if name == 'javac':
                version_records = cached.get('versions')
                assert isinstance(version_records, list), f'Missing cached javac version records: {path}'
                versions = [
                    item for item in cached.get('versions', [])
                    if item.get('label') == 'javac -version'
                ]
                assert len(versions) == 1, f'Expected exactly one javac version record: {path}'
                version = versions[0]
                assert version.get('returncode') == 0, f'javac version check failed: {path}'
                file_path = version.get('path')
            else:
                file_path = cached.get(name)
            assert file_path is not None and digest is not None, f'Incomplete cached input evidence: {path}: {name}'
            assert Path(file_path).is_file() and sha(Path(file_path)) == digest, \
                f'Changed cached verification input: {path}: {name}'

    stubs = record.get('generated_stub_sha256', {})
    if stubs:
        assert isinstance(stubs, dict), f'Malformed generated-stub hashes: {path}'
        for name, digest in stubs.items():
            candidates = [resolve_path(name), resolve_path(name, path.parent)]
            candidate = next((item for item in candidates if item.is_file()), None)
            assert candidate is not None and sha(candidate) == digest, f'Changed generated stub: {path}: {name}'

    commands = record.get('commands')
    if path.name != 'resource-verification.json':
        assert isinstance(commands, list) and commands, f'Missing executed check results: {path}'
    if commands is not None:
        assert isinstance(commands, list), f'Malformed command results: {path}'
        for command in commands:
            assert isinstance(command, dict), f'Malformed command result: {path}'
            code = command.get('returncode', command.get('exit'))
            assert code == 0, f'Failed final check recorded in {path}: {command}'
    if 'returncode' in record:
        assert record['returncode'] == 0, f'Failed report: {path}'
    if 'failures' in record:
        assert not record['failures'], f'Unresolved report failures: {path}'
    if 'source_stable_after_run' in record:
        assert record['source_stable_after_run'], f'Source changed during checks: {path}'
    if 'source_stable' in record:
        assert record['source_stable'], f'Source changed during checks: {path}'
    if path.name == 'resource-verification.json':
        assert record.get('checks') == len(record.get('passed', [])) and not record.get('failures'), path
    return record


def verify_audit(name):
    report = read(OUT / name)
    findings = report.get('findings')
    assert isinstance(findings, list), f'Malformed audit findings: {name}'
    problems = [item for item in findings if item.get('severity', '').lower() in ('error', 'warning')]
    assert not problems, f'Audit has errors or warnings: {name}: {problems}'
    return report


def main():
    baseline = read(OUT / 'baseline.json')
    original = SOURCE
    assert git(original, 'rev-parse', 'HEAD').strip() == baseline['source_head'], 'Original HEAD changed'
    assert git(original, 'status', '--porcelain=v1', '--untracked-files=all') == baseline['source_status'] == '', \
        'Original source worktree changed'
    assert git(ROOT, 'rev-parse', 'HEAD').strip() == baseline['target_head'], 'NEO start commit changed'
    assert sha(PREVIOUS) == baseline['base_release_sha256'], 'Goal16B base JAR changed'
    assert all(sha(ROOT / path) == digest for path, digest in baseline['old_releases'].items()), \
        'A prior release JAR changed'
    assert all(sha(ROOT / path) == digest for path, digest in baseline['old_release_files'].items()), \
        'A prior release file or receipt changed'
    assert all(sha(ROOT / path) == baseline['files'][path]
               for path in baseline['preserved_g6_g12_files']), 'A G6-G12 repair file changed'
    assert sha(ROOT / 'tools/migration/package_goal15a.py') == baseline['files']['tools/migration/package_goal15a.py'], \
        'Corrected Goal15A packager changed'
    goal15a = read(ROOT / 'build/migration/releases/goal15a/release.json')
    assert goal15a['reports'][:2] == ['migration/GOAL15A.md', 'migration/GOAL15A-ACCEPTANCE.md'], \
        'Corrected Goal15A receipt index changed'
    assert sha(ROOT / 'migration/GOAL17.md') == baseline['files']['migration/GOAL17.md'], \
        'Frozen Goal17 preparation record changed'

    resource_result = verify()
    verification = read(OUT / 'verification.json')
    verified_reports = verification.get('source_verified_reports')
    assert isinstance(verified_reports, list) and verified_reports, 'Missing source-verified report index'
    evidence_hashes = verification.get('evidence_sha256')
    assert isinstance(evidence_hashes, dict) and evidence_hashes, 'Missing final evidence hashes'
    for name, digest in evidence_hashes.items():
        path = resolve_path(name)
        assert path.is_file() and sha(path) == digest, f'Final evidence changed or missing: {name}'
    for name in verified_reports:
        assert name in evidence_hashes, f'Source report missing from evidence hash map: {name}'
        verify_source_report(ROOT / name)

    for name in AUDITS:
        verify_audit(name)
    for name in ('runData.log', 'build.log'):
        log = OUT / name
        assert log.is_file() and 'BUILD SUCCESSFUL' in log.read_text(encoding='utf-8-sig'), \
            f'Missing successful offline {name}'
    for name in REPORTS:
        assert (ROOT / name).is_file(), f'Missing delivery report: {name}'

    stamp = read(ROOT / 'src/generated/resources/.migration-stamp.json')
    with zipfile.ZipFile(JAR) as current, zipfile.ZipFile(PREVIOUS) as prior:
        names = current.namelist()
        assert len(names) == len(set(names)), 'Duplicate JAR entries'
        assert not any(
            name.startswith(('tools/', 'migration/')) or '/.cache/' in name or '.migration-stamp' in name
            for name in names
        ), 'Migration or local build metadata leaked into the JAR'
        for name in stamp['generated']:
            assert current.read(name) == (ROOT / 'src/generated/resources' / name).read_bytes(), \
                f'Generated resource differs inside JAR: {name}'
        for _, target in ASSETS:
            rel = target.split('/assets/hbmsntm/', 1)[1]
            entry = 'assets/hbmsntm/' + rel
            assert current.read(entry) == (ROOT / target).read_bytes(), f'Owned texture differs inside JAR: {entry}'
        zh_entry = 'assets/hbmsntm/lang/zh_cn.json'
        assert current.read(zh_entry) == (ROOT / ZH_INPUT).read_bytes(), 'Chinese language source differs inside JAR'
        for source in JAVA:
            assert source + '.class' in names, f'Missing compiled class: {source}'
        classes_root = ROOT / 'build/classes/java/main'
        compiled_classes = sorted(classes_root.rglob('*.class'))
        assert compiled_classes, 'No compiled classes found in the final build output'
        for compiled in compiled_classes:
            name = compiled.relative_to(classes_root).as_posix()
            assert name in names and current.read(name) == compiled.read_bytes(), \
                f'JAR class differs from final compiled output: {name}'
        for name in names:
            if changed_class(name):
                compiled = ROOT / 'build/classes/java/main' / name
                assert compiled.is_file() and current.read(name) == compiled.read_bytes(), \
                    f'JAR class differs from final compiled class: {name}'

        for rel in (
            'data/hbmsntm/recipe/43.json',
            'data/hbmsntm/recipe/45.json',
        ):
            assert current.read(rel) == (ROOT / 'src/generated/resources' / rel).read_bytes(), \
                f'Frozen recipe differs inside final JAR: {rel}'
            assert prior.read(rel) == current.read(rel), f'Prior recipe changed in JAR: {rel}'

        old_files = {item.filename for item in prior.infolist() if not item.is_dir()}
        new_files = {item.filename for item in current.infolist() if not item.is_dir()}
        jar_delta = {
            'added': sorted(new_files - old_files),
            'removed': sorted(old_files - new_files),
            'modified': sorted(name for name in old_files & new_files if prior.read(name) != current.read(name)),
        }
        old_dirs = {item.filename for item in prior.infolist() if item.is_dir()}
        new_dirs = {item.filename for item in current.infolist() if item.is_dir()}
        directory_delta = {
            'added': sorted(new_dirs - old_dirs),
            'removed': sorted(old_dirs - new_dirs),
        }
    allowed_resources = GENERATED_RESOURCE_PATHS | {zh_entry}
    allowed_resources |= {
        'assets/hbmsntm/' + target.split('/assets/hbmsntm/', 1)[1] for _, target in ASSETS
    }
    assert not jar_delta['removed'] and not directory_delta['removed'], (jar_delta, directory_delta)
    assert all(changed_class(name) or name in allowed_resources
               for entries in jar_delta.values() for name in entries), jar_delta

    # Compare all tracked and non-ignored worktree files to the actual frozen Goal17A start.
    current_names = {
        name for name in git(ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0')
        if name
    }
    allowed_delta = ALLOWED_INPUTS | RECORDS | {
        'src/generated/resources/' + name for name in GENERATED_RESOURCE_PATHS
    }
    changes = []
    diffs = []
    for name in sorted(current_names | baseline['files'].keys()):
        path = ROOT / name
        before = baseline['files'].get(name)
        after = sha(path) if path.is_file() else None
        if before == after:
            continue
        assert name in allowed_delta, f'Unassigned path changed from frozen start: {name}'
        assert after is not None, f'Unexpected deletion from frozen start: {name}'
        changes.append({
            'path': name,
            'status': 'added' if before is None else 'modified',
            'before_sha256': before,
            'after_sha256': after,
        })
        before_path = OUT / 'baseline-files' / name
        try:
            old_lines = before_path.read_text(encoding='utf-8').splitlines(keepends=True) if before_path.is_file() else []
            new_lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
            if '\0' not in ''.join(old_lines + new_lines):
                diffs.extend(difflib.unified_diff(old_lines, new_lines, 'baseline/' + name, 'goal17a/' + name))
        except UnicodeDecodeError:
            pass
    changes_path = OUT / 'changed-files.json'
    diff_path = OUT / 'actual-diff.patch'
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    diff_path.write_text(''.join(diffs), encoding='utf-8')

    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / 'hbmsntm-198A-goal17a.jar'
    if destination.exists():
        assert sha(destination) == sha(JAR), 'Refusing to overwrite a different Goal17A JAR'
    else:
        shutil.copyfile(JAR, destination)
    digest = sha(destination)
    sums_path = RELEASE / 'SHA256SUMS.txt'
    sums_path.write_text(digest + '  ' + destination.name + '\n', encoding='ascii')

    report_hashes = {name: sha(ROOT / name) for name in REPORTS}
    evidence_hashes = {
        **report_hashes,
        'build/migration/goal17a/resource-verification.json': sha(OUT / 'resource-verification.json'),
        'build/migration/goal17a/changed-files.json': sha(changes_path),
        'build/migration/goal17a/actual-diff.patch': sha(diff_path),
    }
    receipt = {
        'file': destination.name,
        'bytes': destination.stat().st_size,
        'sha256': digest,
        'source_commit': baseline['source_head'],
        'target_start_commit': baseline['target_head'],
        'base_release': PREVIOUS.relative_to(ROOT).as_posix(),
        'actual_start': 'build/migration/goal17a/baseline.json',
        'changed_inputs': resource_result['changed_inputs'],
        'generated_resource_count': len(stamp['generated']),
        'changed_files': {
            'path': 'build/migration/goal17a/changed-files.json',
            'sha256': sha(changes_path),
            'count': len(changes),
        },
        'actual_diff': {
            'path': 'build/migration/goal17a/actual-diff.patch',
            'sha256': sha(diff_path),
        },
        'jar_delta': jar_delta,
        'jar_directory_delta': directory_delta,
        'old_releases': baseline['old_releases'],
        'preserved_release_files': len(baseline['old_release_files']),
        'preserved_g6_g12_files': baseline['preserved_g6_g12_files'],
        'preserved_goal15a_corrected_receipt_and_packer': True,
        'preserved_goal17_preparation_record': True,
        'resource_checks': resource_result,
        'verification': verification,
        'reports': REPORTS,
        'report_sha256': report_hashes,
        'evidence_sha256': evidence_hashes,
        'evidence': 'Static source/resource checks, isolated regression reports, offline runData/build and exact independent JAR audit; real game, save, UI, JEI, multiplayer and dedicated-server acceptance remains partial-unverified.',
    }
    (RELEASE / 'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        key: receipt[key] for key in ('file', 'bytes', 'sha256', 'generated_resource_count', 'preserved_release_files')
    }, ensure_ascii=False))
    print(
        f'JAR delta +{len(jar_delta["added"])}/~{len(jar_delta["modified"])}/-{len(jar_delta["removed"])}; '
        f'{len(changes)} frozen-start file changes; all {len(baseline["old_releases"])} old JARs preserved.'
    )


if __name__ == '__main__':
    main()
