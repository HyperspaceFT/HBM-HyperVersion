"""Package Goal21C (ZIRNOX meltdown instant effects: the zirnox_debris entity, 72 per meltdown, and its renderer, ExplosionNukeGeneric.waste
of radius 35, the original meltdown() order, ZirnoxMeltdownGameTests) cumulatively on the goal21b package, without replacing any previous
delivery.

python -B -X utf8 tools/migration/package_goal21c.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending; the real mode needs --gametest-log (the GameTest
dedicated-server log of the settled tree) and writes only build/migration/releases/goal21c/ (the JAR, SHA256SUMS.txt, release.json).

The frozen Goal21C start is build/migration/goal21c/baseline.json: NEO HEAD dbfa6746 plus the uncommitted Goal21A delivery, the control-NBT
null fix and the Goal21B delivery (all three packaged by the goal21b package; build/libs at the start is that package). Every change since the
start is computed from the baseline file hashes (not from git diff, which would include the start content) and must be in the owner table
below; start content outside the owner table must still equal its start hash. The JAR delta against the goal21b package is attributed per
entry to goal21c; any entry without that owner fails. Counts that records quote (suites, generated resources, GameTests, releases) are
computed here, never hard-coded."""
from pathlib import Path
import argparse
import json
import re
import shutil
import sys
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import owner_class
from package_goal19c import tree_files, git
from package_review_g20_display_fixes import protected_drift as display_protected_drift, split_drift, ACCEPTANCE_CHECKLISTS
from migration import BUILD_FILES

OUT = ROOT/'build/migration/goal21c'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
START_21A = ROOT/'build/migration/goal21a/baseline.json'
START_21B = ROOT/'build/migration/goal21b/baseline.json'
REFERENCE_21B = ROOT/'build/migration/goal21b/final/summary.json'
PREVIOUS = ROOT/'build/migration/releases/goal21b/hbmsntm-198A-goal21b.jar'
PREVIOUS_SHA = 'be66861146616cacef620c1275a33de3eef9afaa18126968e959cea008a7e161'
PREVIOUS_BYTES = 18333655
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal21b/release.json'
PREVIOUS_RECEIPT_SHA = '7d701582966450847f05eec29a7ca74762fdf8b12aed46bbf3b99c7366f058ac'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal21b/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = 'ed7b2371fcb3ba3057ab4845122921246c0d6d01b0e988642c428bb7355c29da'
DISPLAY_RECEIPT = ROOT/'build/migration/releases/review-g20-display-fixes-20261016/release.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal21c'
RELEASE_NAME = 'hbmsntm-198A-goal21c.jar'
SOURCE_HEAD = '6a11998d5852ff3da326f0130357e10431ae3839'
START_HEAD = 'dbfa6746f9728bb551bfdfdaaedca3edaa42ba13'
# build/libs at the start is the goal21b package itself; packaging it again would package no Goal21C change.
START_JAR_SHA = PREVIOUS_SHA
SNAPSHOT = 'migration/baselines/review-6a11998d5852.json'
STAMP = 'src/generated/resources/.migration-stamp.json'
EN = 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
# commits.json gained commit_two (4d02ccdf) after the display-fix receipt hashed it (goal21a baseline explained_previous_drift); the Goal21A
# and Goal21B final runners protected it at this hash.
COMMITS = 'build/migration/review-fixes-g20-display/commits.json'
COMMITS_SHA = '08b26a3169564433ec3caee828f0523033b626b5f536689554dec45b2e0b9fa1'
J = 'src/main/java/com/hbm/'
JAVA = [J+p for p in (
    'entity/projectile/ZirnoxDebris.java', 'render/entity/projectile/RenderZirnoxDebris.java', 'entity/NtmEntityTypes.java', 'main/ClientProxy.java',
    'main/ResourceManager.java', 'explosion/ExplosionNukeGeneric.java', 'blockentity/machine/ReactorZirnoxBlockEntity.java',
    'datagen/NtmLanguageProvider.java')]
NEW_JAVA = JAVA[:2]
GAMETEST_JAVA = J+'gametest/ZirnoxMeltdownGameTests.java'
R = 'src/main/resources/assets/hbmsntm/'
RESOURCES = [R+'models/obj/zirnox/deb_%s.obj' % n for n in ('blank', 'concrete', 'element', 'exchanger', 'shrapnel')] + [
    R+'models/obj/projectiles/deb_graphite.obj', R+'textures/models/machines/zirnox_deb_element.png']
