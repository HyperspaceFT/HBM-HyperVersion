"""Package Goal28D (the last batch of Goal 28: the vacuum refinery and the rotary furnace with their recipe tables, menus, screens, renderers and JEI categories, CrucibleUtil.pourSingleStack, the
mustard willow crop block with its leaf item, the oily scraps, five shredder rows, five crystallizer rows, three assembly rows, the rotary furnace anvil construction row, the item tags ntm:gems_coke
and ntm:nuggets_bismoid, solid_fuel and rocket_fuel as burnable FuelItems, nine language keys and ResourceCompletionGameTests), cumulatively on the goal28c package, without replacing any previous
delivery. The user's decision of 2026-11-04 ("按 C 做") put the acidizer wax rows, ass.chipBismoid and ntm:nuggets_bismoid into the batch.

python -B -X utf8 tools/migration/package_goal28d.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only build/migration/releases/goal28d/ (the JAR,
SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal28d/gametest-final.log (the GameTest dedicated-server log of the settled tree). The receipt is assembled in both
modes (with None for what is not produced yet in --check) so a --check run also proves the receipt code; only the real mode writes it.

THE START IS RECONSTRUCTED, NOT FROZEN. The 28D-0 freeze was skipped: the first 28D write came before any baseline existed. build/migration/goal28d/baseline.json (reconstructed: true) was
written afterwards by reconstruct_start.py: its hashes are the goal28c baseline (files + migration_files) overridden by the after_sha256 of the goal28c receipt's changed_files, both written
before 28D began; a start copy in baseline-files/ exists only where its bytes hash to the recorded value; the generation stamp has a hash and no bytes (hash_only). This packager recomputes the
start hashes from the goal28c baseline and receipt and asserts they equal the 28D baseline, hashes every start copy, and says so in the receipt (start_reconstruction). It does not read the
freeze-only fields of the earlier baselines (target_status, stamp_state, old_release_files, previous_receipt_protected_paths, startup-verification.json, freeze.log, start_compile.log,
start_status.txt, start_head.txt): the old release files and the protected paths come from the goal28c receipt, the goal28c baseline and the disk.

The start tree is NEO HEAD 66a00353 (the mod rename, = origin/master) with the UNCOMMITTED Goal28A-28C delivery in the worktree. The original did not move (4f5924e2b, the 28A observation point,
unchanged in 28B, 28C and 28D): there is no upstream range to classify, no new snapshot and one compare, against review-4f5924e2b9e1.json. Every change since the start is computed from the
start hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with their start bytes
(baseline-files) and their +/- lines are reported. The JAR delta against the goal28c package is attributed per entry (goal28d or a recompile difference); any entry without an owner fails.
Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys, assembler rows, crystallizer rows) are computed here from the original and NEO sources and
the GameTest log where they can be.

The receipts that hash records (goal21a..goal28c, the review-g21d-hazard-fix receipt) already differ from some older hashes at the start (the acceptance checklists, GOAL21D.md, GOAL22C.md,
goal21d-static-review.md, the goal24a working notes and migration/GOAL24B.md, known from earlier batches; the goal28c receipt itself matches every hash it records); they stay pinned at their
Goal28C start hash and must still equal it; no receipt is rewritten and no other protected path may drift. Every Goal 28C and earlier record, GOAL28-THREAD-PROMPTS.md and
SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL28.md is a shared record, GOAL28D.md the task book and delivery record (hashed by the receipt).

It adds the resource_completion facts (checked against the original and NEO source texts, the generated JSON and the language files). The Goal28C-only receipt key recipe_completion is dropped
and the receipt says so; so are the keys that belong to a moved original. The two old casting regressions run unchanged through the goal27a wrapper in the final rerun and their javac errors are
attributed by casting_attribution.py (casting-attribution.json)."""
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
                             eol_counts, insertions, in_compare_inventory)
from package_goal22a import annotations, GAMETEST_ANNOTATION
from package_goal22b import (git_ro, edit_counts, stale_diff, receipt_protected, start_drift_paths, strip_java_comments,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE
from package_goal27a import is_comment, OLD_MACHINE_SUITES
from package_goal27c import recompile_equal, stray_removals, RECOMPILE_ONLY, RECOMPILE_OWNER
from package_goal28c import (OUT as GOAL28C_OUT, BASELINE as GOAL28C_BASELINE, protected_paths as goal28c_protected_paths, merged_files, original_blob, original_text,
                             original_line, lang_file, paren_body, split_args, stack_count, recipe_rows, gated_spans, row_facts, registry_names, GAMETEST_METHOD,
                             CARRIED_REPINS, KNOWN_DIFFERENCES as KNOWN_DIFFERENCES_28C, changed_since_start as goal28c_changed_since_start)

OUT = ROOT/'build/migration/goal28d'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
START_ANALYSIS = OUT/'start-analysis.json'
VERIFIER_REPORT_MD = OUT/'verifier-report.md'
VERIFIER_SCOPE = ROOT/'build/migration/verifier/goal28d'
REFERENCE_PREVIOUS = GOAL28C_OUT/'final/summary.json'
PREVIOUS = ROOT/'build/migration/releases/goal28c/hbmsntm-198A-goal28c.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal28d'
RELEASE_NAME = 'hbmsntm-198A-goal28d.jar'
OWNER = 'goal28d'
PREVIOUS_OWNER = 'goal28c'
# The original did not move this batch: SOURCE_HEAD is the 28A observation point (unchanged since) and the head the goal28c receipt records.
SOURCE_HEAD = '4f5924e2b9e1e49cee61787674d2658acb3d559b'
START_PREFIX = '66a00353'
START_PARENT_PREFIX = 'c1f6f397'
UNTRACK_PREFIX = '66050453'
GOAL27_DELIVERY_PREFIX = 'adaf265c'
TASK_BOOK = 'migration/GOAL28D.md'
SNAPSHOT = 'migration/baselines/review-4f5924e2b9e1.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
SRC = 'src/main/java/'
J = SRC+'com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
O_RES = RES+'assets/hbm/'
START_RECONSTRUCTION_METHOD_PREFIX = 'NOT frozen before the first 28D write.'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a', 'goal26b', 'goal26c', 'goal26d', 'goal27a', 'goal27b', 'goal27c', 'goal27d', 'goal28a', 'goal28b'}

# Production (owner goal28d): 15 new production Java files and the GameTest class; the MODIFIED production sources are the handoff owner table.
NEW_PRODUCTION = [J+p+'.java' for p in (
    'blockentity/machine/MachineRotaryFurnaceBlockEntity', 'blockentity/machine/oil/MachineVacuumDistillBlockEntity', 'blocks/generic/MustardWillowBlock', 'blocks/machine/MachineRotaryFurnaceBlock',
    'blocks/machine/MachineVacuumDistillBlock', 'handler/jei/RotaryFurnaceRecipeHandler', 'handler/jei/VacuumRefineryRecipeHandler', 'inventory/menus/MachineRotaryFurnaceMenu',
    'inventory/menus/MachineVacuumDistillMenu', 'inventory/recipes/RotaryFurnaceRecipes', 'inventory/recipes/VacuumRefineryRecipes', 'inventory/screens/MachineRotaryFurnaceScreen',
    'inventory/screens/MachineVacuumDistillScreen', 'render/blockentity/RenderRotaryFurnace', 'render/blockentity/RenderVacuumDistill')]
RESOURCE_TESTS = J+'gametest/ResourceCompletionGameTests.java'
NEW_JAVA = NEW_PRODUCTION + [RESOURCE_TESTS]
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blockentity/NtmBlockEntityTypes', 'blocks/NtmBlocks', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockStateProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmItemModelProvider',
    'datagen/NtmItemTagProvider', 'datagen/NtmLanguageProvider', 'handler/jei/NtmJeiPlugin', 'inventory/NtmCreativeTabs', 'inventory/NtmMenuTypes', 'inventory/recipes/AssemblyMachineRecipes',
    'inventory/recipes/CrystallizerRecipes', 'inventory/recipes/ShredderRecipes', 'inventory/recipes/anvil/AnvilRecipes', 'inventory/recipes/loader/SerializableRecipe', 'items/NtmItems',
    'main/ClientProxy', 'main/CommonEvents', 'main/ResourceManager', 'util/CrucibleUtil', 'world/feature/OilSpot')]
(NTM_BLOCK_ENTITY_TYPES, NTM_BLOCKS, LOOT_PROVIDER, BLOCKSTATE_PROVIDER, BLOCK_TAG_PROVIDER, ITEM_MODEL_PROVIDER, ITEM_TAG_PROVIDER, LANG_PROVIDER, JEI_PLUGIN, CREATIVE_TABS, MENU_TYPES,
 ASSEMBLER, CRYSTALLIZER, SHREDDER, ANVIL, SERIALIZABLE_RECIPE, NTM_ITEMS, CLIENT_PROXY, COMMON_EVENTS, RESOURCE_MANAGER, CRUCIBLE_UTIL, OIL_SPOT) = MODIFIED_JAVA
# The six older GameTests the batch edits by design (counts and states this batch changed: the acidizer row totals 60 -> 65, the crucible alloy recipe count, the assembler row totals and the
# ass.platemixed expectation). Five edit only integer literals and comments; RecipeCompletionGameTests moves one expectation (a row no longer unregistered) and adds an assertion line. The
# @GameTest methods and annotations of every one are the start's.
EDITED_GAMETESTS = [J+'gametest/'+n+'.java' for n in ('SmokeGameTests', 'OverworldWorldgenGameTests', 'NetherEndWorldgenGameTests', 'RadiationControlGameTests', 'RecipeCompletionGameTests',
                                                      'CrucibleAlloyGameTests')]
RECIPE_COMPLETION_TESTS = J+'gametest/RecipeCompletionGameTests.java'
LITERAL_ONLY_GAMETESTS = [p for p in EDITED_GAMETESTS if p != RECIPE_COMPLETION_TESTS]
OLDER_GAMETEST_DIR = J+'gametest/'
# Must stay byte-identical to the start: the existing refinery, fraction, mixer, combination and refinery recipe code, the oil bubble feature, Mats and IFluidCopiable (the handoff list); every other
# source file outside the owner table is held to its start hash by the general src/main check.
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'blockentity/machine/oil/MachineRefineryBlockEntity', 'inventory/recipes/FractionRecipes', 'inventory/recipes/MixerRecipes', 'inventory/recipes/CombinationRecipes',
    'inventory/recipes/RefineryRecipes', 'world/feature/OilBubbleFeature', 'inventory/material/Mats', 'blockentity/IFluidCopiable')]
# Allowed removed CODE lines of the modified production files (comment lines may be replaced freely): the removed line must start with the token. Everything else is insert-only.
ALLOWED_REMOVED_CODE = {
    NTM_ITEMS: ('public static final DeferredItem<Item> SOLID_FUEL = ', 'public static final DeferredItem<Item> ROCKET_FUEL = '),
    OIL_SPOT: ('level.setBlock(above, Blocks.DEAD_BUSH.defaultBlockState(), 3);',),
    CRYSTALLIZER: ('return "Ore acidizer (crystallizer) recipes.',),
}
# The one comment line of AssemblyMachineRecipes the batch rewrote (the deferral note loses ass.chipBismoid).
ASSEMBLER_COMMENT_START = '// ass.chipBismoid, ass.chipQuantum and ass.atomicClock (:129-134) are deferred with their inputs (GOAL13B B4).'
ASSEMBLER_COMMENT_NOW = '// ass.chipQuantum and ass.atomicClock (:131-134) are deferred with their inputs (GOAL13B B4).'
# Older tools that must equal their start bytes: every tools/migration file of the start; only the two new tools are added.
VERIFY_TOOL = 'tools/migration/verify_goal28d_resources.py'
PACKAGE_TOOL = 'tools/migration/package_goal28d.py'
NEW_TOOLS = [VERIFY_TOOL, PACKAGE_TOOL]
TOOLS = NEW_TOOLS
RESOURCE_OWNERSHIP = 'migration/goal28d-resource-ownership.json'
# Hand-written resources: the 16 imported files (models, model textures, GUIs, the eight willow stage textures, the leaf and oily scraps icons) listed by the ownership record; byte copies of the original.
IMPORTED_ROOTS = (ASSETS_ROOT+'models/', ASSETS_ROOT+'textures/')
# Generated by runData: blockstates, block models, item models, loot tables and the two item tags; en_us.json, the block mineable tag and the stamp change.
GENERATED_ADDED_PATHS = sorted([GENERATED_ROOT+p for p in (
    'assets/hbmsntm/blockstates/machine_rotary_furnace.json', 'assets/hbmsntm/blockstates/machine_vacuum_distill.json', 'assets/hbmsntm/blockstates/plant_mustard_willow.json',
    'assets/hbmsntm/models/block/machine_rotary_furnace_particle.json', 'assets/hbmsntm/models/block/machine_vacuum_distill_particle.json',
    'assets/hbmsntm/models/block/plant_mustard_willow_cd0.json', 'assets/hbmsntm/models/block/plant_mustard_willow_cd1.json',
    'assets/hbmsntm/models/block/plant_mustard_willow_cd2_lower.json', 'assets/hbmsntm/models/block/plant_mustard_willow_cd2_upper.json',
    'assets/hbmsntm/models/block/plant_mustard_willow_cd3_lower.json', 'assets/hbmsntm/models/block/plant_mustard_willow_cd3_upper.json',
    'assets/hbmsntm/models/block/plant_mustard_willow_cd4_lower.json', 'assets/hbmsntm/models/block/plant_mustard_willow_cd4_upper.json',
    'assets/hbmsntm/models/item/machine_rotary_furnace.json', 'assets/hbmsntm/models/item/machine_vacuum_distill.json', 'assets/hbmsntm/models/item/plant_item_mustardwillow.json',
    'assets/hbmsntm/models/item/plant_mustard_willow.json', 'assets/hbmsntm/models/item/scrap_oil.json',
    'data/hbmsntm/loot_table/blocks/machine_rotary_furnace.json', 'data/hbmsntm/loot_table/blocks/machine_vacuum_distill.json', 'data/hbmsntm/loot_table/blocks/plant_mustard_willow.json',
    'data/ntm/tags/item/gems_coke.json', 'data/ntm/tags/item/nuggets_bismoid.json')])
REQUIRED_GENERATED = GENERATED_ADDED_PATHS
GENERATED_COUNTS = dict(blockstates=3, block_models=10, item_models=5, loot_tables=3, item_tags=2)
PICKAXE_TAG = GENERATED_ROOT+'data/minecraft/tags/block/mineable/pickaxe.json'
GENERATED_MODIFIED = [STAMP, EN, PICKAXE_TAG]
# Language: 9 new keys (8 upstream, 1 local); nothing changed or removed. NEO key -> original key.
UPSTREAM_KEYS = {'block.hbmsntm.machine_vacuum_distill': 'tile.machine_vacuum_distill.name', 'block.hbmsntm.machine_rotary_furnace': 'tile.machine_rotary_furnace.name',
                 'block.hbmsntm.plant_mustard_willow': 'tile.plant_flower.cd0.name', 'block.hbmsntm.plant_mustard_willow.mature': 'tile.plant_tall.cd4.name',
                 'item.hbmsntm.plant_item_mustardwillow': 'item.plant_item.mustardwillow.name', 'item.hbmsntm.scrap_oil': 'item.scrap_oil.name',
                 'container.vacuumDistill': 'container.vacuumDistill', 'container.machineRotaryFurnace': 'container.machineRotaryFurnace'}
