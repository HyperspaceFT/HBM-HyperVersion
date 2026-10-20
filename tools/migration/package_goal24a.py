"""Package Goal24A (the RBMK core: the `rbmk` config section with 21 dials and the static RBMKDials facade; the column base RBMKBaseBlock /
RBMKBaseBlockEntity with heat flow, passive cooling, the LID state, the DODD overlay and the meltdown sequence; the four passive columns rbmk_blank,
rbmk_reflector, rbmk_absorber, rbmk_moderator; the lids rbmk_lid and rbmk_lid_glass; deco_rbmk and deco_rbmk_smooth; the debris blocks pribris,
pribris_burning, pribris_radiating and the debris entity rbmk_debris; debris_fuel; the meltdown_tool RBMK branch; ass.rbmk and seven crafting recipes; 40
imported resources; the screwdriver as ToolingItem; the Goal 23 close-out remainders of 24A-2; the 24A-1 upstream classification of the 26 changed original
files with the two adapted fluid names and the new observation snapshot review-aee05a40f10f.json; RBMKCoreGameTests and new HazardGameTests methods; the turbofan redstone probe at the port cells with the three Goal17B regression files adjusted)
cumulatively on the goal23c package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal24a.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal24a/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal24a/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal24a/baseline.json: NEO HEAD 1114adf5 (the Goal 24 planning commit on top of the pushed Goal 23 close-out commit
09173669) with a CLEAN worktree (no uncommitted earlier batch paths); the original repository HEAD moved from 6a11998d to aee05a40f before this batch
(24A-1). build/libs at the start is the goal23c package byte for byte. Every change since the start is computed from the baseline file hashes (not from git
diff) and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with their start
bytes (baseline-files where copied, otherwise the blob at the start commit with the working tree's CRLF line endings, checked against the baseline hash).
The JAR delta against the goal23c package is attributed per entry (goal24a); any entry without exactly one owner fails. Counts that records quote (suites,
GameTests, generated resources, classes, releases, language keys, recipes) are computed here, never hard-coded; the previous package's SHA-256, size and
receipt hashes are read from the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal23b, the review-g21d-hazard-fix receipt and goal23c) were written before later appends to the acceptance
checklists, before the O1 record notes and (goal22c) before the thorium follow-up section of GOAL22C.md; those records already differ from their older
receipt hashes at the frozen start (baseline older_receipt_evidence_drift), and GOAL23C-ACCEPTANCE.md differs from the goal23c receipt hash (baseline
previous_receipt_evidence_drift: the Goal 23 in-game acceptance results appended). They are listed in the receipt as start drift and must still equal their
Goal24A start hash; no receipt is rewritten and no other protected path may drift.

Unlike the Goal23C packager this one takes the original commit from the baseline (aee05a40f, moved) instead of the Goal21D constant, defines its own
original_blob / original_line helpers for it, and carries two compare runs: build/migration/goal24a/compare-old.json against the old snapshot
review-6a11998d5852.json (the 26 changed original files = the classification) and build/migration/goal24a/compare.json against the new snapshot
review-aee05a40f10f.json (0/0/0, 52 groups no-observed-file-change)."""
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
from package_goal22c import NAMES_RELEASE, J
from package_goal23b import report_problems
from package_goal23c import (OUT as GOAL23C_OUT, BASELINE as GOAL23C_BASELINE, protected_paths as goal23c_protected_paths, split_args)

OUT = ROOT/'build/migration/goal24a'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL23C_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL23C_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal23c/hbmsntm-198A-goal23c.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal24a'
RELEASE_NAME = 'hbmsntm-198A-goal24a.jar'
OWNER = 'goal24a'
# The original moved this batch (24A-1): SOURCE_HEAD is where the original stands now, SOURCE_PREVIOUS the commit the old snapshot and the goal23c receipt record.
SOURCE_HEAD = 'aee05a40f10fb7bb9b042b65eccaa449ecc1672d'
SOURCE_PREVIOUS = '6a11998d5852ff3da326f0130357e10431ae3839'
PLANNING_PREFIX = '1114adf5'
GOAL23_CLOSEOUT = '09173669'
SNAPSHOT_OLD = 'migration/baselines/review-6a11998d5852.json'
SNAPSHOT_NEW = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'

# Production (owner goal24a), NEW: the 17 RBMK classes (build/migration/goal24a/review-new-files.txt) and the GameTest class.
NEW_JAVA = [J+p+'.java' for p in (
    'blockentity/machine/rbmk/RBMKAbsorberBlockEntity', 'blockentity/machine/rbmk/RBMKBaseBlockEntity', 'blockentity/machine/rbmk/RBMKBlankBlockEntity',
    'blockentity/machine/rbmk/RBMKColumnType', 'blockentity/machine/rbmk/RBMKDials', 'blockentity/machine/rbmk/RBMKModeratorBlockEntity',
    'blockentity/machine/rbmk/RBMKReflectorBlockEntity', 'blockentity/machine/rbmk/RBMKType',
    'blocks/machine/rbmk/RBMKBaseBlock', 'blocks/machine/rbmk/RBMKDebrisBlock', 'blocks/machine/rbmk/RBMKDebrisBurningBlock',
    'blocks/machine/rbmk/RBMKDebrisRadiatingBlock', 'blocks/machine/rbmk/RBMKPassiveBlock',
    'entity/projectile/RBMKDebris', 'items/machine/RBMKLidItem', 'render/blockentity/RenderRBMKLid', 'render/entity/projectile/RenderRBMKDebris',
    'gametest/RBMKCoreGameTests')]
RBMK_TESTS = NEW_JAVA[-1]
# Production, MODIFIED existing sources (handoff-packaging.md; the real set is computed from the tree against the start and every other src/ change fails).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blockentity/NtmBlockEntityTypes', 'blockentity/machine/LockableBaseBlockEntity', 'blockentity/machine/MachineTurbofanBlockEntity', 'blocks/ITooltipProvider', 'blocks/NtmBlocks', 'config/CommonConfig',
    'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockStateProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmItemModelProvider',
    'datagen/NtmLanguageProvider', 'datagen/NtmRecipeProvider', 'entity/NtmEntityTypes', 'entity/projectile/ZirnoxDebris', 'hazard/HazardRegistry',
    'hazard/type/HazardTypeRadiation', 'inventory/NtmCreativeTabs', 'inventory/fluid/FluidType', 'inventory/fluid/trait/FT_Pheromone',
    'inventory/fluid/trait/FluidTrait', 'inventory/recipes/AssemblyMachineRecipes', 'items/NtmItems', 'items/tools/DyatlovItem', 'items/tools/ToolingItem',
    'main/ClientProxy', 'main/ResourceManager', 'render/model/loader/NtmGeometry', 'util/ContaminationUtil', 'gametest/HazardGameTests')]
(BLOCK_ENTITY_TYPES, LOCKABLE, TURBOFAN, TOOLTIP_PROVIDER, BLOCKS, COMMON_CONFIG, LOOT_PROVIDER, BLOCK_STATE_PROVIDER, TAG_PROVIDER, ITEM_MODEL_PROVIDER, PROVIDER,
 RECIPE_PROVIDER, ENTITY_TYPES, ZIRNOX_DEBRIS, HAZARD_REGISTRY, HAZARD_RADIATION, CREATIVE_TABS, FLUID_TYPE, FT_PHEROMONE, FLUID_TRAIT, ASSEMBLY, ITEMS,
 DYATLOV, TOOLING, CLIENT_PROXY, RESOURCE_MANAGER, GEOMETRY, CONTAMINATION, HAZARD_TESTS) = MODIFIED_JAVA
# Listed in the freeze scope but not expected to change; allowed to change (the task book names NtmConfig; the client entry may gain the debris renderer).
OPTIONAL_JAVA = [J+'config/NtmConfig.java', J+'main/NuclearTechModClient.java']
# Registration and datagen files that must stay insert-only against their start bytes.
STRICT_INSERT_ONLY = [BLOCK_ENTITY_TYPES, BLOCKS, LOOT_PROVIDER, BLOCK_STATE_PROVIDER, TAG_PROVIDER, ITEM_MODEL_PROVIDER, RECIPE_PROVIDER, ENTITY_TYPES,
                      CREATIVE_TABS, ASSEMBLY, CLIENT_PROXY, RESOURCE_MANAGER, DYATLOV, ZH_INPUT]
# The 40 imported original resources: NEO target -> original path (under the original repository), derived by the layout rules of the ownership record
# (textures/block -> textures/blocks, textures/item -> textures/items, models/obj/rbmk -> models/rbmk, models/obj/projectiles -> models/projectiles).
_COLUMN_TEXTURES = [f'rbmk_{c}_{s}.png' for c in ('blank', 'moderator', 'absorber', 'reflector') for s in ('side', 'top', 'cover_side', 'cover_top', 'glass_side', 'glass_top')] \
    + ['rbmk_top.png', 'rbmk_side.png', 'rbmk_debris.png', 'rbmk_debris_burning.png', 'rbmk_debris_radiating.png', 'rbmk_fuel.png', 'rbmk_control.png']
ASSETS = {ASSETS_ROOT+'textures/block/rbmk/'+n: O_RES+'textures/blocks/rbmk/'+n for n in _COLUMN_TEXTURES}
ASSETS.update({ASSETS_ROOT+'textures/item/'+n+'.png': O_RES+'textures/items/'+n+'.png' for n in ('debris_fuel', 'rbmk_lid', 'rbmk_lid_glass')})
ASSETS[ASSETS_ROOT+'models/obj/rbmk/debris.obj'] = O_RES+'models/rbmk/debris.obj'
ASSETS.update({ASSETS_ROOT+'models/obj/projectiles/'+n+'.obj': O_RES+'models/projectiles/'+n+'.obj' for n in ('deb_blank', 'deb_element', 'deb_fuel', 'deb_lid', 'deb_rod')})
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = PRODUCTION_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
GENERATED = [STAMP, EN]
TAG_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
# Generated by runData for this batch (relative to src/generated/resources): 9 blockstates, 9 block models, 12 item models, 9 loot tables, 7 recipes + 7 advancements.
_BLOCKS = ('deco_rbmk', 'deco_rbmk_smooth', 'pribris', 'pribris_burning', 'pribris_radiating', 'rbmk_absorber', 'rbmk_blank', 'rbmk_moderator', 'rbmk_reflector')
_ITEMS = ('debris_fuel', 'deco_rbmk', 'deco_rbmk_smooth', 'pribris', 'pribris_burning', 'pribris_radiating', 'rbmk_absorber', 'rbmk_blank', 'rbmk_lid',
          'rbmk_lid_glass', 'rbmk_moderator', 'rbmk_reflector')
