"""Package Goal20A (uranium/thorium crystallizer rows, yellowcake alignment, thorium smelting, TH232 breeding rod) cumulatively on the
review-g19-fixes-20261015 package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal20a.py [--check]

Both modes run every check. --check writes nothing and prints what is still pending. The frozen Goal20A start is the tree committed by
Goal20A-0 (build/migration/goal20a/baseline.json, taken before the commits; the commits changed no file content), whose generated tree
and build equalled the fixes JAR (the fixes JAR was rebuilt from that tree). Every class and resource delta of the JAR against the fixes
JAR must be explained by the three Goal20A production sources or the generated files (eight added, four retired, the stamp). Evidence of
the final run is read from build/migration/goal20a/ (production build/audit logs, the final suite summary, the two Goal20A verifier
reports it names, compare.json) and the records from migration/."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal17b import resolve
from package_goal18b import verify_report, owner_class
from package_goal19a import goal18b_hashed_paths
from package_goal19b import goal19a_hashed_paths
from package_goal19c import protected_drift as goal19c_protected_drift, goal19b_hashed_paths, old_release_files as goal19c_start_release_files, current_paths, tree_files, git
from package_review_g19_fixes import fix_start_protected, COMMITS

OUT = ROOT/'build/migration/goal20a'
PREVIOUS = ROOT/'build/migration/releases/review-g19-fixes-20261015/hbmsntm-198A-g19-fixes.jar'
PREVIOUS_SHA = '11d1eacea635e624ddb82b2459f8288a0b185959664bc6a65cb1e804ea248211'
PREVIOUS_BYTES = 18108534
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/review-g19-fixes-20261015/release.json'
PREVIOUS_RECEIPT_SHA = '18fa913704e2f38afa103f9e6ee4b9b1de318df4293863c37f8994fda16cf569'
PREVIOUS_SUMS = ROOT/'build/migration/releases/review-g19-fixes-20261015/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = '9bb4540dab17bce8cdd589aba76af675b6dd8ccb383fd18470a479c3deaa8f4f'
PREVIOUS_COMPARE = OUT/'fixes/compare.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal20a'
RELEASE_NAME = 'hbmsntm-198A-goal20a.jar'
SOURCE_HEAD = 'd31426cbd97ade3bdd852617413f22c23be4fd82'
START_HEAD = '70bc989982eb0f05f54148158428baf2f37caddb'
SNAPSHOT = 'migration/baselines/review-d31426cbd97a.json'
COMPARE = OUT/'compare.json'
FINAL_SUMMARY = OUT/'final/summary.json'
DEFERRED_KEYS = 108
EN_KEYS = 2329
ZH_KEYS = 2221
AUDITS = ('localization-audit-20a.json', 'resources-audit-20a.json', 'packaged-resources-20a.json')
# The 41-row intermediate runData (runData-production-archive.log) archived the four retired thorium-fuel smelting files with
# -PmigrationArchiveOrphans=true; the final 45-row chain is compile/runData/build-production.log.
LOGS = ('compile-production.log', 'runData-production-archive.log', 'runData-production.log', 'build-production.log')
GOAL20A_PRODUCTION = ['src/main/java/com/hbm/'+p for p in (
    'datagen/NtmRecipeProvider.java',
    'inventory/recipes/ChemicalPlantRecipes.java',
    'inventory/recipes/CrystallizerRecipes.java',
)]
GENERATED_ADDED = ['src/generated/resources/data/hbmsntm/'+p for p in (
    'advancement/recipes/misc/ingot_th232_from_smelting_ore_thorium.json',
    'advancement/recipes/misc/ingot_th232_from_smelting_ore_thorium_deepslate.json',
    'advancement/recipes/misc/powder_thorium_to_ingot_th232.json',
    'advancement/recipes/misc/rod_zirnox_th232.json',
    'recipe/ingot_th232_from_smelting_ore_thorium.json',
    'recipe/ingot_th232_from_smelting_ore_thorium_deepslate.json',
    'recipe/powder_thorium_to_ingot_th232.json',
    'recipe/rod_zirnox_th232.json',
)]
GENERATED_RETIRED = ['src/generated/resources/data/hbmsntm/'+p for p in (
    'advancement/recipes/misc/ingot_thorium_fuel_from_smelting_ore_thorium.json',
    'advancement/recipes/misc/ingot_thorium_fuel_from_smelting_ore_thorium_deepslate.json',
    'recipe/ingot_thorium_fuel_from_smelting_ore_thorium.json',
    'recipe/ingot_thorium_fuel_from_smelting_ore_thorium_deepslate.json',
)]
GENERATED = GENERATED_ADDED + ['src/generated/resources/.migration-stamp.json']
RECORDS = ['migration/GOAL20A.md', 'migration/GOAL20A-ACCEPTANCE.md', 'migration/GOAL20.md', 'migration/README.md', 'migration/UPSTREAM-REVIEWS.md',
           'migration/LOCALIZATION.md', 'migration/features.json',
           'migration/goal20a-materials-review.json', 'migration/goal20a-finite-accounting.json', 'migration/goal20a-static-review.md',
           'migration/goal20a-custom-crystallizer-example.json', 'migration/goal20a-crystallizer-recipes.json', 'migration/goal20a-localization-review.json',
           'migration/REVIEW-FIXES-ZIRNOX.md', 'migration/REVIEW-FIXES-FALLOUT-DUMMYABLE.md', 'migration/REVIEW-FIXES-FALLOUT-STOMP.md']
# Hashed by the receipt (frozen afterwards): this batch's own reports and evidence. README, features, UPSTREAM-REVIEWS, LOCALIZATION and the
# fix records (already hashed by the fixes receipt) are checked for existence only.
REPORTS = ['migration/GOAL20A.md', 'migration/GOAL20A-ACCEPTANCE.md', 'migration/goal20a-finite-accounting.json', 'migration/goal20a-static-review.md',
           'migration/goal20a-materials-review.json', 'migration/goal20a-custom-crystallizer-example.json', 'migration/goal20a-crystallizer-recipes.json',
           'migration/goal20a-localization-review.json',
           'build/migration/goal20a/final/summary.json', 'build/migration/goal20a/compare.json', 'build/migration/goal20a/commits.json']
SUITE_README = 'tools/migration/goal20a_regression/README.md'
GOAL20A_TOOLS = ['tools/migration/verify_goal20a_recipes.py', 'tools/migration/verify_goal20a_machine.py', 'tools/migration/package_goal20a.py',
                 'tools/migration/package_review_g19_fixes.py', SUITE_README]
GOAL20A_SUITE_DIR = 'tools/migration/goal20a_regression/'
FIX_RECORDS_UPDATED = ['migration/REVIEW-FIXES-ZIRNOX.md', 'migration/REVIEW-FIXES-FALLOUT-DUMMYABLE.md', 'migration/REVIEW-FIXES-FALLOUT-STOMP.md']
ALLOWED_GROUPS = {
    'production': GOAL20A_PRODUCTION,
    'generated': GENERATED,
    'records': RECORDS,
    'tools': GOAL20A_TOOLS,
}
GOAL20A_KINDS = ('recipes', 'machine')
MUTATION_MINIMUM = {'recipes': 8, 'machine': 6}
EXCLUDED_SHA_FIELDS = {
    'mutated_sha256': 'hash of the temporary mutated copy; must differ from every production source hash of the report',
    'source_sha256_after_run': 'production hashes re-read after the run; must equal source_sha256',
}
# String-valued *_sha256 fields of the Goal20A reports that name one known file.
STRING_SHA_FILES = {
    'finite_sha256': None,  # resolved from the report's own finite path
}
PRODUCTION_HASH_FIELDS = ('source_sha256', 'extracted_source_sha256', 'production_source_sha256', 'source_hashes', 'final_source_hashes', 'production_sha256')


def protected_drift():
    drift = goal19c_protected_drift()
    drift += [f'goal19c receipt or old release: {p}' for p, h in sorted(fix_start_protected().items()) if not (ROOT/p).is_file() or sha(ROOT/p) != h]
    fixes = read(PREVIOUS_RECEIPT)
    drift += [f'fixes receipt: {p}' for p, h in sorted(fixes['evidence_sha256'].items()) if not (ROOT/p).is_file() or sha(ROOT/p) != h]
    return drift


def assert_writable(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for label, hashed in (('Goal18B', goal18b_hashed_paths()), ('Goal19A', goal19a_hashed_paths()), ('Goal19B', goal19b_hashed_paths()),
                          ('Goal19C', fix_start_protected()), ('fixes', read(PREVIOUS_RECEIPT)['evidence_sha256'])):
        assert rel not in hashed, f'Refusing to write {label} receipt evidence: '+rel
    assert rel not in goal19c_start_release_files(), 'Refusing to write a previous release file: '+rel
    inside = Path(path).resolve().is_relative_to(RELEASE.resolve())
    assert not Path(path).resolve().is_relative_to(RELEASES.resolve()) or inside, 'Refusing to write outside the Goal20A release directory: '+rel


def schema(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for kind in GOAL20A_KINDS:
        if rel.startswith(f'build/migration/goal20a/{kind}/'):
            return kind
    return 'older'


def resolve_20a(name, report, field):
    path = Path(str(name).replace('\\', '/'))
    if path.is_absolute(): return path
    candidates = [ROOT/path, ROOT/'src/main/java'/path, ROOT/'src/generated/resources'/path, report.parent/path, report.parent/'stubs'/path,
                  report.parent/'sources'/path, report.parent/'classes'/path, SOURCE/path, SOURCE/'src/main/java'/path]
    return next((p for p in candidates if p.is_file()), candidates[0])


def verify_sha_fields(path, data):
    """Every *_sha256 field of a Goal20A report and of each mutations[] item is verified or excluded with its rule."""
    production = set()
    for field in PRODUCTION_HASH_FIELDS:
        if isinstance(data.get(field), dict):
            production |= set(data[field].values())
    records = [('report', data), *[('mutations[%d]' % i, m) for i, m in enumerate(data.get('mutations', []) if isinstance(data.get('mutations'), list) else [])]]
    verified, excluded = 0, 0
    for where, record in records:
        for field, value in record.items():
            if not field.endswith('_sha256'):
                continue
            label = f'{path}:{where}:{field}'
            if field == 'mutated_sha256':
                assert isinstance(value, str) and len(value) == 64, 'Malformed '+label
                assert production and value not in production, 'Mutated copy equals a production source: '+label
                excluded += 1
            elif field == 'source_sha256_after_run':
                assert value == data.get('source_sha256'), 'Production changed during the run: '+label
                excluded += 1
            elif isinstance(value, dict):
                assert value, 'Empty hash map '+label
                for name, digest in value.items():
                    target = resolve_20a(name, Path(path), field)
                    assert target.is_file(), 'Missing verification input: '+label+': '+str(name)
                    assert sha(target) == digest, 'Verification input changed: '+label+': '+str(name)
                verified += 1
            elif isinstance(value, str) and any(isinstance(record.get(k), str) for k in (field[:-len('_sha256')], field[:-len('_sha256')]+'_path')):
                companion = next(record[k] for k in (field[:-len('_sha256')], field[:-len('_sha256')]+'_path') if isinstance(record.get(k), str))
                target = resolve_20a(companion, Path(path), field)
                assert target.is_file() and sha(target) == value, 'Hashed companion file changed: '+label
                verified += 1
            else:
                raise AssertionError('Unknown *_sha256 field (neither verified nor excluded): '+label)
    for name, export in (data.get('exports') or {}).items():
        assert sha(resolve_20a(export['path'], Path(path), 'exports')) == export['sha256'], 'Changed export: '+name
        verified += 1
    example = data.get('custom_example')
    if isinstance(example, dict):
        assert sha(resolve_20a(example['path'], Path(path), 'custom_example')) == example['sha256'], 'The custom crystallizer example changed since its recipes run'
        verified += 1
    expectation = data.get('original_expectation')
    if isinstance(expectation, dict):
        for name, digest in (expectation.get('original_file_sha256') or {}).items():
            target = SOURCE/name if (SOURCE/name).is_file() else SOURCE/'src/main/java'/name
            assert sha(target) == digest, 'Original source changed: '+name
            verified += 1
    return verified, excluded


def mutation_count(path, data):
    kind = schema(path)
    entries = data.get('mutations') if isinstance(data.get('mutations'), list) else []
    for m in entries:
        if 'commands' in m:
            commands = m['commands']
            ok = (m.get('detected') is True and commands[0]['returncode'] == 0 and commands[-1]['returncode'] != 0
                  and ('AssertionError' in commands[-1]['output']) and m['expected_fragment'] in commands[-1]['output'])
            if 'compiled_successfully' in m: ok = ok and m['compiled_successfully'] is True
        else:
            ok = m.get('detected') is True and str(m.get('kind', '')).startswith('static') and m['expected_fragment'] in m['message']
        assert ok, f'{kind} mutation not detected by its expected assertion: '+str(m.get('label'))
    total = len(entries)
    assert total >= MUTATION_MINIMUM[kind], f'{kind} mutations {total}, expected >= {MUTATION_MINIMUM[kind]}'
    detected = data.get('mutations_detected')
    assert detected in (total, f'{total}/{total}'), f'{kind} report mutation count {detected!r} disagrees with its {total} records'
    return dict(detected=total, total=total, schema=kind)


def verify_report_20a(path):
    path = Path(path)
    assert schema(path) != 'older', 'Not a Goal20A report: '+str(path)
    data = verify_report(path)
    verified, excluded = verify_sha_fields(path, data)
    assert data.get('source_stable_after_run') is True, 'Source not stable after the run: '+str(path)
    return dict(sha_fields_verified=verified, sha_fields_excluded=excluded, mutations=mutation_count(path, data))


def lang(archive, entry):
    return json.loads(archive.read(entry).decode('utf-8'))


def report_of(summary, suite):
    entry = summary['suites'][suite]
    assert entry['status'] == 'as-expected' and entry['exit'] == 0, f'{suite} did not pass in the final run: {entry["status"]}'
    assert entry.get('report'), f'{suite} printed no report path'
    return entry['report']


def main(check):
    pending = []
    base = read(OUT/'baseline.json')
    commits = read(COMMITS)
    one, two = commits['commit_one']['id'], commits['commit_two']['id']

    # 1. Heads and the clean original.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD, 'Unexpected frozen start'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    assert git(ROOT, 'rev-parse', 'HEAD').strip() == two, 'NEO HEAD is not commit two'

    # 2. Previous deliveries: the fixes package, the goal19c package and every older receipt's hashed paths and release files.
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'Fixes JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'Fixes release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'Fixes SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Fixes SHA256SUMS.txt content changed'
    prior_receipt = read(PREVIOUS_RECEIPT)
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    assert prior_receipt['commits']['commit_one']['id'] == one and prior_receipt['commits']['commit_two']['id'] == two, 'Fixes receipt names other commits'
    for p, h in base['old_release_files'].items(): assert sha(ROOT/p) == h, 'Previous release file changed: '+p
    drift = protected_drift()
    assert not drift, 'Protected evidence drifted: '+str(drift)
    old_releases = dict(base['old_releases'])
    old_releases[PREVIOUS.relative_to(ROOT).as_posix()] = PREVIOUS_SHA
    assert len(old_releases) == len(base['old_releases']) + 1

    # 3. Final suite summary and the two Goal20A reports it names.
    assert FINAL_SUMMARY.is_file(), 'Missing final suite summary (run build/migration/goal20a/final/run_final.py run, then summary)'
    final = read(FINAL_SUMMARY)
    assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
    assert len(final['suites']) == 64, 'Final run did not cover 64 suites'
    report_checks = {}
    for kind, suite in (('recipes', 'verify_goal20a_recipes.py --mutations'), ('machine', 'verify_goal20a_machine.py --mutations')):
        rel = report_of(final, suite)
        assert schema(ROOT/rel) == kind, f'{suite} report is not under build/migration/goal20a/{kind}/: {rel}'
        report_checks[rel] = verify_report_20a(ROOT/rel)
    recipes_report = next(p for p in report_checks if schema(ROOT/p) == 'recipes')
    machine_report = next(p for p in report_checks if schema(ROOT/p) == 'machine')

    # 4. Build logs and audits of the final production run.
    for name in LOGS:
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), 'Missing successful '+name
    for name in AUDITS:
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
    assert read(OUT/'localization-audit-20a.json')['coverage']['deferred_keys'] == DEFERRED_KEYS, 'Deferred localization count changed'
    exits = dict(l.split('=') for l in (OUT/'prod-exits.txt').read_text(encoding='utf-8').split())
    assert all(v == '0' for v in exits.values()), 'A production-run command failed: '+str(exits)

    # 5. Generation stamp.
    stamp = read(ROOT/'src/generated/resources/.migration-stamp.json')
    assert all((ROOT/p).is_file() and normalized_sha(ROOT/p) == h for p, h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p) == h for p, h in stamp['generated'].items()), 'Generated stamp stale'
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    assert java_now <= set(stamp['inputs']), 'Unrecorded Java generation input: '+str(sorted(java_now-set(stamp['inputs'])))
    for p in GENERATED_RETIRED: assert not (ROOT/p).exists() and p[len('src/generated/resources/'):] not in stamp['generated'], 'Retired generated file still present: '+p

    # 6. Sources and generated resources changed since the frozen start.
    current = current_paths()
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    assert since == sorted(GOAL20A_PRODUCTION), 'Source change since the Goal20A start differs from the list: '+str(since)
    # The retired files are still in the git index (deleted in the worktree), so the cached listing names them; they are checked as removals below.
    generated_since = sorted(p for p in current if p.startswith('src/generated/') and (ROOT/p).is_file() and base['files'].get(p) != sha(ROOT/p))
    assert generated_since == sorted(GENERATED), 'Generated change since the Goal20A start: '+str(generated_since)
    removed = sorted(p for p in base['files'] if p.startswith(('src/main/', 'src/generated/')) and not (ROOT/p).is_file())
    assert removed == sorted(GENERATED_RETIRED), 'Removed since the Goal20A start: '+str(removed)

    # 7. JAR contents and the delta against the fixes JAR.
    classes_root = ROOT/'build/classes/java/main'
    classes = sorted(classes_root.rglob('*.class'))
    assert classes
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
        names = jar.namelist()
        assert len(names) == len(set(names)), 'Duplicate archive entries'
        assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
        for p in stamp['generated']: assert jar.read(p) == (ROOT/'src/generated/resources'/p).read_bytes(), p
        assert jar.read('assets/hbmsntm/lang/zh_cn.json') == (ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
        for path in classes:
            name = path.relative_to(classes_root).as_posix()
            assert jar.read(name) == path.read_bytes(), name
        for entry, count in (('assets/hbmsntm/lang/en_us.json', EN_KEYS), ('assets/hbmsntm/lang/zh_cn.json', ZH_KEYS)):
            assert jar.read(entry) == prior.read(entry), 'Language file changed although Goal20A adds no text: '+entry
            assert len(lang(jar, entry)) == count, f'{entry} has {len(lang(jar, entry))} keys, expected {count}'
        old = {i.filename for i in prior.infolist() if not i.is_dir()}
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
        dir_delta = {'added': sorted({i.filename for i in jar.infolist() if i.is_dir()} - {i.filename for i in prior.infolist() if i.is_dir()}),
                     'removed': sorted({i.filename for i in prior.infolist() if i.is_dir()} - {i.filename for i in jar.infolist() if i.is_dir()})}
    since_set = set(since)
    gen = lambda p: p[len('src/generated/resources/'):]
    assert delta['added'] == sorted(gen(p) for p in GENERATED_ADDED), 'Added JAR entries differ from the generated additions: '+str(delta['added'])
    assert delta['removed'] == sorted(gen(p) for p in GENERATED_RETIRED), 'Removed JAR entries differ from the retired generated files: '+str(delta['removed'])
    assert not dir_delta['added'] and not dir_delta['removed'], 'JAR directories changed: '+str(dir_delta)
    unexplained = [n for n in delta['modified'] if not (n.endswith('.class') and owner_class(n) in since_set)]
    assert not unexplained, 'Unexplained JAR change: '+str(unexplained)
    owners = sorted({owner_class(n) for n in delta['modified']})
    assert set(owners) == since_set, 'Not every Goal20A source changed a class: '+str(sorted(since_set - set(owners)))

    # 8. Paths changed since the frozen start, against the explicit allowlist.
    allowed = {p for paths in ALLOWED_GROUPS.values() for p in paths}
    changes, diff = [], []
    for p in sorted(current | set(base['files'])):
        if p.startswith(GOAL20A_SUITE_DIR): continue
        path = ROOT/p; before = base['files'].get(p); after = sha(path) if path.is_file() else None
        if before == after: continue
        if p in GENERATED_RETIRED:
            assert after is None
            changes.append(dict(path=p, status='retired', before_sha256=before, after_sha256=None, groups=['generated'])); continue
        assert p in allowed, 'Unassigned path changed from the Goal20A start: '+p
        assert after is not None, 'Unexpected deletion: '+p
        changes.append(dict(path=p, status='added' if before is None else 'modified', before_sha256=before, after_sha256=after,
                            groups=sorted(g for g, paths in ALLOWED_GROUPS.items() if p in paths)))
        old_path = OUT/'baseline-files'/p
        try:
            old_lines = old_path.read_text(encoding='utf-8').splitlines(keepends=True) if old_path.is_file() else []
            new_lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
            binary = '\0' in ''.join(old_lines+new_lines)
        except UnicodeDecodeError:
            binary = True
        if binary:
            diff.append(f'Binary file goal20a/{p}: {before or "absent"} -> {after}\n')
        elif before is not None and not old_path.is_file():
            diff.append(f'No frozen copy of goal20a/{p} at the start: {before} -> {after}\n')
        else:
            diff.extend(difflib.unified_diff(old_lines, new_lines, 'goal20a-start/'+p, 'goal20a/'+p))
    suite_tree = sorted(p for p in current if p.startswith(GOAL20A_SUITE_DIR))
    assert suite_tree and all(p not in base['files'] for p in suite_tree), 'Goal20A suite files existed at the start'
    for p in GOAL20A_TOOLS: assert (ROOT/p).is_file() or (check and p == SUITE_README), 'Listed Goal20A tool missing: '+p
    dirty_fix_records = [p for p in FIX_RECORDS_UPDATED if git(ROOT, 'status', '--porcelain=v1', '--', p) == '']
    assert not dirty_fix_records, 'Fix records lost their Goal20A-0 update: '+str(dirty_fix_records)

    # 9. Records, the d31426c snapshot and compare.json.
    assert base['files'].get(SNAPSHOT) == sha(ROOT/SNAPSHOT), 'Snapshot changed since the Goal20A start'
    impacted = {}
    if check:
        pending += ['records: '+p for p in dict.fromkeys(REPORTS+RECORDS) if p.startswith('migration/') and not (ROOT/p).is_file()]
        pending += ['records (unchanged since the Goal20A start): '+p for p in dict.fromkeys(REPORTS+RECORDS)
                    if p.startswith('migration/') and (ROOT/p).is_file() and base['files'].get(p) == sha(ROOT/p)]
        if not (ROOT/SUITE_README).is_file(): pending.append('suite README '+SUITE_README)
        if not COMPARE.is_file(): pending.append('compare '+COMPARE.relative_to(ROOT).as_posix())
    else:
        for p in REPORTS+RECORDS+[SUITE_README]: assert (ROOT/p).is_file(), 'Missing record: '+p
        machine = read(ROOT/machine_report)
        finite_path = resolve_20a(machine['finite_ledger_path'], ROOT/machine_report, 'finite_ledger')
        assert sha(finite_path) == machine['finite_ledger_sha256'], 'Final machine finite.json changed'
        accounting = read(ROOT/'migration/goal20a-finite-accounting.json')
        assert accounting['ledger'] == read(finite_path) and accounting['source_sha256'] == sha(finite_path), 'Finite accounting is not the final machine ledger'
        recipes = read(ROOT/recipes_report)
        example = resolve_20a(recipes['custom_example']['path'], ROOT/recipes_report, 'custom_example')
        assert (ROOT/'migration/goal20a-custom-crystallizer-example.json').read_bytes() == example.read_bytes(), 'migration/goal20a-custom-crystallizer-example.json is not a byte copy of the final recipes run example'
        rows_export = next(v for k, v in recipes['exports'].items() if 'crystallizer-recipes' in k)
        assert (ROOT/'migration/goal20a-crystallizer-recipes.json').read_bytes() == resolve_20a(rows_export['path'], ROOT/recipes_report, 'exports').read_bytes(), 'migration/goal20a-crystallizer-recipes.json is not the final export'
        features = {f['id']: f for f in read(ROOT/'migration/features.json')['features']}
        for fid in ('crystallization', 'chemical-plant', 'materials', 'zirnox-reactor'):
            assert features[fid]['status'] == 'partial-unverified', fid+' is not partial-unverified'
        assert 'src/main/java/com/hbm/inventory/recipes/CrystallizerRecipes.java' in features['crystallization']['target_paths']
        assert 'src/main/java/com/hbm/inventory/recipes/ChemicalPlantRecipes.java' in features['chemical-plant']['target_paths']
        assert 'src/main/java/com/hbm/datagen/NtmRecipeProvider.java' in features['materials']['target_paths']
        compare = read(COMPARE)
        assert compare['kind'] == 'migration-delta', 'compare.json is not a migration delta'
        assert compare['baseline_source_commit'] == compare['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the d31426c snapshot'
        assert not any(compare['changes']['source'][k] for k in ('added', 'removed', 'modified')), 'compare.json reports source changes'
        for side in ('source', 'target'): assert not compare['unmapped_changes'][side], 'compare.json reports unmapped '+side+' changes'
        assert not compare['removed_feature_ids'] and not compare['manifest_missing_files'], 'compare.json reports removed features or missing files'
        target = compare['changes']['target']
        def paths(entries): return {e['path'] if isinstance(e, dict) else e for e in entries}
        assert paths(target['removed']) == set(GENERATED_RETIRED), 'compare.json removed target files are not the retired generated files: '+str(target['removed'])
        previous_compare = read(PREVIOUS_COMPARE)['changes']['target']
        expected = paths(previous_compare['added']) | paths(previous_compare['modified']) | since_set | set(GENERATED_ADDED)
        assert paths(target['added']) | paths(target['modified']) == expected, 'compare.json target changes differ from the packaged changes: '+str(
            sorted((paths(target['added']) | paths(target['modified'])) ^ expected))
        impacted = {f['id']: {k: f[k] for k in ('state', 'mapping_changed', 'source', 'target', 'upstream_changed_dependencies') if k in f}
                    for f in compare['features'] if f['state'] != 'no-observed-file-change' or f['mapping_changed'] or f['source'] or f['target'] or f['upstream_changed_dependencies']}

    summary = dict(jar_delta={k: len(v) for k, v in delta.items()}, changes_since_goal20a_start=len(changes), sources_changed=len(since),
                   generated_changed=len(generated_since), generated_retired=len(GENERATED_RETIRED), compiled_classes_verified=len(classes),
                   generated_resource_count=len(stamp['generated']), old_releases_preserved=len(old_releases), final_suites=len(final['suites']),
                   mutations={p: f"{c['mutations']['detected']}/{c['mutations']['total']}" for p, c in report_checks.items()},
                   jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check passed; nothing written. Pending:')
        for item in pending: print('  '+item)
        return

    changes_path = OUT/'goal20a-changed-files.json'; diff_path = OUT/'goal20a-actual-diff.patch'
    for target in (changes_path, diff_path, RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json'): assert_writable(target)
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    diff_path.write_text(''.join(diff), encoding='utf-8', newline='\n')
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different Goal20A JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest != PREVIOUS_SHA, 'The Goal20A JAR is the fixes JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in REPORTS}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified',
                   scope='Goal20A: sulfuric acid crystallizer rows for the seven NEO uranium ores and the two thorium ores (36 -> 45 default rows), chem.yellowcake '
                         'aligned to two uranium billets, thorium ore and thorium powder smelting to the thorium-232 ingot, the ZIRNOX TH232 breeding rod recipe; '
                         'Goal20A-0 committed Goal19B/19C and the three fixes (commit one) and the Goal20 planning (commit two) and packaged the fixes.',
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, commits=commits, target_head_at_packaging=two,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA,
                   actual_start='build/migration/goal20a/baseline.json', generated_resource_count=len(stamp['generated']), compiled_classes_verified=len(classes),
                   goal20a_production=since, generated_since_goal20a_start=generated_since, generated_retired=GENERATED_RETIRED,
                   new_language_keys=dict(count=0, english_keys=EN_KEYS, chinese_keys=ZH_KEYS),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA),
                   changed_files=dict(path=changes_path.relative_to(ROOT).as_posix(), sha256=sha(changes_path), count=len(changes)),
                   actual_diff=dict(path=diff_path.relative_to(ROOT).as_posix(), sha256=sha(diff_path)),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), unchanged_since_goal20a_start=True),
                   compare=dict(path=COMPARE.relative_to(ROOT).as_posix(), sha256=sha(COMPARE), impacted_features=impacted),
                   final_suites=dict(path=FINAL_SUMMARY.relative_to(ROOT).as_posix(), sha256=sha(FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   source_report_checks=report_checks, goal20a_reports={'recipes': recipes_report, 'machine': machine_report},
                   run_logs={n: sha(OUT/n) for n in LOGS+AUDITS+('prod-exits.txt',)},
                   jar_delta=delta, jar_directory_delta=dir_delta, class_owners=owners, old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   goal19c_receipt_evidence_unchanged=len(fix_start_protected()), fixes_receipt_evidence_unchanged=len(prior_receipt['evidence_sha256']),
                   reports=REPORTS, report_sha256=hashes, records_not_hashed=[p for p in RECORDS if p not in REPORTS],
                   evidence_sha256={**hashes, changes_path.relative_to(ROOT).as_posix(): sha(changes_path), diff_path.relative_to(ROOT).as_posix(): sha(diff_path),
                                    SNAPSHOT: sha(ROOT/SNAPSHOT), recipes_report: sha(ROOT/recipes_report), machine_report: sha(ROOT/machine_report),
                                    finite_path.relative_to(ROOT).as_posix(): sha(finite_path)},
                   evidence='Windows offline compile/runData/build, isolated production-method checks in stub worlds (crystallizer defaults, sync and JEI bridge; the '
                            'ZIRNOX reactor breeding a TH232 rod with the Goal19B turbine/condenser chain), static generated-recipe and provider checks, exact resources '
                            'and independent JAR bytes. No furnace, crafting table, chemical plant or reactor was run in a game; the ZIRNOX reactor may only be placed '
                            'or run in separately authorized disposable worlds; real save, multiplayer, JEI and dedicated server remain unverified.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the fixes package; %s Goal20A-start changes; %s sources, %s generated files changed, %s retired; %s old JARs preserved.' % (
        len(delta['added']), len(delta['modified']), len(delta['removed']), len(changes), len(since), len(generated_since), len(GENERATED_RETIRED), len(old_releases)))


if __name__ == '__main__':
    main('--check' in sys.argv[1:])
