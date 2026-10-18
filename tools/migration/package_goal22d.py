"""Package Goal22D (material hazard registration addendum: HazardRegistry.registerMaterialAddendum with the special billets, powder_caesium and the
ore crystals of the original HazardRegistry.java, the ASBESTOS and P_WHITE frames of the original OreDictManager.java, the new Frame.asbestos method,
and the HazardGameTests additions) cumulatively on the goal22c package, without replacing any previous delivery. It also packages, for the first time,
the Goal22C thorium fuel rod recipe follow-up that was done after the goal22c package (GOAL22C.md "跟进").

python -B -X utf8 tools/migration/package_goal22d.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal22d/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to
build/migration/goal22d/gametest-final.log (the GameTest dedicated-server log of the settled tree).

The frozen start is build/migration/goal22d/baseline.json: NEO HEAD 29702b40 plus the Goal22A, Goal22B and Goal22C deliveries and the Goal22C thorium
fuel rod follow-up kept UNCOMMITTED (133 dirty paths, Goal 22 decision 14). build/libs at the start is NOT the goal22c package: it is the follow-up's
working-tree JAR (baseline goal22c_followup), whose entry delta against the goal22c package is recorded and must be exactly the follow-up's. Every
change since the start is computed from the baseline file hashes (not from git diff) and must be in the owner table below; every other path must
still equal its start hash. Several start paths (the generation stamp, README, features, UPSTREAM-REVIEWS, LOCALIZATION, GOAL22.md, GOAL22D.md and
the unified acceptance checklist GOAL22C-ACCEPTANCE.md) are modified again here: their before hash is the start hash, their after hash the live one.
The JAR delta against the goal22c package is attributed per entry (the follow-up or goal22d); any entry without exactly one owner fails. Counts that
records quote (suites, GameTests, generated resources, classes, releases, registrations) are computed here, never hard-coded; the previous package's
SHA-256, size and receipt hashes are read from the files and the baseline, not from literals. The batch adds no language key: the language provider,
en_us.json, zh_cn.json and the zh_cn mapping must equal their start hashes.

The receipts that hash records (goal21a..goal21d, the review-g21d-hazard-fix receipt, goal22a, goal22b and goal22c) were written before the Goal 21
in-game acceptance appended its result lines to the acceptance checklists, before the O1 record notes and (goal22c) before the thorium follow-up
section of GOAL22C.md; those records already differ from their receipt hashes at the frozen start (baseline older_receipt_evidence_drift and
previous_receipt_evidence_drift). They are listed in the receipt as start drift (receipt hashes, start hash, current hash) and must still equal their
start hash; no receipt is rewritten and no other protected path may drift. migration/GOAL22C-ACCEPTANCE.md, which the goal22c receipt hashes, is
the one receipt-hashed record this batch changes (section 4 of the unified checklist): it is listed as explained drift, insert-only against its start
copy with at most one edited line inside section 4."""
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
from package_goal22b import (git_ro, original_blob, edit_counts, stale_diff, verifier_problems, receipt_protected, start_drift_paths, AUDITS, LOGS, FILES,
                             CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, GAMETEST_ANNOTATION, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import (OUT as GOAL22C_OUT, BASELINE as GOAL22C_BASELINE, protected_paths as goal22c_protected_paths, recipe_summary, zirnox_ordinals,
                             RECIPE_DIR, ADVANCEMENT_DIR, GENERATED_ROOT, SHARED_RECORDS, NAMES_RELEASE, J, PROVIDER, LANGUAGE_FILES, RODS)

OUT = ROOT/'build/migration/goal22d'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL22C_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL22C_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal22c/hbmsntm-198A-goal22c.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal22d'
RELEASE_NAME = 'hbmsntm-198A-goal22d.jar'
OWNER = 'goal22d'
FOLLOWUP_OWNER = 'goal22c-thorium-rod-followup'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
# Production (owner goal22d): both files exist at the start. HazardRegistry is insert-only except one javadoc line; HazardGameTests is rewritten in
# part (counts only).
HAZARD_REGISTRY = J+'hazard/HazardRegistry.java'
HAZARD_TESTS = J+'gametest/HazardGameTests.java'
MODIFIED_JAVA = [HAZARD_REGISTRY, HAZARD_TESTS]
PRODUCTION = MODIFIED_JAVA
GENERATED = [STAMP]
TOOLS = ['tools/migration/verify_goal22d_hazards.py', 'tools/migration/package_goal22d.py']
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal22d-* or GOAL22D-* record is hashed as well.
REPORTS = ['migration/GOAL22D.md', 'migration/GOAL22D-ACCEPTANCE.md', 'migration/goal22d-static-review.md']
BATCH_RECORD = re.compile(r'migration/(goal22d-[^/]+\.(json|md)|GOAL22D-[^/]+\.md)')
# The goal22c receipt hashes the unified checklist; section 4 of it is filled by this batch (explained drift, not a protected path at its goal22c hash).
ACCEPTANCE_22C = 'migration/GOAL22C-ACCEPTANCE.md'
ACCEPTANCE_SECTION = re.compile(r'##\s*4\.')
ACCEPTANCE_NEXT_SECTION = re.compile(r'##\s*5\.')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = MODIFIED_JAVA + GENERATED + TOOLS + REPORTS + SHARED_RECORDS + [ACCEPTANCE_22C]
# The one edited line of HazardRegistry.java: the Frame javadoc names the new asbestos method.
FRAME_OLD, FRAME_NEW = 'rad/hot/hydro/blinding collect', 'rad/hot/hydro/blinding/asbestos collect'
ORIGINAL_HAZARDS = 'src/main/java/com/hbm/hazard/HazardRegistry.java'
ORIGINAL_DICT = 'src/main/java/com/hbm/inventory/OreDictManager.java'
# The 18 new registrations: id -> (original path, line, kind, [(type, level)]). Levels are the float32 products the handoff records (crystal = block = 10,
# billet 0.5, powder 3); the verifier computes them from the original constants, here they are only compared with its report (relative 1e-4).
ADDENDUM = {
    'billet_balefire_gold': (ORIGINAL_HAZARDS, 331, 'item', [('RADIATION', 250.0)]),
    'billet_flashlead': (ORIGINAL_HAZARDS, 332, 'item', [('RADIATION', 6250.0), ('HOT', 7.0)]),
    'billet_po210be': (ORIGINAL_HAZARDS, 333, 'item', [('RADIATION', 112.5)]),
    'billet_ra226be': (ORIGINAL_HAZARDS, 334, 'item', [('RADIATION', 11.25)]),
    'billet_pu238be': (ORIGINAL_HAZARDS, 335, 'item', [('RADIATION', 15.0)]),
    'powder_caesium': (ORIGINAL_HAZARDS, 478, 'item', [('HYDROACTIVE', 1.0), ('HOT', 3.0)]),
    'crystal_uranium': (ORIGINAL_HAZARDS, 485, 'item', [('RADIATION', 3.5)]),
    'crystal_thorium': (ORIGINAL_HAZARDS, 486, 'item', [('RADIATION', 1.0)]),
    'crystal_plutonium': (ORIGINAL_HAZARDS, 487, 'item', [('RADIATION', 75.0)]),
    'crystal_schraranium': (ORIGINAL_HAZARDS, 488, 'item', [('RADIATION', 15.0)]),
    'crystal_schrabidium': (ORIGINAL_HAZARDS, 489, 'item', [('RADIATION', 150.0)]),
    'crystal_phosphorus': (ORIGINAL_HAZARDS, 490, 'item', [('HOT', 20.0)]),
    'crystal_lithium': (ORIGINAL_HAZARDS, 491, 'item', [('HYDROACTIVE', 10.0)]),
    'crystal_trixite': (ORIGINAL_HAZARDS, 492, 'item', [('RADIATION', 250.0)]),
    # ASBESTOS frame (OreDictManager.java:424, .asbestos(1F)): shape multipliers ingot 1, powder 3, block 10; the ore shapes are not registered.
    'ingot_asbestos': (ORIGINAL_DICT, 424, 'frame', [('ASBESTOS', 1.0)]),
    'powder_asbestos': (ORIGINAL_DICT, 424, 'frame', [('ASBESTOS', 3.0)]),
    'block_asbestos': (ORIGINAL_DICT, 424, 'frame', [('ASBESTOS', 10.0)]),
    # P_WHITE frame (OreDictManager.java:460, .hot(5)): the ingot only, NEO has no block_white_phosphorus.
    'ingot_phosphorus': (ORIGINAL_DICT, 460, 'frame', [('HOT', 5.0)]),
}
ITEM_ROWS = [i for i, v in ADDENDUM.items() if v[2] == 'item']
FRAME_ROWS = [i for i, v in ADDENDUM.items() if v[2] == 'frame']
# Original lines that must name each table id (the stored blob at the recorded commit); frame ids appear as the shape call of the frame line.
SHAPE_CALL = {'ingot_asbestos': '.ingot(ingot_asbestos)', 'powder_asbestos': '.dust(powder_asbestos)', 'block_asbestos': '.block(block_asbestos)',
              'ingot_phosphorus': '.ingot(ingot_phosphorus)'}
FRAME_CALL = {424: '.asbestos(1F)', 460: '.hot(5)'}
# Skipped, deferred or unchanged original rows (no fifth state): id/name -> (original path, line(s), state, reason).
SKIPPED = {
    'pellet_rtg..pellet_rtg_depleted': (ORIGINAL_HAZARDS, '337-347', 'RTG-deferred',
                                        'eleven registerRTGPellet rows need the RTG modifier; NEO has no hazard/modifier RTG class (pellet_rtg exists and stays without hazard)'),
    'block_fallout': (ORIGINAL_HAZARDS, '477', 'NEO-missing-skip', 'NEO has no block_fallout block'),
    'tile_lab_broken': (ORIGINAL_HAZARDS, '481', 'NEO-missing-skip', 'NEO has no tile_lab_broken block'),
    'block_white_phosphorus': (ORIGINAL_DICT, '460', 'NEO-missing-skip', 'NEO has no block_white_phosphorus block (the P_WHITE ingot is registered)'),
    'ore shapes of ASBESTOS': (ORIGINAL_DICT, '424', 'ore-not-registered', 'ore blocks never carry hazards (Goal 21 decision 13)'),
}
UNCHANGED_EXISTING = {
    'fallout': (ORIGINAL_HAZARDS, 476, 'ModBlocks.fallout', 'NEO FALLOUT already RADIATION 60 (fo * powder * 2)'),
    'brick_asbestos': (ORIGINAL_HAZARDS, 480, 'brick_asbestos', 'already registered, ASBESTOS 1'),
    'powder_coltan_ore': (ORIGINAL_HAZARDS, 482, 'powder_coltan_ore', 'already registered, ASBESTOS 3'),
}
RTG_LINES = range(337, 348)
FEATURE_GROUP = 'materials'
FOLLOWUP_ROD = 'rod_zirnox_thorium_fuel'
# Indexed by the receipt as evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start:
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'chain.sh', 'handoff-tests.md', 'handoff-packaging.md')
GAMETEST_LOG = 'build/migration/goal22d/gametest-final.log'
NEW_SUITE = 'verify_goal22d_hazards.py --gametest-log build/migration/goal22d/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
RADIATION_NOTE = ('Goal22D: ore crystals (crystal_schrabidium 150, crystal_trixite 250, crystal_plutonium 75 RAD/s per item), the special billets '
                  '(billet_flashlead 6250 and HOT 7, billet_balefire_gold 250) and caesium powder (hydroactive, hot) now carry their original hazards, '
                  'including stacks already in existing saves; keep crystallizer output in shielded containers and test only in separately authorized '
                  'disposable worlds. ')