OWNERSHIP = 'migration/goal21c-resource-ownership.json'
# entity.hbmsntm.zirnox_debris: the original registers entity_zirnox_debris (EntityMappings.java:134) without a language key; the NEO name is local.
KEY = 'entity.hbmsntm.zirnox_debris'
PROVIDER = J+'datagen/NtmLanguageProvider.java'
LOCALIZATION_RECORD = ['migration/localization/zh_cn-map.json']
PRODUCTION = JAVA + [GAMETEST_JAVA] + RESOURCES + [ZH_INPUT]
GENERATED = [EN, STAMP]
TOOLS = ['tools/migration/verify_goal21c_meltdown.py', 'tools/migration/package_goal21c.py']
# Hashed by the receipt (frozen afterwards): this batch's ledger and reports; any further migration/goal21c-* record is hashed as well.
REPORTS = ['migration/GOAL21C.md', 'migration/GOAL21C-ACCEPTANCE.md', 'migration/goal21c-static-review.md', 'migration/goal21c-finite-accounting.json',
           'migration/goal21c-resource-ownership.json', 'migration/goal21c-localization-review.json']
BATCH_RECORD = re.compile(r'migration/goal21c-[^/]+\.(json|md)')
SHARED_RECORDS = ['migration/GOAL21.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md',
                  'migration/RESOURCE-OWNERSHIP.md']
# Must have changed (or been added) by the time of the real run; the rest of the owner table is optional.
REQUIRED_CHANGES = PRODUCTION + GENERATED + LOCALIZATION_RECORD + TOOLS + REPORTS + ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md',
                                                                                    'migration/features.json']
NAMES_RELEASE = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
OWNER = 'goal21c'
ZH_ENTRY = 'assets/hbmsntm/lang/zh_cn.json'
EN_ENTRY = 'assets/hbmsntm/lang/en_us.json'
AUDITS = ('localization-audit.json', 'resources-audit.json', 'packaged-resources.json')
VERIFY_REPORT = 'verify/meltdown-report.json'
FINAL_SUMMARY = 'final/summary.json'
COMPARE = 'compare.json'
MELTDOWN_SUITE = 'verify_goal21c_meltdown.py --final --gametest-log build/migration/goal21c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
GAMETEST = re.compile(r'All (\d+) required tests passed')
GAMETEST_ANNOTATION = re.compile(r'^\s*@GameTest\(', re.M)
SCOPE = ('Goal21C: the ZIRNOX meltdown instant effects of the original TileEntityReactorZirnox.meltdown() in its order (wreck, explosion, '
         'zirnoxDebris(), ExplosionNukeGeneric.waste of radius 35): the zirnox_debris entity (ZirnoxDebris, original EntityZirnoxDebris; six '
         'types with their sizes, gravity, wall reflection, rotation, CONCRETE/EXCHANGER digging, ELEMENT/GRAPHITE radiation, permanent scrap '
         'and pickup into the debris_* items) spawned 72 times per meltdown, its client renderer RenderZirnoxDebris with six original OBJ models '
         'and one texture, the ExplosionNukeGeneric.waste contamination, the entity name and Chinese; ZirnoxMeltdownGameTests.')
GOAL21C_RADIATION = ('Goal21C: a ZIRNOX meltdown spawns 72 zirnox_debris entities that never despawn (the original permaScrap default); '
                     'ELEMENT and GRAPHITE debris give RADIATION amplifier 7 or 4 for 60 seconds to every living entity within 2.5 blocks '
                     'each server tick, CONCRETE and EXCHANGER debris remove blocks around their impact (unbreakable blocks included), and the '
                     'nuclear waste of radius 35 (effective radius about 25 to 27 blocks) turns terrain into waste blocks. Trigger a meltdown '
                     'only in separately authorized disposable worlds, never in real saves. ')
OLD_MELTDOWN_DEFERRED = ('Deferred and not implemented, unlike the original: the zirnoxDebris() debris entities, the nuclear waste contamination '
                         'of radius 35 (ExplosionNukeGeneric.waste), the ZIRNOXBoom achievement for nearby players and the radMark marker.')
