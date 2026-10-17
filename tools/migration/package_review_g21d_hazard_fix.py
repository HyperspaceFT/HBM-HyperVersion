"""Package Goal21D review fix O1 (CommonEvents.onLivingTick applied the hazards of a player's selected hotbar item, offhand and armor twice per
tick and on both logical sides; it now applies them on the server only, once per stack per tick) cumulatively on the goal21d package, without
replacing any previous delivery.

python -B -X utf8 tools/migration/package_review_g21d_hazard_fix.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending; the real mode writes only
build/migration/releases/review-g21d-hazard-fix-20261017/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to
build/migration/review-fixes-g21d-hazard/gametest-fix.log (the GameTest dedicated-server log of the settled tree).

The frozen start is build/migration/review-fixes-g21d-hazard/baseline.json: NEO HEAD dbfa6746 plus the uncommitted Goal21A delivery, the control-NBT
null fix, the Goal21B, Goal21C and Goal21D deliveries (build/libs at the start is the goal21d package). Every change since the start is computed from
the baseline file hashes (not from git diff, which would include the start content) and must be in the owner table below; start content outside the
owner table must still equal its start hash. The JAR delta against the goal21d package is attributed per entry to review-g21d-hazard and must be
exactly the two changed classes. The fix adds no resource and no language key: en_us.json, zh_cn.json, the zh_cn mapping and NtmLanguageProvider must
equal their start bytes. Counts that records quote (suites, GameTests, generated resources, releases) are computed here, never hard-coded.

The goal21d receipt hashes GOAL21D.md, GOAL21D-ACCEPTANCE.md and goal21d-static-review.md, and the goal21d receipt explains the drift of
GOAL21C-ACCEPTANCE.md (hashed by the goal21c receipt). This batch inserts a dated note into each of the four, so each is checked as insert-only against
its frozen start copy (whose hash must equal the hash its newest receipt records), every inserted block carrying the batch marker and the date, and
listed as explained drift with before and after hashes. No other protected path may drift, and no receipt is rewritten."""
from collections import Counter
from difflib import SequenceMatcher
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
from package_review_g20_display_fixes import protected_drift as display_protected_drift, split_drift
from migration import BUILD_FILES
from package_goal21d import (BASELINE as GOAL21D_BASELINE, protected_paths as goal21d_protected_paths, ACCEPTANCE_21C, UNCHANGED_LANGUAGE,
                             LOCALIZATION_RECORD, STAMP, EN, SNAPSHOT, SOURCE_HEAD, START_HEAD, ZH_ENTRY, EN_ENTRY, AUDITS, lang_delta,
                             compare_paths, lines_of, eol_counts, insertions, in_compare_inventory, changed_since_start)

