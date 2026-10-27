"""Package Goal27D (the last batch of Goal 27: the casting base shared by foundry_mold and the new foundry_basin, the 17-mold definition table and the 14 new mold items, casts resolved
through the 27A material registry, the generic mold smithing recipe, the JEI casting rows for every (mold, material) pair, the Goal 27 unified acceptance checklist and the
FoundryMoldGameTests), cumulatively on the goal27c package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal27d.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal27d/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal27d/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal27d/baseline.json: NEO HEAD 690ce8c0 (the 2026-10-26 commit and push of Goal 27 batches 27A and 27B, = origin/master; parent 71c2f660 = the
Goal 27 planning commit) plus the UNCOMMITTED Goal27C delivery, 101 status lines: the 100 changed files of the goal27c receipt (each equal to its receipt after-hash at the freeze) and
the Goal 27 planning session's post-push edit of GOAL27-THREAD-PROMPTS.md. Unlike the goal27c start, whose 27A and 27B deliveries were committed, the Goal27C delivery is working-tree
state: the packager checks that the goal27c receipt's changed files are exactly the dirty start files (plus the planning edit) at their receipt hashes. freeze_start.py hashed every
tracked and dirty file live (10,830 hashes) before the first 27D write and copied the 101 dirty files and the planned files into baseline-files/ (130 copies); start_status.txt (101 lines),
start_head.txt and start_hashes.txt record it. The start bytes of a file are the live bytes at the freeze = baseline-files. build/libs at the start is the goal27c package
(baseline build_libs_jar_sha256_at_freeze = the goal27c JAR hash). The original HEAD aee05a40f did not move since 24A, so there is no upstream classification and no new snapshot. Every
change since the start is computed from the baseline file hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified
production files are compared with their start bytes (baseline-files, or the start-commit blob for a file the freeze did not copy) and their +/- lines are reported. The JAR delta against
the goal27c package is attributed per entry; any entry without exactly one owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, recipes,
molds, casting rows) are computed here from the original and NEO sources and the GameTest log where they can be; the figures the handoff states are asserted against those computations.

GOAL27-THREAD-PROMPTS.md is a planning-session edit after the 27C freeze: it may differ from its baseline hash, it is attributed to the owner "planning-session" (not goal27d), never fails
the packager and is never restored; its start and current hashes are recorded in the receipt. GOAL27D.md is the task book and delivery record of this batch and is hashed by the receipt.
The 27C records (GOAL27C.md, GOAL27C-ACCEPTANCE.md, goal27c-*) are hashed by the goal27c receipt and must equal their hash; a dated line the main agent appends to one of them is accepted
only when it is insert-only against the start bytes and is then reported (appended_27c_records) with before and after hashes.

The receipts that hash records (goal21a..goal27c, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start (the acceptance checklists, GOAL21D.md,
GOAL22C.md, goal21d-static-review.md and the goal24a working notes, known from earlier batches); they are listed in the receipt as start drift and must still equal their Goal27D start hash;
no receipt is rewritten and no other protected path may drift. The goal27c receipt itself drifts nowhere (baseline previous_receipt_evidence_drift is empty). Every GOAL27A* / GOAL27B* /
goal27a-* / goal27b-* record, every Goal 26 and earlier record and SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL27.md is a shared record, GOAL27D.md the task book and
delivery record (hashed by the receipt).

Like the packagers of 24B..27C this one has a single compare run (build/migration/goal27d/compare.json against the snapshot review-aee05a40f10f.json taken at the end of 24A: original 0/0/0,
target = exactly the goal27c compare target paths (read from build/migration/goal27c/compare.json) plus this batch's compare-inventory paths, the stamp dropped), no upstream
classification; it adds the foundry_molds facts (checked against the original and NEO source texts). The Goal27C-only receipt key foundry_casting is dropped and the receipt says so;
the two old casting regressions run unchanged through the goal27a wrapper in the final rerun and their javac errors are attributed by casting_attribution.py (casting-attribution.json)."""
from collections import Counter
from pathlib import Path
import argparse
import difflib
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
from migration import BUILD_FILES, matches as feature_matches
from package_goal21d import (LOCALIZATION_RECORD, STAMP, EN, ZH_ENTRY, EN_ENTRY, lang_delta, compare_paths, lines_of,
                             eol_counts, insertions, in_compare_inventory, changed_since_start)
from package_goal22a import annotations, GAMETEST_ANNOTATION
from package_goal22b import (git_ro, edit_counts, stale_diff, receipt_protected, start_drift_paths, strip_java_comments, original_blob,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE
from package_goal23b import report_problems
from package_goal24a import original_text, original_line, SOURCE_HEAD
from package_goal27a import is_comment, body_of, split_top, lang_file, OLD_MACHINE_SUITES
from package_goal27c import (OUT as GOAL27C_OUT, BASELINE as GOAL27C_BASELINE, protected_paths as goal27c_protected_paths, strip_noise, cut_methods, stray_removals,
                             recipe_item, generated_recipe, recompile_equal, RECOMPILE_ONLY, RECOMPILE_OWNER)

OUT = ROOT/'build/migration/goal27d'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
START_HASHES = OUT/'start_hashes.txt'
REFERENCE_PREVIOUS = GOAL27C_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL27C_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal27c/hbmsntm-198A-goal27c.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal27d'
RELEASE_NAME = 'hbmsntm-198A-goal27d.jar'
OWNER = 'goal27d'
PREVIOUS_OWNER = 'goal27c'
PLANNING_OWNER = 'planning-session'
START_PREFIX = '690ce8c0'
PLANNING_PREFIX = '71c2f660'
GOAL26_CLOSEOUT = '0786697d'
START_STATUS_LINES = 101
THREAD_PROMPTS = 'migration/GOAL27-THREAD-PROMPTS.md'
TASK_BOOK = 'migration/GOAL27D.md'
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
SRC = 'src/main/java/'
J = SRC+'com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
TEXTURE_ROOT = RES+'assets/hbmsntm/textures/'
O_RES = RES+'assets/hbm/'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a', 'goal26b', 'goal26c', 'goal26d', 'goal27a', 'goal27b'}

# Production (owner goal27d): the NEW Java files (the casting base block entity and block, the basin block entity and block, the mold item with its definition table, the generic mold
# smithing recipe, and the GameTest class) and the MODIFIED production sources (the handoff owner table); the optional ones and the edited older GameTests are listed separately.
NEW_JAVA = [J+p+'.java' for p in (
    'blockentity/machine/FoundryCastingBlockEntity', 'blockentity/machine/FoundryBasinBlockEntity', 'blocks/machine/FoundryCastingBlock', 'blocks/machine/FoundryBasinBlock',
    'items/machine/MoldItem', 'inventory/recipes/anvil/AnvilSmithingMoldRecipe', 'gametest/FoundryMoldGameTests')]
(CASTING_BE, BASIN_BE, CASTING_BLOCK, BASIN_BLOCK, MOLD_ITEM, SMITHING_MOLD, MOLD_TESTS) = NEW_JAVA
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blockentity/machine/FoundryMoldBlockEntity', 'blocks/machine/FoundryMoldBlock', 'items/NtmItems', 'blocks/NtmBlocks', 'blockentity/NtmBlockEntityTypes', 'inventory/NtmCreativeTabs',
    'inventory/recipes/anvil/AnvilRecipes', 'inventory/recipes/CopperCastingRecipes', 'handler/jei/CrucibleCastingRecipeHandler', 'handler/jei/NtmJeiPlugin', 'render/blockentity/RenderFoundry',
    'main/ClientProxy', 'datagen/NtmBlockStateProvider', 'datagen/NtmItemModelProvider', 'datagen/NtmRecipeProvider', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider',
    'datagen/NtmLanguageProvider')]
(MOLD_BE, MOLD_BLOCK, NTM_ITEMS, NTM_BLOCKS, NTM_BE_TYPES, CREATIVE_TABS, ANVIL_RECIPES, COPPER_CASTING, JEI_HANDLER, JEI_PLUGIN, RENDERER, CLIENT_PROXY, STATE_PROVIDER, ITEM_MODEL_PROVIDER,
 RECIPE_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER, LANG_PROVIDER) = MODIFIED_JAVA
# Older GameTest classes the batch edits by design (27D changes the rules they pinned): FoundryChannelGameTests.mold_regression's mold-limit block (the three hard-coded 27C molds) and
# CrucibleAlloyGameTests' smithing recipe count (23 -> 37: 14 AnvilSmithingMoldRecipe rows are appended). Only those lines may change; the @GameTest methods and annotations are the start's.
EDITED_GAMETESTS = [J+'gametest/FoundryChannelGameTests.java', J+'gametest/CrucibleAlloyGameTests.java']
(CHANNEL_TESTS, CRUCIBLE_TESTS) = EDITED_GAMETESTS
OPTIONAL_JAVA = [J+p+'.java' for p in ('gametest/SmokeTestSupport',)]
OLDER_GAMETEST_DIR = J+'gametest/'
# Must stay byte-identical to the start (the handoff list), plus every other GameTest class and every other handler/jei class: see main().
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'inventory/material/Mats', 'inventory/material/MaterialEntries', 'inventory/material/MatDistribution', 'inventory/material/MaterialShapes', 'inventory/material/NTMMaterial',
    'inventory/recipes/CrucibleRecipes', 'inventory/recipes/CrucibleRecipe', 'inventory/recipes/loader/SerializableRecipe', 'inventory/recipes/ShredderRecipes',
    'items/CopperScrapsItem', 'items/CastPlateItem', 'items/WireDenseItem',
    'blockentity/machine/FoundryBaseBlockEntity', 'blockentity/machine/FoundryChannelBlockEntity', 'blockentity/machine/FoundryTankBlockEntity', 'blockentity/machine/FoundryOutletBlockEntity',
    'blocks/machine/FoundryChannelBlock', 'blocks/machine/FoundryTankBlock', 'blocks/machine/FoundryOutletBlock', 'util/CrucibleUtil', 'blockentity/machine/MachineCrucibleBlockEntity',
    'inventory/recipes/anvil/AnvilSmithingIngotMoldRecipe', 'inventory/recipes/anvil/AnvilSmithingCastMoldRecipe', 'inventory/recipes/anvil/AnvilSmithingBladeMoldRecipe',
    'inventory/recipes/anvil/AnvilSmithingRecipe', 'uninos/UniNodespace', 'uninos/NodeNet', 'uninos/GenNode', 'uninos/INetworkProvider', 'uninos/networkproviders/FoundryNetwork',
    'uninos/networkproviders/FoundryNetworkProvider', 'uninos/networkproviders/FoundryNode')] + [SRC+'api/hbm/block/ICrucibleAcceptor.java']
BASE_BE = J+'blockentity/machine/FoundryBaseBlockEntity.java'
# Older tools that must equal their start bytes (handoff list); every file of the two frozen casting regression folders is added in main().
OLD_TOOLS_FROZEN = ['tools/migration/'+p for p in ('package_goal27c.py', 'verify_goal27c_foundry.py', 'package_goal27b.py', 'verify_goal27b_crucible_alloys.py', 'package_goal27a.py',
                                                    'verify_goal27a_material_system.py', 'goal27a_casting_regression_run.py', 'goal27a_casting_compat.py', 'goal27a_scrap_textures.py',
                                                    'goal27a_effect_icons.py', 'goal26c_oldsuite_run.py', 'goal26c_oldsuite_compat.py', 'verify_goal10a.py', 'verify_goal10a_resources.py',
                                                    'verify_goal5a_casting.py', 'verify_goal5a_casting_resources.py', 'goal10a_scrap_textures.py', 'goal10a_mutation_check.py')]
FROZEN_TOOL_DIRS = ('tools/migration/goal10a_regression/', 'tools/migration/goal5a_casting_regression/')
NEW_TOOLS = ['tools/migration/verify_goal27d_molds.py', 'tools/migration/package_goal27d.py']
TOOLS = NEW_TOOLS
# Hand-written resources (byte imports from the original; migration/goal27d-resource-ownership.json lists them): the 14 new mold item textures and the 4 foundry_basin block textures.
MOLD_NAMES = ('nugget', 'billet', 'plate', 'wire', 'wire_dense', 'blades', 'stamp', 'shell', 'pipe', 'ingots', 'plates', 'plates_cast', 'wires_dense', 'block')  # the 14 new molds (not ingot, blade, plate_cast)
TEXTURE_PATTERN = re.compile(re.escape(TEXTURE_ROOT)+r'(item/mold_[a-z_]+\.png(?:\.mcmeta)?|block/foundry_basin_[a-z_]+\.png(?:\.mcmeta)?)')
REQUIRED_TEXTURES = [TEXTURE_ROOT+'item/mold_'+n+'.png' for n in MOLD_NAMES] + [TEXTURE_ROOT+'block/foundry_basin_'+n+'.png' for n in ('top', 'side', 'bottom', 'inner')]
RESOURCE_OWNERSHIP = 'migration/goal27d-resource-ownership.json'
# Generated by runData: a blockstate, block model(s), an item model, a recipe with its advancement and a loot table for foundry_basin; 14 mold item models; en_us.json and the pickaxe tag change; the stamp.
BLOCK_NAMES = ('foundry_basin',)
GENERATED_ADDED = re.compile(re.escape(GENERATED_ROOT)+r'(assets/hbmsntm/(?:blockstates|models/block|models/item)/foundry_basin[a-z_]*\.json|assets/hbmsntm/models/item/mold_[a-z_]+\.json|'
                             r'data/hbmsntm/(?:recipe|loot_table/blocks|advancement/recipes/[a-z]+)/foundry_basin\.json)')
