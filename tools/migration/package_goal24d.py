"""Package Goal24D (RBMK control rods and the steam side, no console yet: the control columns rbmk_control, rbmk_control_mod and rbmk_control_auto (RBMKControlBlockEntity,
RBMKControlManualBlockEntity, RBMKControlAutoBlockEntity, RBMKPipedBaseBlock, RBMKControlBlock, RBMKControlAutoBlock, two menus and screens with server-validated control
packets, RenderRBMKPiped and RenderRBMKControl) and the CONTROL_ROD branch of RBMKNeutronHandler; the steam channel rbmk_boiler, the fluid heater rbmk_heater, the cooler
rbmk_cooler and the fluid connector rbmk_loader with their fluid ports, menus, screens and the RBMKSteamParticle, and the port helper and the meltdown overpressure branch of
RBMKBaseBlockEntity; six crafting recipes; 46 imported resources; 59 language keys; RBMKControlSteamGameTests) cumulatively on the goal24c package, without replacing any
previous delivery.

python -B -X utf8 tools/migration/package_goal24d.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal24d/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal24d/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal24d/baseline.json: NEO HEAD 1114adf5 (the Goal 24 planning commit on top of the pushed Goal 23 close-out commit 09173669)
with the UNCOMMITTED Goal24A, Goal24B and Goal24C deliveries (690 default status entries). The original HEAD aee05a40f did not move since 24A, so there is no upstream
classification and no new snapshot. build/libs at the start is the goal24c package byte for byte. Every change since the start is computed from the baseline file
hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with
their start bytes (baseline-files holds all 40 scope copies). The JAR delta against the goal24c package is attributed per entry (goal24d); any entry without exactly one
owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys) are computed here, never hard-coded; the previous
package's SHA-256, size and receipt hashes are read from the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal24b, the review-g21d-hazard-fix receipt) already differ from their older hashes at the frozen start for the acceptance
checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes build/migration/goal24a/main-notes.md (baseline older_receipt_evidence_drift;
the goal24a receipt hashed main-notes.md before the 24A session appended its "Delivered" section, the goal24b and goal24c receipts hash it at its current hash). They
are listed in the receipt as start drift and must still equal their Goal24D start hash; no receipt is rewritten and no other protected path may drift. The goal24c
receipt has no drift of its own at the start (baseline previous_receipt_evidence_drift is empty).

Like the Goal24C packager this one has a single compare run (build/migration/goal24d/compare.json against the snapshot review-aee05a40f10f.json taken at the end of
24A: original 0/0/0, target = exactly the Goal24C compare-inventory paths (read from build/migration/goal24c/compare.json, which already holds the 24B paths) plus this
batch's), no upstream classification and no rbmk_reactor constants; it adds the rbmk_control_steam constants (checked against the original and NEO source texts)."""
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
from package_goal24c import (OUT as GOAL24C_OUT, BASELINE as GOAL24C_BASELINE, protected_paths as goal24c_protected_paths, normalize_value, captured, direction_names)

OUT = ROOT/'build/migration/goal24d'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL24C_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL24C_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal24c/hbmsntm-198A-goal24c.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal24d'
RELEASE_NAME = 'hbmsntm-198A-goal24d.jar'
OWNER = 'goal24d'
PLANNING_PREFIX = '1114adf5'
GOAL23_CLOSEOUT = '09173669'
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
START_STATUS_ENTRIES = 690
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
CONFIG = J+'config/CommonConfig.java'

# Production (owner goal24d), NEW (handoff-packaging.md; builder-a-progress.md / builder-b-progress.md name the final classes: if package B names a class differently or adds
# a helper class, edit this list, --check reports the difference as an unassigned src/ path).
NEW_JAVA = [J+p+'.java' for p in (
    'blockentity/machine/rbmk/RBMKControlBlockEntity', 'blockentity/machine/rbmk/RBMKControlManualBlockEntity', 'blockentity/machine/rbmk/RBMKControlAutoBlockEntity',
    'blockentity/machine/rbmk/RBMKBoilerBlockEntity', 'blockentity/machine/rbmk/RBMKHeaterBlockEntity', 'blockentity/machine/rbmk/RBMKCoolerBlockEntity',
    'blocks/machine/rbmk/RBMKPipedBaseBlock', 'blocks/machine/rbmk/RBMKControlBlock', 'blocks/machine/rbmk/RBMKControlAutoBlock', 'blocks/machine/rbmk/RBMKBoilerBlock',
    'blocks/machine/rbmk/RBMKHeaterBlock', 'blocks/machine/rbmk/RBMKCoolerBlock', 'blocks/machine/rbmk/RBMKLoaderBlock',
    'inventory/menus/RBMKControlMenu', 'inventory/menus/RBMKControlAutoMenu', 'inventory/menus/RBMKBoilerMenu', 'inventory/menus/RBMKHeaterMenu',
    'inventory/screens/RBMKControlScreen', 'inventory/screens/RBMKControlAutoScreen', 'inventory/screens/RBMKBoilerScreen', 'inventory/screens/RBMKHeaterScreen',
    'render/blockentity/RenderRBMKPiped', 'render/blockentity/RenderRBMKControl', 'particle/RBMKSteamParticle', 'gametest/RBMKControlSteamGameTests')]
(CONTROL_BE, MANUAL_BE, AUTO_BE, BOILER_BE, HEATER_BE, COOLER_BE, PIPED_BLOCK, CONTROL_BLOCK, AUTO_BLOCK, BOILER_BLOCK, HEATER_BLOCK, COOLER_BLOCK, LOADER_BLOCK,
 CONTROL_MENU, AUTO_MENU, BOILER_MENU, HEATER_MENU, CONTROL_SCREEN, AUTO_SCREEN, BOILER_SCREEN, HEATER_SCREEN, PIPED_RENDERER, CONTROL_RENDERER, STEAM_PARTICLE,
 CONTROL_STEAM_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'handler/neutron/RBMKNeutronHandler', 'blockentity/machine/rbmk/RBMKBaseBlockEntity', 'blocks/machine/rbmk/RBMKBaseBlock', 'blocks/NtmBlocks', 'blockentity/NtmBlockEntityTypes',
    'inventory/NtmMenuTypes', 'main/NuclearTechModClient', 'main/ClientProxy', 'main/ResourceManager', 'inventory/NtmCreativeTabs', 'datagen/NtmBlockStateProvider',
    'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmLanguageProvider', 'datagen/NtmRecipeProvider')]
(RBMK_HANDLER, BASE_BE, BASE_BLOCK, BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, CLIENT, CLIENT_PROXY, RESOURCE_MANAGER, CREATIVE_TABS, BLOCK_STATE_PROVIDER,
 LOOT_PROVIDER, TAG_PROVIDER, PROVIDER, RECIPE_PROVIDER) = MODIFIED_JAVA
# The handoff expected NtmItemModelProvider to change if needed; builder-a-progress.md says it did not (simpleBlockWithItem writes the item model of the cube columns).
# It may change, it is not required to.
ITEM_MODEL_PROVIDER = J+'datagen/NtmItemModelProvider.java'
OPTIONAL_JAVA = [ITEM_MODEL_PROVIDER]
# No new package-info and no comment-only edit in this batch: every new Java source compiles to a class and every modified source changes a class file.
NO_CLASS_JAVA = []
SAME_CLASS_JAVA = []
ANVIL_RECIPES = J+'inventory/recipes/anvil/AnvilRecipes.java'
# Registration and datagen files that must stay insert-only against their start bytes. The other modified files carry edits by design: RBMKBaseBlockEntity (the 24A overpressure
# hook becomes collectOverpressurePipes / handleOverpressure(Set)), RBMKBaseBlock (hasOwnLid in getCollisionShape), RBMKNeutronHandler (the two 24C CONTROL_ROD placeholder
# comments become the original branches), NtmBlockStateProvider (the column array), NtmRecipeProvider (the rbmk_control placeholder comment).
STRICT_INSERT_ONLY = [BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, CLIENT, CLIENT_PROXY, RESOURCE_MANAGER, CREATIVE_TABS, LOOT_PROVIDER, TAG_PROVIDER, PROVIDER, ITEM_MODEL_PROVIDER, ZH_INPUT]
# For the non-strict files every removed start line must be a comment line or start with one of these (stripped) code prefixes; the removed comments are listed in the receipt.
ALLOWED_REMOVED_CODE = {
    BASE_BE: ('if(RBMKDials.getOverpressure())', 'handleOverpressure();', 'protected void handleOverpressure() { }'),
    BASE_BLOCK: ('return this.getLid(level, pos) != LidType.NONE ? LID_SHAPE : Shapes.block();',),
    RBMK_HANDLER: ('else if(type == RBMKType.REFLECTOR) {',),
    BLOCK_STATE_PROVIDER: ('for(DeferredBlock<? extends Block> column : new DeferredBlock[] {NtmBlocks.RBMK_BLANK',),
    RECIPE_PROVIDER: (),
}
# The 46 imported original resources: NEO target -> original path, derived by the layout rules of the ownership record (textures/block -> textures/blocks, models/obj/rbmk ->
# models/rbmk, the GUI textures keep their path). 21 belong to package A (control rods), 25 to package B (steam channel, heater, cooler, loader).
_COLUMN_PARTS = ('side', 'top', 'pipe_side', 'pipe_top')
_LID_PARTS = ('cover_top', 'cover_side', 'glass_top', 'glass_side')
ASSETS = {ASSETS_ROOT+f'textures/block/rbmk/{n}_{p}.png': O_RES+f'textures/blocks/rbmk/{n}_{p}.png'
          for n in ('rbmk_control', 'rbmk_control_mod', 'rbmk_control_auto') for p in _COLUMN_PARTS}
