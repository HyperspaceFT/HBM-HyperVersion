"""Package Goal28A (the first batch of Goal 28: the upstream delta review aee05a40f..4f5924e2b with the fluid burner and GenericRecipe icon adaptations, config-gated nether and end
ore generation (two new codec types and a worldgen config group), six nether ore blocks, smoldering netherrack and infernal coal with drops and processing rows, nether uranium and coal
outgassing, hand drills, the JEI anvil tier text and variants, the dropped scraps' entity name and the NetherEndWorldgenGameTests), cumulatively on the goal27d package, without
replacing any previous delivery. It also packages the three small fixes made after goal27d (D3 AnvilRecipeHandler.java, D5 ContaminationUtil.java, the mod rename in gradle.properties).

python -B -X utf8 tools/migration/package_goal28a.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal28a/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal28a/gametest-final.log (the GameTest dedicated-server
log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a --check run also proves the receipt code; only the real mode
writes it.

The frozen start is build/migration/goal28a/baseline.json: NEO HEAD 66a00353 (the mod rename, = origin/master at the freeze; parent c1f6f397, then 66050453 which untracked migration/,
then adaf265c which committed the Goal 27 delivery and the D3 / D5 fixes) with a CLEAN worktree. Unlike every earlier start, migration/ is Git-ignored, so the baseline hashes the tracked
tree (`files`, 10,270 hashes) and the ignored migration/ directory from disk (`migration_files`, 619 hashes) separately; this packager merges them (one start-hash map) and finds changes
under migration/ by walking the directory, because `git ls-files` no longer lists it. freeze_start.py copied 51 planned files into baseline-files/. build/libs at the start is
0fdd8ac0...f581, the post-rename JAR that already holds D3, D5 and the rename, NOT the goal27d package (2a380c7d...a6b0). The original HEAD moved this batch: 4f5924e2b (39 commits past
the aee05a40f snapshot, 66 files): the packager checks the classification against git's name-status, the compare against the aee05a40f snapshot (compare-old.json: original +5/~61/-1,
target = the goal27d compare target set + the small fixes + this batch), the new snapshot review-4f5924e2b9e1.json and the compare against it (compare.json: 0/0/0, unmapped 0/0).
Every change since the start is computed from the baseline hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified
production files are compared with their start bytes (baseline-files, or the start-commit blob) and their +/- lines are reported. The JAR delta against the goal27d package is attributed per
entry (goal28a, or one of the three small fixes, whose byte changes are also recorded by verifier-pkg/small-fix-jar-delta.json); any entry without an owner fails. Counts that records quote
(suites, GameTests, generated resources, classes, releases, language keys) are computed here from the original and NEO sources and the GameTest log where they can be.

The receipts that hash records (goal21a..goal27d, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start (the acceptance checklists, GOAL21D.md,
GOAL22C.md, goal21d-static-review.md and the goal24a working notes, known from earlier batches; the goal27d receipt: GOAL27D-ACCEPTANCE.md, GOAL25D-ACCEPTANCE.md, GOAL26D-ACCEPTANCE.md,
written or extended after its packaging); they are listed in the receipt as start drift and must still equal their Goal28A start hash; no receipt is rewritten and no other protected path
may drift, except migration/GOAL24B.md, whose one ledger sentence about the plutonium and polonium sources the task book changes (a single replaced line, reported as ledger_edit). Every
Goal 27 and earlier record, GOAL28B/C/D.md, GOAL28-THREAD-PROMPTS.md and SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL28.md is a shared record, GOAL28A.md the task
book and delivery record (hashed by the receipt).

Like the packagers of 24A (the last batch that moved the original) this one carries two compare runs (compare-old.json, compare.json) and the upstream classification of the moved range;
it adds the nether_end_worldgen facts (checked against the original and NEO source texts). The Goal27D-only receipt key foundry_molds is dropped and the receipt says so; the two old casting
regressions run unchanged through the goal27a wrapper in the final rerun and their javac errors are attributed by casting_attribution.py (casting-attribution.json)."""
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
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE
from package_goal23b import report_problems
from package_goal27a import is_comment, body_of, OLD_MACHINE_SUITES
from package_goal27c import strip_noise, cut_methods, stray_removals, recompile_equal, RECOMPILE_ONLY, RECOMPILE_OWNER
from package_goal27d import OUT as GOAL27D_OUT, BASELINE as GOAL27D_BASELINE, protected_paths as goal27d_protected_paths

OUT = ROOT/'build/migration/goal28a'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
NAME_STATUS = OUT/'name-status.txt'
UPSTREAM_DELTA = OUT/'upstream-delta.json'
SMALL_FIX_DELTA = OUT/'verifier-pkg/small-fix-jar-delta.json'
REFERENCE_PREVIOUS = GOAL27D_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL27D_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal27d/hbmsntm-198A-goal27d.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal28a'
RELEASE_NAME = 'hbmsntm-198A-goal28a.jar'
OWNER = 'goal28a'
PREVIOUS_OWNER = 'goal27d'
SMALL_FIX_OWNERS = {'D3': 'small-fix-D3', 'D5': 'small-fix-D5', 'mod-rename': 'small-fix-mod-rename'}
# The original moved this batch (28A-1): SOURCE_HEAD is where the original stands now, SOURCE_PREVIOUS the commit the old snapshot and the goal27d receipt record.
SOURCE_HEAD = '4f5924e2b9e1e49cee61787674d2658acb3d559b'
SOURCE_PREVIOUS = 'aee05a40f10fb7bb9b042b65eccaa449ecc1672d'
START_PREFIX = '66a00353'
START_PARENT_PREFIX = 'c1f6f397'
UNTRACK_PREFIX = '66050453'
GOAL27_DELIVERY_PREFIX = 'adaf265c'
TASK_BOOK = 'migration/GOAL28A.md'
SNAPSHOT_OLD = 'migration/baselines/review-aee05a40f10f.json'
SNAPSHOT_NEW = 'migration/baselines/review-4f5924e2b9e1.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
SRC = 'src/main/java/'
J = SRC+'com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
TEXTURE_ROOT = RES+'assets/hbmsntm/textures/'
O_RES = RES+'assets/hbm/'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a', 'goal26b', 'goal26c', 'goal26d', 'goal27a', 'goal27b', 'goal27c'}

# Production (owner goal28a): the NEW Java files (the two worldgen codec types with their registry class, the smoldering netherrack feature, the nether coal and smolder blocks, and the
# GameTest class) and the MODIFIED production sources (the handoff owner table); the optional ones and the edited older GameTest are listed separately.
NEW_JAVA = [J+p+'.java' for p in (
    'world/gen/ConfigGatedAddFeaturesBiomeModifier', 'world/gen/ConfigCountPlacement', 'world/gen/NtmWorldgenCodecs', 'world/feature/SmolderingNetherrackFeature',
    'blocks/generic/NetherCoalBlock', 'blocks/generic/SmolderBlock', 'gametest/NetherEndWorldgenGameTests')]
(GATED_MODIFIER, COUNT_PLACEMENT, WORLDGEN_CODECS, SMOLDERING_FEATURE, NETHER_COAL_BLOCK, SMOLDER_BLOCK, WORLDGEN_TESTS) = NEW_JAVA
MODIFIED_JAVA = [J+p+'.java' for p in (
    'config/CommonConfig', 'world/gen/NtmConfiguredFeatures', 'world/gen/NtmPlacedFeatures', 'world/gen/NtmBiomeModifiers', 'world/feature/NtmFeatures', 'main/NuclearTechMod',
    'blocks/NtmBlocks', 'blocks/generic/OutgasBlock', 'items/NtmItems', 'inventory/NtmCreativeTabs', 'inventory/recipes/CentrifugeRecipes', 'inventory/recipes/CrystallizerRecipes',
    'inventory/recipes/ShredderRecipes', 'inventory/recipes/loader/GenericRecipe', 'blockentity/machine/heater/HeaterOilburnerBlockEntity', 'blocks/machine/heater/HeaterOilburnerBlock',
    'inventory/menus/HeaterOilburnerMenu', 'inventory/screens/HeaterOilburnerScreen', 'handler/jei/AnvilRecipeHandler', 'handler/jei/AnvilConstructionRecipeHandler', 'items/CopperScrapsItem',
    'datagen/NtmBlockStateProvider', 'datagen/NtmItemModelProvider', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmRecipeProvider', 'datagen/NtmLanguageProvider')]
(COMMON_CONFIG, CONFIGURED_FEATURES, PLACED_FEATURES, BIOME_MODIFIERS_JAVA, NTM_FEATURES, NUCLEAR_TECH_MOD, NTM_BLOCKS, OUTGAS_BLOCK, NTM_ITEMS, CREATIVE_TABS, CENTRIFUGE_RECIPES,
 CRYSTALLIZER_RECIPES, SHREDDER_RECIPES, GENERIC_RECIPE, BURNER_BE, BURNER_BLOCK, BURNER_MENU, BURNER_SCREEN, JEI_ANVIL, JEI_ANVIL_CONSTRUCTION, COPPER_SCRAPS, STATE_PROVIDER,
 ITEM_MODEL_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER, RECIPE_PROVIDER, LANG_PROVIDER) = MODIFIED_JAVA
# The older GameTest the batch edits by design: RBMKCoreGameTests.rbmk_screwdriver_tooling's oil-burner block (4f5924e2b removed the burner's screwdriver config, HeaterOilburner.java).
# Only that method may change; RadiationControlGameTests and SmokeGameTests may change only their row-count checks; the @GameTest methods and annotations are the start's.
EDITED_GAMETESTS = [J+'gametest/'+n+'.java' for n in ('RBMKCoreGameTests', 'RadiationControlGameTests', 'SmokeGameTests')]
(RBMK_TESTS, RADIATION_TESTS, SMOKE_TESTS) = EDITED_GAMETESTS
# RadiationControlGameTests and SmokeGameTests pin the default acidizer (crystallizer) table at 47 rows and the centrifuge table at 77: the batch appends rows (53 and 80), so only those count checks change.
ROW_COUNT_CHECK = re.compile(r'check\((?:defaults\.size\(\)|rows|centrifuge) == (\d+),')
SCREWDRIVER_METHOD = r'public static void rbmk_screwdriver_tooling\([^\n]*'
# Optional (changed only when the batch needed it; reported): the screwdriver/tooling item (hand drill durability), an additive GameTest helper.
OPTIONAL_JAVA = [J+p+'.java' for p in ('items/tools/ToolingItem', 'gametest/SmokeTestSupport')]
OLDER_GAMETEST_DIR = J+'gametest/'
# The three small fixes made after the goal27d package, packaged and regression-run with this batch: file -> (fix id, README mark).
SMALL_FIX_FILES = {J+'handler/jei/AnvilRecipeHandler.java': 'D3', J+'util/ContaminationUtil.java': 'D5', 'gradle.properties': 'mod-rename'}
SMALL_FIX_JAVA = [p for p in SMALL_FIX_FILES if p.startswith(SRC)]
SMALL_FIX_JAR_ENTRIES = {'META-INF/neoforge.mods.toml': 'mod-rename'}
# Must stay byte-identical to the start (the handoff list), plus every other GameTest class and every other handler/jei class: see main().
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'world/feature/OilBubbleFeature', 'world/feature/ColtanDepositFeature', 'world/feature/BedrockOilDepositFeature', 'world/feature/LandmineFeature', 'world/feature/CrashedBombFeature',
    'world/feature/BlueprintChestFeature', 'blocks/machine/FoundryOutletBlock', 'blockentity/machine/FoundryOutletBlockEntity', 'items/machine/MoldItem', 'inventory/recipes/CrucibleRecipes',
    'util/ContaminationUtil')]
UNCHANGED_DIRS = (J+'inventory/material/', J+'blockentity/machine/Foundry', RES+'data/hbmsntm/worldgen/')
# Older tools that must equal their start bytes (handoff list); every file of the two frozen casting regression folders is added in main().
OLD_TOOLS_FROZEN = ['tools/migration/'+p for p in ('package_goal27d.py', 'verify_goal27d_molds.py', 'package_goal27c.py', 'verify_goal27c_foundry.py', 'package_goal27b.py', 'verify_goal27b_crucible_alloys.py',
                                                    'package_goal27a.py', 'verify_goal27a_material_system.py', 'goal27a_casting_regression_run.py', 'goal27a_casting_compat.py', 'goal27a_scrap_textures.py',
                                                    'goal27a_effect_icons.py', 'goal26c_oldsuite_run.py', 'goal26c_oldsuite_compat.py', 'verify_goal10a.py', 'verify_goal10a_resources.py',
                                                    'verify_goal5a_casting.py', 'verify_goal5a_casting_resources.py', 'goal10a_scrap_textures.py', 'goal10a_mutation_check.py')]
FROZEN_TOOL_DIRS = ('tools/migration/goal10a_regression/', 'tools/migration/goal5a_casting_regression/')
NEW_TOOLS = ['tools/migration/verify_goal28a_worldgen.py', 'tools/migration/package_goal28a.py']
TOOLS = NEW_TOOLS
# Hand-written resources (byte imports from the original at 4f5924e2b; migration/goal28a-resource-ownership.json lists them): the six nether ore block textures and the nether coal
# animation, the infernal coal and two hand drill item textures, and the REPLACED fluid burner GUI (the start file is a local pixel edit of the pre-delta original; the bytes are replaced).
ORE_NAMES = ('tungsten', 'sulfur', 'fire', 'coal', 'smoldering', 'cobalt')
ITEM_TEXTURES = ('coal_infernal', 'hand_drill', 'hand_drill_desh')
TEXTURE_PATTERN = re.compile(re.escape(TEXTURE_ROOT)+r'(block/ore_nether_(?:'+'|'.join(ORE_NAMES)+r')\.png(?:\.mcmeta)?|item/(?:'+'|'.join(ITEM_TEXTURES)+r')\.png|gui/machine/gui_oilburner\.png)')
GUI_TEXTURE = TEXTURE_ROOT+'gui/machine/gui_oilburner.png'
REQUIRED_TEXTURES = ([TEXTURE_ROOT+'block/ore_nether_'+n+'.png' for n in ORE_NAMES] + [TEXTURE_ROOT+'block/ore_nether_coal.png.mcmeta'] + [TEXTURE_ROOT+'item/'+n+'.png' for n in ITEM_TEXTURES]
                     + [GUI_TEXTURE])
RESOURCE_OWNERSHIP = 'migration/goal28a-resource-ownership.json'
# Generated by runData: nine worldgen configured and placed features, four biome modifiers, six blockstates and block models, nine item models, six loot tables, four recipes with their
# advancements (hand_drill, hand_drill_desh, the nether tungsten and cobalt smelting rows); en_us.json and the pickaxe tag change; the stamp.
WORLDGEN_NAMES = ('ore_nether_uranium', 'ore_nether_tungsten', 'ore_nether_sulfur', 'ore_nether_fire', 'ore_nether_coal', 'ore_nether_cobalt', 'ore_nether_plutonium', 'ore_tikite', 'smoldering_netherrack')
BIOME_MODIFIER_NAMES = ('add_nether_ores', 'add_nether_plutonium_ore', 'add_smoldering_netherrack', 'add_end_ores')
BLOCK_NAMES = tuple('ore_nether_'+n for n in ORE_NAMES)
ITEM_MODEL_NAMES = BLOCK_NAMES + ITEM_TEXTURES
RECIPE_NAMES = ('hand_drill', 'hand_drill_desh', 'ingot_tungsten_from_smelting_ore_nether_tungsten', 'ingot_cobalt_from_smelting_ore_nether_cobalt')
GENERATED_ADDED = re.compile(re.escape(GENERATED_ROOT)+r'(?:assets/hbmsntm/blockstates/(?:'+'|'.join(BLOCK_NAMES)+r')\.json|assets/hbmsntm/models/block/(?:'+'|'.join(BLOCK_NAMES)+r')\.json|'
                             r'assets/hbmsntm/models/item/(?:'+'|'.join(ITEM_MODEL_NAMES)+r')\.json|data/hbmsntm/loot_table/blocks/(?:'+'|'.join(BLOCK_NAMES)+r')\.json|'
                             r'data/hbmsntm/recipe/[a-z0-9_]+\.json|data/hbmsntm/advancement/recipes/[a-z]+/[a-z0-9_]+\.json|'
                             r'data/hbmsntm/worldgen/configured_feature/(?:'+'|'.join(WORLDGEN_NAMES)+r')\.json|data/hbmsntm/worldgen/placed_feature/(?:'+'|'.join(n+'_placed' for n in WORLDGEN_NAMES)+r')\.json|'
                             r'data/hbmsntm/neoforge/biome_modifier/(?:'+'|'.join(BIOME_MODIFIER_NAMES)+r')\.json)')
GENERATED_COUNTS = dict(blockstates=6, block_models=6, item_models=9, loot_tables=6, recipes=4, advancements=4, configured_features=9, placed_features=9, biome_modifiers=4)
PICKAXE_TAG = GENERATED_ROOT+'data/minecraft/tags/block/mineable/pickaxe.json'
REQUIRED_GENERATED = sorted([GENERATED_ROOT+f'assets/hbmsntm/blockstates/{n}.json' for n in BLOCK_NAMES] + [GENERATED_ROOT+f'assets/hbmsntm/models/block/{n}.json' for n in BLOCK_NAMES]
                            + [GENERATED_ROOT+f'assets/hbmsntm/models/item/{n}.json' for n in ITEM_MODEL_NAMES] + [GENERATED_ROOT+f'data/hbmsntm/loot_table/blocks/{n}.json' for n in BLOCK_NAMES]
                            + [GENERATED_ROOT+f'data/hbmsntm/recipe/{n}.json' for n in RECIPE_NAMES]
                            + [GENERATED_ROOT+f'data/hbmsntm/worldgen/configured_feature/{n}.json' for n in WORLDGEN_NAMES]
                            + [GENERATED_ROOT+f'data/hbmsntm/worldgen/placed_feature/{n}_placed.json' for n in WORLDGEN_NAMES]
                            + [GENERATED_ROOT+f'data/hbmsntm/neoforge/biome_modifier/{n}.json' for n in BIOME_MODIFIER_NAMES])
