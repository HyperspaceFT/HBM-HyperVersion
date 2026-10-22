"""Package Goal25D (the fourth and last batch of Goal 25, RBMK operation and fuel logistics: the RBMK crane console rbmk_crane_console, a two-box DummyableBlock (RBMKCraneConsoleBlock with the
core RBMKCraneConsoleBlockEntity: the crane position, the lift progress, the detection box of the operator, the five crane keys, the load / unload through IRBMKLoadable, the span search above the
reactor, the persistence and the sync) with its OBJ renderer and item form (RenderCraneConsole), the RBMKBaseBlockEntity.craneIndicator that the RBMK console shows, the rbmk_tool crane branch, five
crane KeyMappings (up / down / left / right / enter) with the client key read through the proxy (getIsKeyPressed), its shaped crafting recipe, five imported resources, six language keys, RBMKCraneGameTests and the 25D unified Goal 25
acceptance checklist GOAL25D-ACCEPTANCE.md, cumulatively on the goal25c package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal25d.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal25d/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal25d/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal25d/baseline.json: NEO HEAD 783b6d13 (the Goal 25 planning commit, local, on top of the pushed Goal 24 close-out commit 17c8062f) PLUS the
UNCOMMITTED Goal25A, Goal25B and Goal25C deliveries (121 status lines, packaged as goal25a, goal25b and goal25c and committed together with 25D after the unified acceptance, GOAL25 decision 2).
Unlike the 25C freeze this one was CAPTURED before any 25D write (capture_start.py: start_status.txt, start_head.txt, start_hashes.txt and baseline-files, 136 verbatim copies of the 121 dirty
start files and 15 clean files the batch planned to touch) and freeze_start.py rebuilt the full start tree from those captures (dirty start files from start_hashes.txt, clean files with a copy from
the copy, the other clean files hashed live). build/libs at the start AND at the freeze IS the goal25c package (baseline build_libs_jar_sha256_at_start / _at_freeze). The original HEAD aee05a40f
did not move since 24A, so there is no upstream classification and no new snapshot. Every change since the start is computed from the baseline file hashes (not from git diff) and must be in the
owner table below; every other path must still equal its start hash. The modified production files are compared with their start bytes (baseline-files; a modified file the freeze did not copy has
NO reproducible start bytes and is reported as pending). The JAR delta against the goal25c package is attributed per entry (goal25d only); any entry without exactly one owner fails. Counts that
records quote (suites, GameTests, generated resources, classes, releases, language keys) are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from
the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal25c, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start for the acceptance checklists,
GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes build/migration/goal24a/main-notes.md (baseline older_receipt_evidence_drift); the goal25a, goal25b and goal25c
receipts differ from nothing at the start (baseline previous_receipt_evidence_drift is empty). They are listed in the receipt as start drift and must still equal their Goal25D start hash; no
receipt is rewritten and no other protected path may drift. The Goal25A, Goal25B, Goal25C and Goal24 records must equal their start hash; migration/GOAL25.md is edited by the main agent
(a shared record), GOAL25D.md is the task book and delivery record (hashed by the receipt) and GOAL25D-ACCEPTANCE.md the unified Goal 25 acceptance checklist (hashed, written, not run).

Like the earlier packagers of 24B..25C this one has a single compare run (build/migration/goal25d/compare.json against the snapshot review-aee05a40f10f.json taken at the end of 24A:
original 0/0/0, target = exactly the goal25c compare target paths (24A-25C, read from build/migration/goal25c/compare.json) plus this batch's compare-inventory paths), no upstream
classification; it adds the rbmk_crane constants (checked against the original and NEO source texts). The Goal25C-only receipt key rbmk_autoloader is dropped."""
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
from package_goal24e import split_args, OneOf, jsonable
from package_goal25c import OUT as GOAL25C_OUT, BASELINE as GOAL25C_BASELINE, protected_paths as goal25c_protected_paths

OUT = ROOT/'build/migration/goal25d'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
START_HASHES = OUT/'start_hashes.txt'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
REFERENCE_PREVIOUS = GOAL25C_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL25C_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal25c/hbmsntm-198A-goal25c.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
# The receipts of the two batches before the previous one: with the previous receipt their changed_files are the uncommitted start (Goal25A, Goal25B and Goal25C deliveries).
OLDER_PREVIOUS_RECEIPTS = [ROOT/'build/migration/releases/goal25a/release.json', ROOT/'build/migration/releases/goal25b/release.json']
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal25d'
RELEASE_NAME = 'hbmsntm-198A-goal25d.jar'
OWNER = 'goal25d'
PLANNING_PREFIX = '783b6d13'
GOAL24_CLOSEOUT = '17c8062f'
START_STATUS_LINES = 121
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'

# Production (owner goal25d), NEW (handoff-packaging.md; builder-report.md names the final classes: if a class is named differently or a helper class is added, edit this
# list, --check reports the difference as an unassigned src/ path).
NEW_JAVA = [J+p+'.java' for p in (
    'blocks/machine/rbmk/RBMKCraneConsoleBlock', 'blockentity/machine/rbmk/RBMKCraneConsoleBlockEntity', 'render/blockentity/RenderCraneConsole', 'gametest/RBMKCraneGameTests')]
(CRANE_BLOCK, CRANE_BE, CRANE_RENDER, CRANE_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails; a review fix may add a file: --check reports it
# as an unassigned src/ path instead of failing silently).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blockentity/machine/rbmk/RBMKBaseBlockEntity', 'blockentity/machine/rbmk/RBMKConsoleBlockEntity', 'blockentity/machine/rbmk/RBMKSlottedBaseBlockEntity',
    'blockentity/machine/rbmk/IRBMKLoadable', 'items/tools/RBMKToolItem', 'handler/HbmKeybinds', 'main/ResourceManager', 'main/ClientProxy', 'blocks/NtmBlocks',
    'blockentity/NtmBlockEntityTypes', 'inventory/NtmCreativeTabs', 'datagen/NtmRecipeProvider', 'datagen/NtmBlockStateProvider', 'datagen/NtmBlockLootTableProvider',
    'datagen/NtmBlockTagProvider', 'datagen/NtmLanguageProvider', 'main/ServerProxy', 'blockentity/machine/rbmk/RBMKStorageBlockEntity')]
(RBMK_BASE_BE, RBMK_CONSOLE_BE, RBMK_SLOTTED_BE, RBMK_LOADABLE, TOOL_ITEM, KEYBINDS, RESOURCE_MANAGER, CLIENT_PROXY, BLOCKS, BLOCK_ENTITY_TYPES, CREATIVE_TABS, RECIPE_PROVIDER,
 BLOCK_STATE_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER, PROVIDER, SERVER_PROXY, RBMK_STORAGE_BE) = MODIFIED_JAVA
# Frozen copies the freeze took that this batch is not expected to change (a change fails as an unassigned path): the keybind receiver chain stays byte-identical to its start.
OPTIONAL_JAVA = []
UNCHANGED_JAVA = [J+p+'.java' for p in ('handler/HbmKeybindsServer', 'network/toserver/KeybindReceiver', 'extprop/HbmPlayerAttachments')]
# Modified sources whose compiled class need not change (comment-only edits that keep the line numbers); every other modified source must show a modified class in the JAR.
SAME_CLASS_JAVA = [RBMK_LOADABLE, RBMK_SLOTTED_BE, RBMK_STORAGE_BE]
NO_CLASS_JAVA = []
# JAR classes whose source is unchanged since the start and that differ from the previous package only in recompiled debug names; none known at the Goal25D start. An entry maps the class to the
# exact Utf8 constants replaced: it is owned as a recompile difference only when its source is unchanged and the previous bytes with exactly these constants replaced equal the new bytes
# (the Goal25B precedent: javap -v shows only LocalVariableTable names).
RECOMPILE_ONLY = {}
RECOMPILE_OWNER = 'recompile-debug-names'
ANVIL_RECIPES = J+'inventory/recipes/anvil/AnvilRecipes.java'
# The registration and datagen files stay insert-only against their start bytes (the Chinese file and the mapping only gain lines too). The five RBMK sources and the tool item below also
# change comments (and, in the console block entity, one start line): they are held to ALLOWED_REMOVED_CODE instead.
STRICT_INSERT_ONLY = [p for p in MODIFIED_JAVA if p not in (RBMK_BASE_BE, RBMK_CONSOLE_BE, RBMK_SLOTTED_BE, RBMK_STORAGE_BE, RBMK_LOADABLE, TOOL_ITEM)] + [ZH_INPUT, LOCALIZATION_RECORD]
# Start CODE lines a non-insert-only file may drop, by prefix (an empty prefix allows only comment lines to go): the console's placeholder column indicator byte is replaced by the real one.
ALLOWED_REMOVED_CODE = {RBMK_BASE_BE: '', RBMK_CONSOLE_BE: 'columns[index].data.putByte("indicator", (byte) 0);', RBMK_SLOTTED_BE: '', RBMK_STORAGE_BE: '', RBMK_LOADABLE: '', TOOL_ITEM: ''}
# The 5 imported original resources: NEO target -> original path, derived by the layout rules of the ownership record (textures/blocks -> textures/block, the OBJs go under models/obj,
# the model textures keep their path).
ASSETS = {
    ASSETS_ROOT+'models/obj/rbmk/crane_console.obj': O_RES+'models/rbmk/crane_console.obj',
    ASSETS_ROOT+'models/obj/rbmk/crane.obj': O_RES+'models/rbmk/crane.obj',
    ASSETS_ROOT+'textures/models/machines/crane_console.png': O_RES+'textures/models/machines/crane_console.png',
    ASSETS_ROOT+'textures/models/machines/rbmk_crane.png': O_RES+'textures/models/machines/rbmk_crane.png',
    ASSETS_ROOT+'textures/block/rbmk/rbmk_crane_console.png': O_RES+'textures/blocks/rbmk/rbmk_crane_console.png',
}
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
TAG_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
GENERATED = [STAMP, EN, GENERATED_ROOT+TAG_ENTRY]
# Generated by runData for this batch (relative to src/generated/resources): the particle-only blockstate, the particle and item models, the loot table, the shaped crafting recipe and its
# advancement (the advancement folder depends on the recipe category, so it is matched by name; exactly one).
EXPECTED_GENERATED_BASE = sorted(['assets/hbmsntm/blockstates/rbmk_crane_console.json', 'assets/hbmsntm/models/block/rbmk_crane_console_particle.json', 'assets/hbmsntm/models/item/rbmk_crane_console.json',
                                  'data/hbmsntm/loot_table/blocks/rbmk_crane_console.json', 'data/hbmsntm/recipe/rbmk_crane_console.json'])
ADVANCEMENT = re.compile(r'data/hbmsntm/advancement/recipes/[a-z_]+/rbmk_crane_console\.json')
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, TAG_ENTRY])
G_CRANE_RECIPE = GENERATED_ROOT+'data/hbmsntm/recipe/rbmk_crane_console.json'
NEW_TOOLS = ['tools/migration/verify_goal25d_rbmk_crane.py', 'tools/migration/package_goal25d.py']
TOOLS = NEW_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal25d-* or GOAL25D-* record is hashed as well.
REPORTS = ['migration/GOAL25D.md', 'migration/GOAL25D-ACCEPTANCE.md', 'migration/goal25d-static-review.md', 'migration/goal25d-localization-review.json',
           'migration/goal25d-resource-ownership.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal25d-[^/]+\.(json|md)|GOAL25D-[^/]+\.md)')
GOAL25_RECORD = 'migration/GOAL25.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md',
                  'migration/RESOURCE-OWNERSHIP.md', GOAL25_RECORD]
