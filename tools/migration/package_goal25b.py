"""Package Goal25B (the second batch of Goal 25, RBMK operation and fuel logistics: the irradiation channel rbmk_outgasser (RBMKOutgasserBlock, RBMKOutgasserBlockEntity with 2 slots, a
64,000 mB gas tank that starts as tritium, DURATION 10,000 and the flux efficiency min(1 - fluxRatio * 0.8, 1) * dialOutgasserSpeedMod, RBMKOutgasserMenu, RBMKOutgasserScreen, the lid BER)
with its shaped GHG/GRG/GTG recipe; the RBMKNeutronHandler OUTGASSER branch; OutgasserRecipes / hbmIrradiation.json with 16 default rows (the original's 19 minus the 3 mushroom rows),
OutgasserRecipeSync, OutgasserRecipesPacket and OutgasserRecipeClientSync; the JEI irradiation category; seven imported resources; RBMKOutgasserGameTests and the 25B acceptance
checklist GOAL25B-ACCEPTANCE.md) cumulatively on the goal25a package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal25b.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal25b/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal25b/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal25b/baseline.json: NEO HEAD 783b6d13 (the Goal 25 planning commit, local, on top of the pushed Goal 24 close-out commit 17c8062f) PLUS the
UNCOMMITTED Goal25A delivery (65 status lines, packaged as goal25a and committed together with 25B-25D after the unified acceptance, GOAL25 decision 2); the start hashes are the
working tree at the freeze, not the commit. build/libs at the start IS the goal25a package (same SHA-256). The original HEAD aee05a40f did not move since 24A, so there is no
upstream classification and no new snapshot. Every change since the start is computed from the baseline file hashes (not from git diff) and must be in the owner table below; every
other path must still equal its start hash. The modified production files are compared with their start bytes (baseline-files holds 31 scope copies; a modified file the freeze did
not copy has NO reproducible start bytes, because its start version is in no commit, and is reported as pending). The JAR delta against the goal25a package is attributed per entry
(goal25b only); any entry without exactly one owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys) are computed here,
never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal24e, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start for the acceptance checklists,
GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes build/migration/goal24a/main-notes.md (baseline older_receipt_evidence_drift); the goal25a receipt
differs from nothing at the start (baseline previous_receipt_evidence_drift is empty). They are listed in the receipt as start drift and must still equal their Goal25B start hash; no
receipt is rewritten and no other protected path may drift. The Goal 25 planning documents of 25C and 25D (migration/GOAL25C.md, GOAL25D.md, GOAL25-THREAD-PROMPTS.md) and the
Goal25A and Goal24 records must equal their start hash; migration/GOAL25.md and GOAL25B.md are edited by the main agent (GOAL25.md is a shared record, GOAL25B.md the task book and
delivery record, hashed by the receipt).

Like the Goal25A packager this one has a single compare run (build/migration/goal25b/compare.json against the snapshot review-aee05a40f10f.json taken at the end of 24A: original
0/0/0, target = exactly the goal25a compare target paths (24A-25A, read from build/migration/goal25a/compare.json) plus this batch's compare-inventory paths), no upstream
classification; it adds the rbmk_outgasser constants (checked against the original and NEO source texts). The Goal25A-only receipt keys rbmk_recycling, pile_balance, pending_small_fixes
and goal24_closeout are dropped."""
from collections import Counter
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
from package_goal21d import (LOCALIZATION_RECORD, STAMP, EN, ZH_ENTRY, EN_ENTRY, lang_delta, compare_paths, lines_of,
                             eol_counts, insertions, in_compare_inventory, changed_since_start)
from package_goal22a import annotations
from package_goal22b import (git_ro, edit_counts, stale_diff, receipt_protected, start_drift_paths,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE
from package_goal23b import report_problems
from package_goal24a import original_text, original_line, original_blob, lang_file, provider_keys as base_provider_keys, SOURCE_HEAD
from package_goal24c import captured, normalize_value
from package_goal24e import split_args, OneOf, jsonable, enum_offsets, COLUMN_TYPES
from package_goal25a import OUT as GOAL25A_OUT, BASELINE as GOAL25A_BASELINE, protected_paths as goal25a_protected_paths

OUT = ROOT/'build/migration/goal25b'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL25A_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL25A_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal25a/hbmsntm-198A-goal25a.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal25b'
RELEASE_NAME = 'hbmsntm-198A-goal25b.jar'
OWNER = 'goal25b'
PLANNING_PREFIX = '783b6d13'
GOAL24_CLOSEOUT = '17c8062f'
START_STATUS_LINES = 65
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'

# Production (owner goal25b), NEW (handoff-packaging.md; builder-report.md names the final classes: if a class is named differently or a helper class is added, edit this
# list, --check reports the difference as an unassigned src/ path).
NEW_JAVA = [J+p+'.java' for p in (
    'blocks/machine/rbmk/RBMKOutgasserBlock', 'blockentity/machine/rbmk/RBMKOutgasserBlockEntity', 'inventory/recipes/OutgasserRecipes', 'inventory/recipes/OutgasserRecipeSync',
    'network/toclient/OutgasserRecipesPacket', 'handler/OutgasserRecipeClientSync', 'inventory/menus/RBMKOutgasserMenu', 'inventory/screens/RBMKOutgasserScreen',
    'handler/jei/IrradiationRecipeHandler', 'gametest/RBMKOutgasserGameTests')]
(OUTGASSER_BLOCK, OUTGASSER_BE, OUTGASSER_RECIPES, OUTGASSER_SYNC, OUTGASSER_PACKET, OUTGASSER_CLIENT_SYNC, OUTGASSER_MENU, OUTGASSER_SCREEN, IRRADIATION_JEI, OUTGASSER_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'handler/neutron/RBMKNeutronHandler', 'inventory/recipes/loader/SerializableRecipe', 'network/NtmNetwork', 'handler/jei/NtmJeiPlugin', 'blocks/NtmBlocks',
    'blockentity/NtmBlockEntityTypes', 'inventory/NtmMenuTypes', 'inventory/NtmCreativeTabs', 'main/NuclearTechModClient', 'main/ClientProxy', 'datagen/NtmRecipeProvider',
    'datagen/NtmBlockStateProvider', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmLanguageProvider')]
(NEUTRON_HANDLER, SERIALIZABLE, NETWORK, JEI_PLUGIN, BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, CREATIVE_TABS, CLIENT, CLIENT_PROXY, RECIPE_PROVIDER, BLOCK_STATE_PROVIDER,
 LOOT_PROVIDER, TAG_PROVIDER, PROVIDER) = MODIFIED_JAVA
# Frozen copies the freeze took that this batch is not expected to change (a change fails as an unassigned path).
OPTIONAL_JAVA = []
COMMENT_ONLY_JAVA = []
SAME_CLASS_JAVA = list(COMMENT_ONLY_JAVA)
NO_CLASS_JAVA = []
# JAR classes whose source is unchanged since the start and that differ from the previous package only in recompiled debug names (main agent, 2026-10-21):
# javap -v of RBMKRecyclingGameTests$1 (goal25a vs this build) differs only in the LocalVariableTable names of its two parameters (arg0/arg1 -> pos/state).
# An entry is owned as a recompile difference only when its source is unchanged and the previous bytes with exactly these Utf8 constants replaced equal the new bytes.
RECOMPILE_ONLY = {'com/hbm/gametest/RBMKRecyclingGameTests$1.class': ((b'\x01\x00\x04arg0', b'\x01\x00\x03pos'), (b'\x01\x00\x04arg1', b'\x01\x00\x05state'))}
RECOMPILE_OWNER = 'recompile-debug-names'
ANVIL_RECIPES = J+'inventory/recipes/anvil/AnvilRecipes.java'
COLUMN_TYPE_FILE = J+'blockentity/machine/rbmk/RBMKColumnType.java'
COMMON_CONFIG = J+'config/CommonConfig.java'
# Registration and datagen files that must stay insert-only against their start bytes (the Chinese file and the mapping only gain lines too). RBMKNeutronHandler (the branch replaces
# placeholder comments) and the block state provider (the column list gains an entry) are not.
STRICT_INSERT_ONLY = [SERIALIZABLE, NETWORK, JEI_PLUGIN, BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, CREATIVE_TABS, CLIENT, CLIENT_PROXY, RECIPE_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER, PROVIDER,
                      ZH_INPUT, LOCALIZATION_RECORD]
# For the non-strict files every removed start line (compared stripped, so re-indentation does not count) must be a comment line or start with one of these stripped code prefixes;
# the removed comments are listed in the receipt.
ALLOWED_REMOVED_CODE = {
    NEUTRON_HANDLER: (),
    BLOCK_STATE_PROVIDER: ('NtmBlocks.RBMK_BOILER, NtmBlocks.RBMK_HEATER, NtmBlocks.RBMK_COOLER, NtmBlocks.RBMK_STORAGE}) {',),
}
# The 7 imported original resources: NEO target -> original path, derived by the layout rules of the ownership record (textures/blocks -> textures/block; the GUI texture keeps its path).
ASSETS = {ASSETS_ROOT+'textures/block/rbmk/rbmk_outgasser_'+n+'.png': O_RES+'textures/blocks/rbmk/rbmk_outgasser_'+n+'.png' for n in ('side', 'top', 'cover_top', 'cover_side', 'glass_top', 'glass_side')}
ASSETS[ASSETS_ROOT+'textures/gui/reactors/gui_rbmk_outgasser.png'] = O_RES+'textures/gui/reactors/gui_rbmk_outgasser.png'
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
TAG_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
GENERATED = [STAMP, EN, GENERATED_ROOT+TAG_ENTRY]
# Generated by runData for this batch (relative to src/generated/resources): the blockstate, block and item model, loot table, the shaped recipe and its advancement (the advancement
# folder depends on the recipe category, so it is matched by name).
EXPECTED_GENERATED_BASE = sorted(['assets/hbmsntm/blockstates/rbmk_outgasser.json', 'assets/hbmsntm/models/block/rbmk_outgasser.json', 'assets/hbmsntm/models/item/rbmk_outgasser.json',
                                  'data/hbmsntm/loot_table/blocks/rbmk_outgasser.json', 'data/hbmsntm/recipe/rbmk_outgasser.json'])
ADVANCEMENT = re.compile(r'data/hbmsntm/advancement/recipes/[a-z_]+/rbmk_outgasser\.json')
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, TAG_ENTRY])
G_OUTGASSER_RECIPE = GENERATED_ROOT+'data/hbmsntm/recipe/rbmk_outgasser.json'
NEW_TOOLS = ['tools/migration/verify_goal25b_rbmk_outgasser.py', 'tools/migration/package_goal25b.py']
TOOLS = NEW_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal25b-* or GOAL25B-* record is hashed as well.
REPORTS = ['migration/GOAL25B.md', 'migration/GOAL25B-ACCEPTANCE.md', 'migration/goal25b-static-review.md', 'migration/goal25b-localization-review.json',
           'migration/goal25b-resource-ownership.json', 'migration/goal25b-materials-review.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal25b-[^/]+\.(json|md)|GOAL25B-[^/]+\.md)')
