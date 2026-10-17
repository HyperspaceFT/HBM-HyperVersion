"""Package Goal21B (ZIRNOX wreck radiation and fire, one-shot schedule and foam branch, six debris_* items and the pile of fallout, hazards,
four shredder rows, wreck loot completion) cumulatively on the goal21a package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal21b.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending; the real mode needs --gametest-log (the GameTest
dedicated-server log of the settled tree) and writes only build/migration/releases/goal21b/ (the JAR, SHA256SUMS.txt, release.json).

The frozen Goal21B start is build/migration/goal21b/baseline.json: NEO HEAD dbfa6746 plus the uncommitted Goal21A delivery (the goal21a
package) plus the uncommitted, unpackaged control-NBT null fix (REVIEW-FIXES-CONTROL-NBT-NULL.md, baseline start_content.fix_paths). Every
change since the start is computed from the baseline file hashes (not from git diff, which would include the start content) and must be in
the owner table below. The JAR delta against the goal21a package is attributed per entry to goal21b or to control-nbt-null-fix (start
content the goal21a package does not contain); any entry with neither owner fails. Counts that records quote (suites, generated resources,
GameTests, releases) are computed here, never hard-coded."""
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

OUT = ROOT/'build/migration/goal21b'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
START_21A = ROOT/'build/migration/goal21a/baseline.json'
REFERENCE_21A = ROOT/'build/migration/goal21a/final/summary.json'
PREVIOUS = ROOT/'build/migration/releases/goal21a/hbmsntm-198A-goal21a.jar'
PREVIOUS_SHA = '303e837a0aa868da91d6bed73eaa6df881af441eb04bb05ecb6699d92024133a'
PREVIOUS_BYTES = 18301049
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal21a/release.json'
PREVIOUS_RECEIPT_SHA = '9e6bb45ad72565be39024094f0feef188d61a262355691b2418df8fff00b3e11'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal21a/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = 'ba3ae53a12cb663be2d96f6c50efc3d17268a446a40882916ed09b61e40c150a'
DISPLAY_RECEIPT = ROOT/'build/migration/releases/review-g20-display-fixes-20261016/release.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal21b'
RELEASE_NAME = 'hbmsntm-198A-goal21b.jar'
SOURCE_HEAD = '6a11998d5852ff3da326f0130357e10431ae3839'
START_HEAD = 'dbfa6746f9728bb551bfdfdaaedca3edaa42ba13'
# build/libs at the start: the control-NBT fix build (A+B+C), not a delivery; packaging it again would package no Goal21B change.
START_JAR_SHA = '7191c254c1340903f32d4284951ed473ef3d6140fc88cc35de157f470438f766'
SNAPSHOT = 'migration/baselines/review-6a11998d5852.json'
STAMP = 'src/generated/resources/.migration-stamp.json'
EN = 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
# commits.json gained commit_two (4d02ccdf) after the display-fix receipt hashed it (goal21a baseline explained_previous_drift); the Goal21A
# final runner protected it at this hash.
COMMITS = 'build/migration/review-fixes-g20-display/commits.json'
COMMITS_SHA = '08b26a3169564433ec3caee828f0523033b626b5f536689554dec45b2e0b9fa1'
J = 'src/main/java/com/hbm/'
JAVA = [J+p for p in (
    'blockentity/machine/ZirnoxDestroyedBlockEntity.java', 'blocks/machine/ZirnoxDestroyedBlock.java', 'items/NtmItems.java',
    'inventory/NtmCreativeTabs.java', 'hazard/HazardRegistry.java', 'inventory/recipes/ShredderRecipes.java',
    'datagen/NtmBlockLootTableProvider.java', 'datagen/NtmItemModelProvider.java', 'datagen/NtmLanguageProvider.java')]