ASSETS.update({ASSETS_ROOT+f'textures/block/rbmk/{n}.png': O_RES+f'textures/blocks/rbmk/{n}.png'
               for n in ('rbmk_control_auto', 'rbmk_control_red', 'rbmk_control_yellow', 'rbmk_control_green', 'rbmk_control_blue', 'rbmk_control_purple')})
ASSETS[ASSETS_ROOT+'models/obj/rbmk/rbmk_rods.obj'] = O_RES+'models/rbmk/rbmk_rods.obj'
ASSETS.update({ASSETS_ROOT+f'textures/gui/reactors/{n}.png': O_RES+f'textures/gui/reactors/{n}.png' for n in ('gui_rbmk_control', 'gui_rbmk_control_auto')})
A_ASSETS = list(ASSETS)
ASSETS.update({ASSETS_ROOT+f'textures/block/rbmk/{n}_{p}.png': O_RES+f'textures/blocks/rbmk/{n}_{p}.png'
               for n in ('rbmk_boiler', 'rbmk_heater') for p in ('side', 'top', *_LID_PARTS, 'pipe_side', 'pipe_top')})
ASSETS.update({ASSETS_ROOT+f'textures/block/rbmk/rbmk_cooler_{p}.png': O_RES+f'textures/blocks/rbmk/rbmk_cooler_{p}.png' for p in ('side', 'top', *_LID_PARTS)})
ASSETS[ASSETS_ROOT+'textures/block/rbmk_loader.png'] = O_RES+'textures/blocks/rbmk_loader.png'
ASSETS.update({ASSETS_ROOT+f'textures/gui/reactors/{n}.png': O_RES+f'textures/gui/reactors/{n}.png' for n in ('gui_rbmk_boiler', 'gui_rbmk_heater')})
B_ASSETS = [t for t in ASSETS if t not in A_ASSETS]
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
TAG_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
GENERATED = [STAMP, EN, GENERATED_ROOT+TAG_ENTRY]
# Generated by runData for this batch (relative to src/generated/resources): blockstates, block models, item models and loot tables of the seven blocks, the six recipes + advancements.
_BLOCKS = ('rbmk_control', 'rbmk_control_mod', 'rbmk_control_auto', 'rbmk_boiler', 'rbmk_heater', 'rbmk_cooler', 'rbmk_loader')
_RECIPES = ('rbmk_control', 'rbmk_control_auto', 'rbmk_loader', 'rbmk_boiler', 'rbmk_heater', 'rbmk_cooler')
EXPECTED_GENERATED = sorted([f'assets/hbmsntm/{kind}/{b}.json' for kind in ('blockstates', 'models/block', 'models/item') for b in _BLOCKS]
                            + [f'data/hbmsntm/loot_table/blocks/{b}.json' for b in _BLOCKS]
                            + [f'data/hbmsntm/recipe/{r}.json' for r in _RECIPES] + [f'data/hbmsntm/advancement/recipes/misc/{r}.json' for r in _RECIPES])
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, TAG_ENTRY])
NEW_TOOLS = ['tools/migration/verify_goal24d_rbmk_control_steam.py', 'tools/migration/package_goal24d.py']
TOOLS = NEW_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal24d-* or GOAL24D-* record is hashed as well.
REPORTS = ['migration/GOAL24D.md', 'migration/GOAL24D-ACCEPTANCE.md', 'migration/goal24d-static-review.md', 'migration/goal24d-localization-review.json',
           'migration/goal24d-resource-ownership.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal24d-[^/]+\.(json|md)|GOAL24D-[^/]+\.md)')
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/GOAL24.md']
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + SHARED_RECORDS
# The 59 new language keys: NEO key -> original key (None: a NEO-local key). Package A: 21 upstream + 12 local (the auto-rod GUI's hard-coded English, GUIRBMKControlAuto.java:170-187);
# package B: 26 upstream.
KEYS = {'block.hbmsntm.rbmk_control': 'tile.rbmk_control.name', 'block.hbmsntm.rbmk_control_mod': 'tile.rbmk_control_mod.name', 'block.hbmsntm.rbmk_control_auto': 'tile.rbmk_control_auto.name',
        'container.rbmkControl': 'container.rbmkControl', 'container.rbmkControlAuto': 'container.rbmkControlAuto'}
KEYS.update({'rbmk.control.'+t: 'rbmk.control.'+t for t in ('level', 'red', 'yellow', 'green', 'blue', 'purple')})
KEYS.update({'tile.rbmk.dodd.'+t: 'tile.rbmk.dodd.'+t for t in ('level', 'targetLevel', 'startingLevel', 'mult', 'color', 'levelLower', 'levelUpper', 'heatLower', 'heatUpper', 'function')})
KEYS.update({'container.rbmkControlAuto.'+t: None for t in ('function', 'linear', 'quadUp', 'quadDown', 'selectLinear', 'selectQuadUp', 'selectQuadDown', 'levelUpper', 'levelLower',
                                                          'heatUpper', 'heatLower', 'save')})
A_KEY_COUNT = len(KEYS)
KEYS.update({'block.hbmsntm.rbmk_boiler': 'tile.rbmk_boiler.name', 'block.hbmsntm.rbmk_heater': 'tile.rbmk_heater.name', 'block.hbmsntm.rbmk_cooler': 'tile.rbmk_cooler.name',
             'block.hbmsntm.rbmk_loader': 'tile.rbmk_loader.name', 'block.hbmsntm.rbmk_loader.desc': 'tile.rbmk_loader.desc',
             'container.rbmkBoiler': 'container.rbmkBoiler', 'container.rbmkHeater': 'container.rbmkHeater'})
KEYS.update({'rbmk.boiler.'+t: 'rbmk.boiler.'+t for t in ('water', 'steam', 'type')})
KEYS.update({'tile.rbmk.dodd.'+t: 'tile.rbmk.dodd.'+t for t in ('feed', 'feed_max', 'feed_type', 'feed_p', 'steam', 'steam_max', 'steam_type', 'steam_p',
                                                                 't0', 't0_max', 't0_type', 't0_p', 't1', 't1_max', 't1_type', 't1_p')})
EXPECTED_KINDS = {'upstream': sum(1 for v in KEYS.values() if v), 'local': sum(1 for v in KEYS.values() if not v)}
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rbmk-cs] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'main-notes.md', 'builder-a-progress.md', 'builder-b-progress.md',
                  'handoff-production-a.md', 'handoff-production-b.md', 'handoff-gametest.md', 'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md',
                  'make_production_diff.py', 'chain.sh')
