"""Package Goal23A (Goal 22 close-out remainders: the fluid trait tooltip keys of FT_Combustible, FT_Polluting and FT_VentRadiation aligned with the original
hbmfluid.trait.* keys with 13 language keys, HazardSystem.register stacking a repeated registration through the new HazardData.merge, the HazardTypeHot
reacher scan over the main inventory, the HazardTypeHydroactive explosion at eye height with block damage, and four HazardGameTests) cumulatively on the
goal22d package, without replacing any previous delivery. The Sa326 crystal lethality trace (23A-5) is static only and changes no code.

python -B -X utf8 tools/migration/package_goal23a.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal23a/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal23a/gametest-final.log (the
GameTest dedicated-server log of the settled tree).

The frozen start is build/migration/goal23a/baseline.json: NEO HEAD dd69a404 (the Goal 23 planning commit on top of the Goal 22 close-out commit 670d5911)
with a CLEAN working tree (no dirty path, no pending small fix). build/libs at the start is the goal22d package byte for byte. Every change since the
start is computed from the baseline file hashes (not from git diff) and must be in the owner table below; every other path must still equal its start
hash. Several start paths (the generation stamp, en_us.json, zh_cn.json, the zh_cn mapping, README, features, UPSTREAM-REVIEWS, LOCALIZATION, GOAL23.md and
GOAL23A.md) are modified here: their before hash is the start hash, their after hash the live one. The JAR delta against the goal22d package is attributed
per entry (goal23a); any entry without exactly one owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases,
language keys) are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the files and the baseline, not
from literals.

The receipts that hash records (goal21a..goal22d and the review-g21d-hazard-fix receipt) were written before later appends to the acceptance checklists
(the Goal 21 and Goal 22 in-game acceptance result lines, the close-out checklist corrections), before the O1 record notes and (goal22c) before the
thorium follow-up section of GOAL22C.md; those records already differ from their receipt hashes at the frozen start (baseline
previous_receipt_evidence_drift and older_receipt_evidence_drift). They are listed in the receipt as start drift (receipt hashes, the Goal22D start hash,
the Goal23A start hash, current hash) and must still equal their Goal23A start hash; no receipt is rewritten and no other protected path may drift. Four of
them changed between the Goal22D start and the Goal23A start (GOAL21C-, GOAL22A-, GOAL22B- and GOAL22C-ACCEPTANCE.md): the pin an earlier packager set at
the Goal22D start hash is replaced by the Goal23A start hash and the replaced pins are listed in the receipt."""
from collections import Counter
from pathlib import Path
import argparse
import json
import re
import shutil
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import owner_class
from package_goal19c import tree_files
from package_review_g20_display_fixes import protected_drift as display_protected_drift, split_drift
from migration import BUILD_FILES, matches as feature_matches
from package_goal21d import (LOCALIZATION_RECORD, STAMP, EN, SNAPSHOT, SOURCE_HEAD, ZH_ENTRY, EN_ENTRY, lang_delta, compare_paths, lines_of,
                             eol_counts, insertions, in_compare_inventory, changed_since_start)
from package_goal22a import annotations
from package_goal22b import (git_ro, original_blob, edit_counts, stale_diff, verifier_problems as base_verifier_problems, receipt_protected,
                             start_drift_paths, AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE, J
from package_goal22d import OUT as GOAL22D_OUT, BASELINE as GOAL22D_BASELINE, protected_paths as goal22d_protected_paths

OUT = ROOT/'build/migration/goal23a'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL22D_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL22D_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal22d/hbmsntm-198A-goal22d.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal23a'
RELEASE_NAME = 'hbmsntm-198A-goal23a.jar'
OWNER = 'goal23a'
GOAL22_CLOSEOUT = '670d5911'
PLANNING_PREFIX = 'dd69a404'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
# Production (owner goal23a): the nine modified Java sources plus the Chinese file and its mapping. No file is new and no registry or save format
# changes. NtmLanguageProvider and HazardData are insert-only against their start copies; the others replace lines (the receipt records each one's
# added and removed line counts).
TRAIT = J+'inventory/fluid/trait/'
FT_COMBUSTIBLE, FT_POLLUTING, FT_VENT_RADIATION = TRAIT+'FT_Combustible.java', TRAIT+'FT_Polluting.java', TRAIT+'FT_VentRadiation.java'
PROVIDER = J+'datagen/NtmLanguageProvider.java'
HAZARD_DATA, HAZARD_SYSTEM = J+'hazard/HazardData.java', J+'hazard/HazardSystem.java'
HAZARD_HOT, HAZARD_HYDRO = J+'hazard/type/HazardTypeHot.java', J+'hazard/type/HazardTypeHydroactive.java'
HAZARD_TESTS = J+'gametest/HazardGameTests.java'
MODIFIED_JAVA = [FT_COMBUSTIBLE, FT_POLLUTING, FT_VENT_RADIATION, PROVIDER, HAZARD_DATA, HAZARD_SYSTEM, HAZARD_HOT, HAZARD_HYDRO, HAZARD_TESTS]
PRODUCTION = MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]
# Insert-only production sources: path -> exact inserted line count (None = any, removed must be 0).
INSERT_ONLY = {PROVIDER: 15, HAZARD_DATA: None}
GENERATED = [STAMP, EN]
TOOLS = ['tools/migration/verify_goal23a_closeout.py', 'tools/migration/package_goal23a.py']
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal23a-* or GOAL23A-* record is hashed as well.
REPORTS = ['migration/GOAL23A.md', 'migration/GOAL23A-ACCEPTANCE.md', 'migration/goal23a-static-review.md']
BATCH_RECORD = re.compile(r'migration/(goal23a-[^/]+\.(json|md)|GOAL23A-[^/]+\.md)')
SHARED_RECORDS = ['migration/GOAL23.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md']
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + SHARED_RECORDS
# The 13 language keys (English via NtmLanguageProvider, Chinese in zh_cn.json): 12 are the original's keys (upstream mapping entries, the original
# English and Chinese verbatim), pollution.trait.fallout is NEO-local (the original has no such key).
UPSTREAM_KEYS = ['hbmfluid.trait.combustible', 'hbmfluid.trait.perBucket', 'hbmfluid.trait.fuelGrade', 'hbmfluid.trait.polluting', 'hbmfluid.trait.spilled',
                 'hbmfluid.trait.burned', 'hbmfluid.trait.perMB', 'hbmfluid.trait.radioactive', 'hbmfluid.trait.provides', 'pollution.trait.soot',
                 'pollution.trait.poison', 'pollution.trait.heavymetal']