# Shared records the batch may leave untouched (RESOURCE-OWNERSHIP.md "if touched"; FOUNDATIONS.md is required: the proxy key read is a base change, main-notes decision 5).
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
# The Goal 25 planning prompt document: no change is expected in this batch (GOAL25D.md is this batch's task book and delivery record, hashed as REPORTS[0]).
PLANNING_FROZEN = ['migration/GOAL25-THREAD-PROMPTS.md']
FROZEN_RECORD = re.compile(r'migration/(GOAL25[ABC][^/]*\.md|goal25[abc]-[^/]+|GOAL24[^/]*\.md|goal24[^/]*)')
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED_BASE + the advancement.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]
# The new language keys: NEO key -> (original key, expected map kind). All six are upstream with the original English and Chinese verbatim (the block name tile.rbmk_crane_console.name,
# en_US.lang:6222 / zh_CN.lang:5347; the five key labels hbm.key.crane*, en_US.lang:1433-1437 / zh_CN.lang:1157-1161: the task book wrote hbm.keys.*, the real prefix is hbm.key).
SOURCE_KEYS = {'block.hbmsntm.rbmk_crane_console': ('tile.rbmk_crane_console.name', 'upstream'),
               'hbmsntm.keys.craneLoad': ('hbm.key.craneLoad', 'upstream'), 'hbmsntm.keys.craneMoveDown': ('hbm.key.craneMoveDown', 'upstream'),
               'hbmsntm.keys.craneMoveLeft': ('hbm.key.craneMoveLeft', 'upstream'), 'hbmsntm.keys.craneMoveRight': ('hbm.key.craneMoveRight', 'upstream'),
               'hbmsntm.keys.craneMoveUp': ('hbm.key.craneMoveUp', 'upstream')}
KEYS = {k: v[0] for k, v in SOURCE_KEYS.items()}
EXPECTED_KINDS = dict(Counter(v[1] for v in SOURCE_KEYS.values()))
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rbmk-crane] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the sessions of the batch.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'capture_start.py', 'freeze_start.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_hashes.txt', 'start_head.txt',
                  'main-notes.md', 'handoff-builder.md', 'builder-report.md', 'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md', 'verifier-report.md', 'review-report.md',
                  'chain.sh', 'make_production_diff.py', 'import_resources.py', 'add_zh.py')
# Review files under OUT (for example the static review's notes or diffs) the main agent names when it knows them; each must exist and is indexed by the receipt. Extend this list from the
# real run (review notes, the builder's and verifiers' progress and scope files, logs ...); --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'builder_compile.log', 'builder_rundata.log', 'builder_build.log', 'builder_pre_rundata_generated.txt',
                   'review-diff.patch', 'review-new-files.txt', 'verifier-progress.md')
GAMETEST_LOG = 'build/migration/goal25d/gametest-final.log'
NEW_SUITE = 'verify_goal25d_rbmk_crane.py --gametest-log build/migration/goal25d/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_CRANE = 'rbmk-crane'
NEW_FEATURES = (FEATURE_CRANE,)
# The groups the snapshot of the end of 24A predates (24B rbmk-fuel, 24C rbmk-reactor, 24D rbmk-control and rbmk-steam, 24E rbmk-console, 25A rbmk-storage and rbmk-recycling,
# 25B rbmk-outgasser, 25C rbmk-autoloader).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser', 'rbmk-autoloader'}
RADIATION_NOTE = ('Goal25D: the crane moves fuel rods, possibly hot and spent, between columns without removing their radiation; the unified Goal 25 acceptance checklist '
                  'GOAL25D-ACCEPTANCE.md must be run only in a separately authorized disposable world. ')