# Review files under OUT (for example the two independent static reviews' notes or diffs) the main agent names when it knows them; each must exist and is
# indexed by the receipt. Extend this list from the real run (review notes, the builders' and verifiers' progress and scope files, logs ...);
# --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'packaging-progress.md', 'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt',
                   # Main agent, from the real run: builder logs and helpers, scout notes, the review diff, final-chain logs, the rerun and compare checks, the
                   # record drafts and their values, the packager checks.
                   'builder-a-compile-1.log', 'builder-a-compile-2.log', 'builder-a-done.txt', 'builder-b-compile-1.log', 'builder-b-compile-2.log',
                   'builder-b-done.txt', 'builder-b-rundata-1.log', 'builder_a_crlf.py', 'builder_a_lang.py', 'builder_a_resources.py', 'builder_b_diffcheck.py',
                   'builder_b_genhash.py', 'builder_b_lang.py', 'builder_b_resources.py', 'en_us-before-builder-b.json', 'gen-after-builder-b-rundata-1.json',
                   'gen-before-builder-b-rundata-1.json', 'ownership-before-builder-b.json', 'pickaxe-before-builder-b.json', 'stamp-before-builder-b-rundata-1.json',
                   'scout-fluid.md', 'scout-materials.md', 'scout-rbmk.md', 'split_scout.py', 'probe_baseline.py', 'production-diff.patch',
                   'verifier-gt-progress.md', 'verifier-script-progress.md', 'verify-final.log', 'chain-final.out', 'localization-final.log',
                   'packaged-resources-final.log', 'resources-audit-final.log', 'validate-final-before-features.log', 'check_shared_unchanged.py',
                   'main_fix_zh_auto.py', 'make_localization_review.py', 'add_features.py', 'features-notes.json', 'ledger-draft.md', 'compare_fail_sets.py',
                   'compare.log', 'compare-exit.txt', 'delivery-draft.md', 'readme-line.md', 'upstream-entry.md', 'loc-section.md', 'goal24-progress.md',
                   'goal24-progress-tail.md', 'apply_records.py', 'record-values.json', 'package-check-1.log', 'package-check-2.log')
GAMETEST_LOG = 'build/migration/goal24d/gametest-final.log'
NEW_SUITE = 'verify_goal24d_rbmk_control_steam.py --gametest-log build/migration/goal24d/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_CONTROL, FEATURE_STEAM = 'rbmk-control', 'rbmk-steam'
FEATURE_REACTOR, FEATURE_FUEL = 'rbmk-reactor', 'rbmk-fuel'
RADIATION_NOTE = ('Goal24D: control rods throttle RBMK neutron streams (a fully withdrawn rod passes them unchanged); unlidded columns and stream hits still raise chunk '
                  'radiation as in Goal24C; run reactors only in separately authorized disposable worlds. ')
MELTDOWN_NOTE = ('Goal24D: steam channels, heaters, coolers and control columns melt down with the reactor; with dialEnableMeltdownOverpressure enabled (default off) a '
                 'meltdown reaching a steam channel destroys connected steam pipes and explodes the machines on that steam network; only in disposable worlds away from builds. ')
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_RBMK = ORIGINAL+'tileentity/machine/rbmk/'
(O_CONTROL, O_MANUAL, O_AUTO, O_BOILER, O_HEATER, O_COOLER, O_BASE, O_DIALS) = (O_RBMK+n+'.java' for n in (
    'TileEntityRBMKControl', 'TileEntityRBMKControlManual', 'TileEntityRBMKControlAuto', 'TileEntityRBMKBoiler', 'TileEntityRBMKHeater', 'TileEntityRBMKCooler',
    'TileEntityRBMKBase', 'RBMKDials'))
O_BLOCKS = ORIGINAL+'blocks/machine/rbmk/'
(O_BLOCK_CONTROL, O_BLOCK_AUTO, O_PIPED, O_BLOCK_BOILER, O_BLOCK_HEATER, O_BLOCK_COOLER, O_LOADER) = (O_BLOCKS+n+'.java' for n in (
    'RBMKControl', 'RBMKControlAuto', 'RBMKPipedBase', 'RBMKBoiler', 'RBMKHeater', 'RBMKCooler', 'RBMKLoader'))
(O_GUI_CONTROL, O_GUI_AUTO, O_GUI_BOILER, O_GUI_HEATER) = (ORIGINAL+'inventory/gui/'+n+'.java' for n in ('GUIRBMKControl', 'GUIRBMKControlAuto', 'GUIRBMKBoiler', 'GUIRBMKHeater'))
(O_CONT_CONTROL, O_CONT_AUTO, O_CONT_GENERIC, O_CONT_HEATER) = (ORIGINAL+'inventory/container/'+n+'.java' for n in (
    'ContainerRBMKControl', 'ContainerRBMKControlAuto', 'ContainerRBMKGeneric', 'ContainerRBMKHeater'))
O_ROD_RENDERER = ORIGINAL+'render/tileentity/RenderRBMKControlRod.java'
O_BLOCK_RENDERER = ORIGINAL+'render/block/RenderRBMKControl.java'
O_PARTICLE = ORIGINAL+'particle/ParticleRBMKSteam.java'
O_RBMK_HANDLER = ORIGINAL+'handler/neutron/RBMKNeutronHandler.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_ANVIL = ORIGINAL+'inventory/recipes/anvil/AnvilRecipes.java'
O_CLIENT_PROXY = ORIGINAL+'main/ClientProxy.java'
O_SOURCES = [O_CONTROL, O_MANUAL, O_AUTO, O_BOILER, O_HEATER, O_COOLER, O_BASE, O_DIALS, O_BLOCK_CONTROL, O_BLOCK_AUTO, O_PIPED, O_BLOCK_BOILER, O_BLOCK_HEATER, O_BLOCK_COOLER,
             O_LOADER, O_GUI_CONTROL, O_GUI_AUTO, O_GUI_BOILER, O_GUI_HEATER, O_CONT_CONTROL, O_CONT_AUTO, O_CONT_GENERIC, O_CONT_HEATER, O_ROD_RENDERER, O_BLOCK_RENDERER,
             O_PARTICLE, O_RBMK_HANDLER, O_CRAFTING, O_ANVIL, O_CLIENT_PROXY]
