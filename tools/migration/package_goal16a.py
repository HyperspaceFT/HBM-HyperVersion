"""Package Goal16A against its frozen real starting point; never replace an old release."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import zipfile
from verify_goal16a_resources import ROOT, OUT, JAVA, ASSETS, EXPECTED_INPUTS, GENERATED_NEW, GENERATED_CHANGED, read, sha, verify

RELEASE = ROOT/'build/migration/releases/goal16a'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
PREVIOUS = ROOT/'build/migration/releases/goal15b/hbmsntm-198A-goal15b.jar'
RECORDS = {
    'migration/GOAL16A.md', 'migration/GOAL16A-ACCEPTANCE.md',
    'migration/README.md', 'migration/UPSTREAM-REVIEWS.md', 'migration/features.json',
    'migration/LOCALIZATION.md', 'migration/localization/zh_cn-map.json', 'migration/RESOURCE-OWNERSHIP.md',
    'migration/goal16a-static-review.md', 'migration/goal16a-materials-review.json',
    'migration/goal16a-mixer-recipes.json', 'migration/goal16a-mixer-comparison.json',
    'migration/goal16a-custom-mixer-example.json', 'migration/goal16a-finite-accounting.json',
    'migration/goal16a-resource-ownership.json', 'migration/goal16a-localization-review.json',
    'tools/migration/package_goal16a.py', 'tools/migration/verify_goal16a_resources.py',
    'tools/migration/verify_goal16a_affected.py', 'tools/migration/verify_goal16a_recipes.py',
    'tools/migration/verify_goal16a_machine.py', 'tools/migration/verify_goal16a_structures.py',
    'tools/migration/verify_goal16a_acquisition.py', 'tools/migration/goal16a_regression/README.md',
    'tools/migration/goal16a_regression/recipe_stubs.py', 'tools/migration/goal16a_regression/machine_stubs.py',
    'tools/migration/goal16a_regression/structure_stubs.py', 'tools/migration/goal16a_regression/acquisition_stubs.py',
    'tools/migration/goal16a_regression/Goal16ARecipeRegression.java',
    'tools/migration/goal16a_regression/Goal16AMachineRegression.java',
    'tools/migration/goal16a_regression/Goal16AStructureRegression.java',
    'tools/migration/goal16a_regression/Goal16AAcquisitionRegression.java',
    'src/generated/resources/.migration-stamp.json',
}
REPORTS = ['migration/GOAL16A.md', 'migration/GOAL16A-ACCEPTANCE.md',
           'migration/goal16a-static-review.md', 'build/migration/goal16a/verification.json']


def git(root, *args):
    return subprocess.check_output(['git', '-c', f'safe.directory={root.as_posix()}', *args], cwd=root).decode('utf-8')


def changed_class(name):
    return any(name == p+'.class' or (name.startswith(p+'$') and name.endswith('.class')) for p in JAVA)


def input_path(name):
    name = name.replace('\\', '/')
    p = Path(name)
    if p.is_absolute():
        return p
    return ROOT/name if name.startswith(('src/', 'tools/', 'build/', '.gradle/')) else ROOT/'src/main/java'/name


def hash_map(values, label):
    assert isinstance(values, dict), label
    for path, digest in values.items():
        assert isinstance(digest, str) and len(digest) == 64, (label, path)
        p = input_path(path)
        assert p.is_file() and sha(p) == digest, f'Verified input changed: {label}: {path}'


def check_report(path):
    record = read(path)
    source_present = False
    for key in ('source_sha256', 'source_hashes', 'production_sha256', 'source_inputs_sha256', 'extracted_input_sha256'):
        if isinstance(record.get(key), dict):
            hash_map(record[key], str(path)+':'+key)
            source_present = True
    assert source_present, f'No source provenance: {path}'
    for key in ('fixture_sha256', 'fixtures_sha256', 'adapter_sha256', 'imported_generator_sha256', 'cache_sha256', 'java_sha256', 'compiled_input_sha256'):
        if isinstance(record.get(key), dict):
            hash_map(record[key], str(path)+':'+key)
    if isinstance(record.get('fixture_sha256'), str):
        assert sha(ROOT/'tools/migration/goal16a_regression/Goal16AStructureRegression.java') == record['fixture_sha256']
    if 'original_sha256' in record:
        assert sha(ROOT.parent/'Hbm-s-Nuclear-Tech-GIT/src/main/java/com/hbm/inventory/recipes/MixerRecipes.java') == record['original_sha256']
    for rel, digest in record.get('generated_service_sha256', {}).items():
        data = (path.parent/'services'/rel).read_text(encoding='utf-8').encode('utf-8')
        assert hashlib.sha256(data).hexdigest() == digest, f'Generated service changed: {rel}'
    for cmd in record.get('commands', []):
        assert cmd.get('returncode', cmd.get('exit')) == 0, f'Failed final command: {path}'
    for case in record.get('records', []):
        hash_map(case['compiled_input_sha256'], str(path)+':'+case['label'])
        assert case['commands'][0]['returncode'] == 0, 'A compile failure is not mutation detection'
        execution = case['commands'][1]
        if case['label'] == 'production':
            assert execution['returncode'] == 0
        else:
            assert execution['returncode'] != 0 and 'java.lang.AssertionError' in execution['output']
    if isinstance(record.get('adapter_sha256'), str):
        assert sha(path.parent/'verify_goal15b-adapted.py') == record['adapter_sha256']
    for rel, digest in record.get('generated_stub_sha256', {}).items():
        assert sha(path.parent/rel.replace('\\', '/')) == digest, f'Acquisition stub changed: {rel}'
    if 'cached_inputs' in record:
        cached = record['cached_inputs']
        assert sha(Path(cached['gson'])) == cached['gson_sha256']
        assert all(v['returncode'] == 0 for v in cached['versions'])
        assert record['source_stable_after_run'] and not record['failures']
    if 'cached_engine_sha256' in record:
        cache = ROOT/'.gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar'
        assert sha(cache) == record['cached_engine_sha256']
    if 'returncode' in record:
        assert record['returncode'] == 0 and record['productionUnchanged'] and record['legacyToolsUnchanged']
    return record


def main():
    baseline = read(OUT/'baseline.json')
    original = ROOT.parent/'Hbm-s-Nuclear-Tech-GIT'
    assert git(original, 'status', '--porcelain=v1') == baseline['source_status'] == ''
    assert git(original, 'rev-parse', 'HEAD').strip() == baseline['source_head']
    assert git(ROOT, 'rev-parse', 'HEAD').strip() == baseline['target_head']
    assert sha(PREVIOUS) == baseline['base_release_sha256']
    for name, digest in baseline['old_release_files'].items():
        assert sha(ROOT/name) == digest, f'Old release changed: {name}'
    for name in baseline['preserved_g6_g12_files']:
        assert sha(ROOT/name) == baseline['files'][name], f'G6-G12 repair changed: {name}'
    assert sha(ROOT/'tools/migration/package_goal15a.py') == baseline['files']['tools/migration/package_goal15a.py']
    prior_features = read(OUT/'baseline-files/migration/features.json')['features']
    final_features = {f['id']:f for f in read(ROOT/'migration/features.json')['features']}
    assert set(final_features) == {f['id'] for f in prior_features} | {'fluid-mixing'}
    assert final_features['fluid-mixing']['status'] == 'partial-unverified'
    linked = {'materials', 'crucible-alloying', 'basic-assembly', 'oil-coking'}
    for prior_feature in prior_features:
        current_feature = final_features[prior_feature['id']]
        if prior_feature['id'] not in linked:
            assert current_feature == prior_feature, f'Unrelated feature changed: {prior_feature["id"]}'
        else:
            for key, value in prior_feature.items():
                if key in ('notes', 'evidence'):
                    assert current_feature[key][:len(value)] == value, f'Prior feature record overwritten: {prior_feature["id"]}'
                else:
                    assert current_feature[key] == value, f'Prior feature state changed: {prior_feature["id"]}'
    recipe_outputs = OUT/'recipes/b2408858402c4379b9dcd21d9e59010b'
    for generated, delivered in [('_hbmMixer.json','goal16a-mixer-recipes.json'),
                                 ('original-mapping.json','goal16a-mixer-comparison.json'),
                                 ('custom-example.json','goal16a-custom-mixer-example.json')]:
        assert (recipe_outputs/generated).read_bytes() == (ROOT/'migration'/delivered).read_bytes(), f'Recipe evidence not actual writer/check output: {delivered}'
    assert (OUT/'machine/54f374ecc69a416f97b36a66d5d94ce5/finite-accounting.json').read_bytes() == (ROOT/'migration/goal16a-finite-accounting.json').read_bytes()
    resource_result = verify()
    verification = read(OUT/'verification.json')
    assert verification['status'] == 'local-delivery-complete; gameplay partial-unverified'
    for name in verification['source_verified_reports']:
        check_report(ROOT/name)
    for name, digest in verification['evidence_sha256'].items():
        assert sha(ROOT/name) == digest, f'Final evidence changed: {name}'
    for name in ('localization-audit.json', 'resources-audit.json', 'packaged-resources.json'):
        report = read(OUT/name)
        assert not [f for f in report['findings'] if f['severity'] in ('error', 'warning')], name
    for name in ('runData.log', 'build.log'):
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig'), name
    assert all((ROOT/name).is_file() for name in REPORTS), 'Broken report index'
    assert REPORTS[:2] == ['migration/GOAL16A.md', 'migration/GOAL16A-ACCEPTANCE.md']
    stamp = read(ROOT/'src/generated/resources/.migration-stamp.json')
    with zipfile.ZipFile(JAR) as current, zipfile.ZipFile(PREVIOUS) as prior:
        names = current.namelist()
        assert len(names) == len(set(names)), 'Duplicate JAR entries'
        assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or '.migration-stamp' in n for n in names)
        for name in stamp['generated']:
            assert current.read(name) == (ROOT/'src/generated/resources'/name).read_bytes(), name
        for _, name in ASSETS:
            assert current.read('assets/hbmsntm/'+name) == (ROOT/'src/main/resources/assets/hbmsntm'/name).read_bytes(), name
        zh = 'assets/hbmsntm/lang/zh_cn.json'
        assert current.read(zh) == (ROOT/'src/main/resources'/zh).read_bytes()
        for name in JAVA:
            assert name+'.class' in names, f'Missing class: {name}'
        for name in names:
            if changed_class(name):
                assert current.read(name) == (ROOT/'build/classes/java/main'/name).read_bytes(), name
        old = {e.filename for e in prior.infolist() if not e.is_dir()}
        new = {e.filename for e in current.infolist() if not e.is_dir()}
        delta = dict(added=sorted(new-old), removed=sorted(old-new), modified=sorted(n for n in old & new if prior.read(n) != current.read(n)))
        directory_delta = dict(added=sorted({e.filename for e in current.infolist() if e.is_dir()} - {e.filename for e in prior.infolist() if e.is_dir()}),
                               removed=sorted({e.filename for e in prior.infolist() if e.is_dir()} - {e.filename for e in current.infolist() if e.is_dir()}))
    allowed_resources = GENERATED_NEW | GENERATED_CHANGED | {'assets/hbmsntm/lang/zh_cn.json'} | {'assets/hbmsntm/'+n for _, n in ASSETS}
    assert not delta['removed'] and not directory_delta['removed'], delta
    assert all(changed_class(n) or n in allowed_resources for values in delta.values() for n in values), delta
    current_names = {n for n in git(ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0') if n}
    allowed_delta = EXPECTED_INPUTS | RECORDS | {'src/generated/resources/'+p for p in GENERATED_NEW | GENERATED_CHANGED}
    changes = []
    diff = []
    for name in sorted(current_names | baseline['files'].keys()):
        path = ROOT/name
        before = baseline['files'].get(name)
        after = sha(path) if path.is_file() else None
        if before == after:
            continue
        assert name in allowed_delta, f'Unassigned path changed since real start: {name}'
        changes.append(dict(path=name, status='added' if before is None else 'removed' if after is None else 'modified', before_sha256=before, after_sha256=after))
        prior = OUT/'baseline-files'/name
        try:
            a = prior.read_text(encoding='utf-8').splitlines(keepends=True) if prior.is_file() else []
            b = path.read_text(encoding='utf-8').splitlines(keepends=True) if path.is_file() else []
            if '\0' not in ''.join(a+b):
                diff.extend(difflib.unified_diff(a,b,'baseline/'+name,'goal16a/'+name))
        except UnicodeDecodeError:
            pass
    (OUT/'changed-files.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (OUT/'actual-diff.patch').write_text(''.join(diff), encoding='utf-8')
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE/'hbmsntm-198A-goal16a.jar'
    if destination.exists():
        assert sha(destination) == sha(JAR), 'Refusing to replace a different Goal16A JAR'
    else:
        shutil.copyfile(JAR, destination)
    digest = sha(destination)
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+destination.name+'\n', encoding='ascii')
    receipt = dict(file=destination.name, bytes=destination.stat().st_size, sha256=digest,
                   source_commit=baseline['source_head'], target_start_commit=baseline['target_head'],
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), actual_start='build/migration/goal16a/baseline.json',
                   changed_inputs=resource_result['changed_inputs'], generated_resource_count=len(stamp['generated']),
                   changed_files='build/migration/goal16a/changed-files.json', actual_diff='build/migration/goal16a/actual-diff.patch',
                   jar_delta=delta, jar_directory_delta=directory_delta, old_releases=baseline['old_releases'],
                   preserved_release_files=len(baseline['old_release_files']), preserved_g6_g12_files=baseline['preserved_g6_g12_files'],
                   preserved15a_corrected_indexes=True, resource_checks=resource_result, verification=verification,
                   evidence='Static source, isolated methods, offline generation/build and exact JAR bytes; no real game/save/UI/multiplayer/dedicated-server acceptance.',
                   reports=REPORTS)
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('file','bytes','sha256','generated_resource_count','preserved_release_files')},ensure_ascii=False))
    print(f'JAR delta +{len(delta["added"])} / ~{len(delta["modified"])} / -{len(delta["removed"])}; {len(baseline["old_releases"])} old JARs preserved.')


if __name__ == '__main__':
    main()
