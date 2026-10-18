"""Package Goal22C (plutonium/MOX/U233 fuel closure: eleven shapeless fuel alloy rows of the original MineralRecipes.java and four ZIRNOX rod
recipes of the original RodRecipes.java in NtmRecipeProvider, the FuelClosureGameTests class and the Goal 22 unified acceptance checklist)
cumulatively on the goal22b package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal22c.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal22c/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to
build/migration/goal22c/gametest-final.log (the GameTest dedicated-server log of the settled tree).

The frozen start is build/migration/goal22c/baseline.json: NEO HEAD 29702b40 plus the Goal22A and Goal22B deliveries kept UNCOMMITTED (95
dirty paths, Goal 22 decision 14). build/libs at the start equals the goal22b package byte for byte. Every change since the start is computed
from the baseline file hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash.
Several start paths (the recipe provider, the generation stamp, README, features, UPSTREAM-REVIEWS, LOCALIZATION, GOAL22.md, GOAL22C.md) are
modified again here: their before hash is the start hash, their after hash the live one. The JAR delta against the goal22b package is
attributed per entry (goal22c); any entry without an owner fails. Counts that records quote (suites, GameTests, generated resources, classes,
releases, recipes) are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the files and the
baseline, not from literals. The batch adds no language key: the language provider, en_us.json, zh_cn.json and the zh_cn mapping must equal
their start hashes.

The receipts that hash records (goal21a..goal21d, the review-g21d-hazard-fix receipt, goal22a and goal22b) were written before the Goal 21
in-game acceptance appended its result lines to the acceptance checklists and before the O1 record notes; those records already differ from
their older receipt hashes at the frozen start (baseline older_receipt_evidence_drift; the goal22b receipt records their start hash,
previous_receipt_evidence_drift is empty). They are listed in the receipt as start drift (receipt hashes, start hash, current hash) and must
still equal their start hash; no receipt is rewritten and no other protected path may drift."""
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
from package_goal22b import (OUT as GOAL22B_OUT, BASELINE as GOAL22B_BASELINE, protected_paths as goal22b_protected_paths, receipt_protected,
                             start_drift_paths, git_ro, original_blob, edit_counts, stale_diff, verifier_problems, AUDITS, LOGS, FILES, CHAIN_FILES,
                             CHAIN_COMMANDS, GAMETEST, GAMETEST_ANNOTATION, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)