LOCAL_KEY, LOCAL_ZH = 'pollution.trait.fallout', '沉降物'
KEYS = sorted(UPSTREAM_KEYS + [LOCAL_KEY])
NEW_TESTS = ['hazard_register_stacks', 'hazard_hot_reacher_anywhere_in_inventory', 'hazard_hydroactive_held_explodes_at_eye_height',
             'hazard_hydroactive_dropped_item_explodes']
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'compile-start.log', 'add_localization.py', 'planning-commit-msg.txt',
                  'chain.sh', 'handoff-verifier.md', 'handoff-packaging.md')
GAMETEST_LOG = 'build/migration/goal23a/gametest-final.log'
NEW_SUITE = 'verify_goal23a_closeout.py --gametest-log build/migration/goal23a/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_MATERIALS, FEATURE_FLUIDS = 'materials', 'fluid-logistics'
RADIATION_NOTE = ('Goal23A: a player or mob holding hydroactive materials (caesium powder, lithium, sodium and strontium items, Sr-90 and Cs-137 powders, '
                  'the lithium crystal at level 10) in water or rain now sets off a block-breaking explosion at eye height, and dropped ones explode at half '
                  'their height, as in the original; disableHydroactive turns this off; test only in separately authorized disposable worlds away from '
                  'buildings. ')
ORIGINAL = 'src/main/java/com/hbm/'
O_SYSTEM, O_HOT, O_HYDRO = ORIGINAL+'hazard/HazardSystem.java', ORIGINAL+'hazard/type/HazardTypeHot.java', ORIGINAL+'hazard/type/HazardTypeHydroactive.java'
O_TRAIT = ORIGINAL+'inventory/fluid/trait/'
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'register_ore_map_put': (O_SYSTEM, 'oreMap.put((String)o, data);'),
    'register_item_map_put': (O_SYSTEM, 'itemMap.put((Item)o, data);'),
    'register_block_item_map_put': (O_SYSTEM, 'itemMap.put(Item.getItemFromBlock((Block)o), data);'),
    'register_stack_map_put': (O_SYSTEM, 'stackMap.put(new ComparableStack((ItemStack)o), data);'),
    'register_comparable_stack_map_put': (O_SYSTEM, 'stackMap.put((ComparableStack)o, data);'),
    'query_ore_map': (O_SYSTEM, 'chronological.add(oreMap.get(name));'),
    'query_item_map': (O_SYSTEM, 'chronological.add(itemMap.get(stack.getItem()));'),
    'query_stack_map': (O_SYSTEM, 'chronological.add(stackMap.get(comp));'),
    'hot_enable528_gate': (O_HOT, '!GeneralConfig.enable528'),
    'hot_reacher_inventory': (O_HOT, 'inventory.hasItem(ModItems.reacher)'),
    'hot_fire_condition': (O_HOT, '!reacher && !target.isWet() && level > 0'),
    'hydro_held_explosion': (O_HYDRO, 'target.posY + target.getEyeHeight() - target.getYOffset(), target.posZ, level, false, true);'),
    'hydro_dropped_explosion': (O_HYDRO, 'item.posY + item.height * 0.5, item.posZ, level, false, true);'),
    'trait_combustible': (O_TRAIT+'FT_Combustible.java', 'resolveKey("hbmfluid.trait.combustible")'),
    'trait_provides': (O_TRAIT+'FT_Combustible.java', 'resolveKey("hbmfluid.trait.provides")'),
    'trait_per_bucket': (O_TRAIT+'FT_Combustible.java', 'resolveKey("hbmfluid.trait.perBucket")'),
    'trait_fuel_grade': (O_TRAIT+'FT_Combustible.java', 'resolveKey("hbmfluid.trait.fuelGrade")'),
    'trait_polluting': (O_TRAIT+'FT_Polluting.java', 'resolveKey("hbmfluid.trait.polluting")'),
    'trait_spilled': (O_TRAIT+'FT_Polluting.java', 'resolveKey("hbmfluid.trait.spilled")'),
    'trait_burned': (O_TRAIT+'FT_Polluting.java', 'resolveKey("hbmfluid.trait.burned")'),
    'trait_per_mb': (O_TRAIT+'FT_Polluting.java', 'resolveKey("hbmfluid.trait.perMB")'),
    'trait_pollution_type': (O_TRAIT+'FT_Polluting.java', '"pollution.trait." + entry.getKey().name().toLowerCase(Locale.US)'),
    'trait_radioactive': (O_TRAIT+'FT_VentRadiation.java', 'resolveKey("hbmfluid.trait.radioactive")'),
}
VERIFIER_REFERENCE = re.compile(r'(?:HazardSystem|HazardTypeHot|HazardTypeHydroactive|FT_Combustible|FT_Polluting|FT_VentRadiation)\.java:\d+(?:-\d+)?')