CRAFT_IDS = ('rbmk_lid', 'rbmk_absorber', 'rbmk_reflector', 'deco_rbmk', 'deco_rbmk_smooth', 'rbmk_blank_from_deco_rbmk', 'rbmk_blank_from_deco_rbmk_smooth')
_ADVANCEMENT_FOLDER = {'rbmk_lid': 'misc', 'rbmk_absorber': 'misc', 'rbmk_reflector': 'misc', 'deco_rbmk': 'building_blocks', 'deco_rbmk_smooth': 'building_blocks',
                       'rbmk_blank_from_deco_rbmk': 'misc', 'rbmk_blank_from_deco_rbmk_smooth': 'misc'}
EXPECTED_GENERATED = sorted([f'assets/hbmsntm/blockstates/{b}.json' for b in _BLOCKS] + [f'assets/hbmsntm/models/block/{b}.json' for b in _BLOCKS]
                            + [f'assets/hbmsntm/models/item/{i}.json' for i in _ITEMS] + [f'data/hbmsntm/loot_table/blocks/{b}.json' for b in _BLOCKS]
                            + [f'data/hbmsntm/recipe/{r}.json' for r in CRAFT_IDS]
                            + [f'data/hbmsntm/advancement/recipes/{_ADVANCEMENT_FOLDER[r]}/{r}.json' for r in CRAFT_IDS])
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, TAG_ENTRY])
NEW_TOOLS = ['tools/migration/verify_goal24a_rbmk_core.py', 'tools/migration/package_goal24a.py']
# Existing tools the turbofan adaptation changes (the 19A precedent): the Goal17B regressions move their redstone anchors to the port cells; owned by goal24a.
MODIFIED_TOOLS = ['tools/migration/goal17b_regression/Goal17BMachineRegression.java', 'tools/migration/goal17b_regression/Goal17BEntityRegression.java',
                  'tools/migration/verify_goal17b_machine.py']
TOOLS = NEW_TOOLS + MODIFIED_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports and the new snapshot; any further migration/goal24a-* or GOAL24A-* record is hashed as well.
REPORTS = ['migration/GOAL24A.md', 'migration/GOAL24A-ACCEPTANCE.md', 'migration/goal24a-static-review.md', 'migration/goal24a-resource-ownership.json',
           'migration/goal24a-upstream-classification.json', SNAPSHOT_NEW]
RESOURCE_OWNERSHIP, CLASSIFICATION = REPORTS[3], REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal24a-[^/]+\.(json|md)|GOAL24A-[^/]+\.md)')
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md',
                  'migration/GOAL24.md', 'migration/GOAL24-THREAD-PROMPTS.md']
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED.
REQUIRED_CHANGES = [p for p in PRODUCTION if p not in OPTIONAL_JAVA] + GENERATED + [GENERATED_ROOT+TAG_ENTRY] + TOOLS + REPORTS + SHARED_RECORDS
# The 17 new language keys: NEO key -> original key (None: a NEO-local key). The two changed English values are the fluid names the 24A-1 classification adapted.
KEYS = {'block.hbmsntm.deco_rbmk': 'tile.deco_rbmk.name', 'block.hbmsntm.deco_rbmk_smooth': 'tile.deco_rbmk_smooth.name', 'block.hbmsntm.pribris': 'tile.pribris.name',
        'block.hbmsntm.pribris_burning': 'tile.pribris_burning.name', 'block.hbmsntm.pribris_radiating': 'tile.pribris_radiating.name',
        'block.hbmsntm.rbmk_absorber': 'tile.rbmk_absorber.name', 'block.hbmsntm.rbmk_blank': 'tile.rbmk_blank.name',
        'block.hbmsntm.rbmk_moderator': 'tile.rbmk_moderator.name', 'block.hbmsntm.rbmk_reflector': 'tile.rbmk_reflector.name',
        'desc.misc.holdShiftMoreInfo': None, 'entity.hbmsntm.rbmk_debris': None,
        'hbmfluid.trait.glyphidPheromones': 'hbmfluid.trait.glyphidPheromones', 'hbmfluid.trait.modifiedPheromones': 'hbmfluid.trait.modifiedPheromones',
        'item.hbmsntm.debris_fuel': 'item.debris_fuel.name', 'item.hbmsntm.rbmk_lid': 'item.rbmk_lid.name', 'item.hbmsntm.rbmk_lid_glass': 'item.rbmk_lid_glass.name',
        'tile.rbmk.dodd.heat': 'tile.rbmk.dodd.heat'}
CHANGED_KEYS = {'hbmfluid.calcium_chloride': 'Calcium chloride Solution', 'hbmfluid.potassium_chloride': 'Potassium chloride Solution'}
EXPECTED_KINDS = {'upstream': sum(1 for v in KEYS.values() if v), 'local': sum(1 for v in KEYS.values() if not v)}
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
PROVIDER_ADD_ITEM = re.compile(r'this\.add\(NtmItems\.(\w+), "(.*)"\);$')
PROVIDER_ADD_BLOCK = re.compile(r'this\.add\(NtmBlocks\.(\w+), "(.*)"\);$')
PROVIDER_ADD_KEY = re.compile(r'this\.add\("([\w.]+)", "(.*)"\);$')
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rbmk-core] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'compile-start.log', 'upstream-delta.json', 'planning-commit-msg.txt', 'main-notes.md',
                  'builder-progress.md', 'handoff-production.md', 'handoff-gametest.md', 'handoff-verifier.md', 'handoff-packaging.md')
# Review files under OUT (for example the two independent static reviews' notes or diffs) the main agent names when it knows them; each must exist and is
# indexed by the receipt. Extend this list from the real run (final-run.log, final-summary.log, compare.log, review notes, features/records scripts).
REVIEW_EVIDENCE = ('verifier-gt-progress.md', 'review-diff.patch', 'review-new-files.txt', 'make_final_runner.py', 'make_explained.py', 'final_explained.py')
COMPARE_OLD = 'compare-old.json'
GAMETEST_LOG = 'build/migration/goal24a/gametest-final.log'
NEW_SUITE = 'verify_goal24a_rbmk_core.py --gametest-log build/migration/goal24a/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_GROUP, FEATURE_ZIRNOX, FEATURE_MATERIALS = 'rbmk-core', 'zirnox-reactor', 'materials'
RADIATION_NOTE = ('Goal24A: pribris_radiating contaminates every living entity within 100 blocks and burns those within 5; debris_fuel is 500 RAD/s; handle both only in '
                  'separately authorized disposable worlds, never in a player\'s inventory. ')
MELTDOWN_NOTE = ('Goal24A: meltdown_tool melts every horizontally connected RBMK column into debris blocks and flings permanent debris entities (dialEnablePermaScrap '
                 'true); only in disposable worlds away from builds. ')
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_DIALS = ORIGINAL+'tileentity/machine/rbmk/RBMKDials.java'
O_BASE = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKBase.java'
O_DEBRIS_ENTITY = ORIGINAL+'entity/projectile/EntityRBMKDebris.java'
O_HAZARD = ORIGINAL+'hazard/HazardRegistry.java'
O_MOD_ITEMS = ORIGINAL+'items/ModItems.java'
O_ASSEMBLY = ORIGINAL+'inventory/recipes/AssemblyMachineRecipes.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_TOOLING = ORIGINAL+'items/tool/ItemTooling.java'
O_TURBOFAN = ORIGINAL+'tileentity/machine/TileEntityMachineTurbofan.java'
O_DEGRADATION = ORIGINAL+'items/tool/ItemCraftingDegradation.java'
O_RBMK_SOURCES = [ORIGINAL+p for p in (
    'tileentity/machine/rbmk/RBMKDials.java', 'tileentity/machine/rbmk/TileEntityRBMKBase.java', 'tileentity/machine/rbmk/TileEntityRBMKBlank.java',
    'tileentity/machine/rbmk/TileEntityRBMKAbsorber.java', 'tileentity/machine/rbmk/TileEntityRBMKModerator.java', 'tileentity/machine/rbmk/TileEntityRBMKReflector.java',
    'blocks/machine/rbmk/RBMKBase.java', 'blocks/machine/rbmk/RBMKBlank.java', 'blocks/machine/rbmk/RBMKAbsorber.java', 'blocks/machine/rbmk/RBMKModerator.java',
    'blocks/machine/rbmk/RBMKReflector.java', 'blocks/machine/rbmk/RBMKDebris.java', 'blocks/machine/rbmk/RBMKDebrisBurning.java',
    'blocks/machine/rbmk/RBMKDebrisRadiating.java', 'items/machine/ItemRBMKLid.java', 'entity/projectile/EntityRBMKDebris.java')]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'tile_max_heat': (O_BASE, 'return 1500D;'),
    'tile_tracking_range': (O_BASE, 'return 15;'),
    'tile_heat_floor': (O_BASE, 'if(heat < 20) heat = 20D;'),
    'tile_passive_cooling': (O_BASE, 'return min + (max - min) * ((4 - MathHelper.clamp_int(neighbors, 0, 4)) / 4D);'),
    'tile_step_size': (O_BASE, 'double stepSize = RBMKDials.getColumnHeatFlow(worldObj);'),
    'dial_passive_cooling': (O_DIALS, 'KEY_PASSIVE_COOLING("dialPassiveCooling"'),
    'dial_passive_cooling_inner': (O_DIALS, 'KEY_PASSIVE_COOLING_INNER("dialPassiveCoolingInner"'),
    'dial_column_heat_flow': (O_DIALS, 'KEY_COLUMN_HEAT_FLOW("dialColumnHeatFlow"'),
    'dial_column_height': (O_DIALS, 'KEY_COLUMN_HEIGHT("dialColumnHeight"'),
    'dial_column_height_minus_one': (O_DIALS, 'RBMKKeys.KEY_COLUMN_HEIGHT, 2, 16) - 1'),
    'debris_lifetime_blank': (O_DEBRIS_ENTITY, 'case BLANK: return 3 * 60 * 20;'),
    'debris_lifetime_lid': (O_DEBRIS_ENTITY, 'case LID: return 30 * 20;'),
    'hazard_debris_fuel': (O_HAZARD, 'HazardSystem.register(debris_fuel'),
    'turbofan_con_pos': (O_TURBOFAN, 'new DirPos(this.xCoord + rot.offsetX, this.yCoord, this.zCoord + rot.offsetZ, rot),'),
    'turbofan_redstone_probe': (O_TURBOFAN, 'for(DirPos pos : getConPos()) {'),
    'screwdriver': (O_MOD_ITEMS, 'screwdriver = new ItemTooling(ToolType.SCREWDRIVER, 100)'),
    'screwdriver_desh': (O_MOD_ITEMS, 'screwdriver_desh = new ItemTooling(ToolType.SCREWDRIVER, 0)'),
    'tooling_on_use': (O_TOOLING, 'if(((IToolable)b).onScrew('),
    'degradation_stack': (O_DEGRADATION, 'this.setMaxStackSize(1);'),
    'degradation_no_repair': (O_DEGRADATION, 'this.setNoRepair();'),
    'ass.rbmk': (O_ASSEMBLY, 'new GenericRecipe("ass.rbmk")'),
    'craft_rbmk_lid': (O_CRAFTING, 'new ItemStack(ModItems.rbmk_lid, 4)'),
    'craft_rbmk_absorber': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_absorber, 1)'),
    'craft_rbmk_reflector': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_reflector, 1)'),
    'craft_deco_rbmk': (O_CRAFTING, 'new ItemStack(ModBlocks.deco_rbmk, 8)'),
    'craft_deco_rbmk_smooth': (O_CRAFTING, 'new ItemStack(ModBlocks.deco_rbmk_smooth, 1)'),
    'craft_rbmk_blank_from_deco_rbmk': (O_CRAFTING, "'R', ModBlocks.deco_rbmk })"),
    'craft_rbmk_blank_from_deco_rbmk_smooth': (O_CRAFTING, "'R', ModBlocks.deco_rbmk_smooth })"),
}
# The original crafting rows: NEO recipe id -> (output name, count, a token of the key expression that picks the row among several with that output).
CRAFTING = {'rbmk_lid': ('rbmk_lid', 4, None), 'rbmk_absorber': ('rbmk_absorber', 1, None), 'rbmk_reflector': ('rbmk_reflector', 1, None),
            'deco_rbmk': ('deco_rbmk', 8, None), 'deco_rbmk_smooth': ('deco_rbmk_smooth', 1, None),
            'rbmk_blank_from_deco_rbmk': ('rbmk_blank', 1, "'R', ModBlocks.deco_rbmk })"), 'rbmk_blank_from_deco_rbmk_smooth': ('rbmk_blank', 1, "'R', ModBlocks.deco_rbmk_smooth })")}