OUT = ROOT/'build/migration/goal22c'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL22B_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL22B_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal22b/hbmsntm-198A-goal22b.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal22c'
RELEASE_NAME = 'hbmsntm-198A-goal22c.jar'
OWNER = 'goal22c'
J = 'src/main/java/com/hbm/'
GENERATED_ROOT = 'src/generated/resources/'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
# Production (owner goal22c), NEW: the GameTest class. MODIFIED: the recipe provider, insert-only against its start copy.
NEW_JAVA = [J+'gametest/FuelClosureGameTests.java']
MODIFIED_JAVA = [J+'datagen/NtmRecipeProvider.java']
(FUEL_TESTS,) = NEW_JAVA
(RECIPE_PROVIDER,) = MODIFIED_JAVA
STRICT_INSERT_ONLY = [RECIPE_PROVIDER]
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA
PRODUCTION = PRODUCTION_JAVA
GENERATED = [STAMP]
TOOLS = ['tools/migration/verify_goal22c_fuel.py', 'tools/migration/package_goal22c.py']
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal22c-* or GOAL22C-* record is hashed as well.
REPORTS = ['migration/GOAL22C.md', 'migration/GOAL22C-ACCEPTANCE.md', 'migration/goal22c-static-review.md']
BATCH_RECORD = re.compile(r'migration/(goal22c-[^/]+\.(json|md)|GOAL22C-[^/]+\.md)')
SHARED_RECORDS = ['migration/GOAL22.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md']
NAMES_RELEASE = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
# The batch adds no language key: these must equal their start hashes (the language provider is not copied into baseline-files).
PROVIDER = J+'datagen/NtmLanguageProvider.java'
LANGUAGE_FILES = [PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD]
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = NEW_JAVA + MODIFIED_JAVA + GENERATED + TOOLS + REPORTS + SHARED_RECORDS
# The fifteen new recipes (handoff, GOAL22C.md C1): id -> (original references, ingredient multiset, result item, result count).
MINERAL = 'src/main/java/com/hbm/crafting/MineralRecipes.java'
RODS = 'src/main/java/com/hbm/crafting/RodRecipes.java'
ALLOY = {
    'billet_thorium_fuel_from_billets': ([(MINERAL, 156)], {'billet_th232': 5, 'billet_u233': 1}, 'billet_thorium_fuel', 6),
    'billet_thorium_fuel_from_nuggets': ([(MINERAL, 157)], {'nugget_th232': 5, 'nugget_u233': 1}, 'billet_thorium_fuel', 1),
    'billet_uranium_fuel_from_billets': ([(MINERAL, 159)], {'billet_u238': 5, 'billet_u235': 1}, 'billet_uranium_fuel', 6),
    'billet_uranium_fuel_from_nuggets': ([(MINERAL, 160)], {'nugget_u238': 5, 'nugget_u235': 1}, 'billet_uranium_fuel', 1),
    'billet_plutonium_fuel_from_billets': ([(MINERAL, 162)], {'billet_u238': 2, 'billet_pu_mix': 1}, 'billet_plutonium_fuel', 3),
    'billet_plutonium_fuel_from_nuggets': ([(MINERAL, 163)], {'nugget_pu_mix': 2, 'nugget_u238': 4}, 'billet_plutonium_fuel', 1),
    'billet_pu_mix_from_billets': ([(MINERAL, 165)], {'billet_pu239': 2, 'billet_pu240': 1}, 'billet_pu_mix', 3),
    'billet_pu_mix_from_nuggets': ([(MINERAL, 166)], {'nugget_pu239': 4, 'nugget_pu240': 2}, 'billet_pu_mix', 1),
    'billet_mox_fuel_from_billets': ([(MINERAL, 177)], {'billet_uranium_fuel': 2, 'billet_pu239': 1}, 'billet_mox_fuel', 3),
    'billet_mox_fuel_from_nuggets': ([(MINERAL, 178)], {'nugget_pu239': 2, 'nugget_uranium_fuel': 4}, 'billet_mox_fuel', 1),
    # The original writes "nuggetPluonium240" (an ore name nothing registers), so :419 itself never matches (its "tiny" duplicate :420 does);
    # NEO uses the intended nugget_pu240.
    'ingot_pu_mix_from_nuggets': ([(MINERAL, 419)], {'nugget_pu239': 6, 'nugget_pu240': 3}, 'ingot_pu_mix', 1),
}
# Rods: id -> (original reference, ZirnoxType constant, ingredient multiset); output rod_zirnox with meta = ZirnoxType ordinal, count 1, no life data.
RODS_RECIPES = {
    'rod_zirnox_mox_fuel': ((RODS, 31), 'MOX_FUEL', {'rod_zirnox_empty': 1, 'billet_mox_fuel': 2}),
    'rod_zirnox_plutonium_fuel': ((RODS, 32), 'PLUTONIUM_FUEL', {'rod_zirnox_empty': 1, 'billet_plutonium_fuel': 2}),
    'rod_zirnox_u233_fuel': ((RODS, 33), 'U233_FUEL', {'rod_zirnox_empty': 1, 'billet_u233': 2}),
    'rod_zirnox_zfb_mox': ((RODS, 37), 'ZFB_MOX', {'rod_zirnox_empty': 1, 'billet_mox_fuel': 1, 'billet_zirconium': 1}),
}
RECIPE_IDS = list(ALLOY) + list(RODS_RECIPES)
RECIPE_DIR = 'data/hbmsntm/recipe/'
ADVANCEMENT_DIR = 'data/hbmsntm/advancement/recipes/misc/'
# The 30 generated files the batch adds (stamp-relative names), and the same under src/generated/resources.
EXPECTED_GENERATED = sorted([RECIPE_DIR+i+'.json' for i in RECIPE_IDS] + [ADVANCEMENT_DIR+i+'.json' for i in RECIPE_IDS])
EXPECTED_GENERATED_PATHS = {GENERATED_ROOT+p for p in EXPECTED_GENERATED}
ZIRNOX_ROD_ITEM = J+'items/machine/ZirnoxRodItem.java'
FEATURE_GROUPS = ['zirnox-reactor', 'spent-fuel']
# Indexed by the receipt as evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start:
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'chain.sh', 'handoff-tests.md', 'handoff-packaging.md')
GAMETEST_LOG = 'build/migration/goal22c/gametest-final.log'
NEW_SUITE = 'verify_goal22c_fuel.py --gametest-log build/migration/goal22c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
TYPO_MARK = 'nuggetPluonium240'


