"""Package Goal25C (the third batch of Goal 25, RBMK operation and fuel logistics: the RBMK autoloader rbmk_autoloader, a 1x9 DummyableBlock machine (RBMKAutoloaderBlock with the core
RBMKAutoloaderBlockEntity: 18 slots, 9 inputs and 9 outputs, the four-stage piston state machine with SPEED 0.005 and 40-tick pauses, a 20-tick check, the cycle threshold 5..95 %, the
hull limit 1,000) standing on a fuel channel, RBMKAutoloaderMenu, RBMKAutoloaderScreen, the OBJ block entity renderer with its item form, the lift sounds and the tower-steam particles)
with its assembly-machine recipe ass.rbmkautoloader (a Java row in AssemblyMachineRecipes, no generated recipe JSON), four imported resources, two language keys,
RBMKAutoloaderGameTests and the 25C acceptance checklist GOAL25C-ACCEPTANCE.md, cumulatively on the goal25b package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal25c.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal25c/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal25c/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal25c/baseline.json: NEO HEAD 783b6d13 (the Goal 25 planning commit, local, on top of the pushed Goal 24 close-out commit 17c8062f) PLUS the
UNCOMMITTED Goal25A and Goal25B deliveries (98 status lines, packaged as goal25a and goal25b and committed together with 25C-25D after the unified acceptance, GOAL25 decision 2).
Unlike the earlier freezes this one RECONSTRUCTS the start (freeze_start.py docstring): the first 25C writes (the four imported resources, their ownership record, the two Chinese
entries, builder edits) had begun before the freeze ran, so the start hashes come from start_status.txt / start_hashes.txt / baseline-files captured before the first 25C write and,
for every clean file, from the HEAD blob in worktree form. build/libs at the start IS the goal25b package (baseline build_libs_jar_sha256_at_start); at the freeze it was already a
builder build (build_libs_jar_sha256_at_freeze), which is not evidence. The original HEAD aee05a40f did not move since 24A, so there is no upstream classification and no new
snapshot. Every change since the start is computed from the baseline file hashes (not from git diff) and must be in the owner table below; every other path must still equal its
start hash. The modified production files are compared with their start bytes (baseline-files holds 101 scope copies, ResourceManager.java and AssemblyMachineRecipes.java among
them; a modified file the freeze did not copy has NO reproducible start bytes and is reported as pending). The JAR delta against the goal25b package is attributed per entry
(goal25c only); any entry without exactly one owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys) are computed here,
never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal25a, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start for the acceptance checklists,
GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes build/migration/goal24a/main-notes.md (baseline older_receipt_evidence_drift); the goal25b receipt
differs from nothing at the start (baseline previous_receipt_evidence_drift is empty). They are listed in the receipt as start drift and must still equal their Goal25C start hash; no
receipt is rewritten and no other protected path may drift. The Goal 25 planning documents of 25D (migration/GOAL25D.md, GOAL25-THREAD-PROMPTS.md) and the Goal25A, Goal25B and Goal24
records must equal their start hash; migration/GOAL25.md and GOAL25C.md are edited by the main agent (GOAL25.md is a shared record, GOAL25C.md the task book and delivery record,
hashed by the receipt).

Like the earlier packagers of 24B..25B this one has a single compare run (build/migration/goal25c/compare.json against the snapshot review-aee05a40f10f.json taken at the end of 24A:
original 0/0/0, target = exactly the goal25b compare target paths (24A-25B, read from build/migration/goal25b/compare.json) plus this batch's compare-inventory paths), no upstream
classification; it adds the rbmk_autoloader constants (checked against the original and NEO source texts). The Goal25B-only receipt key rbmk_outgasser is dropped."""
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
from package_goal25b import OUT as GOAL25B_OUT, BASELINE as GOAL25B_BASELINE, protected_paths as goal25b_protected_paths

OUT = ROOT/'build/migration/goal25c'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
START_HASHES = OUT/'start_hashes.txt'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
REFERENCE_PREVIOUS = GOAL25B_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL25B_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal25b/hbmsntm-198A-goal25b.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
OLDER_PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal25a/release.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal25c'
RELEASE_NAME = 'hbmsntm-198A-goal25c.jar'
OWNER = 'goal25c'
PLANNING_PREFIX = '783b6d13'
GOAL24_CLOSEOUT = '17c8062f'
START_STATUS_LINES = 98
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'

# Production (owner goal25c), NEW (handoff-packaging.md; builder-report.md names the final classes: if a class is named differently or a helper class is added, edit this
# list, --check reports the difference as an unassigned src/ path).
NEW_JAVA = [J+p+'.java' for p in (
    'blocks/machine/rbmk/RBMKAutoloaderBlock', 'blockentity/machine/rbmk/RBMKAutoloaderBlockEntity', 'inventory/menus/RBMKAutoloaderMenu', 'inventory/screens/RBMKAutoloaderScreen',
    'render/blockentity/RenderRBMKAutoloader', 'gametest/RBMKAutoloaderGameTests')]
(AUTOLOADER_BLOCK, AUTOLOADER_BE, AUTOLOADER_MENU, AUTOLOADER_SCREEN, AUTOLOADER_RENDER, AUTOLOADER_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails; a review fix may add a file: --check reports it
# as an unassigned src/ path instead of failing silently).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blocks/NtmBlocks', 'blockentity/NtmBlockEntityTypes', 'inventory/NtmMenuTypes', 'inventory/NtmCreativeTabs', 'main/NuclearTechModClient', 'main/ClientProxy', 'main/ResourceManager',
    'inventory/recipes/AssemblyMachineRecipes', 'datagen/NtmBlockStateProvider', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmLanguageProvider')]
(BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, CREATIVE_TABS, CLIENT, CLIENT_PROXY, RESOURCE_MANAGER, ASSEMBLY_RECIPES, BLOCK_STATE_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER, PROVIDER) = MODIFIED_JAVA
# Frozen copies the freeze took that this batch is not expected to change (a change fails as an unassigned path).
OPTIONAL_JAVA = []
SAME_CLASS_JAVA = []
NO_CLASS_JAVA = []
# JAR classes whose source is unchanged since the start and that differ from the previous package only in recompiled debug names; none known at the Goal25C start (the goal25b package
# already carries the recompiled RBMKRecyclingGameTests$1 of Goal25B). An entry maps the class to the exact Utf8 constants replaced: it is owned as a recompile difference only when its
# source is unchanged and the previous bytes with exactly these constants replaced equal the new bytes (the Goal25B precedent: javap -v shows only LocalVariableTable names).
RECOMPILE_ONLY = {}
RECOMPILE_OWNER = 'recompile-debug-names'
ANVIL_RECIPES = J+'inventory/recipes/anvil/AnvilRecipes.java'
ROD_BE = J+'blockentity/machine/rbmk/RBMKRodBlockEntity.java'
# Every modified registration, datagen and assembly-recipe file stays insert-only against its start bytes (the Chinese file and the mapping only gain lines too): at the Goal25C start the
# real diff of all 12 files and both records against baseline-files was insert-only (computed with this module's insertions()).
STRICT_INSERT_ONLY = list(MODIFIED_JAVA) + [ZH_INPUT, LOCALIZATION_RECORD]
# No non-strict file in this batch: kept so a future non-insert-only file would need an explicit allowance (as in 25B) instead of passing silently.
ALLOWED_REMOVED_CODE = {}
# The 4 imported original resources: NEO target -> original path, derived by the layout rules of the ownership record (textures/blocks -> textures/block/rbmk, the OBJ goes under
# models/obj, the model texture and the GUI keep their path).
ASSETS = {
    ASSETS_ROOT+'models/obj/rbmk/autoloader.obj': O_RES+'models/rbmk/autoloader.obj',
    ASSETS_ROOT+'textures/models/machines/rbmk_autoloader.png': O_RES+'textures/models/machines/rbmk_autoloader.png',
    ASSETS_ROOT+'textures/block/rbmk/rbmk_autoloader.png': O_RES+'textures/blocks/rbmk_autoloader.png',
    ASSETS_ROOT+'textures/gui/machine/gui_autoloader.png': O_RES+'textures/gui/machine/gui_autoloader.png',
}
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
TAG_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
GENERATED = [STAMP, EN, GENERATED_ROOT+TAG_ENTRY]
# Generated by runData for this batch (relative to src/generated/resources): the particle-only blockstate, the particle and item models, the loot table. No crafting recipe and no
# advancement (the recipe is an assembly-machine row in Java).
EXPECTED_GENERATED = sorted(['assets/hbmsntm/blockstates/rbmk_autoloader.json', 'assets/hbmsntm/models/block/rbmk_autoloader_particle.json', 'assets/hbmsntm/models/item/rbmk_autoloader.json',
                             'data/hbmsntm/loot_table/blocks/rbmk_autoloader.json'])
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, TAG_ENTRY])
NEW_TOOLS = ['tools/migration/verify_goal25c_rbmk_autoloader.py', 'tools/migration/package_goal25c.py']
TOOLS = NEW_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal25c-* or GOAL25C-* record is hashed as well.
REPORTS = ['migration/GOAL25C.md', 'migration/GOAL25C-ACCEPTANCE.md', 'migration/goal25c-static-review.md', 'migration/goal25c-localization-review.json',
           'migration/goal25c-resource-ownership.json', 'migration/goal25c-materials-review.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal25c-[^/]+\.(json|md)|GOAL25C-[^/]+\.md)')
GOAL25_RECORD = 'migration/GOAL25.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md',
                  'migration/RESOURCE-OWNERSHIP.md', GOAL25_RECORD]
