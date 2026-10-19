"""Package Goal23B (RTG pellets, item layer only: RTGPelletItem with ten pellets, RTGPelletDepletedItem with six depleted pellets, RTGUtil decay and
power, the rtg config section, the eleven original hazard rows with HazardModifierRTGRadiation, ten pellet and four recycling recipes, 16 item models,
15 imported textures, the creative tab entries, 47 language keys and nine RTGPelletGameTests) cumulatively on the goal23a package, without replacing
any previous delivery. The RT generator that consumes the pellets is Goal23C.

python -B -X utf8 tools/migration/package_goal23b.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal23b/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal23b/gametest-final.log (the
GameTest dedicated-server log of the settled tree).

The frozen start is build/migration/goal23b/baseline.json: NEO HEAD dd69a404 (the Goal 23 planning commit on top of the Goal 22 close-out commit 670d5911)
plus the 24 uncommitted Goal23A paths (decision 15: Goal 23 is committed once at its close-out), each equal to the goal23a receipt's after_sha256.
build/libs at the start is the goal23a package byte for byte. Every change since the start is computed from the baseline file hashes (not from git diff)
and must be in the owner table below; every other path must still equal its start hash. Several Goal23A paths (the language provider, HazardGameTests,
zh_cn.json, the zh_cn mapping, en_us.json, the generation stamp, README, features, UPSTREAM-REVIEWS, LOCALIZATION and GOAL23.md) are modified again
here: their before hash is the start hash (the goal23a after hash), their after hash the live one. The JAR delta against the goal23a package is
attributed per entry (goal23b); any entry without exactly one owner fails. Counts that records quote (suites, GameTests, generated resources, classes,
releases, language keys, recipes, hazard rows) are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from
the files and the baseline, not from literals.

The concurrent read-only batch 23D may create migration/RBMK-SCOPE.md and tools/migration/verify_goal23d_rbmk_scope.py. They are listed in the receipt
as owner goal23d-concurrent with their final hashes, never packaged, never attributed to this batch and never an unassigned change.

The receipts that hash records (goal21a..goal23a and the review-g21d-hazard-fix receipt) were written before later appends to the acceptance checklists,
before the O1 record notes and (goal22c) before the thorium follow-up section of GOAL22C.md; those records already differ from their older receipt hashes
at the frozen start (baseline older_receipt_evidence_drift; the goal23a receipt records their start hash, previous_receipt_evidence_drift is empty).
They are listed in the receipt as start drift and must still equal their Goal23B start hash; no receipt is rewritten and no other protected path may
drift."""
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
import argparse
import hashlib
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
from package_goal22b import (git_ro, original_blob, edit_counts, stale_diff, receipt_protected, start_drift_paths, strip_java_comments,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE, J
from package_goal23a import (OUT as GOAL23A_OUT, BASELINE as GOAL23A_BASELINE, protected_paths as goal23a_protected_paths,
                             verifier_problems, original_line)

OUT = ROOT/'build/migration/goal23b'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL23A_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL23A_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal23a/hbmsntm-198A-goal23a.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal23b'
RELEASE_NAME = 'hbmsntm-198A-goal23b.jar'
OWNER = 'goal23b'
OWNER_23A = 'goal23a'
OWNER_23D = 'goal23d-concurrent'
GOAL22_CLOSEOUT = '670d5911'
PLANNING_PREFIX = 'dd69a404'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
TEXTURES = RES+'assets/hbmsntm/textures/item/'
O_TEXTURES = RES+'assets/hbm/textures/items/'

# The ten pellets (pellet_rtg keeps its ID, nine are new) and the six depleted materials, in the original's order.
PELLET_SUFFIXES = ['radium', 'weak', 'strontium', 'cobalt', 'actinium', 'americium', 'polonium', 'gold', 'lead']
PELLET_IDS = ['pellet_rtg'] + ['pellet_rtg_'+n for n in PELLET_SUFFIXES]
DEPLETED_MATERIALS = ['bismuth', 'mercury', 'neptunium', 'lead', 'zirconium', 'nickel']
RECYCLED_MATERIALS = ['bismuth', 'lead', 'neptunium', 'zirconium']
RECIPE_IDS = PELLET_IDS + ['pellet_rtg_depleted_'+m for m in RECYCLED_MATERIALS]
SKIPPED_RECIPES = ['pellet_rtg_depleted_mercury', 'pellet_rtg_depleted_nickel']

# Production (owner goal23b), NEW: the pellet and depleted pellet items, the util, the hazard modifier and the GameTest class.
NEW_JAVA = [J+'items/machine/RTGPelletItem.java', J+'items/machine/RTGPelletDepletedItem.java', J+'util/RTGUtil.java',
            J+'hazard/modifier/HazardModifierRTGRadiation.java', J+'gametest/RTGPelletGameTests.java']
(PELLET_ITEM, DEPLETED_ITEM, RTG_UTIL, RTG_MODIFIER, RTG_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources. NtmItems replaces exactly the PELLET_RTG registration line and HazardRegistry exactly the deferral comment
# line; the language, recipe, model and creative tab providers and CommonConfig are insert-only; HazardGameTests changes the pellet_rtg deferral guard
# and its comments (the receipt records each one's added and removed line counts).
MODIFIED_JAVA = [J+p+'.java' for p in ('items/NtmItems', 'config/CommonConfig', 'hazard/HazardRegistry', 'datagen/NtmRecipeProvider',
                                       'datagen/NtmItemModelProvider', 'datagen/NtmLanguageProvider', 'inventory/NtmCreativeTabs', 'gametest/HazardGameTests')]
(ITEMS, COMMON_CONFIG, HAZARD_REGISTRY, RECIPE_PROVIDER, ITEM_MODEL_PROVIDER, PROVIDER, CREATIVE_TABS, HAZARD_TESTS) = MODIFIED_JAVA
INSERT_ONLY = [COMMON_CONFIG, RECIPE_PROVIDER, ITEM_MODEL_PROVIDER, PROVIDER, CREATIVE_TABS]
# path -> a token the single removed start line must contain.
ONE_LINE_REPLACED = {ITEMS: '"pellet_rtg"', HAZARD_REGISTRY: 'RTG'}
# The 15 imported original textures (byte for byte): NEO path -> original path under src/main/resources of the original at SOURCE_HEAD.
TEXTURE_NAMES = ['pellet_rtg_'+n for n in PELLET_SUFFIXES] + ['pellet_rtg_depleted.'+m for m in DEPLETED_MATERIALS]
ASSETS = {TEXTURES+n+'.png': O_TEXTURES+n+'.png' for n in TEXTURE_NAMES}
UNCHANGED_TEXTURE = TEXTURES+'pellet_rtg.png'
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA
PRODUCTION = PRODUCTION_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
GENERATED = [STAMP, EN]
# Generated by runData for this batch (relative to src/generated/resources): 16 item models, 14 recipes and 14 recipe advancements.
EXPECTED_GENERATED = sorted(
    ['assets/hbmsntm/models/item/pellet_rtg_%s.json' % n for n in PELLET_SUFFIXES] + ['assets/hbmsntm/models/item/pellet_rtg_depleted.json']
    + ['assets/hbmsntm/models/item/pellet_rtg_depleted_%d.json' % i for i in range(len(DEPLETED_MATERIALS))]
    + ['data/hbmsntm/recipe/%s.json' % r for r in RECIPE_IDS] + ['data/hbmsntm/advancement/recipes/misc/%s.json' % r for r in RECIPE_IDS])
TOOLS = ['tools/migration/verify_goal23b_rtg.py', 'tools/migration/package_goal23b.py']
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal23b-* or GOAL23B-* record is hashed as well.
REPORTS = ['migration/GOAL23B.md', 'migration/GOAL23B-ACCEPTANCE.md', 'migration/goal23b-static-review.md', 'migration/goal23b-resource-ownership.json',
           'migration/goal23b-localization-review.json']
RESOURCE_OWNERSHIP = REPORTS[3]
BATCH_RECORD = re.compile(r'migration/(goal23b-[^/]+\.(json|md)|GOAL23B-[^/]+\.md)')
SHARED_RECORDS = ['migration/GOAL23.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md']
# The read-only batch 23D creates exactly these two paths (baseline concurrent_session); never packaged, never attributed to this batch.
CONCURRENT_23D = ['migration/RBMK-SCOPE.md', 'tools/migration/verify_goal23d_rbmk_scope.py']
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + SHARED_RECORDS
EXPECTED_KEY_COUNT, EXPECTED_KINDS = 47, {'upstream': 26, 'local': 21}
PROVIDER_ADD_ITEM = re.compile(r'this\.add\(NtmItems\.(PELLET_RTG\w*), (?:(DESC), |this\.getName\(DepletedRTGMaterial\.(\w+)\), )?"(.*)"\);$')
PROVIDER_ADD_KEY = re.compile(r'this\.add\("([\w.]+)", ')
NEW_TESTS = ['rtg_pellet_lifespans', 'rtg_pellet_decay', 'rtg_pellet_scaled_power', 'rtg_pellet_depletion', 'rtg_pellet_recipes', 'rtg_pellet_hazards',
             'rtg_pellet_stack_size', 'rtg_pellet_living_radium', 'rtg_pellet_tooltip_and_use']
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'compile-start.log', 'add_localization.py', 'import_textures.py', 'write_review.py',
                  'make_review_diff.py', 'review-production.diff', 'chain.sh', 'handoff-localization.md', 'handoff-gametest.md', 'handoff-verifier.md',
                  'handoff-packaging.md')
GAMETEST_LOG = 'build/migration/goal23b/gametest-final.log'
NEW_SUITE = 'verify_goal23b_rtg.py --gametest-log build/migration/goal23b/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_GROUP, FEATURE_MATERIALS = 'rtg-power', 'materials'
RADIATION_NOTE = ('Goal23B: RTG pellets carry the original\'s hazards (Pu-238 pellet 15 RAD/s, radium 11.25, lead-209 15,000 with fire and blindness, gold-198 750, '
                  'polonium-210 112.5), falling linearly as they decay; hold the strong ones only in separately authorized disposable worlds. ')
VERIFIER_REFERENCE = re.compile(r'(?:ItemRTGPellet|ItemRTGPelletDepleted|RTGUtil|HazardRegistry|ModItems|MineralRecipes|MachineConfig|VersatileConfig|'
                                r'HazardModifierRTGRadiation)\.java:\d+(?:-\d+)?')
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_MOD_ITEMS, O_PELLET, O_DEPLETED = ORIGINAL+'items/ModItems.java', ORIGINAL+'items/machine/ItemRTGPellet.java', ORIGINAL+'items/machine/ItemRTGPelletDepleted.java'
O_UTIL, O_MODIFIER, O_HAZARD = ORIGINAL+'util/RTGUtil.java', ORIGINAL+'hazard/modifier/HazardModifierRTGRadiation.java', ORIGINAL+'hazard/HazardRegistry.java'
O_RECIPES, O_MACHINE_CONFIG, O_VERSATILE = ORIGINAL+'crafting/MineralRecipes.java', ORIGINAL+'config/MachineConfig.java', ORIGINAL+'config/VersatileConfig.java'
O_SOURCES = [O_PELLET, O_DEPLETED, O_UTIL, O_MODIFIER, O_MACHINE_CONFIG]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'depleted_item_container': (O_MOD_ITEMS, 'pellet_rtg_depleted = new ItemRTGPelletDepleted()'),
    **{'pellet_'+i: (O_MOD_ITEMS, i+' = new ItemRTGPellet(') for i in PELLET_IDS},
    **{'recipe_'+i: (O_RECIPES, 'new ItemStack(ModItems.'+i+'), new Object[]') for i in PELLET_IDS},
    **{'recycle_'+m: (O_RECIPES, 'DepletedRTGMaterial.'+m.upper()+'.ordinal()) });') for m in DEPLETED_MATERIALS},
    'hazard_helper': (O_HAZARD, 'private static void registerRTGPellet(Item pellet, float base, float target, float hot, float blinding)'),
    'hazard_depleted_neptunium': (O_HAZARD, 'DepletedRTGMaterial.NEPTUNIUM.ordinal()), makeData(RADIATION, np237 * rtg)'),
    'modifier': (O_MODIFIER, 'public class HazardModifierRTGRadiation'),
    'config_scale_rtg_power': (O_MACHINE_CONFIG, '"9.00_scaleRTGPower"'),
    'config_do_rtgs_decay': (O_MACHINE_CONFIG, '"9.01_doRTGsDecay"'),
    'rtg_decay': (O_VERSATILE, 'public static boolean rtgDecay()'),
    'scale_rtg_power': (O_VERSATILE, 'public static boolean scaleRTGPower()'),
    'get_lifespan': (O_UTIL, 'public static long getLifespan(float halfLife'),
    'pellet_facts': (O_PELLET, 'facts = new String[]'),
}
# Original rows, parsed from the stored blobs: pellets (ModItems), recipes (MineralRecipes), hazard rows (HazardRegistry).
O_PELLET_ROW = re.compile(r'(\w+) = new ItemRTGPellet\((.*?)\)\.setDecays\(DepletedRTGMaterial\.(\w+), \(long\) \(RTGUtil\.getLifespan\(([\d.]+)F, '
                          r'HalfLifeType\.(\w+), false\) \* 1\.5\)\)')
