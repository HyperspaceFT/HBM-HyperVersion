"""Package Goal22A (Goal 21 close-out remainders: English and Chinese names and creative-tab entries for the nine registered but unnamed
ore blocks, the Chinese name of powder_co60_tiny, six smelting recipes, five appended crystallizer rows, the OilBubbleFeature far-chunk write
guard, SmokeGameTests) cumulatively on the review-g21d-hazard-fix package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal22a.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal22a/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to
build/migration/goal22a/gametest-final.log (the GameTest dedicated-server log of the settled tree).

The frozen start is build/migration/goal22a/baseline.json: NEO HEAD 29702b40 (the Goal 22 planning commit on top of the Goal 21 close-out
36c6597e) with a clean worktree. Every change since the start is computed from the baseline file hashes (not from git diff) and must be in the
owner table below; every other path must still equal its start hash. build/libs at the start is the small-fix build: the review-g21d-hazard-fix
package plus exactly the classes of the D1 and O2 small fixes, which are committed in 36c6597e and in no package; this receipt attributes them
(small-fix-D1, small-fix-O2). The JAR delta against the review-g21d-hazard-fix package is attributed per entry (goal22a, small-fix-D1,
small-fix-O2); any entry without an owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases,
language keys, crystallizer rows) are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the
files and the baseline, not from literals.

The receipts that hash records (goal21a..goal21d and the fix receipt) were written before the Goal 21 in-game acceptance appended its result
lines to the acceptance checklists and before the O1 record notes; those records already differ from their receipt hashes at the frozen start
(baseline previous_receipt_evidence_drift and older_receipt_evidence_drift). They are listed in the receipt as start drift (receipt hashes,
start hash, current hash) and must still equal their start hash; no receipt is rewritten and no other protected path may drift."""
from collections import Counter
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
from package_goal21d import (LOCALIZATION_RECORD, STAMP, EN, SNAPSHOT, SOURCE_HEAD, ZH_ENTRY, EN_ENTRY, lang_delta, compare_paths, lines_of,
                             eol_counts, insertions, in_compare_inventory, changed_since_start)
from package_review_g21d_hazard_fix import BASELINE as FIX_BASELINE, PREVIOUS_RECEIPT as GOAL21D_RECEIPT, protected_paths as fix_protected_paths

OUT = ROOT/'build/migration/goal22a'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
FIX_OUT = ROOT/'build/migration/review-fixes-g21d-hazard'
REFERENCE_FIX = FIX_OUT/'final/summary.json'
PREVIOUS_COMPARE = FIX_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/review-g21d-hazard-fix-20261017/hbmsntm-198A-g21d-hazard-fix.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal22a'
RELEASE_NAME = 'hbmsntm-198A-goal22a.jar'
START_HEAD = '29702b40e1212b95c81fa730d13e33bd69109a7f'
CLOSEOUT_HEAD = '36c6597e131e47dd90763d11c0f5a7c4d439fbdf'
OWNER = 'goal22a'
SMALL_OWNERS = {'D1': 'small-fix-D1', 'O2': 'small-fix-O2'}
J = 'src/main/java/com/hbm/'
GENERATED_ROOT = 'src/generated/resources/'
# Production (owner goal22a): six Java sources, the Chinese file and the zh_cn mapping.
PRODUCTION_JAVA = [J+'datagen/NtmLanguageProvider.java', J+'datagen/NtmRecipeProvider.java', J+'inventory/NtmCreativeTabs.java',
                   J+'inventory/recipes/CrystallizerRecipes.java', J+'world/feature/OilBubbleFeature.java', J+'gametest/SmokeGameTests.java']
PROVIDER, RECIPE_PROVIDER, CREATIVE_TABS, CRYSTALLIZER, OIL, SMOKE = PRODUCTION_JAVA
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
PRODUCTION = PRODUCTION_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]
GENERATED = [STAMP, EN]
TOOLS = ['tools/migration/verify_goal22a_closeout.py', 'tools/migration/package_goal22a.py']
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal22a-* or GOAL22A-* record is hashed as well.
REPORTS = ['migration/GOAL22A.md', 'migration/GOAL22A-ACCEPTANCE.md', 'migration/goal22a-localization-review.json', 'migration/goal22a-static-review.md']
BATCH_RECORD = re.compile(r'migration/(goal22a-[^/]+\.(json|md)|GOAL22A-[^/]+\.md)')
SHARED_RECORDS = ['migration/GOAL22.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md']
NAMES_RELEASE = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
# The nine registered but unnamed ore blocks, in the creative-tab and provider order of the task book, and the Chinese-only item.
NINE = ['ore_schrabidium', 'ore_nether_uranium', 'ore_nether_uranium_scorched', 'ore_nether_plutonium', 'ore_nether_schrabidium', 'ore_tikite',
        'ore_gneiss_uranium', 'ore_gneiss_uranium_scorched', 'ore_gneiss_schrabidium']