# The original sources each new mapping group must list (source_paths or source_watch; the groups together must cover all of them, plus the imported resources).
CONTROL_SOURCES = [O_CONTROL, O_MANUAL, O_AUTO, O_BLOCK_CONTROL, O_BLOCK_AUTO, O_PIPED, O_GUI_CONTROL, O_GUI_AUTO, O_CONT_CONTROL, O_CONT_AUTO, O_ROD_RENDERER, O_BLOCK_RENDERER]
STEAM_SOURCES = [O_BOILER, O_HEATER, O_COOLER, O_BLOCK_BOILER, O_BLOCK_HEATER, O_BLOCK_COOLER, O_LOADER, O_GUI_BOILER, O_GUI_HEATER, O_CONT_GENERIC, O_CONT_HEATER, O_PARTICLE]
FEATURE_SOURCES = CONTROL_SOURCES + STEAM_SOURCES
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'control_speed': (O_CONTROL, 'public static final double speed'), 'control_update': (O_CONTROL, 'public void updateEntity()'),
    'control_lid_removable': (O_CONTROL, 'public boolean isLidRemovable()'), 'control_get_mult': (O_CONTROL, 'public double getMult()'), 'control_melt': (O_CONTROL, 'public void onMelt('),
    'manual_get_mult': (O_MANUAL, 'public double getMult()'), 'manual_set_target': (O_MANUAL, 'public void setTarget('), 'manual_permission': (O_MANUAL, 'public boolean hasPermission('),
    'manual_receive_control': (O_MANUAL, 'public void receiveControl('), 'auto_update': (O_AUTO, 'public void updateEntity()'), 'auto_receive_control': (O_AUTO, 'public void receiveControl('),
    'neutron_control_branch': (O_RBMK_HANDLER, 'type == RBMKType.CONTROL_ROD'), 'neutron_control_tail': (O_RBMK_HANDLER, 'lastNodeType == RBMKType.CONTROL_ROD'),
    'boiler_update': (O_BOILER, 'public void updateEntity()'), 'boiler_heat_from_steam': (O_BOILER, 'public static double getHeatFromSteam('),
    'boiler_factor_from_steam': (O_BOILER, 'public static double getFactorFromSteam('), 'boiler_compressor': (O_BOILER, 'public void cyceCompressor()'),
    'boiler_melt': (O_BOILER, 'public void onMelt('), 'heater_update': (O_HEATER, 'public void updateEntity()'), 'cooler_update': (O_COOLER, 'public void updateEntity()'),
    'base_overpressure': (O_BASE, 'if(RBMKDials.getOverpressure(worldObj) && !pipes.isEmpty())'), 'base_ports_no_loader': (O_BASE, 'public PortDef[] getPortsNoLoader()'),
    'base_ports_close_loader': (O_BASE, 'public PortDef[] getPortsCloseLoader()'), 'base_ports_classic_loader': (O_BASE, 'public PortDef[] getPortsClassicLoader()'),
    'loader_can_connect': (O_LOADER, 'public boolean canConnect('), 'particle_class': (O_PARTICLE, 'public class ParticleRBMKSteam'),
    'proxy_rbmksteam': (O_CLIENT_PROXY, 'if("rbmksteam".equals(type))'),
    'recipe_rbmk_control': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_control, 1)'), 'recipe_rbmk_control_mod': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_control_mod, 1)'),
    'recipe_rbmk_control_auto': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_control_auto, 1)'), 'recipe_rbmk_loader': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_loader, 1)'),
    'recipe_rbmk_boiler': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_boiler, 1)'), 'recipe_rbmk_heater': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_heater, 1)'),
    'recipe_rbmk_cooler': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_cooler, 1)'),
    'anvil_rbmk_control': (O_ANVIL, 'new ComparableStack(ModBlocks.rbmk_control)'), 'anvil_rbmk_control_mod': (O_ANVIL, 'new ComparableStack(ModBlocks.rbmk_control_mod)'),
    'anvil_rbmk_control_auto': (O_ANVIL, 'new ComparableStack(ModBlocks.rbmk_control_auto)'), 'anvil_rbmk_boiler': (O_ANVIL, 'new ComparableStack(ModBlocks.rbmk_boiler)'),
    'anvil_rbmk_cooler': (O_ANVIL, 'new ComparableStack(ModBlocks.rbmk_cooler)'),
}
# Original crafting-manager key expressions -> the NEO ingredient (each generated recipe is compared against the parsed original row). Forms follow the existing generated
# recipes (items by registry name, ANY_PLASTIC.ingot() through the ntm:ingots_plastic tag the 24B screwdriver recipe uses, STEEL.plate() through the c:plates/steel tag
# and CU.ingot() as either copper ingot, as the existing NtmRecipeProvider rows do, for example gear_large).
KEY_TABLE = {'GRAPHITE.ingot()': {'item': 'hbmsntm:ingot_graphite'}, 'ModItems.motor': {'item': 'hbmsntm:motor'}, 'ModBlocks.rbmk_absorber': {'item': 'hbmsntm:rbmk_absorber'},
             'DictFrame.fromOne(ModItems.circuit, EnumCircuitType.ADVANCED)': {'item': 'hbmsntm:circuit_military_grade_board'}, 'ModBlocks.rbmk_control': {'item': 'hbmsntm:rbmk_control'},
             'ModItems.crt_display': {'item': 'hbmsntm:crt_display'}, 'STEEL.plate()': {'tag': 'c:plates/steel'},
             'CU.ingot()': [{'item': 'hbmsntm:ingot_copper'}, {'item': 'minecraft:copper_ingot'}],
             'ModItems.tank_steel': {'item': 'hbmsntm:tank_steel'}, 'CU.pipe()': {'item': 'hbmsntm:pipe_copper'}, 'CU.shell()': {'item': 'hbmsntm:shell_copper'},
             'ModBlocks.rbmk_blank': {'item': 'hbmsntm:rbmk_blank'}, 'STEEL.shell()': {'item': 'hbmsntm:shell_steel'}, 'ANY_PLASTIC.ingot()': {'tag': 'ntm:ingots_plastic'},
             'ModItems.plate_polymer': {'item': 'hbmsntm:plate_polymer'}, 'ModBlocks.steel_grate': {'item': 'hbmsntm:steel_grate'}}