GOAL25_RECORD = 'migration/GOAL25.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md',
                  'migration/RESOURCE-OWNERSHIP.md', GOAL25_RECORD]
# Shared records the batch may leave untouched (FOUNDATIONS.md and RESOURCE-OWNERSHIP.md "if touched").
OPTIONAL_RECORDS = ['migration/FOUNDATIONS.md', 'migration/RESOURCE-OWNERSHIP.md']
# The Goal 25 planning documents of the later batches: no change is expected in this batch.
PLANNING_FROZEN = ['migration/GOAL25C.md', 'migration/GOAL25D.md', 'migration/GOAL25-THREAD-PROMPTS.md']
FROZEN_RECORD = re.compile(r'migration/(GOAL25A[^/]*\.md|goal25a-[^/]+|GOAL24[^/]*\.md|goal24[^/]*)')
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED_BASE + the advancement.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]
# The new language keys: NEO key -> (original key, expected map kind). The block and container names are upstream under the original keys (GOAL25 decision 16: the irradiation channel
# keeps the original English and Chinese verbatim); the five DODD overlay keys are the progress / gas rows of the channel's getDiagData (review fix F1) and equal the original keys.
SOURCE_KEYS = {'block.hbmsntm.rbmk_outgasser': ('tile.rbmk_outgasser.name', 'upstream'), 'container.rbmkOutgasser': ('container.rbmkOutgasser', 'upstream')}
SOURCE_KEYS.update({'tile.rbmk.dodd.'+t: ('tile.rbmk.dodd.'+t, 'upstream') for t in ('progress', 'gas', 'gas_type', 'gas_p', 'gas_max')})
KEYS = {k: v[0] for k, v in SOURCE_KEYS.items()}
EXPECTED_KINDS = dict(Counter(v[1] for v in SOURCE_KEYS.values()))
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rbmk-outgasser] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'compile-start.log', 'main-notes.md', 'builder-report.md', 'handoff-production.md',
                  'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md', 'verifier-report.md', 'review-report.md', 'chain.sh', 'add_zh.py', 'make_ownership.py',
                  'make_production_diff.py')
# Review files under OUT (for example the static review's notes or diffs) the main agent names when it knows them; each must exist and is indexed by the receipt. Extend this list from the
# real run (review notes, the builder's and verifiers' progress and scope files, logs ...); --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'packaging-progress.md', 'packaging-report.md', 'make_loc_review.py',
                   'add_features.py', 'features-notes.json', 'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt',
                   'builder-compile-1.log', 'review-diff.patch', 'review-new-files.txt', 'rundata-1.log', 'stamp-before-rundata-1.json',
                   'verifier-progress.md')
GAMETEST_LOG = 'build/migration/goal25b/gametest-final.log'
NEW_SUITE = 'verify_goal25b_rbmk_outgasser.py --gametest-log build/migration/goal25b/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_OUTGASSER = 'rbmk-outgasser'
NEW_FEATURES = (FEATURE_OUTGASSER,)
# The groups the snapshot of the end of 24A predates (24B rbmk-fuel, 24C rbmk-reactor, 24D rbmk-control and rbmk-steam, 24E rbmk-console, 25A rbmk-storage and rbmk-recycling).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling'}
RADIATION_NOTE = ("Goal25B: the irradiation channel's products are radioactive (gold-198 500 RAD/s per ingot as registered in Goal 21D, thorium fuel), and a neutron stream passing an "
                  "unlidded channel raises its chunk's radiation like any unlidded column; the acceptance checklist GOAL25B-ACCEPTANCE.md must be run only in a separately authorized "
                  "disposable world. ")
