"""Package Goal28B (the second batch of Goal 28: the overworld part of world generation: the graphitic schist stratum with the schist ores, the depth deposits with depth rock and the nether depth
neodymium, the iron / titanium / aluminium / copper ore clusters, alexandrite, the hematite / bauxite / malachite ore layers, 22 new blocks with drops, the schist smelting, centrifuge,
crystallizer and shredder rows, the gas shale fluid container, 17 worldgen config keys, a config-driven rarity placement and the OverworldWorldgenGameTests), cumulatively on the goal28a package,
without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal28b.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal28b/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal28b/gametest-final.log (the GameTest dedicated-server
log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a --check run also proves the receipt code; only the real mode
writes it.

The frozen start is build/migration/goal28b/baseline.json: NEO HEAD 66a00353 (the mod rename, = origin/master) with the UNCOMMITTED Goal28A delivery in the worktree (35 modified and 76 untracked
files at the freeze; packaged as goal28a, never committed). `files` (the tracked tree plus the untracked, non-ignored files) hashes the disk content of the worktree, so the 28A delivery is part of
the start; `migration_files` hashes the Git-ignored migration/ directory from disk. This packager merges them (one start-hash map) and finds changes under migration/ by walking the directory.
freeze_start.py copied 128 planned, modified and untracked files into baseline-files/. build/libs at the start is the goal28a package (109fe56d...9974). The original did not move (4f5924e2b,
the 28A observation point): there is no upstream range to classify, no new snapshot and one compare, against review-4f5924e2b9e1.json: original 0/0/0, the target set is this batch's own
compare-inventory paths plus any residual between the snapshot and the start (computed from the snapshot's raw hashes, expected empty: the 28A self-compare was 0/0/0).
Every change since the start is computed from the baseline hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified
production files are compared with their start bytes (baseline-files) and their +/- lines are reported. The JAR delta against the goal28a package is attributed per entry (goal28b or a
recompile difference); any entry without an owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys) are computed here from the
original and NEO sources and the GameTest log where they can be.

The receipts that hash records (goal21a..goal28a, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start (the acceptance checklists, GOAL21D.md, GOAL22C.md,
goal21d-static-review.md and the goal24a working notes, known from earlier batches, and migration/GOAL24B.md, whose one ledger sentence Goal28A replaced; the goal28a receipt itself matches
every hash it records); they are listed in the receipt as start drift and must still equal their Goal28B start hash; no receipt is rewritten and no other protected path may drift. Every
Goal 28A and earlier record, GOAL28C/D.md, GOAL28-THREAD-PROMPTS.md and SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL28.md is a shared record, GOAL28B.md the task book and
delivery record (hashed by the receipt).

It adds the overworld_worldgen facts (checked against the original and NEO source texts). The Goal28A-only receipt key nether_end_worldgen is dropped and the receipt says so; so are the keys
that belong to a moved original (upstream, the old compare, the small fixes, the ledger edit). The two old casting regressions run unchanged through the goal27a wrapper in the final rerun and
their javac errors are attributed by casting_attribution.py (casting-attribution.json)."""
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
from package_goal28a import OUT as GOAL28A_OUT, BASELINE as GOAL28A_BASELINE, protected_paths as goal28a_protected_paths

OUT = ROOT/'build/migration/goal28b'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
VERIFIER_REPORT_MD = OUT/'verifier-report.md'
REFERENCE_PREVIOUS = GOAL28A_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL28A_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal28a/hbmsntm-198A-goal28a.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal28b'
RELEASE_NAME = 'hbmsntm-198A-goal28b.jar'
OWNER = 'goal28b'
PREVIOUS_OWNER = 'goal28a'
# The original did not move this batch: SOURCE_HEAD is the 28A observation point and the head the goal28a receipt records.
SOURCE_HEAD = '4f5924e2b9e1e49cee61787674d2658acb3d559b'
START_PREFIX = '66a00353'
START_PARENT_PREFIX = 'c1f6f397'
UNTRACK_PREFIX = '66050453'
GOAL27_DELIVERY_PREFIX = 'adaf265c'
TASK_BOOK = 'migration/GOAL28B.md'
SNAPSHOT = 'migration/baselines/review-4f5924e2b9e1.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
SRC = 'src/main/java/'
J = SRC+'com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
TEXTURE_ROOT = RES+'assets/hbmsntm/textures/'
O_RES = RES+'assets/hbm/'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a', 'goal26b', 'goal26c', 'goal26d', 'goal27a', 'goal27b', 'goal27c', 'goal27d'}

# Production (owner goal28b): the NEW Java files (the schist stratum, depth deposit and ore layer features with their configurations, the config rarity placement, the depth block and the
# GameTest class) and the MODIFIED production sources (the handoff owner table); the optional ones and the edited older GameTests are listed separately.
NEW_JAVA = [J+p+'.java' for p in (
    'world/feature/SchistStratumFeature', 'world/feature/DepthDepositFeature', 'world/feature/DepthDepositConfiguration', 'world/feature/OreLayerFeature', 'world/feature/OreLayerConfiguration',
    'world/gen/ConfigRarityPlacement', 'blocks/generic/DepthBlock', 'gametest/OverworldWorldgenGameTests')]
(SCHIST_FEATURE, DEPTH_FEATURE, DEPTH_CONFIGURATION, LAYER_FEATURE, LAYER_CONFIGURATION, RARITY_PLACEMENT, DEPTH_BLOCK, WORLDGEN_TESTS) = NEW_JAVA
MODIFIED_JAVA = [J+p+'.java' for p in (
    'config/CommonConfig', 'world/gen/NtmWorldgenCodecs', 'world/gen/NtmConfiguredFeatures', 'world/gen/NtmPlacedFeatures', 'world/gen/NtmBiomeModifiers', 'world/feature/NtmFeatures', 'blocks/NtmBlocks',
    'blocks/generic/OutgasBlock', 'inventory/NtmCreativeTabs', 'inventory/FluidContainerRegistry', 'inventory/recipes/CentrifugeRecipes', 'inventory/recipes/CrystallizerRecipes',
    'inventory/recipes/ShredderRecipes', 'datagen/NtmBlockStateProvider', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmRecipeProvider', 'datagen/NtmLanguageProvider',
    'blockentity/machine/heater/HeaterOilburnerBlockEntity')]
(COMMON_CONFIG, WORLDGEN_CODECS, CONFIGURED_FEATURES, PLACED_FEATURES, BIOME_MODIFIERS_JAVA, NTM_FEATURES, NTM_BLOCKS, OUTGAS_BLOCK, CREATIVE_TABS, FLUID_CONTAINERS, CENTRIFUGE_RECIPES,
 CRYSTALLIZER_RECIPES, SHREDDER_RECIPES, STATE_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER, RECIPE_PROVIDER, LANG_PROVIDER, HEATER_OILBURNER_BE) = MODIFIED_JAVA
# The older GameTests whose row-count expectations this batch changes by design: the default acidizer (crystallizer) table grows 53 -> 60 rows and the centrifuge table 80 -> 83. Only those count
# checks (and their citation comments) may change; the @GameTest methods and annotations are the start's. Any other older GameTest the verifier edits is listed in verifier-report.md.
EDITED_GAMETESTS = [J+'gametest/'+n+'.java' for n in ('SmokeGameTests', 'RadiationControlGameTests', 'NetherEndWorldgenGameTests')]
(SMOKE_TESTS, RADIATION_TESTS, NETHER_END_TESTS) = EDITED_GAMETESTS
EDITED_EXTRA = []  # older GameTests that verifier-report.md names beyond EDITED_GAMETESTS (filled in main())
ROW_COUNT_CHECK = re.compile(r'check\([\w.()]*?(?:size\(\)|rows|centrifuge|crystallizer)\s*==\s*(\d+),')
ROW_MAP = {53: 60, 80: 83}
# Optional (changed only when the batch needed it; reported): an additive GameTest helper.
OPTIONAL_JAVA = [J+p+'.java' for p in ('gametest/SmokeTestSupport',)]
OLDER_GAMETEST_DIR = J+'gametest/'
# Must stay byte-identical to the start (the handoff list), plus every other GameTest class and every handler/jei class: see main().
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'world/feature/OilBubbleFeature', 'world/feature/ColtanDepositFeature', 'world/feature/BedrockOilDepositFeature', 'world/feature/LandmineFeature', 'world/feature/CrashedBombFeature',
    'world/feature/BlueprintChestFeature', 'world/feature/SmolderingNetherrackFeature', 'world/gen/ConfigCountPlacement', 'world/gen/ConfigGatedAddFeaturesBiomeModifier', 'items/tools/ToolAbilityItem',
    'items/NtmItems', 'blocks/machine/FoundryOutletBlock', 'blockentity/machine/FoundryOutletBlockEntity', 'items/machine/MoldItem', 'inventory/recipes/CrucibleRecipes', 'util/ContaminationUtil')] + [
    SRC+'api/hbm/item/IDepthRockTool.java']
UNCHANGED_DIRS = (J+'inventory/material/', J+'blockentity/machine/Foundry', RES+'data/hbmsntm/worldgen/', RES+'data/hbmsntm/neoforge/biome_modifier/')
# Older tools that must equal their start bytes (handoff list); every file of the two frozen casting regression folders is added in main().
OLD_TOOLS_FROZEN = ['tools/migration/'+p for p in ('package_goal28a.py', 'verify_goal28a_worldgen.py', 'package_goal27d.py', 'verify_goal27d_molds.py', 'package_goal27c.py', 'verify_goal27c_foundry.py', 'package_goal27b.py',
                                                    'verify_goal27b_crucible_alloys.py', 'package_goal27a.py', 'verify_goal27a_material_system.py', 'goal27a_casting_regression_run.py', 'goal27a_casting_compat.py',
                                                    'goal27a_scrap_textures.py', 'goal27a_effect_icons.py', 'goal26c_oldsuite_run.py', 'goal26c_oldsuite_compat.py', 'verify_goal10a.py', 'verify_goal10a_resources.py',
                                                    'verify_goal5a_casting.py', 'verify_goal5a_casting_resources.py', 'goal10a_scrap_textures.py', 'goal10a_mutation_check.py')]
FROZEN_TOOL_DIRS = ('tools/migration/goal10a_regression/', 'tools/migration/goal5a_casting_regression/')
NEW_TOOLS = ['tools/migration/verify_goal28b_worldgen.py', 'tools/migration/package_goal28b.py']
TOOLS = NEW_TOOLS
# The 22 new blocks (migration/goal28b-resource-ownership.json lists their 14 textures: the schist stone, ores and gas shale reuse textures the start already holds).
CLUSTER_NAMES = ('cluster_aluminium', 'cluster_copper', 'cluster_iron', 'cluster_titanium', 'cluster_depth_iron', 'cluster_depth_titanium', 'cluster_depth_tungsten')
DEPTH_ORE_NAMES = ('ore_depth_borax', 'ore_depth_cinnabar', 'ore_depth_nether_neodymium', 'ore_depth_zirconium')
GNEISS_NAMES = ('ore_gneiss_asbestos', 'ore_gneiss_copper', 'ore_gneiss_gas', 'ore_gneiss_gold', 'ore_gneiss_iron', 'ore_gneiss_lithium', 'ore_gneiss_rare')
STONE_NAMES = ('stone_depth', 'stone_depth_nether', 'stone_gneiss')
BLOCK_NAMES = CLUSTER_NAMES + ('ore_alexandrite',) + DEPTH_ORE_NAMES + GNEISS_NAMES + STONE_NAMES
ITEM_MODEL_NAMES = BLOCK_NAMES
# The block texture files this batch imports (14): the cluster, depth and alexandrite blocks; the original calls cinnabar "cinnebar".
TEXTURE_NAMES = ('cluster_aluminium', 'cluster_copper', 'cluster_depth_iron', 'cluster_depth_titanium', 'cluster_depth_tungsten', 'cluster_iron', 'cluster_titanium', 'ore_alexandrite', 'ore_depth_borax',
                 'ore_depth_cinnabar', 'ore_depth_nether_neodymium', 'ore_depth_zirconium', 'stone_depth', 'stone_depth_nether')
TEXTURE_PATTERN = re.compile(re.escape(TEXTURE_ROOT)+r'block/(?:'+'|'.join(TEXTURE_NAMES)+r')\.png')
REQUIRED_TEXTURES = [TEXTURE_ROOT+'block/'+n+'.png' for n in TEXTURE_NAMES]
RESOURCE_OWNERSHIP = 'migration/goal28b-resource-ownership.json'
# Generated by runData: 24 configured and 25 placed features (the nether neodymium feature is placed twice), 7 biome modifiers, 22 blockstates, block models, item models and loot tables, 5 smelting
# recipes with their advancements; en_us.json, the pickaxe tag and the malachite loot table change; the stamp.
CONFIGURED_NAMES = ('bauxite_layer', 'cluster_aluminium', 'cluster_copper', 'cluster_iron', 'cluster_titanium', 'depth_cluster_iron', 'depth_cluster_titanium', 'depth_cluster_tungsten', 'depth_ore_borax',
                    'depth_ore_cinnabar', 'depth_ore_nether_neodymium', 'depth_ore_zirconium', 'hematite_layer', 'malachite_layer', 'ore_alexandrite', 'ore_gneiss_asbestos', 'ore_gneiss_copper',
                    'ore_gneiss_gas', 'ore_gneiss_gold', 'ore_gneiss_iron', 'ore_gneiss_lithium', 'ore_gneiss_rare', 'ore_gneiss_uranium', 'schist_stratum')
PLACED_NAMES = tuple(n+'_placed' if n != 'depth_ore_nether_neodymium' else None for n in CONFIGURED_NAMES)
PLACED_NAMES = tuple(n for n in PLACED_NAMES if n) + ('depth_ore_nether_neodymium_high_placed', 'depth_ore_nether_neodymium_low_placed')
BIOME_MODIFIER_NAMES = ('add_alexandrite_ore', 'add_bauxite_layer', 'add_hematite_layer', 'add_malachite_layer', 'add_nether_depth_deposits', 'add_overworld_ores', 'add_schist_stratum')
RECIPE_NAMES = ('copper_ingot_from_smelting_ore_gneiss_copper', 'gold_ingot_from_smelting_ore_gneiss_gold', 'ingot_schrabidium_from_smelting_ore_gneiss_schrabidium',
                'iron_ingot_from_smelting_ore_gneiss_iron', 'lithium_from_smelting_ore_gneiss_lithium')
GENERATED_ADDED = re.compile(re.escape(GENERATED_ROOT)+r'(?:assets/hbmsntm/blockstates/(?:'+'|'.join(BLOCK_NAMES)+r')\.json|assets/hbmsntm/models/block/(?:'+'|'.join(BLOCK_NAMES)+r')\.json|'
                             r'assets/hbmsntm/models/item/(?:'+'|'.join(ITEM_MODEL_NAMES)+r')\.json|data/hbmsntm/loot_table/blocks/(?:'+'|'.join(BLOCK_NAMES)+r')\.json|'
                             r'data/hbmsntm/recipe/[a-z0-9_]+\.json|data/hbmsntm/advancement/recipes/[a-z]+/[a-z0-9_]+\.json|'
                             r'data/hbmsntm/worldgen/configured_feature/(?:'+'|'.join(CONFIGURED_NAMES)+r')\.json|data/hbmsntm/worldgen/placed_feature/(?:'+'|'.join(PLACED_NAMES)+r')\.json|'
                             r'data/hbmsntm/neoforge/biome_modifier/(?:'+'|'.join(BIOME_MODIFIER_NAMES)+r')\.json)')
GENERATED_COUNTS = dict(blockstates=22, block_models=22, item_models=22, loot_tables=22, recipes=5, advancements=5, configured_features=24, placed_features=25, biome_modifiers=7)
PICKAXE_TAG = GENERATED_ROOT+'data/minecraft/tags/block/mineable/pickaxe.json'
MALACHITE_LOOT = GENERATED_ROOT+'data/hbmsntm/loot_table/blocks/resource_malachite.json'
REQUIRED_GENERATED = sorted([GENERATED_ROOT+f'assets/hbmsntm/blockstates/{n}.json' for n in BLOCK_NAMES] + [GENERATED_ROOT+f'assets/hbmsntm/models/block/{n}.json' for n in BLOCK_NAMES]
                            + [GENERATED_ROOT+f'assets/hbmsntm/models/item/{n}.json' for n in ITEM_MODEL_NAMES] + [GENERATED_ROOT+f'data/hbmsntm/loot_table/blocks/{n}.json' for n in BLOCK_NAMES]
                            + [GENERATED_ROOT+f'data/hbmsntm/recipe/{n}.json' for n in RECIPE_NAMES]
                            + [GENERATED_ROOT+f'data/hbmsntm/worldgen/configured_feature/{n}.json' for n in CONFIGURED_NAMES]
                            + [GENERATED_ROOT+f'data/hbmsntm/worldgen/placed_feature/{n}.json' for n in PLACED_NAMES]
                            + [GENERATED_ROOT+f'data/hbmsntm/neoforge/biome_modifier/{n}.json' for n in BIOME_MODIFIER_NAMES])