NEO_PELLET_ROW = re.compile(r'ITEMS\.register\("(pellet_rtg\w*)", \(\) -> new RTGPelletItem\(new Item\.Properties\(\), (.*?)\)\.setDecays\(DepletedRTGMaterial\.(\w+), '
                            r'\(long\) \(RTGUtil\.getLifespan\(([\d.]+)F, HalfLifeType\.(\w+), false\) \* 1\.5\)\)\);(?: // :(\d+))?')
O_RECIPE_ROW = re.compile(r'new ShapelessOreRecipe\(new ItemStack\(ModItems\.(pellet_rtg\w*)\), new Object\[\] \{ ([^}]*) \}\)')
O_RECYCLE_ROW = re.compile(r'addShapelessRecipe\(new ItemStack\(ModItems\.(\w+), (\d+)\), new Object\[\] \{ new ItemStack\(ModItems\.pellet_rtg_depleted, 1, '
                           r'DepletedRTGMaterial\.(\w+)\.ordinal\(\)\) \}\)')
O_HAZARD_ROW = re.compile(r'registerRTGPellet\((\w+), (.*)\);$')
NEO_HAZARD_ROW = re.compile(r'registerRTGPellet\((\w+), (.*)\); // :(\d+)$')


def scope_text(pellets, depleted, recipes, recycling, models, textures, key_count, kinds, rows, new_tests, total_tests):
    return (f'Goal23B (RTG pellets, item layer only; the RT generator that consumes them is Goal23C): RTGPelletItem registers {pellets} pellets in the original\'s '
            f'construction order (pellet_rtg keeps its ID, {pellets - 1} new IDs pellet_rtg_radium, _weak, _strontium, _cobalt, _actinium, _americium, _polonium, _gold '
            f'and _lead) with the original heat, depletion material and lifespan (RTGUtil.getLifespan x 1.5; gold and lead read doRTGsDecay at run time), stack '
            f'size 1, and the remaining life in the custom data long PELLET_DEPLETION (a missing key means the maximum and is not written back, a NEO-only '
            f'equivalent of the original\'s write-back in the tooltip, so pellet_rtg stacks saved before stay valid); decay runs through RTGUtil.updateRTGs / '
            f'handleDecay (called by the Goal23C machine) into pellet_rtg_depleted (RTGPelletDepletedItem, an EnumMultiItem with the {depleted} materials BISMUTH, '
            f'MERCURY, NEPTUNIUM, LEAD, ZIRCONIUM and NICKEL as hbmsntm:meta 0-{depleted - 1}, craftRemainder plate_iron); new config section rtg with scaleRTGPower '
            f'(false) and doRTGsDecay (true), each OR 5.28 mode (rtgDecay / scaleRTGPower as the original VersatileConfig); the {rows} original hazard rows '
            f'(HazardRegistry.registerRTGPellets, HazardModifierRTGRadiation: radiation falls linearly toward 0 with the depletion); {recipes} shapeless pellet recipes '
            f'(three billets and an iron plate) and {recycling} recycling recipes (bismuth, lead, neptunium, zirconium; the mercury and nickel recipes are not '
            f'registered because NEO has no mercury ingot and no nickel); {models} item models (the depleted pellet with hbmsntm:item_meta overrides); {textures} '
            f'textures imported byte for byte; the CONTROL creative tab lists the pellets and the depleted pellets; {key_count} language keys ({kinds.get("upstream", 0)} '
            f'upstream with the original Chinese, {kinds.get("local", 0)} local); {new_tests} GameTests are added ({total_tests} in total). Gameplay impact: RTG pellets are '
            f'radioactive like the original (Pu-238 pellet 15 RAD/s and hot 3, radium 11.25, weak 5.25, lead-209 15,000 with fire 7 and blindness 50, gold-198 750 '
            f'with fire 5, polonium-210 112.5 with fire 3); only the Pu-238, weak and radium pellets have NEO survival sources, the other seven are craftable only '
            f'from billets NEO cannot produce yet.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal23b release directory: '+rel


def protected_paths(base):
    """What the goal23a packager protected (built there from the Goal21A..Goal22D starts and receipts, the goal22d receipt and the goal23a start), plus
    every path the goal23a receipt hashes (base previous_receipt_protected_paths), the paths the older receipts hash (the 23B baseline lists the goal22d
    receipt among them) and every release file of the frozen start (the goal23a package included). The records that already drifted (the acceptance
    checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md) are pinned at their Goal23B start hash (baseline files) instead of any receipt hash or any
    earlier start hash. One path never carries two hashes. Returns (protected, repinned) where repinned maps a record to the pin the goal23a packager set
    at its Goal23A start hash, for the records that changed between the two starts (expected none)."""
    goal23a_start = read(GOAL23A_BASELINE)
    out = dict(goal23a_protected_paths(goal23a_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'], 'Start drift path is not a frozen file: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal23a_start['files'].get(p))
        if earlier is not None and earlier != base['files'][p]: repinned[p] = earlier
        out[p] = base['files'][p]
    assert all(p.endswith('-ACCEPTANCE.md') for p in repinned), 'A non-checklist pin changed between the Goal23A and Goal23B starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal23a_start):
    """{path: {receipts, start_sha256, goal23a_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal23a receipt'] = base['previous_receipt_protected_paths'][p]
        start = base['files'][p]
        newest = receipts.get('goal23a receipt')
        if newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21 and Goal 22 in-game acceptance result lines, the O1 record notes or the '
                           'thorium follow-up section); the goal23a receipt does not hash it. Frozen at the Goal23B start hash; this batch must not change it and '
                           'no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal23a) records the start hash. Frozen at '
                           'the start hash; this batch must not change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal23a package; the goal23a receipt hash is older than the start hash. Frozen at the start hash; this batch '
                           'must not change it and the goal23a receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal23a_start_sha256=goal23a_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned:
            entry['repinned_from_goal23a_start_pin_sha256'] = repinned[p]
        out[p] = entry
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
    if p in SHARED_RECORDS: return 'records'
    return None


def report_problems(report, required):
    """Why verify/report.json (the passing tools/migration/verify_goal23b_rtg.py report) is not a passing run, [] otherwise: the goal23a / goal22b checks,
    reading the summary's mutations_applied as the mutation total (the goal23b report has no mutations_total), plus a skipped mutation."""
    summary = report.get('summary') if isinstance(report.get('summary'), dict) else {}
    if 'mutations_total' not in summary and 'mutations_applied' in summary:
        report = dict(report, summary=dict(summary, mutations_total=summary['mutations_applied']))
    problems = verifier_problems(report, required)
    if summary.get('mutations_skipped'): problems.append('mutations skipped: '+str(summary['mutations_skipped'][:5]))
    return problems


def original_text(path):
    return original_blob(path).decode('utf-8').replace('\r\n', '\n')


def enum_names(text, name):
    """Constants of `enum name { ... }` in source order (comments and a trailing ';' ignored)."""
    match = re.search(r'enum\s+'+name+r'\s*\{(.*?)\}', strip_java_comments(text), re.S)
    return [t.strip().split('(')[0].strip() for t in re.split(r'[,;]', match.group(1)) if t.strip()] if match else None


def provider_keys(lines):
    """The language keys the given NtmLanguageProvider lines add (pellet item names, descriptions and depleted names through NtmItems constants, plain keys)."""
    keys, other = [], []
    for raw in lines:
        line = raw.strip()
        m = PROVIDER_ADD_ITEM.match(line)
        if m:
            const, desc, material, _ = m.groups()
            keys.append('item.hbmsntm.'+const.lower()+('.desc' if desc else '')+('.'+material.lower() if material else ''))
            continue
        m = PROVIDER_ADD_KEY.match(line)
        if m: keys.append(m.group(1)); continue
        other.append(line)
    return keys, other


def one_line_replaced(old, new, token):
    """(removed start line, inserted [(index, line)]) when the new text is the old text with exactly one line replaced (the removed line contains the token)
    and lines inserted; otherwise (None, why)."""
    removed = Counter(old) - Counter(new)
    if sum(removed.values()) != 1: return None, f'removes {sum(removed.values())} start lines, expected exactly 1'
    line = next(iter(removed))
    if token not in line: return None, f'the removed start line {line.strip()[:80]!r} does not contain {token!r}'
    rest = list(old)
    rest.pop(rest.index(line))
    inserted = insertions(rest, new)
    if inserted is None: return None, 'another start line was changed or moved'
    return line, inserted


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
    goal23a_start = read(GOAL23A_BASELINE)

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal23B commits nothing), the recorded start: HEAD plus the 24 Goal23A paths.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at 6a11998d'
    assert start_head.startswith(PLANNING_PREFIX) and start_head == prior_receipt['target_start_commit'] == prior_receipt['target_head_at_packaging'] \
        == prior_receipt['planning_commit']['id'], 'The frozen start is not the Goal 23 planning commit the goal23a receipt records'
    assert base['pending_small_fixes'] == [], 'The frozen start has a pending small fix'
    assert base['concurrent_session']['owned_paths'] == CONCURRENT_23D and base['concurrent_session']['present_at_start'] == [], \
        'The frozen start does not record the 23D concurrent session as expected'
    assert set(base['start_content']) == {'committed', 'uncommitted'}, 'Baseline start content differs'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal23B: '+head
    assert git_ro(ROOT, 'rev-parse', 'HEAD~1').strip().startswith(GOAL22_CLOSEOUT), 'NEO HEAD~1 is not the Goal 22 close-out commit'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b',
                                                          'goal22c', 'goal22d'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['dirty_paths'] == len(base['dirty_paths']) and startup['frozen_file_hashes'] == len(base['files']) \
        and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['previous_jar_sha256'] == base['previous_release']['sha256'] and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']), 'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_verified'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal23a generated tree'
    # The start tree is HEAD plus the goal23a delivery, uncommitted: the dirty paths are exactly the goal23a receipt's changed files at their after hashes.
    goal23a_paths = list(base['goal23a_paths'])
    assert sorted(goal23a_paths) == sorted(base['dirty_paths']) == sorted(c['path'] for c in prior_receipt['changed_files']), \
        'The start dirty paths are not the goal23a receipt changed files'
    receipt_after = {c['path']: c['after_sha256'] for c in prior_receipt['changed_files']}
    for p in goal23a_paths: assert base['files'][p] == receipt_after[p], 'The start copy of a goal23a path differs from the receipt after hash: '+p
    # build/libs at the start is the goal23a package byte for byte.
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal23a package, every old release file and the protected evidence.
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal23a receipt list + the goal23a package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal23a receipt count + the goal23a release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal23a receipt'
    assert base['previous_receipt_evidence_drift'] == [], 'The goal23a receipt evidence had already drifted at the start: '+str(base['previous_receipt_evidence_drift'])
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal23a_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal23a receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal23b. Everything else equals its start hash. The 23D paths are listed apart.
    changes = changed_since_start(base)
    concurrent_23d = {p: (sha(ROOT/p) if (ROOT/p).is_file() else None) for p in CONCURRENT_23D}
    for p in CONCURRENT_23D:
        assert p not in base['files'] and p not in protected, 'A 23D concurrent path is part of the frozen start or protected evidence: '+p
        changes.pop(p, None)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal23B start that the owner table does not list (production outside the 13 Java files, the 15 textures, zh_cn.json '
         'and the mapping, a protected record, an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal23B start: '+str(deleted)
    for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD] + GENERATED + SHARED_RECORDS + REPORTS[:1]: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION if p.startswith('src/')})
    need(not outside, 'src/main change outside the 13 Java files, the 15 textures and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p),
                        **({'start_owner': OWNER_23A} if p in goal23a_paths else {})) for p, s in sorted(changes.items())]
    # The Goal23A paths this batch does not modify still equal the goal23a receipt after hash (they equal their start hash, checked above against the receipt).
    goal23a_unchanged = sorted(p for p in goal23a_paths if p not in changes)
    for p in goal23a_unchanged: assert sha(ROOT/p) == receipt_after[p], 'A goal23a path changed without being in the change list: '+p
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
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}')
    for p in NEW_JAVA:
        if (ROOT/p).is_file():
            eol = eol_counts((ROOT/p).read_bytes())
            need(eol[0] == 0 or eol[1] == 0, f'{p} mixes CRLF and LF line endings: {eol}')

    # Production Java facts: insert-only providers/config/tabs, the two one-line replacements, every line edit counted.
    insert_summary, edit_summary, replaced_summary, inserted_lines = {}, {}, {}, {}
    for p in MODIFIED_JAVA:
        if p not in start_text: continue
        start_lines, live_lines = lines_of(start_text[p]), lines_of((ROOT/p).read_bytes())
        edit_summary[p] = edit_counts(start_lines, live_lines)
        if p in INSERT_ONLY:
            inserted = insertions(start_lines, live_lines)
            if not need(inserted is not None, f'{p} is not insert-only against the start copy (a start line was changed, moved or removed)'): continue
            insert_summary[p] = len(inserted)
            inserted_lines[p] = [l for _, l in inserted]
            need(edit_summary[p]['removed'] == 0, f'{p} removes {edit_summary[p]["removed"]} start lines (insert-only expected)')
        elif p in ONE_LINE_REPLACED:
            line, inserted = one_line_replaced(start_lines, live_lines, ONE_LINE_REPLACED[p])
            if not need(line is not None, f'{p} is not the start copy with exactly one line replaced and lines inserted: {inserted}'): continue
            replaced_summary[p] = dict(removed_line=line.strip(), inserted_lines=len(inserted))
    # Language provider: the inserted lines add exactly the batch keys (items through NtmItems constants), the rest are comments and one import.
    provider_added = []
    if PROVIDER in inserted_lines:
        provider_added, provider_other = provider_keys(inserted_lines[PROVIDER])
        stray = [l for l in provider_other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} inserts lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(provider_added) == len(set(provider_added)), f'{PROVIDER} adds a language key twice')
    # HazardGameTests: the pellet_rtg deferral guard and comments only; no test method added or lost, the annotation count unchanged.
    if HAZARD_TESTS in start_text:
        names_now = set(GAMETEST_METHOD.findall((ROOT/HAZARD_TESTS).read_text(encoding='utf-8')))
        names_start = set(GAMETEST_METHOD.findall((START_FILES/HAZARD_TESTS).read_text(encoding='utf-8')))
        need(names_now == names_start, f'{HAZARD_TESTS} changed its GameTest methods: added {sorted(names_now - names_start)}, lost {sorted(names_start - names_now)}')
        need(annotations(ROOT/HAZARD_TESTS) == annotations(START_FILES/HAZARD_TESTS), f'{HAZARD_TESTS} changed its @GameTest annotation count')
        removed = Counter(lines_of(start_text[HAZARD_TESTS])) - Counter(lines_of((ROOT/HAZARD_TESTS).read_bytes()))
        need(not any('@GameTest' in l for l in removed) and any('pellet_rtg' in l for l in removed),
             f'{HAZARD_TESTS} removed lines are not the pellet_rtg deferral guard and comments: {sorted(removed)[:3]}')
    # Config: section rtg with the two keys of the original MachineConfig (defaults and comments).
    config = {}
    if COMMON_CONFIG in inserted_lines:
        text = '\n'.join(inserted_lines[COMMON_CONFIG])
        config = {k: dict(default=d, comment=c) for c, k, d in re.findall(r'\.comment\("([^"]*)"\)\s*\.translation\("hbmsntm\.configuration\.\w+"\)\s*\.define\("(\w+)", (\w+)\)', text)}
        need('builder.push("rtg")' in text and set(config) == {'scaleRTGPower', 'doRTGsDecay'}, f'{COMMON_CONFIG} does not add exactly the rtg section with scaleRTGPower and doRTGsDecay: {sorted(config)}')
        need(config.get('scaleRTGPower', {}).get('default') == 'false' and config.get('doRTGsDecay', {}).get('default') == 'true',
             f'{COMMON_CONFIG} rtg defaults are not scaleRTGPower false / doRTGsDecay true: {config}')
    # The original, parsed from the stored blobs at the recorded commit (independent of the worktree's line endings).
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    mod_items, mineral = original_text(O_MOD_ITEMS), original_text(O_RECIPES)
    original_pellets = {m.group(1): dict(heat=m.group(2), depleted=m.group(3), half_life=m.group(4), type=m.group(5)) for m in O_PELLET_ROW.finditer(mod_items)}
    assert sorted(original_pellets) == sorted(PELLET_IDS), 'The original ModItems pellets are not the ten pellet IDs: '+str(sorted(original_pellets))
    original_order = [m.group(1) for m in O_PELLET_ROW.finditer(mod_items)]
    original_recipes = {m.group(1): sorted(('hbmsntm:plate_iron' if t == 'IRON.plate()' else 'hbmsntm:'+t.replace('ModItems.', '')) for t in m.group(2).split(', '))
                        for m in O_RECIPE_ROW.finditer(mineral)}
    assert sorted(original_recipes) == sorted(PELLET_IDS), 'The original MineralRecipes pellet rows are not the ten pellet IDs: '+str(sorted(original_recipes))
    original_recycle = {m.group(3): ('hbmsntm:'+m.group(1), int(m.group(2))) for m in O_RECYCLE_ROW.finditer(mineral)}
    original_materials = enum_names(original_text(O_DEPLETED), 'DepletedRTGMaterial')
    assert original_materials == [m.upper() for m in DEPLETED_MATERIALS], 'The original DepletedRTGMaterial order differs: '+str(original_materials)
    assert sorted(original_recycle) == sorted(m.upper() for m in DEPLETED_MATERIALS if m != 'nickel'), 'The original recycling rows differ: '+str(sorted(original_recycle))
    # NEO NtmItems pellets against the original rows (heat, material, half-life, type, line note) and the depleted enum order.
    pellets = []
    if (ROOT/ITEMS).is_file() and ITEMS in changes:
        items_text = (ROOT/ITEMS).read_text(encoding='utf-8').replace('\r\n', '\n')
        neo_rows = {m.group(1): m for m in NEO_PELLET_ROW.finditer(items_text)}
        neo_order = [m.group(1) for m in NEO_PELLET_ROW.finditer(items_text)]
        need(sorted(neo_rows) == sorted(PELLET_IDS) and neo_order == original_order, f'{ITEMS} registers the pellets {neo_order}, not the ten in the original order {original_order}')
        for i in PELLET_IDS:
            if i not in neo_rows: continue
            m, o = neo_rows[i], original_pellets[i]
            heat_neo, heat_old = m.group(2), o['heat']
            same_heat = heat_neo == heat_old if heat_neo.isdigit() else re.findall(r'\? (\d+) : (\d+)', heat_neo) == re.findall(r'\? (\d+) : (\d+)', heat_old) != []
            line = int(original_refs['pellet_'+i].rsplit(':', 1)[1])
            need(same_heat and m.group(3) == o['depleted'] and m.group(4) == o['half_life'] and m.group(5) == o['type'] and (m.group(6) is None or int(m.group(6)) == line),
                 f'{ITEMS} pellet {i} differs from the original ModItems row: heat {heat_neo!r}/{heat_old!r}, {m.group(3)}/{o["depleted"]}, {m.group(4)}/{o["half_life"]}, '
                 f'{m.group(5)}/{o["type"]}, line note {m.group(6)}/{line}')
            pellets.append(dict(id=i, heat=heat_neo, depleted=m.group(3), half_life=float(m.group(4)), half_life_type=m.group(5), original=original_refs['pellet_'+i],
                                neo_line=items_text[:m.start()].count('\n')+1))
        need('craftRemainder(PLATE_IRON.get())' in items_text and 'new RTGPelletDepletedItem(' in items_text,
             f'{ITEMS} does not register pellet_rtg_depleted as RTGPelletDepletedItem with craftRemainder(PLATE_IRON.get())')
    if (ROOT/DEPLETED_ITEM).is_file():
        need(enum_names((ROOT/DEPLETED_ITEM).read_text(encoding='utf-8'), 'DepletedRTGMaterial') == original_materials,
             f'{DEPLETED_ITEM} DepletedRTGMaterial order is not the original {original_materials}')
    # Imported textures: byte for byte equal to the original worktree file and its stored blob, and to the ownership record.
    imported = {}
    ownership = None
    if need((ROOT/RESOURCE_OWNERSHIP).is_file(), 'record missing: '+RESOURCE_OWNERSHIP):
        ownership = read(ROOT/RESOURCE_OWNERSHIP)
        entries = {a.get('target_path'): a for a in ownership.get('assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(ASSETS), f'{RESOURCE_OWNERSHIP} does not list the {len(ASSETS)} textures at {SOURCE_HEAD[:8]}')
    for target, original in ASSETS.items():
        if not (ROOT/target).is_file(): continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        entry = {a.get('target_path'): a for a in (ownership or {}).get('assets', [])}.get(target, {})
        imported[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size,
                                original_worktree_sha256=sha(SOURCE/original), original_blob_sha256=hashlib.sha256(blob).hexdigest(), original_blob_bytes=len(blob),
                                source_last_change_commit=entry.get('source_last_change_commit'))
        need((ROOT/target).read_bytes() == checked_out == blob, f'{target} is not byte-identical to the original file {original} (worktree and blob at {SOURCE_HEAD[:8]})')
        if entry:
            need(entry.get('source_path') == original and entry.get('sha256') == sha(ROOT/target) and entry.get('bytes') == (ROOT/target).stat().st_size,
                 f'{RESOURCE_OWNERSHIP} entry differs from the live texture or the original path: {target}')
    unchanged_texture = None
    if (ROOT/UNCHANGED_TEXTURE).is_file():
        original = O_TEXTURES+'pellet_rtg.png'
        unchanged_texture = dict(path=UNCHANGED_TEXTURE, sha256=sha(ROOT/UNCHANGED_TEXTURE), original_path=original, original_sha256=sha(SOURCE/original))
        need(UNCHANGED_TEXTURE not in changes and sha(ROOT/UNCHANGED_TEXTURE) == base['files'][UNCHANGED_TEXTURE] == sha(SOURCE/original),
             f'{UNCHANGED_TEXTURE} changed or differs from the original')
        if ownership: need([u.get('target_sha256') for u in ownership.get('unchanged', [])] == [sha(ROOT/UNCHANGED_TEXTURE)], f'{RESOURCE_OWNERSHIP} unchanged entry differs from the live pellet_rtg.png')
    # Hazard rows: the eleven registerRTGPellets rows against the original HazardRegistry.java:337-347 (arguments, order, line numbers), the call site and the modifier.
    hazard_rows = []
    registry_text = (ROOT/HAZARD_REGISTRY).read_text(encoding='utf-8').replace('\r\n', '\n') if (ROOT/HAZARD_REGISTRY).is_file() else ''
    body = re.search(r'private static void registerRTGPellets\(\) \{\n(.*?)\n    \}', registry_text, re.S)
    if need(body is not None, f'{HAZARD_REGISTRY} has no registerRTGPellets()'):
        body_lines = [l.strip() for l in body.group(1).split('\n') if l.strip()]
        o_lines = original_text(O_HAZARD).split('\n')
        o_rows = [(n, l.strip()) for n, l in enumerate(o_lines, 1) if O_HAZARD_ROW.match(l.strip()) or 'DepletedRTGMaterial.NEPTUNIUM.ordinal()), makeData(RADIATION, np237 * rtg)' in l]
        need(len(o_rows) == len(body_lines) == 11, f'registerRTGPellets rows: original {len(o_rows)}, NEO {len(body_lines)}, expected 11')
        for (n, o_text), l in zip(o_rows, body_lines):
            m = NEO_HAZARD_ROW.search(l)
            o = O_HAZARD_ROW.search(o_text)
            if m and o:
                same = m.group(1).lower() == o.group(1).lower() and m.group(2) == o.group(2) and int(m.group(3)) == n
            else:
                same = ('MetaHelper.newStack(PELLET_RTG_DEPLETED, 1, DepletedRTGMaterial.NEPTUNIUM.ordinal()), makeData(RADIATION, np237 * rtg)); // :%d' % n) in l
            need(same, f'{HAZARD_REGISTRY} registerRTGPellets row {l!r} differs from the original HazardRegistry.java:{n} {o_text!r}')
            hazard_rows.append(dict(original=f'{O_HAZARD}:{n}', original_text=o_text, neo_text=l))
        need(registry_text.find('registerMaterialAddendum();') != -1 and registry_text.find('registerMaterialAddendum();') < registry_text.find('registerRTGPellets();'),
             f'{HAZARD_REGISTRY} does not call registerRTGPellets() after registerMaterialAddendum()')
    if (ROOT/RTG_MODIFIER).is_file():
        need('instanceof RTGPelletItem' in (ROOT/RTG_MODIFIER).read_text(encoding='utf-8'), RTG_MODIFIER+' does not guard on RTGPelletItem')
    # features.json group rtg-power (mapped paths) and the materials note.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}

    # 4. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    keys = sorted(provider_added)
    need(len(keys) == EXPECTED_KEY_COUNT, f'{PROVIDER} adds {len(keys)} language keys, expected {EXPECTED_KEY_COUNT}')
    expected_delta = dict(added=keys, removed=[], changed=[])
    need(en_delta == expected_delta, 'generated en_us.json delta is not the provider keys (all old keys unchanged): '+json.dumps(en_delta, ensure_ascii=False)[:600])
    need(zh_delta == expected_delta, 'zh_cn.json delta is not the provider keys: '+json.dumps(zh_delta, ensure_ascii=False)[:600])
    need(map_delta == expected_delta, 'zh_cn-map.json delta is not the provider keys: '+json.dumps(map_delta, ensure_ascii=False)[:600])
    need(len(en_now) == prior_receipt['language']['totals']['en_us'] + len(keys) and len(zh_now) == prior_receipt['language']['totals']['zh_cn'] + len(keys)
         and len(map_now) == prior_receipt['language']['totals']['zh_cn_map'] + len(keys),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal23a totals {prior_receipt["language"]["totals"]} + {len(keys)}')
    language_kinds = {}
    if map_delta == expected_delta:
        language_kinds = dict(Counter(map_now[k].get('kind') for k in keys))
        need(language_kinds == EXPECTED_KINDS, f'zh_cn-map.json kinds of the new entries are {language_kinds}, expected {EXPECTED_KINDS}')
        bad = []
        for k in keys:
            e = map_now[k]
            if e.get('target_en') != en_now.get(k) or e.get('target_zh') != zh_now.get(k): bad.append(k)
            elif e.get('kind') == 'upstream' and (not e.get('source_key') or e.get('source_zh') != e.get('target_zh') or e.get('source_en') != e.get('target_en')): bad.append(k)
            elif e.get('kind') == 'local' and not str(e.get('reason', '')).strip(): bad.append(k)
        need(not bad, 'zh_cn-map.json entries do not match en_us.json / zh_cn.json or lack source/reason data: '+str(bad))
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal23a generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected pellet models, recipes and advancements: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == [EN_ENTRY], f'Generated resources changed since the start: {generated_changed[:5]} (expected only {EN_ENTRY})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    need(generated_since == sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED]),
         'Generated files changed since the start differ from the stamp, en_us.json and the expected additions: extra %s, missing %s' % (
             sorted(set(generated_since) - set(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED]))[:8],
             sorted(set(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED]) - set(generated_since))[:8]))
    # Recipes (computed from the generated JSON) against the original MineralRecipes rows.
    recipes = {}
    for rid in RECIPE_IDS:
        path = ROOT/GENERATED_ROOT/'data/hbmsntm/recipe'/(rid+'.json')
        if not path.is_file(): continue
        data = read(path)
        ingredients = []
        for ing in data.get('ingredients', []):
            if 'item' in ing: ingredients.append(ing['item'])
            else: ingredients.append(ing.get('items', '?')+json.dumps(ing.get('components', {}), sort_keys=True)+('' if ing.get('strict') is not True else ' strict'))
        recipes[rid] = dict(type=data.get('type'), ingredients=ingredients, result=data.get('result'))
    if len(recipes) == len(RECIPE_IDS):
        for rid in PELLET_IDS:
            r = recipes[rid]
            need(r['type'] == 'minecraft:crafting_shapeless' and sorted(r['ingredients']) == original_recipes[rid] and r['result'] == {'count': 1, 'id': 'hbmsntm:'+rid},
                 f'recipe {rid} differs from the original MineralRecipes row: {r} vs {original_recipes[rid]}')
        for m in RECYCLED_MATERIALS:
            rid, r = 'pellet_rtg_depleted_'+m, recipes['pellet_rtg_depleted_'+m]
            o_result, o_count = original_recycle[m.upper()]
            ordinal = DEPLETED_MATERIALS.index(m)
            need(r['type'] == 'minecraft:crafting_shapeless' and r['ingredients'] == ['hbmsntm:pellet_rtg_depleted'+json.dumps({'hbmsntm:meta': ordinal}, sort_keys=True)]
                 and r['result'] == {'count': o_count, 'id': o_result}, f'recipe {rid} differs from the original recycling row: {r} vs {o_result} x{o_count}, meta {ordinal}')
    need(not any((ROOT/GENERATED_ROOT/'data/hbmsntm/recipe'/(s+'.json')).exists() for s in SKIPPED_RECIPES), 'a recycling recipe for mercury or nickel exists: NEO has no mercury ingot and no nickel')
    # Mapped paths: every changed path inside the compare inventory must be matched by a feature group.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    if need(FEATURE_GROUP in by_id, 'migration/features.json has no group '+FEATURE_GROUP):
        group_entry = by_id[FEATURE_GROUP]
        need(group_entry.get('status') == 'partial-unverified' and group_entry.get('reviewed_source_commit') == SOURCE_HEAD,
             f'features.json group {FEATURE_GROUP} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in O_SOURCES + [v for v in ASSETS.values()] if not feature_matches(group_entry, 'source', p)]
        need(not missing_source, f'features.json group {FEATURE_GROUP} lists in neither source_paths nor source_watch: {missing_source[:4]} ({len(missing_source)} paths)')
        missing_target = [p for p in NEW_JAVA if not feature_matches(group_entry, 'target', p)]
        need(not missing_target, f'features.json group {FEATURE_GROUP} lacks the new classes in target_paths/target_watch: {missing_target}')
        watch = [GENERATED_ROOT+p for p in EXPECTED_GENERATED] + [TOOLS[0]]
        missing_watch = [p for p in watch if not feature_matches(group_entry, 'target', p)]
        need(not missing_watch, f'features.json group {FEATURE_GROUP} lacks the generated models/recipes/advancements or the verifier in target_watch: {missing_watch[:4]} ({len(missing_watch)} paths)')
        absent = [p for p in group_entry.get('source_paths', []) if not (SOURCE/p).is_file()]
        need(not absent, f'features.json group {FEATURE_GROUP} source_paths missing in the original: {absent}')
    if need(FEATURE_MATERIALS in by_id, 'migration/features.json has no group '+FEATURE_MATERIALS):
        need('Goal23B' in ' '.join(by_id[FEATURE_MATERIALS].get('notes', [])), f'migration/features.json group {FEATURE_MATERIALS} notes do not mention Goal23B')
    need(set(by_id) == set(start_features) | {FEATURE_GROUP}, 'features.json group ids are not the start ids + '+FEATURE_GROUP+': '+str(sorted(set(by_id) ^ (set(start_features) | {FEATURE_GROUP}))))
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))

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
    new_test_names = sorted(GAMETEST_METHOD.findall((ROOT/RTG_TESTS).read_text(encoding='utf-8'))) if (ROOT/RTG_TESTS).is_file() else []
    rtg_annotations = annotations(ROOT/RTG_TESTS) if (ROOT/RTG_TESTS).is_file() else 0
    need(new_test_names == sorted(NEW_TESTS), f'{RTG_TESTS} holds the GameTest methods {new_test_names}, not {sorted(NEW_TESTS)}')
    need(gametest_added == len(new_test_names) == rtg_annotations, f'GameTest sources grew by {gametest_added} tests, RTGPelletGameTests holds {rtg_annotations} annotations and '
         f'{len(new_test_names)} methods (another GameTest file changed?)')
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
            need(all(f'[hbm-rtg] {n} passed' in text for n in new_test_names), 'GameTest log lacks "[hbm-rtg] <name> passed" for: '+str([n for n in new_test_names if f'[hbm-rtg] {n} passed' not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal23b/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal23b/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal23b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE:
        if not need((OUT/name).is_file(), 'start evidence missing: build/migration/goal23b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain.sh output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal23b/'+name+' (written by chain.sh final)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start copies, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    if diff_path.is_file() and diff_path.stat().st_size and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        listed_in_diff = NEW_JAVA + MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal23a final run plus the Goal23B verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert NEW_SUITE not in reference_suites, 'The Goal23B suite is already in the goal23a final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal23b/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        assert set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal23a final set + the Goal23B verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE})))
        entry = final['suites'][NEW_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, NEW_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal23b/'+VERIFY_REPORT+' (tools/migration/verify_goal23b_rtg.py report)'):
        report = read(OUT/VERIFY_REPORT)
        problems = report_problems(report, [p for p in production_changed if not p.startswith(RES) or p == ZH_INPUT])
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        mutations = report.get('mutations')
        mutation_entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
        detected = summary_part.get('mutations_detected', sum(1 for e in mutation_entries if isinstance(e, dict) and e.get('detected') is True))
        total = summary_part.get('mutations_total', summary_part.get('mutations_applied', len(mutation_entries)))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=TOOLS[0],
                        tool_sha256=sha(ROOT/TOOLS[0]) if (ROOT/TOOLS[0]).is_file() else None, mutations_detected=f'{detected}/{total}', mutations_total=total)
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(VERIFIER_REFERENCE.findall(json.dumps(report, ensure_ascii=False))))
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree): the original unchanged, the target exactly the goal23a receipt's compare target
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
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal23b/'+COMPARE+' (compare against '+SNAPSHOT+'; expected target set: %d paths)' % len(expected_target)):
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

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal23b.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal23a) package (run build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 15 textures and every compiled class equal the sources.
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [e for e, t in asset_entries.items() if e not in names or not (ROOT/t).is_file() or jar.read(e) != (ROOT/t).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json, the textures or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == en_delta == expected_delta and zh_jar == zh_delta == expected_delta,
                 f'JAR en_us.json or zh_cn.json delta against the previous package is not the {len(keys)} RTG keys: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        generated_entries = set(generated_added)
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if n.endswith('.class') and owner_class(n) in PRODUCTION_JAVA: owner = [OWNER]
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY): owner = [OWNER]
                elif kind == 'added' and (n in asset_entries or n in generated_entries): owner = [OWNER]
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the 13 Java sources, the 15 textures, the generated additions and the modified en_us.json / zh_cn.json are owned): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) == set(changed_java), 'Changed Java sources and goal23b JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the textures + language + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for n in ('com/hbm/items/machine/RTGPelletDepletedItem$DepletedRTGMaterial.class', 'com/hbm/util/RTGUtil$HalfLifeType.class'):
            need(n in jar_delta['added'], n+' is not an added JAR class')
        for p in MODIFIED_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['modified'], outer+'.class is not a modified JAR class')
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal23a_start=sorted(repinned),
                   goal23a_paths_unchanged=len(goal23a_unchanged), concurrent_23d=concurrent_23d,
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                   insert_lines=insert_summary, replaced_lines=replaced_summary, edit_counts=edit_summary, config=config, pellets=len(pellets), recipes=sorted(recipes),
                   hazard_rows=len(hazard_rows), gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_rtg_tests=new_test_names,
                   final_suites_expected=final_expected, compare=compare['counts'] if compare else None, compare_target_expected=len(expected_target),
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta, class_owners=class_owners,
                   protected_paths=len(protected), old_releases_preserved=len(old_releases), preserved_release_files=len(base['old_release_files']),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
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
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal23b JAR'
    hashes = {p: sha(ROOT/p) for p in reports}
    local_keys = [k for k in keys if map_now[k].get('kind') == 'local']
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(pellets), len(DEPLETED_MATERIALS), len(PELLET_IDS), len(RECYCLED_MATERIALS), sum(1 for p in generated_added if '/models/item/' in p),
                                    len(ASSETS), len(keys), language_kinds, len(hazard_rows), len(new_test_names), gametest_count),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=start_head, planning_commit=prior_receipt['planning_commit'], commits={},
                   target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha, base_release_receipt_sha256=previous_receipt_sha,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, dirty_paths=base['dirty_paths'],
                                      note='The start tree is HEAD dd69a404 (the Goal 23 planning commit on top of the Goal 22 close-out commit 670d5911) plus the '
                                           '24 Goal23A paths, kept uncommitted by Goal 23 decision 15: the dirty paths are exactly the goal23a receipt\'s changed '
                                           'files at their receipt after-hashes, and build/libs at the start is the goal23a package byte for byte. Paths this '
                                           'batch changes again (the language provider, HazardGameTests, zh_cn.json, the zh_cn mapping, en_us.json, the stamp and '
                                           'the shared records) record the start hash (the goal23a after hash) as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes], production_unchanged_optional=[],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, one_line_replacements=replaced_summary, edited_lines=edit_summary,
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported, unchanged_resources=[unchanged_texture],
                   pellets=pellets,
                   config=dict(section='rtg', keys=config, original=[original_refs['config_scale_rtg_power'], original_refs['config_do_rtgs_decay']],
                               note='scaleRTGPower (false) and doRTGsDecay (true) with the original MachineConfig comments; rtgDecay() and scaleRTGPower() each OR 5.28 mode '
                                    '(original VersatileConfig); no language entry, like every existing config key.'),
                   recipes=dict(ids=RECIPE_IDS, generated=recipes, not_registered=SKIPPED_RECIPES,
                                original_references={k: v for k, v in original_refs.items() if k.startswith(('recipe_', 'recycle_'))},
                                note='Ten shapeless pellet recipes (three billets and an iron plate, original MineralRecipes.java) and four recycling recipes on the '
                                     'depleted pellet by hbmsntm:meta (non-strict); the mercury recycling (no mercury ingot in NEO) and the nickel recycling '
                                     '(no nickel) are deferred (Goal 23 decision 9). Only the Pu-238, weak and radium pellets have NEO survival sources; strontium, '
                                     'cobalt, actinium, americium, polonium, gold and lead pellets need billets NEO cannot produce yet.'),
                   hazards=dict(verifier_report=verifier['path'], verifier_report_sha256=verifier['sha256'], verifier_original_references=verifier_references,
                                original_references=original_refs, rows=hazard_rows,
                                modifier=dict(neo=RTG_MODIFIER, original=O_MODIFIER,
                                              note='level + (target - level) * depletion with depletion = 1 - life / max; stacks that are not RTGPelletItem keep their level.'),
                                gameplay='RTG pellets are radioactive like the original: Pu-238 pellet 15 RAD/s and hot 3, radium 11.25, weak 5.25, lead-209 15,000 with fire 7 and '
                                         'blindness 50, gold-198 750 with fire 5, polonium-210 112.5 with fire 3, falling linearly as they decay.'),
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=local_keys,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines_inserted=insert_summary.get(PROVIDER), jar_delta=language,
                                 note='Upstream entries reuse the original English and Chinese verbatim (pellet names and descriptions, the six depleted pellet names, '
                                      'desc.item.rtgHeat and desc.item.rtgDecay); local entries are the polonium description, the extended-info tooltip lines and the '
                                      'pellet_rtg fact lines (the original hard-codes them in English).'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report, repinned_since_goal22d_start=prior_receipt['repinned_since_goal22d_start'],
                   repinned_since_goal23a_start={p: dict(goal23a_start_pin_sha256=h, goal23b_start_sha256=base['files'][p]) for p, h in repinned.items()},
                   goal23a_paths_unchanged={p: receipt_after[p] for p in goal23a_unchanged},
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log), result=gametest_line, tests=gametest_count, added_tests=gametest_added,
                                 new_rtg_tests=new_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; the nine RTGPelletGameTests cover the '
                                      'registry, the lifespans, decay, scaled power and depletion through the production RTGUtil, the recipes through the real '
                                      'RecipeManager, the hazards through HazardSystem, stack size and craft remainder, a real pig holding radium and lead pellets '
                                      '(updateLivingInventory and one CommonEvents.onLivingTick), and the tooltip components and use() on a mock player; no machine '
                                      '(the RT generator is Goal23C), no rendered tooltip, no client, no real player and no saved world.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   concurrent_23d=dict(owner=OWNER_23D, files=concurrent_23d,
                                       note='The read-only batch 23D (RBMK scope) creates exactly these two paths; they are neither packaged nor attributed to Goal23B; '
                                            'the hashes are those at packaging.'),
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, '
                            'the static verifier with in-memory mutations, the final old-suite rerun, compare against the review-6a11998d5852 snapshot and two '
                            'independent static reviews. No in-game client test was run: the pellet names and descriptions, the tooltip and creative tab in either '
                            'language, JEI, a real player crafting a pellet in survival, real decay inside a machine (Goal23C) and multiplayer are unverified; '
                            'GOAL23B-ACCEPTANCE.md is written but not executed.')
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal23a package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