MELTDOWN_NOTE = ('Goal25B: the irradiation channel melts down like the other columns and flings 4–5 extra column debris; meltdown tests only in disposable worlds away from builds. ')
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_TE = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKOutgasser.java'
O_BLOCK = ORIGINAL+'blocks/machine/rbmk/RBMKOutgasser.java'
O_CONTAINER = ORIGINAL+'inventory/container/ContainerRBMKOutgasser.java'
O_GUI = ORIGINAL+'inventory/gui/GUIRBMKOutgasser.java'
O_RECIPES = ORIGINAL+'inventory/recipes/OutgasserRecipes.java'
O_NEUTRON = ORIGINAL+'handler/neutron/RBMKNeutronHandler.java'
O_NEI = ORIGINAL+'handler/nei/OutgasserHandler.java'
O_DIALS = ORIGINAL+'tileentity/machine/rbmk/RBMKDials.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_ANVIL = ORIGINAL+'inventory/recipes/anvil/AnvilRecipes.java'
O_CONSOLE = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKConsole.java'
O_SOURCES = [O_TE, O_BLOCK, O_CONTAINER, O_GUI, O_RECIPES, O_NEUTRON, O_NEI, O_DIALS, O_CRAFTING, O_ANVIL, O_CONSOLE]
# The original sources each new mapping group must list (source_paths or source_watch; plus the imported resources).
FEATURE_SOURCES = {FEATURE_OUTGASSER: [O_TE, O_BLOCK, O_CONTAINER, O_GUI, O_RECIPES, O_CRAFTING] + list(ASSETS.values())}
# The NEO paths each new mapping group must cover (target_paths or target_watch).
FEATURE_TARGETS = {FEATURE_OUTGASSER: [OUTGASSER_BLOCK, OUTGASSER_BE, OUTGASSER_RECIPES, OUTGASSER_SYNC, OUTGASSER_PACKET, OUTGASSER_CLIENT_SYNC, OUTGASSER_MENU, OUTGASSER_SCREEN,
                                       IRRADIATION_JEI, OUTGASSER_TESTS, NEW_TOOLS[0], G_OUTGASSER_RECIPE] + list(ASSETS)}
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'outgasser_slots': (O_TE, 'super(2);'), 'outgasser_tank': (O_TE, 'gas = new FluidTank(Fluids.TRITIUM, 64000);'), 'outgasser_duration': (O_TE, 'public static final int duration'),
    'outgasser_update': (O_TE, 'public void updateEntity()'), 'outgasser_receive_flux': (O_TE, 'public void receiveFlux('), 'outgasser_efficiency': (O_TE, 'double efficiency = Math.min('),
    'outgasser_progress': (O_TE, 'progress += stream.fluxQuantity'), 'outgasser_threshold': (O_TE, 'if(progress > duration)'), 'outgasser_can_process': (O_TE, 'public boolean canProcess()'),
    'outgasser_fusion_only': (O_TE, 'if(output.fusionOnly) return false;'), 'outgasser_set_tank_type': (O_TE, 'gas.setTankType(fluid.type);'),
    'outgasser_capacity_test': (O_TE, 'gas.getFill() + fluid.fill > gas.getMaxFill()'), 'outgasser_process': (O_TE, 'private void process()'),
    'outgasser_on_melt': (O_TE, 'public void onMelt(int reduce)'), 'outgasser_melt_count': (O_TE, 'int count = 4 + worldObj.rand.nextInt(2);'),
    'outgasser_rbmk_type': (O_TE, 'RBMKNeutronHandler.RBMKType.OUTGASSER'), 'outgasser_console_type': (O_TE, 'return ColumnType.OUTGASSER;'),
    'outgasser_valid_for_slot': (O_TE, 'public boolean isItemValidForSlot('), 'outgasser_can_extract': (O_TE, 'public boolean canExtractItem('),
    'outgasser_accessible_slots': (O_TE, 'public int[] getAccessibleSlotsFromSide('), 'outgasser_ports': (O_TE, 'ports.update('),
    'outgasser_block_proxy': (O_BLOCK, 'TileEntityProxyCombo'), 'outgasser_container': (O_CONTAINER, 'public ItemStack transferStackInSlot('),
    'outgasser_gui': (O_GUI, 'this.ySize = 186;'), 'outgasser_gui_progress': (O_GUI, 'int progress = (int) (rod.progress * 13 / rod.duration);'),
    'outgasser_gui_gas': (O_GUI, 'int gas = (int) (rod.gas.getFill() * 42 / rod.gas.getMaxFill());'),
    'neutron_outgasser_branch': (O_NEUTRON, 'type == RBMKType.OUTGASSER'),
    'recipes_defaults': (O_RECIPES, 'public void registerDefaults()'), 'recipes_get_output': (O_RECIPES, 'public static OutgasserRecipe getOutput('),
    'recipes_file': (O_RECIPES, 'return "hbmIrradiation.json";'), 'recipes_read': (O_RECIPES, 'public void readRecipe('), 'recipes_write': (O_RECIPES, 'public void writeRecipe('),
    'dial_outgasser': (O_DIALS, 'KEY_OUTGASSER_MOD'), 'nei_outgasser': (O_NEI, 'class OutgasserHandler'),
    'recipe_rbmk_outgasser': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_outgasser, 1)'), 'anvil_rbmk_outgasser': (O_ANVIL, 'ModBlocks.rbmk_outgasser'),
}
# Constants compared between the original and NEO source texts: id -> (original path, regex, NEO path, regex, expected unique values in order[, expected NEO values when they differ]).
# Numbers are compared as floats (underscores dropped, F / D suffixes dropped), anything else as text. The group-1 value of every match is collected. A NEO regex that finds
# nothing (the class is not written yet, or its text differs from the handoff) is reported as pending with its id.
CONSTANTS = {
    # Block entity (TileEntityRBMKOutgasser): 2 slots, a 64,000 mB tank that starts as tritium, DURATION 10,000, strict > DURATION, efficiency min(1 - fluxRatio * 0.8, 1) * dialOutgasserSpeedMod.
    'outgasser_slots': (O_TE, r'super\((\d+)\);', OUTGASSER_BE, r'RBMK_OUTGASSER\.get\(\), pos, state, (\d+)\)', [2]),
    'outgasser_duration': (O_TE, r'public static final int duration = (\d+);', OUTGASSER_BE, r'DURATION = (\d+);', [10000]),
    'outgasser_tank_fluid': (O_TE, r'new FluidTank\(Fluids\.(\w+), \d+\)', OUTGASSER_BE, r'new FluidTank\(Fluids\.(\w+), \d+\)', ['TRITIUM']),
    'outgasser_tank_capacity': (O_TE, r'new FluidTank\(Fluids\.\w+, (\d+)\)', OUTGASSER_BE, r'new FluidTank\(Fluids\.\w+, (\d+)\)', [64000]),
    'outgasser_efficiency_slope': (O_TE, r'Math\.min\(1 - stream\.fluxRatio \* ([\d.]+), \d+\)', OUTGASSER_BE, r'Math\.min\(1 - stream\.fluxRatio \* ([\d.]+), \d+\)', [0.8]),
    'outgasser_efficiency_cap': (O_TE, r'Math\.min\(1 - stream\.fluxRatio \* [\d.]+, (\d+)\)', OUTGASSER_BE, r'Math\.min\(1 - stream\.fluxRatio \* [\d.]+, (\d+)\)', [1]),
    'outgasser_dial_call': (O_TE, r'efficiency \* RBMKDials\.(getOutgasserMod)\(', OUTGASSER_BE, r'efficiency \* RBMKDials\.(getOutgasserMod)\(', ['getOutgasserMod']),
    'outgasser_threshold_operator': (O_TE, r'if\(progress (>=?) duration\)', OUTGASSER_BE, r'if\(progress (>=?) DURATION\)', ['>']),
    'outgasser_dial_default': (O_DIALS, r'KEY_OUTGASSER_MOD\("dialOutgasserSpeedMod", ([\d.]+)\)', COMMON_CONFIG, r'defineInRange\("dialOutgasserSpeedMod", ([\d.]+)D', [1.0]),
    'outgasser_melt_base': (O_TE, r'int count = (\d+) \+ worldObj\.rand\.nextInt\(\d+\);', OUTGASSER_BE, r'int count = (\d+) \+ this\.level\.random\.nextInt\(\d+\);', [4]),
    'outgasser_melt_random': (O_TE, r'int count = \d+ \+ worldObj\.rand\.nextInt\((\d+)\);', OUTGASSER_BE, r'int count = \d+ \+ this\.level\.random\.nextInt\((\d+)\);', [2]),
    'outgasser_melt_debris': (O_TE, r'spawnDebris\(DebrisType\.(\w+)\)', OUTGASSER_BE, r'spawnDebris\(DebrisType\.(\w+)\)', ['BLANK']),
    'outgasser_rbmk_type': (O_TE, r'RBMKType\.(OUTGASSER);', OUTGASSER_BE, r'RBMKType\.(OUTGASSER);', ['OUTGASSER']),
    'outgasser_console_type': (O_TE, r'return ColumnType\.(\w+);', OUTGASSER_BE, r'return RBMKColumnType\.(\w+);', ['OUTGASSER']),
    # Automation: slot 0 takes inputs with a row, only slot 1 is extracted, both slots are reachable from every face.
    'outgasser_accessible_slots': (O_TE, r'return new int\[\] \{([\d, ]+)\};', OUTGASSER_BE, r'SLOTS = new int\[\] \{([\d, ]+)\};', ['0, 1']),
    'outgasser_extract_slot': (O_TE, r'canExtractItem\(int i, ItemStack itemStack, int j\) \{\s*return i == (\d+);', OUTGASSER_BE,
                               r'canTakeItemThroughFace\(int index, ItemStack stack, Direction direction\) \{\s*return index == (\d+);', [1]),
    'outgasser_input_slot': (O_TE, r'getOutput\(itemStack\) != null && i == (\d+);', OUTGASSER_BE, r'if\(slot != (\d+)\) return false;', [0]),
    # Menu (ContainerRBMKOutgasser): input at 48/45, crafting output at 112/69, the player inventory 20 px lower than the plain 84 / 142 rows (104 / 162 in the NEO playerInv call).
    'menu_input_x': (O_CONTAINER, r'new Slot\(tedf, 0, (\d+), \d+\)', OUTGASSER_MENU, r'new Slot\(be, 0, (\d+), \d+\)', [48]),
    'menu_input_y': (O_CONTAINER, r'new Slot\(tedf, 0, \d+, (\d+)\)', OUTGASSER_MENU, r'new Slot\(be, 0, \d+, (\d+)\)', [45]),
    'menu_output_x': (O_CONTAINER, r'SlotCraftingOutput\(invPlayer\.player, tedf, 1, (\d+), \d+\)', OUTGASSER_MENU, r'SlotCraftingOutput\(inventory\.player, be, 1, (\d+), \d+\)', [112]),
    'menu_output_y': (O_CONTAINER, r'SlotCraftingOutput\(invPlayer\.player, tedf, 1, \d+, (\d+)\)', OUTGASSER_MENU, r'SlotCraftingOutput\(inventory\.player, be, 1, \d+, (\d+)\)', [69]),
    'menu_inventory_y': (O_CONTAINER, r'new Slot\(invPlayer, j \+ i \* 9 \+ 9, 8 \+ j \* 18, (\d+) \+ i \* 18 \+ 20\)', OUTGASSER_MENU, r'this\.playerInv\(inventory, 8, (\d+), \d+\)', [84], [104]),
    'menu_hotbar_y': (O_CONTAINER, r'new Slot\(invPlayer, i, 8 \+ i \* 18, (\d+) \+ 20\)', OUTGASSER_MENU, r'this\.playerInv\(inventory, 8, \d+, (\d+)\)', [142], [162]),
    # Screen (GUIRBMKOutgasser): 176 x 186, progress bar 13 px at 82/50 (6 high), gas gauge 42 px at 115/66 (10 wide, texture u 188), tank tooltip rectangle 112/21 16 x 48.
    'gui_width': (O_GUI, r'this\.xSize = (\d+);', OUTGASSER_SCREEN, r'this\.imageWidth = (\d+);', [176]),
    'gui_height': (O_GUI, r'this\.ySize = (\d+);', OUTGASSER_SCREEN, r'this\.imageHeight = (\d+);', [186]),
    'gui_progress_width': (O_GUI, r'rod\.progress \* (\d+) / rod\.duration\)', OUTGASSER_SCREEN, r'be\.progress \* (\d+) / RBMKOutgasserBlockEntity\.DURATION\)', [13]),
    'gui_progress_x': (O_GUI, r'guiLeft \+ (\d+), guiTop \+ \d+, 176, 0, progress, \d+\)', OUTGASSER_SCREEN, r'this\.leftPos \+ (\d+), this\.topPos \+ \d+, 176, 0, progress, \d+\)', [82]),
    'gui_progress_y': (O_GUI, r'guiLeft \+ \d+, guiTop \+ (\d+), 176, 0, progress, \d+\)', OUTGASSER_SCREEN, r'this\.leftPos \+ \d+, this\.topPos \+ (\d+), 176, 0, progress, \d+\)', [50]),
    'gui_progress_height': (O_GUI, r'guiLeft \+ \d+, guiTop \+ \d+, 176, 0, progress, (\d+)\)', OUTGASSER_SCREEN, r'this\.leftPos \+ \d+, this\.topPos \+ \d+, 176, 0, progress, (\d+)\)', [6]),
    'gui_gas_height': (O_GUI, r'rod\.gas\.getFill\(\) \* (\d+) / rod\.gas\.getMaxFill\(\)', OUTGASSER_SCREEN, r'be\.gas\.getFill\(\) \* (\d+) / be\.gas\.getMaxFill\(\)', [42]),
    'gui_gas_x': (O_GUI, r'guiLeft \+ (\d+), guiTop \+ \d+ - gas, \d+, 42 - gas, \d+, gas\)', OUTGASSER_SCREEN, r'this\.leftPos \+ (\d+), this\.topPos \+ \d+ - gas, \d+, 42 - gas, \d+, gas\)', [115]),
    'gui_gas_y': (O_GUI, r'guiLeft \+ \d+, guiTop \+ (\d+) - gas, \d+, 42 - gas, \d+, gas\)', OUTGASSER_SCREEN, r'this\.leftPos \+ \d+, this\.topPos \+ (\d+) - gas, \d+, 42 - gas, \d+, gas\)', [66]),
    'gui_gas_u': (O_GUI, r'guiTop \+ \d+ - gas, (\d+), 42 - gas, \d+, gas\)', OUTGASSER_SCREEN, r'this\.topPos \+ \d+ - gas, (\d+), 42 - gas, \d+, gas\)', [188]),
    'gui_gas_width': (O_GUI, r'guiTop \+ \d+ - gas, \d+, 42 - gas, (\d+), gas\)', OUTGASSER_SCREEN, r'this\.topPos \+ \d+ - gas, \d+, 42 - gas, (\d+), gas\)', [10]),
    'gui_tank_x': (O_GUI, r'renderTankInfo\(this, mouseX, mouseY, guiLeft \+ (\d+), guiTop \+ \d+, \d+, \d+\)', OUTGASSER_SCREEN,
                   r'renderTankTooltip\(guiGraphics, mouseX, mouseY, this\.leftPos \+ (\d+), this\.topPos \+ \d+, \d+, \d+\)', [112]),
    'gui_tank_y': (O_GUI, r'renderTankInfo\(this, mouseX, mouseY, guiLeft \+ \d+, guiTop \+ (\d+), \d+, \d+\)', OUTGASSER_SCREEN,
                   r'renderTankTooltip\(guiGraphics, mouseX, mouseY, this\.leftPos \+ \d+, this\.topPos \+ (\d+), \d+, \d+\)', [21]),
    'gui_tank_width': (O_GUI, r'renderTankInfo\(this, mouseX, mouseY, guiLeft \+ \d+, guiTop \+ \d+, (\d+), \d+\)', OUTGASSER_SCREEN,
                       r'renderTankTooltip\(guiGraphics, mouseX, mouseY, this\.leftPos \+ \d+, this\.topPos \+ \d+, (\d+), \d+\)', [16]),
    'gui_tank_height': (O_GUI, r'renderTankInfo\(this, mouseX, mouseY, guiLeft \+ \d+, guiTop \+ \d+, \d+, (\d+)\)', OUTGASSER_SCREEN,
                        r'renderTankTooltip\(guiGraphics, mouseX, mouseY, this\.leftPos \+ \d+, this\.topPos \+ \d+, \d+, (\d+)\)', [48]),
    # Recipe table: the file name.
    'recipes_file_name': (O_RECIPES, r'return "(hbmIrradiation\.json)";', OUTGASSER_RECIPES, r'getFileName\(\) \{ return "(hbmIrradiation\.json)"; \}', ['hbmIrradiation.json']),
}
# NEO-only facts (no original counterpart): id -> (NEO path, regex, expected unique values). Recorded in the receipt; a regex that finds nothing is pending.
NEO_FACTS = {
    'fusion_only_never_processed': (OUTGASSER_BE, r'if\(output\.(fusionOnly)\) return false;', ['fusionOnly']),
    'lenient_file_rows': (OUTGASSER_RECIPES, r'if\(lenient\) (handler\.readRecipeLenient)\(rows\.get\(i\), i\)', ['handler.readRecipeLenient']),
    'sync_max_recipes': (OUTGASSER_RECIPES, r'MAX_SYNC_RECIPES = (\d+);', [4096]),
    'sync_max_gas': (OUTGASSER_RECIPES, r'MAX_GAS = (\d[\d_]*);', [64000]),
    'packet_direction': (NETWORK, r'registrar\.(playToClient)\(OutgasserRecipesPacket\.TYPE', ['playToClient']),
    'packet_id': (OUTGASSER_PACKET, r'NuclearTechMod\.withDefaultNamespace\("(outgasser_recipes)"\)', ['outgasser_recipes']),
    'extra_cell_proxy': (OUTGASSER_BLOCK, r'new ProxyComboBlockEntity\(pos, state\)\.(inventory\(\)\.fluid\(\))', ['inventory().fluid()']),
    'jei_recipe_type': (IRRADIATION_JEI, r'RecipeType\.create\(NuclearTechMod\.MODID, "(irradiation)"', ['irradiation']),
    'jei_title_block': (IRRADIATION_JEI, r'Component\.translatable\(NtmBlocks\.(RBMK_OUTGASSER)\.get\(\)\.getDescriptionId\(\)\)', ['RBMK_OUTGASSER']),
    'jei_fusion_rows_hidden': (IRRADIATION_JEI, r'if\(!recipe\.(fusionOnly)\) rows\.add\(recipe\)', ['fusionOnly']),
    'menu_shift_click_output': (OUTGASSER_MENU, r'if\(index < be\.getContainerSize\(\)\) \{\s*if\(!this\.(moveItemStackTo)\(stack, be\.getContainerSize\(\), this\.slots\.size\(\), true\)\) return', ['moveItemStackTo']),
}
# Known source differences the batch deliberately leaves (recorded with the observed values; not asserted equal).
KNOWN_DIFFERENCES = {'default_rows': 'the original lists 19 rows, NEO 16 (the 3 mushroom rows are not ported; GOAL25 miscounted 17/14)',
                     'default_inputs': 'the original keys 14 rows on ore dictionary names, NEO uses concrete items (no NEO item tags besides aluminium)',
                     'menu_shift_click': 'the original merges a shift-clicked output back into the input slot (ContainerRBMKOutgasser :39-46), NEO moves it to the player (NEO-only)',
                     'file_loading': 'NEO loads hbmIrradiation.json row by row (bad or duplicate rows are logged and skipped, MACHINE-CHECKLIST), sync and snapshot self-check are strict',
                     'opencomputers': 'the OpenComputers callbacks (:219-272) are not ported'}