def scope_text(alloy, rods):
    return (f'Goal22C (plutonium/MOX/U233 fuel closure): {len(alloy)+len(rods)} new crafting recipes in NtmRecipeProvider (insert-only, nothing else in the '
            f'production tree changes except the new FuelClosureGameTests class): {len(alloy)} shapeless fuel alloy rows of the original MineralRecipes.java '
            f'(:156,157 billet_thorium_fuel from billets and from nuggets; :159,160 billet_uranium_fuel; :162,163 billet_plutonium_fuel; :165,166 '
            f'billet_pu_mix, the reactor-grade plutonium billet; :177,178 billet_mox_fuel; :419 ingot_pu_mix from 6 nugget_pu239 + 3 nugget_pu240) and '
            f'{len(rods)} ZIRNOX rod recipes of the original RodRecipes.java (:31 MOX, :32 plutonium, :33 U233, :37 ZFB MOX; empty rod + billets, output '
            f'rod_zirnox with meta = ZirnoxType ordinal, count 1, no life data), with the {len(alloy)+len(rods)} generated recipe and '
            f'{len(alloy)+len(rods)} advancement JSONs. The original :419 row writes "{TYPO_MARK}", an ore name nothing registers, so that row never matches '
            f'in the original, while its "tiny" duplicate :420 crafts the same ingot from the same nuggets; NEO uses the intended nugget_pu240 (same effective '
            f'result), the typo recorded as upstream-shared. Deferred and recorded: the LES rod (RodRecipes.java:35, billet_les has no survival source) and '
            f'the lithium rod (:36, NEO has no lithium ingot). Not ported because redundant: the "tiny" alloy rows (MineralRecipes.java:158,161,164,167,420; '
            f'the original registers every nugget under both nugget<Mat> and tiny<Mat>, OreDictManager.java:839, so they repeat the nugget rows). Unchanged: the ZIRNOX reactor, '
            f'ZirnoxRodItem, hazards, PUREX, the spent-fuel pool, every registry ID and all language (no new key; the language provider, en_us.json, '
            f'zh_cn.json and the zh_cn mapping equal their start hashes). With these recipes natural-uranium cold waste processed by PUREX closes into '
            f'plutonium, MOX and U233 fuel and ZIRNOX rods, and the thorium fuel billet gets its first survival source. The batch also writes the Goal 22 '
            f'unified in-game acceptance checklist migration/GOAL22C-ACCEPTANCE.md (not executed).')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal22c release directory: '+rel


def protected_paths(base):
    """What the goal22b packager protected (built there from the Goal21A..Goal22A starts and receipts), plus every path the goal22b receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 22C baseline lists the goal22a receipt among them) and every
    release file of the frozen start. The records that already drifted at the start are pinned at their start hash (baseline files) instead of any
    receipt hash; the goal22b packager pinned the same records at the goal22b start hash, which must be equal. One path never carries two hashes."""
    out = dict(goal22b_protected_paths(read(GOAL22B_BASELINE)))
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'], 'Start drift path is not a frozen file: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    for p in drift:
        assert out.get(p, base['files'][p]) == base['files'][p], 'The goal22b start pinned another hash for '+p
        out.pop(p, None)
        out[p] = base['files'][p]
    return out