LOCAL_KEYS = ['container.machineRotaryFurnace.empty']
KEYS = sorted(list(UPSTREAM_KEYS) + LOCAL_KEYS)
REMOVED_KEYS = []
LANG_CHANGED = []
EN_CHANGED = ZH_CHANGED = LANG_CHANGED
LANG_SOURCE = UPSTREAM_KEYS
UPSTREAM_ADDED = 8
LOCAL_ADDED = 1
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal28d-* or GOAL28D-* record is hashed as well.
REPORTS = ['migration/GOAL28D.md', 'migration/GOAL28D-ACCEPTANCE.md', RESOURCE_OWNERSHIP, 'migration/goal28d-static-review.md', 'migration/goal28d-materials-review.json',
           'migration/goal28d-localization-review.json']
LEDGER = REPORTS[4]
LOCALIZATION_REVIEW = REPORTS[5]
BATCH_RECORD = re.compile(r'migration/(goal28d-[^/]+\.(json|md)|GOAL28D(?:-[^/]+)?\.md)')
GOAL28_RECORD = 'migration/GOAL28.md'
FOUNDATIONS_RECORD = 'migration/FOUNDATIONS.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', FOUNDATIONS_RECORD, GOAL28_RECORD, LOCALIZATION_RECORD]
# Shared records the batch may leave untouched.
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
# The records of the other batches and the files no batch of this kind touches: no change is expected.
PLANNING_FROZEN = ['migration/SURVIVAL-PLAYABILITY.md', 'migration/GOAL28-THREAD-PROMPTS.md']
# Every Goal 28C and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 27, GOAL28A..C*, goal28a-c-*): pinned at their start hash.
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-7]|28A|28B|28C)(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-7]|28a|28b|28c)(?!\d)[a-z]?-[^/]+)')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = (NEW_JAVA + MODIFIED_JAVA + REQUIRED_GENERATED + GENERATED_MODIFIED + [ZH_INPUT] + TOOLS + REPORTS + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]
                    + [p for p in EDITED_GAMETESTS])
GAMETEST_MARKER = '[hbm-28d] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager). The start is reconstructed: its evidence is the baseline, the
# script that wrote it, its analysis and the recorded edit scripts (edit-scripts/*), not a freeze log.
START_EVIDENCE = ('baseline.json', 'reconstruct_start.py', 'start-analysis.json', 'RESUME.md', 'chain.sh', 'make_production_diff.py')
# Review files under OUT; each must exist and is indexed by the receipt. --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'casting_attribution.py', 'chain_compare.sh', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-report.md', 'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'compare.log', 'localization-final.log', 'resources-audit-final.log', 'packaged-resources-final.log')
EXTERNAL_EVIDENCE = ('build/migration/verifier/goal28d/scope-start.txt', 'build/migration/verifier/goal28d/scope-end.txt')
CASTING_ATTRIBUTION = 'casting-attribution.json'
CASTING_DIR = OUT/'final/castingsuites'
CASTING_SUITES = ('verify_goal10a', 'verify_goal5a_casting')
FAIL_SET_DIFF = 'final/fail-set-diff.json'
GAMETEST_LOG = 'build/migration/goal28d/gametest-final.log'
VERIFY_REPORT = 'verify/report.json'
NEW_SUITE = 'verify_goal28d_resources.py --gametest-log build/migration/goal28d/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
OLD_SUITE_28C = 'verify_goal28c_recipes.py --gametest-log build/migration/goal28c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# features.json: two new groups vacuum-refinery and rotary-furnace; notes of materials, crystallization, shredder, oil-refining and anvil-stamps (and possibly foundry-casting, oil-extraction) may change;
# every group keeps reviewed_source_commit (the original did not move) and its status.
NEW_FEATURES = ('vacuum-refinery', 'rotary-furnace')
NOTES_GROUPS = {'materials', 'crystallization', 'shredder', 'oil-refining', 'anvil-stamps', 'foundry-casting', 'oil-extraction', 'crucible-alloying'}
NOTES_MAY_CHANGE = NOTES_GROUPS | set(NEW_FEATURES)
RADIATION_NOTE = 'Goal28D: no new radiation source. Radiosolvent and sour gas are corrosive or toxic fluids, not radioactive. '
MELTDOWN_NOTE = 'Goal28D: no new meltdown path; the survival route to the vacuum refinery now passes a running RBMK. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_TEVD = ORIGINAL+'tileentity/machine/oil/TileEntityMachineVacuumDistill.java'
O_VRR = ORIGINAL+'inventory/recipes/VacuumRefineryRecipes.java'
O_MVD = ORIGINAL+'blocks/machine/MachineVacuumDistill.java'
O_TERF = ORIGINAL+'tileentity/machine/TileEntityMachineRotaryFurnace.java'
O_RFR = ORIGINAL+'inventory/recipes/RotaryFurnaceRecipes.java'
O_MRF = ORIGINAL+'blocks/machine/MachineRotaryFurnace.java'
O_FLOWER = ORIGINAL+'blocks/generic/BlockNTMFlower.java'
O_TALL = ORIGINAL+'blocks/generic/BlockTallPlant.java'
O_OILSPOT = ORIGINAL+'world/feature/OilSpot.java'
O_SHREDDER = ORIGINAL+'inventory/recipes/ShredderRecipes.java'
O_CRYST = ORIGINAL+'inventory/recipes/CrystallizerRecipes.java'
O_AMR = ORIGINAL+'inventory/recipes/AssemblyMachineRecipes.java'
O_ANVIL = ORIGINAL+'inventory/recipes/anvil/AnvilRecipes.java'
O_FUEL = ORIGINAL+'handler/FuelHandler.java'
O_MIXER = ORIGINAL+'inventory/recipes/MixerRecipes.java'
O_FRACTION = ORIGINAL+'inventory/recipes/FractionRecipes.java'
O_OUTGASSER = ORIGINAL+'inventory/recipes/OutgasserRecipes.java'
O_OREDICT = ORIGINAL+'inventory/OreDictManager.java'
O_LANG_EN = O_RES+'lang/en_US.lang'
O_LANG_ZH = O_RES+'lang/zh_CN.lang'
O_SOURCES = [O_TEVD, O_VRR, O_MVD, O_TERF, O_RFR, O_MRF, O_FLOWER, O_TALL, O_OILSPOT, O_SHREDDER, O_CRYST, O_AMR, O_ANVIL, O_FUEL, O_MIXER, O_FRACTION, O_OUTGASSER, O_OREDICT, O_LANG_EN, O_LANG_ZH]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'vac_power': (O_TEVD, 'maxPower = 1_000_000'), 'vac_tanks': (O_TEVD, 'new FluidTank(Fluids.OIL, 64_000).withPressure(2)'), 'vac_refine': (O_TEVD, 'if(power < 10_000) return;'),
    'vac_fractions': (O_VRR, 'vac_frac_heavy = 40'), 'vac_oil_row': (O_VRR, 'recipes.put(Fluids.OIL, new VacuumRefineryRecipe('), 'vac_ds_row': (O_VRR, 'recipes.put(Fluids.OIL_DS, new VacuumRefineryRecipe('),
    'vac_file': (O_VRR, 'getFileName() { return "hbmVacRefinery.json"; }'), 'vac_dims': (O_MVD, 'return new int[] {8, 0, 1, 1, 1, 1};'),
    'rot_max_output': (O_TERF, 'maxOutput = MaterialShapes.BLOCK.q(16)'), 'rot_burn': (O_TERF, '.setCokeTimeMod(1.25)'), 'rot_tanks': (O_TERF, 'new FluidTank(Fluids.STEAM, 12_000)'),
    'rot_pour': (O_TERF, 'CrucibleUtil.pourSingleStack(worldObj, xCoord + 0.5D + rot.offsetX * 2.875D'), 'rot_steam_mult': (O_TERF, 'float steamUseMult = (float)(10 * Math.log10(processSpeed) + 1);'),
    'rot_dims': (O_MRF, 'return new int[] {4, 0, 1, 1, 2, 2};'), 'rot_rows': (O_RFR, 'recipes.add(new RotaryFurnaceRecipe(new MaterialStack(MAT_STEEL, INGOT.q(1)), 100, 100'),
    'willow_growth_flower': (O_FLOWER, 'cadmium willows can only grow with water'), 'willow_tall_reset': (O_TALL, 'ownMeta < 8'), 'willow_loot': (O_TALL, '3 + world.rand.nextInt(4)'),
    'oil_spot_willow': (O_OILSPOT, 'addWillows && world.rand.nextInt(50) == 0'), 'shredder_scrap': (O_SHREDDER, 'ShredderRecipes.setRecipe(ModBlocks.dirt_dead, new ItemStack(ModItems.scrap_oil, 1));'),
    'cryst_cadmium': (O_CRYST, 'new CrystallizerRecipe(new ItemStack(ModItems.powder_cadmium), 100).setReq(10)'), 'cryst_arsenic': (O_CRYST, 'new CrystallizerRecipe(new ItemStack(ModItems.nugget_arsenic), 100).prod(0.3F).setReq(16)'),
    'cryst_wax_crude': (O_CRYST, 'EnumTarType.CRUDE)),\t\tnew CrystallizerRecipe(DictFrame.fromOne(ModItems.oil_tar, EnumTarType.WAX), 20)'), 'cryst_class': (O_CRYST, 'public float productivity = 0F;'),
    'ass_platemixed': (O_AMR, 'new GenericRecipe("ass.platemixed")'), 'ass_chipbismoid': (O_AMR, 'new GenericRecipe("ass.chipBismoid")'), 'ass_vaccumrefinery': (O_AMR, 'new GenericRecipe("ass.vaccumrefinery")'),
    'ass_no528': (O_AMR, 'if(!GeneralConfig.enable528) { // precass otherwise'), 'anvil_saturnite': (O_ANVIL, 'Block[] anvils = new Block[]{ModBlocks.anvil_iron, ModBlocks.anvil_lead};'),
    'anvil_rotary_furnace': (O_ANVIL, 'new AnvilOutput(new ItemStack(ModBlocks.machine_rotary_furnace))).setTier(2)'), 'fuel_solid': (O_FUEL, 'if(fuel.getItem().equals(ModItems.solid_fuel))'),
    'fuel_rocket': (O_FUEL, 'if(fuel.getItem().equals(ModItems.rocket_fuel))'), 'mixer_radiosolvent': (O_MIXER, 'register(Fluids.RADIOSOLVENT, new MixerRecipe(1000, 50)'),
    'fraction_reformgas': (O_FRACTION, 'fractions.put(Fluids.LIGHTOIL_VACUUM'), 'outgasser_radiosolvent': (O_OUTGASSER, 'new OutgasserRecipe(null, new FluidStack(Fluids.RADIOSOLVENT, 100))'),
    'tag_coke': (O_OREDICT, 'ANY_COKE = new DictFrame("AnyCoke", "Coke");'), 'tag_bismoid': (O_OREDICT, 'ANY_BISMOID = new DictGroup("AnyBismoid", BI, AS);'),
}
# Expected figures of the handoff and the task book (every value is also computed from the sources).
EXPECTED = dict(assembler_rows_start=82, assembler_rows_added=3, assembler_rows=85, original_assembler_rows=355, crystallizer_rows_start=60, crystallizer_rows_added=5, crystallizer_rows=65,
                shredder_rows=5, rotary_rows_ported=8, rotary_rows_original=13, imported_assets=16, language_added=9, language_changed=0, deferred_entries=106,
                en_total=3024, zh_total=2918, map_total=3024, gametest_start=338, gametest_added=18, gametest_total=356, generated_added=23, new_production_java=15, modified_java=22,
                edited_gametests=6, release_files_added=3)
# The rows of the original rotary furnace table (RotaryFurnaceRecipes.java:39-54) NEO does not register (the recorded omissions), as (material, ingot quanta, duration, steam).
ROTARY_OMITTED = [('MAT_STEEL', 2, 200, 25), ('MAT_STEEL', 3, 200, 25), ('MAT_STEEL', 4, 400, 25), ('MAT_WEAPONSTEEL', 1, 200, 400), ('MAT_TITANIUM', 4, 40, 100)]
# original block -> NEO block of the five shredder rows (the sixth original row, stone_porous, has no NEO block).
SHREDDER_BLOCKS = [('dirt_dead', 'DIRT_DEAD'), ('dirt_oily', 'DIRT_OILY'), ('sand_dirty', 'SAND_OILY'), ('sand_dirty_red', 'SAND_RED_OILY'), ('stone_cracked', 'STONE_CRACKED')]
# The five crystallizer rows: (NEO input constant, input count, acid fluid, acid amount, NEO output constant, ticks, productivity, original line token).
CRYSTALLIZER_ROWS = [('PLANT_ITEM_MUSTARDWILLOW', 10, 'RADIOSOLVENT', 250, 'POWDER_CADMIUM', 100, 0.0, 'powder_cadmium), 100).setReq(10)'),
                     ('SCRAP_OIL', 16, 'RADIOSOLVENT', 100, 'NUGGET_ARSENIC', 100, 0.3, 'nugget_arsenic), 100).prod(0.3F).setReq(16)'),
                     ('OIL_TAR_CRUDE', 1, 'CHLORINE', 250, 'OIL_TAR_WAX', 20, 0.0, 'EnumTarType.CRUDE'),
                     ('OIL_TAR_CRACK', 1, 'CHLORINE', 100, 'OIL_TAR_WAX', 20, 0.0, 'EnumTarType.CRACK'),
                     ('OIL_TAR_PARAFFIN', 1, 'CHLORINE', 100, 'OIL_TAR_WAX', 20, 0.0, 'EnumTarType.PARAFFIN')]
# The three assembly rows (registered after ass.emptypackage in this order): name -> (NEO product constant, product count, setup, input counts, original product token).
ASSEMBLY_ROWS = {'ass.platemixed': ('PLATE_MIXED', 4, [50, 100], [2, 1, 1], 'plate_mixed'), 'ass.vaccumrefinery': ('MACHINE_VACUUM_DISTILL', 1, [200, 100], [16, 16, 4, 1, 12, 3, 4], 'machine_vacuum_distill'),
                 'ass.chipBismoid': ('CIRCUIT_VERSATILE_INTEGRATED', 1, [100, 1500], [2, 2, 1, 2], 'CHIP_BISMOID')}
# The two new item tags: tag path -> (original dictionary token, OreDictManager line token, NEO members: NtmItems constants).
NEW_TAGS = {'gems_coke': ('ANY_COKE', 'ANY_COKE = new DictFrame("AnyCoke", "Coke");', ('COKE_COAL', 'COKE_LIGNITE', 'COKE_PETROLEUM')),
            'nuggets_bismoid': ('ANY_BISMOID', 'ANY_BISMOID = new DictGroup("AnyBismoid", BI, AS);', ('NUGGET_BISMUTH', 'NUGGET_ARSENIC'))}
