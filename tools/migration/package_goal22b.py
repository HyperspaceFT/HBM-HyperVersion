"""Package Goal22B (PUREX cold-waste reprocessing: the machine_purex multiblock with its block entity, module, menu, screen, renderer, JEI
category and PUREXRecipes default table, ass.purex, nuclear_waste_tiny and the NuclearWasteItem drop behavior, the gas centrifuge MUD outputs,
the chemical plant speed-upgrade tooltip text, eight English and Chinese language keys, four imported original assets) cumulatively on the
goal22a package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal22b.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal22b/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to
build/migration/goal22b/gametest-final.log (the GameTest dedicated-server log of the settled tree).

The frozen start is build/migration/goal22b/baseline.json: NEO HEAD 29702b40 plus the Goal22A delivery kept UNCOMMITTED (33 dirty paths,
Goal 22 decision 14). build/libs at the start equals the goal22a package byte for byte. Every change since the start is computed from the
baseline file hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. Several
Goal22A paths (the language provider, the recipe provider, the creative tabs, zh_cn.json, the zh_cn mapping, en_us.json, the generation stamp,
README, features, UPSTREAM-REVIEWS, LOCALIZATION, GOAL22.md) are modified again here: their before hash is the start hash, their after hash
the live one. The JAR delta against the goal22a package is attributed per entry (goal22b); any entry without an owner fails. Counts that
records quote (suites, GameTests, generated resources, classes, releases, language keys, recipe rows) are computed here, never hard-coded; the
previous package's SHA-256, size and receipt hashes are read from the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal21d, the review-g21d-hazard-fix receipt and goal22a) were written before the Goal 21 in-game
acceptance appended its result lines to the acceptance checklists and before the O1 record notes; those records already differ from their older
receipt hashes at the frozen start (baseline older_receipt_evidence_drift; the goal22a receipt records their start hash, previous_receipt_
evidence_drift is empty). They are listed in the receipt as start drift (receipt hashes, start hash, current hash) and must still equal their
start hash; no receipt is rewritten and no other protected path may drift."""
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import owner_class
from package_goal19c import tree_files
from package_review_g20_display_fixes import protected_drift as display_protected_drift, split_drift
from migration import BUILD_FILES
from package_goal21d import (LOCALIZATION_RECORD, STAMP, EN, SNAPSHOT, SOURCE_HEAD, ZH_ENTRY, EN_ENTRY, lang_delta, compare_paths, lines_of,
                             eol_counts, insertions, in_compare_inventory, changed_since_start)
from package_goal22a import BASELINE as GOAL22A_BASELINE, OUT as GOAL22A_OUT, protected_paths as goal22a_protected_paths, find_key, annotations

OUT = ROOT/'build/migration/goal22b'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL22A_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL22A_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal22a/hbmsntm-198A-goal22a.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal22b'
RELEASE_NAME = 'hbmsntm-198A-goal22b.jar'
OWNER = 'goal22b'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
GENERATED_ROOT = 'src/generated/resources/'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
# Production (owner goal22b), NEW: the PUREX classes, the shared waste item class and the GameTest class.
NEW_JAVA = [J+p+'.java' for p in ('blocks/machine/MachinePUREXBlock', 'blockentity/machine/MachinePUREXBlockEntity', 'module/machine/ModuleMachinePUREX',
                                  'inventory/recipes/PUREXRecipes', 'inventory/menus/MachinePUREXMenu', 'inventory/screens/MachinePUREXScreen',
                                  'render/blockentity/RenderPUREX', 'handler/jei/PUREXRecipeHandler', 'items/NuclearWasteItem', 'gametest/PUREXGameTests')]