GAMETEST_JAVA = J+'gametest/ZirnoxWreckGameTests.java'
# fallout_pile: hbmsntm:fallout is the fallout-layer BlockItem (NtmItems FALLOUT_PILE comment); the original item and texture are 'fallout'.
ITEMS = ('debris_metal', 'debris_graphite', 'debris_concrete', 'debris_exchanger', 'debris_shrapnel', 'debris_element', 'fallout_pile')
ORIGINAL_NAME = {**{n: n for n in ITEMS}, 'fallout_pile': 'fallout'}
TEX = 'src/main/resources/assets/hbmsntm/textures/item/%s.png'
ORIGINAL_TEX = 'src/main/resources/assets/hbm/textures/items/%s.png'
MODEL = 'src/generated/resources/assets/hbmsntm/models/item/%s.json'
LOOT = 'src/generated/resources/data/hbmsntm/loot_table/blocks/zirnox_destroyed.json'
LOOT_ITEMS = ('debris_metal', 'debris_graphite', 'fallout_pile')
ORIGINAL_EN = 'src/main/resources/assets/hbm/lang/en_US.lang'
KEYS = {'item.hbmsntm.'+n: 'item.'+ORIGINAL_NAME[n]+'.name' for n in ITEMS}
PRODUCTION = JAVA + [GAMETEST_JAVA] + [TEX % n for n in ITEMS] + [ZH_INPUT]
GENERATED = [EN] + [MODEL % n for n in ITEMS] + [LOOT, STAMP]
LOCALIZATION_RECORD = ['migration/localization/zh_cn-map.json']
TOOLS = ['tools/migration/verify_goal21b_wreck.py', 'tools/migration/package_goal21b.py']
# Hashed by the receipt (frozen afterwards): this batch's ledger and reports; any further migration/goal21b-* record is hashed as well.
REPORTS = ['migration/GOAL21B.md', 'migration/GOAL21B-ACCEPTANCE.md', 'migration/goal21b-finite-accounting.json',
           'migration/goal21b-resource-ownership.json', 'migration/goal21b-localization-review.json', 'migration/goal21b-hazard-review.json',
           'migration/goal21b-static-review.md']
BATCH_RECORD = re.compile(r'migration/goal21b-[^/]+\.(json|md)')
SHARED_RECORDS = ['migration/GOAL21.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md',
                  'migration/RESOURCE-OWNERSHIP.md']
# Must have changed (or been added) by the time of the real run; the rest of the owner table is optional.
REQUIRED_CHANGES = PRODUCTION + GENERATED + LOCALIZATION_RECORD + TOOLS + REPORTS + ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md',
                                                                                    'migration/features.json']
NAMES_RELEASE = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
# Start content that the goal21a package does not contain (REVIEW-FIXES-CONTROL-NBT-NULL.md): owner of its JAR entries.
FIX = 'control-nbt-null-fix'
FIX_JAVA = [J+'network/toserver/CompoundTagControl.java', J+'network/toserver/CompoundTagItemControl.java']
FIX_CLASSES = ['com/hbm/network/toserver/CompoundTagControl.class', 'com/hbm/network/toserver/CompoundTagItemControl.class']
FIX_ZH_KEY = 'container.nuke_fstbmb'
ZH_ENTRY = 'assets/hbmsntm/lang/zh_cn.json'
AUDITS = ('localization-audit.json', 'resources-audit.json', 'packaged-resources.json')
VERIFY_REPORT = 'verify/wreck-report.json'
FINAL_SUMMARY = 'final/summary.json'
COMPARE = 'compare.json'
WRECK_SUITE = 'verify_goal21b_wreck.py --final --jar build/libs/hbmsntm-198A.jar'
FIX_SUITE = 'verify_review_control_nbt_null.py --jar build/libs/hbmsntm-198A.jar'
GAMETEST = re.compile(r'All (\d+) required tests passed')
# The Goal21A server's 34 tests plus the eight Goal21B wreck tests of GOAL21B.md B6 (a floor; the receipt records the count in the log).
GAMETEST_MIN = 42
SCOPE = ('Goal21B: the ZIRNOX wreck (ZirnoxDestroyedBlockEntity) radiates every living entity within 100 blocks each server tick as the original '
         'TileEntityZirnoxDestroyed (500,000 rads burning, 75,000 extinguished, divided by the blast resistance summed along the ray and the '
         'squared distance) and deals fire damage 2 within 5 blocks while burning; ZirnoxDestroyedBlock schedules its tick once on placement and '
         'extinguishes the core 1/25 under block_foam; six debris_* items and the pile of fallout (fallout_pile, since hbmsntm:fallout is the '
         'fallout-layer block item) with their hazards, seven original textures, item models, names and Chinese; four shredder rows '
         '(debris_shrapnel, debris_exchanger, debris_metal, debris_graphite; user ruling A); the wreck loot completed with 6 debris_metal, 2 debris_graphite and 4 fallout_pile; ZirnoxWreckGameTests.')
