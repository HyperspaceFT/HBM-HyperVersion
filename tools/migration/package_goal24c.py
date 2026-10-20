"""Package Goal24C (the RBMK reactor core loop, no control rods, boilers or console yet: the neutron nodespace handler/neutron/ (NeutronHandler, NeutronNodeWorld with a
static Map<Level, StreamWorld>, NeutronNode, NeutronStream, RBMKNeutronHandler, package-info with the original's documentation) ticked from NtmEventHandler's server tick,
cleared on level unload and server stop; the fuel columns rbmk_rod and rbmk_rod_mod (RBMKRodBlock, RBMKRodBlockEntity on RBMKSlottedBaseBlockEntity, IRBMKLoadable,
IRBMKFluxReceiver.receiveFlux, menu and screen, block-entity renderer, baked body model); corium_block; the rbmk_rod crafting recipe; 23 imported resources; 12 language
keys; RBMKReactorGameTests) cumulatively on the goal24b package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal24c.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal24c/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal24c/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal24c/baseline.json: NEO HEAD 1114adf5 (the Goal 24 planning commit on top of the pushed Goal 23 close-out commit 09173669)
with the UNCOMMITTED Goal24A and Goal24B deliveries (655 default status entries). The original HEAD aee05a40f did not move since 24A, so there is no upstream
classification and no new snapshot. build/libs at the start is the goal24b package byte for byte. Every change since the start is computed from the baseline file
hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with
their start bytes (baseline-files, which holds all of them: 34 scope copies plus the four supplement copies freeze.log records for RenderRBMKLid,
NtmBlockLootTableProvider, NtmBlockTagProvider and NtmGeometry, whose bytes equal their baseline hashes). The JAR delta against the goal24b package is attributed
per entry (goal24c); any entry without exactly one owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys)
are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal24a, the review-g21d-hazard-fix receipt) already differ from their older hashes at the frozen start for the acceptance
checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes build/migration/goal24a/main-notes.md (baseline
older_receipt_evidence_drift; the goal24a receipt hashed main-notes.md before the 24A session appended its "Delivered" section, the goal24b receipt hashes it at its
current hash). They are listed in the receipt as start drift and must still equal their Goal24C start hash; no receipt is rewritten and no other protected path may
drift. The goal24b receipt has no drift of its own at the start (baseline previous_receipt_evidence_drift is empty).

Like the Goal24B packager this one has a single compare run (build/migration/goal24c/compare.json against the snapshot review-aee05a40f10f.json taken at the end of
24A: original 0/0/0, target = exactly the Goal24B compare-inventory paths (read from build/migration/goal24b/compare.json) plus this batch's), no upstream
classification, no screwdriver section and no rbmk_fuel constants; it adds the rbmk_reactor constants (checked against the original and NEO source texts)."""
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
from package_goal24a import original_text, original_line, original_blob, lang_file, provider_keys, SOURCE_HEAD
from package_goal24b import OUT as GOAL24B_OUT, BASELINE as GOAL24B_BASELINE, protected_paths as goal24b_protected_paths

OUT = ROOT/'build/migration/goal24c'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL24B_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL24B_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal24b/hbmsntm-198A-goal24b.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal24c'
RELEASE_NAME = 'hbmsntm-198A-goal24c.jar'
OWNER = 'goal24c'
PLANNING_PREFIX = '1114adf5'
GOAL23_CLOSEOUT = '09173669'
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
START_STATUS_ENTRIES = 655
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'

# Production (owner goal24c), NEW: the neutron package, the loadable interface, the slotted base and the fuel-column block entity, the column block, corium, menu, screen,
# the renderer and baked model, and the GameTest class (handoff-packaging.md; builder-progress.md names the baked model RBMKElementBakedModel).
NEW_JAVA = [J+p+'.java' for p in (
    'handler/neutron/NeutronHandler', 'handler/neutron/NeutronNodeWorld', 'handler/neutron/NeutronNode', 'handler/neutron/NeutronStream',
    'handler/neutron/RBMKNeutronHandler', 'handler/neutron/package-info',
    'blockentity/machine/rbmk/IRBMKLoadable', 'blockentity/machine/rbmk/RBMKSlottedBaseBlockEntity', 'blockentity/machine/rbmk/RBMKRodBlockEntity',
    'blocks/machine/rbmk/RBMKRodBlock', 'blocks/generic/CoriumBlock', 'inventory/menus/RBMKRodMenu', 'inventory/screens/RBMKRodScreen',
    'render/blockentity/RenderRBMKRod', 'render/model/RBMKElementBakedModel', 'gametest/RBMKReactorGameTests')]
(NEUTRON_HANDLER, NODE_WORLD, NEUTRON_NODE, NEUTRON_STREAM, RBMK_HANDLER, PACKAGE_INFO, LOADABLE, SLOTTED, ROD_BE, ROD_BLOCK, CORIUM, ROD_MENU, ROD_SCREEN,
 ROD_RENDERER, BAKED_MODEL, REACTOR_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blockentity/machine/rbmk/IRBMKFluxReceiver', 'blockentity/machine/rbmk/RBMKBaseBlockEntity', 'main/NtmEventHandler', 'blocks/NtmBlocks', 'blockentity/NtmBlockEntityTypes',
    'inventory/NtmMenuTypes', 'main/NuclearTechModClient', 'main/ClientProxy', 'main/ResourceManager', 'render/blockentity/RenderRBMKLid', 'render/model/loader/NtmGeometry',
    'inventory/NtmCreativeTabs', 'datagen/NtmBlockStateProvider', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmLanguageProvider',
    'datagen/NtmRecipeProvider')]
(FLUX_RECEIVER, BASE_BE, EVENT_HANDLER, BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, CLIENT, CLIENT_PROXY, RESOURCE_MANAGER, LID_RENDERER, GEOMETRY, CREATIVE_TABS, BLOCK_STATE_PROVIDER,
 LOOT_PROVIDER, TAG_PROVIDER, PROVIDER, RECIPE_PROVIDER) = MODIFIED_JAVA
# The handoff expected NtmItemModelProvider to change too; builder-progress.md says it did not need to. It may change, it is not required to.
ITEM_MODEL_PROVIDER = J+'datagen/NtmItemModelProvider.java'
# Review fix (main agent): one comment line of the 24A RBMKBaseBlock.useItemOn went stale when RBMKRodBlock began to override it; the
# edit stays on its line, so the class file need not change.
BASE_BLOCK = J+'blocks/machine/rbmk/RBMKBaseBlock.java'
OPTIONAL_JAVA = [ITEM_MODEL_PROVIDER, BASE_BLOCK]
# Javadoc-only package-info.java compiles to no class file unless it carries annotations; it needs no JAR class.
NO_CLASS_JAVA = [PACKAGE_INFO]
# Sources whose edit may leave every class file byte-identical (a comment changed on its own line).
SAME_CLASS_JAVA = [BASE_BLOCK]
ANVIL_RECIPES = J+'inventory/recipes/anvil/AnvilRecipes.java'
# Registration and datagen files that must stay insert-only against their start bytes.
STRICT_INSERT_ONLY = [BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, CLIENT, CLIENT_PROXY, RESOURCE_MANAGER, CREATIVE_TABS, BLOCK_STATE_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER,
                      PROVIDER, RECIPE_PROVIDER, ITEM_MODEL_PROVIDER, ZH_INPUT]