GENERATED_TAGS = re.compile(re.escape(GENERATED_ROOT)+r'data/[a-z_]+/tags/.*\.json')  # the tag files that gained the blocks (pickaxe.json is required, others allowed)
GENERATED_MODIFIED = [STAMP, EN, PICKAXE_TAG, MALACHITE_LOOT]
# Language: 40 new keys (the 22 block names, trait.tile.depth and 17 worldgen config keys); nothing changed or removed.
ORIGINAL_BLOCK_KEY = {n: n.replace('cinnabar', 'cinnebar') for n in BLOCK_NAMES}
UPSTREAM_KEYS = {'block.hbmsntm.'+n: 'tile.'+ORIGINAL_BLOCK_KEY[n]+'.name' for n in BLOCK_NAMES}
UPSTREAM_KEYS['trait.tile.depth'] = 'trait.tile.depth'
CONFIG_KEYS = ('alexandriteSpawnRate', 'aluminiumClusterSpawnRate', 'copperClusterSpawnRate', 'enableBauxite', 'enableHematite', 'enableMalachite', 'gneissAsbestosSpawnRate', 'gneissCopperSpawnRate',
               'gneissGasShaleSpawnRate', 'gneissGoldSpawnRate', 'gneissIronSpawnRate', 'gneissLithiumSpawnRate', 'gneissRareEarthSpawnRate', 'gneissUraniumSpawnRate', 'ironClusterSpawnRate',
               'overworldOres', 'titaniumClusterSpawnRate')
LOCAL_KEYS = ['hbmsntm.configuration.worldgen.'+k for k in CONFIG_KEYS]
KEYS = sorted(list(UPSTREAM_KEYS) + LOCAL_KEYS)
REMOVED_KEYS = []
LANG_CHANGED = []
EN_CHANGED = ZH_CHANGED = LANG_CHANGED
LANG_SOURCE = UPSTREAM_KEYS
UPSTREAM_ADDED = 23
LOCAL_ADDED = 17
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal28b-* or GOAL28B-* record is hashed as well.
REPORTS = ['migration/GOAL28B.md', 'migration/GOAL28B-ACCEPTANCE.md', RESOURCE_OWNERSHIP, 'migration/goal28b-static-review.md', 'migration/goal28b-materials-review.json',
           'migration/goal28b-localization-review.json']
LEDGER = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal28b-[^/]+\.(json|md)|GOAL28B-[^/]+\.md)')
GOAL28_RECORD = 'migration/GOAL28.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md', GOAL28_RECORD, LOCALIZATION_RECORD]
# Shared records the batch may leave untouched ("if touched" in the handoff).
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
# The records of the other batches and the files no batch of this kind touches: no change is expected.
PLANNING_FROZEN = ['migration/SURVIVAL-PLAYABILITY.md', 'migration/GOAL28-THREAD-PROMPTS.md', 'migration/GOAL28C.md', 'migration/GOAL28D.md']
# Every Goal 28A and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 27, GOAL28A*, goal28a-*): GOAL24B.md is a start-drift record pinned at its start hash like the others.
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-7]|28A)(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-7]|28a)(?!\d)[a-z]?-[^/]+)')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = (NEW_JAVA + MODIFIED_JAVA + EDITED_GAMETESTS + REQUIRED_TEXTURES + REQUIRED_GENERATED + GENERATED_MODIFIED + [ZH_INPUT] + TOOLS + REPORTS
                    + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS])
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-28b] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the
# sessions of the batch. Every top-level handoff-*.md, *-report.md, builder-*.log and verifier-*.log of OUT is indexed as well.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_head.txt', 'handoff-builder.md', 'handoff-verifier.md',
                  'handoff-packaging.md', 'handoff-reviewer.md', 'chain.sh', 'gw.sh', 'add_zh.py', 'add_zh.log', 'write_ownership.py', 'make_diff.py', 'production-builder.diff', 'make_production_diff.py')
# Review files under OUT; each must exist and is indexed by the receipt. --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'casting_attribution.py', 'packaging-progress.md', 'packaging-report.md', 'verifier-report.md',
                   'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier/scope-start.txt', 'verifier/scope-end.txt', 'verify-final.out', 'compare.log', 'localization-final.log',
                   'resources-audit-final.log', 'packaged-resources-final.log')
CASTING_ATTRIBUTION = 'casting-attribution.json'
CASTING_DIR = OUT/'final/castingsuites'
CASTING_SUITES = ('verify_goal10a', 'verify_goal5a_casting')
FAIL_SET_DIFF = 'final/fail-set-diff.json'
COMPARE_EXITS = ('compare',)
GAMETEST_LOG = 'build/migration/goal28b/gametest-final.log'
NEW_SUITE = 'verify_goal28b_worldgen.py --gametest-log build/migration/goal28b/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
OLD_SUITE_28A = 'verify_goal28a_worldgen.py --gametest-log build/migration/goal28a/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# features.json: no new group; world-generation, materials, crystallization, centrifuge, shredder and fluid-container-transfer may change notes / target_paths / target_watch (handoff);
# every group keeps reviewed_source_commit (the original did not move) and its status.
NEW_FEATURE = 'world-generation'
NOTES_MAY_CHANGE = {'materials', 'centrifuge', 'crystallization', 'shredder', 'fluid-container-transfer', NEW_FEATURE}
RADIATION_NOTE = ('Goal28B: schist uranium ore releases radon and schist asbestos ore releases asbestos when mined or randomly ticked; mine them with a gas mask in a disposable world. ')
MELTDOWN_NOTE = 'Goal28B: no new meltdown path. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_WORLDGEN = ORIGINAL+'lib/HbmWorldGen.java'
O_TOOLBOX = ORIGINAL+'world/generator/DungeonToolbox.java'
O_MAINREGISTRY = ORIGINAL+'main/MainRegistry.java'
O_WORLDCONFIG = ORIGINAL+'config/WorldConfig.java'
O_SCHIST = ORIGINAL+'world/feature/SchistStratum.java'
O_ORELAYER = ORIGINAL+'world/feature/OreLayer3D.java'
O_DEPTHDEPOSIT = ORIGINAL+'world/feature/DepthDeposit.java'
O_MODBLOCKS = ORIGINAL+'blocks/ModBlocks.java'
O_BLOCKDEPTH = ORIGINAL+'blocks/generic/BlockDepth.java'
O_BLOCKDEPTHORE = ORIGINAL+'blocks/generic/BlockDepthOre.java'
O_BLOCKCLUSTER = ORIGINAL+'blocks/generic/BlockCluster.java'
O_BLOCKORE = ORIGINAL+'blocks/generic/BlockOre.java'
O_RESOURCESTONE = ORIGINAL+'blocks/generic/BlockResourceStone.java'
O_OUTGAS = ORIGINAL+'blocks/generic/BlockOutgas.java'
O_SMELTING = ORIGINAL+'crafting/SmeltingRecipes.java'
O_CENTRIFUGE = ORIGINAL+'inventory/recipes/CentrifugeRecipes.java'
O_SHREDDER = ORIGINAL+'inventory/recipes/ShredderRecipes.java'
O_CRYSTALLIZER = ORIGINAL+'inventory/recipes/CrystallizerRecipes.java'
O_FLUIDCONTAINERS = ORIGINAL+'inventory/FluidContainerRegistry.java'
O_OREDICT = ORIGINAL+'inventory/OreDictManager.java'
O_LANG_EN = O_RES+'lang/en_US.lang'
O_LANG_ZH = O_RES+'lang/zh_CN.lang'
O_SOURCES = [O_WORLDGEN, O_TOOLBOX, O_MAINREGISTRY, O_WORLDCONFIG, O_SCHIST, O_ORELAYER, O_DEPTHDEPOSIT, O_MODBLOCKS, O_BLOCKDEPTH, O_BLOCKDEPTHORE, O_BLOCKCLUSTER, O_BLOCKORE, O_RESOURCESTONE, O_OUTGAS,
             O_SMELTING, O_CENTRIFUGE, O_SHREDDER, O_CRYSTALLIZER, O_FLUIDCONTAINERS, O_OREDICT, O_LANG_EN, O_LANG_ZH]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'alexandrite_roll': (O_WORLDGEN, 'WorldConfig.alexandriteSpawn > 0 && rand.nextInt(WorldConfig.alexandriteSpawn) == 0'), 'alexandrite_vein': (O_WORLDGEN, 'ModBlocks.ore_alexandrite)'),
    'overworld_switch': (O_WORLDGEN, 'if(WorldConfig.overworldOre)'), 'depth_iron': (O_WORLDGEN, 'ModBlocks.cluster_depth_iron, rand, 24'),
    'depth_cinnabar': (O_WORLDGEN, 'ModBlocks.ore_depth_cinnebar, rand, 16'), 'depth_nether_low': (O_WORLDGEN, 'generateConditionNether(world, i, 0, 3, j, 7'),
    'depth_nether_high': (O_WORLDGEN, 'generateConditionNether(world, i, 125, 3, j, 7'), 'gneiss_iron_vein': (O_WORLDGEN, 'ModBlocks.ore_gneiss_iron, ModBlocks.stone_gneiss'),
    'gneiss_uranium_vein': (O_WORLDGEN, 'WorldConfig.uraniumSpawn * 3, 6, 30, 10, ModBlocks.ore_gneiss_uranium'), 'gneiss_gas_vein': (O_WORLDGEN, 'WorldConfig.gassshaleSpawn * 3, 10, 30, 10'),
    'cluster_iron_vein': (O_WORLDGEN, 'WorldConfig.ironClusterSpawn, 6, 15, 45'), 'cluster_copper_vein': (O_WORLDGEN, 'WorldConfig.copperClusterSpawn, 6, 15, 20'),
    'vein_height': (O_TOOLBOX, 'int y = minHeight + (variance > 0'), 'depth_generate': (O_DEPTHDEPOSIT, 'if(j < 1 || j > 126)'), 'depth_bedrock': (O_DEPTHDEPOSIT, 'yes you\'ve heard right, bedrock'),
    'schist_registration': (O_MAINREGISTRY, 'MinecraftForge.EVENT_BUS.register(new SchistStratum())'), 'layer_hematite': (O_MAINREGISTRY, 'EnumStoneType.HEMATITE.ordinal()).setScaleH(0.04D)'),
    'layer_bauxite': (O_MAINREGISTRY, 'EnumStoneType.BAUXITE.ordinal()).setScaleH(0.03D)'), 'layer_malachite': (O_MAINREGISTRY, 'EnumStoneType.MALACHITE.ordinal()).setScaleH(0.1D)'),
    'schist_noise': (O_SCHIST, 'new NoiseGeneratorPerlin(new Random(event.world.getSeed()), 4)'), 'schist_scale': (O_SCHIST, 'double scale = 0.01D'), 'schist_threshold': (O_SCHIST, 'int threshold = 5'),
    'schist_range': (O_SCHIST, 'int range = (int)((n - threshold) * 3)'), 'schist_fold': (O_SCHIST, 'range = 8 - range'), 'schist_height': (O_SCHIST, 'for(int y = 30 - range; y <= 30 + range; y++)'),
    'layer_third_noise': (O_ORELAYER, 'double nz = cacheX[ox][y]'), 'layer_seed_x': (O_ORELAYER, 'world.getSeed() + 101 + id'), 'layer_height': (O_ORELAYER, 'for(int y = 64; y > 5; y--)'),
    'cfg_overworld': (O_WORLDCONFIG, '2.D00_overworldOres'), 'cfg_iron_cluster': (O_WORLDCONFIG, '2.C00_ironClusterSpawn'), 'cfg_alexandrite': (O_WORLDCONFIG, '2.20_alexandriteSpawnRate'),
    'cfg_hematite': (O_WORLDCONFIG, '2.L00_enableHematite'), 'block_stone_depth': (O_MODBLOCKS, 'stone_depth = new BlockDepth()'), 'block_gneiss_uranium': (O_MODBLOCKS, 'ore_gneiss_uranium = new BlockOutgas'),
    'block_cluster_iron': (O_MODBLOCKS, 'cluster_iron = new BlockCluster'), 'depth_tool': (O_BLOCKDEPTH, '(float) (1D / 50D)'), 'depth_drop_cinnabar': (O_BLOCKDEPTHORE, 'return 2 + rand.nextInt(3)'),
    'depth_drop_alexandrite': (O_BLOCKDEPTHORE, 'quantity > 2) quantity = 2'), 'cluster_drop': (O_BLOCKCLUSTER, 'return ModItems.crystal_iron'), 'malachite_drop': (O_RESOURCESTONE, 'EnumChunkType.MALACHITE, 3 + fortune'),
    'asbestos_drop': (O_BLOCKORE, 'this == ModBlocks.ore_asbestos || this == ModBlocks.ore_gneiss_asbestos'), 'rare_drop': (O_BLOCKORE, 'this == ModBlocks.ore_rare || this == ModBlocks.ore_gneiss_rare'),
    'outgas_gneiss': (O_OUTGAS, 'this == ModBlocks.ore_gneiss_uranium'), 'outgas_asbestos': (O_OUTGAS, 'this == ModBlocks.ore_asbestos || this == ModBlocks.ore_gneiss_asbestos'),
    'smelt_gneiss_iron': (O_SMELTING, 'ModBlocks.ore_gneiss_iron'), 'smelt_gneiss_lithium': (O_SMELTING, 'ModBlocks.ore_gneiss_lithium'), 'smelt_gneiss_schrabidium': (O_SMELTING, 'ModBlocks.ore_gneiss_schrabidium'),
    'shred_gneiss': (O_SHREDDER, 'ModBlocks.stone_gneiss, new ItemStack(ModItems.powder_lithium_tiny'), 'cryst_gneiss': (O_CRYSTALLIZER, 'ComparableStack(ModBlocks.stone_gneiss)'),
    'gas_shale_container': (O_FLUIDCONTAINERS, 'ModBlocks.ore_gneiss_gas'),
}
# The overworld vein table: block -> NEO config key. Every other value (count expression, size, height, target) is parsed from the original; the count expression is evaluated with the
# defaults the original passes to its config loader (WorldConfig.loadFromConfig), not the field initialisers (uraniumSpawn 6 and asbestosSpawn 4 are overwritten with 7 and 2).
VEIN_KEYS = {'ore_gneiss_iron': 'gneissIronSpawnRate', 'ore_gneiss_gold': 'gneissGoldSpawnRate', 'ore_gneiss_uranium': 'gneissUraniumSpawnRate', 'ore_gneiss_copper': 'gneissCopperSpawnRate',
             'ore_gneiss_asbestos': 'gneissAsbestosSpawnRate', 'ore_gneiss_lithium': 'gneissLithiumSpawnRate', 'ore_gneiss_rare': 'gneissRareEarthSpawnRate', 'ore_gneiss_gas': 'gneissGasShaleSpawnRate',
             'cluster_iron': 'ironClusterSpawnRate', 'cluster_titanium': 'titaniumClusterSpawnRate', 'cluster_aluminium': 'aluminiumClusterSpawnRate', 'cluster_copper': 'copperClusterSpawnRate'}
# The depth deposit table: original block -> (NEO configured feature, NEO placed feature(s)).
DEPTH_FEATURES = {'cluster_depth_iron': ('depth_cluster_iron', ['depth_cluster_iron_placed']), 'cluster_depth_titanium': ('depth_cluster_titanium', ['depth_cluster_titanium_placed']),
                  'cluster_depth_tungsten': ('depth_cluster_tungsten', ['depth_cluster_tungsten_placed']), 'ore_depth_cinnebar': ('depth_ore_cinnabar', ['depth_ore_cinnabar_placed']),
                  'ore_depth_zirconium': ('depth_ore_zirconium', ['depth_ore_zirconium_placed']), 'ore_depth_borax': ('depth_ore_borax', ['depth_ore_borax_placed']),
                  'ore_depth_nether_neodymium': ('depth_ore_nether_neodymium', ['depth_ore_nether_neodymium_low_placed', 'depth_ore_nether_neodymium_high_placed'])}
WORLDGEN_SWITCH_KEYS = ('overworldOres', 'enableHematite', 'enableMalachite', 'enableBauxite')
WORLDGEN_COUNT_KEYS = tuple(sorted(VEIN_KEYS.values()))
# Expected figures of the handoff and the task book (every value is also computed from the sources). The handoff text said 25 configured / 26 placed features; the tree holds 24 / 25. depth_deposits counts the original rows: six overworld deposits and two nether neodymium rows (HbmWorldGen.java:103-108, 523-524).
EXPECTED = dict(configured_features=24, placed_features=25, biome_modifiers=7, blocks=22, imported_assets=14, config_values=17, language_added=40, language_changed=0, deferred_entries=106,
                crystallizer_rows=60, centrifuge_rows=83, veins=13, depth_deposits=8, layers=3, smelting_rows=5, depth_destroy_progress=1/50)