MELTDOWN_NOTE = 'Goal25D: the crane adds no meltdown path of its own; reactor tests stay in disposable worlds. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_TE = ORIGINAL+'tileentity/machine/rbmk/TileEntityCraneConsole.java'
O_BLOCK = ORIGINAL+'blocks/machine/rbmk/RBMKCraneConsole.java'
O_RENDER = ORIGINAL+'render/tileentity/RenderCraneConsole.java'
O_ITEM_RENDER = ORIGINAL+'render/item/ItemRenderLibrary.java'
O_BASE = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKBase.java'
O_CONSOLE = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKConsole.java'
O_TOOL = ORIGINAL+'items/tool/ItemRBMKTool.java'
O_KEYBINDS = ORIGINAL+'handler/HbmKeybinds.java'
O_CLIENT_PROXY = ORIGINAL+'main/ClientProxy.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_MODBLOCKS = ORIGINAL+'blocks/ModBlocks.java'
O_RESOURCE_MANAGER = ORIGINAL+'main/ResourceManager.java'
O_SOURCES = [O_TE, O_BLOCK, O_RENDER, O_ITEM_RENDER, O_BASE, O_CONSOLE, O_TOOL, O_KEYBINDS, O_CLIENT_PROXY, O_CRAFTING, O_MODBLOCKS, O_RESOURCE_MANAGER, O_LANG_EN, O_LANG_ZH]
# The original sources each new mapping group must list (source_paths or source_watch; plus the imported resources).
FEATURE_SOURCES = {FEATURE_CRANE: [O_TE, O_BLOCK, O_RENDER] + list(ASSETS.values())}
# The NEO paths each new mapping group must cover (target_paths or target_watch).
FEATURE_TARGETS = {FEATURE_CRANE: [CRANE_BLOCK, CRANE_BE, CRANE_RENDER, CRANE_TESTS, RESOURCE_MANAGER, KEYBINDS, SERVER_PROXY, NEW_TOOLS[0], NEW_TOOLS[1]]
                   + [GENERATED_ROOT+p for p in EXPECTED_GENERATED_BASE] + list(ASSETS)}
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'crane_class': (O_TE, 'public class TileEntityCraneConsole extends TileEntityLoadedBase'), 'crane_speed': (O_TE, 'private static final double speed = 0.05D;'),
    'crane_update': (O_TE, 'public void updateEntity()'), 'crane_indicator_set': (O_TE, 'aboveColumn.craneIndicator = 10;'),
    'crane_progress_down': (O_TE, 'progress -= 0.04D;'), 'crane_progress_up': (O_TE, 'progress += 0.04D;'), 'crane_progress_clamp': (O_TE, 'if(progress > 1D) {'),
    'crane_load': (O_TE, 'column.load(this.loadedItem);'), 'crane_provide_next': (O_TE, 'this.loadedItem = column.provideNext();'), 'crane_unload': (O_TE, 'column.unload();'),
    'crane_box': (O_TE, 'double minX = xCoord + 0.5 - side.offsetX * 1.5;'), 'crane_box_query': (O_TE, 'List<EntityPlayer> players = worldObj.getEntitiesWithinAABB'),
    'crane_first_player': (O_TE, 'EntityPlayer player = players.get(0);'), 'crane_tilt_front': (O_TE, 'tiltFront = 30;'), 'crane_tilt_left': (O_TE, 'tiltLeft = 30;'),
    'crane_load_key': (O_TE, 'if(props.getKeyPressed(EnumKeybind.CRANE_LOAD)) {'), 'crane_clamp_front': (O_TE, 'posFront = MathHelper.clamp_double(posFront, -spanB, spanF);'),
    'crane_clamp_left': (O_TE, 'posLeft = MathHelper.clamp_double(posLeft, -spanR, spanL);'), 'crane_network_pack': (O_TE, 'networkPackNT(250);'),
    'crane_has_item': (O_TE, 'public boolean hasItemLoaded()'), 'crane_is_loading': (O_TE, 'public boolean isCraneLoading()'), 'crane_can_interact': (O_TE, 'public boolean canTargetInteract('),
    'crane_column_at_pos': (O_TE, 'public TileEntityRBMKBase getColumnAtPos()'), 'crane_serialize': (O_TE, 'public void serialize(ByteBuf buf)'),
    'crane_deserialize': (O_TE, 'public void deserialize(ByteBuf buf)'), 'crane_set_target': (O_TE, 'public void setTarget(int x, int y, int z)'),
    'crane_find_room': (O_TE, 'private int findRoomExtent('), 'crane_cycle_rotation': (O_TE, 'public void cycleCraneRotation()'),
    'crane_read_nbt': (O_TE, 'public void readFromNBT('), 'crane_write_nbt': (O_TE, 'public void writeToNBT('), 'crane_render_bbox': (O_TE, 'public AxisAlignedBB getRenderBoundingBox()'),
    'crane_render_distance': (O_TE, 'public double getMaxRenderDistanceSquared()'), 'crane_oc_name': (O_TE, 'public String getComponentName()'),
    'block_class': (O_BLOCK, 'public class RBMKCraneConsole extends BlockDummyable implements IToolable'), 'block_hardness': (O_BLOCK, 'this.setHardness(3F);'),
    'block_resistance': (O_BLOCK, 'this.setResistance(30F);'), 'block_core_meta': (O_BLOCK, 'if(meta >= this.offset)'), 'block_dimensions': (O_BLOCK, 'public int[] getDimensions()'),
    'block_offset': (O_BLOCK, 'public int getOffset()'), 'block_all_dimensions': (O_BLOCK, 'public int[][] getAllDimensions()'), 'block_fill_space': (O_BLOCK, 'public void fillSpace('),
    'block_check_requirement': (O_BLOCK, 'protected boolean checkRequirement('), 'block_collision': (O_BLOCK, 'public AxisAlignedBB getCollisionBoundingBoxFromPool('),
    'block_screw': (O_BLOCK, 'public boolean onScrew('), 'block_registered': (O_MODBLOCKS, 'rbmk_crane_console = new RBMKCraneConsole()'),
    'base_indicator_decrement': (O_BASE, 'if(this.craneIndicator > 0) this.craneIndicator--;'), 'base_indicator_write': (O_BASE, 'buf.writeByte((byte) this.craneIndicator);'),
    'base_indicator_read': (O_BASE, 'this.craneIndicator = buf.readByte();'), 'console_indicator': (O_CONSOLE, 'setByte("indicator", (byte) rbmk.craneIndicator);'),
    'tool_crane_branch': (O_TOOL, 'if(b == ModBlocks.rbmk_crane_console && stack.hasTagCompound())'),
    'tool_crane_target': (O_TOOL, 'TileEntityCraneConsole console = (TileEntityCraneConsole)world.getTileEntity'),
    'key_up': (O_KEYBINDS, 'public static KeyBinding craneUpKey'), 'key_down': (O_KEYBINDS, 'public static KeyBinding craneDownKey'), 'key_left': (O_KEYBINDS, 'public static KeyBinding craneLeftKey'),
    'key_right': (O_KEYBINDS, 'public static KeyBinding craneRightKey'), 'key_load': (O_KEYBINDS, 'public static KeyBinding craneLoadKey'),
    'key_register_up': (O_KEYBINDS, 'ClientRegistry.registerKeyBinding(craneUpKey);'), 'key_register_load': (O_KEYBINDS, 'ClientRegistry.registerKeyBinding(craneLoadKey);'),
    'key_enum': (O_KEYBINDS, 'public static enum EnumKeybind'), 'key_pressed_up': (O_CLIENT_PROXY, 'case CRANE_UP:'), 'key_pressed_load': (O_CLIENT_PROXY, 'case CRANE_LOAD:'),
    'render_class': (O_RENDER, 'public class RenderCraneConsole extends TileEntitySpecialRenderer'), 'render_console': (O_RENDER, 'ResourceManager.rbmk_crane_console.renderPart("Console_Coonsole");'),
    'render_joystick': (O_RENDER, 'GL11.glTranslated(0.75, 1, 0);'), 'render_meter1': (O_RENDER, 'ResourceManager.rbmk_crane_console.renderPart("Meter1");'),
    'render_meter2': (O_RENDER, 'ResourceManager.rbmk_crane_console.renderPart("Meter2");'), 'render_lamp1': (O_RENDER, 'if(console.isCraneLoading()) GL11.glColor3f(0.8F, 0.8F, 0F);'),
    'render_lamp2': (O_RENDER, 'if(console.isAboveValidTarget()) GL11.glColor3f(0F, 1F, 0F);'), 'render_height': (O_RENDER, 'int height = console.height - 6;'),
    'render_lift': (O_RENDER, 'GL11.glTranslated(0, -3.25 * (1 - '), 'render_girder': (O_RENDER, 'ResourceManager.rbmk_crane.renderPart("Girder");'),
    'item_renderer': (O_ITEM_RENDER, 'renderers.put(Item.getItemFromBlock(ModBlocks.rbmk_crane_console)'),
    'resource_console_obj': (O_RESOURCE_MANAGER, 'rbmk_crane_console = new HFRWavefrontObject('), 'resource_crane_obj': (O_RESOURCE_MANAGER, 'rbmk_crane = new HFRWavefrontObject('),
    'resource_console_tex': (O_RESOURCE_MANAGER, 'rbmk_crane_console_tex = new ResourceLocation('), 'resource_crane_tex': (O_RESOURCE_MANAGER, 'rbmk_crane_tex = new ResourceLocation('),
    'recipe_row': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_crane_console, 1)'),
    'lang_block_en': (O_LANG_EN, 'tile.rbmk_crane_console.name='), 'lang_load_en': (O_LANG_EN, 'hbm.key.craneLoad='), 'lang_up_en': (O_LANG_EN, 'hbm.key.craneMoveUp='),
    'lang_block_zh': (O_LANG_ZH, 'tile.rbmk_crane_console.name='), 'lang_load_zh': (O_LANG_ZH, 'hbm.key.craneLoad='), 'lang_up_zh': (O_LANG_ZH, 'hbm.key.craneMoveUp='),
}
# Constants compared between the original and NEO source texts: id -> (original path, regex, NEO path, regex, expected unique values in order[, expected NEO values when they differ]).
# Numbers are compared as floats (underscores dropped, F / D suffixes dropped), anything else as text. The group-1 value of every match is collected. A NEO regex that finds
# nothing (the class is not written yet, or its text differs from the handoff) is reported as pending with its id.
SYNC_O = r'buf\.write(\w+)\('
CONSTANTS = {
    # Block entity (TileEntityCraneConsole): the speed, the lift steps, the detection box, the key tilt, the clamps, the network range, the span search and the target geometry.
    'speed': (O_TE, r'private static final double speed = ([\d.]+)D;', CRANE_BE, r'private static final double speed = ([\d.]+)D;', [0.05]),
    'progress_step': (O_TE, r'progress [-+]= ([\d.]+)D;', CRANE_BE, r'progress [-+]= ([\d.]+)D;', [0.04]),
    'progress_initial': (O_TE, r'public double progress = ([\d.]+)D;', CRANE_BE, r'public double progress = ([\d.]+)D;', [1]),
    'down_guard': (O_TE, r'if\(progress > (\d+)\)', CRANE_BE, r'if\(progress > (\d+)\)', [0]),
    'progress_at_load': (O_TE, r'progress = (\d+);\s*goesDown = false;', CRANE_BE, r'progress = (\d+);\s*goesDown = false;', [0]),
    'progress_up_guard': (O_TE, r'\} else if\(progress != (\d+)\)', CRANE_BE, r'\} else if\(progress != (\d+)\)', [1]),
    'progress_clamp': (O_TE, r'if\(progress > (\d+)D\)', CRANE_BE, r'if\(progress > (\d+)D\)', [1]),
    'crane_indicator_value': (O_TE, r'craneIndicator = (\d+);', CRANE_BE, r'craneIndicator = (\d+);', [10]),
    'box_half_width': (O_TE, r'side\.offsetX \* ([\d.]+)', CRANE_BE, r'side\.getStepX\(\) \* ([\d.]+)', [1.5]),
    'box_half_width_z': (O_TE, r'side\.offsetZ \* ([\d.]+)', CRANE_BE, r'side\.getStepZ\(\) \* ([\d.]+)', [1.5]),
    'box_depth_x': (O_TE, r'dir\.offsetX \* (\d+);', CRANE_BE, r'dir\.getStepX\(\) \* (\d+);', [2]),
    'box_depth_z': (O_TE, r'dir\.offsetZ \* (\d+);', CRANE_BE, r'dir\.getStepZ\(\) \* (\d+);', [2]),
    'box_centre': (O_TE, r'xCoord \+ ([\d.]+) -', CRANE_BE, r'getX\(\) \+ ([\d.]+) -', [0.5]),
    'box_height': (O_TE, r'yCoord \+ (\d+),\s*Math\.max\(minZ, maxZ\)', CRANE_BE, r'getY\(\) \+ (\d+),\s*Math\.max\(minZ, maxZ\)', [2]),
    'box_side_rotation': (O_TE, r'ForgeDirection side = dir\.getRotation\(ForgeDirection\.(\w+)\)', CRANE_BE, r'Direction side = dir\.(getClockWise)\(\)', ['UP'], ['getClockWise']),
    'tilt_degrees': (O_TE, r'tilt(?:Front|Left) = (-?\d+);\s*if\(!worldObj\.isRemote\)', CRANE_BE, r'tilt(?:Front|Left) = (\d+) \* (?:front|left);', [30, '-30'], [30]),
    'tilt_reset': (O_TE, r'tiltFront = (\d+);\s*tiltLeft = (\d+);\s*if\(players', CRANE_BE, r'tiltFront = (\d+);\s*tiltLeft = (\d+);\s*if\(!players', [0]),
    'first_player': (O_TE, r'EntityPlayer player = players\.get\((\d+)\)', CRANE_BE, r'Player player = players\.get\((\d+)\)', [0]),
    'clamp_front_low': (O_TE, r'clamp_double\(posFront, -(\w+),', CRANE_BE, r'Mth\.clamp\(posFront, -(\w+),', ['spanB']),
    'clamp_front_high': (O_TE, r'clamp_double\(posFront, -\w+, (\w+)\)', CRANE_BE, r'Mth\.clamp\(posFront, -\w+, (\w+)\)', ['spanF']),
    'clamp_left_low': (O_TE, r'clamp_double\(posLeft, -(\w+),', CRANE_BE, r'Mth\.clamp\(posLeft, -(\w+),', ['spanR']),
    'clamp_left_high': (O_TE, r'clamp_double\(posLeft, -\w+, (\w+)\)', CRANE_BE, r'Mth\.clamp\(posLeft, -\w+, (\w+)\)', ['spanL']),
    'network_pack_range': (O_TE, r'networkPackNT\((\d+)\)', CRANE_BE, r'networkPackNT\((\d+)\)', [250]),
    'held_is_rod': (O_TE, r'loadedItem\.getItem\(\) instanceof (ItemRBMKRod)', CRANE_BE, r'loadedItem\.getItem\(\) instanceof (RBMKRodItem)', ['ItemRBMKRod'], ['RBMKRodItem']),
    'held_values': (O_TE, r'this\.(loaded\w+) = ItemRBMKRod\.get\w+\(loadedItem\)', CRANE_BE, r'this\.(loaded\w+) = RBMKRodItem\.get\w+\(loadedItem\)', ['loadedHeat', 'loadedEnrichment']),
    'held_getters': (O_TE, r'this\.loaded\w+ = ItemRBMKRod\.(get\w+)\(loadedItem\)', CRANE_BE, r'this\.loaded\w+ = RBMKRodItem\.(get\w+)\(loadedItem\)', ['getHullHeat', 'getEnrichment']),
    'findroom_max': (O_TE, r'findRoomExtent\(x, girderY, z, dir, (\d+)\)', CRANE_BE, r'findRoomExtent\(x, girderY, z, dir, (\d+)\)', [16]),
    'findroom_start': (O_TE, r'for ?\(int i = (\d+); i < max; i\+\+\)', CRANE_BE, r'for ?\(int i = (\d+); i < max; i\+\+\)', [1]),
    'findroom_wall': (O_TE, r'isAirBlock\([^\n]*\)\) \{\s*return (i - 1);', CRANE_BE, r'isEmptyBlock\([^\n]*\)\) \{\s*return (i - 1);', ['i - 1']),
    'girder_offset': (O_TE, r'int girderY = centerY \+ (\d+);', CRANE_BE, r'int girderY = centerY \+ (\d+);', [6]),
    'center_offset': (O_TE, r'this\.centerY = y \+ RBMKDials\.getColumnHeight\(worldObj\) \+ (\d+);', CRANE_BE, r'this\.centerY = y \+ RBMKDials\.getColumnHeight\(\) \+ (\d+);', [1]),
    'crane_height': (O_TE, r'this\.height = (\d+);', CRANE_BE, r'this\.height = (\d+);', [7]),
    'span_first_direction': (O_TE, r'getOrientation\(this\.getBlockMetadata\(\) - BlockDummyable\.offset\)\.(getOpposite)\(\)', CRANE_BE, r'getValue\(DummyableBlock\.FACING\)\.(getOpposite)\(\)', ['getOpposite']),
    'span_rotation': (O_TE, r'dir = dir\.getRotation\(ForgeDirection\.(\w+)\)', CRANE_BE, r'dir = dir\.(getClockWise)\(\)', ['UP'], ['getClockWise']),
    'rotation_step': (O_TE, r'craneRotationOffset = \(this\.craneRotationOffset \+ (\d+)\) % \d+;', CRANE_BE, r'craneRotationOffset = \(this\.craneRotationOffset \+ (\d+)\) % \d+;', [90]),
    'rotation_modulus': (O_TE, r'craneRotationOffset = \(this\.craneRotationOffset \+ \d+\) % (\d+);', CRANE_BE, r'craneRotationOffset = \(this\.craneRotationOffset \+ \d+\) % (\d+);', [360]),
    'column_floor': (O_TE, r'Math\.floor\(this\.centerX - dir\.offsetX \* this\.posFront - left\.offsetX \* this\.posLeft \+ ([\d.]+)D\)', CRANE_BE,
                     r'Math\.floor\(this\.centerX - dir\.getStepX\(\) \* this\.posFront - left\.getStepX\(\) \* this\.posLeft \+ ([\d.]+)D\)', [0.5]),
    'column_floor_z': (O_TE, r'Math\.floor\(this\.centerZ - dir\.offsetZ \* this\.posFront - left\.offsetZ \* this\.posLeft \+ ([\d.]+)D\)', CRANE_BE,
                       r'Math\.floor\(this\.centerZ - dir\.getStepZ\(\) \* this\.posFront - left\.getStepZ\(\) \* this\.posLeft \+ ([\d.]+)D\)', [0.5]),
    'column_below_lift': (O_TE, r'int y = this\.centerY - (\d+);', CRANE_BE, r'int y = this\.centerY - (\d+);', [1]),
    'column_left_rotation': (O_TE, r'ForgeDirection left = dir\.getRotation\(ForgeDirection\.(\w+)\)', CRANE_BE, r'Direction left = dir\.(getCounterClockWise)\(\)', ['DOWN'], ['getCounterClockWise']),
    # NBT (the lift progress and goesDown are not saved).
    'nbt_read_boolean': (O_TE, r'nbt\.getBoolean\("(\w+)"\)', CRANE_BE, r'tag\.getBoolean\("(\w+)"\)', ['crane']),
    'nbt_read_int': (O_TE, r'nbt\.getInteger\("(\w+)"\)', CRANE_BE, r'tag\.getInt\("(\w+)"\)',
                     ['craneRotationOffset', 'centerX', 'centerY', 'centerZ', 'spanF', 'spanB', 'spanL', 'spanR', 'height']),
    'nbt_read_double': (O_TE, r'nbt\.getDouble\("(\w+)"\)', CRANE_BE, r'tag\.getDouble\("(\w+)"\)', ['posFront', 'posLeft']),
    'nbt_write_boolean': (O_TE, r'nbt\.setBoolean\("(\w+)"', CRANE_BE, r'tag\.putBoolean\("(\w+)"', ['crane']),
    'nbt_write_int': (O_TE, r'nbt\.setInteger\("(\w+)"', CRANE_BE, r'tag\.putInt\("(\w+)"', ['craneRotationOffset', 'centerX', 'centerY', 'centerZ', 'spanF', 'spanB', 'spanL', 'spanR', 'height']),
    'nbt_write_double': (O_TE, r'nbt\.setDouble\("(\w+)"', CRANE_BE, r'tag\.putDouble\("(\w+)"', ['posFront', 'posLeft']),
    'nbt_held_key': (O_TE, r'nbt\.(?:getCompoundTag|setTag)\("(\w+)"', CRANE_BE, r'tag\.(?:getCompound|put)\("(\w+)"', ['held']),
    # Block (RBMKCraneConsole): the two boxes, the offset, hardness 3 / resistance 30, the screwdriver turn.
    'block_dimensions': (O_BLOCK, r'getDimensions\(\) \{\s*return new int\[\] \{([\d, ]+)\};', CRANE_BLOCK, r'getDimensions\(\) \{\s*return new int\[\] \{([\d, ]+)\};', ['1, 0, 0, 0, 1, 1']),
    'block_extra_box': (O_BLOCK, r'MultiblockHandlerXR\.fillSpace\([^;]*new int\[\] \{([\d, ]+)\}', CRANE_BLOCK, r'EXTRA_DIMENSIONS = new int\[\] \{([\d, ]+)\};', ['0, 0, 0, 1, 1, 1']),
    'block_offset': (O_BLOCK, r'getOffset\(\) \{\s*return (\d+);', CRANE_BLOCK, r'getOffset\(\) \{\s*return (\d+);', [1]),
    # Hardness and resistance live in NEO's registration (NtmBlocks), not in the block class.
    'block_hardness': (O_BLOCK, r'this\.setHardness\(([\d.]+)F\)', BLOCKS, r'RBMK_CRANE_CONSOLE = register\("rbmk_crane_console"[^\n]*?strength\(([\d.]+)F, [\d.]+F\)', [3]),
    'block_resistance': (O_BLOCK, r'this\.setResistance\(([\d.]+)F\)', BLOCKS, r'RBMK_CRANE_CONSOLE = register\("rbmk_crane_console"[^\n]*?strength\([\d.]+F, ([\d.]+)F\)', [30]),
    'block_tool': (O_BLOCK, r'tool [=!]= ToolType\.(\w+)', CRANE_BLOCK, r'tool [=!]= ToolType\.(\w+)', ['SCREWDRIVER']),
    'block_rotation_call': (O_BLOCK, r'tile\.(cycleCraneRotation)\(\)', CRANE_BLOCK, r'console\.(cycleCraneRotation)\(\)', ['cycleCraneRotation']),
    # RBMK base and console: the crane marker's decrement, its sync byte and the console column data.
    'indicator_decrement': (O_BASE, r'if\(this\.craneIndicator > (\d+)\) this\.craneIndicator--;', RBMK_BASE_BE, r'if\(this\.craneIndicator > (\d+)\) this\.craneIndicator--;', [0]),
    'indicator_write': (O_BASE, r'buf\.writeByte\(\(byte\) this\.(craneIndicator)\)', RBMK_BASE_BE, r'buf\.writeByte\(\(byte\) this\.(craneIndicator)\)', ['craneIndicator']),
    'indicator_read': (O_BASE, r'this\.craneIndicator = buf\.(readByte)\(\)', RBMK_BASE_BE, r'this\.craneIndicator = buf\.(readByte)\(\)', ['readByte']),
    'console_indicator_key': (O_CONSOLE, r'data\.setByte\("(indicator)", \(byte\) rbmk\.craneIndicator\)', RBMK_CONSOLE_BE, r'data\.putByte\("(indicator)", \(byte\) rbmk\.craneIndicator\)', ['indicator']),
    # rbmk_tool: the crane branch targets the console core with the stack's position.
    'tool_target_keys': (O_TOOL, r'getInteger\("(pos[XYZ])"\)', TOOL_ITEM, r'getInt\("(pos[XYZ])"\)', ['posX', 'posY', 'posZ']),
    # Keybinds: the five ids, the default keys, the registration and the pressed state.
    'key_ids': (O_KEYBINDS, r'new KeyBinding\(category \+ "\.(crane\w+)"', KEYBINDS, r'new KeyMapping\(category \+ "\.(crane\w+)"', ['craneMoveUp', 'craneMoveDown', 'craneMoveLeft', 'craneMoveRight', 'craneLoad']),
    'key_defaults': (O_KEYBINDS, r'new KeyBinding\(category \+ "\.crane\w+", Keyboard\.(KEY_\w+)', KEYBINDS, r'"\.crane\w+", InputConstants\.Type\.KEYSYM, InputConstants\.(KEY_\w+)',
                     ['KEY_UP', 'KEY_DOWN', 'KEY_LEFT', 'KEY_RIGHT', 'KEY_RETURN']),
    'key_registered': (O_KEYBINDS, r'registerKeyBinding\(crane(\w+)Key\)', KEYBINDS, r'event\.register\(CRANE_(\w+)\)', ['Up', 'Down', 'Left', 'Right', 'Load'], ['UP', 'DOWN', 'LEFT', 'RIGHT', 'LOAD']),
    'key_pressed_cases': (O_CLIENT_PROXY, r'case (CRANE_\w+):\s*return HbmKeybinds\.crane\w+Key\.getIsKeyPressed\(\)', KEYBINDS, r'case (CRANE_\w+) -> CRANE_\w+\.isDown\(\)',
                          ['CRANE_UP', 'CRANE_DOWN', 'CRANE_LEFT', 'CRANE_RIGHT', 'CRANE_LOAD']),
    # Renderer (RenderCraneConsole): the parts, the facing angles, the joystick, the meters, the lamps, the girders, the lift travel and the item transforms.
    'render_parts': (O_RENDER, r'renderPart\("(\w+)"\)', CRANE_RENDER, r'renderPart\("(\w+)"\)',
                     ['Console_Coonsole', 'JoyStick', 'Meter1', 'Meter2', 'Shotgun', 'MiniNuke', 'Lamp1', 'Lamp2', 'Girder', 'Main', 'Tube', 'Carriage', 'Lift'],
                     ['Console_Coonsole', 'JoyStick', 'Meter1', 'Meter2', 'Lamp1', 'Lamp2', 'Girder', 'Main', 'Tube', 'Carriage', 'Lift']),
    'render_facing_angles': (O_RENDER, r'teFacing = (\d+); break;', CRANE_RENDER, r'-> teFacing = (\d+);', [90, 180, 270, 0]),
    'render_facing_cases': (O_RENDER, r'case (\d): teFacing', CRANE_RENDER, r'case (\w+) -> teFacing', [2, 4, 3, 5], ['NORTH', 'WEST', 'SOUTH', 'EAST']),
    'render_console_shift': (O_RENDER, r'glTranslated\(([\d.]+), 0, 0\);', CRANE_RENDER, r'translate\(([\d.]+)F, 0F, 0F\);', [0.5]),
    'render_joystick_pivot': (O_RENDER, r'glTranslated\(([\d.]+), 1, 0\);', CRANE_RENDER, r'translate\(([\d.]+)F, 1F, 0F\);', [0.75, 0]),
    'render_joystick_offset': (O_RENDER, r'glTranslated\(-0\.75, (-[\d.]+), 0\)', CRANE_RENDER, r'translate\(-0\.75F, (-[\d.]+)F, 0F\)', ['-1.015']),
    'render_meter_height': (O_RENDER, r'glTranslated\(0, ([\d.]+), [\d.]+\);\s*double (?:heat|enrichment)', CRANE_RENDER, r'translate\(0F, ([\d.]+)F, [\d.]+F\);\s*double (?:heat|enrichment)', [1.25]),
    'render_meter_depth': (O_RENDER, r'glTranslated\(0, [\d.]+, ([\d.]+)\);\s*double (?:heat|enrichment)', CRANE_RENDER, r'translate\(0F, [\d.]+F, ([\d.]+)F\);\s*double (?:heat|enrichment)', [0.75, 0.25]),
    'render_meter_wobble_scale': (O_RENDER, r'currentTimeMillis\(\) \* ([\d.]+) % \d+\)', CRANE_RENDER, r'currentTimeMillis\(\) \* ([\d.]+) % \d+\)', [0.01]),
    'render_meter_wobble_modulus': (O_RENDER, r'currentTimeMillis\(\) \* [\d.]+ % (\d+)\)', CRANE_RENDER, r'currentTimeMillis\(\) \* [\d.]+ % (\d+)\)', [360]),
    'render_meter_wobble_degrees': (O_RENDER, r'\* (\d+) / Math\.PI', CRANE_RENDER, r'\* (\d+) / Math\.PI', [180]),
    'render_meter_wobble_amplitude': (O_RENDER, r'Math\.PI \* ([\d.]+) \+', CRANE_RENDER, r'Math\.PI \* ([\d.]+) \+', [0.05]),
    'render_meter_zero': (O_RENDER, r'\+ (\d+) - \d+ \* (?:heat|enrichment)', CRANE_RENDER, r'\+ (\d+) - \d+ \* (?:heat|enrichment)', [135]),
    'render_meter_span': (O_RENDER, r'- (\d+) \* (?:heat|enrichment)', CRANE_RENDER, r'- (\d+) \* (?:heat|enrichment)', [270]),
    'render_lamp_colours': (O_RENDER, r'glColor3f\(([\d., F]+)\)', CRANE_RENDER, r'setColor\(([\d., F]+), 1F\)', ['0.8F, 0.8F, 0F', '0F, 1F, 0F', '0F, 0.1F, 0F', '1F, 0F, 0F', '1F, 1F, 1F']),
    'render_tube_height': (O_RENDER, r'int height = console\.height - (\d+);', CRANE_RENDER, r'int height = console\.height - (\d+);', [6]),
    'render_girder_span_pairs': (O_RENDER, r'girderSpan = console\.(span\w+ \+ console\.span\w+) \+ \d+;', CRANE_RENDER, r'girderSpan = console\.(span\w+ \+ console\.span\w+) \+ \d+;',
                                 ['spanF + console.spanB', 'spanL + console.spanR']),
    'render_girder_span_plus': (O_RENDER, r'girderSpan = console\.span\w+ \+ console\.span\w+ \+ (\d+);', CRANE_RENDER, r'girderSpan = console\.span\w+ \+ console\.span\w+ \+ (\d+);', [1]),
    'render_girder_shifts': (O_RENDER, r'glTranslated\((?:0, 0, )?(-?pos[XZ] [+-] console\.span\w)', CRANE_RENDER, r'\(float\) \((-?pos[XZ] [+-] console\.span\w)\)',
                             ['posX + console.spanB', '-posZ - console.spanR', 'posX - console.spanF', '-posZ + console.spanL']),
    'render_girder_step': (O_RENDER, r'glTranslated\((-\d+), 0, 0\);\s*\}', CRANE_RENDER, r'translate\((-\d+)F, 0F, 0F\);\s*\}', ['-1']),
    'render_lift_travel': (O_RENDER, r'glTranslated\(0, -([\d.]+) \* \(1 - ', CRANE_RENDER, r'-([\d.]+)D \* \(1 - ', [3.25]),
    'item_shift': (O_ITEM_RENDER, r'rbmk_crane_console\), new ItemRenderBase\(\) \{\s*public void renderInventory\(\) \{\s*GL11\.glTranslated\(0, (-?\d+), 0\)', CRANE_RENDER, r'translate\(0F, (-?\d+)F, 0F\);\s*RenderContext\.scale', ['-3']),
    'item_scale': (O_ITEM_RENDER, r'rbmk_crane_console\), new ItemRenderBase\(\) \{\s*public void renderInventory\(\) \{\s*GL11\.glTranslated\(0, -?\d+, 0\);\s*GL11\.glScaled\(([\d.]+),', CRANE_RENDER,
                   r'RenderContext\.scale\(([\d.]+)F,', [3.5]),
    # ResourceManager: the two OBJs and their textures.
    'obj_paths': (O_RESOURCE_MANAGER, r'rbmk_crane(?:_console)? = new HFRWavefrontObject\(new ResourceLocation\(RefStrings\.MODID, "models/rbmk/(\w+\.obj)"\)\)', RESOURCE_MANAGER,
                  r'rbmk_crane(?:_console)? = new HFRWavefrontObject\("models/obj/rbmk/(\w+\.obj)"\)', ['crane_console.obj', 'crane.obj']),
    'texture_paths': (O_RESOURCE_MANAGER, r'rbmk_crane(?:_console)?_tex = new ResourceLocation\(RefStrings\.MODID, "(textures/models/machines/\w+\.png)"\)', RESOURCE_MANAGER,
                      r'RBMK_CRANE(?:_CONSOLE)?_TEX = NuclearTechMod\.withDefaultNamespace\("(textures/models/machines/\w+\.png)"\)',
                      ['textures/models/machines/crane_console.png', 'textures/models/machines/rbmk_crane.png']),
}
# Ordered sequences (a slice of the file between two markers, every match of the regex in order): id -> (original path, start marker, end marker, regex, NEO path, start marker, end marker,
# regex, expected values[, expected NEO values when they differ]). A slice whose start marker is missing is reported as pending with its id.
SEQUENCES = {
    'sync_write_types': (O_TE, 'public void serialize(ByteBuf buf)', 'public void deserialize(ByteBuf buf)', SYNC_O, CRANE_BE, 'public void serialize(RegistryFriendlyByteBuf buf)',
                         'public void deserialize(RegistryFriendlyByteBuf buf)', SYNC_O, ['Boolean'] + ['Int'] * 9 + ['Double'] * 3 + ['Boolean', 'Double', 'Double']),
    'sync_read_types': (O_TE, 'public void deserialize(ByteBuf buf)', 'public void setTarget(', r'buf\.read(\w+)\(', CRANE_BE, 'public void deserialize(RegistryFriendlyByteBuf buf)',
                        'public void setTarget(', r'buf\.read(\w+)\(', ['Boolean'] + ['Int'] * 9 + ['Double'] * 3 + ['Boolean', 'Double', 'Double']),
    'sync_write_fields': (O_TE, 'public void serialize(ByteBuf buf)', 'public void deserialize(ByteBuf buf)', r'buf\.write\w+\(this\.(\w+)(?:\(\))?\)', CRANE_BE,
                          'public void serialize(RegistryFriendlyByteBuf buf)', 'public void deserialize(RegistryFriendlyByteBuf buf)', r'buf\.write\w+\(this\.(\w+)(?:\(\))?\)',
                          ['setUpCrane', 'craneRotationOffset', 'centerX', 'centerY', 'centerZ', 'spanF', 'spanB', 'spanL', 'spanR', 'height', 'posFront', 'posLeft', 'progress', 'hasItemLoaded',
                           'loadedHeat', 'loadedEnrichment']),
    'sync_read_fields': (O_TE, 'public void deserialize(ByteBuf buf)', 'public void setTarget(', r'this\.(\w+) = buf\.read\w+\(\)', CRANE_BE, 'public void deserialize(RegistryFriendlyByteBuf buf)',
                         'public void setTarget(', r'this\.(\w+) = buf\.read\w+\(\)',
                         ['setUpCrane', 'craneRotationOffset', 'centerX', 'centerY', 'centerZ', 'spanF', 'spanB', 'spanL', 'spanR', 'height', 'syncFront', 'syncLeft', 'syncProgress', 'hasLoaded',
                          'loadedHeat', 'loadedEnrichment']),
    'span_order': (O_TE, 'public void setTarget(', 'private int findRoomExtent(', r'this\.(span\w) = this\.findRoomExtent', CRANE_BE, 'public void setTarget(', 'private int findRoomExtent(',
                   r'this\.(span\w) = this\.findRoomExtent', ['spanF', 'spanR', 'spanB', 'spanL']),
    'base_sync_types': (O_BASE, 'public void serialize(ByteBuf buf)', 'public void deserialize(ByteBuf buf)', SYNC_O, RBMK_BASE_BE, 'public void serialize(RegistryFriendlyByteBuf buf)',
                        'public void deserialize(RegistryFriendlyByteBuf buf)', SYNC_O, ['Double', 'Int', 'Int', 'Byte'], ['Double', 'Byte']),
    'base_sync_fields': (O_BASE, 'public void serialize(ByteBuf buf)', 'public void deserialize(ByteBuf buf)', r'buf\.write\w+\((?:\(byte\) )?this\.(\w+)\)', RBMK_BASE_BE,
                         'public void serialize(RegistryFriendlyByteBuf buf)', 'public void deserialize(RegistryFriendlyByteBuf buf)', r'buf\.write\w+\((?:\(byte\) )?this\.(\w+)\)',
                         ['heat', 'reasimWater', 'reasimSteam', 'craneIndicator'], ['heat', 'craneIndicator']),
    'item_parts': (O_ITEM_RENDER, 'Item.getItemFromBlock(ModBlocks.rbmk_crane_console)', 'GL11.glShadeModel(GL11.GL_FLAT);', r'renderPart\("(\w+)"\)', CRANE_RENDER, 'public void renderCommon(', None,
                   r'renderPart\("(\w+)"\)', ['Console_Coonsole', 'JoyStick', 'Meter1', 'Meter2']),
}
# NEO-only facts (no original counterpart, or a deliberate NEO form): id -> (NEO path, regex, expected unique values). Recorded in the receipt; a regex that finds nothing is pending.
NEO_FACTS = {
    'find_core_null_guard_block': (CRANE_BLOCK, r'BlockPos core = this\.findCore\(level, pos\);\s*(?://[^\n]*\s*)?if\((core != null)', ['core != null']),
    'find_core_type_guard_block': (CRANE_BLOCK, r'level\.getBlockEntity\(core\) (instanceof RBMKCraneConsoleBlockEntity) console', ['instanceof RBMKCraneConsoleBlockEntity']),
    'find_core_type_guard_column': (CRANE_BE, r'this\.level\.getBlockEntity\(core\) (instanceof RBMKBaseBlockEntity) column', ['instanceof RBMKBaseBlockEntity']),
    'move_crane_api': (CRANE_BE, r'public void (moveCrane)\(int front, int left\)', ['moveCrane']),
    'start_load_api': (CRANE_BE, r'public void (startLoad)\(\)', ['startLoad']),
    'tick_uses_move_crane': (CRANE_BE, r'this\.(moveCrane)\(front, sideways\)', ['moveCrane']),
    'tick_uses_start_load': (CRANE_BE, r'this\.(startLoad)\(\)', ['startLoad']),
    'loaded_item_accessor': (CRANE_BE, r'public ItemStack (getLoadedItem)\(\)', ['getLoadedItem']),
    'render_box_infinite': (CRANE_BE, r'public AABB getRenderBoundingBox\(\) \{\s*return AABB\.(INFINITE);', ['INFINITE']),
    'set_changed_cycle': (CRANE_BE, r'craneRotationOffset = \(this\.craneRotationOffset \+ 90\) % 360;\s*this\.(setChanged)\(\);', ['setChanged']),
    'ticker_core_only': (CRANE_BLOCK, r'if\(state\.getValue\(TYPE\) != DummyBlockType\.(CORE)\) return null;', ['CORE']),
    'core_block_entity': (CRANE_BLOCK, r'state\.getValue\(TYPE\) == DummyBlockType\.(CORE) \? new RBMKCraneConsoleBlockEntity', ['CORE']),
    'dummyable_base': (CRANE_BLOCK, r'public class RBMKCraneConsoleBlock extends (DummyableBlock)', ['DummyableBlock']),
    'toolable': (CRANE_BLOCK, r'public class RBMKCraneConsoleBlock extends DummyableBlock implements (IToolable)', ['IToolable']),
    # The key state: the server reads the player attachment (KeybindReceiver -> HbmKeybindsServer, byte-identical to the start), the client asks the proxy (original ClientProxy.getIsKeyPressed
    # :1973-1987, ServerProxy :68 false); HbmKeybinds no longer touches HbmPlayerAttachments (review fix 1).
    'proxy_key_server': (SERVER_PROXY, r'public boolean (getIsKeyPressed)\(HbmKeybinds\.EnumKeybind key\) \{\s*return (?:false);', ['getIsKeyPressed']),
    'proxy_key_client': (CLIENT_PROXY, r'public boolean (getIsKeyPressed)\(HbmKeybinds\.EnumKeybind key\) \{\s*return HbmKeybinds\.getIsKeyPressed\(key\);', ['getIsKeyPressed']),
    'crane_key_server': (CRANE_BE, r'if\(!player\.level\(\)\.isClientSide\) return HbmPlayerAttachments\.getData\(player\)\.(getKeyPressed)\(key\);', ['getKeyPressed']),
    'crane_key_client': (CRANE_BE, r'return player == NuclearTechMod\.proxy\.me\(\) && NuclearTechMod\.proxy\.(getIsKeyPressed)\(key\);', ['getIsKeyPressed']),
    'tool_has_position': (TOOL_ITEM, r'if\(b instanceof RBMKCraneConsoleBlock crane && (hasPosition)\(stack\)\)', ['hasPosition']),
    'tool_find_core_guard': (TOOL_ITEM, r'BlockPos core = crane\.findCore\(level, pos\);\s*[^\n]*?(core != null && level\.getBlockEntity\(core\) instanceof RBMKCraneConsoleBlockEntity) be', ['core != null && level.getBlockEntity(core) instanceof RBMKCraneConsoleBlockEntity']),
    'tool_set_message': (TOOL_ITEM, r'b instanceof RBMKCraneConsoleBlock crane.*?getDescriptionId\(\) \+ "(\.set)"', ['.set']),
    'block_registered': (BLOCKS, r'RBMK_CRANE_CONSOLE = register\("(rbmk_crane_console)"', ['rbmk_crane_console']),
    'block_entity_type_registered': (BLOCK_ENTITY_TYPES, r'RBMK_CRANE_CONSOLE = BLOCK_ENTITY_TYPES\.register\("(rbmk_crane_console)"', ['rbmk_crane_console']),
    'renderer_registered': (CLIENT_PROXY, r'BlockEntityRenderers\.register\(NtmBlockEntityTypes\.(RBMK_CRANE_CONSOLE)\.get\(\), new RenderCraneConsole\(\)\)', ['RBMK_CRANE_CONSOLE']),
    'creative_tab': (CREATIVE_TABS, r'output\.accept\(NtmBlocks\.(RBMK_CRANE_CONSOLE)\)', ['RBMK_CRANE_CONSOLE']),
    'loot_drop_self': (LOOT_PROVIDER, r'dropSelf\(NtmBlocks\.(RBMK_CRANE_CONSOLE)\.get\(\)\)', ['RBMK_CRANE_CONSOLE']),
    'pickaxe_tag': (TAG_PROVIDER, r'(NtmBlocks\.RBMK_CRANE_CONSOLE)\.get\(\),', ['NtmBlocks.RBMK_CRANE_CONSOLE']),
    'blockstate_particle_only': (BLOCK_STATE_PROVIDER, r'particleOnlyBlock\(NtmBlocks\.(RBMK_CRANE_CONSOLE), modLoc\("block/rbmk/rbmk_crane_console"\)\)', ['RBMK_CRANE_CONSOLE']),
    'obj_registered': (RESOURCE_MANAGER, r'rbmk_crane_console = new HFRWavefrontObject\("(models/obj/rbmk/crane_console\.obj)"\)', ['models/obj/rbmk/crane_console.obj']),
    'obj_crane_registered': (RESOURCE_MANAGER, r'rbmk_crane = new HFRWavefrontObject\("(models/obj/rbmk/crane\.obj)"\)', ['models/obj/rbmk/crane.obj']),
    'item_renderer_block': (CRANE_RENDER, r'NtmBlocks\.(RBMK_CRANE_CONSOLE)\.asItem\(\)', ['RBMK_CRANE_CONSOLE']),
    'recipe_provider_id': (RECIPE_PROVIDER, r'ResourceLocation\.fromNamespaceAndPath\("hbmsntm", "(rbmk_crane_console)"\)', ['rbmk_crane_console']),
}
# Known source differences the batch deliberately leaves (recorded; not asserted equal, but each is backed by a NEO constant or fact above where it can be).
KNOWN_DIFFERENCES = {
    'oc_callbacks': 'the OpenComputers callbacks (TileEntityCraneConsole.java:391-480: getComponentName rbmk_crane, move, load, getRodInfo, getDepletion, getXenonPoison, getCranePos) are not ported',
    'half_slab_bounds': 'the original collision and bounds for metadata UP (RBMKCraneConsole.java:65-82) cannot apply to a placed multiblock (its parts never carry that metadata); NEO keeps the full cube',
    'move_crane_split': 'NEO extracts the key actions of the tick into moveCrane(front, left) and startLoad() (original :157-177) so the GameTests can drive them; the tick calls them with the same effects',
    'loaded_item_accessor': 'getLoadedItem() is NEO-only (GameTest accessor); the original keeps loadedItem private',
    'find_core_guards': 'the original dereferences findCore results without checks (RBMKCraneConsole.java:90-92, TileEntityCraneConsole.java:237-240); NEO checks null and the block entity type (NEO-defensive)',
    'set_changed': 'NEO calls setChanged when the position changes, after setTarget and cycleCraneRotation and after a load / unload (1.7.10 saved every chunk tile entity); the original has markDirty only in setTarget, the load branch and onScrew',
    'client_key_state': 'the original reads the key state of the player from HbmPlayerProps on both sides (TileEntityCraneConsole.java:151-155; the client props hold the local player\'s keys, HbmKeybinds.java:203-205); NEO reads the server attachment on the server and asks the proxy (ServerProxy false / ClientProxy HbmKeybinds.getIsKeyPressed, original ClientProxy.java:1973-1987) for the local player on the client, because the synced attachment is replaced by every server sync; HbmKeybinds no longer touches the attachment',
    'tool_has_position': 'NEO requires the three position keys on the rbmk_tool stack (the original ItemRBMKTool.java:70-85 asks for any NBT and would link 0, 0, 0)',
    'turn_progress': 'turnProgress is never set by the original deserialize (:276-296), so the client snaps to the synced values each tick; kept (upstream-shared)',
    'render_distance': 'the original getMaxRenderDistanceSquared returns 65536 (:387-389); NEO uses the base renderer view distance (256 blocks) with an infinite render box',
    'lamp_drawing': 'the original draws the lamps with GL_TEXTURE_2D and lighting off and lightmap 240 / 240; NEO draws them with the white texture, full-bright and unlit, tinted by the shader colour',
    'obj_path': 'the original loads models/rbmk/crane_console.obj and crane.obj, NEO models/obj/rbmk/... (layout rule; both files are byte-identical to the original worktree)',
    'shotgun_mini_nuke': 'the original renderer comments out the Shotgun / MiniNuke objects (RenderCraneConsole.java:66-69); the OBJ keeps them unrendered and NEO does not draw them',
    'column_height_dial': 'RBMKDials.getColumnHeight takes the world in the original (setTarget :300) and no argument in NEO (a global dial)',
    'base_sync': 'the original RBMK base syncs heat, reasimWater, reasimSteam and the indicator byte (TileEntityRBMKBase.java:292-305); NEO syncs heat and the indicator byte (the ReaSim fields are not ported, GOAL24 decision 5): the indicator byte still follows heat',
    'console_screen_indicator': 'the RBMK console screen does not draw the indicator in the original either (GUIRBMKConsole has no "indicator"); the original reader is RenderRBMKConsole :77, already ported',
    'recipe_528': 'the original recipe sits in the !enable528 branch (CraftingManager.java:990); NEO has no 528 mode and registers it unconditionally',
    'enum_keybind_duck': 'NEO\'s EnumKeybind has DUCK, which the original lacks; the five CRANE_* constants keep the original relative order and the start order of the other constants is unchanged',
}
# The recipe: the original row (CraftingManager.java:990) -> the NEO generated JSON; each original key expression maps to the NEO ingredient.
KEY_TABLE = {'B.ingot()': {'item': 'hbmsntm:ingot_boron'}, 'ModBlocks.deco_rbmk': {'item': 'hbmsntm:deco_rbmk'},
             'DictFrame.fromOne(ModItems.circuit, EnumCircuitType.ANALOG)': {'item': 'hbmsntm:circuit_analog_board'}}