# The reviewed differences the receipt carries (the task book, RESUME.md and the review); the Goal28C ones that still hold are carried unchanged as carried_28c.
KNOWN_DIFFERENCES = {
    'user_decision': 'the user decided on 2026-11-04 ("按 C 做", option C): the acidizer wax rows (tar + chlorine -> wax), ass.chipBismoid and the tag ntm:nuggets_bismoid are in the batch, so the radiosolvent chain, the vacuum refinery recipe and the bismoid circuit are reachable',
    'start_not_frozen': 'the 28D-0 freeze was skipped; the start is reconstructed (baseline.json reconstructed: true, reconstruct_start.py, edit-scripts/); 32 of the 33 start files modified by the batch have start bytes that hash to the recorded value, .migration-stamp.json has a hash only',
    'config_file_name': 'the vacuum refinery table is read from hbmVacuumRefinery.json, the original names it hbmVacRefinery.json (VacuumRefineryRecipes.java getFileName)',
    'rotary_rows': 'the rotary furnace registers 8 of the 13 original rows: the three iron fragment steel rows (no iron bedrock ore fragment item), the weapon steel row (GOAL28D limit) and the titanium row (no titanium tetrachloride fluid) are not registered; the coke steel row takes the tag ntm:gems_coke, the gunmetal row takes three of ntm:ingots_copper',
    'shredder_rows': 'five of the six original scrap_oil shredder rows (ShredderRecipes.java:302-306); stone_porous (:307) has no NEO block',
    'weapon_steel_claim': 'the task book says NEO has no weapon steel item; INGOT_WEAPON_STEEL, MAT_WEAPONSTEEL and GAS_COKER exist, the row stays out because of the batch limit',
    'anvil_tier_five': 'the task book (D3 item 5) asks for a tier 5 construction row; the original has none (the only 5 tier row is the doomsday missile, AnvilRecipes.java:562); the test asserts Variant.SATURNITE.tier == 5 and the tier 4 gate instead',
    'fuel_times': 'solid_fuel burns 3200 ticks and rocket_fuel 6400 as NEO FuelItems (original FuelHandler single * 16 and * 32 with single = 200); the rotary furnace burn module applies the original factors (coke 1.25, rocket 1.5, solid 1.5, balefire 1.5)',
    'growth_conditions': 'the task book missed the original growth conditions: CD0 and CD1 also need water next to the soil, CD1 needs air above, CD3 -> CD4 turns the soil into dirt',
    'rotary_omissions': 'no smoke can or smoke particle effect: the soot goes straight to PollutionHandler; the pour particle is the vanilla dust; burnHeat is synchronised for the piston animation; the two new recipe tables have no client sync; hasWater uses FluidTags.WATER so waterlogged blocks count; the screen shows raw quanta (NEO Mats has no formatAmount)',
    'oil_bubble_dead_bush': 'OilBubbleFeature.java:178 still places the dead bush (the task book limit)',
    'out_of_scope_defects': 'ore_basalt drops the joke item (NtmBlockLootTableProvider.java:168-179, original BlockOreBasalt.java:32-37); RenderRefinery has no render box; ModuleBurnTime.java:62 tests BALEFIRE_AND_STEEL (original solid_fuel_bf); coke burn times 3200/2400/6400 (original 3200 uniform); with enable528 true the circuits have no assembly row, so the vacuum refinery cannot be made',
    'reachability': 'the survival route to the vacuum refinery runs through cracked tar (CrackingRecipes.java:41, hot boiler), chlorine from the combination furnace (fluorite powder, sodalite), a running RBMK (rubber, radium/beryllium rods) that irradiates the wax to radiosolvent, a 3 tier anvil for the desh motors and the cadmium alloy',
}
# 27A / 27B / 27C / 27D / 28A / 28B / 28C ones the receipt carries forward under a new heading.
CARRIED = CARRIED_REPINS


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal28d release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a reconstructed-start file: the baseline-files copy when it reproduces the baseline hash, else the blob at the start commit (with CRLF where the working tree had it);
    None when nothing reproduces the baseline hash (the generation stamp is hash-only)."""
    if (START_FILES/p).is_file():
        data = (START_FILES/p).read_bytes()
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    if (ROOT/p).is_file() and p != STAMP and sha(ROOT/p) == base['files'][p]: return (ROOT/p).read_bytes()  # unchanged since the start
    try: blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT, stderr=subprocess.DEVNULL)
    except Exception: return None
    for data in (blob, blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def start_json(base, p):
    data = start_bytes(base, p)
    assert data is not None, 'No reproducible start bytes for '+p
    return json.loads(data.decode('utf-8-sig'))


def protected_paths(receipt):
    """What the goal28c packager protected (built there from the Goal21A..Goal28B starts and receipts and the goal28c freeze), plus every path the goal28c receipt hashes and the three
    release files of the goal28c package. Records that already drifted from an older receipt stay pinned at the Goal28C start hash (the goal28c step set it); one path never carries two
    hashes. Returns the protected map."""
    goal28c_start = read(GOAL28C_BASELINE)
    goal28c_start['files'] = merged_files(goal28c_start)
    out = dict(goal28c_protected_paths(goal28c_start)[0])
    release_files = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(PREVIOUS.parent.iterdir()) if p.is_file()}
    for p, h in {**receipt_protected(receipt), **release_files}.items():
        assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    return out


def changed_since_start(base):
    """{path: added|modified|deleted} against the reconstructed start hashes (the same walk as the goal28c packager: the Git-visible files and every file found under migration/)."""
    return goal28c_changed_since_start(base)


def reconstructed_start(base, receipt):
    """The start recomputed from the goal28c baseline (files + migration_files) overridden by the after_sha256 of the goal28c receipt's changed_files, as reconstruct_start.py derived it."""
    start28c = read(GOAL28C_BASELINE)
    expected = merged_files(start28c)
    for row in receipt['changed_files']:
        if row.get('after_sha256'): expected[row['path']] = row['after_sha256']
        else: expected.pop(row['path'], None)
    return expected


def scope_text(tests, total_tests):
    return (f'Goal28D (the last batch of Goal 28: the vacuum refinery and the rotary furnace, with the user\'s decision of 2026-11-04 to include the acidizer wax rows, ass.chipBismoid and the '
            f'ntm:nuggets_bismoid tag; original 4f5924e2b, unchanged since Goal28A): the vacuum refinery (machine block with its multiblock, block entity, recipe table hbmVacuumRefinery.json for crude '
            f'oil and desulfurized crude oil, menu, screen, renderer and JEI category), the rotary furnace (machine block, block entity with its burn, steam and pour module, 8 of the 13 original '
            f'recipe rows, menu, screen, renderer and JEI category), CrucibleUtil.pourSingleStack, the mustard willow crop (a two-block plant with five growth stages, the leaf item, oil spot '
            f'placement), the oily scraps item, five shredder rows (the dead, oily and cracked blocks and the two oily sands to oily scraps), five acidizer rows (mustard willow leaves and oily '
            f'scraps with radiosolvent, three tar types with chlorine to wax), three assembly rows (ass.platemixed, ass.vaccumrefinery, ass.chipBismoid), the rotary furnace anvil construction row, '
            f'the item tags ntm:gems_coke and ntm:nuggets_bismoid, solid_fuel and rocket_fuel as burnable items, 9 language keys (8 upstream, 1 local) and {tests} ResourceCompletionGameTests '
            f'({total_tests} GameTests in total). Gameplay impact: the vacuum refinery and the rotary furnace are craftable and usable; radiosolvent, sour gas, vacuum oil fractions and reformate are '
            f'produced and consumed; mustard willow grows on oil spots and its leaves become cadmium powder; the survival route to the vacuum refinery now needs a running RBMK (the wax is irradiated '
            f'to radiosolvent), chlorine from the combination furnace and a tier 3 anvil for the desh motors; the rotary furnace cannot make weapon steel, titanium or the iron fragment steel '
            f'(not registered).')


def group(p, imported):
    if p in NEW_JAVA: return 'gametest-new' if p == RESOURCE_TESTS else 'production-new'
    if p in EDITED_GAMETESTS: return 'gametest-edit'
    if p in MODIFIED_JAVA: return 'production'
    if p in imported: return 'production-resource-imported'
    if p == ZH_INPUT: return 'language'
    if p in GENERATED_MODIFIED or p in GENERATED_ADDED_PATHS: return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p) or p == TASK_BOOK: return 'reports'
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records'
    return None


def owner_of(p):
    return OWNER


def generated_json(path):
    return read(ROOT/path) if (ROOT/path).is_file() else None


def line_of(text, token):
    """1-based line of the first line of text that contains the token (None when absent)."""
    for number, line in enumerate(text.split('\n'), 1):
        if token in line: return number
    return None