GENERATED_TAGS = re.compile(re.escape(GENERATED_ROOT)+r'data/[a-z_]+/tags/.*\.json')  # the tag files that gained the ores (pickaxe.json is required, others allowed)
GENERATED_MODIFIED = [STAMP, EN, PICKAXE_TAG]
# Language: the 21 new keys (six block names, the infernal coal and two hand drills, the eleven worldgen config keys and the burner's ignition text), the two heater_oilburner descriptions
# reworded. The handoff text said en +34; the files give +21 (confirmed: en, zh and the mapping all +21 / -0 / 2 changed).
UPSTREAM_KEYS = {'block.hbmsntm.ore_nether_'+n: 'tile.ore_nether_'+n+'.name' for n in ORE_NAMES}
UPSTREAM_KEYS.update({'item.hbmsntm.coal_infernal': 'item.coal_infernal.name', 'item.hbmsntm.hand_drill': 'item.hand_drill.name', 'item.hbmsntm.hand_drill_desh': 'item.hand_drill_desh.name'})
CONFIG_KEYS = ('enablePlutoniumNetherOre', 'endOres', 'endTikiteSpawnRate', 'netherCoalSpawnRate', 'netherCobaltSpawnRate', 'netherOres', 'netherPhosphorusSpawnRate', 'netherPlutoniumSpawnRate',
               'netherSulfurSpawnRate', 'netherTungstenSpawnRate', 'netherUraniumSpawnRate')
LOCAL_KEYS = ['hbmsntm.configuration.worldgen.'+k for k in CONFIG_KEYS] + ['heater_oilburner.ignition']
KEYS = sorted(list(UPSTREAM_KEYS) + LOCAL_KEYS)
REMOVED_KEYS = []
LANG_CHANGED = ['block.hbmsntm.heater_oilburner.desc', 'tile.heater_oilburner.desc']
EN_CHANGED = ZH_CHANGED = LANG_CHANGED
LANG_SOURCE = UPSTREAM_KEYS
UPSTREAM_ADDED = 9
LOCAL_ADDED = 12
# Hashed by the receipt (frozen afterwards): this batch's reports and the new snapshot; any further migration/goal28a-* or GOAL28A-* record is hashed as well.
REPORTS = ['migration/GOAL28A.md', 'migration/GOAL28A-ACCEPTANCE.md', 'migration/goal28a-upstream-classification.json', RESOURCE_OWNERSHIP, 'migration/goal28a-static-review.md',
           'migration/goal28a-materials-review.json', 'migration/goal28a-localization-review.json', SNAPSHOT_NEW]
CLASSIFICATION = REPORTS[2]
LEDGER = REPORTS[5]
BATCH_RECORD = re.compile(r'migration/(goal28a-[^/]+\.(json|md)|GOAL28A-[^/]+\.md)')
GOAL28_RECORD = 'migration/GOAL28.md'
LEDGER_EDIT = 'migration/GOAL24B.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md', GOAL28_RECORD, LOCALIZATION_RECORD]
# Shared records the batch may leave untouched ("if touched" in the handoff).
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
# The records of the other batches and the files no batch of this kind touches: no change is expected.
PLANNING_FROZEN = ['migration/SURVIVAL-PLAYABILITY.md', 'migration/GOAL28-THREAD-PROMPTS.md', 'migration/GOAL28B.md', 'migration/GOAL28C.md', 'migration/GOAL28D.md']
# Every Goal 27 and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 27), except the one ledger sentence of GOAL24B.md.
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-7])(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-7])(?!\d)[a-z]?-[^/]+)')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = (NEW_JAVA + MODIFIED_JAVA + EDITED_GAMETESTS + REQUIRED_TEXTURES + REQUIRED_GENERATED + GENERATED_MODIFIED + [ZH_INPUT] + TOOLS + REPORTS + [LEDGER_EDIT]
                    + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS])
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-28a] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the
# sessions of the batch. Every top-level handoff-*.md and *-report.md of OUT is indexed as well.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_head.txt', 'main-notes.md', 'handoff-builder.md',
                  'handoff-builder-m2.md', 'handoff-verifier.md', 'handoff-packaging.md', 'handoff-reviewer.md', 'chain.sh', 'gw.sh', 'import_textures.py', 'add_zh.py', 'add_zh_oilburner.py',
                  'make_classification.py', 'png_pixels.py', 'make_production_diff.py', 'upstream-delta.json', 'name-status.txt')
# Review files under OUT; each must exist and is indexed by the receipt. --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'casting_attribution.py', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-progress.md', 'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier-pkg/small-fix-jar-delta.json', 'verifier-gt/scope-before.txt',
                   'verifier-gt/scope-after.txt', 'verify-final.out', 'compare-old.log', 'snapshot.log', 'compare.log', 'localization-final.log', 'resources-audit-final.log', 'packaged-resources-final.log')
CASTING_ATTRIBUTION = 'casting-attribution.json'
CASTING_DIR = OUT/'final/castingsuites'
CASTING_SUITES = ('verify_goal10a', 'verify_goal5a_casting')
FAIL_SET_DIFF = 'final/fail-set-diff.json'
COMPARE_OLD = 'compare-old.json'
COMPARE_EXITS = ('compare_old', 'snapshot', 'compare')
GAMETEST_LOG = 'build/migration/goal28a/gametest-final.log'
NEW_SUITE = 'verify_goal28a_worldgen.py --gametest-log build/migration/goal28a/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
OLD_SUITE_27D = 'verify_goal27d_molds.py --gametest-log build/migration/goal27d/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# features.json: ONE new group world-generation; materials, centrifuge, crystallization, shredder and fluid-burner may change notes / target_paths / target_watch (handoff); every group
# advances reviewed_source_commit to 4f5924e2b; no group changes status.
NEW_FEATURE = 'world-generation'
NOTES_MAY_CHANGE = {'materials', 'centrifuge', 'crystallization', 'shredder', 'fluid-burner', NEW_FEATURE}
# The groups the snapshot of the end of 24A predates (24B..27D); the old compare snapshot (aee05a40f10f) holds the others.
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser', 'rbmk-autoloader', 'rbmk-crane',
                          'hazard-system', 'radiation-detection', 'gas-masks', 'hazmat-suits', 'radiation-medicine', 'material-system', 'foundry-casting'}
RADIATION_NOTE = ('Goal28A: nether uranium ore releases radon gas when mined or randomly ticked; mine it with a gas mask in a disposable world. ')
MELTDOWN_NOTE = 'Goal28A: no new meltdown path. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_WORLDGEN = ORIGINAL+'lib/HbmWorldGen.java'
O_TOOLBOX = ORIGINAL+'world/generator/DungeonToolbox.java'
O_WORLDCONFIG = ORIGINAL+'config/WorldConfig.java'
O_GENERALCONFIG = ORIGINAL+'config/GeneralConfig.java'
O_MODBLOCKS = ORIGINAL+'blocks/ModBlocks.java'
O_BLOCKORE = ORIGINAL+'blocks/generic/BlockOre.java'
O_NETHERCOAL = ORIGINAL+'blocks/generic/BlockNetherCoal.java'
O_SMOLDER = ORIGINAL+'blocks/generic/BlockSmolder.java'
O_OUTGAS = ORIGINAL+'blocks/generic/BlockOutgas.java'
O_SMELTING = ORIGINAL+'crafting/SmeltingRecipes.java'
O_CENTRIFUGE = ORIGINAL+'inventory/recipes/CentrifugeRecipes.java'
O_SHREDDER = ORIGINAL+'inventory/recipes/ShredderRecipes.java'
O_CRYSTALLIZER = ORIGINAL+'inventory/recipes/CrystallizerRecipes.java'
O_FUEL = ORIGINAL+'handler/FuelHandler.java'
O_TOOLRECIPES = ORIGINAL+'crafting/ToolRecipes.java'
O_MODITEMS = ORIGINAL+'items/ModItems.java'
O_BURNER_TE = ORIGINAL+'tileentity/machine/TileEntityHeaterOilburner.java'
O_BURNER_BLOCK = ORIGINAL+'blocks/machine/HeaterOilburner.java'
O_GENERIC_RECIPE = ORIGINAL+'inventory/recipes/loader/GenericRecipe.java'
O_LANG_EN = O_RES+'lang/en_US.lang'
O_LANG_ZH = O_RES+'lang/zh_CN.lang'
O_SOURCES = [O_WORLDGEN, O_TOOLBOX, O_WORLDCONFIG, O_GENERALCONFIG, O_MODBLOCKS, O_BLOCKORE, O_NETHERCOAL, O_SMOLDER, O_OUTGAS, O_SMELTING, O_CENTRIFUGE, O_SHREDDER, O_CRYSTALLIZER, O_FUEL,
             O_TOOLRECIPES, O_MODITEMS, O_BURNER_TE, O_BURNER_BLOCK, O_GENERIC_RECIPE, O_LANG_EN, O_LANG_ZH]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'generate_nether': (O_WORLDGEN, 'private void generateNether'), 'nether_ore_switch': (O_WORLDGEN, 'if(WorldConfig.netherOre)'), 'uranium_vein': (O_WORLDGEN, 'WorldConfig.netherUraniumuSpawn, 6, 0, 127'),
    'cobalt_vein': (O_WORLDGEN, 'WorldConfig.netherCobaltSpawn, 6, 100, 26'), 'coal_vein': (O_WORLDGEN, 'WorldConfig.netherCoalSpawn, 32, 16, 96'),
    'plutonium_guard': (O_WORLDGEN, 'if(GeneralConfig.enablePlutoniumOre)'), 'smoldering_loop': (O_WORLDGEN, 'ModBlocks.ore_nether_smoldering'), 'end_tikite': (O_WORLDGEN, 'WorldConfig.endTikiteSpawn, 6, 0, 127'),
    'vein_height': (O_TOOLBOX, 'int y = minHeight + (variance > 0'), 'cfg_nether_ores': (O_WORLDCONFIG, '2.D01_netherOres'), 'cfg_end_ores': (O_WORLDCONFIG, '2.D02_endOres'),
    'cfg_uranium': (O_WORLDCONFIG, '2.N00_uraniumSpawnrate'), 'cfg_cobalt': (O_WORLDCONFIG, '2.N06_cobaltSpawnrate'), 'cfg_tikite': (O_WORLDCONFIG, '2.E00_tikiteSpawnrate'),
    'cfg_plutonium': (O_GENERALCONFIG, '1.02_enablePlutoniumNetherOre'), 'block_coal': (O_MODBLOCKS, 'ore_nether_coal = new BlockNetherCoal'), 'block_smoldering': (O_MODBLOCKS, 'ore_nether_smoldering = new BlockSmolder'),
    'block_uranium': (O_MODBLOCKS, 'ore_nether_uranium = new BlockOutgas'), 'block_tikite': (O_MODBLOCKS, 'ore_tikite = new BlockDragonProof'),
    'drop_sulfur': (O_BLOCKORE, 'ore_nether_sulfur) return 2 + rand.nextInt(3)'), 'drop_cobalt': (O_BLOCKORE, 'ore_nether_cobalt) return 5 + rand.nextInt(8)'),
    'drop_fire': (O_BLOCKORE, 'rand.nextInt(10) == 0 ? ModItems.ingot_phosphorus : ModItems.powder_fire'), 'drop_coal': (O_NETHERCOAL, 'return ModItems.coal_infernal'),
    'drop_smoldering': (O_SMOLDER, 'return ModItems.powder_fire'), 'step_coal': (O_NETHERCOAL, 'entity.setFire(3)'), 'step_smoldering': (O_SMOLDER, 'entity.setFire(3)'),
    'outgas_radon': (O_OUTGAS, 'this == ModBlocks.ore_nether_uranium'), 'outgas_monoxide': (O_OUTGAS, 'this == ModBlocks.ore_nether_coal'),
    'smelt_tungsten': (O_SMELTING, 'ModBlocks.ore_nether_tungsten'), 'smelt_cobalt': (O_SMELTING, 'ModBlocks.ore_nether_cobalt'), 'fuel_infernal': (O_FUEL, 'return 4800'),
    'shred_fire': (O_SHREDDER, 'setRecipe(ModBlocks.ore_nether_fire'), 'shred_infernal': (O_SHREDDER, 'setRecipe(ModItems.coal_infernal'),
    'cryst_fire': (O_CRYSTALLIZER, 'new ComparableStack(ModBlocks.ore_nether_fire)'), 'cryst_tikite': (O_CRYSTALLIZER, 'new ComparableStack(ModBlocks.ore_tikite)'),
    'cryst_infernal': (O_CRYSTALLIZER, 'new ComparableStack(ModItems.coal_infernal)'), 'hand_drill_item': (O_MODITEMS, 'hand_drill = new ItemTooling(ToolType.HAND_DRILL, 100)'),
    'hand_drill_desh_item': (O_MODITEMS, 'hand_drill_desh = new ItemTooling(ToolType.HAND_DRILL, 0)'), 'hand_drill_recipe': (O_TOOLRECIPES, 'new ItemStack(ModItems.hand_drill), new Object[]'),
    'hand_drill_desh_recipe': (O_TOOLRECIPES, 'new ItemStack(ModItems.hand_drill_desh), new Object[]'),
    'burner_capacity': (O_BURNER_TE, 'public int maxHeatEnergy = 500_000'), 'burner_overdrive_rate': (O_BURNER_TE, 'this.maxBurnRate = 10 * (od + 1)'), 'burner_overdrive_heat': (O_BURNER_TE, 'this.maxHeatEnergy = 500_000 * (od + 1)'),
    'generic_recipe_icon': (O_GENERIC_RECIPE, 'if(!stacks.isEmpty()) this.setIcon(stacks.get(0))'),
}
# The nether and end vein table, id -> (WorldConfig/GeneralConfig field the original counts with, NEO config key). Every other value is parsed from the original.
VEIN_FIELDS = {'ore_nether_uranium': ('netherUraniumuSpawn', 'netherUraniumSpawnRate'), 'ore_nether_tungsten': ('netherTungstenSpawn', 'netherTungstenSpawnRate'),
               'ore_nether_sulfur': ('netherSulfurSpawn', 'netherSulfurSpawnRate'), 'ore_nether_fire': ('netherPhosphorusSpawn', 'netherPhosphorusSpawnRate'),
               'ore_nether_coal': ('netherCoalSpawn', 'netherCoalSpawnRate'), 'ore_nether_cobalt': ('netherCobaltSpawn', 'netherCobaltSpawnRate'),
               'ore_nether_plutonium': ('netherPlutoniumSpawn', 'netherPlutoniumSpawnRate'), 'ore_tikite': ('endTikiteSpawn', 'endTikiteSpawnRate')}
SWITCH_FIELDS = {'netherOre': 'netherOres', 'endOre': 'endOres', 'enablePlutoniumOre': 'enablePlutoniumNetherOre'}
# Expected figures of the handoff and the task book (every value is also computed from the sources).
EXPECTED = dict(veins=8, nether_veins=7, configured_features=9, placed_features=9, biome_modifiers=4, blocks=6, imported_assets=11, config_values=11, language_added=21, language_changed=2,
                deferred_entries=106, classified_files=66, crystallizer_rows=53, smoldering=dict(tries=30, min_height=16, variation=96, scan_depth=5), burner_capacity=500000, fuel_ticks=4800,
                hand_drill_durability=100, source_added=5, source_modified=61, source_removed=1, categories={'neo-adapt-28a': 6, 'neo-counterpart-equivalent': 4, 'not-applicable-content': 36, 'not-migrated-other': 20})
CLASSIFICATION_CATEGORIES = {'neo-adapt-28a', 'neo-counterpart-equivalent', 'network-architecture', 'not-applicable-content', 'not-migrated-other'}
KNOWN_DIFFERENCES = {
    'smoldering_not_gated': 'smoldering netherrack is NOT gated by netherOres: HbmWorldGen.java:527-535 sits outside `if(WorldConfig.netherOre)` (:503-525); the task book grouped it with the six ores, NEO follows the original (a plain neoforge:add_features modifier)',
    'plutonium_double_gate': 'nether plutonium needs both netherOres and enablePlutoniumNetherOre (HbmWorldGen.java:511-512 is inside the netherOre block); enablePlutoniumNetherOre defaults to false (GeneralConfig.java:99)',
    'smoldering_height': 'smoldering netherrack spans y 11..111 (d = 16 + rand(96), y = d-5..d); the task book wrote 16-111',
    'centrifuge_gravel': 'nether tungsten and cobalt centrifuge rows end in gravel (shared W.ore()/CO.ore() ore-dictionary rows, OreDictManager.java:382,400; CentrifugeRecipes.java:102-106,198-202), not netherrack as the task book said; nether sulfur has no centrifuge row in either; the nether plutonium 4th output is gravel (:142)',
    'crystallizer_extra_rows': 'three crystallizer rows beyond the task book for nether sulfur, tungsten and cobalt (ore-dictionary rows CrystallizerRecipes.java:71,74,81): 53 rows in total',
    'shredder_coal_skip': 'the shredder auto rule would add ore_nether_coal -> 2 coal powder, which has no original row: it is skipped; only coal_infernal -> 2 powder_coal (:199) and ore_nether_fire -> 6 powder_fire (:150) are explicit',
    'smelting_experience': 'furnace experience uses NEO\'s unified 0.7F instead of the original 12.0 / 2.0 (SmeltingRecipes.java:38,46)',
    'sa326_nether_ore': 'nether Sa326 ore is not generated (the original has no generation); ore_nether_schrabidium keeps its registration',
    'geyser_bedrock_neodymium': 'nether geyser (HbmWorldGen.java:537-545), the nether bedrock ore (:514-520) and the depth neodymium ore (:522-524, 28B) are not ported',
    'scraps_name': 'a dropped scraps item entity is named through item.hbmsntm.scraps.generic: vanilla ItemEntity.getName() translates the bare description id, which dropped the %s of item.hbmsntm.scraps',
    'ros_satellites': 'RoR (launch pad, excavator, IRORInteractive) and satellite (findplayer) changes of the range are not migrated: NEO has no RoR transport and no satellite command caller',
}

