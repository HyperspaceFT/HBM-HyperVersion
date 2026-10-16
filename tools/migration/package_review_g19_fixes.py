"""Package the three post-Goal19C fixes (ZIRNOX parity, fallout DummyableBlock exclusion, fallout stomp parity) cumulatively on the
goal19c package, without replacing any previous delivery. Goal20A-0.

python -B -X utf8 tools/migration/package_review_g19_fixes.py [--check]

Both modes run every check. --check writes nothing and prints what is still pending. The fixes were committed by Goal20A-0 (commit one:
Goal19B, Goal19C and the fixes; commit two: the Goal20 planning documents), so the packaged tree is the committed HEAD plus the records
this packaging updates (commit ids, package SHA) and this script. The frozen start of the fixes is the ZIRNOX parity start
(build/migration/review-fixes/zirnox-parity/baseline.json), which is the delivered Goal19C tree: every source and generated delta of the
JAR against the goal19c JAR must be explained by the six fix production sources or the three generated files. Evidence of this run is
read from build/migration/goal20a/fixes/ (runData, build, audits, the three verifiers with --jar, validate) and the pre-commit suite
summary from build/migration/goal20a/precommit/summary.json."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import owner_class
from package_goal19a import goal18b_hashed_paths
from package_goal19b import goal19a_hashed_paths
from package_goal19c import protected_drift as goal19c_protected_drift, goal19b_hashed_paths, old_release_files, current_paths, tree_files, git

OUT = ROOT/'build/migration/goal20a'
FIX = OUT/'fixes'
PRECOMMIT = OUT/'precommit/summary.json'
COMMITS = OUT/'commits.json'
FIX_START = ROOT/'build/migration/review-fixes/zirnox-parity/baseline.json'
PREVIOUS = ROOT/'build/migration/releases/goal19c/hbmsntm-198A-goal19c.jar'
PREVIOUS_SHA = 'dc847aa91b20e98de4464d992c9a0b046727f439102b0bcbb2380f6c7bf38005'
PREVIOUS_BYTES = 18107985
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal19c/release.json'
PREVIOUS_RECEIPT_SHA = '4deea63ba06b0714dbf49d3f1c65f5ecaf6b79e440642193079f758afdd21ac4'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal19c/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = '965de67d8e450632643786bec5d1d2ea9f662c47019c48cc9e7e5d9ccc359c59'
PREVIOUS_COMPARE = ROOT/'build/migration/goal19c/compare.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'review-g19-fixes-20261015'
RELEASE_NAME = 'hbmsntm-198A-g19-fixes.jar'
SOURCE_HEAD = 'd31426cbd97ade3bdd852617413f22c23be4fd82'
START_HEAD = '70bc989982eb0f05f54148158428baf2f37caddb'
SNAPSHOT = 'migration/baselines/review-d31426cbd97a.json'
COMPARE = FIX/'compare.json'
DEFERRED_KEYS = 108
AUDITS = ('localization-audit-fixes.json', 'resources-audit-fixes.json', 'packaged-resources-fixes.json')
LOGS = ('runData-fixes.log', 'build-fixes.log')
VERIFIERS = {
    'zirnox-parity': ('tools/migration/verify_review_zirnox_parity.py', 'verify-zirnox-fixes.log'),
    'fallout-dummyable': ('tools/migration/verify_review_fallout_dummyable.py', 'verify-dummyable-fixes.log'),
    'fallout-stomp-parity': ('tools/migration/verify_review_fallout_stomp_parity.py', 'verify-stomp-fixes.log'),
}
FIX_PRODUCTION = ['src/main/java/com/hbm/'+p for p in (
    'blockentity/machine/ZirnoxDestroyedBlockEntity.java',
    'blocks/NtmBlocks.java',
    'blocks/machine/ZirnoxDestroyedBlock.java',
    'datagen/NtmBlockLootTableProvider.java',
    'datagen/NtmBlockTagProvider.java',
    'entity/effect/FalloutRain.java',
)]
FIX_GENERATED = ['src/generated/resources/'+p for p in (
    '.migration-stamp.json',
    'data/hbmsntm/loot_table/blocks/zirnox_destroyed.json',
    'data/minecraft/tags/block/mineable/pickaxe.json',
)]
FIX_TOOLS = ['tools/migration/'+p for p in (
    'verify_review_zirnox_parity.py', 'verify_review_fallout_dummyable.py', 'verify_review_fallout_stomp_parity.py',
    'review_fixes/ZirnoxParityRegression.java', 'review_fixes/FalloutDummyableRegression.java', 'review_fixes/FalloutStompParityRegression.java',
)]
FIX_RECORDS = ['migration/REVIEW-FIXES-ZIRNOX.md', 'migration/REVIEW-FIXES-FALLOUT-DUMMYABLE.md', 'migration/REVIEW-FIXES-FALLOUT-STOMP.md',
               'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md']
PLANNING = ['migration/GOAL20.md', 'migration/GOAL20A.md', 'migration/GOAL20B.md', 'migration/GOAL20C.md', 'migration/GOAL20-THREAD-PROMPTS.md']
THIS = 'tools/migration/package_review_g19_fixes.py'
# Tracked paths that may be dirty against commit two when this runs: the records this packaging updates and this script.
ALLOWED_DIRTY = set(FIX_RECORDS) | {THIS, 'migration/GOAL20A.md'}
# Hashed by the receipt (frozen afterwards): the three fix records and this run's evidence. README, features.json and UPSTREAM-REVIEWS are
# checked for existence and for having been updated, but not hashed, so later batches can keep editing them (goal19c precedent).
REPORTS = FIX_RECORDS[:3] + ['build/migration/goal20a/precommit/summary.json', 'build/migration/goal20a/commits.json']
RECORDS = FIX_RECORDS[3:]


def fix_start_protected():
    start = read(OUT/'baseline.json')
    return {**start['goal19c_receipt_protected_paths'], **start['old_release_files']}


def protected_drift():
    drift = goal19c_protected_drift()
    drift += [f'goal19c receipt or old release: {p}' for p, h in sorted(fix_start_protected().items()) if not (ROOT/p).is_file() or sha(ROOT/p) != h]
    return drift


def assert_writable(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for label, hashed in (('Goal18B', goal18b_hashed_paths()), ('Goal19A', goal19a_hashed_paths()), ('Goal19B', goal19b_hashed_paths())):
        assert rel not in hashed, f'Refusing to write {label} receipt evidence: '+rel
    assert rel not in old_release_files(), 'Refusing to write a previous release file: '+rel
    assert rel not in fix_start_protected(), 'Refusing to write Goal19C receipt evidence or a previous release file: '+rel
    inside = Path(path).resolve().is_relative_to(RELEASE.resolve())
    assert not Path(path).resolve().is_relative_to(RELEASES.resolve()) or inside, 'Refusing to write outside the fixes release directory: '+rel


def report_from_log(log):
    """The report path a verifier printed (its own run directory), relative to ROOT."""
    text = (FIX/log).read_text(encoding='utf-8', errors='replace')
    found = None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('Evidence: '): continue
        candidate = Path(line[len('Evidence: '):].strip().replace('\\', '/'))
        if not candidate.is_absolute(): candidate = ROOT/candidate
        if candidate.is_dir(): candidate = candidate/'report.json'
        if candidate.suffix == '.json' and candidate.is_file() and candidate.resolve().is_relative_to(ROOT):
            found = candidate.resolve().relative_to(ROOT).as_posix()
    assert found, 'No evidence directory printed in '+log
    return found


def main(check):
    pending = []
    base = read(OUT/'baseline.json')
    fix_start = read(FIX_START)

    # 1. Heads, commits and the clean original.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD, 'Unexpected frozen Goal20A start'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    assert COMMITS.is_file(), 'Missing '+COMMITS.relative_to(ROOT).as_posix()+' (the 20A-0 commits have not been recorded)'
    commits = read(COMMITS)
    one, two = commits['commit_one']['id'], commits['commit_two']['id']
    head = git(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == two, f'NEO HEAD {head} is not commit two {two}'
    assert git(ROOT, 'rev-parse', two+'^').strip() == one and git(ROOT, 'rev-parse', one+'^').strip() == START_HEAD, 'Commit chain is not start -> one -> two'
    one_paths = set(git(ROOT, 'diff-tree', '--no-commit-id', '--name-only', '-r', one).split('\n')) - {''}
    two_paths = set(git(ROOT, 'diff-tree', '--no-commit-id', '--name-only', '-r', two).split('\n')) - {''}
    assert one_paths == set(commits['commit_one']['paths']) and two_paths == set(commits['commit_two']['paths']), 'Committed paths differ from commits.json'
    assert two_paths == set(PLANNING) | {'migration/README.md'}, 'Commit two is not the planning documents plus README: '+str(sorted(two_paths))
    assert not (one_paths & set(PLANNING)), 'Commit one contains planning documents'
    expected_one = set(base['uncommitted_paths']) - set(PLANNING)
    assert one_paths == expected_one, 'Commit one differs from the uncommitted start paths minus planning: '+str(sorted(one_paths ^ expected_one))
    dirty = {line[3:] for line in git(ROOT, 'status', '--porcelain=v1', '--untracked-files=all').splitlines()}
    assert dirty <= ALLOWED_DIRTY, 'Unexpected dirty paths at packaging time: '+str(sorted(dirty - ALLOWED_DIRTY))

    # 2. Previous deliveries.
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'Goal19C JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'Goal19C release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'Goal19C SHA256SUMS.txt changed'
    for p, h in base['old_release_files'].items(): assert sha(ROOT/p) == h, 'Previous release file changed: '+p
    drift = protected_drift()
    assert not drift, 'Protected evidence drifted: '+str(drift)
    old_releases = dict(base['old_releases'])
    assert old_releases.get(PREVIOUS.relative_to(ROOT).as_posix()) == PREVIOUS_SHA

    # 3. Changes since the fix start (= the delivered Goal19C tree, whose generated tree equalled the goal19c JAR).
    assert fix_start['build_libs_jar_sha256'] == PREVIOUS_SHA if 'build_libs_jar_sha256' in fix_start else True
    current = current_paths()
    allowed = set(FIX_PRODUCTION) | set(FIX_GENERATED) | set(FIX_TOOLS) | set(FIX_RECORDS) | set(PLANNING) | {THIS, 'migration/GOAL20A.md'}
    changes, diff = [], []
    for p in sorted(current | set(fix_start['files'])):
        path = ROOT/p; before = fix_start['files'].get(p); after = sha(path) if path.is_file() else None
        if before == after: continue
        assert p in allowed, 'Unassigned path changed since the fix start: '+p
        assert after is not None, 'Unexpected deletion: '+p
        changes.append(dict(path=p, status='added' if before is None else 'modified', before_sha256=before, after_sha256=after))
        old_path = ROOT/'build/migration/review-fixes/zirnox-parity/baseline-files'/p
        if not old_path.is_file():
            old_path = ROOT/'build/migration/goal20a/baseline-files'/p
        try:
            old_lines = old_path.read_text(encoding='utf-8').splitlines(keepends=True) if old_path.is_file() and before == sha(old_path) else None
            new_lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
        except UnicodeDecodeError:
            old_lines, new_lines = None, None
        if new_lines is None:
            diff.append(f'Binary file g19-fixes/{p}: {before or "absent"} -> {after}\n')
        elif old_lines is None and before is not None:
            diff.append(f'No frozen copy of g19-fixes/{p} at the fix start: {before} -> {after}\n')
        else:
            diff.extend(difflib.unified_diff(old_lines or [], new_lines, 'g19-fixes-start/'+p, 'g19-fixes/'+p))
    since = sorted(p for p in tree_files('src/main') if fix_start['files'].get(p) != sha(ROOT/p))
    assert since == sorted(FIX_PRODUCTION), 'Sources since the fix start differ from the six fix sources: '+str(since)
    generated_since = sorted(p for p in current if p.startswith('src/generated/') and fix_start['files'].get(p) != sha(ROOT/p))
    assert generated_since == sorted(FIX_GENERATED), 'Generated change since the fix start: '+str(generated_since)
    removed = sorted(p for p in fix_start['files'] if p.startswith(('src/main/', 'src/generated/')) and not (ROOT/p).is_file())
    assert not removed, 'Removed since the fix start: '+str(removed)

    # 4. This run's build, audits, validate and verifiers.
    for name in LOGS:
        assert 'BUILD SUCCESSFUL' in (FIX/name).read_text(encoding='utf-8-sig', errors='replace'), 'Missing successful '+name
    for name in AUDITS:
        audit = read(FIX/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
    assert read(FIX/'localization-audit-fixes.json')['coverage']['deferred_keys'] == DEFERRED_KEYS, 'Deferred localization count changed'
    exits = dict(l.split('=') for l in (FIX/'exits.txt').read_text(encoding='utf-8').split())
    assert all(v == '0' for v in exits.values()), 'A fixes-run command failed: '+str(exits)
    verifier_reports = {}
    for key, (tool, log) in VERIFIERS.items():
        report_path = report_from_log(log)
        report = read(ROOT/report_path)
        for p, h in report['production_sha256'].items():
            assert sha(ROOT/'src/main/java'/p) == h, f'{key} verifier ran on another {p}'
        assert report.get('jar') is not None, key+' verifier did not run with --jar'
        verifier_reports[key] = dict(tool=tool, log=(FIX/log).relative_to(ROOT).as_posix(), log_sha256=sha(FIX/log), report=report_path, sha256=sha(ROOT/report_path))
    precommit = read(PRECOMMIT)
    assert precommit['ok'] and not precommit['stop'] and not precommit['protected_drift'], 'Pre-commit suite run has unexplained results: '+str(precommit['stop'])
    assert len(precommit['suites']) == 62, 'Pre-commit run did not cover 62 suites'

    # 5. Generation stamp and JAR contents.
    stamp = read(ROOT/'src/generated/resources/.migration-stamp.json')
    assert all((ROOT/p).is_file() and normalized_sha(ROOT/p) == h for p, h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p) == h for p, h in stamp['generated'].items()), 'Generated stamp stale'
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    assert java_now <= set(stamp['inputs']), 'Unrecorded Java generation input: '+str(sorted(java_now-set(stamp['inputs'])))
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
        for entry in ('assets/hbmsntm/lang/en_us.json', 'assets/hbmsntm/lang/zh_cn.json'):
            assert jar.read(entry) == prior.read(entry), 'Language file changed although the fixes add no text: '+entry
        old = {i.filename for i in prior.infolist() if not i.is_dir()}
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
        dir_delta = {'added': sorted({i.filename for i in jar.infolist() if i.is_dir()} - {i.filename for i in prior.infolist() if i.is_dir()}),
                     'removed': sorted({i.filename for i in prior.infolist() if i.is_dir()} - {i.filename for i in jar.infolist() if i.is_dir()})}

    # 6. JAR delta against the goal19c JAR: every change is owned by a fix source or a fix generated file.
    assert not delta['added'] and not delta['removed'] and not dir_delta['added'] and not dir_delta['removed'], 'The fixes add or remove JAR entries: '+str(delta)+str(dir_delta)
    since_set, generated_set = set(since), set(generated_since)
    unexplained = [n for n in delta['modified'] if not ((n.endswith('.class') and owner_class(n) in since_set) or 'src/generated/resources/'+n in generated_set)]
    assert not unexplained, 'Unexplained JAR change: '+str(unexplained)
    owners = sorted({owner_class(n) for n in delta['modified'] if n.endswith('.class')})
    assert set(owners) == since_set, 'Not every fix source changed a class: '+str(sorted(since_set - set(owners)))

    # 7. Snapshot and compare.json (written by the main agent after the build, on the committed tree).
    assert base['files'].get(SNAPSHOT) == sha(ROOT/SNAPSHOT) and fix_start['files'].get(SNAPSHOT) == sha(ROOT/SNAPSHOT), 'Snapshot changed'
    impacted = {}
    if check:
        if not COMPARE.is_file(): pending.append('compare '+COMPARE.relative_to(ROOT).as_posix())
        pending += ['records (unchanged since commit two): '+p for p in FIX_RECORDS if git(ROOT, 'status', '--porcelain=v1', '--', p) == '']
    if COMPARE.is_file():
        compare = read(COMPARE)
        assert compare['kind'] == 'migration-delta', 'compare.json is not a migration delta'
        assert compare['baseline_source_commit'] == compare['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the d31426c snapshot'
        assert not any(compare['changes']['source'][k] for k in ('added', 'removed', 'modified')), 'compare.json reports source changes'
        for side in ('source', 'target'): assert not compare['unmapped_changes'][side], 'compare.json reports unmapped '+side+' changes'
        assert not compare['removed_feature_ids'] and not compare['manifest_missing_files'], 'compare.json reports removed features or missing files'
        target = compare['changes']['target']
        def paths(entries): return {e['path'] if isinstance(e, dict) else e for e in entries}
        assert not target['removed'], 'compare.json reports removed target files'
        previous_compare = read(PREVIOUS_COMPARE)['changes']['target']
        expected = paths(previous_compare['added']) | paths(previous_compare['modified']) | since_set | {p for p in FIX_GENERATED if not p.endswith('/.migration-stamp.json')}
        assert paths(target['added']) | paths(target['modified']) == expected, 'compare.json target changes differ from the goal19c compare plus the fixes: '+str(
            sorted((paths(target['added']) | paths(target['modified'])) ^ expected))
        impacted = {f['id']: {k: f[k] for k in ('state', 'mapping_changed', 'source', 'target', 'upstream_changed_dependencies') if k in f}
                    for f in compare['features'] if f['state'] != 'no-observed-file-change' or f['mapping_changed'] or f['source'] or f['target'] or f['upstream_changed_dependencies']}
    elif not check:
        raise AssertionError('Missing '+COMPARE.relative_to(ROOT).as_posix())

    summary = dict(jar_delta={k: len(v) for k, v in delta.items()}, changes_since_fix_start=len(changes), sources_changed=len(since), generated_changed=len(generated_since),
                   compiled_classes_verified=len(classes), generated_resource_count=len(stamp['generated']), old_releases_preserved=len(old_releases),
                   precommit_suites=len(precommit['suites']), commit_one=one, commit_two=two, jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check passed; nothing written. Pending:')
        for item in pending: print('  '+item)
        return

    for p in REPORTS+RECORDS: assert (ROOT/p).is_file(), 'Missing record: '+p
    stale = [p for p in FIX_RECORDS if git(ROOT, 'status', '--porcelain=v1', '--', p) == '']
    assert not stale, 'Records not updated with the commit ids and package SHA: '+str(stale)
    changes_path = FIX/'g19-fixes-changed-files.json'; diff_path = FIX/'g19-fixes-actual-diff.patch'
    for target in (changes_path, diff_path, RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json'): assert_writable(target)
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    diff_path.write_text(''.join(diff), encoding='utf-8', newline='\n')
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different fixes JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest != PREVIOUS_SHA, 'The fixes JAR is the Goal19C JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in REPORTS}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified',
                   scope='Post-Goal19C fixes packaged cumulatively on goal19c: ZIRNOX parity (strength 5/100 and 100/800, wreck scrap loot, mineable/pickaxe '
                         'tag, wreck proxy flags, onFire key), fallout rain DummyableBlock exclusion, fallout stomp parity (layer liquid test, inner-loop falling '
                         'position). No new player-visible text.',
                   meltdown_warning=read(PREVIOUS_RECEIPT)['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, commits=commits, target_head_at_packaging=head,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA,
                   fix_start='build/migration/review-fixes/zirnox-parity/baseline.json', goal20a_start='build/migration/goal20a/baseline.json',
                   generated_resource_count=len(stamp['generated']), compiled_classes_verified=len(classes),
                   fix_production=since, generated_since_fix_start=generated_since, fix_tools=FIX_TOOLS,
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA),
                   changed_files=dict(path=changes_path.relative_to(ROOT).as_posix(), sha256=sha(changes_path), count=len(changes)),
                   actual_diff=dict(path=diff_path.relative_to(ROOT).as_posix(), sha256=sha(diff_path)),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), unchanged_since_fix_start=True),
                   compare=dict(path=COMPARE.relative_to(ROOT).as_posix(), sha256=sha(COMPARE), impacted_features=impacted),
                   precommit_suites=dict(path=PRECOMMIT.relative_to(ROOT).as_posix(), sha256=sha(PRECOMMIT), suites=len(precommit['suites']), ok=precommit['ok']),
                   verifiers=verifier_reports, run_logs={n: sha(FIX/n) for n in LOGS+AUDITS+('exits.txt',)},
                   jar_delta=delta, jar_directory_delta=dir_delta, class_owners=owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   goal19c_release=dict(jar=PREVIOUS_SHA, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA, receipt_evidence_unchanged=len(fix_start_protected())),
                   reports=REPORTS, report_sha256=hashes, records_not_hashed=RECORDS,
                   evidence_sha256={**hashes, changes_path.relative_to(ROOT).as_posix(): sha(changes_path), diff_path.relative_to(ROOT).as_posix(): sha(diff_path),
                                    SNAPSHOT: sha(ROOT/SNAPSHOT), COMPARE.relative_to(ROOT).as_posix(): sha(COMPARE),
                                    **{v['report']: v['sha256'] for v in verifier_reports.values()}, **{v['log']: v['log_sha256'] for v in verifier_reports.values()}},
                   evidence='Windows offline runData/build, the three fix verifiers with --jar (static source/generated checks, javap, extracted-production-method '
                            'harnesses), the 62-suite pre-commit rerun, exact resources and independent JAR bytes. No game, server, real save, multiplayer or '
                            'dedicated-server run; the ZIRNOX reactor may only be placed or run in separately authorized disposable worlds.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against goal19c; %s fix-start changes; %s sources and %s generated files; %s old JARs preserved.' % (
        len(delta['added']), len(delta['modified']), len(delta['removed']), len(changes), len(since), len(generated_since), len(old_releases)))


if __name__ == '__main__':
    main('--check' in sys.argv[1:])
