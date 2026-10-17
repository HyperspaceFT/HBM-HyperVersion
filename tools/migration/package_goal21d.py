"""Package Goal21D (material radiation hazard registration: the OreDictManager DictFrame rows and the fuel/yellowcake item rows registered in
HazardRegistry on the existing NEO items and blocks, HazardGameTests) cumulatively on the goal21c package, without replacing any previous
delivery.

python -B -X utf8 tools/migration/package_goal21d.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending; the real mode writes only
build/migration/releases/goal21d/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to
build/migration/goal21d/gametest-final.log (the GameTest dedicated-server log of the settled tree).

The frozen Goal21D start is build/migration/goal21d/baseline.json: NEO HEAD dbfa6746 plus the uncommitted Goal21A delivery, the control-NBT
null fix, the Goal21B delivery and the Goal21C delivery (all four packaged by the goal21c package; build/libs at the start is that package).
Every change since the start is computed from the baseline file hashes (not from git diff, which would include the start content) and must be
in the owner table below; start content outside the owner table must still equal its start hash. The JAR delta against the goal21c package is
attributed per entry to goal21d; any entry without that owner fails. Goal21D adds no resource and no language key: en_us.json, zh_cn.json, the
zh_cn mapping and NtmLanguageProvider must equal their start bytes. Counts that records quote (suites, generated resources, GameTests,
releases) are computed here, never hard-coded.

The one protected record Goal21D edits is migration/GOAL21C-ACCEPTANCE.md (hashed by the goal21c receipt): a pointer is inserted into its
section 8, so it is checked as insert-only against its frozen start copy (whose hash must equal the goal21c receipt hash) and listed as
explained drift with before and after hashes. Every other protected path must be unchanged."""
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
from package_review_g20_display_fixes import protected_drift as display_protected_drift, split_drift, ACCEPTANCE_CHECKLISTS
from migration import BUILD_FILES

OUT = ROOT/'build/migration/goal21d'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
START_21A = ROOT/'build/migration/goal21a/baseline.json'
START_21B = ROOT/'build/migration/goal21b/baseline.json'
START_21C = ROOT/'build/migration/goal21c/baseline.json'
REFERENCE_21C = ROOT/'build/migration/goal21c/final/summary.json'
PREVIOUS = ROOT/'build/migration/releases/goal21c/hbmsntm-198A-goal21c.jar'
PREVIOUS_SHA = '1444e973d74ebd5f7f3ab919f70c2a952429b5ceb35f1fb8183b3dadbbb8522e'
PREVIOUS_BYTES = 18385391
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal21c/release.json'
PREVIOUS_RECEIPT_SHA = 'fe99017f7aa09cbf540c475acef99ae95a1b0359b2628004feb6dfeb87b76ffa'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal21c/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = 'd3b161ba043ee69d3db37f1c05cdf96187b3fdfc2578c2c6026cd06b54ebed45'
DISPLAY_RECEIPT = ROOT/'build/migration/releases/review-g20-display-fixes-20261016/release.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal21d'
RELEASE_NAME = 'hbmsntm-198A-goal21d.jar'
SOURCE_HEAD = '6a11998d5852ff3da326f0130357e10431ae3839'
START_HEAD = 'dbfa6746f9728bb551bfdfdaaedca3edaa42ba13'
# build/libs at the start is the goal21c package itself; packaging it again would package no Goal21D change.
START_JAR_SHA = PREVIOUS_SHA
SNAPSHOT = 'migration/baselines/review-6a11998d5852.json'
STAMP = 'src/generated/resources/.migration-stamp.json'
EN = 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
# commits.json gained commit_two (4d02ccdf) after the display-fix receipt hashed it (goal21a baseline explained_previous_drift); the Goal21A,
# Goal21B and Goal21C final runners protected it at this hash.
COMMITS = 'build/migration/review-fixes-g20-display/commits.json'
COMMITS_SHA = '08b26a3169564433ec3caee828f0523033b626b5f536689554dec45b2e0b9fa1'
J = 'src/main/java/com/hbm/'
HAZARD_REGISTRY = J+'hazard/HazardRegistry.java'
GAMETEST_JAVA = J+'gametest/HazardGameTests.java'
JAVA = [HAZARD_REGISTRY]
NEW_JAVA = [GAMETEST_JAVA]
PRODUCTION = JAVA + NEW_JAVA
PROVIDER = J+'datagen/NtmLanguageProvider.java'
LOCALIZATION_RECORD = 'migration/localization/zh_cn-map.json'
# Goal21D adds no resource and no language key: these must equal their start bytes.
UNCHANGED_LANGUAGE = [EN, ZH_INPUT, LOCALIZATION_RECORD, PROVIDER]
NO_OWNERSHIP_RECORD = 'migration/goal21d-resource-ownership.json'
GENERATED = [STAMP]
TOOLS = ['tools/migration/verify_goal21d_hazards.py', 'tools/migration/package_goal21d.py']
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal21d-* record is hashed as well.
REPORTS = ['migration/GOAL21D.md', 'migration/GOAL21D-ACCEPTANCE.md', 'migration/goal21d-static-review.md', 'migration/goal21d-hazard-review.json',
           'migration/goal21d-localization-review.json']