OUT = ROOT/'build/migration/review-fixes-g21d-hazard'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_21D = ROOT/'build/migration/goal21d/final/summary.json'
PREVIOUS_COMPARE = ROOT/'build/migration/goal21d/compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal21d/hbmsntm-198A-goal21d.jar'
PREVIOUS_SHA = 'b17291d178184e6b967685cf6deb84048e27b9aa106ba7962e5cce06d42e45e3'
PREVIOUS_BYTES = 18407190
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal21d/release.json'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal21d/SHA256SUMS.txt'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'review-g21d-hazard-fix-20261017'
RELEASE_NAME = 'hbmsntm-198A-g21d-hazard-fix.jar'
# build/libs at the start is the goal21d package itself; packaging it again would package no fix.
START_JAR_SHA = PREVIOUS_SHA
OWNER = 'review-g21d-hazard'
DATE = '2026-10-17'
MARKER = 'REVIEW-FIXES-GOAL21D-HAZARD-ONCE'
J = 'src/main/java/com/hbm/'
COMMON_EVENTS = J+'main/CommonEvents.java'
GAMETEST_JAVA = J+'gametest/HazardGameTests.java'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
PRODUCTION = [COMMON_EVENTS, GAMETEST_JAVA]
GENERATED = [STAMP]
VERIFIER = 'tools/migration/verify_review_goal21d_hazard_once.py'
THIS = 'tools/migration/package_review_g21d_hazard_fix.py'
TOOLS = [VERIFIER, THIS]
# The verifier's isolated harness files: added only if the verifier needs them.
OPTIONAL_TOOLS = ['tools/migration/review_fixes/HazardOnceRegression.java', 'tools/migration/review_fixes/hazard_once_stubs.py']
FIX_RECORD = 'migration/REVIEW-FIXES-GOAL21D-HAZARD-ONCE.md'
FIX_RECORD_PATTERN = re.compile(r'migration/REVIEW-FIXES-GOAL21D-HAZARD-[^/]+\.(json|md)')
# Hashed by the goal21d receipt (report_sha256), hashed by this receipt again and edited here by dated insert-only notes.
NOTE_RECORDS_21D = ['migration/GOAL21D.md', 'migration/GOAL21D-ACCEPTANCE.md', 'migration/goal21d-static-review.md']
# Hashed by the goal21c receipt; the goal21d receipt explains its drift (goal21c_acceptance_drift_explained.after_sha256).
NOTE_RECORDS = NOTE_RECORDS_21D + [ACCEPTANCE_21C]
SHARED_RECORDS = ['migration/GOAL21.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md']
NAMES_RELEASE = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
# Must have changed (or been added) by the time of the real run; the rest of the owner table is optional.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + [FIX_RECORD] + NOTE_RECORDS + ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md', 'migration/features.json']
# Evidence the receipt indexes (the main agent produces them in OUT; the two Gradle logs must end in BUILD SUCCESSFUL).
LOGS = ('rundata-fix.log', 'build-fix.log')
FILES = ('start-worktree.patch', 'production-vs-start.diff', 'validate.log', 'startup-verification.json')
VERIFY_REPORT = 'verify-report.json'
FINAL_SUMMARY = 'final/summary.json'
COMPARE = 'compare.json'
# Written by chain.sh next to the logs; checked and indexed when present.
CHAIN_FILES = ('chain-exits.txt', 'chain-done.txt', 'jar-fix.sha256')
GAMETEST_LOG = 'build/migration/review-fixes-g21d-hazard/gametest-fix.log'
NEW_SUITE = ('verify_review_goal21d_hazard_once.py --tree --jar build/libs/hbmsntm-198A.jar '
             '--gametest-log build/migration/review-fixes-g21d-hazard/gametest-fix.log')
GAMETEST = re.compile(r'All (\d+) required tests passed')
GAMETEST_ANNOTATION = re.compile(r'^\s*@GameTest\(', re.M)
SCOPE = ('Goal21D review fix O1: CommonEvents.onLivingTick applied the material hazards of a player\'s selected hotbar item, offhand and armor twice per '
         'tick (HazardSystem.updatePlayerInventory and then updateLivingInventory, because a Player is also a LivingEntity) and on both logical sides; the hazards '
         'are now applied on the server only, once per stack per tick (players through updatePlayerInventory, other living entities through '
         'updateLivingInventory), as the original ModEventHandler does (:1023, :572-576). Geiger readings with a radioactive item in hand now equal the '
         'readings with it elsewhere in the inventory. EntityEffectHandler.tick and the dropped-item path are unchanged. HazardGameTests gains one test. No '
         'resource, language key or save data changes.')
HAZARD_ONCE_RADIATION = ('Goal21D review fix: the hazards of a radioactive item in a player\'s selected hotbar slot, offhand or armor slots were applied twice per '
                         'tick (and on the client as well) in the Goal21D package, so radiation, heat and blinding readings with such an item in hand or worn '
                         'were twice the original values; they are now applied once on the server, as the original, and equal the readings with the same item '
                         'elsewhere in the inventory. ')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert rel not in NOTE_RECORDS, 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the review-g21d-hazard release directory: '+rel


def protected_paths(base, prior_receipt):
    """(protected, note_hashes): what the Goal21D final runner protected (built there from the Goal21A..Goal21D starts), plus every path the goal21d
    receipt hashes, the paths the older receipts hash (older_receipt_protected_paths) and every release file of the frozen start. The four insert-only
    records are returned separately with the hash their newest receipt records. One path never carries two different hashes."""
    out = goal21d_protected_paths(read(GOAL21D_BASELINE))
    # The goal21d packager protected the 21C acceptance master list at its goal21c receipt version; the goal21d receipt explains its drift.
    goal21c_receipt_version = out.pop(ACCEPTANCE_21C)
    receipts = base['older_receipt_protected_paths']
    assert receipts['goal21c'][ACCEPTANCE_21C] == goal21c_receipt_version, 'The goal21c receipt hash of '+ACCEPTANCE_21C+' differs between the starts'
    for source in (*receipts.values(), base['previous_receipt_protected_paths'], base['old_release_files']):
        for p, h in source.items():
            if p != ACCEPTANCE_21C: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    explained = prior_receipt['goal21c_acceptance_drift_explained']
    assert explained['path'] == ACCEPTANCE_21C and explained['before_sha256'] == goal21c_receipt_version, 'goal21d receipt does not explain the goal21c receipt version'
    notes = {p: out.pop(p) for p in NOTE_RECORDS_21D}
    notes[ACCEPTANCE_21C] = explained['after_sha256']
    return out, notes


