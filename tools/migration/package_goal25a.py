"""Package Goal25A (the first batch of Goal 25, RBMK operation and fuel logistics: the Goal 24 close-out remainders (b) the config key enableMachineGravity without the trailing space,
(d) chem.batteryquantum with cold perfluoromethyl, (e) the CompoundTagControl guard for unloaded or far positions, (f) the RBMKColumnType comment, (g) 15 English keys and 16 Chinese
entries, (h) the small-pile thermal balance GameTest; the storage column rbmk_storage (RBMKStorageBlock, RBMKStorageBlockEntity with 12 rod slots compacted every 10 ticks and the
IRBMKLoadable tail-in / head-out, RBMKStorageMenu, RBMKStorageScreen, the lid BER) with its C/R/C recipe; RBMK rods in the spent fuel pool drum (cooled every tick, extraction gate at
50 degrees) with 31 JEI display rows; the cold rod disassembly CustomRecipe hbmsntm:rbmk_rod_disassembly with NEO's first recipe serializer NtmRecipeSerializers and its JEI category;
seven imported resources; RBMKRecyclingGameTests and the 25A acceptance checklist GOAL25A-ACCEPTANCE.md) cumulatively on the goal24e package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal25a.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal25a/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal25a/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal25a/baseline.json: NEO HEAD 783b6d13 (the Goal 25 planning commit, local, on top of the pushed Goal 24 close-out commit 17c8062f) with a CLEAN
worktree; the start hashes are the committed tree. The original HEAD aee05a40f did not move since 24A, so there is no upstream classification and no new snapshot. build/libs at the
start is NOT the goal24e package: it is the D1b small-fix build, whose JAR entries differ from the goal24e package in exactly the five class entries of the three small fixes committed
in 17c8062f (baseline pending_small_fixes, jar-delta-start.json); the goal25a JAR delta against the goal24e package therefore also carries those five entries, owned by
small-fixes-17c8062f (their sources are unchanged since the start). Every change since the start is computed from the baseline file hashes (not from git diff) and must be in the owner
table below; every other path must still equal its start hash. The modified production files are compared with their start bytes (baseline-files holds 34 scope copies; ClientProxy.java
and RBMKConsoleGameTests.java come from the start-commit blob, in the CRLF form of the working tree where the baseline hash says so). The JAR delta against the goal24e package is
attributed per entry (goal25a or small-fixes-17c8062f); any entry without exactly one owner fails. Counts that records quote (suites, GameTests, generated resources, classes,
releases, language keys) are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal24d, the review-g21d-hazard-fix receipt) already differ from their older hashes at the frozen start for the acceptance checklists,
GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes build/migration/goal24a/main-notes.md (baseline older_receipt_evidence_drift); the goal24e receipt
differs at the start in migration/GOAL24E-ACCEPTANCE.md only (baseline previous_receipt_evidence_drift: the acceptance session appended its results after the package was written). They
are listed in the receipt as start drift and must still equal their Goal25A start hash; no receipt is rewritten and no other protected path may drift.

A concurrent session (local_52dd115d, the user-relayed decision of 2026-10-20 to drop the redundant review) edited the Goal 25 planning documents after the freeze: migration/GOAL25B.md,
GOAL25C.md, GOAL25D.md and GOAL25-THREAD-PROMPTS.md must equal the hashes in build/migration/goal25a/concurrent-session.json; migration/GOAL25.md is also edited by the 25A main agent
(progress), so it is a shared record (changed, not hashed) with both owners recorded.

Like the Goal24E packager this one has a single compare run (build/migration/goal25a/compare.json against the snapshot review-aee05a40f10f.json taken at the end of 24A: original
0/0/0, target = exactly the goal24e compare target paths (24A-24E, read from build/migration/goal24e/compare.json) plus this batch's compare-inventory paths plus the three small-fix
sources, which changed since that snapshot), no upstream classification; it adds the rbmk_recycling constants (checked against the original and NEO source texts). The Goal24E-only
receipt key rbmk_console is dropped."""
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
from package_goal22b import (git_ro, edit_counts, stale_diff, receipt_protected, start_drift_paths,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE
from package_goal23b import report_problems
from package_goal24a import original_text, original_line, original_blob, lang_file, provider_keys as base_provider_keys, SOURCE_HEAD
from package_goal24c import captured, normalize_value
from package_goal24e import (OUT as GOAL24E_OUT, BASELINE as GOAL24E_BASELINE, protected_paths as goal24e_protected_paths, split_args, OneOf, jsonable,
                             enum_offsets, COLUMN_TYPES)

OUT = ROOT/'build/migration/goal25a'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
JAR_DELTA_START = OUT/'jar-delta-start.json'
CONCURRENT = OUT/'concurrent-session.json'
REFERENCE_PREVIOUS = GOAL24E_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL24E_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal24e/hbmsntm-198A-goal24e.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal25a'
RELEASE_NAME = 'hbmsntm-198A-goal25a.jar'
OWNER = 'goal25a'
SMALL_OWNER = 'small-fixes-17c8062f'
CONCURRENT_OWNER = 'session-local_52dd115d'
PLANNING_PREFIX = '783b6d13'
GOAL24_CLOSEOUT = '17c8062f'
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
CONFIG = J+'config/CommonConfig.java'

# The three small fixes committed in 17c8062f (D1 NtmGeometry, D2 RenderRBMKPiped, D1b RBMKElementBakedModel): in build/libs at the start, in no goal package.
SMALL_FIX_SOURCES = [J+'render/blockentity/RenderRBMKPiped.java', J+'render/model/RBMKElementBakedModel.java', J+'render/model/loader/NtmGeometry.java']
SMALL_FIX_ENTRIES = ['com/hbm/render/blockentity/RenderRBMKPiped.class', 'com/hbm/render/model/RBMKElementBakedModel$1.class', 'com/hbm/render/model/RBMKElementBakedModel$RodBaker.class',
                     'com/hbm/render/model/RBMKElementBakedModel.class', 'com/hbm/render/model/loader/NtmGeometry.class']

# Production (owner goal25a), NEW (handoff-packaging.md; builder-report.md names the final classes: if the builder names a class differently or adds a helper class, edit this
# list, --check reports the difference as an unassigned src/ path).
NEW_JAVA = [J+p+'.java' for p in (
    'blocks/machine/rbmk/RBMKStorageBlock', 'blockentity/machine/rbmk/RBMKStorageBlockEntity', 'inventory/menus/RBMKStorageMenu', 'inventory/screens/RBMKStorageScreen',
    'registry/NtmRecipeSerializers', 'inventory/recipes/crafting/RBMKRodDisassemblyRecipe', 'handler/jei/RBMKRodDisassemblyRecipeHandler', 'gametest/RBMKRecyclingGameTests')]
(STORAGE_BLOCK, STORAGE_BE, STORAGE_MENU, STORAGE_SCREEN, SERIALIZERS, DISASSEMBLY_RECIPE, DISASSEMBLY_JEI, RECYCLING_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blockentity/NtmBlockEntityTypes', 'blockentity/machine/MachineWasteDrumBlockEntity', 'blockentity/machine/rbmk/RBMKColumnType', 'blocks/NtmBlocks', 'config/CommonConfig',
    'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockStateProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmLanguageProvider', 'datagen/NtmRecipeProvider',
    'handler/jei/FuelPoolRecipeHandler', 'handler/jei/NtmJeiPlugin', 'inventory/NtmCreativeTabs', 'inventory/NtmMenuTypes', 'inventory/recipes/ChemicalPlantRecipes',
    'main/ClientProxy', 'main/NuclearTechMod', 'main/NuclearTechModClient', 'network/toserver/CompoundTagControl', 'gametest/RBMKConsoleGameTests')]
(BLOCK_ENTITY_TYPES, DRUM, COLUMN_TYPE_FILE, BLOCKS, COMMON_CONFIG, LOOT_PROVIDER, BLOCK_STATE_PROVIDER, TAG_PROVIDER, PROVIDER, RECIPE_PROVIDER, FUEL_POOL_JEI, JEI_PLUGIN,
 CREATIVE_TABS, MENU_TYPES, CHEM_RECIPES, CLIENT_PROXY, MOD, CLIENT, CONTROL_PACKET, CONSOLE_TESTS) = MODIFIED_JAVA