(BLOCK, BLOCK_ENTITY, MODULE, PUREX_RECIPES, MENU, SCREEN, RENDERER, JEI_HANDLER, WASTE_ITEM, PUREX_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (handoff-production.md plus the two by-design GameTest updates and the optional SmokeGameTests).
MODIFIED_JAVA = [J+p+'.java' for p in ('blocks/NtmBlocks', 'blockentity/NtmBlockEntityTypes', 'inventory/NtmMenuTypes', 'inventory/NtmCreativeTabs',
                                       'items/NtmItems', 'items/machine/DepletedFuelItem', 'hazard/HazardRegistry', 'datagen/NtmRecipeProvider',
                                       'datagen/NtmItemModelProvider', 'datagen/NtmBlockStateProvider', 'datagen/NtmBlockLootTableProvider',
                                       'datagen/NtmBlockTagProvider', 'datagen/NtmLanguageProvider', 'inventory/recipes/AssemblyMachineRecipes',
                                       'inventory/recipes/GasCentrifugeRecipes', 'inventory/recipes/loader/SerializableRecipe',
                                       'blockentity/machine/MachineChemicalPlantBlockEntity', 'main/NuclearTechModClient', 'main/ClientProxy',
                                       'main/ResourceManager', 'handler/jei/NtmJeiPlugin', 'gametest/WasteDrumGameTests',
                                       'gametest/GasCentrifugeGameTests', 'gametest/SmokeGameTests')]
(BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, CREATIVE_TABS, ITEMS, DEPLETED_FUEL, HAZARD_REGISTRY, RECIPE_PROVIDER, ITEM_MODEL_PROVIDER, BLOCK_STATE_PROVIDER,
 LOOT_PROVIDER, TAG_PROVIDER, PROVIDER, ASSEMBLY, CENTRIFUGE_RECIPES, SERIALIZABLE, CHEM_PLANT_BE, CLIENT_MOD, CLIENT_PROXY, RESOURCE_MANAGER, JEI_PLUGIN,
 WASTE_DRUM_TESTS, CENTRIFUGE_TESTS, SMOKE) = MODIFIED_JAVA
# A listed file may stay unchanged (the main agent marks it optional).
OPTIONAL_UNCHANGED = {SMOKE}
# Modified sources that must stay insert-only against their start copy (the rest of the modified sources may replace lines; the receipt records
# each one's added and removed line counts).
STRICT_INSERT_ONLY = [PROVIDER, CREATIVE_TABS, RECIPE_PROVIDER, SERIALIZABLE]
# The four imported original assets (byte for byte): NEO path -> original path under src/main/resources of the original at SOURCE_HEAD.
ASSETS = {ASSETS_ROOT+'models/obj/machines/purex.obj': RES+'assets/hbm/models/machines/purex.obj',
          ASSETS_ROOT+'textures/models/machines/purex.png': RES+'assets/hbm/textures/models/machines/purex.png',
          ASSETS_ROOT+'textures/gui/processing/gui_purex.png': RES+'assets/hbm/textures/gui/processing/gui_purex.png',
          ASSETS_ROOT+'textures/item/nuclear_waste_tiny.png': RES+'assets/hbm/textures/items/nuclear_waste_tiny.png'}
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA
PRODUCTION = PRODUCTION_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
GENERATED = [STAMP, EN]
TOOLS = ['tools/migration/verify_goal22b_purex.py', 'tools/migration/package_goal22b.py']
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal22b-* or GOAL22B-* record is hashed as well.
REPORTS = ['migration/GOAL22B.md', 'migration/GOAL22B-ACCEPTANCE.md', 'migration/goal22b-localization-review.json', 'migration/goal22b-static-review.md',
           'migration/goal22b-redundant-review.md', 'migration/goal22b-resource-ownership.json', 'migration/goal22b-custom-purex-example.json']
BATCH_RECORD = re.compile(r'migration/(goal22b-[^/]+\.(json|md)|GOAL22B-[^/]+\.md)')
SHARED_RECORDS = ['migration/GOAL22.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md']
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
NAMES_RELEASE = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
RESOURCE_OWNERSHIP = 'migration/goal22b-resource-ownership.json'
# Must have changed (or been added) by the time of the real run; the rest of the owner table is optional.
REQUIRED_CHANGES = (NEW_JAVA + list(ASSETS) + [p for p in MODIFIED_JAVA if p not in OPTIONAL_UNCHANGED] + [ZH_INPUT, LOCALIZATION_RECORD] + GENERATED
                    + TOOLS + REPORTS + SHARED_RECORDS)
# The eight new language keys (English via NtmLanguageProvider, Chinese from the original zh_CN.lang; all upstream mapping entries).
KEYS = ['autoswitch.schrab', 'autoswitch.zirnox', 'block.hbmsntm.machine_purex', 'block.hbmsntm.machine_purex.desc', 'container.machinePUREX',
        'item.hbmsntm.nuclear_waste_tiny', 'purex.recycle', 'purex.schrab']
# The 11 default PUREX rows in original order (task book B3) and the feature group that lists the new paths.
ROWS = ['purex.zirnoxnu', 'purex.zirnoxmeu', 'purex.zirnoxthmeu', 'purex.zirnoxmox', 'purex.zirnoxmep', 'purex.zirnoxheu233', 'purex.zirnoxheu235',
        'purex.zirnoxles', 'purex.zirnoxzfbmox', 'purex.schraranium', 'purex.schrabzirnox']
ROW = re.compile(r'new GenericRecipe\("(purex\.[a-z0-9_]+)"\)')
ORIGINAL_ROW = re.compile(r'new PUREXRecipe\("(purex\.[a-z0-9_]+)"\)')
ORIGINAL_RECIPES = 'src/main/java/com/hbm/inventory/recipes/PUREXRecipes.java'
FEATURE_GROUP = 'purex-reprocessing'
GENERATED_NEW_NAME = re.compile(r'machine_purex|nuclear_waste')
AUDITS = {'localization-audit-final.json': 'localization-audit.json', 'resources-audit-final.json': 'resources-audit.json',
          'packaged-resources-final.json': 'packaged-resources.json'}
# Indexed by the receipt as evidence files of this batch; the two Gradle logs must end in BUILD SUCCESSFUL.
LOGS = ('rundata-final.log', 'build-final.log')
FILES = ('production-vs-start.diff', 'validate-final.log')
# Frozen with the start (always present).
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'chain.sh', 'handoff-production.md')
# Written by chain.sh next to the logs; checked and indexed when present.
CHAIN_FILES = ('chain-exits-final.txt', 'chain-done-final.txt', 'jar-final.sha256', 'stamp-before-rundata-final.json')
CHAIN_COMMANDS = ('runData', 'gametest', 'build', 'loc', 'audit', 'jar', 'validate')
VERIFY_REPORT = 'verify/report.json'
FINAL_SUMMARY = 'final/summary.json'
COMPARE = 'compare.json'
GAMETEST_LOG = 'build/migration/goal22b/gametest-final.log'
NEW_SUITE = 'verify_goal22b_purex.py --gametest-log build/migration/goal22b/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
GAMETEST = re.compile(r'All (\d+) required tests passed')
GAMETEST_ANNOTATION = re.compile(r'^\s*@GameTest\(', re.M)
GOAL22B_RADIATION = ('Goal22B: PUREX consumes radioactive cold ZIRNOX waste and produces radioactive nuggets (plutonium, uranium, neptunium, technetium) and '
                     'nuclear_waste_tiny (RADIATION 1.5 per item); nuclear_waste, nuclear_waste_vitrified and nuclear_waste_tiny drops now never despawn and are '
                     'invulnerable like the original ItemNuclearWaste (only the void or /kill removes them). Run PUREX and drop waste only in separately '
                     'authorized disposable worlds. ')