KNOWN_DIFFERENCES = {
    'stratum_not_gated': 'the schist stratum is NOT gated by overworldOres: MainRegistry.java:597 registers it unconditionally; it runs in step local_modifications (a plain neoforge:add_features modifier); the task book grouped it with the overworld ores',
    'alexandrite_rarity': 'alexandrite is NOT gated by overworldOres (HbmWorldGen.java:98-99 sits before the `if(WorldConfig.overworldOre)` block) and uses the new hbmsntm:config_rarity placement with alexandriteSpawnRate (every nth chunk, 0 = off)',
    'layers_gated_each': 'each ore layer is gated by its own switch (enableHematite / enableMalachite / enableBauxite, MainRegistry.java:602-604) through a config_gated_add_features modifier; the layer index (0 hematite, 1 bauxite, 2 malachite) is fixed, the original numbers the layers by creation order',
    'overworld_modifier': 'add_overworld_ores (gated by overworldOres) holds the six depth deposits, the eight schist ores and the four clusters in the original order (HbmWorldGen.java:98-139); the nether neodymium deposits (HbmWorldGen.java:523-524) are a new modifier add_nether_depth_deposits gated by netherOres',
    'schist_counts': 'the eight schist vein counts are separate keys holding the effective original counts: iron 25, gold 10 (constants, HbmWorldGen.java:110-111), uranium 7 x 3, copper 12 x 3, asbestos 2 x 3, gas shale 5 x 3, lithium 6, rare earth 6 (the config loader defaults, WorldConfig.java:127-146; the field initialisers uraniumSpawn = 6 and asbestosSpawn = 4 are overwritten)',
    'noise_equivalence': 'n = 15 * PerlinSimplexNoise(LegacyRandomSource(seed), octaves -3..0).getValue(x, z) stands for the 1.7.10 NoiseGeneratorPerlin(new Random(seed), 4).func_151601_a(x, z) (sum divided by 1 + 2 + 4 + 8); the GameTest checks the equivalence numerically',
    'layer_third_noise': 'the third noise value of an ore layer reproduces the original\'s cacheX[ox][y] read (OreLayer3D.java:111), not its noiseZ cache (built, never read); seeds seed + 101 + layer and seed + 102 + layer; y 64 down to 6; only #minecraft:stone_ore_replaceables is replaced',
    'depth_floor': 'depth deposits are placed relative to the bottom of the world (above_bottom 0..2, y >= bottom + 1 and <= bottom + 126), so the overworld keeps its y = -64 floor; the original replaces stone and bedrock at y 0..2; the nether deposits sit at y 0..2 and 125..127',
    'depth_rarity': 'the depth deposits use minecraft:rarity_filter with the original chances (24, 32, 32, 16, 16, 16, nether 16 and 16), not a config key (HbmWorldGen.java:98-99, 523-524 have none)',
    'depth_drops': 'the depth ores (cluster_depth_*, ore_depth_*, ore_alexandrite) drop through depthOreDrop: count, ore fortune bonus, optional cap, wrapped in explosion decay (the original drops every item as its own stack, so an explosion keeps each with chance 1/radius); silk touch is unchanged',
    'heater_slot': 'the oil burner heater accepts a full container of its tank fluid in slot 0 (gas shale has no empty container; original ContainerOilburner.java:22 takes any item)',
    'depth_rock': 'depth rock and all depth ores (DepthBlock): destroy progress exactly 1/50 per tick when the main-hand item is an IDepthRockTool whose canBreakRock is true, otherwise unbreakable (destroy time -1, explosion resistance 10), BlockDepth.java:25-34',
    'malachite_drop': 'malachite now drops chunk_malachite 3..4 with the ore bonus for fortune (an approximation of the original 3 + fortune + rand(fortune + 2), BlockResourceStone.java:33-41); alexandrite drops one gem with the ore bonus capped at 2; clusters drop one crystal without a fortune bonus',
    'schist_smelting': 'schist copper smelts to the vanilla copper ingot (Goal 28 decision 10); the schist smelting rows use NEO\'s unified 0.7F experience instead of the original 5.0F / 10F / 256.0F (SmeltingRecipes.java:54-60)',
    'acidizer_centrifuge_rows': 'acidizer 53 -> 60 rows (graphitic schist -> lithium powder, schist iron / gold / copper / rare earth / lithium ore rows, depth cinnabar ore -> cinnabar crystal with peroxide, CrystallizerRecipes.java:87, OreDictManager.java:437), centrifuge 80 -> 83 rows (schist iron, gold, copper as the vanilla ore rows; no rare earth row because NEO\'s ore_rare has none); shredder: graphitic schist -> 1 tiny lithium powder, schist lithium via the auto rule, depth borax / zirconium / nether neodymium ore -> 2 of their dust (OreDictManager.java:438,473-474, ShredderRecipes.java:66); no schist rare earth row (the original names only ore_rare, ShredderRecipes.java:193); no row for gas shale or alexandrite',
    'gas_shale_container': 'the gas shale block is a fluid container with petroleum 250 (50 with enable528) and an empty container of ItemStack.EMPTY (FluidContainerRegistry.java:45)',
}

# 27A / 27B / 27C / 27D / 28A ones the receipt carries forward under a new heading.
CARRIED_REPINS = 'repinned_since_'


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal28b release directory: '+rel