POWDER = 'item.hbmsntm.powder_co60_tiny'
POWDER_ZH = '小撮钴-60粉'
# Original SmeltingRecipes.java:32-35 and :56-57 -> (input block, result item); the NEO experience stays 0.7F (original 6.0F, 12.0F, 24.0F).
SMELTING = [('ore_uranium_scorched', 'ingot_uranium'), ('ore_nether_uranium', 'ingot_uranium'), ('ore_nether_uranium_scorched', 'ingot_uranium'),
            ('ore_nether_plutonium', 'ingot_plutonium'), ('ore_gneiss_uranium', 'ingot_uranium'), ('ore_gneiss_uranium_scorched', 'ingot_uranium')]
SMELTING_IDS = [f'{result}_from_smelting_{ore}' for ore, result in SMELTING]
SMELTING_LINE = re.compile(r'addOreSmelting\(recipeOutput, NtmBlocks\.(\w+)\.get\(\), NtmItems\.(\w+)\.get\(\), 0\.7F\);')
RECIPE_DIR = GENERATED_ROOT+'data/hbmsntm/recipe/'
ADVANCEMENT = re.compile(re.escape(GENERATED_ROOT+'data/hbmsntm/advancement/recipes/')+r'[a-z_]+/('+'|'.join(SMELTING_IDS)+r')\.json')
# Crystallizer: five rows appended to the 41 default rows (original CrystallizerRecipes.java:67 U.ore() and :69 PU.ore()).
CRYSTALLIZER_ADDED = ['ORE_NETHER_URANIUM', 'ORE_NETHER_URANIUM_SCORCHED', 'ORE_GNEISS_URANIUM', 'ORE_GNEISS_URANIUM_SCORCHED', 'ORE_NETHER_PLUTONIUM']
# Must have changed (or been added) by the time of the real run; the rest of the owner table is optional.
REQUIRED_CHANGES = (PRODUCTION + GENERATED + [RECIPE_DIR+i+'.json' for i in SMELTING_IDS] + TOOLS + REPORTS + SHARED_RECORDS)
AUDITS = {'localization-audit-final.json': 'localization-audit.json', 'resources-audit-final.json': 'resources-audit.json',
          'packaged-resources-final.json': 'packaged-resources.json'}
# Indexed by the receipt as evidence files of this batch; the two Gradle logs must end in BUILD SUCCESSFUL.
LOGS = ('rundata-final.log', 'build-final.log')
FILES = ('production-vs-start.diff', 'validate-final.log')
# Frozen with the start (always present).
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'chain.sh')
# Written by chain.sh next to the logs; checked and indexed when present.
CHAIN_FILES = ('chain-exits-final.txt', 'chain-done-final.txt', 'jar-final.sha256', 'stamp-before-rundata-final.json')
VERIFY_REPORT = 'verify/report.json'
FINAL_SUMMARY = 'final/summary.json'
COMPARE = 'compare.json'
GAMETEST_LOG = 'build/migration/goal22a/gametest-final.log'
NEW_SUITE = 'verify_goal22a_closeout.py --gametest-log build/migration/goal22a/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
GAMETEST = re.compile(r'All (\d+) required tests passed')
GAMETEST_ANNOTATION = re.compile(r'^\s*@GameTest\(', re.M)
DATE_LINE = re.compile(r'\d{4}-\d{2}-\d{2}')
SCOPE = ('Goal22A (Goal 21 close-out remainders): English (NtmLanguageProvider) and Chinese (zh_cn.json and the zh_cn mapping, original '
         'translations) names and creative-tab entries for the nine registered but unnamed ore blocks (ore_schrabidium, ore_nether_uranium, '
         'ore_nether_uranium_scorched, ore_nether_plutonium, ore_nether_schrabidium, ore_tikite, ore_gneiss_uranium, '
         'ore_gneiss_uranium_scorched, ore_gneiss_schrabidium) and the Chinese name of powder_co60_tiny; six smelting recipes (original '
         'SmeltingRecipes.java:32-35 and :56-57: the scorched, nether, scorched nether, schist and scorched schist uranium ores to the uranium '
         'ingot and the nether plutonium ore to the plutonium ingot; the experience is NEO\'s 0.7F, the original is 6.0F, 12.0F and 24.0F); five '
         'appended crystallizer rows (original CrystallizerRecipes.java:67 U.ore() remaining members and :69 plutonium, in sulfuric acid), the '
         'default table 41 -> 46 rows, the first 41 unchanged; the OilBubbleFeature.addSurfaceSpot far-chunk write guard (reads and random draws '
         'unchanged; only writes WorldGenRegion would drop are skipped); SmokeGameTests expects 46 rows and gains goal22a_ore_names_and_outputs; '
         'and the first packaging of the D1 small fix (MachineChungusBlock lever direction) and the O2 small fix (CommonEvents dropped-item hazards '
         'and EntityEffectHandler crater pollution on the server only), both committed in 36c6597e and in no earlier package. Local difference: '
         'NEO generates none of these ores (no nether or schist world generation); they come from Goal21C nuclear-waste contamination, the creative '
         'tab or commands. No registration, hazard, centrifuge, world generation or save-data change.')