OPTIONAL_JAVA = []
# The comment-only edits (RBMKColumnType class comment (f); RBMKConsoleGameTests: two line references to CompoundTagControl, review fix): the diff against the start bytes may add or
# remove comment lines and blank lines only, and the compiled class may or may not differ (a longer comment shifts the line number table).
COMMENT_ONLY_JAVA = [COLUMN_TYPE_FILE, CONSOLE_TESTS]
SAME_CLASS_JAVA = list(COMMENT_ONLY_JAVA)
NO_CLASS_JAVA = []
ANVIL_RECIPES = J+'inventory/recipes/anvil/AnvilRecipes.java'
# Registration and datagen files that must stay insert-only against their start bytes (the language provider and the Chinese file only gain lines too).
STRICT_INSERT_ONLY = [BLOCK_ENTITY_TYPES, BLOCKS, LOOT_PROVIDER, TAG_PROVIDER, PROVIDER, JEI_PLUGIN, CREATIVE_TABS, MENU_TYPES, CLIENT_PROXY, MOD, CLIENT, ZH_INPUT]
# For the non-strict files every removed start line (compared stripped, so re-indentation does not count) must be a comment line or start with one of these stripped code prefixes;
# the removed comments are listed in the receipt.
ALLOWED_REMOVED_CODE = {
    BLOCK_STATE_PROVIDER: ('NtmBlocks.RBMK_BOILER, NtmBlocks.RBMK_HEATER, NtmBlocks.RBMK_COOLER}) {',),
    RECIPE_PROVIDER: (),
    DRUM: ('if(changed) this.setChanged();', 'return !stack.isEmpty() && this.isKey(stack);', '@Override public boolean canTakeItemThroughFace('),
    FUEL_POOL_JEI: ('builder.addInputSlot(48, 24).setStandardSlotBackground().addItemStack(recipe.input());',
                    'builder.addOutputSlot(102, 24).setStandardSlotBackground().addItemStack(recipe.output());'),
    COMMON_CONFIG: ('.translation("hbmsntm.configuration.enableMachineGravity ")', '.define("enableMachineGravity ", false);'),
    CHEM_RECIPES: ('.inputFluids(new FluidStack(Fluids.PERFLUOROMETHYL, 8000))',),
    CONTROL_PACKET: ('context.enqueueWork(', 'Player player = context.player();', 'BlockEntity be = player.level.getBlockEntity(packet.pos);', 'icr.receiveControl(player, packet.tag);',
                     'icr.receiveControl(packet.tag);', '});'),
}
# The 7 imported original resources: NEO target -> original path, derived by the layout rules of the ownership record (textures/blocks -> textures/block; the GUI texture keeps its path).
ASSETS = {ASSETS_ROOT+'textures/block/rbmk/rbmk_storage_'+n+'.png': O_RES+'textures/blocks/rbmk/rbmk_storage_'+n+'.png' for n in ('side', 'top', 'cover_top', 'cover_side', 'glass_top', 'glass_side')}
ASSETS[ASSETS_ROOT+'textures/gui/reactors/gui_rbmk_storage.png'] = O_RES+'textures/gui/reactors/gui_rbmk_storage.png'
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
TAG_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
GENERATED = [STAMP, EN, GENERATED_ROOT+TAG_ENTRY]
# Generated by runData for this batch (relative to src/generated/resources): the blockstate, block and item model, loot table of the storage column, the two recipes (the shaped C/R/C
# row and the special rod disassembly recipe, which has no advancement) and the storage recipe's advancement. The advancement folder depends on the recipe category, so it is matched by name.
EXPECTED_GENERATED_BASE = sorted(['assets/hbmsntm/blockstates/rbmk_storage.json', 'assets/hbmsntm/models/block/rbmk_storage.json', 'assets/hbmsntm/models/item/rbmk_storage.json',
                                  'data/hbmsntm/loot_table/blocks/rbmk_storage.json', 'data/hbmsntm/recipe/rbmk_rod_disassembly.json', 'data/hbmsntm/recipe/rbmk_storage.json'])
ADVANCEMENT = re.compile(r'data/hbmsntm/advancement/recipes/[a-z_]+/rbmk_storage\.json')
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, TAG_ENTRY])
G_STORAGE_RECIPE = GENERATED_ROOT+'data/hbmsntm/recipe/rbmk_storage.json'
G_DISASSEMBLY_RECIPE = GENERATED_ROOT+'data/hbmsntm/recipe/rbmk_rod_disassembly.json'
NEW_TOOLS = ['tools/migration/verify_goal25a_rbmk_recycling.py', 'tools/migration/goal25a_pile_model.py', 'tools/migration/package_goal25a.py']
TOOLS = NEW_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal25a-* or GOAL25A-* record is hashed as well.
REPORTS = ['migration/GOAL25A.md', 'migration/GOAL25A-ACCEPTANCE.md', 'migration/goal25a-static-review.md', 'migration/goal25a-localization-review.json',
           'migration/goal25a-resource-ownership.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal25a-[^/]+\.(json|md)|GOAL25A-[^/]+\.md)')
GOAL25_RECORD = 'migration/GOAL25.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md', GOAL25_RECORD]
# Edited by the concurrent session after the freeze: their hashes come from concurrent-session.json (GOAL25.md is a shared record, see the docstring).
CONCURRENT_RECORDS = ['migration/GOAL25B.md', 'migration/GOAL25C.md', 'migration/GOAL25D.md', 'migration/GOAL25-THREAD-PROMPTS.md']
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED_BASE + the advancement.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + SHARED_RECORDS
# The new language keys: NEO key -> (original key or None, expected map kind). The block and container names are LOCAL rewrites of original keys (GOAL25 decision 16; the original source
# key, English and Chinese stay recorded in the map entry); the 11 key binding names and the mutation effect are upstream under the original keys (hbm.key.* singular; NEO calc / gunTertiary
# are the original calculator / gunTertitary); the JEI title is a NEO-local key (the original NEI title is hard-coded English).
SOURCE_KEYS = {'block.hbmsntm.rbmk_storage': ('tile.rbmk_storage.name', 'local'), 'container.rbmkStorage': ('container.rbmkStorage', 'local'),
               'jei.hbmsntm.rbmk_rod_disassembly': (None, 'local'), 'effect.hbmsntm.mutation': ('potion.hbm_mutation', 'upstream'), 'hbmsntm.keys': ('hbm.key', 'upstream'),
               'hbmsntm.keys.calc': ('hbm.key.calculator', 'upstream'), 'hbmsntm.keys.gunTertiary': ('hbm.key.gunTertitary', 'upstream')}
SOURCE_KEYS.update({'hbmsntm.keys.'+t: ('hbm.key.'+t, 'upstream') for t in ('toggleBack', 'toggleMagnet', 'toggleHUD', 'ability', 'abilityAlt', 'reload', 'gunPrimary', 'gunSecondary')})
KEYS = {k: v[0] for k, v in SOURCE_KEYS.items()}
EXPECTED_KINDS = {'upstream': sum(1 for v in SOURCE_KEYS.values() if v[1] == 'upstream'), 'local': sum(1 for v in SOURCE_KEYS.values() if v[1] == 'local')}
# item.hbmsntm.shell_copper existed in English since 24D and in the mapping as a deferred entry; 25A adds its Chinese ("铜壳", the original item.shellntm.name "%s壳" with hbmmat.copper) and
# moves the entry from deferred to local. zh +16 = the 15 keys + this one; the mapping gains 15 entries and changes this one.
SHELL = 'item.hbmsntm.shell_copper'
SHELL_ZH = '铜壳'
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rbmk-recycling] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'jar-delta-start.json', 'concurrent-session.json', 'main-notes.md', 'builder-report.md',
                  'handoff-production.md', 'handoff-pile.md', 'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md', 'make_production_diff.py', 'chain.sh',
                  'pile/notes.md', 'pile/model-run.json')
# Review files under OUT (for example the static review's notes or diffs) the main agent names when it knows them; each must exist and is indexed by the receipt. Extend this list from the
# real run (review notes, the builder's and verifiers' progress and scope files, logs ...); --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'packaging-progress.md', 'verifier-pkg/scope-before.txt',
                   'verifier-pkg/scope-after.txt')
GAMETEST_LOG = 'build/migration/goal25a/gametest-final.log'
NEW_SUITE = 'verify_goal25a_rbmk_recycling.py --gametest-log build/migration/goal25a/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_STORAGE, FEATURE_RECYCLING = 'rbmk-storage', 'rbmk-recycling'
NEW_FEATURES = (FEATURE_STORAGE, FEATURE_RECYCLING)
# The groups the snapshot of the end of 24A predates (24B rbmk-fuel, 24C rbmk-reactor, 24D rbmk-control and rbmk-steam, 24E rbmk-console).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console'}
RADIATION_NOTE = ('Goal25A: hot and spent RBMK rods keep their radiation in the spent fuel pool and the storage column; the disassembled pellets are radioactive as well; the acceptance '
                  'checklist GOAL25A-ACCEPTANCE.md must be run only in a separately authorized disposable world. ')
MELTDOWN_NOTE = ('Goal25A: the storage column melts down like the other columns (base onMelt) and drops its rods; meltdown tests only in disposable worlds away from builds. ')
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_STORAGE_TE = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKStorage.java'
O_STORAGE_BLOCK = ORIGINAL+'blocks/machine/rbmk/RBMKStorage.java'
O_STORAGE_CONTAINER = ORIGINAL+'inventory/container/ContainerRBMKStorage.java'
O_STORAGE_GUI = ORIGINAL+'inventory/gui/GUIRBMKStorage.java'
O_DRUM = ORIGINAL+'tileentity/machine/TileEntityWasteDrum.java'
O_FUEL_POOL = ORIGINAL+'inventory/recipes/FuelPoolRecipes.java'
O_CRAFTING_HANDLER = ORIGINAL+'crafting/handlers/RBMKFuelCraftingHandler.java'
O_NEI_DISASSEMBLY = ORIGINAL+'handler/nei/RBMKRodDisassemblyHandler.java'
O_NEI_FUEL_POOL = ORIGINAL+'handler/nei/FuelPoolHandler.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_ANVIL = ORIGINAL+'inventory/recipes/anvil/AnvilRecipes.java'
O_CHEM = ORIGINAL+'inventory/recipes/ChemicalPlantRecipes.java'
O_ROD = ORIGINAL+'items/machine/ItemRBMKRod.java'
O_MOD_ITEMS = ORIGINAL+'items/ModItems.java'
O_CONSOLE = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKConsole.java'
O_SOURCES = [O_STORAGE_TE, O_STORAGE_BLOCK, O_STORAGE_CONTAINER, O_STORAGE_GUI, O_DRUM, O_FUEL_POOL, O_CRAFTING_HANDLER, O_NEI_DISASSEMBLY, O_NEI_FUEL_POOL, O_CRAFTING, O_ANVIL, O_CHEM, O_ROD,
             O_MOD_ITEMS, O_CONSOLE]