def original_blob(path):
    """Bytes of a file in the original repository at the 28B commit (independent of its worktree)."""
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
    """The Goal28B start hash of a frozen path: the merged baseline hashes, or for a build/ record (Git-ignored, so the baseline does not list it) the hash the goal28a receipt
    records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal28a packager protected (built there from the Goal21A..Goal27D starts and receipts and the goal28a start), plus every path the goal28a receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (goal21a..goal27d) and every release file of the frozen start (the goal28a package included).
    The records that already drifted (the older drift: the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes, GOAL24B.md with the one
    ledger sentence Goal28A replaced; the newer drift: the GOAL25D / GOAL26D / GOAL27D acceptance checklists) are pinned at their Goal28B start hash instead of any receipt hash or any earlier
    start hash. One path never carries two hashes. Returns (protected, repinned): repinned maps a record to the pin the goal28a packager set (its Goal28A start hash) for the records
    whose pin changed between the starts."""
    goal28a_start = dict(read(GOAL28A_BASELINE))
    goal28a_start['files'] = merged_files(goal28a_start)
    out = dict(goal28a_protected_paths(goal28a_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal28a receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal28a_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    return out, repinned


def start_drift_report(base, repinned, goal28a_start):
    """{path: {receipts, start_sha256, goal28a_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal28a receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal28a receipt') or receipts.get('goal27d receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif p == 'migration/GOAL24B.md':
            explanation = ('Goal28A replaced one ledger sentence of this record (plutonium powder and polonium-210 are reachable with enablePlutoniumNetherOre, default off; the goal28a receipt reported it as '
                           'ledger_edit but does not hash the file); the goal24b receipt hash is older than the start hash. Frozen at the Goal28B start hash; this batch must not change it and the goal24b receipt is not rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21..26 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal27d and goal28a '
                           'receipts do not hash it. Frozen at the Goal28B start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the newest receipt that hashes it (the in-game acceptance results of Goal 25, 26 and 27 were recorded in the checklists once the packages existed); that '
                           'receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and no receipt is rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal28a_start_sha256=goal28a_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal28a_start_pin_sha256'] = repinned[p]
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
    return (f'Goal28B (the second batch of Goal 28, world generation and resources): the overworld ore generation of the original at 4f5924e2b (unchanged since Goal28A): the graphitic schist stratum with the schist uranium, '
            f'iron, gold, copper, asbestos, lithium, rare earth ores and gas shale; the depth deposits (iron / titanium / tungsten depth clusters, depth cinnabar, zirconium, borax) and the nether depth neodymium with '
            f'depth rock; the iron, titanium, aluminium and copper ore clusters; alexandrite; the hematite, bauxite and malachite ore layers; 22 new blocks with drops, tags and loot tables; 17 worldgen config keys '
            f'and a config-driven rarity placement; the schist smelting, centrifuge, acidizer and shredder rows and the gas shale fluid container; {tests} OverworldWorldgenGameTests ({total_tests} GameTests in total). '
            f'Gameplay impact: the overworld now generates a graphitic schist band around y 26-34 with schist iron, gold, uranium, copper, asbestos, lithium, rare earth ores and gas shale; depth deposits at the world '
            f'bottom (iron/titanium/tungsten depth clusters, depth cinnabar, zirconium, borax) and nether depth neodymium near the nether floor and roof, embedded in depth rock that only depth-rock tools (or '
            f'explosions) break; iron, titanium, aluminium and copper ore clusters; alexandrite ore; hematite, bauxite and malachite ore layers (malachite now drops malachite chunks); lithium (cubes, powder, '
            f'crystals), zirconium, borax, neodymium, alexandrite, hematite, malachite and bauxite are obtainable in survival; schist uranium and asbestos ore release radon and asbestos; gas shale holds 250 mB petroleum and can be burned in the oil burner heater.')


def group(p, imported):
    if p in NEW_JAVA: return 'production-new'
    if p in EDITED_GAMETESTS or p in EDITED_EXTRA: return 'gametest-edit'
    if p in MODIFIED_JAVA or p in OPTIONAL_JAVA: return 'production'
    if p in imported: return 'production-resource-imported'
    if p == ZH_INPUT: return 'language'
    if p in GENERATED_MODIFIED or GENERATED_ADDED.fullmatch(p) or GENERATED_TAGS.fullmatch(p): return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p) or p == TASK_BOOK: return 'reports'
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records'
    return None


def owner_of(p):
    return OWNER




def original_int_default(text, field):
    m = re.search(r'public static int '+field+r' = (-?\d+);', text)
    return int(m.group(1)) if m else None


def config_default(text, field):
    """The default the original passes to its config loader for WorldConfig.<field> (int or bool), not the field initialiser."""
    m = re.search(r'\b'+field+r' = CommonConfig\.createConfig(?:Int|Bool)\(config, CATEGORY_OREGEN, "[^"]*", "[^"]*", (-?\d+|true|false)\)', text)
    if not m: return None
    return m.group(1) == 'true' if m.group(1) in ('true', 'false') else int(m.group(1))


def count_value(expression, text):
    """Evaluate a vein count expression of HbmWorldGen: an integer, WorldConfig.<field> or WorldConfig.<field> * <factor>."""
    m = re.fullmatch(r'\s*(\d+)\s*', expression)
    if m: return int(m.group(1))
    m = re.fullmatch(r'\s*WorldConfig\.(\w+)(?:\s*\*\s*(\d+))?\s*', expression)
    if not m: return None
    base_value = config_default(text, m.group(1))
    return None if base_value is None else base_value * int(m.group(2) or 1)


def parse_overworld_veins(text):
    """{ore: dict(count, size, min, variance, target)} of every `DungeonToolbox.generateOre(world, rand, i, j, count, size, minHeight, variance, ModBlocks.<ore>[, ModBlocks.<target>])`."""
    out = {}
    for count, size, low, var, ore, target in re.findall(r'DungeonToolbox\.generateOre\(world, rand, i, j, ([^,]+?), (\d+), (\d+), (\d+), ModBlocks\.(\w+)(?:, ModBlocks\.(\w+))?\)', text):
        out[ore] = dict(count_expression=count.strip(), size=int(size), min_height=int(low), variance=int(var), target=target or None)
    return out


def parse_depth_deposits(text):
    """[dict] of every `DepthDeposit.generateCondition(Overworld|Nether)(world, i, yMin, yDev, j, size, fill, ModBlocks.<ore>, rand, chance)`, in source order."""
    return [dict(dimension=d.lower(), y_min=int(y), y_dev=int(dev), size=int(size), fill=float(fill), ore=ore, chance=int(chance))
            for d, y, dev, size, fill, ore, chance in re.findall(r'DepthDeposit\.generateCondition(Overworld|Nether)\(world, i, (\d+), (\d+), j, (\d+), ([\d.]+)D, ModBlocks\.(\w+), rand, (\d+)\)', text)]


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
    goal28a_start = read(GOAL28A_BASELINE)
    goal28a_start['files'] = merged_files(goal28a_start)
    tracked_count = len(base['files'])

    # 1. Heads: the clean original at 4f5924e2b (unchanged since Goal28A), NEO at the start commit 66a00353 (the mod rename, = origin/master at the freeze; Goal28B commits nothing) with the UNCOMMITTED
    # Goal28A delivery in the worktree at the freeze (35 modified, 76 untracked files). The Goal 27 delivery adaf265c is two commits below; migration/ is untracked and Git-ignored (66050453), so the
    # start is `files` (the worktree content of the tracked and the untracked non-ignored files) + `migration_files`.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at 4f5924e2b'
    assert start_head.startswith(START_PREFIX), 'The frozen start is not on the mod rename commit 66a00353'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Rename the mod' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the mod rename commit'
    status_text = START_STATUS.read_text(encoding='utf-8')
    status_lines = [l for l in status_text.splitlines() if l]
    assert status_lines and base['target_status'] == status_text, 'start_status.txt differs from the baseline target status (the frozen start holds the uncommitted Goal28A delivery)'
    assert len(status_lines) == len(base['modified_at_start']) + len(base['untracked_at_start']) and sorted(l[3:] for l in status_lines) == sorted(base['modified_at_start'] + base['untracked_at_start']), \
        'start_status.txt does not list the modified_at_start and untracked_at_start paths of the baseline'
    assert base['target_parent'].startswith(START_PARENT_PREFIX) and base['origin_master'] == start_head, 'The start commit is not origin/master on c1f6f397'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal28a receipt records another original commit than 4f5924e2b (the original must be unmoved)'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal28B (the delivery stays uncommitted until the Goal 28 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2, 3)}
    assert chain[1].startswith(START_PARENT_PREFIX) and chain[2].startswith(UNTRACK_PREFIX) and chain[3].startswith(GOAL27_DELIVERY_PREFIX), \
        'NEO HEAD~1..3 are not c1f6f397, the migration/ untrack commit 66050453 and the Goal 27 delivery adaf265c: '+str(chain)
    committed_files = [l for l in git_ro(ROOT, 'show', '--name-only', '--format=', start_head).splitlines() if l.strip()]
    assert committed_files and not any(p.startswith('build/') for p in committed_files), 'The start commit is empty or holds build/ files'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and 'mod rename' in base['start_content']['committed'] and base['start_content']['uncommitted'].startswith('the Goal28A delivery'), \
        'Baseline start content differs (expected the committed mod rename and the uncommitted Goal28A delivery)'
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
        and startup['target_status_lines'] == len(status_lines) and startup['modified'] == len(base['modified_at_start']) and startup['untracked'] == len(base['untracked_at_start']) \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == older_drift_nonempty, \
        'startup-verification.json differs from baseline.json'
    base['files'] = merged_files(base)
    start_stamp = start_json(base, STAMP)
    assert base['stamp_state']['generated_resources_recorded'] == prior_receipt['generated_resource_count'] == len(start_stamp['generated']) \
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal28a generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_freeze']
    assert base['target_head'] == start_head and not [p for p in committed_files if p.startswith('migration/')], 'The start commit holds migration/ files (Git-ignored since 66050453)'
    # The start content must be exactly the packaged Goal28A delivery: every Git-visible path the goal28a receipt lists has the receipt's after-hash at the start, and the receipt lists no other one.
    delivery = {c['path']: c for c in prior_receipt['changed_files']}
    delivery_visible = sorted(p for p in delivery if not p.startswith(('migration/', 'build/')))
    need(delivery_visible == sorted(base['modified_at_start'] + base['untracked_at_start']),
         'The Git-visible paths of the goal28a receipt differ from the 28B start status: only in receipt %s, only at the start %s' % (
             sorted(set(delivery_visible) - set(base['modified_at_start'] + base['untracked_at_start']))[:4], sorted(set(base['modified_at_start'] + base['untracked_at_start']) - set(delivery_visible))[:4]))
    delivery_moved = sorted(p for p in delivery if p in base['files'] and base['files'][p] != delivery[p]['after_sha256'])
    uncommitted_start = dict(
        status_entries=len(status_lines), status=status_lines, modified=len(base['modified_at_start']), untracked=len(base['untracked_at_start']),
        modified_paths=base['modified_at_start'], untracked_paths=base['untracked_at_start'],
        description='the worktree holds the uncommitted Goal28A delivery (packaged as goal28a, never committed): the start content of this batch; baseline `files` hashes the worktree content, so every 28A change is part of the start',
        goal28a_delivery_paths=len(delivery), goal28a_paths_changed_since_package=delivery_moved,
        committed_delivery=dict(commit=start_head[:8], parent=base['target_parent'][:8], files_in_commit=len(committed_files), untrack_commit=chain[2][:8], goal27_delivery_commit=chain[3][:8],
                                note='66a00353 renames the mod (gradle.properties mod_name / mod_authors -> neoforge.mods.toml) and ignores .claude; c1f6f397 rewrites the README; 66050453 untracks and ignores '
                                     'migration/; adaf265c commits the Goal 27 delivery (27C and 27D) with the small fixes D3 and D5.'),
        migration_dir=dict(tracked_files_hashed=tracked_count, migration_files_hashed=len(base['migration_files']), copied_scope=len(base['copied_scope']),
                           note='migration/ is Git-ignored: `git ls-files` no longer lists it, so the baseline hashes it from disk and this packager finds its changes by walking the directory.'))

    # 2. Previous deliveries: the goal28a package (build/libs at the freeze is byte-identical to it), every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the freeze is not the goal28a package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal28a receipt list + the goal28a package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal28a receipt count + the goal28a release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal28a receipt'
    newer_drift = sorted(base['previous_receipt_evidence_drift'])
    need(newer_drift == [], 'The baseline records drift against the goal28a receipt (expected none: the receipt matches every hash it records): '+str(newer_drift))
    protected, repinned = protected_paths(base)
    need(all(p.endswith('-ACCEPTANCE.md') or p == 'migration/GOAL24B.md' for p in repinned), 'A pin other than an acceptance checklist or GOAL24B.md changed between the Goal28A and Goal28B starts: '+str(sorted(repinned)))
    drift_report = start_drift_report(base, repinned, goal28a_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal28a receipt: '+str(sorted(explained))
    # No small fix lies between the goal28a package and this start: the README lines above the Goal28A line (newest first) must name none. Any that does is listed as packaged with goal28b.
    readme_start = start_bytes(base, 'migration/README.md')
    readme_start_lines = readme_start.decode('utf-8').split('\n') if readme_start else []
    goal28a_line = next((i for i, l in enumerate(readme_start_lines) if l.startswith('2026-10-28 Goal28A')), None)
    need(goal28a_line is not None, 'migration/README.md (start copy) has no "2026-10-28 Goal28A" delivery line')
    small_fixes_after_goal28a = [l[:140] for l in readme_start_lines[:goal28a_line] if l.startswith('2026-10-') and '小修' in l] if goal28a_line is not None else None

    # 3. Changes since the start: each path in the owner table, attributed to goal28b. Everything else equals its start hash (the merged tracked and migration/ hashes).
    changes = changed_since_start(base)
    imported = {p for p in changes if TEXTURE_PATTERN.fullmatch(p)}
    verifier_md = VERIFIER_REPORT_MD.read_text(encoding='utf-8', errors='replace') if VERIFIER_REPORT_MD.is_file() else None
    need(verifier_md is not None, 'evidence missing: build/migration/goal28b/verifier-report.md (the GameTest / verifier session\'s report; it lists the older GameTest lines it edited)')
    if verifier_md is not None:
        for name in sorted(set(re.findall(r'\b(\w+GameTests)\.java', verifier_md))):
            p = J+'gametest/'+name+'.java'
            if p in changes and p in base['files'] and p not in EDITED_GAMETESTS and p != WORLDGEN_TESTS and p not in EDITED_EXTRA: EDITED_EXTRA.append(p)
    optional_changed = [p for p in OPTIONAL_JAVA if p in changes]
    modified_java = MODIFIED_JAVA + optional_changed
    edited_gametests = EDITED_GAMETESTS + EDITED_EXTRA
    production_java = NEW_JAVA + modified_java + [p for p in edited_gametests if p in changes]
    older_gametests_frozen = sorted(p for p in base['files'] if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p not in OPTIONAL_JAVA and p not in edited_gametests)
    unassigned = sorted(p for p in changes if group(p, imported) is None)
    need(not unassigned, 'Path changed since the Goal28B start that the owner table does not list (production outside the listed new and modified Java files, OverworldWorldgenGameTests and the older GameTests '
         'verifier-report.md names, a hand-written resource other than the 14 block textures, a generated file other than the stamp, en_us.json, the pickaxe tag, the malachite loot table and the worldgen, '
         'blockstate, model, loot table and recipe set, a protected or frozen record, an older tool, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal 28A and earlier records, GOAL28C/D.md, GOAL28-THREAD-PROMPTS.md or SURVIVAL-PLAYABILITY.md changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal28B start: '+str(deleted)
    for p in MODIFIED_JAVA + EDITED_GAMETESTS + GENERATED_MODIFIED + [ZH_INPUT, TASK_BOOK] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + REQUIRED_TEXTURES + REQUIRED_GENERATED + NEW_TOOLS + REPORTS[1:]:
        assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(production_java) - imported - {ZH_INPUT})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified (+ optional), {len(NEW_JAVA)} new and {len(edited_gametests)} edited GameTest Java files, the 14 block textures '
         'and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools = OLD_TOOLS_FROZEN + sorted(p for p in base['files'] if p.startswith(FROZEN_TOOL_DIRS))
    frozen_tools_changed = sorted(p for p in frozen_tools if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (package_goal28a.py, verify_goal28a_worldgen.py, package_goal27d.py, the 27A-27D packagers and verifiers, the casting regression '
         'wrapper and compat, the Goal 26C old-suite wrapper, the casting regressions and their folders): '+str(frozen_tools_changed))
    jei_classes = sorted(p for p in base['files'] if p.startswith(J+'handler/jei/'))
    frozen_dir_files = sorted(p for p in base['files'] if p.startswith(UNCHANGED_DIRS) or (p.startswith(GENERATED_ROOT+'data/hbmsntm/worldgen/') or p.startswith(GENERATED_ROOT+'data/hbmsntm/neoforge/biome_modifier/')))
    unchanged_bad = [p for p in UNCHANGED_JAVA + older_gametests_frozen + jei_classes + frozen_dir_files if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed (the six pre-existing feature classes, SmolderingNetherrackFeature, ConfigCountPlacement, ConfigGatedAddFeaturesBiomeModifier, '
         'IDepthRockTool, ToolAbilityItem, NtmItems, the foundry outlet block and block entity, the Goal 27 material / casting tables, MoldItem, ContaminationUtil, every handler/jei class, every other GameTest '
         'class, the hand-written worldgen data and biome modifiers and every generated worldgen / biome modifier JSON of the start): '+str(unchanged_bad[:8]))
    goal28_now = sha(ROOT/GOAL28_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository before the start. The batch ran under the main '
                                               'agent (production review, the migration/ records, zh_cn.json and the mapping) with a production builder (the 28B Java, runData), a GameTest verifier '
                                               '(OverworldWorldgenGameTests, the older row-count lines, verify_goal28b_worldgen.py, runData and the GameTest server), a reviewer and this packaging '
                                               'verifier (the packager, the final runner, the casting-regression attribution) working in the same checkout; each wrote only its named files (the scope snapshots '
                                               'of the verifiers are indexed as evidence).',
                             goal28_md=dict(start_sha256=base['files'][GOAL28_RECORD], current_sha256=goal28_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p) if (ROOT/p).is_file() else None) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p, imported), owner=owner_of(p), owners=[owner_of(p)], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    need(baselines_now == start_baselines, 'A snapshot changed or was added (the original did not move: no new snapshot): '+str(sorted(set(baselines_now) ^ set(start_baselines))))
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-4f5924e2b9e1 snapshot changed'
    production_changed = [p for p in production_java if p in changes]

    # The modified production files keep their start line endings (reported); new Java files are not mixed.
    gametest_edit_files = [p for p in edited_gametests if p in changes]
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
    content_rules = {}
    # The registration, bootstrap and provider files only gain lines: no start line is removed except a terminator or a call chain that an added line extends, and the by-design replacements below.
    registration_files = (COMMON_CONFIG, WORLDGEN_CODECS, CONFIGURED_FEATURES, PLACED_FEATURES, BIOME_MODIFIERS_JAVA, NTM_FEATURES, NTM_BLOCKS, CREATIVE_TABS, STATE_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER,
                          RECIPE_PROVIDER, LANG_PROVIDER, SHREDDER_RECIPES, OUTGAS_BLOCK, FLUID_CONTAINERS, CENTRIFUGE_RECIPES, CRYSTALLIZER_RECIPES)
    # By design: the WORLDGEN_SWITCHES / WORLDGEN_COUNTS name sets grow (CommonConfig), the schist uranium ores become OutgasBlock registrations (ModBlocks.java:1275-1276), the outgas class gains the schist
    # ore / asbestos arms (BlockOutgas.java:41-60), the crystallizer file description names the new table, and the malachite loot table drops chunks instead of itself (BlockResourceStone.java:33-41).
    by_design = {COMMON_CONFIG: r'WORLDGEN_SWITCHES = Set\.of|SpawnRate"', NTM_BLOCKS: r'ORE_GNEISS_URANIUM(?:_SCORCHED)? = register', OUTGAS_BLOCK: r'ORE_NETHER_URANIUM|BRICK_ASBESTOS',
                 CRYSTALLIZER_RECIPES: r'Ore acidizer \(crystallizer\) recipes', LOOT_PROVIDER: r'RESOURCE_MALACHITE'}
    for p in registration_files:
        if p not in removed_lines: continue
        stray = stray_removals(removed_lines[p], added_lines[p])
        replaced = [s for s in stray if p in by_design and re.search(by_design[p], s)]
        stray = [s for s in stray if s not in replaced]
        content_rules[p] = not stray
        if replaced: content_rules[p+'#replaced_by_design'] = replaced
        need(not stray, f'{p} removes start lines that no added line extends: {stray[:4]}')
    # The older GameTests the batch edits by design: the @GameTest methods are the start's; only table row-count checks (and their citation comments) change.
    gametest_edits = {}
    for p in gametest_edit_files:
        if p not in start_text: continue
        now_text, was_text = (ROOT/p).read_text(encoding='utf-8'), start_text[p].decode('utf-8')
        names_now, names_was = GAMETEST_METHOD.findall(now_text), GAMETEST_METHOD.findall(was_text)
        annotations_now, annotations_was = len(GAMETEST_ANNOTATION.findall(now_text)), len(GAMETEST_ANNOTATION.findall(was_text))
        touched = [l.strip() for l in removed_lines[p] + added_lines[p] if '@GameTest' in l or 'public static void' in l]
        code_removed = [l for l in removed_lines[p] if not is_comment(l)]
        code_added = [l for l in added_lines[p] if not is_comment(l)]
        counts_old = [int(m.group(1)) for l in code_removed for m in [ROW_COUNT_CHECK.search(l)] if m]
        counts_new = [int(m.group(1)) for l in code_added for m in [ROW_COUNT_CHECK.search(l)] if m]
        entry = dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p), added=len(added_lines[p]), removed=len(removed_lines[p]), game_tests=annotations_now, game_tests_at_start=annotations_was,
                     methods_unchanged=names_now == names_was, rule='only the table row-count checks change (acidizer / crystallizer default table 53 -> 60 rows, centrifuge 80 -> 83 rows)',
                     removed_counts=counts_old, added_counts=counts_new, changed_lines=dict(removed=[l.strip()[:160] for l in code_removed], added=[l.strip()[:160] for l in code_added]),
                     rule_holds=bool(counts_new) and len(code_removed) == len(counts_old) and len(code_added) == len(counts_new) and not touched
                     and sorted(ROW_MAP.get(c, c) for c in counts_old) == sorted(counts_new) and all(c in ROW_MAP for c in counts_old))
        gametest_edits[p] = entry
        need(entry['rule_holds'] and entry['methods_unchanged'] and annotations_now == annotations_was, f'{p} changed beyond its allowed edit ({entry["rule"]}): {json.dumps(entry, ensure_ascii=False)[:500]}')

    # 4. Overworld worldgen against the original (EXPECTED holds the handoff figures; every value is computed from the sources; the NEO side is read from the generated worldgen JSON and from
    # tolerant source patterns, the behaviour itself is the job of verify_goal28b_worldgen.py and OverworldWorldgenGameTests).
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

    def modifier(name): return generated_json(GENERATED_ROOT+f'data/hbmsntm/neoforge/biome_modifier/{name}.json')

    def placed_height(placed):
        h = next((m for m in (placed or {}).get('placement', []) if m.get('type') == 'minecraft:height_range'), {}).get('height', {})
        low, high = h.get('min_inclusive', {}), h.get('max_inclusive', {})
        return h.get('type'), (list(low)[0] if low else None, low.get(list(low)[0]) if low else None), (list(high)[0] if high else None, high.get(list(high)[0]) if high else None)

    o_veins = parse_overworld_veins(o[O_WORLDGEN])
    wc = o[O_WORLDCONFIG]
    # 4a. The config group: 17 new keys (overworldOres, eight schist counts, four cluster counts, alexandriteSpawnRate, three layer switches); the defaults equal the original's loader defaults (WorldConfig.java:121,
    # 127-147,176-179,193-195) multiplied as HbmWorldGen.java:110-139 does; ranges 0..256 (alexandrite 0..10000: an "every nth chunk" value).
    config_source = neo_text(COMMON_CONFIG)
    config_text = (lambda t: t[t.index('builder.push("worldgen")'):t.index('builder.pop()', t.index('builder.push("worldgen")'))])(config_source) if 'builder.push("worldgen")' in config_source else ''
    neo_ints = {m[0]: int(m[1]) for m in re.findall(r'defineInRange\("(\w+)",\s*(-?\d+),', config_text)}
    neo_bools = {m[0]: m[1] == 'true' for m in re.findall(r'\.define\("(\w+)",\s*(true|false)\)', config_text)}
    neo_ranges = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'defineInRange\("(\w+)",\s*-?\d+,\s*(-?\d+),\s*(-?\d+)\)', config_text)}
    expected_ints = {key: count_value(o_veins[ore]['count_expression'], wc) if ore in o_veins else None for ore, key in VEIN_KEYS.items()}
    expected_ints['alexandriteSpawnRate'] = config_default(wc, 'alexandriteSpawn')
    expected_bools = {'overworldOres': config_default(wc, 'overworldOre'), 'enableHematite': config_default(wc, 'enableHematite'), 'enableMalachite': config_default(wc, 'enableMalachite'),
                      'enableBauxite': config_default(wc, 'enableBauxite')}
    new_ints = {k: neo_ints.get(k) for k in expected_ints}
    new_bools = {k: neo_bools.get(k) for k in expected_bools}
    expected_ranges = {k: (0, 10000 if k == 'alexandriteSpawnRate' else 256) for k in expected_ints}
    fact('config_group', dict(keys=sorted(k for k in CONFIG_KEYS if k in neo_ints or k in neo_bools), ints=new_ints, bools=new_bools),
         dict(keys=sorted(CONFIG_KEYS), ints=expected_ints, bools=expected_bools),
         ok=sorted(k for k in CONFIG_KEYS if k in neo_ints or k in neo_bools) == sorted(CONFIG_KEYS) and new_ints == expected_ints and new_bools == expected_bools and all(v is not None for v in expected_ints.values())
         and len(CONFIG_KEYS) == EXPECTED['config_values'] and all(neo_ranges.get(k) == r for k, r in expected_ranges.items()) and 'private static boolean' not in config_text)
    fact('config_effective_defaults', dict(declared_uranium=original_int_default(wc, 'uraniumSpawn'), loaded_uranium=config_default(wc, 'uraniumSpawn'), declared_asbestos=original_int_default(wc, 'asbestosSpawn'),
                                           loaded_asbestos=config_default(wc, 'asbestosSpawn')), dict(declared_uranium=6, loaded_uranium=7, declared_asbestos=4, loaded_asbestos=2))
    # The three name sets the codec types validate against: the switches grow by four, the counts by twelve, the "every nth chunk" set holds alexandriteSpawnRate.
    def names_of(pattern):
        m = re.search(pattern, config_source)
        return sorted(re.findall(r'"(\w+)"', m.group(1))) if m else None
    switches, counts_set, rarities = names_of(r'WORLDGEN_SWITCHES = Set\.of\(([^)]*)\)'), names_of(r'WORLDGEN_COUNTS = Set\.of\(([^)]*)\)'), names_of(r'WORLDGEN_RARITIES = Set\.of\(([^)]*)\)')
    fact('config_name_sets', dict(switches=switches, counts=counts_set, rarities=rarities), None,
         ok=switches == sorted(['netherOres', 'endOres', 'enablePlutoniumNetherOre', *WORLDGEN_SWITCH_KEYS]) and counts_set is not None and set(WORLDGEN_COUNT_KEYS) - {'alexandriteSpawnRate'} <= set(counts_set)
         and len([k for k in counts_set if k.startswith(('gneiss', 'ironCluster', 'titaniumCluster', 'aluminiumCluster', 'copperCluster'))]) == len(VEIN_KEYS) and rarities == ['alexandriteSpawnRate'])
    # 4b. The rarity placement and the three feature types: config_rarity reads the value for every chunk (`if(spawn > 0 && rand.nextInt(spawn) == 0)`, HbmWorldGen.java:98-99), the stratum, depth
    # deposit and ore layer features are registered under their own names.
    n_codecs, n_rarity, n_features = code(WORLDGEN_CODECS), code(RARITY_PLACEMENT), code(NTM_FEATURES)
    fact('codec_types', dict(rarity_registered='"config_rarity"' in n_codecs and 'PLACEMENT_MODIFIER_TYPES' in n_codecs, rarity_reads_per_chunk=bool(re.search(r'worldgenRarity\(this\.config\)\.get\(\)', n_rarity)),
                             rarity_roll=bool(re.search(r'chance > 0 && random\.nextInt\(chance\) == 0', n_rarity)), rarity_names_validated='WORLDGEN_RARITIES' in n_rarity,
                             original_roll='WorldConfig.alexandriteSpawn > 0 && rand.nextInt(WorldConfig.alexandriteSpawn) == 0' in o[O_WORLDGEN],
                             features_registered=dict(schist='"schist_stratum"' in n_features, depth='"depth_deposit"' in n_features, layer='"ore_layer"' in n_features),
                             client_free=not re.search(r'net\.minecraft\.client|com\.hbm\.render\.', n_rarity)),
         dict(rarity_registered=True, rarity_reads_per_chunk=True, rarity_roll=True, rarity_names_validated=True, original_roll=True, features_registered=dict(schist=True, depth=True, layer=True), client_free=True))
    # 4c. The vein table: HbmWorldGen.java:98-139 (generateOre(world, rand, i, j, count, size, minHeight, variance, ore[, target])); DungeonToolbox.java:65-83: y = minHeight + rand(variance) -> the uniform
    # height range [min, min + variance - 1]; the eight schist ores replace stone_gneiss, the clusters and alexandrite stone (NEO: #minecraft:stone_ore_replaceables); alexandrite is rolled once per nth chunk.
    veins, vein_ok = {}, True
    for ore, key in {**VEIN_KEYS, 'ore_alexandrite': 'alexandriteSpawnRate'}.items():
        row = o_veins.get(ore)
        configured, placed = gen('configured_feature', ore), gen('placed_feature', ore+'_placed')
        gneiss = ore.startswith('ore_gneiss')
        entry = dict(original=row, neo_config_key=key, original_default=expected_ints.get(key))
        if row and configured and placed:
            ore_config, placement = configured.get('config', {}), placed.get('placement', [])
            height = placed_height(placed)
            rolled = 'hbmsntm:config_rarity' if ore == 'ore_alexandrite' else 'hbmsntm:config_count'
            expected_target = {'predicate_type': 'minecraft:block_match', 'block': 'hbmsntm:stone_gneiss'} if gneiss else {'predicate_type': 'minecraft:tag_match', 'tag': 'minecraft:stone_ore_replaceables'}
            entry['neo'] = dict(type=configured.get('type'), size=ore_config.get('size'), state=[t['state']['Name'] for t in ore_config.get('targets', [])], target=[t['target'] for t in ore_config.get('targets', [])],
                                modifiers=[m.get('type') for m in placement], config=placement[0].get('config') if placement else None, height=height)
            entry['ok'] = (entry['neo']['type'] == 'minecraft:ore' and entry['neo']['size'] == row['size'] and entry['neo']['state'] == ['hbmsntm:'+ore] and entry['neo']['target'] == [expected_target]
                           and row['target'] == ('stone_gneiss' if gneiss else None) and entry['neo']['modifiers'] == [rolled, 'minecraft:in_square', 'minecraft:height_range', 'minecraft:biome']
                           and entry['neo']['config'] == key and height == ('minecraft:uniform', ('absolute', row['min_height']), ('absolute', row['min_height'] + row['variance'] - 1))
                           and new_ints.get(key) == expected_ints.get(key) and (ore != 'ore_alexandrite' or row['count_expression'] == '1'))
        else: entry['ok'] = False
        veins[ore] = entry
        vein_ok = vein_ok and entry['ok']
    fact('veins', {k: dict(original=v['original'], neo=v.get('neo'), original_default=v['original_default']) for k, v in veins.items()}, None, ok=vein_ok and len(veins) == EXPECTED['veins'])
    # 4d. The depth deposits: HbmWorldGen.java:101-107,523-524 -> DepthDeposit.generateConditionOverworld/Nether(world, i, yMin, yDev, j, size, fill, ore, rand, chance); DepthDeposit.java: a sphere of radius
    # `size` around the centre, `if(j < 1 || j > 126) continue`, replaces the target and bedrock, ore when len + rand(2) < size * fill else filler when len + rand(2) <= size. NEO: DepthDepositFeature, a
    # rarity_filter with the original chance, the height relative to the bottom of the world (overworld) or absolute (nether, y 0..2 and 125..127).
    o_depth = parse_depth_deposits(o[O_WORLDGEN])
    depth, depth_ok = [], True
    for row in o_depth:
        neo_name, _placed_names = DEPTH_FEATURES.get(row['ore'], (None, []))
        neo_ore = 'ore_depth_cinnabar' if row['ore'] == 'ore_depth_cinnebar' else row['ore']
        placed_name = (neo_name+'_placed') if row['ore'] != 'ore_depth_nether_neodymium' else 'depth_ore_nether_neodymium_'+('low' if row['y_min'] == 0 else 'high')+'_placed'
        configured, placed = (gen('configured_feature', neo_name) if neo_name else None), gen('placed_feature', placed_name)
        nether = row['dimension'] == 'nether'
        entry = dict(original=row, neo_feature=neo_name, neo_placed=placed_name)
        if configured and placed:
            c = configured.get('config', {})
            placement = placed.get('placement', [])
            height = placed_height(placed)
            expected_height = ('minecraft:uniform', ('absolute' if nether else 'above_bottom', row['y_min']), ('absolute' if nether else 'above_bottom', row['y_min'] + row['y_dev'] - 1))
            expected_target = {'predicate_type': 'minecraft:block_match', 'block': 'minecraft:netherrack'} if nether else {'predicate_type': 'minecraft:tag_match', 'tag': 'minecraft:base_stone_overworld'}
            entry['neo'] = dict(type=configured.get('type'), size=c.get('size'), fill=c.get('fill'), ore=c.get('ore', {}).get('Name'), filler=c.get('filler', {}).get('Name'), target=c.get('target'),
                                modifiers=[m.get('type') for m in placement], chance=placement[0].get('chance') if placement else None, height=height)
            entry['ok'] = (entry['neo']['type'] == 'hbmsntm:depth_deposit' and entry['neo']['size'] == row['size'] and entry['neo']['fill'] == row['fill'] and entry['neo']['ore'] == 'hbmsntm:'+neo_ore
                           and entry['neo']['filler'] == ('hbmsntm:stone_depth_nether' if nether else 'hbmsntm:stone_depth') and entry['neo']['target'] == expected_target
                           and entry['neo']['modifiers'] == ['minecraft:rarity_filter', 'minecraft:in_square', 'minecraft:height_range', 'minecraft:biome'] and entry['neo']['chance'] == row['chance'] and height == expected_height)
        else: entry['ok'] = False
        depth.append(entry)
        depth_ok = depth_ok and entry['ok']
    n_depth = code(DEPTH_FEATURE)
    fact('depth_deposits', depth, None, ok=depth_ok and len(depth) == EXPECTED['depth_deposits'])
    fact('depth_feature', dict(original_bounds='if(j < 1 || j > 126)' in o[O_DEPTHDEPOSIT], original_bedrock='target.isReplaceableOreGen(world, i, j, k, Blocks.bedrock)' in o[O_DEPTHDEPOSIT],
                               original_draws='len + rand.nextInt(2) < size * fill' in o[O_DEPTHDEPOSIT] and 'len + rand.nextInt(2) <= size' in o[O_DEPTHDEPOSIT],
                               neo_bounds=bool(re.search(r'MIN_OFFSET = 1;', n_depth)) and bool(re.search(r'MAX_OFFSET = 126;', n_depth)) and 'getMinBuildHeight() + MIN_OFFSET' in n_depth and 'getMinBuildHeight() + MAX_OFFSET' in n_depth,
                               neo_bedrock='Blocks.BEDROCK' in n_depth, neo_draws='len + random.nextInt(2) < size * config.fill()' in n_depth and 'len + random.nextInt(2) <= size' in n_depth),
         dict(original_bounds=True, original_bedrock=True, original_draws=True, neo_bounds=True, neo_bedrock=True, neo_draws=True))
    # 4e. The three ore layers: MainRegistry.java:602-604 (new OreLayer3D(stone_resource, TYPE).setScaleH().setScaleV().setThreshold(), each behind its own switch); OreLayer3D.java: noiseX/noiseY seeded
    # seed + 101 + id / + 102 + id, y 64 down to 6, the third factor is cacheX[ox][y] (:111). NEO: OreLayerFeature constants, the configured layer index = the creation order (0 hematite, 1 bauxite, 2 malachite).
    layer_rows = re.findall(r'if\(WorldConfig\.(\w+)\) new OreLayer3D\(ModBlocks\.stone_resource, EnumStoneType\.(\w+)\.ordinal\(\)\)\.setScaleH\(([\d.]+)D\)\.setScaleV\(([\d.]+)D\)\.setThreshold\((\d+)\);', o[O_MAINREGISTRY])
    layers, layers_ok = [], True
    for index, (switch, kind, scale_h, scale_v, threshold) in enumerate(layer_rows):
        name = kind.lower()
        configured, placed, mod = gen('configured_feature', name+'_layer'), gen('placed_feature', name+'_layer_placed'), modifier(f'add_{name}_layer')
        entry = dict(original=dict(switch=switch, type=kind, scale_h=float(scale_h), scale_v=float(scale_v), threshold=float(threshold), layer=index))
        c = (configured or {}).get('config', {})
        entry['neo'] = dict(type=(configured or {}).get('type'), layer=c.get('layer'), scale_h=c.get('scale_h'), scale_v=c.get('scale_v'), threshold=c.get('threshold'), state=c.get('state', {}).get('Name'),
                            placement=(placed or {}).get('placement'), modifier=dict(type=(mod or {}).get('type'), biomes=(mod or {}).get('biomes'), config=(mod or {}).get('config'), step=(mod or {}).get('step'),
                                                                                    features=(mod or {}).get('features')))
        entry['ok'] = (entry['neo']['type'] == 'hbmsntm:ore_layer' and entry['neo']['layer'] == index and entry['neo']['scale_h'] == float(scale_h) and entry['neo']['scale_v'] == float(scale_v)
                       and entry['neo']['threshold'] == float(threshold) and entry['neo']['state'] == 'hbmsntm:resource_'+name and entry['neo']['placement'] == []
                       and entry['neo']['modifier'] == dict(type='hbmsntm:config_gated_add_features', biomes='#minecraft:is_overworld', config=[switch], step='underground_ores', features=f'hbmsntm:{name}_layer_placed')
                       and switch in WORLDGEN_SWITCH_KEYS)
        layers.append(entry)
        layers_ok = layers_ok and entry['ok']
    n_layer = code(LAYER_FEATURE)
    fact('ore_layers', layers, None, ok=layers_ok and [e['original']['type'] for e in layers] == ['HEMATITE', 'BAUXITE', 'MALACHITE'] and len(layers) == EXPECTED['layers'])
    fact('ore_layer_feature', dict(original=dict(seed_x='world.getSeed() + 101 + id' in o[O_ORELAYER], seed_y='world.getSeed() + 102 + id' in o[O_ORELAYER], heights='for(int y = 64; y > 5; y--)' in o[O_ORELAYER],
                                                 third_noise='double nz = cacheX[ox][y];' in o[O_ORELAYER], threshold='nx * ny * nz > threshold' in o[O_ORELAYER], octaves='new NoiseGeneratorPerlin(new Random(world.getSeed() + 101 + id), 4)' in o[O_ORELAYER]),
                                   neo=dict(seed_x=bool(re.search(r'SEED_OFFSET_X = 101L', n_layer)) and 'seed + SEED_OFFSET_X + config.layer()' in n_layer, seed_y=bool(re.search(r'SEED_OFFSET_Y = 102L', n_layer)) and 'seed + SEED_OFFSET_Y + config.layer()' in n_layer,
                                            heights=bool(re.search(r'Y_MIN = 6;', n_layer)) and bool(re.search(r'Y_MAX = 64;', n_layer)), third_noise='double nz = cacheX[third][y];' in n_layer and 'int third = gridZ + x - gridX - (minZ - 16);' in n_layer and 'int gridX = Math.floorDiv(x - 8, 16) * 16;' in n_layer,
                                            threshold='nx * ny * nz > threshold' in n_layer, octaves='List.of(-3, -2, -1, 0)' in n_layer and 'LEGACY_AMPLITUDE = 15.0D' in n_layer,
                                            replaces_stone_ore_replaceables='BlockTags.STONE_ORE_REPLACEABLES' in n_layer, overworld_only='Level.OVERWORLD' in n_layer)),
         None, ok='world.getSeed() + 101 + id' in o[O_ORELAYER] and 'world.getSeed() + 102 + id' in o[O_ORELAYER] and 'for(int y = 64; y > 5; y--)' in o[O_ORELAYER] and 'double nz = cacheX[ox][y];' in o[O_ORELAYER]
         and 'SEED_OFFSET_X = 101L' in n_layer and 'SEED_OFFSET_Y = 102L' in n_layer and 'Y_MIN = 6;' in n_layer and 'Y_MAX = 64;' in n_layer and 'double nz = cacheX[third][y];' in n_layer and 'int third = gridZ + x - gridX - (minZ - 16);' in n_layer and 'int gridX = Math.floorDiv(x - 8, 16) * 16;' in n_layer
         and 'nx * ny * nz > threshold' in n_layer and 'List.of(-3, -2, -1, 0)' in n_layer and 'LEGACY_AMPLITUDE = 15.0D' in n_layer and 'BlockTags.STONE_ORE_REPLACEABLES' in n_layer and 'Level.OVERWORLD' in n_layer)
    # 4f. The schist stratum: SchistStratum.java:25-60 (NoiseGeneratorPerlin(new Random(seed), 4), scale 0.01, threshold 5, range = (n - 5) * 3 folded above 4 to 8 - range, y 30 -/+ range); registered
    # unconditionally (MainRegistry.java:597). NEO: SchistStratumFeature constants, an ungated add_features modifier in step local_modifications.
    o_schist = dict(scale=re.search(r'double scale = ([\d.]+)D;', o[O_SCHIST]), threshold=re.search(r'int threshold = (\d+);', o[O_SCHIST]), range_mult=re.search(r'\(n - threshold\) \* (\d+)\)', o[O_SCHIST]),
                    fold=re.search(r'if\(range > (\d+)\)\s*range = (\d+) - range;', o[O_SCHIST]), center=re.search(r'for\(int y = (\d+) - range; y <= \1 \+ range; y\+\+\)', o[O_SCHIST]),
                    octaves=re.search(r'new NoiseGeneratorPerlin\(new Random\(event\.world\.getSeed\(\)\), (\d+)\)', o[O_SCHIST]))
    original_schist = dict(scale=float(o_schist['scale'].group(1)) if o_schist['scale'] else None, threshold=int(o_schist['threshold'].group(1)) if o_schist['threshold'] else None,
                           range_mult=int(o_schist['range_mult'].group(1)) if o_schist['range_mult'] else None, fold_above=int(o_schist['fold'].group(1)) if o_schist['fold'] else None,
                           fold=int(o_schist['fold'].group(2)) if o_schist['fold'] else None, center_y=int(o_schist['center'].group(1)) if o_schist['center'] else None,
                           octaves=int(o_schist['octaves'].group(1)) if o_schist['octaves'] else None, dimension_zero='world.provider.dimensionId != 0' in o[O_SCHIST], registered_unconditionally=
                           'MinecraftForge.EVENT_BUS.register(new SchistStratum());' in o[O_MAINREGISTRY] and 'if(WorldConfig.overworldOre) MinecraftForge.EVENT_BUS.register(new SchistStratum' not in o[O_MAINREGISTRY])
    n_schist = code(SCHIST_FEATURE)

    def neo_constant(name, kind=float):
        m = re.search(name+r' = ([\d.]+)D?;', n_schist)
        return kind(m.group(1)) if m else None
    neo_schist = dict(scale=neo_constant('SCALE'), threshold=neo_constant('THRESHOLD', int), range_mult=neo_constant('RANGE_MULT', int), fold_above=neo_constant('FOLD_ABOVE', int), fold=neo_constant('FOLD', int),
                      center_y=neo_constant('CENTER_Y', int), amplitude=neo_constant('LEGACY_AMPLITUDE'), octave_list='List.of(-3, -2, -1, 0)' in n_schist, overworld_only='Level.OVERWORLD' in n_schist,
                      replaces_stone_ore_replaceables='BlockTags.STONE_ORE_REPLACEABLES' in n_schist, flags_2=bool(re.search(r'level\.setBlock\(pos, gneiss, 2\)', n_schist)))
    fact('schist_stratum', dict(original=original_schist, neo=neo_schist), None,
         ok=all(v is not None for v in original_schist.values()) and original_schist['dimension_zero'] and original_schist['registered_unconditionally']
         and (neo_schist['scale'], neo_schist['threshold'], neo_schist['range_mult'], neo_schist['fold_above'], neo_schist['fold'], neo_schist['center_y']) ==
         (original_schist['scale'], original_schist['threshold'], original_schist['range_mult'], original_schist['fold_above'], original_schist['fold'], original_schist['center_y'])
         and neo_schist['amplitude'] == float(2**original_schist['octaves'] - 1) and neo_schist['octave_list'] and neo_schist['overworld_only'] and neo_schist['replaces_stone_ore_replaceables'] and neo_schist['flags_2'])
    # 4g. The seven biome modifiers: the stratum (ungated, local_modifications), alexandrite (ungated, config_rarity), the three layers (own switch each), add_overworld_ores (overworldOres: six depth deposits, eight
    # schist ores, four clusters in the original order), add_nether_depth_deposits (netherOres: neodymium low then high). The 28A modifiers are pinned unchanged by the frozen generated tree.
    overworld_order = [e['neo_placed'] for e in depth if e['original']['dimension'] == 'overworld'] + [ore+'_placed' for ore in o_veins if ore in VEIN_KEYS]
    wants = {'add_schist_stratum': ('neoforge:add_features', '#minecraft:is_overworld', None, 'hbmsntm:schist_stratum_placed', 'local_modifications'),
             'add_alexandrite_ore': ('neoforge:add_features', '#minecraft:is_overworld', None, 'hbmsntm:ore_alexandrite_placed', 'underground_ores'),
             'add_hematite_layer': ('hbmsntm:config_gated_add_features', '#minecraft:is_overworld', ['enableHematite'], 'hbmsntm:hematite_layer_placed', 'underground_ores'),
             'add_bauxite_layer': ('hbmsntm:config_gated_add_features', '#minecraft:is_overworld', ['enableBauxite'], 'hbmsntm:bauxite_layer_placed', 'underground_ores'),
             'add_malachite_layer': ('hbmsntm:config_gated_add_features', '#minecraft:is_overworld', ['enableMalachite'], 'hbmsntm:malachite_layer_placed', 'underground_ores'),
             'add_overworld_ores': ('hbmsntm:config_gated_add_features', '#minecraft:is_overworld', ['overworldOres'], ['hbmsntm:'+n for n in overworld_order], 'underground_ores'),
             'add_nether_depth_deposits': ('hbmsntm:config_gated_add_features', '#minecraft:is_nether', ['netherOres'], ['hbmsntm:depth_ore_nether_neodymium_low_placed', 'hbmsntm:depth_ore_nether_neodymium_high_placed'], 'underground_ores')}
    got = {}
    for name in wants:
        m = modifier(name) or {}
        got[name] = dict(type=m.get('type'), biomes=m.get('biomes'), config=m.get('config'), features=m.get('features'), step=m.get('step'))
    fact('biome_modifiers', got, {n: dict(type=w[0], biomes=w[1], config=w[2], features=w[3], step=w[4]) for n, w in wants.items()},
         ok=got == {n: dict(type=w[0], biomes=w[1], config=w[2], features=w[3], step=w[4]) for n, w in wants.items()} and len(wants) == EXPECTED['biome_modifiers'] and len(overworld_order) == 18)
    fact('worldgen_names', dict(configured=len([n for n in CONFIGURED_NAMES if gen('configured_feature', n)]), placed=len([n for n in PLACED_NAMES if gen('placed_feature', n)]),
                                biome_modifiers=len([n for n in BIOME_MODIFIER_NAMES if modifier(n)])),
         dict(configured=EXPECTED['configured_features'], placed=EXPECTED['placed_features'], biome_modifiers=EXPECTED['biome_modifiers']))
    # 4h. The 22 blocks (ModBlocks.java:1253-1256,1271-1294,1308-1309): class, hardness, resistance. BlockCluster / BlockGeneric / BlockOre -> Block, BlockOutgas -> OutgasBlock(true, true), BlockDepth /
    # BlockDepthOre -> DepthBlock (unbreakable, resistance 10: strength(-1.0F)).
    o_blocks = {}
    for name in BLOCK_NAMES:
        oname = ORIGINAL_BLOCK_KEY[name]
        m = re.search(r'^\s*'+oname+r' = new (\w+)\(([^;]*?)\)\.setBlockName\("'+oname+r'"\)([^\n]*)$', o[O_MODBLOCKS], re.M)
        if m:
            tail, args = m.group(3), [a.strip() for a in m.group(2).split(',') if a.strip()]
            hardness, resistance = re.search(r'setHardness\(([\d.]+)F\)', tail), re.search(r'setResistance\(([\d.]+)F\)', tail)
            o_blocks[name] = dict(cls=m.group(1), args=[a for a in args if a != 'Material.rock'], hardness=float(hardness.group(1)) if hardness else None, resistance=float(resistance.group(1)) if resistance else None)
    n_blocks_code = code(NTM_BLOCKS)
    n_blocks = {}
    for name in BLOCK_NAMES:
        m = re.search(r'register\("'+name+r'",\s*\(\)\s*->\s*new (\w+)\(((?:true, true, )?)BlockBehaviour\.Properties\.of\(\)\.strength\((-?[\d.]+)F\)\.explosionResistance\(([\d.]+)F\)', n_blocks_code)
        if m: n_blocks[name] = dict(cls=m.group(1), outgas_args=[a.strip() for a in m.group(2).split(',') if a.strip()], hardness=float(m.group(3)), resistance=float(m.group(4)))
    neo_class = {'BlockCluster': 'Block', 'BlockGeneric': 'Block', 'BlockOre': 'Block', 'BlockOutgas': 'OutgasBlock', 'BlockDepth': 'DepthBlock', 'BlockDepthOre': 'DepthBlock'}
    blocks_ok = set()
    for name, ob in o_blocks.items():
        nb = n_blocks.get(name)
        unbreakable = ob['cls'] in ('BlockDepth', 'BlockDepthOre')
        expected_strength, expected_resistance = (-1.0, 10.0) if unbreakable else (ob['hardness'], ob['resistance'])
        if nb and neo_class.get(ob['cls']) == nb['cls'] and nb['hardness'] == expected_strength and nb['resistance'] == expected_resistance \
                and (ob['cls'] != 'BlockOutgas' or (ob['args'] == ['true', '5', 'true'] and nb['outgas_args'] == ['true', 'true'])):
            blocks_ok.add(name)
    fact('block_properties', {n: dict(original=o_blocks.get(n), neo=n_blocks.get(n)) for n in BLOCK_NAMES}, None, ok=blocks_ok == set(BLOCK_NAMES) and len(BLOCK_NAMES) == EXPECTED['blocks'])
    n_depth_block = code(DEPTH_BLOCK)
    fact('depth_rock', dict(original=dict(progress='return (float) (1D / 50D);' in o[O_BLOCKDEPTH], tool='instanceof IDepthRockTool' in o[O_BLOCKDEPTH], unbreakable='this.setBlockUnbreakable();' in o[O_BLOCKDEPTH],
                                          resistance='this.setResistance(10.0F);' in o[O_BLOCKDEPTH], tooltip='trait.tile.depth' in o[O_BLOCKDEPTH], ore_extends_depth='extends BlockDepth' in o[O_BLOCKDEPTHORE]),
                            neo=dict(progress=bool(re.search(r'return 1\.0F / 50\.0F;', n_depth_block)), tool=bool(re.search(r'instanceof IDepthRockTool tool && tool\.canBreakRock\(', n_depth_block)),
                                     main_hand='player.getMainHandItem()' in n_depth_block, falls_back='super.getDestroyProgress(state, player, level, pos)' in n_depth_block,
                                     tooltip='"trait.tile.depth"' in n_depth_block)),
         None, ok='return (float) (1D / 50D);' in o[O_BLOCKDEPTH] and 'instanceof IDepthRockTool' in o[O_BLOCKDEPTH] and 'this.setBlockUnbreakable();' in o[O_BLOCKDEPTH] and 'trait.tile.depth' in o[O_BLOCKDEPTH]
         and bool(re.search(r'return 1\.0F / 50\.0F;', n_depth_block)) and bool(re.search(r'instanceof IDepthRockTool tool && tool\.canBreakRock\(', n_depth_block)) and 'player.getMainHandItem()' in n_depth_block
         and 'super.getDestroyProgress(state, player, level, pos)' in n_depth_block and '"trait.tile.depth"' in n_depth_block)
    # 4i. Drops (BlockCluster.java:19-28, BlockDepthOre.java:10-65, BlockOre.java:60-119, BlockResourceStone.java:33-41): the loot tables derive from these figures.
    def drops(name):
        d = generated_json(GENERATED_ROOT+f'data/hbmsntm/loot_table/blocks/{name}.json')
        if not d: return None
        out = []

        def walk(node):
            if isinstance(node, dict):
                if node.get('type') == 'minecraft:item':
                    count = next((f for f in node.get('functions', []) if f.get('function') == 'minecraft:set_count'), None)
                    silk = any(c.get('condition') == 'minecraft:match_tool' for c in node.get('conditions', []))
                    limit = next((f for f in node.get('functions', []) if f.get('function') == 'minecraft:limit_count'), None)
                    decay = any(f.get('function') == 'minecraft:explosion_decay' for f in node.get('functions', []))
                    out.append(dict(item=node.get('name'), silk_touch=silk, count=[count['count']['min'], count['count']['max']] if count and isinstance(count.get('count'), dict) else None,
                                    fortune=any(f.get('function') == 'minecraft:apply_bonus' for f in node.get('functions', [])), limit=limit['limit']['max'] if limit else None, explosion_decay=decay))
                for v in node.values(): walk(v)
            elif isinstance(node, list):
                for v in node: walk(v)
        walk(d.get('pools', []))
        return out
    cluster_drops = dict(re.findall(r'if\(this == ModBlocks\.(cluster_\w+)\)\s*return ModItems\.(\w+);', o[O_BLOCKCLUSTER]))
    depth_drops = dict(re.findall(r'if\(this == ModBlocks\.(\w+)\) \{\s*return ModItems\.(\w+);', o[O_BLOCKDEPTHORE]))
    depth_counts = {k: [int(a), int(a)+int(n)-1] for k, a, n in re.findall(r'if\(this == ModBlocks\.(\w+)\) \{\s*return (\d+) \+ rand\.nextInt\((\d+)\);', o[O_BLOCKDEPTHORE])}
    item_id = lambda token: 'hbmsntm:'+token.replace('cinnebar', 'cinnabar')
    expected_drops = {}   # block -> (item, count, fortune, limit)
    depth_block_names = set()
    for block, item in cluster_drops.items(): expected_drops[block] = (item_id(item), None, False, None)
    for block, item in depth_drops.items():
        neo_block = ORIGINAL_BLOCK_KEY and block.replace('cinnebar', 'cinnabar')
        expected_drops[neo_block] = (item_id(item), depth_counts.get(block, [1, 1]), True, 2 if block == 'ore_alexandrite' else None)
        depth_block_names.add(neo_block)
    expected_drops['ore_gneiss_asbestos'] = ('hbmsntm:ingot_asbestos', [1, 1], True, None)
    expected_drops['ore_gneiss_rare'] = ('hbmsntm:rare_earth_ore_chunk', [1, 1], True, None)
    got_drops = {n: drops(n) for n in BLOCK_NAMES}
    drop_ok = bool(cluster_drops) and len(cluster_drops) == 4 and len(depth_drops) == 8 and 'this == ModBlocks.ore_asbestos || this == ModBlocks.ore_gneiss_asbestos' in o[O_BLOCKORE] \
        and 'this == ModBlocks.ore_rare || this == ModBlocks.ore_gneiss_rare' in o[O_BLOCKORE] and 'quantity > 2) quantity = 2' in o[O_BLOCKDEPTHORE]
    for block, (item, count, fortune, limit) in expected_drops.items():
        entries = got_drops.get(block) or []
        drop_ok = drop_ok and any(d['item'] == item and not d['silk_touch'] and d['fortune'] == fortune and d['limit'] == limit and (d['explosion_decay'] if block in depth_block_names else True) and (count is None or d['count'] == count) and (count is not None or d['count'] is None) for d in entries) \
            and any(d['item'] == 'hbmsntm:'+block and d['silk_touch'] for d in entries)
    for block in ('ore_gneiss_iron', 'ore_gneiss_gold', 'ore_gneiss_copper', 'ore_gneiss_lithium', 'ore_gneiss_gas', 'stone_depth', 'stone_depth_nether', 'stone_gneiss'):
        drop_ok = drop_ok and [d['item'] for d in got_drops.get(block) or []] == ['hbmsntm:'+block]
    malachite = drops('resource_malachite') or []
    malachite_original = re.search(r'EnumChunkType\.MALACHITE, (\d+) \+ fortune \+ world\.rand\.nextInt\(fortune \+ 2\)', o[O_RESOURCESTONE])
    drop_ok = drop_ok and bool(malachite_original) and any(d['item'] == 'hbmsntm:chunk_malachite' and not d['silk_touch'] and d['fortune'] and d['count'] == [int(malachite_original.group(1)), int(malachite_original.group(1)) + 1] for d in malachite) \
        and any(d['item'] == 'hbmsntm:resource_malachite' and d['silk_touch'] for d in malachite)
    fact('drops', dict(original=dict(clusters=cluster_drops, depth=depth_drops, depth_counts=depth_counts, malachite=malachite_original.groups() if malachite_original else None), expected=expected_drops,
                       neo={n: got_drops.get(n) for n in list(expected_drops) + ['resource_malachite']} | {'resource_malachite': malachite}), None, ok=drop_ok)
    pickaxe = read(ROOT/PICKAXE_TAG)['values'] if (ROOT/PICKAXE_TAG).is_file() else []
    fact('pickaxe_tag', {n: 'hbmsntm:'+n in pickaxe for n in BLOCK_NAMES}, {n: True for n in BLOCK_NAMES})
    needs_tags = sorted(p.relative_to(ROOT).as_posix() for base_dir in (GENERATED_ROOT+'data', RES+'data') for p in (ROOT/base_dir).glob('*/tags/block/needs_*.json'))
    depth_in_needs = sorted(p for p in needs_tags if any('hbmsntm:'+n in (ROOT/p).read_text(encoding='utf-8') for n in ('stone_depth', 'stone_depth_nether', 'ore_alexandrite') + DEPTH_ORE_NAMES + tuple(c for c in CLUSTER_NAMES if 'depth' in c)))
    fact('depth_blocks_in_no_needs_tool_tag', depth_in_needs, [])
    # 4j. Outgassing (BlockOutgas.java:41-60): the schist uranium ores release radon, the schist asbestos ore asbestos.
    n_outgas = code(OUTGAS_BLOCK)
    fact('outgassing', dict(original_radon='this == ModBlocks.ore_gneiss_uranium || this == ModBlocks.ore_gneiss_uranium_scorched' in re.sub(r'\s*\n\s*', ' ', o[O_OUTGAS]),
                            original_asbestos='this == ModBlocks.ore_asbestos || this == ModBlocks.ore_gneiss_asbestos' in o[O_OUTGAS],
                            neo_radon=bool(re.search(r'ORE_GNEISS_URANIUM\.get\(\)\s*\|\|\s*this\s*==\s*NtmBlocks\.ORE_GNEISS_URANIUM_SCORCHED\.get\(\)', n_outgas)) and 'GAS_RADON' in n_outgas,
                            neo_asbestos=bool(re.search(r'this == NtmBlocks\.ORE_GNEISS_ASBESTOS\.get\(\)', n_outgas)) and 'GAS_ASBESTOS' in n_outgas),
         dict(original_radon=True, original_asbestos=True, neo_radon=True, neo_asbestos=True))
    # 4k. Recipes: the five schist smelting rows (SmeltingRecipes.java:54-60: iron, gold, copper, lithium, schrabidium; the uranium rows are older), the acidizer rows (CrystallizerRecipes.java:62-63,72,80,86,105),
    # the centrifuge rows (CentrifugeRecipes.java:66-77,108-113 with the ore dictionary members), the shredder rows (ShredderRecipes.java:176) and the gas shale container (FluidContainerRegistry.java:45).
    def recipe(name): return generated_json(GENERATED_ROOT+f'data/hbmsntm/recipe/{name}.json') or {}
    smelt_item = {'Items.iron_ingot': 'minecraft:iron_ingot', 'Items.gold_ingot': 'minecraft:gold_ingot', 'ModItems.ingot_copper': 'minecraft:copper_ingot', 'ModItems.lithium': 'hbmsntm:lithium', 'ModItems.ingot_schrabidium': 'hbmsntm:ingot_schrabidium'}
    o_smelt = {m[0]: m[1] for m in re.findall(r'GameRegistry\.addSmelting\(Item\.getItemFromBlock\(ModBlocks\.(ore_gneiss_(?:iron|gold|copper|lithium|schrabidium))\), new ItemStack\(([\w.]+)\), [\d.]+F?\)', o[O_SMELTING])}
    smelting = {}
    for name in RECIPE_NAMES:
        r = recipe(name)
        ore = r.get('ingredient', {}).get('item', '').replace('hbmsntm:', '')
        smelting[ore] = dict(recipe=name, result=r.get('result', {}).get('id'), experience=r.get('experience'), type=r.get('type'))
    fact('smelting_rows', dict(original={k: smelt_item.get(v, v) for k, v in o_smelt.items()}, neo=smelting), None,
         ok=len(o_smelt) == EXPECTED['smelting_rows'] and sorted(smelting) == sorted(o_smelt) and all(smelting[k]['result'] == smelt_item.get(o_smelt[k]) and smelting[k]['type'] == 'minecraft:smelting' for k in o_smelt))
    n_shred, n_cryst, n_cent, n_fluid = code(SHREDDER_RECIPES), code(CRYSTALLIZER_RECIPES), code(CENTRIFUGE_RECIPES), code(FLUID_CONTAINERS)
    o_cent = o[O_CENTRIFUGE]
    SHRED_DEPTH = (('ORE_DEPTH_BORAX', 'POWDER_BORAX'), ('ORE_DEPTH_ZIRCONIUM', 'POWDER_ZIRCONIUM'), ('ORE_DEPTH_NETHER_NEODYMIUM', 'POWDER_NEODYMIUM'))
    fact('processing_rows', dict(original=dict(shred_gneiss='setRecipe(ModBlocks.stone_gneiss, new ItemStack(ModItems.powder_lithium_tiny, 1))' in o[O_SHREDDER], cryst_gneiss='ComparableStack(ModBlocks.stone_gneiss)' in o[O_CRYSTALLIZER] and 'new CrystallizerRecipe(ModItems.powder_lithium, utilityTime).prod(0.25F)' in o[O_CRYSTALLIZER],
                                       centrifuge_iron_gold_copper='recipes.put(new OreDictStack(IRON.ore())' in o_cent and 'recipes.put(new OreDictStack(GOLD.ore())' in o_cent and 'recipes.put(new OreDictStack(CU.ore())' in o_cent),
                                 neo=dict(shred_gneiss=bool(re.search(r'registerIfAbsent\(new ItemStack\(NtmBlocks\.STONE_GNEISS\.get\(\)\), new ItemStack\(NtmItems\.POWDER_LITHIUM_TINY\.get\(\), 1\)\)', n_shred)),
                                          shred_depth=[bool(re.search(r'registerIfAbsent\(new ItemStack\(NtmBlocks\.'+b+r'\.get\(\)\), new ItemStack\(NtmItems\.'+i+r'\.get\(\), 2\)\)', n_shred)) for b, i in SHRED_DEPTH],
                                          shred_gneiss_rare_absent='ORE_GNEISS_RARE' not in n_shred,
                                          cryst_gneiss=bool(re.search(r'ComparableStack\(NtmBlocks\.STONE_GNEISS\.get\(\), 1\), new FluidStack\(Fluids\.PEROXIDE, DEFAULT_ACID\), new ItemStack\(NtmItems\.POWDER_LITHIUM\.get\(\)\), 100, 0\.25F\)', n_cryst)),
                                          cryst_ores=[bool(re.search(r'single\(NtmBlocks\.'+b+r'\.get\(\), NtmItems\.'+i+r'\.get\(\), Fluids\.'+f+r'\)', n_cryst)) for b, i, f in (
                                              ('ORE_GNEISS_IRON', 'CRYSTAL_IRON', 'PEROXIDE'), ('ORE_GNEISS_GOLD', 'CRYSTAL_GOLD', 'PEROXIDE'), ('ORE_GNEISS_COPPER', 'CRYSTAL_COPPER', 'PEROXIDE'),
                                              ('ORE_GNEISS_RARE', 'CRYSTAL_RARE', 'SULFURIC_ACID'), ('ORE_GNEISS_LITHIUM', 'CRYSTAL_LITHIUM', 'SULFURIC_ACID'), ('ORE_DEPTH_CINNABAR', 'CRYSTAL_CINNABAR', 'PEROXIDE'))],
                                          cryst_rows_documented=(re.search(r'Goal 28B\), (\d+) rows\.', neo_text(CRYSTALLIZER_RECIPES)) or [None, None])[1],
                                          centrifuge=[bool(re.search(r'setRecipe\(NtmBlocks\.'+b+r'\.get\(\), stack\(NtmItems\.'+a+r'\.get\(\), 1\), stack\(NtmItems\.'+a+r'\.get\(\), 1\), stack\(NtmItems\.'+c+r'\.get\(\), 1\), stack\(Blocks\.STONE, 1\)\)', n_cent))
                                                      for b, a, c in (('ORE_GNEISS_IRON', 'POWDER_IRON', 'POWDER_IRON'), ('ORE_GNEISS_GOLD', 'POWDER_GOLD', 'POWDER_GOLD'), ('ORE_GNEISS_COPPER', 'POWDER_COPPER', 'POWDER_GOLD'))])), None,
         ok='setRecipe(ModBlocks.stone_gneiss, new ItemStack(ModItems.powder_lithium_tiny, 1))' in o[O_SHREDDER] and 'ComparableStack(ModBlocks.stone_gneiss)' in o[O_CRYSTALLIZER]
         and 'recipes.put(new OreDictStack(IRON.ore())' in o_cent and 'recipes.put(new OreDictStack(GOLD.ore())' in o_cent and 'recipes.put(new OreDictStack(CU.ore())' in o_cent
         and bool(re.search(r'registerIfAbsent\(new ItemStack\(NtmBlocks\.STONE_GNEISS\.get\(\)\), new ItemStack\(NtmItems\.POWDER_LITHIUM_TINY\.get\(\), 1\)\)', n_shred))
         and 'ShredderRecipes.setRecipe(ModBlocks.ore_rare, new ItemStack(ModItems.powder_desh_mix, 1));' in o[O_SHREDDER] and 'ORE_GNEISS_RARE' not in n_shred
         and all(bool(re.search(r'registerIfAbsent\(new ItemStack\(NtmBlocks\.'+b+r'\.get\(\)\), new ItemStack\(NtmItems\.'+i+r'\.get\(\), 2\)\)', n_shred)) for b, i in SHRED_DEPTH)
         and '.ore(ore_cinnebar, ore_depth_cinnebar)' in o[O_OREDICT] and '.ore(ore_depth_borax)' in o[O_OREDICT] and '.ore(ore_depth_zirconium)' in o[O_OREDICT] and '.oreNether(ore_depth_nether_neodymium)' in o[O_OREDICT]
         and bool(re.search(r'OreDictStack\("oreCinnabar"\),\s*new CrystallizerRecipe\(ModItems\.crystal_cinnebar, baseTime\)\.prod\(0\.05F\)', o[O_CRYSTALLIZER]))
         and bool(re.search(r'single\(NtmBlocks\.ORE_DEPTH_CINNABAR\.get\(\), NtmItems\.CRYSTAL_CINNABAR\.get\(\), Fluids\.PEROXIDE\)', n_cryst))
         and bool(re.search(r'ComparableStack\(NtmBlocks\.STONE_GNEISS\.get\(\), 1\), new FluidStack\(Fluids\.PEROXIDE, DEFAULT_ACID\), new ItemStack\(NtmItems\.POWDER_LITHIUM\.get\(\)\), 100, 0\.25F\)', n_cryst))
         and all(bool(re.search(r'single\(NtmBlocks\.'+b+r'\.get\(\), NtmItems\.'+i+r'\.get\(\), Fluids\.'+f+r'\)', n_cryst)) for b, i, f in (
             ('ORE_GNEISS_IRON', 'CRYSTAL_IRON', 'PEROXIDE'), ('ORE_GNEISS_GOLD', 'CRYSTAL_GOLD', 'PEROXIDE'), ('ORE_GNEISS_COPPER', 'CRYSTAL_COPPER', 'PEROXIDE'), ('ORE_GNEISS_RARE', 'CRYSTAL_RARE', 'SULFURIC_ACID'),
             ('ORE_GNEISS_LITHIUM', 'CRYSTAL_LITHIUM', 'SULFURIC_ACID'), ('ORE_DEPTH_CINNABAR', 'CRYSTAL_CINNABAR', 'PEROXIDE')))
         and (re.search(r'Goal 28B\), (\d+) rows\.', neo_text(CRYSTALLIZER_RECIPES)) or [None, None])[1] == str(EXPECTED['crystallizer_rows'])
         and all(bool(re.search(r'setRecipe\(NtmBlocks\.'+b+r'\.get\(\), stack\(NtmItems\.'+a+r'\.get\(\), 1\), stack\(NtmItems\.'+a+r'\.get\(\), 1\), stack\(NtmItems\.'+c+r'\.get\(\), 1\), stack\(Blocks\.STONE, 1\)\)', n_cent))
                 for b, a, c in (('ORE_GNEISS_IRON', 'POWDER_IRON', 'POWDER_IRON'), ('ORE_GNEISS_GOLD', 'POWDER_GOLD', 'POWDER_GOLD'), ('ORE_GNEISS_COPPER', 'POWDER_COPPER', 'POWDER_GOLD'))))
    fact('gas_shale_container', dict(original='new FluidContainer(new ItemStack(ModBlocks.ore_gneiss_gas), null, Fluids.PETROLEUM, GeneralConfig.enable528 ? 50 : 250)' in o[O_FLUIDCONTAINERS],
                                     neo=bool(re.search(r'new FluidContainer\(new ItemStack\(NtmBlocks\.ORE_GNEISS_GAS\.get\(\)\), ItemStack\.EMPTY, Fluids\.PETROLEUM, NtmConfig\.enable528\(\) \? 50 : 250\)', n_fluid))),
         dict(original=True, neo=True))
    n_tabs = code(CREATIVE_TABS)
    fact('creative_tab', {n: bool(re.search(r'output\.accept\(NtmBlocks\.'+n.upper()+r'\);', n_tabs)) for n in BLOCK_NAMES}, {n: True for n in BLOCK_NAMES})
    fact('client_isolation', dict(client_references_in_common_classes=sorted(p for p in (SCHIST_FEATURE, DEPTH_FEATURE, DEPTH_CONFIGURATION, LAYER_FEATURE, LAYER_CONFIGURATION, RARITY_PLACEMENT, DEPTH_BLOCK, OUTGAS_BLOCK)
                                                                          if (ROOT/p).is_file() and re.search(r'net\.minecraft\.client|com\.hbm\.render\.|mezz\.jei', code(p)))), dict(client_references_in_common_classes=[]))
    facts['original_references'] = original_refs
    need(not bad, 'overworld-worldgen facts differ from the original or the handoff figures (or the NEO source / generated file is missing or its text differs): '+', '.join(
        f'{k}={json.dumps(facts[k], ensure_ascii=False, default=str)[:240]}' for k in bad))
    # The materials/reachability record (the main agent's; pending until written): it must say which items and rows are reachable and which sources are new.
    ledger = read(ROOT/LEDGER) if (ROOT/LEDGER).is_file() else None
    if need(ledger is not None, 'record missing: '+LEDGER):
        need(str(ledger.get('goal')) == '28B', f'{LEDGER} is not the Goal 28B ledger')

    # 5. Resources: the byte imports (original worktree file and stored blob at 4f5924e2b), against migration/goal28b-resource-ownership.json.
    ownership = read(ROOT/RESOURCE_OWNERSHIP) if (ROOT/RESOURCE_OWNERSHIP).is_file() else None

    def original_texture(target):
        """The original path of an imported NEO texture: block/x.png <- textures/blocks/x.png; the original names cinnabar "cinnebar" (ore_depth_cinnebar.png)."""
        rel = target[len(TEXTURE_ROOT):]
        if rel.startswith('item/'): return O_RES+'textures/items/'+rel[len('item/'):]
        if rel.startswith('block/'): return O_RES+'textures/blocks/'+rel[len('block/'):].replace('cinnabar', 'cinnebar')
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
    need(not [t for t in imported_facts.values() if t['replaced']], 'an imported texture replaces a start file: '+str(sorted(t for t, v in imported_facts.items() if v['replaced'])))
    if need(ownership is not None, 'record missing: '+RESOURCE_OWNERSHIP):
        entries = {a.get('target_path'): a for a in ownership.get('imported_assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == imported, f'{RESOURCE_OWNERSHIP} imported_assets are not the {len(imported)} imported textures at {SOURCE_HEAD[:8]}: {sorted(set(entries) ^ imported)[:4]}')
        for target, entry in entries.items():
            if target in imported_facts:
                need(entry.get('source_path') == imported_facts[target]['original_path'] and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('size') == (ROOT/target).stat().st_size,
                     f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original: {target}')

    # 6. features.json: no new group (world-generation exists since Goal28A); every group keeps reviewed_source_commit (the original did not move) and its status; only materials, centrifuge, crystallization,
    # shredder, fluid-container-transfer and world-generation may change notes / target_paths / target_watch (the handoff list).
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit 4f5924e2b'
    assert NOTES_MAY_CHANGE <= set(start_features), 'The start mapping does not hold the groups the handoff allows to change'
    may_change = lambda i: i in NOTES_MAY_CHANGE
    need(set(by_id) == set(start_features), 'features.json group ids are not the start ids: '+str(sorted(set(by_id) ^ set(start_features))))
    group_world = by_id.get(NEW_FEATURE)
    if need(group_world is not None, 'migration/features.json lacks the group '+NEW_FEATURE):
        need(group_world.get('status') == 'partial-unverified' and group_world.get('reviewed_source_commit') == SOURCE_HEAD, f'features.json group {NEW_FEATURE} is not partial-unverified at {SOURCE_HEAD[:8]}')
        unlisted = [p for p in O_SOURCES if not p.startswith(O_RES) and not any(feature_matches(f, 'source', p) for f in features)]
        need(not unlisted, f'features.json lists these original sources in no group (source_paths / source_watch): {unlisted}')
        mapped_java = [p for p in NEW_JAVA + [pp for pp in (OUTGAS_BLOCK, COMMON_CONFIG, HEATER_OILBURNER_BE) if pp in changes] if p != WORLDGEN_TESTS and not any(feature_matches(f, 'target', p) for f in features)]
        need(not mapped_java, f'features.json maps these new / changed Java paths in no group (target_paths / target_watch): {mapped_java[:4]}')
    absent = sorted({p for f in features for p in f.get('source_paths', []) if not (SOURCE/p).is_file()})
    need(not absent, f'features.json source_paths missing in the original: {absent[:6]}')
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    need(all(may_change(i) for i in notes_changed), 'features.json groups whose notes changed beyond materials / centrifuge / crystallization / shredder / fluid-container-transfer / world-generation: '+str([i for i in notes_changed if not may_change(i)]))
    paths_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('target_paths') != start_features[i].get('target_paths'))
    need(all(may_change(i) for i in paths_changed), 'features.json groups whose target_paths changed beyond the allowed groups: '+str([i for i in paths_changed if not may_change(i)]))
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    # world-generation (this batch's group) may also append to its evidence and acceptance lists; every other field of every group stays as it was.
    free = lambda i: ('notes', 'target_watch', 'target_paths', 'reviewed_source_commit', 'source_paths', 'source_watch') + (('evidence', 'acceptance') if i == 'world-generation' else ())
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in free(i)} !=
                          {k: v for k, v in start_features[i].items() if k not in free(i)})
    appended_only = all(by_id['world-generation'].get(k, [])[:len(start_features['world-generation'].get(k, []))] == start_features['world-generation'].get(k, [])
                        for k in ('evidence', 'acceptance'))
    need(not shrunk and not other_fields and appended_only, f'features.json previous groups lost target_watch entries {shrunk} or changed other fields {other_fields}'
         + ('' if appended_only else ' (world-generation evidence / acceptance changed other than by appending)'))
    watch_grown = sorted(i for i, f in by_id.items() if i in start_features and set(f.get('target_watch', [])) - set(start_features[i].get('target_watch', [])))
    need(all(may_change(i) for i in watch_grown), 'features.json groups whose target_watch grew beyond the allowed groups: '+str([i for i in watch_grown if not may_change(i)]))
    source_changed = sorted(i for i, f in by_id.items() if i in start_features and (f.get('source_paths') != start_features[i].get('source_paths') or f.get('source_watch') != start_features[i].get('source_watch')))
    need(all(may_change(i) for i in source_changed), 'features.json groups whose source_paths / source_watch changed beyond the allowed groups: '+str([i for i in source_changed if not may_change(i)]))
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped; the main agent adds target_paths / target_watch to world-generation): '+str(unmapped[:6]))

    # 7. Language and the generated tree: 40 new keys (the 22 block names and trait.tile.depth upstream, the 17 worldgen config keys local); nothing changed or removed; the stamp must be current, the
    # generated additions the overworld worldgen set.
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
    need(len(KEYS) == EXPECTED['language_added'], f'expected new language keys: {len(KEYS)}, the handoff lists {EXPECTED["language_added"]}')
    need(en_delta == expected_en, 'generated en_us.json delta is not the 40 new keys: '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_zh, 'zh_cn.json delta is not the 40 new keys: '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_map, 'zh_cn-map.json delta is not the 40 new entries: '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal28a totals'
    delta_net = len(KEYS) - len(REMOVED_KEYS)
    need(len(en_now) == totals['en_us'] + delta_net and len(zh_now) == totals['zh_cn'] + delta_net and len(map_now) == totals['zh_cn_map'] + delta_net,
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal28a totals {totals} + {delta_net}')
    map_kinds, start_kinds = dict(Counter(e.get('kind') for e in map_now.values())), dict(Counter(e.get('kind') for e in map_start.values()))
    kinds_added = Counter((map_now.get(k) or {}).get('kind') for k in KEYS)
    expected_kinds = {k: start_kinds.get(k, 0) + kinds_added.get(k, 0) for k in set(start_kinds) | set(kinds_added)}
    expected_kinds = {k: v for k, v in expected_kinds.items() if v}
    need(start_kinds == totals['zh_cn_map_by_kind'] and map_kinds == expected_kinds and map_kinds.get('deferred') == EXPECTED['deferred_entries'],
         f'mapping kinds are {map_kinds}, expected the goal28a kinds {totals["zh_cn_map_by_kind"]} adjusted by the added keys {expected_kinds} (deferred {EXPECTED["deferred_entries"]} unchanged)')
    need(dict(kinds_added) == {'upstream': UPSTREAM_ADDED, 'local': LOCAL_ADDED}, f'new mapping entries are {dict(kinds_added)}, expected {UPSTREAM_ADDED} upstream (the 22 block names and trait.tile.depth) and {LOCAL_ADDED} local (the worldgen config keys)')
    need(all((map_now.get(k) or {}).get('kind') == 'upstream' for k in LANG_SOURCE), 'mapping entries of the upstream keys are not kind upstream: '+str([k for k in LANG_SOURCE if (map_now.get(k) or {}).get('kind') != 'upstream']))
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if not (ROOT/'src/generated/resources'/p).is_file() or normalized_sha(ROOT/'src/generated/resources'/p) != h)
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
    changed_allowed = {EN_ENTRY, MALACHITE_LOOT[len(GENERATED_ROOT):]} | set(tags_modified)
    need({EN_ENTRY, PICKAXE_TAG[len(GENERATED_ROOT):], MALACHITE_LOOT[len(GENERATED_ROOT):]} <= set(generated_changed) and set(generated_changed) <= changed_allowed,
         f'Generated resources changed since the start are not en_us.json, the malachite loot table and the tag files that gained the blocks (pickaxe.json required): {generated_changed[:8]}')
    world_added = [p for p in generated_added if GENERATED_ADDED.fullmatch(GENERATED_ROOT+p)]
    need(world_added == generated_added, f'Generated additions other than the overworld worldgen, blockstate, model, loot table and recipe set: {sorted(set(generated_added) - set(world_added))[:6]}')
    counts_added = dict(blockstates=len([p for p in generated_added if '/blockstates/' in p]), block_models=len([p for p in generated_added if '/models/block/' in p]), item_models=len([p for p in generated_added if '/models/item/' in p]),
                        loot_tables=len([p for p in generated_added if '/loot_table/' in p]), recipes=len([p for p in generated_added if p.startswith('data/hbmsntm/recipe/')]),
                        advancements=len([p for p in generated_added if '/advancement/' in p]), configured_features=len([p for p in generated_added if '/configured_feature/' in p]),
                        placed_features=len([p for p in generated_added if '/placed_feature/' in p]), biome_modifiers=len([p for p in generated_added if '/biome_modifier/' in p]))
    need(counts_added == GENERATED_COUNTS, f'generated additions are {counts_added}, the handoff expects {GENERATED_COUNTS}')
    need(sorted(GENERATED_ROOT+p for p in generated_added) == sorted(set(REQUIRED_GENERATED) | {GENERATED_ROOT+p for p in generated_added if '/advancement/' in p}),
         'generated additions differ from the expected set: extra %s, missing %s' % (sorted({GENERATED_ROOT+p for p in generated_added} - set(REQUIRED_GENERATED) - {GENERATED_ROOT+p for p in generated_added if '/advancement/' in p})[:6],
                                                                                    sorted(set(REQUIRED_GENERATED) - {GENERATED_ROOT+p for p in generated_added})[:6]))
    advancements = {n: [p for p in generated_added if re.fullmatch(r'data/hbmsntm/advancement/recipes/[a-z]+/'+n+'\\.json', p)] for n in RECIPE_NAMES}
    need(all(len(v) == 1 for v in advancements.values()), 'generated recipe advancements: exactly one per recipe expected: '+str(advancements))
    for path in (v[0] for v in advancements.values() if v):
        adv = read(ROOT/(GENERATED_ROOT+path))
        need(adv.get('rewards') == {'recipes': ['hbmsntm:'+Path(path).stem]}, f'{path} does not reward its own recipe')
    need(len(stamp['generated']) == prior_receipt['generated_resource_count'] + len(generated_added), f'generated resource count {len(stamp["generated"])} is not the goal28a count {prior_receipt["generated_resource_count"]} + {len(generated_added)}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted([STAMP] + [GENERATED_ROOT+p for p in generated_added] + [GENERATED_ROOT+p for p in generated_changed])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, the stamp additions and the stamp changes: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))

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
    need(gametest_added == worldgen_annotations, f'GameTest sources grew by {gametest_added} tests, OverworldWorldgenGameTests holds {worldgen_annotations} (another GameTest class changed its test count, e.g. SmokeTestSupport?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in worldgen_test_names), 'GameTest log lacks "[hbm-28b] <name> passed" for: '+str([n for n in worldgen_test_names if (GAMETEST_MARKER % n) not in text]))
            worldgen_lines = [l.split('[hbm-28b] ', 1)[1].strip() for l in text.splitlines() if '[hbm-28b] ' in l and ' passed' not in l.split('[hbm-28b] ', 1)[1]]
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries, audit_comparison = {}, {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal28b/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad_findings = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad_findings and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad_findings))
        # This batch adds language keys and resources, so the info / review counts may differ from the previous receipt: recorded, not required equal.
        audit_comparison[key] = dict(previous=prior_receipt['audits'][key], now=audit['summary'], equal=audit['summary'] == prior_receipt['audits'][key])
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal28b/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if name == 'production-vs-start.diff':
            if (OUT/name).is_file() and (OUT/name).stat().st_size > 0: evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)  # judged below
            continue
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal28b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    named = list(START_EVIDENCE) + list(REVIEW_EVIDENCE)
    named += sorted(p.name for p in OUT.glob('handoff-*.md') if p.name not in named) + sorted(p.name for p in OUT.glob('*-report.md') if p.name not in named)
    for name in named:
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal28b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/FAIL_SET_DIFF).is_file(): evidence[(OUT/FAIL_SET_DIFF).relative_to(ROOT).as_posix()] = sha(OUT/FAIL_SET_DIFF)
    # The casting regressions (goal27a_casting_regression_run.py, unchanged wrapper): one record per suite in the final rerun's own directory; its transcript is hashed with it.
    casting = {}
    for suite in CASTING_SUITES:
        rec_path = CASTING_DIR/f'{suite}-compat.json'
        if not need(rec_path.is_file(), f'evidence missing: build/migration/goal28b/final/castingsuites/{suite}-compat.json (goal27a_casting_regression_run.py {suite}, redirected into final/ by run_final.py)'): continue
        rec = read(rec_path)
        transcript = ROOT/rec['transcript'] if rec.get('transcript') else None
        casting[suite] = dict(record=rec_path.relative_to(ROOT).as_posix(), exit=rec.get('exit'), mode=rec.get('mode'), blockers=rec.get('blockers'), stages=rec.get('stages'),
                              javac_errors_by_attribution=rec.get('javac_errors_by_attribution'), transcript=rec.get('transcript'))
        evidence[rec_path.relative_to(ROOT).as_posix()] = sha(rec_path)
        if need(transcript is not None and transcript.is_file(), f'{rec_path.name} names no existing transcript'): evidence[transcript.relative_to(ROOT).as_posix()] = sha(transcript)
    attribution = None
    if need((OUT/CASTING_ATTRIBUTION).is_file(), 'evidence missing: build/migration/goal28b/'+CASTING_ATTRIBUTION+' (casting_attribution.py, after the final rerun)'):
        att = read(OUT/CASTING_ATTRIBUTION)
        problems = []
        if att.get('mode') != 'compare' or att.get('missing_inputs'): problems.append(f'mode {att.get("mode")!r}, missing inputs {att.get("missing_inputs")}')
        if att.get('baseline_sha256') != sha(BASELINE) or att.get('tool_sha256') != sha(OUT/'casting_attribution.py'): problems.append('written by another baseline or another version of casting_attribution.py')
        if att.get('old_dir') != (GOAL28A_OUT/'final/castingsuites').relative_to(ROOT).as_posix() or att.get('new_dir') != CASTING_DIR.relative_to(ROOT).as_posix(): problems.append(f'compares {att.get("old_dir")} with {att.get("new_dir")}')
        if sorted(att.get('suites', {})) != sorted(CASTING_SUITES): problems.append('suites '+str(sorted(att.get('suites', {}))))
        for suite, entry in att.get('suites', {}).items():
            for side in ('old', 'new'):
                s = entry.get(side) or {}
                if not s.get('parse_matches_record'): problems.append(f'{suite} {side}: the parsed javac errors do not match the record')
                if side == 'new' and suite in casting and s.get('record_sha256') != sha(ROOT/casting[suite]['record']): problems.append(f'{suite}: the new record changed after the attribution')
            for e in entry.get('new_errors', []) + entry.get('moved', []):
                file = e.get('at', '').rsplit(':', 1)[0] if 'at' in e else (e.get('identity') or {}).get('file', '')
                if e.get('attribution') == 'unattributed': problems.append(f'{suite}: unattributed error {e.get("at") or e.get("identity")}')
                elif e.get('attribution') == '28B change' and file not in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed to a 28B change but the file did not change')
                elif e.get('attribution') == 'not 28B' and file in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed "not 28B" but the file changed')
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
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal28b/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files and edited GameTests against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    diffed_modified = [p for p in modified_java + gametest_edit_files if p in changes]
    listed_in_diff = NEW_JAVA + diffed_modified
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal28b/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in diffed_modified) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(p in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([p for p in listed_in_diff if p not in diff_text]))
    final = None
    # The suites of the goal28a final run plus the Goal28B verifier (the two casting regressions are in the goal28a set and run unchanged, redirected into final/; verify_goal28a_worldgen.py is an old suite now).
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal28a final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal28B suite is already in the goal28a final run'
    assert OLD_SUITE_28A in reference_suites, 'The goal28a final run does not hold the Goal28A verifier: '+OLD_SUITE_28A
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal28b/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal28a final set + the Goal28B verifier: '+str(sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal28b/'+VERIFY_REPORT+' (tools/migration/verify_goal28b_worldgen.py report; run it with --gametest-log and --jar after the final build)'):
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
        verifier_references = sorted(set(re.findall(r'(?:HbmWorldGen|DungeonToolbox|WorldConfig|MainRegistry|ModBlocks|SchistStratum|OreLayer3D|DepthDeposit|BlockDepth|BlockDepthOre|BlockCluster|BlockOre|BlockResourceStone|'
                                                    r'BlockOutgas|SmeltingRecipes|OreDictManager|ShredderRecipes|CrystallizerRecipes|CentrifugeRecipes|FluidContainerRegistry|ContainerOilburner|ModItems)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # The compare: the original did not move since the 28A observation point, so ONE compare, against review-4f5924e2b9e1.json (the snapshot is not rewritten). Original 0/0/0. The target set is this
    # batch's own compare-inventory paths (added = absent from the snapshot, modified = present) plus any residual between the snapshot and the start (computed from the snapshot's raw hashes; expected
    # empty: the 28A self-compare was 0/0/0 on the tree this batch starts from).
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
    snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'], snapshot_sha256_at_start=base['snapshot']['sha256'],
                    residual_modified=residual_modified, residual_added=residual_added, residual_removed=residual_removed)
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal28b/'+COMPARE+' (compare against '+SNAPSHOT+': original 0/0/0, target set of %d paths = this batch\'s %d compare-inventory paths + %d residual)' % (
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
        need(len(cmp['features']) == len(features) and set(states) <= {'no-observed-file-change', 'target-changed'} and any(f.get('id') == NEW_FEATURE and f.get('state') == 'target-changed' for f in cmp['features']),
             f'{COMPARE} feature states are {dict(states)}, expected only no-observed-file-change / target-changed over {len(features)} groups, with {NEW_FEATURE} target-changed')
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states), target_listed=len(listed_added) + len(listed_modified),
                       target_added=len(listed_added), target_modified=len(listed_modified), own_paths=len(own_target), residual=len(set(residual_modified) | set(residual_added)),
                       changed_groups=sorted(f['id'] for f in cmp['features'] if f.get('state') == 'target-changed'))
        evidence[compare['path']] = compare['sha256']

    # 9. JAR: build/libs is what gets packaged; delta against the previous package (goal28a), every entry owned by goal28b or a recompile.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the goal28a package (run the final build)')
    if True:  # --check also runs the delta code (against the current build/libs, which is still the goal28a package until the final build)
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
            need(en_jar == expected_en and zh_jar == expected_zh, 'JAR en_us.json / zh_cn.json differ from the goal28a package by something other than the Goal28B delta: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
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
        need(not unowned, 'JAR entry without an owner (only classes of the owner-table Java sources and the edited older GameTests, the generated additions / changes (blockstates, models, loot tables, recipes, '
             'worldgen features, biome modifiers, en_us.json, the pickaxe tag, the malachite loot table), zh_cn.json, the imported textures and META-INF/MANIFEST.MF are owned): '+str(unowned[:10]))
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in production_java if p in changes]
        allowed_classes = set(changed_java)
        need(set(class_owners) <= allowed_classes and set(changed_java) <= set(class_owners),
             'Changed Java sources and goal28b JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners))) + '; unexpected: '+str(sorted(set(class_owners) - allowed_classes)))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
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
                   generated_added_counts=counts_added, imported_textures=sorted(imported), start_drift=sorted(drift_report), repinned_since_goal28a_start=sorted(repinned),
                   language_delta=dict(en=en_delta, zh=zh_delta, map=map_delta), language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, line_endings=line_endings, content_rules=content_rules, gametest_edits={p: dict(added=e['added'], removed=e['removed'], rule_holds=e['rule_holds']) for p, e in gametest_edits.items()},
                   overworld_worldgen={k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v, default=str)) < 200 else f'<{len(v)} items>') for k, v in facts.items()}, overworld_worldgen_facts_bad=bad,
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_worldgen_tests=worldgen_test_names, final_suites_expected=final_expected,
                   audit_comparison=audit_comparison,
                   casting_regressions={s: dict(exit=c['exit'], mode=c['mode'], blockers=len(c['blockers'] or []), javac_errors_by_attribution=c['javac_errors_by_attribution']) for s, c in casting.items()},
                   casting_attribution=opt(attribution, 'summary'),
                   compare=opt(compare, 'counts'), compare_target_expected=len(expected_target), compare_added_expected=len(expected_added), compare_residual=dict(modified=residual_modified, added=residual_added, removed=residual_removed),
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
    overworld_worldgen = dict(neo=NEW_JAVA + modified_java, original=O_SOURCES, facts=facts, expected=EXPECTED, known_differences=KNOWN_DIFFERENCES, original_references=original_refs,
                              language_keys=language_keys, local_language_keys=local_keys, imported_resources=imported_facts, resource_ownership_record=RESOURCE_OWNERSHIP, reachability_record=LEDGER,
                              worldgen_lines_from_gametest_log=worldgen_lines,
                              note=f'Overworld ore generation: a worldgen config group of {EXPECTED["config_values"]} more keys (the overworldOres switch, the three layer switches, eight schist vein counts, four cluster counts and the '
                                   f'alexandrite "every nth chunk" rate) read by the existing hbmsntm:config_gated_add_features and hbmsntm:config_count types and the new hbmsntm:config_rarity placement; three new feature types '
                                   f'(the schist stratum, the depth deposit, the ore layer); {EXPECTED["configured_features"]} configured and {EXPECTED["placed_features"]} placed features (HbmWorldGen.java:98-139, 523-524: size, y range '
                                   f'min..min+variance-1, target stone_gneiss / stone ore replaceables; the depth deposits relative to the world bottom) and {EXPECTED["biome_modifiers"]} biome modifiers (the stratum and alexandrite '
                                   'ungated, the three layers behind their own switches, the schist ores, depth deposits and clusters behind overworldOres, the nether neodymium behind netherOres); 22 new blocks with the original '
                                   'drops (clusters one crystal, depth ores with the ore bonus and explosion decay, alexandrite capped at 2, malachite now drops chunks), depth rock destroyed only by depth-rock tools '
                                   '(destroy progress 1/50, otherwise unbreakable), schist uranium and asbestos outgassing; five schist smelting rows, the acidizer rows (53 -> 60), the centrifuge rows (80 -> 83), the shredder rows and '
                                   'the gas shale fluid container (250 mB petroleum, 50 with enable528; accepted by the oil burner heater). The geyser is not ported; the Sa326 and nether bedrock ores are not part of this batch '
                                   '(known_differences).')
    casting_record = dict(attribution=attribution, suites=casting, wrapper='tools/migration/goal27a_casting_regression_run.py (unchanged)', policy='tools/migration/goal27a_casting_compat.py (unchanged)',
                          note='The two frozen isolated casting regressions (verify_goal10a.py, verify_goal5a_casting.py) run through the unchanged Goal27A wrapper in the final rerun, redirected into '
                               'build/migration/goal28b/final/castingsuites; both already stopped at javac on the Goal26D to Goal28A trees, so none of their assertions is reached. casting-attribution.json '
                               'pairs the javac errors of the Goal28A final run with the Goal28B run and attributes every new or moved error by file to a Goal28B change or to "not 28B"; it is evidence about javac '
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
                                      note=f'The start tree is HEAD 66a00353 (the mod rename, = origin/master) with the UNCOMMITTED Goal28A delivery in the worktree ({len(base["modified_at_start"])} modified and '
                                           f'{len(base["untracked_at_start"])} untracked files, packaged as goal28a and never committed). migration/ is Git-ignored: freeze_start.py hashed every tracked and untracked non-ignored file '
                                           f'({tracked_count} baseline hashes, disk content) and every file under migration/ from disk ({len(base["migration_files"])} migration hashes) before the first 28B write and copied '
                                           f'{len(base["copied_scope"])} planned, modified and untracked files (baseline-files). build/libs at the start is the goal28a package {start_jar_sha[:8]}. The original did not move '
                                           '(4f5924e2b); paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, line_endings=line_endings, content_rules=content_rules, gametest_edits=gametest_edits, start_copies_supplement=[],
                   overworld_worldgen=overworld_worldgen, casting_attribution=casting_record,
                   language=dict(changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']), added=dict(en_us=en_delta['added'], zh_cn=zh_delta['added'], zh_cn_map=map_delta['added']),
                                 removed=dict(en_us=en_delta['removed'], zh_cn=zh_delta['removed'], zh_cn_map=map_delta['removed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds), jar_delta=language,
                                 start_sha256={p: base['files'][p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD, LANG_PROVIDER)},
                                 note='Goal28B adds 40 keys: the 22 block names and trait.tile.depth (upstream: tile.<block>.name, trait.tile.depth; ore_depth_cinnebar is NEO ore_depth_cinnabar) and the 17 '
                                      'hbmsntm.configuration.worldgen.* config keys (local: overworldOres, enableHematite / enableMalachite / enableBauxite, eight schist counts, four cluster counts, alexandriteSpawnRate); '
                                      'nothing is changed or removed; the 106 deferred entries are unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith(CARRIED_REPINS)},
                   repinned_since_goal28a_start={p: dict(goal28a_start_pin_sha256=h, goal28b_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok'), old_machine_suites_through=OLD_MACHINE_SUITES, casting_suites_through=['goal27a_casting_regression_run.py verify_goal10a',
                                                                                                                                                                            'goal27a_casting_regression_run.py verify_goal5a_casting']),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_worldgen_tests=worldgen_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per OverworldWorldgenGameTests test (names in new_worldgen_tests): what those '
                                      'tests assert about the decoded biome modifiers, the config gates and counts, the rarity placement, the stratum noise, the ore layers, the depth deposits, the blocks and their drops, '
                                      'depth rock destruction, outgassing, the recipes, the gas shale container and the oil burner slot; the older GameTests whose default table sizes changed are re-pinned (acidizer 60, centrifuge 83); '
                                      'no client (the models, the textures and the JEI screens are not drawn), no real player, no saved world, no world generation seen in a real world, no distribution sampling beyond the seeded test feature runs.'),
                   audits=audit_summaries, audit_comparison=audit_comparison, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['nether_end_worldgen (the Goal28A-only domain key; Goal28B adds overworld_worldgen)',
                                 'upstream / compare.old / snapshot.new (the original did not move this batch: no classification, no old compare, no new snapshot; the compare is against review-4f5924e2b9e1)',
                                 'small_fixes / ledger_edit (no small fix and no ledger edit since the goal28a package)',
                                 'casting_regressions (the Goal27A key; Goal28B carries casting_attribution as Goal27B to Goal28A did: the wrapper and the two suites are unchanged, only their javac errors are attributed)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun (the old isolated suites through the goal26c wrapper and the two casting regressions through the unchanged goal27a wrapper, whose javac '
                            'errors are attributed by casting_attribution.py), one compare against the review-4f5924e2b9e1 snapshot, and one static review. No in-game client test was run: no overworld world generation '
                            'was seen in a real world and no vein distribution was sampled; the block models and icons, the depth rock mining speed with a real tool, the JEI screens and the Chinese UI are not seen on screen; '
                            'no survival chain (finding, mining, smelting and processing the ores, radon from the schist uranium in a real world) was run; no dedicated server beyond GameTest; the Goal 28 acceptance '
                            'checklist GOAL28B-ACCEPTANCE.md is written, not run.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False, default=str))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal28b JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal28a package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