def scope_text(language_count, upstream_count, local_count, new_tests, total_tests):
    return (f'Goal23A (Goal 22 close-out remainders, no new item, block, registration, recipe, data component or save format): (23A-2) FT_Combustible, '
            f'FT_Polluting and FT_VentRadiation use the original\'s fluid trait tooltip keys (hbmfluid.trait.combustible, polluting, spilled, burned, perMB, '
            f'radioactive instead of fluids.trait.* / fluid.trait.perMB) and {language_count} language keys are added (NtmLanguageProvider inserts 15 lines; '
            f'generated en_us.json +{language_count}; zh_cn.json +{language_count}; zh_cn-map.json +{language_count} entries: {upstream_count} upstream '
            f'reusing the original Chinese, {local_count} local pollution.trait.fallout "{LOCAL_ZH}"); FT_Combustible\'s "Provides ... per bucket" line no '
            f'longer glues the fuel grade onto "per bucket" and shows the energy in red, as in the original. (23A-3) HazardSystem.register stacks a repeated '
            f'item/block/stack registration through the new HazardData.merge (a copy; an overriding later registration purges; a colliding mutex yields; '
            f'otherwise append and OR) instead of replacing it; queries are unchanged and today no key is registered twice, so no hazard reading changes. '
            f'(23A-4) HazardTypeHot: the reacher exempts a player when anywhere in the 36 main inventory slots or the offhand (original inventory.hasItem); '
            f'HazardTypeHydroactive: a held hydroactive item in water or rain explodes at eye height and breaks blocks (ExplosionInteraction.TNT), a dropped '
            f'one at half its height (TNT unchanged). (23A-5) The Sa326 crystal lethality is a static trace only, no code. {new_tests} HazardGameTests are '
            f'added ({total_tests} GameTests in total). Gameplay impact: a player or mob holding caesium powder, lithium crystals or other hydroactive '
            f'materials in water or rain now gets a block-breaking explosion at eye height (original behavior; disableHydroactive turns it off; the lithium '
            f'crystal is level 10, 2.5 x TNT).')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal23a release directory: '+rel


def protected_paths(base):
    """What the goal22d packager protected (built there from the Goal21A..Goal22C starts and receipts, the goal22c receipt and the goal22d start), plus
    every path the goal22d receipt hashes (base previous_receipt_protected_paths), the paths the older receipts hash (the 23A baseline lists the goal22c
    receipt among them) and every release file of the frozen start. The records that already drifted (the acceptance checklists after the Goal 21 and
    Goal 22 in-game acceptance and the close-out corrections, GOAL22C.md after the thorium follow-up, the O1 notes) are pinned at their Goal23A start hash
    (baseline files) instead of any receipt hash or any earlier start hash. One path never carries two hashes. Returns (protected, repinned) where repinned
    maps a record to the pin the goal22d packager set at its Goal22D start hash, for the records that changed between the two starts."""
    goal22d_start = read(GOAL22D_BASELINE)
    out = dict(goal22d_protected_paths(goal22d_start))
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'], 'Start drift path is not a frozen file: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        # The goal22d packager returns the unified checklist GOAL22C-ACCEPTANCE.md unpinned (it filled its section 4), but its final runner pinned it at its start hash.
        earlier = out.pop(p, goal22d_start['files'].get(p))
        if earlier is not None and earlier != base['files'][p]: repinned[p] = earlier
        out[p] = base['files'][p]
    assert all(p.endswith('-ACCEPTANCE.md') for p in repinned), 'A non-checklist pin changed between the Goal22D and Goal23A starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal22d_start):
    """{path: {receipts, start_sha256, goal22d_start_sha256, current_sha256, explanation}} for the records that differ from a receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal22d receipt'] = base['previous_receipt_protected_paths'][p]
        start = base['files'][p]
        newest = receipts.get('goal22d receipt')
        if newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21 and Goal 22 in-game acceptance result lines, the O1 record notes or the '
                           'thorium follow-up section); the goal22d receipt does not hash it. Frozen at the Goal23A start hash; this batch must not change it and '
                           'no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal22d) records the start hash. Frozen at '
                           'the start hash; this batch must not change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal22d package: the Goal 22 in-game acceptance results and the close-out checklist corrections were written into '
                           'it, so the goal22d receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal22d '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal22d_start_sha256=goal22d_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned:
            entry['repinned_from_goal22d_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def group(p):
    if p in MODIFIED_JAVA: return 'production'
    if p == ZH_INPUT: return 'production-chinese'
    if p == LOCALIZATION_RECORD: return 'production-localization-record'
    if p in GENERATED: return 'generated'
    if p in TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    return None


def verifier_problems(report, required):
    """Why verify/report.json (the passing tools/migration/verify_goal23a_closeout.py report) is not a passing run, [] otherwise: the goal22b checks plus
    the report's own 'pass' flag when it carries one."""
    problems = []
    if 'pass' in report and report['pass'] is not True: problems.append('pass is '+repr(report['pass']))
    problems += base_verifier_problems(dict(report, ok=report['pass']) if 'pass' in report and 'ok' not in report else report, required)
    return problems