BATCH_RECORD = re.compile(r'migration/goal21d-[^/]+\.(json|md)')
SHARED_RECORDS = ['migration/GOAL21.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md']
# Hashed by the goal21c receipt; Goal21D inserts a pointer into its section 8 (insert-only against the frozen start copy).
ACCEPTANCE_21C = 'migration/GOAL21C-ACCEPTANCE.md'
ACCEPTANCE_SECTION = re.compile(r'##\s*8\.')
ACCEPTANCE_NEXT_SECTION = re.compile(r'##\s*9\.')
POINTER = re.compile(r'21D')
# Must have changed (or been added) by the time of the real run; the rest of the owner table is optional.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md', 'migration/features.json',
                                                              'migration/GOAL21.md', ACCEPTANCE_21C]
NAMES_RELEASE = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
OWNER = 'goal21d'
ZH_ENTRY = 'assets/hbmsntm/lang/zh_cn.json'
EN_ENTRY = 'assets/hbmsntm/lang/en_us.json'
AUDITS = ('localization-audit.json', 'resources-audit.json', 'packaged-resources.json')
# Indexed by the receipt as evidence files of this batch; the two Gradle logs must end in BUILD SUCCESSFUL.
LOGS = ('rundata-final.log', 'build.log')
FILES = ('start-worktree.patch', 'production-vs-start.diff')
VERIFY_REPORT = 'verify/hazard-report.json'
FINAL_SUMMARY = 'final/summary.json'
COMPARE = 'compare.json'
GAMETEST_LOG = 'build/migration/goal21d/gametest-final.log'
HAZARD_SUITE = 'verify_goal21d_hazards.py --gametest-log build/migration/goal21d/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
GAMETEST = re.compile(r'All (\d+) required tests passed')
GAMETEST_ANNOTATION = re.compile(r'^\s*@GameTest\(', re.M)
SCOPE = ('Goal21D: the material radiation hazards of the original OreDictManager.registerOres (DictFrame rows OreDictManager.java:347-374, '
         ':454-455 and :490-495: rad, hot, blinding and hydro entries with the original per-shape multipliers) and the fuel and yellowcake item '
         'rows (HazardRegistry.java:289-329 and :473-474), registered in the NEO HazardRegistry on the existing NEO items and blocks (nuggets, '
         'billets, ingots, blocks, powders and the named items); ores are not registered (decision 13: NEO has no ore dictionary); '
         'HazardGameTests. No resource, no language key and no save data changes.')
GOAL21D_RADIATION = ('Goal21D: radioactive materials now carry the original radiation, heat, blinding and hydroactive hazards: uranium, thorium, '
                     'plutonium, neptunium, polonium, radium, actinium, americium, cobalt-60, gold-198, lead-209, schrabidium, solinium, '
                     'schrabidate, schraranium, ghiorsium-336, watz mud, strontium-90, iodine-131, xenon-135, caesium-137, astatine-209, fuel '
                     'nuggets/billets/ingots/blocks and yellowcake, held or in the inventory of a player or living entity. Existing worlds are '
                     'affected immediately after the update (hazards are looked up by item ID at runtime; no save data changes). Keep such '
                     'materials in shielded containers and wear protection; this is the original behavior, not a NEO addition. ')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert rel != ACCEPTANCE_21C, 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal21d release directory: '+rel


