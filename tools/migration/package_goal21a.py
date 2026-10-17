"""Package Goal21A (upstream d31426c..6a11998d review, four machine texture reimports, four Leviathan fixes, the balefire bomb fix, the
review-6a11998d5852 snapshot)
cumulatively on the review-g20-display-fixes-20261016 package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal21a.py [--check]

Both modes run every check. --check writes nothing and prints what is still pending (missing chain evidence, records, snapshot or compare
results). The frozen Goal21A start is build/migration/goal21a/baseline.json (NEO HEAD dbfa6746 = the Goal 21 planning commit, clean tree);
Goal21A commits nothing, so every change since the start is `git diff --name-status dbfa6746` plus the untracked files, and each must be in
the owner table below. Every JAR delta against the display-fix JAR must be one of the four PNGs, the two language files or a class of the
five changed Java sources. Writes only build/migration/releases/goal21a/ (the JAR, SHA256SUMS.txt, release.json)."""
from pathlib import Path
import json
import re
import shutil
import sys
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import owner_class
from package_goal19c import tree_files, git
from package_review_g20_display_fixes import protected_drift as display_protected_drift, split_drift, ACCEPTANCE_CHECKLISTS

OUT = ROOT/'build/migration/goal21a'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
PREVIOUS = ROOT/'build/migration/releases/review-g20-display-fixes-20261016/hbmsntm-198A-g20-display-fixes.jar'
PREVIOUS_SHA = 'e85d8277484eadd0f9642078452720b8baa69a20d118d6662655c6eaf41c85cf'
PREVIOUS_BYTES = 18303149
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/review-g20-display-fixes-20261016/release.json'
PREVIOUS_RECEIPT_SHA = '30836ee4744abc1fd4516d706fb2354eee33fa77f1058698b7a23f40da64bcba'
PREVIOUS_SUMS = ROOT/'build/migration/releases/review-g20-display-fixes-20261016/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = 'c583985625eacda5291f5b207f4f921dfe0ab5c6ddd1211c07114ae78b91ebd4'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal21a'
RELEASE_NAME = 'hbmsntm-198A-goal21a.jar'
SOURCE_HEAD = '6a11998d5852ff3da326f0130357e10431ae3839'
OBSERVED_SOURCE = 'd31426cbd97ade3bdd852617413f22c23be4fd82'
START_HEAD = 'dbfa6746f9728bb551bfdfdaaedca3edaa42ba13'
OLD_SNAPSHOT = 'migration/baselines/review-d31426cbd97a.json'
SNAPSHOT = 'migration/baselines/review-6a11998d5852.json'
CLASSIFICATION = 'migration/goal21a-upstream-classification.json'
STAMP = 'src/generated/resources/.migration-stamp.json'
EN = 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
# commits.json was hashed by the display-fix receipt before commit_two (4d02ccdf) was recorded into it (baseline explained_previous_drift);
# it is accepted only at the hash it has had since then.
COMMITS = 'build/migration/review-fixes-g20-display/commits.json'
COMMITS_SHA = '08b26a3169564433ec3caee828f0523033b626b5f536689554dec45b2e0b9fa1'
COMMIT_TWO = '4d02ccdfbfd6e5dfc3fc2713a1b6d85b5bfb94b2'
KEY = 'machine_chungus.compressor_locked'
EN_TEXT = 'Cannot change compressor setting while operational!'
ZH_TEXT = '运行中无法更改压缩机设置！'
TEXTURES = ('battery_socket', 'chungus', 'industrial_turbine', 'wood_burner')
TEX = 'src/main/resources/assets/hbmsntm/textures/models/machines/%s.png'
ORIGINAL_TEX = 'src/main/resources/assets/hbm/textures/models/machines/%s.png'
ORIGINAL_BALEFIRE = 'src/main/java/com/hbm/tileentity/bomb/TileEntityNukeBalefire.java'
JAVA = ['src/main/java/com/hbm/'+p for p in (
    'blocks/machine/MachineChungusBlock.java', 'render/blockentity/RenderChungus.java', 'blockentity/machine/ChungusBlockEntity.java',
    'datagen/NtmLanguageProvider.java', 'blockentity/bomb/NukeBalefireBlockEntity.java')]