def scope_text(rows, original_total, deferred, key_count):
    return (f'Goal22B (PUREX cold-waste reprocessing): the machine_purex 5x5x5 multiblock (original MachinePUREX, TileEntityMachinePUREX, ModuleMachinePUREX, '
            f'ContainerMachinePUREX, GUIMachinePUREX, RenderPUREX; 16 bottom-ring inventory, power and fluid proxies) as the NEO block, block entity, module, menu, '
            f'screen, renderer and OBJ model, with the PUREXRecipes table (hbmPUREX.json, limits 3/3/6/1) registering the {len(rows)} default rows ({", ".join(rows)}: '
            f'nine ZIRNOX cold-waste rows in autoswitch.zirnox, purex.schraranium, and purex.schrabzirnox in autoswitch.schrab; original PUREXRecipes.java lines '
            f':90-169 and :524-539), the JEI category purex and the ass.purex assembler recipe (original AssemblyMachineRecipes.java:270-272); the new item '
            f'nuclear_waste_tiny (hazard wst x nugget = 1.5, original HazardRegistry.java:212; 9 tiny <-> 1 nuclear_waste and the billet recipes, original '
            f'MineralRecipes.java:389-390 and :150) and the shared NuclearWasteItem (nuclear_waste, nuclear_waste_vitrified and nuclear_waste_tiny drops never '
            f'despawn, are invulnerable and have pickup delay 10 as the original ItemNuclearWaste; DepletedFuelItem now extends it with unchanged behavior; '
            f'billet_nuclear_waste stays a plain Item); the gas centrifuge MUD_HEAVY and MUD outputs (original GasCentrifugeRecipes.java:32-33; the WATZ '
            f'recognizer is still not converted); the chemical plant speed-upgrade consumption tooltip text lvl*50 -> lvl*100 to match its own formula (Goal 22 '
            f'decision 17, no formula change); {key_count} English keys with their original Chinese; four original assets imported byte for byte (purex.obj, '
            f'purex.png, gui_purex.png, nuclear_waste_tiny.png). Local differences: no GenericRecipes client sync, so a server-side custom hbmPUREX.json does not '
            f'reach client JEI or the recipe selector (the same limitation as the chemical plant, Goal 22 decision 16); {deferred} of the {original_total} original '
            f'rows are deferred with their fuel systems (listed in the PUREXRecipes comment); any-face proxy access is the accepted NEO-only multiblock difference.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal22b release directory: '+rel


def git_ro(repo, *args):
    """Read-only git (no optional index lock)."""
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+repo.as_posix(), *args], cwd=repo).decode('utf-8')


def original_blob(path):
    """Bytes of a file at the original repository's recorded commit (independent of its worktree)."""
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+SOURCE.as_posix(), 'show', SOURCE_HEAD+':'+path], cwd=SOURCE)


def receipt_protected(receipt):
    """Every path a receipt hashes (report and evidence maps, each top-level {path, sha256} entry, verification evidence), without build/libs."""
    out = {}
    for key in ('report_sha256', 'evidence_sha256'): out.update(receipt.get(key, {}))
    for value in receipt.values():
        if isinstance(value, dict) and isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str): out[value['path']] = value['sha256']
    verification = receipt.get('verification')
    if isinstance(verification, dict): out.update(verification.get('evidence_sha256', {}))
    return {p: h for p, h in out.items() if not p.startswith('build/libs/')}


def start_drift_paths(base):
    """The receipt-hashed records that already differ from an older receipt's hash at the frozen start (baseline drift lists)."""
    return sorted(set(base['previous_receipt_evidence_drift']).union(*base['older_receipt_evidence_drift'].values()))


def protected_paths(base):
    """What the goal22a packager protected (built there from the Goal21A..Goal21D starts, the older receipts and the review-fix receipt), plus every
    path the goal22a receipt hashes, the paths the older receipts hash (the 22B baseline lists the review-fix receipt among them) and every release
    file of the frozen start. The records that already drifted at the start are pinned at their start hash (baseline files) instead of any older
    receipt hash. One path never carries two different hashes."""
    out = dict(goal22a_protected_paths(read(GOAL22A_BASELINE)))
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'], 'Start drift path is not a frozen file: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    for p in drift:
        assert out.get(p, base['files'][p]) == base['files'][p], 'The goal22a start pinned another hash for '+p
        out.pop(p, None)
        out[p] = base['files'][p]
    return out