NEW_MELTDOWN_DEFERRED = ('Since Goal21C the meltdown also spawns 72 radioactive, block-digging zirnox_debris entities and contaminates the '
                         'terrain with nuclear waste of radius 35 (effective radius about 25 to 27 blocks) as the original (see '
                         'radiation_warning). Still deferred and not implemented, unlike the original: the ZIRNOXBoom achievement for nearby '
                         'players and the radMark marker.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal21c release directory: '+rel


def protected_paths(base):
    """What the Goal21B final runner protected (built from the Goal21A and Goal21B starts as there), plus every path the goal21b receipt
    hashes and every release file of the frozen Goal21C start. One path never carries two different hashes."""
    start = read(START_21A)
    start_21b = read(START_21B)
    display = read(DISPLAY_RECEIPT)
    assert COMMITS in start['explained_previous_drift']
    out = {p: h for p, h in start['goal20c_receipt_protected_paths'].items() if p not in start['goal20c_drift_explained']}
    out.update({p: display['acceptance_records'][p] for p in start['goal20c_drift_explained']})
    out.update(start['previous_receipt_protected_paths'])
    out[COMMITS] = COMMITS_SHA
    out.update({p: display['acceptance_records'][p] for p in ACCEPTANCE_CHECKLISTS})
    out.update(start['old_release_files'])
    for p, h in {**start_21b['previous_receipt_protected_paths'], **start_21b['old_release_files'],
                 **base['goal21a_receipt_protected_paths'], **base['previous_receipt_protected_paths'], **base['old_release_files']}.items():
        assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    return out


def changed_since_start(base):
    """{path: added|modified|deleted} against the frozen start's file hashes (git-visible files; build/ outputs excluded)."""
    now = {n for n in git(ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0') if n}
    out = {}
    for p in sorted(now | set(base['files'])):
        if p.startswith('build/'):
            continue
        before = base['files'].get(p)
        if not (ROOT/p).is_file():
            if before: out[p] = 'deleted'
            continue
        if before is None: out[p] = 'added'
        elif before != sha(ROOT/p): out[p] = 'modified'
    return out


def group(p):
    if p in JAVA: return 'production'
    if p == GAMETEST_JAVA: return 'gametest'
    if p in RESOURCES: return 'resources'
    if p in GENERATED or p == ZH_INPUT or p in LOCALIZATION_RECORD: return 'language'
    if p in TOOLS: return 'tools'
    if p in REPORTS or p in SHARED_RECORDS or BATCH_RECORD.fullmatch(p): return 'records'
    return None


def in_compare_inventory(p):
    """The target inventory of tools/migration/migration.py: src/**, data/** and the build files, without .cache and the stamp."""
    return (p.startswith(('src/', 'data/')) or p in BUILD_FILES) and '.cache' not in p.split('/') and not p.endswith('/.migration-stamp.json')


def lang_delta(old, new):
    return dict(added=sorted(set(new)-set(old)), removed=sorted(set(old)-set(new)), changed=sorted(k for k in set(old) & set(new) if old[k] != new[k]))


def compare_paths(entries):
    return {e['path'] if isinstance(e, dict) else e for e in entries}


def jar_entry(path):
    for prefix in ('src/main/resources/', 'src/generated/resources/'):
        if path.startswith(prefix): return path[len(prefix):]
    raise AssertionError('not a resource: '+path)


def main(check, gametest_log):
    pending = []
    base = read(BASELINE)
    prior_receipt = read(PREVIOUS_RECEIPT)

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal21C commits nothing), the recorded start content.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD, 'Unexpected frozen start'
    assert base['build_libs_jar_sha256'] == START_JAR_SHA, 'Baseline names another start build'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == START_HEAD, 'NEO HEAD moved during Goal21C: '+head
    assert set(base['start_content']) >= {'goal21a', 'control_nbt_null_fix', 'goal21b', 'fix_paths'}, 'Baseline start content lacks a group'

    # 2. Previous deliveries: the goal21b package, every old release file and the protected evidence (Goal21B runner set + goal21b receipt).
    assert base['previous_release'] == dict(path=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES), 'Baseline names another previous release'
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'goal21b JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'goal21b release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'goal21b SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'goal21b SHA256SUMS.txt content changed'
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    for p, h in base['old_release_files'].items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release file changed: '+p
    old_releases = dict(base['old_releases'])
    assert old_releases.get(PREVIOUS.relative_to(ROOT).as_posix()) == PREVIOUS_SHA
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    protected = protected_paths(base)
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)

    # 3. Changes since the start: each path in the owner table, attributed to goal21c; the start attribution is recorded alongside. Start
    # content (21A, the control-NBT fix, 21B) outside the owner table is therefore unchanged; its shared files carry only this batch's delta
    # (the language checks below).
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    assert not unassigned, 'Unassigned path changed since the Goal21C start: '+str(unassigned)
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal21C start: '+str(deleted)
    missing_required = [p for p in REQUIRED_CHANGES if p not in changes]
    if missing_required:
        if not check: raise AssertionError('Required Goal21C changes missing: '+str(missing_required))
        pending += ['change not present yet: '+p for p in missing_required]
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    assert set(since) <= set(PRODUCTION), 'src/main change outside the production list: '+str(sorted(set(since) - set(PRODUCTION)))
    for p in NEW_JAVA + [GAMETEST_JAVA] + RESOURCES:
        assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, start_attribution=base['dirty_attribution'].get(p, []),
                        before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    start_content_touched = sorted(p for p in changes if base['dirty_attribution'].get(p))
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    assert baselines_now == {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}, 'A snapshot was added or changed'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'], 'review-6a11998d5852 snapshot changed'

    # 4. Language and the generated tree: en_us.json and zh_cn.json gain exactly the one entity name, the mapping one entry; since the start
    # only en_us.json and the stamp of the generated tree may change, and no generated resource is added or retired.
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    assert set(generated_since) <= set(GENERATED), 'Generated change outside the Goal21C list: '+str(generated_since)
    provider_en = re.findall(r'this\.add\("'+re.escape(KEY)+r'", "([^"]*)"\);', (ROOT/PROVIDER).read_text(encoding='utf-8'))
    assert len(provider_en) == 1, 'NtmLanguageProvider does not add '+KEY+' exactly once'
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    en_delta = lang_delta(en_start, en_now)
    if en_delta == dict(added=[], removed=[], changed=[]):
        if not check: raise AssertionError('en_us.json not regenerated (run runData)')
        pending.append('generated en_us.json lacks '+KEY+' (runData)')
    else:
        assert en_delta == dict(added=[KEY], removed=[], changed=[]), 'en_us.json delta is not exactly the one key: '+str(en_delta)
        assert en_now[KEY] == provider_en[0], 'Generated English differs from NtmLanguageProvider'
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    zh_delta = lang_delta(zh_start, zh_now)
    if zh_delta == dict(added=[], removed=[], changed=[]):
        if not check: raise AssertionError('zh_cn.json lacks '+KEY)
        pending.append('zh_cn.json lacks '+KEY)
    else:
        assert zh_delta == dict(added=[KEY], removed=[], changed=[]) and zh_now[KEY].strip(), 'zh_cn.json delta is not exactly the one key: '+str(zh_delta)
    map_start = read(START_FILES/LOCALIZATION_RECORD[0])['entries']
    mapping = read(ROOT/LOCALIZATION_RECORD[0])['entries']
    map_delta = lang_delta(map_start, mapping)
    if KEY not in mapping:
        if not check: raise AssertionError('zh_cn-map.json lacks '+KEY)
        pending.append('zh_cn-map.json lacks '+KEY)
    else:
        assert map_delta == dict(added=[KEY], removed=[], changed=[]), 'zh_cn-map.json delta is not exactly the one entry: '+str(map_delta)
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    stamp_current = not stale and not mismatch and not unrecorded
    if not stamp_current:
        if not check: raise AssertionError(f'Stamp not current: stale {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
        pending.append(f'stamp not current (runData): stale {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
    start_generated = set(read(START_FILES/STAMP)['generated'])
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal21b generated tree'
    generated_added = sorted(set(stamp['generated']) - start_generated)
    generated_retired = sorted(start_generated - set(stamp['generated']))
    assert not generated_added and not generated_retired, f'Generated resources added {generated_added} or retired {generated_retired} since the start'

    # 5. Evidence: GameTest log, audits, the final suite run, the meltdown verifier and compare.
    evidence = {}
    gametest_line = gametest_count = None
    meltdown_tests = len(GAMETEST_ANNOTATION.findall((ROOT/GAMETEST_JAVA).read_text(encoding='utf-8'))) if (ROOT/GAMETEST_JAVA).is_file() else 0
    gametest_expected = prior_receipt['gametest']['tests'] + meltdown_tests
    log = (ROOT/gametest_log).resolve() if gametest_log else None
    if log is None or not log.is_file():
        if not check: raise AssertionError('GameTest log missing: pass --gametest-log PATH')
        pending.append('GameTest log (--gametest-log): '+(str(gametest_log) if gametest_log else 'not given'))
    else:
        assert log.is_relative_to(ROOT), 'GameTest log outside the NEO repository: '+str(log)
        text = log.read_text(encoding='utf-8-sig', errors='replace')
        found = GAMETEST.findall(text)
        assert found and 'BUILD SUCCESSFUL' in text and 'invalid dist' not in text and 'NoClassDefFoundError' not in text, 'GameTest run did not pass cleanly'
        gametest_count = int(found[-1])
        # The goal21b server's tests plus every @GameTest of ZirnoxMeltdownGameTests (no other GameTest source may change: owner table).
        assert meltdown_tests and gametest_count == gametest_expected, \
            f'GameTest server ran {gametest_count} tests, not the {prior_receipt["gametest"]["tests"]} goal21b tests + {meltdown_tests} meltdown tests'
        gametest_line = f'All {gametest_count} required tests passed'
        evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name in AUDITS:
        if not (OUT/name).is_file():
            if not check: raise AssertionError('Missing audit: '+name)
            pending.append('evidence: build/migration/goal21c/'+name)
            continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        audit_summaries[name] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    final = None
    # The 72 suites of the Goal21B final run plus the meltdown verifier.
    final_expected = len(read(REFERENCE_21B)['suites']) + 1
    if (OUT/FINAL_SUMMARY).is_file():
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        entry = final['suites'][MELTDOWN_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, MELTDOWN_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    elif check:
        pending.append('evidence: build/migration/goal21c/'+FINAL_SUMMARY)
    else:
        raise AssertionError('Missing final suite summary')
    verifier = None
    if (OUT/VERIFY_REPORT).is_file():
        report = read(OUT/VERIFY_REPORT)
        detected, total = (int(x) for x in str(report.get('mutations_detected', '0/0')).split('/'))
        mutations = report.get('mutations', {})
        mutations = list(mutations.values()) if isinstance(mutations, dict) else mutations
        complete = (report.get('ok') is True and report.get('final') is True and detected == total == len(mutations) > 0
                    and all(m.get('detected') for m in mutations) and not report.get('code_mutations_without_semantic_catch'))
        if not complete:
            if not check: raise AssertionError(VERIFY_REPORT+' is not a passing --final run with every mutation detected')
            pending.append('%s is not a passing --final run (ok=%s, final=%s, mutations %s)' % (VERIFY_REPORT, report.get('ok'), report.get('final'), report.get('mutations_detected')))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), mutations_detected=report.get('mutations_detected'))
        evidence[verifier['path']] = verifier['sha256']
    elif check:
        pending.append('evidence: build/migration/goal21c/'+VERIFY_REPORT)
    else:
        raise AssertionError('Missing '+VERIFY_REPORT)
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree, older than Goal21B): the original unchanged, the target exactly the
    # goal21b receipt's compare target set (the control-NBT fix and Goal21B paths) plus the Goal21C paths inside the compare inventory
    # (compare never lists the stamp). No new snapshot is generated.
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'goal21b receipt compare target set is incomplete'
    expected_target = sorted(previous_target | {p for p in changes if in_compare_inventory(p)})
    if (OUT/COMPARE).is_file():
        cmp = read(OUT/COMPARE)
        assert cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the 6a11998d snapshot'
        counts = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        assert all(v == 0 for v in counts['source'].values()), 'compare.json source is not 0/0/0: '+str(counts['source'])
        target = cmp['changes']['target']
        assert not target['removed'], 'compare.json target removed: '+str(target['removed'])
        listed = sorted(p for p in compare_paths(target['added']) | compare_paths(target['modified']) if not p.endswith('/.migration-stamp.json'))
        assert listed == expected_target, 'compare.json target set differs: extra %s, missing %s' % (
            sorted(set(listed) - set(expected_target)), sorted(set(expected_target) - set(listed)))
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts,
                       target_owners={p: sorted(set(prior_compare['target_owners'].get(p, [])) | ({OWNER} if p in changes else set())) for p in listed})
        evidence[compare['path']] = compare['sha256']
    elif check:
        pending.append('evidence: build/migration/goal21c/'+COMPARE)
    else:
        raise AssertionError('Missing '+COMPARE)

    # 6. JAR: build/libs is what gets packaged; delta against the goal21b package, every entry owned by goal21c.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    ownership = {i['target']: i for i in read(ROOT/OWNERSHIP)['imports']}
    assert sorted(ownership) == sorted(RESOURCES), 'Ownership record imports differ from the owner table: '+str(sorted(set(ownership) ^ set(RESOURCES)))
    resources = {}
    for p in RESOURCES:
        if not (ROOT/p).is_file():
            continue
        o = ownership[p]['original']
        resources[p] = dict(sha256=sha(ROOT/p), bytes=(ROOT/p).stat().st_size, original=o, original_sha256=sha(SOURCE/o),
                            ownership_sha256=ownership[p]['sha256'], start_sha256=base['files'].get(p))
        assert resources[p]['sha256'] == resources[p]['original_sha256'] == resources[p]['ownership_sha256'] and ownership[p]['bytes'] == resources[p]['bytes'], \
            'Resource is not the original bytes recorded in the ownership record: '+p
    if sha(JAR) in (PREVIOUS_SHA, START_JAR_SHA):
        if not check: raise AssertionError('build/libs JAR is still the goal21b package (run build)')
        pending.append('build/libs/hbmsntm-198A.jar is still the goal21b package')
    else:
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        resources_added = sorted(jar_entry(p) for p in RESOURCES)
        resources_modified = sorted([EN_ENTRY, ZH_ENTRY])
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            for p in stamp['generated']: assert jar.read(p) == (ROOT/'src/generated/resources'/p).read_bytes(), p
            assert jar.read(ZH_ENTRY) == (ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
            for path in classes:
                name = path.relative_to(classes_root).as_posix()
                assert jar.read(name) == path.read_bytes(), name
            for p in RESOURCES:
                assert sha(ROOT/p) == ownership[p]['sha256'] and jar.read(jar_entry(p)) == (ROOT/p).read_bytes(), 'Packaged resource is not the recorded original bytes: '+p
            prior_zh = json.loads(prior.read(ZH_ENTRY))
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(prior_zh, json.loads(jar.read(ZH_ENTRY)))
            # The goal21b package to the start: nothing (the start zh_cn.json is the packaged one); the start to now: only the entity name.
            zh_prior_to_start = lang_delta(prior_zh, zh_start)
            assert zh_prior_to_start == dict(added=[], removed=[], changed=[]), 'Start zh_cn.json differs from the goal21b package: '+str(zh_prior_to_start)
            assert en_jar == dict(added=[KEY], removed=[], changed=[]), 'JAR en_us.json delta: '+str(en_jar)
            assert zh_jar == dict(added=[KEY], removed=[], changed=[]), 'JAR zh_cn.json delta: '+str(zh_jar)
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        goal21c_java = JAVA + [GAMETEST_JAVA]
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                if n.endswith('.class'):
                    owner = [OWNER] if owner_class(n) in goal21c_java else []
                elif (kind == 'added' and n in resources_added) or (kind == 'modified' and n in resources_modified):
                    owner = [OWNER]
                else:
                    owner = []
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        assert not unowned, 'Unowned JAR change: '+str(unowned)
        assert sorted(n for n in jar_delta['added'] if not n.endswith('.class')) == resources_added, 'Added JAR resources: '+str(
            [n for n in jar_delta['added'] if not n.endswith('.class')])
        assert sorted(n for n in jar_delta['modified'] if not n.endswith('.class')) == resources_modified, 'Modified JAR resources: '+str(
            [n for n in jar_delta['modified'] if not n.endswith('.class')])
        assert not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed JAR resources: '+str(jar_delta['removed'])
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        assert set(class_owners) == set(goal21c_java), 'Not every changed Java source changed a class: '+str(sorted(set(goal21c_java) - set(class_owners)))
        for p in NEW_JAVA + [GAMETEST_JAVA]:
            assert any(owner_class(n) == p for n in jar_delta['added']), p+' is not a new JAR class'
        # A new JAR directory is accepted only as the parent of an added Goal21C entry.
        stray = [d for d in dir_delta['added'] if not any(n.startswith(d) for n in jar_delta['added'])]
        assert not stray and not dir_delta['removed'], 'JAR directory delta: '+str(dir_delta)
        added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
        removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
        assert classes and len(classes) == prior_receipt['compiled_classes_verified'] + added_classes - removed_classes, \
            f'Compiled class count {len(classes)} is not the goal21b count {prior_receipt["compiled_classes_verified"]} +{added_classes} -{removed_classes}'
        language = dict(en=en_jar, zh=zh_jar, zh_goal21b_to_start=zh_prior_to_start)

    # 7. Records.
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    if unnamed:
        if not check: raise AssertionError('Records do not name '+RELEASE_NAME+': '+str(unnamed))
        pending += ['records (do not name '+RELEASE_NAME+'): '+p for p in unnamed]
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    missing_reports = [p for p in reports if not (ROOT/p).is_file()]
    if missing_reports:
        if not check: raise AssertionError('Missing records: '+str(missing_reports))
        pending += ['records: '+p for p in missing_reports]
    if not check:
        assert base['files'].get('migration/GOAL21C.md') != sha(ROOT/'migration/GOAL21C.md'), 'GOAL21C.md has no delivery record'

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=generated_added,
                   start_content_touched=start_content_touched, en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta,
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta,
                   class_owners=class_owners, gametest=gametest_line, gametest_expected=gametest_expected, final_suites_expected=final_expected,
                   compare=compare['counts'] if compare else None, compare_target_expected=len(expected_target), resources=len(resources),
                   protected_paths=len(protected), old_releases_preserved=len(old_releases), preserved_release_files=len(base['old_release_files']),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending:' if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different goal21c JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest == sha(JAR) and digest not in (PREVIOUS_SHA, START_JAR_SHA), 'Packaged JAR is not build/libs or is an older JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in reports}
    evidence[BASELINE.relative_to(ROOT).as_posix()] = sha(BASELINE)
    assert OLD_MELTDOWN_DEFERRED in prior_receipt['meltdown_warning'], 'goal21b meltdown_warning wording changed'
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified', scope=SCOPE,
                   radiation_warning=GOAL21C_RADIATION+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'].replace(OLD_MELTDOWN_DEFERRED, NEW_MELTDOWN_DEFERRED),
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, planning_commit=START_HEAD, commits={}, target_head_at_packaging=head,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], dirty_attribution=base['dirty_attribution'], start_build_sha256=START_JAR_SHA,
                                      touched_by_goal21c=start_content_touched,
                                      note='The start tree is HEAD dbfa6746 + the uncommitted Goal21A delivery + the control-NBT null fix + the '
                                           'uncommitted Goal21B delivery, all packaged by goal21b; start-content files changed here carry only '
                                           'Goal21C hunks and are attributed to goal21c.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added,
                   compiled_classes_verified=prior_receipt['compiled_classes_verified'] + sum(1 for n in jar_delta['added'] if n.endswith('.class')) - sum(1 for n in jar_delta['removed'] if n.endswith('.class')),
                   production=PRODUCTION, sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   resources=resources, resource_ownership=dict(path=OWNERSHIP, sha256=sha(ROOT/OWNERSHIP)),
                   language=dict(keys={KEY: dict(en=en_now[KEY], zh=zh_now[KEY], original_key=None,
                                                 note='The original registers entity_zirnox_debris (EntityMappings.java:134) without a language key.')},
                                 jar_delta=language),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; it covers the '
                                      'meltdown order, the 72 debris, their movement, digging, radiation and pickup and the waste contamination as '
                                      'far as ZirnoxMeltdownGameTests asserts them, not the debris rendering or a meltdown in a real world.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + LOCALIZATION_RECORD,
                   evidence_sha256={**hashes, **evidence, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the resource, packaged-resource and localization audits, '
                            'the static meltdown verifier with mutations, the final old-suite rerun, compare against the review-6a11998d5852 snapshot '
                            'and independent JAR bytes (six original OBJ models and one texture, the entity name, classes of the changed sources). No '
                            'client, real save, multiplayer or player interaction was run: the debris models and textures, their client motion, '
                            'the entity name and a meltdown in a real world are unverified in game.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal21b package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