# The original sources each new mapping group must list (source_paths or source_watch; plus the imported resources for the storage group).
FEATURE_SOURCES = {FEATURE_STORAGE: [O_STORAGE_TE, O_STORAGE_BLOCK, O_STORAGE_CONTAINER, O_STORAGE_GUI, O_CRAFTING] + list(ASSETS.values()),
                   FEATURE_RECYCLING: [O_DRUM, O_FUEL_POOL, O_CRAFTING_HANDLER, O_NEI_DISASSEMBLY, O_NEI_FUEL_POOL, O_CRAFTING]}
# The NEO paths each new mapping group must cover (target_paths or target_watch).
FEATURE_TARGETS = {FEATURE_STORAGE: [STORAGE_BLOCK, STORAGE_BE, STORAGE_MENU, STORAGE_SCREEN] + list(ASSETS) + [G_STORAGE_RECIPE],
                   FEATURE_RECYCLING: [SERIALIZERS, DISASSEMBLY_RECIPE, DISASSEMBLY_JEI, DRUM, RECYCLING_TESTS, G_DISASSEMBLY_RECIPE, NEW_TOOLS[0]]}
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'storage_update': (O_STORAGE_TE, 'public void updateEntity()'), 'storage_compaction_loop': (O_STORAGE_TE, 'for(int i = 0; i < slots.length - 1; i++)'),
    'storage_valid_for_slot': (O_STORAGE_TE, 'public boolean isItemValidForSlot('), 'storage_can_extract': (O_STORAGE_TE, 'public boolean canExtractItem('),
    'storage_accessible_slots': (O_STORAGE_TE, 'public int[] getAccessibleSlotsFromSide('), 'storage_can_load': (O_STORAGE_TE, 'public boolean canLoad('),
    'storage_load': (O_STORAGE_TE, 'public void load('), 'storage_can_unload': (O_STORAGE_TE, 'public boolean canUnload()'), 'storage_provide_next': (O_STORAGE_TE, 'public ItemStack provideNext()'),
    'storage_unload': (O_STORAGE_TE, 'public void unload()'), 'storage_console_type': (O_STORAGE_TE, 'ColumnType.STORAGE'),
    'storage_block_proxy': (O_STORAGE_BLOCK, 'TileEntityProxyCombo'), 'storage_container': (O_STORAGE_CONTAINER, 'public ItemStack transferStackInSlot('),
    'storage_gui': (O_STORAGE_GUI, 'this.ySize = 186;'),
    'drum_valid_for_slot': (O_DRUM, 'public boolean isItemValidForSlot('), 'drum_can_extract': (O_DRUM, 'public boolean canExtractItem('), 'drum_update': (O_DRUM, 'public void updateEntity()'),
    'drum_decay_ticks': (O_DRUM, 'int r = 60 * 60 * 20 / water;'), 'drum_rod_update_heat': (O_DRUM, 'rod.updateHeat('), 'drum_rod_provide_heat': (O_DRUM, 'rod.provideHeat('),
    'fuel_pool_rod_rows': (O_FUEL_POOL, 'ItemRBMKRod.craftableRods'), 'nei_rod_rows': (O_NEI_DISASSEMBLY, 'public static HashMap<ComparableStack, ItemStack> getRecipes()'),
    'nei_to_stack': (O_NEI_DISASSEMBLY, 'public ItemStack toStack()'), 'nei_usage_hiding': (O_NEI_DISASSEMBLY, 'public void loadUsageRecipes('),
    'disassembly_matches': (O_CRAFTING_HANDLER, 'public boolean matches('), 'disassembly_result': (O_CRAFTING_HANDLER, 'public ItemStack getCraftingResult('),
    'disassembly_register': (O_CRAFTING, 'GameRegistry.addRecipe(new RBMKFuelCraftingHandler());'), 'rod_enrichment': (O_ROD, 'public static double getEnrichment('),
    'rod_poison_level': (O_ROD, 'public static double getPoisonLevel('), 'rod_craftable_list': (O_ROD, 'public static List<ItemRBMKRod> craftableRods'),
    'recipe_rbmk_storage': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_storage, 1)'), 'anvil_rbmk_storage': (O_ANVIL, 'ModBlocks.rbmk_storage'),
    'chem_batteryquantum': (O_CHEM, '"chem.batteryquantum"'),
}
# Constants compared between the original and NEO source texts: id -> (original path, regex, NEO path, regex, expected unique values in order[, expected NEO values when they differ]).
# Numbers are compared as floats (underscores dropped, F / D suffixes dropped), anything else as text. The group-1 value of every match is collected. A NEO regex that finds
# nothing (the class is not written yet, or its text differs from the handoff) is reported as pending with its id.
DRUM_PROVIDE = r'provideHeat\([^;]*?'
CHEM_BATTERY = r'"chem\.batteryquantum"\)'
CONSTANTS = {
    # Storage column (TileEntityRBMKStorage): 12 slots, one forward compaction pass every 10 world ticks, autoloader in at slot 11 / out at slot 0.
    'storage_slots': (O_STORAGE_TE, r'super\((\d+)\);', STORAGE_BE, r'RBMK_STORAGE\.get\(\), pos, state, (\d+)\)', [12]),
    'storage_compaction_period': (O_STORAGE_TE, r'getTotalWorldTime\(\) % (\d+) == 0', STORAGE_BE, r'getGameTime\(\) % (\d+) == 0', [10]),
    'storage_accessible_slots': (O_STORAGE_TE, r'return new int\[\] \{([\d, ]+)\};', STORAGE_BE, r'SLOTS = new int\[\] \{([\d, ]+)\};', ['0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11']),
    'storage_load_slot': (O_STORAGE_TE, r'slots\[(\d+)\] = toLoad\.copy\(\)', STORAGE_BE, r'slots\.set\((\d+), toLoad\.copy\(\)\)', [11]),
    'storage_can_load_slot': (O_STORAGE_TE, r'return slots\[(\d+)\] == null;', STORAGE_BE, r'slots\.get\((\d+)\)\.isEmpty\(\) && toLoad', [11]),
    'storage_can_unload_slot': (O_STORAGE_TE, r'return slots\[(\d+)\] != null;', STORAGE_BE, r'return !this\.slots\.get\((\d+)\)\.isEmpty\(\);', [0]),
    'storage_provide_slot': (O_STORAGE_TE, r'return slots\[(\d+)\];', STORAGE_BE, r'return this\.slots\.get\((\d+)\);', [0]),
    'storage_unload_slot': (O_STORAGE_TE, r'slots\[(\d+)\] = null;', STORAGE_BE, r'slots\.set\((\d+), ItemStack\.EMPTY\);', [0]),
    # Spent fuel pool drum (TileEntityWasteDrum): 60 * 60 * 20 = 72000 ticks per adjacent water, a rod is cooled by updateHeat 0.025 then provideHeat(reference 20, 0.025) and never rolls,
    # extraction by automation only below 50 in core and hull.
    'drum_decay_ticks': (O_DRUM, r'int r = ([\d* ]+) / water;', DRUM, r'DECAY_TICKS = (\d+);', ['60 * 60 * 20'], [72000]),
    'drum_rod_update_heat': (O_DRUM, r'rod\.updateHeat\(worldObj, slots\[i\], ([\d.]+)D\)', DRUM, r'rod\.updateHeat\(this\.level, stack, ([\d.]+)D\)', [0.025]),
    'drum_rod_provide_reference': (O_DRUM, r'rod\.provideHeat\(worldObj, slots\[i\], ([\d.]+)D, [\d.]+D\)', DRUM, r'rod\.provideHeat\(this\.level, stack, ([\d.]+)D, [\d.]+D\)', [20]),
    'drum_rod_provide_modifier': (O_DRUM, r'rod\.provideHeat\(worldObj, slots\[i\], [\d.]+D, ([\d.]+)D\)', DRUM, r'rod\.provideHeat\(this\.level, stack, [\d.]+D, ([\d.]+)D\)', [0.025]),
    'drum_extract_core': (O_DRUM, r'getCoreHeat\(itemStack\) < (\d+)', DRUM, r'getCoreHeat\(stack\) < (\d+)', [50]),
    'drum_extract_hull': (O_DRUM, r'getHullHeat\(itemStack\) < (\d+)', DRUM, r'getHullHeat\(stack\) < (\d+)', [50]),
    # Cold rod disassembly (RBMKFuelCraftingHandler): core and hull below 50, enrichment above 0.99 gives nothing, 8 pellets, META = 4 - clamp(ceil(enrichment * 5 - 1), 0, 4) + (xenon >= 0.5 ? 5 : 0).
    'disassembly_hull_limit': (O_CRAFTING_HANDLER, r'getHullHeat\(stack\) < (\d+) && ItemRBMKRod\.getCoreHeat\(stack\) < \d+', DISASSEMBLY_RECIPE,
                               r'getHullHeat\(stack\) < (\d+) && RBMKRodItem\.getCoreHeat\(stack\) < \d+', [50]),
    'disassembly_core_limit': (O_CRAFTING_HANDLER, r'getHullHeat\(stack\) < \d+ && ItemRBMKRod\.getCoreHeat\(stack\) < (\d+)', DISASSEMBLY_RECIPE,
                               r'getHullHeat\(stack\) < \d+ && RBMKRodItem\.getCoreHeat\(stack\) < (\d+)', [50]),
    'disassembly_enrichment_cutoff': (O_CRAFTING_HANDLER, r'getEnrichment\(stack\) > ([\d.]+)D', DISASSEMBLY_RECIPE, r'getEnrichment\(stack\) > ([\d.]+)D', [0.99]),
    'disassembly_pellets': (O_CRAFTING_HANDLER, r'new ItemStack\(rod\.pellet, (\d+)\)', DISASSEMBLY_RECIPE, r'MetaHelper\.newStack\(rod\.pellet, (\d+), meta\)', [8]),
    'disassembly_meta_base': (O_CRAFTING_HANDLER, r'int enrichment = (\d+) - MathHelper', DISASSEMBLY_RECIPE, r'int enrichment = (\d+) - Mth', [4]),
    'disassembly_meta_scale': (O_CRAFTING_HANDLER, r'getEnrichment\(stack\) \* (\d+) - \d+\)', DISASSEMBLY_RECIPE, r'getEnrichment\(stack\) \* (\d+) - \d+\)', [5]),
    'disassembly_meta_offset': (O_CRAFTING_HANDLER, r'getEnrichment\(stack\) \* \d+ - (\d+)\)', DISASSEMBLY_RECIPE, r'getEnrichment\(stack\) \* \d+ - (\d+)\)', [1]),
    'disassembly_meta_clamp_low': (O_CRAFTING_HANDLER, r'getEnrichment\(stack\) \* \d+ - \d+\), (\d+), \d+\)', DISASSEMBLY_RECIPE, r'getEnrichment\(stack\) \* \d+ - \d+\), (\d+), \d+\)', [0]),
    'disassembly_meta_clamp_high': (O_CRAFTING_HANDLER, r'getEnrichment\(stack\) \* \d+ - \d+\), \d+, (\d+)\)', DISASSEMBLY_RECIPE, r'getEnrichment\(stack\) \* \d+ - \d+\), \d+, (\d+)\)', [4]),
    'disassembly_xenon_threshold': (O_CRAFTING_HANDLER, r'getPoisonLevel\(stack\) >= ([\d.]+)D', DISASSEMBLY_RECIPE, r'getPoisonLevel\(stack\) >= ([\d.]+)D', [0.5]),
    'disassembly_xenon_offset': (O_CRAFTING_HANDLER, r'getPoisonLevel\(stack\) >= [\d.]+D \? (\d+) : 0', DISASSEMBLY_RECIPE, r'getPoisonLevel\(stack\) >= [\d.]+D \? (\d+) : 0', [5]),
    # JEI rows: the fuel pool rows are the hot rod (yield 0.2 x, core 100, hull 50) -> the rod at yield 0.2 x; the disassembly rows are 5 grades per rod (yield min(1 - e / 5, 0.99) x) plus
    # the xenon-50 rows at META e + 5 for pellets with xenon.
    'fuel_pool_yield': (O_FUEL_POOL, r'setYield\(result, ([\d.]+) \* rod\.yield\)', FUEL_POOL_JEI, r'setYield\((?:hot|cooled), ([\d.]+) \* rod\.yield\)', [0.2]),
    'jei_default_yield': (O_NEI_DISASSEMBLY, r'setYield\(stack, ([\d.]+) \* rod\.yield\)', FUEL_POOL_JEI, r'setYield\((?:hot|cooled), ([\d.]+) \* rod\.yield\)', [0.2]),
    'jei_hot_core': (O_NEI_DISASSEMBLY, r'setCoreHeat\(stack, (\d+)\)', FUEL_POOL_JEI, r'setCoreHeat\(hot, (\d+)\)', [100]),
    'jei_hot_hull': (O_NEI_DISASSEMBLY, r'setHullHeat\(stack, (\d+)\)', FUEL_POOL_JEI, r'setHullHeat\(hot, (\d+)\)', [50]),
    'jei_grades': (O_NEI_DISASSEMBLY, r'enrichment <= (\d+)', DISASSEMBLY_JEI, r'enrichment <= (\d+)', [4]),
    'jei_grade_divisor': (O_NEI_DISASSEMBLY, r'Math\.min\(1 - \(\(double\) enrichment\) / (\d+), [\d.]+\)', DISASSEMBLY_JEI, r'Math\.min\(1 - \(\(double\) enrichment\) / (\d+), [\d.]+\)', [5]),
    'jei_grade_cap': (O_NEI_DISASSEMBLY, r'Math\.min\(1 - \(\(double\) enrichment\) / \d+, ([\d.]+)\)', DISASSEMBLY_JEI, r'Math\.min\(1 - \(\(double\) enrichment\) / \d+, ([\d.]+)\)', [0.99]),
    'jei_xenon_level': (O_NEI_DISASSEMBLY, r'setPoison\(stack, (\d+)\)', DISASSEMBLY_JEI, r'setPoison\(stack, (\d+)\)', [50]),
    'jei_xenon_meta_offset': (O_NEI_DISASSEMBLY, r'enrichment \+ (\d+)\)', DISASSEMBLY_JEI, r'enrichment \+ (\d+)\)', [5]),
    # (d) chem.batteryquantum: cold perfluoromethyl 8,000 mB in, warm perfluoromethyl 8,000 mB out.
    'chem_battery_input_fluid': (O_CHEM, CHEM_BATTERY+r'.*?inputFluids\(new FluidStack\(Fluids\.(\w+), [\d_]+\)\)', CHEM_RECIPES, CHEM_BATTERY+r'\.setupNamed.*?inputFluids\(new FluidStack\(Fluids\.(\w+), \d+\)\)',
                                 ['PERFLUOROMETHYL_COLD']),
    'chem_battery_input_amount': (O_CHEM, CHEM_BATTERY+r'.*?inputFluids\(new FluidStack\(Fluids\.\w+, ([\d_]+)\)\)', CHEM_RECIPES, CHEM_BATTERY+r'\.setupNamed.*?inputFluids\(new FluidStack\(Fluids\.\w+, (\d+)\)\)', [8000]),
    'chem_battery_output_fluid': (O_CHEM, CHEM_BATTERY+r'.*?outputFluids\(new FluidStack\(Fluids\.(\w+), [\d_]+\)\)', CHEM_RECIPES, CHEM_BATTERY+r'\.setupNamed.*?outputFluids\(new FluidStack\(Fluids\.(\w+), \d+\)\)',
                                  ['PERFLUOROMETHYL']),
    'chem_battery_output_amount': (O_CHEM, CHEM_BATTERY+r'.*?outputFluids\(new FluidStack\(Fluids\.\w+, ([\d_]+)\)\)', CHEM_RECIPES, CHEM_BATTERY+r'\.setupNamed.*?outputFluids\(new FluidStack\(Fluids\.\w+, (\d+)\)\)', [8000]),
}
# NEO-only facts (no original counterpart): id -> (NEO path, regex, expected unique values). Recorded in the receipt; a regex that finds nothing is pending.
NEO_FACTS = {
    'config_key': (COMMON_CONFIG, r'\.define\("(enableMachineGravity ?)", false\)', ['enableMachineGravity']),
    'config_translation': (COMMON_CONFIG, r'\.translation\("hbmsntm\.configuration\.(enableMachineGravity ?)"\)', ['enableMachineGravity']),
    'control_max_distance': (CONTROL_PACKET, r'MAX_DISTANCE = ([\d.]+)D', [64]),
    # Level.isLoaded without its build-height test (getBlockEntity repeats it); the isolated machine regressions' stub Level has no isLoaded.
    'control_guard_loaded': (CONTROL_PACKET, r'if\(player\.level\(\)\.(hasChunk)\(pos\.getX\(\) >> 4, pos\.getZ\(\) >> 4\)', ['hasChunk']),
    'control_guard_distance': (CONTROL_PACKET, r'player\.(distanceToSqr)\(pos\.getX\(\) \+ 0\.5D, pos\.getY\(\) \+ 0\.5D, pos\.getZ\(\) \+ 0\.5D\) <= MAX_DISTANCE \* MAX_DISTANCE', ['distanceToSqr']),
    'serializer_id': (SERIALIZERS, r'RECIPE_SERIALIZERS\.register\("(\w+)"', ['rbmk_rod_disassembly']),
    'serializer_registry': (SERIALIZERS, r'DeferredRegister\.create\(Registries\.(RECIPE_SERIALIZER),', ['RECIPE_SERIALIZER']),
    'recipe_base_class': (DISASSEMBLY_RECIPE, r'class RBMKRodDisassemblyRecipe extends (\w+)', ['CustomRecipe']),
    'drum_place_rule': (DRUM, r'(this\.isKey\(stack\) \|\| stack\.getItem\(\) instanceof RBMKRodItem)', ['this.isKey(stack) || stack.getItem() instanceof RBMKRodItem']),
    'storage_place_rule': (STORAGE_BE, r'(stack\.getItem\(\) instanceof RBMKRodItem)', ['stack.getItem() instanceof RBMKRodItem']),
}
# Known source differences the batch deliberately leaves (recorded with the observed values; not asserted equal): the original chem.batteryquantum dense wire is BSCCO, NEO's is GOLD
# (an out-of-scope finding of the main agent, main-notes.md).
KNOWN_DIFFERENCES = {'chem_battery_dense_wire': (O_CHEM, CHEM_BATTERY+r'.*?OreDictStack\((\w+)\.wireDense\(\), 24\)', CHEM_RECIPES, CHEM_BATTERY+r'\.setupNamed.*?WIRE_DENSE\.get\(\), 24, WireDenseItem\.Type\.(\w+)\.meta')}
COLUMN_TYPES_STORAGE = ('STORAGE',)