# The 23 imported original resources: NEO target -> original path, derived by the layout rules of the ownership record (textures/block -> textures/blocks,
# models/obj/rbmk -> models/rbmk, the GUI texture keeps its path).
_VARIANTS = ('rbmk_element', 'rbmk_element_mod')
_PARTS = ('side', 'top', 'cover_top', 'cover_side', 'glass_top', 'glass_side', 'inner', 'fuel')
ASSETS = {ASSETS_ROOT+f'textures/block/rbmk/{v}_{p}.png': O_RES+f'textures/blocks/rbmk/{v}_{p}.png' for v in _VARIANTS for p in _PARTS}
ASSETS.update({ASSETS_ROOT+f'textures/block/{n}': O_RES+f'textures/blocks/{n}' for n in ('corium_still.png', 'corium_still.png.mcmeta', 'corium_flowing.png', 'corium_flowing.png.mcmeta')})
ASSETS.update({ASSETS_ROOT+f'models/obj/rbmk/{n}.obj': O_RES+f'models/rbmk/{n}.obj' for n in ('rbmk_element', 'rbmk_element_rods')})
ASSETS[ASSETS_ROOT+'textures/gui/reactors/gui_rbmk_element.png'] = O_RES+'textures/gui/reactors/gui_rbmk_element.png'
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
TAG_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
GENERATED = [STAMP, EN, GENERATED_ROOT+TAG_ENTRY]
# Generated by runData for this batch (relative to src/generated/resources): 3 blockstates, 3 block models, 3 item models, 3 loot tables, the rbmk_rod recipe + advancement.
_BLOCKS = ('corium_block', 'rbmk_rod', 'rbmk_rod_mod')
EXPECTED_GENERATED = sorted([f'assets/hbmsntm/{kind}/{b}.json' for kind in ('blockstates', 'models/block', 'models/item') for b in _BLOCKS]
                            + [f'data/hbmsntm/loot_table/blocks/{b}.json' for b in _BLOCKS]
                            + ['data/hbmsntm/recipe/rbmk_rod.json', 'data/hbmsntm/advancement/recipes/misc/rbmk_rod.json'])
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, TAG_ENTRY])
NEW_TOOLS = ['tools/migration/verify_goal24c_rbmk_reactor.py', 'tools/migration/package_goal24c.py']
TOOLS = NEW_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal24c-* or GOAL24C-* record is hashed as well.
REPORTS = ['migration/GOAL24C.md', 'migration/GOAL24C-ACCEPTANCE.md', 'migration/goal24c-static-review.md', 'migration/goal24c-localization-review.json',
           'migration/goal24c-resource-ownership.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal24c-[^/]+\.(json|md)|GOAL24C-[^/]+\.md)')
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/GOAL24.md']
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + SHARED_RECORDS
# The 12 new language keys: NEO key -> original key (None: a NEO-local key). The two hover lines of GUIRBMKRod are hard-coded English in the original (GUIRBMKRod.java:33, :35).
KEYS = {'block.hbmsntm.rbmk_rod': 'tile.rbmk_rod.name', 'block.hbmsntm.rbmk_rod_mod': 'tile.rbmk_rod_mod.name', 'block.hbmsntm.corium_block': 'tile.corium_block.name',
        'container.rbmkRod': 'container.rbmkRod', 'container.rbmkRod.autoloaderHot': None, 'container.rbmkRod.manualHot': None}
KEYS.update({'tile.rbmk.dodd.'+t: 'tile.rbmk.dodd.'+t for t in ('fluxSlow', 'fluxFast', 'hasRod', 'f_heat', 'f_xenon', 'f_yield')})
EXPECTED_KINDS = {'upstream': sum(1 for v in KEYS.values() if v), 'local': sum(1 for v in KEYS.values() if not v)}
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rbmk-reactor] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'main-notes.md', 'builder-progress.md', 'handoff-production.md',
                  'handoff-gametest.md', 'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md', 'make_production_diff.py', 'chain.sh')
# Review files under OUT (for example the two independent static reviews' notes or diffs) the main agent names when it knows them; each must exist and is
# indexed by the receipt. Extend this list from the real run (review notes, the verifier and packager progress files, the verifier-gt / verifier-script files ...);
# --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'packaging-progress.md', 'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt',
                   'production-diff.patch', 'builder-compile-1.log', 'builder-compile-2.log', 'builder-rundata-1.log', 'stamp-before-builder-rundata-1.json',
                   'generated-before-builder-rundata-1.json', 'import_resources.py', 'insert_localization.py', 'crlf_edit.py')
GAMETEST_LOG = 'build/migration/goal24c/gametest-final.log'
NEW_SUITE = 'verify_goal24c_rbmk_reactor.py --gametest-log build/migration/goal24c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_GROUP, FEATURE_FUEL = 'rbmk-reactor', 'rbmk-fuel'
RADIATION_NOTE = ('Goal24C: a burning RBMK fuel column without a lid raises its chunk\'s radiation by 5 % of its neutron flux every tick, and every neutron stream passing '
                  'an unlidded column adds the same; corium burns, damages and contaminates whoever stands on it; run reactors only in separately authorized disposable worlds. ')
MELTDOWN_NOTE = ('Goal24C: a fuel column above 1,500 °C (or broken while its rod\'s hull is at 1,500 °C or more) melts the whole connected RBMK down into debris blocks and '
                 'corium and flings fuel, graphite and element debris; meltdowns are enabled by default (dialDisableMeltdowns false) and there are no control rods yet (24D); '
                 'only in disposable worlds away from builds. ')
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_NEUTRON = ORIGINAL+'handler/neutron/'
O_HANDLER, O_NODE_WORLD, O_NODE, O_STREAM, O_RBMK_HANDLER, O_PACKAGE_INFO = (O_NEUTRON+n+'.java' for n in (
    'NeutronHandler', 'NeutronNodeWorld', 'NeutronNode', 'NeutronStream', 'RBMKNeutronHandler', 'package-info'))
O_RBMK = ORIGINAL+'tileentity/machine/rbmk/'
O_ROD_TILE, O_FLUX, O_LOADABLE, O_BASE_TILE, O_SLOTTED_TILE, O_ACTIVE_TILE, O_DIALS = (O_RBMK+n+'.java' for n in (
    'TileEntityRBMKRod', 'IRBMKFluxReceiver', 'IRBMKLoadable', 'TileEntityRBMKBase', 'TileEntityRBMKSlottedBase', 'TileEntityRBMKActiveBase', 'RBMKDials'))