PRODUCTION = [TEX % n for n in TEXTURES] + JAVA + [ZH_INPUT]
GENERATED = [EN, STAMP]
LOCALIZATION_RECORD = ['migration/localization/zh_cn-map.json']
TOOLS = ['tools/migration/verify_goal21a_leviathan.py', 'tools/migration/verify_goal21a_balefire.py', 'tools/migration/package_goal21a.py']
BATCH_RECORDS = ['migration/goal21a-upstream-classification.json', 'migration/goal21a-resource-ownership.json', 'migration/goal21a-localization-review.json',
                 'migration/goal21a-static-review.md', 'migration/GOAL21A-ACCEPTANCE.md', 'migration/GOAL21A.md']
SHARED_RECORDS = ['migration/GOAL21.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md',
                  'migration/RESOURCE-OWNERSHIP.md']
OWNERS = {
    'production': PRODUCTION,
    'generated': GENERATED,
    'localization-record': LOCALIZATION_RECORD,
    'tools': TOOLS,
    'snapshot': [SNAPSHOT],
    'records': BATCH_RECORDS + SHARED_RECORDS,
}
# Must have changed (or been added) by the time of the real run; the rest of the owner table is optional.
REQUIRED_CHANGES = PRODUCTION + GENERATED + LOCALIZATION_RECORD + TOOLS + [SNAPSHOT] + BATCH_RECORDS + ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md',
                                                                                              'migration/features.json']
# Hashed by the receipt (frozen afterwards): this batch's own records.
REPORTS = BATCH_RECORDS
NAMES_RELEASE = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
EVIDENCE = ['chain-exits.txt', 'runData.log', 'gametest.log', 'build.log', 'localization-audit.json', 'resources-audit.json', 'packaged-resources.json',
            'validate.log', 'upstream-delta.json', 'compare-old-final.json', 'compare-new.json', 'verify/leviathan-report.json',
            'verify/balefire-report.json', 'final/summary.json', 'baseline.json']
LOGS = ('runData.log', 'gametest.log', 'build.log')
AUDITS = ('localization-audit.json', 'resources-audit.json', 'packaged-resources.json')
GAMETEST = re.compile(r'All (\d+) required tests passed')
FINAL_SUITES = 70
SCOPE = ('Goal21A: the original d31426c..6a11998d delta classified file by file (five adapted: the textures and the balefire bomb); four '
         'machine model textures (battery_socket, chungus, industrial_turbine, wood_burner) reimported byte-for-byte from the original at '
         '6a11998d (upstream electric port redraw, b67f35e7); four Leviathan fixes: MachineChungusBlock CODEC typed as its own class, the '
         'compressor lock message as language key machine_chungus.compressor_locked (English as the original, Chinese as the industrial '
         'turbine), the lever angle via Fluids.STEAM.getID() (STEAM id 2, angle unchanged), and the original infinite render bounding box '
         'wired through RenderChungus (plus shouldRenderOffScreen); the balefire bomb (NukeBalefireBlockEntity) explodes only while started and '
         'accepts setTimer only for 1..999 on the server, as the original TileEntityNukeBalefire; the review-6a11998d5852 observation snapshot.')


def assert_writable(path, base, prior_receipt):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for label, hashed in (('display-fix receipt', base['previous_receipt_protected_paths']), ('goal20c receipt', base['goal20c_receipt_protected_paths']),
                          ('display-fix acceptance records', prior_receipt['acceptance_records'])):
        assert rel not in hashed, f'Refusing to write {label} evidence: '+rel
    assert rel not in base['old_release_files'], 'Refusing to write a previous release file: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal21a release directory: '+rel


def changed_paths():
    """{path: status} since the start commit: tracked changes plus untracked files (Goal21A commits nothing)."""
    out = {}
    for line in git(ROOT, 'diff', '--name-status', '--no-renames', START_HEAD).splitlines():
        status, path = line.split('\t', 1)
        out[path] = status
    for path in git(ROOT, 'ls-files', '-z', '--others', '--exclude-standard').split('\0'):
        if path: out[path] = '??'
    return out


def lang_delta(old, new):
    return dict(added=sorted(set(new)-set(old)), removed=sorted(set(old)-set(new)), changed=sorted(k for k in set(old) & set(new) if old[k] != new[k]))


def compare_paths(entries):
    return {e['path'] if isinstance(e, dict) else e for e in entries}