# Original crafting-manager key expressions -> the NEO ingredient (the generated recipe is compared against the parsed original row).
KEY_TABLE = {'ModBlocks.crate_steel': {'item': 'hbmsntm:crate_steel'}, 'ModBlocks.rbmk_blank': {'item': 'hbmsntm:rbmk_blank'}}


def scope_text(key_count, shell_zh, kinds, assets, tests, total_tests, rods):
    return (f'Goal25A (the first batch of Goal 25: RBMK operation and fuel logistics): the storage column rbmk_storage (RBMKStorageBlock; RBMKStorageBlockEntity with 12 rod-only slots compacted '
            f'forward by one pass every 10 ticks, the IRBMKLoadable tail-in at slot 11 and head-out at slot 0, console type STORAGE, every non-core block an inventory-only proxy as the original '
            f'TileEntityProxyCombo; RBMKStorageMenu, RBMKStorageScreen and the lid renderer) with the shaped C/R/C recipe (steel crate, structural column; the tier-4 anvil recycling row is not '
            f'registered, the 4-tier anvil is unreachable); the spent fuel pool drum takes RBMK rods (with adjacent water each rod is cooled every tick by updateHeat 0.025 then provideHeat to '
            f'20 at 0.025 and never converts, automation takes it out only when core and hull are below 50 degrees, hand extraction is unchanged) with {rods} display-only JEI rows "hot rod -> '
            f'cooled rod (yield x0.2)"; the cold rod disassembly special recipe hbmsntm:rbmk_rod_disassembly (NtmRecipeSerializers, NEO\'s first recipe serializer, RBMKRodDisassemblyRecipe: one '
            f'cold rod gives 8 pellets with META by enrichment grade and xenon plus the empty rod) with a JEI category; the Goal 24 close-out remainders (b) config key enableMachineGravity '
            f'without the trailing space (an old file\'s spaced key is removed and the default false written), (d) chem.batteryquantum takes cold perfluoromethyl 8,000 mB and gives '
            f'perfluoromethyl 8,000 mB, (e) CompoundTagControl looks up the block entity only for a loaded position within 64 blocks, (f) the RBMKColumnType comment, (g) {key_count} English keys '
            f'({kinds.get("upstream", 0)} upstream, {kinds.get("local", 0)} NEO-local) and {key_count + 1} Chinese entries (key bindings, the mutation effect, the storage column, the JEI title, '
            f'{shell_zh} for the copper shell), (h) the small-pile thermal balance GameTest equals the original-formula model tick by tick (the original layout makes no steam); {assets} imported '
            f'resources (six storage column textures and the GUI), {tests} RBMKRecyclingGameTests ({total_tests} GameTests in total, one batch per test) and the 25A real-game acceptance '
            f'checklist GOAL25A-ACCEPTANCE.md (written, not executed). Gameplay impact: spent rods can be cooled in the pool and taken apart into pellets; a storage column holds 12 rods; the quantum '
            f'battery now consumes cold perfluoromethyl; an old config\'s machine-gravity setting is reset to false; control packets for unloaded or far positions are ignored.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal25a release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 34 scope copies) when it reproduces the baseline hash, otherwise the blob at the start commit (with CRLF
    where the working tree had it) when it reproduces the baseline hash; None when neither does."""
    if (START_FILES/p).is_file():
        data = (START_FILES/p).read_bytes()
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT)
    for data in (blob, blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def start_pin(base, p):
    """The Goal25A start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does not list it)
    the hash the goal24e receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal24e packager protected (built there from the Goal21A..Goal24D starts and receipts and the goal24e start), plus every path the goal24e receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 25A baseline lists the goal24d receipt among them) and every release file of the frozen
    start (the goal24e package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a main-notes.md and,
    from the goal24e receipt, GOAL24E-ACCEPTANCE.md) are pinned at their Goal25A start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal24e packager set at its Goal24E start hash, for the records that changed between the two starts."""
    goal24e_start = read(GOAL24E_BASELINE)
    out = dict(goal24e_protected_paths(goal24e_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal24e receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal24e_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift.
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal24E and Goal25A starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal24e_start):
    """{path: {receipts, start_sha256, goal24e_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal24e receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal24e receipt')
        if p in base['previous_receipt_evidence_drift']:
            explanation = ('Changed after the goal24e receipt hashed it: the Goal 24 acceptance session appended its results after the goal24e package was written, so the goal24e receipt hash is older '
                           'than the start hash. Frozen at the start hash; this batch must not change it and the goal24e receipt is not rewritten.')
        elif p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the goal24b..goal24e receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22, 23 and 24 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal24e '
                           'receipt does not hash it. Frozen at the Goal25A start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal24e) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal24e package; the goal24e receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal24e '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal24e_start_sha256=goal24e_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal24e_start_pin_sha256'] = repinned[p]
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
    if p in CONCURRENT_RECORDS: return 'concurrent-session'
    return None


def owners_of(p):
    """The owner id(s) of a changed path: the concurrent session for the planning documents it edited, both for GOAL25.md, goal25a otherwise."""
    if p in CONCURRENT_RECORDS: return [CONCURRENT_OWNER]
    if p == GOAL25_RECORD: return [OWNER, CONCURRENT_OWNER]
    return [OWNER]


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
    goal24e_start = read(GOAL24E_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal25A commits nothing), the recorded clean start on top of the Goal 24 close-out commit.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 25 planning commit'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 25 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    assert base['target_status'] == '', 'The frozen start worktree was not clean: '+base['target_status'][:200]
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal24e receipt records another original commit than the frozen start'
    fixes = base['pending_small_fixes']
    assert fixes['commit'].startswith(GOAL24_CLOSEOUT) and fixes['sources'] == SMALL_FIX_SOURCES and fixes['jar_entries'] == SMALL_FIX_ENTRIES == base['build_libs_vs_previous']['modified'] \
        and base['build_libs_vs_previous']['added'] == [] and base['build_libs_vs_previous']['removed'] == [], 'Baseline pending_small_fixes / build_libs_vs_previous are not the three small fixes of 17c8062f'
    committed = git_ro(ROOT, 'show', '--name-only', '--format=', fixes['commit']).split()
    assert all(s in committed for s in SMALL_FIX_SOURCES), 'The small-fix commit does not touch all three small-fix sources'
    assert all(sha(ROOT/s) == base['files'][s] for s in SMALL_FIX_SOURCES), 'A small-fix source changed since the start (its class entries would not be the start build/libs entries)'
    jar_start = read(JAR_DELTA_START)
    assert jar_start['live_sha256'] == base['build_libs_jar_sha256'] and jar_start['previous_sha256'] == base['previous_release']['sha256'] and jar_start['changed'] == SMALL_FIX_ENTRIES \
        and jar_start['added'] == [] and jar_start['removed'] == [], 'jar-delta-start.json differs from baseline.json'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and base['start_content']['uncommitted'].startswith('none'), 'Baseline start content differs'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal25A: '+head
    closeout = git_ro(ROOT, 'rev-parse', 'HEAD~1').strip()
    assert closeout.startswith(GOAL24_CLOSEOUT) and closeout == fixes['commit'], 'NEO HEAD~1 is not the Goal 24 close-out commit 17c8062f'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b',
                                                          'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b', 'goal24c', 'goal24d'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] and startup['target_head'] == start_head and startup['source_clean'] is True and startup['target_clean'] is True \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'] and startup['generated_resources_verified'] == base['stamp_state']['generated_resources_verified'] \
        and startup['build_libs_vs_previous'] == base['build_libs_vs_previous'], 'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_verified'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal24e generated tree'
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal24e package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha != previous_sha and base['build_libs_vs_previous']['modified'] == SMALL_FIX_ENTRIES, 'build/libs at the start is not the previous package + the five small-fix entries'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal24e receipt list + the goal24e package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal24e receipt count + the goal24e release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal24e receipt'
    # The goal24e receipt drifted at the start in the Goal 24 acceptance checklist only (the session appended its results after packaging).
    drift_prev = base['previous_receipt_evidence_drift']
    assert list(drift_prev) == ['migration/GOAL24E-ACCEPTANCE.md'] and drift_prev['migration/GOAL24E-ACCEPTANCE.md']['receipt'] == prior_receipt['report_sha256']['migration/GOAL24E-ACCEPTANCE.md'] \
        and drift_prev['migration/GOAL24E-ACCEPTANCE.md']['now'] == base['files']['migration/GOAL24E-ACCEPTANCE.md'], 'The goal24e receipt drift at the start is not GOAL24E-ACCEPTANCE.md alone'
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal24e_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal24e receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal25a (or the concurrent session). Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal25A start that the owner table does not list (production outside the 20 modified Java files, the 8 new classes incl. RBMKRecyclingGameTests, '
         'the 7 resources, zh_cn.json and the mapping, a protected record, an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal25A start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD, ANVIL_RECIPES] + GENERATED + SHARED_RECORDS + CONCURRENT_RECORDS + REPORTS[:1]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    need(sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES], f'{ANVIL_RECIPES} changed since the start (the tier-4 anvil recycling row of the storage column stays unregistered: the 4-tier anvil is unreachable)')
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION + OPTIONAL_JAVA if p.startswith('src/')})
    need(not outside, 'src/main change outside the 20 modified and 8 new Java files, the 7 resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    # The concurrent session's edits equal the hashes it reported; GOAL25.md is shared with the 25A progress edit.
    concurrent = read(CONCURRENT)
    assert set(concurrent['files']) == set(CONCURRENT_RECORDS) | {GOAL25_RECORD}, 'concurrent-session.json lists other records than the owner table'
    for p in CONCURRENT_RECORDS: need(sha(ROOT/p) == concurrent['files'][p], f'{p} differs from the hash the concurrent session reported in concurrent-session.json')
    goal25_now = sha(ROOT/GOAL25_RECORD)
    concurrent_record = dict(session=concurrent['session'], name=concurrent['name'], reason=concurrent['reason'], note=concurrent['note'],
                             files={p: dict(start_sha256=base['files'][p], reported_sha256=concurrent['files'][p], current_sha256=sha(ROOT/p),
                                            owners=owners_of(p)) for p in CONCURRENT_RECORDS + [GOAL25_RECORD]},
                             goal25_md_edited_after_session=goal25_now != concurrent['files'][GOAL25_RECORD])
    change_list = [dict(path=p, change=s, group=group(p), owner=owners_of(p)[0], owners=owners_of(p), before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal25A takes no new snapshot)'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-aee05a40f10f snapshot changed'
    production_changed = [p for p in PRODUCTION + OPTIONAL_JAVA if p in changes]

    # The modified production files keep their start line endings; new Java files are not mixed.
    start_text = {}
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]:
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

    # Production Java facts: insert-only registration files, every line edit counted, the removed lines of the edited files accounted for, the comment-only edits.
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
        elif p in COMMENT_ONLY_JAVA:
            code = [l.strip() for l in added_lines[p] + removed_lines[p] if not is_comment(l)]
            need(not code, f'{p} changes code lines although the owner table says comment-only: {code[:4]}')
            removed_comments[p] = [l.strip() for l in removed_lines[p] if is_comment(l) and l.strip()]
        elif p in ALLOWED_REMOVED_CODE:
            # Compared stripped: re-indented lines (CompoundTagControl's body) cancel out; what is left was really removed.
            net_removed = list((Counter(l.strip() for l in start_lines) - Counter(l.strip() for l in live_lines)).elements())
            comments = [l for l in net_removed if is_comment(l)]
            code = [l for l in net_removed if not is_comment(l)]
            stray = [l for l in code if not l.startswith(ALLOWED_REMOVED_CODE[p])]
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
    # NEO constants against the original (storage slots and compaction, drum cooling and gate, disassembly formula, JEI rows, chem.batteryquantum).
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
    known_differences = {kid: dict(original=captured(original_text(o_path), o_regex), neo=captured(neo_text(n_path), n_regex) if (ROOT/n_path).is_file() else None, original_path=o_path, neo_path=n_path)
                         for kid, (o_path, o_regex, n_path, n_regex) in KNOWN_DIFFERENCES.items()}
    # The storage column type offset equals the original ColumnType (TileEntityRBMKConsole), the same table the console uses.
    o_console_text = original_text(O_CONSOLE)
    column_types = dict(original=enum_offsets(o_console_text, COLUMN_TYPES), neo=enum_offsets(neo_text(COLUMN_TYPE_FILE), COLUMN_TYPES))
    assert list(column_types['original']) == list(COLUMN_TYPES), 'The original ColumnType members are not the owner table\'s'
    need(column_types['neo'] == column_types['original'], f'{COLUMN_TYPE_FILE} members / offsets differ from the original ColumnType (TileEntityRBMKConsole)')
    # The craftable rods: the original adds every rod made from a pellet to craftableRods (32 incl. rbmk_fuel_drx); NEO registers 31 (rbmk_fuel_drx is not migrated, GOAL24 decision 5).
    o_rods = re.findall(r'new ItemRBMKRod\((rbmk_pellet_\w+)\)', original_text(O_MOD_ITEMS))
    neo_rods = len(re.findall(r'new RBMKRodItem\(', neo_text(J+'items/NtmItems.java')))
    rods = dict(original_with_pellet=len(o_rods), original_excluded=[r for r in o_rods if r == 'rbmk_pellet_drx'], original_craftable_migrated=len([r for r in o_rods if r != 'rbmk_pellet_drx']),
                neo_craftable=neo_rods)
    need(rods['original_craftable_migrated'] == rods['neo_craftable'], f'NEO registers {neo_rods} rods, the original {rods["original_craftable_migrated"]} without rbmk_fuel_drx')
    # Logical sides: the block entity, block and menu (common code) import nothing from net.minecraft.client; the screen exists.
    client_imports = {p: (ROOT/p).is_file() and 'net.minecraft.client' in neo_text(p) for p in (STORAGE_BE, STORAGE_BLOCK, STORAGE_MENU, SERIALIZERS, DISASSEMBLY_RECIPE)}
    need(not any(client_imports.values()) and all((ROOT/p).is_file() for p in (STORAGE_BE, STORAGE_BLOCK, STORAGE_MENU, STORAGE_SCREEN, SERIALIZERS, DISASSEMBLY_RECIPE)),
         'common-side storage / recipe classes are missing or import net.minecraft.client: '+str(sorted(p for p, v in client_imports.items() if v)))
    need('IRBMKLoadable' in neo_text(STORAGE_BE) and 'extends RBMKSlottedBaseBlockEntity' in neo_text(STORAGE_BE), f'{STORAGE_BE} is not an RBMKSlottedBaseBlockEntity implementing IRBMKLoadable')
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
    # features.json: the two new groups, the unchanged status and reviewed_source_commit of the previous groups.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES <= set(start_features) and not set(NEW_FEATURES) & set(start_features), \
        'The start mapping does not hold rbmk-fuel (24B), rbmk-reactor (24C), rbmk-control and rbmk-steam (24D), rbmk-console (24E) and not yet the two Goal25A groups'
    new_groups = {g: by_id[g] for g in NEW_FEATURES if g in by_id}

    # 4. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_en = dict(added=sorted(KEYS), removed=[], changed=[])
    expected_zh = dict(added=sorted(set(KEYS) | {SHELL}), removed=[], changed=[])
    expected_map = dict(added=sorted(KEYS), removed=[], changed=[SHELL])
    need(en_delta == expected_en, f'generated en_us.json delta is not the {len(KEYS)} new keys (no value changed): '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_zh, f'zh_cn.json delta is not the {len(KEYS)} new keys + {SHELL} (all old values unchanged): '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_map, f'zh_cn-map.json delta is not the {len(KEYS)} new entries + {SHELL} changed from deferred to local: '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal24e totals'
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) + 1 and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal24e totals {totals} + {len(KEYS)} (zh + {len(KEYS) + 1})')
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
        # The copper shell: deferred -> local with the composed original name (item.shellntm.name "%s壳" + hbmmat.copper "铜").
        shell_old, shell_new = map_start.get(SHELL, {}), map_now.get(SHELL, {})
        if not (shell_old.get('kind') == 'deferred' and shell_new.get('kind') == 'local' and shell_new.get('reason') and shell_new.get('target_en') == en_now.get(SHELL) == shell_old.get('target_en')
                and shell_new.get('target_zh') == zh_now.get(SHELL) == SHELL_ZH and SHELL not in zh_start): bad.append(SHELL)
        need(not bad, 'zh_cn-map.json entries do not match en_us.json / zh_cn.json, the original en_US.lang / zh_CN.lang values at aee05a40f or the expected kinds: '+str(bad[:8]))
        original_text_checked = not bad
    map_kinds = dict(Counter(e.get('kind') for e in map_now.values()))
    start_kinds = dict(Counter(e.get('kind') for e in map_start.values()))
    expected_kinds_now = dict(start_kinds, upstream=start_kinds.get('upstream', 0) + EXPECTED_KINDS['upstream'], local=start_kinds.get('local', 0) + EXPECTED_KINDS['local'] + 1,
                              deferred=start_kinds.get('deferred', 0) - 1)
    need(map_kinds == expected_kinds_now, f'mapping kinds are {map_kinds}, expected {expected_kinds_now} (upstream +{EXPECTED_KINDS["upstream"]}, local +{EXPECTED_KINDS["local"] + 1} incl. {SHELL}, deferred -1)')
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    stamp_current = not stale and not mismatch and not unrecorded
    need(stamp_current, f'{STAMP} not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
    start_stamp = read(START_FILES/STAMP)
    start_generated = start_stamp['generated']
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal24e generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    advancements = sorted(p for p in generated_added if ADVANCEMENT.fullmatch(p))
    EXPECTED_GENERATED = sorted(EXPECTED_GENERATED_BASE + advancements)
    need(len(advancements) == 1, 'The generated advancements are not exactly one for rbmk_storage (the special rod disassembly recipe has none): '+str(advancements))
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected blockstate, model, loot table, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, the pickaxe tag and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # The pickaxe tag: the start list plus rbmk_storage, in the start order.
    tag_start_bytes = start_bytes(base, GENERATED_ROOT+TAG_ENTRY)
    assert tag_start_bytes is not None, 'No reproducible start bytes for the pickaxe tag'
    tag_start, tag_now = json.loads(tag_start_bytes.decode('utf-8-sig'))['values'], read(ROOT/(GENERATED_ROOT+TAG_ENTRY))['values']
    tag_inserted = insertions(tag_start, tag_now)
    need(tag_inserted is not None and [v for _, v in tag_inserted] == ['hbmsntm:rbmk_storage'],
         f'the pickaxe tag is not the start list plus hbmsntm:rbmk_storage: inserted {None if tag_inserted is None else [v for _, v in tag_inserted]}')
    # Recipes: the shaped storage recipe (computed from the generated JSON) against the original row; the special rod disassembly recipe; no anvil row is registered.
    o_crafting, o_anvil = original_text(O_CRAFTING), original_text(O_ANVIL)
    o_row = original_shaped_row(o_crafting, 'Blocks', 'rbmk_storage', 1)
    assert o_row is not None and all(v is not None for v in o_row['key'].values()), f'The original rbmk_storage recipe row could not be parsed or translated: {o_row}'
    assert 'GameRegistry.addRecipe(new RBMKFuelCraftingHandler());' in o_crafting, 'The original no longer registers RBMKFuelCraftingHandler'
    anvil_lines = [i for i, l in enumerate(o_anvil.split('\n'), 1) if 'ModBlocks.rbmk_storage' in l]
    assert anvil_lines, 'The original has no anvil row for rbmk_storage any more'
    crafting = {}
    if (ROOT/G_STORAGE_RECIPE).is_file():
        data = read(ROOT/G_STORAGE_RECIPE)
        neo_row = dict(pattern=data.get('pattern'), key=data.get('key'), result=data.get('result'))
        crafting['rbmk_storage'] = dict(type=data.get('type'), neo=neo_row, original=jsonable(o_row))
        need(data.get('type') == 'minecraft:crafting_shaped' and row_matches(neo_row, o_row), f'{G_STORAGE_RECIPE} differs from the original recipe row: {neo_row} vs {jsonable(o_row)}')
    else:
        need(False, 'generated recipe missing: '+G_STORAGE_RECIPE)
    special = None
    if (ROOT/G_DISASSEMBLY_RECIPE).is_file():
        special = read(ROOT/G_DISASSEMBLY_RECIPE)
        need(special.get('type') == 'hbmsntm:rbmk_rod_disassembly' and set(special) <= {'type', 'category'}, f'{G_DISASSEMBLY_RECIPE} is not the bare special recipe: {special}')
    else:
        need(False, 'generated recipe missing: '+G_DISASSEMBLY_RECIPE)
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
    recycling_test_names = sorted(GAMETEST_METHOD.findall((ROOT/RECYCLING_TESTS).read_text(encoding='utf-8'))) if (ROOT/RECYCLING_TESTS).is_file() else []
    recycling_annotations = annotations(ROOT/RECYCLING_TESTS) if (ROOT/RECYCLING_TESTS).is_file() else 0
    need(bool(recycling_test_names) and recycling_annotations == len(recycling_test_names), f'{RECYCLING_TESTS} holds {recycling_annotations} @GameTest annotations and {len(recycling_test_names)} parsed methods')
    need(gametest_added == recycling_annotations, f'GameTest sources grew by {gametest_added} tests, RBMKRecyclingGameTests holds {recycling_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in recycling_test_names), 'GameTest log lacks "[hbm-rbmk-recycling] <name> passed" for: '+str([n for n in recycling_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal25a/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal25a/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal25a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal25a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal25a/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA + OPTIONAL_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal25a/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal24e final run plus the Goal25A verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal24e final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal25A suite is already in the goal24e final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal25a/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal24e final set + the Goal25A verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = pile_balance = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal25a/'+VERIFY_REPORT+' (tools/migration/verify_goal25a_rbmk_recycling.py report)'):
        report = read(OUT/VERIFY_REPORT)
        # RBMKConsoleGameTests is a comment-only edit: the verifier does not hash it (the receipt's changed_files do).
        required_hashes = [p for p in production_changed if (not p.startswith(RES) or p == ZH_INPUT) and p != CONSOLE_TESTS]
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
        verifier_references = sorted(set(re.findall(r'(?:TileEntityRBMKStorage|RBMKStorage|ContainerRBMKStorage|GUIRBMKStorage|TileEntityWasteDrum|FuelPoolRecipes|RBMKFuelCraftingHandler|RBMKRodDisassemblyHandler|'
                                                      r'FuelPoolHandler|ItemRBMKRod|CraftingManager|AnvilRecipes|ChemicalPlantRecipes|NBTControlPacket|ClientProxy)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        # The verifier ran against the final GameTest log and expected the sources' total; the pile model run is compared tick by tick (item (h)).
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
        pile = gt_extra.get('pile') or {}
        need(pile.get('ok') is True and pile.get('compared_ticks') == 2400 and pile.get('first_fail_t') is None and not pile.get('failing_fields') and pile.get('max_abs', [None, None])[1] == 0.0,
             f'{VERIFY_REPORT} pile comparison is not 2400 ticks with zero deviation: {json.dumps(pile)[:300]}')
        model = read(ROOT/'build/migration/goal25a/pile/model-run.json') if (OUT/'pile/model-run.json').is_file() else {}
        primary = (model.get('runs') or {}).get('primary', {}).get('summary', {})
        steam = {k: v for k, v in (primary.get('final') or {}).items() if k.endswith('.steam')}
        need(bool(steam) and all(v == 0.0 for v in steam.values()) and primary.get('boiler_over_100') is False, 'the original-formula pile model makes steam in the original layout: '+str(steam))
        pile_balance = dict(ticks=pile.get('compared_ticks'), max_abs_deviation=pile.get('max_abs'), max_rel_deviation=pile.get('max_rel'), first_fail_tick=pile.get('first_fail_t'),
                            nu_column_t2400=opt(pile, 'model_t2400', 'nu.col'), nu_column_t2400_game=opt(pile, 'log_t2400', 'nu.col'), console_fuel_temp_model=pile.get('console_fuel_temp_model'),
                            console_fuel_temp_game=pile.get('console_fuel_temp_log'), steam_in_model=steam, model='tools/migration/goal25a_pile_model.py', model_run='build/migration/goal25a/pile/model-run.json',
                            note='Item (h): the GameTest small-pile trajectory over 2400 ticks equals the original-formula model exactly (0 deviation); the original layout makes no steam (heat in about 7.7/tick '
                                 'against passive cooling about 8.1/tick, equilibrium).')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal24e compare paths (which hold the 24B..24E paths) plus this batch's compare-inventory paths and the
    # three small-fix sources that changed since that snapshot).
    cmp24e = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal24e/compare.json differs from the goal24e receipt'
    c24e_added = sorted(p for p in compare_paths(cmp24e['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c24e_modified = sorted(p for p in compare_paths(cmp24e['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    small_target = sorted(p for p in SMALL_FIX_SOURCES if in_compare_inventory(p))
    expected_target = sorted(set(c24e_added) | set(c24e_modified) | set(own_target) | set(small_target))
    expected_added = sorted(set(c24e_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal25a/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-24e paths + %d of this batch + %d small-fix sources)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(c24e_added) + len(c24e_modified), len(own_target), len(small_target))):
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
        owner_of_target = lambda p: [OWNER] if p in own_target else [SMALL_OWNER] if p in small_target and p not in c24e_added and p not in c24e_modified else ['goal24a-goal24e (goal24e compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal24e_paths=len(c24e_added) + len(c24e_modified), goal25a_paths=len(own_target), small_fix_paths=small_target)
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the rbmk-fuel (24B), rbmk-reactor (24C), rbmk-control and rbmk-steam (24D) and rbmk-console (24E) groups.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without rbmk-fuel, rbmk-reactor, rbmk-control, rbmk-steam and rbmk-console)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal25a (or the small fixes of 17c8062f).
    jar_delta = dir_delta = entry_owners = class_owners = language = small_fix_entries = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) not in (previous_sha, start_jar_sha), 'build/libs/hbmsntm-198A.jar is still the previous (goal24e) package or the start build (run the final build)'):
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
                 f'JAR en_us.json or zh_cn.json delta against the previous package is not the {len(KEYS)} new keys (+ {SHELL} in Chinese): en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
            small_fix_entries = {n: dict(sha256=hashlib.sha256(jar.read(n)).hexdigest(), previous_sha256=hashlib.sha256(prior.read(n)).hexdigest(), equals_build_classes=n in names) for n in SMALL_FIX_ENTRIES if n in names}
        generated_entries = set(generated_added)
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if kind == 'modified' and n in SMALL_FIX_ENTRIES: owner = [SMALL_OWNER]
                elif n.endswith('.class') and owner_class(n) in PRODUCTION_JAVA: owner = [OWNER]
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY, TAG_ENTRY, 'META-INF/MANIFEST.MF'): owner = [OWNER]
                elif kind == 'added' and (n in asset_entries or n in generated_entries): owner = [OWNER]
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 5 small-fix class entries of 17c8062f, the 7 imported resources, the generated additions and '
             'the modified en_us.json / zh_cn.json / pickaxe tag / MANIFEST.MF are owned): '+str(unowned[:10]))
        need(sorted(n for n in jar_delta['modified'] if n in SMALL_FIX_ENTRIES) == sorted(SMALL_FIX_ENTRIES), 'The five small-fix class entries are not all modified against the goal24e package: '+str(
            sorted(set(SMALL_FIX_ENTRIES) - set(jar_delta['modified']))))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) - set(SMALL_FIX_SOURCES) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA) and set(SMALL_FIX_SOURCES) <= set(class_owners),
             'Changed Java sources and goal25a JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java) - set(SMALL_FIX_SOURCES))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, TAG_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + pickaxe tag + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        inner = 'com/hbm/handler/jei/RBMKRodDisassemblyRecipeHandler$DisassemblyRecipe.class'
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal24e_start=sorted(repinned),
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, removed_comment_lines={p: len(v) for p, v in removed_comments.items()},
                   constants={k: c['neo'] == c.get('neo_expected', c['original']) for k, c in constants.items()}, neo_facts={k: f['neo'] == f['expected'] for k, f in neo_facts.items()},
                   known_differences=known_differences, column_types_equal=column_types['neo'] == column_types['original'], rods=rods,
                   client_imports_in_common_classes=sorted(p for p, v in client_imports.items() if v),
                   crafting_recipes=len(crafting), gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_recycling_tests=recycling_test_names, final_suites_expected=final_expected,
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
    rbmk_recycling = dict(neo=[STORAGE_BLOCK, STORAGE_BE, STORAGE_MENU, STORAGE_SCREEN, SERIALIZERS, DISASSEMBLY_RECIPE, DISASSEMBLY_JEI, DRUM, FUEL_POOL_JEI, COLUMN_TYPE_FILE, CONTROL_PACKET],
                          original=[p for p in O_SOURCES], constants=constants, neo_only_facts=neo_facts, known_differences=known_differences, column_types=column_types, craftable_rods=rods,
                          original_references=original_refs,
                          defaults=dict(storage_slots=12, storage_compaction_period_ticks=10, storage_autoloader_in_slot=11, storage_autoloader_out_slot=0, drum_decay_ticks=72000,
                                        rod_update_heat=0.025, rod_provide_heat_reference=20, rod_provide_heat_modifier=0.025, drum_extraction_core_below=50, drum_extraction_hull_below=50,
                                        disassembly_stack_count=1, disassembly_core_below=50, disassembly_hull_below=50, disassembly_enrichment_nothing_above=0.99, disassembly_pellets=8,
                                        disassembly_meta='4 - clamp(ceil(enrichment * 5 - 1), 0, 4) + (xenon >= 0.5 ? 5 : 0)', jei_fuel_pool_rows=rods['neo_craftable'], jei_fuel_pool_yield=0.2,
                                        jei_fuel_pool_hot_core=100, jei_fuel_pool_hot_hull=50, jei_disassembly_grades=5, jei_disassembly_xenon=50, control_guard_blocks=64),
                          note='The storage column keeps 12 rod slots; every 10 world ticks one forward pass moves a rod into an empty slot in front of it (TileEntityRBMKStorage :27-41), so a gap '
                               'closes by one slot per pass; the autoloader loads into slot 11 and unloads from slot 0 (:69-91); isItemValidForSlot accepts rods only, extraction is always allowed and '
                               'every slot is reachable from every face (:53-66); every non-core block of the 3-deep multiblock is an inventory-only proxy (RBMKStorage.java:14-19). The spent fuel pool drum '
                               'cools each rod every tick while water touches it (updateHeat 0.025 then provideHeat to the reference 20 at 0.025, TileEntityWasteDrum :212-216), the rod never rolls to convert, '
                               'and automation takes a rod out only when core and hull are below 50 (:183-189); hand extraction is not gated (ContainerWasteDrum uses plain slots). The cold rod '
                               'disassembly recipe (RBMKFuelCraftingHandler :17-61, registered CraftingManager :74,80) takes exactly one cold rod (core and hull below 50) with a pellet: an enrichment '
                               'above 0.99 gives nothing, otherwise 8 pellets with META = 4 - clamp(ceil(enrichment x 5 - 1), 0, 4) + (xenon >= 0.5 ? 5 : 0), the rod\'s container item is the empty rod. JEI '
                               'shows 31 display-only fuel pool rows "hot rod (yield 0.2x, core 100, hull 50) -> rod (yield 0.2x)" and per rod 5 disassembly grades plus the xenon-50 rows for pellets with xenon '
                               '(NEI hiding of hot rods by heat is not expressible: rods have no JEI subtype). NEO-only: the CompoundTagControl guard (64 blocks, loaded position, block entity branch only), the '
                               'rod guard of IRBMKLoadable.canLoad, the one-second setChanged of a cooling drum. Not migrated: the tier-4 anvil recycling row (AnvilRecipes.java:921-925, 4-tier anvil unreachable), '
                               'rbmk_fuel_drx (GOAL24 decision 5). Known difference left as found: chem.batteryquantum dense wire BSCCO (original) vs GOLD (NEO), a candidate small fix.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), SHELL_ZH, language_kinds, len(ASSETS), len(recycling_test_names), gametest_expected, rods['neo_craftable']),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=start_head[:8], goal24_closeout=closeout,
                   uncommitted_start=dict(status_entries=0, description=base['start_content']['uncommitted'], base_release=previous_rel, status=[],
                                          note='clean worktree: the start hashes are the committed tree; the Goal 25 planning documents are committed in 783b6d13'),
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha,
                                      note='The start tree is HEAD 783b6d13 (the Goal 25 planning commit, local, not pushed) on top of the pushed Goal 24 close-out commit 17c8062f, with a clean worktree. '
                                           'build/libs at the start is NOT the goal24e package: it is the D1b small-fix build 479fd6f3... whose JAR entries differ from the goal24e package in exactly the five '
                                           'class entries of the three small fixes committed in 17c8062f (D1 NtmGeometry, D2 RenderRBMKPiped, D1b RBMKElementBakedModel); goal25a packages them with the '
                                           'batch, the sources are unchanged since the start. The original did not move since 24A. The freeze copied 34 scope files to baseline-files; ClientProxy.java '
                                           'and RBMKConsoleGameTests.java come from the start-commit blob. Paths this batch changes record the start hash as before_sha256.'),
                   pending_small_fixes=dict(fixes, jar_entries_in_release=small_fix_entries, owner=SMALL_OWNER, sources_unchanged_since_start=True),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, removed_comment_lines=removed_comments, start_copies_supplement=[],
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   rbmk_recycling=rbmk_recycling, pile_balance=pile_balance,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked, shell_copper=dict(key=SHELL, zh=zh_now.get(SHELL),
                                                                                                                                       map_before=map_start.get(SHELL), map_after=map_now.get(SHELL)),
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note=f'{EXPECTED_KINDS["upstream"]} entries are upstream (the 11 key binding names hbmsntm.keys* from hbm.key*, English and Chinese verbatim, and the mutation effect from '
                                      f'potion.hbm_mutation); {EXPECTED_KINDS["local"]} are NEO-local (the storage column block and container names, a local rewrite of tile.rbmk_storage.name / '
                                      'container.rbmkStorage following the RBMK反应堆…柱 naming of 24A-24D, GOAL25 decision 16, with the original source key, English and Chinese kept in the map entry; '
                                      'the JEI title of the rod disassembly category, whose original NEI title is hard-coded English); item.hbmsntm.shell_copper (English since 24D) gains its Chinese '
                                      '"铜壳" and moves from deferred to local in the mapping. No existing key changes its English value.'),
                   recipes=dict(crafting=crafting, special=dict(path=G_DISASSEMBLY_RECIPE.replace(GENERATED_ROOT, ''), content=special), not_registered=['anvil row (tier 4) rbmk_storage -> rbmk_blank + 2 crate_steel: '
                                'AnvilRecipes.java:921-925, the 4-tier anvil is unreachable in NEO (NtmRecipeProvider comment)'],
                                original_references={k: v for k, v in original_refs.items() if k.startswith(('recipe_', 'anvil_', 'disassembly_register', 'chem_'))},
                                anvil_recipes_unchanged=sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES],
                                chem_batteryquantum=dict(change='fluid input only: PERFLUOROMETHYL -> PERFLUOROMETHYL_COLD, 8,000 mB; items, output, duration and power unchanged',
                                                         added_lines=[l.strip() for l in added_lines.get(CHEM_RECIPES, [])], removed_lines=[l.strip() for l in removed_lines.get(CHEM_RECIPES, [])]),
                                note='The storage recipe equals the original row (CraftingManager :770); the disassembly recipe is a bare special recipe (type hbmsntm:rbmk_rod_disassembly), registered through '
                                     'NtmRecipeSerializers; AnvilRecipes stays unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith('repinned_since_')},
                   repinned_since_goal24e_start={p: dict(goal24e_start_pin_sha256=h, goal25a_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_recycling_tests=recycling_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per RBMKRecyclingGameTests test: the storage column (layout, '
                                      'compaction, automation, drops, meltdown), the drum cooling and rules, the disassembly recipe, the config and chem close-outs, the control guard and the pile balance; '
                                      'no client (the storage screen, the lid renderer, the JEI rows and the crafting GUI are not rendered), no real player, no saved world, no survival chain.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['rbmk_console (the Goal24E-only key; Goal25A adds rbmk_recycling and pile_balance)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the original-formula pile model compared tick by tick, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and two static '
                            'reviews (the redundant review ran before the user dropped it on 2026-10-20). No in-game client test was run: the storage screen, the lid rendering, the JEI rows and the rod '
                            'disassembly category, the crafting GUI and the Chinese UI are unverified; no survival chain (reactor to pool to disassembly) in a world was run; no multiplayer or dedicated '
                            'server beyond GameTest; GOAL25A-ACCEPTANCE.md (the 25A real-game checklist) is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, start_jar_sha), 'build/libs JAR is an older JAR'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal25a JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal24e package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