O_ROD_BLOCK = ORIGINAL+'blocks/machine/rbmk/RBMKRod.java'
O_CONTAINER = ORIGINAL+'inventory/container/ContainerRBMKRod.java'
O_GUI = ORIGINAL+'inventory/gui/GUIRBMKRod.java'
O_FUEL_RENDERER = ORIGINAL+'render/tileentity/RenderRBMKFuelChannel.java'
O_BLOCK_RENDERER = ORIGINAL+'render/block/RenderRBMKRod.java'
O_CORIUM = ORIGINAL+'blocks/fluid/CoriumFinite.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_ANVIL = ORIGINAL+'inventory/recipes/anvil/AnvilRecipes.java'
O_EVENTS = ORIGINAL+'main/ModEventHandler.java'
O_SOURCES = [O_HANDLER, O_NODE_WORLD, O_NODE, O_STREAM, O_RBMK_HANDLER, O_PACKAGE_INFO, O_ROD_TILE, O_FLUX, O_LOADABLE, O_BASE_TILE, O_SLOTTED_TILE, O_ACTIVE_TILE, O_DIALS,
             O_ROD_BLOCK, O_CONTAINER, O_GUI, O_FUEL_RENDERER, O_BLOCK_RENDERER, O_CORIUM, O_CRAFTING, O_ANVIL, O_EVENTS]
# The groups of original sources the rbmk-reactor mapping group must list (source_paths or source_watch); the 23 imported resources are added.
FEATURE_SOURCES = [O_HANDLER, O_NODE_WORLD, O_NODE, O_STREAM, O_RBMK_HANDLER, O_PACKAGE_INFO, O_ROD_TILE, O_FLUX, O_LOADABLE, O_ROD_BLOCK, O_CONTAINER, O_GUI, O_FUEL_RENDERER,
                   O_BLOCK_RENDERER, O_CORIUM]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'handler_tick': (O_HANDLER, 'public void onServerTick('), 'handler_cache_time': (O_HANDLER, 'int cacheTime = '), 'handler_remove_empty': (O_HANDLER, 'NeutronNodeWorld.removeEmptyWorlds()'),
    'handler_clean_nodes': (O_HANDLER, 'cleanNodes()'), 'node_world_stream_worlds': (O_NODE_WORLD, 'public static HashMap<World, StreamWorld> streamWorlds'),
    'node_world_get_or_add': (O_NODE_WORLD, 'public static StreamWorld getOrAddWorld('), 'unload_hook': (O_EVENTS, 'NeutronNodeWorld.streamWorlds.remove(event.world)'),
    'rbmk_make_node': (O_RBMK_HANDLER, 'public static RBMKNeutronNode makeNode('), 'rbmk_check_node': (O_RBMK_HANDLER, 'public List<BlockPos> checkNode('),
    'rbmk_run_stream': (O_RBMK_HANDLER, 'public void runStreamInteraction('), 'rbmk_get_hits': (O_RBMK_HANDLER, 'public int getHits('),
    'rbmk_irradiate': (O_RBMK_HANDLER, 'public void irradiateFromFlux('),
    'rod_track_range': (O_ROD_TILE, 'public int trackingRange()'), 'rod_receive_flux': (O_ROD_TILE, 'public void receiveFlux('), 'rod_cold_autoloader': (O_ROD_TILE, 'public boolean coldEnoughForAutoloader()'),
    'rod_cold_manual': (O_ROD_TILE, 'public boolean coldEnoughForManual()'), 'rod_invalidate': (O_ROD_TILE, 'public void invalidate()'), 'rod_update': (O_ROD_TILE, 'public void updateEntity()'),
    'rod_heat_clamp': (O_ROD_TILE, 'if(this.heat > 10_000)'), 'rod_flux_from_type': (O_ROD_TILE, 'private double fluxFromType('), 'rod_flux_dirs': (O_ROD_TILE, 'public static final ForgeDirection[] fluxDirs'),
    'rod_on_melt': (O_ROD_TILE, 'public void onMelt('), 'rod_can_load': (O_ROD_TILE, 'public boolean canLoad('),
    'base_max_heat': (O_BASE_TILE, 'public double maxHeat()'), 'block_break': (O_ROD_BLOCK, 'public void breakBlock('), 'block_activated': (O_ROD_BLOCK, 'public boolean onBlockActivated('),
    'container_slot_click': (O_CONTAINER, 'public ItemStack slotClick('), 'container_transfer': (O_CONTAINER, 'public ItemStack transferStackInSlot('),
    'gui_hover_autoloader': (O_GUI, 'Fuel skin temperature has exceeded 1,000'), 'gui_hover_manual': (O_GUI, 'Fuel skin temperature has exceeded 200'),
    'corium_collide': (O_CORIUM, 'public void onEntityCollidedWithBlock('), 'recipe_rbmk_rod': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_rod, 1)'),
    'recipe_rbmk_rod_mod': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_rod_mod, 1)'), 'anvil_rbmk_rod': (O_ANVIL, 'new ComparableStack(ModBlocks.rbmk_rod)'),
    'anvil_rbmk_rod_mod': (O_ANVIL, 'new ComparableStack(ModBlocks.rbmk_rod_mod)'),
}
# Original crafting-manager key expressions -> the NEO ingredient (the generated recipe of rbmk_rod is compared against the parsed original row).
KEY_TABLE = {'STEEL.shell()': {'item': 'hbmsntm:shell_steel'}, 'ModBlocks.rbmk_blank': {'item': 'hbmsntm:rbmk_blank'}}
# Constants compared between the original and NEO source texts: id -> (original path, regex, NEO path, regex, expected unique values in order). Numbers are compared as floats
# (underscores dropped, F / D suffixes dropped), anything else as text. The group-1 value of every match is collected.
_DIAL = r'%s\("%s", ([\d.]+)\)'
_NEO_DIAL = r'defineInRange\("%s", ([\d.]+)D?,'
CONSTANTS = {
    'node_cache_clear_ticks': (O_HANDLER, r'int cacheTime = (\d+);', 'src/main/java/com/hbm/handler/neutron/NeutronHandler.java', r'int cacheTime = (\d+);', [20]),
    'dial_flux_range': (O_DIALS, _DIAL % ('KEY_FLUX_RANGE', 'dialFluxRange'), 'src/main/java/com/hbm/config/CommonConfig.java', _NEO_DIAL % 'dialFluxRange', [5]),
    'dial_moderator_efficiency': (O_DIALS, _DIAL % ('KEY_MODERATOR_EFFICIENCY', 'dialModeratorEfficiency'), 'src/main/java/com/hbm/config/CommonConfig.java', _NEO_DIAL % 'dialModeratorEfficiency', [1.0]),
    'dial_absorber_efficiency': (O_DIALS, _DIAL % ('KEY_ABSORBER_EFFICIENCY', 'dialAbsorberEfficiency'), 'src/main/java/com/hbm/config/CommonConfig.java', _NEO_DIAL % 'dialAbsorberEfficiency', [1.0]),
    'dial_reflector_efficiency': (O_DIALS, _DIAL % ('KEY_REFLECTOR_EFFICIENCY', 'dialReflectorEfficiency'), 'src/main/java/com/hbm/config/CommonConfig.java', _NEO_DIAL % 'dialReflectorEfficiency', [1.0]),
    'dial_absorber_heat_conversion': (O_DIALS, _DIAL % ('KEY_ABSORBER_HEAT_CONVERSION', 'dialAbsorberHeatConversion'), 'src/main/java/com/hbm/config/CommonConfig.java', _NEO_DIAL % 'dialAbsorberHeatConversion', [0.05]),
    'dial_disable_meltdowns': (O_DIALS, r'KEY_DISABLE_MELTDOWNS\("dialDisableMeltdowns", (\w+)\)', 'src/main/java/com/hbm/config/CommonConfig.java', r'define\("dialDisableMeltdowns", (\w+)\)', ['false']),
    'column_radiation_per_flux': (O_ROD_TILE, r'incrementRad\([^;]*\(float\) \(this\.fluxQuantity \* ([\d.]+F)\)', ROD_BE, r'incrementRad\([^;]*\(float\) \(this\.fluxQuantity \* ([\d.]+F)\)', [0.05]),
    'stream_radiation_per_flux': (O_RBMK_HANDLER, r'\(float\) \((?:this\.)?fluxQuantity \* ([\d.]+F)', RBMK_HANDLER, r'\(float\) \((?:this\.)?fluxQuantity \* ([\d.]+F)', [0.05]),
    'flux_from_type_slow': (O_ROD_TILE, r'case SLOW: return slowFlux \+ fastFlux \* ([\d.]+);', ROD_BE, r'case SLOW: return slowFlux \+ fastFlux \* ([\d.]+);', [0.5]),
    'flux_from_type_fast': (O_ROD_TILE, r'case FAST: return fastFlux \+ slowFlux \* ([\d.]+);', ROD_BE, r'case FAST: return fastFlux \+ slowFlux \* ([\d.]+);', [0.3]),
    'manual_removal_max_hull': (O_ROD_TILE, r'coldEnoughForManual\(\)\s*\{.*?<=\s*([\d_]+);', ROD_BE, r'coldEnoughForManual\(\)\s*\{.*?<=\s*([\d_]+);', [200]),
    'autoloader_max_hull': (O_ROD_TILE, r'coldEnoughForAutoloader\(\)\s*\{.*?<=\s*([\d_]+);', ROD_BE, r'coldEnoughForAutoloader\(\)\s*\{.*?<=\s*([\d_]+);', [1000]),
    'break_meltdown_hull': (O_ROD_TILE, r'getHullHeat\(slots\[0\]\) >= (\d+)', ROD_BLOCK, r'getHullHeat\(stack\) >= (\d+)', [1500]),
    'column_max_heat': (O_BASE_TILE, r'public double maxHeat\(\) \{\s*return ([\d.]+)D;', 'src/main/java/com/hbm/blockentity/machine/rbmk/RBMKBaseBlockEntity.java', r'public double maxHeat\(\) \{\s*return ([\d.]+)D;', [1500]),
    'column_heat_clamp': (O_ROD_TILE, r'if\(this\.heat > ([\d_]+)\) this\.heat = [\d_]+;', ROD_BE, r'if\(this\.heat > ([\d_]+)\) this\.heat = [\d_]+;', [10000]),
    'sync_range': (O_ROD_TILE, r'public int trackingRange\(\) \{\s*return (\d+);', ROD_BE, r'public int trackingRange\(\) \{\s*return (\d+);', [25]),
    'corium_fire_seconds': (O_CORIUM, r'setFire\((\d+)\)', CORIUM, r'igniteForSeconds\((\d+)\)', [3]),
    'corium_radiation_damage': (O_CORIUM, r'attackEntityFrom\([^;]*?, ([\d.]+)F\)', CORIUM, r'\.hurt\([^;]*?, ([\d.]+)F\)', [2]),
    'corium_contamination': (O_CORIUM, r'contaminate\([^;]*?, ([\d.]+)F\)', CORIUM, r'contaminate\([^;]*?, ([\d.]+)F\)', [1]),
}
STREAM_DIRECTIONS = ['NORTH', 'EAST', 'SOUTH', 'WEST']
# NtmEventHandler: the three neutron calls and where they live (original NeutronHandler on ServerTickEvent START, ModEventHandler.onUnload; the server-stop clear is NEO-only).
EVENT_HOOKS = ('NeutronHandler.onServerTick(', 'NeutronNodeWorld.removeWorld(', 'NeutronNodeWorld.removeAllWorlds(')