GOAL21B_RADIATION = ('Goal21B: the ZIRNOX wreck radiates 500,000 rads (burning) or 75,000 rads (extinguished) to every living entity within 100 '
                     'blocks each server tick, attenuated only by blast resistance and squared distance, and burns entities within 5 blocks '
                     'while on fire; the six debris_* items and the pile of fallout are radioactive (debris_graphite also hot). Place a wreck or '
                     'handle its debris only in separately authorized disposable worlds, never in real saves. ')
OLD_MELTDOWN_TAIL = ', the radMark marker, and the wreck radiation, fire damage and foam extinguishing.'
NEW_MELTDOWN_TAIL = (' and the radMark marker. Since Goal21B the wreck radiates and burns nearby entities as the original (see '
                     'radiation_warning) and its loot includes radioactive debris.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal21b release directory: '+rel


def protected_paths(base):
    """What the Goal21A final runner protected (built from the Goal21A start as there), plus every path the goal21a receipt hashes and every
    release file of the frozen Goal21B start. One path never carries two different hashes."""
    start = read(START_21A)
    display = read(DISPLAY_RECEIPT)
    assert COMMITS in start['explained_previous_drift']
    out = {p: h for p, h in start['goal20c_receipt_protected_paths'].items() if p not in start['goal20c_drift_explained']}
    out.update({p: display['acceptance_records'][p] for p in start['goal20c_drift_explained']})
    out.update(start['previous_receipt_protected_paths'])
    out[COMMITS] = COMMITS_SHA
    out.update({p: display['acceptance_records'][p] for p in ACCEPTANCE_CHECKLISTS})
    out.update(start['old_release_files'])
    for p, h in {**base['previous_receipt_protected_paths'], **base['old_release_files']}.items():
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
    if p in PRODUCTION: return 'production'
    if p in GENERATED: return 'generated'
    if p in LOCALIZATION_RECORD: return 'localization-record'
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


def original_lang(path):
    out = {}
    for line in (SOURCE/path).read_text(encoding='utf-8', errors='replace').splitlines():
        key, sep, value = line.partition('=')
        if sep and not line.startswith('#'): out.setdefault(key.strip(), value.strip())
    return out


def jar_entry(path):
    for prefix in ('src/main/resources/', 'src/generated/resources/'):
        if path.startswith(prefix): return path[len(prefix):]
    raise AssertionError('not a resource: '+path)


def main(check, gametest_log):
    pending = []
    base = read(BASELINE)
    prior_receipt = read(PREVIOUS_RECEIPT)

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal21B commits nothing), the recorded start content.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD, 'Unexpected frozen start'
    assert base['build_libs_jar_sha256'] == START_JAR_SHA, 'Baseline names another start build'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == START_HEAD, 'NEO HEAD moved during Goal21B: '+head
    fix_paths = base['start_content']['fix_paths']
    assert set(FIX_JAVA) <= set(fix_paths) and ZH_INPUT in fix_paths, 'Baseline fix paths do not name the control classes and zh_cn.json'

    # 2. Previous deliveries: the goal21a package, every old release file and the protected evidence (Goal21A runner set + goal21a receipt).
    assert base['previous_release'] == dict(path=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES), 'Baseline names another previous release'
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'goal21a JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'goal21a release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'goal21a SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'goal21a SHA256SUMS.txt content changed'
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

    # 3. Changes since the start: each path in the owner table, attributed to goal21b; the start attribution is recorded alongside.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    assert not unassigned, 'Unassigned path changed since the Goal21B start: '+str(unassigned)
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal21B start: '+str(deleted)
    missing_required = [p for p in REQUIRED_CHANGES if p not in changes]
    if missing_required:
        if not check: raise AssertionError('Required Goal21B changes missing: '+str(missing_required))
        pending += ['change not present yet: '+p for p in missing_required]
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    assert set(since) <= set(PRODUCTION), 'src/main change outside the production list: '+str(sorted(set(since) - set(PRODUCTION)))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner='goal21b', start_attribution=base['dirty_attribution'].get(p, []),
                        before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    assert baselines_now == {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}, 'A snapshot was added or changed'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'], 'review-6a11998d5852 snapshot changed'

    # 4. Generated tree: en_us.json gains exactly the seven names (original English), seven new item models, the loot table, the stamp.
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    assert set(generated_since) <= set(GENERATED), 'Generated change outside the Goal21B list: '+str(generated_since)
    original_en = original_lang(ORIGINAL_EN)
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    en_delta = lang_delta(en_start, en_now)
    if en_delta == dict(added=[], removed=[], changed=[]):
        if not check: raise AssertionError('en_us.json not regenerated (run runData)')
        pending.append('generated en_us.json lacks the seven names (runData)')
    else:
        assert en_delta == dict(added=sorted(KEYS), removed=[], changed=[]), 'en_us.json delta is not exactly the seven names: '+str(en_delta)
        wrong = {k: (en_now[k], original_en.get(o)) for k, o in KEYS.items() if en_now[k] != original_en.get(o)}
        assert not wrong, 'English differs from the original en_US.lang: '+str(wrong)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    zh_delta = lang_delta(zh_start, zh_now)
    if zh_delta == dict(added=[], removed=[], changed=[]):
        if not check: raise AssertionError('zh_cn.json lacks the seven names')
        pending.append('zh_cn.json lacks the seven names')
    else:
        assert zh_delta == dict(added=sorted(KEYS), removed=[], changed=[]) and all(zh_now[k].strip() for k in KEYS), 'zh_cn.json delta is not exactly the seven names: '+str(zh_delta)
    mapping = read(ROOT/LOCALIZATION_RECORD[0])['entries']
    unmapped = sorted(k for k in KEYS if k not in mapping)
    if unmapped:
        if not check: raise AssertionError('zh_cn-map.json lacks: '+str(unmapped))
        pending.append('zh_cn-map.json lacks: '+str(unmapped))
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal21a generated tree'
    generated_added = sorted(set(stamp['generated']) - start_generated)
    generated_retired = sorted(start_generated - set(stamp['generated']))
    models = sorted(jar_entry(MODEL % n) for n in ITEMS)
    assert not generated_retired, 'Generated resources retired since the start: '+str(generated_retired)
    if generated_added != models:
        if not check or generated_added: raise AssertionError('Generated resources added since the start are not the seven item models: '+str(generated_added))
        pending.append('stamp does not record the seven item models yet (runData)')
    loot = (ROOT/LOOT).read_text(encoding='utf-8')
    loot_missing = [n for n in LOOT_ITEMS if '"hbmsntm:'+n+'"' not in loot]
    if loot_missing:
        if not check: raise AssertionError('Wreck loot table lacks: '+str(loot_missing))
        pending.append('wreck loot table lacks: '+str(loot_missing))

    # 5. Evidence: GameTest log, audits, the final suite run, the wreck verifier and compare.
    evidence = {}
    gametest_line = gametest_count = None
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
        assert gametest_count >= GAMETEST_MIN, f'GameTest server ran {gametest_count} tests, fewer than the {GAMETEST_MIN} expected with the wreck tests'
        gametest_line = f'All {gametest_count} required tests passed'
        evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name in AUDITS:
        if not (OUT/name).is_file():
            if not check: raise AssertionError('Missing audit: '+name)
            pending.append('evidence: build/migration/goal21b/'+name)
            continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        audit_summaries[name] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    final = None
    final_expected = len(read(REFERENCE_21A)['suites']) + 2
    if (OUT/FINAL_SUMMARY).is_file():
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        entry = final['suites'][WRECK_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, WRECK_SUITE+' did not pass in the final run'
        entry = final['suites'][FIX_SUITE]
        assert entry['status'] == 'as-expected' or 'explanation' in entry, FIX_SUITE+' has an unexplained result'
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    elif check:
        pending.append('evidence: build/migration/goal21b/'+FINAL_SUMMARY)
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
        pending.append('evidence: build/migration/goal21b/'+VERIFY_REPORT)
    else:
        raise AssertionError('Missing '+VERIFY_REPORT)
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree): the original unchanged, the target exactly the start-content fix
    # paths plus the Goal21B paths inside the compare inventory (compare never lists the stamp). No new snapshot is generated.
    expected_target = sorted({p for p in fix_paths if in_compare_inventory(p)} | {p for p in changes if in_compare_inventory(p)})
    if (OUT/COMPARE).is_file():
        cmp = read(OUT/COMPARE)
        assert cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the 6a11998d snapshot'
        counts = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        assert all(v == 0 for v in counts['source'].values()), 'compare.json source is not 0/0/0: '+str(counts['source'])
        target = cmp['changes']['target']
        assert not target['removed'], 'compare.json target removed: '+str(target['removed'])
        listed = sorted(compare_paths(target['added']) | compare_paths(target['modified']))
        assert listed == expected_target, 'compare.json target set differs: extra %s, missing %s' % (
            sorted(set(listed) - set(expected_target)), sorted(set(expected_target) - set(listed)))
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts,
                       target_owners={p: [o for o, hit in ((FIX, p in fix_paths), ('goal21b', p in changes)) if hit] for p in listed})
        evidence[compare['path']] = compare['sha256']
    elif check:
        pending.append('evidence: build/migration/goal21b/'+COMPARE)
    else:
        raise AssertionError('Missing '+COMPARE)

    # 6. JAR: build/libs is what gets packaged; delta against the goal21a package, every entry owned by goal21b or the start-content fix.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    textures = {}
    for n in ITEMS:
        p, o = TEX % n, ORIGINAL_TEX % ORIGINAL_NAME[n]
        if not (ROOT/p).is_file():
            continue
        textures[p] = dict(sha256=sha(ROOT/p), bytes=(ROOT/p).stat().st_size, original=o, original_sha256=sha(SOURCE/o), start_sha256=base['files'].get(p))
        assert textures[p]['start_sha256'] is None and textures[p]['sha256'] == textures[p]['original_sha256'], 'Texture is not the original bytes: '+p
    if sha(JAR) in (PREVIOUS_SHA, START_JAR_SHA):
        if not check: raise AssertionError('build/libs JAR is still the goal21a package or the start build (run build)')
        pending.append('build/libs/hbmsntm-198A.jar is still the goal21a package or the start build')
    else:
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        texture_entries = sorted(jar_entry(TEX % n) for n in ITEMS)
        resources_added = sorted(texture_entries + models)
        resources_modified = sorted([jar_entry(EN), ZH_ENTRY, jar_entry(LOOT)])
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            for p in stamp['generated']: assert jar.read(p) == (ROOT/'src/generated/resources'/p).read_bytes(), p
            assert jar.read(ZH_ENTRY) == (ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
            for path in classes:
                name = path.relative_to(classes_root).as_posix()
                assert jar.read(name) == path.read_bytes(), name
            for n in ITEMS:
                assert jar.read(jar_entry(TEX % n)) == (ROOT/(TEX % n)).read_bytes() == (SOURCE/(ORIGINAL_TEX % ORIGINAL_NAME[n])).read_bytes(), 'Packaged texture is not the original bytes: '+n
            prior_zh = json.loads(prior.read(ZH_ENTRY))
            en_jar = lang_delta(json.loads(prior.read('assets/hbmsntm/lang/en_us.json')), json.loads(jar.read('assets/hbmsntm/lang/en_us.json')))
            zh_jar = lang_delta(prior_zh, json.loads(jar.read(ZH_ENTRY)))
            # The goal21a package to the start: only the fix's container.nuke_fstbmb; the start to now: only the seven Goal21B names.
            zh_fix = lang_delta(prior_zh, zh_start)
            assert zh_fix == dict(added=[], removed=[], changed=[FIX_ZH_KEY]), 'Start zh_cn.json differs from the goal21a package beyond the fix: '+str(zh_fix)
            assert en_jar == dict(added=sorted(KEYS), removed=[], changed=[]), 'JAR en_us.json delta: '+str(en_jar)
            assert zh_jar == dict(added=sorted(KEYS), removed=[], changed=[FIX_ZH_KEY]), 'JAR zh_cn.json delta: '+str(zh_jar)
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        goal21b_java = JAVA + [GAMETEST_JAVA]
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                if n.endswith('.class'):
                    source = owner_class(n)
                    owner = [FIX] if source in FIX_JAVA else ['goal21b'] if source in goal21b_java else []
                elif n == ZH_ENTRY:
                    owner = [FIX, 'goal21b']
                elif (kind == 'added' and n in resources_added) or (kind == 'modified' and n in resources_modified):
                    owner = ['goal21b']
                else:
                    owner = []
                # The fix adds and removes nothing (REVIEW-FIXES-CONTROL-NBT-NULL.md: no entries added or removed).
                if not owner or (kind != 'modified' and FIX in owner): unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        assert not unowned, 'Unowned JAR change: '+str(unowned)
        assert sorted(n for n in jar_delta['added'] if not n.endswith('.class')) == resources_added, 'Added JAR resources: '+str(
            [n for n in jar_delta['added'] if not n.endswith('.class')])
        assert sorted(n for n in jar_delta['modified'] if not n.endswith('.class')) == resources_modified, 'Modified JAR resources: '+str(
            [n for n in jar_delta['modified'] if not n.endswith('.class')])
        assert not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed JAR resources: '+str(jar_delta['removed'])
        assert sorted(n for n in jar_delta['modified'] if n.endswith('.class') and owner_class(n) in FIX_JAVA) == FIX_CLASSES, 'Fix-owned classes in the JAR delta'
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        assert set(class_owners) == set(goal21b_java) | set(FIX_JAVA), 'Not every changed Java source changed a class: '+str(sorted(set(goal21b_java) - set(class_owners)))
        assert any(owner_class(n) == GAMETEST_JAVA for n in jar_delta['added']), 'ZirnoxWreckGameTests is not a new JAR class'
        # A new JAR directory is accepted only as the parent of an added Goal21B entry.
        stray = [d for d in dir_delta['added'] if not any(n.startswith(d) for n in jar_delta['added'])]
        assert not stray and not dir_delta['removed'], 'JAR directory delta: '+str(dir_delta)
        added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
        removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
        assert classes and len(classes) == prior_receipt['compiled_classes_verified'] + added_classes - removed_classes, \
            f'Compiled class count {len(classes)} is not the goal21a count {prior_receipt["compiled_classes_verified"]} +{added_classes} -{removed_classes}'
        language = dict(en=en_jar, zh=zh_jar, zh_goal21a_to_start=zh_fix)

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
        assert base['files'].get('migration/GOAL21B.md') != sha(ROOT/'migration/GOAL21B.md'), 'GOAL21B.md has no delivery record'

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=generated_added,
                   en_delta=en_delta, zh_delta=zh_delta, jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None,
                   class_owners=class_owners, gametest=gametest_line, final_suites_expected=final_expected,
                   compare=compare['counts'] if compare else None, compare_target_expected=len(expected_target), textures=len(textures),
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
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different goal21b JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest == sha(JAR) and digest not in (PREVIOUS_SHA, START_JAR_SHA), 'Packaged JAR is not build/libs or is an older JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in reports}
    evidence[BASELINE.relative_to(ROOT).as_posix()] = sha(BASELINE)
    assert OLD_MELTDOWN_TAIL in prior_receipt['meltdown_warning'], 'goal21a meltdown_warning wording changed'
    zh_names = read(ROOT/ZH_INPUT)
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified', scope=SCOPE,
                   radiation_warning=GOAL21B_RADIATION+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'].replace(OLD_MELTDOWN_TAIL, NEW_MELTDOWN_TAIL),
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, planning_commit=START_HEAD, commits={}, target_head_at_packaging=head,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], dirty_attribution=base['dirty_attribution'], start_build_sha256=START_JAR_SHA,
                                      note='The start tree is HEAD dbfa6746 + the uncommitted Goal21A delivery + the control-NBT null fix; the fix is '
                                           'packaged here for the first time and its JAR entries are attributed to control-nbt-null-fix, not to Goal21B.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added,
                   compiled_classes_verified=prior_receipt['compiled_classes_verified'] + sum(1 for n in jar_delta['added'] if n.endswith('.class')) - sum(1 for n in jar_delta['removed'] if n.endswith('.class')),
                   production=PRODUCTION, sources_changed=since, generated_since_start=generated_since, changed_files=change_list, textures=textures,
                   language=dict(keys={k: dict(en=en_now[k], zh=zh_names[k], original_key=o) for k, o in KEYS.items()}, jar_delta=language),
                   loot=dict(path=LOOT, sha256=sha(ROOT/LOOT), added_items=['hbmsntm:'+n for n in LOOT_ITEMS]),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; it covers the wreck '
                                      'radiation formula, shielding, fire damage, extinguish roll, one-shot schedule, foam, loot and the debris items as '
                                      'far as ZirnoxWreckGameTests asserts them, not lethality or Geiger readings in a real world.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + LOCALIZATION_RECORD,
                   evidence_sha256={**hashes, **evidence, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the resource, packaged-resource and localization audits, '
                            'the static wreck verifier with mutations, the final old-suite rerun, compare against the review-6a11998d5852 snapshot and '
                            'independent JAR bytes (seven original textures, seven names, item models, the wreck loot table, classes of the changed '
                            'sources). No client, real save, multiplayer or player interaction was run: radiation doses and lethality in a real world, '
                            'Geiger readings, item textures, names and creative-tab placement are unverified in game.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal21a package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