PICKAXE_TAG = GENERATED_ROOT+'data/minecraft/tags/block/mineable/pickaxe.json'
REQUIRED_GENERATED = sorted([GENERATED_ROOT+f'{kind}/foundry_basin.json' for kind in ('assets/hbmsntm/blockstates', 'assets/hbmsntm/models/item', 'data/hbmsntm/recipe', 'data/hbmsntm/loot_table/blocks')]
                            + [GENERATED_ROOT+f'assets/hbmsntm/models/item/mold_{n}.json' for n in MOLD_NAMES])  # the block model and the recipe advancement (any category folder) are checked separately
# The foundry_mold blockstate / models may change when the builder re-models the mold (allowed as a modification, reported); no new file for it is expected.
GENERATED_TAGS = re.compile(re.escape(GENERATED_ROOT)+r'data/[a-z_]+/tags/.*\.json')  # the tag files that gained the basin (pickaxe.json is required, others allowed)
GENERATED_MOLD = re.compile(re.escape(GENERATED_ROOT)+r'assets/hbmsntm/(?:blockstates|models/block|models/item)/foundry_mold[a-z_]*\.json')
GENERATED_MODIFIED = [STAMP, EN, PICKAXE_TAG]
# Language: the 29 new keys (the basin, foundry.noCast, the 13 shape titles and the 14 new mold names), casting.no_mold removed, the existing molds' names reworded.
SHAPE_KEYS = ('billet', 'blade', 'blades', 'block', 'ingot', 'ntmpipe', 'nugget', 'plate', 'plateTriple', 'shell', 'stamp', 'wireDense', 'wireFine')
KEYS = sorted(['block.hbmsntm.foundry_basin', 'foundry.noCast'] + ['shape.'+n for n in SHAPE_KEYS] + ['item.hbmsntm.mold_'+n for n in MOLD_NAMES])
REMOVED_KEYS = ['casting.no_mold']
EN_CHANGED = ['item.hbmsntm.mold_blade', 'item.hbmsntm.mold_ingot']
ZH_CHANGED = ['item.hbmsntm.mold_blade', 'item.hbmsntm.mold_ingot', 'item.hbmsntm.mold_plate_cast']
# The upstream entries (kind upstream in the mapping): NEO key -> original key (en_US.lang:1207, :5050-5076, :5601; zh_CN.lang:979, :4321-4346, :4826); the mold names are kind local (item.mold.name + shape.*).
LANG_SOURCE = dict({'block.hbmsntm.foundry_basin': 'tile.foundry_basin.name', 'foundry.noCast': 'foundry.noCast'}, **{'shape.'+n: 'shape.'+n for n in SHAPE_KEYS})
MOLD_NAME_KEY = 'item.mold.name'
UPSTREAM_ADDED = 15
LOCAL_ADDED = 14
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal27d-* or GOAL27D-* record is hashed as well.
REPORTS = ['migration/GOAL27D.md', 'migration/GOAL27D-ACCEPTANCE.md', 'migration/goal27d-static-review.md', 'migration/goal27d-materials-review.json', 'migration/goal27d-localization-review.json',
           RESOURCE_OWNERSHIP]
LEDGER = REPORTS[3]
BATCH_RECORD = re.compile(r'migration/(goal27d-[^/]+\.(json|md)|GOAL27D-[^/]+\.md)')
GOAL27_RECORD = 'migration/GOAL27.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md', GOAL27_RECORD,
                  LOCALIZATION_RECORD]
# Shared records the batch may leave untouched ("possibly" in the handoff).
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
# The records of the other batches and the files no batch of this kind touches: no change is expected.
PLANNING_FROZEN = ['migration/SURVIVAL-PLAYABILITY.md']
# Every Goal 26 and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 26) and every Goal27A / Goal27B record (GOAL27A*, GOAL27B*, goal27a-*, goal27b-*).
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-6])(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-6])(?!\d)[a-z]?-[^/]+|GOAL27[AB](?:-[^/]+)?\.md|goal27[ab]-[^/]+)')
# The Goal27C records (owner goal27c, uncommitted at the start, hashed by the goal27c receipt): a dated line may be appended; anything else is drift.
RECORD_27C = re.compile(r'migration/(goal27c-[^/]+\.(json|md)|GOAL27C(?:-[^/]+)?\.md)')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = (NEW_JAVA + MODIFIED_JAVA + EDITED_GAMETESTS + REQUIRED_TEXTURES + REQUIRED_GENERATED + GENERATED_MODIFIED + [ZH_INPUT] + TOOLS + REPORTS
                    + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS])
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-mold] %s passed'
ROWS_MARKER = re.compile(r'\[hbm-mold\] rows (\d+)')
ROW_LINE = re.compile(r'\[hbm-mold\] row (\w+) ')
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the
# sessions of the batch. Every top-level handoff-*.md and *-report.md of OUT is indexed as well.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'make_freeze.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_head.txt', 'start_hashes.txt',
                  'main-notes.md', 'handoff-builder.md', 'handoff-verifier.md', 'handoff-packaging.md', 'handoff-reviewer.md', 'builder-progress.md', 'chain.sh', 'gw.sh', 'import_textures.py',
                  'add_zh.py', 'make_production_diff.py')
# Review files under OUT; each must exist and is indexed by the receipt. --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'casting_attribution.py', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-progress.md', 'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier-gt/scope-before.txt', 'verifier-gt/scope-after.txt',
                   'verify-final.out', 'compare.log', 'localization-final.log', 'resources-audit-final.log', 'packaged-resources-final.log')
CASTING_ATTRIBUTION = 'casting-attribution.json'
CASTING_DIR = OUT/'final/castingsuites'
CASTING_SUITES = ('verify_goal10a', 'verify_goal5a_casting')
FAIL_SET_DIFF = 'final/fail-set-diff.json'
GAMETEST_LOG = 'build/migration/goal27d/gametest-final.log'
NEW_SUITE = 'verify_goal27d_molds.py --gametest-log build/migration/goal27d/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
OLD_SUITE_27C = 'verify_goal27c_foundry.py --gametest-log build/migration/goal27c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# features.json: no new group (handoff); foundry-casting, materials and anvil-stamps may change notes / target_paths / target_watch; every existing group keeps its status and reviewed_source_commit.
NOTES_MAY_CHANGE = {'foundry-casting', 'materials', 'anvil-stamps'}
# The groups the snapshot of the end of 24A predates (24B..27C).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser', 'rbmk-autoloader', 'rbmk-crane',
                          'hazard-system', 'radiation-detection', 'gas-masks', 'hazmat-suits', 'radiation-medicine', 'material-system', 'foundry-casting'}
RADIATION_NOTE = ('Goal27D: molds cast radioactive materials (uranium, plutonium, ferrouranium, ...) into radioactive ingots, nuggets, billets and blocks; handle radioactive casts only in a '
                  'disposable world. ')
MELTDOWN_NOTE = 'Goal27D: no new meltdown path. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_MOLD = ORIGINAL+'items/machine/ItemMold.java'
O_CASTING_TE = ORIGINAL+'tileentity/machine/TileEntityFoundryCastingBase.java'
O_BASIN_TE = ORIGINAL+'tileentity/machine/TileEntityFoundryBasin.java'
O_BASIN_BLOCK = ORIGINAL+'blocks/machine/FoundryBasin.java'
O_CASTING_BLOCK = ORIGINAL+'blocks/machine/FoundryCastingBase.java'
O_ANVIL = ORIGINAL+'inventory/recipes/anvil/AnvilRecipes.java'
O_SMITHING = ORIGINAL+'inventory/recipes/anvil/AnvilSmithingMold.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_MODBLOCKS = ORIGINAL+'blocks/ModBlocks.java'
O_SHAPES = ORIGINAL+'inventory/material/MaterialShapes.java'
O_LANG_EN = O_RES+'lang/en_US.lang'
O_LANG_ZH = O_RES+'lang/zh_CN.lang'
O_MOLD_TE = ORIGINAL+'tileentity/machine/TileEntityFoundryMold.java'
O_SOURCES = [O_MOLD, O_CASTING_TE, O_MOLD_TE, O_BASIN_TE, O_BASIN_BLOCK, O_CASTING_BLOCK, O_ANVIL, O_SMITHING, O_CRAFTING, O_MODBLOCKS, O_SHAPES, O_LANG_EN, O_LANG_ZH]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'mold_overrides_stone': (O_MOLD, 'blockOverrides.put(Mats.MAT_STONE'), 'mold_overrides_obsidian': (O_MOLD, 'blockOverrides.put(Mats.MAT_OBSIDIAN'),
    'mold_nugget': (O_MOLD, '"nugget", MaterialShapes.NUGGET'), 'mold_wire': (O_MOLD, '"wire", MaterialShapes.WIRE, 8'), 'mold_blade': (O_MOLD, '"blade", MaterialShapes.INGOT.q(3)'),
    'mold_stamp': (O_MOLD, '"stamp", MaterialShapes.INGOT.q(4)'), 'mold_ingots': (O_MOLD, '"ingots", MaterialShapes.INGOT, 9'), 'mold_wires_dense': (O_MOLD, '"wires_dense", MaterialShapes.DENSEWIRE, 9'),
    'mold_block': (O_MOLD, '"block", MaterialShapes.BLOCK'), 'mold_shape_cost': (O_MOLD, 'return shape.q(amount);'), 'mold_shape_title': (O_MOLD, 'I18nUtil.resolveKey("shape." + shape.name())'),
    'mold_multi_title': (O_MOLD, 'I18nUtil.resolveKey("shape." + name)'),
    'casting_cooloff_reset': (O_CASTING_TE, 'cooloff = 200;'), 'casting_capacity': (O_CASTING_TE, 'return mold == null ? 0 : mold.getCost();'),
    'casting_installed_mold': (O_CASTING_TE, 'if(mold.size == this.getMoldSize())'), 'casting_slot_gate': (O_CASTING_TE, 'if(this.slots[1] != null) return false;'),
    'casting_output_gate': (O_CASTING_TE, 'return mold.getOutput(stack.material) != null;'), 'casting_mold_size': (O_CASTING_TE, 'public abstract int getMoldSize();'),
    'basin_size': (O_BASIN_TE, 'return 1;'), 'basin_flow_refused': (O_BASIN_TE, 'canAcceptPartialFlow'), 'basin_block_flow_refused': (O_BASIN_BLOCK, 'canAcceptPartialFlow'),
    'smithing_first_row': (O_ANVIL, 'new AnvilSmithingMold(0,'), 'smithing_last_row': (O_ANVIL, 'new AnvilSmithingMold(21,'),
    'smithing_count_gate': (O_SMITHING, 'left.stackSize == matchesPrefix.stacksize'), 'smithing_explicit_gate': (O_SMITHING, 'left.getItemDamage() == stack.getItemDamage() && left.stackSize  == stack.stackSize'),
    'recipe_basin': (O_CRAFTING, 'new ItemStack(ModBlocks.foundry_basin)'), 'block_basin': (O_MODBLOCKS, 'foundry_basin = new FoundryBasin()'),
}
# Expected figures of the handoff and the task book (every value is also computed from the sources).
MOLD_ORDER = [0, 1, 2, 3, 4, 19, 20, 5, 6, 7, 8, 9, 10, 11, 13, 21, 12]
EXPECTED = dict(nugget=8, ingot=72, block=648, molds=17, small=12, large=5, mold_costs=[8, 48, 72, 72, 72, 216, 72, 216, 288, 288, 288, 216, 648, 648, 648, 648, 648], cooloff=200, new_smithing=14,
                existing_smithing=3, new_items=14, basin_hardness=5.0, basin_resistance=10.0, language_added=29, deferred_entries=106, recipes=1, stack_override_materials=2)
KNOWN_DIFFERENCES = {
    'gun_and_custom_molds': 'the gun molds (ItemMold.java ids 16, 17, 22-28) and the custom-shape molds (ids 100+) are not ported: the 17 mainline molds are (main-notes.md)',
    'slag_tap': 'the slag tap (CraftingManager.java:927) and flowing slag are not ported; slag is cast through the shape molds (ingot_raw slag variant, block_slag) like any material',
    'upgrade_plug_sound': 'inserting a mold is silent: NEO has no upgradePlug sound (main-notes.md "Findings before dispatch")',
    'insert_only_when_empty': 'a mold can be inserted only while the casting block holds no material (amount == 0), as NEO\'s foundry_mold did before 27D; upstream inserts into an empty slot 0 regardless',
    'initial_cooloff': 'the original field initialiser is cooloff = 100 (TileEntityFoundryCastingBase.java:26) but every tick that does not count down resets it to 200 (:61), so it matters only when a block fills before its first update tick; NEO starts at 200',
    'shape_title_keys': '27A added no shape.* keys: 27D adds the 13 keys the molds use (original en_US.lang:5050-5076, zh_CN.lang:4321-4346); the task book says they existed',
    'explicit_samples_undamaged': 'the explicit smithing samples (blades, stamps) must be undamaged, as upstream compared item damage (AnvilSmithingMold.java:52)',
    'jei_types': 'JEI recipes are MoldItem.CastingRow (mold, material, cost, output) instead of upstream\'s Shape / Casting types',
    'basin_floor_texture': 'the basin model draws its floor top face with #bottom, as upstream RenderFoundryBasin does (main-notes.md after the builder)',
    'hardness': 'the basin uses the original hardness 5.0 and resistance 10.0 (ModBlocks.java:1771); NEO\'s existing foundry_mold keeps its local 0.6',
    'block_slag_recipe': 'the 9:1 block_slag compression pair (MineralRecipes.java:58) is not in NEO: the block mold can cast block_slag but nothing crafts it back (main-notes.md out-of-scope finding)',
}
RECIPE_ROW = re.compile(r'(addRecipeAuto|addShapelessAuto)\(new ItemStack\(ModBlocks\.(foundry_basin)(?:, (\d+))?\), new Object\[\] \{ (.*?) \}\);')