def group(p):
    if p in PRODUCTION: return 'production'
    if p in GENERATED: return 'generated'
    if p in TOOLS or p in OPTIONAL_TOOLS: return 'tools'
    if p == FIX_RECORD or FIX_RECORD_PATTERN.fullmatch(p): return 'fix-record'
    if p in NOTE_RECORDS: return 'explained-records'
    if p in SHARED_RECORDS: return 'records'
    return None


def annotations(path):
    return len(GAMETEST_ANNOTATION.findall(Path(path).read_text(encoding='utf-8')))


def note_insertions(p, start, now):
    """([(index, line)], blocks): the lines this batch inserted into a protected record. Insert-only against the frozen start copy, line endings kept,
    every contiguous inserted block carrying the batch marker and the date."""
    assert (eol_counts(start)[0] == 0) <= (eol_counts(now)[0] == 0) and (eol_counts(start)[1] == 0) <= (eol_counts(now)[1] == 0), p+' line endings changed'
    new_lines = lines_of(now)
    inserted = insertions(lines_of(start), new_lines)
    assert inserted is not None, p+' is not insert-only against the frozen start copy (a start line was changed, moved or removed)'
    blocks = []
    for j, line in inserted:
        if blocks and blocks[-1][-1][0] == j-1: blocks[-1].append((j, line))
        else: blocks.append([(j, line)])
    for block in blocks:
        text = '\n'.join(line for _, line in block)
        assert MARKER in text and DATE in text, f'{p}: the inserted block at line {block[0][0]+1} lacks the marker {MARKER} or the date {DATE}'
    return inserted, blocks


def stale_diff(diff_text):
    """Why production-vs-start.diff is stale, or None: it must carry every line added or removed in the two production files against their frozen start
    copies (a removed or added line counts once per occurrence)."""
    diff = diff_text.replace('\r\n', '\n').split('\n')
    plus = Counter(l[1:] for l in diff if l.startswith('+') and not l.startswith('+++'))
    minus = Counter(l[1:] for l in diff if l.startswith('-') and not l.startswith('---'))
    need_plus, need_minus = Counter(), Counter()
    for p in PRODUCTION:
        old, new = lines_of((START_FILES/p).read_bytes()), lines_of((ROOT/p).read_bytes())
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
            if tag in ('replace', 'delete'): need_minus.update(old[i1:i2])
            if tag in ('replace', 'insert'): need_plus.update(new[j1:j2])
    short_plus = sorted(l for l, n in need_plus.items() if plus[l] < n)
    short_minus = sorted(l for l, n in need_minus.items() if minus[l] < n)
    if short_plus or short_minus:
        return f'production-vs-start.diff is stale: {len(short_plus)} added and {len(short_minus)} removed production lines missing (first: {(short_plus or short_minus)[:1]})'
    return None


def find_key(data, key):
    """Every value stored under key anywhere in a JSON structure."""
    found = []
    if isinstance(data, dict):
        for k, v in data.items():
            if k == key: found.append(v)
            found += find_key(v, key)
    elif isinstance(data, list):
        for v in data: found += find_key(v, key)
    return found