def main(check):
    pending = []
    base = read(BASELINE)
    prior_receipt = read(PREVIOUS_RECEIPT)

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal21A commits nothing).
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD and base['observed_source'] == OBSERVED_SOURCE, 'Unexpected frozen start'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == START_HEAD, 'NEO HEAD moved during Goal21A: '+head

    # 2. Previous deliveries: the display-fix package, every old release file, and the protected evidence of the older receipts.
    assert base['previous_release'] == dict(path=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES), 'Baseline names another previous release'
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'display-fix JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'display-fix release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'display-fix SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'display-fix SHA256SUMS.txt content changed'
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    for p, h in base['old_release_files'].items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release file changed: '+p
    old_releases = dict(base['old_releases'])
    assert old_releases.get(PREVIOUS.relative_to(ROOT).as_posix()) == PREVIOUS_SHA
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    explained_previous = {}
    for p, h in sorted(base['previous_receipt_protected_paths'].items()):
        now = sha(ROOT/p) if (ROOT/p).is_file() else None
        if now == h: continue
        assert p == COMMITS and p in base['explained_previous_drift'], 'display-fix receipt evidence drifted: '+p
        assert now == COMMITS_SHA and read(ROOT/p)['commit_two']['id'] == COMMIT_TWO, 'commits.json is not at its recorded post-commit-two hash'
        explained_previous[p] = dict(receipt_sha256=h, sha256_now=now, explanation=base['explained_previous_drift'][p])
    goal20c_drift = {}
    for p, h in sorted(base['goal20c_receipt_protected_paths'].items()):
        now = sha(ROOT/p) if (ROOT/p).is_file() else None
        if now == h: continue
        assert p in base['goal20c_drift_explained'], 'goal20c receipt evidence drifted: '+p
        assert now == prior_receipt['acceptance_records'].get(p), 'goal20c checklist differs from the display-fix receipt acceptance record: '+p
        goal20c_drift[p] = dict(goal20c_sha256=h, display_fix_sha256=now, explanation='dated 2026-10-16 acceptance result lines (display-fix receipt acceptance_drift_explained)')
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    for p in ACCEPTANCE_CHECKLISTS:
        assert sha(ROOT/p) == prior_receipt['acceptance_records'][p], 'Acceptance checklist changed after the display-fix receipt: '+p

    # 3. Changes since the start: each path in the owner table.
    changes = changed_paths()
    allowed = {p: g for g, paths in OWNERS.items() for p in paths}
    unassigned = sorted(p for p in changes if p not in allowed)
    assert not unassigned, 'Unassigned path changed since the Goal21A start: '+str(unassigned)
    deleted = sorted(p for p, s in changes.items() if s.startswith('D'))
    assert not deleted, 'Deleted since the Goal21A start: '+str(deleted)
    missing_required = [p for p in REQUIRED_CHANGES if p not in changes]
    for p in missing_required:
        if check or p in SHARED_RECORDS + BATCH_RECORDS + [SNAPSHOT]:
            pending.append('change not present yet: '+p)
    if not check:
        assert not missing_required, 'Required Goal21A changes missing: '+str(missing_required)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    assert set(since) <= set(PRODUCTION), 'src/main change outside the production list: '+str(sorted(set(since) - set(PRODUCTION)))
    for p in ('build.gradle', 'gradle.lockfile', 'gradle.properties'): assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, git_status=s, group=allowed[p], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]

    # 4. Generated tree: en_us.json gains exactly the one key, plus the stamp; the stamp is current.
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    assert set(generated_since) <= set(GENERATED), 'Generated change outside en_us.json and the stamp: '+str(generated_since)
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    en_delta = lang_delta(en_start, en_now)
    if en_delta == dict(added=[], removed=[], changed=[]):
        if not check: raise AssertionError('en_us.json not regenerated (run runData)')
        pending.append('generated en_us.json lacks '+KEY+' (runData)')
    else:
        assert en_delta == dict(added=[KEY], removed=[], changed=[]) and en_now[KEY] == EN_TEXT, 'en_us.json delta is not exactly the one key: '+str(en_delta)
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    assert not stale and not mismatch and not unrecorded, f'Stamp not current: stale {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}'
    assert len(stamp['generated']) == prior_receipt['generated_resource_count'], 'Generated resource count changed from the display-fix package'

    # 5. Chain evidence (runData, GameTest, build, audits, validate) and the final suite run.
    missing_evidence = [n for n in EVIDENCE if not (OUT/n).is_file()]
    if missing_evidence:
        if not check: raise AssertionError('Missing evidence: '+str(missing_evidence))
        pending += ['evidence: build/migration/goal21a/'+n for n in missing_evidence]
    gametest_line = None
    audit_summaries = {}
    # The chain truncates chain-exits.txt when it starts, so all seven exit codes mean this chain run finished; while it runs, --check
    # reports it pending instead of reading half-written logs.
    exits = dict(l.split('=') for l in (OUT/'chain-exits.txt').read_text(encoding='utf-8').split()) if (OUT/'chain-exits.txt').is_file() else {}
    assert all(v == '0' for v in exits.values()), 'A chain command failed: '+str(exits)
    finished = set(exits) >= {'runData', 'gametest', 'build', 'loc', 'audit', 'jar', 'validate'} and (OUT/'chain-done.txt').is_file()
    if not finished:
        if not check: raise AssertionError('Chain not finished: '+str(exits))
        pending.append('chain not finished: '+str(exits))
    else:
        assert (OUT/'jar.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain'
        for name in LOGS:
            assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), 'Missing successful '+name
        text = (OUT/'gametest.log').read_text(encoding='utf-8-sig', errors='replace')
        found = GAMETEST.findall(text)
        assert found and 'invalid dist' not in text and 'NoClassDefFoundError' not in text, 'GameTest run did not pass cleanly'
        gametest_line = f'All {found[-1]} required tests passed'
        for name in AUDITS:
            audit = read(OUT/name)
            bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
            assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
            audit_summaries[name] = audit['summary']
    for name in ('verify/leviathan-report.json', 'verify/balefire-report.json'):
        if (OUT/name).is_file():
            report = read(OUT/name)
            if not (report['ok'] and report['final']):
                if not check: raise AssertionError(name+' is not a passing --final run')
                pending.append('%s is not a passing --final run (ok=%s, final=%s)' % (name, report['ok'], report['final']))
    if (OUT/'verify/balefire-report.json').is_file():
        bale = read(OUT/'verify/balefire-report.json')
        detected, total = (int(x) for x in bale['mutations_detected'].split('/'))
        assert detected == total >= 6 and all(m['detected'] and m['static_detected'] and m['compiled']['detected'] for m in bale['mutations']),             'balefire mutations not all detected: '+bale['mutations_detected']
    final = None
    if (OUT/'final/summary.json').is_file():
        final = read(OUT/'final/summary.json')
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == FINAL_SUITES, f'Final run did not cover {FINAL_SUITES} suites'
        for suite in ('verify_goal21a_leviathan.py --final', 'verify_goal21a_balefire.py --final'):
            entry = final['suites'][suite]
            assert entry['status'] == 'as-expected' and entry['exit'] == 0, suite+' did not pass in the final run'

    # 6. JAR: build/libs is what gets packaged; delta against the display-fix JAR.
    jar_delta = dir_delta = owners = language = None
    if sha(JAR) == PREVIOUS_SHA:
        if not check: raise AssertionError('build/libs JAR is still the display-fix JAR (run build)')
        pending.append('build/libs/hbmsntm-198A.jar is still the display-fix JAR')
    else:
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        assert classes and len(classes) == prior_receipt['compiled_classes_verified'], f'Compiled class count {len(classes)} differs from the display-fix package'
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            for p in stamp['generated']: assert jar.read(p) == (ROOT/'src/generated/resources'/p).read_bytes(), p
            assert jar.read('assets/hbmsntm/lang/zh_cn.json') == (ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
            for path in classes:
                name = path.relative_to(classes_root).as_posix()
                assert jar.read(name) == path.read_bytes(), name
            for n in TEXTURES:
                entry = (TEX % n)[len('src/main/resources/'):]
                assert jar.read(entry) == (ROOT/(TEX % n)).read_bytes() == (SOURCE/(ORIGINAL_TEX % n)).read_bytes(), 'Packaged texture is not the original HEAD bytes: '+entry
            en_jar = lang_delta(json.loads(prior.read('assets/hbmsntm/lang/en_us.json')), json.loads(jar.read('assets/hbmsntm/lang/en_us.json')))
            zh_jar = lang_delta(json.loads(prior.read('assets/hbmsntm/lang/zh_cn.json')), json.loads(jar.read('assets/hbmsntm/lang/zh_cn.json')))
            assert en_jar == zh_jar == dict(added=[KEY], removed=[], changed=[]), f'JAR language delta: en {en_jar}, zh {zh_jar}'
            assert json.loads(jar.read('assets/hbmsntm/lang/zh_cn.json'))[KEY] == ZH_TEXT
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            dir_delta = {'added': sorted({i.filename for i in jar.infolist() if i.is_dir()} - {i.filename for i in prior.infolist() if i.is_dir()}),
                         'removed': sorted({i.filename for i in prior.infolist() if i.is_dir()} - {i.filename for i in jar.infolist() if i.is_dir()})}
        assert not jar_delta['added'] and not jar_delta['removed'] and not dir_delta['added'] and not dir_delta['removed'], 'JAR entries added or removed: '+str(jar_delta)+str(dir_delta)
        resources = sorted([(TEX % n)[len('src/main/resources/'):] for n in TEXTURES] + ['assets/hbmsntm/lang/en_us.json', 'assets/hbmsntm/lang/zh_cn.json'])
        unexplained = [n for n in jar_delta['modified'] if not ((n.endswith('.class') and owner_class(n) in JAVA) or n in resources)]
        assert not unexplained, 'Unexplained JAR change: '+str(unexplained)
        assert sorted(n for n in jar_delta['modified'] if not n.endswith('.class')) == resources, 'Modified JAR resources: '+str(
            [n for n in jar_delta['modified'] if not n.endswith('.class')])
        owners = sorted({owner_class(n) for n in jar_delta['modified'] if n.endswith('.class')})
        assert owners == sorted(JAVA), 'Not every changed Java source changed a class: '+str(sorted(set(JAVA) - set(owners)))
        language = dict(en=en_jar, zh=zh_jar)

    # 7. Records, snapshot and both compare results.
    textures = {}
    for n in TEXTURES:
        textures[TEX % n] = dict(old_sha256=sha(START_FILES/(TEX % n)), old_bytes=(START_FILES/(TEX % n)).stat().st_size,
                                 new_sha256=sha(ROOT/(TEX % n)), new_bytes=(ROOT/(TEX % n)).stat().st_size, original=ORIGINAL_TEX % n)
        assert textures[TEX % n]['old_sha256'] == base['files'][TEX % n] != textures[TEX % n]['new_sha256'], 'Texture not reimported: '+n
    compares = {}
    if (ROOT/CLASSIFICATION).is_file() and (OUT/'compare-old-final.json').is_file():
        cls = read(ROOT/CLASSIFICATION)
        cmp_old = read(OUT/'compare-old-final.json')
        assert cmp_old['kind'] == 'migration-delta' and cmp_old['baseline_source_commit'] == OBSERVED_SOURCE and cmp_old['current_source_commit'] == SOURCE_HEAD, \
            'compare-old-final.json is not d31426c -> 6a11998d'
        src = cmp_old['changes']['source']
        paths = compare_paths(src['added']) | compare_paths(src['modified']) | compare_paths(src['removed'])
        moves = len(src.get('same_content_move_candidates', []))
        entries = cls['entries']
        # A rename is one classification entry (change 'renamed', git -M), so the entry count is the compare file count minus its moves.
        assert len(entries) == len(paths) - moves, f'classification has {len(entries)} entries, compare reports {len(paths)} source files ({moves} move candidates)'
        renamed = sorted(e['path'] for e in entries if e.get('change') == 'renamed')
        assert renamed == sorted(t for m in src.get('same_content_move_candidates', []) for t in m['to_candidates']), 'renamed entries differ from the compare moves: '+str(renamed)
        categories = {}
        for e in entries: categories[e['category']] = categories.get(e['category'], 0) + 1
        assert cls['summary'] == categories, 'classification summary differs from its entries'
        # Goal21A adapts exactly the four reimported textures and the balefire bomb (TileEntityNukeBalefire -> NukeBalefireBlockEntity).
        adapted = sorted(e['path'] for e in entries if e['category'] == 'neo-adapt-21a')
        assert adapted == sorted([ORIGINAL_TEX % n for n in TEXTURES] + [ORIGINAL_BALEFIRE]), 'neo-adapt-21a entries: '+str(adapted)
        blob = json.dumps(entries, ensure_ascii=False)
        unclassified = sorted(p for p in paths if p not in {e['path'] for e in entries} and p not in blob)
        assert not unclassified, 'Source changes without a classification entry: '+str(unclassified)
        assert cls['reviewed_source_commit'] == SOURCE_HEAD and cls['baseline_source_commit'] == OBSERVED_SOURCE, 'classification commits'
        compares['old'] = dict(path=(OUT/'compare-old-final.json').relative_to(ROOT).as_posix(), sha256=sha(OUT/'compare-old-final.json'),
                               source={k: len(v) for k, v in src.items()}, target={k: len(v) for k, v in cmp_old['changes']['target'].items()},
                               source_files=len(paths), classification_entries=len(entries))
    elif check:
        pending.append('compare against the old baseline / classification not both present')
    else:
        raise AssertionError('Missing classification or compare-old-final.json')
    if (ROOT/SNAPSHOT).is_file() and (OUT/'compare-new.json').is_file():
        snap = read(ROOT/SNAPSHOT)
        assert snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '', 'snapshot is not of the clean original at 6a11998d'
        cmp_new = read(OUT/'compare-new.json')
        assert cmp_new['baseline_source_commit'] == cmp_new['current_source_commit'] == SOURCE_HEAD, 'compare-new.json is not against the 6a11998d snapshot'
        counts = {side: {k: len(cmp_new['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        assert all(v == 0 for side in counts.values() for v in side.values()), 'compare-new.json is not 0/0/0 on both sides: '+str(counts)
        compares['new'] = dict(path=(OUT/'compare-new.json').relative_to(ROOT).as_posix(), sha256=sha(OUT/'compare-new.json'), counts=counts)
    elif check:
        pending.append('snapshot '+SNAPSHOT+' / compare-new.json not both present')
    else:
        raise AssertionError('Missing snapshot or compare-new.json')
    assert sha(ROOT/OLD_SNAPSHOT) == base['files'][OLD_SNAPSHOT], 'Old snapshot changed'
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    if unnamed:
        if not check: raise AssertionError('Records do not name '+RELEASE_NAME+': '+str(unnamed))
        pending += ['records (do not name '+RELEASE_NAME+'): '+p for p in unnamed]
    missing_reports = [p for p in REPORTS if not (ROOT/p).is_file()]
    if missing_reports:
        if not check: raise AssertionError('Missing records: '+str(missing_reports))
        pending += ['records: '+p for p in missing_reports]
    if not check:
        assert base['files'].get('migration/GOAL21A.md') != sha(ROOT/'migration/GOAL21A.md'), 'GOAL21A.md has no delivery record'

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, en_delta=en_delta,
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, class_owners=owners, gametest=gametest_line,
                   compares={k: v.get('counts', v.get('source_files')) for k, v in compares.items()}, old_releases_preserved=len(old_releases),
                   preserved_release_files=len(base['old_release_files']), explained_previous_drift=sorted(explained_previous), goal20c_drift=sorted(goal20c_drift),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending:' if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    for target in (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json'): assert_writable(target, base, prior_receipt)
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different goal21a JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest == sha(JAR) and digest != PREVIOUS_SHA, 'Packaged JAR is not build/libs or is the display-fix JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in REPORTS if (ROOT/p).is_file()}
    evidence = {(OUT/n).relative_to(ROOT).as_posix(): sha(OUT/n) for n in EVIDENCE}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified', scope=SCOPE,
                   radiation_warning=prior_receipt['radiation_warning'], meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, observed_source_commit=OBSERVED_SOURCE, target_start_commit=START_HEAD, planning_commit=START_HEAD,
                   commits={}, target_head_at_packaging=head, base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(), generated_resource_count=len(stamp['generated']),
                   compiled_classes_verified=prior_receipt['compiled_classes_verified'], production=PRODUCTION, sources_changed=since,
                   generated_since_start=generated_since, changed_files=change_list, textures=textures,
                   language=dict(key=KEY, en=EN_TEXT, zh=ZH_TEXT, jar_delta=language),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA),
                   explained_previous_drift=explained_previous, goal20c_drift_explained=goal20c_drift, older_checklist_drift_explained=sorted(explained),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT)), old_snapshot=dict(path=OLD_SNAPSHOT, sha256=sha(ROOT/OLD_SNAPSHOT)), compare=compares,
                   final_suites=dict(path='build/migration/goal21a/final/summary.json', sha256=sha(OUT/'final/summary.json'), suites=len(final['suites']), ok=final['ok']),
                   gametest=dict(log='build/migration/goal21a/gametest.log', sha256=sha(OUT/'gametest.log'), result=gametest_line,
                                 note='GameTest dedicated server (real world engine, no client classes); the Goal21A changes are textures, a chat '
                                      'message key, client rendering and the balefire timer, which no GameTest exercises.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, class_owners=owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=REPORTS, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + LOCALIZATION_RECORD,
                   evidence_sha256={**hashes, **evidence, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the resource, packaged-resource and localization audits, '
                            'validate, the static Leviathan verifier with in-memory fallback mutations, the final old-suite rerun, both compare runs and '
                            'independent JAR bytes (four original textures, one language key, classes of the five changed sources, the balefire stub-world harness). No client, real '
                            'save, multiplayer or player interaction was run: the textures, the lock message, the lever angle and the render bounding '
                            'box are unverified in game.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the display-fix package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    main('--check' in sys.argv[1:])