# 27A / 27B / 27C ones the receipt carries forward under a new heading.
CARRIED_REPINS = 'repinned_since_'


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal27d release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 101 dirty and the planned files) when it reproduces the baseline hash, else the blob at the start
    commit (with CRLF where the working tree had it); None when nothing reproduces the baseline hash. A file the Goal27C delivery left unchanged (for example CrucibleAlloyGameTests.java)
    is not a copy: its start bytes are the start-commit blob."""
    if (START_FILES/p).is_file():
        data = (START_FILES/p).read_bytes()
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    try: blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT,
                                        stderr=subprocess.DEVNULL)
    except Exception: return None
    for data in (blob, blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def start_json(base, p):
    data = start_bytes(base, p)
    assert data is not None, 'No reproducible start bytes for '+p
    return json.loads(data.decode('utf-8-sig'))


def start_pin(base, p):
    """The Goal27D start hash of a frozen path: baseline files, or for a build/ record (Git-ignored, so baseline files does not list it) the hash the goal27c receipt
    records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal27c packager protected (built there from the Goal21A..Goal27B starts and receipts and the goal27c start), plus every path the goal27c receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (goal21a..goal27b) and every release file of the frozen start (the goal27c package
    included). The records that already drifted (the older drift: the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes)
    are pinned at their Goal27D start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal27c packager set at its Goal27C start hash, for the records that changed between the starts."""
    goal27c_start = read(GOAL27C_BASELINE)
    out = dict(goal27c_protected_paths(goal27c_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal27c receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal27c_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    assert all(p.endswith('-ACCEPTANCE.md') for p in repinned), 'A non-checklist pin changed between the Goal27C and Goal27D starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal27c_start):
    """{path: {receipts, start_sha256, goal27c_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal27c receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal27c receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21..26 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal27c '
                           'receipt does not hash it. Frozen at the Goal27D start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal27c) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal27c package; the goal27c receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal27c '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal27c_start_sha256=goal27c_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal27c_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def scope_text(tests, total_tests):
    return (f'Goal27D (the last batch of Goal 27: foundry basin, molds and casts): a casting base shared by foundry_mold and the new foundry_basin; a mold definition table with 17 molds (14 new mold '
            f'items, the three existing generalised); casts resolved through the 27A material registry, explicit multi-output and override tables; a generic mold smithing recipe for the 14 new molds; '
            f'JEI casting rows for every (mold, material) pair; the Goal 27 unified real-game acceptance checklist GOAL27D-ACCEPTANCE.md; {tests} FoundryMoldGameTests ({total_tests} GameTests in total, '
            f'one batch per test). Gameplay impact: every registered material can now be cast into its ingots, nuggets, billets, plates, wires, dense wires, cast plates, shells, pipes and blocks where NEO '
            f'has the item; ferrouranium ingots (and so the tier-4 anvil) are obtainable in survival; the foundry basin casts nine ingots/plates/dense wires, three cast plates or a block at once; '
            f'molds are smithed on a tier-1 anvil from a sample of the shape; combinations without an item are refused.')


def group(p, imported):
    if p in NEW_JAVA: return 'production-new'
    if p in EDITED_GAMETESTS: return 'gametest-edit'
    if p in MODIFIED_JAVA or p in OPTIONAL_JAVA: return 'production'
    if p in imported: return 'production-resource-imported'
    if p == ZH_INPUT: return 'language'
    if p in GENERATED_MODIFIED or GENERATED_ADDED.fullmatch(p) or GENERATED_MOLD.fullmatch(p) or GENERATED_TAGS.fullmatch(p): return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p == THREAD_PROMPTS: return 'planning-session'
    if p in REPORTS or BATCH_RECORD.fullmatch(p) or p == TASK_BOOK: return 'reports'
    if RECORD_27C.fullmatch(p): return 'previous-batch-record-append'
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records'
    return None


def owner_of(p):
    """goal27d, except the planning-session edit of GOAL27-THREAD-PROMPTS.md (a separate session)."""
    return PLANNING_OWNER if p == THREAD_PROMPTS else OWNER


def original_lang(text):
    return {k: v for k, _, v in (l.partition('=') for l in text.split('\n') if '=' in l and not l.startswith('#'))}


def original_recipes(text):
    """{block: dict(type, count, pattern, key | ingredients)} of the foundry basin row of the original CraftingManager (items mapped to NEO ids)."""
    out = {}
    for kind, name, count, args in RECIPE_ROW.findall(text):
        parts = split_top(args)
        if kind == 'addRecipeAuto':
            rows = [p.strip('"') for p in parts if p.startswith('"')]
            rest = [p for p in parts if not p.startswith('"')]
            out[name] = dict(type='minecraft:crafting_shaped', count=int(count or 1), pattern=rows, key={rest[i].strip("'"): recipe_item(rest[i+1]) for i in range(0, len(rest), 2)})
        else:
            out[name] = dict(type='minecraft:crafting_shapeless', count=int(count or 1), ingredients=sorted(recipe_item(p) for p in parts))
    return out


SHAPE_DEF = re.compile(r'MaterialShapes (\w+)\s*=\s*new MaterialShapes\((?:(\d+)|(\w+)\.quantity \* (\d+)|(\w+)\.quantity)\s*[,)]')


def shape_quanta(text):
    """{NAME: quantity} of the MaterialShapes constants whose quantity is a literal, `X.quantity * k` or `X.quantity` (the expressions the molds use), in file order."""
    out = {}
    for name, lit, base_name, factor, same in SHAPE_DEF.findall(text):
        if lit: out[name] = int(lit)
        elif base_name and base_name in out: out[name] = out[base_name]*int(factor)
        elif same and same in out: out[name] = out[same]
    return out


MOLD_ROW = re.compile(r'(?:registerMold\(new Mold(?:Shape|Multi|Block)|register\(new (?:Shape|Multi|Block)Mold)\(\s*(\d+),\s*(S|L),\s*"(\w+)",\s*MaterialShapes\.(\w+)(?:\.q\((\d+)\))?(?:,\s*(\d+)(?=\s*[,)]))?')


def mold_rows(text, quanta):
    """{id: (size, name, shape, q, amount, cost)} of the mold definition rows (ItemMold.java:46-92 / MoldItem.java): cost = shape quantity * q (multi molds) or * amount (shape molds)."""
    out = {}
    for mold_id, size, name, shape, q, amount in MOLD_ROW.findall(text):
        factor = int(q) if q else int(amount) if amount else 1
        out[int(mold_id)] = (size, name, shape, int(q) if q else None, int(amount) if amount else 1, quanta[shape]*factor)
    return out


def generated_recipe(path):
    """The comparable form of a generated recipe JSON (category dropped), or None when the file does not exist."""
    if not (ROOT/path).is_file(): return None
    d = read(ROOT/path)
    out = dict(type=d.get('type'), count=(d.get('result') or {}).get('count', 1), result=(d.get('result') or {}).get('id'))
    if d.get('type') == 'minecraft:crafting_shaped':
        out.update(pattern=d.get('pattern'), key={k: v.get('item') for k, v in (d.get('key') or {}).items()})
    else:
        out.update(ingredients=sorted(i.get('item') for i in d.get('ingredients', [])))
    return out


def smithing_rows(text):
    """The `new AnvilSmithingMold(id, ...` rows of the original AnvilRecipes: the mold ids in file order."""
    return [int(i) for i in re.findall(r'new AnvilSmithingMold\((\d+),', text)]


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
    goal27c_start = read(GOAL27C_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal27D commits nothing): HEAD 690ce8c0 (the 2026-10-26 push of 27A and 27B,
    # = origin/master) on the Goal 27 planning commit 71c2f660 on the Goal 26 close-out 0786697d, with 101 status lines: the UNCOMMITTED Goal27C delivery (the 100 changed files of the
    # goal27c receipt) and the planning session's post-push edit of GOAL27-THREAD-PROMPTS.md.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(START_PREFIX), 'The frozen start is not on the 2026-10-26 push commit 690ce8c0'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 27' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the Goal 27 push commit'
    status_lines = base['target_status'].splitlines()
    delivery_changed = {e['path']: e for e in prior_receipt['changed_files']}
    assert len(status_lines) == START_STATUS_LINES and START_STATUS.read_text(encoding='utf-8').splitlines() == status_lines \
        and {l[3:] for l in status_lines} == set(delivery_changed) | {THREAD_PROMPTS}, \
        f'The frozen start is not the {START_STATUS_LINES} status lines of the uncommitted Goal27C delivery (the goal27c receipt changed files) and GOAL27-THREAD-PROMPTS.md: baseline target_status / start_status.txt'
    assert base['target_parent'].startswith(PLANNING_PREFIX) and base['origin_master'] == start_head, 'The start commit is not origin/master on the Goal 27 planning commit 71c2f660'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal27c receipt records another original commit than the frozen start'
    assert prior_receipt['target_start_commit'] == prior_receipt['target_head_at_packaging'] == start_head, \
        'The goal27c package was not built on the start commit 690ce8c0 (the Goal27C delivery is uncommitted on it)'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal27D (the Goal27C and Goal27D deliveries stay uncommitted until the Goal 27 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2)}
    assert chain[1].startswith(PLANNING_PREFIX) and chain[2].startswith(GOAL26_CLOSEOUT), 'NEO HEAD~1..2 are not the Goal 27 planning commit 71c2f660 and the Goal 26 close-out 0786697d: '+str(chain)
    committed_files = [l for l in git_ro(ROOT, 'show', '--name-only', '--format=', start_head).splitlines() if l.strip()]
    assert committed_files and not any(p.startswith('build/') for p in committed_files), 'The start commit is empty or holds build/ files'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and '27A and 27B' in base['start_content']['committed'] and '27C delivery' in base['start_content']['uncommitted'], \
        'Baseline start content differs (expected the committed 27A and 27B deliveries and the uncommitted 27C delivery)'
    assert set(base['older_receipt_protected_paths']) == OLDER_RECEIPTS, 'Baseline older receipts differ'
    assert base['goal27c_changed_after_drift'] == {}, 'The baseline records Goal27C files changed after the goal27c receipt: '+str(base['goal27c_changed_after_drift'])
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    older_drift_nonempty = {k: v for k, v in base['older_receipt_evidence_drift'].items() if v}  # freeze_start.py records only the non-empty entries in startup-verification.json
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256_at_freeze'] == base['build_libs_jar_sha256_at_freeze'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_lines'] == len(status_lines) == startup['dirty_start_files'] == START_STATUS_LINES \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == older_drift_nonempty, \
        'startup-verification.json differs from baseline.json'
    start_stamp = start_json(base, STAMP)
    assert base['stamp_state']['generated_resources_recorded'] == prior_receipt['generated_resource_count'] == len(start_stamp['generated']) \
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal27c generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_freeze']

    # The Goal27C delivery is working-tree state at this start: every changed file of the goal27c receipt must have exactly the receipt's after-hash in the frozen start (no shared record
    # differs: the 27C records are all hashed or listed as not hashed, and the freeze followed the packaging by minutes), and none of them is in the start commit's own file list.
    delivery_differs = sorted(p for p, e in delivery_changed.items() if base['files'].get(p) != e['after_sha256'])
    assert not delivery_differs, 'A Goal27C delivery file differs from its receipt after-hash at the Goal27D start: '+str(delivery_differs[:6])
    dirty = {}
    for line in START_HASHES.read_text(encoding='utf-8').splitlines():
        if line.strip():
            h, p = line.split(None, 1)
            dirty[p.strip().lstrip('*')] = h
    assert set(dirty) == set(delivery_changed) | {THREAD_PROMPTS} and all(base['files'].get(p) == h for p, h in dirty.items()), \
        'start_hashes.txt is not the 101 dirty start files at their baseline hashes'
    frozen_27c = prior_receipt['concurrent_session']['frozen_planning_documents']
    planning_edit_note = ('Edited by the Goal 27 planning session (a separate session, not part of this batch) after the 27C freeze: it deleted the round-pacing paragraphs of the 27C and 27D prompts. May differ '
                          'from the start hash; never restored; not hashed by the receipt.')
    planning_session_edit = dict(path=THREAD_PROMPTS, owner=PLANNING_OWNER, start_sha256=base['files'][THREAD_PROMPTS], current_sha256=sha(ROOT/THREAD_PROMPTS),
                                 changed_since_start=base['files'][THREAD_PROMPTS] != sha(ROOT/THREAD_PROMPTS), receipt_goal27c_sha256=(prior_receipt.get('planning_session_edit') or {}).get('current_sha256'),
                                 note=planning_edit_note)
    uncommitted_start = dict(
        status_entries=len(status_lines), status=status_lines,
        description='the uncommitted Goal27C delivery (the 100 changed files of the goal27c receipt) and the planning-session edit of GOAL27-THREAD-PROMPTS.md',
        committed_delivery=dict(commit=start_head[:8], parent=base['target_parent'][:8], files_in_commit=len(committed_files),
                                note='690ce8c0 commits and pushes Goal 27 batches 27A and 27B (origin/master); the Goal27C delivery is NOT in it.'),
        uncommitted_delivery=dict(batch='goal27c', receipt=PREVIOUS_RECEIPT.relative_to(ROOT).as_posix(), receipt_changed_files=len(delivery_changed),
                                  equal_to_receipt_after_sha256=sum(1 for p, e in delivery_changed.items() if base['files'].get(p) == e['after_sha256']),
                                  note='Their start bytes are the Goal27C delivery (baseline-files holds a copy of each dirty file); this batch builds on them and owns every change it makes to them. '
                                       'The 27C records (GOAL27C.md, GOAL27C-ACCEPTANCE.md, goal27c-*) are hashed by the goal27c receipt and must keep their hash unless the main agent appends a dated line.'),
        planning_edit=planning_session_edit)

    # 2. Previous deliveries: the goal27c package, every old release file and the protected evidence; build/libs at the freeze is the goal27c package itself.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the freeze is not the goal27c package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal27c receipt list + the goal27c package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal27c receipt count + the goal27c release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal27c receipt'
    assert not base['previous_receipt_evidence_drift'], 'The goal27c receipt records evidence drift at the start: '+str(list(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal27c_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    # The 27C records the goal27c receipt hashes may gain a dated line from the main agent (insert-only against the start bytes); every other protected path must equal its pin.
    appendable = sorted(p for p in protected if RECORD_27C.fullmatch(p) and p in base['files'] and (ROOT/p).is_file() and sha(ROOT/p) != protected[p])
    appended_27c, appended_bad = {}, []
    for p in appendable:
        data = start_bytes(base, p)
        inserted = insertions(lines_of(data), lines_of((ROOT/p).read_bytes())) if data is not None else None
        if inserted is None: appended_bad.append(p)
        else: appended_27c[p] = dict(start_sha256=protected[p], current_sha256=sha(ROOT/p), inserted_lines=len(inserted),
                                     note='A dated line appended by the main agent to a Goal27C record during Goal27D (insert-only against the start bytes); the goal27c receipt is not rewritten.')
    need(not appended_bad, 'Goal27C records changed other than by inserted lines (they must equal their start hash or only gain lines): '+str(appended_bad))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or (sha(ROOT/p) != h and p not in appended_27c))
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal27c receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal27d (GOAL27-THREAD-PROMPTS.md to the planning session). Everything else equals its start hash.
    changes = changed_since_start(base)
    imported = {p for p in changes if TEXTURE_PATTERN.fullmatch(p)}
    optional_changed = [p for p in OPTIONAL_JAVA if p in changes]
    modified_java = MODIFIED_JAVA + optional_changed
    production_java = NEW_JAVA + modified_java + [p for p in EDITED_GAMETESTS if p in changes]
    older_gametests_frozen = sorted(p for p in base['files'] if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p not in OPTIONAL_JAVA and p not in EDITED_GAMETESTS)
    unassigned = sorted(p for p in changes if group(p, imported) is None)
    need(not unassigned, 'Path changed since the Goal27D start that the owner table does not list (production outside the listed new and modified Java files, FoundryMoldGameTests and the two edited '
         'GameTests, a hand-written resource other than the 14 mold item and 4 foundry_basin textures, a generated file other than the stamp, en_us.json, the pickaxe tag and the foundry_basin / mold '
         'blockstates / models / recipe / advancement / loot table, a protected or frozen record, an older tool, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal 26 and earlier records, the Goal27A / Goal27B records or SURVIVAL-PLAYABILITY.md changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal27D start: '+str(deleted)
    for p in MODIFIED_JAVA + EDITED_GAMETESTS + GENERATED_MODIFIED + [ZH_INPUT, TASK_BOOK] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + REQUIRED_TEXTURES + REQUIRED_GENERATED + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    block_models = {n: sorted(p for p in changes if re.fullmatch(re.escape(GENERATED_ROOT)+r'assets/hbmsntm/models/block/'+n+r'[a-z_]*\.json', p)) for n in BLOCK_NAMES}
    need(all(block_models.values()), 'no generated block model assets/hbmsntm/models/block/<block>*.json yet for: '+str([n for n, v in block_models.items() if not v]))
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(production_java) - imported - {ZH_INPUT})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified (+ optional), {len(NEW_JAVA)} new and {len(EDITED_GAMETESTS)} edited GameTest Java files, the mold / foundry_basin textures and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools = OLD_TOOLS_FROZEN + sorted(p for p in base['files'] if p.startswith(FROZEN_TOOL_DIRS))
    frozen_tools_changed = sorted(p for p in frozen_tools if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (package_goal27c.py, verify_goal27c_foundry.py, package_goal27b.py, verify_goal27b_crucible_alloys.py, '
         'package_goal27a.py, verify_goal27a_material_system.py, the casting regression wrapper and compat, the Goal 26C old-suite wrapper, the casting regressions and their folders): '+str(frozen_tools_changed))
    jei_classes = sorted(p for p in base['files'] if p.startswith(J+'handler/jei/') and p not in (JEI_HANDLER, JEI_PLUGIN))
    unchanged_bad = [p for p in UNCHANGED_JAVA + older_gametests_frozen + jei_classes if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed (Mats / MaterialEntries / MatDistribution / MaterialShapes / NTMMaterial, CrucibleRecipes / CrucibleRecipe / '
         'SerializableRecipe / ShredderRecipes, CopperScrapsItem / CastPlateItem / WireDenseItem, the channel / tank / outlet block entities and blocks, FoundryBaseBlockEntity, CrucibleUtil, ICrucibleAcceptor, '
         'MachineCrucibleBlockEntity, the other anvil smithing recipes, UniNodespace and the foundry node network, every other handler/jei class, every other GameTest class): '+str(unchanged_bad))
    goal27_now = sha(ROOT/GOAL27_RECORD)
    concurrent_record = dict(sessions=[PLANNING_OWNER], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository before the start. The batch ran under the main '
                                                           'agent (production review, the migration/ records) with a production builder (the 27D Java, runData), a GameTest verifier (FoundryMoldGameTests, '
                                                           'the two edited old GameTest lines, verify_goal27d_molds.py, runData and the GameTest server), a reviewer and this packaging verifier (the packager, the '
                                                           'final runner, the casting-regression attribution) working in the same checkout; each wrote only its named files (the scope snapshots of the verifiers are '
                                                           'indexed as evidence). The Goal 27 planning session edited GOAL27-THREAD-PROMPTS.md after the 27C freeze (planning_session_edit).',
                             goal27_md=dict(start_sha256=base['files'][GOAL27_RECORD], current_sha256=goal27_now, owners=[PREVIOUS_OWNER, OWNER]),
                             planning_session_edit=planning_session_edit,
                             frozen_planning_documents={p: dict(start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p) if (ROOT/p).is_file() else None) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p, imported), owner=owner_of(p), owners=[owner_of(p)], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal27D takes no new snapshot)'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-aee05a40f10f snapshot changed'
    production_changed = [p for p in production_java if p in changes]

    # The modified production files keep their start line endings (reported); new Java files are not mixed.
    gametest_edit_files = [p for p in EDITED_GAMETESTS if p in changes]
    start_text, line_endings = {}, {}
    for p in modified_java + gametest_edit_files:
        if p not in changes: continue
        data = start_bytes(base, p)
        if not need(data is not None, p+' has no reproducible start bytes (not in baseline-files and the start-commit blob does not match the baseline hash)'): continue
        start_text[p] = data
        start_eol, eol = eol_counts(data), eol_counts((ROOT/p).read_bytes())
        line_endings[p] = dict(start_crlf_lf=list(start_eol), now_crlf_lf=list(eol))
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}')
    for p in NEW_JAVA:
        if (ROOT/p).is_file():
            eol = eol_counts((ROOT/p).read_bytes())
            line_endings[p] = dict(start_crlf_lf=None, now_crlf_lf=list(eol))
            need(eol[0] == 0 or eol[1] == 0, f'{p} mixes CRLF and LF line endings: {eol}')

    # Production Java facts: every line edit counted (+/- against the start bytes); the judged edits (the handoff owner table's content rules) follow.
    edit_summary, inserted_lines, insert_summary, added_lines, removed_lines = {}, {}, {}, {}, {}
    for p in modified_java + gametest_edit_files:
        if p not in start_text: continue
        start_lines, live_lines = lines_of(start_text[p]), lines_of((ROOT/p).read_bytes())
        edit_summary[p] = edit_counts(start_lines, live_lines)
        added_lines[p] = list((Counter(live_lines) - Counter(start_lines)).elements())
        removed_lines[p] = list((Counter(start_lines) - Counter(live_lines)).elements())
        inserted = insertions(start_lines, live_lines)
        if inserted is not None:
            insert_summary[p] = len(inserted)
            inserted_lines[p] = [l for _, l in inserted]
    for p in NEW_JAVA:
        if (ROOT/p).is_file(): edit_summary[p] = dict(added=len(lines_of((ROOT/p).read_bytes())), removed=0)
    neo_text = lambda path: (ROOT/path).read_text(encoding='utf-8').replace('\r\n', '\n') if (ROOT/path).is_file() else ''
    text_of_start = lambda p: start_text[p].decode('utf-8').replace('\r\n', '\n') if p in start_text else ''
    content_rules = {}
    # CopperCastingRecipes: the class javadoc only (comments); no code line changes.
    if COPPER_CASTING in start_text:
        content_rules[COPPER_CASTING] = strip_noise(neo_text(COPPER_CASTING)) == strip_noise(text_of_start(COPPER_CASTING))
        need(content_rules[COPPER_CASTING], f'{COPPER_CASTING} differs from the start outside comments and imports (the handoff allows its class javadoc only)')
    # FoundryMoldBlockEntity / FoundryMoldBlock: rebuilt on the shared casting base (a rewrite: reported by their +/-, judged by what they now extend).
    if MOLD_BE in start_text:
        content_rules[MOLD_BE] = bool(re.search(r'class FoundryMoldBlockEntity extends FoundryCastingBlockEntity\b', neo_text(MOLD_BE))) and bool(re.search(r'int getMoldSize\(\)', neo_text(MOLD_BE)))
        need(content_rules[MOLD_BE], f'{MOLD_BE} does not extend FoundryCastingBlockEntity with a getMoldSize()')
    if MOLD_BLOCK in start_text:
        content_rules[MOLD_BLOCK] = bool(re.search(r'class FoundryMoldBlock extends FoundryCastingBlock\b', neo_text(MOLD_BLOCK)))
        need(content_rules[MOLD_BLOCK], f'{MOLD_BLOCK} does not extend FoundryCastingBlock')
    # The registration / provider files: no start line removed except a terminator or a call chain extended by an added line; the single-line registrations carry only mold / basin additions.
    rewritten = (MOLD_BE, MOLD_BLOCK, JEI_HANDLER, RENDERER)
    for p in modified_java:
        if p not in removed_lines or p in (MOLD_BE, MOLD_BLOCK, COPPER_CASTING): continue
        stray = stray_removals(removed_lines[p], added_lines[p])
        # The three existing molds (ingot, blade, cast plate) are re-defined by 27D: their registrations, JEI listings and English names (and the old casting.no_mold hint) are replaced, not extended.
        replaced = [s for s in stray if re.search(r'(?i)mold|casting', s)] if p in (NTM_ITEMS, JEI_PLUGIN, LANG_PROVIDER) else []
        stray = [s for s in stray if s not in replaced]
        content_rules[p] = not stray
        if replaced: content_rules[p+'#existing_mold_lines_replaced'] = replaced[:12]
        if p in rewritten: content_rules[p+'#start_lines_not_extended'] = stray[:12]  # reported: these files are rewritten by the batch
        else: need(not stray, f'{p} removes start lines that no added line extends: {stray[:4]}')
    for p in (NTM_ITEMS, NTM_BLOCKS, NTM_BE_TYPES, CREATIVE_TABS, LOOT_PROVIDER, TAG_PROVIDER, LANG_PROVIDER, STATE_PROVIDER, ITEM_MODEL_PROVIDER, RECIPE_PROVIDER):
        if p not in added_lines: continue
        odd = [l.strip()[:90] for l in added_lines[p] if not is_comment(l) and not l.lstrip().startswith('import ') and l.strip() not in ('}', ');', '{', ')', '};', '});')
               and not re.search(r'(?i)foundry|basin|mold|casting|cast|crucible|shape|Builder\.of\(|\.build\(null\)|^\s*\(\) ->|^\s*\w+,?\s*$|^\s*[.\w]+\(\)\s*[,;]?\s*$|\.pattern\(|\.define\(|\.unlockedBy\(|^\s*for\s*\(', l)]
        content_rules[p+'#added'] = not odd
        need(not odd, f'{p} adds lines that are not mold / basin / casting registrations: {odd[:4]}')
    # The two older GameTests the batch edits by design: the @GameTest methods are the start's; only the stated lines change.
    gametest_edits = {}
    for p in gametest_edit_files:
        if p not in start_text: continue
        now_text, was_text = (ROOT/p).read_text(encoding='utf-8'), start_text[p].decode('utf-8')
        names_now, names_was = GAMETEST_METHOD.findall(now_text), GAMETEST_METHOD.findall(was_text)
        annotations_now, annotations_was = len(GAMETEST_ANNOTATION.findall(now_text)), len(GAMETEST_ANNOTATION.findall(was_text))
        touched = [l.strip() for l in removed_lines[p] + added_lines[p] if '@GameTest' in l or 'public static void' in l]
        entry = dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p), added=len(added_lines[p]), removed=len(removed_lines[p]), game_tests=annotations_now, game_tests_at_start=annotations_was,
                     methods_unchanged=names_now == names_was)
        if p == CRUCIBLE_TESTS:
            one = len(removed_lines[p]) == 1 and len(added_lines[p]) == 1 and 'smithing.size() == 23' in removed_lines[p][0] and 'smithing.size() == 37' in added_lines[p][0]
            entry.update(rule='one line: the smithing recipe count 23 -> 37 (the 14 AnvilSmithingMoldRecipe rows 27D appends)', rule_holds=one and not touched, removed_line=removed_lines[p][:1], added_line=added_lines[p][:1])
        else:
            outside_method = strip_noise(cut_methods(now_text, r'public static void mold_regression\([^\n]*')) == strip_noise(cut_methods(was_text, r'public static void mold_regression\([^\n]*'))
            entry.update(rule='only the mold-limit block of mold_regression changes (the three hard-coded 27C molds become the 27D rules)', rule_holds=outside_method and not touched, outside_mold_regression_equal=outside_method)
        gametest_edits[p] = entry
        need(entry['rule_holds'] and entry['methods_unchanged'] and annotations_now == annotations_was, f'{p} changed beyond its allowed edit ({entry["rule"]}): {json.dumps(entry, ensure_ascii=False)[:400]}')

    # 4. The foundry molds against the original (EXPECTED holds the handoff figures; every value is computed from the sources; the NEO side is checked with tolerant source patterns, the
    # behaviour itself is the job of verify_goal27d_molds.py and the GameTests).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    facts, bad = {}, []

    def fact(key, value, expected=None, ok=None):
        facts[key] = value if expected is None else dict(value=value, expected=expected)
        if ok is None: ok = expected is None or value == expected
        if not ok: bad.append(key)

    o = {path: original_text(path) for path in O_SOURCES}
    n_shapes = neo_text(J+'inventory/material/MaterialShapes.java')
    o_q, n_q = shape_quanta(o[O_SHAPES]), shape_quanta(n_shapes)
    used_shapes = ('NUGGET', 'BILLET', 'INGOT', 'PLATE', 'WIRE', 'CASTPLATE', 'DENSEWIRE', 'SHELL', 'PIPE', 'BLOCK')
    fact('quanta', {k: n_q.get(k) for k in used_shapes}, None, ok=all(o_q.get(k) is not None and o_q.get(k) == n_q.get(k) for k in used_shapes)
         and (n_q['NUGGET'], n_q['INGOT'], n_q['BLOCK']) == (EXPECTED['nugget'], EXPECTED['ingot'], EXPECTED['block']))
    code = lambda p: strip_java_comments(neo_text(p))
    o_molds, n_molds = mold_rows(o[O_MOLD], o_q), mold_rows(code(MOLD_ITEM), n_q)
    ported_costs = [n_molds[i][5] if i in n_molds else None for i in MOLD_ORDER]
    sizes = Counter(n_molds[i][0] for i in n_molds)
    fact('mold_table', dict(ids=sorted(n_molds), small=sizes.get('S', 0), large=sizes.get('L', 0), costs_in_id_order_of_ItemMold=ported_costs), dict(ids=sorted(MOLD_ORDER), small=EXPECTED['small'], large=EXPECTED['large'],
         costs_in_id_order_of_ItemMold=EXPECTED['mold_costs']), ok=sorted(n_molds) == sorted(MOLD_ORDER) and len(n_molds) == EXPECTED['molds'] and sizes.get('S', 0) == EXPECTED['small'] and sizes.get('L', 0) == EXPECTED['large']
         and ported_costs == EXPECTED['mold_costs'] and all(o_molds.get(i) == n_molds[i] for i in n_molds))
    fact('mold_rows_equal_to_original', {i: dict(original=o_molds.get(i), neo=n_molds[i]) for i in sorted(n_molds) if o_molds.get(i) != n_molds[i]}, {})
    fact('molds_not_ported', sorted(set(o_molds) - set(n_molds)), [16, 17, 22, 23, 24, 25, 26, 27, 28])
    body = lambda text, header: (body_of(text, header) or '  ')[1:-1]  # body_of returns the braces too
    o_cast, n_cast = o[O_CASTING_TE], code(CASTING_BE)
    fact('casting_base_original', dict(cooloff_resets=len(re.findall(r'cooloff = 200;', o_cast)), initial_cooloff=re.findall(r'public int cooloff = (\d+);', o_cast), capacity='return mold == null ? 0 : mold.getCost();' in o_cast,
                                       size_gate='if(mold.size == this.getMoldSize())' in o_cast, slot_gate='if(this.slots[1] != null) return false;' in o_cast, output_gate='return mold.getOutput(stack.material) != null;' in o_cast,
                                       casts_when_full='this.amount == this.getCapacity() && slots[1] == null' in o_cast), dict(cooloff_resets=2, initial_cooloff=['100'], capacity=True, size_gate=True, slot_gate=True, output_gate=True, casts_when_full=True))
    fact('casting_base_neo', dict(cooloff=EXPECTED['cooloff'] if re.search(r'COOLOFF\s*=\s*200\s*;', n_cast) else None, capacity=bool(re.search(r'mold\s*==\s*null\s*\?\s*0\s*:\s*mold\.getCost\(\)', n_cast)),
                                  size_gate=bool(re.search(r'mold\.size\s*==\s*this\.getMoldSize\(\)', n_cast)), output_gate='getOutput(' in n_cast, standard_check='standardCheck' in n_cast,
                                  nbt_keys=all(f'"{k}"' in n_cast for k in ('cooloff',)) and all(f'"{k}"' in code(BASE_BE) for k in ('type', 'amount'))), dict(cooloff=EXPECTED['cooloff'], capacity=True, size_gate=True, output_gate=True, standard_check=True, nbt_keys=True))
    sizes_original = dict(mold=body(o[O_MOLD_TE], 'public int getMoldSize()').strip(), basin=body(o[O_BASIN_TE], 'public int getMoldSize()').strip())
    size_neo = lambda p: body(code(p), 'public int getMoldSize()').strip()
    fact('mold_sizes', dict(original=sizes_original, neo=dict(mold=size_neo(MOLD_BE), basin=size_neo(BASIN_BE))), None,
         ok=sizes_original == dict(mold='return 0;', basin='return 1;') and bool(re.fullmatch(r'return\s+(?:MoldItem\.)?(?:SIZE_SMALL|0)\s*;', size_neo(MOLD_BE))) and bool(re.fullmatch(r'return\s+(?:MoldItem\.)?(?:SIZE_LARGE|1)\s*;', size_neo(BASIN_BE))))
    fact('basin_refuses_flow', dict(original_entity=bool(re.search(r'canAcceptPartialFlow\([^)]*\)\s*\{\s*return false;', o[O_BASIN_TE])), original_block=bool(re.search(r'canAcceptPartialFlow\([^)]*\)\s*\{\s*return false;', o[O_BASIN_BLOCK])),
                                    neo_entity=bool(re.search(r'canAcceptPartialFlow\([^)]*\)\s*\{\s*return false;', code(BASIN_BE))), neo_block=bool(re.search(r'canAcceptPartialFlow\([^)]*\)\s*\{\s*return false;', code(BASIN_BLOCK)))
                                    or 'canAcceptPartialFlow' not in code(BASIN_BLOCK)), dict(original_entity=True, original_block=True, neo_entity=True, neo_block=True))
    blocks_original = {m[0]: (float(m[1]), float(m[2])) for m in re.findall(r'foundry_(basin) = new \w+\(\)\.setBlockName\("[a-z_]+"\)\.setHardness\(([\d.]+)F\)\.setResistance\(([\d.]+)F\)', o[O_MODBLOCKS])}
    fact('block_strength', blocks_original, {'basin': (EXPECTED['basin_hardness'], EXPECTED['basin_resistance'])})
    n_blocks_code = code(NTM_BLOCKS)
    fact('neo_block_strength', bool(re.search(r'"foundry_basin"[\s\S]{0,400}?strength\(\s*5\.0F\s*,\s*10\.0F\s*\)', n_blocks_code)), True)
    # The anvil smithing rows: the original has 17 `new AnvilSmithingMold(id, ...)` rows; NEO had three (ingot, blade, cast plate) and 27D appends the other 14 (the order is the GameTest's check).
    o_smithing = smithing_rows(o[O_ANVIL])
    fact('smithing_rows_original', o_smithing, [0, 1, 2, 3, 19, 13, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 21])
    fact('smithing_new_rows', sorted(i for i in o_smithing if i not in (2, 5, 19)), None, ok=len(o_smithing) - EXPECTED['existing_smithing'] == EXPECTED['new_smithing'] and sorted(o_smithing) == sorted(MOLD_ORDER))
    fact('smithing_matching_rules', dict(prefix_count='left.stackSize == matchesPrefix.stacksize' in o[O_SMITHING], explicit_damage_and_size='left.getItemDamage() == stack.getItemDamage() && left.stackSize  == stack.stackSize' in o[O_SMITHING]),
         dict(prefix_count=True, explicit_damage_and_size=True))
    fact('neo_smithing', dict(recipe_class='class AnvilSmithingMoldRecipe' in code(SMITHING_MOLD), registered='AnvilSmithingMoldRecipe' in code(ANVIL_RECIPES), blank_mold_consumed='MOLD_BASE' in code(SMITHING_MOLD) or 'mold_base' in code(SMITHING_MOLD)),
         None, ok='class AnvilSmithingMoldRecipe' in code(SMITHING_MOLD) and 'AnvilSmithingMoldRecipe' in code(ANVIL_RECIPES))
    fact('block_overrides', dict(original_stone='blockOverrides.put(Mats.MAT_STONE' in o[O_MOLD], original_obsidian='blockOverrides.put(Mats.MAT_OBSIDIAN' in o[O_MOLD], neo_stone=bool(re.search(r'STONE', code(MOLD_ITEM))),
                                 neo_obsidian=bool(re.search(r'OBSIDIAN', code(MOLD_ITEM)))), dict(original_stone=True, original_obsidian=True, neo_stone=True, neo_obsidian=True))
    # The crafting recipe of the basin: the original row (CraftingManager.java:922) against the generated NEO recipe JSON.
    o_recipes = original_recipes(o[O_CRAFTING])
    fact('recipes_original', {n: o_recipes.get(n) for n in BLOCK_NAMES}, None, ok=sorted(o_recipes) == sorted(BLOCK_NAMES) and o_recipes['foundry_basin']['count'] == 1 and o_recipes['foundry_basin']['type'] == 'minecraft:crafting_shaped'
         and None not in list(o_recipes['foundry_basin'].get('key', {}).values()))
    n_recipes = {n: generated_recipe(GENERATED_ROOT+f'data/hbmsntm/recipe/{n}.json') for n in BLOCK_NAMES}
    fact('recipes_generated', n_recipes, None, ok=all(n_recipes[n] is not None and n_recipes[n] == dict({k: v for k, v in o_recipes[n].items() if k != 'count'}, count=o_recipes[n]['count'], result='hbmsntm:'+n)
                                                    for n in BLOCK_NAMES if n in o_recipes))
    loot_ok = {}
    for n in BLOCK_NAMES:
        path = ROOT/(GENERATED_ROOT+f'data/hbmsntm/loot_table/blocks/{n}.json')
        loot_ok[n] = path.is_file() and [e.get('name') for pool in read(path).get('pools', []) for e in pool.get('entries', [])] == ['hbmsntm:'+n]
    fact('loot_tables', loot_ok, {n: True for n in BLOCK_NAMES})
    pickaxe = read(ROOT/PICKAXE_TAG)['values'] if (ROOT/PICKAXE_TAG).is_file() else []
    fact('pickaxe_tag', {n: 'hbmsntm:'+n in pickaxe for n in BLOCK_NAMES}, {n: True for n in BLOCK_NAMES})
    n_items_code = code(NTM_ITEMS)
    fact('neo_mold_items_registered', {n: f'"mold_{n}"' in n_items_code for n in MOLD_NAMES}, {n: True for n in MOLD_NAMES})
    fact('neo_blocks_registered', dict(block='"foundry_basin"' in n_blocks_code, block_entity_type='"foundry_basin"' in code(NTM_BE_TYPES), basin_in_client_proxy=bool(re.search(r'(?i)foundry_?basin|BASIN', code(CLIENT_PROXY)))), None,
         ok='"foundry_basin"' in n_blocks_code and '"foundry_basin"' in code(NTM_BE_TYPES))
    fact('neo_interface', dict(casting_block='ICrucibleAcceptor' in code(CASTING_BLOCK), basin_block_extends=bool(re.search(r'class FoundryBasinBlock extends FoundryCastingBlock\b', code(BASIN_BLOCK))),
                               basin_entity_extends=bool(re.search(r'class FoundryBasinBlockEntity extends FoundryCastingBlockEntity\b', code(BASIN_BE)))), dict(casting_block=True, basin_block_extends=True, basin_entity_extends=True))
    # Client isolation: no common class (casting base, basin, mold block entities and blocks, the mold item, the smithing recipe) names the renderer, the client packages or JEI.
    common_classes = [CASTING_BE, BASIN_BE, CASTING_BLOCK, BASIN_BLOCK, MOLD_ITEM, SMITHING_MOLD, MOLD_BE, MOLD_BLOCK, NTM_ITEMS, ANVIL_RECIPES]
    renderer_users = sorted(p for p in common_classes if (ROOT/p).is_file() and re.search(r'RenderFoundry|net\.minecraft\.client|com\.hbm\.render\.|mezz\.jei', code(p)))
    fact('client_isolation', dict(client_references_in_common_classes=renderer_users), None, ok=not renderer_users)
    facts['original_references'] = original_refs
    need(not bad, 'foundry-molds facts differ from the original or the handoff figures (or the NEO source / generated file is missing or its text differs): '+', '.join(
        f'{k}={json.dumps(facts[k], ensure_ascii=False)[:240]}' for k in bad))
    # The materials/reachability record (the main agent's; pending until written): it must say which molds, casts and ingredients are reachable.
    ledger = read(ROOT/LEDGER) if (ROOT/LEDGER).is_file() else None
    if need(ledger is not None, 'record missing: '+LEDGER):
        need(ledger.get('goal') == '27D', f'{LEDGER} is not the Goal 27D ledger')

    # 5. Resources: the byte imports (original worktree file and stored blob), against migration/goal27d-resource-ownership.json.
    ownership = read(ROOT/RESOURCE_OWNERSHIP) if (ROOT/RESOURCE_OWNERSHIP).is_file() else None

    def original_texture(target):
        """The original path of an imported NEO texture: item/mold_x.png <- textures/items/mold_x.png, block/foundry_basin_x.png <- textures/blocks/foundry_basin_x.png."""
        rel = target[len(TEXTURE_ROOT):]
        return O_RES+'textures/'+('items/'+rel[len('item/'):] if rel.startswith('item/') else 'blocks/'+rel[len('block/'):])

    imported_facts = {}
    for target in sorted(imported):
        original = original_texture(target)
        if not (SOURCE/original).is_file():
            need(False, 'no original texture for the imported resource '+target+' (expected '+original+')')
            continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        imported_facts[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size, original_worktree_sha256=sha(SOURCE/original),
                                      original_blob_sha256=hashlib.sha256(blob).hexdigest())
        need((ROOT/target).read_bytes() == checked_out == blob, f'{target} is not byte-identical to the original {original} (worktree and stored blob at {SOURCE_HEAD[:8]})')
    need(set(REQUIRED_TEXTURES) <= imported, 'imported textures missing: '+str(sorted(set(REQUIRED_TEXTURES) - imported)))
    if need(ownership is not None, 'record missing: '+RESOURCE_OWNERSHIP):
        entries = {a.get('target_path'): a for a in ownership.get('imported_assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == imported, f'{RESOURCE_OWNERSHIP} imported_assets are not the {len(imported)} imported textures at {SOURCE_HEAD[:8]}: {sorted(set(entries) ^ imported)[:4]}')
        for target, entry in entries.items():
            if target in imported_facts:
                need(entry.get('source_path') == imported_facts[target]['original_path'] and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('size') == (ROOT/target).stat().st_size,
                     f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original: {target}')

    # 6. features.json: no new group; every group keeps status and reviewed_source_commit; only foundry-casting, materials and anvil-stamps may change notes / target_paths / target_watch.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES <= set(start_features) and NOTES_MAY_CHANGE <= set(start_features), 'The start mapping does not hold the groups of 24B-27C (foundry-casting included)'
    may_change = lambda i: i in NOTES_MAY_CHANGE
    need(set(by_id) == set(start_features), 'features.json group ids are not the start ids (Goal27D adds no group): '+str(sorted(set(by_id) ^ set(start_features))))
    group_foundry = by_id.get('foundry-casting')
    if need(group_foundry is not None, 'migration/features.json lacks the group foundry-casting'):
        need(group_foundry.get('status') == 'partial-unverified' and group_foundry.get('reviewed_source_commit') == SOURCE_HEAD, f'features.json group foundry-casting is not partial-unverified at {SOURCE_HEAD[:8]}')
        unlisted = [p for p in O_SOURCES if not any(feature_matches(f, 'source', p) for f in features)]
        need(not unlisted, f'features.json lists these original sources in no group (source_paths / source_watch): {unlisted}')
        mapped_java = [p for p in NEW_JAVA + [pp for pp in (MOLD_BE, MOLD_BLOCK) if pp in changes] if p != MOLD_TESTS and not any(feature_matches(f, 'target', p) for f in features)]
        need(not mapped_java, f'features.json maps these new / changed Java paths in no group (target_paths / target_watch): {mapped_java[:4]}')
    absent = sorted({p for f in features for p in f.get('source_paths', []) if not (SOURCE/p).is_file()})
    need(not absent, f'features.json source_paths missing in the original: {absent[:6]}')
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    need(all(may_change(i) for i in notes_changed), 'features.json groups whose notes changed beyond foundry-casting / materials / anvil-stamps: '+str([i for i in notes_changed if not may_change(i)]))
    paths_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('target_paths') != start_features[i].get('target_paths'))
    need(all(may_change(i) for i in paths_changed), 'features.json groups whose target_paths changed beyond foundry-casting / materials / anvil-stamps: '+str([i for i in paths_changed if not may_change(i)]))
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in ('notes', 'target_watch', 'target_paths')} !=
                          {k: v for k, v in start_features[i].items() if k not in ('notes', 'target_watch', 'target_paths')})
    need(not shrunk and not other_fields, f'features.json previous groups lost target_watch entries {shrunk} or changed other fields {other_fields}')
    watch_grown = sorted(i for i, f in by_id.items() if i in start_features and set(f.get('target_watch', [])) - set(start_features[i].get('target_watch', [])))
    need(all(may_change(i) for i in watch_grown), 'features.json groups whose target_watch grew beyond foundry-casting / materials / anvil-stamps: '+str([i for i in watch_grown if not may_change(i)]))
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped; the main agent adds target_paths / target_watch to foundry-casting): '+str(unmapped[:6]))

    # 7. Language and the generated tree: 29 new keys, casting.no_mold removed, the existing molds' names reworded (English generated, Chinese and the mapping by the main agent), the stamp must be
    # current, the generated additions the foundry_basin and mold-item set.
    en_start, en_now = start_json(base, EN), read(ROOT/EN)
    zh_start, zh_now = start_json(base, ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = start_json(base, LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    o_en, o_zh = lang_file(O_LANG_EN), lang_file(O_LANG_ZH)
    placeholders = lambda s: sorted(re.findall(r'%[sdf%]|%\d\$[sd]', s or ''))
    language_keys = {}
    for key, source_key in LANG_SOURCE.items():
        language_keys[key] = dict(original_key=source_key, original_en=o_en.get(source_key), original_zh=o_zh.get(source_key), en=en_now.get(key), zh=zh_now.get(key), map_kind=(map_now.get(key) or {}).get('kind'),
                                  en_line=original_line(O_LANG_EN, source_key+'='), zh_line=original_line(O_LANG_ZH, source_key+'='))
    need(all(v['original_en'] and v['original_zh'] for v in language_keys.values()), 'original language lines missing: '+str([k for k, v in language_keys.items() if not (v['original_en'] and v['original_zh'])]))
    need(all(v['en'] and v['zh'] and placeholders(v['en']) == placeholders(v['original_en']) and placeholders(v['zh']) == placeholders(v['original_zh']) for v in language_keys.values()),
         'NEO language values missing or with other placeholders than the original: '+str([k for k, v in language_keys.items() if not (v['en'] and v['zh'] and placeholders(v['en']) == placeholders(v['original_en'])
                                                                                                                                    and placeholders(v['zh']) == placeholders(v['original_zh']))]))
    mold_name_source = dict(original_key=MOLD_NAME_KEY, original_en=o_en.get(MOLD_NAME_KEY), original_zh=o_zh.get(MOLD_NAME_KEY), en_line=original_line(O_LANG_EN, MOLD_NAME_KEY+'='), zh_line=original_line(O_LANG_ZH, MOLD_NAME_KEY+'='),
                            neo={k: dict(en=en_now.get(k), zh=zh_now.get(k)) for k in sorted(k for k in KEYS if k.startswith('item.hbmsntm.mold_'))})
    need(all(v['en'] and v['zh'] for v in mold_name_source['neo'].values()), 'a new mold item name lacks English or Chinese: '+str([k for k, v in mold_name_source['neo'].items() if not (v['en'] and v['zh'])]))
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_en = dict(added=sorted(KEYS), removed=sorted(REMOVED_KEYS), changed=sorted(EN_CHANGED))
    expected_zh = dict(added=sorted(KEYS), removed=sorted(REMOVED_KEYS), changed=sorted(ZH_CHANGED))
    expected_map = dict(added=sorted(KEYS), removed=sorted(REMOVED_KEYS), changed=sorted(set(EN_CHANGED) | set(ZH_CHANGED)))
    need(len(KEYS) == EXPECTED['language_added'], f'expected new language keys: {len(KEYS)}, the handoff says {EXPECTED["language_added"]}')
    need(en_delta == expected_en, 'generated en_us.json delta is not the 29 new keys, casting.no_mold removed and mold_blade / mold_ingot reworded: '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_zh, 'zh_cn.json delta is not the 29 new keys, casting.no_mold removed and mold_blade / mold_ingot / mold_plate_cast changed: '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_map, 'zh_cn-map.json delta is not the 29 new entries, casting.no_mold removed and the changed mold entries: '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal27c totals'
    delta_net = len(KEYS) - len(REMOVED_KEYS)
    need(len(en_now) == totals['en_us'] + delta_net and len(zh_now) == totals['zh_cn'] + delta_net and len(map_now) == totals['zh_cn_map'] + delta_net,
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal27c totals {totals} + {delta_net}')
    map_kinds, start_kinds = dict(Counter(e.get('kind') for e in map_now.values())), dict(Counter(e.get('kind') for e in map_start.values()))
    kinds_added = Counter((map_now.get(k) or {}).get('kind') for k in KEYS)
    kinds_removed = Counter((map_start.get(k) or {}).get('kind') for k in REMOVED_KEYS)
    expected_kinds = {k: start_kinds.get(k, 0) + kinds_added.get(k, 0) - kinds_removed.get(k, 0) for k in set(start_kinds) | set(kinds_added)}
    expected_kinds = {k: v for k, v in expected_kinds.items() if v}
    need(start_kinds == totals['zh_cn_map_by_kind'] and map_kinds == expected_kinds and map_kinds.get('deferred') == EXPECTED['deferred_entries'],
         f'mapping kinds are {map_kinds}, expected the goal27c kinds {totals["zh_cn_map_by_kind"]} adjusted by the added / removed keys {expected_kinds} (deferred {EXPECTED["deferred_entries"]} unchanged)')
    need(dict(kinds_added) == {'upstream': UPSTREAM_ADDED, 'local': LOCAL_ADDED} and kinds_removed == Counter(local=1),
         f'new mapping entries are {dict(kinds_added)}, expected {UPSTREAM_ADDED} upstream (the basin, foundry.noCast, the 13 shape titles) and {LOCAL_ADDED} local (the 14 mold names); removed {dict(kinds_removed)}')
    need(all((map_now.get(k) or {}).get('kind') == 'upstream' for k in LANG_SOURCE), 'mapping entries of the upstream keys are not kind upstream: '+str([k for k in LANG_SOURCE if (map_now.get(k) or {}).get('kind') != 'upstream']))
    need(all((map_start[k] or {}).get('kind') == (map_now[k] or {}).get('kind') for k in expected_map['changed']), 'a changed mapping entry changed its kind: '+str(expected_map['changed']))
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    stamp_current = not stale and not mismatch and not unrecorded
    need(stamp_current, f'{STAMP} not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
    start_generated = start_stamp['generated']
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    mold_modified = sorted(p for p in generated_changed if GENERATED_MOLD.fullmatch(GENERATED_ROOT+p))
    tags_modified = sorted(p for p in generated_changed if GENERATED_TAGS.fullmatch(GENERATED_ROOT+p))
    need({EN_ENTRY, PICKAXE_TAG[len(GENERATED_ROOT):]} <= set(generated_changed) and set(generated_changed) <= {EN_ENTRY} | set(tags_modified) | set(mold_modified),
         f'Generated resources changed since the start are not en_us.json, the tag files that gained the basin (pickaxe.json required) and the foundry_mold / mold item models: {generated_changed[:8]}')
    foundry_added = [p for p in generated_added if GENERATED_ADDED.fullmatch(GENERATED_ROOT+p)]
    need(foundry_added == generated_added, f'Generated additions other than the foundry_basin and mold item model set: {sorted(set(generated_added) - set(foundry_added))[:6]}')
    advancements = {n: [p for p in generated_added if re.fullmatch(r'data/hbmsntm/advancement/recipes/[a-z]+/'+n+'\\.json', p)] for n in BLOCK_NAMES}
    need(all(len(v) == 1 for v in advancements.values()), 'generated recipe advancements: exactly one per block expected: '+str(advancements))
    for path in (v[0] for v in advancements.values() if v):
        adv = read(ROOT/(GENERATED_ROOT+path))
        need(adv.get('rewards') == {'recipes': ['hbmsntm:'+Path(path).stem]}, f'{path} does not reward its own recipe')
    need(len(stamp['generated']) == prior_receipt['generated_resource_count'] + len(generated_added), f'generated resource count {len(stamp["generated"])} is not the goal27c count {prior_receipt["generated_resource_count"]} + {len(generated_added)}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted([STAMP] + [GENERATED_ROOT+p for p in generated_added] + [GENERATED_ROOT+p for p in generated_changed])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, the stamp additions and the stamp changes: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))

    # 8. Evidence: GameTest log, audits, Gradle logs, diff, the final suite run, the verifier report, the casting attribution, compare and the batch's own scripts and records.
    evidence = {}
    gametest_line = gametest_count = None
    jei_rows = None
    yield_lines = []
    total_now = sum(annotations(p) for p in sorted(GAMETEST_DIR.glob('*.java')))
    total_start = 0
    for p in sorted(GAMETEST_DIR.glob('*.java')):
        rel = p.relative_to(ROOT).as_posix()
        if rel in base['files']:
            data = start_bytes(base, rel)
            assert data is not None, 'No reproducible start bytes for '+rel
            total_start += len(GAMETEST_ANNOTATION.findall(data.decode('utf-8')))
    assert total_start == prior_receipt['gametest']['tests'], 'The start GameTest sources do not hold the previous count of '+str(prior_receipt['gametest']['tests'])
    gametest_added = total_now - total_start
    gametest_expected = total_now
    mold_test_names = sorted(GAMETEST_METHOD.findall((ROOT/MOLD_TESTS).read_text(encoding='utf-8'))) if (ROOT/MOLD_TESTS).is_file() else []
    mold_annotations = annotations(ROOT/MOLD_TESTS) if (ROOT/MOLD_TESTS).is_file() else 0
    need(bool(mold_test_names) and mold_annotations == len(mold_test_names), f'{MOLD_TESTS} holds {mold_annotations} @GameTest annotations and {len(mold_test_names)} parsed methods (or the file does not exist yet)')
    need(gametest_added == mold_annotations, f'GameTest sources grew by {gametest_added} tests, FoundryMoldGameTests holds {mold_annotations} (another GameTest class changed its test count, e.g. SmokeTestSupport?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in mold_test_names), 'GameTest log lacks "[hbm-mold] <name> passed" for: '+str([n for n in mold_test_names if (GAMETEST_MARKER % n) not in text]))
            rows = ROWS_MARKER.findall(text)
            row_lines = len(ROW_LINE.findall(text))
            if need(len(rows) == 1 and row_lines == int(rows[0]) > 0, f'GameTest log lacks one "[hbm-mold] rows N" line with N matching its "[hbm-mold] row <mold> <material> -> ..." lines (rows {rows}, row lines {row_lines})'):
                jei_rows = int(rows[0])
            yield_lines = [l.split('[hbm-mold] ', 1)[1].strip() for l in text.splitlines() if '[hbm-mold] casting_yield: ' in l or '[hbm-mold] slag: ' in l]
            # Yields the original's amounts dictate (ItemMold.java:46-77, MaterialShapes quanta): nugget 8 -> 1, ingot 72 -> 1, wire 72 -> 8, ingots / plates / dense wires 648 -> 9, cast plates 648 -> 3, block 648 -> 1, slag via ingot_raw / block_slag.
            expected_yields = ['casting_yield: mold_nugget + Uranium 8 -> hbmsntm:nugget_uranium x1', 'casting_yield: mold_ingot + Steel 72 -> hbmsntm:ingot_steel x1', 'casting_yield: mold_wire + Copper 72 -> hbmsntm:wire_copper x8',
                               'casting_yield: mold_ingots + Steel 648 -> hbmsntm:ingot_steel x9', 'casting_yield: mold_plates_cast + Steel 648 -> hbmsntm:cast_plate x3', 'casting_yield: mold_block + Iron 648 -> minecraft:iron_block x1',
                               'casting_yield: mold_block + Stone 648 -> minecraft:stone x1', 'casting_yield: mold_block + Obsidian 648 -> minecraft:obsidian x1', 'slag: mold_ingot + Slag 72 -> hbmsntm:ingot_raw x1',
                               'slag: mold_block + Slag 648 -> hbmsntm:block_slag x1']
            need(all(y in yield_lines for y in expected_yields), 'GameTest log lacks the expected cast yields: '+str([y for y in expected_yields if y not in yield_lines]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries, audit_comparison = {}, {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal27d/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad_findings = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad_findings and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad_findings))
        # This batch adds language keys and resources, so the info / review counts may differ from the previous receipt: recorded, not required equal.
        audit_comparison[key] = dict(previous=prior_receipt['audits'][key], now=audit['summary'], equal=audit['summary'] == prior_receipt['audits'][key])
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal27d/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if name == 'production-vs-start.diff':
            if (OUT/name).is_file() and (OUT/name).stat().st_size > 0: evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)  # judged below
            continue
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal27d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    named = list(START_EVIDENCE) + list(REVIEW_EVIDENCE)
    named += sorted(p.name for p in OUT.glob('handoff-*.md') if p.name not in named) + sorted(p.name for p in OUT.glob('*-report.md') if p.name not in named)
    for name in named:
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal27d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/FAIL_SET_DIFF).is_file(): evidence[(OUT/FAIL_SET_DIFF).relative_to(ROOT).as_posix()] = sha(OUT/FAIL_SET_DIFF)
    # The casting regressions (goal27a_casting_regression_run.py, unchanged wrapper): one record per suite in the final rerun's own directory; its transcript is hashed with it.
    casting = {}
    for suite in CASTING_SUITES:
        rec_path = CASTING_DIR/f'{suite}-compat.json'
        if not need(rec_path.is_file(), f'evidence missing: build/migration/goal27d/final/castingsuites/{suite}-compat.json (goal27a_casting_regression_run.py {suite}, redirected into final/ by run_final.py)'): continue
        rec = read(rec_path)
        transcript = ROOT/rec['transcript'] if rec.get('transcript') else None
        casting[suite] = dict(record=rec_path.relative_to(ROOT).as_posix(), exit=rec.get('exit'), mode=rec.get('mode'), blockers=rec.get('blockers'), stages=rec.get('stages'),
                              javac_errors_by_attribution=rec.get('javac_errors_by_attribution'), transcript=rec.get('transcript'))
        evidence[rec_path.relative_to(ROOT).as_posix()] = sha(rec_path)
        if need(transcript is not None and transcript.is_file(), f'{rec_path.name} names no existing transcript'): evidence[transcript.relative_to(ROOT).as_posix()] = sha(transcript)
    attribution = None
    if need((OUT/CASTING_ATTRIBUTION).is_file(), 'evidence missing: build/migration/goal27d/'+CASTING_ATTRIBUTION+' (casting_attribution.py, after the final rerun)'):
        att = read(OUT/CASTING_ATTRIBUTION)
        problems = []
        if att.get('mode') != 'compare' or att.get('missing_inputs'): problems.append(f'mode {att.get("mode")!r}, missing inputs {att.get("missing_inputs")}')
        if att.get('baseline_sha256') != sha(BASELINE) or att.get('tool_sha256') != sha(OUT/'casting_attribution.py'): problems.append('written by another baseline or another version of casting_attribution.py')
        if att.get('old_dir') != (GOAL27C_OUT/'final/castingsuites').relative_to(ROOT).as_posix() or att.get('new_dir') != CASTING_DIR.relative_to(ROOT).as_posix(): problems.append(f'compares {att.get("old_dir")} with {att.get("new_dir")}')
        if sorted(att.get('suites', {})) != sorted(CASTING_SUITES): problems.append('suites '+str(sorted(att.get('suites', {}))))
        for suite, entry in att.get('suites', {}).items():
            for side in ('old', 'new'):
                s = entry.get(side) or {}
                if not s.get('parse_matches_record'): problems.append(f'{suite} {side}: the parsed javac errors do not match the record')
                if side == 'new' and suite in casting and s.get('record_sha256') != sha(ROOT/casting[suite]['record']): problems.append(f'{suite}: the new record changed after the attribution')
            for e in entry.get('new_errors', []) + entry.get('moved', []):
                file = e.get('at', '').rsplit(':', 1)[0] if 'at' in e else (e.get('identity') or {}).get('file', '')
                if e.get('attribution') == 'unattributed': problems.append(f'{suite}: unattributed error {e.get("at") or e.get("identity")}')
                elif e.get('attribution') == '27D change' and file not in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed to a 27D change but the file did not change')
                elif e.get('attribution') == 'not 27D' and file in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed "not 27D" but the file changed')
        need(not problems, CASTING_ATTRIBUTION+' is not a consistent attribution of the two casting regressions: '+'; '.join(problems[:6]))
        attribution = dict(path=(OUT/CASTING_ATTRIBUTION).relative_to(ROOT).as_posix(), sha256=sha(OUT/CASTING_ATTRIBUTION), summary=att.get('summary'),
                           suites={s: dict(counts=e.get('counts'), new_errors_by_attribution=e.get('new_errors_by_attribution'), moved_by_attribution=e.get('moved_by_attribution'),
                                           disappeared_by_file_status=e.get('disappeared_by_file_status'), stages_changed=e.get('stages_changed')) for s, e in att.get('suites', {}).items()})
        evidence[attribution['path']] = attribution['sha256']
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal27d/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files and edited GameTests against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    diffed_modified = [p for p in modified_java + gametest_edit_files if p in changes]
    listed_in_diff = NEW_JAVA + diffed_modified
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal27d/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in diffed_modified) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(p in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([p for p in listed_in_diff if p not in diff_text]))
    final = None
    # The suites of the goal27c final run plus the Goal27D verifier (the two casting regressions are in the goal27c set and run unchanged, redirected into final/; verify_goal27c_foundry.py is an old suite now).
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal27c final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal27D suite is already in the goal27c final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal27d/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal27c final set + the Goal27D verifier: '+str(sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal27d/'+VERIFY_REPORT+' (tools/migration/verify_goal27d_molds.py report; run it with --gametest-log and --jar after the final build)'):
        report = read(OUT/VERIFY_REPORT)
        required_hashes = list(production_changed)
        problems = report_problems(report, required_hashes)
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        need(not summary_part.get('checks_pending'), VERIFY_REPORT+' still has pending checks: '+str(summary_part.get('checks_pending'))[:300])
        need(report.get('start_target_head') == start_head and report.get('original_head') == SOURCE_HEAD, VERIFY_REPORT+' records another start commit or original commit')
        stale_hashes = sorted(p for p in required_hashes if (report.get('production_sha256') or {}).get(p) != sha(ROOT/p))
        need(not stale_hashes, VERIFY_REPORT+' production_sha256 differs from the live files (rerun the verifier after the last edit): '+str(stale_hashes))
        mutations = report.get('mutations')
        mutation_entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
        detected = summary_part.get('mutations_detected', sum(1 for e in mutation_entries if isinstance(e, dict) and e.get('detected') is True))
        total = summary_part.get('mutations_total', summary_part.get('mutations_applied', len(mutation_entries)))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=NEW_TOOLS[0],
                        tool_sha256=sha(ROOT/NEW_TOOLS[0]) if (ROOT/NEW_TOOLS[0]).is_file() else None, mutations_detected=f'{detected}/{total}', mutations_total=total,
                        checks_passed=summary_part.get('checks_passed'), command=report.get('command'))
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(re.findall(r'(?:ItemMold|TileEntityFoundry\w+|FoundryBasin|FoundryCastingBase|AnvilRecipes|AnvilSmithingMold|CraftingManager|MaterialShapes|ModBlocks)\.java:\d+(?:-\d+)?',
                                                json.dumps(report, ensure_ascii=False))))
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal27c compare target paths plus this batch's compare-inventory paths).
    cmp_prev = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal27c/compare.json differs from the goal27c receipt'
    prev_added = sorted(p for p in compare_paths(cmp_prev['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    prev_modified = sorted(p for p in compare_paths(cmp_prev['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(prev_added) | set(prev_modified) | set(own_target))
    expected_added = sorted(set(prev_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal27d/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-27c paths + the %d of this batch not already among them (%d compare-inventory paths changed)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(prev_added) + len(prev_modified), len(set(own_target) - set(prev_added) - set(prev_modified)), len(own_target))):
        cmp = read(OUT/COMPARE)
        need(cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, COMPARE+' is not against the aee05a40f snapshot')
        need(cmp['current_target_state']['commit'] == start_head, COMPARE+' records another target commit than the start commit')
        counts_cmp = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(all(v == 0 for v in counts_cmp['source'].values()) and counts_cmp['target']['removed'] == 0, COMPARE+' original is not 0/0/0 or the target removes paths: '+str(counts_cmp))
        listed = sorted(p for p in compare_paths(cmp['changes']['target']['added']) | compare_paths(cmp['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
        need(listed == expected_target, COMPARE+' target set differs: extra %s, missing %s' % (sorted(set(listed) - set(expected_target))[:8], sorted(set(expected_target) - set(listed))[:8]))
        listed_added = sorted(p for p in compare_paths(cmp['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
        need(listed_added == expected_added, f'{COMPARE} target added set differs: extra {sorted(set(listed_added) - set(expected_added))[:6]}, missing {sorted(set(expected_added) - set(listed_added))[:6]}')
        need(not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], COMPARE+' reports unmapped changes: '+str(cmp['unmapped_changes']))
        need(not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], COMPARE+' reports removed features or missing files')
        states = Counter(f.get('state') for f in cmp['features'])
        need(len(cmp['features']) == len(features) and set(states) <= {'target-changed', 'no-observed-file-change'}, f'{COMPARE} feature states are {dict(states)}, expected only target-changed / no-observed-file-change over {len(features)} groups')
        for g in ('foundry-casting',):
            need(any(f.get('id') == g and f.get('state') == 'target-changed' for f in cmp['features']), f'{COMPARE} does not report {g} as target-changed')
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal27c (goal27c compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal27c_paths=len(prev_added) + len(prev_modified), goal27d_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-27C)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 9. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal27d or a recompile.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal27c) package (run the final build)')
    if True:  # --check also runs the delta code (against the current build/libs, which is still the previous package until the final build)
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [p[len(RES):] for p in sorted(imported) if p[len(RES):] not in names or jar.read(p[len(RES):]) != (ROOT/p).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, the imported textures, zh_cn.json or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == expected_en and zh_jar == expected_zh, 'JAR en_us.json / zh_cn.json differ from the previous package by something other than the foundry molds delta: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            recompile_only = {n for n in RECOMPILE_ONLY if n in jar_delta['modified'] and recompile_equal(n, prior.read(n), jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        generated_entries = set(generated_added) | set(generated_changed) | {ZH_ENTRY} | {p[len(RES):] for p in imported}
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if n.endswith('.class') and owner_class(n) in production_java: owner = [OWNER]
                elif kind == 'modified' and n == 'META-INF/MANIFEST.MF': owner = [OWNER]
                elif kind in ('added', 'modified') and n in generated_entries and not n.endswith('.class'): owner = [OWNER]
                elif kind == 'modified' and n in recompile_only and owner_class(n) not in changes: owner = [RECOMPILE_OWNER]
                if not owner: unowned.append(f'{kind}: {n}' + (' [source ' + owner_class(n) + ' unchanged since the start: a recompile difference, not a source change]' if n.endswith('.class') and owner_class(n) not in changes else ''))
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources and the two edited GameTests, the generated additions / changes (foundry_basin blockstate, models, recipe, advancement, loot table, '
             'mold item models, en_us.json, the tags), zh_cn.json, the imported textures and META-INF/MANIFEST.MF are owned): '+str(unowned[:10]))
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in production_java if p in changes]
        comment_only = [p for p in (COPPER_CASTING,) if content_rules.get(p)]  # javadoc-only edits may leave the class bytes unchanged (no required class change)
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(comment_only) <= set(class_owners),
             'Changed Java sources and goal27d JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(comment_only) - set(class_owners))) + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == generated_entries, 'JAR non-class delta differs from the generated additions / changes + zh_cn.json + the imported textures: extra %s, missing %s' % (
            sorted(non_class - generated_entries)[:8], sorted(generated_entries - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for p in modified_java + gametest_edit_files:
            outer = p[len('src/main/java/'):-len('.java')]
            if p in changes and p not in comment_only: need(outer+'.class' in jar_delta['modified'], outer+'.class is not a modified JAR class')
        added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
        removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
        need(bool(classes) and len(classes) == prior_receipt['compiled_classes_verified'] + added_classes - removed_classes,
             f'Compiled class count {len(classes)} is not the previous count {prior_receipt["compiled_classes_verified"]} +{added_classes} -{removed_classes}')
        language = dict(en=en_jar, zh=zh_jar)

    # 10. Records: the release name and the batch reports.
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    for p in unnamed: need(False, 'record does not name '+RELEASE_NAME+': '+p)
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS:
        if p not in OPTIONAL_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p
    indexed = {Path(p).relative_to(OUT.relative_to(ROOT)).as_posix() for p in evidence if p.startswith(OUT.relative_to(ROOT).as_posix()+'/')}
    unindexed = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in indexed and p.name != 'baseline.json')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added), generated_modified=generated_changed,
                   imported_textures=sorted(imported), planning_session_edit=planning_session_edit, appended_27c_records=sorted(appended_27c),
                   start_drift=sorted(drift_report), repinned_since_goal27c_start=sorted(repinned),
                   language_delta=dict(en=en_delta, zh=zh_delta, map=map_delta), language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, line_endings=line_endings, content_rules=content_rules, gametest_edits={p: dict(added=e['added'], removed=e['removed'], rule_holds=e['rule_holds']) for p, e in gametest_edits.items()},
                   foundry_molds={k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v)) < 200 else f'<{len(v)} items>') for k, v in facts.items()}, foundry_molds_facts_bad=bad,
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_mold_tests=mold_test_names, jei_casting_rows=jei_rows, final_suites_expected=final_expected,
                   audit_comparison=audit_comparison,
                   casting_regressions={s: dict(exit=c['exit'], mode=c['mode'], blockers=len(c['blockers'] or []), javac_errors_by_attribution=c['javac_errors_by_attribution']) for s, c in casting.items()},
                   casting_attribution=opt(attribution, 'summary'),
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
    foundry_molds = dict(neo=NEW_JAVA + modified_java, original=O_SOURCES, facts=facts, expected=EXPECTED, known_differences=KNOWN_DIFFERENCES, original_references=original_refs,
                         language_keys=language_keys, mold_names=mold_name_source, imported_resources=imported_facts, resource_ownership_record=RESOURCE_OWNERSHIP, reachability_record=LEDGER,
                         jei_casting_rows=jei_rows, cast_yields_from_gametest_log=yield_lines,
                         note=f'Casting base shared by foundry_mold and foundry_basin (slot 0 mold / slot 1 cast, installed mold must match the block\'s size, capacity = the mold cost, a pour is refused when the mold has no output for '
                              f'the material, cooloff {EXPECTED["cooloff"]} ticks, ItemMold.java / TileEntityFoundryCastingBase.java); foundry_basin takes large molds only, pours from UP only, refuses flow and is not connected by channels; '
                              f'17 molds (ids, sizes, costs and amounts per ItemMold.java:46-77: nugget 8, billet 48, ingot / plate / 8 wires / dense wire 72, cast plate and blade 216, blades / stamp / shell 288, pipe 216, '
                              f'nine ingots / plates / dense wires, three cast plates and the block 648); outputs from the 27A material registry (MaterialEntries.getPreferred for the shape molds, explicit blade / blades / stamp '
                              f'maps, stone and obsidian block overrides, slag through ingot_raw and block_slag); {EXPECTED["new_smithing"]} new anvil smithing rows (AnvilRecipes.java:98-126) beside the three kept '
                              f'c:ingots / cast plate / blade rows; {jei_rows} JEI casting rows (mold x material, from the GameTest log); old foundry_mold saves load; the gun molds, the custom-shape molds, the slag tap and flowing '
                              'slag and the upgradePlug sound are deferred (known_differences).')
    casting_record = dict(attribution=attribution, suites=casting, wrapper='tools/migration/goal27a_casting_regression_run.py (unchanged)', policy='tools/migration/goal27a_casting_compat.py (unchanged)',
                          note='The two frozen isolated casting regressions (verify_goal10a.py, verify_goal5a_casting.py) run through the unchanged Goal27A wrapper in the final rerun, redirected into '
                               'build/migration/goal27d/final/castingsuites; both already stopped at javac on the Goal26D, Goal27A, Goal27B and Goal27C trees, so none of their assertions is reached. casting-attribution.json '
                               'pairs the javac errors of the Goal27C final run with the Goal27D run and attributes every new or moved error by file to a Goal27D change or to "not 27D"; it is evidence about javac '
                               'in the frozen stub worlds only.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(mold_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   uncommitted_start=uncommitted_start,
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, reconstruction=base['reconstruction'], push_commit_parent=chain[1], goal26_closeout_commit=chain[2],
                                      note=f'The start tree is HEAD 690ce8c0 (the 2026-10-26 commit and push of Goal 27 batches 27A and 27B, = origin/master) on the Goal 27 planning commit 71c2f660 on the Goal 26 '
                                           f'close-out 0786697d, with {len(status_lines)} status lines: the UNCOMMITTED Goal27C delivery (the {len(delivery_changed)} changed files of the goal27c receipt, each equal to its receipt after-hash) and '
                                           f'the planning-session edit of GOAL27-THREAD-PROMPTS.md. build/libs at the start is the goal27c package {start_jar_sha[:8]}. The original did not move since 24A (aee05a40f). freeze_start.py hashed '
                                           f'every tracked and dirty file live ({len(base["files"])} baseline hashes) before the first 27D write and copied the dirty or planned files ({len(base["copied_scope"])} baseline-files); paths '
                                           f'this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, line_endings=line_endings, content_rules=content_rules, gametest_edits=gametest_edits, start_copies_supplement=[],
                   appended_27c_records=appended_27c,
                   foundry_molds=foundry_molds, casting_attribution=casting_record,
                   language=dict(changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']), added=dict(en_us=en_delta['added'], zh_cn=zh_delta['added'], zh_cn_map=map_delta['added']),
                                 removed=dict(en_us=en_delta['removed'], zh_cn=zh_delta['removed'], zh_cn_map=map_delta['removed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds), jar_delta=language,
                                 start_sha256={p: base['files'][p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD, LANG_PROVIDER)},
                                 note='Goal27D adds 29 keys: block.hbmsntm.foundry_basin (original tile.foundry_basin.name, en_US.lang:5601, zh_CN.lang:4826), foundry.noCast (en_US.lang:1207, zh_CN.lang:979), the 13 shape.* titles '
                                      '(en_US.lang:5050-5076, zh_CN.lang:4321-4346; 27A added none) and the 14 new mold names item.hbmsntm.mold_* (local; the original builds them from item.mold.name, en_US.lang:3459, zh_CN.lang:2926 + the shape title); '
                                      'casting.no_mold is removed (replaced by foundry.noCast); item.hbmsntm.mold_ingot and mold_blade (en and zh) and mold_plate_cast (zh) are reworded; the 106 deferred entries are unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith(CARRIED_REPINS)},
                   repinned_since_goal27c_start={p: dict(goal27c_start_pin_sha256=h, goal27d_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record, planning_session_edit=planning_session_edit,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok'), old_machine_suites_through=OLD_MACHINE_SUITES, casting_suites_through=['goal27a_casting_regression_run.py verify_goal10a',
                                                                                                                                                                            'goal27a_casting_regression_run.py verify_goal5a_casting']),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_mold_tests=mold_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per FoundryMoldGameTests test (names in new_mold_tests): what those '
                                      'tests assert about the 17-mold table (ids, sizes, costs, amounts, titles, items), the casting yields, the rejects, the multi molds, the 200-tick cooloff, the basin rules, the 14 smithing rows, '
                                      'slag, old foundry_mold saves and the 27C pour chain; the mold-limit block of FoundryChannelGameTests and the smithing count of CrucibleAlloyGameTests are re-pinned to the 27D rules; no client '
                                      '(the renderer, the models, the textures and the JEI screen are not drawn), no real player, no saved world, no survival chain.'),
                   audits=audit_summaries, audit_comparison=audit_comparison, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['foundry_casting (the Goal27C-only domain key; Goal27D adds foundry_molds)',
                                 'casting_regressions (the Goal27A key; Goal27D carries casting_attribution as Goal27B and Goal27C did: the wrapper and the two suites are unchanged, only their javac errors are attributed)',
                                 'material_system (the Goal27A-only domain key)', 'crucible_alloys (the Goal27B-only domain key)',
                                 'planning_commit / goal27a_delivery (the Goal27A and Goal27B deliveries are committed in the start commit 690ce8c0; see uncommitted_start.committed_delivery)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun (the six old isolated suites through the goal26c wrapper and the two casting regressions through the unchanged goal27a wrapper, whose javac '
                            'errors are attributed by casting_attribution.py), compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. No in-game client test was run: '
                            'the foundry_basin and the foundry_mold models, the molten levels and casts, the mold items\' icons and tooltips, the JEI casting screen and the Chinese UI are not seen on screen; no survival chain '
                            '(smelting in a crucible, smithing a mold on an anvil, casting through channels, tanks, outlets, molds and the basin) in a world was run; no dedicated server beyond GameTest; the Goal 27 unified '
                            'acceptance checklist GOAL27D-ACCEPTANCE.md is written, not run.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal27d JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal27c package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