# The 16 default rows, in the original's order: (original input expression, NEO input, original solid, NEO solid, solid count, fluid, mB). The mushroom rows (3) are excluded.
OTAR = 'DictFrame.fromOne(ModItems.oil_tar, EnumTarType.%s)'
EXPECTED_ROWS = [
    ('LI.block()', 'BLOCK_LITHIUM', None, None, 0, 'TRITIUM', 10000), ('LI.ingot()', 'LITHIUM', None, None, 0, 'TRITIUM', 1000),
    ('LI.dust()', 'POWDER_LITHIUM', None, None, 0, 'TRITIUM', 1000), ('LI.dustTiny()', 'POWDER_LITHIUM_TINY', None, None, 0, 'TRITIUM', 100),
    ('GOLD.ingot()', 'Items.GOLD_INGOT', 'ModItems.ingot_au198', 'INGOT_AU198', 1, None, 0), ('GOLD.nugget()', 'Items.GOLD_NUGGET', 'ModItems.nugget_au198', 'NUGGET_AU198', 1, None, 0),
    ('GOLD.dust()', 'POWDER_GOLD', 'ModItems.powder_au198', 'POWDER_AU198', 1, None, 0),
    ('TH232.ingot()', 'INGOT_TH232', 'ModItems.ingot_thorium_fuel', 'INGOT_THORIUM_FUEL', 1, None, 0),
    ('TH232.nugget()', 'NUGGET_TH232', 'ModItems.nugget_thorium_fuel', 'NUGGET_THORIUM_FUEL', 1, None, 0),
    ('TH232.billet()', 'BILLET_TH232', 'ModItems.billet_thorium_fuel', 'BILLET_THORIUM_FUEL', 1, None, 0),
    ('COAL.gem()', 'Items.COAL', 'oil_tar:COAL', 'OIL_TAR_COAL', 1, 'SYNGAS', 50), ('COAL.dust()', 'POWDER_COAL', 'oil_tar:COAL', 'OIL_TAR_COAL', 1, 'SYNGAS', 50),
    ('COAL.block()', 'Items.COAL_BLOCK', 'oil_tar:COAL', 'OIL_TAR_COAL', 9, 'SYNGAS', 500), ('PVC.ingot()', 'INGOT_PVC', 'ModItems.ingot_c4', 'INGOT_C4', 1, 'COLLOID', 250),
    (OTAR % 'COAL', 'OIL_TAR_COAL', None, None, 0, 'COALOIL', 100), (OTAR % 'WAX', 'OIL_TAR_WAX', None, None, 0, 'RADIOSOLVENT', 100)]
EXPECTED_ROW_COUNT = 16
ORIGINAL_ROW_COUNT = 19
O_ROW = re.compile(r'recipes\.put\(new (OreDictStack|ComparableStack)\((.*)\),\s*new OutgasserRecipe\((.*)\)\);\s*$')
O_FLUID = re.compile(r'^(.*), (null|new FluidStack\(Fluids\.(\w+), ([\d_]+)\))$')
O_SOLID_ITEM = re.compile(r'new ItemStack\((Mod(?:Items|Blocks)\.\w+)\)$')
O_SOLID_TAR = re.compile(r'DictFrame\.fromOne\(ModItems\.oil_tar, EnumTarType\.(\w+)(?:, (\d+))?\)$')
N_ROW = re.compile(r'^\s*(gas|solid|both)\((.*)\);\s*$')

# Original crafting-manager key expressions -> the NEO ingredient (the generated recipe is compared against the parsed original row).
KEY_TABLE = {'ModBlocks.steel_grate': {'item': 'hbmsntm:steel_grate'}, 'Blocks.hopper': {'item': 'minecraft:hopper'}, 'ModItems.tank_steel': {'item': 'hbmsntm:tank_steel'},
             'ModBlocks.rbmk_blank': {'item': 'hbmsntm:rbmk_blank'}}