GOAL22A_RADIATION = ('Goal22A adds no hazard; the nine ore blocks carry no material hazard in NEO (Goal21 decision 13). ')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal22a release directory: '+rel


def start_drift_paths(base):
    """The receipt-hashed records that already differ from their receipt hash at the frozen start (baseline drift lists)."""
    return sorted(set(base['previous_receipt_evidence_drift']).union(*base['older_receipt_evidence_drift'].values()))


def protected_paths(base):
    """What the review-g21d-hazard-fix packager protected (built there from the Goal21A..Goal21D starts, the older receipts and the goal21d
    receipt; its four insert-only records come back at the fix receipt's hashes below), plus every path the fix receipt hashes, the paths the
    goal21a..goal21d receipts hash and every release file of the frozen start. The records that already drifted at the start are pinned at their
    start hash (baseline files) instead of any receipt hash. One path never carries two different hashes."""
    fix_base = read(FIX_BASELINE)
    out, _ = fix_protected_paths(fix_base, read(GOAL21D_RECEIPT))
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'], 'Start drift path is not a frozen file: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    for p in drift:
        out.pop(p, None)
        out[p] = base['files'][p]
    return out


def start_drift_report(base):
    """{path: {receipts: {label: hash}, start_sha256, current_sha256}} for the records that differ from their receipt hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['review-g21d-hazard-fix receipt'] = base['previous_receipt_protected_paths'][p]
        start = base['files'][p]
        newest = receipts.get('review-g21d-hazard-fix receipt')
        out[p] = dict(receipt_hashes=receipts, start_sha256=start, current_sha256=sha(ROOT/p),
                      explanation=('Appended to after its receipt(s) were written (Goal 21 in-game acceptance result lines or the O1 record notes); the '
                                   'newest receipt that hashes it'+(' records the start hash' if newest == start else ' is older than the start')+
                                   '. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.'))
    return out


def group(p):
    if p in PRODUCTION_JAVA: return 'production'
    if p == ZH_INPUT: return 'production-chinese'
    if p == LOCALIZATION_RECORD: return 'production-localization-record'
    if p in GENERATED: return 'generated'
    if p in [RECIPE_DIR+i+'.json' for i in SMELTING_IDS] or ADVANCEMENT.fullmatch(p): return 'generated'
    if p in TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    return None


def annotations(path):
    return len(GAMETEST_ANNOTATION.findall(Path(path).read_text(encoding='utf-8')))


def default_rows(text):
    """Rows the default crystallizer table holds: ore() = stone + deepslate = 2 rows, single() = 1, from the registerDefaults() statements."""
    match = re.search(r'public void registerDefaults\(\) \{\n(.*?)\n    \}', text.replace('\r\n', '\n'), re.S)
    assert match, 'registerDefaults() not found'
    body = '\n'.join(l.split('//')[0] for l in match.group(1).split('\n'))
    return dict(ore=len(re.findall(r'^\s*ore\(', body, re.M)), single=len(re.findall(r'^\s*single\(', body, re.M)),
                rows=2*len(re.findall(r'^\s*ore\(', body, re.M)) + len(re.findall(r'^\s*single\(', body, re.M)))


def default_statements(text):
    """The statements of registerDefaults() in order, comments and blank lines dropped."""
    match = re.search(r'public void registerDefaults\(\) \{\n(.*?)\n    \}', text.replace('\r\n', '\n'), re.S)
    assert match, 'registerDefaults() not found'
    return [s for s in (l.split('//')[0].strip() for l in match.group(1).split('\n')) if s]


def stale_diff(diff_text):
    """Why production-vs-start.diff is stale, or None: it must carry at least every net added and every net removed production line (a multiset
    comparison of the live and the frozen start copies of the production files)."""
    diff = diff_text.replace('\r\n', '\n').split('\n')
    plus = Counter(l[1:] for l in diff if l.startswith('+') and not l.startswith('+++'))
    minus = Counter(l[1:] for l in diff if l.startswith('-') and not l.startswith('---'))
    need_plus, need_minus = Counter(), Counter()
    for p in PRODUCTION:
        old, new = Counter(lines_of((START_FILES/p).read_bytes())), Counter(lines_of((ROOT/p).read_bytes()))
        need_plus.update(new - old)
        need_minus.update(old - new)
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
    """Why verify/report.json (the passing tools/migration/verify_goal22a_closeout.py report) is not a passing run, [] otherwise."""
    problems = []
    if 'ok' in report and report['ok'] is not True: problems.append('ok is '+repr(report['ok']))
    for key in ('result', 'status'):
        if key in report and str(report[key]).lower() not in ('pass', 'passed', 'ok'): problems.append(f'{key} is {report[key]!r}')
    if not any(k in report for k in ('ok', 'result', 'status')) and 'checks' not in report and 'static_checks' not in report:
        problems.append('report carries no ok/result/status and no checks')
    checks = report.get('checks', {})
    entries = list(checks.items()) if isinstance(checks, dict) else [(c.get('name', c.get('id', i)), c) for i, c in enumerate(checks) if isinstance(c, dict)]
    failed = [n for n, c in entries if isinstance(c, dict) and (str(c.get('status', 'pass')).lower() in ('fail', 'failed') or c.get('ok') is False or c.get('passed') is False)]
    if failed: problems.append('failed checks: '+str(failed[:5]))
    mutations = report.get('mutations')
    entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
    if not entries: problems.append('report lists no mutations')
    undetected = [e for e in entries if isinstance(e, dict) and e.get('detected') is False]
    if undetected: problems.append(f'{len(undetected)} undetected mutations')
    if 'mutations_detected' in report:
        # The verifier may write mutations_detected and mutation_count as separate integers or one 'N/M' string.
        raw = str(report['mutations_detected'])
        detected, total = (int(x) for x in raw.split('/')) if '/' in raw else (int(raw), int(report.get('mutation_count', len(entries))))
        if detected != total or not total: problems.append('mutations_detected is '+raw+' of '+str(total))
    if report.get('mutations_undetected'): problems.append('undetected mutations: '+str(report['mutations_undetected'][:5]))
    hashes = find_key(report, 'production_sha256')
    if not hashes:
        problems.append('report carries no production_sha256')
    for table in hashes:
        if not isinstance(table, dict): problems.append('production_sha256 is not a mapping'); continue
        for k, v in table.items():
            rel = k.replace('\\', '/')
            rel = rel[len(ROOT.as_posix())+1:] if rel.startswith(ROOT.as_posix()+'/') else rel
            if not (ROOT/rel).is_file(): problems.append('production_sha256 names a missing file: '+rel)
            elif v not in (sha(ROOT/rel), normalized_sha(ROOT/rel)): problems.append('production_sha256 differs from the live file: '+rel)
        for p in PRODUCTION:
            if not any(k.replace('\\', '/').endswith(p) or p.endswith(k.replace('\\', '/')) for k in table): problems.append('production_sha256 lacks '+p)
    return problems


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

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal22A commits nothing), the recorded start content.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD and base['planning_commit'] == START_HEAD, 'Unexpected frozen start'
    assert base['closeout_head'] == CLOSEOUT_HEAD and base['target_status'] == '' and base['dirty_paths'] == [] and base['source_status'] == '', 'The frozen start was not clean'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == START_HEAD, 'NEO HEAD moved during Goal22A: '+head
    assert set(base['start_content']) == {'committed', 'small_fixes'} and set(base['start_content']['small_fixes']) == set(SMALL_OWNERS), 'Baseline start content differs'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['dirty_paths'] == len(base['dirty_paths']) and startup['frozen_file_hashes'] == len(base['files']) \
        and startup['old_release_files'] == len(base['old_release_files']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'], 'startup-verification.json differs from baseline.json'
    # The D1 and O2 small fixes: committed, unpackaged. Their sources still hold the recorded hash and the README names them.
    small = base['start_content']['small_fixes']
    small_paths = {p: k for k, v in small.items() for p in v['paths']}
    small_classes = {c: k for k, v in small.items() for c in v['classes']}
    readme_now = (ROOT/'migration/README.md').read_text(encoding='utf-8')
    readme_start = (START_FILES/'migration/README.md').read_text(encoding='utf-8')
    for k, v in small.items():
        for p, h in v['paths'].items():
            assert base['files'][p] == h == sha(ROOT/p) == sha(START_FILES/p), 'Small-fix source '+k+' changed since the start: '+p
        assert v['readme'] in readme_start and v['readme'] in readme_now, 'README lacks the small-fix line '+k+': '+v['readme']
    assert base['build_libs_vs_previous'] == dict(added=[], removed=[], modified=sorted(small_classes)), 'build/libs at the start is not the previous package + the small-fix classes'
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the review-g21d-hazard-fix package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert sha(PREVIOUS) == previous_sha and PREVIOUS.stat().st_size == previous_bytes, 'Previous JAR changed'
    assert prior_receipt['sha256'] == previous_sha and prior_receipt['bytes'] == previous_bytes, 'Previous receipt names another JAR'
    previous_receipt_sha = base['old_release_files'][PREVIOUS_RECEIPT.relative_to(ROOT).as_posix()]
    previous_sums_sha = base['old_release_files'][PREVIOUS_SUMS.relative_to(ROOT).as_posix()]
    assert sha(PREVIOUS_RECEIPT) == previous_receipt_sha, 'Previous release.json changed'
    assert sha(PREVIOUS_SUMS) == previous_sums_sha, 'Previous SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (previous_sha+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Previous SHA256SUMS.txt content changed'
    for p, h in base['old_release_files'].items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release file changed: '+p
    old_releases = dict(base['old_releases'])
    assert old_releases.get(PREVIOUS.relative_to(ROOT).as_posix()) == previous_sha
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    protected = protected_paths(base)
    drift_report = start_drift_report(base)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)

    # 3. Changes since the start: each path in the owner table, attributed to goal22a. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    assert not unassigned, 'Unassigned path changed since the Goal22A start: '+str(unassigned)
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal22A start: '+str(deleted)
    for p in PRODUCTION + GENERATED: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in TOOLS: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    missing_required = [p for p in REQUIRED_CHANGES if p not in changes]
    for p in missing_required: need(False, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    assert set(since) <= set(PRODUCTION_JAVA + [ZH_INPUT]), 'src/main change outside the production list: '+str(sorted(set(since) - set(PRODUCTION_JAVA + [ZH_INPUT])))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    for p in small_paths: assert p not in changes, 'A small-fix source changed since the start: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p))
                   for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    assert baselines_now == {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}, 'A snapshot was added or changed'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'], 'review-6a11998d5852 snapshot changed'

    # The production files keep their start line endings (the frozen start copies are the baseline files).
    for p in PRODUCTION:
        start_eol, eol = eol_counts((START_FILES/p).read_bytes()), eol_counts((ROOT/p).read_bytes())
        assert (start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), \
            f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}'
        if (ROOT/p).read_bytes() == (START_FILES/p).read_bytes(): need(False, p+' still equals the start')

    # Production Java facts: insert-only files (provider, creative tab, recipe provider), the crystallizer rows, the GameTest count.
    insert_summary = {}
    for p in (PROVIDER, CREATIVE_TABS, RECIPE_PROVIDER):
        inserted = insertions(lines_of((START_FILES/p).read_bytes()), lines_of((ROOT/p).read_bytes()))
        if not need(inserted is not None, p+' is not insert-only against the start copy (a start line was changed, moved or removed)'): continue
        insert_summary[p] = len(inserted)
        if not inserted: continue
        text = '\n'.join(l for _, l in inserted)
        if p == PROVIDER or p == CREATIVE_TABS:
            found = sorted(re.findall(r'NtmBlocks\.(ORE_\w+)', text))
            need(found == sorted(i.upper() for i in NINE), f'{p} inserts {found}, not the nine ore blocks')
        else:
            pairs = sorted(SMELTING_LINE.findall(text))
            need(pairs == sorted((o.upper(), r.upper()) for o, r in SMELTING), f'{p} inserts the smelting rows {pairs}, not the six original rows')
    crystallizer_start, crystallizer_now = (START_FILES/CRYSTALLIZER).read_text(encoding='utf-8'), (ROOT/CRYSTALLIZER).read_text(encoding='utf-8')
    rows_start, rows_now = default_rows(crystallizer_start), default_rows(crystallizer_now)
    need(rows_now['rows'] == rows_start['rows'] + len(CRYSTALLIZER_ADDED), f'crystallizer default table has {rows_now["rows"]} rows, not {rows_start["rows"]} + {len(CRYSTALLIZER_ADDED)}')
    statements_start, statements_now = default_statements(crystallizer_start), default_statements(crystallizer_now)
    appended = [f'single(NtmBlocks.{o}.get(), NtmItems.{"CRYSTAL_PLUTONIUM" if o == "ORE_NETHER_PLUTONIUM" else "CRYSTAL_URANIUM"}.get(), Fluids.SULFURIC_ACID);'
                for o in CRYSTALLIZER_ADDED]
    need(statements_now[:len(statements_start)] == statements_start and sorted(statements_now[len(statements_start):]) == sorted(appended),
         'the start registerDefaults() statements are not an unchanged prefix followed by exactly the five original rows (U.ore() remainder + plutonium)')
    need(f', {rows_now["rows"]} rows;' in crystallizer_now and f'expected {rows_now["rows"]}"' in (ROOT/SMOKE).read_text(encoding='utf-8'),
         f'getComment() or the SmokeGameTests row assertion does not state {rows_now["rows"]} rows')

    # 4. Language and the generated tree.
    empty = dict(added=[], removed=[], changed=[])
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    en_expected = sorted('block.hbmsntm.'+i for i in NINE)
    need(en_delta == dict(added=en_expected, removed=[], changed=[]), 'generated en_us.json delta is not the nine block names: '+json.dumps(en_delta, ensure_ascii=False))
    need(zh_delta == dict(added=sorted(en_expected+[POWDER]), removed=[], changed=[]), 'zh_cn.json delta is not the nine block names + powder_co60_tiny: '+json.dumps(zh_delta, ensure_ascii=False))
    need(map_delta == dict(added=en_expected, removed=[], changed=[POWDER]), 'zh_cn-map.json delta is not nine new entries + the powder_co60_tiny change: '+json.dumps(map_delta, ensure_ascii=False))
    if map_delta['added'] == en_expected:
        bad = [k for k in en_expected if map_now[k].get('kind') != 'upstream' or map_now[k].get('source_key') != 'tile.'+k[len('block.hbmsntm.'):]+'.name'
               or map_now[k].get('target_zh') != zh_now.get(k) or map_now[k].get('target_en') != en_now.get(k)]
        need(not bad, 'zh_cn-map.json entries are not upstream entries matching en_us.json and zh_cn.json: '+str(bad))
    if POWDER in map_now:
        need(map_now[POWDER].get('kind') == 'local' and map_now[POWDER].get('target_zh') == POWDER_ZH == zh_now.get(POWDER) and map_now[POWDER].get('reason'),
             'zh_cn-map.json powder_co60_tiny is not a local entry with '+POWDER_ZH)
    map_kinds = dict(Counter(e.get('kind') for e in map_now.values()))
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
    need(generated_changed == [EN_ENTRY], f'Generated resources changed since the start: {generated_changed[:5]} (expected only {EN_ENTRY})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    need(sorted(GENERATED_ROOT+p for p in generated_added) == sorted(p for p in generated_since if p not in GENERATED),
         'Stamp-recorded generated additions differ from the generated files added since the start: stamp %s, tree %s' % (
             generated_added[:8], [p for p in generated_since if p not in GENERATED][:8]))
    for i in SMELTING_IDS:
        need((ROOT/(RECIPE_DIR+i+'.json')).is_file(), 'generated smelting recipe missing: '+RECIPE_DIR+i+'.json')
    advancements = sorted(p for p in generated_since if ADVANCEMENT.fullmatch(p))
    need(len(advancements) in (0, len(SMELTING_IDS)), f'runData generated {len(advancements)} recipe advancements for the {len(SMELTING_IDS)} smelting recipes')
    generated_added_entries = {GENERATED_ROOT+p: p for p in generated_added}

    # 5. Evidence: GameTest log, audits, Gradle logs, diff, the final suite run, the verifier report and compare.
    evidence = {}
    gametest_line = gametest_count = None
    smoke_now, smoke_start = annotations(ROOT/SMOKE), annotations(START_FILES/SMOKE)
    total_now = sum(annotations(p) for p in sorted(GAMETEST_DIR.glob('*.java')))
    assert total_now - smoke_now + smoke_start == prior_receipt['gametest']['tests'], \
        'The start GameTest sources do not hold the previous count of '+str(prior_receipt['gametest']['tests'])
    smoke_added = smoke_now - smoke_start
    gametest_expected = total_now
    need(smoke_added == 1, f'{SMOKE} gained {smoke_added} @GameTest methods so far (expected 1: goal22a_ore_names_and_outputs)')
    log = (ROOT/gametest_log).resolve() if gametest_log else None
    if need(log is not None and log.is_file(), 'GameTest log (--gametest-log): '+(str(gametest_log) if gametest_log else 'not given')+' does not exist yet'):
        assert log.is_relative_to(ROOT), 'GameTest log outside the NEO repository: '+str(log)
        text = log.read_text(encoding='utf-8-sig', errors='replace')
        found = GAMETEST.findall(text)
        if need(bool(found) and 'BUILD SUCCESSFUL' in text and 'invalid dist' not in text and 'NoClassDefFoundError' not in text,
                log.relative_to(ROOT).as_posix()+' did not pass cleanly (needs "All N required tests passed" and BUILD SUCCESSFUL, no "invalid dist" or NoClassDefFoundError)'):
            gametest_count = int(found[-1])
            need(gametest_count == gametest_expected,
                 f'GameTest server ran {gametest_count} tests, the sources hold {gametest_expected} @GameTest methods ({prior_receipt["gametest"]["tests"]} previous tests + {smoke_added})')
            gametest_line = f'All {gametest_count} required tests passed'
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence: build/migration/goal22a/'+name): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence: build/migration/goal22a/'+name): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence: build/migration/goal22a/'+name+' (missing or empty)'): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE:
        assert (OUT/name).is_file(), 'Missing frozen start evidence: '+name
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain.sh output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
    for name in CHAIN_FILES:
        if (OUT/name).is_file(): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change.
    diff_path = OUT/'production-vs-start.diff'
    if diff_path.is_file() and diff_path.stat().st_size and all((ROOT/p).read_bytes() != (START_FILES/p).read_bytes() for p in PRODUCTION):
        message = stale_diff(diff_path.read_text(encoding='utf-8-sig'))
        if message: need(False, message)
    final = None
    # The suites of the review-fix final run plus the Goal22A verifier.
    reference_suites = set(read(REFERENCE_FIX)['suites'])
    final_expected = len(reference_suites) + 1
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence: build/migration/goal22a/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        assert set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the review-fix final set + the Goal22A verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE})))
        entry = final['suites'][NEW_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, NEW_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence: build/migration/goal22a/'+VERIFY_REPORT+' (tools/migration/verify_goal22a_closeout.py report)'):
        report = read(OUT/VERIFY_REPORT)
        problems = verifier_problems(report)
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=TOOLS[0],
                        tool_sha256=sha(ROOT/TOOLS[0]) if (ROOT/TOOLS[0]).is_file() else None,
                        mutations_detected=report.get('mutations_detected', report.get('mutation_count')))
        evidence[verifier['path']] = verifier['sha256']
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree): the original unchanged, the target exactly the fix receipt's compare
    # target set plus this batch's paths inside the compare inventory plus the D1/O2 source paths (committed since the fix, so absent from the
    # fix compare); compare never lists the stamp; unmapped changes as in the fix. No new snapshot.
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'previous receipt compare target set is incomplete'
    prior_cmp = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_compare['sha256'], 'previous compare.json changed'
    assert compare_paths(prior_cmp['changes']['target']['added']) | compare_paths(prior_cmp['changes']['target']['modified']) == previous_target, \
        'previous compare.json target set differs from its receipt'
    small_in_compare = {p for p in small_paths if in_compare_inventory(p)}
    expected_target = sorted(previous_target | {p for p in changes if in_compare_inventory(p)} | small_in_compare)
    if need((OUT/COMPARE).is_file(), 'evidence: build/migration/goal22a/'+COMPARE+' (compare against '+SNAPSHOT+'; expected target set: %d paths)' % len(expected_target)):
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

        def compare_owners(p):
            return set(prior_compare['target_owners'].get(p, [])) | ({OWNER} if p in changes else set()) | ({SMALL_OWNERS[small_paths[p]]} if p in small_paths else set())
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts,
                       target_owners={p: sorted(compare_owners(p)) for p in listed})
        evidence[compare['path']] = compare['sha256']

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned (goal22a, small-fix-D1, small-fix-O2).
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    crystallizer_jar = None
    classes = []
    if need(sha(JAR) not in (previous_sha, start_jar_sha), 'build/libs/hbmsntm-198A.jar is still the previous package or the small-fix start build (run build)'):
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
            need(en_jar == en_delta and zh_jar == zh_delta, 'JAR en_us.json or zh_cn.json delta against the previous package differs from the source delta: en '+str(en_jar)+', zh '+str(zh_jar))
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        small_src_owner = {p: SMALL_OWNERS[k] for p, k in small_paths.items()}
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if n.endswith('.class'):
                    source = owner_class(n)
                    if source in small_src_owner: owner = [small_src_owner[source]]
                    elif source in PRODUCTION_JAVA: owner = [OWNER]
                elif n in (ZH_ENTRY, EN_ENTRY) or (kind == 'added' and GENERATED_ROOT+n in generated_added_entries):
                    owner = [OWNER]
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        assert not unowned, 'Unowned JAR change: '+str(unowned)
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        assert not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta)
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        small_changed = sorted(n for n in changed_classes if owner_class(n) in small_src_owner)
        assert small_changed == sorted(small_classes) and all(n in jar_delta['modified'] for n in small_changed), \
            'The small-fix class delta is not exactly the three recorded classes: '+str(small_changed)
        need(set(class_owners) == set(PRODUCTION_JAVA) | set(small_paths), 'Not every changed Java source changed a class: '+str(sorted((set(PRODUCTION_JAVA) | set(small_paths)) - set(class_owners)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(PRODUCTION_JAVA) - set(small_paths))))
        for n in ('com/hbm/datagen/NtmLanguageProvider.class', 'com/hbm/datagen/NtmRecipeProvider.class', 'com/hbm/world/feature/OilBubbleFeature.class'):
            need(n in jar_delta['modified'], n+' is not a modified JAR class')
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed']))
        need(all(n in set(generated_added) for n in jar_delta['added'] if not n.endswith('.class')),
             'Added non-class JAR entries that are not generated additions: '+str([n for n in jar_delta['added'] if not n.endswith('.class')][:8]))
        added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
        removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
        assert classes and len(classes) == prior_receipt['compiled_classes_verified'] + added_classes - removed_classes, \
            f'Compiled class count {len(classes)} is not the previous count {prior_receipt["compiled_classes_verified"]} +{added_classes} -{removed_classes}'
        language = dict(en=en_jar, zh=zh_jar)
        crystallizer_jar = dict(source_rows_start=rows_start['rows'], source_rows_now=rows_now['rows'])

    # 7. Records: the release name, the batch reports, the README small-fix line of the oil guard.
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    for p in unnamed: need(False, 'record does not name '+RELEASE_NAME+': '+p)
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p
    read(ROOT/'migration/features.json')
    start_readme_lines = set(readme_start.splitlines())
    oil_lines = [l for l in readme_now.splitlines() if l not in start_readme_lines and 'OilBubbleFeature' in l and DATE_LINE.match(l)]
    need(len(oil_lines) == 1, f'migration/README.md has {len(oil_lines)} new dated lines naming OilBubbleFeature (expected the one small-fix line)')
    small_report = {k: dict(owner=SMALL_OWNERS[k], paths=v['paths'], sources_sha256_now={p: sha(ROOT/p) for p in v['paths']}, classes=v['classes'],
                            readme=v['readme'], readme_line=next((l for l in readme_now.splitlines() if v['readme'] in l), None),
                            first_packaged_in=OWNER, state='committed in '+CLOSEOUT_HEAD[:8]+', in no earlier package')
                    for k, v in small.items()}
    oil_report = dict(owner=OWNER, path=OIL, rule='small fix done inside the batch (README small-fix rule)', readme_line=oil_lines[0] if len(oil_lines) == 1 else None,
                      classes=sorted(n for n in (jar_delta or {}).get('modified', []) + (jar_delta or {}).get('added', []) if n.endswith('.class') and owner_class(n) == OIL))

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=generated_added,
                   start_drift=sorted(drift_report), en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, map_kinds=map_kinds,
                   crystallizer_rows=dict(start=rows_start['rows'], now=rows_now['rows']), insert_lines=insert_summary,
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta, class_owners=class_owners,
                   gametest=gametest_line, gametest_expected=gametest_expected, smoke_tests_added=smoke_added,
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
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different goal22a JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest == sha(JAR) and digest not in (previous_sha, start_jar_sha), 'Packaged JAR is not build/libs or is an older JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in reports}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified', scope=SCOPE,
                   radiation_warning=GOAL22A_RADIATION+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, planning_commit=START_HEAD, commits={}, target_head_at_packaging=head,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=previous_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, closeout_head=CLOSEOUT_HEAD,
                                      note='The start tree is HEAD 29702b40 (the Goal 22 planning commit on top of the Goal 21 close-out 36c6597e) with a '
                                           'clean worktree. build/libs at the start is the review-g21d-hazard-fix package plus exactly the classes of the '
                                           'D1 and O2 small fixes, which are packaged here for the first time (small_fixes).'),
                   small_fixes=small_report, batch_small_fix=oil_report,
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added,
                   compiled_classes_verified=len(classes),
                   production=PRODUCTION, sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   resources={}, resource_ownership=None,
                   smelting=dict(rows=[dict(input=o, result=r, experience=0.7, original_experience='SmeltingRecipes.java:32-35 (6.0F, 12.0F, 24.0F as recorded in the task book)')
                                       for o, r in SMELTING], recipe_ids=SMELTING_IDS, advancements=advancements),
                   crystallizer=dict(rows_start=rows_start['rows'], rows_now=rows_now['rows'], appended=CRYSTALLIZER_ADDED, first_rows_unchanged=True,
                                     source=crystallizer_jar),
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added'],
                                           zh_cn_map_changed=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 provider_add_calls=dict(start=len(re.findall(r'^\s*this\.add\(', (START_FILES/PROVIDER).read_text(encoding='utf-8'), re.M)),
                                                         now=len(re.findall(r'^\s*this\.add\(', (ROOT/PROVIDER).read_text(encoding='utf-8'), re.M))),
                                 provider_lines_inserted=insert_summary.get(PROVIDER), jar_delta=language,
                                 note='Nine block names (original en_US.lang/zh_CN.lang tile.<id>.name) plus the NEO-only powder_co60_tiny Chinese name '
                                      '(local mapping entry, deferred -> local).'),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; goal22a_ore_names_and_outputs '
                                      'checks the English names, the six smelting results and the five sulfuric acid rows, and the existing acidizer test '
                                      'expects the 46-row default table; the Chinese names, the creative tab, JEI and the oil-field log are not covered.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + [LOCALIZATION_RECORD],
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, '
                            'the static, generated-tree and JAR verifier with mutations, the final old-suite rerun, compare against the review-6a11998d5852 '
                            'snapshot and independent JAR bytes. No client, real save, multiplayer or in-game test was run: the Chinese names, the creative '
                            'tab entries, the furnace and acidizer behavior with these ores and the oil-field log are unverified in game.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the review-g21d-hazard-fix package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
