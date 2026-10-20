"""Package Goal24B (the RBMK fuel items, no reactor yet: RBMKRodItem registered 31 times as rbmk_fuel_ueu .. rbmk_fuel_zfb_am_mix with the plain item rbmk_fuel_empty,
custom-data state yield / xenon / core / hull, nine burn functions, five depletion functions, xenon, core/hull heat, rectify 20 .. 1,000,000, the 1.7.10 durability bar,
stack 1 and the empty-rod craft remainder; IRBMKFluxReceiver.NType for 24C; RBMKPelletItem registered 31 times with META 0-9 (five xenon-disabled pellets 0-4), item_meta
overlay models and the JEI MetaSubtypeInterpreter; the 62 hazard rows registerRBMKFuels() with HazardModifierRBMKRadiation / HazardModifierRBMKHot; 49 crafting recipes
(rbmk_fuel_empty, 31 rods, nine beryllium-source billet rows, six ZFB billet rows, screwdriver, screwdriver_desh) and the PUREX row purex.uzh; 69 imported textures; 134
language keys; RBMKFuelGameTests) cumulatively on the goal24a package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal24b.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal24b/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal24b/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal24b/baseline.json: NEO HEAD 1114adf5 (the Goal 24 planning commit on top of the pushed Goal 23 close-out commit 09173669)
with the UNCOMMITTED Goal24A delivery (124 status entries: the goal24a package, not committed by decision 2) and the planning session's two edits to
migration/GOAL24B.md and migration/GOAL24-THREAD-PROMPTS.md. The original HEAD aee05a40f did not move since 24A, so there is no upstream classification and no new
snapshot. build/libs at the start is the goal24a package byte for byte. Every change since the start is computed from the baseline file hashes (not from git diff)
and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with their start bytes
(baseline-files, which holds all of them). The JAR delta against the goal24a package is attributed per entry (goal24b); any entry without exactly one owner fails.
Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys, recipes) are computed here, never hard-coded; the previous
package's SHA-256, size and receipt hashes are read from the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal23c and the review-g21d-hazard-fix receipt) already differ from their older hashes at the frozen start for the acceptance
checklists, GOAL21D.md, GOAL22C.md and goal21d-static-review.md (baseline older_receipt_evidence_drift); the goal24a receipt hashed build/migration/goal24a/main-notes.md
before the 24A session appended its "Delivered" section (baseline previous_receipt_evidence_drift, explained in freeze_start.py). They are listed in the receipt as
start drift and must still equal their Goal24B start hash; no receipt is rewritten and no other protected path may drift.

Unlike the Goal24A packager this one has a single compare run (build/migration/goal24b/compare.json against the snapshot review-aee05a40f10f.json taken at the end
of 24A: original 0/0/0, target = exactly this batch's compare-inventory paths), no upstream classification, no turbofan or screwdriver-tooling section (the two
screwdriver recipes are crafting rows) and no rbmk column constants; it adds the rbmk_fuel constants and the screwdriver_recipes section."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import owner_class
from package_goal19c import tree_files
from package_review_g20_display_fixes import protected_drift as display_protected_drift, split_drift
from migration import BUILD_FILES, matches as feature_matches
from package_goal21d import (LOCALIZATION_RECORD, STAMP, EN, ZH_ENTRY, EN_ENTRY, lang_delta, compare_paths, lines_of,
                             eol_counts, insertions, in_compare_inventory, changed_since_start)
from package_goal22a import annotations
from package_goal22b import (git_ro, edit_counts, stale_diff, receipt_protected, start_drift_paths, ROWS as PUREX_DEFAULT_ROWS, ROW as PUREX_ROW,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE, J
from package_goal23b import report_problems
from package_goal23c import split_args
from package_goal24a import (OUT as GOAL24A_OUT, BASELINE as GOAL24A_BASELINE, protected_paths as goal24a_protected_paths, original_text, original_line,
                             lang_file, provider_keys, SOURCE_HEAD)

OUT = ROOT/'build/migration/goal24b'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL24A_OUT/'final/summary.json'
PREVIOUS = ROOT/'build/migration/releases/goal24a/hbmsntm-198A-goal24a.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal24b'
RELEASE_NAME = 'hbmsntm-198A-goal24b.jar'
OWNER = 'goal24b'
PLANNING_PREFIX = '1114adf5'
GOAL23_CLOSEOUT = '09173669'
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
START_STATUS_ENTRIES = 124
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'

# The 31 rods and pellets in the original registration order (ModItems.java:3028-3058 pellets, :3077-3317 rods; rbmk_fuel_drx / rbmk_pellet_drx and rbmk_fuel_test are not
# migrated). The order and the set are re-derived from the original below; the five pellets without xenon are disableXenon() there.
RODS = ('ueu', 'meu', 'heu233', 'heu235', 'uzh', 'thmeu', 'lep', 'mep', 'hep239', 'hep241', 'lea', 'mea', 'hea241', 'hea242', 'men', 'hen', 'mox', 'les', 'mes', 'hes',
        'leaus', 'heaus', 'po210be', 'ra226be', 'pu238be', 'balefire_gold', 'flashlead', 'balefire', 'zfb_bismuth', 'zfb_pu241', 'zfb_am_mix')
NO_XENON = ('po210be', 'ra226be', 'balefire_gold', 'flashlead', 'balefire')
ROD_TEXTURE = {x: 'rbmk_fuel_hep' if x == 'hep239' else 'rbmk_fuel_'+x for x in RODS}
OVERLAYS = tuple(f'rbmk_pellet_overlay_e{i}' for i in range(5)) + ('rbmk_pellet_overlay_xenon',)

# Production (owner goal24b), NEW: the five classes, and the GameTest class.
NEW_JAVA = [J+p+'.java' for p in (
    'blockentity/machine/rbmk/IRBMKFluxReceiver', 'items/machine/RBMKRodItem', 'items/machine/RBMKPelletItem', 'hazard/modifier/HazardModifierRBMKRadiation',
    'hazard/modifier/HazardModifierRBMKHot', 'gametest/RBMKFuelGameTests')]
FLUX_RECEIVER, ROD_ITEM, PELLET_ITEM, MOD_RADIATION, MOD_HOT, FUEL_TESTS = NEW_JAVA
# Production, MODIFIED existing sources (handoff-packaging.md; the real set is computed from the tree against the start and every other src/ change fails).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'items/NtmItems', 'hazard/HazardRegistry', 'inventory/recipes/PUREXRecipes', 'datagen/NtmRecipeProvider', 'datagen/NtmItemModelProvider', 'datagen/NtmLanguageProvider',
    'main/NuclearTechModClient', 'inventory/NtmCreativeTabs', 'handler/jei/NtmJeiPlugin',
    # The existing PUREX GameTests pinned the 11-row table; two assertions now expect purex.uzh as row 12 (main agent, after the GameTest run).
    'gametest/PUREXGameTests')]
(ITEMS, HAZARD_REGISTRY, PUREX, RECIPE_PROVIDER, ITEM_MODEL_PROVIDER, PROVIDER, CLIENT, CREATIVE_TABS, JEI, PUREX_TESTS) = MODIFIED_JAVA
# Registration and datagen files that must stay insert-only against their start bytes (PUREXRecipes also edits its class javadoc and is checked on its own).
STRICT_INSERT_ONLY = [ITEMS, HAZARD_REGISTRY, RECIPE_PROVIDER, ITEM_MODEL_PROVIDER, PROVIDER, CLIENT, CREATIVE_TABS, JEI, ZH_INPUT]
# The 69 imported original textures: NEO target -> original path (textures/item -> textures/items), derived by the layout rule of the ownership record.
_TEXTURES = ['rbmk_fuel_empty'] + [ROD_TEXTURE[x] for x in RODS] + ['rbmk_pellet_'+x for x in RODS] + list(OVERLAYS)
ASSETS = {ASSETS_ROOT+'textures/item/'+n+'.png': O_RES+'textures/items/'+n+'.png' for n in _TEXTURES}
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA
PRODUCTION = PRODUCTION_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
GENERATED = [STAMP, EN]
# Generated by runData for this batch (relative to src/generated/resources): 32 rod item models, 31 pellet base models + 285 per-meta models, 49 recipes + 49 advancements.
BERYLLIUM_IDS = [f'billet_{x}be_from_{k}' for x in ('po210', 'pu238', 'ra226') for k in ('nuggets', 'billet', 'billets')]
ZFB_IDS = [f'billet_zfb_{x}_from_{k}' for x in ('bismuth', 'pu241', 'am_mix') for k in ('nuggets', 'billets')]
SCREWDRIVER_IDS = ('screwdriver', 'screwdriver_desh')
CRAFT_IDS = ['rbmk_fuel_empty'] + ['rbmk_fuel_'+x for x in RODS] + BERYLLIUM_IDS + ZFB_IDS + list(SCREWDRIVER_IDS)
_ADVANCEMENT_FOLDER = {**{r: 'misc' for r in CRAFT_IDS}, **{r: 'tools' for r in SCREWDRIVER_IDS}}
_ITEM_MODELS = ['rbmk_fuel_empty'] + ['rbmk_fuel_'+x for x in RODS] + ['rbmk_pellet_'+x for x in RODS] \
    + [f'rbmk_pellet_{x}_{i}' for x in RODS for i in range(5 if x in NO_XENON else 10)]
EXPECTED_GENERATED = sorted([f'assets/hbmsntm/models/item/{n}.json' for n in _ITEM_MODELS] + [f'data/hbmsntm/recipe/{r}.json' for r in CRAFT_IDS]
                            + [f'data/hbmsntm/advancement/recipes/{_ADVANCEMENT_FOLDER[r]}/{r}.json' for r in CRAFT_IDS])
EXPECTED_MODIFIED_GENERATED = [EN_ENTRY]
NEW_TOOLS = ['tools/migration/verify_goal24b_rbmk_fuel.py', 'tools/migration/package_goal24b.py']
TOOLS = NEW_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal24b-* or GOAL24B-* record is hashed as well.
REPORTS = ['migration/GOAL24B.md', 'migration/GOAL24B-ACCEPTANCE.md', 'migration/goal24b-static-review.md', 'migration/goal24b-resource-ownership.json']
RESOURCE_OWNERSHIP = REPORTS[3]
BATCH_RECORD = re.compile(r'migration/(goal24b-[^/]+\.(json|md)|GOAL24B-[^/]+\.md)')
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/GOAL24.md']
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + SHARED_RECORDS
# The 134 new language keys: NEO key -> original key (None: a NEO-local key). The hea241 pellet name has an original key but is a local entry (the original Chinese drops a character).
_TRAITS = ('coreTemp', 'diffusion', 'fluxFunc', 'funcType', 'heat', 'melt', 'neutron.any', 'neutron.fast', 'neutron.slow', 'skinTemp', 'source', 'splitsInto', 'splitsWith',
           'xenon', 'xenonBurn', 'xenonGen')
_FUNCS = ('passive', 'log_ten', 'plateu', 'arch', 'sigmoid', 'square_root', 'linear', 'quadratic', 'experimental')
_PELLET_TEXTS = ('recycling', 'brandNew', 'barelyDepleted', 'moderatelyDepleted', 'highlyDepleted', 'fullyDepleted', 'highXenon')
KEYS = {'item.hbmsntm.rbmk_fuel_empty': 'item.rbmk_fuel_empty.name'}
KEYS.update({'item.hbmsntm.rbmk_fuel_'+x: 'item.rbmk_fuel_%s.name' % ('hep' if x == 'hep239' else x) for x in RODS})
KEYS.update({'item.hbmsntm.rbmk_pellet_'+x: f'item.rbmk_pellet_{x}.name' for x in RODS})
KEYS.update({'trait.rbmk.'+t: 'trait.rbmk.'+t for t in _TRAITS})
KEYS.update({'trait.rbmk.func.'+f: None for f in _FUNCS})
KEYS.update({'trait.rbmk.funcDesc.'+f: None for f in _FUNCS if f != 'passive'})
KEYS.update({'desc.item.rbmkPellet.'+t: None for t in _PELLET_TEXTS})
KEYS.update({f'item.hbmsntm.rbmk_pellet_{x}.fullName': None for x in RODS})
LOCAL_WITH_SOURCE = {'item.hbmsntm.rbmk_pellet_hea241'}
EXPECTED_KINDS = {'upstream': sum(1 for k, v in KEYS.items() if v and k not in LOCAL_WITH_SOURCE), 'local': sum(1 for k, v in KEYS.items() if not v or k in LOCAL_WITH_SOURCE)}
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rbmk-fuel] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'main-notes.md', 'builder-progress.md', 'handoff-production.md',
                  'handoff-gametest.md', 'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md', 'expected_values.py', 'scout-precedents.md', 'scout-inventory.md',
                  'scout-ledger.md')
# Review files under OUT (for example the two independent static reviews' notes or diffs) the main agent names when it knows them; each must exist and is
# indexed by the receipt. Extend this list from the real run (review notes, the verifier and packager progress files, make_final_runner.py ...).
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'chain.sh', 'scout-ledger-a.md', 'scout-ledger-b.md', 'builder_copy_textures.py',
                   'builder_lang.py', 'builder_gen_snapshot.py', 'builder-rundata-1.log', 'gen-before-builder-rundata-1.json', 'gen-after-builder-rundata-1.json',
                   'verifier-gt-progress.md', 'verifier-gt/gen_expected.py', 'verifier-gt/RBMKFuelGameTests.java.tmpl', 'verifier-gt/expected-print.txt',
                   'verifier-gt/gametest-3.log', 'verifier-gt/gametest-4.log', 'verifier-gt/scope-start.txt', 'verifier-gt/scope-end.txt',
                   'verifier-script-progress.md', 'verifier-script/scope-before.txt', 'verifier-script/scope-after.txt', 'packaging-progress.md',
                   'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'production-diff.patch', 'changed_since_start.py', 'verify-after-fixes.log',
                   'verify-final.log', 'make_production_diff.py', 'make_localization_review.py', 'add_features.py', 'features-notes.json')
GAMETEST_LOG = 'build/migration/goal24b/gametest-final.log'
NEW_SUITE = 'verify_goal24b_rbmk_fuel.py --gametest-log build/migration/goal24b/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_GROUP, FEATURE_MATERIALS, FEATURE_PUREX = 'rbmk-fuel', 'materials', 'purex-reprocessing'
RADIATION_NOTE = ('Goal24B: every RBMK fuel rod and pellet is radioactive, more so as it depletes and with xenon poison (a fresh UEU rod 1.4 RAD/s, a fully depleted one '
                  '1,200 RAD/s plus up to 1,250 from xenon); a rod whose hull is above 100 °C sets its holder on fire; handle depleted or hot rods only in separately '
                  'authorized disposable worlds. ')
MELTDOWN_NOTE = 'Goal24B adds no meltdown path (the fuel columns that burn rods are 24C). '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_MOD_ITEMS = ORIGINAL+'items/ModItems.java'
O_ROD = ORIGINAL+'items/machine/ItemRBMKRod.java'
O_PELLET = ORIGINAL+'items/machine/ItemRBMKPellet.java'
O_FLUX = ORIGINAL+'tileentity/machine/rbmk/IRBMKFluxReceiver.java'
O_MOD_RADIATION = ORIGINAL+'hazard/modifier/HazardModifierRBMKRadiation.java'
O_MOD_HOT = ORIGINAL+'hazard/modifier/HazardModifierRBMKHot.java'
O_HAZARD = ORIGINAL+'hazard/HazardRegistry.java'
O_ROD_RECIPES = ORIGINAL+'crafting/RodRecipes.java'
O_MINERAL = ORIGINAL+'crafting/MineralRecipes.java'
O_TOOL_RECIPES = ORIGINAL+'crafting/ToolRecipes.java'
O_PUREX = ORIGINAL+'inventory/recipes/PUREXRecipes.java'
O_SOURCES = [O_ROD, O_PELLET, O_FLUX, O_MOD_RADIATION, O_MOD_HOT, O_MOD_ITEMS, O_HAZARD, O_ROD_RECIPES, O_MINERAL, O_TOOL_RECIPES, O_PUREX]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'rod_class': (O_ROD, 'public class ItemRBMKRod'), 'rod_burn': (O_ROD, 'public double burn('), 'rod_rectify': (O_ROD, 'private double rectify('),
    'rod_update_heat': (O_ROD, 'public void updateHeat('), 'rod_provide_heat': (O_ROD, 'public double provideHeat('),
    'rod_reactivity_func': (O_ROD, 'public double reactivityFunc('), 'rod_depletion_modifier': (O_ROD, 'public double reactivityModByEnrichment('),
    'rod_enrichment': (O_ROD, 'public static double getEnrichment('), 'rod_show_bar': (O_ROD, 'public boolean showDurabilityBar('),
    'rod_nbt_defaults': (O_ROD, 'private static void setNBTDefaults('),
    'pellet_xenon_icon': (O_PELLET, 'rbmk_pellet_overlay_xenon'), 'pellet_rectify': (O_PELLET, 'public static int rectify(int meta)'),
    'pellet_has_xenon': (O_PELLET, 'public static boolean hasXenon(int meta)'),
    'pellet_ueu': (O_MOD_ITEMS, 'rbmk_pellet_ueu = (ItemRBMKPellet)'), 'pellet_po210be_no_xenon': (O_MOD_ITEMS, 'rbmk_pellet_po210be = (ItemRBMKPellet)'),
    'rod_empty': (O_MOD_ITEMS, 'rbmk_fuel_empty = new Item()'), 'rod_ueu': (O_MOD_ITEMS, 'rbmk_fuel_ueu = (ItemRBMKRod)'),
    'rod_hep239_texture_hep': (O_MOD_ITEMS, 'rbmk_fuel_hep239 = (ItemRBMKRod)'),
    'hazard_first_rod': (O_HAZARD, 'registerRBMKRod(rbmk_fuel_ueu'), 'hazard_first_pellet': (O_HAZARD, 'registerRBMKPellet(rbmk_pellet_ueu'),
    'hazard_helper_pellet': (O_HAZARD, 'private static void registerRBMKPellet(Item pellet, float base, float dep, boolean linear, float blinding'),
    'hazard_helper_rod': (O_HAZARD, 'private static void registerRBMK(Item rod'),
    'recipe_empty_rod': (O_ROD_RECIPES, 'new ItemStack(ModItems.rbmk_fuel_empty, 1)'), 'recipe_first_rod': (O_ROD_RECIPES, 'addRBMKRod(U, ModItems.rbmk_fuel_ueu)'),
    'recipe_rod_helper': (O_ROD_RECIPES, 'public static void addRBMKRod(Item billet, Item out)'),
    'recipe_po210be_nuggets': (O_MINERAL, 'new ItemStack(ModItems.billet_po210be, 1)'), 'recipe_zfb_bismuth_nuggets': (O_MINERAL, 'new ItemStack(ModItems.billet_zfb_bismuth, 1)'),
    'recipe_screwdriver': (O_TOOL_RECIPES, 'new ItemStack(ModItems.screwdriver, 1)'), 'recipe_screwdriver_desh': (O_TOOL_RECIPES, 'new ItemStack(ModItems.screwdriver_desh, 1)'),
    'purex_uzh': (O_PUREX, 'new PUREXRecipe("purex.uzh")'),
}
# Original crafting-manager key expressions and the original's ore-dictionary billets / nuggets -> the NEO ingredient (the verifier applies the same table).
KEY_TABLE = {'ZR.ingot()': {'item': 'hbmsntm:ingot_zirconium'}, 'ModItems.rod_quad_empty': {'item': 'hbmsntm:rod_quad_empty'}, 'IRON.ingot()': {'item': 'minecraft:iron_ingot'},
             'STEEL.ingot()': {'item': 'hbmsntm:ingot_steel'}, 'DESH.ingot()': {'item': 'hbmsntm:ingot_desh'}, 'ANY_PLASTIC.ingot()': {'tag': 'ntm:ingots_plastic'}}
FRAME_BILLETS = {'U': 'billet_uranium', 'U233': 'billet_u233', 'U235': 'billet_u235', 'PURG': 'billet_pu_mix', 'PU239': 'billet_pu239', 'PU241': 'billet_pu241',
                 'AMRG': 'billet_am_mix', 'AM241': 'billet_am241', 'AM242': 'billet_am242', 'NP237': 'billet_neptunium', 'ZR': 'billet_zirconium', 'BI': 'billet_bismuth',
                 'PU240': 'billet_pu240'}
FRAME_NUGGETS = {'ZR': 'nugget_zirconium', 'U': 'nugget_uranium', 'PU241': 'nugget_pu241', 'BI': 'nugget_bismuth', 'U235': 'nugget_u235', 'PU240': 'nugget_pu240',
                 'AMRG': 'nugget_am_mix'}
NUGGET_NAMES = {'nuggetPolonium210': 'nugget_polonium', 'nuggetPlutonium238': 'nugget_pu238', 'nuggetRadium226': 'nugget_ra226'}


def scope_text(key_count, kinds, assets, fuel_tests, total_tests):
    return (f'Goal24B (the RBMK fuel items, no reactor yet): RBMKRodItem registered 31 times (rbmk_fuel_ueu .. rbmk_fuel_zfb_am_mix and rbmk_fuel_uzh; the NEO id '
            f'rbmk_fuel_hep239 uses the texture rbmk_fuel_hep) plus the plain item rbmk_fuel_empty, with the state in custom data yield / xenon / core / hull (read with per-key '
            f'defaults and never written on read), nine burn functions, five depletion functions, xenon generation and burn, core and hull heat, rectify 20 .. 1,000,000, the '
            f'1.7.10 durability bar, tooltips through translation keys, stack size 1, the empty rod as craft remainder and IRBMKFluxReceiver.NType for 24C; RBMKPelletItem '
            f'(extends NuclearWasteItem, IMetaItem) registered 31 times with META 0-9 (the five xenon-disabled pellets 0-4), item_meta overlay models and the JEI '
            f'MetaSubtypeInterpreter, with no production or consumption yet (Goal 25 / SILEX); the 62 hazard rows registerRBMKFuels() in HazardRegistry with '
            f'HazardModifierRBMKRadiation and HazardModifierRBMKHot; 49 generated crafting recipes with advancements (rbmk_fuel_empty, 31 rbmk_fuel_<x> from eight billets and the '
            f'empty rod, nine beryllium-source billet rows, six ZFB billet rows, and screwdriver and screwdriver_desh, the 24A out-of-scope finding 2 merged by the user decision '
            f'of 2026-10-19) and the PUREX row 12 purex.uzh; {assets} imported textures; {key_count} language keys ({kinds.get("upstream", 0)} upstream, '
            f'{kinds.get("local", 0)} NEO-local); {fuel_tests} RBMKFuelGameTests ({total_tests} GameTests in total). Gameplay impact: every fuel rod and pellet is radioactive and '
            f'its radiation rises as it depletes and with xenon; a rod whose hull is above 100 °C sets its holder on fire; rods and the empty rod are craftable from billets, but '
            f'only the rods whose eight billets are obtainable in NEO survival are reachable (ledger in GOAL24B.md); screwdrivers become craftable; the PUREX gains the uzh row; '
            f'pellets and the australium / balefire gold / flashlead rods are creative-only for now.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal24b release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy, otherwise the blob at the start commit (with CRLF where the working tree had it) when it reproduces the
    baseline hash; None when neither does."""
    if p in base['copied_scope']: return (START_FILES/p).read_bytes()
    blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT)
    for data in (blob, blob.replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def start_pin(base, p):
    """The Goal24B start hash of a frozen path: baseline files, or for a build/ record that drifted after the goal24a receipt (build/ is Git-ignored, so baseline files
    does not list it) the `now` hash of baseline previous_receipt_evidence_drift."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_evidence_drift'][p]['now']


def protected_paths(base):
    """What the goal24a packager protected (built there from the Goal21A..Goal23C starts and receipts and the goal24a start), plus every path the goal24a receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 24B baseline lists the goal23c receipt among them) and every release file of the frozen
    start (the goal24a package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a
    main-notes.md, which the 24A session appended to after packaging) are pinned at their Goal24B start hash (baseline files) instead of any receipt hash or any earlier
    start hash. One path never carries two hashes. Returns (protected, repinned) where repinned maps a record to the pin the goal24a packager set at its Goal24A start hash,
    for the records that changed between the two starts (acceptance checklists only)."""
    goal24a_start = read(GOAL24A_BASELINE)
    out = dict(goal24a_protected_paths(goal24a_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_evidence_drift'], 'Start drift path is not a frozen file or a recorded build drift: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal24a_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and the 24A working notes (the goal24a receipt hashed them before the "Delivered" section).
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal24A and Goal24B starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal24a_start):
    """{path: {receipts, start_sha256, goal24a_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal24a receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal24a receipt')
        if p in base['previous_receipt_evidence_drift']:
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (freeze_start.py EXPLAINED_DRIFT); the goal24a '
                           'receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal24a receipt is not rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22 and 23 in-game acceptance results, the O1 record notes or the thorium follow-up '
                           'section); the goal24a receipt does not hash it. Frozen at the Goal24B start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal24a) records the start hash. Frozen at the start '
                           'hash; this batch must not change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal24a package; the goal24a receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it '
                           'and the goal24a receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal24a_start_sha256=goal24a_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal24a_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def group(p):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA: return 'production'
    if p in ASSETS: return 'production-resource'
    if p == ZH_INPUT: return 'production-chinese'
    if p == LOCALIZATION_RECORD: return 'production-localization-record'
    if p.startswith(GENERATED_ROOT): return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    return None


def balanced(stmt, token):
    """The text between the parentheses of `token(...)` in a Java statement (token includes the opening call name, for example '.inputItems'), or None."""
    start = stmt.find(token+'(')
    if start < 0: return None
    begin, depth = start+len(token), 0
    for i in range(begin, len(stmt)):
        if stmt[i] == '(': depth += 1
        elif stmt[i] == ')':
            depth -= 1
            if depth == 0: return stmt[begin+1:i]
    return None


def purex_row(text, neo):
    """{ticks, power, items [[name, count]], fluids [[name, mB]], output [name, count]} of the purex.uzh statement in NEO (neo=True) or the original, or None."""
    text = text.replace('\r\n', '\n')
    at = text.find('("purex.uzh")')
    if at < 0: return None
    stmt = text[at:text.index(';', at)]
    setup = re.search(r'\.setup\((\d+), ([\d_]+)\)', stmt)
    items_text, fluids_text = balanced(stmt, '.inputItems'), balanced(stmt, '.inputFluids')
    out = re.search(r'\.outputItems\(new ItemStack\((?:Ntm|Mod)Items\.(\w+?)(?:\.get\(\))?, (\d+)\)\)', stmt)
    if not (setup and items_text is not None and fluids_text is not None and out): return None
    items = []
    for arg in split_args(items_text):
        m = re.match(r'^new ComparableStack\((?:Ntm|Mod)Items\.(\w+?)(?:\.get\(\))?(?:, (\d+))?\)$', arg)
        z = re.match(r'^new OreDictStack\(ZR\.billet\(\), (\d+)\)$', arg)
        if m: items.append([m.group(1).lower(), int(m.group(2) or 1)])
        elif z and not neo: items.append(['billet_zirconium', int(z.group(1))])
        else: items.append(['?', arg])
    fluids = [[m.group(1).lower(), int(m.group(2).replace('_', ''))] for m in re.finditer(r'new FluidStack\(Fluids\.(\w+), ([\d_]+)\)', fluids_text)]
    return dict(ticks=int(setup.group(1)), power=int(setup.group(2).replace('_', '')), items=items, fluids=fluids, output=[out.group(1).lower(), int(out.group(2))])


def craft_items(expr):
    """The NEO item id of an original ingredient expression of the RBMK / beryllium / ZFB recipes (None when the tables do not know it)."""
    expr = expr.strip()
    m = re.fullmatch(r'ModItems\.(\w+)', expr)
    if m: return m.group(1)
    if expr.startswith('"') and expr.endswith('"'): return NUGGET_NAMES.get(expr[1:-1])
    m = re.fullmatch(r'(\w+)\.(billet|nugget)\(\)', expr)
    if m: return (FRAME_BILLETS if m.group(2) == 'billet' else FRAME_NUGGETS).get(m.group(1))
    return FRAME_BILLETS.get(expr)


def original_shaped(text, output, count):
    """{pattern, key, result} of the single original addRecipeAuto row producing `output` x `count`, or None."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.search(r'addRecipeAuto\(new ItemStack\(ModItems\.(\w+), (\d+)\), new Object\[\] \{ (.*) \}\);', line)
        if not m or m.group(1) != output or int(m.group(2)) != count: continue
        tokens = split_args(m.group(3))
        pattern = [t[1:-1] for t in tokens if t.startswith('"')]
        rest = [t for t in tokens if not t.startswith('"')]
        key = {rest[i].strip("'"): KEY_TABLE.get(rest[i+1]) for i in range(0, len(rest)-1, 2)}
        rows.append(dict(pattern=pattern, key=key, result=dict(count=count, id='hbmsntm:'+output)))
    return rows[0] if len(rows) == 1 else None


def original_rod_rows(text):
    """[(output id, billet item id)] of the addRBMKRod(<billet>, ModItems.rbmk_fuel_<x>) rows, in source order (the helper bodies and the drx shapeless row do not match)."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.match(r'\s*addRBMKRod\((.+), ModItems\.(rbmk_fuel_\w+)\);', line)
        if m: rows.append((m.group(2), craft_items(m.group(1))))
    return rows


def original_mineral_rows(text):
    """[(output item, count, [ingredient item ids])] of the beryllium-source and ZFB billet ShapelessOreRecipe rows of MineralRecipes, in source order."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.search(r'new ShapelessOreRecipe\(new ItemStack\(ModItems\.(billet_(?:po210be|pu238be|ra226be|zfb_\w+)), (\d+)\), new Object\[\] \{ (.*) \}\)\);', line)
        if m: rows.append((m.group(1), int(m.group(2)), [craft_items(t) for t in split_args(m.group(3))]))
    return rows


def mineral_id(output, count, ingredients, raw_tokens_have_nugget):
    return output+('_from_nuggets' if raw_tokens_have_nugget else '_from_billet' if count == 2 else '_from_billets')


def original_hazard_rows(text):
    """[(kind, id, normalized argument text)] of the non-DRX RBMK rod and pellet rows of the original HazardRegistry.registerItems, in source order."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.match(r'\s*registerRBMK(Rod|Pellet)\(rbmk_(?:fuel|pellet)_(\w+), (.*)\);\s*$', line)
        if m and m.group(2) != 'drx': rows.append((m.group(1).lower(), m.group(2), re.sub(r'\s+', '', m.group(3))))
    return rows


def neo_hazard_rows(text):
    """The same rows from NEO's registerRBMKFuels() body."""
    body = re.search(r'private static void registerRBMKFuels\(\) \{(.*?)\n    \}', text.replace('\r\n', '\n'), re.S)
    rows = []
    for line in (body.group(1) if body else '').split('\n'):
        m = re.match(r'\s*registerRBMK(Rod|Pellet)\(RBMK_(?:FUEL|PELLET)_(\w+), (.*)\);(?:\s*//.*)?$', line)
        if m: rows.append((m.group(1).lower(), m.group(2).lower(), re.sub(r'\s+', '', m.group(3))))
    return rows


def main(check, gametest_log):
    pending = []

    def need(condition, message):
        """A condition of the real run: raises there; --check only lists it as pending."""
        if condition: return True
        if not check: raise AssertionError(message)
        pending.append(message)
        return False

    def opt(value, *path):
        """value[path...] or None when a link is missing (the receipt is also assembled in --check, before the evidence exists)."""
        for key in path:
            if value is None: return None
            value = value[key]
        return value

    base = read(BASELINE)
    prior_receipt = read(PREVIOUS_RECEIPT)
    goal24a_start = read(GOAL24A_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal24B commits nothing), the recorded start with the uncommitted 24A delivery.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 24 planning commit'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 24 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    # baseline.json stores `status --untracked-files=all` (every untracked file listed); the 124 entries of the handoff are the default `status --porcelain=v1`
    # (untracked directories collapsed) counted by startup-verification.json.
    full_status = [l for l in base['target_status'].splitlines() if l]
    assert full_status and all(l[:2] in ('??', ' M') for l in full_status), 'The frozen start status holds entries other than modified / untracked'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal24a receipt records another original commit than the frozen start'
    assert base['pending_small_fixes'] == [], 'The frozen start has a pending small fix'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and 'Goal24A' in base['start_content']['uncommitted'], 'Baseline start content differs'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal24B: '+head
    closeout = git_ro(ROOT, 'rev-parse', 'HEAD~1').strip()
    assert closeout.startswith(GOAL23_CLOSEOUT), 'NEO HEAD~1 is not the Goal 23 close-out commit'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b',
                                                          'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_entries'] == START_STATUS_ENTRIES and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'] and startup['generated_resources_verified'] == base['stamp_state']['generated_resources_verified'], \
        'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_verified'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal24a generated tree'
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal24a package, every old release file and the protected evidence.
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal24a receipt list + the goal24a package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal24a receipt count + the goal24a release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal24a receipt'
    # The only goal24a receipt record that drifted before the start: the 24A working notes, appended to after the receipt was written (freeze_start.py EXPLAINED_DRIFT).
    assert sorted(base['previous_receipt_evidence_drift']) == ['build/migration/goal24a/main-notes.md'], 'The goal24a receipt evidence drifted differently at the start: '+str(
        sorted(base['previous_receipt_evidence_drift']))
    for p, d in base['previous_receipt_evidence_drift'].items():
        assert d['receipt'] == receipt_protected(prior_receipt)[p] and d['now'] == start_pin(base, p), 'previous_receipt_evidence_drift differs from the receipt or the frozen pin: '+p
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal24a_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal24a receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal24b. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal24B start that the owner table does not list (production outside the 9 modified Java files, the 5 new classes + RBMKFuelGameTests, '
         'the 69 textures, zh_cn.json and the mapping, a protected record, an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal24B start: '+str(deleted)
    for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD] + GENERATED + SHARED_RECORDS + REPORTS[:1]: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION if p.startswith('src/')})
    need(not outside, 'src/main change outside the 9 modified and 6 new Java files, the 69 textures and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal24B takes no new snapshot)'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-aee05a40f10f snapshot changed'
    production_changed = [p for p in PRODUCTION if p in changes]

    # The modified production files keep their start line endings; new Java files are not mixed.
    start_text = {}
    for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]:
        if p not in changes: continue
        data = start_bytes(base, p)
        if not need(data is not None, p+' has no reproducible start bytes (not in baseline-files and the start-commit blob does not match the baseline hash)'): continue
        start_text[p] = data
        start_eol, eol = eol_counts(data), eol_counts((ROOT/p).read_bytes())
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}')
    for p in NEW_JAVA:
        if (ROOT/p).is_file():
            eol = eol_counts((ROOT/p).read_bytes())
            need(eol[0] == 0 or eol[1] == 0, f'{p} mixes CRLF and LF line endings: {eol}')

    # Production Java facts: insert-only registration files and every line edit counted.
    insert_summary, edit_summary, inserted_lines, added_lines, removed_lines = {}, {}, {}, {}, {}
    for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]:
        if p not in start_text: continue
        start_lines, live_lines = lines_of(start_text[p]), lines_of((ROOT/p).read_bytes())
        edit_summary[p] = edit_counts(start_lines, live_lines)
        added_lines[p] = list((Counter(live_lines) - Counter(start_lines)).elements())
        removed_lines[p] = list((Counter(start_lines) - Counter(live_lines)).elements())
        if p in STRICT_INSERT_ONLY:
            inserted = insertions(start_lines, live_lines)
            if not need(inserted is not None, f'{p} is not insert-only against the start copy (a start line was changed, moved or removed)'): continue
            insert_summary[p] = len(inserted)
            inserted_lines[p] = [l for _, l in inserted]
            need(edit_summary[p]['removed'] == 0, f'{p} removes {edit_summary[p]["removed"]} start lines (insert-only expected)')
    # Language provider: the added lines carry exactly the 134 new keys (items through constants, plain keys); nothing is removed.
    provider_added = []
    if PROVIDER in added_lines:
        keys_added, other = provider_keys(added_lines[PROVIDER])
        provider_added = sorted(keys_added)
        stray = [l for l in other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} adds lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(keys_added) == len(set(keys_added)), f'{PROVIDER} adds a language key twice')
        need(provider_added == sorted(KEYS), f'{PROVIDER} adds the language keys differently than expected: missing {sorted(set(KEYS) - set(provider_added))[:6]}, unexpected {sorted(set(provider_added) - set(KEYS))[:6]}')
        need(not provider_keys(removed_lines[PROVIDER])[0], f'{PROVIDER} removes language entries: {provider_keys(removed_lines[PROVIDER])[0][:4]}')
    # PUREXRecipes: the first 11 rows unchanged, the 12th is purex.uzh, the class javadoc no longer lists it as unregistered.
    purex_facts = None
    if PUREX in start_text and (ROOT/PUREX).is_file():
        live, old = (ROOT/PUREX).read_text(encoding='utf-8').replace('\r\n', '\n'), start_text[PUREX].decode('utf-8').replace('\r\n', '\n')
        rows_now, rows_start = PUREX_ROW.findall(live), PUREX_ROW.findall(old)
        need(rows_start == PUREX_DEFAULT_ROWS and rows_now == PUREX_DEFAULT_ROWS + ['purex.uzh'], f'{PUREX} rows are {rows_now}, expected the 11 start rows {PUREX_DEFAULT_ROWS} + purex.uzh as the 12th')
        need('purex.uzh (RBMK uzh billet)</li>' in old and 'purex.uzh (RBMK uzh billet)</li>' not in live, f'{PUREX} javadoc still lists purex.uzh as not registered (or did not at the start)')
        need(edit_summary[PUREX]['removed'] == len(removed_lines[PUREX]) <= 3, f'{PUREX} changes more than the javadoc lines: {edit_summary[PUREX]}')
        purex_facts = dict(rows=rows_now, row_index=len(rows_now), edit_counts=edit_summary[PUREX])
    # The original, parsed from the stored blobs at the recorded commit (independent of the worktree's line endings).
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    o_items, o_rod, o_pellet = original_text(O_MOD_ITEMS), original_text(O_ROD), original_text(O_PELLET)
    o_pellets = {m.group(1): (m.group(2), '.disableXenon()' in m.group(3)) for m in re.finditer(
        r'rbmk_pellet_(\w+) = \(ItemRBMKPellet\) new ItemRBMKPellet\("([^"]*)"\)(.*?)setTextureName\(', o_items) if m.group(1) not in ('drx', 'test')}
    o_rods = {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(
        r'rbmk_fuel_(\w+) = \(ItemRBMKRod\) new ItemRBMKRod\(rbmk_pellet_(\w+)\).*?setTextureName\(RefStrings\.MODID \+ ":(\w+)"\);', o_items, re.S) if m.group(1) not in ('drx', 'test')}
    o_rod_ids = tuple(m.group(1) for m in re.finditer(r'rbmk_fuel_(\w+) = \(ItemRBMKRod\)', o_items) if m.group(1) not in ('drx', 'test'))
    assert o_rod_ids == RODS and tuple(o_pellets) == RODS, 'The original rod / pellet registrations differ from the owner table: '+str((o_rod_ids, tuple(o_pellets)))
    assert all(o_rods[x] == (x, ROD_TEXTURE[x]) for x in RODS), 'An original rod does not pair with its pellet or texture: '+str({x: o_rods[x] for x in RODS if o_rods[x] != (x, ROD_TEXTURE[x])})
    assert tuple(x for x in RODS if o_pellets[x][1]) == NO_XENON, 'The original disableXenon pellets differ from the owner table'
    assert all(f'":{o}"' in o_pellet or f'"hbm:{o}' in o_pellet or o.replace('rbmk_pellet_overlay_', 'rbmk_pellet_overlay_') in o_pellet for o in ('rbmk_pellet_overlay_e', 'rbmk_pellet_overlay_xenon')), \
        'The original pellet overlay names differ'
    o_hazard_rows = original_hazard_rows(original_text(O_HAZARD))
    assert len(o_hazard_rows) == 62 and Counter(k for k, _, _ in o_hazard_rows) == {'rod': 31, 'pellet': 31}, 'The original no longer has 31 + 31 non-DRX RBMK hazard rows: '+str(len(o_hazard_rows))
    original_rbmk = dict(
        rectify=[int(re.search(r'if\(num < (\d+)D', o_rod).group(1)), int(re.search(r'if\(num > ([\d_]+)D\)', o_rod).group(1).replace('_', ''))],
        defaults=dict(core=float(re.search(r'setCoreHeat\(stack, ([\d.]+)D\);\s*setHullHeat', o_rod).group(1)), hull=float(re.search(r'setHullHeat\(stack, ([\d.]+)D\);\s*\}', o_rod).group(1)),
                      yield_from_item='setYield(stack, ((ItemRBMKRod)stack.getItem()).yield)' in o_rod),
        pellet_metas=dict(with_xenon=int(re.search(r'i < \(this\.hasXenon \? (\d+) : (\d+)\)', o_pellet).group(1)), without_xenon=int(re.search(r'i < \(this\.hasXenon \? (\d+) : (\d+)\)', o_pellet).group(2))))
    assert original_rbmk == dict(rectify=[20, 1000000], defaults=dict(core=20.0, hull=20.0, yield_from_item=True), pellet_metas=dict(with_xenon=10, without_xenon=5)), \
        'The original rod / pellet constants differ: '+str(original_rbmk)
    # NEO constants against the original: rectify, defaults, the hazard rows and the registrations.
    neo_ids_ok = hazard_rows_ok = None
    rbmk_fuel = None
    neo_hazard = []
    if (ROOT/ROD_ITEM).is_file() and (ROOT/PELLET_ITEM).is_file() and (ROOT/ITEMS).is_file() and (ROOT/HAZARD_REGISTRY).is_file():
        n_rod, n_pellet = ((ROOT/p).read_text(encoding='utf-8').replace('\r\n', '\n') for p in (ROD_ITEM, PELLET_ITEM))
        n_items, n_hazard = ((ROOT/p).read_text(encoding='utf-8').replace('\r\n', '\n') for p in (ITEMS, HAZARD_REGISTRY))
        neo_rods = tuple(m.group(1) for m in re.finditer(r'DeferredItem<Item> RBMK_FUEL_(?!EMPTY)\w+ = ITEMS\.register\("rbmk_fuel_(\w+)", \(\) -> new RBMKRodItem\(', n_items))
        neo_pellets = {m.group(1): '.disableXenon()' in m.group(2) for m in re.finditer(
            r'DeferredItem<Item> RBMK_PELLET_\w+ = ITEMS\.register\("rbmk_pellet_(\w+)", \(\) -> (new RBMKPelletItem\(new Item\.Properties\(\)\)(?:\.disableXenon\(\))?)\);', n_items)}
        neo_ids_ok = neo_rods == RODS and tuple(neo_pellets) == RODS and tuple(x for x in RODS if neo_pellets.get(x)) == NO_XENON \
            and len(re.findall(r'DeferredItem<Item> RBMK_FUEL_EMPTY = ITEMS\.register\("rbmk_fuel_empty", \(\) -> new Item\(new Item\.Properties\(\)\)\);', n_items)) == 1
        need(neo_ids_ok, f'{ITEMS} does not register the 31 rods, the 31 pellets (five with disableXenon) and rbmk_fuel_empty once each in the original order: rods {neo_rods == RODS}, pellets {tuple(neo_pellets) == RODS}')
        neo_hazard = neo_hazard_rows(n_hazard)
        hazard_rows_ok = neo_hazard == [(k, i, a) for k, i, a in o_hazard_rows] and n_hazard.count('registerRBMKFuels();') == 1
        need(hazard_rows_ok, f'{HAZARD_REGISTRY} registerRBMKFuels() rows differ from the original HazardRegistry (62 rows, same arguments) or are not called once: {len(neo_hazard)} NEO rows; '
             f'differing ids {sorted({i for (k, i, a) in o_hazard_rows if (k, i, a) not in neo_hazard})[:6]}')
        parsed = dict(
            rectify=[int(m.group(1)) if (m := re.search(r'if\(num < (\d+)D', n_rod)) else None, int(m.group(1).replace('_', '')) if (m := re.search(r'if\(num > ([\d_]+)D\)', n_rod)) else None],
            defaults=dict(core=float(m.group(1)) if (m := re.search(r'case KEY_CORE, KEY_HULL -> ([\d.]+)D;', n_rod)) else None,
                          hull=float(m.group(1)) if (m := re.search(r'case KEY_CORE, KEY_HULL -> ([\d.]+)D;', n_rod)) else None,
                          yield_from_item='case KEY_YIELD -> stack.getItem() instanceof RBMKRodItem rod ? rod.yield : 0D;' in n_rod),
            pellet_metas=dict(with_xenon=int(m.group(1)) if (m := re.search(r'i < \(this\.hasXenon \? (\d+) : (\d+)\)', n_pellet)) else None,
                              without_xenon=int(m.group(2)) if m else None))
        need(parsed == original_rbmk, f'NEO rod / pellet constants differ from the original: {parsed} vs {original_rbmk}')
        rbmk_fuel = dict(neo=[ROD_ITEM, PELLET_ITEM, FLUX_RECEIVER, MOD_RADIATION, MOD_HOT, HAZARD_REGISTRY, ITEMS], original=[O_ROD, O_PELLET, O_FLUX, O_MOD_RADIATION, O_MOD_HOT, O_HAZARD, O_MOD_ITEMS],
                         rods=len(neo_rods), pellets=len(neo_pellets), hazard_rows=len(neo_hazard), hazard_rows_by_kind=dict(Counter(k for k, _, _ in neo_hazard)),
                         rectify_floor_ceiling=parsed['rectify'], state_defaults=dict(yield_=parsed['defaults']['yield_from_item'] and 'item yield', xenon=0, core=parsed['defaults']['core'], hull=parsed['defaults']['hull']),
                         pellet_metas=dict(xenon_enabled=parsed['pellet_metas']['with_xenon'], xenon_disabled=parsed['pellet_metas']['without_xenon'], xenon_disabled_pellets=list(NO_XENON)),
                         original_constants=original_rbmk, original_references={k: v for k, v in original_refs.items() if k.startswith(('rod_', 'pellet_', 'hazard_'))},
                         note='31 rods rbmk_fuel_ueu .. zfb_am_mix (hep239 with the texture rbmk_fuel_hep) + rbmk_fuel_empty, 31 pellets (META 0-9, the five xenon-disabled 0-4), 62 '
                              'hazard rows equal to the original arguments, rectify 20 .. 1,000,000, a missing custom-data key reads as the item yield / 20 / 20 / 0 without a write.')
    # Imported resources: byte for byte equal to the original worktree file and its stored blob (PNG), and to the ownership record.
    imported = {}
    ownership = None
    if need((ROOT/RESOURCE_OWNERSHIP).is_file(), 'record missing: '+RESOURCE_OWNERSHIP):
        ownership = read(ROOT/RESOURCE_OWNERSHIP)
        entries = {a.get('target_path'): a for a in ownership.get('assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(ASSETS), f'{RESOURCE_OWNERSHIP} does not list the {len(ASSETS)} textures at {SOURCE_HEAD[:8]}')
        need(all(entries.get(t, {}).get('source_path') == o for t, o in ASSETS.items()), f'{RESOURCE_OWNERSHIP} source paths differ from the layout rule of the owner table')
    for target, original in ASSETS.items():
        assert (SOURCE/original).is_file(), 'Original texture missing: '+original
        if not (ROOT/target).is_file(): continue
        blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+SOURCE.as_posix(), 'show', SOURCE_HEAD+':'+original], cwd=SOURCE)
        checked_out = (SOURCE/original).read_bytes()
        entry = {a.get('target_path'): a for a in (ownership or {}).get('assets', [])}.get(target, {})
        imported[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size,
                                original_worktree_sha256=sha(SOURCE/original), original_blob_sha256=hashlib.sha256(blob).hexdigest(), original_blob_bytes=len(blob),
                                source_last_change_commit=entry.get('source_last_change_commit'))
        need((ROOT/target).read_bytes() == checked_out, f'{target} is not byte-identical to the original worktree file {original}')
        need(checked_out == blob, f'{target} is not byte-identical to the stored blob of {original} at {SOURCE_HEAD[:8]}')
        if entry:
            need(entry.get('source_path') == original and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('bytes') == (ROOT/target).stat().st_size,
                 f'{RESOURCE_OWNERSHIP} entry differs from the live texture or the original path: {target}')
    # features.json: the new rbmk-fuel group, the unchanged status and reviewed_source_commit of the 52 groups, the notes.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'

    # 4. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_delta = dict(added=sorted(KEYS), removed=[], changed=[])
    need(en_delta == expected_delta, 'generated en_us.json delta is not the 134 new keys (no value changed): '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_delta, 'zh_cn.json delta is not the 134 new keys (all old keys unchanged): '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_delta, 'zh_cn-map.json delta is not the 134 new keys (all old entries unchanged): '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal24a totals {totals} + {len(KEYS)}')
    language_kinds, original_text_checked = {}, False
    if map_delta == expected_delta and en_delta == expected_delta:
        language_kinds = dict(Counter(map_now[k].get('kind') for k in KEYS))
        need(language_kinds == EXPECTED_KINDS, f'zh_cn-map.json kinds of the new entries are {language_kinds}, expected {EXPECTED_KINDS}')
        o_en, o_zh = lang_file(O_LANG_EN), lang_file(O_LANG_ZH)
        o_full_names = {x: o_pellets[x][0] for x in RODS}
        bad = []
        for k, source_key in KEYS.items():
            e = map_now[k]
            if e.get('target_en') != en_now.get(k) or e.get('target_zh') != zh_now.get(k): bad.append(k)
            elif source_key is None:
                if e.get('kind') != 'local' or not e.get('reason'): bad.append(k)
                elif k.endswith('.fullName') and en_now[k] != o_full_names[k[len('item.hbmsntm.rbmk_pellet_'):-len('.fullName')]]: bad.append(k)
                elif k.startswith('trait.rbmk.funcDesc.') and en_now[k] != zh_now[k]: bad.append(k)
            elif k in LOCAL_WITH_SOURCE:
                if e.get('kind') != 'local' or not e.get('reason') or e.get('source_key') != source_key or e.get('source_en') != o_en.get(source_key) \
                        or e.get('source_zh') != o_zh.get(source_key) or e.get('target_en') != e.get('source_en') or e.get('target_zh') == e.get('source_zh') \
                        or e.get('target_zh').replace('燃料芯块', '料芯块') != e.get('source_zh'): bad.append(k)
            elif e.get('kind') != 'upstream' or e.get('source_key') != source_key or e.get('source_zh') != e.get('target_zh') or e.get('source_en') != e.get('target_en'): bad.append(k)
            elif e.get('source_en') != o_en.get(source_key) or e.get('source_zh') != o_zh.get(source_key): bad.append(k)
        need(not bad, 'zh_cn-map.json entries do not match en_us.json / zh_cn.json, the original en_US.lang / zh_CN.lang values at aee05a40f, the original pellet full names or the expected kinds: '+str(bad[:8]))
        original_text_checked = not bad
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal24a generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected item model, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # Recipes: the 49 crafting recipes (computed from the generated JSON) against the original rows; the original rows are parsed from the stored blobs.
    o_rod_recipes, o_mineral, o_tool_recipes = original_text(O_ROD_RECIPES), original_text(O_MINERAL), original_text(O_TOOL_RECIPES)
    expected_crafting = {}
    empty_row = original_shaped(o_rod_recipes, 'rbmk_fuel_empty', 1)
    assert empty_row is not None and all(v is not None for v in empty_row['key'].values()), f'The original rbmk_fuel_empty row could not be parsed or translated: {empty_row}'
    expected_crafting['rbmk_fuel_empty'] = ('crafting_shaped', empty_row)
    rod_rows = original_rod_rows(o_rod_recipes)
    assert sorted(o for o, _ in rod_rows) == sorted('rbmk_fuel_'+x for x in RODS) and all(b for _, b in rod_rows), f'The original addRBMKRod rows could not be parsed or translated: {rod_rows}'
    for out, billet in rod_rows:
        expected_crafting[out] = ('crafting_shapeless', dict(ingredients=sorted(['hbmsntm:rbmk_fuel_empty']+['hbmsntm:'+billet]*8), result=dict(count=1, id='hbmsntm:'+out)))
    mineral_rows = original_mineral_rows(o_mineral)
    mineral_lines = [l for l in o_mineral.replace('\r\n', '\n').split('\n') if re.search(r'new ShapelessOreRecipe\(new ItemStack\(ModItems\.billet_(?:po210be|pu238be|ra226be|zfb_\w+), ', l)]
    assert len(mineral_rows) == len(mineral_lines) == 15 and all(None not in ing for _, _, ing in mineral_rows), f'The original MineralRecipes rows could not be parsed or translated: {mineral_rows}'
    for (out, count, ing), line in zip(mineral_rows, mineral_lines):
        rid = mineral_id(out, count, ing, 'nugget' in line.lower())
        expected_crafting[rid] = ('crafting_shapeless', dict(ingredients=sorted('hbmsntm:'+i for i in ing), result=dict(count=count, id='hbmsntm:'+out)))
    screwdriver_rows = {}
    for rid in SCREWDRIVER_IDS:
        row = original_shaped(o_tool_recipes, rid, 1)
        assert row is not None and all(v is not None for v in row['key'].values()), f'The original {rid} row could not be parsed or translated: {row}'
        expected_crafting[rid] = ('crafting_shaped', row)
        screwdriver_rows[rid] = row
    assert sorted(expected_crafting) == sorted(CRAFT_IDS), 'The recipes parsed from the original differ from the 49 expected ids: '+str(sorted(set(expected_crafting) ^ set(CRAFT_IDS)))
    crafting, crafting_bad = {}, []
    for rid in CRAFT_IDS:
        path = ROOT/GENERATED_ROOT/'data/hbmsntm/recipe'/(rid+'.json')
        if not path.is_file(): continue
        data = read(path)
        kind, o_row = expected_crafting[rid]
        if kind == 'crafting_shaped':
            neo_row = dict(pattern=data.get('pattern'), key=data.get('key'), result=data.get('result'))
            same = neo_row == o_row
        else:
            ingredients = sorted((i.get('item') or '#'+i.get('tag', '?')) for i in data.get('ingredients', []))
            neo_row = dict(ingredients=ingredients, result=data.get('result'))
            same = neo_row == o_row
        crafting[rid] = dict(type=data.get('type'), neo=neo_row, original=o_row)
        if data.get('type') != 'minecraft:'+kind or not same: crafting_bad.append(rid)
    need(not crafting_bad and len(crafting) == len(CRAFT_IDS), f'crafting recipes differ from the original rows (through the translation tables) or are missing: {crafting_bad or sorted(set(CRAFT_IDS) - set(crafting))}')
    # PUREX row purex.uzh against the original (600 tick / 1,000 HE/t, nitric acid 1,000 + hydrogen 4,000, billet_uranium_fuel + 3 billet_zirconium -> 4 billet_uzh).
    o_purex = purex_row(original_text(O_PUREX), False)
    assert o_purex == dict(ticks=600, power=1000, items=[['billet_uranium_fuel', 1], ['billet_zirconium', 3]], fluids=[['nitric_acid', 1000], ['hydrogen', 4000]], output=['billet_uzh', 4]), \
        'The original purex.uzh row differs from the task book: '+str(o_purex)
    n_purex = purex_row((ROOT/PUREX).read_text(encoding='utf-8'), True) if (ROOT/PUREX).is_file() else None
    need(n_purex == o_purex, f'{PUREX} purex.uzh differs from the original (through the item-name translation): {n_purex} vs {o_purex}')
    purex = dict(neo=n_purex, original=o_purex, original_reference=original_refs['purex_uzh'], **(purex_facts or {}))
    # Mapped paths: every changed path inside the compare inventory must be matched by a feature group.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    if need(FEATURE_GROUP in by_id, 'migration/features.json has no group '+FEATURE_GROUP):
        group_entry = by_id[FEATURE_GROUP]
        need(group_entry.get('status') == 'partial-unverified' and group_entry.get('reviewed_source_commit') == SOURCE_HEAD,
             f'features.json group {FEATURE_GROUP} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in [O_ROD, O_PELLET, O_FLUX, O_MOD_RADIATION, O_MOD_HOT, O_MOD_ITEMS, O_HAZARD, O_ROD_RECIPES, O_MINERAL, O_TOOL_RECIPES, O_PUREX] + list(ASSETS.values())
                          if not feature_matches(group_entry, 'source', p)]
        need(not missing_source, f'features.json group {FEATURE_GROUP} lists in neither source_paths nor source_watch: {missing_source[:4]} ({len(missing_source)} paths)')
        missing_target = [p for p in NEW_JAVA if not feature_matches(group_entry, 'target', p)]
        need(not missing_target, f'features.json group {FEATURE_GROUP} lacks the new classes in target_paths/target_watch: {missing_target}')
        watch = list(ASSETS) + [GENERATED_ROOT+p for p in EXPECTED_GENERATED] + [NEW_TOOLS[0]]
        missing_watch = [p for p in watch if not feature_matches(group_entry, 'target', p)]
        need(not missing_watch, f'features.json group {FEATURE_GROUP} lacks the textures, the generated item models / recipes / advancements or the verifier in target_watch: {missing_watch[:4]} ({len(missing_watch)} paths)')
        absent = [p for p in group_entry.get('source_paths', []) if not (SOURCE/p).is_file()]
        need(not absent, f'features.json group {FEATURE_GROUP} source_paths missing in the original: {absent}')
    if need(FEATURE_MATERIALS in by_id, 'migration/features.json has no group '+FEATURE_MATERIALS):
        notes = ' '.join(by_id[FEATURE_MATERIALS].get('notes', []))
        need('62' in notes and 'RBMK' in notes, f'migration/features.json group {FEATURE_MATERIALS} notes do not mention the 62 RBMK hazard rows')
    if need(FEATURE_PUREX in by_id, 'migration/features.json has no group '+FEATURE_PUREX):
        need('purex.uzh' in ' '.join(by_id[FEATURE_PUREX].get('notes', [])), f'migration/features.json group {FEATURE_PUREX} notes do not mention purex.uzh')
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
    fuel_test_names = sorted(GAMETEST_METHOD.findall((ROOT/FUEL_TESTS).read_text(encoding='utf-8'))) if (ROOT/FUEL_TESTS).is_file() else []
    fuel_annotations = annotations(ROOT/FUEL_TESTS) if (ROOT/FUEL_TESTS).is_file() else 0
    need(bool(fuel_test_names) and fuel_annotations == len(fuel_test_names), f'{FUEL_TESTS} holds {fuel_annotations} @GameTest annotations and {len(fuel_test_names)} parsed methods')
    need(gametest_added == fuel_annotations, f'GameTest sources grew by {gametest_added} tests, RBMKFuelGameTests holds {fuel_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in fuel_test_names), 'GameTest log lacks "[hbm-rbmk-fuel] <name> passed" for: '+str([n for n in fuel_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24b/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24b/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal24b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal24b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal24b/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal24b/production-vs-start.diff') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal24a final run plus the Goal24B verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal24a final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal24B suite is already in the goal24a final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal24b/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal24a final set + the Goal24B verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal24b/'+VERIFY_REPORT+' (tools/migration/verify_goal24b_rbmk_fuel.py report)'):
        report = read(OUT/VERIFY_REPORT)
        problems = report_problems(report, [p for p in production_changed if not p.startswith(RES) or p == ZH_INPUT])
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        mutations = report.get('mutations')
        mutation_entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
        detected = summary_part.get('mutations_detected', sum(1 for e in mutation_entries if isinstance(e, dict) and e.get('detected') is True))
        total = summary_part.get('mutations_total', summary_part.get('mutations_applied', len(mutation_entries)))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=NEW_TOOLS[0],
                        tool_sha256=sha(ROOT/NEW_TOOLS[0]) if (ROOT/NEW_TOOLS[0]).is_file() else None, mutations_detected=f'{detected}/{total}', mutations_total=total)
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(re.findall(r'(?:ItemRBMKRod|ItemRBMKPellet|IRBMKFluxReceiver|HazardModifierRBMK\w+|HazardRegistry|ModItems|RodRecipes|MineralRecipes|PUREXRecipes|ToolRecipes)\.java:\d+(?:-\d+)?',
                                                      json.dumps(report, ensure_ascii=False))))
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly this batch's compare-inventory paths; the snapshot holds the uncommitted 24A content).
    expected_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_added = sorted(p for p in expected_target if p not in base['files'])
    expected_modified = sorted(p for p in expected_target if p in base['files'])
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal24b/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d)' % (
            len(expected_target), len(expected_added), len(expected_modified))):
        cmp = read(OUT/COMPARE)
        need(cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, COMPARE+' is not against the aee05a40f snapshot')
        need(cmp['current_target_state']['commit'] == start_head, COMPARE+' records another target commit than the start commit')
        counts = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(all(v == 0 for v in counts['source'].values()) and counts['target']['removed'] == 0, COMPARE+' original is not 0/0/0 or the target removes paths: '+str(counts))
        listed = sorted(p for p in compare_paths(cmp['changes']['target']['added']) | compare_paths(cmp['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
        need(listed == expected_target, COMPARE+' target set differs: extra %s, missing %s' % (sorted(set(listed) - set(expected_target))[:8], sorted(set(expected_target) - set(listed))[:8]))
        listed_added = sorted(p for p in compare_paths(cmp['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
        need(not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], COMPARE+' reports unmapped changes: '+str(cmp['unmapped_changes']))
        need(not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], COMPARE+' reports removed features or missing files')
        states = Counter(f.get('state') for f in cmp['features'])
        need(len(cmp['features']) == len(features) and set(states) <= {'target-changed', 'no-observed-file-change'}, f'{COMPARE} feature states are {dict(states)}, expected only target-changed / no-observed-file-change over {len(features)} groups')
        need(any(f.get('id') == FEATURE_GROUP and f.get('state') == 'target-changed' for f in cmp['features']), f'{COMPARE} does not report {FEATURE_GROUP} as target-changed')
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: [OWNER] for p in listed})
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        need({f['id'] for f in snap['manifest']['features']} == set(start_features), SNAPSHOT+' does not hold the 52 mapping groups of the start')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal24b.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal24a) package (run build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 69 textures and every compiled class equal the sources.
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [e for e, t in asset_entries.items() if e not in names or not (ROOT/t).is_file() or jar.read(e) != (ROOT/t).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json, the imported textures or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == en_delta == expected_delta and zh_jar == zh_delta == expected_delta,
                 f'JAR en_us.json or zh_cn.json delta against the previous package is not the {len(KEYS)} new keys: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
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
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 69 imported textures, the generated additions and the modified '
             'en_us.json / zh_cn.json are owned; META-INF/MANIFEST.MF is not): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) == set(changed_java), 'Changed Java sources and goal24b JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported textures + language + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for inner in ('com/hbm/items/machine/RBMKRodItem$EnumBurnFunc.class', 'com/hbm/items/machine/RBMKRodItem$EnumDepleteFunc.class', 'com/hbm/blockentity/machine/rbmk/IRBMKFluxReceiver$NType.class'):
            need(inner in jar_delta['added'], inner+' is not an added JAR class')
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal24a_start=sorted(repinned),
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                   insert_lines=insert_summary, edit_counts=edit_summary, rbmk_fuel=opt(rbmk_fuel, 'note') and {k: rbmk_fuel[k] for k in ('rods', 'pellets', 'hazard_rows', 'rectify_floor_ceiling')},
                   crafting_recipes=len(crafting), purex=purex_facts, gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_fuel_tests=fuel_test_names, final_suites_expected=final_expected,
                   compare=opt(compare, 'counts'), compare_target_expected=len(expected_target),
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta, class_owners=class_owners,
                   protected_paths=len(protected), old_releases_preserved=len(old_releases), preserved_release_files=len(base['old_release_files']),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)

    # The receipt: assembled in both modes (None where the evidence does not exist yet in --check); only the real run writes it, and there every need() above raised.
    dest = RELEASE/RELEASE_NAME
    digest = sha(JAR)
    hashes = {p: sha(ROOT/p) for p in reports if (ROOT/p).is_file()}
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), language_kinds, len(ASSETS), len(fuel_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=prior_receipt['planning_commit'],
                   goal23_closeout=closeout, uncommitted_start=dict(status_entries=START_STATUS_ENTRIES, description=base['start_content']['uncommitted'],
                                                                    base_release=previous_rel, status=[l for l in base['target_status'].splitlines() if l]),
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha,
                                      note='The start tree is HEAD 1114adf5 (the Goal 24 planning commit on top of the pushed Goal 23 close-out commit 09173669) with the UNCOMMITTED '
                                           'Goal24A delivery (124 status entries; the goal24a package, not committed by decision 2) and the planning session\'s edits to '
                                           'migration/GOAL24B.md and migration/GOAL24-THREAD-PROMPTS.md; no pending small fix; build/libs at the start is the goal24a package '
                                           'byte for byte. The original did not move since 24A. Paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary,
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   rbmk_fuel=rbmk_fuel, screwdriver_recipes={rid: dict(neo=opt(crafting, rid, 'neo'), original=screwdriver_rows[rid],
                                                                      original_reference=original_refs['recipe_'+rid]) for rid in SCREWDRIVER_IDS},
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note='78 entries are upstream (32 rod names with the original English and Chinese verbatim, 30 pellet names, 16 trait.rbmk.* keys); 56 are '
                                      'NEO-local (the nine burn-function titles, the eight function format strings, the seven pellet tooltip lines, the 31 pellet full names, '
                                      'which are hard-coded English in the original, and the hea241 pellet name, whose original Chinese drops a character and is corrected). '
                                      'No existing key changes its value.'),
                   recipes=dict(crafting=crafting, purex=purex, not_registered=['rbmk_fuel_drx', 'rbmk_fuel_test', 'rbmk_pellet_drx'],
                                original_references={k: v for k, v in original_refs.items() if k.startswith(('recipe_', 'purex_'))},
                                note='49 crafting recipes equal the original rows (RodRecipes.java:89-120, MineralRecipes.java:183-198, ToolRecipes.java:139-140) through the '
                                     'billet / nugget / ingot translation tables: the empty rod (shaped), 31 rods (shapeless: the empty rod and eight billets), nine beryllium '
                                     'source rows, six ZFB rows, and two shaped screwdrivers (the Desh one with the ntm:ingots_plastic tag for ANY_PLASTIC); purex.uzh is the '
                                     '12th PUREX default row. Whether a rod is reachable in survival depends on its billets (ledger in GOAL24B.md).'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report, repinned_since_goal22d_start=prior_receipt['repinned_since_goal22d_start'],
                   repinned_since_goal23a_start=prior_receipt['repinned_since_goal23a_start'], repinned_since_goal23b_start=prior_receipt['repinned_since_goal23b_start'],
                   repinned_since_goal23c_start=prior_receipt['repinned_since_goal23c_start'],
                   repinned_since_goal24a_start={p: dict(goal24a_start_pin_sha256=h, goal24b_start_sha256=base['files'][p]) for p, h in repinned.items()},
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_fuel_tests=fuel_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; RBMKFuelGameTests drive the item methods directly '
                                      '(default state, the nine reactivity curves and five depletion modifiers, xenon, burn, updateHeat / provideHeat, rectify and the durability bar, '
                                      'the hazard modifiers and hot level, the pellet metas, the 49 recipes and purex.uzh, stack sizes); no client (item models, pellet overlays, '
                                      'tooltips, the durability bar, creative tabs and JEI are not rendered), no real player, no saved world, no reactor.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier '
                            'with in-memory mutations, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and two independent static '
                            'reviews. No in-game client test was run: the item models, pellet overlays, tooltips, the durability bar, creative tabs and JEI in either language, '
                            'real crafting, PUREX processing or a Geiger reading in a world, burning in a reactor (24C), and multiplayer or a dedicated server beyond GameTest are '
                            'unverified; GOAL24B-ACCEPTANCE.md is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, start_jar_sha), 'build/libs JAR is an older JAR'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal24b JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal24a package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