# Constants compared between the original and NEO source texts: id -> (original path, regex, NEO path, regex, expected unique values in order[, expected NEO values when they differ]).
# Numbers are compared as floats (underscores dropped, F / D suffixes dropped), anything else as text. The group-1 value of every match is collected. A NEO regex that finds
# nothing (the class is not written yet, or its text differs from the handoff) is reported as pending with its id.
_DIAL = r'%s\("%s", ([\d.]+)\)'
_NEO_DIAL = r'defineInRange\("%s", ([\d.]+)D?,'
_FLUID_TABLE = r'%s\(FluidType \w+\) \{[^}]*?Fluids\.%s\) return ([\d.]+)D;'
CONSTANTS = {
    'dial_control_speed': (O_DIALS, _DIAL % ('KEY_CONTROL_SPEED_MOD', 'dialControlSpeed'), CONFIG, _NEO_DIAL % 'dialControlSpeed', [1.0]),
    'dial_control_surge_mod': (O_DIALS, _DIAL % ('KEY_SURGE_MOD', 'dialControlSurgeMod'), CONFIG, _NEO_DIAL % 'dialControlSurgeMod', [1.0]),
    'dial_boiler_heat_consumption': (O_DIALS, _DIAL % ('KEY_BOILER_HEAT_CONSUMPTION', 'dialBoilerHeatConsumption'), CONFIG, _NEO_DIAL % 'dialBoilerHeatConsumption', [0.1]),
    'dial_enable_meltdown_overpressure': (O_DIALS, r'KEY_ENABLE_MELTDOWN_OVERPRESSURE\("dialEnableMeltdownOverpressure", (\w+)\)', CONFIG,
                                          r'define\("dialEnableMeltdownOverpressure", (\w+)\)', ['false']),
    'control_speed': (O_CONTROL, r'public static final double speed = ([\d.]+)D;', CONTROL_BE, r'public static final double speed = ([\d.]+)D;', [0.00277]),
    'control_sync_range': (O_CONTROL, r'public int trackingRange\(\) \{\s*return (\d+);', CONTROL_BE, r'public int trackingRange\(\) \{\s*return (\d+);', [100]),
    'control_melt_debris_base': (O_CONTROL, r'int count = (\d+) \+ worldObj\.rand\.nextInt\(\d+\)', CONTROL_BE, r'int count = (\d+) \+ \w+\.random\.nextInt\(\d+\)', [2]),
    'control_melt_debris_random': (O_CONTROL, r'int count = \d+ \+ worldObj\.rand\.nextInt\((\d+)\)', CONTROL_BE, r'int count = \d+ \+ \w+\.random\.nextInt\((\d+)\)', [2]),
    'manual_surge_exponent': (O_MANUAL, r'Math\.pow\(\(1D - this\.level\), (\d+)\)', MANUAL_BE, r'Math\.pow\(\(1D - this\.level\), (\d+)\)', [15]),
    'manual_surge_guard': (O_MANUAL, r'Math\.abs\(this\.level - this\.targetLevel\) > ([\d.]+)D', MANUAL_BE, r'Math\.abs\(this\.level - this\.targetLevel\) > ([\d.]+)D', [0.01]),
    'manual_permission_distance': (O_MANUAL, r'lengthVector\(\) < (\d+)', MANUAL_BE, r'\.length\(\) < (\d+)', [20]),
    'auto_permission_distance': (O_AUTO, r'lengthVector\(\) < (\d+)', AUTO_BE, r'\.length\(\) < (\d+)', [20]),
    'auto_level_scale': (O_AUTO, r'this\.targetLevel = fauxLevel \* ([\d.]+)D;', AUTO_BE, r'this\.targetLevel = fauxLevel \* ([\d.]+)D;', [0.01]),
    'auto_quad_exponent': (O_AUTO, r', (\d+)\) \* \(this\.level', AUTO_BE, r', (\d+)\) \* \(this\.level', [2]),
    'boiler_feed_capacity': (O_BOILER, r'new FluidTank\(Fluids\.WATER, ([\d_]+)\)', BOILER_BE, r'new FluidTank\(Fluids\.WATER, ([\d_]+)\)', [10000]),
    'boiler_steam_capacity': (O_BOILER, r'new FluidTank\(Fluids\.STEAM, ([\d_]+)\)', BOILER_BE, r'new FluidTank\(Fluids\.STEAM, ([\d_]+)\)', [1000000]),
    'boiler_vent_delay_base': (O_BOILER, r'ventDelay = (\d+) \+ ', BOILER_BE, r'ventDelay = (\d+) \+ ', [20]),
    'boiler_vent_delay_random': (O_BOILER, r'ventDelay = \d+ \+ \w+\.rand\.nextInt\((\d+)\)', BOILER_BE, r'ventDelay = \d+ \+ [\w.()]*?nextInt\((\d+)\)', [10]),
    'boiler_compression_guard': (O_BOILER, r'(?:this\.)?heat > (\d+) && (?:this\.)?feed\.getFill\(\) > 0', BOILER_BE, r'(?:this\.)?heat > (\d+) && (?:this\.)?feed\.getFill\(\) > 0', [50]),
    'boiler_compression_divisor': (O_BOILER, r'steam\.setFill\(steam\.getFill\(\) / (\d+)\)', BOILER_BE, r'steam\.setFill\(steam\.getFill\(\) / (\d+)\)', [10]),
    'boiler_decompression_factor': (O_BOILER, r'Math\.min\(steam\.getFill\(\) \* (\d+), ', BOILER_BE, r'Math\.min\(steam\.getFill\(\) \* (\d+), ', [1000]),
    'heater_feed_capacity': (O_HEATER, r'new FluidTank\(Fluids\.COOLANT, ([\d_]+)\)', HEATER_BE, r'new FluidTank\(Fluids\.COOLANT, ([\d_]+)\)', [16000]),
    'heater_steam_capacity': (O_HEATER, r'new FluidTank\(Fluids\.COOLANT_HOT, ([\d_]+)\)', HEATER_BE, r'new FluidTank\(Fluids\.COOLANT_HOT, ([\d_]+)\)', [16000]),
    'heater_reset_heat': (O_HEATER, r'heat <= (\d+) \|\| (?:this\.)?feed\.getFill\(\) <= 0', HEATER_BE, r'heat <= (\d+) \|\| (?:this\.)?feed\.getFill\(\) <= 0', [50]),
    'heater_tu_per_degree': (O_HEATER, r'TU_PER_DEGREE = ([\d_]+)D \* eff', HEATER_BE, r'TU_PER_DEGREE = ([\d_]+)D \* eff', [2000]),
    'cooler_cold_capacity': (O_COOLER, r'new FluidTank\(Fluids\.PERFLUOROMETHYL_COLD, ([\d_]+)\)', COOLER_BE, r'new FluidTank\(Fluids\.PERFLUOROMETHYL_COLD, ([\d_]+)\)', [4000]),
    'cooler_hot_capacity': (O_COOLER, r'new FluidTank\(Fluids\.PERFLUOROMETHYL, ([\d_]+)\)', COOLER_BE, r'new FluidTank\(Fluids\.PERFLUOROMETHYL, ([\d_]+)\)', [4000]),
    'cooler_scan_interval': (O_COOLER, r'if\((?:this\.)?timer <= 0\) \{\s*(?:this\.)?timer = (\d+);', COOLER_BE, r'if\((?:this\.)?timer <= 0\) \{\s*(?:this\.)?timer = (\d+);', [60]),
    'cooler_scan_cells': (O_COOLER, r'for\s*\(int i = 0; i < (\d+); i\+\+\)', COOLER_BE, r'for\s*\(int i = 0; i < (\d+); i\+\+\)', [25]),
    'cooler_scan_width': (O_COOLER, r'i / (\d+)', COOLER_BE, r'i / (\d+)', [5]),
    'cooler_fluid_per_operation': (O_COOLER, r'getFill\(\) >= (\d+) &&', COOLER_BE, r'getFill\(\) >= (\d+) &&', [50]),
    'cooler_heat_removed': (O_COOLER, r'neighbor\.heat -= (\d+);', COOLER_BE, r'\.heat -= (\d+)D?;', [200]),
    'cooler_heat_floor': (O_COOLER, r'neighbor\.heat < (\d+)\)', COOLER_BE, r'\.heat < (\d+)D?\)', [20]),
    'overpressure_divisor': (O_BASE, r'pipeBlocks\.size\(\) / (\d+)', BASE_BE, r'pipeBlocks\.size\(\) / (\d+)', [5]),
    'overpressure_cap': (O_BASE, r'Math\.min\(pipeBlocks\.size\(\) / \d+, (\d+)\)', BASE_BE, r'Math\.min\(pipeBlocks\.size\(\) / \d+, (\d+)\)', [100]),
    'overpressure_explosion_power': (O_BASE, r'newExplosion\(null, [^;]*?, ([\d.]+)F, \w+, \w+\)', BASE_BE, r'explode\(null, [^;]*?, ([\d.]+)F, \w+, [\w.]+\)', [5]),
    'overpressure_explosion_fire': (O_BASE, r'newExplosion\(null, [^;]*?, [\d.]+F, (\w+), \w+\)', BASE_BE, r'explode\(null, [^;]*?, [\d.]+F, (\w+), [\w.]+\)', ['false']),
    # The original's third argument (false: no terrain damage) is NEO's Level.ExplosionInteraction.NONE.
    'overpressure_explosion_terrain': (O_BASE, r'newExplosion\(null, [^;]*?, [\d.]+F, \w+, (\w+)\)', BASE_BE, r'explode\(null, [^;]*?, [\d.]+F, \w+, Level\.ExplosionInteraction\.(\w+)\)',
                                       ['false'], ['NONE']),
}
for _grade, _heat, _factor in (('STEAM', 100, 1), ('HOTSTEAM', 300, 10), ('SUPERHOTSTEAM', 450, 100), ('ULTRAHOTSTEAM', 600, 1000)):
    CONSTANTS['boiler_heat_'+_grade.lower()] = (O_BOILER, _FLUID_TABLE % ('getHeatFromSteam', _grade), BOILER_BE, _FLUID_TABLE % ('getHeatFromSteam', _grade), [_heat])
    CONSTANTS['boiler_factor_'+_grade.lower()] = (O_BOILER, _FLUID_TABLE % ('getFactorFromSteam', _grade), BOILER_BE, _FLUID_TABLE % ('getFactorFromSteam', _grade), [_factor])
# RBMKNeutronHandler: the CONTROL_ROD branch and the tail block are the original's two branches (text anchors; each exactly once), and the control column is not a flux receiver
# (the branch order of the handler would never reach CONTROL_ROD otherwise).
HANDLER_HOOKS = ('type == RBMKType.CONTROL_ROD', 'lastNodeType == RBMKType.CONTROL_ROD')