def protected_paths(base):
    """What the Goal21C final runner protected (built there from the Goal21A, Goal21B and Goal21C starts), plus every path the goal21c receipt
    hashes, the paths the goal21a and goal21b receipts hash (older_receipt_protected_paths) and every release file of the frozen Goal21D
    start. One path never carries two different hashes."""
    start = read(START_21A)
    start_21b = read(START_21B)
    start_21c = read(START_21C)
    display = read(DISPLAY_RECEIPT)
    assert COMMITS in start['explained_previous_drift']
    out = {p: h for p, h in start['goal20c_receipt_protected_paths'].items() if p not in start['goal20c_drift_explained']}
    out.update({p: display['acceptance_records'][p] for p in start['goal20c_drift_explained']})
    out.update(start['previous_receipt_protected_paths'])
    out[COMMITS] = COMMITS_SHA
    out.update({p: display['acceptance_records'][p] for p in ACCEPTANCE_CHECKLISTS})
    out.update(start['old_release_files'])
    older = {p: h for receipt in base['older_receipt_protected_paths'].values() for p, h in receipt.items()}
    for p, h in {**start_21b['previous_receipt_protected_paths'], **start_21b['old_release_files'],
                 **start_21c['goal21a_receipt_protected_paths'], **start_21c['previous_receipt_protected_paths'], **start_21c['old_release_files'],
                 **older, **base['previous_receipt_protected_paths'], **base['old_release_files']}.items():
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
    if p in GENERATED: return 'generated'
    if p in TOOLS: return 'tools'
    if p in REPORTS or p in SHARED_RECORDS or p == ACCEPTANCE_21C or BATCH_RECORD.fullmatch(p): return 'records'
    return None


def in_compare_inventory(p):
    """The target inventory of tools/migration/migration.py: src/**, data/** and the build files, without .cache and the stamp."""
    return (p.startswith(('src/', 'data/')) or p in BUILD_FILES) and '.cache' not in p.split('/') and not p.endswith('/.migration-stamp.json')


def lang_delta(old, new):
    return dict(added=sorted(set(new)-set(old)), removed=sorted(set(old)-set(new)), changed=sorted(k for k in set(old) & set(new) if old[k] != new[k]))


def compare_paths(entries):
    return {e['path'] if isinstance(e, dict) else e for e in entries}


def lines_of(data):
    return data.decode('utf-8').replace('\r\n', '\n').split('\n')


def eol_counts(data):
    """(CRLF, lone LF): the line ending style of a file."""
    crlf = data.count(b'\r\n')
    return crlf, data.count(b'\n') - crlf


def insertions(old, new):
    """[(index in new, line)] of the lines only the new text has when it is the old text plus inserted lines; None when a start line was
    changed, moved or removed. The longest-match alignment is used when it needs no replacement, otherwise a greedy subsequence match."""
    ops = SequenceMatcher(None, old, new, autojunk=False).get_opcodes()
    if all(t in ('equal', 'insert') for t, *_ in ops):
        return [(j, new[j]) for t, _, _, j1, j2 in ops if t == 'insert' for j in range(j1, j2)]
    matched, i = set(), 0
    for j, line in enumerate(new):
        if i < len(old) and line == old[i]:
            i += 1
            matched.add(j)
    return None if i < len(old) else [(j, line) for j, line in enumerate(new) if j not in matched]