ROTARY_ROW = re.compile(r'new RotaryFurnaceRecipe\(new MaterialStack\((?:Mats\.)?MAT_(\w+),\s*(?:MaterialShapes\.)?INGOT\.q\((\d+)\)\),\s*(\d+),\s*(\d+)')
CRYSTAL_NEO_ROW = re.compile(r'add\(new CrystallizerRecipe\(new ComparableStack\(NtmItems\.(\w+)\.get\(\), (\d+)\), new FluidStack\(Fluids\.(\w+), (\d+)\), new ItemStack\(NtmItems\.(\w+)\.get\(\)\), (\d+), ([\d.]+)F\)\);')


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
    goal28c_start = read(GOAL28C_BASELINE)
    goal28c_start['files'] = merged_files(goal28c_start)

    # 1. The reconstructed start. The 28D-0 freeze was skipped; baseline.json (reconstructed: true) was written afterwards by reconstruct_start.py from the goal28c baseline and the goal28c
    # receipt. This packager recomputes the start hashes the same way and asserts they equal the baseline, then checks every start copy against its recorded hash.
    assert base.get('reconstructed') is True and base['method'].startswith(START_RECONSTRUCTION_METHOD_PREFIX), 'baseline.json is not the reconstructed Goal28D start'
    assert not set(base['files']) & set(base['migration_files']), 'The tracked tree and migration_files overlap'
    tracked_count, migration_count = len(base['files']), len(base['migration_files'])
    base['files'] = merged_files(base)
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD, 'The reconstructed start records another original commit than 4f5924e2b'
    assert start_head.startswith(START_PREFIX), 'The reconstructed start is not on the mod rename commit 66a00353'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal28c receipt records another original commit than 4f5924e2b (the original must be unmoved)'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal28D (the delivery stays uncommitted until the Goal 28 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2, 3)}
    assert chain[1].startswith(START_PARENT_PREFIX) and chain[2].startswith(UNTRACK_PREFIX) and chain[3].startswith(GOAL27_DELIVERY_PREFIX), \
        'NEO HEAD~1..3 are not c1f6f397, the migration/ untrack commit 66050453 and the Goal 27 delivery adaf265c: '+str(chain)
    committed_files = [l for l in git_ro(ROOT, 'show', '--name-only', '--format=', start_head).splitlines() if l.strip()]
    assert committed_files and not any(p.startswith(('build/', 'migration/')) for p in committed_files), 'The start commit is empty or holds build/ or migration/ files'
    recomputed = reconstructed_start(base, prior_receipt)
    assert recomputed == base['files'], 'The Goal28D start is not the goal28c baseline overridden by the goal28c receipt: '+str(
        sorted(set(recomputed) ^ set(base['files']))[:6] or sorted(p for p in recomputed if recomputed[p] != base['files'][p])[:6])
    hash_only = list(base['hash_only'])
    assert hash_only == [STAMP] and base['files'].get(STAMP), 'The only hash-only start file must be the generation stamp'
    for p in base['start_copies']:
        if p in hash_only: continue
        assert (START_FILES/p).is_file() and sha(START_FILES/p) == base['files'][p], 'Start copy differs from the recorded hash: '+p
    assert start_bytes(base, STAMP) is None, 'The generation stamp has start bytes after all (hash_only is wrong)'
    start_analysis = read(START_ANALYSIS)
    analysis_counts = {k: len(v) for k, v in start_analysis.items()}
    assert analysis_counts['start'] == len(base['files']) and analysis_counts['unresolved'] == 1 and analysis_counts['resolved'] + analysis_counts['unresolved'] == analysis_counts['modified']         and analysis_counts['missing'] == 0, 'start-analysis.json does not match the reconstructed start: '+str(analysis_counts)
    start_reconstruction = dict(
        method=base['method'], reconstruct_script='build/migration/goal28d/reconstruct_start.py', baseline=BASELINE.relative_to(ROOT).as_posix(), baseline_sha256=sha(BASELINE),
        files=tracked_count, migration_files=migration_count, start_paths=len(base['files']), start_copies=len(base['start_copies']), start_copy_methods=dict(Counter(base['start_copies'].values())),
        hash_only=hash_only, modified_at_reconstruction=analysis_counts['modified'], added_at_reconstruction=analysis_counts['added'], analysis=START_ANALYSIS.relative_to(ROOT).as_posix(),
        analysis_sha256=sha(START_ANALYSIS), edit_scripts='build/migration/goal28d/edit-scripts/',
        recomputed_equal=True,
        note='NOT frozen before the first 28D write. Every start hash is the goal28c baseline (files + migration_files) overridden by the after_sha256 of the goal28c receipt changed_files, both '
             'written before Goal28D began, recomputed by this packager and asserted equal to baseline.json. A start copy exists (baseline-files) only where its bytes hash to the recorded '
             'value; the generation stamp has a hash and no bytes. The freeze-only fields (target_status, stamp_state, old_release_files, previous_receipt_protected_paths, startup-verification.json, '
             'freeze.log, start_compile.log, start_status.txt, start_head.txt) do not exist for this batch: the old release files, the protected paths and the stamp contents come from the '
             'goal28c receipt, the goal28c baseline and the disk.')
    start_stamp_generated = sorted(p[len(GENERATED_ROOT):] for p in base['files'] if p.startswith(GENERATED_ROOT) and p != STAMP)
    assert len(start_stamp_generated) == prior_receipt['generated_resource_count'], 'The start generated tree is not the goal28c generated resource count'
    uncommitted_start = dict(
        description='the worktree holds the uncommitted Goal28A-28C delivery (packaged as goal28a, goal28b and goal28c, never committed) on HEAD 66a00353: the start content of this batch; baseline `files` '
                    'hashes the worktree content, so every 28A, 28B and 28C change is part of the start',
        goal28c_delivery_paths=len(prior_receipt['changed_files']),
        committed_delivery=dict(commit=start_head[:8], parent=chain[1][:8], files_in_commit=len(committed_files), untrack_commit=chain[2][:8], goal27_delivery_commit=chain[3][:8],
                                note='66a00353 renames the mod and ignores .claude; c1f6f397 rewrites the README; 66050453 untracks and ignores migration/; adaf265c commits the Goal 27 delivery (27C and 27D) '
                                     'with the small fixes D3 and D5.'),
        migration_dir=dict(tracked_files_hashed=tracked_count, migration_files_hashed=migration_count,
                           note='migration/ is Git-ignored: `git ls-files` no longer lists it, so the baseline hashes it from disk and this packager finds its changes by walking the directory.'))

    # 2. Previous deliveries: the goal28c package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], prior_receipt['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert sha(PREVIOUS) == previous_sha and PREVIOUS.stat().st_size == previous_bytes, 'Previous JAR changed'
    assert prior_receipt['sha256'] == previous_sha, 'Previous receipt names another JAR'
    previous_receipt_sha, previous_sums_sha = sha(PREVIOUS_RECEIPT), sha(PREVIOUS_SUMS)
    assert PREVIOUS_SUMS.read_bytes() == (previous_sha+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Previous SHA256SUMS.txt content changed'
    previous_rel = PREVIOUS.relative_to(ROOT).as_posix()
    old_releases = {**prior_receipt['old_releases'], previous_rel: previous_sha}
    for p, h in old_releases.items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release JAR changed: '+p
    old_release_files = {p.relative_to(ROOT).as_posix(): sha(p) for d in sorted(RELEASES.iterdir()) if d.is_dir() and d.resolve() != RELEASE.resolve() for p in sorted(d.iterdir()) if p.is_file()}
    assert len(old_release_files) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal28c receipt count + the goal28c release directory: %d vs %d + %d' % (len(old_release_files), prior_receipt['preserved_release_files'], len(list(PREVIOUS.parent.iterdir())))
    for p, h in goal28c_start['old_release_files'].items(): assert old_release_files.get(p) == h, 'Release file of the goal28c freeze changed: '+p
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    protected = protected_paths(prior_receipt)
    drift_report = {}
    for p, entry in prior_receipt['start_drift_explained'].items():
        pinned = protected.get(p)
        assert pinned is not None and (p not in base['files'] or pinned == base['files'][p]), 'Start drift pin differs from the Goal28D start hash: '+p
        drift_report[p] = dict(entry, goal28d_start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p) if (ROOT/p).is_file() else None)
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal28c receipt: '+str(sorted(explained))
    # No small fix lies between the goal28c package and this start: the README lines above the Goal28C line (newest first) must name none.
    readme_start = start_bytes(base, 'migration/README.md')
    readme_start_lines = readme_start.decode('utf-8').split('\n') if readme_start else []
    goal28c_line = next((i for i, l in enumerate(readme_start_lines) if l.startswith('2026-11-04 Goal28C')), None)
    need(goal28c_line is not None, 'migration/README.md (start copy) has no "2026-11-04 Goal28C" delivery line')
    small_fixes_after_goal28c = [l[:140] for l in readme_start_lines[:goal28c_line] if l.startswith('2026-1') and '小修' in l] if goal28c_line is not None else None

    # 3. Changes since the start: each path in the owner table, attributed to goal28d. Everything else equals its start hash.
    changes = changed_since_start(base)
    imported = {p for p in changes if p.startswith(IMPORTED_ROOTS) and changes[p] == 'added'}
    verifier_md = VERIFIER_REPORT_MD.read_text(encoding='utf-8', errors='replace') if VERIFIER_REPORT_MD.is_file() else None
    need(verifier_md is not None, 'evidence missing: build/migration/goal28d/verifier-report.md (the main agent writes it from the GameTest verifier\'s report)')
    production_java = NEW_PRODUCTION + MODIFIED_JAVA + [RESOURCE_TESTS] + [p for p in EDITED_GAMETESTS if p in changes]
    older_gametests_frozen = sorted(p for p in base['files'] if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p not in EDITED_GAMETESTS)
    unassigned = sorted(p for p in changes if group(p, imported) is None)
    need(not unassigned, 'Path changed since the Goal28D start that the owner table does not list (production outside the 15 new and 22 modified Java files, ResourceCompletionGameTests and the six '
         'edited GameTests, a hand-written resource other than the 16 imported ones, a generated file other than the stamp, en_us.json, the block pickaxe tag and the 23 additions, a protected or frozen '
         'record, an older tool, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal 28C and earlier records, GOAL28-THREAD-PROMPTS.md or SURVIVAL-PLAYABILITY.md changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal28D start: '+str(deleted)
    for p in MODIFIED_JAVA + EDITED_GAMETESTS + GENERATED_MODIFIED + [ZH_INPUT, TASK_BOOK] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS and p != FOUNDATIONS_RECORD]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    assert FOUNDATIONS_RECORD in base['files'], 'FOUNDATIONS.md is not a start file'
    for p in NEW_JAVA + REQUIRED_GENERATED + NEW_TOOLS + REPORTS[1:]:
        assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(production_java) - imported - {ZH_INPUT})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified, {len(NEW_JAVA)} new and {len(EDITED_GAMETESTS)} edited GameTest Java files, the {EXPECTED["imported_assets"]} imported resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools_changed = sorted(p for p in base['files'] if p.startswith('tools/') and (not (ROOT/p).is_file() or sha(ROOT/p) != base['files'][p]))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (every tools/ file of the start): '+str(frozen_tools_changed))
    unchanged_bad = [p for p in UNCHANGED_JAVA + older_gametests_frozen if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed (MachineRefineryBlockEntity, FractionRecipes, MixerRecipes, CombinationRecipes, RefineryRecipes, OilBubbleFeature, '
         'Mats, IFluidCopiable, every other GameTest class): '+str(unchanged_bad[:8]))
    goal28_now = sha(ROOT/GOAL28_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json records no concurrent session editing the NEO repository (the start is reconstructed, not frozen). The batch ran under the main agent '
                                               '(production review, the migration/ records, zh_cn.json and the mapping) with a production builder (the 28D Java, the imported resources, runData), a GameTest '
                                               'verifier (ResourceCompletionGameTests, the six older expectations, verify_goal28d_resources.py, runData and the GameTest server), a reviewer, an explorer and this '
                                               'packaging verifier (the packager, the final runner, the casting-regression attribution) working in the same checkout; each wrote only its named files (the scope '
                                               'snapshots of the verifiers are indexed as evidence).',
                             goal28_md=dict(start_sha256=base['files'][GOAL28_RECORD], current_sha256=goal28_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p) if (ROOT/p).is_file() else None) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p, imported), owner=owner_of(p), owners=[owner_of(p)], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    need(baselines_now == start_baselines, 'A snapshot changed or was added (the original did not move: no new snapshot): '+str(sorted(set(baselines_now) ^ set(start_baselines))))
    snapshot_sha = sha(ROOT/SNAPSHOT)
    assert base['files'][SNAPSHOT] == snapshot_sha, 'review-4f5924e2b9e1 snapshot changed'
    production_changed = [p for p in production_java if p in changes]

    # The modified production files keep their start line endings (reported); new Java files are not mixed.
    gametest_edit_files = [p for p in EDITED_GAMETESTS if p in changes]
    start_text, line_endings = {}, {}
    for p in MODIFIED_JAVA + gametest_edit_files:
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
    unexpected_new = sorted(p for p in changes if p.startswith(SRC) and p.endswith('.java') and changes[p] == 'added' and p not in NEW_JAVA)
    need(not unexpected_new, 'new Java files under src/main/java other than the owner table\'s: '+str(unexpected_new))

    # Production Java facts: every line edit counted (+/- against the start bytes); the judged edits (the handoff owner table's content rules) follow.
    edit_summary, inserted_lines, insert_summary, added_lines, removed_lines = {}, {}, {}, {}, {}
    for p in MODIFIED_JAVA + gametest_edit_files:
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
    content_rules = {}
    # The production files only gain lines (handoff: insert-only, "add ... only"): the removed CODE lines are exactly the ones the owner table names (ALLOWED_REMOVED_CODE: the plain solid_fuel and
    # rocket_fuel items, the dead bush of the oil spot, the crystallizer's description line), plus a terminator or a call chain that an added line extends; comment lines are free. The
    # assembler additionally keeps its start rows and gets one contiguous block after the last start row.
    removed_code_report = {}
    for p in MODIFIED_JAVA:
        if p not in removed_lines: continue
        allowed = ALLOWED_REMOVED_CODE.get(p, ())
        explicit = [l.strip() for l in removed_lines[p] if allowed and l.strip().startswith(allowed)]
        rest = [l for l in removed_lines[p] if not (allowed and l.strip().startswith(allowed))]
        stray = stray_removals(rest, added_lines[p])
        if p == ASSEMBLER: stray = [l for l in stray if not l.startswith(ASSEMBLER_COMMENT_START[:60])]
        content_rules[p] = not stray and (not allowed or len(explicit) == len(allowed))
        if explicit or stray: removed_code_report[p] = dict(allowed_removed=explicit, allowed_tokens=list(allowed), stray=stray)
        need(content_rules[p], f'{p} removes start lines other than the owner table allows ({list(allowed)}) or that no added line extends: stray {stray[:4]}, allowed removed {explicit}')
    assembler_rule = None
    if ASSEMBLER in start_text:
        start_lines, live_lines = lines_of(start_text[ASSEMBLER]), lines_of((ROOT/ASSEMBLER).read_bytes())
        comment_now = [l for l in live_lines if l.strip() == ASSEMBLER_COMMENT_NOW]
        comment_was = [l for l in start_lines if l.strip() == ASSEMBLER_COMMENT_START]
        # The one rewritten comment line (the deferral note loses ass.chipBismoid) is mapped back before the insert-only judgement.
        normalised_start = [l.replace('ass.chipBismoid, ass.chipQuantum and ass.atomicClock (:129-134)', 'ass.chipQuantum and ass.atomicClock (:131-134)') for l in start_lines]
        inserted = insertions(normalised_start, live_lines)
        inserted_at = {i for i, _ in (inserted or [])}
        imports = [(i, l) for i, l in (inserted or []) if l.strip().startswith('import ')]
        block = [i for i, l in (inserted or []) if not l.strip().startswith('import ')]
        class_line = next((i for i, l in enumerate(live_lines) if re.match(r'\s*public class ', l)), None)
        last_start_row = max((i for i, l in enumerate(live_lines) if 'this.register(' in l and i not in inserted_at), default=-1)
        rule = dict(insert_only=inserted is not None, imports=[l.strip() for _, l in imports], block_lines=len(block), block_at=[block[0] + 1, block[-1] + 1] if block else None,
                    comment_rewritten=dict(was=len(comment_was), now=len(comment_now)))
        rule['imports_in_header'] = class_line is not None and all(i < class_line for i, _ in imports)
        rule['after_last_start_row'] = bool(block) and all(i > last_start_row for i in block)
        rule['holds'] = bool(inserted is not None and len(comment_now) == len(comment_was) == 1 and rule['imports_in_header'] and rule['after_last_start_row'])
        assembler_rule = rule
        content_rules[ASSEMBLER] = content_rules.get(ASSEMBLER, True) and rule['holds']
        need(rule['holds'], f'{ASSEMBLER} is not the start file plus imports and the appended rows (one rewritten deferral comment aside): {json.dumps(rule)[:400]}')
    # The six older GameTests the batch edits by design: the @GameTest methods and annotations are the start's. Five edit only expectations (every changed code line differs from its start line
    # in integer literals only); RecipeCompletionGameTests may also change a condition and add an assertion line (a row that used to be unregistered), so its changed lines are listed whole.
    gametest_edits = {}
    for p in gametest_edit_files:
        if p not in start_text: continue
        now_text, was_text = (ROOT/p).read_text(encoding='utf-8'), start_text[p].decode('utf-8')
        names_now, names_was = GAMETEST_METHOD.findall(now_text), GAMETEST_METHOD.findall(was_text)
        annotations_now, annotations_was = len(GAMETEST_ANNOTATION.findall(now_text)), len(GAMETEST_ANNOTATION.findall(was_text))
        touched = [l.strip() for l in removed_lines[p] + added_lines[p] if '@GameTest' in l or 'public static void' in l]
        code_was = [l for l in lines_of(start_text[p]) if not is_comment(l) and l.strip()]
        code_now = [l for l in lines_of((ROOT/p).read_bytes()) if not is_comment(l) and l.strip()]
        normalised = lambda s: re.sub(r'\d[\d_]*', '#', re.sub(r'"(?:[^"\\]|\\.)*"', '""', s))  # integer literals and the text of string literals (assertion messages) are free
        pairs, unpaired = [], []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, code_was, code_now, autojunk=False).get_opcodes():
            if tag == 'equal': continue
            if tag == 'replace' and i2 - i1 == j2 - j1:
                for a, b in zip(code_was[i1:i2], code_now[j1:j2]):
                    (pairs if normalised(a) == normalised(b) else unpaired).append((a.strip()[:160], b.strip()[:160]))
            else: unpaired.append((' | '.join(l.strip()[:80] for l in code_was[i1:i2]), ' | '.join(l.strip()[:80] for l in code_now[j1:j2])))
        literal_only = p in LITERAL_ONLY_GAMETESTS
        entry = dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p), added=len(added_lines[p]), removed=len(removed_lines[p]), game_tests=annotations_now, game_tests_at_start=annotations_was,
                     methods_unchanged=names_now == names_was,
                     rule=('only expectations change: every changed code line differs from its start line in integer literals and in the text of string literals (assertion messages) only; comments free' if literal_only else
                           'the @GameTest methods and annotations are the start\'s; the changed code lines are listed whole (an expectation such as a row that used to be unregistered, and the assertion text); comments free'),
                     changed_lines=[dict(was=a, now=b) for a, b in pairs], not_literal_only=[dict(was=a, now=b) for a, b in unpaired],
                     rule_holds=bool(pairs or unpaired) and not touched and (not unpaired if literal_only else len(unpaired) <= 6))
        gametest_edits[p] = entry
        need(entry['rule_holds'] and entry['methods_unchanged'] and annotations_now == annotations_was, f'{p} changed beyond its allowed edit ({entry["rule"]}): {json.dumps(entry, ensure_ascii=False)[:500]}')

    # 4. Resource completion against the original (EXPECTED holds the handoff figures; every value is computed from the sources; the NEO side is read from the source texts and the generated JSON;
    # the behaviour itself is the job of verify_goal28d_resources.py and ResourceCompletionGameTests).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    facts, bad = {}, []

    def fact(key, value, expected=None, ok=None):
        facts[key] = value if expected is None else dict(value=value, expected=expected)
        if ok is None: ok = expected is None or value == expected
        if not ok: bad.append(key)

    o = {path: original_text(path) for path in O_SOURCES}
    code = lambda p: strip_java_comments(neo_text(p))
    ocode = lambda p: strip_java_comments(o[p])
    registry = registry_names()
    n_vac_be, n_rot_be = J+'blockentity/machine/oil/MachineVacuumDistillBlockEntity.java', J+'blockentity/machine/MachineRotaryFurnaceBlockEntity.java'
    n_vac_block, n_rot_block = J+'blocks/machine/MachineVacuumDistillBlock.java', J+'blocks/machine/MachineRotaryFurnaceBlock.java'
    n_vac_recipes, n_rot_recipes = J+'inventory/recipes/VacuumRefineryRecipes.java', J+'inventory/recipes/RotaryFurnaceRecipes.java'
    n_willow = J+'blocks/generic/MustardWillowBlock.java'
    integer = lambda s: int(s.replace('_', '').rstrip('Ll'))
    dims = lambda text: (lambda m: [int(x) for x in m.group(1).replace(' ', '').split(',')] if m else None)(re.search(r'new int\[\]\s*\{([\d,\s]+)\}', text[max(text.find('getDimensions'), 0):]))
    tank_pattern = re.compile(r'new FluidTank\(Fluids\.(\w+),\s*([\d_]+)\)(?:\.withPressure\((\d+)\))?')
    tanks_of = lambda text: [[a, integer(b), int(c) if c else None] for a, b, c in tank_pattern.findall(text)]

    # 4a. The vacuum refinery (TileEntityMachineVacuumDistill.java:36, 48-52, 165; VacuumRefineryRecipes.java:20-40; MachineVacuumDistill.java:53): the four fraction percentages, the OIL and OIL_DS
    # rows and their four output fluids, the machine's power buffer, the oil tank (64000 mB, pressure 2) and the four 24000 mB output tanks, the 10000 power gate and the 8x2x2... multiblock size.
    def frac_consts(text): return {m.group(1): int(m.group(2)) for m in re.finditer(r'vac_frac_(\w+)\s*=\s*(\d+)', text)}

    def vacuum_rows(text):
        out = {}
        for m in re.finditer(r'recipes\.put\(Fluids\.(\w+),\s*new VacuumRefineryRecipe\(', text):
            out[m.group(1)] = re.findall(r'new FluidStack\(Fluids\.(\w+),\s*(\w+)\)', paren_body(text, m.end() - 1) or '')
        return out

    o_vac, n_vac = vacuum_rows(ocode(O_VRR)), vacuum_rows(code(n_vac_recipes))
    o_power, n_power = re.search(r'maxPower\s*=\s*([\d_]+)', ocode(O_TEVD)), re.search(r'MAX_POWER\s*=\s*([\d_]+)', code(n_vac_be))
    o_gate, n_gate = re.search(r'power\s*<\s*([\d_]+)\)\s*return', ocode(O_TEVD)), re.search(r'POWER_PER_OPERATION\s*=\s*([\d_]+)', code(n_vac_be))
    vac_value = dict(fractions=frac_consts(code(n_vac_recipes)), rows=n_vac, max_power=integer(n_power.group(1)) if n_power else None, power_gate=integer(n_gate.group(1)) if n_gate else None,
                     power_gate_used='this.power < POWER_PER_OPERATION' in code(n_vac_be), tanks=tanks_of(code(n_vac_be)), dimensions=dims(code(n_vac_block)), file_name='hbmVacuumRefinery.json')
    vac_expected = dict(fractions=frac_consts(ocode(O_VRR)), rows=o_vac, max_power=integer(o_power.group(1)) if o_power else None, power_gate=integer(o_gate.group(1)) if o_gate else None,
                        power_gate_used=True, tanks=tanks_of(ocode(O_TEVD)), dimensions=dims(ocode(O_MVD)), file_name='hbmVacuumRefinery.json')
    fact('vacuum_refinery', vac_value, vac_expected, ok=vac_value == vac_expected and len(o_vac) == 2 and set(o_vac) == {'OIL', 'OIL_DS'} and vac_expected['fractions'] == dict(heavy=40, reform=25, light=20, sour=15)
         and vac_expected['max_power'] == 1_000_000 and vac_expected['power_gate'] == 10_000 and len(vac_expected['tanks']) == 5)
    facts['vacuum_refinery_config_file'] = dict(original='hbmVacRefinery.json' if '"hbmVacRefinery.json"' in o[O_VRR] else None, neo='hbmVacuumRefinery.json' if '"hbmVacuumRefinery.json"' in neo_text(n_vac_recipes) else None)
    if facts['vacuum_refinery_config_file'] != dict(original='hbmVacRefinery.json', neo='hbmVacuumRefinery.json'): bad.append('vacuum_refinery_config_file')
    # 4b. The rotary furnace (RotaryFurnaceRecipes.java:39-54: 13 rows; TileEntityMachineRotaryFurnace.java:58, 68-79, 81-83, 156, 187; MachineRotaryFurnace.java:39): the rows NEO registers are
    # original rows (material, ingot quanta, duration, steam), the original rows NEO does not register are exactly the recorded omissions, and the burn module, the output cap, the tanks, the
    # steam formula, the pour offset and the multiblock size are the original's.
    def rotary_rows(text): return [(m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))) for m in ROTARY_ROW.finditer(text)]

    o_rows_rot, n_rows_rot = rotary_rows(ocode(O_RFR)), rotary_rows(code(n_rot_recipes))
    omitted = list(o_rows_rot)
    for row in n_rows_rot:
        if row in omitted: omitted.remove(row)
    expected_omitted = [(m.removeprefix('MAT_'), q, d, s) for m, q, d, s in ROTARY_OMITTED]
    burn_module = lambda text: (lambda m: re.sub(r'\s+', '', m.group(1)) if m else None)(re.search(r'new ModuleBurnTime\(\)(.*?);', text, re.S))
    rot_tokens = ('MaterialShapes.BLOCK.q(16)', 'new FluidTank(Fluids.NONE, 16_000)', 'new FluidTank(Fluids.STEAM, 12_000)', 'new FluidTank(Fluids.SPENTSTEAM, 120)',
                  'float steamUseMult = (float) (10 * Math.log10(processSpeed) + 1);', '2.875D', 'CrucibleUtil.pourSingleStack(')
    o_rot_text, n_rot_text = re.sub(r'\s+', ' ', ocode(O_TERF)).replace('(float)(', '(float) ('), re.sub(r'\s+', ' ', code(n_rot_be))
    rot_value = dict(rows_original=len(o_rows_rot), rows_neo=len(n_rows_rot), rows_neo_in_original=len(n_rows_rot) == len(o_rows_rot) - len(omitted), omitted=omitted, burn_module=burn_module(code(n_rot_be)),
                     tokens_neo={t: t in n_rot_text for t in rot_tokens}, dimensions=dims(code(n_rot_block)))
    rot_expected = dict(rows_original=EXPECTED['rotary_rows_original'], rows_neo=EXPECTED['rotary_rows_ported'], rows_neo_in_original=True, omitted=expected_omitted, burn_module=burn_module(ocode(O_TERF)),
                        tokens_neo={t: True for t in rot_tokens}, dimensions=dims(ocode(O_MRF)))
    fact('rotary_furnace', rot_value, rot_expected, ok=rot_value == rot_expected and rot_expected['burn_module'] is not None and 'setCokeTimeMod(1.25)' in (rot_expected['burn_module'] or '')
         and all(t in o_rot_text for t in rot_tokens if t != 'CrucibleUtil.pourSingleStack(') and 'CrucibleUtil.pourSingleStack(' in o_rot_text)
    # 4c. CrucibleUtil.pourSingleStack (CrucibleUtil.java:21 in the original, 9 parameters): NEO's overload has 7: the safe flag is fixed to true (the NEO javadoc says safe mode) and the quanta argument is left out
    # (it only limits spilling, which safe mode never does); the furnace calls it with (level, x, y, z, 6, stack, impact).
    o_crucible = original_text(ORIGINAL+'util/CrucibleUtil.java') if (SOURCE/(ORIGINAL+'util/CrucibleUtil.java')).is_file() else ''
    o_pour = re.search(r'public static (?:Mats\.)?MaterialStack pourSingleStack\(([^)]*)\)', o_crucible)
    n_pour = re.search(r'public static (?:Mats\.)?MaterialStack pourSingleStack\(([^)]*)\)', code(CRUCIBLE_UTIL))
    fact('pour_single_stack', dict(original=bool(o_pour), neo=bool(n_pour), parameters_original=len(split_args(o_pour.group(1))) if o_pour else None, parameters_neo=len(split_args(n_pour.group(1))) if n_pour else None),
         dict(original=True, neo=True, parameters_original=9, parameters_neo=7),
         ok=bool(o_pour and n_pour) and ' boolean safe,' in o_pour.group(0) and ' int quanta,' in o_pour.group(0) and len(split_args(o_pour.group(1))) == 9 and len(split_args(n_pour.group(1))) == 7
         and 'safe mode' in neo_text(CRUCIBLE_UTIL) and 'quanta argument' in neo_text(CRUCIBLE_UTIL))
    # 4d. The five shredder rows (ShredderRecipes.java:302-307: six scrap_oil rows, stone_porous has no NEO block): original block -> oily scraps, count 1, in the original order.
    o_scrap = re.findall(r'ShredderRecipes\.setRecipe\(ModBlocks\.(\w+),\s*new ItemStack\(ModItems\.scrap_oil,\s*1\)\);', ocode(O_SHREDDER))
    n_scrap = re.findall(r'registerIfAbsent\(new ItemStack\(NtmBlocks\.(\w+)\.get\(\)\),\s*new ItemStack\(NtmItems\.SCRAP_OIL\.get\(\),\s*1\)\);', code(SHREDDER))
    fact('shredder_rows', dict(neo=n_scrap, original=o_scrap, neo_blocks_registered=[registry.get(c) for c in n_scrap]),
         dict(neo=[n for _, n in SHREDDER_BLOCKS], original=[a for a, _ in SHREDDER_BLOCKS] + ['stone_porous'], neo_blocks_registered=[registry.get(n) for _, n in SHREDDER_BLOCKS]),
         ok=n_scrap == [n for _, n in SHREDDER_BLOCKS] and o_scrap == [a for a, _ in SHREDDER_BLOCKS] + ['stone_porous'] and len(n_scrap) == EXPECTED['shredder_rows'] and all(registry.get(c) for c in n_scrap))
    # 4e. The five crystallizer rows (CrystallizerRecipes.java:108-109, 212-214 and the class field productivity): input and count, acid fluid and amount, output, ticks and productivity. The
    # table grows from 60 to 65 rows: NEO registers most rows through loops, so the row count is the expectation the settled GameTests carry (SmokeGameTests, OverworldWorldgenGameTests,
    # NetherEndWorldgenGameTests and RadiationControlGameTests move 60 -> 65), not a source count.
    neo_cryst = {(m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), m.group(5), int(m.group(6)), float(m.group(7))) for m in CRYSTAL_NEO_ROW.finditer(code(CRYSTALLIZER))}
    o_cryst_lines = o[O_CRYST].split(chr(10))

    def original_cryst(*needles):
        line = next((l for l in o_cryst_lines if all(n in l for n in needles)), '')
        fluid = re.search(r'new FluidStack\(Fluids\.(\w+),\s*([\d_]+)\)', line)
        ticks = re.search(r'new CrystallizerRecipe\((?:[^()]|\([^()]*\))*?,\s*(\d+)\)', line)
        prod, req = re.search(r'\.prod\(([\d.]+)F\)', line), re.search(r'\.setReq\((\d+)\)', line)
        return [fluid.group(1) if fluid else None, integer(fluid.group(2)) if fluid else None, int(ticks.group(1)) if ticks else None, float(prod.group(1)) if prod else 0.0, int(req.group(1)) if req else 1]
    cryst_rows = {}
    for const_in, count_in, acid, amount, const_out, ticks, prod, token in CRYSTALLIZER_ROWS:
        original = original_cryst('oil_tar, '+token+'))', 'EnumTarType.WAX), 20)') if token.startswith('EnumTarType') else original_cryst(token)
        neo_key = (const_in, count_in, acid, amount, const_out, ticks, prod)
        cryst_rows[const_in] = dict(neo=neo_key in neo_cryst, original=original, expected=[acid, amount, ticks, prod, count_in], ok=neo_key in neo_cryst and original == [acid, amount, ticks, prod, count_in])
    edited_60_to_65 = {Path(p).stem: any('60' in c['was'] and '65' in c['now'] for c in (gametest_edits.get(p) or {}).get('changed_lines', []) + (gametest_edits.get(p) or {}).get('not_literal_only', [])) for p in (
        J+'gametest/SmokeGameTests.java', J+'gametest/OverworldWorldgenGameTests.java', J+'gametest/NetherEndWorldgenGameTests.java', J+'gametest/RadiationControlGameTests.java')}
    fact('crystallizer_rows', dict(rows={k: dict(neo=v['neo'], original=v['original'], ok=v['ok']) for k, v in cryst_rows.items()}, edited_60_to_65=edited_60_to_65,
                                   productivity_field='public float productivity = 0F;' in o[O_CRYST]),
         None, ok=all(v['ok'] for v in cryst_rows.values()) and len(CRYSTALLIZER_ROWS) == EXPECTED['crystallizer_rows_added'] and all(edited_60_to_65.values()) and 'public float productivity = 0F;' in o[O_CRYST]
         and EXPECTED['crystallizer_rows_start'] + EXPECTED['crystallizer_rows_added'] == EXPECTED['crystallizer_rows'])
    # 4f. The three assembly rows (AssemblyMachineRecipes.java:81-82, 129-130 inside if(no528), 327-328): setup, the product and its count, the input count list in order; the table grows from 82 to
    # 85 rows with the three rows appended after the last start row in the order platemixed, vaccumrefinery, chipBismoid (chipBismoid inside the not-528 branch).
    o_rows, o_order = recipe_rows(o[O_AMR])
    n_rows, n_order = recipe_rows(neo_text(ASSEMBLER))
    s_rows, s_order = recipe_rows(start_text[ASSEMBLER].decode('utf-8').replace('\r\n', '\n')) if ASSEMBLER in start_text else ({}, [])
    o_gates, n_gates = gated_spans(o[O_AMR], 'if(!GeneralConfig.enable528) {'), gated_spans(neo_text(ASSEMBLER), 'if(!NtmConfig.enable528()) {')
    assembly_rows, assembly_ok = {}, True
    for name, (product, count, setup, input_counts, original_product) in ASSEMBLY_ROWS.items():
        orow, nrow = o_rows.get(name), n_rows.get(name)
        of = row_facts(orow['stmt'], True) if orow else None
        nf = row_facts(nrow['stmt'], False, registry) if nrow else None
        if of and nf:
            # The versatile circuit is a DictFrame / plain item output in the two sources: read the circuit type from the statement text.
            if of['output'] is None and original_product in orow['stmt']: of['output'] = original_product
            if nf['output'] is None and product in nrow['stmt']: nf['output'] = registry.get(product)
        gated_o = bool(orow) and any(a < orow['pos'] < b for a, b in o_gates)
        gated_n = bool(nrow) and any(a < nrow['pos'] < b for a, b in n_gates)
        ok = bool(of and nf and of['setup'] == nf['setup'] == setup and of['input_counts'] == nf['input_counts'] == input_counts and of['output_count'] in (count, None) and nf['output_count'] in (count, None)
                  and nf['output'] == registry.get(product) and gated_o == gated_n == (name == 'ass.chipBismoid') and n_order.count(name) == 1 and not nf['expensive'])
        if ok and name != 'ass.chipBismoid': ok = of['output_count'] == nf['output_count'] == count and of['output'] == original_product
        assembly_rows[name] = dict(original_line=f'{O_AMR}:{orow["line"]}' if orow else None, neo_line=f'{ASSEMBLER}:{nrow["line"]}' if nrow else None, original=of, neo=nf, gated_original=gated_o, gated_neo=gated_n, ok=ok)
        assembly_ok = assembly_ok and ok
    fact('assembly_rows', {k: dict(original_line=v['original_line'], neo_line=v['neo_line'], setup=(v['neo'] or {}).get('setup'), output=(v['neo'] or {}).get('output'), output_count=(v['neo'] or {}).get('output_count'),
                                   input_counts=(v['neo'] or {}).get('input_counts'), gated_outside_528=v['gated_neo'], ok=v['ok']) for k, v in assembly_rows.items()}, None,
         ok=assembly_ok and n_order[len(s_order):] == list(ASSEMBLY_ROWS) and n_order[:len(s_order)] == s_order and len(s_order) == EXPECTED['assembler_rows_start']
         and len(n_order) == EXPECTED['assembler_rows'] and len(o_order) == EXPECTED['original_assembler_rows'])
    failed_rows = {k: dict(original=v['original'], neo=v['neo']) for k, v in assembly_rows.items() if not v['ok']}
    if failed_rows: facts['assembly_rows_failed'] = failed_rows
    fact('assembler_table', dict(start_rows=len(s_order), rows=len(n_order), start_order_kept=n_order[:len(s_order)] == s_order, appended=n_order[len(s_order):], original_rows=len(o_order)),
         dict(start_rows=EXPECTED['assembler_rows_start'], rows=EXPECTED['assembler_rows'], start_order_kept=True, appended=list(ASSEMBLY_ROWS), original_rows=EXPECTED['original_assembler_rows']))
    # 4g. The rotary furnace anvil construction row (AnvilRecipes.java:326-331): four inputs with the original's counts, tier 2, output the rotary furnace.
    def anvil_row(text, token):
        i = text.find(token)
        start = text.rfind('new AnvilConstructionRecipe(', 0, i) if i >= 0 else -1
        if start < 0: return None
        body = paren_body(text, start + len('new AnvilConstructionRecipe'))
        inputs = re.search(r'new AStack\[\]\s*\{(.*?)\}\s*,\s*new AnvilOutput', body or '', re.S)
        tier = re.search(r'\.setTier\((\d+)\)', text[start + len('new AnvilConstructionRecipe') + len(body or ''):][:60])
        return dict(counts=[stack_count(a) for a in split_args(inputs.group(1))] if inputs else None, tier=int(tier.group(1)) if tier else None)
    anvil_o, anvil_n = anvil_row(ocode(O_ANVIL), 'new AnvilOutput(new ItemStack(ModBlocks.machine_rotary_furnace))'), anvil_row(code(ANVIL), 'new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_ROTARY_FURNACE.asItem()))')
    fact('anvil_row', dict(neo=anvil_n, original=anvil_o), dict(neo=dict(counts=[8, 16, 4, 8], tier=2), original=dict(counts=[8, 16, 4, 8], tier=2)),
         ok=anvil_n == anvil_o == dict(counts=[8, 16, 4, 8], tier=2))
    # 4h. The two item tags (OreDictManager.java:322 ANY_COKE, :326 ANY_BISMOID): the generated tag JSON holds exactly the NEO members of the original dictionary.
    tags = {}
    for tag, (dictionary, token, members) in NEW_TAGS.items():
        t = generated_json(GENERATED_ROOT+f'data/ntm/tags/item/{tag}.json')
        tags[tag] = dict(original=dictionary, original_line=f'{O_OREDICT}:{original_line(O_OREDICT, token)}', values=sorted((t or {}).get('values', [])) if t else None,
                         expected=sorted('hbmsntm:'+registry.get(c, '?'+c) for c in members), declared=bool(re.search(r'ItemTags\.create\(ResourceLocation\.fromNamespaceAndPath\("ntm", "'+tag+r'"\)\)', code(ITEM_TAG_PROVIDER))))
    fact('item_tags', tags, None, ok=all(v['values'] == v['expected'] and v['declared'] and not any(e.startswith('hbmsntm:?') for e in v['expected']) for v in tags.values()) and len(tags) == 2)
    # 4i. solid_fuel and rocket_fuel (FuelHandler.java:19-27: single = 200, * 16 and * 32): burn times 3200 and 6400 as NEO FuelItems.
    o_single = re.search(r'int single = (\d+);', ocode(O_FUEL))
    o_solid, o_rocket = re.search(r'ModItems\.solid_fuel\)\)\s*return single \* (\d+);', ocode(O_FUEL)), re.search(r'ModItems\.rocket_fuel\)\)\s*return single \* (\d+);', ocode(O_FUEL))
    n_items = code(NTM_ITEMS)
    n_solid, n_rocket = re.search(r'SOLID_FUEL = ITEMS\.register\("solid_fuel", \(\) -> new FuelItem\(new Item\.Properties\(\), (\d+)\)\);', n_items), re.search(r'ROCKET_FUEL = ITEMS\.register\("rocket_fuel", \(\) -> new FuelItem\(new Item\.Properties\(\), (\d+)\)\);', n_items)
    fact('fuel_items', dict(neo=dict(solid_fuel=int(n_solid.group(1)) if n_solid else None, rocket_fuel=int(n_rocket.group(1)) if n_rocket else None),
                            original=dict(solid_fuel=int(o_single.group(1)) * int(o_solid.group(1)) if o_single and o_solid else None, rocket_fuel=int(o_single.group(1)) * int(o_rocket.group(1)) if o_single and o_rocket else None)),
         dict(neo=dict(solid_fuel=3200, rocket_fuel=6400), original=dict(solid_fuel=3200, rocket_fuel=6400)))
    # 4j. The mustard willow (BlockNTMFlower.java:141 growth water, BlockTallPlant.java:153 reset, :347 loot 3 + nextInt(4), OilSpot.java:63 one in 50 on grass or dirt): the generated loot table drops the
    # leaves uniformly 3..6 from the mature upper half, the block's growth reads water through FluidTags.WATER, the oil spot places the plant above grass and dirt (one in 50) instead of the dead bush.
    loot = generated_json(GENERATED_ROOT+'data/hbmsntm/loot_table/blocks/plant_mustard_willow.json') or {}
    uniform = [f['count'] for pool in loot.get('pools', []) for e in pool.get('entries', []) for f in e.get('functions', []) if f.get('function') == 'minecraft:set_count']
    n_oil_spot, o_oil_spot = code(OIL_SPOT), ocode(O_OILSPOT)
    fact('mustard_willow', dict(loot_count=[[c.get('min'), c.get('max')] for c in uniform], loot_condition=[p.get('conditions', [{}])[0].get('properties') for p in loot.get('pools', [])[1:]],
                                original_loot='3 + world.rand.nextInt(4)' in o[O_TALL], neo_water='FluidTags.WATER' in code(n_willow), original_water='cadmium willows can only grow with water' in o[O_FLOWER],
                                oil_spot_neo='addWillows && random.nextInt(50) == 0' in n_oil_spot and 'NtmBlocks.PLANT_MUSTARD_WILLOW.get().defaultBlockState()' in n_oil_spot and 'DEAD_BUSH' not in n_oil_spot,
                                oil_spot_original='addWillows && world.rand.nextInt(50) == 0' in o_oil_spot),
         dict(loot_count=[[3.0, 6.0]], loot_condition=[{'age': '4', 'half': 'upper'}], original_loot=True, neo_water=True, original_water=True, oil_spot_neo=True, oil_spot_original=True))
    facts['original_references'] = original_refs
    need(not bad, 'resource-completion facts differ from the original or the handoff figures (or the NEO source / generated file is missing or its text differs): '+', '.join(
        f'{k}={json.dumps(facts.get(k + "_failed", facts[k]), ensure_ascii=False, default=str)[:300]}' for k in bad))
    # The materials/reachability record (the main agent's; pending until written): it must say which recipes are reachable and which inputs have no source.
    ledger = read(ROOT/LEDGER) if (ROOT/LEDGER).is_file() else None
    if need(ledger is not None, 'record missing: '+LEDGER):
        need(str(ledger.get('goal')) == '28D', f'{LEDGER} is not the Goal 28D ledger')

    # 5. Resources: the 16 byte imports (original worktree file and stored blob at 4f5924e2b), against migration/goal28d-resource-ownership.json (its source paths are checked here, not trusted).
    ownership = read(ROOT/RESOURCE_OWNERSHIP) if (ROOT/RESOURCE_OWNERSHIP).is_file() else None
    entries = {a.get('target_path'): a for a in (ownership or {}).get('imported_assets', [])}
    imported_facts = {}
    for target in sorted(imported):
        entry = entries.get(target)
        if not need(entry is not None, 'no resource-ownership entry for the imported resource '+target): continue
        original = entry['source_path']
        if not (SOURCE/original).is_file():
            need(False, 'no original file for the imported resource '+target+' (expected '+original+')')
            continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        imported_facts[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size, original_worktree_sha256=sha(SOURCE/original),
                                      original_blob_sha256=hashlib.sha256(blob).hexdigest(), start_sha256=base['files'].get(target), replaced=target in base['files'])
        # The original checkout converts text files to CRLF (core.autocrlf true): the .obj worktree files equal the import byte for byte, their stored blobs differ in line endings only.
        imported_facts[target]['blob_line_endings_only'] = blob != checked_out and blob.replace(bytes([13, 10]), bytes([10])) == checked_out.replace(bytes([13, 10]), bytes([10]))
        need((ROOT/target).read_bytes() == checked_out and (blob == checked_out or imported_facts[target]['blob_line_endings_only']), f'{target} is not byte-identical to the original {original} (worktree; the stored blob at {SOURCE_HEAD[:8]} may differ in line endings only)')
    need(len(imported) == EXPECTED['imported_assets'], f'{len(imported)} imported resources, the handoff lists {EXPECTED["imported_assets"]}')
    need(not [t for t in imported_facts.values() if t['replaced']], 'an imported resource replaces a start file: '+str(sorted(t for t, v in imported_facts.items() if v['replaced'])))
    if need(ownership is not None, 'record missing: '+RESOURCE_OWNERSHIP):
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == imported, f'{RESOURCE_OWNERSHIP} imported_assets are not the {len(imported)} imported resources at {SOURCE_HEAD[:8]}: {sorted(set(entries) ^ imported)[:4]}')
        need(not ownership.get('replaced_target_files') and not ownership.get('already_present'), f'{RESOURCE_OWNERSHIP} lists replaced or already present targets')
        for target, entry in entries.items():
            if target in imported_facts:
                need(entry.get('source_path') == imported_facts[target]['original_path'] and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('size') == (ROOT/target).stat().st_size,
                     f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original: {target}')

    # 6. features.json: two new groups vacuum-refinery and rotary-furnace (partial-unverified at the original commit); every other group keeps reviewed_source_commit (the original did not move) and
    # its status; only the groups in NOTES_MAY_CHANGE may change notes / target_paths / target_watch / source lists.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit 4f5924e2b'
    assert (NOTES_GROUPS) <= set(start_features) and not set(NEW_FEATURES) & set(start_features), 'The start mapping does not hold the groups the handoff allows to change, or already holds the new groups'
    may_change = lambda i: i in NOTES_MAY_CHANGE
    need(set(by_id) == set(start_features) | set(NEW_FEATURES), 'features.json group ids are not the start ids + vacuum-refinery and rotary-furnace: '+str(sorted(set(by_id) ^ (set(start_features) | set(NEW_FEATURES)))))
    for new_id in NEW_FEATURES:
        group_new = by_id.get(new_id)
        if need(group_new is not None, 'migration/features.json lacks the group '+new_id):
            need(group_new.get('status') == 'partial-unverified' and group_new.get('reviewed_source_commit') == SOURCE_HEAD, f'features.json group {new_id} is not partial-unverified at {SOURCE_HEAD[:8]}')
    unlisted = [p for p in O_SOURCES if not p.startswith(O_RES) and not any(feature_matches(f, 'source', p) for f in features)]
    need(not unlisted, f'features.json lists these original sources in no group (source_paths / source_watch): {unlisted}')
    mapped_java = [p for p in MODIFIED_JAVA + NEW_PRODUCTION if not any(feature_matches(f, 'target', p) for f in features)]
    need(not mapped_java, f'features.json maps these changed Java paths in no group (target_paths / target_watch): {mapped_java[:4]}')
    group_vac, group_rot = by_id.get('vacuum-refinery'), by_id.get('rotary-furnace')
    if group_vac and group_rot:
        vac_paths = [n_vac_be, n_vac_block, n_vac_recipes, J+'inventory/menus/MachineVacuumDistillMenu.java']
        rot_paths = [n_rot_be, n_rot_block, n_rot_recipes, J+'inventory/menus/MachineRotaryFurnaceMenu.java']
        need(all(feature_matches(group_vac, 'target', p) for p in vac_paths) and all(feature_matches(group_rot, 'target', p) for p in rot_paths),
             'features.json groups vacuum-refinery / rotary-furnace do not map their block entity, block, recipe table and menu: '+str([p for p in vac_paths if not feature_matches(group_vac, 'target', p)] + [p for p in rot_paths if not feature_matches(group_rot, 'target', p)]))
    absent = sorted({p for f in features for p in f.get('source_paths', []) if not (SOURCE/p).is_file()})
    need(not absent, f'features.json source_paths missing in the original: {absent[:6]}')
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    need(all(may_change(i) for i in notes_changed), 'features.json groups whose notes changed beyond '+str(sorted(NOTES_MAY_CHANGE))+': '+str([i for i in notes_changed if not may_change(i)]))
    paths_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('target_paths') != start_features[i].get('target_paths'))
    need(all(may_change(i) for i in paths_changed), 'features.json groups whose target_paths changed beyond the allowed groups: '+str([i for i in paths_changed if not may_change(i)]))
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    free = lambda i: ('notes', 'target_watch', 'target_paths', 'reviewed_source_commit', 'source_paths', 'source_watch') + (('evidence', 'acceptance') if may_change(i) else ())
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in free(i)} != {k: v for k, v in start_features[i].items() if k not in free(i)})
    appended_only = sorted(i for i in by_id if i in start_features and may_change(i) and not all(by_id[i].get(k, [])[:len(start_features[i].get(k, []))] == start_features[i].get(k, []) for k in ('evidence', 'acceptance')))
    need(not shrunk and not other_fields and not appended_only, f'features.json previous groups lost target_watch entries {shrunk} or changed other fields {other_fields}'
         + ('' if not appended_only else f' (evidence / acceptance changed other than by appending: {appended_only})'))
    watch_grown = sorted(i for i, f in by_id.items() if i in start_features and set(f.get('target_watch', [])) - set(start_features[i].get('target_watch', [])))
    need(all(may_change(i) for i in watch_grown), 'features.json groups whose target_watch grew beyond the allowed groups: '+str([i for i in watch_grown if not may_change(i)]))
    source_changed = sorted(i for i, f in by_id.items() if i in start_features and (f.get('source_paths') != start_features[i].get('source_paths') or f.get('source_watch') != start_features[i].get('source_watch')))
    need(all(may_change(i) for i in source_changed), 'features.json groups whose source_paths / source_watch changed beyond the allowed groups: '+str([i for i in source_changed if not may_change(i)]))
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped; the main agent adds target_paths / target_watch to vacuum-refinery and rotary-furnace): '+str(unmapped[:6]))
    features_record = dict(new_groups=list(NEW_FEATURES), notes_changed=notes_changed, target_paths_changed=paths_changed, target_watch_grown=watch_grown, source_lists_changed=source_changed,
                           groups_allowed=sorted(NOTES_MAY_CHANGE))

    # 7. Language and the generated tree: 9 new keys (8 upstream, 1 local); nothing changed or removed; the stamp must be current, the generated additions the 23 expected files.
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
    local_keys = {k: dict(en=en_now.get(k), zh=zh_now.get(k), map_kind=(map_now.get(k) or {}).get('kind')) for k in LOCAL_KEYS}
    need(all(v['en'] and v['zh'] and v['map_kind'] == 'local' for v in local_keys.values()), 'a local language key lacks English, Chinese or its local mapping entry: '+str(local_keys))
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_en = dict(added=sorted(KEYS), removed=sorted(REMOVED_KEYS), changed=sorted(EN_CHANGED))
    expected_zh = dict(added=sorted(KEYS), removed=sorted(REMOVED_KEYS), changed=sorted(ZH_CHANGED))
    expected_map = dict(added=sorted(KEYS), removed=sorted(REMOVED_KEYS), changed=sorted(set(EN_CHANGED) | set(ZH_CHANGED)))
    need(len(KEYS) == EXPECTED['language_added'], f'expected new language keys: {len(KEYS)}, the handoff lists {EXPECTED["language_added"]}')
    need(en_delta == expected_en, 'generated en_us.json delta is not the 9 new keys: '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_zh, 'zh_cn.json delta is not the 9 new keys: '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_map, 'zh_cn-map.json delta is not the 9 new entries: '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal28c totals'
    delta_net = len(KEYS) - len(REMOVED_KEYS)
    need(len(en_now) == totals['en_us'] + delta_net and len(zh_now) == totals['zh_cn'] + delta_net and len(map_now) == totals['zh_cn_map'] + delta_net,
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal28c totals {totals} + {delta_net}')
    map_kinds, start_kinds = dict(Counter(e.get('kind') for e in map_now.values())), dict(Counter(e.get('kind') for e in map_start.values()))
    kinds_added = Counter((map_now.get(k) or {}).get('kind') for k in KEYS)
    expected_kinds = {k: start_kinds.get(k, 0) + kinds_added.get(k, 0) for k in set(start_kinds) | set(kinds_added)}
    expected_kinds = {k: v for k, v in expected_kinds.items() if v}
    need(start_kinds == totals['zh_cn_map_by_kind'] and map_kinds == expected_kinds and map_kinds.get('deferred') == EXPECTED['deferred_entries'],
         f'mapping kinds are {map_kinds}, expected the goal28c kinds {totals["zh_cn_map_by_kind"]} adjusted by the added keys {expected_kinds} (deferred {EXPECTED["deferred_entries"]} unchanged)')
    expected_added_kinds = {k: v for k, v in {'upstream': UPSTREAM_ADDED, 'local': LOCAL_ADDED}.items() if v}
    need(dict(kinds_added) == expected_added_kinds, f'new mapping entries are {dict(kinds_added)}, expected {UPSTREAM_ADDED} upstream and {LOCAL_ADDED} local')
    need((len(en_now), len(zh_now), len(map_now)) == (EXPECTED['en_total'], EXPECTED['zh_total'], EXPECTED['map_total']),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)}, the handoff expects {EXPECTED["en_total"]} / {EXPECTED["zh_total"]} / {EXPECTED["map_total"]}')
    need(all((map_now.get(k) or {}).get('kind') == 'upstream' for k in LANG_SOURCE), 'mapping entries of the upstream keys are not kind upstream: '+str([k for k in LANG_SOURCE if (map_now.get(k) or {}).get('kind') != 'upstream']))
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if not (ROOT/'src/generated/resources'/p).is_file() or normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    stamp_current = not stale and not mismatch and not unrecorded
    need(stamp_current, f'{STAMP} not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
    start_generated = set(start_stamp_generated)
    generated_added = sorted(set(stamp['generated']) - start_generated)
    generated_retired = sorted(start_generated - set(stamp['generated']))
    generated_changed = sorted(p for p in start_generated if p in stamp['generated'] and base['files'][GENERATED_ROOT+p] != sha(ROOT/'src/generated/resources'/p))
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    changed_allowed = {EN_ENTRY, 'data/minecraft/tags/block/mineable/pickaxe.json'}
    need(set(generated_changed) == changed_allowed, f'Generated resources changed since the start are not exactly en_us.json and the block pickaxe tag: {generated_changed[:8]}')
    need(sorted(GENERATED_ROOT+p for p in generated_added) == GENERATED_ADDED_PATHS, 'generated additions differ from the 23 expected files: extra %s, missing %s' % (
        sorted({GENERATED_ROOT+p for p in generated_added} - set(GENERATED_ADDED_PATHS))[:6], sorted(set(GENERATED_ADDED_PATHS) - {GENERATED_ROOT+p for p in generated_added})[:6]))
    counts_added = dict(blockstates=len([p for p in generated_added if '/blockstates/' in p]), block_models=len([p for p in generated_added if '/models/block/' in p]),
                        item_models=len([p for p in generated_added if '/models/item/' in p]), loot_tables=len([p for p in generated_added if '/loot_table/' in p]),
                        item_tags=len([p for p in generated_added if p.startswith('data/ntm/tags/item/')]))
    need(counts_added == GENERATED_COUNTS and len(generated_added) == EXPECTED['generated_added'], f'generated additions are {counts_added} ({len(generated_added)}), the handoff expects {GENERATED_COUNTS} ({EXPECTED["generated_added"]})')
    need(len(stamp['generated']) == prior_receipt['generated_resource_count'] + len(generated_added), f'generated resource count {len(stamp["generated"])} is not the goal28c count {prior_receipt["generated_resource_count"]} + {len(generated_added)}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted([STAMP] + [GENERATED_ROOT+p for p in generated_added] + [GENERATED_ROOT+p for p in generated_changed])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, the stamp additions and the stamp changes: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))

    # 8. Evidence: GameTest log, audits, Gradle logs, diff, the final suite run, the verifier report, the casting attribution, compare and the batch's own scripts and records.
    evidence = {}
    gametest_line = gametest_count = None
    resource_lines = []
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
    resource_test_names = sorted(GAMETEST_METHOD.findall((ROOT/RESOURCE_TESTS).read_text(encoding='utf-8'))) if (ROOT/RESOURCE_TESTS).is_file() else []
    resource_annotations = annotations(ROOT/RESOURCE_TESTS) if (ROOT/RESOURCE_TESTS).is_file() else 0
    need(bool(resource_test_names) and resource_annotations == len(resource_test_names), f'{RESOURCE_TESTS} holds {resource_annotations} @GameTest annotations and {len(resource_test_names)} parsed methods (or the file does not exist yet)')
    need(gametest_added == resource_annotations == EXPECTED['gametest_added'] and total_now == EXPECTED['gametest_total'] == EXPECTED['gametest_start'] + EXPECTED['gametest_added'],
         f'GameTest sources grew by {gametest_added} tests ({total_start} -> {total_now}), ResourceCompletionGameTests holds {resource_annotations}, the handoff expects +{EXPECTED["gametest_added"]} = {EXPECTED["gametest_total"]}')
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
            need(all((GAMETEST_MARKER % n) in text for n in resource_test_names), 'GameTest log lacks "[hbm-28d] <name> passed" for: '+str([n for n in resource_test_names if (GAMETEST_MARKER % n) not in text]))
            resource_lines = [l.split('[hbm-28d] ', 1)[1].strip() for l in text.splitlines() if '[hbm-28d] ' in l and ' passed' not in l.split('[hbm-28d] ', 1)[1]]
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries, audit_comparison = {}, {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal28d/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad_findings = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad_findings and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad_findings))
        # This batch adds language keys and resources, so the info / review counts may differ from the previous receipt: recorded, not required equal.
        audit_comparison[key] = dict(previous=prior_receipt['audits'][key], now=audit['summary'], equal=audit['summary'] == prior_receipt['audits'][key])
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal28d/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if name == 'production-vs-start.diff':
            if (OUT/name).is_file() and (OUT/name).stat().st_size > 0: evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)  # judged below
            continue
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal28d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    named = list(START_EVIDENCE) + list(REVIEW_EVIDENCE)
    named += sorted(p.name for pattern in ('handoff-*.md', 'write_records*.py', 'write_delivery_records*.py', 'builder-*.log', 'verifier-*.log') for p in OUT.glob(pattern) if p.name not in named)
    for name in named:
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start') + ' evidence missing: build/migration/goal28d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for sub in ('edit-scripts', 'reversal-mismatch', 'verifier-pkg'):
        for p in sorted((OUT/sub).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts: evidence[p.relative_to(ROOT).as_posix()] = sha(p)
    for rel in EXTERNAL_EVIDENCE:
        if need((ROOT/rel).is_file(), 'evidence missing: '+rel+' (the GameTest verifier\'s scope snapshot)'): evidence[rel] = sha(ROOT/rel)
    for name in (FAIL_SET_DIFF, 'chain-exits-compare.txt', 'chain-done-compare.txt'):
        if (OUT/name).is_file(): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # The casting regressions (goal27a_casting_regression_run.py, unchanged wrapper): one record per suite in the final rerun's own directory; its transcript is hashed with it.
    casting = {}
    for suite in CASTING_SUITES:
        rec_path = CASTING_DIR/f'{suite}-compat.json'
        if not need(rec_path.is_file(), f'evidence missing: build/migration/goal28d/final/castingsuites/{suite}-compat.json (goal27a_casting_regression_run.py {suite}, redirected into final/ by run_final.py)'): continue
        rec = read(rec_path)
        transcript = ROOT/rec['transcript'] if rec.get('transcript') else None
        casting[suite] = dict(record=rec_path.relative_to(ROOT).as_posix(), exit=rec.get('exit'), mode=rec.get('mode'), blockers=rec.get('blockers'), stages=rec.get('stages'),
                              javac_errors_by_attribution=rec.get('javac_errors_by_attribution'), transcript=rec.get('transcript'))
        evidence[rec_path.relative_to(ROOT).as_posix()] = sha(rec_path)
        if need(transcript is not None and transcript.is_file(), f'{rec_path.name} names no existing transcript'): evidence[transcript.relative_to(ROOT).as_posix()] = sha(transcript)
    attribution = None
    if need((OUT/CASTING_ATTRIBUTION).is_file(), 'evidence missing: build/migration/goal28d/'+CASTING_ATTRIBUTION+' (casting_attribution.py, after the final rerun)'):
        att = read(OUT/CASTING_ATTRIBUTION)
        problems = []
        if att.get('mode') != 'compare' or att.get('missing_inputs'): problems.append(f'mode {att.get("mode")!r}, missing inputs {att.get("missing_inputs")}')
        if att.get('baseline_sha256') != sha(BASELINE) or att.get('tool_sha256') != sha(OUT/'casting_attribution.py'): problems.append('written by another baseline or another version of casting_attribution.py')
        if att.get('old_dir') != (GOAL28C_OUT/'final/castingsuites').relative_to(ROOT).as_posix() or att.get('new_dir') != CASTING_DIR.relative_to(ROOT).as_posix(): problems.append(f'compares {att.get("old_dir")} with {att.get("new_dir")}')
        if sorted(att.get('suites', {})) != sorted(CASTING_SUITES): problems.append('suites '+str(sorted(att.get('suites', {}))))
        for suite, entry in att.get('suites', {}).items():
            for side in ('old', 'new'):
                s = entry.get(side) or {}
                if not s.get('parse_matches_record'): problems.append(f'{suite} {side}: the parsed javac errors do not match the record')
                if side == 'new' and suite in casting and s.get('record_sha256') != sha(ROOT/casting[suite]['record']): problems.append(f'{suite}: the new record changed after the attribution')
            for e in entry.get('new_errors', []) + entry.get('moved', []):
                file = e.get('at', '').rsplit(':', 1)[0] if 'at' in e else (e.get('identity') or {}).get('file', '')
                if e.get('attribution') == 'unattributed': problems.append(f'{suite}: unattributed error {e.get("at") or e.get("identity")}')
                elif e.get('attribution') == '28D change' and file not in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed to a 28D change but the file did not change')
                elif e.get('attribution') == 'not 28D' and file in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed "not 28D" but the file changed')
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
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal28d/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files and edited GameTests against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    diffed_modified = [p for p in MODIFIED_JAVA + gametest_edit_files if p in changes]
    listed_in_diff = NEW_JAVA + diffed_modified
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal28d/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in diffed_modified) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(p in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([p for p in listed_in_diff if p not in diff_text]))
    final = None
    # The suites of the goal28c final run plus the Goal28D verifier (the two casting regressions are in the goal28c set and run unchanged, redirected into final/; verify_goal28c_recipes.py is an old suite now).
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal28c final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal28D suite is already in the goal28c final run'
    assert OLD_SUITE_28C in reference_suites, 'The goal28c final run does not hold the Goal28C verifier: '+OLD_SUITE_28C
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal28d/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal28c final set + the Goal28D verifier: '+str(sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    # The Goal28D verifier report. It records no production hashes, no start commit and no GameTest-log block, so the packager judges it here: it passed with no failed check and every
    # mutation detected, it was run with the final log and the final JAR (command and the JAR hash it recorded), against the original at 4f5924e2b, and its sections V0..V9 all passed.
    verifier = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal28d/'+VERIFY_REPORT+' (written by verify_goal28d_resources.py in the final suite rerun)'):
        report = read(OUT/VERIFY_REPORT)
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        problems = []
        if report.get('pass') is not True or report.get('failed') or summary_part.get('checks_failed') != 0: problems.append('not a passing run: pass %s, failed %s' % (report.get('pass'), report.get('failed')))
        if report.get('undetected_mutations') or summary_part.get('mutations_detected') != summary_part.get('mutations_total') or summary_part.get('mutations_skipped'): problems.append(
            'mutations: detected %s of %s, undetected %s, skipped %s' % (summary_part.get('mutations_detected'), summary_part.get('mutations_total'), report.get('undetected_mutations'), summary_part.get('mutations_skipped')))
        if report.get('command') != NEW_SUITE: problems.append('run with another command: %s' % report.get('command'))
        if report.get('original_head') != SOURCE_HEAD: problems.append('records another original commit')
        if ((report.get('extra') or {}).get('jar') or {}).get('jar_sha256') != sha(JAR): problems.append('was run against another JAR than build/libs (rerun the verifier after the last build): %s' % ((report.get('extra') or {}).get('jar') or {}).get('jar_sha256'))
        sections = report.get('sections') or {}
        if sorted(sections) != [f'V{i}' for i in range(10)] or any(s.get('status') != 'PASS' or s.get('failed') for s in sections.values()): problems.append('sections: '+str({k: v.get('status') for k, v in sections.items()}))
        need(not problems, VERIFY_REPORT+' is not a passing verifier run on the final tree: '+'; '.join(problems))
        mutation_entries = list((report.get('mutations') or {}).values()) if isinstance(report.get('mutations'), dict) else []
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=VERIFY_TOOL, tool_sha256=sha(ROOT/VERIFY_TOOL) if (ROOT/VERIFY_TOOL).is_file() else None,
                        mutations_detected=f'{summary_part.get("mutations_detected")}/{summary_part.get("mutations_total")}', mutations_total=summary_part.get('mutations_total'), checks_passed=summary_part.get('checks_passed'),
                        command=report.get('command'), jar_sha256=((report.get('extra') or {}).get('jar') or {}).get('jar_sha256'), sections={k: v.get('checks') for k, v in sections.items()},
                        mutation_entries=len(mutation_entries), note='the report records no production_sha256, start_target_head or GameTest-log block (unlike the Goal23B..Goal28C reports): freshness is the recorded JAR hash and the command')
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(re.findall(r'(?:VacuumRefineryRecipes|RotaryFurnaceRecipes|TileEntityMachineVacuumDistill|TileEntityMachineRotaryFurnace|MachineVacuumDistill|MachineRotaryFurnace|BlockNTMFlower|'
                                                    r'BlockTallPlant|OilSpot|ShredderRecipes|CrystallizerRecipes|AssemblyMachineRecipes|AnvilRecipes|FuelHandler|OreDictManager|CrucibleUtil)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        verifier['original_references'] = verifier_references
    # The compare: the original did not move since the 28A observation point (unchanged in 28B, 28C and 28D), so ONE compare, against review-4f5924e2b9e1.json (the snapshot is not rewritten). Original 0/0/0.
    # The target set is this batch's own compare-inventory paths (added = absent from the snapshot, modified = present) plus the residual between the snapshot and the start (computed from the
    # snapshot's raw hashes: the snapshot is the Goal28A tree, so the residual is the Goal28B and Goal28C deliveries' compare-inventory paths).
    snap = read(ROOT/SNAPSHOT)
    need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '', SNAPSHOT+' is not a clean observation of the original at 4f5924e2b')
    snap_files = snap['target']['files']
    start_inventory = {p: h for p, h in base['files'].items() if in_compare_inventory(p)}
    residual_modified = sorted(p for p, h in start_inventory.items() if p in snap_files and snap_files[p]['raw_sha256'] != h)
    residual_added = sorted(p for p in start_inventory if p not in snap_files)
    residual_removed = sorted(p for p in snap_files if in_compare_inventory(p) and p not in start_inventory)
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_added = sorted(set(residual_added) | {p for p in own_target if p not in snap_files})
    expected_modified = sorted((set(residual_modified) | {p for p in own_target if p in snap_files}) - set(expected_added))
    expected_target = sorted(set(expected_added) | set(expected_modified))
    snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=snapshot_sha, new_snapshot=False, source_commit=snap['source']['commit'], snapshot_sha256_at_start=base['files'][SNAPSHOT],
                    residual_modified=residual_modified, residual_added=residual_added, residual_removed=residual_removed)
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal28d/'+COMPARE+' (compare against '+SNAPSHOT+': original 0/0/0, target set of %d paths = this batch\'s %d compare-inventory paths + %d residual)' % (
            len(expected_target), len(own_target), len(set(residual_modified) | set(residual_added)))):
        cmp = read(OUT/COMPARE)
        need(cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, COMPARE+' is not against the 4f5924e2b snapshot')
        need(cmp['current_target_state']['commit'] == start_head, COMPARE+' records another target commit than the start commit')
        counts_cmp = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(all(v == 0 for v in counts_cmp['source'].values()) and counts_cmp['target']['removed'] == 0, COMPARE+' original is not 0/0/0 or the target removed a path: '+str(counts_cmp))
        listed_added = sorted(p for p in compare_paths(cmp['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
        listed_modified = sorted(p for p in compare_paths(cmp['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
        need(listed_added == expected_added and listed_modified == expected_modified,
             f'{COMPARE} target set differs: added extra %s missing %s, modified extra %s missing %s' % (sorted(set(listed_added) - set(expected_added))[:6], sorted(set(expected_added) - set(listed_added))[:6],
                                                                                                 sorted(set(listed_modified) - set(expected_modified))[:6], sorted(set(expected_modified) - set(listed_modified))[:6]))
        need(not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], COMPARE+' reports unmapped changes: '+str(cmp['unmapped_changes'])[:300])
        need(not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], COMPARE+' reports removed features or missing files')
        states = Counter(f.get('state') for f in cmp['features'])
        need(len(cmp['features']) == len(features) and set(states) <= {'no-observed-file-change', 'target-changed'} and all(any(f.get('id') == n and f.get('state') == 'target-changed' for f in cmp['features']) for n in NEW_FEATURES),
             f'{COMPARE} feature states are {dict(states)}, expected only no-observed-file-change / target-changed over {len(features)} groups, with {list(NEW_FEATURES)} target-changed')
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states), target_listed=len(listed_added) + len(listed_modified),
                       target_added=len(listed_added), target_modified=len(listed_modified), own_paths=len(own_target), residual=len(set(residual_modified) | set(residual_added)),
                       changed_groups=sorted(f['id'] for f in cmp['features'] if f.get('state') == 'target-changed'))
        evidence[compare['path']] = compare['sha256']

    # 9. JAR: build/libs is what gets packaged; delta against the previous package (goal28c), every entry owned by goal28d or a recompile.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the goal28c package (run the final build)')
    if True:  # --check also runs the delta code (against the current build/libs)
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            differs = [p for p in stamp['generated'] if p not in names or not (ROOT/'src/generated/resources'/p).is_file() or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [p[len(RES):] for p in sorted(imported) if p[len(RES):] not in names or jar.read(p[len(RES):]) != (ROOT/p).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, the imported resources, zh_cn.json or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == expected_en and zh_jar == expected_zh, 'JAR en_us.json / zh_cn.json differ from the goal28c package by something other than the Goal28D delta: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            recompile_only = {n for n in RECOMPILE_ONLY if n in jar_delta['modified'] and recompile_equal(n, prior.read(n), jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        generated_entries = set(generated_added) | set(generated_changed) | {ZH_ENTRY} | {p[len(RES):] for p in imported}
        entry_owners, unowned = {}, []
        for kind, entries_now in jar_delta.items():
            for n in entries_now:
                owner = []
                if n.endswith('.class') and owner_class(n) in production_java: owner = [OWNER]
                elif kind == 'modified' and n == 'META-INF/MANIFEST.MF': owner = [OWNER]
                elif kind in ('added', 'modified') and n in generated_entries and not n.endswith('.class'): owner = [OWNER]
                elif kind == 'modified' and n in recompile_only and owner_class(n) not in changes: owner = [RECOMPILE_OWNER]
                if not owner: unowned.append(f'{kind}: {n}' + (' [source ' + owner_class(n) + ' unchanged since the start: a recompile difference, not a source change]' if n.endswith('.class') and owner_class(n) not in changes else ''))
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without an owner (only classes of the owner-table Java sources and the edited older GameTests, the generated additions / changes (23 files, en_us.json, the block pickaxe tag), '
             'zh_cn.json, the 16 imported resources and META-INF/MANIFEST.MF are owned): '+str(unowned[:10]))
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in production_java if p in changes]
        allowed_classes = set(changed_java)
        need(set(class_owners) <= allowed_classes and set(changed_java) <= set(class_owners),
             'Changed Java sources and goal28d JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners))) + '; unexpected: '+str(sorted(set(class_owners) - allowed_classes)))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == generated_entries, 'JAR non-class delta differs from the generated additions / changes + zh_cn.json + the imported resources: extra %s, missing %s' % (
            sorted(non_class - generated_entries)[:8], sorted(generated_entries - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for p in MODIFIED_JAVA + gametest_edit_files:
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

    need(small_fixes_after_goal28c == [], 'migration/README.md (start copy) names small fixes above the Goal28C line (they would be packaged with goal28d; list them in the receipt): '+str(small_fixes_after_goal28c))

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added), generated_modified=generated_changed,
                   generated_added_counts=counts_added, imported_resources=sorted(imported), start_drift=sorted(drift_report), small_fixes_after_goal28c=small_fixes_after_goal28c,
                   start_reconstruction={k: start_reconstruction[k] for k in ('files', 'migration_files', 'start_paths', 'start_copies', 'hash_only', 'recomputed_equal')},
                   language_delta=dict(en=en_delta, zh=zh_delta, map=map_delta), language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, line_endings=line_endings, content_rules=content_rules, removed_code=removed_code_report, assembler_rule=assembler_rule,
                   gametest_edits={p: dict(added=e['added'], removed=e['removed'], rule_holds=e['rule_holds']) for p, e in gametest_edits.items()},
                   resource_completion={k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v, default=str)) < 200 else f'<{len(v)} items>') for k, v in facts.items()}, resource_completion_facts_bad=bad,
                   assembly_rows_ok=sorted(k for k, v in assembly_rows.items() if v['ok']), crystallizer_rows_ok=sorted(k for k, v in cryst_rows.items() if v['ok']), features=features_record,
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_resource_tests=resource_test_names, final_suites_expected=final_expected,
                   audit_comparison=audit_comparison,
                   casting_regressions={s: dict(exit=c['exit'], mode=c['mode'], blockers=len(c['blockers'] or []), javac_errors_by_attribution=c['javac_errors_by_attribution']) for s, c in casting.items()},
                   casting_attribution=opt(attribution, 'summary'),
                   compare=opt(compare, 'counts'), compare_target_expected=len(expected_target), compare_added_expected=len(expected_added), compare_own_paths=len(own_target),
                   compare_residual=dict(modified=len(residual_modified), added=len(residual_added), removed=len(residual_removed)),
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta, class_owners=class_owners,
                   protected_paths=len(protected), old_releases_preserved=len(old_releases), preserved_release_files=len(old_release_files),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)),
                   out_files_not_indexed=unindexed)
    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)

    # The receipt: assembled in both modes (None where the evidence does not exist yet in --check); only the real run writes it, and there every need() above raised.
    dest = RELEASE/RELEASE_NAME
    digest = sha(JAR)
    hashes = {p: sha(ROOT/p) for p in reports if (ROOT/p).is_file()}
    resource_completion = dict(neo=MODIFIED_JAVA + NEW_PRODUCTION, original=O_SOURCES, facts=facts, expected=EXPECTED, known_differences=KNOWN_DIFFERENCES, carried_known_differences_28c=KNOWN_DIFFERENCES_28C,
                               original_references=original_refs,
                               assembly_rows={k: dict(original_line=v['original_line'], neo_line=v['neo_line'], original=v['original'], neo=v['neo'], ok=v['ok']) for k, v in assembly_rows.items()},
                               assembler_rule=assembler_rule, crystallizer_rows=cryst_rows, item_tags=tags, imported_resources=imported_facts, resource_ownership_record=RESOURCE_OWNERSHIP, reachability_record=LEDGER,
                               language_keys=language_keys, local_language_keys=local_keys, resource_lines_from_gametest_log=resource_lines,
                               note='Resource completion: the vacuum refinery (recipe table hbmVacuumRefinery.json, four fractions 40/25/20/15, 1000000 power buffer, 64000 mB oil tank at pressure 2, four 24000 mB output tanks, '
                                    '10000 power per refinement, multiblock 8-high) and the rotary furnace (8 of the 13 original rows, the burn module, 12000 mB steam and 120 mB spent steam tanks, a 16-block output '
                                    'cap, the pour at 2.875 blocks, CrucibleUtil.pourSingleStack); the mustard willow (five growth stages, leaves dropped 3 to 6 at maturity, one in 50 on oil spot grass and dirt); '
                                    'five shredder rows to oily scraps; five acidizer rows; three assembly rows; the rotary furnace anvil row (tier 2, 8/16/4/8 inputs); the tags ntm:gems_coke and ntm:nuggets_bismoid; solid '
                                    'and rocket fuel burn times 3200 and 6400; nine language keys. The recipe_completion key of Goal28C is dropped: that domain belongs to the previous receipt.')
    casting_record = dict(attribution=attribution, suites=casting, wrapper='tools/migration/goal27a_casting_regression_run.py (unchanged)', policy='tools/migration/goal27a_casting_compat.py (unchanged)',
                          note='The two frozen isolated casting regressions (verify_goal10a.py, verify_goal5a_casting.py) run through the unchanged Goal27A wrapper in the final rerun, redirected into '
                               'build/migration/goal28d/final/castingsuites; both already stopped at javac on the Goal26D to Goal28C trees, so none of their assertions is reached. casting-attribution.json '
                               'pairs the javac errors of the Goal28C final run with the Goal28D run and attributes every new or moved error by file to a Goal28D change or to "not 28D"; it is evidence about javac '
                               'in the frozen stub worlds only.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(resource_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   uncommitted_start=uncommitted_start, start_reconstruction=start_reconstruction,
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(committed='the mod rename 66a00353 (on c1f6f397, 66050453 and the Goal 27 delivery adaf265c)', uncommitted='the Goal28A-28C delivery', start_build_sha256=previous_sha,
                                      push_commit_parent=chain[1], untrack_commit=chain[2], goal27_delivery_commit=chain[3], small_fixes_after_goal28c=small_fixes_after_goal28c,
                                      note=f'The start tree is HEAD 66a00353 (the mod rename, = origin/master) with the UNCOMMITTED Goal28A-28C delivery in the worktree (packaged as goal28a, goal28b and goal28c, never committed). The start is '
                                           f'RECONSTRUCTED, not frozen (start_reconstruction): {len(base["files"])} start hashes ({tracked_count} tracked-tree and {migration_count} migration/ hashes) are the goal28c baseline overridden '
                                           f'by the goal28c receipt; {len(base["start_copies"])} start copies exist where their bytes hash to the recorded value, the generation stamp has a hash only. build/libs at the start is taken to be the '
                                           f'goal28c package {previous_sha[:8]} (the baseline records no build hash); no small fix lies between the goal28c package and this start, so the JAR delta against the goal28c package is entirely '
                                           'this batch. The original did not move (4f5924e2b); paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, line_endings=line_endings, content_rules=content_rules, removed_code=removed_code_report, gametest_edits=gametest_edits,
                   start_copies_supplement=[],
                   resource_completion=resource_completion, casting_attribution=casting_record, features=features_record,
                   language=dict(changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']), added=dict(en_us=en_delta['added'], zh_cn=zh_delta['added'], zh_cn_map=map_delta['added']),
                                 removed=dict(en_us=en_delta['removed'], zh_cn=zh_delta['removed'], zh_cn_map=map_delta['removed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds), jar_delta=language,
                                 start_sha256={p: base['files'][p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD, LANG_PROVIDER)},
                                 note='Goal28D adds 9 keys, 8 upstream (the vacuum refinery, rotary furnace, mustard willow and mature willow blocks, the willow leaf item, the oily scraps item, the two container titles) '
                                      'and one local (container.machineRotaryFurnace.empty); nothing is changed or removed; the '+str(EXPECTED['deferred_entries'])+' deferred entries are unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith(CARRIED_REPINS)},
                   repinned_since_goal28c_start={},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok'), old_machine_suites_through=OLD_MACHINE_SUITES, casting_suites_through=['goal27a_casting_regression_run.py verify_goal10a',
                                                                                                                                                                            'goal27a_casting_regression_run.py verify_goal5a_casting']),
                   verifier=verifier,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_resource_tests=resource_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, ResourceCompletionGameTests (names in new_resource_tests): what those tests '
                                      'assert about the vacuum refinery and rotary furnace recipes and machines, the mustard willow growth, loot and oil spot placement, the shredder, crystallizer and assembly rows, the anvil '
                                      'row, the tags and the fuel items; no client (the machine GUIs, the renderers, the JEI categories and the block and item icons are not drawn), no real player, no saved world, no '
                                      'survival crafting chain.'),
                   audits=audit_summaries, audit_comparison=audit_comparison, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(old_release_files),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + [p for p in OPTIONAL_RECORDS if p in changes],
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['recipe_completion (the Goal28C-only domain key; Goal28D adds resource_completion)',
                                 'upstream / compare.old / snapshot.new (the original did not move this batch: no classification, no old compare, no new snapshot; the compare is against review-4f5924e2b9e1)',
                                 'small_fixes / ledger_edit (no small fix and no ledger edit since the goal28c package; start_content.small_fixes_after_goal28c is the empty check)',
                                 'casting_regressions (the Goal27A key; Goal28D carries casting_attribution as Goal27B to Goal28C did: the wrapper and the two suites are unchanged, only their javac errors are attributed)',
                                 'target_status / stamp_state / old_release_files / previous_receipt_protected_paths / startup freeze fields (the start is reconstructed; see start_reconstruction)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun (the old isolated suites through the goal26c wrapper and the two casting regressions through the unchanged goal27a wrapper, whose javac '
                            'errors are attributed by casting_attribution.py), one compare against the review-4f5924e2b9e1 snapshot, and one static review. The start was reconstructed after the first 28D write. No '
                            'in-game client test was run: no machine was built or used by a real player, the machine GUIs, the renderers, the JEI categories, the mustard willow models and the Chinese UI are not '
                            'seen on screen; no survival chain (an RBMK, chlorine, a tier 3 anvil, the vacuum refinery) was run; no dedicated server beyond GameTest; the Goal 28 acceptance checklist '
                            'GOAL28D-ACCEPTANCE.md is written, not run.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False, default=str))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal28d JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal28c package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