# Shared records the batch may leave untouched (FOUNDATIONS.md and RESOURCE-OWNERSHIP.md "if touched").
OPTIONAL_RECORDS = ['migration/FOUNDATIONS.md', 'migration/RESOURCE-OWNERSHIP.md']
# The Goal 25 planning documents of the later batch: no change is expected in this batch.
PLANNING_FROZEN = ['migration/GOAL25D.md', 'migration/GOAL25-THREAD-PROMPTS.md']
FROZEN_RECORD = re.compile(r'migration/(GOAL25[AB][^/]*\.md|goal25[ab]-[^/]+|GOAL24[^/]*\.md|goal24[^/]*)')
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]
# The new language keys: NEO key -> (original key, expected map kind). The block and container names are upstream under the original keys (the autoloader keeps the original English and
# Chinese verbatim: en_US.lang:788 / :6212, zh_CN.lang:5911 / :5920).
SOURCE_KEYS = {'block.hbmsntm.rbmk_autoloader': ('tile.rbmk_autoloader.name', 'upstream'), 'container.rbmkAutoloader': ('container.rbmkAutoloader', 'upstream')}
KEYS = {k: v[0] for k, v in SOURCE_KEYS.items()}
EXPECTED_KINDS = dict(Counter(v[1] for v in SOURCE_KEYS.values()))
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rbmk-autoloader] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start. There is no handoff-production.md
# in 25C (the builder's handoff is recorded in main-notes.md) and no add_zh.py / make_ownership.py (the main agent wrote those records directly).
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_hashes.txt', 'start_head.txt',
                  'main-notes.md', 'builder-report.md', 'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md', 'verifier-report.md', 'review-report.md', 'chain.sh',
                  'make_production_diff.py')
# Review files under OUT (for example the static review's notes or diffs) the main agent names when it knows them; each must exist and is indexed by the receipt. Extend this list from the
# real run (review notes, the builder's and verifiers' progress and scope files, logs ...); --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'builder_compile.log', 'builder_rundata.log', 'builder_build.log',
                   'review-report.md', 'review-diff.patch', 'review-new-files.txt', 'verifier-progress.md')
GAMETEST_LOG = 'build/migration/goal25c/gametest-final.log'
NEW_SUITE = 'verify_goal25c_rbmk_autoloader.py --gametest-log build/migration/goal25c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_AUTOLOADER = 'rbmk-autoloader'
NEW_FEATURES = (FEATURE_AUTOLOADER,)
# The groups the snapshot of the end of 24A predates (24B rbmk-fuel, 24C rbmk-reactor, 24D rbmk-control and rbmk-steam, 24E rbmk-console, 25A rbmk-storage and rbmk-recycling,
# 25B rbmk-outgasser).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser'}
RADIATION_NOTE = ('Goal25C: the autoloader moves spent fuel rods out of the reactor into its output slots, where they remain radioactive and possibly hot; the acceptance checklist '
                  'GOAL25C-ACCEPTANCE.md must be run only in a separately authorized disposable world. ')