def acceptance_insertions(start, now):
    """[(index, line)] Goal21D inserted into the 21C acceptance master list: insert-only against the goal21c receipt version, line endings
    kept, every inserted line inside section 8 and (blank lines aside) mentioning 21D."""
    assert (eol_counts(start)[0] == 0) <= (eol_counts(now)[0] == 0) and (eol_counts(start)[1] == 0) <= (eol_counts(now)[1] == 0),         ACCEPTANCE_21C+' line endings changed'
    new_lines = lines_of(now)
    inserted = insertions(lines_of(start), new_lines)
    assert inserted, ACCEPTANCE_21C+' is not insert-only against the goal21c receipt version'
    h8 = [i for i, l in enumerate(new_lines) if ACCEPTANCE_SECTION.match(l)]
    h9 = [i for i, l in enumerate(new_lines) if ACCEPTANCE_NEXT_SECTION.match(l)]
    assert len(h8) == len(h9) == 1, ACCEPTANCE_21C+' sections 8 and 9 not found exactly once'
    outside = [j+1 for j, l in inserted if not h8[0] < j < h9[0]]
    assert not outside, ACCEPTANCE_21C+' gained lines outside section 8 (line numbers): '+str(outside)
    unmentioned = [l for _, l in inserted if l.strip() and not POINTER.search(l)]
    assert not unmentioned, ACCEPTANCE_21C+' gained lines that do not mention 21D: '+str(unmentioned)
    return inserted


def stale_diff(diff_text, registry_inserted, gametest_text):
    """Why production-vs-start.diff is stale, or None: it must carry every line Goal21D added to HazardRegistry.java and every line of the new
    HazardGameTests.java (once that exists), and remove none."""
    diff = diff_text.replace('\r\n', '\n').split('\n')
    plus = Counter(l[1:] for l in diff if l.startswith('+') and not l.startswith('+++'))
    removed = [l for l in diff if l.startswith('-') and not l.startswith('---')]
    # split('\n') leaves one empty element after the final newline of the new file; a diff has no line for it.
    gametest_lines = lines_of(gametest_text.encode('utf-8')) if gametest_text else []
    if gametest_lines and gametest_lines[-1] == '': gametest_lines = gametest_lines[:-1]
    needed = Counter([line for _, line in registry_inserted] + gametest_lines)
    short = sorted(l for l, n in needed.items() if plus[l] < n)
    if removed or short:
        return f'production-vs-start.diff is stale: {len(removed)} removed lines, {len(short)} production lines missing (first: {short[:1]})'
    return None


def jar_entry(path):
    for prefix in ('src/main/resources/', 'src/generated/resources/'):
        if path.startswith(prefix): return path[len(prefix):]
    raise AssertionError('not a resource: '+path)