def start_drift_report(base):
    """{path: {receipts: {label: hash}, start_sha256, current_sha256}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal22b receipt'] = base['previous_receipt_protected_paths'][p]
        start = base['files'][p]
        newest = receipts.get('goal22b receipt')
        out[p] = dict(receipt_hashes=receipts, start_sha256=start, current_sha256=sha(ROOT/p),
                      explanation=('Appended to after its older receipt(s) were written (Goal 21 in-game acceptance result lines or the O1 record notes); the '
                                   'newest receipt that hashes it'+(' (goal22b) records the start hash' if newest == start else ' is older than the start')+
                                   '. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.'))
    return out


def group(p):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA: return 'production'
    if p == STAMP or p in EXPECTED_GENERATED_PATHS: return 'generated'
    if p in TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    return None


def zirnox_ordinals():
    """{constant: ordinal} of NEO's ZirnoxRodItem.ZirnoxType (the meta of the rod_zirnox stack), and {constant: heat}."""
    text = (ROOT/ZIRNOX_ROD_ITEM).read_text(encoding='utf-8')
    body = re.search(r'enum ZirnoxType \{(.*?);', text, re.S).group(1)
    constants = re.findall(r'^\s*([A-Z0-9_]+)\((\d[\d_]*),\s*(\d+)', body, re.M)
    return {n: i for i, (n, _, _) in enumerate(constants)}, {n: int(h) for n, _, h in constants}


def item_name(ref):
    return ref['item'] if 'item' in ref else '#'+ref['tag']