def scope_text(key_count, kinds, assets, tests, total_tests):
    return (f'Goal24D (RBMK control rods and the steam side, no console yet): the control columns rbmk_control, rbmk_control_mod (moderated: graphite debris on a meltdown) and '
            f'rbmk_control_auto (RBMKControlBlockEntity, RBMKControlManualBlockEntity with five colour groups, level buttons and the surge while lowering, '
            f'RBMKControlAutoBlockEntity with the LINEAR / QUAD_UP / QUAD_DOWN target level from column heat, RBMKPipedBaseBlock, RBMKControlBlock, RBMKControlAutoBlock, two menus '
            f'and screens whose control packets are validated on the server, RenderRBMKPiped for the pipe stubs or the lid and RenderRBMKControl for the rod head of rbmk_rods.obj) and '
            f'the CONTROL_ROD branch of RBMKNeutronHandler that multiplies a neutron stream by the rod\'s level (0 stops it); the steam side: the steam channel rbmk_boiler (water to '
            f'STEAM / HOTSTEAM / SUPERHOTSTEAM / ULTRAHOTSTEAM from the column heat, the compression cycle button, a vent particle and sound when the steam tank is full), the fluid '
            f'heater rbmk_heater (heats an FT_Heatable fluid, default COOLANT -> COOLANT_HOT), the cooler rbmk_cooler (cold perfluoromethyl cools every column of its 5 x 5 area by 200 '
            f'each tick it runs; the area is rescanned every 60 ticks) and the fluid connector rbmk_loader, fluid ports at the column top / bottom or through a loader, RBMKSteamParticle, the port helper and the meltdown '
            f'overpressure branch (dialEnableMeltdownOverpressure, default off) of the 24A column base; the shaped recipes rbmk_control, rbmk_control_auto, rbmk_loader, rbmk_boiler, '
            f'rbmk_heater and rbmk_cooler, while rbmk_control_mod (no graphite block in NEO) and the tier-4 anvil recycling rows stay unregistered; {assets} imported resources '
            f'(textures, GUI textures and rbmk_rods.obj); {key_count} language keys ({kinds.get("upstream", 0)} upstream, {kinds.get("local", 0)} NEO-local); {tests} '
            f'RBMKControlSteamGameTests ({total_tests} GameTests in total, one batch per test). Gameplay impact: control rods can now stop or throttle an RBMK chain reaction (level 0 '
            f'blocks a neutron stream); steam channels turn column heat into steam for the existing turbines through the existing fluid ducts and cool the reactor; heaters and '
            f'coolers move heat through fluids; with dialEnableMeltdownOverpressure on, a meltdown that reaches a steam channel destroys up to a fifth (at most 100) of the connected '
            f'steam pipes and blows up the machines on that network.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal24d release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 40 scope copies) when it reproduces the baseline hash, otherwise the blob at the start commit (with CRLF
    where the working tree had it) when it reproduces the baseline hash; None when neither does."""
    if (START_FILES/p).is_file():
        data = (START_FILES/p).read_bytes()
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT)
    for data in (blob, blob.replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def start_pin(base, p):
    """The Goal24D start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does not list
    it) the hash the goal24c receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal24c packager protected (built there from the Goal21A..Goal24B starts and receipts and the goal24c start), plus every path the goal24c receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 24D baseline lists the goal24b receipt among them) and every release file of the frozen
    start (the goal24c package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a
    main-notes.md) are pinned at their Goal24D start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes. Returns (protected,
    repinned) where repinned maps a record to the pin the goal24c packager set at its Goal24C start hash, for the records that changed between the two starts."""
    goal24c_start = read(GOAL24C_BASELINE)
    out = dict(goal24c_protected_paths(goal24c_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal24c receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal24c_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift (empty at this start).
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal24C and Goal24D starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal24c_start):
    """{path: {receipts, start_sha256, goal24c_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal24c receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal24c receipt')
        if p in base['previous_receipt_evidence_drift']:
            explanation = ('Changed after the goal24c receipt hashed it; the goal24c receipt hash is older than the start hash. Frozen at the start hash; this batch must not '
                           'change it and the goal24c receipt is not rewritten.')
        elif p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the '
                           'goal24a receipt hash is older than the start hash, the goal24b and goal24c receipts hash the current content. Frozen at the start hash; this batch '
                           'must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22 and 23 in-game acceptance results, the O1 record notes or the thorium follow-up '
                           'section); the goal24c receipt does not hash it. Frozen at the Goal24D start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal24c) records the start hash. Frozen at the start '
                           'hash; this batch must not change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal24c package; the goal24c receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it '
                           'and the goal24c receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal24c_start_sha256=goal24c_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal24c_start_pin_sha256'] = repinned[p]
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


def split_args(text):
    """The comma-separated arguments of a Java call body at parenthesis depth 0 and outside string literals."""
    out, depth, current, quoted = [], 0, '', False
    for ch in text:
        if ch == '"': quoted = not quoted
        if not quoted:
            if ch == '(': depth += 1
            elif ch == ')': depth -= 1
            elif ch == ',' and depth == 0:
                out.append(current.strip()); current = ''; continue
        current += ch
    out.append(current.strip())
    return [t for t in out if t]


def original_shaped_block(text, output, count):
    """{pattern, key, result} of the single original addRecipeAuto row producing the block `output` x `count`, or None. A key expression missing from KEY_TABLE maps to None."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.search(r'addRecipeAuto\(new ItemStack\(ModBlocks\.(\w+), (\d+)\), new Object\[\] \{ (.*) \}\);', line)
        if not m or m.group(1) != output or int(m.group(2)) != count: continue
        tokens = split_args(m.group(3))
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
    goal24c_start = read(GOAL24C_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal24D commits nothing), the recorded start with the uncommitted 24A, 24B and 24C deliveries.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 24 planning commit'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 24 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    # baseline.json stores `status --untracked-files=all` (every untracked file listed); the 690 entries of the handoff are the default `status --porcelain=v1`
    # (untracked directories collapsed) counted by startup-verification.json.
    full_status = [l for l in base['target_status'].splitlines() if l]
    assert full_status and all(l[:2] in ('??', ' M') for l in full_status), 'The frozen start status holds entries other than modified / untracked'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal24c receipt records another original commit than the frozen start'
    assert base['pending_small_fixes'] == [], 'The frozen start has a pending small fix'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and all(g in base['start_content']['uncommitted'] for g in ('Goal24A', 'Goal24B', 'Goal24C')), \
        'Baseline start content differs'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal24D: '+head
    closeout = git_ro(ROOT, 'rev-parse', 'HEAD~1').strip()
    assert closeout.startswith(GOAL23_CLOSEOUT), 'NEO HEAD~1 is not the Goal 23 close-out commit'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b',
                                                          'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b'}, 'Baseline older receipts differ'
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
        'The start generation stamp was not current or does not hold the goal24c generated tree'
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal24c package, every old release file and the protected evidence.
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal24c receipt list + the goal24c package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal24c receipt count + the goal24c release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal24c receipt'
    # The goal24c receipt has no record that drifted before the start (it hashes the goal24a main-notes at the hash that file still has).
    assert base['previous_receipt_evidence_drift'] == {}, 'The goal24c receipt evidence drifted at the start: '+str(sorted(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal24c_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal24c receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal24d. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal24D start that the owner table does not list (production outside the 15 modified Java files (NtmItemModelProvider optional), the 25 new '
         'classes incl. RBMKControlSteamGameTests, the 46 resources, zh_cn.json and the mapping, a protected record, an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal24D start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD, ANVIL_RECIPES] + GENERATED + SHARED_RECORDS + REPORTS[:1]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    need(sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES], f'{ANVIL_RECIPES} changed since the start (the five tier-4 anvil recycling rows of the control and steam columns are not registered)')
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION + OPTIONAL_JAVA if p.startswith('src/')})
    need(not outside, 'src/main change outside the 15 modified (+ optional NtmItemModelProvider) and 25 new Java files, the 46 resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal24D takes no new snapshot)'
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
            comments = [l for l in removed_lines[p] if l.strip().startswith(('//', '*', '/*'))]
            code = [l for l in removed_lines[p] if l.strip() and l not in comments]
            stray = [l for l in code if not l.strip().startswith(ALLOWED_REMOVED_CODE[p])]
            need(not stray, f'{p} removes start code lines the owner table does not allow: {[l.strip()[:90] for l in stray[:4]]}')
            removed_comments[p] = [l.strip() for l in comments]
    # Language provider: the added lines carry exactly the 59 new keys (blocks through constants, plain keys); nothing is removed.
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
    # NEO constants against the original: dial defaults, control rod speed / surge / auto function constants, boiler / heater / cooler tanks and rules, overpressure.
    steam_constants, constants_bad = {}, []
    for cid, (o_path, o_regex, n_path, n_regex, expected, *neo_expected) in CONSTANTS.items():
        o_values = captured(original_text(o_path), o_regex)
        n_values = captured((ROOT/n_path).read_text(encoding='utf-8').replace('\r\n', '\n'), n_regex) if (ROOT/n_path).is_file() else None
        assert o_values == [normalize_value(str(e)) if not isinstance(e, str) else e for e in expected] or o_values == expected, \
            f'The original constant {cid} ({o_path}) is {o_values}, the owner table expects {expected}'
        wanted = [normalize_value(str(e)) if not isinstance(e, str) else e for e in neo_expected[0]] if neo_expected else o_values
        steam_constants[cid] = dict(original=o_values, neo=n_values, original_path=o_path, neo_path=n_path, **(dict(neo_expected=wanted) if neo_expected else {}))
        if n_values != wanted: constants_bad.append(cid)
    need(not constants_bad and all(c['neo'] is not None for c in steam_constants.values()),
         f'NEO constants differ from the original (or the NEO source is missing / its text differs from the handoff): {sorted(set(constants_bad) | {k for k, c in steam_constants.items() if c["neo"] is None})}')
    handler_text = (ROOT/RBMK_HANDLER).read_text(encoding='utf-8').replace('\r\n', '\n')
    hooks = {h: handler_text.count(h) for h in HANDLER_HOOKS}
    need(all(n == 1 for n in hooks.values()), f'{RBMK_HANDLER} does not hold each of {HANDLER_HOOKS} exactly once (the CONTROL_ROD branch and the tail block): {hooks}')
    control_text = (ROOT/CONTROL_BE).read_text(encoding='utf-8') if (ROOT/CONTROL_BE).is_file() else None
    need(control_text is not None and 'IRBMKFluxReceiver' not in control_text, f'{CONTROL_BE} is missing or implements IRBMKFluxReceiver (the handler would never reach its CONTROL_ROD branch)')
    # Imported resources: byte for byte equal to the original worktree file and, up to line endings (OBJ) or exactly (PNG), its stored blob, and to the ownership record.
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
        if target.endswith('.obj'):
            # The original worktree is clean at SOURCE_HEAD, so its OBJ is the checked-out original; on this Windows checkout it carries CRLF where the stored blob
            # has LF (autocrlf). The blob must match up to that line-ending conversion, and the ownership record's blob fields must say so (goal24a / goal24c precedent).
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
    # features.json: the new rbmk-control and rbmk-steam groups, the unchanged status and reviewed_source_commit of the previous groups.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert FEATURE_FUEL in start_features and FEATURE_REACTOR in start_features and FEATURE_CONTROL not in start_features and FEATURE_STEAM not in start_features, \
        'The start mapping does not hold rbmk-fuel (24B) and rbmk-reactor (24C) and not yet rbmk-control / rbmk-steam'
    new_groups = [by_id[g] for g in (FEATURE_CONTROL, FEATURE_STEAM) if g in by_id]

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
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal24c totals {totals} + {len(KEYS)}')
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
                # The $ line breaks of the hover lines must survive in the Chinese text.
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal24c generated tree'
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
    # Recipes: the six crafting recipes (computed from the generated JSON) against the original rows; rbmk_control_mod and the anvil rows are not registered.
    o_crafting = original_text(O_CRAFTING)
    o_rows = {r: original_shaped_block(o_crafting, r, 1) for r in _RECIPES}
    assert all(row is not None and all(v is not None for v in row['key'].values()) for row in o_rows.values()), \
        f'An original recipe row could not be parsed or translated: {[r for r, row in o_rows.items() if row is None or None in row["key"].values()]}'
    assert original_shaped_block(o_crafting, 'rbmk_control_mod', 1) is not None, 'The original rbmk_control_mod row is gone (the owner table records it as not registered)'
    o_anvil = original_text(O_ANVIL)
    anvil_rows = [t for t in ('rbmk_control', 'rbmk_control_mod', 'rbmk_control_auto', 'rbmk_boiler', 'rbmk_cooler') if f'new ComparableStack(ModBlocks.{t})' not in o_anvil]
    assert not anvil_rows, 'The original anvil recycling rows are gone: '+str(anvil_rows)
    crafting = {}
    for r in _RECIPES:
        recipe_path = ROOT/GENERATED_ROOT/f'data/hbmsntm/recipe/{r}.json'
        if recipe_path.is_file():
            data = read(recipe_path)
            neo_row = dict(pattern=data.get('pattern'), key=data.get('key'), result=data.get('result'))
            crafting[r] = dict(type=data.get('type'), neo=neo_row, original=o_rows[r])
            need(data.get('type') == 'minecraft:crafting_shaped' and neo_row == o_rows[r], f'{recipe_path.relative_to(ROOT).as_posix()} differs from the original CraftingManager row: {neo_row} vs {o_rows[r]}')
        else:
            need(False, 'generated recipe missing: '+recipe_path.relative_to(ROOT).as_posix())
    mod_recipes = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/GENERATED_ROOT/'data/hbmsntm').rglob('*rbmk_control_mod*') if 'recipe' in p.relative_to(ROOT).as_posix())
    need(not mod_recipes, f'a recipe or advancement for rbmk_control_mod is registered (the owner table leaves it out: no graphite block in NEO): {mod_recipes}')
    # Mapped paths: every changed path inside the compare inventory must be matched by a feature group.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    need(len(new_groups) == 2, f'migration/features.json lacks the groups {FEATURE_CONTROL} / {FEATURE_STEAM}: has {[g for g in (FEATURE_CONTROL, FEATURE_STEAM) if g in by_id]}')
    if len(new_groups) == 2:
        for group_entry in new_groups:
            need(group_entry.get('status') == 'partial-unverified' and group_entry.get('reviewed_source_commit') == SOURCE_HEAD,
                 f'features.json group {group_entry.get("id")} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in FEATURE_SOURCES + list(ASSETS.values()) if not any(feature_matches(g, 'source', p) for g in new_groups)]
        need(not missing_source, f'features.json groups {FEATURE_CONTROL} / {FEATURE_STEAM} list in neither source_paths nor source_watch: {missing_source[:4]} ({len(missing_source)} paths)')
        missing_target = [p for p in NEW_JAVA if not any(feature_matches(g, 'target', p) for g in new_groups)]
        need(not missing_target, f'features.json groups {FEATURE_CONTROL} / {FEATURE_STEAM} lack the new classes in target_paths/target_watch: {missing_target}')
        watch = list(ASSETS) + [GENERATED_ROOT+p for p in EXPECTED_GENERATED] + [NEW_TOOLS[0]]
        missing_watch = [p for p in watch if not any(feature_matches(g, 'target', p) for g in new_groups)]
        need(not missing_watch, f'features.json groups {FEATURE_CONTROL} / {FEATURE_STEAM} lack the resources, the generated blockstates / models / loot tables / recipes or the verifier in target_watch: {missing_watch[:4]} ({len(missing_watch)} paths)')
        for group_entry in new_groups:
            absent = [p for p in group_entry.get('source_paths', []) if not (SOURCE/p).is_file()]
            need(not absent, f'features.json group {group_entry.get("id")} source_paths missing in the original: {absent}')
    need(set(by_id) == set(start_features) | {FEATURE_CONTROL, FEATURE_STEAM}, 'features.json group ids are not the start ids + '+FEATURE_CONTROL+' + '+FEATURE_STEAM+': '+str(
        sorted(set(by_id) ^ (set(start_features) | {FEATURE_CONTROL, FEATURE_STEAM}))))
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
    steam_test_names = sorted(GAMETEST_METHOD.findall((ROOT/CONTROL_STEAM_TESTS).read_text(encoding='utf-8'))) if (ROOT/CONTROL_STEAM_TESTS).is_file() else []
    steam_annotations = annotations(ROOT/CONTROL_STEAM_TESTS) if (ROOT/CONTROL_STEAM_TESTS).is_file() else 0
    need(bool(steam_test_names) and steam_annotations == len(steam_test_names), f'{CONTROL_STEAM_TESTS} holds {steam_annotations} @GameTest annotations and {len(steam_test_names)} parsed methods')
    need(gametest_added == steam_annotations, f'GameTest sources grew by {gametest_added} tests, RBMKControlSteamGameTests holds {steam_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in steam_test_names), 'GameTest log lacks "[hbm-rbmk-cs] <name> passed" for: '+str([n for n in steam_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24d/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24d/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal24d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal24d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal24d/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA + OPTIONAL_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal24d/production-vs-start.diff') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal24c final run plus the Goal24D verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal24c final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal24D suite is already in the goal24c final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal24d/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal24c final set + the Goal24D verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal24d/'+VERIFY_REPORT+' (tools/migration/verify_goal24d_rbmk_control_steam.py report)'):
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
        verifier_references = sorted(set(re.findall(r'(?:TileEntityRBMK\w+|RBMKDials|RBMK(?:Control|ControlAuto|PipedBase|Boiler|Heater|Cooler|Loader)|RBMKNeutronHandler|ContainerRBMK\w+|'
                                                      r'GUIRBMK\w+|RenderRBMKControl\w*|ParticleRBMKSteam|CraftingManager|AnvilRecipes|ClientProxy|FluidTank)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the Goal24C compare paths (which hold the 24B paths) plus this batch's compare-inventory paths).
    cmp24c = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal24c/compare.json differs from the goal24c receipt'
    c24c_added = sorted(p for p in compare_paths(cmp24c['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c24c_modified = sorted(p for p in compare_paths(cmp24c['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(c24c_added) | set(c24c_modified) | set(own_target))
    expected_added = sorted(set(c24c_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal24d/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24b + goal24c paths + %d of this batch)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(c24c_added) + len(c24c_modified), len(own_target))):
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
        for g in (FEATURE_CONTROL, FEATURE_STEAM):
            need(any(f.get('id') == g and f.get('state') == 'target-changed' for f in cmp['features']), f'{COMPARE} does not report {g} as target-changed')
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: [OWNER] for p in listed},
                       goal24c_paths=len(c24c_added) + len(c24c_modified), goal24d_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the rbmk-fuel (24B) and rbmk-reactor (24C) groups.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - {FEATURE_FUEL, FEATURE_REACTOR},
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without rbmk-fuel and rbmk-reactor)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal24d.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal24c) package (run build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 46 resources and every compiled class equal the sources.
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
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 46 imported resources, the generated additions and the modified '
             'en_us.json / zh_cn.json / pickaxe tag are owned; META-INF/MANIFEST.MF is not): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA),
             'Changed Java sources and goal24d JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, TAG_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + pickaxe tag + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for inner in ('com/hbm/blockentity/machine/rbmk/RBMKControlManualBlockEntity$RBMKColor.class', 'com/hbm/blockentity/machine/rbmk/RBMKControlAutoBlockEntity$RBMKFunction.class'):
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal24c_start=sorted(repinned),
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                   insert_lines=insert_summary, edit_counts=edit_summary, removed_comment_lines={p: len(v) for p, v in removed_comments.items()},
                   steam_constants={k: c['neo'] == c.get('neo_expected', c['original']) for k, c in steam_constants.items()},
                   handler_hooks=hooks, crafting_recipes=len(crafting), gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_control_steam_tests=steam_test_names, final_suites_expected=final_expected,
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
    rbmk_control_steam = dict(neo=[CONTROL_BE, MANUAL_BE, AUTO_BE, BOILER_BE, HEATER_BE, COOLER_BE, PIPED_BLOCK, CONTROL_BLOCK, AUTO_BLOCK, BOILER_BLOCK, HEATER_BLOCK, COOLER_BLOCK,
                                  LOADER_BLOCK, CONTROL_MENU, AUTO_MENU, BOILER_MENU, HEATER_MENU, CONTROL_SCREEN, AUTO_SCREEN, BOILER_SCREEN, HEATER_SCREEN, PIPED_RENDERER,
                                  CONTROL_RENDERER, STEAM_PARTICLE, BASE_BE, BASE_BLOCK, RBMK_HANDLER], original=[p for p in O_SOURCES],
                              constants=steam_constants, handler_hooks=hooks, original_references=original_refs,
                              defaults=dict(control_speed_dial=1.0, control_surge_dial=1.0, boiler_heat_consumption_dial=0.1, enable_meltdown_overpressure=False),
                              note='A control rod moves 0.00277 per tick x dialControlSpeed 1.0 (0 -> 1 in 362 ticks); the manual rod adds the surge sin((1 - level)^15 x PI) x '
                                   '(startingLevel - target) x dialControlSurgeMod 1.0 to its multiplier while it is lowered by more than 0.01; the automatic rod takes the target '
                                   'level from the column heat between two heat and two level bounds (LINEAR, QUAD_UP, QUAD_DOWN, x 0.01, clamped to 0..1); the neutron handler '
                                   'multiplies a stream by the rod\'s level (0 stops it). Steam grades STEAM 100 °C / factor 1, HOTSTEAM 300 / 10, SUPERHOTSTEAM 450 / 100, '
                                   'ULTRAHOTSTEAM 600 / 1000; the boiler spends dialBoilerHeatConsumption 0.1 °C per mB of water (tanks water 10,000 mB, steam 1,000,000 mB) and '
                                   'refuses to cycle the compression while heat > 50 °C with water in the feed tank; the heater (tanks 16,000 mB) moves 2,000 TU per degree x '
                                   'efficiency; the cooler (tanks 4,000 mB) uses 50 mB per operation and removes 200 °C (floor 20 °C) from every column in its 5 x 5 area on '
                                   'each such tick (the area is rescanned every 60 ticks); the loader connects up for heatable fluids and on the sides for coolable fluids and perfluoromethyl. With '
                                   'dialEnableMeltdownOverpressure (default false) a meltdown that reaches a steam channel destroys up to min(pipes / 5, 100) pipe nodes of its '
                                   'steam network and explodes every receiver on it (power 5, no fire, no terrain damage). Not migrated: the ReaSim control rods and steam '
                                   'inlet/outlet (Goal 26), rbmk_control_mod\'s recipe (no graphite block in NEO), the tier-4 anvil recycling rows, OpenComputers / Energy Control '
                                   'parts and the console (Goal24E).')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), language_kinds, len(ASSETS), len(steam_test_names), gametest_expected),
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
                                           'Goal24A, Goal24B and Goal24C deliveries (690 status entries; the goal24a, goal24b and goal24c packages, not committed by decision 2) and '
                                           'the planning session\'s 2026-10-19 recipe correction of GOAL24D.md / GOAL24-THREAD-PROMPTS.md; no pending small fix; build/libs at the start is '
                                           'the goal24c package byte for byte. The original did not move since 24A. The freeze copied all 40 scope files to baseline-files, so no '
                                           'supplement copy was needed. Paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, removed_comment_lines=removed_comments, start_copies_supplement=[],
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   rbmk_control_steam=rbmk_control_steam,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note='47 entries are upstream (the seven block names, the loader description, the four container titles, the rbmk.control.* and rbmk.boiler.* console '
                                      'labels and the tile.rbmk.dodd.* diagnostic labels of the control rods, the steam channel, the heater and the cooler, English and Chinese verbatim '
                                      'from en_US.lang / zh_CN.lang); 12 are NEO-local (the hover lines and select hints of GUIRBMKControlAuto, hard-coded English in the original, '
                                      'with $ as the line break). No existing key changes its value.'),
                   recipes=dict(crafting=crafting, not_registered=['rbmk_control_mod', 'anvil recycling rows rbmk_control, rbmk_control_mod, rbmk_control_auto, rbmk_boiler, rbmk_cooler (tier-4 anvil)',
                                                                   'ReaSim control rod and steam inlet/outlet rows (Goal 26)'],
                                original_references={k: v for k, v in original_refs.items() if k.startswith(('recipe_', 'anvil_'))},
                                anvil_recipes_unchanged=sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES],
                                note='The six shaped recipes equal the original CraftingManager rows (:760 rbmk_control, :762 rbmk_control_auto, :771 rbmk_loader, :993 rbmk_boiler, :994 '
                                     'rbmk_heater, :995 rbmk_cooler). rbmk_control_mod (:761) needs a graphite block NEO does not have (24A precedent); the AnvilRecipes rows '
                                     '(:868-953) are tier-4 recycling rows (unreachable, 24A precedent); both stay unregistered.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report, repinned_since_goal22d_start=prior_receipt['repinned_since_goal22d_start'],
                   repinned_since_goal23a_start=prior_receipt['repinned_since_goal23a_start'], repinned_since_goal23b_start=prior_receipt['repinned_since_goal23b_start'],
                   repinned_since_goal23c_start=prior_receipt['repinned_since_goal23c_start'], repinned_since_goal24a_start=prior_receipt['repinned_since_goal24a_start'],
                   repinned_since_goal24b_start=prior_receipt['repinned_since_goal24b_start'],
                   repinned_since_goal24c_start={p: dict(goal24c_start_pin_sha256=h, goal24d_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_control_steam_tests=steam_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per RBMKControlSteamGameTests test: the control '
                                      'rod movement, surge and automatic functions, the neutron stream multiplier, the steam channel grades and compression, the heater, the cooler '
                                      'scan, the loader connection rule and the fluid network paths exercised in the tests, the NBT round trips and the six recipes; no client (the '
                                      'rod head, pipe stubs and lid rendering, the four screens and their English / Chinese readouts, the steam vent particle and sound are not '
                                      'rendered or played), no real player, no saved world, no survival reactor build with real steam turbines.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier '
                            'with in-memory mutations, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and an independent and a '
                            'redundant static review. No in-game client test was run: the control-rod head rendering, the pipe stubs, the screens and their English and Chinese '
                            'readouts, the colour buttons, the steam vent particle and sound are unverified; no survival reactor build with real steam turbines in a world was run; '
                            'no multiplayer or dedicated server beyond GameTest; the meltdown overpressure branch is only statically reviewed; GOAL24D-ACCEPTANCE.md is written but '
                            'not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, start_jar_sha), 'build/libs JAR is an older JAR'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal24d JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal24c package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