def original_line(path, token):
    """1-based line of the first line of the original's stored blob (at the recorded commit) that contains the token."""
    for number, line in enumerate(original_blob(path).decode('utf-8').split('\n'), 1):
        if token in line: return number
    raise AssertionError(f'{path} has no line with {token!r} at the recorded original commit')


def main(check, gametest_log):
    pending = []

    def need(condition, message):
        """A condition of the real run: raises there; --check only lists it as pending."""
        if condition: return True
        if not check: raise AssertionError(message)
        pending.append(message)
        return False

    base = read(BASELINE)
    prior_receipt = read(PREVIOUS_RECEIPT)
    goal22d_start = read(GOAL22D_BASELINE)

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal23A commits nothing), the recorded clean start.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at 6a11998d'
    assert start_head.startswith(PLANNING_PREFIX) and base['planning_commit']['id'] == start_head and base['planning_commit']['parent'].startswith(GOAL22_CLOSEOUT), \
        'The frozen start is not the Goal 23 planning commit on top of the Goal 22 close-out commit'
    assert base['target_status'] == '' and base['dirty_paths'] == [] and base['pending_small_fixes'] == [] and base['concurrent_session'] is None, \
        'The frozen start is not a clean tree without pending small fixes'
    assert set(base['start_content']) == {'committed', 'uncommitted'}, 'Baseline start content differs'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal23A: '+head
    assert git_ro(ROOT, 'rev-parse', 'HEAD~1').strip().startswith(GOAL22_CLOSEOUT), 'NEO HEAD~1 is not the Goal 22 close-out commit'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b',
                                                          'goal22c'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['dirty_paths'] == len(base['dirty_paths']) and startup['frozen_file_hashes'] == len(base['files']) \
        and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['previous_jar_sha256'] == base['previous_release']['sha256'] and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']), 'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_verified'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal22d generated tree'
    # build/libs at the start is the goal22d package byte for byte (a clean start has no working-tree JAR).
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal22d package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha and not any(base['build_libs_vs_previous'].values()), 'build/libs at the start is not the previous package byte for byte'
    assert sha(PREVIOUS) == previous_sha and PREVIOUS.stat().st_size == previous_bytes == base['build_libs_jar_bytes'], 'Previous JAR changed'
    assert prior_receipt['sha256'] == previous_sha and prior_receipt['bytes'] == previous_bytes, 'Previous receipt names another JAR'
    previous_receipt_sha = base['old_release_files'][PREVIOUS_RECEIPT.relative_to(ROOT).as_posix()]
    previous_sums_sha = base['old_release_files'][PREVIOUS_SUMS.relative_to(ROOT).as_posix()]
    assert sha(PREVIOUS_RECEIPT) == previous_receipt_sha, 'Previous release.json changed'
    assert sha(PREVIOUS_SUMS) == previous_sums_sha, 'Previous SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (previous_sha+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Previous SHA256SUMS.txt content changed'
    for p, h in base['old_release_files'].items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release file changed: '+p
    previous_rel = PREVIOUS.relative_to(ROOT).as_posix()
    old_releases = dict(base['old_releases'])
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal22d receipt list + the goal22d package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal22d receipt count + the goal22d release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal22d receipt'
    assert base['previous_receipt_evidence_drift'] == ['migration/GOAL21C-ACCEPTANCE.md', 'migration/GOAL22C-ACCEPTANCE.md', 'migration/GOAL22D-ACCEPTANCE.md'], \
        'The goal22d receipt evidence drift at the start is not exactly the three acceptance checklists: '+str(base['previous_receipt_evidence_drift'])
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal22d_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal22d receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal23a. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal23A start that the owner table does not list (production outside the nine Java files, zh_cn.json and the '
         'mapping, a generated file other than the stamp and en_us.json, a protected record, or an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal23A start: '+str(deleted)
    for p in PRODUCTION + GENERATED + SHARED_RECORDS + REPORTS[:1]: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in TOOLS: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION if p.startswith('src/')})
    need(not outside, 'src/main change outside the nine Java files and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    assert baselines_now == {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}, 'A snapshot was added or changed'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'], 'review-6a11998d5852 snapshot changed'
    production_changed = [p for p in PRODUCTION if p in changes]

    # The modified production files keep their start line endings (the frozen start copies are the baseline files).
    start_text = {}
    for p in PRODUCTION:
        if p not in changes: continue
        if not need(p in base['copied_scope'], p+' has no frozen start copy in baseline-files (not in copied_scope)'): continue
        start_text[p] = (START_FILES/p).read_bytes()
        start_eol, eol = eol_counts(start_text[p]), eol_counts((ROOT/p).read_bytes())
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}')

    # Production Java facts: the language provider and HazardData are insert-only against their start copies; every line edit is counted.
    insert_summary, edit_summary = {}, {}
    for p in MODIFIED_JAVA:
        if p not in start_text: continue
        start_lines, live_lines = lines_of(start_text[p]), lines_of((ROOT/p).read_bytes())
        edit_summary[p] = edit_counts(start_lines, live_lines)
        if p not in INSERT_ONLY: continue
        inserted = insertions(start_lines, live_lines)
        if not need(inserted is not None, f'{p} is not insert-only against the start copy (a start line was changed, moved or removed)'): continue
        insert_summary[p] = len(inserted)
        need(edit_summary[p]['removed'] == 0, f'{p} removes {edit_summary[p]["removed"]} start lines (insert-only expected)')
        if INSERT_ONLY[p] is not None: need(len(inserted) == INSERT_ONLY[p], f'{p} inserts {len(inserted)} lines, expected {INSERT_ONLY[p]}')
        if p == PROVIDER:
            text = '\n'.join(l for _, l in inserted)
            added = sorted(re.findall(r'this\.add\("([^"]+)"', text))
            need(added == KEYS, f'{p} adds the keys {added}, not the {len(KEYS)} language keys {KEYS}')
    # The original lines the receipt quotes (the stored blobs at the recorded commit, independent of the worktree's line endings).
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}

    # 4. Language and the generated tree: exactly the 13 keys, in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_delta = dict(added=KEYS, removed=[], changed=[])
    need(en_delta == expected_delta, 'generated en_us.json delta is not the 13 trait keys: '+json.dumps(en_delta, ensure_ascii=False))
    need(zh_delta == expected_delta, 'zh_cn.json delta is not the 13 trait keys: '+json.dumps(zh_delta, ensure_ascii=False))
    need(map_delta == expected_delta, 'zh_cn-map.json delta is not the 13 trait entries: '+json.dumps(map_delta, ensure_ascii=False))
    need(len(en_now) == prior_receipt['language']['totals']['en_us'] + len(KEYS) and len(zh_now) == prior_receipt['language']['totals']['zh_cn'] + len(KEYS)
         and len(map_now) == prior_receipt['language']['totals']['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal22d totals {prior_receipt["language"]["totals"]} + {len(KEYS)}')
    if map_delta == expected_delta:
        bad = [k for k in UPSTREAM_KEYS if map_now[k].get('kind') != 'upstream' or map_now[k].get('source_key') != k or map_now[k].get('source_en') != map_now[k].get('target_en')
               or map_now[k].get('source_zh') != map_now[k].get('target_zh') or map_now[k].get('target_en') != en_now.get(k) or map_now[k].get('target_zh') != zh_now.get(k)]
        need(not bad, 'zh_cn-map.json entries are not upstream entries matching en_us.json and zh_cn.json: '+str(bad))
        local = map_now[LOCAL_KEY]
        need(local.get('kind') == 'local' and local.get('reason') and local.get('target_zh') == LOCAL_ZH == zh_now.get(LOCAL_KEY) and local.get('target_en') == en_now.get(LOCAL_KEY),
             f'zh_cn-map.json {LOCAL_KEY} is not a local entry with a reason and {LOCAL_ZH}')
    language_kinds = dict(Counter(map_now[k].get('kind') for k in KEYS if k in map_now))
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    stamp_current = not stale and not mismatch and not unrecorded
    need(stamp_current, f'{STAMP} not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
    start_stamp = read(START_FILES/STAMP)
    start_generated = start_stamp['generated']
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal22d generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(not generated_added, f'Generated resources added since the start (the batch generates no new resource): {generated_added[:8]}')
    need(generated_changed == [EN_ENTRY], f'Generated resources changed since the start: {generated_changed[:5]} (expected only {EN_ENTRY})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    need(set(generated_since) <= set(GENERATED), 'Generated files changed since the start other than the stamp and en_us.json: '+str([p for p in generated_since if p not in GENERATED][:8]))
    # The mapping groups must list every changed compare-inventory path.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    if need(FEATURE_MATERIALS in by_id, 'migration/features.json has no group '+FEATURE_MATERIALS):
        need('Goal23A' in ' '.join(by_id[FEATURE_MATERIALS].get('notes', [])), f'migration/features.json group {FEATURE_MATERIALS} notes do not mention Goal23A')
        for p in (HAZARD_SYSTEM, HAZARD_DATA, HAZARD_HOT, HAZARD_HYDRO):
            need(feature_matches(by_id[FEATURE_MATERIALS], 'target', p), f'features.json group {FEATURE_MATERIALS} lists {p} in neither target_paths nor target_watch')
    if need(FEATURE_FLUIDS in by_id, 'migration/features.json has no group '+FEATURE_FLUIDS):
        need('Goal23A' in ' '.join(by_id[FEATURE_FLUIDS].get('notes', [])), f'migration/features.json group {FEATURE_FLUIDS} notes do not mention Goal23A')
        need(feature_matches(by_id[FEATURE_FLUIDS], 'target', FT_VENT_RADIATION), f'features.json group {FEATURE_FLUIDS} lists {FT_VENT_RADIATION} in neither target_paths nor target_watch')
    need(set(by_id) == set(start_features), 'features.json group ids differ from the start: '+str(sorted(set(by_id) ^ set(start_features))))
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    task_book = ROOT/REPORTS[0]
    book_text = task_book.read_text(encoding='utf-8') if task_book.is_file() else ''
    start_book = (START_FILES/REPORTS[0]).read_text(encoding='utf-8')
    for token in ('Sa326', '与原版一致'):
        # The task book already names both as the options of 23A-5; the delivery record must add occurrences.
        need(book_text.count(token) > start_book.count(token), f'{REPORTS[0]} does not record the Sa326 trace conclusion (no occurrence of {token!r} added to the start copy)')

    # 5. Evidence: GameTest log, audits, Gradle logs, diff, the final suite run, the verifier report and compare.
    evidence = {}
    gametest_line = gametest_count = None
    total_now = sum(annotations(p) for p in sorted(GAMETEST_DIR.glob('*.java')))
    total_start = 0
    for p in sorted(GAMETEST_DIR.glob('*.java')):
        rel = p.relative_to(ROOT).as_posix()
        if rel in base['files']: total_start += annotations(START_FILES/rel if base['files'][rel] != sha(p) and rel in base['copied_scope'] else p)
    assert total_start == prior_receipt['gametest']['tests'], 'The start GameTest sources do not hold the previous count of '+str(prior_receipt['gametest']['tests'])
    gametest_added = total_now - total_start
    gametest_expected = total_now
    hazard_tests_now, hazard_tests_start = annotations(ROOT/HAZARD_TESTS), annotations(START_FILES/HAZARD_TESTS)
    names_now = set(GAMETEST_METHOD.findall((ROOT/HAZARD_TESTS).read_text(encoding='utf-8')))
    names_start = set(GAMETEST_METHOD.findall((START_FILES/HAZARD_TESTS).read_text(encoding='utf-8')))
    new_test_names = sorted(names_now - names_start)
    need(new_test_names == sorted(NEW_TESTS), f'{HAZARD_TESTS} adds the GameTest methods {new_test_names}, not {sorted(NEW_TESTS)}')
    need(names_start <= names_now, f'{HAZARD_TESTS} lost start GameTest methods: {sorted(names_start - names_now)}')
    need(gametest_added == len(new_test_names) == hazard_tests_now - hazard_tests_start,
         f'GameTest sources grew by {gametest_added} tests, HazardGameTests by {hazard_tests_now - hazard_tests_start} annotations and {len(new_test_names)} methods (another GameTest file changed?)')
    log = (ROOT/gametest_log).resolve() if gametest_log else None
    if need(log is not None and log.is_file(), 'GameTest log (--gametest-log): '+(str(gametest_log) if gametest_log else 'not given')+' does not exist yet'):
        assert log.is_relative_to(ROOT), 'GameTest log outside the NEO repository: '+str(log)
        text = log.read_text(encoding='utf-8-sig', errors='replace')
        found = GAMETEST.findall(text)
        if need(bool(found) and 'BUILD SUCCESSFUL' in text and 'invalid dist' not in text and 'NoClassDefFoundError' not in text,
                log.relative_to(ROOT).as_posix()+' did not pass cleanly (needs "All N required tests passed" and BUILD SUCCESSFUL, no "invalid dist" or NoClassDefFoundError)'):
            gametest_count = int(found[-1])
            need(gametest_count == gametest_expected,
                 f'GameTest server ran {gametest_count} tests, the sources hold {gametest_expected} @GameTest methods ({prior_receipt["gametest"]["tests"]} previous tests + {gametest_added})')
            gametest_line = f'All {gametest_count} required tests passed'
            need(all(f'[hbm-hazard] {n} passed' in text for n in new_test_names), 'GameTest log lacks "[hbm-hazard] <name> passed" for: '+str([n for n in new_test_names if f'[hbm-hazard] {n} passed' not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal23a/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal23a/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal23a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE:
        if not need((OUT/name).is_file(), 'start evidence missing: build/migration/goal23a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain.sh output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal23a/'+name+' (written by chain.sh final)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (all eleven files against their start copies) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    if diff_path.is_file() and diff_path.stat().st_size and all(p in start_text for p in PRODUCTION):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in PRODUCTION])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in PRODUCTION), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in PRODUCTION if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal22d final run plus the Goal23A verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert NEW_SUITE not in reference_suites, 'The Goal23A suite is already in the goal22d final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal23a/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        assert set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal22d final set + the Goal23A verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE})))
        entry = final['suites'][NEW_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, NEW_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal23a/'+VERIFY_REPORT+' (tools/migration/verify_goal23a_closeout.py report)'):
        report = read(OUT/VERIFY_REPORT)
        problems = verifier_problems(report, production_changed)
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        mutations = report.get('mutations')
        mutation_entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
        detected = summary_part.get('mutations_detected', sum(1 for e in mutation_entries if isinstance(e, dict) and e.get('detected') is True))
        total = summary_part.get('mutations_total', len(mutation_entries))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=TOOLS[0],
                        tool_sha256=sha(ROOT/TOOLS[0]) if (ROOT/TOOLS[0]).is_file() else None, mutations_detected=f'{detected}/{total}', mutations_total=total)
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(VERIFIER_REFERENCE.findall(json.dumps(report, ensure_ascii=False))))
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree): the original unchanged, the target exactly the goal22d receipt's compare target
    # set plus this batch's paths inside the compare inventory; compare never lists the stamp; no unmapped change. No new snapshot.
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'previous receipt compare target set is incomplete'
    prior_cmp = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_compare['sha256'], 'previous compare.json changed'
    assert compare_paths(prior_cmp['changes']['target']['added']) | compare_paths(prior_cmp['changes']['target']['modified']) == previous_target, \
        'previous compare.json target set differs from its receipt'
    expected_target = sorted(previous_target | {p for p in changes if in_compare_inventory(p)})
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal23a/'+COMPARE+' (compare against '+SNAPSHOT+'; expected target set: %d paths)' % len(expected_target)):
        cmp = read(OUT/COMPARE)
        assert cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the 6a11998d snapshot'
        counts = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        assert all(v == 0 for v in counts['source'].values()), 'compare.json source is not 0/0/0: '+str(counts['source'])
        target = cmp['changes']['target']
        assert not target['removed'], 'compare.json target removed: '+str(target['removed'])
        assert not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], 'compare.json reports unmapped changes: '+str(cmp['unmapped_changes'])
        assert not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], 'compare.json reports removed features or missing files'
        listed = sorted(p for p in compare_paths(target['added']) | compare_paths(target['modified']) if not p.endswith('/.migration-stamp.json'))
        assert listed == expected_target, 'compare.json target set differs: extra %s, missing %s' % (
            sorted(set(listed) - set(expected_target)), sorted(set(expected_target) - set(listed)))

        def compare_owners(p):
            return set(prior_compare['target_owners'].get(p, [])) | ({OWNER} if p in changes else set())
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts,
                       target_owners={p: sorted(compare_owners(p)) for p in listed})
        evidence[compare['path']] = compare['sha256']

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal23a.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal22d) package (run build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json and every compiled class equal the sources.
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == en_delta == expected_delta and zh_jar == zh_delta == expected_delta,
                 'JAR en_us.json or zh_cn.json delta against the previous package is not the 13 trait keys: en '+str(en_jar)+', zh '+str(zh_jar))
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if n.endswith('.class') and owner_class(n) in MODIFIED_JAVA: owner = [OWNER]
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY): owner = [OWNER]
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the nine Java sources and the modified en_us.json / zh_cn.json are owned): '+str(unowned))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        goal23a_classes = [n for n, o in entry_owners.items() if o['owners'] == [OWNER] and n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in goal23a_classes})
        changed_java = [p for p in MODIFIED_JAVA if p in changes]
        need(set(class_owners) == set(changed_java), 'Changed Java sources and goal23a JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == {ZH_ENTRY, EN_ENTRY}, 'JAR non-class delta is not exactly en_us.json and zh_cn.json: extra %s, missing %s' % (
            sorted(non_class - {ZH_ENTRY, EN_ENTRY})[:8], sorted({ZH_ENTRY, EN_ENTRY} - non_class)))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        for n in ('com/hbm/hazard/HazardData.class', 'com/hbm/hazard/HazardSystem.class', 'com/hbm/hazard/type/HazardTypeHot.class', 'com/hbm/hazard/type/HazardTypeHydroactive.class',
                  'com/hbm/inventory/fluid/trait/FT_Combustible.class', 'com/hbm/inventory/fluid/trait/FT_Polluting.class', 'com/hbm/inventory/fluid/trait/FT_VentRadiation.class',
                  'com/hbm/datagen/NtmLanguageProvider.class', 'com/hbm/gametest/HazardGameTests.class'):
            need(n in jar_delta['modified'], n+' is not a modified JAR class')
        added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
        removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
        need(bool(classes) and len(classes) == prior_receipt['compiled_classes_verified'] + added_classes - removed_classes,
             f'Compiled class count {len(classes)} is not the previous count {prior_receipt["compiled_classes_verified"]} +{added_classes} -{removed_classes}')
        language = dict(en=en_jar, zh=zh_jar)

    # 7. Records: the release name and the batch reports.
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    for p in unnamed: need(False, 'record does not name '+RELEASE_NAME+': '+p)
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added),
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal22d_start=sorted(repinned),
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                   insert_lines=insert_summary, edit_counts=edit_summary, gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added,
                   new_hazard_tests=new_test_names, final_suites_expected=final_expected, compare=compare['counts'] if compare else None,
                   compare_target_expected=len(expected_target), jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None,
                   jar_directory_delta=dir_delta, class_owners=class_owners, protected_paths=len(protected), old_releases_preserved=len(old_releases),
                   preserved_release_files=len(base['old_release_files']), older_checklist_drift_explained=sorted(explained),
                   jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists. Build the whole receipt before the first write.
    dest = RELEASE/RELEASE_NAME
    digest = sha(JAR)
    assert digest not in (previous_sha, start_jar_sha), 'build/libs JAR is an older JAR'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal23a JAR'
    hashes = {p: sha(ROOT/p) for p in reports}
    local_count = sum(1 for k in KEYS if map_now[k].get('kind') == 'local')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), len(KEYS) - local_count, local_count, len(new_test_names), gametest_count),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=start_head,
                   planning_commit=dict(id=base['planning_commit']['id'], parent=base['planning_commit']['parent'], paths=base['planning_commit']['paths'],
                                        message_file=(OUT/'planning-commit-msg.txt').relative_to(ROOT).as_posix()),
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha, base_release_receipt_sha256=previous_receipt_sha,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, dirty_paths=base['dirty_paths'],
                                      note='The start tree is HEAD dd69a404 (the Goal 23 planning commit on top of the Goal 22 close-out commit 670d5911, which '
                                           'holds all of Goal 22 and the goal22d package sources) with a clean working tree and no pending small fix; build/libs at '
                                           'the start is the goal22d package byte for byte. Paths this batch changes (the stamp, en_us.json, zh_cn.json, the zh_cn '
                                           'mapping, GOAL23A.md, GOAL23.md and the shared records) record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[], production_unchanged_optional=[],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary,
                   resources={},
                   hazards=dict(verifier_report=verifier['path'], verifier_report_sha256=verifier['sha256'], verifier_original_references=verifier_references,
                                original_references=original_refs,
                                register_stacking=dict(
                                    neo='HazardSystem.register merges a repeated Item, Block (asItem), ItemStack (ComparableStack) or ComparableStack registration through '
                                        'itemMap/stackMap.merge(key, data, HazardData::merge) instead of replacing it. HazardData.merge(later) copies the earlier data '
                                        '(doesOverride, mutex bits, entries); a later registration with doesOverride purges the earlier entries; a later mutex that '
                                        'collides with the accumulated mutex bits yields (its entries are dropped); otherwise the later entries are appended and the '
                                        'mutex bits ORed. The tag map keeps the replacing put; the queries (getHazardsFromStack and the rest) are unchanged.',
                                    original='The original keeps frame rows in oreMap and item-level rows in itemMap and stacks them at query time; NEO has no ore '
                                             'dictionary, so frame and item rows both register into itemMap and must stack there.',
                                    gameplay='None today: no key is registered twice, so no hazard reading changes; a later row (23B RTG) with an existing key would stack.'),
                                hot_reacher=dict(
                                    neo='HazardTypeHot exempts a player (outside 5.28 mode) when a reacher is anywhere in the 36 main inventory slots or the offhand '
                                        '(the offhand is a NEO-only extension kept from the earlier hands-only rule); armor is not scanned.',
                                    original='HazardTypeHot uses inventory.hasItem(ModItems.reacher) behind !GeneralConfig.enable528 (the main inventory).'),
                                hydroactive=dict(
                                    neo='A held hydroactive stack in water or rain is emptied and explodes at the holder\'s eye height (getEyeY) with '
                                        'ExplosionInteraction.TNT (breaks blocks); a dropped item explodes at y + half its height (TNT unchanged); '
                                        'disableHydroactive turns both off.',
                                    original='HazardTypeHydroactive: newExplosion at posY + getEyeHeight() - getYOffset() and at item posY + height * 0.5, both with '
                                             '(false, true); the original also checks the block material at the dropped item (NEO uses isInWaterOrRain only).',
                                    gameplay='A player or mob holding caesium powder, lithium crystals or other hydroactive materials in water or rain now gets a '
                                             'block-breaking explosion at eye height (original behavior); the lithium crystal is level 10, 2.5 x TNT.'),
                                sa326=dict(record=REPORTS[0], code_change=False,
                                           note='Static trace of the Sa326 crystal lethality (23A-5); the conclusion is recorded in the task book and changes no code.')),
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now[k].get('kind') == 'local'],
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)}, jar_delta=language,
                                 note='13 keys: 12 upstream (the original English and Chinese verbatim) and pollution.trait.fallout, a NEO-local key for the NEO-only '
                                      'PollutionType.FALLOUT; NtmLanguageProvider inserts 15 lines (2 comment lines + 13 add calls).'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report, repinned_since_goal22d_start={p: dict(goal22d_start_pin_sha256=h, goal23a_start_sha256=base['files'][p])
                                                                                    for p, h in repinned.items()},
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count, added_tests=gametest_added,
                                 new_hazard_tests=new_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; the four new tests cover the '
                                      'register stacking on an otherwise unregistered vanilla item, a hot reacher in a non-hand inventory slot where the test can '
                                      'construct one, and the held and dropped caesium powder explosions in water; tooltips, real player inventories and rain are '
                                      'not covered.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, '
                            'the static verifier with in-memory mutations, the final old-suite rerun, compare against the review-6a11998d5852 snapshot and two '
                            'independent static reviews. No in-game client test was run: the fluid tank tooltips and JEI fluid tooltips in either language, the '
                            'reacher exemption with a real player inventory, the rain case, multiplayer, a dedicated server outside the GameTest run and a '
                            'lithium-crystal blast are unverified; GOAL23A-ACCEPTANCE.md is written but not executed.')
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal22d package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