def scope_text(new_tests):
    return (f'Goal22D (material hazard registration addendum, 21D out-of-scope finding 5): HazardRegistry.registerItems calls a new private method '
            f'registerMaterialAddendum() right after registerMaterials(), registering {len(ADDENDUM)} hazard rows of the original, with NEO\'s existing constants '
            f'and the original multiplication order: {len(ITEM_ROWS)} item-level rows of HazardRegistry.java (:331-335 billet_balefire_gold, billet_flashlead '
            f'with HOT 7, billet_po210be, billet_ra226be, billet_pu238be; :478 powder_caesium HYDROACTIVE 1 + HOT 3; :485-492 the ore crystals uranium, thorium, '
            f'plutonium, schraranium, schrabidium, phosphorus HOT, lithium HYDROACTIVE and trixite, crystal = block = 10) and {len(FRAME_ROWS)} frame rows of '
            f'OreDictManager.java (:424 ASBESTOS frame, ingot_asbestos / powder_asbestos / block_asbestos at 1 / 3 / 10, through the new Frame.asbestos method; '
            f':460 P_WHITE hot(5), ingot_phosphorus HOT 5); the Frame javadoc names asbestos (the only edited line). Skipped and recorded: block_fallout, '
            f'tile_lab_broken and block_white_phosphorus (no NEO identity). Deferred and recorded: the eleven RTG pellet rows (:337-347) with the RTG modifier '
            f'(pellet_rtg stays without hazard). Ore blocks are never registered (Goal 21 decision 13); the fallout block (:476), brick_asbestos (:480) and '
            f'powder_coltan_ore (:482) were already registered and are unchanged, as is every other hazard value. No new item, resource, language key, data '
            f'component or save format (the language provider, en_us.json, zh_cn.json and the zh_cn mapping equal their start hashes). The batch adds '
            f'{new_tests} HazardGameTests and rewrites the unlisted-items loop of hazard_none_for_ores_and_unlisted. Gameplay impact: hazards are looked up by '
            f'item ID at runtime, so crystals, caesium powder and the special billets already in existing saves carry their hazards immediately after the '
            f'update (original behavior). This package also first packages the Goal22C thorium fuel rod recipe follow-up made after the goal22c package '
            f'(recipe {FOLLOWUP_ROD}: empty ZIRNOX rod + 2 billet_thorium_fuel -> rod_zirnox META 3, the original RodRecipes.java:30), with its generated recipe '
            f'and advancement JSONs.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal22d release directory: '+rel


def protected_paths(base):
    """What the goal22c packager protected (built there from the Goal21A..Goal22B starts and receipts, the goal22b receipt and the goal22c start), plus
    every path the goal22c receipt hashes (base previous_receipt_protected_paths), the paths the older receipts hash (the 22D baseline lists the goal22b
    receipt among them) and every release file of the frozen start. The records that already drifted at the start (migration/GOAL22C.md after the
    thorium follow-up, the Goal 21 acceptance appends, the O1 notes) are pinned at their start hash (baseline files) instead of any receipt hash. The
    unified acceptance checklist is returned separately: this batch fills its section 4 (explained drift). One path never carries two hashes."""
    out = dict(goal22c_protected_paths(read(GOAL22C_BASELINE)))
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'], 'Start drift path is not a frozen file: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    for p in drift:
        assert out.get(p, base['files'][p]) == base['files'][p], 'The goal22c start pinned another hash for '+p
        out.pop(p, None)
        out[p] = base['files'][p]
    assert out.get(ACCEPTANCE_22C) == base['files'][ACCEPTANCE_22C], 'The goal22c receipt hash of the unified checklist is not its start hash'
    out.pop(ACCEPTANCE_22C)
    return out


def start_drift_report(base):
    """{path: {receipts: {label: hash}, start_sha256, current_sha256}} for the records that differ from a receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal22c receipt'] = base['previous_receipt_protected_paths'][p]
        start = base['files'][p]
        newest = receipts.get('goal22c receipt')
        if newest is None or newest == start:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21 in-game acceptance result lines or the O1 record notes); the newest '
                           'receipt that hashes it'+(' (goal22c) records the start hash' if newest == start else ' is older than the start')+
                           '. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal22c package: the Goal22C thorium fuel rod follow-up section was appended (GOAL22C.md "跟进"), so the goal22c '
                           'receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal22c receipt is '
                           'not rewritten.')
        out[p] = dict(receipt_hashes=receipts, start_sha256=start, current_sha256=sha(ROOT/p), explanation=explanation)
    return out


def group(p, followup):
    if p in MODIFIED_JAVA: return 'production'
    if p == STAMP: return 'generated'
    if p in TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    if p == ACCEPTANCE_22C: return 'records-acceptance'
    return None


def sections(lines, start_re, next_re):
    """(first, last) index of the section whose heading line matches start_re, up to the heading matching next_re; None when absent."""
    first = next((i for i, l in enumerate(lines) if start_re.match(l)), None)
    if first is None: return None
    last = next((i for i in range(first+1, len(lines)) if next_re.match(lines[i])), len(lines))
    return first, last


def edits_only(old, new, region=None, max_edits=0):
    """(inserted line count, [(old line, [new lines])]) when new is old plus inserted lines plus at most max_edits single-line replacements whose old line
    index lies in region (a range), else None."""
    from difflib import SequenceMatcher
    inserted, edits = 0, []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == 'equal': continue
        if tag == 'insert': inserted += j2-j1; continue
        if tag == 'replace' and i2-i1 == 1 and (region is None or i1 in region):
            edits.append((old[i1], new[j1:j2]))
            inserted += j2-j1-1
            continue
        return None
    return (inserted, edits) if len(edits) <= max_edits else None


def tokens(node):
    """Every key and scalar of a JSON value, flattened (strings as given, numbers as floats when they parse)."""
    out = []
    def walk(n):
        if isinstance(n, dict):
            for k, v in n.items(): out.append(str(k)); walk(v)
        elif isinstance(n, (list, tuple)):
            for v in n: walk(v)
        else: out.append(n)
    walk(node)
    return out


def number(t):
    if isinstance(t, bool): return None
    if isinstance(t, (int, float)): return float(t)
    try: return float(str(t))
    except ValueError: return None


def report_rows(report, ids):
    """{id: [candidate JSON nodes]}: nodes of the verifier report that carry an id as a key or as an exact string value (optionally hbmsntm:-prefixed)."""
    found = {}
    def name(s): return s.removeprefix('hbmsntm:') if isinstance(s, str) else None
    def visit(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if name(k) in ids: found.setdefault(name(k), []).append(v)
            for v in n.values():
                if name(v) in ids: found.setdefault(name(v), []).append(n)
            for v in n.values(): visit(v)
        elif isinstance(n, (list, tuple)):
            for v in n:
                if name(v) in ids: found.setdefault(name(v), []).append(n)
            for v in n: visit(v)
    visit(report)
    return found


def row_supported(candidates, entries):
    """True when one candidate carries every (type, level) of the row: the type name (case-insensitive) and a number equal within 1e-4 relative."""
    for node in candidates:
        flat = tokens(node)
        names = {str(t).upper() for t in flat if isinstance(t, str)}
        numbers = [number(t) for t in flat if number(t) is not None]
        if all(t in names and any(abs(n-level) <= 1e-4*max(1.0, abs(level)) for n in numbers) for t, level in entries): return True
    return False


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
    followup = base['goal22c_followup']
    followup_added, followup_modified = followup['added'], followup['modified']
    followup_paths = sorted(set(followup_added) | set(followup_modified))
    followup_generated = sorted(p for p in followup_added)

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal22D commits nothing), the recorded start content.
    start_head = prior_receipt['target_start_commit']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at 6a11998d'
    assert base['target_head'] == start_head == prior_receipt['target_head_at_packaging'], 'The frozen start is not the goal22c start commit'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal22D: '+head
    assert set(base['start_content']) == {'committed', 'uncommitted'}, 'Baseline start content differs'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b'}, \
        'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['dirty_paths'] == len(base['dirty_paths']) and startup['frozen_file_hashes'] == len(base['files']) \
        and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['previous_jar_sha256'] == base['previous_release']['sha256'] and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] \
        and startup['goal22c_followup_paths'] == len(followup_paths), 'startup-verification.json differs from baseline.json'
    # The start tree is the goal22a..goal22c delivery plus the thorium follow-up, uncommitted: its dirty paths are the goal22c receipt's start paths and
    # changed files plus the follow-up's added files, each at the hash the goal22c receipt recorded (the after hash for a changed file, the receipt's own
    # start hash for a path goal22c left alone) or, for the follow-up's paths, at the follow-up hash recorded in the baseline.
    receipt_changed = {c['path']: c for c in prior_receipt['changed_files']}
    receipt_start = prior_receipt['start_content']['dirty_files']
    assert sorted(base['dirty_paths']) == sorted(set(receipt_start) | set(receipt_changed) | set(followup_added)), \
        'The start dirty paths are not the goal22c start paths + changed files + the follow-up additions'
    for p in followup_modified: assert p in base['dirty_files'], 'Follow-up path is not a start dirty path: '+p
    for p in followup_modified:
        assert followup['goal22c_after_sha256'][p] == receipt_changed[p]['after_sha256'], 'The follow-up records another goal22c hash for '+p
    for p in base['dirty_paths']:
        if p in followup['added']: expected = followup['added'][p]
        elif p in followup_modified: expected = followup['modified'][p]
        else: expected = receipt_changed[p]['after_sha256'] if p in receipt_changed else receipt_start[p]
        assert base['files'][p] == base['dirty_files'][p] == expected, 'The start copy of a goal22a..goal22c or follow-up path differs from the receipt: '+p
    # build/libs at the start is the follow-up's working-tree JAR; its delta against the goal22c package is exactly the follow-up's.
    start_jar_sha = base['build_libs_jar_sha256']
    assert start_jar_sha == followup['build_libs_jar_sha256'] and base['build_libs_vs_previous'] == followup['jar_delta_vs_goal22c'], \
        'build/libs at the start is not the recorded follow-up JAR'
    followup_jar = base['build_libs_vs_previous']
    jar_names = {p.removeprefix(GENERATED_ROOT) for p in followup_generated}
    assert followup_jar['added'] == sorted(jar_names) and not followup_jar['removed'], 'The follow-up JAR delta adds more than its two generated JSONs'
    followup_classes = {owner_class(n) for n in followup_jar['modified']}
    assert all(n.endswith('.class') for n in followup_jar['modified']) and followup_classes <= set(followup_modified), \
        'The follow-up JAR delta modifies classes whose sources the follow-up did not change: '+str(sorted(followup_classes - set(followup_modified)))
    followup_entries = {n: 'added' for n in followup_jar['added']} | {n: 'modified' for n in followup_jar['modified']}

    # 2. Previous deliveries: the goal22c package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha != previous_sha, 'build/libs at the start must be the follow-up JAR, not the previous package'
    assert sha(PREVIOUS) == previous_sha and PREVIOUS.stat().st_size == previous_bytes, 'Previous JAR changed'
    assert prior_receipt['sha256'] == previous_sha and prior_receipt['bytes'] == previous_bytes, 'Previous receipt names another JAR'
    previous_receipt_sha = base['old_release_files'][PREVIOUS_RECEIPT.relative_to(ROOT).as_posix()]
    previous_sums_sha = base['old_release_files'][PREVIOUS_SUMS.relative_to(ROOT).as_posix()]
    assert sha(PREVIOUS_RECEIPT) == previous_receipt_sha, 'Previous release.json changed'
    assert sha(PREVIOUS_SUMS) == previous_sums_sha, 'Previous SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (previous_sha+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Previous SHA256SUMS.txt content changed'
    for p, h in base['old_release_files'].items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release file changed: '+p
    previous_rel = PREVIOUS.relative_to(ROOT).as_posix()
    old_releases = dict(base['old_releases'])
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal22c receipt list + the goal22c package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal22c receipt count + the goal22c release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal22c receipt'
    assert base['previous_receipt_evidence_drift'] == ['migration/GOAL22C.md'], \
        'The goal22c receipt evidence drift at the start is not exactly the follow-up GOAL22C.md: '+str(base['previous_receipt_evidence_drift'])
    assert base['older_receipt_evidence_drift']['goal22a'] == [] and base['older_receipt_evidence_drift']['goal22b'] == [], \
        'The goal22a or goal22b receipt evidence had already drifted at the start'
    protected = protected_paths(base)
    drift_report = start_drift_report(base)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal22c receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal22d. Everything else equals its start hash. The follow-up paths equal
    # their start hash except those this batch changes again (the stamp and the shared records).
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p, followup_paths) is None)
    need(not unassigned, 'Path changed since the Goal22D start that the owner table does not list (production outside HazardRegistry.java and HazardGameTests.java, '
         'a generated file other than the stamp, a follow-up file that must equal its start hash, or an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal22D start: '+str(deleted)
    for p in MODIFIED_JAVA + GENERATED + SHARED_RECORDS + REPORTS[:1] + [ACCEPTANCE_22C]: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in TOOLS: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    for p in followup_paths:
        if p not in changes: need((ROOT/p).is_file() and sha(ROOT/p) == (followup['added'] | followup['modified'])[p], 'follow-up file differs from its start hash: '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(PRODUCTION))
    need(not outside, 'src/main change outside HazardRegistry.java and HazardGameTests.java: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = []
    for p, s in sorted(changes.items()):
        entry = dict(path=p, change=s, group=group(p, followup_paths), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p))
        if p in followup_paths:
            entry['also_goal22c_followup'] = dict(owner=FOLLOWUP_OWNER, before_goal22c_sha256=followup['goal22c_after_sha256'].get(p),
                                                  after_sha256=(followup['added'] | followup['modified'])[p])
        change_list.append(entry)
    for p in followup_paths:
        if p in changes: continue
        change_list.append(dict(path=p, change='added' if p in followup_added else 'modified', group='goal22c-followup', owner=FOLLOWUP_OWNER,
                                before_sha256=followup['goal22c_after_sha256'].get(p), after_sha256=sha(ROOT/p) if (ROOT/p).is_file() else None))
    change_list.sort(key=lambda e: e['path'])
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    assert baselines_now == {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}, 'A snapshot was added or changed'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'], 'review-6a11998d5852 snapshot changed'
    production_changed = [p for p in PRODUCTION if p in changes]

    # The modified production files keep their start line endings (the frozen start copies are the baseline files).
    start_text = {}
    for p in MODIFIED_JAVA:
        if p not in changes: continue
        if not need(p in base['copied_scope'], p+' has no frozen start copy in baseline-files (not in copied_scope)'): continue
        start_text[p] = (START_FILES/p).read_bytes()
        start_eol, eol = eol_counts(start_text[p]), eol_counts((ROOT/p).read_bytes())
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0),
             f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}')

    # Production Java facts. HazardRegistry.java: insert-only against its start copy except exactly one edited line (the Frame javadoc); removed == 1 with
    # that before/after pair. HazardGameTests.java: modified (inserts plus the rewritten loop and the javadoc paragraph), counts recorded only.
    insert_summary, edit_summary, frame_edit = {}, {}, None
    if HAZARD_REGISTRY in start_text:
        start_lines, live_lines = lines_of(start_text[HAZARD_REGISTRY]), lines_of((ROOT/HAZARD_REGISTRY).read_bytes())
        old_hits, new_hits = [l for l in start_lines if FRAME_OLD in l], [l for l in live_lines if FRAME_NEW in l]
        if need(len(old_hits) == 1 and len(new_hits) == 1 and old_hits[0].replace(FRAME_OLD, FRAME_NEW) == new_hits[0],
                f'{HAZARD_REGISTRY}: the Frame javadoc line "{FRAME_OLD}" is not edited to "{FRAME_NEW}" exactly once (start hits {len(old_hits)}, now {len(new_hits)})'):
            canonical = [old_hits[0] if l == new_hits[0] else l for l in live_lines]
            inserted = insertions(start_lines, canonical)
            if need(inserted is not None, f'{HAZARD_REGISTRY} is not insert-only against the start copy apart from the Frame javadoc line (a start line was changed, moved or removed)'):
                insert_summary[HAZARD_REGISTRY] = len(inserted)
            frame_edit = dict(before=old_hits[0].strip(), after=new_hits[0].strip())
        edit_summary[HAZARD_REGISTRY] = edit_counts(start_lines, live_lines)
        need(edit_summary[HAZARD_REGISTRY]['removed'] == 1, f'{HAZARD_REGISTRY} removes {edit_summary[HAZARD_REGISTRY]["removed"]} start lines (expected exactly the Frame javadoc line)')
    if HAZARD_TESTS in start_text:
        edit_summary[HAZARD_TESTS] = edit_counts(lines_of(start_text[HAZARD_TESTS]), lines_of((ROOT/HAZARD_TESTS).read_bytes()))
    # No other production or language file changes: the language provider, en_us.json, zh_cn.json and the mapping equal their start hashes.
    for p in LANGUAGE_FILES: assert p in base['files'], 'Language file is not a start file: '+p
    need(all(sha(ROOT/p) == base['files'][p] for p in LANGUAGE_FILES),
         'language file differs from its start hash (the batch adds no key): '+str([p for p in LANGUAGE_FILES if sha(ROOT/p) != base['files'][p]]))
    # The original lines the receipt quotes (the stored blobs at the recorded commit, independent of the worktree's line endings).
    original_lines = {}
    for path in (ORIGINAL_HAZARDS, ORIGINAL_DICT, RODS):
        original_lines[path] = original_blob(path).decode('utf-8').split('\n')
    for rid, (path, line, kind, entries) in ADDENDUM.items():
        text = original_lines[path][line-1]
        assert (SHAPE_CALL.get(rid) or rid) in text, f'{path}:{line} does not name {SHAPE_CALL.get(rid) or rid}'
        if kind == 'frame': assert FRAME_CALL[line] in text, f'{path}:{line} does not carry {FRAME_CALL[line]}'
        if kind == 'item': assert 'HazardSystem.register' in text, f'{path}:{line} is not a HazardSystem.register row'
    assert all('pellet_rtg' in original_lines[ORIGINAL_HAZARDS][n-1] for n in RTG_LINES), 'The RTG pellet rows moved from HazardRegistry.java:337-347'
    for name, (path, line, token, _) in UNCHANGED_EXISTING.items(): assert token in original_lines[path][line-1], f'{path}:{line} does not name {token}'
    for token, line in (('block_fallout', 477), ('tile_lab_broken', 481)): assert token in original_lines[ORIGINAL_HAZARDS][line-1], f'HazardRegistry.java:{line} does not name {token}'
    assert 'block_white_phosphorus' in original_lines[ORIGINAL_DICT][459], 'OreDictManager.java:460 does not name block_white_phosphorus'
    assert RODS in original_lines and 'THORIUM_FUEL' in original_lines[RODS][29], 'RodRecipes.java:30 (thorium fuel rod) moved'
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}

    # 4. The generated tree: the stamp must be current and nothing is generated beyond the start (the follow-up's two JSONs are already in the start
    # stamp); language is unchanged.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    empty = dict(added=[], removed=[], changed=[])
    need(en_delta == empty, 'generated en_us.json differs from the start (no new key expected): '+json.dumps(en_delta, ensure_ascii=False))
    need(zh_delta == empty, 'zh_cn.json differs from the start (no new key expected): '+json.dumps(zh_delta, ensure_ascii=False))
    need(map_delta == empty, 'zh_cn-map.json differs from the start (no new entry expected): '+json.dumps(map_delta, ensure_ascii=False))
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    stamp_current = not stale and not mismatch and not unrecorded
    need(stamp_current, f'{STAMP} not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
    start_stamp = read(START_FILES/STAMP)
    start_generated = start_stamp['generated']
    assert len(start_generated) == prior_receipt['generated_resource_count'] + len(followup_generated), \
        'Start stamp is not the goal22c generated tree + the follow-up JSONs'
    assert all(p.removeprefix(GENERATED_ROOT) in start_generated for p in followup_generated), 'The start stamp lacks a follow-up generated file'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(not generated_changed, f'Generated resources changed since the start (only the stamp may change): {generated_changed[:8]}')
    need(not generated_added, f'Generated resources added since the start (the batch generates no resource; runData must change the stamp only): {generated_added[:8]}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    need(set(generated_since) <= {STAMP}, 'Generated files changed since the start other than the stamp: '+str([p for p in generated_since if p != STAMP][:8]))
    # The follow-up recipe, packaged first here: shapeless empty rod + 2 thorium fuel billets -> rod_zirnox with meta = THORIUM_FUEL ordinal, no life data.
    ordinals, _ = zirnox_ordinals()
    assert 'THORIUM_FUEL' in ordinals, 'ZirnoxType lacks THORIUM_FUEL'
    followup_recipe = None
    if (ROOT/GENERATED_ROOT/RECIPE_DIR/(FOLLOWUP_ROD+'.json')).is_file():
        info = recipe_summary(FOLLOWUP_ROD)
        want = {'hbmsntm:meta': ordinals['THORIUM_FUEL']}
        need(info['type'] == 'minecraft:crafting_shapeless' and info['ingredients'] == {'rod_zirnox_empty': 1, 'billet_thorium_fuel': 2}
             and info['result'] == 'rod_zirnox' and info['count'] == 1 and info['components'] == want and info['advancement_rewards'] == ['hbmsntm:'+FOLLOWUP_ROD],
             f'{info["recipe_json"]} differs from the original RodRecipes.java:30 row: {info}')
        followup_recipe = dict(id=FOLLOWUP_ROD, original=f'{RODS}:30', original_text=original_lines[RODS][29].strip(), **info)
    else: need(False, 'follow-up recipe JSON missing: '+GENERATED_ROOT+RECIPE_DIR+FOLLOWUP_ROD+'.json')
    # The mapping groups must list every changed compare-inventory path and the follow-up's new generated paths.
    unmapped = sorted(p for p in set(changes) | set(followup_paths) if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    notes = ' '.join(by_id[FEATURE_GROUP].get('notes', [])) if FEATURE_GROUP in by_id else ''
    if need(FEATURE_GROUP in by_id, 'migration/features.json has no group '+FEATURE_GROUP):
        need('Goal22D' in notes and 'RTG' in notes, f'migration/features.json group {FEATURE_GROUP} notes do not mention Goal22D and the RTG deferral')
        need(feature_matches(by_id[FEATURE_GROUP], 'target', HAZARD_REGISTRY), f'features.json group {FEATURE_GROUP} lists {HAZARD_REGISTRY} in neither target_paths nor target_watch')
    task_book = ROOT/REPORTS[0]
    book_text = task_book.read_text(encoding='utf-8') if task_book.is_file() else ''
    missing_rows = sorted(i for i in ADDENDUM if i not in book_text) + sorted(n for n in ('block_fallout', 'tile_lab_broken', 'block_white_phosphorus', 'RTG') if n not in book_text)
    need(not missing_rows, f'{REPORTS[0]} transcription table does not name: {missing_rows}')

    # The unified acceptance checklist: insert-only against its start copy, at most one edited line inside section 4.
    acceptance = None
    if ACCEPTANCE_22C in changes:
        old_bytes, new_bytes = (START_FILES/ACCEPTANCE_22C).read_bytes(), (ROOT/ACCEPTANCE_22C).read_bytes()
        old_lines, new_lines = lines_of(old_bytes), lines_of(new_bytes)
        region = sections(old_lines, ACCEPTANCE_SECTION, ACCEPTANCE_NEXT_SECTION)
        start_eol, eol = eol_counts(old_bytes), eol_counts(new_bytes)
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), f'{ACCEPTANCE_22C} line endings differ from the start: {start_eol} -> {eol}')
        if need(region is not None, f'{ACCEPTANCE_22C}: section 4 heading not found in the start copy'):
            result = edits_only(old_lines, new_lines, range(*region), 1)
            if need(result is not None, f'{ACCEPTANCE_22C} is not insert-only against its start copy (at most one edited line, inside section 4)'):
                acceptance = dict(path=ACCEPTANCE_22C, receipt_sha256=base['previous_receipt_protected_paths'][ACCEPTANCE_22C], start_sha256=base['files'][ACCEPTANCE_22C],
                                  after_sha256=sha(ROOT/ACCEPTANCE_22C), inserted_lines=result[0],
                                  edited_lines=[dict(before=o.strip(), after=[n.strip() for n in ns]) for o, ns in result[1]],
                                  explanation='The goal22c receipt hashes the Goal 22 unified acceptance checklist; Goal22D fills its section 4 (the 22D sampling steps) '
                                              'by insertion, so the goal22c receipt hash is older than the live file. Insert-only against the start copy with at most one '
                                              'edited line inside section 4.')
                need(result[0] + len(result[1]) >= 1, f'{ACCEPTANCE_22C} section 4 has no inserted line')

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
    hazard_tests_now = annotations(ROOT/HAZARD_TESTS)
    hazard_tests_start = annotations(START_FILES/HAZARD_TESTS)
    new_test_names = sorted(set(GAMETEST_METHOD.findall((ROOT/HAZARD_TESTS).read_text(encoding='utf-8'))) - set(GAMETEST_METHOD.findall((START_FILES/HAZARD_TESTS).read_text(encoding='utf-8'))))
    need(gametest_added >= 1, f'{HAZARD_TESTS} holds {hazard_tests_now} @GameTest methods, the start copy {hazard_tests_start} (expected new hazard addendum tests)')
    need(gametest_added == hazard_tests_now - hazard_tests_start, f'GameTest sources grew by {gametest_added} tests, HazardGameTests grew by {hazard_tests_now - hazard_tests_start} (another GameTest file changed?)')
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
        if not need((OUT/name).is_file(), 'evidence: build/migration/goal22d/'+name): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence: build/migration/goal22d/'+name): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence: build/migration/goal22d/'+name+' (missing or empty)'): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE:
        if not need((OUT/name).is_file(), 'start evidence missing: build/migration/goal22d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain.sh output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence: build/migration/goal22d/'+name+' (written by chain.sh final)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (both files against their start copies) and name both files.
    diff_path = OUT/'production-vs-start.diff'
    if diff_path.is_file() and diff_path.stat().st_size and all(p in start_text for p in MODIFIED_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in MODIFIED_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in MODIFIED_JAVA), 'production-vs-start.diff does not contain hunks for HazardRegistry.java and HazardGameTests.java')
    final = None
    # The suites of the goal22c final run plus the Goal22D verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert NEW_SUITE not in reference_suites, 'The Goal22D suite is already in the goal22c final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence: build/migration/goal22d/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        assert set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal22c final set + the Goal22D verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE})))
        entry = final['suites'][NEW_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, NEW_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = hazards = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence: build/migration/goal22d/'+VERIFY_REPORT+' (tools/migration/verify_goal22d_hazards.py report)'):
        report = read(OUT/VERIFY_REPORT)
        problems = verifier_problems(report, [p for p in production_changed])
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=TOOLS[0],
                        tool_sha256=sha(ROOT/TOOLS[0]) if (ROOT/TOOLS[0]).is_file() else None,
                        mutations_detected=report.get('mutations_detected', summary_part.get('mutations_detected', report.get('mutation_count'))),
                        mutations_total=summary_part.get('mutations_total', report.get('mutation_count')))
        evidence[verifier['path']] = verifier['sha256']
        # The 18 registrations and the skipped list come from the verifier report: every id must be found there with all its (type, level) pairs.
        rows = report_rows(report, set(ADDENDUM))
        unsupported = sorted(i for i, (_, _, _, entries) in ADDENDUM.items() if not row_supported(rows.get(i, []), entries))
        need(not unsupported, f'{VERIFY_REPORT} does not carry these addendum rows with their expected (type, level) pairs: {unsupported}')
        report_text = json.dumps(report, ensure_ascii=False)
        missing_skips = sorted(t for t in ('block_fallout', 'tile_lab_broken', 'block_white_phosphorus', 'pellet_rtg') if t not in report_text)
        need(not missing_skips, f'{VERIFY_REPORT} does not list the skipped identities: {missing_skips}')
        hazards = dict(
            verifier_report=verifier['path'], verifier_report_sha256=verifier['sha256'], count=len(ADDENDUM), item_rows=len(ITEM_ROWS), frame_rows=len(FRAME_ROWS),
            registrations={i: dict(original=f'{path}:{line}', kind=kind, entries=[dict(type=t, level=level) for t, level in entries],
                                   found_in_verifier_report=i in rows) for i, (path, line, kind, entries) in ADDENDUM.items()},
            skipped={k: dict(original=f'{path}:{line}', state=state, reason=reason) for k, (path, line, state, reason) in SKIPPED.items()},
            unchanged_existing={k: dict(original=f'{path}:{line}', reason=reason) for k, (path, line, _, reason) in UNCHANGED_EXISTING.items()},
            note='Levels are the float32 products of the original constants (crystal = block = 10, billet 0.5, powder 3), restated as plain numbers and '
                 'checked against the verifier report within 1e-4 relative; the verifier computes them from the original source. Registered through '
                 'HazardRegistry.registerMaterialAddendum; item-level rows without mutex like the original, frame rows with the 21D frame data.')
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree): the original unchanged, the target exactly the goal22c receipt's compare
    # target set plus the follow-up's and this batch's paths inside the compare inventory; compare never lists the stamp; no unmapped change. No new snapshot.
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'previous receipt compare target set is incomplete'
    prior_cmp = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_compare['sha256'], 'previous compare.json changed'
    assert compare_paths(prior_cmp['changes']['target']['added']) | compare_paths(prior_cmp['changes']['target']['modified']) == previous_target, \
        'previous compare.json target set differs from its receipt'
    expected_target = sorted(previous_target | {p for p in changes if in_compare_inventory(p)} | {p for p in followup_paths if in_compare_inventory(p)})
    if need((OUT/COMPARE).is_file(), 'evidence: build/migration/goal22d/'+COMPARE+' (compare against '+SNAPSHOT+'; expected target set: %d paths)' % len(expected_target)):
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
            return set(prior_compare['target_owners'].get(p, [])) | ({OWNER} if p in changes else set()) | ({FOLLOWUP_OWNER} if p in followup_paths else set())
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts,
                       target_owners={p: sorted(compare_owners(p)) for p in listed})
        evidence[compare['path']] = compare['sha256']

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned (the follow-up or goal22d).
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) not in (previous_sha, start_jar_sha), 'build/libs/hbmsntm-198A.jar is still the previous package or the follow-up start JAR (run build)'):
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
            need(en_jar == en_delta == empty and zh_jar == zh_delta == empty,
                 'JAR en_us.json or zh_cn.json differs from the previous package (no new key expected): en '+str(en_jar)+', zh '+str(zh_jar))
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
            followup_json_ok = {n: sha_bytes(jar.read(n)) == followup['added'][GENERATED_ROOT+n] for n in followup_jar['added'] if n in names}
            need(len(followup_json_ok) == len(followup_jar['added']) and all(followup_json_ok.values()),
                 'the follow-up recipe/advancement JSONs in the JAR are missing or differ from their start hashes: '+str(followup_json_ok))
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if followup_entries.get(n) == kind: owner = [FOLLOWUP_OWNER]
                elif n.endswith('.class') and owner_class(n) in PRODUCTION: owner = [OWNER]
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner: '+str(unowned))
        missing_followup = sorted(n for n, kind in followup_entries.items() if entry_owners.get(n, {}).get('owners') != [FOLLOWUP_OWNER])
        need(not missing_followup, 'the follow-up JAR entries are not all in the delta against the goal22c package: '+str(missing_followup))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        goal22d_classes = [n for n, o in entry_owners.items() if o['owners'] == [OWNER]]
        class_owners = sorted({owner_class(n) for n in goal22d_classes})
        changed_java = [p for p in PRODUCTION if p in changes]
        need(set(class_owners) == set(changed_java), 'Changed Java sources and goal22d JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == set(followup_jar['added']), 'JAR non-class delta is not exactly the follow-up recipe/advancement JSONs: extra %s, missing %s' % (
            sorted(non_class - set(followup_jar['added']))[:8], sorted(set(followup_jar['added']) - non_class)[:8]))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        for n in ('com/hbm/hazard/HazardRegistry.class', 'com/hbm/gametest/HazardGameTests.class'):
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta,
                   registrations=len(ADDENDUM), item_rows=len(ITEM_ROWS), frame_rows=len(FRAME_ROWS), skipped=sorted(SKIPPED),
                   insert_lines=insert_summary, edit_counts=edit_summary, frame_edit=frame_edit, acceptance_drift=acceptance,
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_hazard_tests=new_test_names,
                   final_suites_expected=final_expected, compare=compare['counts'] if compare else None,
                   compare_target_expected=len(expected_target), jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None,
                   jar_directory_delta=dir_delta, class_owners=class_owners, followup_jar_entries=len(followup_entries), protected_paths=len(protected),
                   old_releases_preserved=len(old_releases), preserved_release_files=len(base['old_release_files']),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different goal22d JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest == sha(JAR) and digest not in (previous_sha, start_jar_sha), 'Packaged JAR is not build/libs or is an older JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in reports}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(new_test_names)),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=start_head, planning_commit=prior_receipt['planning_commit'], commits={},
                   target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha, base_release_receipt_sha256=previous_receipt_sha,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, dirty_paths=base['dirty_paths'], dirty_files=base['dirty_files'],
                                      note='The start tree is HEAD 29702b40 (the Goal 22 planning commit on top of the Goal 21 close-out 36c6597e) plus the '
                                           'Goal22A, Goal22B and Goal22C deliveries and the Goal22C thorium fuel rod follow-up, kept uncommitted by Goal 22 '
                                           'decision 14: the dirty paths are the goal22c receipt\'s start paths and changed files at the hashes that receipt '
                                           'recorded, plus the follow-up\'s two generated JSONs and seven paths at their follow-up hashes. build/libs at the '
                                           'start is the follow-up\'s working-tree JAR (not the goal22c package); its entry delta against the goal22c '
                                           'package is exactly the follow-up\'s. Paths this batch changes again (the stamp, GOAL22D.md, the unified acceptance '
                                           'checklist and the shared records) record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[], production_unchanged_optional=[],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   goal22c_followup=dict(owner=FOLLOWUP_OWNER, record=followup['record'], added=followup['added'], modified=followup['modified'],
                                         goal22c_after_sha256=followup['goal22c_after_sha256'], start_build_sha256=start_jar_sha,
                                         jar_delta_vs_goal22c=followup_jar, recipe=followup_recipe,
                                         note='Done after the goal22c package and kept unpackaged until now; every follow-up file equals its start hash except '
                                              'the stamp and the shared records this batch changes again (changed_files carries both hashes for those).'),
                   insert_only_lines=insert_summary, edited_lines=edit_summary, hazard_registry_edited_line=frame_edit,
                   resources={},
                   hazards=hazards,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                                 unchanged_sha256={p: base['files'][p] for p in LANGUAGE_FILES}, jar_delta=language,
                                 note='No new language key: the language provider, en_us.json, zh_cn.json and the zh_cn mapping equal their start hashes.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report, acceptance_drift_explained=acceptance,
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count, added_tests=gametest_added,
                                 new_hazard_tests=new_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; HazardGameTests now also '
                                      'covers the 18 addendum rows through HazardSystem.getHazardLevelFromStack, a sample of unchanged existing entries and the '
                                      'per-tick radiation of a controlled non-player holding crystal_schrabidium; the Geiger counter, tooltips, player '
                                      'inventories and real play are not covered.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}, SNAPSHOT: sha(ROOT/SNAPSHOT),
                                    ACCEPTANCE_22C: sha(ROOT/ACCEPTANCE_22C)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, '
                            'the static and original-parsing hazard verifier with in-memory mutations, the final old-suite rerun, compare against the '
                            'review-6a11998d5852 snapshot, the independent static review and independent JAR bytes. No in-game client test was run: the Geiger '
                            'counter, the tooltips and real play with the new hazards (crystals, caesium powder, the special billets, asbestos and white '
                            'phosphorus) are unverified, as are multiplayer and a dedicated server outside the GameTest run; the unified acceptance checklist '
                            'GOAL22C-ACCEPTANCE.md (section 4 filled by this batch) and GOAL22D-ACCEPTANCE.md are written but not executed.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal22c package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


def sha_bytes(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