def verifier_problems(report):
    """Why verify-report.json (a copy of the passing tools/migration/verify_review_goal21d_hazard_once.py report.json) is not a passing run, [] otherwise."""
    problems = []
    if 'ok' in report and report['ok'] is not True: problems.append('ok is '+repr(report['ok']))
    for key in ('result', 'status'):
        if key in report and str(report[key]).lower() not in ('pass', 'passed', 'ok'): problems.append(f'{key} is {report[key]!r}')
    if not any(k in report for k in ('ok', 'result', 'status')) and 'checks' not in report and 'static_checks' not in report:
        problems.append('report carries no ok/result/status and no checks')
    checks = report.get('checks', {})
    entries = list(checks.items()) if isinstance(checks, dict) else [(c.get('name', i), c) for i, c in enumerate(checks) if isinstance(c, dict)]
    failed = [n for n, c in entries if isinstance(c, dict) and (str(c.get('status', 'pass')).lower() in ('fail', 'failed') or c.get('ok') is False or c.get('passed') is False)]
    if failed: problems.append('failed checks: '+str(failed[:5]))
    mutations = report.get('mutations')
    entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
    if not entries: problems.append('report lists no mutations')
    undetected = [e for e in entries if isinstance(e, dict) and e.get('detected') is False]
    if undetected: problems.append(f'{len(undetected)} undetected mutations')
    if 'mutations_detected' in report:
        # The verifier writes mutations_detected and mutation_count as separate integers; an 'N/M' string is accepted as well.
        raw = str(report['mutations_detected'])
        detected, total = (int(x) for x in raw.split('/')) if '/' in raw else (int(raw), int(report.get('mutation_count', 0)))
        if detected != total or not total: problems.append('mutations_detected is '+raw+' of '+str(total))
    if report.get('mutations_undetected'): problems.append('undetected mutations: '+str(report['mutations_undetected'][:5]))
    hashes = find_key(report, 'production_sha256')
    if not hashes:
        problems.append('report carries no production_sha256')
    for table in hashes:
        if not isinstance(table, dict): problems.append('production_sha256 is not a mapping'); continue
        for p in PRODUCTION:
            value = next((v for k, v in table.items() if k.replace('\\', '/').endswith(p) or p.endswith(k.replace('\\', '/'))), None)
            if value is None: problems.append('production_sha256 lacks '+p)
            elif value not in (sha(ROOT/p), normalized_sha(ROOT/p)): problems.append('production_sha256 differs from the live file: '+p)
    return problems


