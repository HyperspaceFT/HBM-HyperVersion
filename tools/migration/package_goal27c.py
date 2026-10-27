"""Package Goal27C (the third batch of Goal 27, the shared ICrucibleAcceptor interface, the foundry channel, storage basin (tank) and outlet with their block entities, the foundry node
network, the crucible pouring through the interface, foundry_mold accepting pours and flows, the data-generated block models and the client renderer for molten levels, and the
FoundryChannelGameTests), cumulatively on the goal27b package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal27c.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal27c/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal27c/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal27c/baseline.json: NEO HEAD 690ce8c0 (the 2026-10-26 commit and push of Goal 27 batches 27A and 27B, = origin/master; parent 71c2f660 =
the Goal 27 planning commit) with 2 status lines: the planning-document edits to GOAL27-THREAD-PROMPTS.md and GOAL27C.md made after that push. The 27A and 27B deliveries, which the
goal27a and goal27b receipts recorded while they were uncommitted, are COMMITTED in the start commit (the packager checks the goal27b receipt's changed files against the start
hashes). freeze_start.py hashed every tracked and dirty file live (10,755 hashes) before the first 27C write and copied the 43 dirty or planned files into baseline-files/;
start_status.txt (2 lines), start_head.txt and start_hashes.txt (2 hashes) record it. The start bytes of a file are the live bytes at the freeze = baseline-files. build/libs at the
start is the goal27b package (baseline build_libs_jar_sha256_at_freeze = the goal27b JAR hash: no small fix in between). The original HEAD aee05a40f did not move since 24A, so there is no
upstream classification and no new snapshot. Every change since the start is computed from the baseline file hashes (not from git diff) and must be in the owner table below; every other
path must still equal its start hash. The modified production files are compared with their start bytes (baseline-files) and their +/- lines are reported. The JAR delta against the
goal27b package is attributed per entry; any entry without exactly one owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, recipes) are
computed here from the original and NEO sources where they can be; the figures the handoff states are asserted against those computations.

GOAL27-THREAD-PROMPTS.md is a planning-session edit after the 27C freeze (a separate session deleted the round-pacing paragraphs of the 27C and 27D prompts; main-notes.md "Concurrent
planning-session edit"): it may differ from its baseline hash, it is attributed to the owner "planning-session" (not goal27c), never fails the packager and is never restored; its
start and current hashes are recorded in the receipt. GOAL27C.md is the task book and delivery record of this batch and is hashed by the receipt.

The receipts that hash records (goal21a..goal27b, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start (the acceptance checklists, GOAL21D.md,
GOAL22C.md, goal21d-static-review.md and the goal24a working notes, known from earlier batches); they are listed in the receipt as start drift and must still equal their Goal27C start hash;
no receipt is rewritten and no other protected path may drift. The goal27b receipt itself drifts nowhere (baseline previous_receipt_evidence_drift is empty). GOAL27D.md, every GOAL27A* /
GOAL27B* / goal27a-* / goal27b-* record, every Goal 26 and earlier record and SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL27.md is a shared record, GOAL27C.md the
task book and delivery record (hashed by the receipt).

Like the packagers of 24B..27B this one has a single compare run (build/migration/goal27c/compare.json against the snapshot review-aee05a40f10f.json taken at the end of 24A: original 0/0/0,
target = exactly the goal27b compare target paths (read from build/migration/goal27b/compare.json) plus this batch's compare-inventory paths, the stamp dropped), no upstream
classification; it adds the foundry_casting facts (checked against the original and NEO source texts). The Goal27B-only receipt key crucible_alloys is dropped and the receipt says so;
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
from package_goal27b import (OUT as GOAL27B_OUT, BASELINE as GOAL27B_BASELINE, protected_paths as goal27b_protected_paths)

OUT = ROOT/'build/migration/goal27c'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
START_HASHES = OUT/'start_hashes.txt'
REFERENCE_PREVIOUS = GOAL27B_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL27B_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal27b/hbmsntm-198A-goal27b.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal27c'
RELEASE_NAME = 'hbmsntm-198A-goal27c.jar'
OWNER = 'goal27c'
PREVIOUS_OWNER = 'goal27b'
PLANNING_OWNER = 'planning-session'
START_PREFIX = '690ce8c0'
PLANNING_PREFIX = '71c2f660'
GOAL26_CLOSEOUT = '0786697d'
START_STATUS_LINES = 2
THREAD_PROMPTS = 'migration/GOAL27-THREAD-PROMPTS.md'
TASK_BOOK = 'migration/GOAL27C.md'
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
SRC = 'src/main/java/'
J = SRC+'com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
TEXTURE_ROOT = RES+'assets/hbmsntm/textures/'
O_RES = RES+'assets/hbm/'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a', 'goal26b', 'goal26c', 'goal26d', 'goal27a'}

# Production (owner goal27c): the NEW Java files (the interface, the util, the foundry block entities, blocks, node network and renderer, and the GameTest class) and the MODIFIED
# production sources (the handoff owner table); the optional ones are listed separately.
NEW_JAVA = [SRC+'api/hbm/block/ICrucibleAcceptor.java'] + [J+p+'.java' for p in (
    'util/CrucibleUtil', 'blockentity/machine/FoundryBaseBlockEntity', 'blockentity/machine/FoundryChannelBlockEntity', 'blockentity/machine/FoundryTankBlockEntity',
    'blockentity/machine/FoundryOutletBlockEntity', 'blocks/machine/FoundryChannelBlock', 'blocks/machine/FoundryTankBlock', 'blocks/machine/FoundryOutletBlock',
    'uninos/networkproviders/FoundryNetwork', 'uninos/networkproviders/FoundryNetworkProvider', 'uninos/networkproviders/FoundryNode', 'render/blockentity/RenderFoundry',
    'gametest/FoundryChannelGameTests')]
(ACCEPTOR, CRUCIBLE_UTIL, BASE_BE, CHANNEL_BE, TANK_BE, OUTLET_BE, CHANNEL_BLOCK, TANK_BLOCK, OUTLET_BLOCK, NETWORK, NETWORK_PROVIDER, NODE, RENDERER, FOUNDRY_TESTS) = NEW_JAVA
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blocks/NtmBlocks', 'blockentity/NtmBlockEntityTypes', 'inventory/NtmCreativeTabs', 'blockentity/machine/MachineCrucibleBlockEntity', 'blockentity/machine/FoundryMoldBlockEntity',
    'blocks/machine/FoundryMoldBlock', 'main/ClientProxy', 'datagen/NtmBlockStateProvider', 'datagen/NtmRecipeProvider', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider',
    'datagen/NtmLanguageProvider')]
(NTM_BLOCKS, NTM_BE_TYPES, CREATIVE_TABS, CRUCIBLE_BE, MOLD_BE, MOLD_BLOCK, CLIENT_PROXY, STATE_PROVIDER, RECIPE_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER, LANG_PROVIDER) = MODIFIED_JAVA
OPTIONAL_JAVA = [J+p+'.java' for p in ('main/ResourceManager', 'datagen/NtmItemModelProvider', 'gametest/SmokeTestSupport')]
RESOURCE_MANAGER = OPTIONAL_JAVA[0]
OLDER_GAMETEST_DIR = J+'gametest/'
# Must stay byte-identical to the start (the handoff list), plus every other GameTest class and every handler/jei class: see main().
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'inventory/material/Mats', 'inventory/material/MaterialEntries', 'inventory/material/MatDistribution', 'inventory/material/MaterialShapes', 'inventory/material/NTMMaterial',
    'inventory/recipes/CrucibleRecipes', 'inventory/recipes/CrucibleRecipe', 'inventory/recipes/CopperCastingRecipes', 'inventory/recipes/loader/SerializableRecipe',
    'inventory/recipes/ShredderRecipes', 'inventory/recipes/anvil/AnvilRecipes', 'items/CopperScrapsItem', 'items/NtmItems', 'uninos/UniNodespace', 'uninos/NodeNet', 'uninos/GenNode',
    'uninos/INetworkProvider')]
# Older tools that must equal their start bytes (handoff list); every file of the two frozen casting regression folders is added in main().
OLD_TOOLS_FROZEN = ['tools/migration/'+p for p in ('package_goal27b.py', 'verify_goal27b_crucible_alloys.py', 'package_goal27a.py', 'verify_goal27a_material_system.py',
                                                    'goal27a_casting_regression_run.py', 'goal27a_casting_compat.py', 'goal27a_scrap_textures.py', 'goal27a_effect_icons.py',
                                                    'goal26c_oldsuite_run.py', 'goal26c_oldsuite_compat.py', 'verify_goal10a.py', 'verify_goal10a_resources.py', 'verify_goal5a_casting.py',
                                                    'verify_goal5a_casting_resources.py', 'goal10a_scrap_textures.py', 'goal10a_mutation_check.py')]
FROZEN_TOOL_DIRS = ('tools/migration/goal10a_regression/', 'tools/migration/goal5a_casting_regression/')
NEW_TOOLS = ['tools/migration/verify_goal27c_foundry.py', 'tools/migration/package_goal27c.py']
TOOLS = NEW_TOOLS
# Hand-written resources (byte imports from the original; migration/goal27c-resource-ownership.json lists them): the foundry block textures and lava_gray.
TEXTURE_PATTERN = re.compile(re.escape(TEXTURE_ROOT)+r'(block/foundry_(?:channel|tank|outlet)_[a-z_]+\.png(?:\.mcmeta)?|models/machines/lava_gray\.png(?:\.mcmeta)?)')
REQUIRED_TEXTURES = [TEXTURE_ROOT+'block/foundry_'+n+'.png' for n in (
    'channel_top', 'channel_side', 'channel_bottom', 'channel_inner', 'tank_top', 'tank_side', 'tank_bottom', 'tank_inner', 'outlet_top', 'outlet_side', 'outlet_bottom', 'outlet_inner',
    'outlet_front', 'outlet_filter', 'outlet_lock')] + [TEXTURE_ROOT+'models/machines/lava_gray.png']
RESOURCE_OWNERSHIP = 'migration/goal27c-resource-ownership.json'
# Generated by runData: per block a blockstate, block model(s), an item model, a recipe with its advancement and a loot table; en_us.json and the pickaxe tag change; the stamp.
BLOCK_NAMES = ('foundry_channel', 'foundry_tank', 'foundry_outlet')
GENERATED_ADDED = re.compile(re.escape(GENERATED_ROOT)+r'(assets/hbmsntm/(?:blockstates|models/block|models/item)/foundry_(?:channel|tank|outlet)[a-z_]*\.json|'
                             r'data/hbmsntm/(?:recipe|loot_table/blocks|advancement/recipes/[a-z]+)/foundry_(?:channel|tank|outlet)\.json)')
PICKAXE_TAG = GENERATED_ROOT+'data/minecraft/tags/block/mineable/pickaxe.json'
REQUIRED_GENERATED = sorted(GENERATED_ROOT+f'{kind}/foundry_{n}.json' for n in ('channel', 'tank', 'outlet') for kind in (
    'assets/hbmsntm/blockstates', 'assets/hbmsntm/models/item', 'data/hbmsntm/recipe', 'data/hbmsntm/loot_table/blocks'))  # the recipe advancement (any category folder) is checked separately
# The foundry_mold blockstate / models may change when the builder re-models the mold (allowed as a modification, reported); no new file for it is expected.
GENERATED_TAGS = re.compile(re.escape(GENERATED_ROOT)+r'data/[a-z_]+/tags/.*\.json')  # the tag files that gained the three blocks (pickaxe.json is required, others allowed)
GENERATED_MOLD = re.compile(re.escape(GENERATED_ROOT)+r'assets/hbmsntm/(?:blockstates|models/block|models/item)/foundry_mold[a-z_]*\.json')
GENERATED_MODIFIED = [STAMP, EN, PICKAXE_TAG]
KEYS = ['block.hbmsntm.foundry_channel', 'block.hbmsntm.foundry_tank', 'block.hbmsntm.foundry_outlet', 'foundry.filter', 'foundry.inverted', 'foundry.invertFilter']
# Original language key -> NEO key (en_US.lang:1204-1206 and :5602-5605, zh_CN.lang:976-978 and :4827-4830).
LANG_SOURCE = {'block.hbmsntm.foundry_channel': 'tile.foundry_channel.name', 'block.hbmsntm.foundry_tank': 'tile.foundry_tank.name', 'block.hbmsntm.foundry_outlet': 'tile.foundry_outlet.name',
               'foundry.filter': 'foundry.filter', 'foundry.inverted': 'foundry.inverted', 'foundry.invertFilter': 'foundry.invertFilter'}
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal27c-* or GOAL27C-* record is hashed as well.
REPORTS = ['migration/GOAL27C.md', 'migration/GOAL27C-ACCEPTANCE.md', 'migration/goal27c-static-review.md', 'migration/goal27c-materials-review.json', 'migration/goal27c-localization-review.json',
           RESOURCE_OWNERSHIP]
LEDGER = REPORTS[3]
BATCH_RECORD = re.compile(r'migration/(goal27c-[^/]+\.(json|md)|GOAL27C-[^/]+\.md)')
GOAL27_RECORD = 'migration/GOAL27.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md', GOAL27_RECORD,
                  LOCALIZATION_RECORD]
# Shared records the batch may leave untouched ("possibly" in the handoff).
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
# The records of the other batches and the files no batch of this kind touches: no change is expected.
PLANNING_FROZEN = ['migration/GOAL27D.md', 'migration/SURVIVAL-PLAYABILITY.md']
# Every Goal 26 and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 26) and every Goal27A / Goal27B record (GOAL27A*, GOAL27B*, goal27a-*, goal27b-*).
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-6])(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-6])(?!\d)[a-z]?-[^/]+|GOAL27[AB](?:-[^/]+)?\.md|goal27[ab]-[^/]+)')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = (NEW_JAVA + MODIFIED_JAVA + REQUIRED_TEXTURES + REQUIRED_GENERATED + GENERATED_MODIFIED + [ZH_INPUT] + TOOLS + REPORTS
                    + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS])
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-foundry] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the
# sessions of the batch. Every top-level handoff-*.md and *-report.md of OUT is indexed as well.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_head.txt', 'start_hashes.txt', 'main-notes.md',
                  'handoff-builder.md', 'handoff-verifier.md', 'handoff-packaging.md', 'handoff-reviewer.md', 'builder-progress.md', 'chain.sh', 'make_production_diff.py')
# Review files under OUT; each must exist and is indexed by the receipt. --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'casting_attribution.py', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-progress.md', 'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier-gt/scope-before.txt', 'verifier-gt/scope-after.txt',
                   'verify-final.out', 'compare.log', 'localization-final.log', 'resources-audit-final.log', 'packaged-resources-final.log')
CASTING_ATTRIBUTION = 'casting-attribution.json'
CASTING_DIR = OUT/'final/castingsuites'
CASTING_SUITES = ('verify_goal10a', 'verify_goal5a_casting')
FAIL_SET_DIFF = 'final/fail-set-diff.json'
GAMETEST_LOG = 'build/migration/goal27c/gametest-final.log'
NEW_SUITE = 'verify_goal27c_foundry.py --gametest-log build/migration/goal27c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# JAR classes whose source is unchanged since the start and that differ from the previous package only in recompiled debug names (as in 26A-27B).
RECOMPILE_ONLY = {'com/hbm/gametest/RBMKRecyclingGameTests$1.class': (((b'\x01\x00\x04arg0', b'\x01\x00\x03pos'), (b'\x01\x00\x04arg1', b'\x01\x00\x05state')),
                                                                    ((b'\x01\x00\x03pos', b'\x01\x00\x04arg0'), (b'\x01\x00\x05state', b'\x01\x00\x04arg1')))}
RECOMPILE_OWNER = 'recompile-debug-names'
# features.json: ONE new group foundry-casting; crucible-alloying may change notes / target_paths / target_watch (handoff); every existing group keeps its status and reviewed_source_commit.
NEW_FEATURE = 'foundry-casting'
NOTES_MAY_CHANGE = {'crucible-alloying'}
# The groups the snapshot of the end of 24A predates (24B..27C).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser', 'rbmk-autoloader', 'rbmk-crane',
                          'hazard-system', 'radiation-detection', 'gas-masks', 'hazmat-suits', 'radiation-medicine', 'material-system', NEW_FEATURE}
RADIATION_NOTE = ('Goal27C: channels, tanks and outlets carry whatever the crucible melts, radioactive materials included, and their scraps keep it; handle radioactive melts only in a '
                  'disposable world. ')
MELTDOWN_NOTE = 'Goal27C: no new meltdown path. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_CHANNEL = ORIGINAL+'tileentity/machine/TileEntityFoundryChannel.java'
O_TANK = ORIGINAL+'tileentity/machine/TileEntityFoundryTank.java'
O_OUTLET = ORIGINAL+'tileentity/machine/TileEntityFoundryOutlet.java'
O_BASE = ORIGINAL+'tileentity/machine/TileEntityFoundryBase.java'
O_CRUCIBLE_TE = ORIGINAL+'tileentity/machine/TileEntityCrucible.java'
O_CRUCIBLE_UTIL = ORIGINAL+'util/CrucibleUtil.java'
O_ACCEPTOR = 'src/main/java/api/hbm/block/ICrucibleAcceptor.java'
O_CHANNEL_BLOCK = ORIGINAL+'blocks/machine/FoundryChannel.java'
O_TANK_BLOCK = ORIGINAL+'blocks/machine/FoundryTank.java'
O_OUTLET_BLOCK = ORIGINAL+'blocks/machine/FoundryOutlet.java'
O_CASTING_BLOCK = ORIGINAL+'blocks/machine/FoundryCastingBase.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_MODBLOCKS = ORIGINAL+'blocks/ModBlocks.java'
O_SHAPES = ORIGINAL+'inventory/material/MaterialShapes.java'
O_LANG_EN = O_RES+'lang/en_US.lang'
O_LANG_ZH = O_RES+'lang/zh_CN.lang'
O_SOURCES = [O_CHANNEL, O_TANK, O_OUTLET, O_BASE, O_CRUCIBLE_TE, O_CRUCIBLE_UTIL, O_ACCEPTOR, O_CHANNEL_BLOCK, O_TANK_BLOCK, O_OUTLET_BLOCK, O_CASTING_BLOCK, O_CRAFTING, O_MODBLOCKS, O_SHAPES,
             O_LANG_EN, O_LANG_ZH]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'acceptor_interface': (O_ACCEPTOR, 'public interface ICrucibleAcceptor'), 'base_standard_check': (O_BASE, 'public boolean standardCheck'), 'base_standard_add': (O_BASE, 'public MaterialStack standardAdd'),
    'base_get_capacity': (O_BASE, 'public abstract int getCapacity()'), 'channel_capacity': (O_CHANNEL, 'return MaterialShapes.INGOT.q(2);'), 'channel_cadence': (O_CHANNEL, 'nextUpdate = 5;'),
    'channel_swap': (O_CHANNEL, 'worldObj.rand.nextInt(5) == 0 || this.amount == 1'), 'channel_flow_key': (O_CHANNEL, 'nbt.setByte("flow"'), 'tank_capacity': (O_TANK, 'return MaterialShapes.BLOCK.q(4);'),
    'tank_cadence': (O_TANK, 'nextUpdate = worldObj.rand.nextInt(6) + 5;'), 'tank_swap': (O_TANK, 'worldObj.rand.nextInt(5) == 0'), 'outlet_filter': (O_OUTLET, 'filter != stack.material ^ invertFilter'),
    'outlet_ray_start': (O_OUTLET, 'y - 0.125'), 'outlet_ray_end': (O_OUTLET, 'y + 0.125 - 4'), 'outlet_invert_key': (O_OUTLET, 'nbt.setBoolean("invert"'), 'outlet_filter_key': (O_OUTLET, 'nbt.setShort("filter"'),
    'crucible_pour_waste': (O_CRUCIBLE_TE, 'this.wasteStack, MaterialShapes.NUGGET.q(3)'), 'crucible_pour_front': (O_CRUCIBLE_TE, 'toCast, MaterialShapes.NUGGET.q(3)'),
    'smeltable_gate': (O_CRUCIBLE_UTIL, 'stack.material.smeltable != SmeltingBehavior.SMELTABLE'), 'recipe_channel': (O_CRAFTING, 'new ItemStack(ModBlocks.foundry_channel, 4)'),
    'recipe_tank': (O_CRAFTING, 'new ItemStack(ModBlocks.foundry_tank)'), 'recipe_outlet': (O_CRAFTING, 'new ItemStack(ModBlocks.foundry_outlet)'),
    'block_channel': (O_MODBLOCKS, 'foundry_channel = new FoundryChannel()'), 'block_tank': (O_MODBLOCKS, 'foundry_tank = new FoundryTank()'), 'block_outlet': (O_MODBLOCKS, 'foundry_outlet = new FoundryOutlet()'),
}
# Expected figures of the handoff and the task book (every value is also computed from the sources).
EXPECTED = dict(nugget=8, ingot=72, block=648, channel_capacity=144, tank_capacity=2592, channel_cadence=5, tank_cadence=(5, 10), pour_quanta=24, pour_range=6, hardness=5.0, resistance=10.0,
                language_keys=6, deferred_entries=106, recipes=3)
KNOWN_DIFFERENCES = {
    'copy_tool': 'the outlet\'s getSettings / pasteSettings (TileEntityFoundryOutlet.java:128-152) are not ported: NEO registers no settings / copy tool item (no caller of ICopiable outside the dummyable forwarding and GameTests)',
    'particles': 'the pouring particle packets (TileEntityFoundryOutlet.java:88-102, TileEntityCrucible.java) and the soot pollution and contact damage are not ported (G10A D10; GOAL27C.md "不做")',
    'slag_tap': 'the slag tap (CraftingManager.java:927) and flowing slag are not ported',
    'basin_and_large_molds': 'the foundry basin and the large molds are Goal 27D (FoundryBasin refuses flow, FoundryBasin.java:83-84)',
    'tank_walls': 'the tank is a static hollow basin model: the connected-wall merging and the upper / outlet side textures of RenderFoundryTank are not reproduced (main-notes.md decision 6)',
    'hardness': 'the three new blocks use the original hardness 5.0 and resistance 10.0 (ModBlocks.java:1772-1774); NEO\'s existing foundry_mold keeps its local 0.6',
    'inside_ray': 'crucible spouts only: a pour ray that starts inside the acceptor\'s collision shape counts as hitting the DOWN face (1.7.10 World.func_147447_a checks the start block first; TileEntityCrucible:169/209 -> CrucibleUtil.tryPourStack:93 passes mop.sideHit), so a channel or tank at the crucible\'s own level under a spout refuses the pour and must be placed one level lower; an outlet passes ForgeDirection.UP to its target whatever face the ray hit (TileEntityFoundryOutlet.java:70 and :85), so an outlet directly above a tank pours',
    'safe_mode_only': 'CrucibleUtil ports only the safe-mode pourFullStack the crucible calls; pourSingleStack and the spill branch are not ported (the crucible is the only caller)',
}
RECIPE_ROW = re.compile(r'(addRecipeAuto|addShapelessAuto)\(new ItemStack\(ModBlocks\.(foundry_(?:channel|tank|outlet))(?:, (\d+))?\), new Object\[\] \{ (.*?) \}\);')

# 27A ones the receipt carries forward under a new heading.
CARRIED_REPINS = 'repinned_since_'


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal27c release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 221 dirty or planned files) when it reproduces the baseline hash, else the blob at the start
    commit (with CRLF where the working tree had it); None when nothing reproduces the baseline hash."""
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
    """The Goal27C start hash of a frozen path: baseline files, or for a build/ record (Git-ignored, so baseline files does not list it) the hash the goal27b receipt
    records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal27b packager protected (built there from the Goal21A..Goal26D starts and receipts and the goal27b start), plus every path the goal27b receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (goal21a..goal26d) and every release file of the frozen start (the goal27b package
    included). The records that already drifted (the older drift: the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes)
    are pinned at their Goal27C start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal27b packager set at its Goal27B start hash, for the records that changed between the starts."""
    goal27b_start = read(GOAL27B_BASELINE)
    out = dict(goal27b_protected_paths(goal27b_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal27b receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal27b_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    assert all(p.endswith('-ACCEPTANCE.md') for p in repinned), 'A non-checklist pin changed between the Goal27B and Goal27C starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal27b_start):
    """{path: {receipts, start_sha256, goal27b_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal27b receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal27b receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21..26 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal27b '
                           'receipt does not hash it. Frozen at the Goal27C start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal27b) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal27b package; the goal27b receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal27b '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal27b_start_sha256=goal27b_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal27b_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def recompile_equal(name, previous_bytes, new_bytes):
    """True when the previous class bytes, patched in one of the directions RECOMPILE_ONLY allows (every pattern occurring exactly once), equal the new class bytes."""
    for pairs in RECOMPILE_ONLY[name]:
        patched = previous_bytes
        if any(patched.count(a) != 1 for a, b in pairs): continue
        for a, b in pairs: patched = patched.replace(a, b)
        if patched == new_bytes: return True
    return False


def scope_text(tests, total_tests):
    return (f'Goal27C (the third batch of Goal 27: the foundry channel, storage basin and outlet): the shared ICrucibleAcceptor pour/flow interface; the foundry channel, foundry storage basin (tank) and '
            f'foundry outlet (red-stone and scrap-filter controls) with their block entities, a foundry node network, crucible pouring into any acceptor, foundry_mold accepting pours and flows, '
            f'data-generated block models and a client renderer for molten levels and the foundry_mold\'s mold and cast; {tests} FoundryChannelGameTests ({total_tests} GameTests in total, one batch per '
            f'test). Gameplay impact: the crucible no longer has to sit right above a mold: its spouts pour into channels, tanks or molds; channels carry molten metal sideways into molds and outlets; '
            f'outlets pour it down into molds, channels or tanks; tanks buffer up to four blocks of metal and release it downward or through outlets; outlets can be '
            f'closed by redstone (or inverted) and filtered by scraps; shovels recover scraps; molten levels and the mold\'s contents are drawn.')




def group(p, imported):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA or p in OPTIONAL_JAVA: return 'production'
    if p in imported: return 'production-resource-imported'
    if p == ZH_INPUT: return 'language'
    if p in GENERATED_MODIFIED or GENERATED_ADDED.fullmatch(p) or GENERATED_MOLD.fullmatch(p) or GENERATED_TAGS.fullmatch(p): return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p == THREAD_PROMPTS: return 'planning-session'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records'
    return None


def owner_of(p):
    """goal27c, except the planning-session edit of GOAL27-THREAD-PROMPTS.md (a separate session, after the 27C freeze)."""
    return PLANNING_OWNER if p == THREAD_PROMPTS else OWNER


def strip_noise(text):
    """Text without block comments, full-line comments, imports and blank lines (for comparing code outside the methods a batch may change)."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return '\n'.join(l.rstrip() for l in text.split('\n') if l.strip() and not l.lstrip().startswith('//') and not l.startswith('import '))


def cut_methods(text, header_pattern):
    """The text without every method (header and brace-balanced body) whose header line matches `header_pattern`; the count is not reported."""
    rx = re.compile(header_pattern)
    while True:
        m = rx.search(text)
        if not m: return text
        j = text.find('{', m.start())  # the header line of a match ends in its own opening brace
        if j < 0: return text
        depth = 0
        for k in range(j, len(text)):
            if text[k] == '{': depth += 1
            elif text[k] == '}':
                depth -= 1
                if depth == 0: break
        text = text[:m.start()] + text[k+1:]


def stray_removals(removed, added):
    """Removed lines that no added line extends (a removed line `x;` or `x,` re-added as `x` plus more is a benign terminator change; blank and comment lines are ignored)."""
    gone = []
    for line in removed:
        core = line.strip().rstrip(';,{ ')
        if is_comment(line) or not core: continue
        if not any(core in a for a in added): gone.append(line.strip()[:90])
    return gone


def original_lang(text):
    return {k: v for k, _, v in (l.partition('=') for l in text.split('\n') if '=' in l and not l.startswith('#'))}




def recipe_item(token):
    """The NEO item id of an item token in the original CraftingManager foundry rows (firebrick ingot, stone slab, steel ingot / plate, the foundry channel)."""
    token = token.strip()
    table = {'ModItems.ingot_firebrick': 'hbmsntm:ingot_firebrick', 'Blocks.stone_slab': 'minecraft:stone_slab', 'STEEL.ingot()': 'hbmsntm:ingot_steel', 'STEEL.plate()': 'hbmsntm:plate_steel'}
    if token in table: return table[token]
    m = re.fullmatch(r'ModBlocks\.(foundry_\w+)', token)
    return 'hbmsntm:'+m.group(1) if m else None


def original_recipes(text):
    """{block: dict(type, count, pattern, key | ingredients)} of the foundry channel / tank / outlet rows of the original CraftingManager (items mapped to NEO ids)."""
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
    goal27b_start = read(GOAL27B_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal27C commits nothing): HEAD 690ce8c0 (the 2026-10-26 push of 27A and 27B,
    # = origin/master) on the Goal 27 planning commit 71c2f660 on the Goal 26 close-out 0786697d, with the 2 status lines of the planning-document edits made after the push.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(START_PREFIX), 'The frozen start is not on the 2026-10-26 push commit 690ce8c0'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 27' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the Goal 27 push commit'
    status_lines = base['target_status'].splitlines()
    assert len(status_lines) == START_STATUS_LINES and START_STATUS.read_text(encoding='utf-8').splitlines() == status_lines and {l[3:] for l in status_lines} == {THREAD_PROMPTS, TASK_BOOK}, \
        f'The frozen start is not the {START_STATUS_LINES} status lines of the post-push planning edits (GOAL27-THREAD-PROMPTS.md, GOAL27C.md): baseline target_status / start_status.txt'
    assert base['target_parent'].startswith(PLANNING_PREFIX) and base['origin_master'] == start_head, 'The start commit is not origin/master on the Goal 27 planning commit 71c2f660'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal27b receipt records another original commit than the frozen start'
    assert prior_receipt['target_start_commit'] == prior_receipt['target_head_at_packaging'] == base['target_parent'], \
        'The goal27b package was not built on the Goal 27 planning commit (the parent of this start commit)'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal27C (the Goal27C delivery stays uncommitted until the Goal 27 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2)}
    assert chain[1].startswith(PLANNING_PREFIX) and chain[2].startswith(GOAL26_CLOSEOUT), 'NEO HEAD~1..2 are not the Goal 27 planning commit 71c2f660 and the Goal 26 close-out 0786697d: '+str(chain)
    committed_files = [l for l in git_ro(ROOT, 'show', '--name-only', '--format=', start_head).splitlines() if l.strip()]
    assert committed_files and not any(p.startswith('build/') for p in committed_files), 'The start commit is empty or holds build/ files'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and '27A and 27B' in base['start_content']['committed'], 'Baseline start content differs (expected the committed 27A and 27B deliveries)'
    assert set(base['older_receipt_protected_paths']) == OLDER_RECEIPTS, 'Baseline older receipts differ'
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
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal27b generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_freeze']

    # The goal27a and goal27b deliveries were uncommitted when their receipts were written; the start commit holds them: every goal27b receipt changed file that the receipt hashes
    # (not a shared record it lists as not hashed) must have exactly the receipt's after-hash at this start, and be in the start commit.
    delivery_changed = {e['path']: e for e in prior_receipt['changed_files']}
    delivery_differs = sorted(p for p, e in delivery_changed.items() if base['files'].get(p) != e['after_sha256'])
    assert all(p in prior_receipt['records_not_hashed'] for p in delivery_differs), 'A Goal27B delivery file other than a record the goal27b receipt does not hash differs from its receipt after-hash at the Goal27C start: '+str(
        [p for p in delivery_differs if p not in prior_receipt['records_not_hashed']])
    not_in_commit = sorted(p for p in delivery_changed if p not in committed_files)
    assert not not_in_commit, 'Goal27B delivery files not in the start commit 690ce8c0: '+str(not_in_commit[:6])
    dirty = {}
    for line in START_HASHES.read_text(encoding='utf-8').splitlines():
        if line.strip():
            h, p = line.split(None, 1)
            dirty[p.strip().lstrip('*')] = h
    assert set(dirty) == {THREAD_PROMPTS, TASK_BOOK} and all(base['files'].get(p) == h for p, h in dirty.items()), 'start_hashes.txt is not the two post-push planning edits at their baseline hashes'
    frozen_27b = prior_receipt['concurrent_session']['frozen_planning_documents']
    planning_edits = {p: dict(owner=owner_of(p), receipt_goal27b_sha256=frozen_27b.get(p, {}).get('current_sha256'), start_sha256=base['files'][p], current_sha256=sha(ROOT/p),
                              note=('Edited by the Goal 27 planning session (a separate session, not part of this batch) after the 27C freeze: it deleted the round-pacing paragraphs of the 27C and 27D prompts '
                                    '(main-notes.md "Concurrent planning-session edit"). May differ from the start hash; never restored; not hashed by the receipt.' if p == THREAD_PROMPTS
                                    else 'Post-push planning edit of 2026-10-26 (uncommitted at the start, in no receipt); this batch\'s task book and delivery record, hashed by the new receipt.'))
                      for p in (THREAD_PROMPTS, TASK_BOOK)}
    uncommitted_start = dict(
        status_entries=len(status_lines), status=status_lines, description='the post-push planning-document edits of 2026-10-26 (GOAL27-THREAD-PROMPTS.md, GOAL27C.md); the 27A and 27B deliveries are committed in the start commit',
        committed_delivery=dict(commit=start_head[:8], parent=base['target_parent'][:8], files_in_commit=len(committed_files), goal27b_receipt=PREVIOUS_RECEIPT.relative_to(ROOT).as_posix(),
                                receipt_changed_files=len(delivery_changed), equal_to_receipt_after_sha256=sum(1 for p, e in delivery_changed.items() if base['files'].get(p) == e['after_sha256']),
                                shared_records_differing_from_receipt_after_sha256={p: dict(receipt_after_sha256=delivery_changed[p]['after_sha256'], start_sha256=base['files'][p], current_sha256=sha(ROOT/p))
                                                                                    for p in delivery_differs},
                                note='The goal27a and goal27b receipts were written while the 27A and 27B deliveries were uncommitted (201 status lines at the 27B start); 690ce8c0 commits and pushes them '
                                     '(origin/master). Their files are owned by goal27a / goal27b; a record the goal27b receipt does not hash (README, features, UPSTREAM-REVIEWS, LOCALIZATION, GOAL27.md) may differ from '
                                     'the receipt after-hash because the commit session added the push line.'),
        planning_edits=planning_edits)
    planning_session_edit = dict(path=THREAD_PROMPTS, owner=PLANNING_OWNER, start_sha256=base['files'][THREAD_PROMPTS], current_sha256=sha(ROOT/THREAD_PROMPTS),
                                 changed_since_start=base['files'][THREAD_PROMPTS] != sha(ROOT/THREAD_PROMPTS), receipt_goal27b_sha256=frozen_27b.get(THREAD_PROMPTS, {}).get('current_sha256'),
                                 note=planning_edits[THREAD_PROMPTS]['note'])


    # 2. Previous deliveries: the goal27b package, every old release file and the protected evidence; build/libs at the freeze is the goal27b package itself.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the freeze is not the goal27b package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal27b receipt list + the goal27b package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal27b receipt count + the goal27b release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal27b receipt'
    assert not base['previous_receipt_evidence_drift'], 'The goal27b receipt records evidence drift at the start: '+str(list(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal27b_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal27b receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal27c (GOAL27-THREAD-PROMPTS.md to the planning session). Everything else equals its start hash.
    changes = changed_since_start(base)
    imported = {p for p in changes if TEXTURE_PATTERN.fullmatch(p)}
    optional_changed = [p for p in OPTIONAL_JAVA if p in changes]
    modified_java = MODIFIED_JAVA + optional_changed
    production_java = NEW_JAVA + modified_java
    older_gametests_frozen = sorted(p for p in base['files'] if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p not in OPTIONAL_JAVA)
    unassigned = sorted(p for p in changes if group(p, imported) is None)
    need(not unassigned, 'Path changed since the Goal27C start that the owner table does not list (production outside the listed new and modified Java files and FoundryChannelGameTests, a hand-written '
         'resource other than the foundry textures and lava_gray, a generated file other than the stamp, en_us.json, the pickaxe tag and the foundry blockstates / models / recipes / advancements / loot tables, '
         'a protected or frozen record, an older tool, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal 26 and earlier records, the Goal27A / Goal27B records, GOAL27D.md or SURVIVAL-PLAYABILITY.md changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal27C start: '+str(deleted)
    for p in MODIFIED_JAVA + GENERATED_MODIFIED + [ZH_INPUT, TASK_BOOK] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + REQUIRED_TEXTURES + REQUIRED_GENERATED + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    block_models = {n: sorted(p for p in changes if re.fullmatch(re.escape(GENERATED_ROOT)+r'assets/hbmsntm/models/block/'+n+r'[a-z_]*\.json', p)) for n in BLOCK_NAMES}
    need(all(block_models.values()), 'no generated block model assets/hbmsntm/models/block/<block>*.json yet for: '+str([n for n, v in block_models.items() if not v]))
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(production_java) - imported - {ZH_INPUT})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified (+ optional) and {len(NEW_JAVA)} new Java files, the foundry textures / lava_gray and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools = OLD_TOOLS_FROZEN + sorted(p for p in base['files'] if p.startswith(FROZEN_TOOL_DIRS))
    frozen_tools_changed = sorted(p for p in frozen_tools if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (package_goal27b.py, verify_goal27b_crucible_alloys.py, package_goal27a.py, verify_goal27a_material_system.py, the casting '
         'regression wrapper and compat, the Goal 26C old-suite wrapper, the casting regressions and their folders): '+str(frozen_tools_changed))
    jei_classes = sorted(p for p in base['files'] if p.startswith(J+'handler/jei/'))
    unchanged_bad = [p for p in UNCHANGED_JAVA + older_gametests_frozen + jei_classes if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed (Mats / MaterialEntries / MatDistribution / MaterialShapes / NTMMaterial, CrucibleRecipes / CrucibleRecipe / '
         'CopperCastingRecipes / SerializableRecipe / ShredderRecipes / AnvilRecipes, CopperScrapsItem, NtmItems, UniNodespace / NodeNet / GenNode / INetworkProvider, every handler/jei class, every other '
         'GameTest class): '+str(unchanged_bad))
    goal27_now = sha(ROOT/GOAL27_RECORD)
    concurrent_record = dict(sessions=[PLANNING_OWNER], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository before the start. The batch ran under the main '
                                                           'agent (production review, the migration/ records) with a production builder (the 27C Java, runData), a GameTest verifier (FoundryChannelGameTests, '
                                                           'verify_goal27c_foundry.py, runData and the GameTest server), a reviewer and this packaging verifier (the packager, the final runner, the casting-regression '
                                                           'attribution) working in the same checkout; each wrote only its named files (the scope snapshots of the verifiers are indexed as evidence). The Goal 27 '
                                                           'planning session edited GOAL27-THREAD-PROMPTS.md after the freeze (planning_session_edit).',
                             goal27_md=dict(start_sha256=base['files'][GOAL27_RECORD], current_sha256=goal27_now, owners=[OWNER]),
                             planning_session_edit=planning_session_edit,
                             frozen_planning_documents={p: dict(start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p) if (ROOT/p).is_file() else None) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p, imported), owner=owner_of(p), owners=[owner_of(p)], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal27C takes no new snapshot)'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-aee05a40f10f snapshot changed'
    production_changed = [p for p in production_java if p in changes]

    # The modified production files keep their start line endings (reported); new Java files are not mixed.
    start_text, line_endings = {}, {}
    for p in modified_java:
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
    for p in modified_java:
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
    # MachineCrucibleBlockEntity: only pour(Direction, List) and the imports (and comments) change.
    if CRUCIBLE_BE in start_text:
        cut = lambda t: strip_noise(cut_methods(t, r'private void pour\(Direction\b[^\n]*'))
        content_rules[CRUCIBLE_BE] = cut(neo_text(CRUCIBLE_BE)) == cut(text_of_start(CRUCIBLE_BE))
        need(content_rules[CRUCIBLE_BE], f'{CRUCIBLE_BE} differs from the start outside pour(Direction, List), its imports and comments')
    # FoundryMoldBlockEntity: only canAccept is added and pour may call it; save / load, limits and cooloff are the start's.
    if MOLD_BE in start_text:
        cut = lambda t: strip_noise(cut_methods(t, r'public int pour\([^\n]*|(?:public\s+)?boolean canAccept\w*\([^\n]*'))
        content_rules[MOLD_BE] = cut(neo_text(MOLD_BE)) == cut(text_of_start(MOLD_BE)) and bool(re.search(r'boolean canAccept\w*\(', neo_text(MOLD_BE)))
        need(content_rules[MOLD_BE], f'{MOLD_BE} differs from the start beyond adding canAccept (and the pour that may call it), or has no canAccept method')
    # FoundryMoldBlock: the class declaration gains `implements ICrucibleAcceptor` and the four interface methods; nothing else of the start is removed.
    if MOLD_BLOCK in start_text:
        gone = [l.strip() for l in removed_lines[MOLD_BLOCK] if not is_comment(l)]
        content_rules[MOLD_BLOCK] = len(gone) <= 1 and all(re.match(r'(?:public\s+)?(?:final\s+)?class\s', l) for l in gone) and 'implements' in neo_text(MOLD_BLOCK) and 'ICrucibleAcceptor' in neo_text(MOLD_BLOCK)
        need(content_rules[MOLD_BLOCK], f'{MOLD_BLOCK} removes start lines other than its class declaration or does not implement ICrucibleAcceptor: {gone[:3]}')
    # The registration / provider files: no start line removed except a terminator or a call chain extended by an added line; the single-line registrations carry only foundry additions.
    for p in modified_java:
        if p not in removed_lines or p in (CRUCIBLE_BE, MOLD_BE, MOLD_BLOCK): continue
        stray = stray_removals(removed_lines[p], added_lines[p])
        content_rules[p] = not stray
        need(not stray, f'{p} removes start lines that no added line extends: {stray[:4]}')
    for p in (NTM_BLOCKS, NTM_BE_TYPES, CREATIVE_TABS, LOOT_PROVIDER, TAG_PROVIDER, LANG_PROVIDER):
        if p not in added_lines: continue
        odd = [l.strip()[:90] for l in added_lines[p] if not is_comment(l) and not l.lstrip().startswith('import ') and l.strip() not in ('}', ');', '{', ')')
               and not re.search(r'(?i)foundry|channel|tank|outlet|filter|invert|crucible|Builder\.of\(|\.build\(null\)|^\s*\(\) ->', l)]
        content_rules[p+'#added'] = not odd
        need(not odd, f'{p} adds lines that are not foundry registrations: {odd[:4]}')

    # 4. The foundry casting against the original (EXPECTED holds the handoff figures; every value is computed from the sources; the NEO side is checked with tolerant source patterns, the
    # behaviour itself is the job of verify_goal27c_foundry.py and the GameTests).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    facts, bad = {}, []

    def fact(key, value, expected=None, ok=None):
        facts[key] = value if expected is None else dict(value=value, expected=expected)
        if ok is None: ok = expected is None or value == expected
        if not ok: bad.append(key)

    o = {path: original_text(path) for path in O_SOURCES}
    n_shapes = neo_text(J+'inventory/material/MaterialShapes.java')
    shape_q = lambda text: {'NUGGET': int(re.search(r'NUGGET = new MaterialShapes\((\d+),', text).group(1))}
    def quanta(text):
        q = shape_q(text)
        q['INGOT'] = q['NUGGET']*int(re.search(r'INGOT = new MaterialShapes\(NUGGET\.quantity \* (\d+),', text).group(1))
        q['BLOCK'] = q['INGOT']*int(re.search(r'BLOCK = new MaterialShapes\(INGOT\.quantity \* (\d+),', text).group(1))
        return q
    o_q, n_q = quanta(o[O_SHAPES]), quanta(n_shapes)
    fact('quanta', dict(nugget=n_q['NUGGET'], ingot=n_q['INGOT'], block=n_q['BLOCK']), dict(nugget=EXPECTED['nugget'], ingot=EXPECTED['ingot'], block=EXPECTED['block']), ok=o_q == n_q
         and (o_q['NUGGET'], o_q['INGOT'], o_q['BLOCK']) == (EXPECTED['nugget'], EXPECTED['ingot'], EXPECTED['block']))
    capacity = lambda text: (lambda m: o_q[m.group(1)]*int(m.group(2)))(re.search(r'return MaterialShapes\.(\w+)\.q\((\d+)\);', body_of(text, 'public int getCapacity()')))
    fact('capacities', dict(channel=capacity(o[O_CHANNEL]), tank=capacity(o[O_TANK])), dict(channel=EXPECTED['channel_capacity'], tank=EXPECTED['tank_capacity']))
    outlet_capacity = re.search(r'return (\d+);', body_of(o[O_OUTLET], 'public int getCapacity()'))
    fact('outlet_capacity', int(outlet_capacity.group(1)) if outlet_capacity else None, 0)
    tank_cadence = re.search(r'nextUpdate = worldObj\.rand\.nextInt\((\d+)\) \+ (\d+);', o[O_TANK])
    cadence = dict(channel=sorted(set(re.findall(r'nextUpdate = (\d+);', o[O_CHANNEL]))), channel_assignments=len(re.findall(r'nextUpdate = \d+;', o[O_CHANNEL])),
                   tank=[int(tank_cadence.group(2)), int(tank_cadence.group(2)) + int(tank_cadence.group(1)) - 1] if tank_cadence else None)
    fact('cadence', cadence, None, ok=cadence['channel'] == [str(EXPECTED['channel_cadence'])] and cadence['channel_assignments'] == 2 and cadence['tank'] == list(EXPECTED['tank_cadence']))
    fact('swap_rules', dict(channel='nextInt(5) == 0 || this.amount == 1' in o[O_CHANNEL], tank_random='worldObj.rand.nextInt(5) == 0' in o[O_TANK], tank_single_quantum='amount == 1' in o[O_TANK]), dict(channel=True, tank_random=True, tank_single_quantum=False))
    fact('outlet_ray', dict(start=o[O_OUTLET].count('Vec3.createVectorHelper(x + 0.5, y - 0.125, z + 0.5)'), end=o[O_OUTLET].count('Vec3.createVectorHelper(x + 0.5, y + 0.125 - 4, z + 0.5)'),
                            filter_expression=o[O_OUTLET].count('filter != null && (filter != stack.material ^ invertFilter)'), back_side='side != ForgeDirection.getOrientation(this.getBlockMetadata()).getOpposite()' in o[O_OUTLET],
                            pours_up=o[O_OUTLET].count('ForgeDirection.UP, stack)') >= 1), dict(start=2, end=2, filter_expression=1, back_side=True, pours_up=True))
    pours = re.findall(r'xCoord \+ 0\.5D \+ dir\.offsetX \* (1\.875D), yCoord \+ (0\.25D), zCoord \+ 0\.5D \+ dir\.offsetZ \* 1\.875D, (\d+), (true), [^,]+, MaterialShapes\.NUGGET\.q\((\d+)\)', o[O_CRUCIBLE_TE])
    fact('crucible_pour', dict(rows=len(pours), offsets=sorted(set(pours)), quanta=o_q['NUGGET']*3), dict(rows=2, offsets=[('1.875D', '0.25D', str(EXPECTED['pour_range']), 'true', '3')], quanta=EXPECTED['pour_quanta']))
    fact('smeltable_gate', 'stack.material.smeltable != SmeltingBehavior.SMELTABLE' in o[O_CRUCIBLE_UTIL], True)
    interface_methods = sorted(re.findall(r'public \w+ (canAcceptPartialPour|pour|canAcceptPartialFlow|flow)\(', o[O_ACCEPTOR]))
    fact('acceptor_interface', interface_methods, ['canAcceptPartialFlow', 'canAcceptPartialPour', 'flow', 'pour'])
    fact('save_keys', dict(base=sorted(set(re.findall(r'nbt\.set\w+\("(type|amount)"', o[O_BASE]))), channel=re.findall(r'nbt\.set\w+\("(flow)"', o[O_CHANNEL]),
                           outlet=sorted(set(re.findall(r'nbt\.set\w+\("(invert|invertFilter|filter)"', o[O_OUTLET])))),
         dict(base=['amount', 'type'], channel=['flow'], outlet=['filter', 'invert', 'invertFilter']))
    blocks_original = {m[0]: (float(m[1]), float(m[2])) for m in re.findall(r'foundry_(channel|tank|outlet) = new \w+\(\)\.setBlockName\("[a-z_]+"\)\.setHardness\(([\d.]+)F\)\.setResistance\(([\d.]+)F\)', o[O_MODBLOCKS])}
    fact('block_strength', blocks_original, {n: (EXPECTED['hardness'], EXPECTED['resistance']) for n in ('channel', 'tank', 'outlet')})
    # The three crafting recipes: the original rows (CraftingManager.java:924-926) against the generated NEO recipe JSON.
    o_recipes = original_recipes(o[O_CRAFTING])
    fact('recipes_original', {n: o_recipes.get(n) for n in BLOCK_NAMES}, None, ok=sorted(o_recipes) == sorted(BLOCK_NAMES) and o_recipes['foundry_channel']['count'] == 4 and o_recipes['foundry_tank']['count'] == 1
         and o_recipes['foundry_outlet']['type'] == 'minecraft:crafting_shapeless' and all(None not in (list(r.get('key', {}).values()) + r.get('ingredients', [])) for r in o_recipes.values()))
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
    # NEO sources (tolerant patterns): the constants and keys the handoff dictates; the behaviour is the verifier's V2 and the GameTests.
    code = lambda p: strip_java_comments(neo_text(p))
    fact('neo_capacities', dict(channel='MaterialShapes.INGOT.q(2)' in code(CHANNEL_BE), tank='MaterialShapes.BLOCK.q(4)' in code(TANK_BE)), dict(channel=True, tank=True))
    fact('neo_cadence', dict(channel=bool(re.search(r'nextUpdate\s*=\s*5\s*;', code(CHANNEL_BE))), tank=bool(re.search(r'nextInt\(\s*6\s*\)\s*\+\s*5', code(TANK_BE)))), dict(channel=True, tank=True))
    fact('neo_swap_rules', dict(channel=bool(re.search(r'nextInt\(\s*5\s*\)\s*==\s*0', code(CHANNEL_BE))) and bool(re.search(r'amount\s*==\s*1', code(CHANNEL_BE))),
                                tank=bool(re.search(r'nextInt\(\s*5\s*\)\s*==\s*0', code(TANK_BE)))), dict(channel=True, tank=True))
    fact('neo_save_keys', dict(base=all(f'"{k}"' in code(BASE_BE) for k in ('type', 'amount')), channel='"flow"' in code(CHANNEL_BE), outlet=all(f'"{k}"' in code(OUTLET_BE) for k in ('invert', 'invertFilter', 'filter'))),
         dict(base=True, channel=True, outlet=True))
    fact('neo_interface', dict(methods=all(m in code(ACCEPTOR) for m in ('canAcceptPartialPour', 'pour(', 'canAcceptPartialFlow', 'flow(')), blocks=all('ICrucibleAcceptor' in code(p) for p in (CHANNEL_BLOCK, TANK_BLOCK, OUTLET_BLOCK, MOLD_BLOCK)),
                               base_entity='ICrucibleAcceptor' in code(BASE_BE)), dict(methods=True, blocks=True, base_entity=True))
    fact('neo_crucible_pours_through_util', dict(call='CrucibleUtil.pourFullStack' in code(CRUCIBLE_BE), offsets='1.875' in code(CRUCIBLE_BE) and '0.25' in code(CRUCIBLE_BE), quanta='POUR_QUANTA' in code(CRUCIBLE_BE) or 'q(3)' in code(CRUCIBLE_BE),
                                                 smeltable='SMELTABLE' in code(CRUCIBLE_UTIL)), dict(call=True, offsets=True, quanta=True, smeltable=True))
    fact('neo_blocks_registered', dict(ids=all(f'"{n}"' in code(NTM_BLOCKS) for n in BLOCK_NAMES), strength=sum(1 for l in added_lines.get(NTM_BLOCKS, []) if 'strength(5.0F, 10.0F)' in l), types=all(f'"{n}"' in code(NTM_BE_TYPES) for n in BLOCK_NAMES)),
         None, ok=all(f'"{n}"' in code(NTM_BLOCKS) for n in BLOCK_NAMES) and all(f'"{n}"' in code(NTM_BE_TYPES) for n in BLOCK_NAMES))
    # Client isolation: the renderer is referenced only from ClientProxy; no common class (block entities, util, interface, node network, blocks) names it or the render package.
    common_classes = [ACCEPTOR, CRUCIBLE_UTIL, BASE_BE, CHANNEL_BE, TANK_BE, OUTLET_BE, CHANNEL_BLOCK, TANK_BLOCK, OUTLET_BLOCK, NETWORK, NETWORK_PROVIDER, NODE, CRUCIBLE_BE, MOLD_BE, MOLD_BLOCK]
    renderer_users = sorted(p for p in common_classes if (ROOT/p).is_file() and re.search(r'RenderFoundry|net\.minecraft\.client|com\.hbm\.render\.|mezz\.jei', strip_java_comments(neo_text(p))))
    fact('client_isolation', dict(client_references_in_common_classes=renderer_users, client_proxy_registers_it='RenderFoundry' in code(CLIENT_PROXY),
                                  renderer_referenced_elsewhere=sorted(p for p in production_java if p not in (RENDERER, CLIENT_PROXY, RESOURCE_MANAGER) and (ROOT/p).is_file() and p not in common_classes
                                                                       and 'RenderFoundry' in strip_java_comments(neo_text(p)))), None,
         ok=not renderer_users and 'RenderFoundry' in code(CLIENT_PROXY))
    facts['original_references'] = original_refs
    need(not bad, 'foundry-casting facts differ from the original or the handoff figures (or the NEO source / generated file is missing or its text differs): '+', '.join(
        f'{k}={json.dumps(facts[k], ensure_ascii=False)[:200]}' for k in bad))
    # The materials/reachability record (the main agent's; pending until written): 27C adds no recipe or material, it must say which blocks and ingredients are reachable.
    ledger = read(ROOT/LEDGER) if (ROOT/LEDGER).is_file() else None
    if need(ledger is not None, 'record missing: '+LEDGER):
        need(ledger.get('goal') == '27C' and len(ledger.get('blocks') or []) == 3, f'{LEDGER} is not the Goal 27C ledger with 3 blocks')

    # 5. Resources: the byte imports (original worktree file and stored blob), against migration/goal27c-resource-ownership.json.
    ownership = read(ROOT/RESOURCE_OWNERSHIP) if (ROOT/RESOURCE_OWNERSHIP).is_file() else None

    def original_texture(target):
        """The original path of an imported NEO texture: block/foundry_x.png <- textures/blocks/foundry_x.png, models/machines/lava_gray.png <- textures/models/machines/lava_gray.png."""
        rel = target[len(TEXTURE_ROOT):]
        return O_RES+'textures/'+('blocks/'+rel[len('block/'):] if rel.startswith('block/') else rel)

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

    # 6. features.json: ONE new group foundry-casting; every group keeps status and reviewed_source_commit; only crucible-alloying (and the new group) may change notes / target_paths / target_watch.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES - {NEW_FEATURE} <= set(start_features) and NEW_FEATURE not in start_features, 'The start mapping does not hold the groups of 24B-27B or already holds foundry-casting'
    may_change = lambda i: i in NOTES_MAY_CHANGE or i == NEW_FEATURE
    need(set(by_id) == set(start_features) | {NEW_FEATURE}, 'features.json group ids are not the start ids + foundry-casting: '+str(sorted(set(by_id) ^ (set(start_features) | {NEW_FEATURE}))))
    new_group = by_id.get(NEW_FEATURE)
    feature_sources = [O_CHANNEL, O_TANK, O_OUTLET, O_BASE, O_ACCEPTOR, O_CRUCIBLE_UTIL, O_CHANNEL_BLOCK, O_TANK_BLOCK, O_OUTLET_BLOCK]
    if need(new_group is not None, 'migration/features.json lacks the group '+NEW_FEATURE):
        need(new_group.get('status') == 'partial-unverified' and new_group.get('reviewed_source_commit') == SOURCE_HEAD, f'features.json group {NEW_FEATURE} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in feature_sources if not feature_matches(new_group, 'source', p)]
        need(not missing_source, f'features.json group {NEW_FEATURE} lists in neither source_paths nor source_watch: {missing_source}')
        absent = [p for p in new_group.get('source_paths', []) if not (SOURCE/p).is_file()]
        need(not absent, f'features.json group {NEW_FEATURE} source_paths missing in the original: {absent}')
        mapped_java = [p for p in NEW_JAVA if p != FOUNDRY_TESTS and not feature_matches(new_group, 'target', p)]
        need(not mapped_java, f'features.json group {NEW_FEATURE} does not map these new Java paths (target_paths / target_watch): {mapped_java[:4]}')
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    need(all(may_change(i) for i in notes_changed), 'features.json groups whose notes changed beyond crucible-alloying: '+str([i for i in notes_changed if not may_change(i)]))
    paths_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('target_paths') != start_features[i].get('target_paths'))
    need(all(may_change(i) for i in paths_changed), 'features.json groups whose target_paths changed beyond crucible-alloying: '+str([i for i in paths_changed if not may_change(i)]))
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in ('notes', 'target_watch', 'target_paths')} !=
                          {k: v for k, v in start_features[i].items() if k not in ('notes', 'target_watch', 'target_paths')})
    need(not shrunk and not other_fields, f'features.json previous groups lost target_watch entries {shrunk} or changed other fields {other_fields}')
    watch_grown = sorted(i for i, f in by_id.items() if i in start_features and set(f.get('target_watch', [])) - set(start_features[i].get('target_watch', [])))
    need(all(may_change(i) for i in watch_grown), 'features.json groups whose target_watch grew beyond crucible-alloying: '+str([i for i in watch_grown if not may_change(i)]))
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped; the main agent adds target_paths / target_watch to foundry-casting): '+str(unmapped[:6]))

    # 7. Language and the generated tree: the six keys (English generated, Chinese and the mapping by the main agent, upstream), the stamp must be current, the generated additions the foundry set.
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
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_delta = dict(added=sorted(KEYS), removed=[], changed=[])
    need(len(KEYS) == EXPECTED['language_keys'], f'expected new language keys: {len(KEYS)}, the handoff says {EXPECTED["language_keys"]}')
    need(en_delta == expected_delta, f'generated en_us.json delta is not the {len(KEYS)} new keys (no value changed): '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_delta, f'zh_cn.json delta is not the {len(KEYS)} new keys (all old values unchanged): '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_delta, f'zh_cn-map.json delta is not the {len(KEYS)} new entries (no old entry changed): '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal27b totals'
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal27b totals {totals} + {len(KEYS)}')
    map_kinds, start_kinds = dict(Counter(e.get('kind') for e in map_now.values())), dict(Counter(e.get('kind') for e in map_start.values()))
    expected_kinds = dict(start_kinds, upstream=start_kinds.get('upstream', 0) + len(KEYS))
    need(start_kinds == totals['zh_cn_map_by_kind'] and map_kinds == expected_kinds and map_kinds.get('deferred') == EXPECTED['deferred_entries'],
         f'mapping kinds are {map_kinds}, expected the goal27b kinds {totals["zh_cn_map_by_kind"]} + {len(KEYS)} upstream (deferred {EXPECTED["deferred_entries"]} unchanged)')
    need(all((map_now.get(k) or {}).get('kind') == 'upstream' for k in KEYS), 'mapping entries of the new keys are not kind upstream: '+str([k for k in KEYS if (map_now.get(k) or {}).get('kind') != 'upstream']))
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
         f'Generated resources changed since the start are not en_us.json, the tag files that gained the blocks (pickaxe.json required) and foundry_mold models: {generated_changed[:8]}')
    foundry_added = [p for p in generated_added if GENERATED_ADDED.fullmatch(GENERATED_ROOT+p)]
    need(foundry_added == generated_added, f'Generated additions other than the foundry channel / tank / outlet set: {sorted(set(generated_added) - set(foundry_added))[:6]}')
    advancements = {n: [p for p in generated_added if re.fullmatch(r'data/hbmsntm/advancement/recipes/[a-z]+/'+n+'\\.json', p)] for n in BLOCK_NAMES}
    need(all(len(v) == 1 for v in advancements.values()), 'generated recipe advancements: exactly one per block expected: '+str(advancements))
    for path in (v[0] for v in advancements.values() if v):
        adv = read(ROOT/(GENERATED_ROOT+path))
        need(adv.get('rewards') == {'recipes': ['hbmsntm:'+Path(path).stem]}, f'{path} does not reward its own recipe')
    need(len(stamp['generated']) == prior_receipt['generated_resource_count'] + len(generated_added), f'generated resource count {len(stamp["generated"])} is not the goal27b count {prior_receipt["generated_resource_count"]} + {len(generated_added)}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted([STAMP] + [GENERATED_ROOT+p for p in generated_added] + [GENERATED_ROOT+p for p in generated_changed])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, the stamp additions and the stamp changes: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))

    # 8. Evidence: GameTest log, audits, Gradle logs, diff, the final suite run, the verifier report, the casting attribution, compare and the batch's own scripts and records.
    evidence = {}
    gametest_line = gametest_count = None
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
    foundry_test_names = sorted(GAMETEST_METHOD.findall((ROOT/FOUNDRY_TESTS).read_text(encoding='utf-8'))) if (ROOT/FOUNDRY_TESTS).is_file() else []
    foundry_annotations = annotations(ROOT/FOUNDRY_TESTS) if (ROOT/FOUNDRY_TESTS).is_file() else 0
    need(bool(foundry_test_names) and foundry_annotations == len(foundry_test_names), f'{FOUNDRY_TESTS} holds {foundry_annotations} @GameTest annotations and {len(foundry_test_names)} parsed methods (or the file does not exist yet)')
    need(gametest_added == foundry_annotations, f'GameTest sources grew by {gametest_added} tests, FoundryChannelGameTests holds {foundry_annotations} (another GameTest class changed its test count, e.g. SmokeTestSupport?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in foundry_test_names), 'GameTest log lacks "[hbm-foundry] <name> passed" for: '+str([n for n in foundry_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries, audit_comparison = {}, {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal27c/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad_findings = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad_findings and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad_findings))
        # Unlike 27B this batch adds language keys and resources, so the info / review counts may differ from the previous receipt: recorded, not required equal.
        audit_comparison[key] = dict(previous=prior_receipt['audits'][key], now=audit['summary'], equal=audit['summary'] == prior_receipt['audits'][key])
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal27c/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if name == 'production-vs-start.diff':
            if (OUT/name).is_file() and (OUT/name).stat().st_size > 0: evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)  # judged below
            continue
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal27c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    named = list(START_EVIDENCE) + list(REVIEW_EVIDENCE)
    named += sorted(p.name for p in OUT.glob('handoff-*.md') if p.name not in named) + sorted(p.name for p in OUT.glob('*-report.md') if p.name not in named)
    for name in named:
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal27c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/FAIL_SET_DIFF).is_file(): evidence[(OUT/FAIL_SET_DIFF).relative_to(ROOT).as_posix()] = sha(OUT/FAIL_SET_DIFF)
    # The casting regressions (goal27a_casting_regression_run.py, unchanged wrapper): one record per suite in the final rerun's own directory; its transcript is hashed with it.
    casting = {}
    for suite in CASTING_SUITES:
        rec_path = CASTING_DIR/f'{suite}-compat.json'
        if not need(rec_path.is_file(), f'evidence missing: build/migration/goal27c/final/castingsuites/{suite}-compat.json (goal27a_casting_regression_run.py {suite}, redirected into final/ by run_final.py)'): continue
        rec = read(rec_path)
        transcript = ROOT/rec['transcript'] if rec.get('transcript') else None
        casting[suite] = dict(record=rec_path.relative_to(ROOT).as_posix(), exit=rec.get('exit'), mode=rec.get('mode'), blockers=rec.get('blockers'), stages=rec.get('stages'),
                              javac_errors_by_attribution=rec.get('javac_errors_by_attribution'), transcript=rec.get('transcript'))
        evidence[rec_path.relative_to(ROOT).as_posix()] = sha(rec_path)
        if need(transcript is not None and transcript.is_file(), f'{rec_path.name} names no existing transcript'): evidence[transcript.relative_to(ROOT).as_posix()] = sha(transcript)
    attribution = None
    if need((OUT/CASTING_ATTRIBUTION).is_file(), 'evidence missing: build/migration/goal27c/'+CASTING_ATTRIBUTION+' (casting_attribution.py, after the final rerun)'):
        att = read(OUT/CASTING_ATTRIBUTION)
        problems = []
        if att.get('mode') != 'compare' or att.get('missing_inputs'): problems.append(f'mode {att.get("mode")!r}, missing inputs {att.get("missing_inputs")}')
        if att.get('baseline_sha256') != sha(BASELINE) or att.get('tool_sha256') != sha(OUT/'casting_attribution.py'): problems.append('written by another baseline or another version of casting_attribution.py')
        if att.get('old_dir') != (GOAL27B_OUT/'final/castingsuites').relative_to(ROOT).as_posix() or att.get('new_dir') != CASTING_DIR.relative_to(ROOT).as_posix(): problems.append(f'compares {att.get("old_dir")} with {att.get("new_dir")}')
        if sorted(att.get('suites', {})) != sorted(CASTING_SUITES): problems.append('suites '+str(sorted(att.get('suites', {}))))
        for suite, entry in att.get('suites', {}).items():
            for side in ('old', 'new'):
                s = entry.get(side) or {}
                if not s.get('parse_matches_record'): problems.append(f'{suite} {side}: the parsed javac errors do not match the record')
                if side == 'new' and suite in casting and s.get('record_sha256') != sha(ROOT/casting[suite]['record']): problems.append(f'{suite}: the new record changed after the attribution')
            for e in entry.get('new_errors', []) + entry.get('moved', []):
                file = e.get('at', '').rsplit(':', 1)[0] if 'at' in e else (e.get('identity') or {}).get('file', '')
                if e.get('attribution') == 'unattributed': problems.append(f'{suite}: unattributed error {e.get("at") or e.get("identity")}')
                elif e.get('attribution') == '27C change' and file not in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed to a 27C change but the file did not change')
                elif e.get('attribution') == 'not 27C' and file in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed "not 27C" but the file changed')
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
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal27c/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in modified_java if p in changes]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal27c/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in modified_java if p in changes) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(p in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([p for p in listed_in_diff if p not in diff_text]))
    final = None
    # The suites of the goal27b final run plus the Goal27C verifier (the two casting regressions are in the goal27b set and run unchanged, redirected into final/).
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal27b final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal27C suite is already in the goal27b final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal27c/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal27b final set + the Goal27C verifier: '+str(sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal27c/'+VERIFY_REPORT+' (tools/migration/verify_goal27c_foundry.py report; the script does not exist yet or writes elsewhere)'):
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
        verifier_references = sorted(set(re.findall(r'(?:TileEntityFoundry\w+|TileEntityCrucible|CrucibleUtil|ICrucibleAcceptor|FoundryChannel|FoundryTank|FoundryOutlet|CraftingManager|MaterialShapes|ModBlocks)\.java:\d+(?:-\d+)?',
                                                json.dumps(report, ensure_ascii=False))))
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal27b compare target paths plus this batch's compare-inventory paths).
    cmp_prev = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal27b/compare.json differs from the goal27b receipt'
    prev_added = sorted(p for p in compare_paths(cmp_prev['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    prev_modified = sorted(p for p in compare_paths(cmp_prev['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(prev_added) | set(prev_modified) | set(own_target))
    expected_added = sorted(set(prev_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal27c/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-27b paths + the %d of this batch not already among them (%d compare-inventory paths changed)' % (
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
        for g in (NEW_FEATURE, 'crucible-alloying'):
            need(any(f.get('id') == g and f.get('state') == 'target-changed' for f in cmp['features']), f'{COMPARE} does not report {g} as target-changed')
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal27b (goal27b compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal27b_paths=len(prev_added) + len(prev_modified), goal27c_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-27B)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 9. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal27c or a recompile.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal27b) package (run the final build)')
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
            need(en_jar == zh_jar == expected_delta, 'JAR en_us.json / zh_cn.json differ from the previous package by something other than the six foundry keys: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
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
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the generated additions / changes (foundry blockstates, models, recipes, advancements, loot tables, en_us.json, the tags), '
             'zh_cn.json, the imported textures and META-INF/MANIFEST.MF are owned): '+str(unowned[:10]))
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in production_java if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) <= set(class_owners),
             'Changed Java sources and goal27c JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners))) + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == generated_entries, 'JAR non-class delta differs from the generated additions / changes + zh_cn.json + the imported textures: extra %s, missing %s' % (
            sorted(non_class - generated_entries)[:8], sorted(generated_entries - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for p in modified_java:
            outer = p[len('src/main/java/'):-len('.java')]
            if p in changes: need(outer+'.class' in jar_delta['modified'], outer+'.class is not a modified JAR class')
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
                   imported_textures=sorted(imported), planning_session_edit=planning_session_edit,
                   start_drift=sorted(drift_report), repinned_since_goal27b_start=sorted(repinned),
                   language_delta=dict(en=en_delta, zh=zh_delta, map=map_delta), language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, line_endings=line_endings, content_rules=content_rules,
                   foundry_casting={k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v)) < 200 else f'<{len(v)} items>') for k, v in facts.items()}, foundry_casting_facts_bad=bad,
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_foundry_tests=foundry_test_names, final_suites_expected=final_expected,
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
    foundry_casting = dict(neo=NEW_JAVA + modified_java, original=O_SOURCES, facts=facts, expected=EXPECTED, known_differences=KNOWN_DIFFERENCES, original_references=original_refs,
                           language_keys=language_keys, imported_resources=imported_facts, resource_ownership_record=RESOURCE_OWNERSHIP, reachability_record=LEDGER,
                           note=f'ICrucibleAcceptor (pour from UP, flow sideways, the remainder contract); foundry channel (capacity {EXPECTED["channel_capacity"]}, every {EXPECTED["channel_cadence"]} ticks, acceptor first then '
                                f'equalise with a 1:5 swap, the node network refuses foreign material), foundry storage basin ({EXPECTED["tank_capacity"]}, {EXPECTED["tank_cadence"][0]}-{EXPECTED["tank_cadence"][1]} ticks, below -> side '
                                'acceptors -> tanks, refuses flow), foundry outlet (no storage, flow from its back side only, closed by redstone or inverted, scrap filter / inverted filter, a ray four blocks down, pours with UP); '
                                f'the crucible pours into any acceptor ({EXPECTED["pour_quanta"]} quanta, SMELTABLE only, safe mode); foundry_mold accepts pours from UP and flows; for crucible spouts a ray that starts inside the acceptor counts '
                                'as hitting its DOWN face (a channel or tank at the spout\'s own level refuses the pour; place it one level lower); the renderer draws channel and tank levels and the foundry_mold mold and cast; copy tool, particles, soot, contact damage, slag tap, basin and large molds (27D) and '
                                'tank wall merging are deferred (known_differences).')
    casting_record = dict(attribution=attribution, suites=casting, wrapper='tools/migration/goal27a_casting_regression_run.py (unchanged)', policy='tools/migration/goal27a_casting_compat.py (unchanged)',
                          note='The two frozen isolated casting regressions (verify_goal10a.py, verify_goal5a_casting.py) run through the unchanged Goal27A wrapper in the final rerun, redirected into '
                               'build/migration/goal27c/final/castingsuites; both already stopped at javac on the Goal26D, Goal27A and Goal27B trees, so none of their assertions is reached. casting-attribution.json '
                               'pairs the javac errors of the Goal27B final run with the Goal27C run and attributes every new or moved error by file to a Goal27C change or to "not 27C"; it is evidence about javac '
                               'in the frozen stub worlds only.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(foundry_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   uncommitted_start=uncommitted_start,
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, reconstruction=base['reconstruction'], push_commit_parent=chain[1], goal26_closeout_commit=chain[2],
                                      note=f'The start tree is HEAD 690ce8c0 (the 2026-10-26 commit and push of Goal 27 batches 27A and 27B, = origin/master) on the Goal 27 planning commit 71c2f660 on the Goal 26 '
                                           f'close-out 0786697d, with {len(status_lines)} status lines: the planning-document edits of GOAL27-THREAD-PROMPTS.md and GOAL27C.md made after the push. build/libs at the start is the '
                                           f'goal27b package {start_jar_sha[:8]}. The original did not move since 24A (aee05a40f). freeze_start.py hashed every tracked and dirty file live ({len(base["files"])} baseline hashes) '
                                           f'before the first 27C write and copied the dirty or planned files ({len(base["copied_scope"])} baseline-files); paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, line_endings=line_endings, content_rules=content_rules, gametest_edits={}, start_copies_supplement=[],
                   foundry_casting=foundry_casting, casting_attribution=casting_record,
                   language=dict(changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']), added=dict(en_us=en_delta['added'], zh_cn=zh_delta['added'], zh_cn_map=map_delta['added']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds), jar_delta=language,
                                 start_sha256={p: base['files'][p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD, LANG_PROVIDER)},
                                 note='Goal27C adds six keys: block.hbmsntm.foundry_channel / foundry_tank / foundry_outlet (original tile.foundry_*.name, en_US.lang:5602-5605, zh_CN.lang:4827-4830) and foundry.filter / '
                                      'foundry.inverted / foundry.invertFilter (en_US.lang:1204-1206, zh_CN.lang:976-978); no value of an existing key changes; the 106 deferred entries are unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith(CARRIED_REPINS)},
                   repinned_since_goal27b_start={p: dict(goal27b_start_pin_sha256=h, goal27c_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record, planning_session_edit=planning_session_edit,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok'), old_machine_suites_through=OLD_MACHINE_SUITES, casting_suites_through=['goal27a_casting_regression_run.py verify_goal10a',
                                                                                                                                                                            'goal27a_casting_regression_run.py verify_goal5a_casting']),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_foundry_tests=foundry_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per FoundryChannelGameTests test (names in new_foundry_tests): what those '
                                      'tests assert about the channel, tank and outlet capacities, cadences and swap rules, the acceptor-first and equalise order, the node network, the outlet ray, redstone and filters, '
                                      'the crucible pouring 24 quanta into acceptors and foundry_mold accepting pours and flows; no client (the renderer, the models and the textures are not drawn), no real player, no saved '
                                      'world, no survival chain.'),
                   audits=audit_summaries, audit_comparison=audit_comparison, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['crucible_alloys (the Goal27B-only domain key; Goal27C adds foundry_casting)',
                                 'casting_regressions (the Goal27A key; Goal27C carries casting_attribution as Goal27B did: the wrapper and the two suites are unchanged, only their javac errors are attributed)',
                                 'material_system (the Goal27A-only domain key)',
                                 'small_fix_d2 (the D2 ContaminationUtil small fix was packaged by goal27a)',
                                 'planning_commit / goal27a_delivery (the Goal27A and Goal27B deliveries are committed in the start commit 690ce8c0; see uncommitted_start.committed_delivery)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun (the six old isolated suites through the goal26c wrapper and the two casting regressions through the unchanged goal27a wrapper, whose javac '
                            'errors are attributed by casting_attribution.py), compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. No in-game client test was run: '
                            'the foundry blocks, the molten levels, the foundry_mold mold and cast, the outlet filter and lock overlays, item tooltips and Chinese UI are not seen on screen; no survival chain '
                            '(smelting in a crucible, pouring through channels, tanks and outlets into molds, recovering scraps with a shovel) in a world was run; no dedicated server beyond GameTest; the acceptance '
                            'checklist GOAL27C-ACCEPTANCE.md is written, not run, and merges into the Goal 27D master list.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal27c JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal27b package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