def start_drift_report(base):
    """{path: {receipts: {label: hash}, start_sha256, current_sha256}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal22a receipt'] = base['previous_receipt_protected_paths'][p]
        start = base['files'][p]
        newest = receipts.get('goal22a receipt')
        out[p] = dict(receipt_hashes=receipts, start_sha256=start, current_sha256=sha(ROOT/p),
                      explanation=('Appended to after its older receipt(s) were written (Goal 21 in-game acceptance result lines or the O1 record notes); the '
                                   'newest receipt that hashes it'+(' (goal22a) records the start hash' if newest == start else ' is older than the start')+
                                   '. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.'))
    return out


def group(p):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA: return 'production'
    if p in ASSETS: return 'production-resource'
    if p == ZH_INPUT: return 'production-chinese'
    if p == LOCALIZATION_RECORD: return 'production-localization-record'
    if p.startswith(GENERATED_ROOT): return 'generated'
    if p in TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records'
    return None


def strip_java_comments(text):
    return re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', text, flags=re.S))


def edit_counts(old_lines, new_lines):
    return dict(added=sum((Counter(new_lines) - Counter(old_lines)).values()), removed=sum((Counter(old_lines) - Counter(new_lines)).values()))


def stale_diff(diff_text, files):
    """Why production-vs-start.diff is stale, or None: it must carry at least every net added and every net removed line of the changed production
    files (a multiset comparison of the live copy and the frozen start copy; a new file has all its lines added). files = [(path, start bytes or
    None)]."""
    diff = diff_text.replace('\r\n', '\n').split('\n')
    plus = Counter(l[1:] for l in diff if l.startswith('+') and not l.startswith('+++ '))
    minus = Counter(l[1:] for l in diff if l.startswith('-') and not l.startswith('--- '))
    need_plus, need_minus = Counter(), Counter()
    def text_lines(data):
        # lines_of splits on '\n', so a file ending in a newline yields a phantom '' that no unified diff prints; drop it.
        lines = lines_of(data)
        return lines[:-1] if lines and lines[-1] == '' else lines
    for p, start in files:
        old, new = Counter(text_lines(start) if start is not None else []), Counter(text_lines((ROOT/p).read_bytes()))
        need_plus.update(new - old)
        need_minus.update(old - new)
    short_plus = sorted(l for l, n in need_plus.items() if plus[l] < n)
    short_minus = sorted(l for l, n in need_minus.items() if minus[l] < n)
    if short_plus or short_minus:
        return f'production-vs-start.diff is stale: {len(short_plus)} added and {len(short_minus)} removed production lines missing (first: {(short_plus or short_minus)[:1]})'
    return None


def verifier_problems(report, required):
    """Why verify/report.json (the passing tools/migration/verify_goal22b_purex.py report) is not a passing run, [] otherwise. required = the
    production paths its production_sha256 table must cover."""
    problems = []
    if 'ok' in report and report['ok'] is not True: problems.append('ok is '+repr(report['ok']))
    for key in ('result', 'status'):
        if key in report and str(report[key]).lower() not in ('pass', 'passed', 'ok'): problems.append(f'{key} is {report[key]!r}')
    if not any(k in report for k in ('ok', 'result', 'status')) and 'checks' not in report and 'static_checks' not in report:
        problems.append('report carries no ok/result/status and no checks')
    if report.get('failed'): problems.append('failed list: '+str(report['failed'][:5]))
    summary = report.get('summary') if isinstance(report.get('summary'), dict) else {}
    if summary.get('checks_failed'): problems.append('summary.checks_failed is '+str(summary['checks_failed']))
    checks = report.get('checks', {})
    entries = list(checks.items()) if isinstance(checks, dict) else [(c.get('name', c.get('id', i)), c) for i, c in enumerate(checks) if isinstance(c, dict)]
    failed = [n for n, c in entries if isinstance(c, dict) and (str(c.get('status', 'pass')).lower() in ('fail', 'failed') or c.get('ok') is False or c.get('passed') is False)]
    if failed: problems.append('failed checks: '+str(failed[:5]))
    mutations = report.get('mutations')
    entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
    if not entries: problems.append('report lists no mutations')
    undetected = [e for e in entries if isinstance(e, dict) and e.get('detected') is False]
    if undetected: problems.append(f'{len(undetected)} undetected mutations')
    if report.get('undetected_mutations') or report.get('mutations_undetected'):
        problems.append('undetected mutations: '+str((report.get('undetected_mutations') or report.get('mutations_undetected'))[:5]))
    if 'mutations_detected' in summary:
        if summary['mutations_detected'] != summary.get('mutations_total') or not summary.get('mutations_total'):
            problems.append(f'summary mutations_detected {summary["mutations_detected"]} of {summary.get("mutations_total")}')
    if 'mutations_detected' in report:
        # The verifier may write mutations_detected and mutation_count as separate integers or one 'N/M' string.
        raw = str(report['mutations_detected'])
        detected, total = (int(x) for x in raw.split('/')) if '/' in raw else (int(raw), int(report.get('mutation_count', len(entries))))
        if detected != total or not total: problems.append('mutations_detected is '+raw+' of '+str(total))
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
        for p in required:
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

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal22B commits nothing), the recorded start content.
    start_head = prior_receipt['target_start_commit']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at 6a11998d'
    assert base['target_head'] == start_head == prior_receipt['target_head_at_packaging'], 'The frozen start is not the goal22a start commit'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal22B: '+head
    assert set(base['start_content']) == {'committed', 'uncommitted'}, 'Baseline start content differs'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['dirty_paths'] == len(base['dirty_paths']) and startup['frozen_file_hashes'] == len(base['files']) \
        and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['previous_jar_sha256'] == base['previous_release']['sha256'] and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'], \
        'startup-verification.json differs from baseline.json'
    # The start tree is the goal22a delivery, uncommitted: its dirty paths are exactly the goal22a receipt's changed files at their after hashes.
    assert sorted(base['dirty_paths']) == sorted(c['path'] for c in prior_receipt['changed_files']), 'The start dirty paths are not the goal22a changed files'
    for c in prior_receipt['changed_files']:
        assert base['files'][c['path']] == base['dirty_files'][c['path']] == c['after_sha256'], 'The start copy of a goal22a path differs from the receipt: '+c['path']
    assert base['build_libs_vs_previous'] == dict(added=[], removed=[], modified=[]), 'build/libs at the start is not the previous package byte for byte'
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal22a package, every old release file and the protected evidence.
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal22a receipt list + the goal22a package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal22a receipt count + the goal22a release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal22a receipt'
    assert base['previous_receipt_evidence_drift'] == [], 'The goal22a receipt evidence had already drifted at the start'
    protected = protected_paths(base)
    drift_report = start_drift_report(base)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)

    # 3. Changes since the start: each path in the owner table, attributed to goal22b. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal22B start that the owner table does not list (production outside the handoff list or an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal22B start: '+str(deleted)
    for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD] + GENERATED: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + TOOLS: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since =sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
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

    # The modified production files keep their start line endings (the frozen start copies are the baseline files); new Java files are not mixed.
    start_text = {}
    for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]:
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

    # Production Java facts: insert-only files, the chemical plant tooltip, the recipe rows, the imported assets, the waste classes.
    insert_summary, edit_summary = {}, {}
    for p in STRICT_INSERT_ONLY:
        if p not in start_text: continue
        inserted = insertions(lines_of(start_text[p]), lines_of((ROOT/p).read_bytes()))
        if need(inserted is not None, p+' is not insert-only against the start copy (a start line was changed, moved or removed)'): insert_summary[p] = len(inserted)
    for p in MODIFIED_JAVA:
        if p in start_text and p not in STRICT_INSERT_ONLY: edit_summary[p] = edit_counts(lines_of(start_text[p]), lines_of((ROOT/p).read_bytes()))
    if CHEM_PLANT_BE in start_text:
        old_l, new_l = lines_of(start_text[CHEM_PLANT_BE]), lines_of((ROOT/CHEM_PLANT_BE).read_bytes())
        # The one code change plus its explaining comment lines (added by the main agent after the default review, finding 2).
        is_comment = lambda l: l.strip().startswith('//')
        new_code = [l for l in new_l if not is_comment(l)]; old_code = [l for l in old_l if not is_comment(l)]
        ops = [o for o in SequenceMatcher(None, old_code, new_code, autojunk=False).get_opcodes() if o[0] != 'equal']
        comment_delta = sum(map(is_comment, new_l)) - sum(map(is_comment, old_l))
        need(len(ops) == 1 and ops[0][0] == 'replace' and ops[0][2]-ops[0][1] == 1 and ops[0][4]-ops[0][3] == 1 and 'lvl * 50' in old_code[ops[0][1]]
             and new_code[ops[0][3]] == old_code[ops[0][1]].replace('lvl * 50', 'lvl * 100') and 0 <= comment_delta <= 2,
             CHEM_PLANT_BE+' differs from the start by more than the one-line tooltip change lvl * 50 -> lvl * 100 (decision 17) and its comment: '+str([(o[0], old_code[o[1]:o[2]][:2], new_code[o[3]:o[4]][:2]) for o in ops[:3]]))
    imported = {}
    for target, original in ASSETS.items():
        if not (ROOT/target).is_file(): continue
        # The original worktree is clean at SOURCE_HEAD, so its file is the checked-out original; on this Windows checkout it carries CRLF where the
        # stored blob has LF (autocrlf), which earlier batches imported as the worktree bytes. The blob must match up to that line-ending conversion.
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        imported[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size,
                                original_worktree_sha256=sha(SOURCE/original), original_blob_sha256=hashlib.sha256(blob).hexdigest(), original_blob_bytes=len(blob),
                                line_endings_converted_from_blob=blob != checked_out)
        need((ROOT/target).read_bytes() == checked_out, f'{target} is not byte-identical to the original worktree file {original}')
        need(blob.replace(b'\r\n', b'\n') == (ROOT/target).read_bytes().replace(b'\r\n', b'\n'), f'{target} differs from the {SOURCE_HEAD[:8]} blob of {original} beyond line endings')
    registered_rows, original_total = [], None
    if (ROOT/PUREX_RECIPES).is_file():
        registered_rows = ROW.findall(strip_java_comments((ROOT/PUREX_RECIPES).read_text(encoding='utf-8')))
        need(registered_rows == ROWS, f'{PUREX_RECIPES} registers {registered_rows}, not the 11 default rows {ROWS} in original order')
        need('hbmPUREX.json' in (ROOT/PUREX_RECIPES).read_text(encoding='utf-8'), PUREX_RECIPES+' does not name hbmPUREX.json')
    original_rows = ORIGINAL_ROW.findall((SOURCE/ORIGINAL_RECIPES).read_text(encoding='utf-8'))
    original_total = len(set(original_rows))
    assert set(ROWS) <= set(original_rows) and original_total == len(original_rows), 'The 11 default rows are not rows of the original PUREXRecipes.java'
    deferred_rows = original_total - len(ROWS)
    if (ROOT/ITEMS).is_file() and ITEMS in changes:
        items_now = (ROOT/ITEMS).read_text(encoding='utf-8')
        need('NUCLEAR_WASTE_TINY' in items_now and items_now.count('NuclearWasteItem') >= 3, ITEMS+' does not register NUCLEAR_WASTE_TINY and construct three waste items as NuclearWasteItem')
        if ITEMS in start_text:
            need([l for l in lines_of(start_text[ITEMS]) if 'BILLET_NUCLEAR_WASTE' in l] == [l for l in items_now.replace('\r\n', '\n').split('\n') if 'BILLET_NUCLEAR_WASTE' in l],
                 ITEMS+': the BILLET_NUCLEAR_WASTE line changed (billet_nuclear_waste stays a plain Item)')
    if (ROOT/DEPLETED_FUEL).is_file() and DEPLETED_FUEL in changes:
        need('extends NuclearWasteItem' in (ROOT/DEPLETED_FUEL).read_text(encoding='utf-8'), DEPLETED_FUEL+' does not extend NuclearWasteItem')
    if (ROOT/CENTRIFUGE_RECIPES).is_file() and CENTRIFUGE_RECIPES in changes:
        need('NUCLEAR_WASTE_TINY' in (ROOT/CENTRIFUGE_RECIPES).read_text(encoding='utf-8'), CENTRIFUGE_RECIPES+' does not use NUCLEAR_WASTE_TINY for the MUD_HEAVY outputs')
    if (ROOT/SERIALIZABLE).is_file() and SERIALIZABLE in changes:
        need((ROOT/SERIALIZABLE).read_text(encoding='utf-8').count('PUREXRecipes.INSTANCE') == 1, SERIALIZABLE+' does not register PUREXRecipes.INSTANCE exactly once')
    features = read(ROOT/'migration/features.json')['features']
    group_entry = next((f for f in features if f.get('id') == FEATURE_GROUP), None)
    if need(group_entry is not None, 'migration/features.json has no group '+FEATURE_GROUP):
        missing = sorted((set(NEW_JAVA) | set(ASSETS)) - set(group_entry.get('target_paths', [])))
        need(not missing, 'features.json group '+FEATURE_GROUP+' lacks target_paths: '+str(missing))
    ownership_path = ROOT/RESOURCE_OWNERSHIP
    if need(ownership_path.is_file(), 'record missing: '+RESOURCE_OWNERSHIP):
        ownership = read(ownership_path)
        entries = {a.get('target_path'): a for a in ownership.get('assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(ASSETS), RESOURCE_OWNERSHIP+' does not list the four assets at '+SOURCE_HEAD[:8])
        for target, original in ASSETS.items():
            if target in entries and (ROOT/target).is_file():
                a = entries[target]
                need(a.get('source_path') == original and a.get('sha256') == sha(ROOT/target) and a.get('bytes') == (ROOT/target).stat().st_size,
                     RESOURCE_OWNERSHIP+' entry differs from the live asset or the original path: '+target)

    # 4. Language and the generated tree.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_keys = sorted(KEYS)
    need(en_delta == dict(added=expected_keys, removed=[], changed=[]), 'generated en_us.json delta is not the eight new keys: '+json.dumps(en_delta, ensure_ascii=False))
    need(zh_delta == dict(added=expected_keys, removed=[], changed=[]), 'zh_cn.json delta is not the eight new keys: '+json.dumps(zh_delta, ensure_ascii=False))
    need(map_delta == dict(added=expected_keys, removed=[], changed=[]), 'zh_cn-map.json delta is not the eight new entries: '+json.dumps(map_delta, ensure_ascii=False))
    bad = [k for k in KEYS if k in map_now and (map_now[k].get('kind') != 'upstream' or not map_now[k].get('source_key')
                                                 or map_now[k].get('target_zh') != zh_now.get(k) or (k in en_now and map_now[k].get('target_en') != en_now[k]))]
    need(not bad, 'zh_cn-map.json entries are not upstream entries matching en_us.json and zh_cn.json: '+str(bad))
    need(all(k in en_now for k in KEYS), 'en_us.json lacks keys (runData): '+str([k for k in KEYS if k not in en_now]))
    map_kinds = dict(Counter(e.get('kind') for e in map_now.values()))
    start_kinds = dict(Counter(e.get('kind') for e in map_start.values()))
    need(map_kinds.get('deferred') == start_kinds.get('deferred'), f'deferred mapping entries changed: start {start_kinds.get("deferred")}, now {map_kinds.get("deferred")}')
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
    other_changed = [p for p in generated_changed if p != EN_ENTRY and '/tags/' not in p]
    need(EN_ENTRY in generated_changed and not other_changed, f'Generated resources changed since the start: {generated_changed[:8]} (expected en_us.json and tag files only)')
    unexpected_added = [p for p in generated_added if not GENERATED_NEW_NAME.search(p)]
    need(not unexpected_added, f'Generated additions that are not machine_purex or nuclear_waste resources: {unexpected_added[:8]}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    need(sorted(GENERATED_ROOT+p for p in generated_added) == sorted(p for p in generated_since if p not in GENERATED and changes[p] == 'added'),
         'Stamp-recorded generated additions differ from the generated files added since the start: stamp %s, tree %s' % (
             generated_added[:8], [p for p in generated_since if p not in GENERATED and changes[p] == 'added'][:8]))
    need(sorted(GENERATED_ROOT+p for p in generated_changed) == sorted(p for p in generated_since if p not in (STAMP,) and changes[p] == 'modified'),
         'Stamp-recorded generated changes differ from the generated files modified since the start: stamp %s, tree %s' % (
             generated_changed[:8], [p for p in generated_since if p != STAMP and changes[p] == 'modified'][:8]))
    for name in ('assets/hbmsntm/blockstates/machine_purex.json', 'data/hbmsntm/loot_table/blocks/machine_purex.json', 'assets/hbmsntm/models/item/machine_purex.json',
                 'assets/hbmsntm/models/item/nuclear_waste_tiny.json'):
        need(name in generated_added, 'runData did not generate '+GENERATED_ROOT+name)
    recipes = sorted(Path(p).stem for p in generated_added if p.startswith('data/hbmsntm/recipe/'))
    advancements = sorted(Path(p).stem for p in generated_added if p.startswith('data/hbmsntm/advancement/recipes/'))
    need(len(recipes) >= 2 and set(advancements) <= set(recipes), f'runData generated {len(recipes)} new recipes and {len(advancements)} advancements (advancements must belong to new recipes)')
    generated_added_entries = {GENERATED_ROOT+p: p for p in generated_added}
    generated_changed_entries = {GENERATED_ROOT+p: p for p in generated_changed}

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
    purex_tests = annotations(ROOT/PUREX_TESTS) if (ROOT/PUREX_TESTS).is_file() else 0
    need(purex_tests >= 1, f'{PUREX_TESTS} holds {purex_tests} @GameTest methods (expected the PUREX suite)')
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
        if not need((OUT/name).is_file(), 'evidence: build/migration/goal22b/'+name): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence: build/migration/goal22b/'+name): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence: build/migration/goal22b/'+name+' (missing or empty)'): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE:
        assert (OUT/name).is_file(), 'Missing frozen start evidence: '+name
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
    # production-vs-start.diff must carry every production line change (modified files against their start copies, new Java files in full).
    diff_path = OUT/'production-vs-start.diff'
    if diff_path.is_file() and diff_path.stat().st_size and all((ROOT/p).is_file() for p in NEW_JAVA):
        message = stale_diff(diff_path.read_text(encoding='utf-8-sig'), [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
    final = None
    # The suites of the goal22a final run plus the Goal22B verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert NEW_SUITE not in reference_suites, 'The Goal22B suite is already in the goal22a final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence: build/migration/goal22b/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        assert set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal22a final set + the Goal22B verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE})))
        entry = final['suites'][NEW_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, NEW_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence: build/migration/goal22b/'+VERIFY_REPORT+' (tools/migration/verify_goal22b_purex.py report)'):
        report = read(OUT/VERIFY_REPORT)
        problems = verifier_problems(report, [p for p in production_changed if not p.startswith(RES) or p == ZH_INPUT])
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=TOOLS[0],
                        tool_sha256=sha(ROOT/TOOLS[0]) if (ROOT/TOOLS[0]).is_file() else None,
                        mutations_detected=report.get('mutations_detected', summary_part.get('mutations_detected', report.get('mutation_count'))),
                        mutations_total=summary_part.get('mutations_total', report.get('mutation_count')))
        evidence[verifier['path']] = verifier['sha256']
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree): the original unchanged, the target exactly the goal22a receipt's compare
    # target set plus this batch's paths inside the compare inventory; compare never lists the stamp; unmapped changes as in goal22a. No new snapshot.
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'previous receipt compare target set is incomplete'
    prior_cmp = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_compare['sha256'], 'previous compare.json changed'
    assert compare_paths(prior_cmp['changes']['target']['added']) | compare_paths(prior_cmp['changes']['target']['modified']) == previous_target, \
        'previous compare.json target set differs from its receipt'
    expected_target = sorted(previous_target | {p for p in changes if in_compare_inventory(p)})
    if need((OUT/COMPARE).is_file(), 'evidence: build/migration/goal22b/'+COMPARE+' (compare against '+SNAPSHOT+'; expected target set: %d paths)' % len(expected_target)):
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
            return set(prior_compare['target_owners'].get(p, [])) | ({OWNER} if p in changes else set())
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts,
                       target_owners={p: sorted(compare_owners(p)) for p in listed})
        evidence[compare['path']] = compare['sha256']

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned (goal22b).
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) not in (previous_sha, start_jar_sha), 'build/libs/hbmsntm-198A.jar is still the previous package (run build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the four assets and every compiled class equal the sources.
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [e for e, t in asset_entries.items() if e not in names or not (ROOT/t).is_file() or jar.read(e) != (ROOT/t).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json, the assets or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == en_delta and zh_jar == zh_delta, 'JAR en_us.json or zh_cn.json delta against the previous package differs from the source delta: en '+str(en_jar)+', zh '+str(zh_jar))
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
                elif n in (ZH_ENTRY, EN_ENTRY) or n in asset_entries or (GENERATED_ROOT+n in generated_added_entries and kind == 'added') \
                        or (GENERATED_ROOT+n in generated_changed_entries and kind == 'modified'):
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
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY} | set(generated_added) | set(generated_changed)
        need(non_class == expected_non_class, 'JAR non-class delta differs from the assets + language + generated delta: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed']))
        for n in ('com/hbm/datagen/NtmLanguageProvider.class', 'com/hbm/datagen/NtmRecipeProvider.class', 'com/hbm/items/NuclearWasteItem.class',
                  'com/hbm/blocks/machine/MachinePUREXBlock.class', 'com/hbm/items/machine/DepletedFuelItem.class'):
            need(n in jar_delta['modified'] or n in jar_delta['added'], n+' is not a changed JAR class')
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
                   map_kinds=map_kinds, purex_rows=registered_rows, original_rows=original_total, deferred_rows=deferred_rows, insert_lines=insert_summary,
                   edit_counts=edit_summary, gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added,
                   purex_tests=purex_tests, final_suites_expected=final_expected, compare=compare['counts'] if compare else None,
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
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different goal22b JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest == sha(JAR) and digest not in (previous_sha, start_jar_sha), 'Packaged JAR is not build/libs or is an older JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in reports}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(registered_rows, original_total, deferred_rows, len(KEYS)),
                   radiation_warning=GOAL22B_RADIATION+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=start_head, planning_commit=prior_receipt['planning_commit'], commits={},
                   target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha, base_release_receipt_sha256=previous_receipt_sha,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, dirty_paths=base['dirty_paths'], dirty_files=base['dirty_files'],
                                      note='The start tree is HEAD 29702b40 (the Goal 22 planning commit on top of the Goal 21 close-out 36c6597e) plus the '
                                           'Goal22A delivery, kept uncommitted by Goal 22 decision 14: the dirty paths are exactly the goal22a receipt\'s '
                                           'changed files at their receipt after-hashes, and build/libs at the start is the goal22a package byte for byte. '
                                           'Paths this batch changes again (language provider, recipe provider, creative tabs, zh_cn.json, the zh_cn mapping, '
                                           'en_us.json, the stamp and the shared records) record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   production_unchanged_optional=sorted(p for p in OPTIONAL_UNCHANGED if p not in changes),
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary,
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   purex=dict(default_rows=registered_rows, original_rows=original_total, deferred_rows=deferred_rows, original_file=ORIGINAL_RECIPES,
                              feature_group=FEATURE_GROUP,
                              note='Default table of 11 rows; no GenericRecipes client sync (a server-side custom hbmPUREX.json does not reach client JEI or '
                                   'the recipe selector, as the chemical plant); the unregistered original rows are listed in the PUREXRecipes comment.'),
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 provider_add_calls=dict(start=len(re.findall(r'^\s*this\.add\(', (START_FILES/PROVIDER).read_text(encoding='utf-8'), re.M)),
                                                         now=len(re.findall(r'^\s*this\.add\(', (ROOT/PROVIDER).read_text(encoding='utf-8'), re.M))),
                                 provider_lines_inserted=insert_summary.get(PROVIDER), jar_delta=language,
                                 note='Eight keys (block name and description, container title, two recipe name wrappers, two autoswitch group names, '
                                      'nuclear_waste_tiny), all upstream mapping entries with the original zh_CN.lang text.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count, added_tests=gametest_added,
                                 purex_tests=purex_tests,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; PUREXGameTests follows task book '
                                      'B4 (structure, the default rows, autoswitch, upgrades, maxPower, blocking, slot rules, NBT and sync round trip, '
                                      'nuclear_waste_tiny and the waste drops, the centrifuge MUD outputs); the screen, recipe selector, renderer, audio, JEI '
                                      'category and Chinese UI are not covered.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + [LOCALIZATION_RECORD],
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, '
                            'the static, generated-tree and JAR verifier with mutations, the final old-suite rerun, compare against the review-6a11998d5852 '
                            'snapshot and independent JAR bytes. No client, real save, multiplayer or in-game test was run: the PUREX screen, recipe selector, '
                            'renderer and animation, loop sound, JEI category, Chinese UI text, the waste drops in a real world and the radiation of the '
                            'products are unverified in game.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal22a package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