def main(check, gametest_log):
    pending = []
    base = read(BASELINE)
    prior_receipt = read(PREVIOUS_RECEIPT)

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal21D commits nothing), the recorded start content.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD, 'Unexpected frozen start'
    assert base['build_libs_jar_sha256'] == START_JAR_SHA, 'Baseline names another start build'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == START_HEAD, 'NEO HEAD moved during Goal21D: '+head
    assert set(base['start_content']) >= {'goal21a', 'control_nbt_null_fix', 'goal21b', 'goal21c', 'fix_paths'}, 'Baseline start content lacks a group'
    assert set(o for owners in base['dirty_attribution'].values() for o in owners) <= {'goal21a', 'control-nbt-null-fix', 'goal21b', 'goal21c'}, \
        'Baseline attributes start content to an unknown owner'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b'} and not any(base['older_receipt_evidence_drift'].values()) \
        and not base['previous_receipt_evidence_drift'], 'Baseline records drifted receipt evidence'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n

    # 2. Previous deliveries: the goal21c package, every old release file and the protected evidence (Goal21C runner set + goal21c receipt
    # + the goal21a and goal21b receipts).
    assert base['previous_release'] == dict(path=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES), 'Baseline names another previous release'
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'goal21c JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'goal21c release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'goal21c SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'goal21c SHA256SUMS.txt content changed'
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    for p, h in base['old_release_files'].items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release file changed: '+p
    old_releases = dict(base['old_releases'])
    assert old_releases.get(PREVIOUS.relative_to(ROOT).as_posix()) == PREVIOUS_SHA
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    protected = protected_paths(base)
    # The goal21c receipt hashes the 21C acceptance master list; Goal21D inserts its pointer there, so it is checked insert-only below.
    acceptance_receipt_sha = protected.pop(ACCEPTANCE_21C)
    assert base['previous_receipt_protected_paths'][ACCEPTANCE_21C] == acceptance_receipt_sha == sha(START_FILES/ACCEPTANCE_21C), \
        'Frozen start copy of '+ACCEPTANCE_21C+' is not the goal21c receipt hash'
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)

    # 3. Changes since the start: each path in the owner table, attributed to goal21d; the start attribution is recorded alongside. Start
    # content (21A, the control-NBT fix, 21B, 21C) outside the owner table is therefore unchanged; its shared files carry only this batch's
    # delta (the checks below).
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    assert not unassigned, 'Unassigned path changed since the Goal21D start: '+str(unassigned)
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal21D start: '+str(deleted)
    assert not (ROOT/NO_OWNERSHIP_RECORD).exists(), 'Goal21D has no resource ownership record: '+NO_OWNERSHIP_RECORD
    missing_required = [p for p in REQUIRED_CHANGES if p not in changes]
    if missing_required:
        if not check: raise AssertionError('Required Goal21D changes missing: '+str(missing_required))
        pending += ['change not present yet: '+p for p in missing_required]
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    assert set(since) <= set(PRODUCTION), 'src/main change outside the production list: '+str(sorted(set(since) - set(PRODUCTION)))
    for p in NEW_JAVA:
        assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, start_attribution=base['dirty_attribution'].get(p, []),
                        before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    start_content_touched = sorted(p for p in changes if base['dirty_attribution'].get(p))
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    assert baselines_now == {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}, 'A snapshot was added or changed'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'], 'review-6a11998d5852 snapshot changed'

    # HazardRegistry.java is insert-only against its frozen start copy and keeps the start's line endings.
    start_registry = (START_FILES/HAZARD_REGISTRY).read_bytes()
    registry = (ROOT/HAZARD_REGISTRY).read_bytes()
    registry_inserted = insertions(lines_of(start_registry), lines_of(registry))
    assert registry_inserted is not None, HAZARD_REGISTRY+' is not insert-only against the start copy (a start line was changed, moved or removed)'
    start_eol, eol = eol_counts(start_registry), eol_counts(registry)
    assert (start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), \
        f'{HAZARD_REGISTRY} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}'
    if not registry_inserted:
        if not check: raise AssertionError(HAZARD_REGISTRY+' has no inserted line')
        pending.append(HAZARD_REGISTRY+' still equals the start')

    # 4. Language and the generated tree: Goal21D adds no key, so en_us.json, zh_cn.json, the mapping and NtmLanguageProvider equal their start
    # bytes; since the start only the stamp of the generated tree may change, and no generated resource is added or retired.
    for p in UNCHANGED_LANGUAGE:
        assert base['files'].get(p) == sha(ROOT/p), 'Goal21D adds no language key, but changed '+p
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    assert set(generated_since) <= set(GENERATED), 'Generated change outside the Goal21D list: '+str(generated_since)
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    empty = dict(added=[], removed=[], changed=[])
    en_delta, zh_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now)
    map_delta = lang_delta(read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries'])
    assert en_delta == zh_delta == map_delta == empty, 'Language delta is not empty'
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal21c generated tree'
    generated_added = sorted(set(stamp['generated']) - start_generated)
    generated_retired = sorted(start_generated - set(stamp['generated']))
    assert not generated_added and not generated_retired, f'Generated resources added {generated_added} or retired {generated_retired} since the start'

    # 5. Evidence: GameTest log, audits, Gradle logs, patch and diff, the final suite run, the hazard verifier and compare.
    evidence = {}
    gametest_line = gametest_count = None
    gametest_text = (ROOT/GAMETEST_JAVA).read_text(encoding='utf-8') if (ROOT/GAMETEST_JAVA).is_file() else ''
    hazard_tests = len(GAMETEST_ANNOTATION.findall(gametest_text))
    gametest_expected = prior_receipt['gametest']['tests'] + hazard_tests
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
        # The goal21c server's tests plus every @GameTest of HazardGameTests (no other GameTest source may change: owner table).
        assert hazard_tests and gametest_count == gametest_expected, \
            f'GameTest server ran {gametest_count} tests, not the {prior_receipt["gametest"]["tests"]} goal21c tests + {hazard_tests} hazard tests'
        gametest_line = f'All {gametest_count} required tests passed'
        evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name in AUDITS:
        if not (OUT/name).is_file():
            if not check: raise AssertionError('Missing audit: '+name)
            pending.append('evidence: build/migration/goal21d/'+name)
            continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        audit_summaries[name] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not (OUT/name).is_file():
            if not check: raise AssertionError('Missing log: '+name)
            pending.append('evidence: build/migration/goal21d/'+name)
            continue
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run'
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not (OUT/name).is_file() or not (OUT/name).stat().st_size:
            if not check: raise AssertionError('Missing or empty evidence file: '+name)
            pending.append('evidence: build/migration/goal21d/'+name)
            continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # production-vs-start.diff must not be stale (HazardGameTests.java is covered once it exists).
    diff_path = OUT/'production-vs-start.diff'
    if diff_path.is_file() and diff_path.stat().st_size:
        message = stale_diff(diff_path.read_text(encoding='utf-8-sig'), registry_inserted, gametest_text)
        if message:
            if not check: raise AssertionError(message)
            pending.append(message)
    final = None
    # The 73 suites of the Goal21C final run plus the hazard verifier.
    reference_suites = set(read(REFERENCE_21C)['suites'])
    final_expected = len(reference_suites) + 1
    if (OUT/FINAL_SUMMARY).is_file():
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        assert set(final['suites']) == reference_suites | {HAZARD_SUITE}, 'Final run suites differ from the goal21c final set + the hazard verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {HAZARD_SUITE})))
        entry = final['suites'][HAZARD_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, HAZARD_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    elif check:
        pending.append('evidence: build/migration/goal21d/'+FINAL_SUMMARY)
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
        pending.append('evidence: build/migration/goal21d/'+VERIFY_REPORT)
    else:
        raise AssertionError('Missing '+VERIFY_REPORT)
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree, older than Goal21B): the original unchanged, the target exactly the
    # goal21c receipt's compare target set (the control-NBT fix, Goal21B and Goal21C paths) plus the Goal21D paths inside the compare inventory
    # (compare never lists the stamp). No new snapshot is generated.
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'goal21c receipt compare target set is incomplete'
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
        pending.append('evidence: build/migration/goal21d/'+COMPARE)
    else:
        raise AssertionError('Missing '+COMPARE)

    # 6. JAR: build/libs is what gets packaged; delta against the goal21c package, every entry owned by goal21d. Classes only: no resource,
    # no language entry and no directory changes (the stamp is not packaged).
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    if sha(JAR) in (PREVIOUS_SHA, START_JAR_SHA):
        if not check: raise AssertionError('build/libs JAR is still the goal21c package (run build)')
        pending.append('build/libs/hbmsntm-198A.jar is still the goal21c package (run build)')
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
                'JAR en_us.json or zh_cn.json differs from the goal21c package: en '+str(en_jar)+', zh '+str(zh_jar)
            assert lang_delta(json.loads(prior.read(ZH_ENTRY)), zh_start) == empty, 'Start zh_cn.json differs from the goal21c package'
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        goal21d_java = JAVA + NEW_JAVA
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = [OWNER] if n.endswith('.class') and owner_class(n) in goal21d_java else []
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        assert not unowned, 'Unowned JAR change: '+str(unowned)
        assert not dir_delta['added'] and not dir_delta['removed'], 'JAR directory delta: '+str(dir_delta)
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        assert set(class_owners) == set(goal21d_java), 'Not every changed Java source changed a class: '+str(sorted(set(goal21d_java) - set(class_owners)))
        assert 'com/hbm/hazard/HazardRegistry.class' in jar_delta['modified'], 'HazardRegistry.class is not a modified JAR class'
        assert 'com/hbm/hazard/HazardRegistry$Frame.class' in jar_delta['added'], 'HazardRegistry$Frame.class is not a new JAR class'
        assert 'com/hbm/gametest/HazardGameTests.class' in jar_delta['added'], 'HazardGameTests.class is not a new JAR class'
        assert not [n for n in jar_delta['removed'] if n.endswith('.class')], 'Removed JAR classes: '+str(jar_delta['removed'])
        added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
        removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
        assert classes and len(classes) == prior_receipt['compiled_classes_verified'] + added_classes - removed_classes, \
            f'Compiled class count {len(classes)} is not the goal21c count {prior_receipt["compiled_classes_verified"]} +{added_classes} -{removed_classes}'
        language = dict(en=en_jar, zh=zh_jar)

    # 7. Records: the release name, the batch reports and the insert-only pointer in the 21C acceptance master list.
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
        assert base['files'].get('migration/GOAL21D.md') != sha(ROOT/'migration/GOAL21D.md'), 'GOAL21D.md has no delivery record'
    acceptance_start = (START_FILES/ACCEPTANCE_21C).read_bytes()
    acceptance_now = (ROOT/ACCEPTANCE_21C).read_bytes()
    acceptance_pointer = None
    if acceptance_now == acceptance_start:
        if not check: raise AssertionError(ACCEPTANCE_21C+' has no Goal21D pointer')
        pending.append(ACCEPTANCE_21C+' still equals the goal21c receipt version (no Goal21D pointer in section 8 yet)')
    else:
        inserted = acceptance_insertions(acceptance_start, acceptance_now)
        acceptance_pointer = dict(path=ACCEPTANCE_21C, before_sha256=acceptance_receipt_sha, after_sha256=sha(ROOT/ACCEPTANCE_21C),
                                  inserted_lines=[l for _, l in inserted], insert_only=True,
                                  explanation='Goal21D inserted its pointer into section 8 of the Goal 21 unified acceptance master list, which the goal21c '
                                              'receipt hashes; only inserted lines mentioning 21D differ from the receipt version. The goal21c receipt is '
                                              'not rewritten.')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=generated_added,
                   start_content_touched=start_content_touched, registry_inserted_lines=len(registry_inserted),
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta,
                   acceptance_21c_pointer=dict(inserted=len(acceptance_pointer['inserted_lines']), after_sha256=acceptance_pointer['after_sha256']) if acceptance_pointer else None,
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta,
                   class_owners=class_owners, gametest=gametest_line, gametest_expected=gametest_expected, hazard_tests=hazard_tests,
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
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different goal21d JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest == sha(JAR) and digest not in (PREVIOUS_SHA, START_JAR_SHA), 'Packaged JAR is not build/libs or is an older JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in reports}
    evidence[BASELINE.relative_to(ROOT).as_posix()] = sha(BASELINE)
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified', scope=SCOPE,
                   radiation_warning=GOAL21D_RADIATION+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, planning_commit=START_HEAD, commits={}, target_head_at_packaging=head,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], dirty_attribution=base['dirty_attribution'], start_build_sha256=START_JAR_SHA,
                                      touched_by_goal21d=start_content_touched,
                                      note='The start tree is HEAD dbfa6746 + the uncommitted Goal21A delivery + the control-NBT null fix + the '
                                           'uncommitted Goal21B delivery + the uncommitted Goal21C delivery, all packaged by goal21c; start-content '
                                           'files changed here carry only Goal21D hunks and are attributed to goal21d.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added,
                   compiled_classes_verified=prior_receipt['compiled_classes_verified'] + sum(1 for n in jar_delta['added'] if n.endswith('.class')) - sum(1 for n in jar_delta['removed'] if n.endswith('.class')),
                   production=PRODUCTION, sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   resources={}, resource_ownership=None,
                   language=dict(keys={}, unchanged={p: sha(ROOT/p) for p in UNCHANGED_LANGUAGE}, jar_delta=language,
                                 note='Goal21D adds no resource and no language key: en_us.json, zh_cn.json, the zh_cn mapping and NtmLanguageProvider '
                                      'equal their start bytes.'),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   goal21c_acceptance_drift_explained=acceptance_pointer,
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; it covers the hazard '
                                      'registrations as far as HazardGameTests asserts them, not the effect of a hazard on a player in a real world, '
                                      'tooltips or protection gear in game.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + [LOCALIZATION_RECORD],
                   evidence_sha256={**hashes, **evidence, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the resource, packaged-resource and localization audits, '
                            'the static hazard verifier with mutations, the final old-suite rerun, compare against the review-6a11998d5852 snapshot '
                            'and independent JAR bytes (classes of the two changed sources only; no resource or language change). No client, real '
                            'save, multiplayer or player interaction was run: the hazard effects on players and entities, tooltips and protection '
                            'gear are unverified in game.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal21c package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