# 27A / 27B / 27C / 27D ones the receipt carries forward under a new heading.
CARRIED_REPINS = 'repinned_since_'


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal28a release directory: '+rel


def original_blob(path):
    """Bytes of a file in the original repository at the 28A commit (independent of its worktree)."""
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
            out.setdefault(k, v)
    return out


def merged_files(base):
    """One start-hash map: the tracked tree (`files`) and the Git-ignored migration/ directory hashed from disk (`migration_files`)."""
    assert not set(base['files']) & set(base['migration_files']), 'The tracked tree and migration_files overlap'
    return {**base['files'], **base['migration_files']}


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the planned files) when it reproduces the baseline hash, else the blob at the start commit (with CRLF where the
    working tree had it); None when nothing reproduces the baseline hash (a migration/ file nobody copied has no blob: Git-ignored)."""
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
    """The Goal28A start hash of a frozen path: the merged baseline hashes, or for a build/ record (Git-ignored, so the baseline does not list it) the hash the goal27d receipt
    records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal27d packager protected (built there from the Goal21A..Goal27C starts and receipts and the goal27d start), plus every path the goal27d receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (goal21a..goal27c) and every release file of the frozen start (the goal27d package included).
    The records that already drifted (the older drift: the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes; the newer drift: the
    GOAL25D / GOAL26D / GOAL27D acceptance checklists written or extended after the goal27d packaging) are pinned at their Goal28A start hash instead of any receipt hash or any earlier
    start hash. One path never carries two hashes. Returns (protected, repinned): repinned maps a record to the pin the goal27d packager set (its Goal27D start hash) for the records
    whose pin changed between the starts."""
    goal27d_start = read(GOAL27D_BASELINE)
    out = dict(goal27d_protected_paths(goal27d_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal27d receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal27d_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    return out, repinned


def start_drift_report(base, repinned, goal27d_start):
    """{path: {receipts, start_sha256, goal27d_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal27d receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal27d receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21..26 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal27d '
                           'receipt does not hash it. Frozen at the Goal28A start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal27d) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal27d package (the in-game acceptance results of Goal 25, 26 and 27 were recorded in the checklists once the packages existed); the goal27d '
                           'receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal27d receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal27d_start_sha256=goal27d_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal27d_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def changed_since_start(base):
    """{path: added|modified|deleted} against the merged start hashes: the Git-visible files and, because migration/ is Git-ignored since 66050453, every file found by walking migration/
    (build/ outputs excluded)."""
    now = {n for n in git_ro(ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0') if n}
    now |= {p.relative_to(ROOT).as_posix() for p in (ROOT/'migration').rglob('*') if p.is_file()}
    out = {}
    for p in sorted(now | set(base['files'])):
        if p.startswith('build/'): continue
        before = base['files'].get(p)
        if not (ROOT/p).is_file():
            if before: out[p] = 'deleted'
            continue
        if before is None: out[p] = 'added'
        elif before != sha(ROOT/p): out[p] = 'modified'
    return out


def scope_text(tests, total_tests):
    return (f'Goal28A (the first batch of Goal 28, world generation and resources): upstream review aee05a40f..4f5924e2b (66 files) with the fluid burner and GenericRecipe icon adaptations; '
            f'config-gated nether and end ore generation (two new codec types, a worldgen config group); six nether ore blocks, smoldering netherrack and infernal coal with drops and processing rows; '
            f'nether uranium and coal outgassing; hand drills; JEI anvil tier text and anvil variants; the dropped scraps\' entity name; {tests} NetherEndWorldgenGameTests ({total_tests} GameTests in total); '
            f'packages the D3, D5 and mod-rename small fixes made after the goal27d package. Gameplay impact: the nether now generates uranium, tungsten, sulfur, phosphorus, burning coal and cobalt ores '
            f'and smoldering netherrack, the end trixite ore (all configurable; nether plutonium ore only when enablePlutoniumNetherOre is turned on); phosphorus (red phosphorus, phosphorus ingots and '
            f'crystals), infernal coal and trixite crystals are obtainable; nether uranium ore releases radon and burning nether coal releases carbon monoxide, burning coal and smoldering netherrack set '
            f'walkers on fire; hand drills are craftable and toggle the foundry outlet\'s filter inversion; the fluid burner is set with a GUI slider instead of a screwdriver, accepts overdrive upgrades and '
            f'holds 500,000 TU (more with overdrive).')


def group(p, imported):
    if p in NEW_JAVA: return 'production-new'
    if p in EDITED_GAMETESTS: return 'gametest-edit'
    if p in MODIFIED_JAVA or p in OPTIONAL_JAVA: return 'production'
    if p in imported: return 'production-resource-imported'
    if p == ZH_INPUT: return 'language'
    if p in GENERATED_MODIFIED or GENERATED_ADDED.fullmatch(p) or GENERATED_TAGS.fullmatch(p): return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p) or p == TASK_BOOK: return 'reports'
    if p == LEDGER_EDIT: return 'ledger-edit'
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records'
    return None


def owner_of(p):
    return OWNER


def small_fix_commits():
    """{file: 'abbrev subject'} of the last commit that touched each small-fix source (read only)."""
    return {p: git_ro(ROOT, 'log', '-1', '--format=%h %s', '--', p).strip() for p in SMALL_FIX_FILES}


def parse_original_veins(text):
    """{field: (amount, min_height, variance, ore, target)} of every `generateOre(world, rand, i, j, WorldConfig.<field>, amount, min, variance, ModBlocks.<ore>, Blocks.<target>)` call."""
    out = {}
    for field, amount, low, var, ore, target in re.findall(r'generateOre\(world, rand, i, j, (?:WorldConfig|GeneralConfig)\.(\w+), (\d+), (\d+), (\d+), ModBlocks\.(\w+), Blocks\.(\w+)\)', text):
        out[field] = (int(amount), int(low), int(var), ore, target)
    return out


def original_int_default(text, field):
    m = re.search(r'public static int '+field+r' = (-?\d+);', text)
    return int(m.group(1)) if m else None


def generated_json(path):
    return read(ROOT/path) if (ROOT/path).is_file() else None


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
    goal27d_start = read(GOAL27D_BASELINE)
    tracked_count = len(base['files'])

    # 1. Heads: the clean original at 4f5924e2b (39 commits past aee05a40f), NEO at the start commit 66a00353 (the mod rename, = origin/master at the freeze; Goal28A commits nothing) with a
    # CLEAN worktree at the freeze. The Goal 27 delivery adaf265c is two commits below; migration/ is untracked and Git-ignored (66050453), so the start is `files` + `migration_files`.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at 4f5924e2b'
    assert start_head.startswith(START_PREFIX), 'The frozen start is not on the mod rename commit 66a00353'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Rename the mod' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the mod rename commit'
    assert base['target_status'] == '' and START_STATUS.read_text(encoding='utf-8') == '', 'The frozen start was not a clean worktree'
    assert base['target_parent'].startswith(START_PARENT_PREFIX) and base['origin_master'] == start_head, 'The start commit is not origin/master on c1f6f397'
    assert prior_receipt['source_commit'] == SOURCE_PREVIOUS, 'The goal27d receipt records another original commit than aee05a40f'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal28A (the delivery stays uncommitted until the Goal 28 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2, 3)}
    assert chain[1].startswith(START_PARENT_PREFIX) and chain[2].startswith(UNTRACK_PREFIX) and chain[3].startswith(GOAL27_DELIVERY_PREFIX), \
        'NEO HEAD~1..3 are not c1f6f397, the migration/ untrack commit 66050453 and the Goal 27 delivery adaf265c: '+str(chain)
    committed_files = [l for l in git_ro(ROOT, 'show', '--name-only', '--format=', start_head).splitlines() if l.strip()]
    assert committed_files and not any(p.startswith('build/') for p in committed_files), 'The start commit is empty or holds build/ files'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and 'mod rename' in base['start_content']['committed'] and base['start_content']['uncommitted'].startswith('none'), \
        'Baseline start content differs (expected the committed mod rename and small fixes and no uncommitted change)'
    assert set(base['older_receipt_protected_paths']) == OLDER_RECEIPTS, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        files_map = base['files'] if n in base['files'] else base['migration_files']
        assert sha(START_FILES/n) == files_map[n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    older_drift_nonempty = {k: v for k, v in base['older_receipt_evidence_drift'].items() if v}  # freeze_start.py records only the non-empty entries in startup-verification.json
    assert startup['frozen_file_hashes'] == tracked_count and startup['migration_file_hashes'] == len(base['migration_files']) and startup['copied_scope'] == len(base['copied_scope']) \
        and startup['old_release_files'] == len(base['old_release_files']) and startup['old_release_jars'] == len(base['old_releases']) \
        and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256_at_freeze'] == base['build_libs_jar_sha256_at_freeze'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_lines'] == 0 and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == older_drift_nonempty, \
        'startup-verification.json differs from baseline.json'
    base['files'] = merged_files(base)
    start_stamp = start_json(base, STAMP)
    assert base['stamp_state']['generated_resources_recorded'] == prior_receipt['generated_resource_count'] == len(start_stamp['generated']) \
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal27d generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_freeze']
    assert base['target_head'] == start_head and not [p for p in committed_files if p.startswith('migration/')], 'The start commit holds migration/ files (Git-ignored since 66050453)'
    uncommitted_start = dict(
        status_entries=0, status=[],
        description='a clean worktree at the freeze: no uncommitted file; migration/ is Git-ignored and hashed separately (baseline migration_files)',
        committed_delivery=dict(commit=start_head[:8], parent=base['target_parent'][:8], files_in_commit=len(committed_files), untrack_commit=chain[2][:8], goal27_delivery_commit=chain[3][:8],
                                note='66a00353 renames the mod (gradle.properties mod_name / mod_authors -> neoforge.mods.toml) and ignores .claude; c1f6f397 rewrites the README; 66050453 untracks and ignores '
                                     'migration/; adaf265c commits the Goal 27 delivery (27C and 27D) with the small fixes D3 (AnvilRecipeHandler.java) and D5 (ContaminationUtil.java).'),
        migration_dir=dict(tracked_files_hashed=tracked_count, migration_files_hashed=len(base['migration_files']), copied_scope=len(base['copied_scope']),
                           note='migration/ is Git-ignored: `git ls-files` no longer lists it, so the baseline hashes it from disk and this packager finds its changes by walking the directory.'))

    # 2. Previous deliveries: the goal27d package, every old release file and the protected evidence; build/libs at the freeze is the post-rename JAR (D3, D5 and the rename), NOT the goal27d package.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha != previous_sha, 'build/libs at the freeze is the goal27d package (expected the post-rename JAR)'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal27d receipt list + the goal27d package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal27d receipt count + the goal27d release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal27d receipt'
    newer_drift = sorted(base['previous_receipt_evidence_drift'])
    need(newer_drift == ['migration/GOAL25D-ACCEPTANCE.md', 'migration/GOAL26D-ACCEPTANCE.md', 'migration/GOAL27D-ACCEPTANCE.md'],
         'The baseline records another newer drift than the three acceptance checklists written or extended after the goal27d packaging: '+str(newer_drift))
    protected, repinned = protected_paths(base)
    need(all(p.endswith('-ACCEPTANCE.md') for p in repinned), 'A non-checklist pin changed between the Goal27D and Goal28A starts: '+str(sorted(repinned)))
    ledger_pin = protected.pop(LEDGER_EDIT, None)
    drift_report = start_drift_report(base, repinned, goal27d_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal27d receipt: '+str(sorted(explained))
    # migration/GOAL24B.md: the one ledger sentence about the plutonium and polonium sources (task book GOAL28A.md); every other line is the start's.
    ledger_now = lines_of((ROOT/LEDGER_EDIT).read_bytes())
    ledger_start_data = start_bytes(base, LEDGER_EDIT)
    ledger_edit = None
    if need(ledger_start_data is not None, LEDGER_EDIT+' has no reproducible start bytes (baseline-files copy missing)'):
        ledger_was = lines_of(ledger_start_data)
        counts = edit_counts(ledger_was, ledger_now)
        removed_line = list((Counter(ledger_was) - Counter(ledger_now)).elements())
        added_line = list((Counter(ledger_now) - Counter(ledger_was)).elements())
        ledger_edit = dict(path=LEDGER_EDIT, start_sha256=base['files'][LEDGER_EDIT], current_sha256=sha(ROOT/LEDGER_EDIT), counts=counts, removed_line=removed_line, added_line=added_line,
                           in_goal24b_receipt=ledger_pin, note='one ledger sentence of the Goal 24B record (plutonium powder and polonium-210 are reachable with enablePlutoniumNetherOre, default off) '
                                                              'changed by the task book GOAL28A.md; the goal24b receipt is not rewritten')
        need(len(removed_line) == 1 and len(added_line) == 1 and re.search(r'(?i)plutonium|polonium|钚|钋', removed_line[0]) and re.search(r'(?i)enablePlutoniumNetherOre', added_line[0]),
             f'{LEDGER_EDIT} must differ from its start by exactly one replaced line (the plutonium / polonium source sentence, now naming enablePlutoniumNetherOre): removed {removed_line[:2]}, added {added_line[:2]}')

    # 3. Changes since the start: each path in the owner table, attributed to goal28a. Everything else equals its start hash (the merged tracked and migration/ hashes).
    changes = changed_since_start(base)
    imported = {p for p in changes if TEXTURE_PATTERN.fullmatch(p)}
    optional_changed = [p for p in OPTIONAL_JAVA if p in changes]
    modified_java = MODIFIED_JAVA + optional_changed
    production_java = NEW_JAVA + modified_java + [p for p in EDITED_GAMETESTS if p in changes]
    older_gametests_frozen = sorted(p for p in base['files'] if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p not in OPTIONAL_JAVA and p not in EDITED_GAMETESTS)
    unassigned = sorted(p for p in changes if group(p, imported) is None)
    need(not unassigned, 'Path changed since the Goal28A start that the owner table does not list (production outside the listed new and modified Java files, NetherEndWorldgenGameTests and the edited '
         'RBMKCoreGameTests, a hand-written resource other than the 6 nether ore textures + animation, 3 item textures and gui_oilburner.png, a generated file other than the stamp, en_us.json, the pickaxe '
         'tag and the nether / end worldgen, blockstate, model, loot table and recipe set, a protected or frozen record, an older tool, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or (FROZEN_RECORD.fullmatch(p) and p != LEDGER_EDIT))
    need(not frozen_changed, 'Goal 27 and earlier records, GOAL28B/C/D.md, GOAL28-THREAD-PROMPTS.md or SURVIVAL-PLAYABILITY.md changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal28A start: '+str(deleted)
    for p in MODIFIED_JAVA + EDITED_GAMETESTS + GENERATED_MODIFIED + [ZH_INPUT, TASK_BOOK, LEDGER_EDIT] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + REQUIRED_TEXTURES[:-1] + REQUIRED_GENERATED + NEW_TOOLS + REPORTS[1:]:
        if p == SNAPSHOT_NEW or p in (CLASSIFICATION, RESOURCE_OWNERSHIP): continue  # already written before the freeze (classification, ownership) or by the chain (snapshot)
        assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes or p in (CLASSIFICATION, RESOURCE_OWNERSHIP), 'change not present yet (still equals the start or absent): '+p)
    # The classification and the resource ownership record exist at the start (migration_files): they may be rewritten, never deleted; the new snapshot comes from the chain.
    for p in (CLASSIFICATION, RESOURCE_OWNERSHIP): need((ROOT/p).is_file(), 'record missing: '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(production_java) - imported - {ZH_INPUT})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified (+ optional), {len(NEW_JAVA)} new and {len(EDITED_GAMETESTS)} edited GameTest Java files, the nether ore / item textures, gui_oilburner.png '
         'and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools = OLD_TOOLS_FROZEN + sorted(p for p in base['files'] if p.startswith(FROZEN_TOOL_DIRS))
    frozen_tools_changed = sorted(p for p in frozen_tools if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (package_goal27d.py, verify_goal27d_molds.py, the 27A-27C packagers and verifiers, the casting regression wrapper and '
         'compat, the Goal 26C old-suite wrapper, the casting regressions and their folders): '+str(frozen_tools_changed))
    jei_classes = sorted(p for p in base['files'] if p.startswith(J+'handler/jei/') and p not in (JEI_ANVIL, JEI_ANVIL_CONSTRUCTION))
    frozen_dir_files = sorted(p for p in base['files'] if p.startswith(UNCHANGED_DIRS) or (p.startswith(GENERATED_ROOT+'data/hbmsntm/worldgen/') or p.startswith(GENERATED_ROOT+'data/hbmsntm/neoforge/biome_modifier/')))
    unchanged_bad = [p for p in UNCHANGED_JAVA + older_gametests_frozen + jei_classes + frozen_dir_files if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed (the six pre-existing feature classes, the foundry outlet block and block entity, the Goal 27 material / casting '
         'tables, MoldItem, ContaminationUtil, every other handler/jei class, every other GameTest class, the hand-written worldgen data and the pre-existing generated worldgen and biome modifier JSONs): '+str(unchanged_bad[:8]))
    goal28_now = sha(ROOT/GOAL28_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository before the start. The batch ran under the main '
                                               'agent (production review, the migration/ records, zh_cn.json and the mapping) with a production builder (the 28A Java, runData), a GameTest verifier '
                                               '(NetherEndWorldgenGameTests, the edited RBMKCoreGameTests oil-burner block, verify_goal28a_worldgen.py, runData and the GameTest server), a reviewer and this packaging '
                                               'verifier (the packager, the final runner, the casting-regression attribution) working in the same checkout; each wrote only its named files (the scope snapshots '
                                               'of the verifiers are indexed as evidence).',
                             goal28_md=dict(start_sha256=base['files'][GOAL28_RECORD], current_sha256=goal28_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p) if (ROOT/p).is_file() else None) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p, imported), owner=owner_of(p), owners=[owner_of(p)], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    added_baselines = sorted(set(baselines_now) - set(start_baselines))
    need(all(baselines_now.get(p) == h for p, h in start_baselines.items()) and added_baselines in ([], [SNAPSHOT_NEW]),
         'A snapshot changed, or a snapshot other than '+SNAPSHOT_NEW+' was added: '+str(added_baselines))
    assert sha(ROOT/SNAPSHOT_OLD) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT_OLD, 'review-aee05a40f10f snapshot changed'
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
    unexpected_new = sorted(p for p in changes if p.startswith(SRC) and p.endswith('.java') and changes[p] == 'added' and p not in NEW_JAVA)
    need(not unexpected_new, 'new Java files under src/main/java other than the owner table\'s: '+str(unexpected_new))

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
    # The registration, bootstrap and provider files only gain lines: no start line is removed except a terminator or a call chain that an added line extends.
    registration_files = (COMMON_CONFIG, CONFIGURED_FEATURES, PLACED_FEATURES, BIOME_MODIFIERS_JAVA, NTM_FEATURES, NUCLEAR_TECH_MOD, NTM_BLOCKS, NTM_ITEMS, CREATIVE_TABS, STATE_PROVIDER,
                          ITEM_MODEL_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER, RECIPE_PROVIDER, LANG_PROVIDER, SHREDDER_RECIPES, OUTGAS_BLOCK, COPPER_SCRAPS, BURNER_MENU)
    for p in registration_files:
        if p not in removed_lines: continue
        stray = stray_removals(removed_lines[p], added_lines[p])
        # By design: the two nether uranium blocks become OutgasBlock registrations (ModBlocks.java:1260-1261) and the two heater_oilburner descriptions are reworded (4f5924e2b dropped the screwdriver text).
        replaced = [s for s in stray if (p == NTM_BLOCKS and re.search(r'ORE_NETHER_URANIUM(?:_SCORCHED)? = register', s)) or (p == LANG_PROVIDER and re.search(r'heater_oilburner\.desc', s))]
        stray = [s for s in stray if s not in replaced]
        content_rules[p] = not stray
        if replaced: content_rules[p+'#replaced_by_design'] = replaced
        need(not stray, f'{p} removes start lines that no added line extends: {stray[:4]}')
    # The rewritten or partly rewritten adaptations are reported by their +/- (the burner, the recipe tables, GenericRecipe's icon line, the JEI anvil text); judged by the verifier's GameTests and script.
    reported_edits = {p: edit_summary[p] for p in (BURNER_BE, BURNER_BLOCK, BURNER_SCREEN, CENTRIFUGE_RECIPES, CRYSTALLIZER_RECIPES, GENERIC_RECIPE, JEI_ANVIL, JEI_ANVIL_CONSTRUCTION) if p in edit_summary}
    content_rules['#reported_rewrites'] = reported_edits
    # The one older GameTest the batch edits by design: the @GameTest methods are the start's; only the oil-burner block of rbmk_screwdriver_tooling changes.
    gametest_edits = {}
    for p in gametest_edit_files:
        if p not in start_text: continue
        now_text, was_text = (ROOT/p).read_text(encoding='utf-8'), start_text[p].decode('utf-8')
        names_now, names_was = GAMETEST_METHOD.findall(now_text), GAMETEST_METHOD.findall(was_text)
        annotations_now, annotations_was = len(GAMETEST_ANNOTATION.findall(now_text)), len(GAMETEST_ANNOTATION.findall(was_text))
        touched = [l.strip() for l in removed_lines[p] + added_lines[p] if '@GameTest' in l or 'public static void' in l]
        entry = dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p), added=len(added_lines[p]), removed=len(removed_lines[p]), game_tests=annotations_now, game_tests_at_start=annotations_was,
                     methods_unchanged=names_now == names_was)
        if p == RBMK_TESTS:
            outside_method = strip_noise(cut_methods(now_text, SCREWDRIVER_METHOD)) == strip_noise(cut_methods(was_text, SCREWDRIVER_METHOD))
            entry.update(rule='only the oil-burner block of rbmk_screwdriver_tooling changes (4f5924e2b removed the screwdriver config of the burner, HeaterOilburner.java)', rule_holds=outside_method and not touched,
                         outside_screwdriver_method_equal=outside_method)
        else:
            code_removed = [l for l in removed_lines[p] if not is_comment(l)]
            code_added = [l for l in added_lines[p] if not is_comment(l)]
            counts_old = [int(m.group(1)) for l in code_removed for m in [ROW_COUNT_CHECK.search(l)] if m]
            counts_new = [int(m.group(1)) for l in code_added for m in [ROW_COUNT_CHECK.search(l)] if m]
            entry.update(rule='only the table row-count checks change (acidizer / crystallizer default table 47 -> 53 rows, centrifuge 77 -> 80 rows)', removed_counts=counts_old, added_counts=counts_new,
                         rule_holds=len(code_removed) == len(counts_old) and len(code_added) == len(counts_new) and bool(counts_new) and not touched
                         and sorted(counts_old) == ({RADIATION_TESTS: [47], SMOKE_TESTS: [47, 77]}[p]) and sorted(counts_new) == ({RADIATION_TESTS: [EXPECTED['crystallizer_rows']], SMOKE_TESTS: [EXPECTED['crystallizer_rows'], 80]}[p]))
        gametest_edits[p] = entry
        need(entry['rule_holds'] and entry['methods_unchanged'] and annotations_now == annotations_was, f'{p} changed beyond its allowed edit ({entry["rule"]}): {json.dumps(entry, ensure_ascii=False)[:400]}')

    # 4. Nether and end worldgen against the original (EXPECTED holds the handoff figures; every value is computed from the sources; the NEO side is read from the generated worldgen JSON and from
    # tolerant source patterns, the behaviour itself is the job of verify_goal28a_worldgen.py and NetherEndWorldgenGameTests).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    facts, bad = {}, []

    def fact(key, value, expected=None, ok=None):
        facts[key] = value if expected is None else dict(value=value, expected=expected)
        if ok is None: ok = expected is None or value == expected
        if not ok: bad.append(key)

    o = {path: original_text(path) for path in O_SOURCES}
    code = lambda p: strip_java_comments(neo_text(p))
    gen = lambda kind, name: generated_json(GENERATED_ROOT+f'data/hbmsntm/worldgen/{kind}/{name}.json')
    # 4a. The vein table: HbmWorldGen.java:503-551 (generateOre(world, rand, i, j, count, amount, minHeight, variance, ore, target)); DungeonToolbox.java:77-78: y = minHeight + rand(variance) -> the
    # uniform height range [min, min + variance - 1]; the config defaults WorldConfig.java:183-191, GeneralConfig.java:18.
    o_veins = parse_original_veins(o[O_WORLDGEN])
    fact('original_vein_count', len(o_veins), EXPECTED['veins'])
    wc_defaults = {field: original_int_default(o[O_WORLDCONFIG], field) for field, _ in VEIN_FIELDS.values()}
    veins, vein_ok = {}, True
    for block_id, (field, key) in VEIN_FIELDS.items():
        row = o_veins.get(field)
        configured, placed = gen('configured_feature', block_id), gen('placed_feature', block_id+'_placed')
        entry = dict(original=dict(zip(('veins_key', 'amount', 'min_height', 'variance', 'ore', 'target'), (field,)+row)) if row else None, original_default_count=wc_defaults.get(field), neo_config_key=key)
        if row and configured and placed:
            amount, low, var, ore, target = row
            target_block = 'minecraft:end_stone' if target == 'end_stone' else 'minecraft:netherrack'
            ore_config = configured.get('config', {})
            placement = placed.get('placement', [])
            height = next((m for m in placement if m.get('type') == 'minecraft:height_range'), {}).get('height', {})
            count = next((m for m in placement if m.get('type') == 'hbmsntm:config_count'), {})
            entry['neo'] = dict(type=configured.get('type'), size=ore_config.get('size'), state=[t['state']['Name'] for t in ore_config.get('targets', [])], target=[t['target'].get('block') for t in ore_config.get('targets', [])],
                                count_config=count.get('config'), height=[height.get('min_inclusive', {}).get('absolute'), height.get('max_inclusive', {}).get('absolute')], height_type=height.get('type'),
                                modifiers=[m.get('type') for m in placement])
            entry['ok'] = (entry['neo']['type'] == 'minecraft:ore' and entry['neo']['size'] == amount and entry['neo']['state'] == ['hbmsntm:'+block_id] and entry['neo']['target'] == [target_block]
                           and ore == block_id and count.get('config') == key and entry['neo']['height'] == [low, low + var - 1] and entry['neo']['height_type'] == 'minecraft:uniform'
                           and entry['neo']['modifiers'] == ['hbmsntm:config_count', 'minecraft:in_square', 'minecraft:height_range', 'minecraft:biome'])
        else: entry['ok'] = False
        veins[block_id] = entry
        vein_ok = vein_ok and entry['ok']
    fact('veins', {k: dict(original=v['original'], neo=v.get('neo')) for k, v in veins.items()}, None, ok=vein_ok and len(veins) == EXPECTED['veins'])
    # 4b. The config group: 11 keys, defaults equal to the original (counts WorldConfig.java:183-191, switches :124-125 and GeneralConfig.java:18/99).
    config_text = (lambda t: t[t.index('builder.push("worldgen")'):t.index('builder.pop()', t.index('builder.push("worldgen")'))])(neo_text(COMMON_CONFIG)) if 'builder.push("worldgen")' in neo_text(COMMON_CONFIG) else ''
    neo_ints = {m[0]: int(m[1]) for m in re.findall(r'defineInRange\("(\w+)",\s*(-?\d+),', config_text)}
    neo_bools = {m[0]: m[1] == 'true' for m in re.findall(r'\.define\("(\w+)",\s*(true|false)\)', config_text)}
    o_bools = {'netherOres': 'public static boolean netherOre = true;' in o[O_WORLDCONFIG], 'endOres': 'public static boolean endOre = true;' in o[O_WORLDCONFIG],
               'enablePlutoniumNetherOre': 'public static boolean enablePlutoniumOre = false;' in o[O_GENERALCONFIG]}
    expected_ints = {key: wc_defaults[field] for field, key in VEIN_FIELDS.values()}
    fact('config_group', dict(keys=sorted(set(neo_ints) | set(neo_bools)), ints=neo_ints, bools=neo_bools), dict(keys=sorted(CONFIG_KEYS), ints=expected_ints, bools={'netherOres': True, 'endOres': True, 'enablePlutoniumNetherOre': False}),
         ok=sorted(set(neo_ints) | set(neo_bools)) == sorted(CONFIG_KEYS) and neo_ints == expected_ints and neo_bools == {'netherOres': True, 'endOres': True, 'enablePlutoniumNetherOre': False}
         and len(CONFIG_KEYS) == EXPECTED['config_values'] and 'private static boolean' not in config_text and all(o_bools.values()))
    fact('config_ranges', dict(neo_range=sorted(set(re.findall(r'defineInRange\("\w+",\s*-?\d+,\s*(-?\d+),\s*(-?\d+)\)', config_text)))), None, ok=sorted(set(re.findall(r'defineInRange\("\w+",\s*-?\d+,\s*(-?\d+),\s*(-?\d+)\)', config_text))) == [('0', '256')])
    # 4c. The two codec types: the registry class registers config_gated_add_features and config_count; the biome modifier reads the switch when it is applied, the placement reads the count per chunk.
    n_codecs, n_modifier, n_placement = code(WORLDGEN_CODECS), code(GATED_MODIFIER), code(COUNT_PLACEMENT)
    fact('codec_types', dict(biome_modifier='"config_gated_add_features"' in n_codecs and 'BIOME_MODIFIER_SERIALIZERS' in n_codecs, placement='"config_count"' in n_codecs and 'PLACEMENT_MODIFIER_TYPES' in n_codecs,
                             modifier_reads_switch=bool(re.search(r'worldgenSwitch\(\w+\)\.get\(\)', n_modifier)), placement_reads_count=bool(re.search(r'worldgenCount\(this\.config\)\.get\(\)', n_placement)),
                             switch_names_validated='WORLDGEN_SWITCHES' in n_modifier, count_names_validated='WORLDGEN_COUNTS' in n_placement,
                             registered_in_mod_class='NtmWorldgenCodecs.register(' in code(NUCLEAR_TECH_MOD)),
         dict(biome_modifier=True, placement=True, modifier_reads_switch=True, placement_reads_count=True, switch_names_validated=True, count_names_validated=True, registered_in_mod_class=True))
    switches = set(re.findall(r'Set\.of\(("[^)]*)\)', neo_text(COMMON_CONFIG)))
    fact('config_name_sets', dict(switches=re.findall(r'WORLDGEN_SWITCHES = Set\.of\(([^)]*)\)', neo_text(COMMON_CONFIG)), counts_listed=len(re.findall(r'"(\w+SpawnRate)"', ''.join(re.findall(r'WORLDGEN_COUNTS = Set\.of\(([^;]*)\);', neo_text(COMMON_CONFIG)))))),
         None, ok='"netherOres", "endOres", "enablePlutoniumNetherOre"' in neo_text(COMMON_CONFIG) and len(re.findall(r'"(\w+SpawnRate)"', ''.join(re.findall(r'WORLDGEN_COUNTS = Set\.of\(([^;]*)\);', neo_text(COMMON_CONFIG))))) == len(VEIN_FIELDS))
    # 4d. The four biome modifiers: the six nether ores behind netherOres (HbmWorldGen.java:503), the plutonium vein behind netherOres AND enablePlutoniumNetherOre (:511-512), smoldering netherrack not
    # gated (:527-535 sits outside the netherOre block: a plain neoforge:add_features) and placed in the last step, after vanilla nether population as in the original, the end trixite behind endOres (:549-551).
    def modifier(name): return generated_json(GENERATED_ROOT+f'data/hbmsntm/neoforge/biome_modifier/{name}.json')
    wants = {'add_nether_ores': ('hbmsntm:config_gated_add_features', '#minecraft:is_nether', ['netherOres'], [f'hbmsntm:ore_nether_{n}_placed' for n in ('uranium', 'tungsten', 'sulfur', 'fire', 'coal', 'cobalt')]),
             'add_nether_plutonium_ore': ('hbmsntm:config_gated_add_features', '#minecraft:is_nether', ['netherOres', 'enablePlutoniumNetherOre'], 'hbmsntm:ore_nether_plutonium_placed'),
             'add_smoldering_netherrack': ('neoforge:add_features', '#minecraft:is_nether', None, 'hbmsntm:smoldering_netherrack_placed'),
             'add_end_ores': ('hbmsntm:config_gated_add_features', '#minecraft:is_end', ['endOres'], 'hbmsntm:ore_tikite_placed')}
    got = {}
    for name, (type_, biomes, config, features_) in wants.items():
        m = modifier(name) or {}
        got[name] = dict(type=m.get('type'), biomes=m.get('biomes'), config=m.get('config'), features=m.get('features'), step=m.get('step'))
    fact('biome_modifiers', got, {n: dict(type=w[0], biomes=w[1], config=w[2], features=w[3], step='top_layer_modification' if n == 'add_smoldering_netherrack' else 'underground_ores') for n, w in wants.items()})
    smolder = gen('configured_feature', 'smoldering_netherrack')
    fact('smoldering_feature', dict(configured=smolder, placed=(gen('placed_feature', 'smoldering_netherrack_placed') or {}).get('placement')), dict(configured={'type': 'hbmsntm:smoldering_netherrack', 'config': {}}, placed=[]))
    # 4e. Smoldering netherrack: 30 tries per chunk, d = 16 + rand(96), y = d-5..d, replace netherrack under air (HbmWorldGen.java:527-535). NEO: SmolderingNetherrackFeature constants.
    o_loop = re.search(r'for\(int k = 0; k < (\d+); k\+\+\)\{\s*int x = i \+ rand\.nextInt\(16\);\s*int z = j \+ rand\.nextInt\(16\);\s*int d = (\d+) \+ rand\.nextInt\((\d+)\);\s*for\(int y = d - (\d+); y <= d; y\+\+\)\s*if\(world\.getBlock\(x, y \+ 1, z\) == Blocks\.air && world\.getBlock\(x, y, z\) == Blocks\.netherrack\)\s*world\.setBlock\(x, y, z, ModBlocks\.ore_nether_smoldering\)', o[O_WORLDGEN])
    o_smolder = dict(tries=int(o_loop.group(1)), min_height=int(o_loop.group(2)), variation=int(o_loop.group(3)), scan_depth=int(o_loop.group(4))) if o_loop else None
    n_feature = code(SMOLDERING_FEATURE)
    n_smolder = dict(tries=int(re.search(r'TRIES\s*=\s*(\d+)', n_feature).group(1)) if re.search(r'TRIES\s*=\s*(\d+)', n_feature) else None, min_height=int(re.search(r'MIN_HEIGHT\s*=\s*(\d+)', n_feature).group(1)) if re.search(r'MIN_HEIGHT\s*=\s*(\d+)', n_feature) else None,
                     variation=int(re.search(r'HEIGHT_VARIATION\s*=\s*(\d+)', n_feature).group(1)) if re.search(r'HEIGHT_VARIATION\s*=\s*(\d+)', n_feature) else None,
                     scan_depth=int(re.search(r'SCAN_DEPTH\s*=\s*(\d+)', n_feature).group(1)) if re.search(r'SCAN_DEPTH\s*=\s*(\d+)', n_feature) else None)
    fact('smoldering_loop', dict(original=o_smolder, neo=n_smolder, neo_replaces_netherrack_under_air=bool(re.search(r'is\(Blocks\.NETHERRACK\)', n_feature)) and bool(re.search(r'above\(\)\)\.is\(Blocks\.AIR\)', n_feature))), None,
         ok=o_smolder == EXPECTED['smoldering'] == dict(tries=n_smolder['tries'], min_height=n_smolder['min_height'], variation=n_smolder['variation'], scan_depth=n_smolder['scan_depth'])
         and bool(re.search(r'is\(Blocks\.NETHERRACK\)', n_feature)) and bool(re.search(r'above\(\)\)\.is\(Blocks\.AIR\)', n_feature)))
    fact('worldgen_names', dict(configured=len([n for n in WORLDGEN_NAMES if gen('configured_feature', n)]), placed=len([n for n in WORLDGEN_NAMES if gen('placed_feature', n+'_placed')]),
                                biome_modifiers=len([n for n in BIOME_MODIFIER_NAMES if modifier(n)])), dict(configured=EXPECTED['configured_features'], placed=EXPECTED['placed_features'], biome_modifiers=EXPECTED['biome_modifiers']))
    # 4f. The six blocks (ModBlocks.java:1258-1267): hardness / resistance / light, the outgas and burn classes.
    o_blocks = {}
    for line in o[O_MODBLOCKS].split('\n'):
        m = re.match(r'\s*(ore_nether_(?:coal|smoldering|uranium|uranium_scorched|tungsten|sulfur|fire|cobalt|plutonium)) = new (\w+)\(Material\.rock(?:, (true|false), (\d+), (true|false))?\)'
                     r'.*?setHardness\(([\d.]+)F\)\.setResistance\(([\d.]+)F\)', line)
        if m: o_blocks[m.group(1)] = dict(cls=m.group(2), args=[m.group(3), m.group(4), m.group(5)] if m.group(3) else None, hardness=float(m.group(6)), resistance=float(m.group(7)),
                                         light=(round(eval(re.search(r'setLightLevel\(([\d./F]+)\)', line).group(1).replace('F', '.0'))*15) if 'setLightLevel' in line else 0))
    n_blocks_code = code(NTM_BLOCKS)
    n_blocks = {}
    for name in o_blocks:
        m = re.search(r'register\("'+name+r'",\s*\(\)\s*->\s*new (\w+)\(((?:true|false), (?:true|false), )?BlockBehaviour\.Properties\.of\(\)\.strength\(([\d.]+)F\)\.explosionResistance\(([\d.]+)F\)([^\n]*?)\)\);', n_blocks_code)
        if m:
            light = re.search(r'lightLevel\(state -> (\d+)\)', m.group(5))
            n_blocks[name] = dict(cls=m.group(1), args=[a.strip() for a in m.group(2).strip().rstrip(',').split(',')] if m.group(2) else None, hardness=float(m.group(3)), resistance=float(m.group(4)), light=int(light.group(1)) if light else 0)
    expected_classes = {'ore_nether_coal': 'NetherCoalBlock', 'ore_nether_smoldering': 'SmolderBlock', 'ore_nether_uranium': 'OutgasBlock', 'ore_nether_uranium_scorched': 'OutgasBlock'}
    blocks_ok = {n for n in o_blocks if n in n_blocks and n_blocks[n]['hardness'] == o_blocks[n]['hardness'] and n_blocks[n]['resistance'] == o_blocks[n]['resistance'] and n_blocks[n]['light'] == o_blocks[n]['light']
                 and n_blocks[n]['cls'] == expected_classes.get(n, 'Block')}
    fact('block_properties', {n: dict(original=o_blocks[n], neo=n_blocks.get(n)) for n in o_blocks}, None, ok=blocks_ok == {n for n in o_blocks if n != 'ore_nether_plutonium'} | ({'ore_nether_plutonium'} & blocks_ok)
         and {'ore_nether_coal', 'ore_nether_smoldering', 'ore_nether_uranium', 'ore_nether_tungsten', 'ore_nether_sulfur', 'ore_nether_fire', 'ore_nether_cobalt'} <= blocks_ok)
    fact('block_outgas_args', dict(original_uranium=o_blocks.get('ore_nether_uranium', {}).get('args'), original_coal=o_blocks.get('ore_nether_coal', {}).get('args'), neo_uranium=n_blocks.get('ore_nether_uranium', {}).get('args'),
                                   neo_coal=n_blocks.get('ore_nether_coal', {}).get('args')), dict(original_uranium=['true', '5', 'true'], original_coal=['false', '5', 'true'], neo_uranium=['true', 'true'], neo_coal=['false', 'true']))
    # 4g. Drops (BlockOre.java:60-119, BlockNetherCoal.java, BlockSmolder.java:35): the loot tables derive from these figures.
    def drops(name):
        d = generated_json(GENERATED_ROOT+f'data/hbmsntm/loot_table/blocks/{name}.json')
        if not d: return None
        out = []

        def walk(node):
            if isinstance(node, dict):
                if node.get('type') == 'minecraft:item':
                    count = next((f for f in node.get('functions', []) if f.get('function') == 'minecraft:set_count'), None)
                    chance = next((c for c in node.get('conditions', []) if c.get('condition') == 'minecraft:random_chance'), None)
                    silk = any(c.get('condition') == 'minecraft:match_tool' for c in node.get('conditions', []))
                    out.append(dict(item=node.get('name'), silk_touch=silk, chance=chance['chance'] if chance else None,
                                    count=[count['count']['min'], count['count']['max']] if count and isinstance(count.get('count'), dict) else None,
                                    fortune=any(f.get('function') == 'minecraft:apply_bonus' for f in node.get('functions', []))))
                for v in node.values(): walk(v)
            elif isinstance(node, list):
                for v in node: walk(v)
        walk(d.get('pools', []))
        return out
    sulfur = re.search(r'ore_nether_sulfur\) return (\d+) \+ rand\.nextInt\((\d+)\)', o[O_BLOCKORE])
    cobalt = re.search(r'ore_nether_cobalt\) return (\d+) \+ rand\.nextInt\((\d+)\)', o[O_BLOCKORE])
    fire = re.search(r'rand\.nextInt\((\d+)\) == 0 \? ModItems\.(\w+) : ModItems\.(\w+)', o[O_BLOCKORE])
    coal_drop, smolder_drop = re.search(r'return ModItems\.(\w+);', o[O_NETHERCOAL]), re.search(r'return ModItems\.(\w+);', o[O_SMOLDER])
    names = {'sulfur': 'hbmsntm:sulfur', 'fragment_cobalt': 'hbmsntm:fragment_cobalt', 'ingot_phosphorus': 'hbmsntm:ingot_phosphorus', 'powder_fire': 'hbmsntm:powder_fire', 'coal_infernal': 'hbmsntm:coal_infernal'}
    expected_drops = {}
    if sulfur: expected_drops['ore_nether_sulfur'] = ('hbmsntm:sulfur', [int(sulfur.group(1)), int(sulfur.group(1)) + int(sulfur.group(2)) - 1], None)
    if cobalt: expected_drops['ore_nether_cobalt'] = ('hbmsntm:fragment_cobalt', [int(cobalt.group(1)), int(cobalt.group(1)) + int(cobalt.group(2)) - 1], None)
    got_drops = {n: drops(n) for n in ('ore_nether_sulfur', 'ore_nether_cobalt', 'ore_nether_fire', 'ore_nether_coal', 'ore_nether_smoldering', 'ore_nether_tungsten')}
    drop_ok = bool(sulfur and cobalt and fire and coal_drop and smolder_drop)
    for n, (item, count, _) in expected_drops.items():
        drop_ok = drop_ok and any(d['item'] == item and d['count'] == count and not d['silk_touch'] for d in got_drops[n] or [])
    drop_ok = drop_ok and bool(fire) and any(d['item'] == names.get(fire.group(2)) and d['chance'] == 1/int(fire.group(1)) for d in got_drops['ore_nether_fire'] or []) \
        and any(d['item'] == names.get(fire.group(3)) and not d['silk_touch'] for d in got_drops['ore_nether_fire'] or []) \
        and any(d['item'] == names.get(coal_drop.group(1)) and not d['silk_touch'] for d in got_drops['ore_nether_coal'] or []) \
        and any(d['item'] == names.get(smolder_drop.group(1)) and not d['silk_touch'] for d in got_drops['ore_nether_smoldering'] or []) \
        and [d['item'] for d in got_drops['ore_nether_tungsten'] or []] == ['hbmsntm:ore_nether_tungsten']
    fact('drops', dict(original=dict(sulfur=sulfur.groups() if sulfur else None, cobalt=cobalt.groups() if cobalt else None, fire=fire.groups() if fire else None, coal=coal_drop.group(1) if coal_drop else None,
                                     smoldering=smolder_drop.group(1) if smolder_drop else None), neo=got_drops), None, ok=drop_ok)
    pickaxe = read(ROOT/PICKAXE_TAG)['values'] if (ROOT/PICKAXE_TAG).is_file() else []
    fact('pickaxe_tag', {n: 'hbmsntm:'+n in pickaxe for n in BLOCK_NAMES}, {n: True for n in BLOCK_NAMES})
    # 4h. Outgassing (BlockOutgas.java:43-56): radon from the nether uranium ores, carbon monoxide from nether coal; burning (BlockNetherCoal / BlockSmolder entity.setFire(3)).
    n_outgas, n_coal, n_smolder_block = code(OUTGAS_BLOCK), code(NETHER_COAL_BLOCK), code(SMOLDER_BLOCK)
    fact('outgassing', dict(original_radon='this == ModBlocks.ore_nether_uranium || this == ModBlocks.ore_nether_uranium_scorched' in o[O_OUTGAS], original_monoxide='this == ModBlocks.ore_nether_coal' in o[O_OUTGAS],
                            neo_radon=bool(re.search(r'ORE_NETHER_URANIUM\.get\(\)\s*\|\|\s*this\s*==\s*NtmBlocks\.ORE_NETHER_URANIUM_SCORCHED\.get\(\)\)\s*\{\s*return NtmBlocks\.GAS_RADON', n_outgas)),
                            neo_monoxide=bool(re.search(r'ORE_NETHER_COAL\.get\(\)\)\s*\{\s*return NtmBlocks\.GAS_MONOXIDE', n_outgas))),
         dict(original_radon=True, original_monoxide=True, neo_radon=True, neo_monoxide=True))
    fact('burning', dict(original_coal='entity.setFire(3)' in o[O_NETHERCOAL], original_smoldering='entity.setFire(3)' in o[O_SMOLDER],
                         neo_coal=bool(re.search(r'(?:igniteForSeconds|setRemainingFireTicks|setSecondsOnFire)\(\s*(?:3|60)', n_coal)), neo_smoldering=bool(re.search(r'(?:igniteForSeconds|setRemainingFireTicks|setSecondsOnFire)\(\s*(?:3|60)', n_smolder_block))),
         dict(original_coal=True, original_smoldering=True, neo_coal=True, neo_smoldering=True))
    # 4i. Recipes and items: the hand drills (ToolRecipes.java:141-142, ModItems.java:3711-3712), the smelting rows (SmeltingRecipes.java:38,46), infernal coal as fuel (FuelHandler.java:41) and in the
    # shredder and crystallizer (ShredderRecipes.java:150,199; CrystallizerRecipes.java:89-90,104).
    def recipe(name): return generated_json(GENERATED_ROOT+f'data/hbmsntm/recipe/{name}.json')
    hd, hdd = recipe('hand_drill') or {}, recipe('hand_drill_desh') or {}
    drill_pattern = r"new ItemStack\(ModItems\.%s\), new Object\[\] \{ \"([^\"]*)\", \"([^\"]*)\", \"([^\"]*)\", 'D', (\w+)\.ingot\(\), 'S', (\w+)(?:\.ingot\(\))? \}"
    o_drill = re.search(drill_pattern % 'hand_drill', o[O_TOOLRECIPES])
    o_desh = re.search(drill_pattern % 'hand_drill_desh', o[O_TOOLRECIPES])
    fact('hand_drill_recipes', dict(original=dict(drill=o_drill.groups() if o_drill else None, desh=o_desh.groups() if o_desh else None),
                                    neo=dict(drill=[hd.get('pattern'), {k: v.get('item') or v.get('tag') for k, v in hd.get('key', {}).items()}, hd.get('result')],
                                             desh=[hdd.get('pattern'), {k: v.get('item') or v.get('tag') for k, v in hdd.get('key', {}).items()}, hdd.get('result')])), None,
         ok=bool(o_drill and o_desh) and hd.get('pattern') == list(o_drill.groups()[:3]) and (o_drill.group(4), o_drill.group(5)) == ('DURA', 'KEY_STICK')
         and hd.get('key', {}).get('D', {}).get('item') == 'hbmsntm:ingot_dura_steel' and hd.get('key', {}).get('S', {}).get('item') == 'minecraft:stick' and hd.get('result', {}).get('id') == 'hbmsntm:hand_drill'
         and hdd.get('pattern') == list(o_desh.groups()[:3]) and (o_desh.group(4), o_desh.group(5)) == ('DESH', 'ANY_PLASTIC') and hdd.get('key', {}).get('D', {}).get('item') == 'hbmsntm:ingot_desh'
         and hdd.get('key', {}).get('S', {}).get('tag') and hdd.get('result', {}).get('id') == 'hbmsntm:hand_drill_desh')
    smelt = {n: recipe(f'ingot_{m}_from_smelting_ore_nether_{m}') or {} for n, m in (('tungsten', 'tungsten'), ('cobalt', 'cobalt'))}
    fact('smelting_rows', {n: dict(ingredient=r.get('ingredient', {}).get('item'), result=r.get('result', {}).get('id'), experience=r.get('experience')) for n, r in smelt.items()},
         None, ok=smelt['tungsten'].get('ingredient', {}).get('item') == 'hbmsntm:ore_nether_tungsten' and smelt['tungsten'].get('result', {}).get('id') == 'hbmsntm:ingot_tungsten'
         and smelt['cobalt'].get('ingredient', {}).get('item') == 'hbmsntm:ore_nether_cobalt' and smelt['cobalt'].get('result', {}).get('id') == 'hbmsntm:ingot_cobalt'
         and 'ModBlocks.ore_nether_tungsten), new ItemStack(ModItems.ingot_tungsten)' in o[O_SMELTING] and 'ModBlocks.ore_nether_cobalt), new ItemStack(ModItems.ingot_cobalt)' in o[O_SMELTING])
    n_items_code = code(NTM_ITEMS)
    fact('items', dict(original_fuel='if(fuel.getItem() == ModItems.coal_infernal)' in o[O_FUEL] and 'return 4800;' in o[O_FUEL],
                       neo_fuel=bool(re.search(r'"coal_infernal",\s*\(\)\s*->\s*new FuelItem\(new Item\.Properties\(\),\s*4800\)', n_items_code)),
                       original_drills='new ItemTooling(ToolType.HAND_DRILL, 100)' in o[O_MODITEMS] and 'new ItemTooling(ToolType.HAND_DRILL, 0)' in o[O_MODITEMS],
                       neo_drills=bool(re.search(r'"hand_drill",\s*\(\)\s*->\s*new ToolingItem\(ToolType\.HAND_DRILL,\s*new Item\.Properties\(\)\.durability\(100\)\)', n_items_code))
                       and bool(re.search(r'"hand_drill_desh",\s*\(\)\s*->\s*new ToolingItem\(ToolType\.HAND_DRILL,\s*new Item\.Properties\(\)\)', n_items_code))),
         dict(original_fuel=True, neo_fuel=True, original_drills=True, neo_drills=True))
    fact('processing_rows', dict(original=dict(shred_fire='setRecipe(ModBlocks.ore_nether_fire, new ItemStack(ModItems.powder_fire, 6))' in o[O_SHREDDER], shred_infernal='setRecipe(ModItems.coal_infernal, new ItemStack(ModItems.powder_coal, 2))' in o[O_SHREDDER],
                                       cryst_fire='ore_nether_fire),\tnew CrystallizerRecipe(ModItems.crystal_phosphorus' in o[O_CRYSTALLIZER] or 'ComparableStack(ModBlocks.ore_nether_fire)' in o[O_CRYSTALLIZER],
                                       cryst_tikite='ComparableStack(ModBlocks.ore_tikite)' in o[O_CRYSTALLIZER], cryst_infernal='ComparableStack(ModItems.coal_infernal)' in o[O_CRYSTALLIZER]),
                                 neo=dict(shred_fire=bool(re.search(r'ORE_NETHER_FIRE', code(SHREDDER_RECIPES))), shred_infernal=bool(re.search(r'COAL_INFERNAL', code(SHREDDER_RECIPES))),
                                          cryst_fire=bool(re.search(r'ORE_NETHER_FIRE', code(CRYSTALLIZER_RECIPES))), cryst_tikite=bool(re.search(r'ORE_TIKITE', code(CRYSTALLIZER_RECIPES))),
                                          cryst_infernal=bool(re.search(r'COAL_INFERNAL', code(CRYSTALLIZER_RECIPES))), centrifuge_plutonium=bool(re.search(r'ORE_NETHER_PLUTONIUM', code(CENTRIFUGE_RECIPES))))), None,
         ok=all(v for v in (('setRecipe(ModBlocks.ore_nether_fire' in o[O_SHREDDER], 'setRecipe(ModItems.coal_infernal' in o[O_SHREDDER], 'ComparableStack(ModBlocks.ore_nether_fire)' in o[O_CRYSTALLIZER],
                              'ComparableStack(ModBlocks.ore_tikite)' in o[O_CRYSTALLIZER], 'ComparableStack(ModItems.coal_infernal)' in o[O_CRYSTALLIZER],
                              'ORE_NETHER_FIRE' in code(SHREDDER_RECIPES), 'COAL_INFERNAL' in code(SHREDDER_RECIPES), 'ORE_NETHER_FIRE' in code(CRYSTALLIZER_RECIPES), 'ORE_TIKITE' in code(CRYSTALLIZER_RECIPES),
                              'COAL_INFERNAL' in code(CRYSTALLIZER_RECIPES)))))
    # 4j. The fluid burner (HeaterOilburner*, TileEntityHeaterOilburner.java): 500,000 TU base, overdrive multiplies the burn rate (10 * (od + 1)) and the heat capacity, the setting is a slider saved as "setting".
    n_burner = code(BURNER_BE)
    fact('fluid_burner', dict(original=dict(capacity='public int maxHeatEnergy = 500_000' in o[O_BURNER_TE], rate='this.maxBurnRate = 10 * (od + 1)' in o[O_BURNER_TE], heat='this.maxHeatEnergy = 500_000 * (od + 1)' in o[O_BURNER_TE]),
                              neo=dict(capacity='maxHeatEnergy = 500_000;' in n_burner, rate='this.maxBurnRate = 10 * (overdrive + 1)' in n_burner, heat='this.maxHeatEnergy = 500_000 * (overdrive + 1)' in n_burner,
                                       saves_setting='tag.putInt("setting"' in n_burner, screwdriver_config_removed='IToolable' not in code(BURNER_BLOCK) and 'onScrew' not in code(BURNER_BLOCK))), None,
         ok='public int maxHeatEnergy = 500_000' in o[O_BURNER_TE] and 'this.maxBurnRate = 10 * (od + 1)' in o[O_BURNER_TE] and 'this.maxHeatEnergy = 500_000 * (od + 1)' in o[O_BURNER_TE]
         and 'maxHeatEnergy = 500_000;' in n_burner and 'this.maxBurnRate = 10 * (overdrive + 1)' in n_burner and 'this.maxHeatEnergy = 500_000 * (overdrive + 1)' in n_burner and 'tag.putInt("setting"' in n_burner)
    fact('generic_recipe_icon', dict(original_line='this.setIcon(stacks.get(0))' in o[O_GENERIC_RECIPE], neo_line='this.setIcon(stacks.get(0))' in code(GENERIC_RECIPE)), dict(original_line=True, neo_line=True))
    fact('scraps_entity_name', dict(neo=bool(re.search(r'getDescriptionId\(ItemStack stack\)\s*\{\s*return this\.getDescriptionId\(\) \+ "\.generic";', code(COPPER_SCRAPS)))), dict(neo=True))
    fact('client_isolation', dict(client_references_in_common_classes=sorted(p for p in (GATED_MODIFIER, COUNT_PLACEMENT, WORLDGEN_CODECS, SMOLDERING_FEATURE, NETHER_COAL_BLOCK, SMOLDER_BLOCK, OUTGAS_BLOCK) if (ROOT/p).is_file()
                                                                      and re.search(r'net\.minecraft\.client|com\.hbm\.render\.|mezz\.jei', code(p)))), dict(client_references_in_common_classes=[]))
    facts['original_references'] = original_refs
    need(not bad, 'nether-end-worldgen facts differ from the original or the handoff figures (or the NEO source / generated file is missing or its text differs): '+', '.join(
        f'{k}={json.dumps(facts[k], ensure_ascii=False)[:240]}' for k in bad))
    # The materials/reachability record (the main agent's; pending until written): it must say which items and rows are reachable and which sources are new.
    ledger = read(ROOT/LEDGER) if (ROOT/LEDGER).is_file() else None
    if need(ledger is not None, 'record missing: '+LEDGER):
        need(str(ledger.get('goal')) == '28A', f'{LEDGER} is not the Goal 28A ledger')

    # 5. Resources: the byte imports (original worktree file and stored blob at 4f5924e2b), against migration/goal28a-resource-ownership.json.
    ownership = read(ROOT/RESOURCE_OWNERSHIP) if (ROOT/RESOURCE_OWNERSHIP).is_file() else None

    def original_texture(target):
        """The original path of an imported NEO texture: item/x.png <- textures/items/x.png, block/x.png[.mcmeta] <- textures/blocks/x.png[.mcmeta], gui/machine/x.png <- textures/gui/machine/x.png."""
        rel = target[len(TEXTURE_ROOT):]
        if rel.startswith('item/'): return O_RES+'textures/items/'+rel[len('item/'):]
        if rel.startswith('block/'): return O_RES+'textures/blocks/'+rel[len('block/'):]
        return O_RES+'textures/'+rel

    imported_facts = {}
    for target in sorted(imported):
        original = original_texture(target)
        if not (SOURCE/original).is_file():
            need(False, 'no original texture for the imported resource '+target+' (expected '+original+')')
            continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        imported_facts[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size, original_worktree_sha256=sha(SOURCE/original),
                                      original_blob_sha256=hashlib.sha256(blob).hexdigest(), start_sha256=base['files'].get(target), replaced=target in base['files'])
        need((ROOT/target).read_bytes() == checked_out == blob, f'{target} is not byte-identical to the original {original} (worktree and stored blob at {SOURCE_HEAD[:8]})')
    need(set(REQUIRED_TEXTURES) <= imported, 'imported textures missing: '+str(sorted(set(REQUIRED_TEXTURES) - imported)))
    need(len(imported) == EXPECTED['imported_assets'], f'{len(imported)} imported textures, the handoff lists {EXPECTED["imported_assets"]}')
    replaced_gui = imported_facts.get(GUI_TEXTURE)
    need(GUI_TEXTURE in base['files'] and (replaced_gui is None or replaced_gui['start_sha256'] != replaced_gui['sha256']), GUI_TEXTURE+' is not a replaced start file (the fluid burner GUI is replaced by the original bytes)')
    if need(ownership is not None, 'record missing: '+RESOURCE_OWNERSHIP):
        entries = {a.get('target_path'): a for a in ownership.get('imported_assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == imported, f'{RESOURCE_OWNERSHIP} imported_assets are not the {len(imported)} imported textures at {SOURCE_HEAD[:8]}: {sorted(set(entries) ^ imported)[:4]}')
        for target, entry in entries.items():
            if target in imported_facts:
                need(entry.get('source_path') == imported_facts[target]['original_path'] and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('size') == (ROOT/target).stat().st_size,
                     f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original: {target}')

    # 6. features.json: ONE new group world-generation; every group advances reviewed_source_commit to 4f5924e2b; no group changes status; only materials, centrifuge, crystallization, shredder, fluid-burner
    # and the new group may change notes / target_paths / target_watch (the handoff list).
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_PREVIOUS for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES <= set(start_features) and (NOTES_MAY_CHANGE - {NEW_FEATURE}) <= set(start_features), 'The start mapping does not hold the groups of 24B-27D'
    may_change = lambda i: i in NOTES_MAY_CHANGE
    need(set(by_id) == set(start_features) | {NEW_FEATURE}, 'features.json group ids are not the start ids + world-generation: '+str(sorted(set(by_id) ^ (set(start_features) | {NEW_FEATURE}))))
    group_world = by_id.get(NEW_FEATURE)
    if need(group_world is not None, 'migration/features.json lacks the group '+NEW_FEATURE):
        need(group_world.get('status') == 'partial-unverified' and group_world.get('reviewed_source_commit') == SOURCE_HEAD, f'features.json group {NEW_FEATURE} is not partial-unverified at {SOURCE_HEAD[:8]}')
        unlisted = [p for p in O_SOURCES if not any(feature_matches(f, 'source', p) for f in features)]
        need(not unlisted, f'features.json lists these original sources in no group (source_paths / source_watch): {unlisted}')
        mapped_java = [p for p in NEW_JAVA + [pp for pp in (OUTGAS_BLOCK, COMMON_CONFIG) if pp in changes] if p != WORLDGEN_TESTS and not any(feature_matches(f, 'target', p) for f in features)]
        need(not mapped_java, f'features.json maps these new / changed Java paths in no group (target_paths / target_watch): {mapped_java[:4]}')
    absent = sorted({p for f in features for p in f.get('source_paths', []) if not (SOURCE/p).is_file()})
    need(not absent, f'features.json source_paths missing in the original: {absent[:6]}')
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    need(all(may_change(i) for i in notes_changed), 'features.json groups whose notes changed beyond materials / centrifuge / crystallization / shredder / fluid-burner: '+str([i for i in notes_changed if not may_change(i)]))
    paths_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('target_paths') != start_features[i].get('target_paths'))
    need(all(may_change(i) for i in paths_changed), 'features.json groups whose target_paths changed beyond materials / centrifuge / crystallization / shredder / fluid-burner: '+str([i for i in paths_changed if not may_change(i)]))
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in ('notes', 'target_watch', 'target_paths', 'reviewed_source_commit')} !=
                          {k: v for k, v in start_features[i].items() if k not in ('notes', 'target_watch', 'target_paths', 'reviewed_source_commit')})
    need(not shrunk and not other_fields, f'features.json previous groups lost target_watch entries {shrunk} or changed other fields {other_fields}')
    watch_grown = sorted(i for i, f in by_id.items() if i in start_features and set(f.get('target_watch', [])) - set(start_features[i].get('target_watch', [])))
    need(all(may_change(i) for i in watch_grown), 'features.json groups whose target_watch grew beyond materials / centrifuge / crystallization / shredder / fluid-burner: '+str([i for i in watch_grown if not may_change(i)]))
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped; the main agent adds target_paths / target_watch to world-generation): '+str(unmapped[:6]))

    # 7. Language and the generated tree: 21 new keys (the six ore names, the infernal coal and two hand drills, the eleven worldgen config keys and the burner's ignition text), the two
    # heater_oilburner descriptions reworded; the stamp must be current, the generated additions the nether / end worldgen set.
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
    need(all(v['en'] and v['zh'] for v in local_keys.values()), 'a local language key lacks English or Chinese: '+str([k for k, v in local_keys.items() if not (v['en'] and v['zh'])]))
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_en = dict(added=sorted(KEYS), removed=sorted(REMOVED_KEYS), changed=sorted(EN_CHANGED))
    expected_zh = dict(added=sorted(KEYS), removed=sorted(REMOVED_KEYS), changed=sorted(ZH_CHANGED))
    expected_map = dict(added=sorted(KEYS), removed=sorted(REMOVED_KEYS), changed=sorted(set(EN_CHANGED) | set(ZH_CHANGED)))
    need(len(KEYS) == EXPECTED['language_added'], f'expected new language keys: {len(KEYS)}, the files give {EXPECTED["language_added"]} (the handoff text said 34: the delta is 21 added, 0 removed, 2 changed)')
    need(en_delta == expected_en, 'generated en_us.json delta is not the 21 new keys and the two reworded heater_oilburner descriptions: '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_zh, 'zh_cn.json delta is not the 21 new keys and the two reworded heater_oilburner descriptions: '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_map, 'zh_cn-map.json delta is not the 21 new entries and the two changed heater_oilburner entries: '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal27d totals'
    delta_net = len(KEYS) - len(REMOVED_KEYS)
    need(len(en_now) == totals['en_us'] + delta_net and len(zh_now) == totals['zh_cn'] + delta_net and len(map_now) == totals['zh_cn_map'] + delta_net,
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal27d totals {totals} + {delta_net}')
    map_kinds, start_kinds = dict(Counter(e.get('kind') for e in map_now.values())), dict(Counter(e.get('kind') for e in map_start.values()))
    kinds_added = Counter((map_now.get(k) or {}).get('kind') for k in KEYS)
    expected_kinds = {k: start_kinds.get(k, 0) + kinds_added.get(k, 0) for k in set(start_kinds) | set(kinds_added)}
    expected_kinds = {k: v for k, v in expected_kinds.items() if v}
    need(start_kinds == totals['zh_cn_map_by_kind'] and map_kinds == expected_kinds and map_kinds.get('deferred') == EXPECTED['deferred_entries'],
         f'mapping kinds are {map_kinds}, expected the goal27d kinds {totals["zh_cn_map_by_kind"]} adjusted by the added keys {expected_kinds} (deferred {EXPECTED["deferred_entries"]} unchanged)')
    need(dict(kinds_added) == {'upstream': UPSTREAM_ADDED, 'local': LOCAL_ADDED}, f'new mapping entries are {dict(kinds_added)}, expected {UPSTREAM_ADDED} upstream (the six ore names, coal_infernal, the two hand drills) and {LOCAL_ADDED} local (the eleven worldgen config keys, the burner ignition text)')
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
    tags_modified = sorted(p for p in generated_changed if GENERATED_TAGS.fullmatch(GENERATED_ROOT+p))
    need({EN_ENTRY, PICKAXE_TAG[len(GENERATED_ROOT):]} <= set(generated_changed) and set(generated_changed) <= {EN_ENTRY} | set(tags_modified),
         f'Generated resources changed since the start are not en_us.json and the tag files that gained the nether ores (pickaxe.json required): {generated_changed[:8]}')
    world_added = [p for p in generated_added if GENERATED_ADDED.fullmatch(GENERATED_ROOT+p)]
    need(world_added == generated_added, f'Generated additions other than the nether / end worldgen, blockstate, model, loot table and recipe set: {sorted(set(generated_added) - set(world_added))[:6]}')
    counts_added = dict(blockstates=len([p for p in generated_added if '/blockstates/' in p]), block_models=len([p for p in generated_added if '/models/block/' in p]), item_models=len([p for p in generated_added if '/models/item/' in p]),
                        loot_tables=len([p for p in generated_added if '/loot_table/' in p]), recipes=len([p for p in generated_added if p.startswith('data/hbmsntm/recipe/')]),
                        advancements=len([p for p in generated_added if '/advancement/' in p]), configured_features=len([p for p in generated_added if '/configured_feature/' in p]),
                        placed_features=len([p for p in generated_added if '/placed_feature/' in p]), biome_modifiers=len([p for p in generated_added if '/biome_modifier/' in p]))
    need(counts_added == GENERATED_COUNTS, f'generated additions are {counts_added}, the handoff expects {GENERATED_COUNTS}')
    need(sorted(GENERATED_ROOT+p for p in generated_added if True) == sorted(set(REQUIRED_GENERATED) | {GENERATED_ROOT+p for p in generated_added if '/advancement/' in p}),
         'generated additions differ from the expected set: extra %s, missing %s' % (sorted({GENERATED_ROOT+p for p in generated_added} - set(REQUIRED_GENERATED) - {GENERATED_ROOT+p for p in generated_added if '/advancement/' in p})[:6],
                                                                                    sorted(set(REQUIRED_GENERATED) - {GENERATED_ROOT+p for p in generated_added})[:6]))
    advancements = {n: [p for p in generated_added if re.fullmatch(r'data/hbmsntm/advancement/recipes/[a-z]+/'+n+'\\.json', p)] for n in RECIPE_NAMES}
    need(all(len(v) == 1 for v in advancements.values()), 'generated recipe advancements: exactly one per recipe expected: '+str(advancements))
    for path in (v[0] for v in advancements.values() if v):
        adv = read(ROOT/(GENERATED_ROOT+path))
        need(adv.get('rewards') == {'recipes': ['hbmsntm:'+Path(path).stem]}, f'{path} does not reward its own recipe')
    need(len(stamp['generated']) == prior_receipt['generated_resource_count'] + len(generated_added), f'generated resource count {len(stamp["generated"])} is not the goal27d count {prior_receipt["generated_resource_count"]} + {len(generated_added)}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted([STAMP] + [GENERATED_ROOT+p for p in generated_added] + [GENERATED_ROOT+p for p in generated_changed])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, the stamp additions and the stamp changes: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # The start stamp already holds the three small fixes (they are Java inputs; the stamp records every Java input hash): the three files differ between the goal27d stamp inputs and the start stamp.
    small_fix_stamp = {p: dict(start_stamp_input=start_stamp['inputs'].get(p)) for p in SMALL_FIX_JAVA}

    # 8. Evidence: GameTest log, audits, Gradle logs, diff, the final suite run, the verifier report, the casting attribution, compare and the batch's own scripts and records.
    evidence = {}
    gametest_line = gametest_count = None
    worldgen_lines = []
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
    worldgen_test_names = sorted(GAMETEST_METHOD.findall((ROOT/WORLDGEN_TESTS).read_text(encoding='utf-8'))) if (ROOT/WORLDGEN_TESTS).is_file() else []
    worldgen_annotations = annotations(ROOT/WORLDGEN_TESTS) if (ROOT/WORLDGEN_TESTS).is_file() else 0
    need(bool(worldgen_test_names) and worldgen_annotations == len(worldgen_test_names), f'{WORLDGEN_TESTS} holds {worldgen_annotations} @GameTest annotations and {len(worldgen_test_names)} parsed methods (or the file does not exist yet)')
    need(gametest_added == worldgen_annotations, f'GameTest sources grew by {gametest_added} tests, NetherEndWorldgenGameTests holds {worldgen_annotations} (another GameTest class changed its test count, e.g. SmokeTestSupport or RBMKCoreGameTests?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in worldgen_test_names), 'GameTest log lacks "[hbm-28a] <name> passed" for: '+str([n for n in worldgen_test_names if (GAMETEST_MARKER % n) not in text]))
            worldgen_lines = [l.split('[hbm-28a] ', 1)[1].strip() for l in text.splitlines() if '[hbm-28a] ' in l and ' passed' not in l.split('[hbm-28a] ', 1)[1]]
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries, audit_comparison = {}, {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal28a/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad_findings = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad_findings and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad_findings))
        # This batch adds language keys and resources, so the info / review counts may differ from the previous receipt: recorded, not required equal.
        audit_comparison[key] = dict(previous=prior_receipt['audits'][key], now=audit['summary'], equal=audit['summary'] == prior_receipt['audits'][key])
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal28a/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if name == 'production-vs-start.diff':
            if (OUT/name).is_file() and (OUT/name).stat().st_size > 0: evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)  # judged below
            continue
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal28a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    named = list(START_EVIDENCE) + list(REVIEW_EVIDENCE)
    named += sorted(p.name for p in OUT.glob('handoff-*.md') if p.name not in named) + sorted(p.name for p in OUT.glob('*-report.md') if p.name not in named)
    for name in named:
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal28a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/FAIL_SET_DIFF).is_file(): evidence[(OUT/FAIL_SET_DIFF).relative_to(ROOT).as_posix()] = sha(OUT/FAIL_SET_DIFF)
    # The casting regressions (goal27a_casting_regression_run.py, unchanged wrapper): one record per suite in the final rerun's own directory; its transcript is hashed with it.
    casting = {}
    for suite in CASTING_SUITES:
        rec_path = CASTING_DIR/f'{suite}-compat.json'
        if not need(rec_path.is_file(), f'evidence missing: build/migration/goal28a/final/castingsuites/{suite}-compat.json (goal27a_casting_regression_run.py {suite}, redirected into final/ by run_final.py)'): continue
        rec = read(rec_path)
        transcript = ROOT/rec['transcript'] if rec.get('transcript') else None
        casting[suite] = dict(record=rec_path.relative_to(ROOT).as_posix(), exit=rec.get('exit'), mode=rec.get('mode'), blockers=rec.get('blockers'), stages=rec.get('stages'),
                              javac_errors_by_attribution=rec.get('javac_errors_by_attribution'), transcript=rec.get('transcript'))
        evidence[rec_path.relative_to(ROOT).as_posix()] = sha(rec_path)
        if need(transcript is not None and transcript.is_file(), f'{rec_path.name} names no existing transcript'): evidence[transcript.relative_to(ROOT).as_posix()] = sha(transcript)
    attribution = None
    if need((OUT/CASTING_ATTRIBUTION).is_file(), 'evidence missing: build/migration/goal28a/'+CASTING_ATTRIBUTION+' (casting_attribution.py, after the final rerun)'):
        att = read(OUT/CASTING_ATTRIBUTION)
        problems = []
        if att.get('mode') != 'compare' or att.get('missing_inputs'): problems.append(f'mode {att.get("mode")!r}, missing inputs {att.get("missing_inputs")}')
        if att.get('baseline_sha256') != sha(BASELINE) or att.get('tool_sha256') != sha(OUT/'casting_attribution.py'): problems.append('written by another baseline or another version of casting_attribution.py')
        if att.get('old_dir') != (GOAL27D_OUT/'final/castingsuites').relative_to(ROOT).as_posix() or att.get('new_dir') != CASTING_DIR.relative_to(ROOT).as_posix(): problems.append(f'compares {att.get("old_dir")} with {att.get("new_dir")}')
        if sorted(att.get('suites', {})) != sorted(CASTING_SUITES): problems.append('suites '+str(sorted(att.get('suites', {}))))
        for suite, entry in att.get('suites', {}).items():
            for side in ('old', 'new'):
                s = entry.get(side) or {}
                if not s.get('parse_matches_record'): problems.append(f'{suite} {side}: the parsed javac errors do not match the record')
                if side == 'new' and suite in casting and s.get('record_sha256') != sha(ROOT/casting[suite]['record']): problems.append(f'{suite}: the new record changed after the attribution')
            for e in entry.get('new_errors', []) + entry.get('moved', []):
                file = e.get('at', '').rsplit(':', 1)[0] if 'at' in e else (e.get('identity') or {}).get('file', '')
                if e.get('attribution') == 'unattributed': problems.append(f'{suite}: unattributed error {e.get("at") or e.get("identity")}')
                elif e.get('attribution') == '28A change' and file not in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed to a 28A change but the file did not change')
                elif e.get('attribution') == 'not 28A' and file in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed "not 28A" but the file changed')
        need(not problems, CASTING_ATTRIBUTION+' is not a consistent attribution of the two casting regressions: '+'; '.join(problems[:6]))
        attribution = dict(path=(OUT/CASTING_ATTRIBUTION).relative_to(ROOT).as_posix(), sha256=sha(OUT/CASTING_ATTRIBUTION), summary=att.get('summary'),
                           suites={s: dict(counts=e.get('counts'), new_errors_by_attribution=e.get('new_errors_by_attribution'), moved_by_attribution=e.get('moved_by_attribution'),
                                           disappeared_by_file_status=e.get('disappeared_by_file_status'), stages_changed=e.get('stages_changed')) for s, e in att.get('suites', {}).items()})
        evidence[attribution['path']] = attribution['sha256']
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS) | set(COMPARE_EXITS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(set(CHAIN_COMMANDS) | set(COMPARE_EXITS))))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal28a/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files and edited GameTests against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    diffed_modified = [p for p in modified_java + gametest_edit_files if p in changes]
    listed_in_diff = NEW_JAVA + diffed_modified
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal28a/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in diffed_modified) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(p in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([p for p in listed_in_diff if p not in diff_text]))
    final = None
    # The suites of the goal27d final run plus the Goal28A verifier (the two casting regressions are in the goal27d set and run unchanged, redirected into final/; verify_goal27d_molds.py is an old suite now).
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal27d final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal28A suite is already in the goal27d final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal28a/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal27d final set + the Goal28A verifier: '+str(sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal28a/'+VERIFY_REPORT+' (tools/migration/verify_goal28a_worldgen.py report; run it with --gametest-log and --jar after the final build)'):
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
        verifier_references = sorted(set(re.findall(r'(?:HbmWorldGen|DungeonToolbox|WorldConfig|GeneralConfig|ModBlocks|BlockOre|BlockNetherCoal|BlockSmolder|BlockOutgas|SmeltingRecipes|FuelHandler|ToolRecipes|ModItems|'
                                                    r'ShredderRecipes|CrystallizerRecipes|CentrifugeRecipes|TileEntityHeaterOilburner|HeaterOilburner|GenericRecipe)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # The upstream classification: 66 files, path-for-path against git's name-status of the original range (aee05a40f..4f5924e2b); the rename counts as an added (new name) and a removed (old name) file in the compare.
    name_status = {}
    for line in NAME_STATUS.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        parts = line.split('\t')
        name_status[parts[-1]] = {'M': 'modified', 'A': 'added', 'R': 'renamed'}[parts[0][0]]
    assert git_ro(SOURCE, 'diff', '--name-status', '-M', SOURCE_PREVIOUS, SOURCE_HEAD).splitlines() == NAME_STATUS.read_text(encoding='utf-8').splitlines(), 'The original range aee05a40f..4f5924e2b differs from the frozen name-status.txt'
    expected_source_counts = dict(added=sum(1 for v in name_status.values() if v in ('added', 'renamed')), modified=sum(1 for v in name_status.values() if v == 'modified'),
                                  removed=sum(1 for v in name_status.values() if v == 'renamed'))
    need(len(name_status) == EXPECTED['classified_files'] and (expected_source_counts['added'], expected_source_counts['modified'], expected_source_counts['removed']) == (EXPECTED['source_added'], EXPECTED['source_modified'], EXPECTED['source_removed']),
         f'the original range changes {len(name_status)} files with counts {expected_source_counts}, the handoff expects {EXPECTED["classified_files"]} and +{EXPECTED["source_added"]}/~{EXPECTED["source_modified"]}/-{EXPECTED["source_removed"]}')
    classification_summary = classification_entries = None
    if need((ROOT/CLASSIFICATION).is_file(), 'record missing: '+CLASSIFICATION):
        classification = read(ROOT/CLASSIFICATION)
        classification_entries = {e['path']: e for e in classification['entries']}
        need(classification.get('baseline_source_commit') == SOURCE_PREVIOUS and classification.get('reviewed_source_commit') == SOURCE_HEAD and classification.get('neo_commit') == start_head,
             f'{CLASSIFICATION} records other commits than aee05a40f / 4f5924e2b / the start commit')
        need(len(classification['entries']) == len(classification_entries) == len(name_status) and set(classification_entries) == set(name_status),
             f'{CLASSIFICATION} entries differ path-for-path from git diff --name-status -M aee05a40f 4f5924e2b ({len(name_status)} files)')
        classification_summary = dict(Counter(e['category'] for e in classification['entries']))
        need(classification.get('summary') == classification_summary and classification_summary == EXPECTED['categories'], f'{CLASSIFICATION} summary {classification.get("summary")} / entries {classification_summary} differ from {EXPECTED["categories"]}')
        need(set(classification_summary) <= CLASSIFICATION_CATEGORIES, f'{CLASSIFICATION} uses unknown categories: {sorted(set(classification_summary) - CLASSIFICATION_CATEGORIES)}')
        need(all(e.get('decision') and e.get('evidence') for e in classification['entries']), f'{CLASSIFICATION} has entries without a decision or evidence')
    # Compare 1: against the old snapshot (aee05a40f10f): original +5/~61/-1 = the classified range, target = the goal27d compare's target set + the small fixes + this batch's compare-inventory paths.
    cmp_prev = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal27d/compare.json differs from the goal27d receipt'
    prev_added = sorted(p for p in compare_paths(cmp_prev['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    prev_modified = sorted(p for p in compare_paths(cmp_prev['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    # The goal27d compare ran on the goal27d tree: the three small fixes changed three compare-inventory files after it (AnvilRecipeHandler.java and ContaminationUtil.java were modified by the batch
    # itself or new to the compare; gradle.properties is a build file), so the expected target set also holds the small-fix files that differ between the goal27d package and the start.
    small_fix_compare = sorted(p for p in SMALL_FIX_FILES if in_compare_inventory(p))
    expected_target = sorted(set(prev_added) | set(prev_modified) | set(own_target) | set(small_fix_compare))
    expected_added = sorted(set(prev_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare_old = compare = None
    if need((OUT/COMPARE_OLD).is_file(), 'evidence missing: build/migration/goal28a/'+COMPARE_OLD+' (compare against '+SNAPSHOT_OLD+': original +%d/~%d/-%d, target set of %d paths = the %d goal24a-27d paths + the %d small-fix / 28A paths not already among them)' % (
            expected_source_counts['added'], expected_source_counts['modified'], expected_source_counts['removed'], len(expected_target), len(prev_added) + len(prev_modified),
            len((set(own_target) | set(small_fix_compare)) - set(prev_added) - set(prev_modified)))):
        cmp_old = read(OUT/COMPARE_OLD)
        need(cmp_old['kind'] == 'migration-delta' and cmp_old['baseline_source_commit'] == SOURCE_PREVIOUS and cmp_old['current_source_commit'] == SOURCE_HEAD, COMPARE_OLD+' is not the aee05a40f -> 4f5924e2b compare')
        need(cmp_old['current_target_state']['commit'] == start_head, COMPARE_OLD+' records another target commit than the start commit')
        counts_old = {side: {k: len(cmp_old['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(counts_old['source'] == expected_source_counts and counts_old['target']['removed'] == 0, f'{COMPARE_OLD} original is {counts_old["source"]}, expected {expected_source_counts} (and no removed target path): {counts_old}')
        source_old = compare_paths(cmp_old['changes']['source']['added']) | compare_paths(cmp_old['changes']['source']['modified']) | compare_paths(cmp_old['changes']['source']['removed'])
        need(source_old == set(name_status) | {l.split('\t')[1] for l in NAME_STATUS.read_text(encoding='utf-8').splitlines() if l.startswith('R')},
             f'{COMPARE_OLD} source set differs from the 66 classified files (+ the renamed file\'s old name)')
        listed = sorted(p for p in compare_paths(cmp_old['changes']['target']['added']) | compare_paths(cmp_old['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
        need(listed == expected_target, f'{COMPARE_OLD} target set differs: extra %s, missing %s' % (sorted(set(listed) - set(expected_target))[:8], sorted(set(expected_target) - set(listed))[:8]))
        listed_added = sorted(p for p in compare_paths(cmp_old['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
        need(listed_added == expected_added, f'{COMPARE_OLD} target added set differs: extra {sorted(set(listed_added) - set(expected_added))[:6]}, missing {sorted(set(expected_added) - set(listed_added))[:6]}')
        need(set(compare_paths(cmp_old['unmapped_changes']['source'])) <= set(name_status) | {l.split('\t')[1] for l in NAME_STATUS.read_text(encoding='utf-8').splitlines() if l.startswith('R')}
             and set(compare_paths(cmp_old['unmapped_changes']['target'])) <= {'gradle.properties'}, COMPARE_OLD+' reports unmapped changes outside the classified files or an unmapped target change other than gradle.properties (the mod-rename small fix, a build file no mapping group owns): '+str(cmp_old['unmapped_changes'])[:300])
        need(not cmp_old['removed_feature_ids'] and not cmp_old['manifest_missing_files'], COMPARE_OLD+' reports removed features or missing files')
        states_old = Counter(f.get('state') for f in cmp_old['features'])
        compare_old = dict(path=(OUT/COMPARE_OLD).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE_OLD), snapshot=SNAPSHOT_OLD, counts=counts_old, feature_states=dict(states_old),
                           target_listed=len(listed), target_added_listed=len(listed_added), goal27d_paths=len(prev_added) + len(prev_modified), goal28a_paths=len(own_target), small_fix_paths=small_fix_compare,
                           unmapped_source=sorted(compare_paths(cmp_old['unmapped_changes']['source'])))
        evidence[compare_old['path']] = compare_old['sha256']
    # The new snapshot (written by the chain) and compare 2 against it: original 0/0/0, target 0/0/0, unmapped 0/0.
    snapshot = None
    if need((ROOT/SNAPSHOT_NEW).is_file(), 'new snapshot missing: '+SNAPSHOT_NEW+' (the chain\'s snapshot step: migration.py snapshot --output '+SNAPSHOT_NEW+')'):
        snap = read(ROOT/SNAPSHOT_NEW)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '', SNAPSHOT_NEW+' is not a clean observation of the original at 4f5924e2b')
        need(snap['target']['commit'] == start_head, SNAPSHOT_NEW+' records another target commit than the start commit')
        need(len(snap['manifest']['features']) == len(features) and {f['id'] for f in snap['manifest']['features']} == set(by_id), SNAPSHOT_NEW+f' does not hold the {len(features)} mapping groups of features.json')
        snapshot = dict(path=SNAPSHOT_NEW, bytes=(ROOT/SNAPSHOT_NEW).stat().st_size, sha256=sha(ROOT/SNAPSHOT_NEW), new_snapshot=True, source_commit=snap['source']['commit'], old_snapshot=SNAPSHOT_OLD, old_snapshot_sha256=base['snapshot']['sha256'])
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal28a/'+COMPARE+' (compare against '+SNAPSHOT_NEW+': original and target 0/0/0, no unmapped change)'):
        cmp = read(OUT/COMPARE)
        need(cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, COMPARE+' is not against the 4f5924e2b snapshot')
        need(cmp['current_target_state']['commit'] == start_head, COMPARE+' records another target commit than the start commit')
        counts_cmp = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(all(v == 0 for side in counts_cmp.values() for v in side.values()), COMPARE+' is not 0/0/0 on both sides: '+str(counts_cmp))
        need(not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], COMPARE+' reports unmapped changes: '+str(cmp['unmapped_changes']))
        need(not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], COMPARE+' reports removed features or missing files')
        states = Counter(f.get('state') for f in cmp['features'])
        need(len(cmp['features']) == len(features) and set(states) == {'no-observed-file-change'}, f'{COMPARE} feature states are {dict(states)}, expected only no-observed-file-change over {len(features)} groups')
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT_NEW, counts=counts_cmp, feature_states=dict(states))
        evidence[compare['path']] = compare['sha256']

    # The three small fixes packaged and regression-run with this batch (made after the goal27d package, in the start tree; the start JAR already holds them): the goal27d package's file hashes and the JAR
    # entries whose bytes they changed were recorded while build/libs was still the start JAR (verifier-pkg/small-fix-jar-delta.json), because the final build overwrites build/libs.
    small_fix_record = read(SMALL_FIX_DELTA) if SMALL_FIX_DELTA.is_file() else None
    small_fixes, small_fix_entries = {}, {}
    if need(small_fix_record is not None, 'evidence missing: '+SMALL_FIX_DELTA.relative_to(ROOT).as_posix()+' (helper small_fix_delta.py, run while build/libs was the start JAR)'):
        need(small_fix_record['start_jar_sha256'] == start_jar_sha and small_fix_record['goal27d_jar_sha256'] == previous_sha, 'small-fix-jar-delta.json records another start JAR or another goal27d package')
        need(sorted(small_fix_record['jar_entries_modified']) == sorted(['META-INF/neoforge.mods.toml', 'com/hbm/handler/jei/AnvilRecipeHandler.class', 'com/hbm/util/ContaminationUtil.class',
                                                                            'com/hbm/util/ContaminationUtil$ContaminationType.class', 'com/hbm/util/ContaminationUtil$HazardType.class'])
             and not small_fix_record['jar_entries_added'] and not small_fix_record['jar_entries_removed'], 'small-fix-jar-delta.json: the start JAR differs from the goal27d package by other entries than the five of D3, D5 and the rename')
        need(sorted(small_fix_record['tracked_files_differing_goal27d_package_vs_28a_start']) == sorted(['.gitignore', 'README.md', 'README.zh_CN.md', 'gradle.properties', STAMP, SMALL_FIX_JAVA[0], SMALL_FIX_JAVA[1]]),
             'tracked files differing between the goal27d package and the 28A start are not the three small fixes + the README files, .gitignore and the stamp: '+str(small_fix_record['tracked_files_differing_goal27d_package_vs_28a_start']))
        readme_lines = (ROOT/'migration/README.md').read_text(encoding='utf-8').split('\n')
        readme_mark = {'mod-rename': next((i for i, l in enumerate(readme_lines, 1) if l.startswith('2026-10-27 小修') and 'mod_name' in l), None),
                       'D3': next((i for i, l in enumerate(readme_lines, 1) if l.startswith('2026-10-27 小修') and 'D3' in l), None),
                       'D5': next((i for i, l in enumerate(readme_lines, 1) if l.startswith('2026-10-27 小修') and 'D5' in l), None)}
        need(all(readme_mark.values()), 'migration/README.md has no "2026-10-27 小修" line for: '+str([k for k, v in readme_mark.items() if not v]))
        commits = small_fix_commits()
        for p, fix in SMALL_FIX_FILES.items():
            rec = small_fix_record['source_files'][p]
            small_fixes[fix] = dict(file=p, last_commit=commits[p], goal27d_package_sha256=rec['goal27d_package_sha256'], start_sha256=rec['start_sha256'], current_sha256=sha(ROOT/p), readme_line=readme_mark[fix],
                                    changed_in_batch=p in changes, packaging='packaged and regression-run with goal28a')
            need(rec['start_sha256'] == base['files'][p] and rec['goal27d_package_sha256'] != rec['start_sha256'], f'{p}: the goal27d package hash equals the start hash (not a small fix since the package) or the start hash differs from the baseline')
        small_fix_entries = {n: SMALL_FIX_OWNERS['mod-rename'] if n == 'META-INF/neoforge.mods.toml' else SMALL_FIX_OWNERS['D3'] if 'AnvilRecipeHandler' in n else SMALL_FIX_OWNERS['D5'] for n in small_fix_record['jar_entries_modified']}

    # 9. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal28a, a small fix, or a recompile.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the goal27d package (run the final build)')
    need(sha(JAR) != start_jar_sha, 'build/libs/hbmsntm-198A.jar is still the 28A start JAR (the post-rename JAR 0fdd8ac0...): run the final build')
    if True:  # --check also runs the delta code (against the current build/libs, which is still the start JAR until the final build)
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
            need(not differs, f'build/libs JAR differs from the generated resources, the imported textures, zh_cn.json or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == expected_en and zh_jar == expected_zh, 'JAR en_us.json / zh_cn.json differ from the goal27d package by something other than the Goal28A delta: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            recompile_only = {n for n in RECOMPILE_ONLY if n in jar_delta['modified'] and recompile_equal(n, prior.read(n), jar.read(n))}
            small_fix_pure = {n for n in small_fix_entries if n in new and small_fix_record and hashlib.sha256(jar.read(n)).hexdigest() == small_fix_record['jar_entries_modified'][n]['start_jar_sha256']}
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
                # A small fix owns the entry too when the bytes are the start JAR's (no later 28A change); an entry both a small fix and a 28A source touch carries both.
                if n in small_fix_entries and kind == 'modified':
                    if n in small_fix_pure and OWNER not in owner: owner = [small_fix_entries[n]]
                    elif OWNER in owner: owner = [OWNER, small_fix_entries[n]]
                    elif not owner: owner = [small_fix_entries[n]]
                if not owner: unowned.append(f'{kind}: {n}' + (' [source ' + owner_class(n) + ' unchanged since the start: a recompile difference, not a source change]' if n.endswith('.class') and owner_class(n) not in changes else ''))
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without an owner (only classes of the owner-table Java sources and the edited RBMKCoreGameTests, the generated additions / changes (nether ore blockstates, models, loot tables, recipes, '
             'worldgen features, biome modifiers, en_us.json, the pickaxe tag), zh_cn.json, the imported textures, META-INF/MANIFEST.MF and the five small-fix entries are owned): '+str(unowned[:10]))
        need(all(n in jar_delta['modified'] for n in small_fix_entries), 'small-fix JAR entries not in the JAR delta: '+str([n for n in small_fix_entries if n not in jar_delta['modified']]))
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in production_java if p in changes]
        allowed_classes = set(changed_java) | set(SMALL_FIX_JAVA)
        need(set(class_owners) <= allowed_classes and set(changed_java) <= set(class_owners),
             'Changed Java sources and goal28a JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners))) + '; unexpected: '+str(sorted(set(class_owners) - allowed_classes)))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'} - set(SMALL_FIX_JAR_ENTRIES)
        need(non_class == generated_entries, 'JAR non-class delta differs from the generated additions / changes + zh_cn.json + the imported textures: extra %s, missing %s' % (
            sorted(non_class - generated_entries)[:8], sorted(generated_entries - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for p in modified_java + gametest_edit_files:
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
                   generated_added_counts=counts_added, imported_textures=sorted(imported), start_drift=sorted(drift_report), repinned_since_goal27d_start=sorted(repinned), ledger_edit=ledger_edit,
                   language_delta=dict(en=en_delta, zh=zh_delta, map=map_delta), language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, line_endings=line_endings, content_rules=content_rules, gametest_edits={p: dict(added=e['added'], removed=e['removed'], rule_holds=e['rule_holds']) for p, e in gametest_edits.items()},
                   nether_end_worldgen={k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v)) < 200 else f'<{len(v)} items>') for k, v in facts.items()}, nether_end_worldgen_facts_bad=bad,
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_worldgen_tests=worldgen_test_names, final_suites_expected=final_expected,
                   classification=classification_summary, audit_comparison=audit_comparison, small_fixes={k: dict(file=v['file'], last_commit=v['last_commit'], readme_line=v['readme_line']) for k, v in small_fixes.items()},
                   casting_regressions={s: dict(exit=c['exit'], mode=c['mode'], blockers=len(c['blockers'] or []), javac_errors_by_attribution=c['javac_errors_by_attribution']) for s, c in casting.items()},
                   casting_attribution=opt(attribution, 'summary'),
                   compare_old=opt(compare_old, 'counts'), compare=opt(compare, 'counts'), compare_target_expected=len(expected_target), compare_added_expected=len(expected_added),
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
    nether_end_worldgen = dict(neo=NEW_JAVA + modified_java, original=O_SOURCES, facts=facts, expected=EXPECTED, known_differences=KNOWN_DIFFERENCES, original_references=original_refs,
                               language_keys=language_keys, local_language_keys=local_keys, imported_resources=imported_facts, resource_ownership_record=RESOURCE_OWNERSHIP, reachability_record=LEDGER,
                               worldgen_lines_from_gametest_log=worldgen_lines,
                               note=f'Config-gated nether and end ore generation: a worldgen config group of {EXPECTED["config_values"]} keys (three switches netherOres / endOres / enablePlutoniumNetherOre, default off for plutonium, '
                                    f'and eight vein counts) read by two new codec types (hbmsntm:config_gated_add_features when the biome modifier is applied, hbmsntm:config_count per chunk); {EXPECTED["configured_features"]} '
                                    f'configured and placed features (HbmWorldGen.java:503-551: size, y range min..min+variance-1, target netherrack / end_stone) and {EXPECTED["biome_modifiers"]} biome modifiers (the six nether ores behind netherOres, '
                                    'plutonium behind netherOres and enablePlutoniumNetherOre, smoldering netherrack NOT gated as in the original, trixite behind endOres); six nether ore blocks and smoldering netherrack with the '
                                    'original drops (sulfur 2..4, cobalt 5..12, fire ore phosphorus ingot 1/10 else fire powder, nether coal infernal coal, smoldering fire powder), burning (nether coal, smoldering netherrack: 3 s) and '
                                    'outgassing (nether uranium radon, nether coal carbon monoxide); tungsten and cobalt smelting, infernal coal fuel (4800) and its shredder / crystallizer rows, the fire ore and trixite rows; hand drills '
                                    '(durability 100 and unbreakable desh); the fluid burner follows 4f5924e2b (500,000 TU base, GUI slider, overdrive multiplies burn rate and heat capacity, setting saved); GenericRecipe icon through '
                                    'setIcon; JEI anvil tier text and variants; dropped scraps named through item.hbmsntm.scraps.generic. The geyser, the nether bedrock ore and the depth neodymium ore (28B) are not ported; the Sa326 nether '
                                    'ore has no generation in the original; RoR and satellites are not migrated (known_differences).')
    upstream = dict(classification=CLASSIFICATION, baseline_source_commit=SOURCE_PREVIOUS, reviewed_source_commit=SOURCE_HEAD, files=len(name_status), changed_added=expected_source_counts['added'],
                    changed_modified=expected_source_counts['modified'], changed_removed=expected_source_counts['removed'], categories=classification_summary,
                    adapted=[dict(path=p, category=e['category']) for p, e in (classification_entries or {}).items() if e['category'] == 'neo-adapt-28a'],
                    name_status=NAME_STATUS.relative_to(ROOT).as_posix(), delta_report=UPSTREAM_DELTA.relative_to(ROOT).as_posix(), commits_in_range=39)
    casting_record = dict(attribution=attribution, suites=casting, wrapper='tools/migration/goal27a_casting_regression_run.py (unchanged)', policy='tools/migration/goal27a_casting_compat.py (unchanged)',
                          note='The two frozen isolated casting regressions (verify_goal10a.py, verify_goal5a_casting.py) run through the unchanged Goal27A wrapper in the final rerun, redirected into '
                               'build/migration/goal28a/final/castingsuites; both already stopped at javac on the Goal26D to Goal27D trees, so none of their assertions is reached. casting-attribution.json '
                               'pairs the javac errors of the Goal27D final run with the Goal28A run and attributes every new or moved error by file to a Goal28A change or to "not 28A"; it is evidence about javac '
                               'in the frozen stub worlds only.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(worldgen_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   uncommitted_start=uncommitted_start,
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, reconstruction=base['reconstruction'], push_commit_parent=chain[1], untrack_commit=chain[2], goal27_delivery_commit=chain[3],
                                      note=f'The start tree is HEAD 66a00353 (the mod rename, = origin/master) on c1f6f397, the migration/ untrack commit 66050453 and the Goal 27 delivery adaf265c, with a CLEAN worktree. '
                                           f'migration/ is Git-ignored: freeze_start.py hashed every tracked file ({tracked_count} baseline hashes) and every file under migration/ from disk ({len(base["migration_files"])} migration hashes) before the '
                                           f'first 28A write and copied {len(base["copied_scope"])} planned files (baseline-files). build/libs at the start is the post-rename JAR {start_jar_sha[:8]}, which already holds the three small fixes '
                                           f'(D3, D5, the mod rename), not the goal27d package {previous_sha[:8]}. The original moved to 4f5924e2b (39 commits past aee05a40f, 66 files); paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, line_endings=line_endings, content_rules=content_rules, gametest_edits=gametest_edits, start_copies_supplement=[],
                   ledger_edit=ledger_edit,
                   small_fixes=dict(small_fixes, note='D3 (JEI anvil row crash, AnvilRecipeHandler.java) and D5 (ContaminationUtil.java) were committed in adaf265c, the mod rename (gradle.properties mod_name / mod_authors -> '
                                                      'neoforge.mods.toml) in 66a00353; the handoff named 4aba849e for D3 and D5, which is not in this checkout\'s history (git log -1 for each file gives the commit shown). Their goal27d '
                                                      'package hashes are the goal27d baseline hashes advanced by the goal27d receipt\'s changed_files; the five JAR entries they changed against the goal27d package were recorded '
                                                      'by small-fix-jar-delta.json while build/libs was the start JAR and are attributed in jar_delta_owners. All three are packaged and regression-run with goal28a.',
                                    jar_entries=small_fix_entries, record=SMALL_FIX_DELTA.relative_to(ROOT).as_posix(), record_sha256=sha(SMALL_FIX_DELTA) if SMALL_FIX_DELTA.is_file() else None),
                   nether_end_worldgen=nether_end_worldgen, upstream=upstream, casting_attribution=casting_record,
                   language=dict(changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']), added=dict(en_us=en_delta['added'], zh_cn=zh_delta['added'], zh_cn_map=map_delta['added']),
                                 removed=dict(en_us=en_delta['removed'], zh_cn=zh_delta['removed'], zh_cn_map=map_delta['removed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds), jar_delta=language,
                                 start_sha256={p: base['files'][p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD, LANG_PROVIDER)},
                                 note='Goal28A adds 21 keys: the six nether ore names, item.hbmsntm.coal_infernal and the two hand drills (upstream: tile.ore_nether_*.name, item.coal_infernal.name, item.hand_drill*.name), the eleven '
                                      'hbmsntm.configuration.worldgen.* config keys and heater_oilburner.ignition (local); block.hbmsntm.heater_oilburner.desc and tile.heater_oilburner.desc are reworded; nothing is removed; the 106 '
                                      'deferred entries are unchanged. The handoff text said en +34: the files give +21 added, 0 removed, 2 changed (en_us.json, zh_cn.json and the mapping alike).'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith(CARRIED_REPINS)},
                   repinned_since_goal27d_start={p: dict(goal27d_start_pin_sha256=h, goal28a_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=dict(old=compare_old, new=compare),
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok'), old_machine_suites_through=OLD_MACHINE_SUITES, casting_suites_through=['goal27a_casting_regression_run.py verify_goal10a',
                                                                                                                                                                            'goal27a_casting_regression_run.py verify_goal5a_casting']),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_worldgen_tests=worldgen_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per NetherEndWorldgenGameTests test (names in new_worldgen_tests): what those '
                                      'tests assert about the decoded biome modifiers, the config gates and counts, the ore features, the blocks and their drops, outgassing, burning, the recipes, the hand drills, '
                                      'the fluid burner and the scraps name; the oil-burner block of RBMKCoreGameTests.rbmk_screwdriver_tooling is re-pinned to the 4f5924e2b rules; no client (the models, the textures, '
                                      'the GUI slider and the JEI screen are not drawn), no real player, no saved world, no world generation seen in a real world, no distribution sampling beyond the seeded test feature runs.'),
                   audits=audit_summaries, audit_comparison=audit_comparison, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['foundry_molds (the Goal27D-only domain key; Goal28A adds nether_end_worldgen)',
                                 'casting_regressions (the Goal27A key; Goal28A carries casting_attribution as Goal27B to Goal27D did: the wrapper and the two suites are unchanged, only their javac errors are attributed)',
                                 'foundry_casting / material_system / crucible_alloys (the Goal27A to Goal27C domain keys)',
                                 'appended_27c_records / planning_session_edit (no Goal 27 record is appended in this batch and no planning session edits a record)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun (the six old isolated suites through the goal26c wrapper and the two casting regressions through the unchanged goal27a wrapper, whose javac '
                            'errors are attributed by casting_attribution.py), compare against the review-aee05a40f10f snapshot (the 66-file range), the new review-4f5924e2b9e1 snapshot and its self-compare, '
                            'and one static review. No in-game client test was run: no nether or end world generation was seen in a real world and no vein distribution was sampled; the ore, hand drill and '
                            'infernal coal models and icons, the burner GUI slider, the JEI anvil screen and the Chinese UI are not seen on screen; no survival chain (finding, mining, smelting and processing the ores, '
                            'radon and carbon monoxide in a real world) was run; no dedicated server beyond GameTest; the Goal 28 acceptance checklist GOAL28A-ACCEPTANCE.md is written, not run.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False, default=str))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha and digest != start_jar_sha, 'build/libs JAR is the previous package or the start JAR'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal28a JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal27d package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