MELTDOWN_NOTE = 'Goal25C: the autoloader adds no meltdown path of its own; reactor tests stay in disposable worlds. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_TE = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKAutoloader.java'
O_BLOCK = ORIGINAL+'blocks/machine/rbmk/RBMKAutoloader.java'
O_CONTAINER = ORIGINAL+'inventory/container/ContainerRBMKAutoloader.java'
O_GUI = ORIGINAL+'inventory/gui/GUIRBMKAutoloader.java'
O_RENDER = ORIGINAL+'render/tileentity/RenderRBMKAutoloader.java'
O_ROD = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKRod.java'
O_MACHINE_BASE = ORIGINAL+'tileentity/TileEntityMachineBase.java'
O_ASSEMBLY = ORIGINAL+'inventory/recipes/AssemblyMachineRecipes.java'
O_MODBLOCKS = ORIGINAL+'blocks/ModBlocks.java'
O_RESOURCE_MANAGER = ORIGINAL+'main/ResourceManager.java'
O_SOUNDS = 'src/main/resources/assets/hbm/sounds.json'
O_SOURCES = [O_TE, O_BLOCK, O_CONTAINER, O_GUI, O_RENDER, O_ROD, O_MACHINE_BASE, O_ASSEMBLY, O_MODBLOCKS, O_RESOURCE_MANAGER, O_SOUNDS, O_LANG_EN, O_LANG_ZH]
# The original sources each new mapping group must list (source_paths or source_watch; plus the imported resources).
FEATURE_SOURCES = {FEATURE_AUTOLOADER: [O_TE, O_BLOCK, O_CONTAINER, O_GUI, O_RENDER, O_ASSEMBLY] + list(ASSETS.values())}
# The NEO paths each new mapping group must cover (target_paths or target_watch).
FEATURE_TARGETS = {FEATURE_AUTOLOADER: [AUTOLOADER_BLOCK, AUTOLOADER_BE, AUTOLOADER_MENU, AUTOLOADER_SCREEN, AUTOLOADER_RENDER, AUTOLOADER_TESTS, ASSEMBLY_RECIPES, RESOURCE_MANAGER,
                                        NEW_TOOLS[0], NEW_TOOLS[1]] + [GENERATED_ROOT+p for p in EXPECTED_GENERATED] + list(ASSETS)}
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'autoloader_class': (O_TE, 'public class TileEntityRBMKAutoloader extends TileEntityMachineBase'), 'autoloader_slots': (O_TE, 'super(18);'),
    'autoloader_speed': (O_TE, 'public static double speed = 0.005D;'), 'autoloader_cycle_default': (O_TE, 'public int cycle = 50;'),
    'autoloader_update': (O_TE, 'public void updateEntity()'), 'autoloader_retract': (O_TE, 'this.piston -= this.speed;'),
    'autoloader_check': (O_TE, 'worldObj.getTotalWorldTime() % 20 == 0'), 'autoloader_cold_check': (O_TE, 'rod.coldEnoughForAutoloader()'),
    'autoloader_swap_out_threshold': (O_TE, '* 100 < cycle'), 'autoloader_extend': (O_TE, 'this.piston += this.speed;'),
    'autoloader_extended': (O_TE, 'if(!isRetracting && this.piston >= 1D)'), 'autoloader_take_out': (O_TE, 'try to take out the old fuel rod'),
    'autoloader_insert': (O_TE, 'try and insert a new fuel rod'), 'autoloader_has_fuel': (O_TE, 'public boolean hasFuel()'), 'autoloader_has_space': (O_TE, 'public boolean hasSpace()'),
    'autoloader_serialize': (O_TE, 'public void serialize(ByteBuf buf)'), 'autoloader_deserialize': (O_TE, 'public void deserialize(ByteBuf buf)'),
    'autoloader_valid_for_slot': (O_TE, 'public boolean isItemValidForSlot('), 'autoloader_accessible_slots': (O_TE, 'public int[] getAccessibleSlotsFromSide('),
    'autoloader_can_extract': (O_TE, 'public boolean canExtractItem('), 'autoloader_read_nbt': (O_TE, 'public void readFromNBT('), 'autoloader_write_nbt': (O_TE, 'public void writeToNBT('),
    'autoloader_render_bbox': (O_TE, 'public AxisAlignedBB getRenderBoundingBox()'), 'autoloader_render_distance': (O_TE, 'public double getMaxRenderDistanceSquared()'),
    'autoloader_has_permission': (O_TE, 'public boolean hasPermission(EntityPlayer player)'), 'autoloader_receive_control': (O_TE, 'public void receiveControl('),
    'autoloader_get_settings': (O_TE, 'public NBTTagCompound getSettings('), 'autoloader_paste_settings': (O_TE, 'public void pasteSettings('),
    'autoloader_client_sound': (O_TE, 'getLoopedSound("hbm:door.wgh_start"'), 'autoloader_client_stop_sound': (O_TE, 'hbm:door.wgh_stop'),
    'autoloader_client_particle': (O_TE, 'data.setString("type", "tower");'),
    'rod_cold_enough': (O_ROD, 'public boolean coldEnoughForAutoloader()'), 'machine_base_use_range': (O_MACHINE_BASE, 'public double getUseRange()'),
    'machine_base_useable': (O_MACHINE_BASE, 'public boolean isUseableByPlayer('),
    'block_bounds': (O_BLOCK, 'this.bounding.add(AxisAlignedBB.getBoundingBox(-0.125'), 'block_core_meta': (O_BLOCK, 'if(meta >= 12) return new TileEntityRBMKAutoloader();'),
    'block_proxy': (O_BLOCK, 'new TileEntityProxyCombo().inventory()'), 'block_dimensions': (O_BLOCK, 'public int[] getDimensions()'), 'block_offset': (O_BLOCK, 'public int getOffset()'),
    'block_open': (O_BLOCK, 'standardOpenBehavior'), 'block_hardness': (O_MODBLOCKS, 'rbmk_autoloader = new RBMKAutoloader()'),
    'container_input': (O_CONTAINER, 'this.addSlots(loader, 0, 17, 18, 3, 3);'), 'container_output': (O_CONTAINER, 'this.addTakeOnlySlots(loader, 9, 107, 18, 3, 3);'),
    'container_player_inv': (O_CONTAINER, 'this.playerInv(invPlayer, 8, 100);'), 'container_shift': (O_CONTAINER, 'public ItemStack transferStackInSlot('),
    'container_can_interact': (O_CONTAINER, 'return loader.isUseableByPlayer(player);'),
    'gui_texture': (O_GUI, 'textures/gui/machine/gui_autoloader.png'), 'gui_size': (O_GUI, 'this.ySize = 182;'), 'gui_minus': (O_GUI, 'guiLeft + 74 <= x'), 'gui_plus': (O_GUI, 'guiLeft + 90 <= x'),
    'gui_percent': (O_GUI, 'String percent = loader.cycle + "%";'),
    'render_base': (O_RENDER, 'ResourceManager.rbmk_autoloader.renderPart("Base");'), 'render_piston': (O_RENDER, 'GL11.glTranslated(0, p * -4D, 0);'),
    'render_lift': (O_RENDER, 'GL11.glTranslated(0, 4, 0);'), 'render_item_scale': (O_RENDER, 'GL11.glScaled(1.75, 1.75, 1.75);'), 'render_item_shift': (O_RENDER, 'GL11.glTranslated(0, -6, 0);'),
    'resource_obj': (O_RESOURCE_MANAGER, 'rbmk_autoloader = new HFRWavefrontObject('), 'resource_texture': (O_RESOURCE_MANAGER, 'rbmk_autoloader_tex = new ResourceLocation('),
    'recipe_row': (O_ASSEMBLY, 'new GenericRecipe("ass.rbmkautoloader")'),
    'lang_container_en': (O_LANG_EN, 'container.rbmkAutoloader='), 'lang_block_en': (O_LANG_EN, 'tile.rbmk_autoloader.name='),
    'lang_container_zh': (O_LANG_ZH, 'container.rbmkAutoloader='), 'lang_block_zh': (O_LANG_ZH, 'tile.rbmk_autoloader.name='),
    'sound_start': (O_SOUNDS, '"door.wgh_start"'), 'sound_stop': (O_SOUNDS, '"door.wgh_stop"'),
}
# Constants compared between the original and NEO source texts: id -> (original path, regex, NEO path, regex, expected unique values in order[, expected NEO values when they differ]).
# Numbers are compared as floats (underscores dropped, F / D suffixes dropped), anything else as text. The group-1 value of every match is collected. A NEO regex that finds
# nothing (the class is not written yet, or its text differs from the handoff) is reported as pending with its id.
ENR = r'getEnrichment\([\w.\[\]()]+\) \* '
SOUND = r'getVolume\(0\.75F\), '
CONSTANTS = {
    # Block entity (TileEntityRBMKAutoloader): 18 slots, the speed, the default threshold, the 40-tick pauses, the 20-tick check, the enrichment tests, the hull limit.
    'slots': (O_TE, r'super\((\d+)\);', AUTOLOADER_BE, r'RBMK_AUTOLOADER\.get\(\), pos, state, (\d+)\)', [18]),
    'speed': (O_TE, r'public static double speed = ([\d.]+)D;', AUTOLOADER_BE, r'public static final double SPEED = ([\d.]+)D;', [0.005]),
    'cycle_default': (O_TE, r'public int cycle = (\d+);', AUTOLOADER_BE, r'public int cycle = (\d+);', [50]),
    'pause_ticks': (O_TE, r'this\.delay = (\d+);', AUTOLOADER_BE, r'this\.delay = (\d+);', [40]),
    'check_interval': (O_TE, r'getTotalWorldTime\(\) % (\d+) == 0', AUTOLOADER_BE, r'getGameTime\(\) % (\d+) == 0', [20]),
    'swap_out_multiplier': (O_TE, ENR+r'(\d+) < cycle', AUTOLOADER_BE, ENR+r'(\d+) < cycle', [100]),
    'swap_out_operator': (O_TE, ENR+r'\d+ (<=?) cycle', AUTOLOADER_BE, ENR+r'\d+ (<=?) cycle', ['<']),
    'load_multiplier': (O_TE, ENR+r'(\d+) >=? cycle', AUTOLOADER_BE, ENR+r'(\d+) >=? cycle', [100]),
    'load_operator': (O_TE, ENR+r'\d+ (>=?) cycle', AUTOLOADER_BE, ENR+r'\d+ (>=?) cycle', ['>=']),
    'cold_check_call': (O_TE, r'rod\.(coldEnoughForAutoloader)\(\)', AUTOLOADER_BE, r'rod\.(coldEnoughForAutoloader)\(\)', ['coldEnoughForAutoloader']),
    'hull_limit': (O_ROD, r'coldEnoughForAutoloader\(\) \{[^}]*?getHullHeat\([\w.\[\]]+\) <= ([\d_]+);', ROD_BE, r'coldEnoughForAutoloader\(\) \{[^}]*?getHullHeat\(\w+\) <= ([\d_]+);', [1000]),
    'rod_slot': (O_TE, r'rod\.slots\[(\d+)\]', AUTOLOADER_BE, r'rod\.slots\.get\((\d+)\)', [0]),
    'piston_full': (O_TE, r'this\.piston >= (\d+)[D)]', AUTOLOADER_BE, r'this\.piston >= (\d+)[D)]', [1]),
    'piston_retract_guard': (O_TE, r'this\.piston > (\d+)D', AUTOLOADER_BE, r'this\.piston > (\d+)D', [0]),
    'piston_extend_guard': (O_TE, r'this\.piston < (\d+)D', AUTOLOADER_BE, r'this\.piston < (\d+)D', [1]),
    'piston_empty': (O_TE, r'this\.piston <= (\d+)\)', AUTOLOADER_BE, r'this\.piston <= (\d+)\)', [0]),
    'output_loop_start': (O_TE, r'for\(int i = (\d+); i < 18; i\+\+\)', AUTOLOADER_BE, r'for\(int i = (\d+); i < 18; i\+\+\)', [9]),
    'input_loop_end': (O_TE, r'for\(int i = 0; i < (\d+); i\+\+\) \{\s*ItemStack stack', AUTOLOADER_BE, r'for\(int i = 0; i < (\d+); i\+\+\) \{\s*ItemStack stack', [9]),
    # Automation: only inputs with enough enrichment into slots 0-8, extraction only from 9 up, every slot visible only while the piston is up.
    'input_slot_limit': (O_TE, r'>= cycle && i < (\d+);', AUTOLOADER_BE, r'return i < (\d+) && stack', [9]),
    'extract_from': (O_TE, r'canExtractItem\(int i, ItemStack itemStack, int j\) \{\s*return i >= (\d+);', AUTOLOADER_BE,
                     r'canTakeItemThroughFace\(int i, ItemStack stack, Direction direction\) \{\s*return i >= (\d+);', [9]),
    'face_operator': (O_TE, r'this\.piston (<=?) 0 \?', AUTOLOADER_BE, r'this\.piston (<=?) 0 \?', ['<=']),
    'face_slots': (O_TE, r'this\.piston <= 0 \? new int\[\] \{\s*(\d[\d, ]*\d)\s*\}', AUTOLOADER_BE, r'SLOTS = new int\[\] \{([\d, ]+)\};', ['0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17']),
    'face_slots_hidden': (O_TE, r': new int\[(\d+)\];', AUTOLOADER_BE, r'NO_SLOTS = new int\[(\d+)\];', [0]),
    # NBT and the client sync.
    'nbt_read_double': (O_TE, r'nbt\.getDouble\("(\w+)"\)', AUTOLOADER_BE, r'tag\.getDouble\("(\w+)"\)', ['piston']),
    'nbt_read_boolean': (O_TE, r'nbt\.getBoolean\("(\w+)"\)', AUTOLOADER_BE, r'tag\.getBoolean\("(\w+)"\)', ['ret']),
    'nbt_read_int': (O_TE, r'nbt\.getInteger\("(\w+)"\)', AUTOLOADER_BE, r'tag\.getInt\("(\w+)"\)', ['delay', 'cycle']),
    'nbt_write_double': (O_TE, r'nbt\.setDouble\("(\w+)"', AUTOLOADER_BE, r'tag\.putDouble\("(\w+)"', ['piston']),
    'nbt_write_boolean': (O_TE, r'nbt\.setBoolean\("(\w+)"', AUTOLOADER_BE, r'tag\.putBoolean\("(\w+)"', ['ret']),
    'nbt_write_int': (O_TE, r'nbt\.setInteger\("(\w+)"', AUTOLOADER_BE, r'tag\.putInt\("(\w+)"', ['delay', 'cycle']),
    'sync_write_order': (O_TE, r'buf\.write(Double|Int)\(', AUTOLOADER_BE, r'buf\.write(Double|Int)\(', ['Double', 'Int']),
    'sync_read_order': (O_TE, r'buf\.read(Double|Int)\(', AUTOLOADER_BE, r'buf\.read(Double|Int)\(', ['Double', 'Int']),
    'turn_progress': (O_TE, r'this\.turnProgress = (\d+);', AUTOLOADER_BE, r'this\.turnProgress = (\d+);', [2]),
    'turn_progress_guard': (O_TE, r'this\.turnProgress > (\d+)', AUTOLOADER_BE, r'this\.turnProgress > (\d+)', [0]),
    # Control, copy settings and the use range.
    'control_keys': (O_TE, r'data\.hasKey\("(\w+)"\)', AUTOLOADER_BE, r'data\.contains\("(\w+)"\)', ['minus', 'plus']),
    'control_floor_guard': (O_TE, r'this\.cycle > (\d+)', AUTOLOADER_BE, r'this\.cycle > (\d+)', [5]),
    'control_step_down': (O_TE, r'this\.cycle -= (\d+)', AUTOLOADER_BE, r'this\.cycle -= (\d+)', [5]),
    'control_ceiling_guard': (O_TE, r'this\.cycle < (\d+)', AUTOLOADER_BE, r'this\.cycle < (\d+)', [95]),
    'control_step_up': (O_TE, r'this\.cycle \+= (\d+)', AUTOLOADER_BE, r'this\.cycle \+= (\d+)', [5]),
    'control_clamp_low': (O_TE, r'clamp_int\(cycle, (\d+), \d+\)', AUTOLOADER_BE, r'Mth\.clamp\(this\.cycle, (\d+), \d+\)', [5]),
    'control_clamp_high': (O_TE, r'clamp_int\(cycle, \d+, (\d+)\)', AUTOLOADER_BE, r'Mth\.clamp\(this\.cycle, \d+, (\d+)\)', [95]),
    'settings_key': (O_TE, r'data\.setInteger\("(\w+)", cycle\)', AUTOLOADER_BE, r'data\.putInt\("(\w+)", cycle\)', ['cycle']),
    'paste_key': (O_TE, r'nbt\.hasKey\("(\w+)"\)', AUTOLOADER_BE, r'nbt\.contains\("(\w+)"\)', ['cycle']),
    'paste_clamp_low': (O_TE, r'clamp_int\(nbt\.getInteger\("cycle"\), (\d+), \d+\)', AUTOLOADER_BE, r'Mth\.clamp\(nbt\.getInt\("cycle"\), (\d+), \d+\)', [5]),
    'paste_clamp_high': (O_TE, r'clamp_int\(nbt\.getInteger\("cycle"\), \d+, (\d+)\)', AUTOLOADER_BE, r'Mth\.clamp\(nbt\.getInt\("cycle"\), \d+, (\d+)\)', [95]),
    'use_range': (O_MACHINE_BASE, r'getUseRange\(\) \{\s*return ([\d.]+)D;', AUTOLOADER_BE, r'<= (\d+)D \* \d+D;', [12]),
    'render_box_height': (O_TE, r'yCoord \+ (\d+), zCoord \+ 1\)', AUTOLOADER_BE, r'pos\.getY\(\) \+ (\d+), pos\.getZ\(\) \+ 1\)', [9]),
    # Client effects: the lift loop sound and the stop sound, the interpolation thresholds, the tower particles.
    'sound_names': (O_TE, r'door\.(wgh_\w+)"', AUTOLOADER_BE, r'NtmSoundEvents\.(WGH_\w+)\.get\(\)', ['wgh_start', 'wgh_stop'], ['WGH_START', 'WGH_STOP']),
    'sound_volumes': (O_TE, r'getVolume\(([\d.]+)F\)', AUTOLOADER_BE, r'getVolume\(([\d.]+)F\)', [0.75, 2]),
    'sound_distance': (O_TE, SOUND+r'([\d.]+)F, [\d.]+F, \d+\)', AUTOLOADER_BE, SOUND+r'([\d.]+)F, [\d.]+F, \d+\)', [25]),
    'sound_pitch': (O_TE, SOUND+r'[\d.]+F, ([\d.]+)F, \d+\)', AUTOLOADER_BE, SOUND+r'[\d.]+F, ([\d.]+)F, \d+\)', [1.0]),
    'sound_keep_alive': (O_TE, SOUND+r'[\d.]+F, [\d.]+F, (\d+)\)', AUTOLOADER_BE, SOUND+r'[\d.]+F, [\d.]+F, (\d+)\)', [5]),
    'render_piston_thresholds': (O_TE, r'this\.renderPiston > ([\d.]+)', AUTOLOADER_BE, r'this\.renderPiston > ([\d.]+)', [0.01, 0.99]),
    'render_piston_upper': (O_TE, r'this\.renderPiston < ([\d.]+)', AUTOLOADER_BE, r'this\.renderPiston < ([\d.]+)', [0.99]),
    'particle_type': (O_TE, r'"type", "(\w+)"', AUTOLOADER_BE, r'NtmParticleTypes\.(COOLING_TOWER)\.get\(\)', ['tower'], ['COOLING_TOWER']),
    'particle_lift': (O_TE, r'"lift", ([\d.]+)F\)', AUTOLOADER_BE, r'"lift", ([\d.]+)F\)', [0]),
    'particle_base': (O_TE, r'"base", ([\d.]+)F\)', AUTOLOADER_BE, r'"base", ([\d.]+)F\)', [0.25]),
    'particle_max': (O_TE, r'"max", ([\d.]+)F\)', AUTOLOADER_BE, r'"max", ([\d.]+)F\)', [1.5]),
    'particle_life_base': (O_TE, r'"life", (\d+) \+', AUTOLOADER_BE, r'"life", (\d+) \+', [70]),
    'particle_life_random': (O_TE, r'"life", \d+ \+ [\w.]+\.nextInt\((\d+)\)', AUTOLOADER_BE, r'"life", \d+ \+ [\w.]+\.nextInt\((\d+)\)', [30]),
    'particle_gaussian': (O_TE, r'nextGaussian\(\) \* ([\d.]+)', AUTOLOADER_BE, r'nextGaussian\(\) \* ([\d.]+)', [0.125]),
    'particle_centre': (O_TE, r'"posX", xCoord \+ ([\d.]+) \+', AUTOLOADER_BE, r'double posX = x \+ ([\d.]+) \+', [0.5]),
    'particle_height': (O_TE, r'"posY", yCoord \+ ([\d.]+)', AUTOLOADER_BE, r', y \+ ([\d.]+), posZ', [0.25]),
    'particle_no_wind': (O_TE, r'"noWind", (\w+)\)', AUTOLOADER_BE, r'"noWind", (\w+)\)', ['true']),
    'particle_alpha_mod': (O_TE, r'"alphaMod", ([\d.]+)F\)', AUTOLOADER_BE, r'"alphaMod", ([\d.]+)F\)', [2]),
    'particle_strafe': (O_TE, r'"strafe", ([\d.]+)F\)', AUTOLOADER_BE, r'"strafe", ([\d.]+)F\)', [0.05]),
    'particle_count': (O_TE, r'for\(int i = 0; i < (\d+); i\+\+\) MainRegistry\.proxy\.effectNT\(data\)', AUTOLOADER_BE, r'for\(int i = 0; i < (\d+); i\+\+\) \{\s*ParticleUtil\.addParticle', [3]),
    # Block (RBMKAutoloader): the two collision boxes, the 1x9 dimensions, the offset, hardness 50 / resistance 60.
    'block_bounds': (O_BLOCK, r'getBoundingBox\(([-\d., ]+)\)', AUTOLOADER_BLOCK, r'new AABB\(([-\d., ]+)\)', ['-0.125, 0, -0.125, 0.125, 4, 0.125', '-0.5, 4, -0.5, 0.5, 9, 0.5']),
    'block_dimensions': (O_BLOCK, r'return new int\[\] \{([\d, ]+)\};', AUTOLOADER_BLOCK, r'new int\[\] \{([\d, ]+)\}', ['8, 0, 0, 0, 0, 0']),
    'block_offset': (O_BLOCK, r'getOffset\(\) \{\s*return (\d+);', AUTOLOADER_BLOCK, r'getOffset\(\) \{\s*return (\d+);', [0]),
    'block_hardness': (O_MODBLOCKS, r'rbmk_autoloader = new RBMKAutoloader\(\)[^\n]*?setHardness\(([\d.]+)F\)', BLOCKS,
                       r'RBMK_AUTOLOADER = register\("rbmk_autoloader"[^\n]*?strength\(([\d.]+)F, [\d.]+F\)', [50]),
    'block_resistance': (O_MODBLOCKS, r'rbmk_autoloader = new RBMKAutoloader\(\)[^\n]*?setResistance\(([\d.]+)F\)', BLOCKS,
                         r'RBMK_AUTOLOADER = register\("rbmk_autoloader"[^\n]*?strength\([\d.]+F, ([\d.]+)F\)', [60]),
    # Menu (ContainerRBMKAutoloader): the input grid at 17/18 (3 x 3), the take-only output grid at 107/18 from slot 9, the player inventory at 8/100, the shift rules.
    'menu_input_first': (O_CONTAINER, r'addSlots\(loader, (\d+), \d+, \d+, \d+, \d+\)', AUTOLOADER_MENU, r'addSlots\(be, (\d+), \d+, \d+, \d+, \d+\)', [0]),
    'menu_input_x': (O_CONTAINER, r'addSlots\(loader, \d+, (\d+), \d+, \d+, \d+\)', AUTOLOADER_MENU, r'addSlots\(be, \d+, (\d+), \d+, \d+, \d+\)', [17]),
    'menu_input_y': (O_CONTAINER, r'addSlots\(loader, \d+, \d+, (\d+), \d+, \d+\)', AUTOLOADER_MENU, r'addSlots\(be, \d+, \d+, (\d+), \d+, \d+\)', [18]),
    'menu_input_rows': (O_CONTAINER, r'addSlots\(loader, \d+, \d+, \d+, (\d+), \d+\)', AUTOLOADER_MENU, r'addSlots\(be, \d+, \d+, \d+, (\d+), \d+\)', [3]),
    'menu_input_columns': (O_CONTAINER, r'addSlots\(loader, \d+, \d+, \d+, \d+, (\d+)\)', AUTOLOADER_MENU, r'addSlots\(be, \d+, \d+, \d+, \d+, (\d+)\)', [3]),
    'menu_output_first': (O_CONTAINER, r'addTakeOnlySlots\(loader, (\d+), \d+, \d+, \d+, \d+\)', AUTOLOADER_MENU, r'addTakeOnlySlots\(be, (\d+), \d+, \d+, \d+, \d+\)', [9]),
    'menu_output_x': (O_CONTAINER, r'addTakeOnlySlots\(loader, \d+, (\d+), \d+, \d+, \d+\)', AUTOLOADER_MENU, r'addTakeOnlySlots\(be, \d+, (\d+), \d+, \d+, \d+\)', [107]),
    'menu_output_y': (O_CONTAINER, r'addTakeOnlySlots\(loader, \d+, \d+, (\d+), \d+, \d+\)', AUTOLOADER_MENU, r'addTakeOnlySlots\(be, \d+, \d+, (\d+), \d+, \d+\)', [18]),
    'menu_output_rows': (O_CONTAINER, r'addTakeOnlySlots\(loader, \d+, \d+, \d+, (\d+), \d+\)', AUTOLOADER_MENU, r'addTakeOnlySlots\(be, \d+, \d+, \d+, (\d+), \d+\)', [3]),
    'menu_output_columns': (O_CONTAINER, r'addTakeOnlySlots\(loader, \d+, \d+, \d+, \d+, (\d+)\)', AUTOLOADER_MENU, r'addTakeOnlySlots\(be, \d+, \d+, \d+, \d+, (\d+)\)', [3]),
    'menu_player_inventory_y': (O_CONTAINER, r'playerInv\((?:invPlayer|inventory), 8, (\d+)\)', AUTOLOADER_MENU, r'playerInv\((?:invPlayer|inventory), 8, (\d+)\)', [100]),
    'menu_shift_boundary': (O_CONTAINER, r'if\(index <= (\d+)\)', AUTOLOADER_MENU, r'if\(index <= (\d+)\)', [17]),
    'menu_shift_out_from': (O_CONTAINER, r'mergeItemStack\(stack, (\d+), this\.inventorySlots\.size\(\), true\)', AUTOLOADER_MENU, r'moveItemStackTo\(stack, (\d+), this\.slots\.size\(\), true\)', [18]),
    'menu_shift_out_reverse': (O_CONTAINER, r'this\.inventorySlots\.size\(\), (true|false)\)', AUTOLOADER_MENU, r'this\.slots\.size\(\), (true|false)\)', ['true']),
    'menu_shift_in_to': (O_CONTAINER, r'mergeItemStack\(stack, 0, (\d+), false\)', AUTOLOADER_MENU, r'moveItemStackTo\(stack, 0, (\d+), false\)', [9]),
    'menu_shift_in_reverse': (O_CONTAINER, r'mergeItemStack\(stack, 0, \d+, (true|false)\)', AUTOLOADER_MENU, r'moveItemStackTo\(stack, 0, \d+, (true|false)\)', ['false']),
    # Screen (GUIRBMKAutoloader): 176 x 182, the machine GUI texture, the two 12 x 12 buttons at 74 and 90 / 36 with the original comparison senses, the centred green percentage at y 23.
    'gui_width': (O_GUI, r'this\.xSize = (\d+);', AUTOLOADER_SCREEN, r'this\.imageWidth = (\d+);', [176]),
    'gui_height': (O_GUI, r'this\.ySize = (\d+);', AUTOLOADER_SCREEN, r'this\.imageHeight = (\d+);', [182]),
    'gui_texture': (O_GUI, r'textures/gui/(machine/gui_autoloader\.png)', AUTOLOADER_SCREEN, r'textures/gui/(machine/gui_autoloader\.png)', ['machine/gui_autoloader.png']),
    'gui_button_x': (O_GUI, r'guiLeft \+ (\d+) <= x', AUTOLOADER_SCREEN, r'leftPos \+ (\d+) <= x', [74, 90]),
    'gui_button_width': (O_GUI, r'guiLeft \+ \d+ \+ (\d+) > x', AUTOLOADER_SCREEN, r'leftPos \+ \d+ \+ (\d+) > x', [12]),
    'gui_button_y': (O_GUI, r'guiTop \+ (\d+) < y', AUTOLOADER_SCREEN, r'topPos \+ (\d+) < y', [36]),
    'gui_button_height': (O_GUI, r'guiTop \+ \d+ \+ (\d+) >= y', AUTOLOADER_SCREEN, r'topPos \+ \d+ \+ (\d+) >= y', [12]),
    'gui_control_keys': (O_GUI, r'data\.setBoolean\("(\w+)", true\)', AUTOLOADER_SCREEN, r'data\.putBoolean\("(\w+)", true\)', ['minus', 'plus']),
    'gui_percent_y': (O_GUI, r'/ 2, (\d+), 0x00FF00\)', AUTOLOADER_SCREEN, r'/ 2, (\d+), 0x00FF00', [23]),
    'gui_percent_colour': (O_GUI, r'/ 2, 23, (0x[0-9A-Fa-f]+)\)', AUTOLOADER_SCREEN, r'/ 2, 23, (0x[0-9A-Fa-f]+), false\)', ['0x00FF00']),
    'gui_title_y': (O_GUI, r'/ 2, (\d+), 0xFFFFFF\)', AUTOLOADER_SCREEN, r'/ 2, (\d+), 0xFFFFFF', [6]),
    'gui_inventory_label': (O_GUI, r'this\.ySize - (\d+) \+ 2', AUTOLOADER_SCREEN, r'this\.imageHeight - (\d+) \+ 2', [96]),
    # Renderer (RenderRBMKAutoloader): the Base and Piston groups, the piston lowered by p x -4 and lifted 4, the item transforms (0, -6, 0) / 1.75 / Y 180, the model texture path.
    'render_parts': (O_RENDER, r'renderPart\("(\w+)"\)', AUTOLOADER_RENDER, r'renderPart\("(\w+)"\)', ['Base', 'Piston']),
    'render_base_offset': (O_RENDER, r'glTranslated\(x \+ ([\d.]+)D, y, z \+ [\d.]+D\)', AUTOLOADER_RENDER, r'translate\(([\d.]+)F, 0F, [\d.]+F\)', [0.5]),
    'render_piston_travel': (O_RENDER, r'glTranslated\(0, p \* (-?\d+)D, 0\)', AUTOLOADER_RENDER, r'\(float\) \(p \* (-?\d+)D\)', ['-4']),
    'render_piston_lift': (O_RENDER, r'glTranslated\(0, (\d+), 0\)', AUTOLOADER_RENDER, r'translate\(0F, (\d+)F, 0F\)', [4]),
    'render_item_shift': (O_RENDER, r'glTranslated\(0, (-\d+), 0\)', AUTOLOADER_RENDER, r'translate\(0F, (-\d+)F, 0F\)', ['-6']),
    'render_item_scale': (O_RENDER, r'glScaled\(([\d.]+), [\d.]+, [\d.]+\)', AUTOLOADER_RENDER, r'scale\(([\d.]+)F, [\d.]+F, [\d.]+F\)', [1.75]),
    'render_item_rotation': (O_RENDER, r'glRotated\((\d+), 0, 1, 0\)', AUTOLOADER_RENDER, r'rotationDegrees\((\d+)F\)', [180]),
    'render_texture': (O_RESOURCE_MANAGER, r'rbmk_autoloader_tex = new ResourceLocation\(RefStrings\.MODID, "(textures/models/machines/rbmk_autoloader\.png)"\)', RESOURCE_MANAGER,
                       r'RBMK_AUTOLOADER_TEX = NuclearTechMod\.withDefaultNamespace\("(textures/models/machines/rbmk_autoloader\.png)"\)', ['textures/models/machines/rbmk_autoloader.png']),
}
# NEO-only facts (no original counterpart, or a deliberate NEO form): id -> (NEO path, regex, expected unique values). Recorded in the receipt; a regex that finds nothing is pending.
NEO_FACTS = {
    'find_core_null_guard': (AUTOLOADER_BE, r'BlockPos core = base\.findCore\(this\.level, below\);\s*if\((core != null)', ['core != null']),
    'rod_below': (AUTOLOADER_BE, r'this\.worldPosition\.(below)\(\)', ['below']),
    'set_changed_after_swap': (AUTOLOADER_BE, r'(rod\.setChanged)\(\);\s*[^\n]*?this\.setChanged\(\);', ['rod.setChanged']),
    'ticker_core_only': (AUTOLOADER_BLOCK, r'if\(state\.getValue\(TYPE\) != DummyBlockType\.(CORE)\) return null;', ['CORE']),
    'core_block_entity': (AUTOLOADER_BLOCK, r'== DummyBlockType\.(CORE)\s*\? new RBMKAutoloaderBlockEntity', ['CORE']),
    'proxy_inventory': (AUTOLOADER_BLOCK, r'new ProxyComboBlockEntity\(pos, state\)\.(inventory\(\))', ['inventory()']),
    'open_behavior': (AUTOLOADER_BLOCK, r'this\.(standardOpenBehavior)\(level, pos, player\)', ['standardOpenBehavior']),
    'dummyable_base': (AUTOLOADER_BLOCK, r'public class RBMKAutoloaderBlock extends (DummyableBlock)', ['DummyableBlock']),
    'screen_left_button_only': (AUTOLOADER_SCREEN, r'if\(button != (GLFW\.GLFW_MOUSE_BUTTON_LEFT)\) return super\.mouseClicked', ['GLFW.GLFW_MOUSE_BUTTON_LEFT']),
    'screen_control_payload': (AUTOLOADER_SCREEN, r'new (CompoundTagControl)\(data, be\.getBlockPos\(\)\)', ['CompoundTagControl']),
    'block_registered': (BLOCKS, r'RBMK_AUTOLOADER = register\("(rbmk_autoloader)"', ['rbmk_autoloader']),
    'block_entity_type_registered': (BLOCK_ENTITY_TYPES, r'RBMK_AUTOLOADER = BLOCK_ENTITY_TYPES\.register\("(rbmk_autoloader)"', ['rbmk_autoloader']),
    'menu_type_registered': (MENU_TYPES, r'RBMK_AUTOLOADER = reg\("(rbmk_autoloader)"', ['rbmk_autoloader']),
    'screen_registered': (CLIENT, r'event\.register\(NtmMenuTypes\.(RBMK_AUTOLOADER)\.get\(\), RBMKAutoloaderScreen::new\)', ['RBMK_AUTOLOADER']),
    'renderer_registered': (CLIENT_PROXY, r'BlockEntityRenderers\.register\(NtmBlockEntityTypes\.(RBMK_AUTOLOADER)\.get\(\), new RenderRBMKAutoloader\(\)\)', ['RBMK_AUTOLOADER']),
    'creative_tab': (CREATIVE_TABS, r'output\.accept\(NtmBlocks\.(RBMK_AUTOLOADER)\)', ['RBMK_AUTOLOADER']),
    'loot_drop_self': (LOOT_PROVIDER, r'dropSelf\(NtmBlocks\.(RBMK_AUTOLOADER)\.get\(\)\)', ['RBMK_AUTOLOADER']),
    'pickaxe_tag': (TAG_PROVIDER, r'(NtmBlocks\.RBMK_AUTOLOADER)\.get\(\),', ['NtmBlocks.RBMK_AUTOLOADER']),
    'blockstate_particle_only': (BLOCK_STATE_PROVIDER, r'particleOnlyBlock\(NtmBlocks\.(RBMK_AUTOLOADER), modLoc\("block/rbmk/rbmk_autoloader"\)\)', ['RBMK_AUTOLOADER']),
    'obj_registered': (RESOURCE_MANAGER, r'rbmk_autoloader = new HFRWavefrontObject\("(models/obj/rbmk/autoloader\.obj)"\)', ['models/obj/rbmk/autoloader.obj']),
}
# Known source differences the batch deliberately leaves (recorded; not asserted equal, but each is backed by a NEO constant or fact above where it can be).
KNOWN_DIFFERENCES = {
    'speed_final': 'the original SPEED is a mutable public static non-final field nothing writes (TileEntityRBMKAutoloader.java:37); NEO declares it final',
    'find_core_null_guard': 'the original dereferences findCore without a null check (:71-73, :98-100); NEO guards it (NEO-defensive)',
    'set_changed': 'NEO calls setChanged on the rod and the loader after a swap and whenever piston, ret or delay changed in a tick (1.7.10 saved every chunk tile entity); the original has no such calls',
    'screen_buttons_left_click_only': 'the original buttons react to any mouse button (GUIRBMKAutoloader.java:36-53), NEO to the left button only (the RBMKControlScreen precedent)',
    'render_distance': 'the original getMaxRenderDistanceSquared returns 65536 (:249-253); NEO uses the base renderer view distance (256 blocks)',
    'obj_path': 'the original loads models/rbmk/autoloader.obj, NEO models/obj/rbmk/autoloader.obj (layout rule; the file is byte-identical to the original worktree)',
    'alpha_mod': 'the original writes alphaMod, which its particle reads as alpha and therefore ignores; NEO keeps the key and the same effect (upstream-shared)',
    'channel_removed': 'if the fuel channel is gone while the piston is extended the original does nothing and the piston stays extended (:93-128); NEO keeps this (upstream-shared)',
    'copy_tool': 'ICopiable getSettings / pasteSettings are ported (cycle 5..95) but NEO has no copy tool yet: only the GameTest drives them',
    'recipe_expensive_branch': 'the original inputItemsEx (ferro plating, 3 Desh motors) and setPools528 are not migrated (NEO has no item_expensive)',
    'ui_sounds': 'the lift sounds door.wgh_start / door.wgh_stop were imported by an earlier batch and are reused (NtmSoundEvents.WGH_START / WGH_STOP)',
}
# The assembly-machine row: the original row (AssemblyMachineRecipes.java:532-535) -> the NEO row. Each input: (original expression, NEO form, count).
ASSEMBLY_ID = 'ass.rbmkautoloader'
EXPECTED_ASSEMBLY_INPUTS = [('STEEL.plateWelded()', 'weldedplate:STEEL', 4), ('PB.plateCast()', 'castplate:LEAD', 4), ('B.ingot()', 'INGOT_BORON', 4), ('ModItems.motor', 'MOTOR', 3)]
EXPECTED_ASSEMBLY = dict(duration=100, power=100, output='rbmk_autoloader', output_count=1)
O_ASSEMBLY_INPUT = re.compile(r'new (?:OreDictStack|ComparableStack)\(([A-Za-z0-9_.]+(?:\(\))?), (\d+)\)')
N_ASSEMBLY_INPUT = re.compile(r'NtmItems\.(castPlateWeldedIngredient|castPlateIngredient)\(CastPlateItem\.Type\.(\w+), (\d+)\)|new ComparableStack\(NtmItems\.(\w+)\.get\(\), (\d+)\)')