CRANE_RECIPE_ID = 'rbmk_crane_console'


def scope_text(key_count, assets, tests, total_tests):
    return (f'Goal25D (the fourth and last batch of Goal 25: RBMK operation and fuel logistics): the RBMK crane console rbmk_crane_console, a two-box console (RBMKCraneConsoleBlock, a DummyableBlock '
            f'with dimensions {{1,0,0,0,1,1}} plus a second box {{0,0,0,1,1,1}} in front of the core; RBMKCraneConsoleBlockEntity) linked with the rbmk_tool to a fuel or storage column. A player standing '
            f'in its detection box (3 wide, 2 deep, 2 high in front of the core; the first player only) drives a crane over the reactor with the arrow keys (0.05 blocks per tick, clamped to the free room '
            f'measured at the girder level, 16 at most) and lowers the lift with Enter (25 ticks down at 0.04 per tick, the load or unload through IRBMKLoadable on the next tick, 25 ticks up) to move single '
            f'fuel rods between columns; the column under the lift shows the crane marker (RBMKBaseBlockEntity.craneIndicator, 10 ticks, synced as one byte and not saved) on the RBMK console grid; '
            f'RenderCraneConsole draws the console with its joystick, meters and lamps and the linked crane and has an item form; five new key bindings with the original defaults (up, down, left, right, '
            f'enter) and the client key read through the proxy (ServerProxy / ClientProxy getIsKeyPressed); the shaped crafting recipe (boron ingot, analog circuit board, deco_rbmk); {key_count} English keys and {key_count} Chinese '
            f'entries (the block name and the five key labels, upstream); {assets} imported resources (the console and crane OBJs, their two textures and the block icon); {tests} RBMKCraneGameTests '
            f'({total_tests} GameTests in total, one batch per test) and the unified Goal 25 acceptance checklist GOAL25D-ACCEPTANCE.md (written, not executed). Gameplay impact: rods can be moved between '
            f'fuel channels and storage columns without opening their screens, whatever their heat; the arrow keys and Enter are read by the crane while a player stands in its detection box.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal25d release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 136 scope copies) when it reproduces the baseline hash. A file the freeze did not copy has no reproducible start
    bytes when it was uncommitted-modified at the freeze (the Goal25A, Goal25B and Goal25C deliveries); the blob at the start commit is tried (with CRLF where the working tree had it) for
    committed files; None when nothing reproduces the baseline hash."""
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
    """The Goal25D start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does not list it)
    the hash the goal25c receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal25c packager protected (built there from the Goal21A..Goal25B starts and receipts and the goal25c start), plus every path the goal25c receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 25C baseline lists the goal25b receipt among them) and every release file of the frozen start
    (the goal25c package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes) are
    pinned at their Goal25D start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal25c packager set at its Goal25C start hash, for the records that changed between the two starts."""
    goal25c_start = read(GOAL25C_BASELINE)
    out = dict(goal25c_protected_paths(goal25c_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal25c receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal25c_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift.
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal25C and Goal25D starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal25c_start):
    """{path: {receipts, start_sha256, goal25c_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal25c receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal25c receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22, 23 and 24 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal25c '
                           'receipt does not hash it. Frozen at the Goal25D start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal25c) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal25c package; the goal25c receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal25c '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal25c_start_sha256=goal25c_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal25c_start_pin_sha256'] = repinned[p]
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


def is_comment(line):
    s = line.strip()
    return not s or s.startswith(('//', '*', '/*', '*/'))


def ordered(text, tokens):
    """Whether the tokens occur in the text in this order (each after the previous one)."""
    at = -1
    for t in tokens:
        at = text.find(t, at+1)
        if at < 0: return False
    return True


def sequence(text, start, end, regex):
    """Every group-1 match of the regex, in order, in the slice of the text from the start marker to the end marker (to the end of the text when the end marker is None); None when a marker
    is missing."""
    i = text.find(start)
    if i < 0: return None
    j = text.find(end, i+len(start)) if end else len(text)
    if j < 0: return None
    return [m.group(1) for m in re.finditer(regex, text[i:j])]


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
    older_receipts = [read(p) for p in OLDER_PREVIOUS_RECEIPTS]
    goal25c_start = read(GOAL25C_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal25D commits nothing), the recorded start on top of the Goal 24 close-out commit
    # with the uncommitted Goal25A, Goal25B and Goal25C deliveries.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 25 planning commit'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 25 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    status_lines = base['target_status'].splitlines()
    assert len(status_lines) == START_STATUS_LINES, f'The frozen start status has {len(status_lines)} lines, not the {START_STATUS_LINES} of the uncommitted Goal25A, Goal25B and Goal25C deliveries'
    assert START_STATUS.read_text(encoding='utf-8').splitlines() == status_lines, 'start_status.txt differs from the baseline target status'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal25c receipt records another original commit than the frozen start'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal25D: '+head
    closeout = git_ro(ROOT, 'rev-parse', 'HEAD~1').strip()
    assert closeout.startswith(GOAL24_CLOSEOUT), 'NEO HEAD~1 is not the Goal 24 close-out commit 17c8062f'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and base['start_content']['uncommitted'].startswith('the Goal25A, Goal25B and Goal25C deliveries'), 'Baseline start content differs'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d',
                                                          'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b', 'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256_at_freeze'] == base['build_libs_jar_sha256_at_freeze'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_lines'] == START_STATUS_LINES and startup['start_dirty'] == START_STATUS_LINES \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'] and startup['changed_at_freeze_time'] == base['changed_at_freeze_time'], \
        'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_recorded'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal25c generated tree'
    # The 121 uncommitted start paths are the goal25a, goal25b and goal25c deliveries: start_hashes.txt (written by capture_start.py before the first 25D write; one entry per file, the
    # status line of an untracked directory may be collapsed to one line in start_status.txt) lists the same paths as the three receipts' changed_files, and every hash in it is the baseline hash.
    start_dirty = {}
    for line in START_HASHES.read_text(encoding='utf-8').splitlines():
        h, p = line.split(' ', 1)
        start_dirty[p.lstrip('*').strip()] = h
    delivered = {}
    for receipt_older in older_receipts + [prior_receipt]:
        delivered.update({e['path']: e for e in receipt_older['changed_files']})
    assert set(start_dirty) == set(delivered), 'The frozen start paths are not the goal25a + goal25b + goal25c deliveries (changed_files): '+str(sorted(set(start_dirty) ^ set(delivered))[:6])
    assert all(base['files'].get(p) == h for p, h in start_dirty.items()), 'start_hashes.txt differs from the baseline file hashes'
    delivery_differs = sorted(p for p, e in delivered.items() if base['files'].get(p) != e['after_sha256'])
    start_jar_sha = base['build_libs_jar_sha256_at_start']

    # 2. Previous deliveries: the goal25c package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the start is not the goal25c package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal25c receipt list + the goal25c package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal25c receipt count + the goal25c release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal25c receipt'
    assert base['previous_receipt_evidence_drift'] == {}, 'The goal25c receipt drifted at the start: '+str(list(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal25c_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal25c receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal25d. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, f'Path changed since the Goal25D start that the owner table does not list (production outside the {len(MODIFIED_JAVA)} modified Java files, the {len(NEW_JAVA)} new classes incl. '
         'RBMKCraneGameTests, the 5 resources, zh_cn.json and the mapping, a protected or frozen record, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal25A / Goal25B / Goal25C / Goal24 records or the 25D planning documents changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal25D start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD, ANVIL_RECIPES] + GENERATED + SHARED_RECORDS + REPORTS[:1]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    need(sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES], f'{ANVIL_RECIPES} changed since the start (the crane console has no anvil row)')
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION + OPTIONAL_JAVA if p.startswith('src/')})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified and {len(NEW_JAVA)} new Java files, the 5 resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    goal25_now = sha(ROOT/GOAL25_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository. The batch ran under the main agent with a builder, a '
                                               'verifier (RBMKCraneGameTests, verify_goal25d_rbmk_crane.py, Gradle), this packaging verifier and a read-only reviewer; each wrote only its '
                                               'named files (scope-before / scope-after snapshots of the verifiers are indexed as evidence). migration/GOAL25.md and GOAL25D.md are edited by the '
                                               'main agent of this batch.',
                             goal25_md=dict(start_sha256=base['files'][GOAL25_RECORD], current_sha256=goal25_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p)) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, owners=[OWNER], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal25D takes no new snapshot)'
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
    # NEO constants against the original (block entity, block, menu, screen, renderer).
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
    # Ordered slices of both texts (the sync field and type order of the crane, the span search order, the base column's sync order, the item renderer's parts).
    sequences, sequences_bad = {}, []
    for sid, (o_path, o_start, o_end, o_regex, n_path, n_start, n_end, n_regex, expected, *neo_expected) in SEQUENCES.items():
        o_values = sequence(original_text(o_path), o_start, o_end, o_regex)
        n_values = sequence(neo_text(n_path), n_start, n_end, n_regex) if (ROOT/n_path).is_file() else None
        assert o_values == expected, f'The original sequence {sid} ({o_path}) is {o_values}, the owner table expects {expected}'
        wanted = neo_expected[0] if neo_expected else expected
        sequences[sid] = dict(original=o_values, neo=n_values, original_path=o_path, neo_path=n_path, **(dict(neo_expected=wanted) if neo_expected else {}))
        if n_values != wanted: sequences_bad.append(sid)
    need(not sequences_bad and all(s['neo'] is not None for s in sequences.values()),
         f'NEO sequences differ from the original (or the NEO source is missing / its text differs from the handoff): {sorted(set(sequences_bad) | {k for k, s in sequences.items() if s["neo"] is None})}')
    # The tick order in both texts: the client interpolation, the crane marker on the column under the lift, the lift going down (the load, then the unload with provideNext), the lift
    # coming up, the operator's box, the first player, the movement keys and the load key, the position clamps, the held rod's values and the network range (TileEntityCraneConsole.java:72-194).
    order_tokens = {'original': ['this.turnProgress > 0', 'aboveColumn.craneIndicator = 10;', 'progress -= 0.04D;', 'column.load(this.loadedItem);', 'this.loadedItem = column.provideNext();',
                                 'column.unload();', 'progress += 0.04D;', 'getEntitiesWithinAABB', 'players.get(0)', 'EnumKeybind.CRANE_UP', 'EnumKeybind.CRANE_LOAD', 'clamp_double(posFront',
                                 'this.loadedHeat = ItemRBMKRod.getHullHeat', 'networkPackNT(250)'],
                    'neo': ['this.turnProgress > 0', 'aboveColumn.craneIndicator = 10;', 'progress -= 0.04D;', 'column.load(this.loadedItem);', 'this.loadedItem = column.provideNext();',
                            'column.unload();', 'progress += 0.04D;', 'getEntitiesOfClass', 'players.get(0)', 'EnumKeybind.CRANE_UP', 'EnumKeybind.CRANE_LOAD', 'Mth.clamp(posFront',
                            'this.loadedHeat = RBMKRodItem.getHullHeat', 'networkPackNT(250)']}
    tick_order = dict(original=ordered(original_text(O_TE), order_tokens['original']), neo=ordered(neo_text(CRANE_BE), order_tokens['neo']))
    assert tick_order['original'], 'The original updateEntity no longer has the interpolation / marker / lift / box / keys / clamp / held values / sync order'
    need(tick_order['neo'], f'{CRANE_BE} updateEntity does not keep the original order: interpolation, marker, lift down and up, box, first player, keys, clamps, held values, network range')
    # Logical sides: the block entity and the block (common code) import nothing from net.minecraft.client; the renderer exists. The block has no GUI.
    common = (CRANE_BE, CRANE_BLOCK)
    client_imports = {p: (ROOT/p).is_file() and 'net.minecraft.client' in neo_text(p) for p in common}
    need(not any(client_imports.values()) and all((ROOT/p).is_file() for p in common + (CRANE_RENDER,)),
         'common-side crane classes are missing or import net.minecraft.client: '+str(sorted(p for p, v in client_imports.items() if v)))
    need('extends LoadedBaseBlockEntity implements ITickable' in neo_text(CRANE_BE), f'{CRANE_BE} is not a LoadedBaseBlockEntity implementing ITickable (the original extends TileEntityLoadedBase)')
    gui_tokens = [t for t in ('useWithoutItem', 'MenuProvider', 'openMenu', 'standardOpenBehavior') if t in neo_text(CRANE_BLOCK)]
    need(not gui_tokens and (ROOT/CRANE_BLOCK).is_file(), f'{CRANE_BLOCK} opens a GUI or is missing (the original crane console has no GUI): {gui_tokens}')
    # The keybind receiver chain stays byte-identical to its start; the EnumKeybind order is the start order with the five CRANE_* constants where the start had them.
    unchanged_bad = [p for p in UNCHANGED_JAVA if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed: '+str(unchanged_bad))

    def enum_names(text):
        m = re.search(r'enum EnumKeybind \{(.*?)\}', text, re.S)
        return re.findall(r'\b([A-Z][A-Z_]+)\b', m.group(1)) if m else None
    enum_start = enum_names((START_FILES/KEYBINDS).read_text(encoding='utf-8')) if (START_FILES/KEYBINDS).is_file() else None
    enum_now = enum_names(neo_text(KEYBINDS))
    enum_original = enum_names(original_text(O_KEYBINDS))
    crane_keys = ['CRANE_UP', 'CRANE_DOWN', 'CRANE_LEFT', 'CRANE_RIGHT', 'CRANE_LOAD']
    need(enum_start is not None and enum_now == enum_start, f'EnumKeybind order differs from the start copy: start {enum_start}, now {enum_now}')
    need(enum_now is not None and enum_now[enum_now.index('CRANE_UP'):enum_now.index('CRANE_UP')+5] == crane_keys if enum_now and 'CRANE_UP' in enum_now else False,
         f'EnumKeybind does not hold {crane_keys} in this order: {enum_now}')
    assert enum_original is not None and enum_original[enum_original.index('CRANE_UP'):enum_original.index('CRANE_UP')+5] == crane_keys, 'The original EnumKeybind lost the CRANE_* order'
    keybind_enum = dict(original=enum_original, start=enum_start, neo=enum_now, original_reference=original_refs['key_enum'],
                        extra_neo_constants=sorted(set(enum_now or []) - set(enum_original)), missing_neo_constants=sorted(set(enum_original) - set(enum_now or [])))
    # The rbmk_tool crane branch uses the same position keys and the console target setter (original ItemRBMKTool.java:70-85).
    # Recipe: the shaped crafting recipe (computed from the generated JSON) against the original row (CraftingManager.java:990); there is no assembly or anvil row.
    o_row = original_shaped_row(original_text(O_CRAFTING), 'Blocks', CRANE_RECIPE_ID, 1)
    assert o_row is not None and all(v is not None for v in o_row['key'].values()), f'The original {CRANE_RECIPE_ID} recipe row could not be parsed or translated: {o_row}'
    assert o_row['pattern'] == ['BCD', 'DDD'], f'The original recipe pattern differs from the owner table: {o_row["pattern"]}'
    crafting = {}
    if (ROOT/G_CRANE_RECIPE).is_file():
        data = read(ROOT/G_CRANE_RECIPE)
        neo_row = dict(pattern=data.get('pattern'), key=data.get('key'), result=data.get('result'))
        crafting[CRANE_RECIPE_ID] = dict(type=data.get('type'), neo=neo_row, original=jsonable(o_row), original_reference=original_refs['recipe_row'])
        need(data.get('type') == 'minecraft:crafting_shaped' and row_matches(neo_row, o_row), f'{G_CRANE_RECIPE} differs from the original recipe row: {neo_row} vs {jsonable(o_row)}')
    else:
        need(False, 'generated recipe missing: '+G_CRANE_RECIPE)
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
            # The original worktree is clean at SOURCE_HEAD, so its OBJ is the checked-out original; on this Windows checkout it carries CRLF where the stored blob has LF (autocrlf).
            # The blob must match up to that line-ending conversion, and the ownership record's blob fields must say so (the 24E console OBJ precedent).
            normalized = (ROOT/target).read_bytes().replace(b'\r\n', b'\n')
            need(blob.replace(b'\r\n', b'\n') == normalized, f'{target} differs from the {SOURCE_HEAD[:8]} blob of {original} beyond line endings')
            if entry:
                need(entry.get('blob_sha256') == hashlib.sha256(blob).hexdigest() and entry.get('blob_bytes') == len(blob) and entry.get('normalized_sha256') == hashlib.sha256(normalized).hexdigest()
                     and entry.get('normalized_equal_to_blob') is True and entry.get('worktree_crlf_lines') == (ROOT/target).read_bytes().count(b'\r\n'),
                     f'{RESOURCE_OWNERSHIP} blob / CRLF fields differ from the stored blob or the live OBJ: {target}')
        else:
            need(checked_out == blob, f'{target} is not byte-identical to the stored blob of {original} at {SOURCE_HEAD[:8]}')
            if entry: need(entry.get('blob_sha256') == hashlib.sha256(blob).hexdigest(), f'{RESOURCE_OWNERSHIP} blob_sha256 differs from the stored blob: {target}')
        if entry:
            need(entry.get('source_path') == original and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('bytes') == (ROOT/target).stat().st_size,
                 f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original path: {target}')
    # features.json: the new group, the unchanged status and reviewed_source_commit of the previous groups.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES <= set(start_features) and not set(NEW_FEATURES) & set(start_features), \
        'The start mapping does not hold the groups of 24B-25C (rbmk-fuel, rbmk-reactor, rbmk-control, rbmk-steam, rbmk-console, rbmk-storage, rbmk-recycling, rbmk-outgasser, rbmk-autoloader) and not yet the Goal25D group'
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
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal25c totals'
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal25c totals {totals} + {len(KEYS)}')
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal25c generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    advancements = sorted(p for p in generated_added if ADVANCEMENT.fullmatch(p))
    EXPECTED_GENERATED = sorted(EXPECTED_GENERATED_BASE + advancements)
    need(len(advancements) == 1, 'The generated advancements are not exactly one for rbmk_crane_console: '+str(advancements))
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected blockstate, model, loot table, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, the pickaxe tag and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # The pickaxe tag: the start list plus rbmk_crane_console, in the start order.
    tag_start_bytes = start_bytes(base, GENERATED_ROOT+TAG_ENTRY)
    assert tag_start_bytes is not None, 'No reproducible start bytes for the pickaxe tag'
    tag_start, tag_now = json.loads(tag_start_bytes.decode('utf-8-sig'))['values'], read(ROOT/(GENERATED_ROOT+TAG_ENTRY))['values']
    tag_inserted = insertions(tag_start, tag_now)
    need(tag_inserted is not None and [v for _, v in tag_inserted] == ['hbmsntm:rbmk_crane_console'],
         f'the pickaxe tag is not the start list plus hbmsntm:rbmk_crane_console: inserted {None if tag_inserted is None else [v for _, v in tag_inserted]}')
    # The generated block files: a particle-only blockstate (the machine is drawn by its renderer), the particle model on the imported icon, the builtin/entity item model, a drop-self loot table.
    generated_facts = {}
    for p, wanted in (('assets/hbmsntm/blockstates/rbmk_crane_console.json', {'variants': {'': {'model': 'hbmsntm:block/rbmk_crane_console_particle'}}}),
                      ('assets/hbmsntm/models/block/rbmk_crane_console_particle.json', {'textures': {'particle': 'hbmsntm:block/rbmk/rbmk_crane_console'}}),
                      ('assets/hbmsntm/models/item/rbmk_crane_console.json', {'parent': 'minecraft:builtin/entity', 'gui_light': 'side'})):
        live = read(ROOT/(GENERATED_ROOT+p)) if (ROOT/(GENERATED_ROOT+p)).is_file() else None
        generated_facts[p] = live
        need(live == wanted, f'generated {p} is not the expected particle-only form: {live}')
    loot_path = GENERATED_ROOT+'data/hbmsntm/loot_table/blocks/rbmk_crane_console.json'
    loot = read(ROOT/loot_path) if (ROOT/loot_path).is_file() else None
    generated_facts['data/hbmsntm/loot_table/blocks/rbmk_crane_console.json'] = loot
    need(loot is not None and loot.get('type') == 'minecraft:block' and [e.get('name') for pool in loot.get('pools', []) for e in pool.get('entries', [])] == ['hbmsntm:rbmk_crane_console'],
         f'generated {loot_path} does not drop hbmsntm:rbmk_crane_console: {loot}')
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
    crane_test_names = sorted(GAMETEST_METHOD.findall((ROOT/CRANE_TESTS).read_text(encoding='utf-8'))) if (ROOT/CRANE_TESTS).is_file() else []
    crane_annotations = annotations(ROOT/CRANE_TESTS) if (ROOT/CRANE_TESTS).is_file() else 0
    need(bool(crane_test_names) and crane_annotations == len(crane_test_names), f'{CRANE_TESTS} holds {crane_annotations} @GameTest annotations and {len(crane_test_names)} parsed methods')
    need(gametest_added == crane_annotations, f'GameTest sources grew by {gametest_added} tests, RBMKCraneGameTests holds {crane_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in crane_test_names), 'GameTest log lacks "[hbm-rbmk-crane] <name> passed" for: '+str([n for n in crane_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal25d/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal25d/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal25d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal25d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal25d/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA + OPTIONAL_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal25d/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal25c final run plus the Goal25D verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal25c final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal25D suite is already in the goal25c final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal25d/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal25c final set + the Goal25D verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal25d/'+VERIFY_REPORT+' (tools/migration/verify_goal25d_rbmk_crane.py report)'):
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
        verifier_references = sorted(set(re.findall(r'(?:TileEntityCraneConsole|RBMKCraneConsole|RenderCraneConsole|ItemRenderLibrary|TileEntityRBMKBase|TileEntityRBMKConsole|ItemRBMKTool|HbmKeybinds|'
                                                      r'CraftingManager|ModBlocks|ResourceManager)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        # The verifier ran against the final GameTest log and expected the sources' total.
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal25c compare target paths (which hold the 24A-25C paths) plus this batch's compare-inventory paths).
    cmp25b = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal25c/compare.json differs from the goal25c receipt'
    c25b_added = sorted(p for p in compare_paths(cmp25b['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c25b_modified = sorted(p for p in compare_paths(cmp25b['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(c25b_added) | set(c25b_modified) | set(own_target))
    expected_added = sorted(set(c25b_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal25d/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-25c paths + %d of this batch)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(c25b_added) + len(c25b_modified), len(own_target))):
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
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal25c (goal25c compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal25c_paths=len(c25b_added) + len(c25b_modified), goal25d_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the groups of 24B-25C.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-25C)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal25d.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal25c) package (run the final build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 5 resources and every compiled class equal the sources.
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
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 5 imported resources, the generated additions and '
             'the modified en_us.json / zh_cn.json / pickaxe tag / MANIFEST.MF are owned): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA),
             'Changed Java sources and goal25d JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, TAG_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + pickaxe tag + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        inners = [n for n in jar_delta['added'] if n.startswith('com/hbm/render/blockentity/RenderCraneConsole$')]
        need(bool(inners) or 'com/hbm/render/blockentity/RenderCraneConsole.class' in jar_delta['added'], 'RenderCraneConsole is not an added JAR class')
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal25c_start=sorted(repinned),
                   delivery_hash_differs_from_receipts=delivery_differs,
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, removed_comment_lines={p: len(v) for p, v in removed_comments.items()},
                   constants={k: c['neo'] == c.get('neo_expected', c['original']) for k, c in constants.items()}, neo_facts={k: f['neo'] == f['expected'] for k, f in neo_facts.items()},
                   sequences={k: s['neo'] == s.get('neo_expected', s['original']) for k, s in sequences.items()}, tick_order=tick_order, keybind_enum_neo_extra=keybind_enum['extra_neo_constants'],
                   client_imports_in_common_classes=sorted(p for p, v in client_imports.items() if v),
                   gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_crane_tests=crane_test_names, final_suites_expected=final_expected,
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
    rbmk_crane = dict(neo=[CRANE_BLOCK, CRANE_BE, CRANE_RENDER, RBMK_BASE_BE, RBMK_CONSOLE_BE, RBMK_LOADABLE, TOOL_ITEM, KEYBINDS, CLIENT_PROXY, RESOURCE_MANAGER],
                      original=[p for p in O_SOURCES], constants=constants, sequences=sequences, neo_only_facts=neo_facts, known_differences=KNOWN_DIFFERENCES, recipe_row=crafting,
                      tick_order=tick_order, keybind_enum=keybind_enum, generated_files=generated_facts, original_references=original_refs,
                      defaults=dict(speed=0.05, lift_step=0.04, lift_ticks='25 down, load or unload on the next tick, 25 up', detection_box='3 wide x 2 deep x 2 high in front of the core, first player only',
                                    crane_indicator_ticks=10, indicator_sync='one byte after heat in the RBMK base sync, not saved', network_range=250, findroom_max=16, tube_height=7, girder_offset=6,
                                    center_offset=1, rotation_step='90 mod 360', hardness=3, resistance=30, dimensions='{1,0,0,0,1,1} + {0,0,0,1,1,1}', offset=1, gui='none',
                                    default_keys='up, down, left, right, enter', nbt_keys='crane, craneRotationOffset, centerX/Y/Z, spanF/B/L/R, height, posFront, posLeft, held'),
                      note='The crane console is a DummyableBlock with two boxes (RBMKCraneConsole.java:25-60, getDimensions {1,0,0,0,1,1}, a second box {0,0,0,1,1,1}, offset 1) whose core block entity '
                           'holds the crane (TileEntityCraneConsole.java). setTarget (:299-313) links the rbmk_tool position, measures the free room in the four directions at the girder level '
                           '(findRoomExtent, 16 blocks at most, i - 1 at the first obstruction) and stores the centre one above the column top; the screwdriver turns the crane by 90 degrees. '
                           'A player standing in the detection box (3 x 2 x 2 in front of the core, the first player only, :119-135) moves the crane with the arrow keys at 0.05 per tick clamped '
                           'to the room (:157-177); Enter lowers the lift by 0.04 per tick (25 ticks), loads or unloads on the tick after arrival through IRBMKLoadable (column.load / unload / '
                           'provideNext, :90-117) and raises it again; the column below is marked with craneIndicator = 10 for the RBMK console (TileEntityRBMKBase.java:292-305, '
                           'TileEntityRBMKConsole.java). The state is saved without the lift progress and goesDown and synced by serialize / deserialize (:276-296, :228-262), '
                           'network range 250. RenderCraneConsole draws the console with joystick, meters and lamps, the girders, tube, carriage and lift, and has an item form '
                           '(ItemRenderLibrary.java:678-694). Not migrated: the OpenComputers callbacks and the 65536 render distance; NEO adds findCore null and type guards, setChanged calls, '
                           'moveCrane / startLoad for the GameTests and requires the rbmk_tool position keys.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), len(ASSETS), len(crane_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=start_head[:8],
                   uncommitted_start=dict(status_entries=len(status_lines), description=base['start_content']['uncommitted'], base_release=previous_rel, status=status_lines,
                                          start_hashes_file='build/migration/goal25d/start_hashes.txt', start_paths=len(start_dirty),
                                          delivery_paths_match_receipts_changed_files=True, paths_whose_start_hash_differs_from_receipt_after_sha256=delivery_differs,
                                          note='The start hashes are the working tree at the start (the Goal25A, Goal25B and Goal25C deliveries are uncommitted), not the commit 783b6d13. '
                                               'start_hashes.txt (written by capture_start.py before the first 25D write) lists one entry per file; start_status.txt may show an untracked directory as one line.'),
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, build_libs_sha256_at_freeze=base['build_libs_jar_sha256_at_freeze'],
                                      reconstruction=base['reconstruction'], goal24_closeout_commit=closeout,
                                      note='The start tree is HEAD 783b6d13 (the Goal 25 planning commit, local, not pushed) on top of the pushed Goal 24 close-out commit 17c8062f, PLUS the uncommitted '
                                           'Goal25A, Goal25B and Goal25C deliveries (121 status lines, packaged as goal25a, goal25b and goal25c). build/libs at the start AND at the freeze IS the goal25c package. '
                                           'The original did not move since 24A (aee05a40f). The start was captured before any 25D write (capture_start.py) and freeze_start.py rebuilt the start tree '
                                           'from the captures; baseline-files holds 136 verbatim copies; paths this batch changes record the start hash as before_sha256, and a modified file the freeze '
                                           'did not copy has no reproducible start bytes.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, removed_comment_lines=removed_comments, start_copies_supplement=[],
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   rbmk_crane=rbmk_crane,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note=f'All {EXPECTED_KINDS.get("upstream", 0)} entries are upstream with the original English and Chinese verbatim: the block name (tile.rbmk_crane_console.name, '
                                      'en_US.lang:6222, zh_CN.lang:5347) and the five key labels (hbm.key.craneMoveUp/Down/Left/Right/craneLoad, en_US.lang:1433-1437, zh_CN.lang:1157-1161). '
                                      'No existing key changes its English value; no deferred entry is added.'),
                   recipes=dict(assembly=None, crafting=crafting, not_registered=[],
                                original_references={k: v for k, v in original_refs.items() if k.startswith('recipe_')},
                                anvil_recipes_unchanged=sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES],
                                note='The recipe is the shaped crafting row BCD / DDD with boron ingot, analog circuit board and deco_rbmk (CraftingManager.java:990, inside !enable528; NEO registers it '
                                     'unconditionally) and the generated JSON equals it. AnvilRecipes stays unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith('repinned_since_')},
                   repinned_since_goal25c_start={p: dict(goal25c_start_pin_sha256=h, goal25d_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_crane_tests=crane_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per RBMKCraneGameTests test: the two-box placement and '
                                      'break, the span search, the lift timings and the load / unload through IRBMKLoadable, the detection box and the keys as moveCrane / startLoad, the crane '
                                      'marker on the base column, the NBT and sync round trip, the rbmk_tool linking and the recipe, hardness and resistance; no client (the renderer, the item '
                                      'form, the key bindings and the client key read, the console grid drawing are not rendered or pressed), no real player, no saved world, no survival chain.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['rbmk_autoloader (the Goal25C-only key; Goal25D adds rbmk_crane; the autoloader constants, assembly row and state-machine facts are not carried)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. No in-game client test was run: '
                            'the crane renderer and item form, the key bindings and the Enter / arrow key input, the RBMK console crane marker, the Chinese UI and the OBJ models in game are unverified; no '
                            'survival chain (crafting the console, linking the rbmk_tool, moving a rod between columns) in a world was run; no multiplayer or dedicated server beyond GameTest; '
                            'GOAL25D-ACCEPTANCE.md (the unified Goal 25 real-game checklist) is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal25d JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal25c package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