def scope_text(key_count, kinds, assets, reactor_tests, total_tests):
    return (f'Goal24C (the RBMK reactor core loop, no control rods, boilers or console yet): the neutron nodespace handler/neutron/ (NeutronHandler, NeutronNodeWorld with a static '
            f'Map<Level, StreamWorld>, NeutronNode, NeutronStream, RBMKNeutronHandler and a package-info carrying the original\'s documentation) ticked from NtmEventHandler\'s '
            f'ServerTickEvent.Pre after the existing work, cleared on LevelEvent.Unload and ServerStoppedEvent (PileNeutronHandler not ported); the fuel columns rbmk_rod and '
            f'rbmk_rod_mod (RBMKRodBlock, RBMKRodBlockEntity on RBMKSlottedBaseBlockEntity, IRBMKLoadable, IRBMKFluxReceiver.receiveFlux added to the 24B interface) that burn the '
            f'24B fuel rods from received flux, heat the column, spread four neutron streams, radiate when unlidded and melt down above 1,500 °C into a corium column with fuel '
            f'debris, with a menu and screen (manual removal only at hull <= 200 °C), a block-entity renderer for rods, Cherenkov glow and the lid, a baked body model and an item '
            f'renderer; corium_block (static: burns, radiation damage 2 and contamination 1 when stood on; no flow, no solidification); the shaped recipe rbmk_rod (steel shell + '
            f'rbmk_blank), while rbmk_rod_mod and the two anvil recycling rows are not registered; {assets} imported resources (the fuel-column textures, the corium textures with '
            f'their animation metadata, the GUI texture and two OBJ models); {key_count} language keys ({kinds.get("upstream", 0)} upstream, {kinds.get("local", 0)} NEO-local); '
            f'{reactor_tests} RBMKReactorGameTests ({total_tests} GameTests in total, one batch per test). Gameplay impact: fuel columns are craftable from rbmk_blank and steel '
            f'shells; a fuelled column next to a neutron source (Ra226Be / Po210Be / Pu238Be rods) or other fuel starts a chain reaction that heats the column and the rod; unlidded '
            f'columns and stream paths raise chunk radiation; a column above 1,500 °C melts the whole connected reactor down (debris, corium, flying fuel debris) unless '
            f'dialDisableMeltdowns is set; without control rods (24D) a chain reaction can only be stopped by removing fuel (by hand at hull <= 200 °C) or by lids and absorbers.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal24c release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 34 scope copies and the four supplement copies) when it reproduces the baseline hash, otherwise the
    blob at the start commit (with CRLF where the working tree had it) when it reproduces the baseline hash; None when neither does."""
    if (START_FILES/p).is_file():
        data = (START_FILES/p).read_bytes()
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT)
    for data in (blob, blob.replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def start_pin(base, p):
    """The Goal24C start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does
    not list it) the hash the goal24b receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal24b packager protected (built there from the Goal21A..Goal24A starts and receipts and the goal24b start), plus every path the goal24b receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 24C baseline lists the goal24a receipt among them) and every release file of the frozen
    start (the goal24b package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a
    main-notes.md) are pinned at their Goal24C start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes. Returns (protected,
    repinned) where repinned maps a record to the pin the goal24b packager set at its Goal24B start hash, for the records that changed between the two starts."""
    goal24b_start = read(GOAL24B_BASELINE)
    out = dict(goal24b_protected_paths(goal24b_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal24b receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal24b_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift (empty at this start).
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal24B and Goal24C starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal24b_start):
    """{path: {receipts, start_sha256, goal24b_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal24b receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal24b receipt')
        if p in base['previous_receipt_evidence_drift']:
            explanation = ('Changed after the goal24b receipt hashed it; the goal24b receipt hash is older than the start hash. Frozen at the start hash; this batch must not '
                           'change it and the goal24b receipt is not rewritten.')
        elif p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the '
                           'goal24a receipt hash is older than the start hash, the goal24b receipt hashes the current content. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22 and 23 in-game acceptance results, the O1 record notes or the thorium follow-up '
                           'section); the goal24b receipt does not hash it. Frozen at the Goal24C start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal24b) records the start hash. Frozen at the start '
                           'hash; this batch must not change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal24b package; the goal24b receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it '
                           'and the goal24b receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal24b_start_sha256=goal24b_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal24b_start_pin_sha256'] = repinned[p]
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


def normalize_value(value):
    """A regex capture as a comparable value: numbers (underscores and an F / D suffix dropped) as float, anything else as text."""
    text = value.replace('_', '')
    return float(text.rstrip('FfDd')) if re.fullmatch(r'[\d.]+[FfDd]?', text) else text


def captured(text, pattern):
    """The distinct normalized group-1 values of every match of the pattern, in order of first appearance (None when there is no match)."""
    values = []
    for m in re.finditer(pattern, text, re.S):
        v = normalize_value(m.group(1))
        if v not in values: values.append(v)
    return values or None


def direction_names(text, pattern):
    m = re.search(pattern, text, re.S)
    return re.findall(r'(?:ForgeDirection|Direction)\.(\w+)', m.group(1)) if m else None


def original_shaped_block(text, output, count):
    """{pattern, key, result} of the single original addRecipeAuto row producing the block `output` x `count`, or None."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.search(r'addRecipeAuto\(new ItemStack\(ModBlocks\.(\w+), (\d+)\), new Object\[\] \{ (.*) \}\);', line)
        if not m or m.group(1) != output or int(m.group(2)) != count: continue
        tokens = [t.strip() for t in re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', m.group(3))]
        pattern = [t[1:-1] for t in tokens if t.startswith('"')]
        rest = [t for t in tokens if not t.startswith('"')]
        key = {rest[i].strip("'"): KEY_TABLE.get(rest[i+1]) for i in range(0, len(rest)-1, 2)}
        rows.append(dict(pattern=pattern, key=key, result=dict(count=count, id='hbmsntm:'+output)))
    return rows[0] if len(rows) == 1 else None


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
    goal24b_start = read(GOAL24B_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal24C commits nothing), the recorded start with the uncommitted 24A and 24B deliveries.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 24 planning commit'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 24 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    # baseline.json stores `status --untracked-files=all` (every untracked file listed); the 655 entries of the handoff are the default `status --porcelain=v1`
    # (untracked directories collapsed) counted by startup-verification.json.
    full_status = [l for l in base['target_status'].splitlines() if l]
    assert full_status and all(l[:2] in ('??', ' M') for l in full_status), 'The frozen start status holds entries other than modified / untracked'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal24b receipt records another original commit than the frozen start'
    assert base['pending_small_fixes'] == [], 'The frozen start has a pending small fix'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and 'Goal24A' in base['start_content']['uncommitted'] and 'Goal24B' in base['start_content']['uncommitted'], \
        'Baseline start content differs'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal24C: '+head
    closeout = git_ro(ROOT, 'rev-parse', 'HEAD~1').strip()
    assert closeout.startswith(GOAL23_CLOSEOUT), 'NEO HEAD~1 is not the Goal 23 close-out commit'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b',
                                                          'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    # The four supplement copies freeze.log records (copied after the freeze, before any 24C edit) must reproduce their baseline hashes too.
    supplement = sorted(p for p in PRODUCTION_JAVA if p in base['files'] and p not in base['copied_scope'] and (START_FILES/p).is_file())
    for n in supplement:
        assert sha(START_FILES/n) == base['files'][n], 'Supplement start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_entries'] == START_STATUS_ENTRIES and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'] and startup['generated_resources_verified'] == base['stamp_state']['generated_resources_verified'], \
        'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_verified'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal24b generated tree'
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal24b package, every old release file and the protected evidence.
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal24b receipt list + the goal24b package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal24b receipt count + the goal24b release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal24b receipt'
    # The goal24b receipt has no record that drifted before the start (it hashes the goal24a main-notes at the hash that file still has).
    assert base['previous_receipt_evidence_drift'] == {}, 'The goal24b receipt evidence drifted at the start: '+str(sorted(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal24b_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal24b receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal24c. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal24C start that the owner table does not list (production outside the 17 modified Java files (NtmItemModelProvider optional), the 16 new '
         'classes incl. RBMKReactorGameTests, the 23 resources, zh_cn.json and the mapping, a protected record, an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal24C start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD, ANVIL_RECIPES] + GENERATED + SHARED_RECORDS + REPORTS[:1]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    need(sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES], f'{ANVIL_RECIPES} changed since the start (the two anvil recycling rows of rbmk_rod / rbmk_rod_mod are not registered)')
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION + OPTIONAL_JAVA if p.startswith('src/')})
    need(not outside, 'src/main change outside the 17 modified (+ optional NtmItemModelProvider) and 16 new Java files, the 23 resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal24C takes no new snapshot)'
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

    # Production Java facts: insert-only registration files and every line edit counted.
    insert_summary, edit_summary, inserted_lines, added_lines, removed_lines = {}, {}, {}, {}, {}
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
    # Language provider: the added lines carry exactly the 12 new keys (blocks through constants, plain keys); nothing is removed.
    provider_added = []
    if PROVIDER in added_lines:
        keys_added, other = provider_keys(added_lines[PROVIDER])
        provider_added = sorted(keys_added)
        stray = [l for l in other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} adds lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(keys_added) == len(set(keys_added)), f'{PROVIDER} adds a language key twice')
        need(provider_added == sorted(KEYS), f'{PROVIDER} adds the language keys differently than expected: missing {sorted(set(KEYS) - set(provider_added))[:6]}, unexpected {sorted(set(provider_added) - set(KEYS))[:6]}')
        need(not provider_keys(removed_lines[PROVIDER])[0], f'{PROVIDER} removes language entries: {provider_keys(removed_lines[PROVIDER])[0][:4]}')
    # The original, parsed from the stored blobs at the recorded commit (independent of the worktree's line endings).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    # NEO constants against the original: dial defaults, flux and heat constants, gates, corium, stream directions and the tick hooks.
    reactor_constants, constants_bad = {}, []
    for cid, (o_path, o_regex, n_path, n_regex, expected) in CONSTANTS.items():
        o_values = captured(original_text(o_path), o_regex)
        n_values = captured((ROOT/n_path).read_text(encoding='utf-8').replace('\r\n', '\n'), n_regex) if (ROOT/n_path).is_file() else None
        assert o_values == [normalize_value(str(e)) if not isinstance(e, str) else e for e in expected] or o_values == expected, \
            f'The original constant {cid} ({o_path}) is {o_values}, the owner table expects {expected}'
        reactor_constants[cid] = dict(original=o_values, neo=n_values, original_path=o_path, neo_path=n_path)
        if n_values != o_values: constants_bad.append(cid)
    o_dirs = direction_names(original_text(O_ROD_TILE), r'fluxDirs = new ForgeDirection\[\] \{(.*?)\};')
    n_dirs = direction_names((ROOT/ROD_BE).read_text(encoding='utf-8'), r'fluxDirs = new Direction\[\] \{(.*?)\};') if (ROOT/ROD_BE).is_file() else None
    assert o_dirs == STREAM_DIRECTIONS, 'The original stream directions differ from the owner table: '+str(o_dirs)
    reactor_constants['stream_directions'] = dict(original=o_dirs, neo=n_dirs, original_path=O_ROD_TILE, neo_path=ROD_BE)
    if n_dirs != o_dirs: constants_bad.append('stream_directions')
    need(not constants_bad and all(c['neo'] is not None for c in reactor_constants.values()),
         f'NEO constants differ from the original (or the NEO source is missing): {sorted(set(constants_bad) | {k for k, c in reactor_constants.items() if c["neo"] is None})}')
    event_text = (ROOT/EVENT_HANDLER).read_text(encoding='utf-8').replace('\r\n', '\n')
    hooks = {h: event_text.count(h) for h in EVENT_HOOKS}
    need(all(n == 1 for n in hooks.values()), f'{EVENT_HANDLER} does not call each of {EVENT_HOOKS} exactly once: {hooks}')
    # Imported resources: byte for byte equal to the original worktree file and, up to line endings (OBJ) or exactly (PNG, mcmeta), its stored blob, and to the ownership record.
    imported = {}
    ownership = None
    if need((ROOT/RESOURCE_OWNERSHIP).is_file(), 'record missing: '+RESOURCE_OWNERSHIP):
        ownership = read(ROOT/RESOURCE_OWNERSHIP)
        entries = {a.get('target_path'): a for a in ownership.get('assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(ASSETS), f'{RESOURCE_OWNERSHIP} does not list the {len(ASSETS)} resources at {SOURCE_HEAD[:8]}')
        need(all(entries.get(t, {}).get('source_path') == o for t, o in ASSETS.items()), f'{RESOURCE_OWNERSHIP} source paths differ from the layout rules of the owner table')
    for target, original in ASSETS.items():
        assert (SOURCE/original).is_file(), 'Original resource missing: '+original
        if not (ROOT/target).is_file(): continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        entry = {a.get('target_path'): a for a in (ownership or {}).get('assets', [])}.get(target, {})
        imported[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size,
                                original_worktree_sha256=sha(SOURCE/original), original_blob_sha256=hashlib.sha256(blob).hexdigest(), original_blob_bytes=len(blob),
                                line_endings_converted_from_blob=blob != checked_out, source_last_change_commit=entry.get('source_last_change_commit'))
        need((ROOT/target).read_bytes() == checked_out, f'{target} is not byte-identical to the original worktree file {original}')
        if target.endswith('.obj'):
            # The original worktree is clean at SOURCE_HEAD, so its OBJ is the checked-out original; on this Windows checkout it carries CRLF where the stored blob
            # has LF (autocrlf). The blob must match up to that line-ending conversion, and the ownership record's blob fields must say so (goal24a precedent).
            normalized = (ROOT/target).read_bytes().replace(b'\r\n', b'\n')
            need(blob.replace(b'\r\n', b'\n') == normalized, f'{target} differs from the {SOURCE_HEAD[:8]} blob of {original} beyond line endings')
            if entry:
                need(entry.get('blob_sha256') == hashlib.sha256(blob).hexdigest() and entry.get('blob_bytes') == len(blob) and entry.get('normalized_sha256') == hashlib.sha256(normalized).hexdigest()
                     and entry.get('normalized_equal_to_blob') is True and entry.get('worktree_crlf_lines') == (ROOT/target).read_bytes().count(b'\r\n'),
                     f'{RESOURCE_OWNERSHIP} blob / CRLF fields differ from the stored blob or the live OBJ: {target}')
        else:
            need(checked_out == blob, f'{target} is not byte-identical to the stored blob of {original} at {SOURCE_HEAD[:8]}')
        if entry:
            need(entry.get('source_path') == original and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('bytes') == (ROOT/target).stat().st_size,
                 f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original path: {target}')
    # features.json: the new rbmk-reactor group, the unchanged status and reviewed_source_commit of the 53 previous groups.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert FEATURE_FUEL in start_features and FEATURE_GROUP not in start_features, 'The start mapping does not hold rbmk-fuel (24B) and not yet rbmk-reactor'

    # 4. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_delta = dict(added=sorted(KEYS), removed=[], changed=[])
    need(en_delta == expected_delta, f'generated en_us.json delta is not the {len(KEYS)} new keys (no value changed): '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_delta, f'zh_cn.json delta is not the {len(KEYS)} new keys (all old keys unchanged): '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_delta, f'zh_cn-map.json delta is not the {len(KEYS)} new keys (all old entries unchanged): '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal24b totals {totals} + {len(KEYS)}')
    language_kinds, original_text_checked = {}, False
    if map_delta == expected_delta and en_delta == expected_delta:
        language_kinds = dict(Counter(map_now[k].get('kind') for k in KEYS))
        need(language_kinds == EXPECTED_KINDS, f'zh_cn-map.json kinds of the new entries are {language_kinds}, expected {EXPECTED_KINDS}')
        o_en, o_zh = lang_file(O_LANG_EN), lang_file(O_LANG_ZH)
        bad = []
        for k, source_key in KEYS.items():
            e = map_now[k]
            if e.get('target_en') != en_now.get(k) or e.get('target_zh') != zh_now.get(k): bad.append(k)
            elif source_key is None:
                # The $ line breaks of the two hover lines must survive in the Chinese text.
                if e.get('kind') != 'local' or not e.get('reason') or not zh_now[k] or en_now[k].count('$') != zh_now[k].count('$'): bad.append(k)
            elif e.get('kind') != 'upstream' or e.get('source_key') != source_key or e.get('source_zh') != e.get('target_zh') or e.get('source_en') != e.get('target_en'): bad.append(k)
            elif e.get('source_en') != o_en.get(source_key) or e.get('source_zh') != o_zh.get(source_key): bad.append(k)
        need(not bad, 'zh_cn-map.json entries do not match en_us.json / zh_cn.json, the original en_US.lang / zh_CN.lang values at aee05a40f or the expected kinds: '+str(bad[:8]))
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal24b generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected blockstate, model, loot table, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, the pickaxe tag and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # Recipes: the rbmk_rod crafting recipe (computed from the generated JSON) against the original row; rbmk_rod_mod and the anvil rows are not registered.
    o_crafting = original_text(O_CRAFTING)
    o_row = original_shaped_block(o_crafting, 'rbmk_rod', 1)
    assert o_row is not None and all(v is not None for v in o_row['key'].values()), f'The original rbmk_rod row could not be parsed or translated: {o_row}'
    assert original_shaped_block(o_crafting, 'rbmk_rod_mod', 1) is not None, 'The original rbmk_rod_mod row is gone (the owner table records it as not registered)'
    o_anvil = original_text(O_ANVIL)
    assert 'ComparableStack(ModBlocks.rbmk_rod)' in o_anvil and 'ComparableStack(ModBlocks.rbmk_rod_mod)' in o_anvil, 'The original anvil recycling rows of rbmk_rod / rbmk_rod_mod are gone'
    crafting = {}
    recipe_path = ROOT/GENERATED_ROOT/'data/hbmsntm/recipe/rbmk_rod.json'
    if recipe_path.is_file():
        data = read(recipe_path)
        neo_row = dict(pattern=data.get('pattern'), key=data.get('key'), result=data.get('result'))
        crafting['rbmk_rod'] = dict(type=data.get('type'), neo=neo_row, original=o_row)
        need(data.get('type') == 'minecraft:crafting_shaped' and neo_row == o_row, f'{recipe_path.relative_to(ROOT).as_posix()} differs from the original CraftingManager row: {neo_row} vs {o_row}')
    else:
        need(False, 'generated recipe missing: '+recipe_path.relative_to(ROOT).as_posix())
    mod_recipes = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/GENERATED_ROOT/'data/hbmsntm').rglob('*rbmk_rod_mod*') if 'recipe' in p.relative_to(ROOT).as_posix())
    need(not mod_recipes, f'a recipe or advancement for rbmk_rod_mod is registered (the owner table leaves it out: no graphite block in NEO): {mod_recipes}')
    # Mapped paths: every changed path inside the compare inventory must be matched by a feature group.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    if need(FEATURE_GROUP in by_id, 'migration/features.json has no group '+FEATURE_GROUP):
        group_entry = by_id[FEATURE_GROUP]
        need(group_entry.get('status') == 'partial-unverified' and group_entry.get('reviewed_source_commit') == SOURCE_HEAD,
             f'features.json group {FEATURE_GROUP} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in FEATURE_SOURCES + list(ASSETS.values()) if not feature_matches(group_entry, 'source', p)]
        need(not missing_source, f'features.json group {FEATURE_GROUP} lists in neither source_paths nor source_watch: {missing_source[:4]} ({len(missing_source)} paths)')
        missing_target = [p for p in NEW_JAVA if not feature_matches(group_entry, 'target', p)]
        need(not missing_target, f'features.json group {FEATURE_GROUP} lacks the new classes in target_paths/target_watch: {missing_target}')
        watch = list(ASSETS) + [GENERATED_ROOT+p for p in EXPECTED_GENERATED] + [NEW_TOOLS[0]]
        missing_watch = [p for p in watch if not feature_matches(group_entry, 'target', p)]
        need(not missing_watch, f'features.json group {FEATURE_GROUP} lacks the resources, the generated blockstates / models / loot tables / recipe or the verifier in target_watch: {missing_watch[:4]} ({len(missing_watch)} paths)')
        absent = [p for p in group_entry.get('source_paths', []) if not (SOURCE/p).is_file()]
        need(not absent, f'features.json group {FEATURE_GROUP} source_paths missing in the original: {absent}')
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
        if rel in base['files']: total_start += annotations(START_FILES/rel if base['files'][rel] != sha(p) and (START_FILES/rel).is_file() else p)
    assert total_start == prior_receipt['gametest']['tests'], 'The start GameTest sources do not hold the previous count of '+str(prior_receipt['gametest']['tests'])
    gametest_added = total_now - total_start
    gametest_expected = total_now
    reactor_test_names = sorted(GAMETEST_METHOD.findall((ROOT/REACTOR_TESTS).read_text(encoding='utf-8'))) if (ROOT/REACTOR_TESTS).is_file() else []
    reactor_annotations = annotations(ROOT/REACTOR_TESTS) if (ROOT/REACTOR_TESTS).is_file() else 0
    need(bool(reactor_test_names) and reactor_annotations == len(reactor_test_names), f'{REACTOR_TESTS} holds {reactor_annotations} @GameTest annotations and {len(reactor_test_names)} parsed methods')
    need(gametest_added == reactor_annotations, f'GameTest sources grew by {gametest_added} tests, RBMKReactorGameTests holds {reactor_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in reactor_test_names), 'GameTest log lacks "[hbm-rbmk-reactor] <name> passed" for: '+str([n for n in reactor_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24c/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24c/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal24c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal24c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal24c/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA + OPTIONAL_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal24c/production-vs-start.diff') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal24b final run plus the Goal24C verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal24b final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal24C suite is already in the goal24b final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal24c/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal24b final set + the Goal24C verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal24c/'+VERIFY_REPORT+' (tools/migration/verify_goal24c_rbmk_reactor.py report)'):
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
        verifier_references = sorted(set(re.findall(r'(?:NeutronHandler|NeutronNodeWorld|NeutronNode|NeutronStream|RBMKNeutronHandler|TileEntityRBMK\w+|RBMKRod|RBMKDials|IRBMK\w+|ContainerRBMKRod|'
                                                      r'GUIRBMKRod|CoriumFinite|CraftingManager|AnvilRecipes|ModEventHandler)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the Goal24B compare paths plus this batch's compare-inventory paths).
    cmp24b = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal24b/compare.json differs from the goal24b receipt'
    c24b_added = sorted(p for p in compare_paths(cmp24b['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c24b_modified = sorted(p for p in compare_paths(cmp24b['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(c24b_added) | set(c24b_modified) | set(own_target))
    expected_added = sorted(set(c24b_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal24c/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24b paths + %d of this batch)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(c24b_added) + len(c24b_modified), len(own_target))):
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
        need(any(f.get('id') == FEATURE_GROUP and f.get('state') == 'target-changed' for f in cmp['features']), f'{COMPARE} does not report {FEATURE_GROUP} as target-changed')
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: [OWNER] for p in listed},
                       goal24b_paths=len(c24b_added) + len(c24b_modified), goal24c_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the rbmk-fuel group 24B added.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - {FEATURE_FUEL}, SNAPSHOT+' does not hold the 52 mapping groups of the end of 24A (the start ids without rbmk-fuel)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal24c.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal24b) package (run build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 23 resources and every compiled class equal the sources.
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [e for e, t in asset_entries.items() if e not in names or not (ROOT/t).is_file() or jar.read(e) != (ROOT/t).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json, the imported resources or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
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
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY, TAG_ENTRY): owner = [OWNER]
                elif kind == 'added' and (n in asset_entries or n in generated_entries): owner = [OWNER]
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 23 imported resources, the generated additions and the modified '
             'en_us.json / zh_cn.json / pickaxe tag are owned; META-INF/MANIFEST.MF is not): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA),
             'Changed Java sources and goal24c JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, TAG_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + pickaxe tag + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            if p in NO_CLASS_JAVA: continue
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for inner in ('com/hbm/handler/neutron/NeutronNodeWorld$StreamWorld.class', 'com/hbm/handler/neutron/RBMKNeutronHandler$RBMKNeutronNode.class',
                      'com/hbm/handler/neutron/RBMKNeutronHandler$RBMKNeutronStream.class'):
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
    # Informational (not a pending item): top-level OUT files no evidence list indexes, for the main agent to extend REVIEW_EVIDENCE with.
    indexed = {Path(p).relative_to(OUT.relative_to(ROOT)).as_posix() for p in evidence if p.startswith(OUT.relative_to(ROOT).as_posix()+'/')}
    unindexed = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in indexed and p.name != 'baseline.json')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added),
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal24b_start=sorted(repinned),
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                   insert_lines=insert_summary, edit_counts=edit_summary, reactor_constants={k: c['neo'] == c['original'] for k, c in reactor_constants.items()},
                   event_hooks=hooks, crafting_recipes=len(crafting), gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_reactor_tests=reactor_test_names, final_suites_expected=final_expected,
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
    rbmk_reactor = dict(neo=[NEUTRON_HANDLER, NODE_WORLD, NEUTRON_NODE, NEUTRON_STREAM, RBMK_HANDLER, PACKAGE_INFO, LOADABLE, SLOTTED, ROD_BE, ROD_BLOCK, CORIUM, ROD_MENU, ROD_SCREEN,
                            ROD_RENDERER, BAKED_MODEL, FLUX_RECEIVER, BASE_BE, EVENT_HANDLER], original=[p for p in O_SOURCES],
                        constants=reactor_constants, event_hooks=hooks, original_references=original_refs,
                        defaults=dict(flux_range=5, moderator_efficiency=1.0, absorber_efficiency=1.0, reflector_efficiency=1.0, absorber_heat_conversion=0.05, disable_meltdowns=False),
                        note='The neutron handler ticks once per server tick after the existing NtmEventHandler work (original NeutronHandler on ServerTickEvent START) and clears a '
                             'level\'s streams and node cache on LevelEvent.Unload (original ModEventHandler.onUnload) and all levels on ServerStoppedEvent (NEO-only). Each fuel column '
                             'spreads four neutron streams (N/E/S/W) over the flux range 5; unlidded columns and stream hits add 5 % of the flux to the chunk radiation; '
                             'fluxFromType SLOW = slow + 0.5 fast, FAST = fast + 0.3 slow; manual removal needs hull <= 200 °C, an autoloader <= 1,000 °C; a column melts down above '
                             '1,500 °C (maxHeat) or when broken with its rod\'s hull at 1,500 °C or more; the column heat is clamped to 10,000; the block entity syncs within 25 '
                             'blocks; the node cache is cleared every 20 ticks; corium sets the standing entity on fire for 3 s, deals 2 radiation damage and adds 1 radiation '
                             'contamination. Not migrated: PileNeutronHandler, ReaSim fuel channels, control rods and the moderated-channel recipe.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), language_kinds, len(ASSETS), len(reactor_test_names), gametest_expected),
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
                                           'Goal24A and Goal24B deliveries (655 status entries; the goal24a and goal24b packages, not committed by decision 2); no pending small fix; '
                                           'build/libs at the start is the goal24b package byte for byte. The original did not move since 24A. Four start copies (RenderRBMKLid, '
                                           'NtmBlockLootTableProvider, NtmBlockTagProvider, NtmGeometry) were added to baseline-files after the freeze, before any 24C edit (freeze.log '
                                           'supplement); their bytes equal the baseline hashes. Paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, start_copies_supplement=supplement,
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   rbmk_reactor=rbmk_reactor,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note='10 entries are upstream (the three block names, container.rbmkRod and the six tile.rbmk.dodd.* diagnostic labels, English and Chinese verbatim from '
                                      'en_US.lang / zh_CN.lang); 2 are NEO-local (the two hover lines of GUIRBMKRod, hard-coded English in the original, with $ as the line break). '
                                      'No existing key changes its value.'),
                   recipes=dict(crafting=crafting, not_registered=['rbmk_rod_mod', 'anvil recycling row rbmk_rod -> rbmk_blank + 2 steel shells',
                                                                   'anvil recycling row rbmk_rod_mod -> rbmk_rod + 4 graphite blocks + 4 bismuth nuggets'],
                                original_references={k: v for k, v in original_refs.items() if k.startswith(('recipe_', 'anvil_'))},
                                anvil_recipes_unchanged=sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES],
                                note='The shaped recipe rbmk_rod (C/R/C: steel shell above and below an rbmk_blank) equals the original CraftingManager row (CraftingManager.java:991). '
                                     'rbmk_rod_mod (CraftingManager.java:992) needs a graphite block NEO does not have (24A precedent); the AnvilRecipes rows (:927-953) are tier-4 recycling '
                                     'rows (unreachable, 24A precedent); both stay unregistered.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report, repinned_since_goal22d_start=prior_receipt['repinned_since_goal22d_start'],
                   repinned_since_goal23a_start=prior_receipt['repinned_since_goal23a_start'], repinned_since_goal23b_start=prior_receipt['repinned_since_goal23b_start'],
                   repinned_since_goal23c_start=prior_receipt['repinned_since_goal23c_start'], repinned_since_goal24a_start=prior_receipt['repinned_since_goal24a_start'],
                   repinned_since_goal24b_start={p: dict(goal24b_start_pin_sha256=h, goal24c_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_reactor_tests=reactor_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per RBMKReactorGameTests test: the neutron '
                                      'nodespace and streams, fuel-column ignition, range and blocking, lids, flux types, the meltdown into corium, the manual-removal gate, the NBT '
                                      'round trip, IRBMKLoadable, corium_block and the rbmk_rod recipe; no client (the fuel-column model, rod / Cherenkov / lid rendering, item renderer, '
                                      'screen and its English / Chinese readouts are not rendered), no real player, no saved world, no survival reactor build.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier '
                            'with in-memory mutations, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and an independent and a '
                            'redundant static review. No in-game client test was run: the fuel-column model, rod / Cherenkov / lid rendering, the item renderer, the screen and its '
                            'English and Chinese readouts are unverified; no survival reactor build or real meltdown in a world was run; no multiplayer or dedicated server beyond '
                            'GameTest; level-unload and server-stop cache cleanup are only statically reviewed; GOAL24C-ACCEPTANCE.md is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, start_jar_sha), 'build/libs JAR is an older JAR'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal24c JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal24b package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