def scope_text(key_count, assets, tests, total_tests):
    return (f'Goal25C (the third batch of Goal 25: RBMK operation and fuel logistics): the RBMK autoloader rbmk_autoloader, a 1x9 machine standing on a fuel channel (RBMKAutoloaderBlock, a '
            f'DummyableBlock whose eight upper blocks are inventory proxies of the core; RBMKAutoloaderBlockEntity with 18 slots, 9 inputs and 9 outputs). Every 20 ticks a retracted loader '
            f'checks the channel below and, when the channel is empty or its rod is enriched below the threshold (default 50 %, set in the GUI from 5 to 95 % in steps of 5) and the rod hull is '
            f'not hotter than 1,000, lowers its piston (200-tick strokes at 0.005 per tick, 40-tick pauses at both ends), swaps the spent rod for a fresh rod whose enrichment reaches the '
            f'threshold in the same tick the piston arrives, and retracts; RBMKAutoloaderMenu, RBMKAutoloaderScreen, the OBJ block entity renderer with its item form, the lift sounds and '
            f'the tower steam; the assembly-machine recipe ass.rbmkautoloader (setup 100 ticks / 100 HE: welded steel plate x4, cast lead plate x4, boron ingot x4, motor x3; the original\'s '
            f'expensive ferro-plating branch and the 528 pools are not migrated); {key_count} English keys and {key_count} Chinese entries (the block and container names, upstream); {assets} '
            f'imported resources (the autoloader OBJ, its model texture, the block icon and the GUI); {tests} RBMKAutoloaderGameTests ({total_tests} GameTests in total, one batch per test) and '
            f'the 25C real-game acceptance checklist GOAL25C-ACCEPTANCE.md (written, not executed). Gameplay impact: RBMK refuelling can be automated for the first time; the spent rods land '
            f'in the loader\'s output slots, where they stay radioactive and possibly hot, and a rod whose hull is above 1,000 is not swapped.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal25c release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 101 scope copies) when it reproduces the baseline hash. A file the freeze did not copy has no reproducible start
    bytes when it was uncommitted-modified at the freeze (the Goal25A and Goal25B deliveries); the blob at the start commit is tried (with CRLF where the working tree had it) for
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
    """The Goal25C start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does not list it)
    the hash the goal25b receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal25b packager protected (built there from the Goal21A..Goal25A starts and receipts and the goal25b start), plus every path the goal25b receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 25C baseline lists the goal25a receipt among them) and every release file of the frozen start
    (the goal25b package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes) are
    pinned at their Goal25C start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal25b packager set at its Goal25B start hash, for the records that changed between the two starts."""
    goal25b_start = read(GOAL25B_BASELINE)
    out = dict(goal25b_protected_paths(goal25b_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal25b receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal25b_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift.
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal25B and Goal25C starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal25b_start):
    """{path: {receipts, start_sha256, goal25b_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal25b receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal25b receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22, 23 and 24 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal25b '
                           'receipt does not hash it. Frozen at the Goal25C start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal25b) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal25b package; the goal25b receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal25b '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal25b_start_sha256=goal25b_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal25b_start_pin_sha256'] = repinned[p]
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


def original_assembly_row(text):
    """The original row `new GenericRecipe("ass.rbmkautoloader")...;` parsed: {duration, power, output, output_count, inputs [(expression, count)], expensive (inputItemsEx present),
    pools528}, or None when the row is missing or not unique."""
    rows = re.findall(r'new GenericRecipe\("'+re.escape(ASSEMBLY_ID)+r'"\)(.*?);\s*\n', text, re.S)
    if len(rows) != 1: return None
    row = rows[0]
    setup, output = re.search(r'\.setup\((\d+), (\d+)\)', row), re.search(r'\.outputItems\(new ItemStack\(ModBlocks\.(\w+), (\d+)\)\)', row)
    inputs = re.search(r'\.inputItems\((.*?)\)\s*\.inputItemsEx', row, re.S) or re.search(r'\.inputItems\((.*)\)$', row.strip(), re.S)
    if not (setup and output and inputs): return None
    return dict(duration=int(setup.group(1)), power=int(setup.group(2)), output=output.group(1), output_count=int(output.group(2)),
                inputs=[(m.group(1), int(m.group(2))) for m in O_ASSEMBLY_INPUT.finditer(inputs.group(1))], expensive='inputItemsEx' in row, pools528='setPools528' in row)


def neo_assembly_row(text):
    """The NEO row parsed the same way (inputs as the NEO forms of EXPECTED_ASSEMBLY_INPUTS), or None when the row is missing or not unique. named = setupNamed used."""
    rows = re.findall(r'new GenericRecipe\("'+re.escape(ASSEMBLY_ID)+r'"\)(.*?)\)\);', text, re.S)
    if len(rows) != 1 or text.count('"'+ASSEMBLY_ID+'"') != 1: return None
    row = rows[0]
    setup, output = re.search(r'\.setup\((\d+), (\d+)\)', row), re.search(r'\.outputItems\(new ItemStack\(NtmBlocks\.(\w+)\.get\(\), (\d+)\)\)', row)
    if not (setup and output): return None
    inputs = []
    for m in N_ASSEMBLY_INPUT.finditer(row):
        if m.group(1): inputs.append((('weldedplate:' if m.group(1) == 'castPlateWeldedIngredient' else 'castplate:')+m.group(2), int(m.group(3))))
        else: inputs.append((m.group(4), int(m.group(5))))
    return dict(duration=int(setup.group(1)), power=int(setup.group(2)), output=output.group(1).lower(), output_count=int(output.group(2)), inputs=inputs,
                named='setupNamed' in row, expensive='inputItemsEx' in row, pools528='setPools528' in row)


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
    older_receipt = read(OLDER_PREVIOUS_RECEIPT)
    goal25b_start = read(GOAL25B_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal25C commits nothing), the recorded start on top of the Goal 24 close-out commit
    # with the uncommitted Goal25A and Goal25B deliveries.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 25 planning commit'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 25 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    status_lines = base['target_status'].splitlines()
    assert len(status_lines) == START_STATUS_LINES, f'The frozen start status has {len(status_lines)} lines, not the {START_STATUS_LINES} of the uncommitted Goal25A and Goal25B deliveries'
    assert START_STATUS.read_text(encoding='utf-8').splitlines() == status_lines, 'start_status.txt differs from the baseline target status'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal25b receipt records another original commit than the frozen start'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal25C: '+head
    closeout = git_ro(ROOT, 'rev-parse', 'HEAD~1').strip()
    assert closeout.startswith(GOAL24_CLOSEOUT), 'NEO HEAD~1 is not the Goal 24 close-out commit 17c8062f'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and base['start_content']['uncommitted'].startswith('the Goal25A and Goal25B deliveries'), 'Baseline start content differs'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d',
                                                          'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b', 'goal24c', 'goal24d', 'goal24e', 'goal25a'}, 'Baseline older receipts differ'
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
        'The start generation stamp was not current or does not hold the goal25b generated tree'
    # The 98 uncommitted start paths are the goal25a and goal25b deliveries: start_hashes.txt (written before the first 25C write; one entry per file, the status line of the untracked
    # directory src/main/java/com/hbm/inventory/recipes/crafting/ is collapsed to one line in start_status.txt) lists the same paths as the two receipts' changed_files, and every
    # hash in it is the baseline hash.
    start_dirty = {}
    for line in START_HASHES.read_text(encoding='utf-8').splitlines():
        h, p = line.split(' ', 1)
        start_dirty[p.lstrip('*').strip()] = h
    delivered = {e['path']: e for e in older_receipt['changed_files']}
    delivered.update({e['path']: e for e in prior_receipt['changed_files']})
    assert set(start_dirty) == set(delivered), 'The frozen start paths are not the goal25a + goal25b deliveries (changed_files): '+str(sorted(set(start_dirty) ^ set(delivered))[:6])
    assert all(base['files'].get(p) == h for p, h in start_dirty.items()), 'start_hashes.txt differs from the baseline file hashes'
    delivery_differs = sorted(p for p, e in delivered.items() if base['files'].get(p) != e['after_sha256'])
    start_jar_sha = base['build_libs_jar_sha256_at_start']

    # 2. Previous deliveries: the goal25b package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the start is not the goal25b package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal25b receipt list + the goal25b package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal25b receipt count + the goal25b release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal25b receipt'
    assert base['previous_receipt_evidence_drift'] == {}, 'The goal25b receipt drifted at the start: '+str(list(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal25b_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal25b receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal25c. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, f'Path changed since the Goal25C start that the owner table does not list (production outside the {len(MODIFIED_JAVA)} modified Java files, the {len(NEW_JAVA)} new classes incl. '
         'RBMKAutoloaderGameTests, the 4 resources, zh_cn.json and the mapping, a protected or frozen record, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal25A / Goal25B / Goal24 records or the 25D planning documents changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal25C start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD, ANVIL_RECIPES] + GENERATED + SHARED_RECORDS + REPORTS[:1]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    need(sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES], f'{ANVIL_RECIPES} changed since the start (the autoloader has no anvil row)')
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION + OPTIONAL_JAVA if p.startswith('src/')})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified and {len(NEW_JAVA)} new Java files, the 4 resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    goal25_now = sha(ROOT/GOAL25_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository. The batch ran under the main agent with a builder, a '
                                               'verifier (RBMKAutoloaderGameTests, verify_goal25c_rbmk_autoloader.py, Gradle), this packaging verifier and a read-only reviewer; each wrote only its '
                                               'named files (scope-before / scope-after snapshots of the verifiers are indexed as evidence). migration/GOAL25.md and GOAL25C.md are edited by the '
                                               'main agent of this batch.',
                             goal25_md=dict(start_sha256=base['files'][GOAL25_RECORD], current_sha256=goal25_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p)) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, owners=[OWNER], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal25C takes no new snapshot)'
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
    # The state machine order in both texts: retract, the 20-tick check opening the stroke, extend, then (piston extended) take the old rod out, put a new rod in, retract again. The
    # swap sits in the same updateEntity pass as the arrival (main-notes.md decision 11, TileEntityRBMKAutoloader.java:84-90 then :93-125).
    order_tokens = {'original': ['this.piston -= this.speed;', 'this.isRetracting = false;', 'this.piston += this.speed;', 'if(!isRetracting && this.piston >= 1D)', 'rod.slots[0].copy()',
                                 'stack.copy()', 'this.isRetracting = true;'],
                    'neo': ['this.piston -= SPEED;', 'this.isRetracting = false;', 'this.piston += SPEED;', 'if(!isRetracting && this.piston >= 1D)', 'rod.slots.get(0).copy()',
                            'stack.copy()', 'this.isRetracting = true;']}
    state_machine_order = dict(original=ordered(original_text(O_TE), order_tokens['original']), neo=ordered(neo_text(AUTOLOADER_BE), order_tokens['neo']))
    assert state_machine_order['original'], 'The original updateEntity no longer has the retract / start / extend / swap / retract order'
    need(state_machine_order['neo'], f'{AUTOLOADER_BE} updateEntity does not keep the original order: retract, start check, extend, take out, insert, retract')
    # Logical sides: the block entity, block and menu (common code) import nothing from net.minecraft.client; the screen and the renderer exist.
    common = (AUTOLOADER_BE, AUTOLOADER_BLOCK, AUTOLOADER_MENU)
    client_imports = {p: (ROOT/p).is_file() and 'net.minecraft.client' in neo_text(p) for p in common}
    need(not any(client_imports.values()) and all((ROOT/p).is_file() for p in common + (AUTOLOADER_SCREEN, AUTOLOADER_RENDER)),
         'common-side autoloader classes are missing or import net.minecraft.client: '+str(sorted(p for p, v in client_imports.items() if v)))
    need('extends MachineBaseBlockEntity' in neo_text(AUTOLOADER_BE) and 'IControlReceiver' in neo_text(AUTOLOADER_BE) and 'ICopiable' in neo_text(AUTOLOADER_BE)
         and 'IRBMKLoadable' not in neo_text(AUTOLOADER_BE),
         f'{AUTOLOADER_BE} is not a MachineBaseBlockEntity implementing IControlReceiver and ICopiable (and, as the original, not IRBMKLoadable)')
    # The assembly-machine row: the original row parsed against the NEO row; no setupNamed (the original row has no customLocalization), the expensive branch and the 528 pools not migrated.
    o_row = original_assembly_row(original_text(O_ASSEMBLY))
    assert o_row is not None and o_row['expensive'] and o_row['pools528'], 'The original ass.rbmkautoloader row could not be parsed'
    assert (o_row['duration'], o_row['power'], o_row['output'], o_row['output_count']) == (EXPECTED_ASSEMBLY['duration'], EXPECTED_ASSEMBLY['power'], EXPECTED_ASSEMBLY['output'],
                                                                                           EXPECTED_ASSEMBLY['output_count']), f'The original row differs from the owner table: {o_row}'
    assert o_row['inputs'] == [(e[0], e[2]) for e in EXPECTED_ASSEMBLY_INPUTS], f'The original row inputs differ from the owner table: {o_row["inputs"]}'
    n_row = neo_assembly_row(neo_text(ASSEMBLY_RECIPES))
    assembly = dict(original=dict(o_row), neo=n_row, expected_neo_inputs=[[e[1], e[2]] for e in EXPECTED_ASSEMBLY_INPUTS], original_reference=original_refs['recipe_row'])
    if need(n_row is not None, f'{ASSEMBLY_RECIPES} has no unique ass.rbmkautoloader row'):
        need((n_row['duration'], n_row['power'], n_row['output'], n_row['output_count']) == (EXPECTED_ASSEMBLY['duration'], EXPECTED_ASSEMBLY['power'], EXPECTED_ASSEMBLY['output'],
                                                                                              EXPECTED_ASSEMBLY['output_count']), f'{ASSEMBLY_RECIPES} ass.rbmkautoloader differs from the original setup / output: {n_row}')
        need(n_row['inputs'] == [(e[1], e[2]) for e in EXPECTED_ASSEMBLY_INPUTS], f'{ASSEMBLY_RECIPES} ass.rbmkautoloader inputs differ from the original row: {n_row["inputs"]}')
        need(not n_row['named'] and not n_row['expensive'] and not n_row['pools528'], f'{ASSEMBLY_RECIPES} ass.rbmkautoloader uses setupNamed or an unmigrated branch: {n_row}')
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
        'The start mapping does not hold the groups of 24B-25B (rbmk-fuel, rbmk-reactor, rbmk-control, rbmk-steam, rbmk-console, rbmk-storage, rbmk-recycling, rbmk-outgasser) and not yet the Goal25C group'
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
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal25b totals'
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal25b totals {totals} + {len(KEYS)}')
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal25b generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected blockstate, particle model, item model and loot table files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, the pickaxe tag and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # The pickaxe tag: the start list plus rbmk_autoloader, in the start order.
    tag_start_bytes = start_bytes(base, GENERATED_ROOT+TAG_ENTRY)
    assert tag_start_bytes is not None, 'No reproducible start bytes for the pickaxe tag'
    tag_start, tag_now = json.loads(tag_start_bytes.decode('utf-8-sig'))['values'], read(ROOT/(GENERATED_ROOT+TAG_ENTRY))['values']
    tag_inserted = insertions(tag_start, tag_now)
    need(tag_inserted is not None and [v for _, v in tag_inserted] == ['hbmsntm:rbmk_autoloader'],
         f'the pickaxe tag is not the start list plus hbmsntm:rbmk_autoloader: inserted {None if tag_inserted is None else [v for _, v in tag_inserted]}')
    # The generated block files: a particle-only blockstate (the machine is drawn by its renderer), the particle model on the imported icon, the builtin/entity item model, a drop-self loot table.
    generated_facts = {}
    for p, wanted in (('assets/hbmsntm/blockstates/rbmk_autoloader.json', {'variants': {'': {'model': 'hbmsntm:block/rbmk_autoloader_particle'}}}),
                      ('assets/hbmsntm/models/block/rbmk_autoloader_particle.json', {'textures': {'particle': 'hbmsntm:block/rbmk/rbmk_autoloader'}}),
                      ('assets/hbmsntm/models/item/rbmk_autoloader.json', {'parent': 'minecraft:builtin/entity', 'gui_light': 'side'})):
        live = read(ROOT/(GENERATED_ROOT+p)) if (ROOT/(GENERATED_ROOT+p)).is_file() else None
        generated_facts[p] = live
        need(live == wanted, f'generated {p} is not the expected particle-only form: {live}')
    loot_path = GENERATED_ROOT+'data/hbmsntm/loot_table/blocks/rbmk_autoloader.json'
    loot = read(ROOT/loot_path) if (ROOT/loot_path).is_file() else None
    generated_facts['data/hbmsntm/loot_table/blocks/rbmk_autoloader.json'] = loot
    need(loot is not None and loot.get('type') == 'minecraft:block' and [e.get('name') for pool in loot.get('pools', []) for e in pool.get('entries', [])] == ['hbmsntm:rbmk_autoloader'],
         f'generated {loot_path} does not drop hbmsntm:rbmk_autoloader: {loot}')
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
    autoloader_test_names = sorted(GAMETEST_METHOD.findall((ROOT/AUTOLOADER_TESTS).read_text(encoding='utf-8'))) if (ROOT/AUTOLOADER_TESTS).is_file() else []
    autoloader_annotations = annotations(ROOT/AUTOLOADER_TESTS) if (ROOT/AUTOLOADER_TESTS).is_file() else 0
    need(bool(autoloader_test_names) and autoloader_annotations == len(autoloader_test_names), f'{AUTOLOADER_TESTS} holds {autoloader_annotations} @GameTest annotations and {len(autoloader_test_names)} parsed methods')
    need(gametest_added == autoloader_annotations, f'GameTest sources grew by {gametest_added} tests, RBMKAutoloaderGameTests holds {autoloader_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in autoloader_test_names), 'GameTest log lacks "[hbm-rbmk-autoloader] <name> passed" for: '+str([n for n in autoloader_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal25c/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal25c/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal25c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal25c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal25c/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA + OPTIONAL_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal25c/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal25b final run plus the Goal25C verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal25b final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal25C suite is already in the goal25b final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal25c/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal25b final set + the Goal25C verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal25c/'+VERIFY_REPORT+' (tools/migration/verify_goal25c_rbmk_autoloader.py report)'):
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
        verifier_references = sorted(set(re.findall(r'(?:TileEntityRBMKAutoloader|RBMKAutoloader|ContainerRBMKAutoloader|GUIRBMKAutoloader|RenderRBMKAutoloader|AssemblyMachineRecipes|'
                                                      r'TileEntityRBMKRod|TileEntityMachineBase|ModBlocks|ResourceManager)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        # The verifier ran against the final GameTest log and expected the sources' total.
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal25b compare target paths (which hold the 24A-25B paths) plus this batch's compare-inventory paths).
    cmp25b = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal25b/compare.json differs from the goal25b receipt'
    c25b_added = sorted(p for p in compare_paths(cmp25b['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c25b_modified = sorted(p for p in compare_paths(cmp25b['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(c25b_added) | set(c25b_modified) | set(own_target))
    expected_added = sorted(set(c25b_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal25c/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-25b paths + %d of this batch)' % (
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
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal25b (goal25b compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal25b_paths=len(c25b_added) + len(c25b_modified), goal25c_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the groups of 24B-25B.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-25B)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal25c.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal25b) package (run the final build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 4 resources and every compiled class equal the sources.
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
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 4 imported resources, the generated additions and '
             'the modified en_us.json / zh_cn.json / pickaxe tag / MANIFEST.MF are owned): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA),
             'Changed Java sources and goal25c JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, TAG_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + pickaxe tag + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        inner = 'com/hbm/render/blockentity/RenderRBMKAutoloader$1.class'
        need(inner in jar_delta['added'], inner+' (the item renderer) is not an added JAR class')
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal25b_start=sorted(repinned),
                   delivery_hash_differs_from_receipts=delivery_differs,
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, removed_comment_lines={p: len(v) for p, v in removed_comments.items()},
                   constants={k: c['neo'] == c.get('neo_expected', c['original']) for k, c in constants.items()}, neo_facts={k: f['neo'] == f['expected'] for k, f in neo_facts.items()},
                   state_machine_order=state_machine_order, assembly_row_equal=bool(n_row) and n_row['inputs'] == [(e[1], e[2]) for e in EXPECTED_ASSEMBLY_INPUTS],
                   client_imports_in_common_classes=sorted(p for p, v in client_imports.items() if v),
                   gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_autoloader_tests=autoloader_test_names, final_suites_expected=final_expected,
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
    rbmk_autoloader = dict(neo=[AUTOLOADER_BLOCK, AUTOLOADER_BE, AUTOLOADER_MENU, AUTOLOADER_SCREEN, AUTOLOADER_RENDER, ASSEMBLY_RECIPES, RESOURCE_MANAGER],
                           original=[p for p in O_SOURCES], constants=constants, neo_only_facts=neo_facts, known_differences=KNOWN_DIFFERENCES, assembly_row=assembly,
                           state_machine_order=state_machine_order, generated_files=generated_facts, original_references=original_refs,
                           defaults=dict(slots=18, input_slots='0-8', output_slots='9-17', speed=0.005, ticks_per_stroke=200, pause_ticks=40, check_interval_ticks=20, cycle_default=50,
                                         cycle_step=5, cycle_range='5..95', swap_out='enrichment x 100 < cycle (or an empty channel)', load='enrichment x 100 >= cycle', hull_limit=1000,
                                         piston_extended_swap='in the same tick the piston reaches 1, then 40 ticks hold, then retract', faces_visible='piston <= 0 only',
                                         nbt_keys='piston, ret, delay, cycle', sync='piston (double) + cycle (int), turnProgress 2', use_range=12, dimensions='1x9 {8,0,0,0,0,0}',
                                         offset=0, hardness=50, resistance=60, gui_size='176 x 182', render_box='y..y+9', assembly='setup(100, 100)'),
                           note='The autoloader is a 1x9 DummyableBlock (RBMKAutoloader.java:18-36) whose core block entity has 18 slots, inputs 0-8 and outputs 9-17 (TileEntityRBMKAutoloader.java:43-45). '
                                'Every 20 ticks a retracted loader with a qualifying input and a free output slot looks at the block below: a fuel channel whose hull is not hotter than 1,000 '
                                '(TileEntityRBMKRod.coldEnoughForAutoloader) and that is empty or holds a rod enriched below the cycle threshold makes it extend (:68-82). The piston moves '
                                '0.005 per tick (200 ticks per stroke, :84-90); in the same pass in which it reaches 1 the old rod goes to the first free output slot and the first input rod '
                                'enriched at least the threshold goes into the channel (:93-125), then it holds 40 ticks and retracts and holds 40 ticks again (:59-65). If the channel '
                                'disappears while extended nothing happens (upstream-shared). The threshold steps by 5 between 5 and 95 (:260-266), is saved with piston, ret and delay '
                                '(:222-238) and synced with the piston (:191-205). Automation reaches the slots only while the piston is up, inserts only qualifying rods into 0-8 and takes '
                                'only from 9-17 (:207-220). The GUI is 176 x 182 with the two 12 x 12 buttons and the green percentage (GUIRBMKAutoloader.java). The renderer draws Base and '
                                'Piston (the piston lowered by p x 4, lifted 4) and an item form; the client plays the lift loop and the tower steam. Not migrated: the original\'s expensive '
                                'ferro-plating recipe branch and the 528 pools. NEO adds a null guard on findCore and setChanged calls; the copy tool does not exist yet.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), len(ASSETS), len(autoloader_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=start_head[:8],
                   uncommitted_start=dict(status_entries=len(status_lines), description=base['start_content']['uncommitted'], base_release=previous_rel, status=status_lines,
                                          start_hashes_file='build/migration/goal25c/start_hashes.txt', start_paths=len(start_dirty),
                                          delivery_paths_match_receipts_changed_files=True, paths_whose_start_hash_differs_from_receipt_after_sha256=delivery_differs,
                                          note='The start hashes are the reconstructed working tree at the start (the Goal25A and Goal25B deliveries are uncommitted), not the commit 783b6d13. '
                                               'start_status.txt shows the untracked directory src/main/java/com/hbm/inventory/recipes/crafting/ as one line; start_hashes.txt lists its file.'),
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, build_libs_sha256_at_freeze=base['build_libs_jar_sha256_at_freeze'],
                                      reconstruction=base['reconstruction'], goal24_closeout_commit=closeout,
                                      note='The start tree is HEAD 783b6d13 (the Goal 25 planning commit, local, not pushed) on top of the pushed Goal 24 close-out commit 17c8062f, PLUS the uncommitted '
                                           'Goal25A and Goal25B deliveries (98 status lines, packaged as goal25b). build/libs at the start IS the goal25b package d37fc1a0...; at the freeze it was '
                                           'already a builder build (not evidence). The original did not move since 24A (aee05a40f). The freeze ran after the first 25C writes and reconstructs '
                                           'the start from files captured before them (freeze_start.py); it copied 101 scope files to baseline-files; paths this batch changes record the start '
                                           'hash as before_sha256, and a modified file the freeze did not copy has no reproducible start bytes.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, removed_comment_lines=removed_comments, start_copies_supplement=[],
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   rbmk_autoloader=rbmk_autoloader,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note=f'Both entries ({EXPECTED_KINDS.get("upstream", 0)}) are upstream with the original English and Chinese verbatim: the block name (tile.rbmk_autoloader.name, '
                                      'en_US.lang:6212, zh_CN.lang:5920) and the container name (container.rbmkAutoloader, en_US.lang:788, zh_CN.lang:5911). No existing key changes its English value; '
                                      'no deferred entry is added.'),
                   recipes=dict(assembly=assembly, crafting={}, not_registered=['the original inputItemsEx branch (ferro plating, 3 Desh motors) and setPools528: NEO has no item_expensive'],
                                original_references={k: v for k, v in original_refs.items() if k.startswith('recipe_')},
                                anvil_recipes_unchanged=sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES],
                                note='The recipe is the assembly-machine row ass.rbmkautoloader (AssemblyMachineRecipes.java:532-535): setup(100, 100), welded steel plate x4, cast lead plate x4, boron '
                                     'ingot x4, motor x3 -> 1 rbmk_autoloader; NEO has no generated crafting recipe for it. AnvilRecipes stays unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith('repinned_since_')},
                   repinned_since_goal25b_start={p: dict(goal25b_start_pin_sha256=h, goal25c_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_autoloader_tests=autoloader_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per RBMKAutoloaderGameTests test: the 1x9 placement '
                                      'and proxies, the swap cycle with its tick timings, the cases that must not swap, the slot and face rules and the menu, the control payload, range and copy '
                                      'settings, the NBT, sync and mid-stroke reload, and the assembly recipe, hardness and resistance; no client (the screen, the renderer, the item icon, the '
                                      'lift sounds and the steam are not rendered or heard), no real player, no saved world, no survival chain.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['rbmk_outgasser (the Goal25B-only key; Goal25C adds rbmk_autoloader; the 25B-only constants, rows and neutron-branch facts are not carried)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. No in-game client test was run: '
                            'the autoloader screen, the renderer and item icon, the lift sounds, the steam particles and the Chinese UI are unverified; no survival chain (assembly machine to '
                            'loader to a refuelled channel) in a world was run; no multiplayer or dedicated server beyond GameTest; GOAL25C-ACCEPTANCE.md (the 25C real-game checklist) is written '
                            'but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal25c JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal25b package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