SKIPPED_OUTPUTS = ('rbmk_moderator', 'rbmk_lid_glass')  # NEO has no graphite block, lead glass or boron glass: creative-only (main-notes)
# Original assembly ingredient expressions -> the NEO ingredient (the verifier applies the same table).
ASSEMBLY_TRANSLATION = {'STEEL.plateCast()': ('cast', 'STEEL'), 'CU.plate()': ('item', 'PLATE_COPPER'), 'RUBBER.ingot()': ('item', 'INGOT_RUBBER')}
# The dials NEO does not register (RBMKDials.java:17-51): the save switch and the three ReaSim dials.
UNREGISTERED_DIALS = {'dialSaveDials', 'dialReasimBoilers', 'dialReasimRange', 'dialReasimBoilerSpeed'}
LID_AND_DEBRIS_TYPES = ('BLANK', 'ELEMENT', 'FUEL', 'GRAPHITE', 'LID', 'ROD')


def scope_text(key_count, kinds, assets, rbmk_tests, hazard_tests, total_tests, changed_keys):
    return (f'Goal24A (the RBMK core and the Goal 23 close-out remainders): the rbmk config section (21 dials of the original RBMKDials, defaults and clamps as the '
            f'original, read through the static facade RBMKDials; ZirnoxDebris reads RBMKDials.getPermaScrap() instead of a constant, default true, ZIRNOX unchanged); '
            f'the column base RBMKBaseBlock / RBMKBaseBlockEntity (heat flow to the four horizontal neighbours, passive cooling 0.1 to 2.5, floor 20, maxHeat 1500, '
            f'NBT heat, lid state none/standard/glass on the core, DODD overlay, meltdown() with a flood fill, standardMelt and the debris spawn); the passive columns '
            f'rbmk_blank, rbmk_reflector, rbmk_absorber, rbmk_moderator; the lids rbmk_lid and rbmk_lid_glass (RBMKLidItem); deco_rbmk and deco_rbmk_smooth; the debris '
            f'blocks pribris, pribris_burning, pribris_radiating and the entity rbmk_debris (RBMKDebris); the item debris_fuel (RADIATION 500, HOT 5); the meltdown_tool '
            f'(DyatlovItem) RBMK branch; the lid renderer and the debris renderer; {assets} imported resources; the assembly row ass.rbmk and seven crafting recipes '
            f'(the moderator and glass-lid rows are skipped because NEO has no graphite block, lead glass or boron glass; no anvil rows because tier 4 is unreachable); '
            f'the screwdriver and screwdriver_desh become ToolingItem (100 / unbreakable, stack 1, no repair; ToolingItem wears and consumes the click only when onScrew '
            f'succeeds, which also affects the defuser; LockableBaseBlockEntity checks the screwdriver by item); the turbofan redstone probe at the port cells (MachineTurbofanBlockEntity, with the Goal17B regressions adjusted); the 24A-2 remainders (FT_Pheromone keys, the FluidTrait '
            f'duplicate pair, the HazardTypeRadiation reacher scan, the ContaminationUtil creative precedence, the meteorShowerChance key, the translatable Hold <LSHIFT> '
            f'hint, five NEO-only vanilla hazard rows deleted by the user decision of 2026-10-19); 24A-1: the original HEAD moved from 6a11998d to aee05a40f, its 26 changed '
            f'files are classified, the two fluid names calcium_chloride and potassium_chloride follow the original spelling, and the observation snapshot '
            f'review-aee05a40f10f.json is new; {key_count} language keys ({kinds.get("upstream", 0)} upstream, {kinds.get("local", 0)} NEO-local) and {changed_keys} changed '
            f'English values; {rbmk_tests} RBMKCoreGameTests and {hazard_tests} new HazardGameTests methods are added ({total_tests} GameTests in total). Gameplay impact: the '
            f'screwdriver now has durability (100) and only wears on a successful use; meltdown_tool melts every connected RBMK column into debris blocks and flings '
            f'permanent debris entities; pribris_radiating contaminates living entities within 100 blocks and burns those within 5; debris_fuel is 500 RAD/s; the five vanilla '
            f'items (gold ingot, blaze powder, green and white wool, coal) lost their NEO-only hazards; existing config files may keep meteorStrikeChance at the stored value; the turbofan now reads redstone at the adjacent 1-block port cell instead of the cell 2 blocks out '
            f'(upstream aee05a40f, changelog "redstone detection offset outwards"), so an existing save with redstone 2 blocks out must move it to the port cell.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal24a release directory: '+rel


def original_blob(path):
    """Bytes of a file at the original repository's current commit SOURCE_HEAD (independent of its worktree)."""
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+SOURCE.as_posix(), 'show', SOURCE_HEAD+':'+path], cwd=SOURCE)


def original_text(path):
    return original_blob(path).decode('utf-8').replace('\r\n', '\n')


def original_line(path, token):
    """1-based line of the first line of the original's stored blob (at SOURCE_HEAD) that contains the token."""
    for number, line in enumerate(original_text(path).split('\n'), 1):
        if token in line: return number
    raise AssertionError(f'{path} has no line with {token!r} at the recorded original commit')