def main(check, gametest_log):
    pending = []
    base = read(BASELINE)
    prior_receipt = read(PREVIOUS_RECEIPT)

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (the fix commits nothing), the recorded start content.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD, 'Unexpected frozen start'
    assert base['build_libs_jar_sha256'] == START_JAR_SHA, 'Baseline names another start build'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == START_HEAD, 'NEO HEAD moved during the fix: '+head
    assert set(base['start_content']) >= {'goal21a', 'control_nbt_null_fix', 'goal21b', 'goal21c', 'goal21d', 'fix_paths'}, 'Baseline start content lacks a group'
    assert set(o for owners in base['dirty_attribution'].values() for o in owners) <= {'goal21a', 'control-nbt-null-fix', 'goal21b', 'goal21c', 'goal21d'}, \
        'Baseline attributes start content to an unknown owner'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c'} and not base['previous_receipt_evidence_drift'], \
        'Baseline records drifted goal21d receipt evidence'
    # The one older-receipt drift is the 21C acceptance master list, which the goal21d receipt explains.
    assert {k: v for k, v in base['older_receipt_evidence_drift'].items() if v} == {'goal21c': [ACCEPTANCE_21C]}, \
        'Baseline records unexplained older receipt drift: '+str(base['older_receipt_evidence_drift'])
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['dirty_paths'] == len(base['dirty_paths']) and startup['frozen_file_hashes'] == len(base['files']) \
        and startup['old_release_files'] == len(base['old_release_files']) and startup['previous_jar_sha256'] == PREVIOUS_SHA, \
        'startup-verification.json differs from baseline.json'

    # 2. Previous deliveries: the goal21d package, every old release file and the protected evidence (Goal21D runner set + goal21d receipt + the
    # older receipts). The receipt and checksum hashes come from the baseline's release files, not from literals.
    assert base['previous_release'] == dict(path=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES), 'Baseline names another previous release'
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'goal21d JAR changed'
    previous_receipt_sha = base['old_release_files'][PREVIOUS_RECEIPT.relative_to(ROOT).as_posix()]
    previous_sums_sha = base['old_release_files'][PREVIOUS_SUMS.relative_to(ROOT).as_posix()]
    assert sha(PREVIOUS_RECEIPT) == previous_receipt_sha, 'goal21d release.json changed'
    assert sha(PREVIOUS_SUMS) == previous_sums_sha, 'goal21d SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'goal21d SHA256SUMS.txt content changed'
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    for p, h in base['old_release_files'].items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release file changed: '+p
    old_releases = dict(base['old_releases'])
    assert old_releases.get(PREVIOUS.relative_to(ROOT).as_posix()) == PREVIOUS_SHA
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    protected, note_hashes = protected_paths(base, prior_receipt)
    # Each insert-only record's frozen start copy must be the version its newest receipt records.
    for p, h in note_hashes.items():
        assert base['files'][p] == sha(START_FILES/p) == h, 'Frozen start copy of '+p+' is not the hash its newest receipt records'
    for p in NOTE_RECORDS_21D: assert prior_receipt['report_sha256'][p] == note_hashes[p], 'goal21d receipt hash of '+p+' differs'
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)

    # 3. Changes since the start: each path in the owner table, attributed to review-g21d-hazard; the start attribution is recorded alongside.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    assert not unassigned, 'Unassigned path changed since the start: '+str(unassigned)
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the start: '+str(deleted)
    for p in PRODUCTION: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in [FIX_RECORD] + TOOLS:
        assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    missing_required = [p for p in REQUIRED_CHANGES if p not in changes]
    if missing_required:
        if not check: raise AssertionError('Required changes missing: '+str(missing_required))
        pending += ['change not present yet (still equals the start or absent): '+p for p in missing_required]
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    assert set(since) <= set(PRODUCTION), 'src/main change outside the production list: '+str(sorted(set(since) - set(PRODUCTION)))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, start_attribution=base['dirty_attribution'].get(p, []),
                        before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    start_content_touched = sorted(p for p in changes if base['dirty_attribution'].get(p))
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    assert baselines_now == {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}, 'A snapshot was added or changed'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'], 'review-6a11998d5852 snapshot changed'

    # The two production files keep their start line endings; the start copies are the frozen baseline files.
    for p in PRODUCTION:
        start_eol, eol = eol_counts((START_FILES/p).read_bytes()), eol_counts((ROOT/p).read_bytes())
        assert (start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), \
            f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}'
        if (ROOT/p).read_bytes() == (START_FILES/p).read_bytes():
            if not check: raise AssertionError(p+' has no change')
            pending.append(p+' still equals the start')

    # 4. Language and the generated tree: the fix adds no key, so en_us.json, zh_cn.json, the mapping and NtmLanguageProvider equal their start bytes;
    # since the start only the stamp of the generated tree may change, and no generated resource is added or retired.
    for p in UNCHANGED_LANGUAGE:
        assert base['files'].get(p) == sha(ROOT/p), 'The fix adds no language key, but changed '+p
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    assert set(generated_since) <= set(GENERATED), 'Generated change outside the fix list: '+str(generated_since)
    # Equal start bytes (asserted above) mean an empty delta; zh_start is therefore the live file.
    zh_start = read(ROOT/ZH_INPUT)
    empty = dict(added=[], removed=[], changed=[])
    en_delta = zh_delta = empty
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    stamp_current = not stale and not mismatch and not unrecorded
    if not stamp_current:
        if not check: raise AssertionError(f'Stamp not current: stale {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
        pending.append(f'{STAMP} not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
    start_stamp = read(START_FILES/STAMP)
    start_generated = set(start_stamp['generated'])
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal21d generated tree'
    generated_added = sorted(set(stamp['generated']) - start_generated)
    generated_retired = sorted(start_generated - set(stamp['generated']))
    assert not generated_added and not generated_retired, f'Generated resources added {generated_added} or retired {generated_retired} since the start'
    # Every generated resource still has its start hash (only the stamp file itself may have changed).
    generated_changed = sorted(p for p, h in start_stamp['generated'].items() if stamp['generated'].get(p) != h)
    assert not generated_changed, 'Generated resource hashes changed since the start: '+str(generated_changed[:5])

    # 5. Evidence: GameTest log, audits, Gradle logs, patch and diff, the final suite run, the verifier report and compare.
    evidence = {}
    gametest_line = gametest_count = None
    hazard_now, hazard_start = annotations(ROOT/GAMETEST_JAVA), annotations(START_FILES/GAMETEST_JAVA)
    total_now = sum(annotations(p) for p in sorted(GAMETEST_DIR.glob('*.java')))
    assert total_now - hazard_now + hazard_start == prior_receipt['gametest']['tests'], \
        'The start GameTest sources do not hold the goal21d count of '+str(prior_receipt['gametest']['tests'])
    hazard_added = hazard_now - hazard_start
    gametest_expected = total_now
    if hazard_added != 1:
        if not check: raise AssertionError(f'HazardGameTests gained {hazard_added} @GameTest methods, not the one the scope states')
        pending.append(f'{GAMETEST_JAVA} gained {hazard_added} @GameTest methods so far (expected 1)')
    log = (ROOT/gametest_log).resolve() if gametest_log else None
    if log is None or not log.is_file():
        if not check: raise AssertionError('GameTest log missing: pass --gametest-log PATH')
        pending.append('GameTest log (--gametest-log): '+(str(gametest_log) if gametest_log else 'not given')+' does not exist yet')
    else:
        assert log.is_relative_to(ROOT), 'GameTest log outside the NEO repository: '+str(log)
        text = log.read_text(encoding='utf-8-sig', errors='replace')
        found = GAMETEST.findall(text)
        assert found and 'BUILD SUCCESSFUL' in text and 'invalid dist' not in text and 'NoClassDefFoundError' not in text, 'GameTest run did not pass cleanly'
        gametest_count = int(found[-1])
        assert gametest_count == gametest_expected, \
            f'GameTest server ran {gametest_count} tests, the sources hold {gametest_expected} @GameTest methods ({prior_receipt["gametest"]["tests"]} goal21d tests + {hazard_added})'
        gametest_line = f'All {gametest_count} required tests passed'
        evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name in AUDITS:
        if not (OUT/name).is_file():
            if not check: raise AssertionError('Missing audit: '+name)
            pending.append('evidence: build/migration/review-fixes-g21d-hazard/'+name)
            continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        assert audit['summary'] == prior_receipt['audits'][name], f'{name} summary {audit["summary"]} differs from the goal21d receipt {prior_receipt["audits"][name]}'
        audit_summaries[name] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not (OUT/name).is_file():
            if not check: raise AssertionError('Missing log: '+name)
            pending.append('evidence: build/migration/review-fixes-g21d-hazard/'+name)
            continue
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run'
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not (OUT/name).is_file() or not (OUT/name).stat().st_size:
            if not check: raise AssertionError('Missing or empty evidence file: '+name)
            pending.append('evidence: build/migration/review-fixes-g21d-hazard/'+name)
            continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    evidence[BASELINE.relative_to(ROOT).as_posix()] = sha(BASELINE)
    # chain.sh output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits.txt').read_text(encoding='utf-8').split())
        assert all(v == '0' for v in exits.values()), 'A chain command failed: '+str(exits)
    for name in CHAIN_FILES:
        if (OUT/name).is_file(): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-fix.sha256').is_file():
        assert (OUT/'jar-fix.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it'
    # production-vs-start.diff must carry every production line change.
    diff_path = OUT/'production-vs-start.diff'
    if diff_path.is_file() and diff_path.stat().st_size and all((ROOT/p).read_bytes() != (START_FILES/p).read_bytes() for p in PRODUCTION):
        message = stale_diff(diff_path.read_text(encoding='utf-8-sig'))
        if message:
            if not check: raise AssertionError(message)
            pending.append(message)
    final = None
    # The 74 suites of the Goal21D final run plus the new hazard-once verifier.
    reference_suites = set(read(REFERENCE_21D)['suites'])
    final_expected = len(reference_suites) + 1
    if (OUT/FINAL_SUMMARY).is_file():
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        assert set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal21d final set + the hazard-once verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE})))
        entry = final['suites'][NEW_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, NEW_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    elif check:
        pending.append('evidence: build/migration/review-fixes-g21d-hazard/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)')
    else:
        raise AssertionError('Missing final suite summary')
    verifier = None
    if (OUT/VERIFY_REPORT).is_file():
        report = read(OUT/VERIFY_REPORT)
        problems = verifier_problems(report)
        if problems:
            if not check: raise AssertionError(VERIFY_REPORT+' is not a passing verifier run: '+str(problems))
            pending.append(VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=VERIFIER,
                        tool_sha256=sha(ROOT/VERIFIER) if (ROOT/VERIFIER).is_file() else None,
                        mutations_detected=report.get('mutations_detected', report.get('mutation_count')))
        evidence[verifier['path']] = verifier['sha256']
    elif check:
        pending.append('evidence: build/migration/review-fixes-g21d-hazard/'+VERIFY_REPORT+' (copy of the passing verifier run report.json)')
    else:
        raise AssertionError('Missing '+VERIFY_REPORT)
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree): the original unchanged, the target exactly the goal21d receipt's compare
    # target set plus this batch's paths inside the compare inventory (compare never lists the stamp); unmapped changes as in goal21d. No new snapshot.
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'goal21d receipt compare target set is incomplete'
    prior_cmp = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_compare['sha256'], 'goal21d compare.json changed'
    assert compare_paths(prior_cmp['changes']['target']['added']) | compare_paths(prior_cmp['changes']['target']['modified']) == previous_target, \
        'goal21d compare.json target set differs from its receipt'
    expected_target = sorted(previous_target | {p for p in changes if in_compare_inventory(p)})
    if (OUT/COMPARE).is_file():
        cmp = read(OUT/COMPARE)
        assert cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the 6a11998d snapshot'
        counts = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        assert all(v == 0 for v in counts['source'].values()), 'compare.json source is not 0/0/0: '+str(counts['source'])
        target = cmp['changes']['target']
        assert not target['removed'], 'compare.json target removed: '+str(target['removed'])
        assert not cmp['unmapped_changes']['source'] and set(cmp['unmapped_changes']['target']) <= set(prior_cmp['unmapped_changes']['target']), \
            'compare.json reports unmapped changes: '+str(cmp['unmapped_changes'])
        assert not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], 'compare.json reports removed features or missing files'
        listed = sorted(p for p in compare_paths(target['added']) | compare_paths(target['modified']) if not p.endswith('/.migration-stamp.json'))
        assert listed == expected_target, 'compare.json target set differs: extra %s, missing %s' % (
            sorted(set(listed) - set(expected_target)), sorted(set(expected_target) - set(listed)))
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts,
                       target_owners={p: sorted(set(prior_compare['target_owners'].get(p, [])) | ({OWNER} if p in changes else set())) for p in listed})
        evidence[compare['path']] = compare['sha256']
    elif check:
        pending.append('evidence: build/migration/review-fixes-g21d-hazard/'+COMPARE)
    else:
        raise AssertionError('Missing '+COMPARE)

    # 6. JAR: build/libs is what gets packaged; delta against the goal21d package, every entry owned by review-g21d-hazard. Exactly the classes of the two
    # changed sources: no added or removed entry, no resource or language entry and no directory change (the stamp is not packaged).
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    if sha(JAR) in (PREVIOUS_SHA, START_JAR_SHA):
        if not check: raise AssertionError('build/libs JAR is still the goal21d package (run build)')
        pending.append('build/libs/hbmsntm-198A.jar is still the goal21d package (run build)')
    else:
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            for p in stamp['generated']: assert jar.read(p) == (ROOT/'src/generated/resources'/p).read_bytes(), p
            assert jar.read(ZH_ENTRY) == (ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
            for path in classes:
                name = path.relative_to(classes_root).as_posix()
                assert jar.read(name) == path.read_bytes(), name
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            assert en_jar == zh_jar == empty and jar.read(EN_ENTRY) == prior.read(EN_ENTRY) and jar.read(ZH_ENTRY) == prior.read(ZH_ENTRY), \
                'JAR en_us.json or zh_cn.json differs from the goal21d package: en '+str(en_jar)+', zh '+str(zh_jar)
            assert lang_delta(json.loads(prior.read(ZH_ENTRY)), zh_start) == empty, 'Start zh_cn.json differs from the goal21d package'
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = [OWNER] if n.endswith('.class') and owner_class(n) in PRODUCTION else []
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        assert not unowned, 'Unowned JAR change: '+str(unowned)
        assert not dir_delta['added'] and not dir_delta['removed'], 'JAR directory delta: '+str(dir_delta)
        # Modified classes only: an inner class of a changed source (HazardGameTests$Mat, $Expectation) changes through shifted line numbers.
        assert not jar_delta['added'] and not jar_delta['removed'], 'The fix adds or removes JAR entries: '+str(jar_delta)
        class_owners = sorted({owner_class(n) for n in jar_delta['modified']})
        assert class_owners == sorted(PRODUCTION), 'Not every changed Java source changed a class: '+str(sorted(set(PRODUCTION) - set(class_owners)))
        assert classes and len(classes) == prior_receipt['compiled_classes_verified'], \
            f'Compiled class count {len(classes)} is not the goal21d count {prior_receipt["compiled_classes_verified"]}'
        language = dict(en=en_jar, zh=zh_jar)

    # 7. Records: the release name, the fix record and the insert-only notes (the four records the earlier receipts hash).
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    if unnamed:
        if not check: raise AssertionError('Records do not name '+RELEASE_NAME+': '+str(unnamed))
        pending += ['records (do not name '+RELEASE_NAME+'): '+p for p in unnamed]
    reports = [FIX_RECORD] + sorted(p for p in changes if FIX_RECORD_PATTERN.fullmatch(p) and p != FIX_RECORD)
    missing_reports = [p for p in reports if not (ROOT/p).is_file()]
    if missing_reports:
        if not check: raise AssertionError('Missing records: '+str(missing_reports))
        pending += ['records: '+p+' does not exist yet' for p in missing_reports]
    for p in SHARED_RECORDS:
        assert (ROOT/p).is_file(), 'Missing shared record: '+p
    read(ROOT/'migration/features.json')
    record_drift = {}
    for p in NOTE_RECORDS:
        start, now = (START_FILES/p).read_bytes(), (ROOT/p).read_bytes()
        if now == start:
            if not check: raise AssertionError(p+' has no dated note')
            pending.append(p+' still equals its start copy (no dated '+MARKER+' note inserted yet)')
            continue
        inserted, blocks = note_insertions(p, start, now)
        hashed_by = 'goal21c receipt (explained by the goal21d receipt)' if p == ACCEPTANCE_21C else 'goal21d receipt'
        record_drift[p] = dict(hashed_by=hashed_by, before_sha256=note_hashes[p], after_sha256=sha(ROOT/p), inserted_blocks=len(blocks),
                               inserted_lines=[line for _, line in inserted], insert_only=True, marker=MARKER, date=DATE,
                               explanation='Review fix O1 inserted a dated note (marker '+MARKER+', '+DATE+'); only inserted lines differ from the version the '
                                           'earlier receipt records. The earlier receipt is not rewritten.')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=generated_added,
                   start_content_touched=start_content_touched, en_delta=en_delta, zh_delta=zh_delta,
                   record_drift_explained={p: dict(inserted_blocks=d['inserted_blocks'], inserted_lines=len(d['inserted_lines']), after_sha256=d['after_sha256']) for p, d in record_drift.items()},
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta,
                   class_owners=class_owners, gametest=gametest_line, gametest_expected=gametest_expected, hazard_tests_added=hazard_added,
                   final_suites_expected=final_expected, compare=compare['counts'] if compare else None, compare_target_expected=len(expected_target),
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
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different review-g21d-hazard JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest == sha(JAR) and digest not in (PREVIOUS_SHA, START_JAR_SHA), 'Packaged JAR is not build/libs or is an older JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in reports}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified', scope=SCOPE,
                   radiation_warning=HAZARD_ONCE_RADIATION+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, planning_commit=START_HEAD, commits={}, target_head_at_packaging=head,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], dirty_attribution=base['dirty_attribution'], start_build_sha256=START_JAR_SHA,
                                      touched_by_review_g21d_hazard=start_content_touched,
                                      note='The start tree is HEAD dbfa6746 + the uncommitted Goal21A delivery + the control-NBT null fix + the '
                                           'uncommitted Goal21B, Goal21C and Goal21D deliveries, all packaged by goal21d; start-content files changed '
                                           'here carry only review-fix hunks and are attributed to review-g21d-hazard.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added,
                   compiled_classes_verified=prior_receipt['compiled_classes_verified'],
                   production=PRODUCTION, sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   resources={}, resource_ownership=None,
                   language=dict(keys={}, unchanged={p: sha(ROOT/p) for p in UNCHANGED_LANGUAGE}, jar_delta=language,
                                 note='The fix adds no resource and no language key: en_us.json, zh_cn.json, the zh_cn mapping and NtmLanguageProvider '
                                      'equal their start bytes.'),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   record_drift_explained=record_drift,
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; the new test calls '
                                      'CommonEvents.onLivingTick on a server Pig, so the single-application dispatch of a player (and the client-side skip) '
                                      'is covered only by the isolated stub-world model in the verifier, not by a player in a real world.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + [LOCALIZATION_RECORD],
                   evidence_sha256={**hashes, **evidence, **{p: d['after_sha256'] for p, d in record_drift.items()}, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the resource, packaged-resource and localization audits, '
                            'the static, behavioural and JAR verifier with mutations (the player dispatch is modelled in an isolated stub-world harness, '
                            'not run with a player), the final old-suite rerun, compare against the review-6a11998d5852 snapshot and independent JAR bytes '
                            '(the classes of the two changed sources only; no resource or language change). No client, real save, multiplayer or in-game '
                            'player test was run: the corrected held and worn hazard readings, the Geiger counter and protection gear are unverified in game.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal21d package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