def scope_text(key_count, rows, assets, tests, total_tests):
    return (f'Goal25B (the second batch of Goal 25: RBMK operation and fuel logistics): the irradiation channel rbmk_outgasser (RBMKOutgasserBlock; RBMKOutgasserBlockEntity with 2 slots, a '
            f'64,000 mB gas tank that starts as tritium, DURATION 10,000, neutron flux adds fluxQuantity x min(1 - fluxRatio x 0.8, 1) x dialOutgasserSpeedMod while the channel can process and '
            f'the cycle completes strictly above 10,000, the gas leaves through the column ports (top, below, rbmk_loader layer) only, a meltdown flings 4-5 BLANK debris, console type OUTGASSER, '
            f'the EXTRA cell is an inventory and fluid proxy; RBMKOutgasserMenu, RBMKOutgasserScreen and the lid renderer) with the shaped GHG/GRG/GTG recipe (steel grate, hopper, structural '
            f'column, steel tank; the tier-4 anvil recycling row is not registered, the 4-tier anvil is unreachable); the RBMKNeutronHandler OUTGASSER branch (a channel that can process takes '
            f'the stream\'s flux and ends it, otherwise the stream passes on); OutgasserRecipes / hbmIrradiation.json with {rows} default rows (the original\'s 19 minus the 3 mushroom rows, '
            f'concrete items, lenient per-row file loading, fusionOnly rows kept but never processed), OutgasserRecipeSync, OutgasserRecipesPacket and OutgasserRecipeClientSync to the client and '
            f'a JEI irradiation category; {key_count} English keys and {key_count} Chinese entries (the block and container names and the five DODD overlay keys, all upstream); {assets} imported '
            f'resources (six channel textures and the GUI), {tests} RBMKOutgasserGameTests ({total_tests} GameTests in total, one batch per test) and the 25B real-game acceptance checklist '
            f'GOAL25B-ACCEPTANCE.md (written, not executed). Gameplay impact: tritium and gold-198 can be produced for the first time (lithium -> tritium, gold -> gold-198, thorium -> thorium '
            f'fuel, coal -> coal tar + syngas, PVC -> C4 + colloid, tars -> coal oil / radiosolvent); the RTG gold pellet chain closes through the gold-198 nuggets and billets; an irradiation '
            f'channel without a lid contaminates its chunk while a neutron stream passes.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal25b release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 31 scope copies) when it reproduces the baseline hash. A file the freeze did not copy has no reproducible start
    bytes when it was uncommitted-modified at the freeze (the Goal25A delivery); the blob at the start commit is tried (with CRLF where the working tree had it) for committed files;
    None when nothing reproduces the baseline hash."""
    if (START_FILES/p).is_file():
        data = (START_FILES/p).read_bytes()
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    try: blob = __import__('subprocess').check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT,
                                                      stderr=__import__('subprocess').DEVNULL)
    except Exception: return None
    for data in (blob, blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def start_pin(base, p):
    """The Goal25B start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does not list it)
    the hash the goal25a receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal25a packager protected (built there from the Goal21A..Goal24E starts and receipts and the goal25a start), plus every path the goal25a receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 25B baseline lists the goal24e receipt among them) and every release file of the frozen start
    (the goal25a package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes) are pinned
    at their Goal25B start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal25a packager set at its Goal25A start hash, for the records that changed between the two starts."""
    goal25a_start = read(GOAL25A_BASELINE)
    out = dict(goal25a_protected_paths(goal25a_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal25a receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal25a_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift.
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal25A and Goal25B starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal25a_start):
    """{path: {receipts, start_sha256, goal25a_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal25a receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal25a receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22, 23 and 24 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal25a '
                           'receipt does not hash it. Frozen at the Goal25B start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal25a) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal25a package; the goal25a receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal25a '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal25a_start_sha256=goal25a_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal25a_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def group(p):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA or p in OPTIONAL_JAVA: return 'production'
    if p in ASSETS: return 'production-resource'
    if p == ZH_INPUT: return 'production-chinese'
    if p == LOCALIZATION_RECORD: return 'production-localization-record'
    if p.startswith(GENERATED_ROOT): return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    return None


def original_shaped_row(text, kind, output, count):
    """{pattern, key, result} of the single original addRecipeAuto row producing ModBlocks/ModItems `output` x `count` (count defaults to 1 when the ItemStack gives none), or None. A key
    expression missing from KEY_TABLE maps to None."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.search(r'addRecipeAuto\(new ItemStack\(Mod'+kind+r'\.(\w+)(?:, (\d+))?\), new Object\[\] \{ (.*) \}\);', line)
        if not m or m.group(1) != output or int(m.group(2) or 1) != count: continue
        tokens = split_args(m.group(3))
        pattern = [t[1:-1] for t in tokens if t.startswith('"')]
        rest = [t for t in tokens if not t.startswith('"')]
        key = {rest[i].strip("'"): KEY_TABLE.get(rest[i+1]) for i in range(0, len(rest)-1, 2)}
        rows.append(dict(pattern=pattern, key=key, result=dict(count=count, id='hbmsntm:'+output)))
    return rows[0] if len(rows) == 1 else None


def row_matches(neo_row, o_row):
    """The generated row equals the parsed original row; an original ingredient with several accepted forms (OneOf) matches any of them."""
    if neo_row.get('pattern') != o_row['pattern'] or neo_row.get('result') != o_row['result'] or set(neo_row.get('key') or ()) != set(o_row['key']): return False
    return all((neo_row['key'][k] in v.forms) if isinstance(v, OneOf) else neo_row['key'][k] == v for k, v in o_row['key'].items())


def is_comment(line):
    s = line.strip()
    return not s or s.startswith(('//', '*', '/*', '*/'))


def top_split(text):
    """Split at the commas outside parentheses."""
    parts, depth, cur = [], 0, ''
    for c in text:
        if c == '(': depth += 1
        elif c == ')': depth -= 1
        if c == ',' and depth == 0: parts.append(cur.strip()); cur = ''
        else: cur += c
    parts.append(cur.strip())
    return parts


def original_rows(text):
    """[(input expression, solid key or None, solid count, fluid or None, mB)] of the original registerDefaults rows without the mushroom rows, and the number of mushroom rows."""
    body = text[text.index('public void registerDefaults()'):text.index('public static OutgasserRecipe getOutput(')]
    rows, mushrooms = [], 0
    for line in body.split('\n'):
        m = O_ROW.search(line.strip())
        if not m: continue
        kind, expr, rest = m.groups()
        if 'mushroom' in expr: mushrooms += 1; continue
        fm = O_FLUID.match(rest)
        solid_text, fluid, amount = fm.group(1), fm.group(3), fm.group(4)
        sm, tm = O_SOLID_ITEM.match(solid_text), O_SOLID_TAR.match(solid_text)
        if solid_text == 'null': solid, count = None, 0
        elif sm: solid, count = sm.group(1), 1
        elif tm: solid, count = 'oil_tar:'+tm.group(1), int(tm.group(2) or 1)
        else: solid, count = '?'+solid_text, 0
        rows.append((expr, solid, count, fluid, int(amount.replace('_', '')) if fluid else 0))
    return rows, mushrooms


def neo_rows(text):
    """[(input name, solid name or None, count, fluid or None, mB)] of the NEO registerDefaults rows, in source order."""
    if 'void registerDefaults()' not in text: return None
    body = text[text.index('void registerDefaults()'):text.index('void deleteRecipes()')]
    name = lambda e: re.sub(r'\.get\(\)$', '', e).replace('NtmItems.', '').replace('NtmBlocks.', '')
    rows = []
    for line in body.split('\n'):
        m = N_ROW.match(line)
        if not m: continue
        args = top_split(m.group(2))
        if m.group(1) == 'gas': rows.append((name(args[0]), None, 0, args[1].replace('Fluids.', ''), int(args[2].replace('_', ''))))
        elif m.group(1) == 'solid': rows.append((name(args[0]), name(args[1]), 1, None, 0))
        else: rows.append((name(args[0]), name(args[1]), int(args[2]), args[3].replace('Fluids.', ''), int(args[4].replace('_', ''))))
    return rows


def ordered(text, tokens):
    """Whether the tokens occur in the text in this order (each after the previous one)."""
    at = -1
    for t in tokens:
        at = text.find(t, at+1)
        if at < 0: return False
    return True


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
    goal25a_start = read(GOAL25A_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal25B commits nothing), the recorded start on top of the Goal 24 close-out commit
    # with the uncommitted Goal25A delivery.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 25 planning commit'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 25 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    status_lines = base['target_status'].splitlines()
    assert len(status_lines) == START_STATUS_LINES, f'The frozen start status has {len(status_lines)} lines, not the {START_STATUS_LINES} of the uncommitted Goal25A delivery'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal25a receipt records another original commit than the frozen start'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal25B: '+head
    closeout = git_ro(ROOT, 'rev-parse', 'HEAD~1').strip()
    assert closeout.startswith(GOAL24_CLOSEOUT), 'NEO HEAD~1 is not the Goal 24 close-out commit 17c8062f'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and base['start_content']['uncommitted'].startswith('the Goal25A delivery'), 'Baseline start content differs'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d',
                                                          'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b', 'goal24c', 'goal24d', 'goal24e'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_lines'] == START_STATUS_LINES \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'] and startup['generated_resources_verified'] == base['stamp_state']['generated_resources_verified'], \
        'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_verified'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal25a generated tree'
    # The 65 uncommitted status lines are the goal25a delivery: the same paths as the goal25a receipt's changed_files, and every hashed report/record at the hash the receipt records.
    status_paths = {l[3:] for l in status_lines}
    delivered = {e['path']: e for e in prior_receipt['changed_files']}
    assert status_paths == set(delivered), 'The frozen start status paths are not the goal25a delivery (changed_files): '+str(sorted(status_paths ^ set(delivered))[:6])
    delivery_differs = sorted(p for p, e in delivered.items() if base['files'].get(p) != e['after_sha256'])
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal25a package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the start is not the goal25a package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal25a receipt list + the goal25a package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal25a receipt count + the goal25a release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal25a receipt'
    assert base['previous_receipt_evidence_drift'] == {}, 'The goal25a receipt drifted at the start: '+str(list(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal25a_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal25a receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal25b. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, f'Path changed since the Goal25B start that the owner table does not list (production outside the {len(MODIFIED_JAVA)} modified Java files, the {len(NEW_JAVA)} new classes incl. '
         'RBMKOutgasserGameTests, the 7 resources, zh_cn.json and the mapping, a protected or frozen record, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal25A / Goal24 records or the 25C / 25D planning documents changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal25B start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD, ANVIL_RECIPES] + GENERATED + SHARED_RECORDS + REPORTS[:1]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    need(sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES], f'{ANVIL_RECIPES} changed since the start (the tier-4 anvil recycling row of the channel stays unregistered: the 4-tier anvil is unreachable)')
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION + OPTIONAL_JAVA if p.startswith('src/')})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified and {len(NEW_JAVA)} new Java files, the 7 resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    goal25_now = sha(ROOT/GOAL25_RECORD)
    concurrent_record = dict(sessions=[], note='No concurrent session edited the NEO repository: baseline.json and startup-verification.json record none; migration/GOAL25.md and GOAL25B.md are edited by the main agent of this batch.',
                             goal25_md=dict(start_sha256=base['files'][GOAL25_RECORD], current_sha256=goal25_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p)) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, owners=[OWNER], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal25B takes no new snapshot)'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-aee05a40f10f snapshot changed'
    production_changed = [p for p in PRODUCTION + OPTIONAL_JAVA if p in changes]

    # The modified production files keep their start line endings; new Java files are not mixed.
    start_text = {}
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]:
        if p not in changes: continue
        data = start_bytes(base, p)
        if not need(data is not None, p+' has no reproducible start bytes (not in baseline-files and the start-commit blob does not match the baseline hash: its start version was uncommitted)'): continue
        start_text[p] = data
        start_eol, eol = eol_counts(data), eol_counts((ROOT/p).read_bytes())
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}')
    for p in NEW_JAVA:
        if (ROOT/p).is_file():
            eol = eol_counts((ROOT/p).read_bytes())
            need(eol[0] == 0 or eol[1] == 0, f'{p} mixes CRLF and LF line endings: {eol}')

    # Production Java facts: insert-only registration files, every line edit counted, the removed lines of the edited files accounted for.
    insert_summary, edit_summary, inserted_lines, added_lines, removed_lines, removed_comments = {}, {}, {}, {}, {}, {}
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]:
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
        elif p in ALLOWED_REMOVED_CODE:
            # Compared stripped: re-indented lines cancel out; what is left was really removed.
            net_removed = list((Counter(l.strip() for l in start_lines) - Counter(l.strip() for l in live_lines)).elements())
            comments = [l for l in net_removed if is_comment(l)]
            code = [l for l in net_removed if not is_comment(l)]
            stray = [l for l in code if not l.startswith(ALLOWED_REMOVED_CODE[p]) or not ALLOWED_REMOVED_CODE[p]]
            need(not stray, f'{p} removes start code lines the owner table does not allow: {[l[:90] for l in stray[:4]]}')
            removed_comments[p] = [l for l in comments if l]
    # Language provider: the added lines carry exactly the new keys (blocks through their constants, plain keys); nothing is removed.
    provider_added = []
    if PROVIDER in added_lines:
        keys_added, other = base_provider_keys(added_lines[PROVIDER])
        provider_added = sorted(keys_added)
        stray = [l for l in other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} adds lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(keys_added) == len(set(keys_added)), f'{PROVIDER} adds a language key twice')
        need(provider_added == sorted(KEYS), f'{PROVIDER} adds the language keys differently than expected: missing {sorted(set(KEYS) - set(provider_added))[:6]}, unexpected {sorted(set(provider_added) - set(KEYS))[:6]}')
        need(not base_provider_keys(removed_lines[PROVIDER])[0], f'{PROVIDER} removes language entries: {base_provider_keys(removed_lines[PROVIDER])[0][:4]}')
    # The original, parsed from the stored blobs at the recorded commit (independent of the worktree's line endings).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    neo_text = lambda path: (ROOT/path).read_text(encoding='utf-8').replace('\r\n', '\n') if (ROOT/path).is_file() else ''
    # NEO constants against the original (block entity, menu, screen, file name).
    constants, constants_bad = {}, []
    for cid, (o_path, o_regex, n_path, n_regex, expected, *neo_expected) in CONSTANTS.items():
        o_values = captured(original_text(o_path), o_regex)
        n_values = captured(neo_text(n_path), n_regex) if (ROOT/n_path).is_file() else None
        assert o_values == [normalize_value(str(e)) for e in expected] or o_values == expected, \
            f'The original constant {cid} ({o_path}) is {o_values}, the owner table expects {expected}'
        wanted = [normalize_value(str(e)) for e in neo_expected[0]] if neo_expected else o_values
        constants[cid] = dict(original=o_values, neo=n_values, original_path=o_path, neo_path=n_path, **(dict(neo_expected=wanted) if neo_expected else {}))
        if n_values != wanted: constants_bad.append(cid)
    need(not constants_bad and all(c['neo'] is not None for c in constants.values()),
         f'NEO constants differ from the original (or the NEO source is missing / its text differs from the handoff): {sorted(set(constants_bad) | {k for k, c in constants.items() if c["neo"] is None})}')
    neo_facts, facts_bad = {}, []
    for fid, (n_path, n_regex, expected) in NEO_FACTS.items():
        n_values = captured(neo_text(n_path), n_regex) if (ROOT/n_path).is_file() else None
        wanted = [normalize_value(str(e)) for e in expected]
        neo_facts[fid] = dict(neo=n_values, expected=wanted, neo_path=n_path)
        if n_values != wanted: facts_bad.append(fid)
    need(not facts_bad, f'NEO-only facts differ from the owner table (or the NEO source is missing / its text differs): {facts_bad}')
    # canProcess order (the setTankType side effect sits before the capacity test, after the type/fill refusal) in both texts; the OUTGASSER branch of the neutron handler takes the flux
    # only for a channel that can process and then returns.
    order_tokens = ['gas.getTankType() != fluid.type && gas.getFill() > 0', 'gas.setTankType(fluid.type);', 'gas.getFill() + fluid.fill > gas.getMaxFill()']
    can_process_order = dict(original=ordered(original_text(O_TE), order_tokens), neo=ordered(neo_text(OUTGASSER_BE), order_tokens))
    assert can_process_order['original'], 'The original canProcess no longer has the refusal / setTankType / capacity order'
    need(can_process_order['neo'], f'{OUTGASSER_BE} canProcess does not keep the original order: refusal, setTankType, capacity test')
    branch = re.compile(r'type == RBMKType\.OUTGASSER\) \{.*?\.canProcess\(\)\) \{\s*column\.receiveFlux\(this\);\s*return;\s*\}', re.S)
    neutron = dict(original=bool(branch.search(original_text(O_NEUTRON))), neo=bool(branch.search(neo_text(NEUTRON_HANDLER))) if (ROOT/NEUTRON_HANDLER).is_file() else None)
    assert neutron['original'], 'The original RBMKNeutronHandler OUTGASSER branch is not canProcess -> receiveFlux -> return'
    need(neutron['neo'], f'{NEUTRON_HANDLER} OUTGASSER branch is not canProcess -> receiveFlux -> return')
    # The 16 default rows against the original's 19 rows minus the 3 mushroom rows.
    o_rows, o_mushrooms = original_rows(original_text(O_RECIPES))
    assert len(o_rows) + o_mushrooms == ORIGINAL_ROW_COUNT and o_mushrooms == 3, f'The original lists {len(o_rows)} rows + {o_mushrooms} mushroom rows, not 16 + 3'
    assert o_rows == [(e[0], e[2], e[4], e[5], e[6]) for e in EXPECTED_ROWS], 'The original default rows differ from the owner table: '+str(
        [r for r in o_rows if r not in [(e[0], e[2], e[4], e[5], e[6]) for e in EXPECTED_ROWS]][:3])
    n_rows = neo_rows(neo_text(OUTGASSER_RECIPES)) if (ROOT/OUTGASSER_RECIPES).is_file() else None
    expected_neo_rows = [(e[1], e[3], e[4], e[5], e[6]) for e in EXPECTED_ROWS]
    default_rows = dict(count_original=ORIGINAL_ROW_COUNT, mushroom_rows_excluded=o_mushrooms, count_expected=EXPECTED_ROW_COUNT, original=[list(r) for r in o_rows],
                        neo=[list(r) for r in n_rows] if n_rows is not None else None, expected_neo=[list(r) for r in expected_neo_rows])
    need(n_rows == expected_neo_rows, f'{OUTGASSER_RECIPES} registerDefaults rows differ from the original rows minus the mushroom rows ({EXPECTED_ROW_COUNT}): '
         + ('source missing' if n_rows is None else f'{len(n_rows)} rows, differing {[r for r in n_rows if r not in expected_neo_rows][:3]}, missing {[r for r in expected_neo_rows if r not in n_rows][:3]}'))
    # The column type offset equals the original ColumnType (TileEntityRBMKConsole), the same table the console uses.
    o_console_text = original_text(O_CONSOLE)
    column_types = dict(original=enum_offsets(o_console_text, COLUMN_TYPES), neo=enum_offsets(neo_text(COLUMN_TYPE_FILE), COLUMN_TYPES))
    assert list(column_types['original']) == list(COLUMN_TYPES), 'The original ColumnType members are not the owner table\'s'
    need(column_types['neo'] == column_types['original'] and column_types['neo'].get('OUTGASSER') == 80, f'{COLUMN_TYPE_FILE} members / offsets differ from the original ColumnType (TileEntityRBMKConsole)')
    # Logical sides: the block entity, block, menu, recipe table, sync and packet (common code) import nothing from net.minecraft.client; the screen and the JEI handler exist.
    common = (OUTGASSER_BE, OUTGASSER_BLOCK, OUTGASSER_MENU, OUTGASSER_RECIPES, OUTGASSER_SYNC, OUTGASSER_PACKET)
    client_imports = {p: (ROOT/p).is_file() and 'net.minecraft.client' in neo_text(p) for p in common}
    need(not any(client_imports.values()) and all((ROOT/p).is_file() for p in common + (OUTGASSER_SCREEN, IRRADIATION_JEI, OUTGASSER_CLIENT_SYNC)),
         'common-side channel classes are missing or import net.minecraft.client: '+str(sorted(p for p, v in client_imports.items() if v)))
    need('IRBMKFluxReceiver' in neo_text(OUTGASSER_BE) and 'extends RBMKSlottedBaseBlockEntity' in neo_text(OUTGASSER_BE),
         f'{OUTGASSER_BE} is not an RBMKSlottedBaseBlockEntity implementing IRBMKFluxReceiver')
    # Imported resources: byte for byte equal to the original worktree file and its stored blob, and to the ownership record.
    imported = {}
    ownership = None
    if need((ROOT/RESOURCE_OWNERSHIP).is_file(), 'record missing: '+RESOURCE_OWNERSHIP):
        ownership = read(ROOT/RESOURCE_OWNERSHIP)
        entries = {a.get('target_path'): a for a in ownership.get('assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(ASSETS), f'{RESOURCE_OWNERSHIP} does not list the {len(ASSETS)} resources at {SOURCE_HEAD[:8]}: '
             f'missing {sorted(set(ASSETS) - set(entries))[:3]} ({len(set(ASSETS) - set(entries))}), unexpected {sorted(set(entries) - set(ASSETS))[:3]}')
        need(all(entries.get(t, {}).get('source_path') == o for t, o in ASSETS.items()), f'{RESOURCE_OWNERSHIP} source paths differ from the layout rules of the owner table')
    for target, original in ASSETS.items():
        assert (SOURCE/original).is_file(), 'Original resource missing: '+original
        if not (ROOT/target).is_file():
            need(False, 'resource not imported yet: '+target)
            continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        entry = {a.get('target_path'): a for a in (ownership or {}).get('assets', [])}.get(target, {})
        imported[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size,
                                original_worktree_sha256=sha(SOURCE/original), original_blob_sha256=hashlib.sha256(blob).hexdigest(), original_blob_bytes=len(blob),
                                line_endings_converted_from_blob=blob != checked_out, source_last_change_commit=entry.get('source_last_change_commit'))
        need((ROOT/target).read_bytes() == checked_out, f'{target} is not byte-identical to the original worktree file {original}')
        need(checked_out == blob, f'{target} is not byte-identical to the stored blob of {original} at {SOURCE_HEAD[:8]}')
        if entry:
            need(entry.get('source_path') == original and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('bytes') == (ROOT/target).stat().st_size
                 and entry.get('blob_sha256') == hashlib.sha256(blob).hexdigest(),
                 f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original path: {target}')
    # features.json: the new group, the unchanged status and reviewed_source_commit of the previous groups.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES <= set(start_features) and not set(NEW_FEATURES) & set(start_features), \
        'The start mapping does not hold the groups of 24B-25A (rbmk-fuel, rbmk-reactor, rbmk-control, rbmk-steam, rbmk-console, rbmk-storage, rbmk-recycling) and not yet the Goal25B group'
    new_groups = {g: by_id[g] for g in NEW_FEATURES if g in by_id}

    # 4. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_en = dict(added=sorted(KEYS), removed=[], changed=[])
    expected_zh = dict(added=sorted(KEYS), removed=[], changed=[])
    expected_map = dict(added=sorted(KEYS), removed=[], changed=[])
    need(en_delta == expected_en, f'generated en_us.json delta is not the {len(KEYS)} new keys (no value changed): '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_zh, f'zh_cn.json delta is not the {len(KEYS)} new keys (all old values unchanged): '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_map, f'zh_cn-map.json delta is not the {len(KEYS)} new entries (no old entry changed): '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal25a totals'
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal25a totals {totals} + {len(KEYS)}')
    language_kinds, original_text_checked = {}, False
    if map_delta == expected_map and en_delta == expected_en and zh_delta == expected_zh:
        language_kinds = dict(Counter(map_now[k].get('kind') for k in KEYS))
        need(language_kinds == EXPECTED_KINDS, f'zh_cn-map.json kinds of the new entries are {language_kinds}, expected {EXPECTED_KINDS}')
        o_en, o_zh = lang_file(O_LANG_EN), lang_file(O_LANG_ZH)
        bad = []
        for k, (source_key, kind) in SOURCE_KEYS.items():
            e = map_now[k]
            if e.get('target_en') != en_now.get(k) or e.get('target_zh') != zh_now.get(k) or not zh_now.get(k): bad.append(k)
            elif e.get('kind') != kind or en_now[k].count('%s') != zh_now[k].count('%s'): bad.append(k)
            elif kind == 'local' and not e.get('reason'): bad.append(k)
            elif source_key is not None and (e.get('source_key') != source_key or e.get('source_en') != o_en.get(source_key) or e.get('source_zh') != o_zh.get(source_key)): bad.append(k)
            elif kind == 'upstream' and (e.get('source_zh') != e.get('target_zh') or e.get('source_en') != e.get('target_en')): bad.append(k)
        need(not bad, 'zh_cn-map.json entries do not match en_us.json / zh_cn.json, the original en_US.lang / zh_CN.lang values at aee05a40f or the expected kinds: '+str(bad[:8]))
        original_text_checked = not bad
    map_kinds = dict(Counter(e.get('kind') for e in map_now.values()))
    start_kinds = dict(Counter(e.get('kind') for e in map_start.values()))
    expected_kinds_now = {k: start_kinds.get(k, 0) + EXPECTED_KINDS.get(k, 0) for k in set(start_kinds) | set(EXPECTED_KINDS)}
    need(map_kinds == expected_kinds_now, f'mapping kinds are {map_kinds}, expected {expected_kinds_now} (upstream +{EXPECTED_KINDS.get("upstream", 0)}, local +{EXPECTED_KINDS.get("local", 0)}, deferred unchanged)')
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    stamp_current = not stale and not mismatch and not unrecorded
    need(stamp_current, f'{STAMP} not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
    start_stamp = read(START_FILES/STAMP)
    start_generated = start_stamp['generated']
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal25a generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    advancements = sorted(p for p in generated_added if ADVANCEMENT.fullmatch(p))
    EXPECTED_GENERATED = sorted(EXPECTED_GENERATED_BASE + advancements)
    need(len(advancements) == 1, 'The generated advancements are not exactly one for rbmk_outgasser: '+str(advancements))
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected blockstate, model, loot table, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, the pickaxe tag and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # The pickaxe tag: the start list plus rbmk_outgasser, in the start order.
    tag_start_bytes = start_bytes(base, GENERATED_ROOT+TAG_ENTRY)
    assert tag_start_bytes is not None, 'No reproducible start bytes for the pickaxe tag'
    tag_start, tag_now = json.loads(tag_start_bytes.decode('utf-8-sig'))['values'], read(ROOT/(GENERATED_ROOT+TAG_ENTRY))['values']
    tag_inserted = insertions(tag_start, tag_now)
    need(tag_inserted is not None and [v for _, v in tag_inserted] == ['hbmsntm:rbmk_outgasser'],
         f'the pickaxe tag is not the start list plus hbmsntm:rbmk_outgasser: inserted {None if tag_inserted is None else [v for _, v in tag_inserted]}')
    # Recipes: the shaped channel recipe (computed from the generated JSON) against the original row; no anvil row is registered.
    o_crafting, o_anvil = original_text(O_CRAFTING), original_text(O_ANVIL)
    o_row = original_shaped_row(o_crafting, 'Blocks', 'rbmk_outgasser', 1)
    assert o_row is not None and all(v is not None for v in o_row['key'].values()), f'The original rbmk_outgasser recipe row could not be parsed or translated: {o_row}'
    anvil_lines = [i for i, l in enumerate(o_anvil.split('\n'), 1) if 'ModBlocks.rbmk_outgasser' in l]
    assert anvil_lines, 'The original has no anvil row for rbmk_outgasser any more'
    crafting = {}
    if (ROOT/G_OUTGASSER_RECIPE).is_file():
        data = read(ROOT/G_OUTGASSER_RECIPE)
        neo_row = dict(pattern=data.get('pattern'), key=data.get('key'), result=data.get('result'))
        crafting['rbmk_outgasser'] = dict(type=data.get('type'), neo=neo_row, original=jsonable(o_row))
        need(data.get('type') == 'minecraft:crafting_shaped' and row_matches(neo_row, o_row), f'{G_OUTGASSER_RECIPE} differs from the original recipe row: {neo_row} vs {jsonable(o_row)}')
    else:
        need(False, 'generated recipe missing: '+G_OUTGASSER_RECIPE)
    # Mapped paths: every changed path inside the compare inventory must be matched by a feature group.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    for gid in NEW_FEATURES:
        entry = new_groups.get(gid)
        if not need(entry is not None, f'migration/features.json lacks the group {gid}'): continue
        need(entry.get('status') == 'partial-unverified' and entry.get('reviewed_source_commit') == SOURCE_HEAD, f'features.json group {gid} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in FEATURE_SOURCES[gid] if not feature_matches(entry, 'source', p)]
        need(not missing_source, f'features.json group {gid} lists in neither source_paths nor source_watch: {missing_source[:4]} ({len(missing_source)} paths)')
        missing_target = [p for p in FEATURE_TARGETS[gid] if not feature_matches(entry, 'target', p)]
        need(not missing_target, f'features.json group {gid} lacks in target_paths / target_watch: {missing_target[:4]} ({len(missing_target)} paths)')
        absent = [p for p in entry.get('source_paths', []) if not (SOURCE/p).is_file()]
        need(not absent, f'features.json group {gid} source_paths missing in the original: {absent}')
    need(set(by_id) == set(start_features) | set(NEW_FEATURES), 'features.json group ids are not the start ids + '+', '.join(NEW_FEATURES)+': '+str(sorted(set(by_id) ^ (set(start_features) | set(NEW_FEATURES)))))
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
        if rel in base['files']: total_start += annotations(START_FILES/rel if base['files'][rel] != sha(p) and (START_FILES/rel).is_file() else p)
    assert total_start == prior_receipt['gametest']['tests'], 'The start GameTest sources do not hold the previous count of '+str(prior_receipt['gametest']['tests'])
    gametest_added = total_now - total_start
    gametest_expected = total_now
    outgasser_test_names = sorted(GAMETEST_METHOD.findall((ROOT/OUTGASSER_TESTS).read_text(encoding='utf-8'))) if (ROOT/OUTGASSER_TESTS).is_file() else []
    outgasser_annotations = annotations(ROOT/OUTGASSER_TESTS) if (ROOT/OUTGASSER_TESTS).is_file() else 0
    need(bool(outgasser_test_names) and outgasser_annotations == len(outgasser_test_names), f'{OUTGASSER_TESTS} holds {outgasser_annotations} @GameTest annotations and {len(outgasser_test_names)} parsed methods')
    need(gametest_added == outgasser_annotations, f'GameTest sources grew by {gametest_added} tests, RBMKOutgasserGameTests holds {outgasser_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in outgasser_test_names), 'GameTest log lacks "[hbm-rbmk-outgasser] <name> passed" for: '+str([n for n in outgasser_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal25b/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal25b/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal25b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal25b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal25b/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA + OPTIONAL_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal25b/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal25a final run plus the Goal25B verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal25a final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal25B suite is already in the goal25a final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal25b/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal25a final set + the Goal25B verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal25b/'+VERIFY_REPORT+' (tools/migration/verify_goal25b_rbmk_outgasser.py report)'):
        report = read(OUT/VERIFY_REPORT)
        required_hashes = [p for p in production_changed if not p.startswith(RES) or p == ZH_INPUT]
        problems = report_problems(report, required_hashes)
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        mutations = report.get('mutations')
        mutation_entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
        detected = summary_part.get('mutations_detected', sum(1 for e in mutation_entries if isinstance(e, dict) and e.get('detected') is True))
        total = summary_part.get('mutations_total', summary_part.get('mutations_applied', len(mutation_entries)))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=NEW_TOOLS[0],
                        tool_sha256=sha(ROOT/NEW_TOOLS[0]) if (ROOT/NEW_TOOLS[0]).is_file() else None, mutations_detected=f'{detected}/{total}', mutations_total=total,
                        checks_passed=summary_part.get('checks_passed'), command=report.get('command'))
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(re.findall(r'(?:TileEntityRBMKOutgasser|RBMKOutgasser|ContainerRBMKOutgasser|GUIRBMKOutgasser|OutgasserRecipes|OutgasserHandler|RBMKNeutronHandler|RBMKDials|'
                                                      r'CraftingManager|AnvilRecipes|TileEntityRBMKConsole)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        # The verifier ran against the final GameTest log and expected the sources' total.
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal25a compare target paths (which hold the 24A-25A paths) plus this batch's compare-inventory paths).
    cmp25a = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal25a/compare.json differs from the goal25a receipt'
    c25a_added = sorted(p for p in compare_paths(cmp25a['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c25a_modified = sorted(p for p in compare_paths(cmp25a['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(c25a_added) | set(c25a_modified) | set(own_target))
    expected_added = sorted(set(c25a_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal25b/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-25a paths + %d of this batch)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(c25a_added) + len(c25a_modified), len(own_target))):
        cmp = read(OUT/COMPARE)
        need(cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, COMPARE+' is not against the aee05a40f snapshot')
        need(cmp['current_target_state']['commit'] == start_head, COMPARE+' records another target commit than the start commit')
        counts = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(all(v == 0 for v in counts['source'].values()) and counts['target']['removed'] == 0, COMPARE+' original is not 0/0/0 or the target removes paths: '+str(counts))
        listed = sorted(p for p in compare_paths(cmp['changes']['target']['added']) | compare_paths(cmp['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
        need(listed == expected_target, COMPARE+' target set differs: extra %s, missing %s' % (sorted(set(listed) - set(expected_target))[:8], sorted(set(expected_target) - set(listed))[:8]))
        listed_added = sorted(p for p in compare_paths(cmp['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
        need(listed_added == expected_added, f'{COMPARE} target added set differs: extra {sorted(set(listed_added) - set(expected_added))[:6]}, missing {sorted(set(expected_added) - set(listed_added))[:6]}')
        need(not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], COMPARE+' reports unmapped changes: '+str(cmp['unmapped_changes']))
        need(not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], COMPARE+' reports removed features or missing files')
        states = Counter(f.get('state') for f in cmp['features'])
        need(len(cmp['features']) == len(features) and set(states) <= {'target-changed', 'no-observed-file-change'}, f'{COMPARE} feature states are {dict(states)}, expected only target-changed / no-observed-file-change over {len(features)} groups')
        for g in NEW_FEATURES:
            need(any(f.get('id') == g and f.get('state') == 'target-changed' for f in cmp['features']), f'{COMPARE} does not report {g} as target-changed')
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal25a (goal25a compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal25a_paths=len(c25a_added) + len(c25a_modified), goal25b_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the groups of 24B-25A.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-25A)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal25b.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal25a) package (run the final build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 7 resources and every compiled class equal the sources.
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [e for e, t in asset_entries.items() if e not in names or not (ROOT/t).is_file() or jar.read(e) != (ROOT/t).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json, the imported resources or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == en_delta == expected_en and zh_jar == zh_delta == expected_zh,
                 f'JAR en_us.json or zh_cn.json delta against the previous package is not the {len(KEYS)} new keys: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            recompile_only = set()
            for n, pairs in RECOMPILE_ONLY.items():
                if n not in jar_delta['modified']: continue
                patched = prior.read(n)
                for a, b in pairs:
                    assert patched.count(a) == 1, (n, a)
                    patched = patched.replace(a, b)
                if patched == jar.read(n): recompile_only.add(n)
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        generated_entries = set(generated_added)
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if n.endswith('.class') and owner_class(n) in PRODUCTION_JAVA: owner = [OWNER]
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY, TAG_ENTRY, 'META-INF/MANIFEST.MF'): owner = [OWNER]
                elif kind == 'added' and (n in asset_entries or n in generated_entries): owner = [OWNER]
                elif kind == 'modified' and n in recompile_only and owner_class(n) not in changes: owner = [RECOMPILE_OWNER]
                if not owner: unowned.append(f'{kind}: {n}' + (' [source ' + owner_class(n) + ' unchanged since the start: a recompile difference, not a source change]' if n.endswith('.class') and owner_class(n) not in changes else ''))
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 7 imported resources, the generated additions and '
             'the modified en_us.json / zh_cn.json / pickaxe tag / MANIFEST.MF are owned): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA),
             'Changed Java sources and goal25b JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, TAG_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + pickaxe tag + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        inner = 'com/hbm/inventory/recipes/OutgasserRecipes$OutgasserRecipe.class'
        need(inner in jar_delta['added'], inner+' is not an added JAR class')
        for p in MODIFIED_JAVA:
            if p in SAME_CLASS_JAVA: continue
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
    # Informational (not a pending item): top-level OUT files no evidence list indexes, for the main agent to extend REVIEW_EVIDENCE with.
    indexed = {Path(p).relative_to(OUT.relative_to(ROOT)).as_posix() for p in evidence if p.startswith(OUT.relative_to(ROOT).as_posix()+'/')}
    unindexed = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in indexed and p.name != 'baseline.json')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added),
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal25a_start=sorted(repinned),
                   delivery_hash_differs_from_goal25a_receipt=delivery_differs,
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, removed_comment_lines={p: len(v) for p, v in removed_comments.items()},
                   constants={k: c['neo'] == c.get('neo_expected', c['original']) for k, c in constants.items()}, neo_facts={k: f['neo'] == f['expected'] for k, f in neo_facts.items()},
                   can_process_order=can_process_order, neutron_branch=neutron, default_rows_equal=n_rows == expected_neo_rows, default_row_count=len(n_rows) if n_rows is not None else None,
                   column_types_equal=column_types['neo'] == column_types['original'],
                   client_imports_in_common_classes=sorted(p for p, v in client_imports.items() if v),
                   crafting_recipes=len(crafting), gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_outgasser_tests=outgasser_test_names, final_suites_expected=final_expected,
                   compare=opt(compare, 'counts'), compare_target_expected=len(expected_target), compare_added_expected=len(expected_added),
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta, class_owners=class_owners,
                   protected_paths=len(protected), old_releases_preserved=len(old_releases), preserved_release_files=len(base['old_release_files']),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)),
                   out_files_not_indexed=unindexed)
    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)

    # The receipt: assembled in both modes (None where the evidence does not exist yet in --check); only the real run writes it, and there every need() above raised.
    dest = RELEASE/RELEASE_NAME
    digest = sha(JAR)
    hashes = {p: sha(ROOT/p) for p in reports if (ROOT/p).is_file()}
    rbmk_outgasser = dict(neo=[OUTGASSER_BLOCK, OUTGASSER_BE, OUTGASSER_RECIPES, OUTGASSER_SYNC, OUTGASSER_PACKET, OUTGASSER_CLIENT_SYNC, OUTGASSER_MENU, OUTGASSER_SCREEN, IRRADIATION_JEI, NEUTRON_HANDLER],
                          original=[p for p in O_SOURCES], constants=constants, neo_only_facts=neo_facts, known_differences=KNOWN_DIFFERENCES, default_rows=default_rows,
                          can_process_order=can_process_order, neutron_branch=neutron, column_types=column_types, original_references=original_refs,
                          defaults=dict(slots=2, duration=10000, tank_fluid='TRITIUM', tank_capacity_mb=64000, efficiency='min(1 - fluxRatio * 0.8, 1) * dialOutgasserSpeedMod',
                                        completion='progress > DURATION (strict)', can_process_order='refusal (type differs and fill > 0), setTankType, capacity test', melt_debris='4 + rand(2) BLANK',
                                        default_rows=EXPECTED_ROW_COUNT, original_rows=ORIGINAL_ROW_COUNT, mushroom_rows_excluded=3, gui_progress_px=13, gui_gas_px=42,
                                        gui_size='176 x 186', tank_tooltip='112/21 16 x 48'),
                          note='The irradiation channel keeps 2 slots (input slot 0, output slot 1 behind SlotCraftingOutput) and a 64,000 mB gas tank that starts as tritium (TileEntityRBMKOutgasser :36-47). '
                               'Neutron flux reaches it only while canProcess() holds (RBMKNeutronHandler :323-329: otherwise the stream passes on); progress grows by fluxQuantity x min(1 - fluxRatio x 0.8, 1) x '
                               'dialOutgasserSpeedMod and the cycle completes strictly above 10,000 (:69-82). canProcess refuses a row whose gas differs from a non-empty tank, sets the tank type as a side effect '
                               'and only then tests the capacity (:84-108); a fusionOnly row never runs. process consumes one input, adds the gas and the solid output (:110-129). A meltdown flings 4 + '
                               'rand(2) BLANK debris (:131-141); the console type is OUTGASSER (offset 80). Automation inserts into slot 0 only for inputs with a row and takes only from slot 1 (:194-206); '
                               'the gas leaves through the column ports only (RBMKBaseBlockEntity.getPortConnections). The EXTRA cell is a ProxyCombo inventory + fluid proxy (RBMKOutgasser.java:18-19). The '
                               'table has 16 default rows (the original\'s 19 minus the three mushroom rows, in the original order; concrete items instead of ore dictionary names); hbmIrradiation.json is '
                               'loaded row by row (bad rows logged and skipped), synced strictly to clients, and shown in a JEI irradiation category (fusionOnly rows hidden). Not migrated: the tier-4 anvil '
                               'recycling row (AnvilRecipes.java:914-920, 4-tier anvil unreachable), the OpenComputers callbacks, the mushroom rows, the fusion breeder. Tritium has no NEO consumer yet '
                               '(the original consumers belong to the deferred fusion reactor).')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), EXPECTED_ROW_COUNT, len(ASSETS), len(outgasser_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=start_head[:8],
                   uncommitted_start=dict(status_entries=len(status_lines), description=base['start_content']['uncommitted'], base_release=previous_rel, status=status_lines,
                                          delivery_paths_match_goal25a_changed_files=True, paths_whose_start_hash_differs_from_goal25a_after_sha256=delivery_differs,
                                          note='The start hashes are the working tree at the freeze (the Goal25A delivery is uncommitted), not the commit 783b6d13.'),
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, goal24_closeout_commit=closeout,
                                      note='The start tree is HEAD 783b6d13 (the Goal 25 planning commit, local, not pushed) on top of the pushed Goal 24 close-out commit 17c8062f, PLUS the uncommitted '
                                           'Goal25A delivery (65 status lines, packaged as goal25a). build/libs at the start IS the goal25a package ed8ef3e4... The original did not move since 24A '
                                           '(aee05a40f). The freeze copied 31 scope files to baseline-files; paths this batch changes record the start hash as before_sha256, and a modified file the freeze '
                                           'did not copy has no reproducible start bytes (its start version is in no commit).'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, removed_comment_lines=removed_comments, start_copies_supplement=[],
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   rbmk_outgasser=rbmk_outgasser,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note=f'All {EXPECTED_KINDS.get("upstream", 0)} entries are upstream with the original English and Chinese verbatim: the block name (tile.rbmk_outgasser.name) and the container '
                                      'name (container.rbmkOutgasser), which the JEI category reuses, and the five DODD overlay keys (tile.rbmk.dodd.progress / gas / gas_type / gas_p / gas_max) of the '
                                      "channel's diagnostic data. No existing key changes its English value."),
                   recipes=dict(crafting=crafting, not_registered=['anvil row (tier 4) rbmk_outgasser -> rbmk_blank + 6 steel_grate + tank_steel + hopper: '
                                'AnvilRecipes.java:914-920, the 4-tier anvil is unreachable in NEO (NtmRecipeProvider comment)'],
                                original_references={k: v for k, v in original_refs.items() if k.startswith(('recipe_', 'anvil_'))},
                                anvil_recipes_unchanged=sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES],
                                note='The channel recipe equals the original row (CraftingManager :769); AnvilRecipes stays unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith('repinned_since_')},
                   repinned_since_goal25a_start={p: dict(goal25a_start_pin_sha256=h, goal25b_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_outgasser_tests=outgasser_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per RBMKOutgasserGameTests test: the flux rates and '
                                      'efficiency, the cycle and its gas / solid rules, the neutron handler branch, the ports and automation, the recipe table and its file and sync handling and the '
                                      'meltdown; no client (the channel screen, the lid renderer, the JEI irradiation category and the crafting GUI are not rendered), no real player, no saved world, '
                                      'no survival chain.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['rbmk_recycling (the Goal25A-only key; Goal25B adds rbmk_outgasser)', 'pile_balance (Goal25A-only)',
                                 'pending_small_fixes (none at the Goal25B start; the three small fixes of 17c8062f were packaged in goal25a)',
                                 'goal24_closeout (Goal25A-only; the commit is recorded in start_content.goal24_closeout_commit)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. No in-game client test was run: '
                            'the channel screen, the lid rendering, the JEI irradiation category and the crafting GUI and the Chinese UI are unverified; no survival chain (reactor to channel to '
                            'tritium or gold-198 and on) in a world was run; no multiplayer or dedicated server beyond GameTest; GOAL25B-ACCEPTANCE.md (the 25B real-game checklist) is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal25b JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal25a package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