def recipe_summary(rid):
    """Facts of one generated recipe JSON: type, ingredient multiset, result item/count/components, plus the advancement's recipe reward."""
    recipe, advancement = ROOT/GENERATED_ROOT/RECIPE_DIR/(rid+'.json'), ROOT/GENERATED_ROOT/ADVANCEMENT_DIR/(rid+'.json')
    data = read(recipe)
    ingredients = Counter(item_name(i).removeprefix('hbmsntm:') for i in data.get('ingredients', []))
    result = data.get('result', {})
    summary = dict(type=data.get('type'), ingredients=dict(sorted(ingredients.items())), result=result.get('id', '').removeprefix('hbmsntm:'),
                   count=result.get('count'), components=result.get('components', {}), recipe_json=recipe.relative_to(ROOT).as_posix(),
                   recipe_sha256=sha(recipe), advancement_json=advancement.relative_to(ROOT).as_posix(),
                   advancement_sha256=sha(advancement) if advancement.is_file() else None,
                   advancement_rewards=read(advancement).get('rewards', {}).get('recipes') if advancement.is_file() else None)
    return summary


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

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal22C commits nothing), the recorded start content.
    start_head = prior_receipt['target_start_commit']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at 6a11998d'
    assert base['target_head'] == start_head == prior_receipt['target_head_at_packaging'], 'The frozen start is not the goal22b start commit'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal22C: '+head
    assert set(base['start_content']) == {'committed', 'uncommitted'}, 'Baseline start content differs'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a'}, \
        'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['dirty_paths'] == len(base['dirty_paths']) and startup['frozen_file_hashes'] == len(base['files']) \
        and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['previous_jar_sha256'] == base['previous_release']['sha256'] and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'], \
        'startup-verification.json differs from baseline.json'
    # The start tree is the goal22a + goal22b delivery, uncommitted: its dirty paths are the goal22b receipt's start paths and changed files, each at the
    # hash the goal22b receipt recorded (the after hash for a changed file, the receipt's own start hash for a path goal22b left alone).
    receipt_changed = {c['path']: c for c in prior_receipt['changed_files']}
    receipt_start = prior_receipt['start_content']['dirty_files']
    assert sorted(base['dirty_paths']) == sorted(set(receipt_start) | set(receipt_changed)), 'The start dirty paths are not the goal22b start paths + changed files'
    for p in base['dirty_paths']:
        expected = receipt_changed[p]['after_sha256'] if p in receipt_changed else receipt_start[p]
        assert base['files'][p] == base['dirty_files'][p] == expected, 'The start copy of a goal22a/goal22b path differs from the goal22b receipt: '+p
    assert base['build_libs_vs_previous'] == dict(added=[], removed=[], modified=[]), 'build/libs at the start is not the previous package byte for byte'
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal22b package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the start is not the previous package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal22b receipt list + the goal22b package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal22b receipt count + the goal22b release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal22b receipt'
    assert base['previous_receipt_evidence_drift'] == [], 'The goal22b receipt evidence had already drifted at the start'
    protected = protected_paths(base)
    drift_report = start_drift_report(base)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal22b receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal22c. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal22C start that the owner table does not list (production outside the handoff list, a generated file '
         'other than the stamp and the 30 recipe/advancement JSONs, or an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal22C start: '+str(deleted)
    for p in MODIFIED_JAVA + GENERATED + SHARED_RECORDS + REPORTS[:1]: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + TOOLS + sorted(EXPECTED_GENERATED_PATHS): assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(PRODUCTION))
    need(not outside, 'src/main change outside the production list: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p))
                   for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    assert baselines_now == {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}, 'A snapshot was added or changed'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'], 'review-6a11998d5852 snapshot changed'
    production_changed = [p for p in PRODUCTION if p in changes]

    # The modified production file keeps its start line endings (the frozen start copy is the baseline file); the new Java file is not mixed.
    start_text = {}
    for p in MODIFIED_JAVA:
        if p not in changes: continue
        if not need(p in base['copied_scope'], p+' has no frozen start copy in baseline-files (not in copied_scope)'): continue
        start_text[p] = (START_FILES/p).read_bytes()
        start_eol, eol = eol_counts(start_text[p]), eol_counts((ROOT/p).read_bytes())
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0),
             f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}')
    for p in NEW_JAVA:
        if (ROOT/p).is_file():
            eol = eol_counts((ROOT/p).read_bytes())
            need(eol[0] == 0 or eol[1] == 0, f'{p} mixes CRLF and LF line endings: {eol}')

    # Production Java facts: the recipe provider is insert-only (removed lines must be 0).
    insert_summary, edit_summary = {}, {}
    for p in STRICT_INSERT_ONLY:
        if p not in start_text: continue
        inserted = insertions(lines_of(start_text[p]), lines_of((ROOT/p).read_bytes()))
        if need(inserted is not None, p+' is not insert-only against the start copy (a start line was changed, moved or removed)'): insert_summary[p] = len(inserted)
    for p in MODIFIED_JAVA:
        if p in start_text:
            edit_summary[p] = edit_counts(lines_of(start_text[p]), lines_of((ROOT/p).read_bytes()))
            need(edit_summary[p]['removed'] == 0, f'{p} removes {edit_summary[p]["removed"]} start lines (insert-only)')
    # No other production or language file changes: the language provider, en_us.json, zh_cn.json and the mapping equal their start hashes.
    for p in LANGUAGE_FILES: assert p in base['files'], 'Language file is not a start file: '+p
    need(all(sha(ROOT/p) == base['files'][p] for p in LANGUAGE_FILES),
         'language file differs from its start hash (the batch adds no key): '+str([p for p in LANGUAGE_FILES if sha(ROOT/p) != base['files'][p]]))
    rods_ordinal, rods_heat = zirnox_ordinals()
    for _, constant, _ in RODS_RECIPES.values(): assert constant in rods_ordinal, 'ZirnoxType lacks '+constant
    u233_heat = rods_heat['U233_FUEL']
    assert u233_heat == max(rods_heat[c] for _, c, _ in RODS_RECIPES.values()), 'The U233 rod is not the hottest of the new rods'
    # The original lines the receipt quotes (the stored blobs at the recorded commit, independent of the worktree's line endings).
    original_lines = {}
    for path in (MINERAL, RODS):
        original_lines[path] = original_blob(path).decode('utf-8').split('\n')
    for rid, (refs, _, result, _) in ALLOY.items():
        for path, line in refs: assert result in original_lines[path][line-1], f'{path}:{line} does not name {result}'
    for rid, ((path, line), constant, _) in RODS_RECIPES.items():
        assert constant in original_lines[path][line-1], f'{path}:{line} does not name {constant}'
    assert TYPO_MARK in original_lines[MINERAL][419-1], 'The original :419 row no longer carries the typo '+TYPO_MARK
    for path, line in (('src/main/java/com/hbm/crafting/RodRecipes.java', 35), ('src/main/java/com/hbm/crafting/RodRecipes.java', 36)):
        assert any(c in original_lines[path][line-1] for c in ('LES_FUEL', 'LITHIUM')), 'Deferred rod line moved: '+str(line)
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}

    # 4. The generated tree: the stamp must be current and the added files exactly the 15 recipes and 15 advancements; language is unchanged.
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the previous generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(not generated_changed, f'Generated resources changed since the start (only the 30 additions are expected): {generated_changed[:8]}')
    need(generated_added == EXPECTED_GENERATED, f'Stamp-recorded generated additions are not the 15 recipe and 15 advancement JSONs: extra '
         f'{sorted(set(generated_added) - set(EXPECTED_GENERATED))[:6]}, missing {sorted(set(EXPECTED_GENERATED) - set(generated_added))[:6]}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    tree_added = sorted(p for p in generated_since if p != STAMP and changes[p] == 'added')
    need(sorted(GENERATED_ROOT+p for p in generated_added) == tree_added,
         'Stamp-recorded generated additions differ from the generated files added since the start: stamp %s, tree %s' % (generated_added[:6], tree_added[:6]))
    need(sorted(p for p in generated_since if p != STAMP and changes[p] == 'modified') == [], 'Generated files modified since the start: '+str(
        [p for p in generated_since if p != STAMP and changes[p] == 'modified'][:6]))
    need(set(tree_added) == EXPECTED_GENERATED_PATHS, f'Generated files added in the tree are not the expected 30: extra {sorted(set(tree_added) - EXPECTED_GENERATED_PATHS)[:6]}, '
         f'missing {sorted(EXPECTED_GENERATED_PATHS - set(tree_added))[:6]}')
    recipes = {}
    if all((ROOT/p).is_file() for p in EXPECTED_GENERATED_PATHS):
        for rid in RECIPE_IDS:
            info = recipe_summary(rid)
            if rid in ALLOY:
                refs, ingredients, result, count = ALLOY[rid]
                original = [f'{path}:{line}' for path, line in refs]
                want_components = {}
            else:
                (path, line), constant, ingredients = RODS_RECIPES[rid]
                result, count, original = 'rod_zirnox', 1, [f'{path}:{line}']
                want_components = {'hbmsntm:meta': rods_ordinal[constant]}
            need(info['type'] == 'minecraft:crafting_shapeless' and info['ingredients'] == ingredients and info['result'] == result and info['count'] == count
                 and info['components'] == want_components,
                 f'{info["recipe_json"]} differs from the original row {original}: type {info["type"]}, ingredients {info["ingredients"]}, result '
                 f'{info["result"]} x{info["count"]} {info["components"]}; expected shapeless {ingredients} -> {result} x{count} {want_components}')
            need(info['advancement_rewards'] == ['hbmsntm:'+rid], f'{info["advancement_json"]} does not reward hbmsntm:{rid}: {info["advancement_rewards"]}')
            recipes[rid] = dict(kind='alloy' if rid in ALLOY else 'zirnox_rod', original=original,
                                original_text=[original_lines[p][int(n)-1].strip() for p, n in (o.rsplit(':', 1) for o in original)], **info)
        recipes['ingot_pu_mix_from_nuggets']['note'] = (f'The original :419 row writes "{TYPO_MARK}" (no such ore name), so that row never matches in the original; '
                                                      'its "tiny" duplicate :420 crafts the same ingot. NEO uses the intended nugget_pu240 (upstream-shared typo).')
    else:
        need(False, 'generated recipe or advancement JSONs missing (runData): '+str(sorted(p for p in EXPECTED_GENERATED_PATHS if not (ROOT/p).is_file())[:6]))
    # The mapping groups must list the new generated paths (and every changed compare-inventory path must map to some group).
    for gid in FEATURE_GROUPS:
        if need(gid in by_id, 'migration/features.json has no group '+gid):
            missing = sorted(p for p in EXPECTED_GENERATED_PATHS if not feature_matches(by_id[gid], 'target', p))
            need(not missing, f'features.json group {gid} lacks {len(missing)} of the 30 new generated paths in target_paths/target_watch: {missing[:4]}')
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))

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
    fuel_tests = annotations(ROOT/FUEL_TESTS) if (ROOT/FUEL_TESTS).is_file() else 0
    need(fuel_tests >= 1, f'{FUEL_TESTS} holds {fuel_tests} @GameTest methods (expected the fuel closure suite)')
    need(gametest_added == fuel_tests, f'GameTest sources grew by {gametest_added} tests, FuelClosureGameTests holds {fuel_tests} (another GameTest file changed?)')
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
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence: build/migration/goal22c/'+name): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence: build/migration/goal22c/'+name): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence: build/migration/goal22c/'+name+' (missing or empty)'): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE:
        if not need((OUT/name).is_file(), 'start evidence missing: build/migration/goal22c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain.sh output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if (OUT/name).is_file(): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (the provider against its start copy, the new Java file in full).
    diff_path = OUT/'production-vs-start.diff'
    if diff_path.is_file() and diff_path.stat().st_size and all((ROOT/p).is_file() for p in NEW_JAVA):
        message = stale_diff(diff_path.read_text(encoding='utf-8-sig'), [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
    final = None
    # The suites of the goal22b final run plus the Goal22C verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert NEW_SUITE not in reference_suites, 'The Goal22C suite is already in the goal22b final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence: build/migration/goal22c/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        assert set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal22b final set + the Goal22C verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE})))
        entry = final['suites'][NEW_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, NEW_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence: build/migration/goal22c/'+VERIFY_REPORT+' (tools/migration/verify_goal22c_fuel.py report)'):
        report = read(OUT/VERIFY_REPORT)
        problems = verifier_problems(report, [p for p in production_changed])
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=TOOLS[0],
                        tool_sha256=sha(ROOT/TOOLS[0]) if (ROOT/TOOLS[0]).is_file() else None,
                        mutations_detected=report.get('mutations_detected', summary_part.get('mutations_detected', report.get('mutation_count'))),
                        mutations_total=summary_part.get('mutations_total', report.get('mutation_count')))
        evidence[verifier['path']] = verifier['sha256']
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree): the original unchanged, the target exactly the goal22b receipt's compare
    # target set plus this batch's paths inside the compare inventory; compare never lists the stamp; no unmapped change. No new snapshot.
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'previous receipt compare target set is incomplete'
    prior_cmp = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_compare['sha256'], 'previous compare.json changed'
    assert compare_paths(prior_cmp['changes']['target']['added']) | compare_paths(prior_cmp['changes']['target']['modified']) == previous_target, \
        'previous compare.json target set differs from its receipt'
    expected_target = sorted(previous_target | {p for p in changes if in_compare_inventory(p)})
    if need((OUT/COMPARE).is_file(), 'evidence: build/migration/goal22c/'+COMPARE+' (compare against '+SNAPSHOT+'; expected target set: %d paths)' % len(expected_target)):
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

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned (goal22c).
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) not in (previous_sha, start_jar_sha), 'build/libs/hbmsntm-198A.jar is still the previous package (run build)'):
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
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if n.endswith('.class'):
                    if owner_class(n) in PRODUCTION_JAVA: owner = [OWNER]
                elif GENERATED_ROOT+n in EXPECTED_GENERATED_PATHS and kind == 'added':
                    owner = [OWNER]
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'Unowned JAR change: '+str(unowned))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) == set(changed_java), 'Changed Java sources and changed JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == set(EXPECTED_GENERATED), 'JAR non-class delta is not the 30 generated recipe/advancement JSONs: extra %s, missing %s' % (
            sorted(non_class - set(EXPECTED_GENERATED))[:8], sorted(set(EXPECTED_GENERATED) - non_class)[:8]))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        need('com/hbm/datagen/NtmRecipeProvider.class' in jar_delta['modified'], 'com/hbm/datagen/NtmRecipeProvider.class is not a modified JAR class')
        need('com/hbm/gametest/FuelClosureGameTests.class' in jar_delta['added'], 'com/hbm/gametest/FuelClosureGameTests.class is not an added JAR class')
        added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
        removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
        need(bool(classes) and len(classes) == prior_receipt['compiled_classes_verified'] + added_classes - removed_classes,
             f'Compiled class count {len(classes)} is not the previous count {prior_receipt["compiled_classes_verified"]} +{added_classes} -{removed_classes}')
        language = dict(en=en_jar, zh=zh_jar)

    # 7. Records: the release name and the batch reports.
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    for p in unnamed: need(False, 'record does not name '+RELEASE_NAME+': '+p)
    need(TYPO_MARK in (ROOT/'migration/UPSTREAM-REVIEWS.md').read_text(encoding='utf-8'), 'migration/UPSTREAM-REVIEWS.md does not record the upstream typo '+TYPO_MARK+' (MineralRecipes.java:419)')
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added),
                   generated_modified=generated_changed, start_drift=sorted(drift_report), en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta,
                   recipes=len(recipes), alloy_rows=len(ALLOY), rod_recipes=len(RODS_RECIPES), insert_lines=insert_summary, edit_counts=edit_summary,
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, fuel_tests=fuel_tests,
                   final_suites_expected=final_expected, compare=compare['counts'] if compare else None,
                   compare_target_expected=len(expected_target), jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None,
                   jar_directory_delta=dir_delta, class_owners=class_owners, protected_paths=len(protected), old_releases_preserved=len(old_releases),
                   preserved_release_files=len(base['old_release_files']), older_checklist_drift_explained=sorted(explained),
                   jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different goal22c JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest == sha(JAR) and digest not in (previous_sha, start_jar_sha), 'Packaged JAR is not build/libs or is an older JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in reports}
    radiation = (f'Goal22C: the new alloy and rod recipes turn PUREX products (plutonium, uranium-233 nuggets) into MOX, plutonium and U233 fuel billets and '
                 f'ZIRNOX rods; all of them are radioactive and the U233 rod is the hottest ZIRNOX fuel (heat {u233_heat} per tick and neighbour step). Craft '
                 f'and run them only in separately authorized disposable worlds. ')
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(ALLOY, RODS_RECIPES),
                   radiation_warning=radiation+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=start_head, planning_commit=prior_receipt['planning_commit'], commits={},
                   target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha, base_release_receipt_sha256=previous_receipt_sha,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, dirty_paths=base['dirty_paths'], dirty_files=base['dirty_files'],
                                      note='The start tree is HEAD 29702b40 (the Goal 22 planning commit on top of the Goal 21 close-out 36c6597e) plus the '
                                           'Goal22A and Goal22B deliveries, kept uncommitted by Goal 22 decision 14: the dirty paths are the goal22b receipt\'s '
                                           'start paths and changed files at the hashes that receipt recorded, and build/libs at the start is the goal22b '
                                           'package byte for byte. Paths this batch changes again (the recipe provider, the stamp, GOAL22C.md and the shared '
                                           'records) record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA if p in changes],
                   production_unchanged_optional=[],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary,
                   resources={}, imported_resources={},
                   recipes=dict(count=len(recipes), alloy=len(ALLOY), zirnox_rods=len(RODS_RECIPES), original_files=[MINERAL, RODS], entries=recipes,
                                deferred=dict(zirnox_rods=['LES_FUEL (RodRecipes.java:35)', 'LITHIUM (RodRecipes.java:36)'],
                                              redundant_tiny_alias_rows='MineralRecipes.java:158,161,164,167,420 (tiny<Mat> is the nugget alias, '
                                                                        'OreDictManager.java:839; not ported)'),
                                note='Insert-only in NtmRecipeProvider; the rod outputs carry the rod_zirnox meta (ZirnoxType ordinal) and no life data; '
                                     'the :419 row uses the intended nugget_pu240 because the original ore name is a typo (upstream-shared).'),
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                                 unchanged_sha256={p: base['files'][p] for p in LANGUAGE_FILES}, jar_delta=language,
                                 note='No new language key: the language provider, en_us.json, zh_cn.json and the zh_cn mapping equal their start hashes.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count, added_tests=gametest_added,
                                 fuel_closure_tests=fuel_tests,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; FuelClosureGameTests covers '
                                      'the recipe registry entries and the crafting matches of the fifteen new recipes, the ZIRNOX heat/life/depletion of the '
                                      'new rods and the PUREX-to-rod recipe closure; the crafting table and JEI display, the Chinese UI and a real '
                                      'ZIRNOX run in a world are not covered.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, '
                            'the static, generated-tree and JAR verifier with mutations, the final old-suite rerun, compare against the review-6a11998d5852 '
                            'snapshot and independent JAR bytes. No client, real save, multiplayer or in-game test was run: the workbench and JEI display of the '
                            'new recipes, the Chinese UI, a real ZIRNOX run with the MOX, plutonium and U233 rods and the radiation of the new billets and rods '
                            'are unverified in game; the unified acceptance checklist GOAL22C-ACCEPTANCE.md is written but not executed.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal22b package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