def lang_file(path):
    """key -> value of an original .lang file at SOURCE_HEAD (the first of a duplicated key wins)."""
    out = {}
    for line in original_text(path).split('\n'):
        if '=' in line and not line.startswith('#'):
            k, _, v = line.partition('=')
            out.setdefault(k.strip(), v)
    return out


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy, otherwise the blob at the (clean) start commit with CRLF where the working tree had it; None
    when neither reproduces the baseline hash."""
    if p in base['copied_scope']: return (START_FILES/p).read_bytes()
    blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT)
    for data in (blob, blob.replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def protected_paths(base):
    """What the goal23c packager protected (built there from the Goal21A..Goal23B starts and receipts and the goal23c start), plus every path the goal23c receipt
    hashes (base previous_receipt_protected_paths), the paths the older receipts hash (the 24A baseline lists the goal23b receipt among them) and every release
    file of the frozen start (the goal23c package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md,
    goal21d-static-review.md and, since the Goal 23 in-game acceptance, GOAL23C-ACCEPTANCE.md) are pinned at their Goal24A start hash (baseline files) instead of
    any receipt hash or any earlier start hash. One path never carries two hashes. Returns (protected, repinned) where repinned maps a record to the pin the goal23c
    packager set at its Goal23C start hash, for the records that changed between the two starts (acceptance checklists only)."""
    goal23c_start = read(GOAL23C_BASELINE)
    out = dict(goal23c_protected_paths(goal23c_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'], 'Start drift path is not a frozen file: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal23c_start['files'].get(p))
        if earlier is not None and earlier != base['files'][p]: repinned[p] = earlier
        out[p] = base['files'][p]
    assert all(p.endswith('-ACCEPTANCE.md') for p in repinned), 'A non-checklist pin changed between the Goal23C and Goal24A starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal23c_start):
    """{path: {receipts, start_sha256, goal23c_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal23c receipt'] = base['previous_receipt_protected_paths'][p]
        start = base['files'][p]
        newest = receipts.get('goal23c receipt')
        if p in base['previous_receipt_evidence_drift']:
            explanation = ('Appended to after the goal23c receipt hashed it (the Goal 23 in-game acceptance results of 2026-10-18); the goal23c receipt hash is older than the '
                           'start hash. Frozen at the start hash; this batch must not change it and the goal23c receipt is not rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21 and Goal 22 in-game acceptance result lines, the O1 record notes or the thorium '
                           'follow-up section); the goal23c receipt does not hash it. Frozen at the Goal24A start hash; this batch must not change it and no earlier '
                           'receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal23c) records the start hash. Frozen at '
                           'the start hash; this batch must not change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal23c package; the goal23c receipt hash is older than the start hash. Frozen at the start hash; this batch '
                           'must not change it and the goal23c receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal23c_start_sha256=goal23c_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned:
            entry['repinned_from_goal23c_start_pin_sha256'] = repinned[p]
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
    if p in MODIFIED_TOOLS: return 'tools-modified'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    return None


def provider_keys(lines):
    """The language keys the given NtmLanguageProvider lines carry (items and blocks through their constants, plain keys), and the lines that carry none."""
    keys, other = [], []
    for raw in lines:
        line = raw.strip()
        m = PROVIDER_ADD_ITEM.match(line)
        if m: keys.append('item.hbmsntm.'+m.group(1).lower()); continue
        m = PROVIDER_ADD_BLOCK.match(line)
        if m: keys.append('block.hbmsntm.'+m.group(1).lower()); continue
        m = PROVIDER_ADD_KEY.match(line)
        if m: keys.append(m.group(1)); continue
        other.append(line)
    return keys, other


def assembly_row(text, rid, neo):
    """{setup, output [name, count], inputs [[kind, name, count]], has_ex, count} of `new GenericRecipe("rid")` in NEO (neo=True) or the original source, or None."""
    text = text.replace('\r\n', '\n')
    found = re.findall(r'new GenericRecipe\("%s"\)(.*?);[ \t]*\n' % re.escape(rid), text, re.S)
    if not found: return None
    stmt = found[0]
    setup = re.search(r'\.setup\((\d+), (\d+)\)', stmt)
    out = re.search(r'\.outputItems\(new ItemStack\(([^,]+?), (\d+)\)\)', stmt)
    start = stmt.find('.inputItems(')
    if not (setup and out) or start < 0: return None
    begin, depth, end = start+len('.inputItems'), 0, None
    for i in range(begin, len(stmt)):
        if stmt[i] == '(': depth += 1
        elif stmt[i] == ')':
            depth -= 1
            if depth == 0: end = i; break
    if end is None: return None
    inputs = []
    for arg in split_args(stmt[begin+1:end]):
        if neo:
            m = (re.match(r'^new ComparableStack\(Ntm(?:Items|Blocks)\.(\w+)\.get\(\), (\d+)\)$', arg), re.match(r'^NtmItems\.castPlateIngredient\(CastPlateItem\.Type\.(\w+), (\d+)\)$', arg))
            if m[0]: inputs.append(['item', m[0].group(1), int(m[0].group(2))])
            elif m[1]: inputs.append(['cast', m[1].group(1), int(m[1].group(2))])
            else: inputs.append(['?', arg, 0])
        else:
            m = (re.match(r'^new OreDictStack\((.+), (\d+)\)$', arg), re.match(r'^new ComparableStack\(Mod(?:Items|Blocks)\.(\w+), (\d+)\)$', arg))
            if m[0] and m[0].group(1) in ASSEMBLY_TRANSLATION: inputs.append([*ASSEMBLY_TRANSLATION[m[0].group(1)], int(m[0].group(2))])
            elif m[1]: inputs.append(['item', m[1].group(1).upper(), int(m[1].group(2))])
            else: inputs.append(['?', arg, 0])
    name = out.group(1)
    name = re.sub(r'^Ntm(?:Items|Blocks)\.(\w+)\.get\(\)$', r'\1', name) if neo else re.sub(r'^Mod(?:Items|Blocks)\.(\w+)$', lambda m: m.group(1).upper(), name)
    return dict(setup=[int(setup.group(1)), int(setup.group(2))], output=[name, int(out.group(2))], inputs=inputs, has_ex='.inputItemsEx(' in stmt, count=len(found))


def translate_craft_key(expr):
    """The NEO recipe-JSON ingredient for an original crafting-manager key expression (None when the table does not know it)."""
    m = re.fullmatch(r'Mod(?:Items|Blocks)\.(\w+)', expr)
    if m: return {'item': 'hbmsntm:'+m.group(1)}
    return {'STEEL.plate()': {'tag': 'c:plates/steel'}, 'B.ingot()': {'item': 'hbmsntm:ingot_boron'}}.get(expr)


def original_craft_row(text, output, count, discriminator):
    """{pattern, key, result} of the single original addRecipeAuto row producing `output` x `count` (and holding the discriminator), or None."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.search(r'addRecipeAuto\(new ItemStack\(Mod(?:Items|Blocks)\.(\w+), (\d+)\), new Object\[\] \{ (.*) \}\);', line)
        if not m or m.group(1) != output or int(m.group(2)) != count: continue
        if discriminator and discriminator not in line: continue
        tokens = split_args(m.group(3))
        pattern = [t[1:-1] for t in tokens if t.startswith('"')]
        rest = [t for t in tokens if not t.startswith('"')]
        key = {rest[i].strip("'"): translate_craft_key(rest[i+1]) for i in range(0, len(rest)-1, 2)}
        rows.append(dict(pattern=pattern, key=key, result=dict(count=count, id='hbmsntm:'+output)))
    return rows[0] if len(rows) == 1 else None


def dial_defaults(text):
    """{key string: default text} of the RBMKKeys enum of the original RBMKDials."""
    return {m.group(1): m.group(2) for m in re.finditer(r'KEY_\w+\("(\w+)", ([\w.]+)\)', text)}


def number(text):
    return float(text.rstrip('DdLlFf')) if re.fullmatch(r'-?[\d.]+[DdLlFf]?', text) else text == 'true' if text in ('true', 'false') else text


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
    goal23c_start = read(GOAL23C_BASELINE)

    # 1. Heads: the clean original at aee05a40f (it moved from 6a11998d), NEO still at the start commit (Goal24A commits nothing), the recorded clean start.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_recorded_head'] == SOURCE_PREVIOUS and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX) and base['target_status'] == '', 'The frozen start is not the clean Goal 24 planning commit'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 24 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    assert prior_receipt['source_commit'] == SOURCE_PREVIOUS, 'The goal23c receipt records another original commit than the snapshot commit'
    assert base['pending_small_fixes'] == [], 'The frozen start has a pending small fix'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and base['start_content']['uncommitted'].startswith('none'), 'Baseline start content differs'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal24A: '+head
    closeout = git_ro(ROOT, 'rev-parse', 'HEAD~1').strip()
    assert closeout.startswith(GOAL23_CLOSEOUT), 'NEO HEAD~1 is not the Goal 23 close-out commit'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b',
                                                          'goal22c', 'goal22d', 'goal23a', 'goal23b'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] and startup['target_head'] == start_head and startup['target_clean'] is True \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) and startup['source_head'] == SOURCE_HEAD \
        and startup['source_delta_entries'] == len(base['source_delta_name_status']) and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'] and startup['generated_resources_verified'] == base['stamp_state']['generated_resources_verified'], \
        'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_verified'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal23c generated tree'
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal23c package, every old release file and the protected evidence.
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal23c receipt list + the goal23c package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal23c receipt count + the goal23c release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal23c receipt'
    # The only goal23c receipt record that drifted before the start: the Goal 23 acceptance checklist, appended after the receipt (the in-game results).
    assert sorted(base['previous_receipt_evidence_drift']) == ['migration/GOAL23C-ACCEPTANCE.md'], 'The goal23c receipt evidence drifted differently at the start: '+str(
        sorted(base['previous_receipt_evidence_drift']))
    for p, d in base['previous_receipt_evidence_drift'].items():
        assert d['receipt'] == prior_receipt['report_sha256'][p] and d['now'] == base['files'][p], 'previous_receipt_evidence_drift differs from the receipt or the frozen file: '+p
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal23c_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal23c receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal24a. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal24A start that the owner table does not list (production outside the 29 modified Java files, the 18 new classes, the 40 '
         'resources, zh_cn.json and the mapping, a protected record, an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal24A start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD] + GENERATED + SHARED_RECORDS + REPORTS[:1]: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in MODIFIED_TOOLS: assert p in base['files'], 'Expected a start tool, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION if p.startswith('src/')})
    need(not outside, 'src/main change outside the 29 modified and 18 new Java files, the 40 resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    need({p: h for p, h in baselines_now.items() if p != SNAPSHOT_NEW} == start_baselines, 'An existing snapshot was added or changed (only '+SNAPSHOT_NEW+' may be new)')
    need(SNAPSHOT_NEW in baselines_now, 'new snapshot missing: '+SNAPSHOT_NEW+' (run.ps1 snapshot --output ...)')
    assert sha(ROOT/SNAPSHOT_OLD) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT_OLD, 'review-6a11998d5852 snapshot changed'
    production_changed = [p for p in PRODUCTION if p in changes]

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

    # Production Java facts: insert-only registration files, every line edit counted, and the exact content edits of the 24A-2 remainders.
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
    # Language provider: the added lines carry exactly the 17 new keys (items and blocks through constants), the two changed fluid names replace their old lines.
    provider_added, provider_changed = [], []
    if PROVIDER in added_lines:
        keys_added, other = provider_keys(added_lines[PROVIDER])
        keys_removed, _ = provider_keys(removed_lines[PROVIDER])
        provider_changed = sorted(keys_removed)
        provider_added = sorted(k for k in keys_added if k not in provider_changed)
        stray = [l for l in other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} adds lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(keys_added) == len(set(keys_added)), f'{PROVIDER} adds a language key twice')
        need(provider_added == sorted(KEYS), f'{PROVIDER} adds the language keys {provider_added}, expected {sorted(KEYS)}')
        need(provider_changed == sorted(CHANGED_KEYS) and set(provider_changed) <= set(keys_added),
             f'{PROVIDER} replaces the language lines {provider_changed}, expected the two fluid names {sorted(CHANGED_KEYS)} (removed and re-added)')
    # The 24A-2 content edits: five vanilla hazard rows, the FluidTrait pair, the PERMA_SCRAP constant, the screwdriver base class.
    if HAZARD_REGISTRY in start_text and (ROOT/HAZARD_REGISTRY).is_file():
        stripped_removed = {l.strip() for l in removed_lines.get(HAZARD_REGISTRY, [])}
        five = ['HazardSystem.register(Items.GOLD_INGOT, makeData(BLINDING, 4F));', 'HazardSystem.register(Items.BLAZE_POWDER, makeData(HOT, 4F));',
                'HazardSystem.register(Blocks.GREEN_WOOL, makeData(RADIATION, 150F));', 'HazardSystem.register(Blocks.WHITE_WOOL, makeData(ASBESTOS, 5F));',
                'HazardSystem.register(Items.COAL, makeData(COAL, 1F));']
        need(all(l in stripped_removed for l in five), f'{HAZARD_REGISTRY} does not remove the five NEO-only vanilla rows (gold ingot, blaze powder, green wool, white wool, coal)')
        live = (ROOT/HAZARD_REGISTRY).read_text(encoding='utf-8')
        need(not re.search(r'register\((?:Items\.(?:GOLD_INGOT|BLAZE_POWDER|COAL)|Blocks\.(?:GREEN|WHITE)_WOOL),', live), f'{HAZARD_REGISTRY} still registers one of the five vanilla rows')
        need(len(re.findall(r'register\(item\(DEBRIS_FUEL\), makeData\(\)\.addEntry\(RADIATION, 500F\)\.addEntry\(HOT, 5F\)\)', live)) == 1,
             f'{HAZARD_REGISTRY} does not register debris_fuel with RADIATION 500 and HOT 5 exactly once')
    if FLUID_TRAIT in start_text and (ROOT/FLUID_TRAIT).is_file():
        live, old = (ROOT/FLUID_TRAIT).read_text(encoding='utf-8'), start_text[FLUID_TRAIT].decode('utf-8')
        need(all(old.count(f'registerTrait("{t}"') == 2 and live.count(f'registerTrait("{t}"') == 1 for t in ('heatable', 'coolable')),
             f'{FLUID_TRAIT} does not remove exactly the duplicated heatable / coolable registrations (start twice, now once)')
    if ZIRNOX_DEBRIS in start_text and (ROOT/ZIRNOX_DEBRIS).is_file():
        live = (ROOT/ZIRNOX_DEBRIS).read_text(encoding='utf-8')
        need('PERMA_SCRAP' in start_text[ZIRNOX_DEBRIS].decode('utf-8') and 'PERMA_SCRAP' not in live and live.count('RBMKDials.getPermaScrap()') == 1,
             f'{ZIRNOX_DEBRIS} does not replace the PERMA_SCRAP constant by RBMKDials.getPermaScrap() exactly once')
    # Turbofan adaptation (planning decision 2026-10-19): the redstone probe iterates the 1-block port cells (getPortProxies), where the start iterated getConPos (the
    # cells 2 blocks out); the original probes getConPos(), which upstream moved to the port cells in 5ef7607e0 (TileEntityMachineTurbofan.java:112-122, :193-195).
    turbofan = None
    if TURBOFAN in start_text and (ROOT/TURBOFAN).is_file():
        live, old = (ROOT/TURBOFAN).read_text(encoding='utf-8'), start_text[TURBOFAN].decode('utf-8')
        probe = 'for(DirPos pos : this.getConPos()) {\n            if(this.level.hasChunkAt(pos.makeCompat()) && this.level.hasNeighborSignal(pos.makeCompat()))'
        probe_now = 'for(DirPos pos : getPortProxies(this.worldPosition, this.getBlockState().getValue(DummyableBlock.FACING))) {\n            if(this.level.hasChunkAt(pos.makeCompat()) && this.level.hasNeighborSignal(pos.makeCompat()))'
        crlf = lambda t: t.replace('\r\n', '\n')
        need(crlf(old).count(probe) == 1 and crlf(live).count(probe_now) == 1 and probe not in crlf(live),
             f'{TURBOFAN} does not move the redstone probe loop from getConPos to getPortProxies exactly once (start loop gone, new loop present once)')
        need(crlf(old).count('DirPos[] getConPos(') == crlf(live).count('DirPos[] getConPos(') == 1 and edit_summary[TURBOFAN]['removed'] == 1 and len(added_lines[TURBOFAN]) == 2,
             f'{TURBOFAN} changes more than the probe loop and one comment line (getConPos and connections must stay): {edit_summary[TURBOFAN]}')
        turbofan = dict(neo=TURBOFAN, original=[O_TURBOFAN], original_references={k: f'{path}:{original_line(path, token)}' for k, (path, token) in ORIGINAL_REFS.items() if k.startswith('turbofan_')},
                        edit_counts=edit_summary[TURBOFAN],
                        behaviour_change='Intentional behaviour change of 24A: old NEO behaviour powered the machine from the cell 2 blocks out (getConPos), the '
                                         'new behaviour reads the adjacent 1-block port cell (upstream aee05a40f, changelog "redstone detection offset outwards"); existing saves '
                                         'with redstone 2 blocks out must move it to the port cell. getConPos and the pipe/cable connections are unchanged.')
    modified_tools = {}
    for p in MODIFIED_TOOLS:
        if (ROOT/p).is_file() and p in changes: modified_tools[p] = dict(before_sha256=base['files'][p], after_sha256=sha(ROOT/p))
    if (ROOT/MODIFIED_TOOLS[2]).is_file():
        need((ROOT/MODIFIED_TOOLS[2]).read_text(encoding='utf-8').count('redstone_probe_at_connections') >= 1, MODIFIED_TOOLS[2]+' does not carry the mutation redstone_probe_at_connections')
    # Screwdriver: NEO registrations and the ToolingItem contract against the original (ModItems.java:3709-3710, ItemTooling.java:30-40, ItemCraftingDegradation.java:12-14).
    o_mod_items, o_tooling, o_degradation = original_text(O_MOD_ITEMS), original_text(O_TOOLING), original_text(O_DEGRADATION)
    original_screwdriver = dict(
        durability=int(re.search(r'screwdriver = new ItemTooling\(ToolType\.SCREWDRIVER, (\d+)\)', o_mod_items).group(1)),
        durability_desh=int(re.search(r'screwdriver_desh = new ItemTooling\(ToolType\.SCREWDRIVER, (\d+)\)', o_mod_items).group(1)),
        stack=int(re.search(r'setMaxStackSize\((\d+)\)', o_degradation).group(1)), no_repair='this.setNoRepair();' in o_degradation,
        wear_only_on_success=bool(re.search(r'if\(\(\(IToolable\)b\)\.onScrew\([^\n]*\) \{\s*if\(this\.getMaxDamage\(\) > 0\)\s*stack\.damageItem\(1, player\);\s*return true;', o_tooling)))
    assert original_screwdriver == dict(durability=100, durability_desh=0, stack=1, no_repair=True, wear_only_on_success=True), 'The original screwdriver differs: '+str(original_screwdriver)
    screwdriver = None
    if (ROOT/ITEMS).is_file() and (ROOT/TOOLING).is_file():
        items_text, tooling_text = (ROOT/ITEMS).read_text(encoding='utf-8'), (ROOT/TOOLING).read_text(encoding='utf-8')
        sd = re.search(r'SCREWDRIVER = ITEMS\.register\("screwdriver", \(\) -> new ToolingItem\(ToolType\.SCREWDRIVER, new Item\.Properties\(\)(?:\.durability\((\d+)\))?\)\);', items_text)
        sdd = re.search(r'SCREWDRIVER_DESH = ITEMS\.register\("screwdriver_desh", \(\) -> new ToolingItem\(ToolType\.SCREWDRIVER, new Item\.Properties\(\)(?:\.durability\((\d+)\))?\)\);', items_text)
        screwdriver = dict(durability=int(sd.group(1) or 0) if sd else None, durability_desh=int(sdd.group(1) or 0) if sdd else None,
                           stack=1 if 'properties.stacksTo(1)' in tooling_text else None, no_repair='.setNoRepair()' in tooling_text,
                           wear_only_on_success=bool(re.search(r'instanceof IToolable toolableBlock\s*&&\s*toolableBlock\.onScrew\([^\n]*\)\) \{', tooling_text)),
                           neo=[ITEMS, TOOLING], original=[O_MOD_ITEMS, O_TOOLING, O_DEGRADATION],
                           original_references={k: f'{path}:{original_line(path, token)}' for k, (path, token) in ORIGINAL_REFS.items()
                                                if k in ('screwdriver', 'screwdriver_desh', 'tooling_on_use', 'degradation_stack', 'degradation_no_repair')})
        need({k: screwdriver[k] for k in original_screwdriver} == original_screwdriver, f'{ITEMS} / {TOOLING} screwdriver differs from the original: {screwdriver} vs {original_screwdriver}')
    # The original, parsed from the stored blobs at the recorded commit (independent of the worktree's line endings).
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    for p in O_RBMK_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    o_base, o_dials, o_debris = original_text(O_BASE), original_text(O_DIALS), original_text(O_DEBRIS_ENTITY)
    o_defaults = dial_defaults(o_dials)
    assert len(o_defaults) == 25, 'The original RBMKDials no longer lists 25 dials: '+str(len(o_defaults))
    lifetimes_original = {m.group(1): eval('*'.join(m.group(2).replace(' ', '').split('*')), {'__builtins__': {}}) for m in re.finditer(r'case (\w+): return ([\d \*]+);', o_debris)}
    original_rbmk = dict(
        max_heat=int(re.search(r'public double maxHeat\(\) \{\s*return (\d+)D;', o_base).group(1)), tracking_range=int(re.search(r'public int trackingRange\(\) \{\s*return (\d+);', o_base).group(1)),
        heat_floor=int(re.search(r'if\(heat < (\d+)\) heat = (\d+)D;', o_base).group(2)),
        passive_cooling_formula='return min + (max - min) * ((4 - MathHelper.clamp_int(neighbors, 0, 4)) / 4D);' in o_base,
        passive_cooling_outer=float(o_defaults['dialPassiveCooling']), passive_cooling_inner=float(o_defaults['dialPassiveCoolingInner']),
        column_heat_flow=float(o_defaults['dialColumnHeatFlow']), column_height_dial=int(o_defaults['dialColumnHeight']),
        column_height_minus_one=bool(re.search(r'KEY_COLUMN_HEIGHT, 2, 16\) - 1\)', o_dials)), lifetimes_ticks=lifetimes_original,
        debris_fuel_hazard=[float(x) for x in re.search(r'register\(debris_fuel, makeData\(\)\.addEntry\(RADIATION, ([\d.]+)F\)\.addEntry\(HOT, ([\d.]+)F\)\)', original_text(O_HAZARD)).groups()])
    assert original_rbmk == dict(max_heat=1500, tracking_range=15, heat_floor=20, passive_cooling_formula=True, passive_cooling_outer=2.5, passive_cooling_inner=0.1, column_heat_flow=0.2,
                                 column_height_dial=4, column_height_minus_one=True, lifetimes_ticks={'BLANK': 3600, 'ELEMENT': 3600, 'FUEL': 12000, 'GRAPHITE': 18000, 'LID': 600, 'ROD': 1200},
                                 debris_fuel_hazard=[500.0, 5.0]), 'The original RBMK constants differ: '+str(original_rbmk)
    # NEO constants against the original: the column base, the facade, the debris entity, the hazard row and the 21 config dials.
    rbmk = None
    neo_files = ('blockentity/machine/rbmk/RBMKBaseBlockEntity.java', 'blockentity/machine/rbmk/RBMKDials.java', 'entity/projectile/RBMKDebris.java')
    if all((ROOT/J/f).is_file() for f in neo_files) and (ROOT/COMMON_CONFIG).is_file() and (ROOT/HAZARD_REGISTRY).is_file():
        n_base, n_dials, n_debris = ((ROOT/J/f).read_text(encoding='utf-8').replace('\r\n', '\n') for f in neo_files)
        n_config = (ROOT/COMMON_CONFIG).read_text(encoding='utf-8').replace('\r\n', '\n')
        n_hazard = (ROOT/HAZARD_REGISTRY).read_text(encoding='utf-8')
        section = re.search(r'builder\.push\("rbmk"\);(.*?)builder\.pop\(\);', n_config, re.S)
        n_defaults = {m.group(1): m.group(2).strip() for m in re.finditer(r'\.(?:defineInRange|define)\("(\w+)", ([^,)]+)', section.group(1))} if section else {}
        config_defaults_ok = set(n_defaults) == set(o_defaults) - UNREGISTERED_DIALS and all(
            number(n_defaults[k]) == (number(o_defaults[k]) if o_defaults[k] not in ('true', 'false') else o_defaults[k] == 'true') for k in n_defaults if k in o_defaults)
        n_lifetimes = {m.group(1): eval('*'.join(m.group(2).replace(' ', '').split('*')), {'__builtins__': {}}) for m in re.finditer(r'case (\w+) -> ([\d \*]+);', n_debris)}
        hazard_match = re.search(r'register\(item\(DEBRIS_FUEL\), makeData\(\)\.addEntry\(RADIATION, ([\d.]+)F\)\.addEntry\(HOT, ([\d.]+)F\)\)', n_hazard)
        parsed = dict(
            max_heat=int(m.group(1)) if (m := re.search(r'public double maxHeat\(\) \{\s*return (\d+)D;', n_base)) else None,
            tracking_range=int(m.group(1)) if (m := re.search(r'public int trackingRange\(\) \{\s*return (\d+);', n_base)) else None,
            heat_floor=int(m.group(2)) if (m := re.search(r'if\(heat < (\d+)\) heat = (\d+)D;', n_base)) else None,
            passive_cooling_formula='return min + (max - min) * ((4 - Mth.clamp(neighbors, 0, 4)) / 4D);' in n_base,
            passive_cooling_outer=number(n_defaults.get('dialPassiveCooling', '?')), passive_cooling_inner=number(n_defaults.get('dialPassiveCoolingInner', '?')),
            column_heat_flow=number(n_defaults.get('dialColumnHeatFlow', '?')), column_height_dial=int(number(n_defaults.get('dialColumnHeight', '0'))),
            column_height_minus_one=bool(re.search(r'getColumnHeight\(\) \{\s*return NtmConfig\.COMMON\.DIAL_COLUMN_HEIGHT\.get\(\) - 1;', n_dials)),
            lifetimes_ticks=n_lifetimes, debris_fuel_hazard=[float(x) for x in hazard_match.groups()] if hazard_match else None)
        need(parsed == original_rbmk and config_defaults_ok and 'RBMKDials.getColumnHeatFlow()' in n_base and len(n_defaults) == 21,
             f'NEO RBMK constants / config dials differ from the original: {parsed} vs {original_rbmk}; dial defaults ok {config_defaults_ok} ({len(n_defaults)} dials)')
        rbmk = dict(neo=[J+'blockentity/machine/rbmk/RBMKBaseBlockEntity.java', J+'blockentity/machine/rbmk/RBMKDials.java', J+'entity/projectile/RBMKDebris.java', COMMON_CONFIG, HAZARD_REGISTRY],
                    original=[O_BASE, O_DIALS, O_DEBRIS_ENTITY, O_HAZARD], constants=parsed, original_constants=original_rbmk, config_dials=len(n_defaults),
                    config_dial_defaults=n_defaults, unregistered_original_dials=sorted(UNREGISTERED_DIALS),
                    original_references={k: v for k, v in original_refs.items() if k.startswith(('tile_', 'dial_', 'debris_', 'hazard_'))},
                    note='maxHeat 1500, trackingRange 15, heat floor 20, passive cooling inner 0.1 .. outer 2.5 scaled by (4 - neighbours) / 4, heat flow 0.2, '
                         'column height dial 4 = 3 blocks above the core (getColumnHeight() = dial - 1), debris lifetimes BLANK/ELEMENT 3600, FUEL 12000, GRAPHITE 18000, '
                         'LID 600, ROD 1200 ticks, debris_fuel RADIATION 500 + HOT 5; the 21 config dials equal the original keys minus dialSaveDials and the three ReaSim dials.')
    # Imported resources: byte for byte equal to the original worktree file and, up to line endings (OBJ) or exactly (PNG), its stored blob, and to the ownership record.
    imported = {}
    ownership = None
    if need((ROOT/RESOURCE_OWNERSHIP).is_file(), 'record missing: '+RESOURCE_OWNERSHIP):
        ownership = read(ROOT/RESOURCE_OWNERSHIP)
        entries = {a.get('target_path'): a for a in ownership.get('assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(ASSETS), f'{RESOURCE_OWNERSHIP} does not list the {len(ASSETS)} resources at {SOURCE_HEAD[:8]}')
        need(all(entries.get(t, {}).get('source_path') == o for t, o in ASSETS.items()), f'{RESOURCE_OWNERSHIP} source paths differ from the layout rules of the owner table')
    if (OUT/'review-new-files.txt').is_file():
        listed = {l.strip() for l in (OUT/'review-new-files.txt').read_text(encoding='utf-8').splitlines() if l.strip()}
        need(listed == (set(NEW_JAVA) - {RBMK_TESTS}) | set(ASSETS), 'review-new-files.txt differs from the 17 new classes + 40 resources of the owner table: '+str(sorted(listed ^ ((set(NEW_JAVA) - {RBMK_TESTS}) | set(ASSETS)))[:6]))
    for target, original in ASSETS.items():
        if not (ROOT/target).is_file(): continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        entry = {a.get('target_path'): a for a in (ownership or {}).get('assets', [])}.get(target, {})
        imported[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size,
                                original_worktree_sha256=sha(SOURCE/original), original_blob_sha256=hashlib.sha256(blob).hexdigest(), original_blob_bytes=len(blob),
                                line_endings_converted_from_blob=blob != checked_out, source_last_change_commit=entry.get('source_last_change_commit'))
        need((ROOT/target).read_bytes() == checked_out, f'{target} is not byte-identical to the original worktree file {original}')
        if target.endswith('.obj'):
            # The original worktree is clean at SOURCE_HEAD, so its OBJ is the checked-out original; on this Windows checkout it carries CRLF where the stored blob
            # has LF (autocrlf), which earlier batches imported as the worktree bytes. The blob must match up to that line-ending conversion.
            need(blob.replace(b'\r\n', b'\n') == (ROOT/target).read_bytes().replace(b'\r\n', b'\n'), f'{target} differs from the {SOURCE_HEAD[:8]} blob of {original} beyond line endings')
        else:
            need(checked_out == blob, f'{target} is not byte-identical to the stored blob of {original} at {SOURCE_HEAD[:8]}')
        if entry:
            need(entry.get('source_path') == original and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('bytes') == (ROOT/target).stat().st_size,
                 f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original path: {target}')
    # features.json: the new rbmk-core group, the reviewed_source_commit advance of the 51 groups and the notes.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_PREVIOUS for f in start_features.values()), 'A start mapping group was not at the recorded original commit 6a11998d'

    # 4. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_delta = dict(added=sorted(KEYS), removed=[], changed=[])
    expected_en_delta = dict(expected_delta, changed=sorted(CHANGED_KEYS))
    need(en_delta == expected_en_delta, 'generated en_us.json delta is not the 17 new keys + the 2 changed fluid names: '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_delta, 'zh_cn.json delta is not the 17 new keys (all old keys unchanged): '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_en_delta, 'zh_cn-map.json delta is not the 17 new keys + the 2 changed fluid entries: '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal23c totals {totals} + {len(KEYS)}')
    need(all(en_now.get(k) == v for k, v in CHANGED_KEYS.items()), f'generated en_us.json does not hold the two changed fluid names {CHANGED_KEYS}')
    language_kinds, original_text_checked = {}, False
    if map_delta == expected_en_delta and en_delta == expected_en_delta:
        language_kinds = dict(Counter(map_now[k].get('kind') for k in KEYS))
        need(language_kinds == {k: v for k, v in EXPECTED_KINDS.items() if v}, f'zh_cn-map.json kinds of the new entries are {language_kinds}, expected {EXPECTED_KINDS}')
        o_en, o_zh = lang_file(O_LANG_EN), lang_file(O_LANG_ZH)
        bad = []
        for k, source_key in KEYS.items():
            e = map_now[k]
            if e.get('target_en') != en_now.get(k) or e.get('target_zh') != zh_now.get(k): bad.append(k)
            elif source_key is None:
                if e.get('kind') != 'local' or not e.get('reason'): bad.append(k)
            elif e.get('kind') != 'upstream' or e.get('source_key') != source_key or e.get('source_zh') != e.get('target_zh') or e.get('source_en') != e.get('target_en'): bad.append(k)
            elif e.get('source_en') != o_en.get(source_key) or e.get('source_zh') != o_zh.get(source_key): bad.append(k)
        for k, text in CHANGED_KEYS.items():
            e = map_now[k]
            old = map_start[k]
            if e.get('source_en') != text or e.get('target_en') != text or e.get('source_en') != o_en.get(k) or old.get('source_en') == text or e.get('source_zh') != old.get('source_zh') \
                    or e.get('target_zh') != old.get('target_zh') or e.get('source_zh') != o_zh.get(k): bad.append(k)
        need(not bad, 'zh_cn-map.json entries do not match en_us.json / zh_cn.json, the original en_US.lang / zh_CN.lang values at aee05a40f or the expected source keys: '+str(bad))
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal23c generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected blockstate, model, loot, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+TAG_ENTRY] + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, the block tag file and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # Recipes: the seven crafting recipes (computed from the generated JSON) against the original CraftingManager rows; no recipe produces the skipped outputs.
    o_crafting = original_text(O_CRAFTING)
    crafting, crafting_bad = {}, []
    for rid, (output, count, discriminator) in CRAFTING.items():
        o_row = original_craft_row(o_crafting, output, count, discriminator)
        assert o_row is not None and all(v is not None for v in o_row['key'].values()), f'The original crafting row for {rid} could not be parsed or translated: {o_row}'
        path = ROOT/GENERATED_ROOT/'data/hbmsntm/recipe'/(rid+'.json')
        if not path.is_file(): continue
        data = read(path)
        neo_row = dict(pattern=data.get('pattern'), key=data.get('key'), result=data.get('result'))
        crafting[rid] = dict(type=data.get('type'), neo=neo_row, original=o_row, original_reference=original_refs['craft_'+rid])
        if data.get('type') != 'minecraft:crafting_shaped' or neo_row != o_row: crafting_bad.append(rid)
    need(not crafting_bad and len(crafting) == len(CRAFTING), f'crafting recipes differ from the original CraftingManager rows (through the translation table) or are missing: {crafting_bad or sorted(set(CRAFTING) - set(crafting))}')
    skipped_found = []
    for path in sorted((ROOT/GENERATED_ROOT/'data/hbmsntm/recipe').glob('*.json')):
        result = read(path).get('result')
        if isinstance(result, dict) and str(result.get('id', result.get('item', ''))).removeprefix('hbmsntm:') in SKIPPED_OUTPUTS: skipped_found.append(path.name)
    need(not skipped_found, f'a recipe produces a skipped output {SKIPPED_OUTPUTS} (NEO has no graphite block, lead glass or boron glass): {skipped_found}')
    # The assembly row ass.rbmk against the original through the ingredient translation table (the original's inputItemsEx / pool branch is not migrated).
    assembly = {}
    neo_assembly = (ROOT/ASSEMBLY).read_text(encoding='utf-8') if (ROOT/ASSEMBLY).is_file() else ''
    o_row, n_row = assembly_row(original_text(O_ASSEMBLY), 'ass.rbmk', False), assembly_row(neo_assembly, 'ass.rbmk', True)
    assert o_row is not None and o_row['count'] == 1 and o_row['has_ex'] and all(i[0] != '?' for i in o_row['inputs']), f'The original ass.rbmk row could not be parsed: {o_row}'
    if need(n_row is not None and n_row['count'] == 1, f'{ASSEMBLY} has no single GenericRecipe("ass.rbmk") row that parses'):
        need(n_row['setup'] == o_row['setup'] == [100, 100] and n_row['output'] == o_row['output'] == ['RBMK_BLANK', 1] and n_row['inputs'] == o_row['inputs'] and not n_row['has_ex'],
             f'{ASSEMBLY} row ass.rbmk differs from the original (through the translation table): {n_row} vs {o_row}')
        assembly['ass.rbmk'] = dict(neo=n_row, original=o_row, original_reference=original_refs['ass.rbmk'])
    # Mapped paths: every changed path inside the compare inventory must be matched by a feature group.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    if need(FEATURE_GROUP in by_id, 'migration/features.json has no group '+FEATURE_GROUP):
        group_entry = by_id[FEATURE_GROUP]
        need(group_entry.get('status') == 'partial-unverified' and group_entry.get('reviewed_source_commit') == SOURCE_HEAD,
             f'features.json group {FEATURE_GROUP} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in O_RBMK_SOURCES + list(ASSETS.values()) if not feature_matches(group_entry, 'source', p)]
        need(not missing_source, f'features.json group {FEATURE_GROUP} lists in neither source_paths nor source_watch: {missing_source[:4]} ({len(missing_source)} paths)')
        missing_target = [p for p in NEW_JAVA if not feature_matches(group_entry, 'target', p)]
        need(not missing_target, f'features.json group {FEATURE_GROUP} lacks the new classes in target_paths/target_watch: {missing_target}')
        watch = [GENERATED_ROOT+p for p in EXPECTED_GENERATED] + [NEW_TOOLS[0]]
        missing_watch = [p for p in watch if not feature_matches(group_entry, 'target', p)]
        need(not missing_watch, f'features.json group {FEATURE_GROUP} lacks the generated blockstate/model/loot/recipe files or the verifier in target_watch: {missing_watch[:4]} ({len(missing_watch)} paths)')
        absent = [p for p in group_entry.get('source_paths', []) if not (SOURCE/p).is_file()]
        need(not absent, f'features.json group {FEATURE_GROUP} source_paths missing in the original: {absent}')
    if need(FEATURE_ZIRNOX in by_id, 'migration/features.json has no group '+FEATURE_ZIRNOX):
        notes = ' '.join(by_id[FEATURE_ZIRNOX].get('notes', []))
        need('PERMA_SCRAP' in notes and 'RBMKDials.getPermaScrap()' in notes, f'migration/features.json group {FEATURE_ZIRNOX} notes do not mention PERMA_SCRAP / RBMKDials.getPermaScrap()')
    if need(FEATURE_MATERIALS in by_id, 'migration/features.json has no group '+FEATURE_MATERIALS):
        need('debris_fuel' in ' '.join(by_id[FEATURE_MATERIALS].get('notes', [])), f'migration/features.json group {FEATURE_MATERIALS} notes do not mention debris_fuel')
    need(set(by_id) == set(start_features) | {FEATURE_GROUP}, 'features.json group ids are not the start ids + '+FEATURE_GROUP+': '+str(sorted(set(by_id) ^ (set(start_features) | {FEATURE_GROUP}))))
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))

    # 24A-1: the classification of the 26 changed original files against git's name-status of the original range.
    name_status = {}
    for line in base['source_delta_name_status']:
        kind, _, path = line.partition('\t')
        name_status[path] = {'M': 'modified', 'A': 'added'}[kind]
    assert git_ro(SOURCE, 'diff', '--name-status', '-M', SOURCE_PREVIOUS, SOURCE_HEAD).splitlines() == base['source_delta_name_status'], 'The original range 6a11998d..aee05a40f differs from the frozen start'
    classification_summary = classification_entries = None
    if need((ROOT/CLASSIFICATION).is_file(), 'record missing: '+CLASSIFICATION):
        classification = read(ROOT/CLASSIFICATION)
        classification_entries = {e['path']: e for e in classification['entries']}
        need(classification.get('baseline_source_commit') == SOURCE_PREVIOUS and classification.get('reviewed_source_commit') == SOURCE_HEAD
             and classification.get('neo_commit') == start_head, f'{CLASSIFICATION} records other commits than 6a11998d / aee05a40f / the start commit')
        need(len(classification['entries']) == len(classification_entries) == len(name_status) and {p: e['change'] for p, e in classification_entries.items()} == name_status,
             f'{CLASSIFICATION} entries differ path-for-path from git diff --name-status -M 6a11998d aee05a40f ({len(name_status)} files)')
        classification_summary = dict(Counter(e['category'] for e in classification['entries']))
        need(classification.get('summary') == classification_summary, f'{CLASSIFICATION} summary differs from the entry categories: {classification.get("summary")} vs {classification_summary}')

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
    rbmk_test_names = sorted(GAMETEST_METHOD.findall((ROOT/RBMK_TESTS).read_text(encoding='utf-8'))) if (ROOT/RBMK_TESTS).is_file() else []
    rbmk_annotations = annotations(ROOT/RBMK_TESTS) if (ROOT/RBMK_TESTS).is_file() else 0
    hazard_names_now = set(GAMETEST_METHOD.findall((ROOT/HAZARD_TESTS).read_text(encoding='utf-8')))
    hazard_names_start = set(GAMETEST_METHOD.findall((START_FILES/HAZARD_TESTS).read_text(encoding='utf-8')))
    hazard_new = sorted(hazard_names_now - hazard_names_start)
    need(not (hazard_names_start - hazard_names_now), f'{HAZARD_TESTS} lost GameTest methods: {sorted(hazard_names_start - hazard_names_now)}')
    need(bool(rbmk_test_names) and rbmk_annotations == len(rbmk_test_names), f'{RBMK_TESTS} holds {rbmk_annotations} @GameTest annotations and {len(rbmk_test_names)} parsed methods')
    need(gametest_added == len(rbmk_test_names) + len(hazard_new) == rbmk_annotations + (annotations(ROOT/HAZARD_TESTS) - annotations(START_FILES/HAZARD_TESTS)),
         f'GameTest sources grew by {gametest_added} tests, RBMKCoreGameTests holds {len(rbmk_test_names)} and HazardGameTests {len(hazard_new)} new methods (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in rbmk_test_names), 'GameTest log lacks "[hbm-rbmk-core] <name> passed" for: '+str([n for n in rbmk_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24a/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24a/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal24a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal24a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal24a/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA + OPTIONAL_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal24a/production-vs-start.diff') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal23c final run plus the Goal24A verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert NEW_SUITE not in reference_suites, 'The Goal24A suite is already in the goal23c final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal24a/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal23c final set + the Goal24A verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal24a/'+VERIFY_REPORT+' (tools/migration/verify_goal24a_rbmk_core.py report)'):
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
        verifier_references = sorted(set(re.findall(r'(?:RBMKDials|TileEntityRBMK\w*|RBMK\w+|EntityRBMKDebris|ItemRBMKLid|ItemTooling|ItemCraftingDegradation|CraftingManager|AssemblyMachineRecipes|HazardRegistry|ModItems|ModBlocks)\.java:\d+(?:-\d+)?',
                                                      json.dumps(report, ensure_ascii=False))))
    # Compare against the old snapshot (original +7/~19, target = the goal23c compare target set + this batch) and against the new snapshot (0/0/0 everywhere).
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT_OLD and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'previous receipt compare target set is incomplete'
    prior_cmp = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_compare['sha256'], 'previous compare.json changed'
    assert compare_paths(prior_cmp['changes']['target']['added']) | compare_paths(prior_cmp['changes']['target']['modified']) == previous_target, \
        'previous compare.json target set differs from its receipt'
    expected_target = sorted(previous_target | {p for p in changes if in_compare_inventory(p)})
    compare_old = compare = None
    expected_source_counts = {k: sum(1 for v in name_status.values() if v == k) for k in ('added', 'modified')} | {'removed': 0}

    def compare_owners(p):
        return set(prior_compare['target_owners'].get(p, [])) | ({OWNER} if p in changes else set())

    if need((OUT/COMPARE_OLD).is_file(), 'evidence missing: build/migration/goal24a/'+COMPARE_OLD+' (compare against '+SNAPSHOT_OLD+'; expected original +%d/~%d/-0 and target set: %d paths)' % (
            expected_source_counts['added'], expected_source_counts['modified'], len(expected_target))):
        cmp_old = read(OUT/COMPARE_OLD)
        need(cmp_old['kind'] == 'migration-delta' and cmp_old['baseline_source_commit'] == SOURCE_PREVIOUS and cmp_old['current_source_commit'] == SOURCE_HEAD, \
            COMPARE_OLD+' is not the 6a11998d snapshot against aee05a40f')
        counts = {side: {k: len(cmp_old['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(counts['source'] == expected_source_counts, f'{COMPARE_OLD} source is {counts["source"]}, expected {expected_source_counts}')
        source_paths = compare_paths(cmp_old['changes']['source']['added']) | compare_paths(cmp_old['changes']['source']['modified'])
        need(source_paths == set(name_status), f'{COMPARE_OLD} source set differs from the 26 classified files: extra %s, missing %s' % (
            sorted(source_paths - set(name_status)), sorted(set(name_status) - source_paths)))
        target = cmp_old['changes']['target']
        need(not target['removed'], COMPARE_OLD+' target removed: '+str(target['removed']))
        need(not cmp_old['unmapped_changes']['target'], COMPARE_OLD+' reports unmapped target changes: '+str(cmp_old['unmapped_changes']['target']))
        need(set(compare_paths(cmp_old['unmapped_changes']['source'])) <= set(name_status), COMPARE_OLD+' reports unmapped source changes outside the classification')
        need(not cmp_old['removed_feature_ids'] and not cmp_old['manifest_missing_files'], COMPARE_OLD+' reports removed features or missing files')
        listed = sorted(p for p in compare_paths(target['added']) | compare_paths(target['modified']) if not p.endswith('/.migration-stamp.json'))
        need(listed == expected_target, COMPARE_OLD+' target set differs: extra %s, missing %s' % (sorted(set(listed) - set(expected_target)), sorted(set(expected_target) - set(listed))))
        if (OUT/'upstream-delta.json').is_file():
            delta = read(OUT/'upstream-delta.json')
            need(compare_paths(delta['changes']['source']['added']) | compare_paths(delta['changes']['source']['modified']) == source_paths, 'upstream-delta.json source set differs from '+COMPARE_OLD)
        compare_old = dict(path=(OUT/COMPARE_OLD).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE_OLD), snapshot=SNAPSHOT_OLD, counts=counts,
                           unmapped_source=len(cmp_old['unmapped_changes']['source']), target_owners={p: sorted(compare_owners(p)) for p in listed})
        evidence[compare_old['path']] = compare_old['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT_NEW).is_file():
        snap = read(ROOT/SNAPSHOT_NEW)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '', \
            SNAPSHOT_NEW+' is not a clean observation of the original at aee05a40f')
        need(snap['target']['commit'] == start_head, SNAPSHOT_NEW+' records another target commit than the start commit')
        need(len(snap['manifest']['features']) == len(features) and {f['id'] for f in snap['manifest']['features']} == set(by_id), SNAPSHOT_NEW+' does not hold the 52 mapping groups of features.json')
        snapshot = dict(path=SNAPSHOT_NEW, bytes=(ROOT/SNAPSHOT_NEW).stat().st_size, sha256=sha(ROOT/SNAPSHOT_NEW), new_snapshot=True, source_commit=snap['source']['commit'],
                        previous=dict(path=SNAPSHOT_OLD, sha256=base['snapshot']['sha256']))
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal24a/'+COMPARE+' (compare against '+SNAPSHOT_NEW+': original and target 0/0/0, no unmapped change)'):
        cmp = read(OUT/COMPARE)
        need(cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, COMPARE+' is not against the aee05a40f snapshot')
        counts = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(all(v == 0 for side in counts.values() for v in side.values()), COMPARE+' is not 0/0/0 on both sides: '+str(counts))
        need(not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], COMPARE+' reports unmapped changes: '+str(cmp['unmapped_changes']))
        need(not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], COMPARE+' reports removed features or missing files')
        states = Counter(f.get('state') for f in cmp['features'])
        need(len(cmp['features']) == len(features) and dict(states) == {'no-observed-file-change': len(features)}, f'{COMPARE} feature states are {dict(states)}, expected all {len(features)} no-observed-file-change')
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT_NEW, counts=counts, feature_states=dict(states))
        evidence[compare['path']] = compare['sha256']

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal24a.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal23c) package (run build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 40 resources and every compiled class equal the sources.
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [e for e, t in asset_entries.items() if e not in names or not (ROOT/t).is_file() or jar.read(e) != (ROOT/t).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json, the imported resources or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == en_delta == expected_en_delta and zh_jar == zh_delta == expected_delta,
                 f'JAR en_us.json or zh_cn.json delta against the previous package is not the {len(KEYS)} new keys (+ the 2 changed fluid names in en_us.json): en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
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
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 40 imported resources, the generated additions and the modified '
             'en_us.json / zh_cn.json / pickaxe tag are owned; META-INF/MANIFEST.MF is not): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it (for example com/hbm/blocks/machine/rbmk/); never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) == set(changed_java), 'Changed Java sources and goal24a JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, TAG_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + block tag + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal23c_start=sorted(repinned),
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                   insert_lines=insert_summary, edit_counts=edit_summary, rbmk=opt(rbmk, 'constants'), screwdriver=screwdriver and {k: screwdriver[k] for k in original_screwdriver},
                   crafting_recipes=sorted(crafting), assembly_rows=sorted(assembly), classification=classification_summary, gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_rbmk_tests=rbmk_test_names, new_hazard_tests=hazard_new, final_suites_expected=final_expected,
                   compare_old=opt(compare_old, 'counts'), compare=opt(compare, 'counts'), compare_target_expected=len(expected_target),
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta, class_owners=class_owners,
                   protected_paths=len(protected), old_releases_preserved=len(old_releases), preserved_release_files=len(base['old_release_files']),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)

    # The receipt: assembled in both modes (None where the evidence does not exist yet in --check); only the real run writes it, and there every need() above raised.
    dest = RELEASE/RELEASE_NAME
    digest = sha(JAR)
    hashes = {p: sha(ROOT/p) for p in reports if (ROOT/p).is_file()}
    planning_paths = [l for l in git_ro(ROOT, 'show', '--name-only', '--format=', start_head).split('\n') if l]
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), language_kinds, len(ASSETS), len(rbmk_test_names), len(hazard_new), gametest_count, len(CHANGED_KEYS)),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=SOURCE_PREVIOUS, target_start_commit=start_head,
                   planning_commit=dict(id=start_head, parent=closeout, paths=planning_paths, message_file='build/migration/goal24a/planning-commit-msg.txt'),
                   goal23_closeout=closeout, commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha,
                                      note='The start tree is HEAD 1114adf5 (the Goal 24 planning commit on top of the pushed Goal 23 close-out commit 09173669) with a clean '
                                           'worktree: no uncommitted earlier batch paths and no pending small fix; build/libs at the start is the goal23c package byte for byte. '
                                           'The original moved from 6a11998d to aee05a40f before the start (24A-1). Paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes], production_unchanged_optional=[p for p in OPTIONAL_JAVA if p not in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary,
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   rbmk=rbmk, screwdriver=screwdriver, turbofan=turbofan, modified_tools=modified_tools,
                   upstream=dict(classification=CLASSIFICATION, baseline_source_commit=SOURCE_PREVIOUS, reviewed_source_commit=SOURCE_HEAD, files=len(name_status),
                                 changed_added=expected_source_counts['added'], changed_modified=expected_source_counts['modified'], categories=classification_summary,
                                 adapted=[dict(path=p, category=e['category'], outcome=e.get('outcome')) for p, e in (classification_entries or {}).items()
                                          if e['category'] in ('neo-adapt-24a', 'neo-counterpart-deferred')],
                                 adapted_language_values={k: dict(old=map_start[k]['target_en'], new=v) for k, v in CHANGED_KEYS.items()}, mapping_groups_advanced=len(start_features),
                                 note='7 commits, 26 files (19 modified, 7 added); none touches an RBMK file or the rows Goal 24 depends on. Adapted: the two English fluid names '
                                      'calcium_chloride and potassium_chloride (en_US.lang spelling fix); the turbofan redstone probe follows upstream (24A scope decision of 2026-10-19: MachineTurbofanBlockEntity probes the port cells). The 51 mapping '
                                      'groups advance reviewed_source_commit to aee05a40f; the new group rbmk-core starts there.'),
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note='15 entries are upstream (13 RBMK names with the original English and Chinese verbatim, the two pheromone traits hbmfluid.trait.glyphidPheromones / '
                                      'modifiedPheromones, tile.rbmk.dodd.heat); 2 are NEO-local (entity.hbmsntm.rbmk_debris, which the original does not have, and '
                                      'desc.misc.holdShiftMoreInfo, the translatable Hold <LSHIFT> hint). hbmfluid.calcium_chloride and potassium_chloride change their English '
                                      'value to the original\'s new spelling (Calcium chloride Solution, Potassium chloride Solution); the Chinese is unchanged.'),
                   recipes=dict(crafting=crafting, assembly=assembly, not_registered=list(SKIPPED_OUTPUTS), anvil_rows=[],
                                original_references={k: v for k, v in original_refs.items() if k.startswith(('craft_', 'ass.'))},
                                note='Seven shaped crafting recipes (lid x4, absorber, reflector, deco_rbmk x8, deco_rbmk_smooth and the blank column from either deco ring) equal the '
                                     'original CraftingManager rows; the moderator and the glass-lid rows are skipped (no graphite block, lead glass or boron glass in NEO: both '
                                     'items are creative-only); no anvil rows (tier 4 is unreachable). ass.rbmk is registered in both enable528 settings with the normal inputs only '
                                     '(no inputItemsEx branch and no pool in NEO).'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report, repinned_since_goal22d_start=prior_receipt['repinned_since_goal22d_start'],
                   repinned_since_goal23a_start=prior_receipt['repinned_since_goal23a_start'], repinned_since_goal23b_start=prior_receipt['repinned_since_goal23b_start'],
                   repinned_since_goal23c_start={p: dict(goal23c_start_pin_sha256=h, goal24a_start_sha256=base['files'][p]) for p, h in repinned.items()},
                   snapshot=snapshot, compare=dict(old=compare_old, new=compare),
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_rbmk_tests=rbmk_test_names, new_hazard_tests=hazard_new,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; the RBMKCoreGameTests cover column placement, heat '
                                      'flow and passive cooling, the dial facade, the lids and the screwdriver, a 2x2 meltdown with debris blocks and entities, the debris block '
                                      'ticks, the debris entity, the recipes, the debris_fuel hazard, the screwdriver base class and the 24A-2 remainders; the new HazardGameTests '
                                      'methods cover the reacher scan, the creative precedence and the five removed vanilla rows; no client (lid and debris renderers, DODD overlay, '
                                      'creative tabs and JEI are not rendered), no real player, no saved world, no real-time observation of a burning or radiating debris field.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}, SNAPSHOT_OLD: sha(ROOT/SNAPSHOT_OLD)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier '
                            'with in-memory mutations, the final old-suite rerun, compare against the review-6a11998d5852 snapshot (original +7/~19) and against the new '
                            'review-aee05a40f10f snapshot (0/0/0), two independent static reviews and the 24A-1 classification recheck. No in-game client test was run: the '
                            'column, lid and debris rendering, the DODD overlay, creative tabs and JEI in either language, a real player crafting the columns or assembling '
                            'ass.rbmk, multiplayer or a dedicated server beyond GameTest, and a client/server config mismatch are unverified; GOAL24A-ACCEPTANCE.md is written but '
                            'not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, start_jar_sha), 'build/libs JAR is an older JAR'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal24a JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal23c package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
