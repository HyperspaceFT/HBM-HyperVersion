"""Package Goal28C (the third batch of Goal 28: recipes for creative-only content and the missing assembly machine rows: 24 assembler rows (the pumpjack, the fracking tower, the radar
and the large radar, the Leviathan turbine, the assembly machine, the chemical plant alternative, the three overdrive upgrades outside 528 mode, the naval mine, the empty fluid pack and
12 metal-plate rows in the alt. blueprint pool and the autoswitch.plates group), 15 crafting recipes (the press preheater, five detonators, the detonator cord, the charge, two mining
charge rows, the AP and HE mines, the rangefinder and the slag block pair), four item tags, the rangefinder item with its texture, four language keys and the RecipeCompletionGameTests),
cumulatively on the goal28b package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal28c.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal28c/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal28c/gametest-final.log (the GameTest dedicated-server
log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a --check run also proves the receipt code; only the real mode
writes it.

The frozen start is build/migration/goal28c/baseline.json: NEO HEAD 66a00353 (the mod rename, = origin/master) with the UNCOMMITTED Goal28A-28B delivery in the worktree (37 modified and
254 untracked files at the freeze; packaged as goal28a and goal28b, never committed). `files` (the tracked tree plus the untracked, non-ignored files) hashes the disk content of the
worktree, so the 28A-28B delivery is part of the start; `migration_files` hashes the Git-ignored migration/ directory from disk. This packager merges them (one start-hash map) and finds
changes under migration/ by walking the directory. freeze_start.py copied 309 planned, modified and untracked files into baseline-files/. build/libs at the start is the goal28b package
(d6f9af7c...a50e). The original did not move (4f5924e2b, the 28A observation point, unchanged in 28B): there is no upstream range to classify, no new snapshot and one compare, against
review-4f5924e2b9e1.json: original 0/0/0, the target set is this batch's own compare-inventory paths plus the residual between the snapshot and the start (computed from the snapshot's raw
hashes: the Goal28B paths, because the snapshot is the Goal28A tree).
Every change since the start is computed from the baseline hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified
production files are compared with their start bytes (baseline-files) and their +/- lines are reported. The JAR delta against the goal28b package is attributed per entry (goal28c or a
recompile difference); any entry without an owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys, assembler rows) are computed
here from the original and NEO sources and the GameTest log where they can be.

The receipts that hash records (goal21a..goal28b, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start (the acceptance checklists, GOAL21D.md,
GOAL22C.md, goal21d-static-review.md and the goal24a working notes, known from earlier batches, and migration/GOAL24B.md, whose one ledger sentence Goal28A replaced; the goal28b receipt
itself matches every hash it records); they are listed in the receipt as start drift and must still equal their Goal28C start hash; no receipt is rewritten and no other protected path may
drift. Every Goal 28B and earlier record, GOAL28D.md, GOAL28-THREAD-PROMPTS.md and SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL28.md is a shared record, GOAL28C.md
the task book and delivery record (hashed by the receipt).

It adds the recipe_completion facts (checked against the original and NEO source texts, the generated recipe, tag and model JSON and build/migration/goal28c/assembler-diff.json (start) / assembler-diff-after.json (settled), the
candidate table of tools/migration/goal28c_assembler_diff.py). The Goal28B-only receipt key overworld_worldgen is dropped and the receipt says so; so are the keys that belong to a moved
original (upstream, the old compare, the small fixes, the ledger edit). The two old casting regressions run unchanged through the goal27a wrapper in the final rerun and their javac errors
are attributed by casting_attribution.py (casting-attribution.json)."""
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
from package_goal28b import OUT as GOAL28B_OUT, BASELINE as GOAL28B_BASELINE, protected_paths as goal28b_protected_paths

OUT = ROOT/'build/migration/goal28c'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
VERIFIER_REPORT_MD = OUT/'verifier-report.md'
REFERENCE_PREVIOUS = GOAL28B_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL28B_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal28b/hbmsntm-198A-goal28b.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal28c'
RELEASE_NAME = 'hbmsntm-198A-goal28c.jar'
OWNER = 'goal28c'
PREVIOUS_OWNER = 'goal28b'
# The original did not move this batch: SOURCE_HEAD is the 28A observation point (unchanged in 28B) and the head the goal28b receipt records.
SOURCE_HEAD = '4f5924e2b9e1e49cee61787674d2658acb3d559b'
START_PREFIX = '66a00353'
START_PARENT_PREFIX = 'c1f6f397'
UNTRACK_PREFIX = '66050453'
GOAL27_DELIVERY_PREFIX = 'adaf265c'
TASK_BOOK = 'migration/GOAL28C.md'
SNAPSHOT = 'migration/baselines/review-4f5924e2b9e1.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
SRC = 'src/main/java/'
J = SRC+'com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
TEXTURE_ROOT = RES+'assets/hbmsntm/textures/'
O_RES = RES+'assets/hbm/'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a', 'goal26b', 'goal26c', 'goal26d', 'goal27a', 'goal27b', 'goal27c', 'goal27d', 'goal28a'}

# Production (owner goal28c): no new production Java file; the GameTest class is new. The MODIFIED production sources are the handoff owner table (the assembler table, the item
# registry, the creative tabs and four datagen providers); the optional ones and the edited older GameTests are listed separately.
RECIPE_TESTS = J+'gametest/RecipeCompletionGameTests.java'
NEW_JAVA = [RECIPE_TESTS]
MODIFIED_JAVA = [J+p+'.java' for p in (
    'inventory/recipes/AssemblyMachineRecipes', 'items/NtmItems', 'inventory/NtmCreativeTabs', 'datagen/NtmRecipeProvider', 'datagen/NtmItemTagProvider', 'datagen/NtmItemModelProvider',
    'datagen/NtmLanguageProvider')]
(ASSEMBLER, NTM_ITEMS, CREATIVE_TABS, RECIPE_PROVIDER, ITEM_TAG_PROVIDER, ITEM_MODEL_PROVIDER, LANG_PROVIDER) = MODIFIED_JAVA
# Older GameTests the batch may edit by design (an expectation and its citation comment only, e.g. a recipe, row or item count): none is known before the run; verifier-report.md names
# them (EDITED_EXTRA is filled in main()). The rule for each: the @GameTest methods and annotations are the start's and every changed code line differs from a start line only in its
# integer literals.
EDITED_GAMETESTS = []
EDITED_EXTRA = []  # older GameTests that verifier-report.md names (filled in main())
# Optional (changed only when the batch needed it; reported): an additive GameTest helper.
OPTIONAL_JAVA = [J+p+'.java' for p in ('gametest/SmokeTestSupport',)]
OLDER_GAMETEST_DIR = J+'gametest/'
# Must stay byte-identical to the start (the handoff list), plus every other GameTest class, every block / block entity / menu class and every handler/jei class: see main().
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'inventory/recipes/loader/GenericRecipe', 'inventory/recipes/loader/GenericRecipes', 'items/machine/BlueprintFolderItem', 'blocks/NtmBlocks')]
UNCHANGED_DIRS = (J+'blocks/', J+'blockentity/', J+'inventory/menus/', J+'handler/jei/')
# Older tools that must equal their start bytes (handoff list); every file of the two frozen casting regression folders is added in main().
OLD_TOOLS_FROZEN = ['tools/migration/'+p for p in ('package_goal28b.py', 'verify_goal28b_worldgen.py', 'package_goal28a.py', 'verify_goal28a_worldgen.py', 'package_goal27d.py', 'verify_goal27d_molds.py',
                                                    'package_goal27c.py', 'verify_goal27c_foundry.py', 'package_goal27b.py', 'verify_goal27b_crucible_alloys.py', 'package_goal27a.py',
                                                    'verify_goal27a_material_system.py', 'goal27a_casting_regression_run.py', 'goal27a_casting_compat.py', 'goal27a_scrap_textures.py',
                                                    'goal27a_effect_icons.py', 'goal26c_oldsuite_run.py', 'goal26c_oldsuite_compat.py', 'verify_goal10a.py', 'verify_goal10a_resources.py',
                                                    'verify_goal5a_casting.py', 'verify_goal5a_casting_resources.py', 'goal10a_scrap_textures.py', 'goal10a_mutation_check.py')]
FROZEN_TOOL_DIRS = ('tools/migration/goal10a_regression/', 'tools/migration/goal5a_casting_regression/')
ASSEMBLER_DIFF_TOOL = 'tools/migration/goal28c_assembler_diff.py'
VERIFY_TOOL = 'tools/migration/verify_goal28c_recipes.py'
NEW_TOOLS = [ASSEMBLER_DIFF_TOOL, VERIFY_TOOL, 'tools/migration/package_goal28c.py']
TOOLS = NEW_TOOLS
ASSEMBLER_DIFF = 'assembler-diff.json'
ASSEMBLER_DIFF_AFTER = 'assembler-diff-after.json'
# The one imported texture (migration/goal28c-resource-ownership.json lists it): the original item icon textures/items/rangefinder.png.
TEXTURE_NAMES = ('rangefinder',)
TEXTURE_PATTERN = re.compile(re.escape(TEXTURE_ROOT)+r'item/(?:'+'|'.join(TEXTURE_NAMES)+r')\.png')
REQUIRED_TEXTURES = [TEXTURE_ROOT+'item/'+n+'.png' for n in TEXTURE_NAMES]
RESOURCE_OWNERSHIP = 'migration/goal28c-resource-ownership.json'
# The 24 assembler rows this batch registers (assembler-diff.json DECISIONS 'register', GOAL28C.md C1, the builder handoff A1-A11), in the order they are appended.
PLATE_ROWS = ('ass.plateiron', 'ass.plategold', 'ass.platetitanium', 'ass.platealu', 'ass.platesteel', 'ass.platelead', 'ass.platecopper', 'ass.plateschrab', 'ass.platecmb',
              'ass.plategunmetal', 'ass.platesaturnite', 'ass.platedura')
OVERDRIVE_ROWS = ('ass.overdrive1', 'ass.overdrive2', 'ass.overdrive3')
ASSEMBLER_ROWS = PLATE_ROWS + ('ass.assembler', 'ass.chemplantAlt', 'ass.pumpjack', 'ass.fracker', 'ass.radar', 'ass.radarlarge', 'ass.leviturbine') + OVERDRIVE_ROWS + ('ass.minenaval', 'ass.emptypackage')
NOT_REGISTERED_ROWS = {'ass.plateweaponsteel': 'NEO has no plate_weaponsteel (original AssemblyMachineRecipes.java:77)'}
PLATE_GROUP = 'autoswitch.plates'
# The 15 crafting recipes: NEO recipe id -> (original source, the original line's token, NEO result item). The slag pair is the original add1To9Pair (MineralRecipes.java:58).
CRAFTING = {
    'press_preheater': ('CM', 'new ItemStack(ModBlocks.press_preheater)', 'press_preheater'), 'detonator': ('CM', 'new ItemStack(ModItems.detonator, 1)', 'detonator'),
    'detonator_multi': ('CM', 'new ItemStack(ModItems.detonator_multi, 1)', 'detonator_multi'), 'detonator_laser': ('CM', 'new ItemStack(ModItems.detonator_laser, 1)', 'detonator_laser'),
    'detonator_deadman': ('CM', 'new ItemStack(ModItems.detonator_deadman, 1)', 'detonator_deadman'), 'detonator_de': ('CM', 'new ItemStack(ModItems.detonator_de, 1)', 'detonator_de'),
    'det_cord': ('CM', 'new ItemStack(ModBlocks.det_cord, 4)', 'det_cord'), 'det_charge': ('CM', 'new ItemStack(ModBlocks.det_charge, 1)', 'det_charge'),
    'det_miner': ('CM', 'new ItemStack(ModBlocks.det_miner, 4)', 'det_miner'), 'det_miner_steel': ('CM', 'new ItemStack(ModBlocks.det_miner, 12)', 'det_miner'),
    'mine_ap': ('WR', 'new ItemStack(ModBlocks.mine_ap, 4)', 'mine_ap'), 'mine_he': ('WR', 'new ItemStack(ModBlocks.mine_he, 1)', 'mine_he'),
    'rangefinder': ('TR', 'new ItemStack(ModItems.rangefinder, 1)', 'rangefinder'),
    'block_slag': ('MR', 'add1To9Pair(new ItemStack(ModBlocks.block_slag), new ItemStack(ModItems.ingot_raw, 9, MAT_SLAG.id))', 'block_slag'),
    'ingot_raw_slag': ('MR', 'add1To9Pair(new ItemStack(ModBlocks.block_slag), new ItemStack(ModItems.ingot_raw, 9, MAT_SLAG.id))', 'ingot_raw'),
}
RECIPE_NAMES = tuple(CRAFTING)
# Not registered (handoff C; one comment line each in the provider): their inputs have no NEO item.
CRAFTING_NOT_REGISTERED = {'det_nuke': ('CM', 'new ItemStack(ModBlocks.det_nuke, 1)', 'man_core'), 'mine_shrap': ('WR', 'new ItemStack(ModBlocks.mine_shrap, 1)', 'pellet_buckshot'),
                           'mine_fat': ('WR', 'new ItemStack(ModBlocks.mine_fat, 1)', 'ammo_standard')}
# The four new item tags: tag path -> (original dictionary token, OreDictManager line token, NEO members: NtmItems constants, or a full id such as minecraft:copper_ingot).
NEW_TAGS = {'ingots_resistant_alloy': ('ANY_RESISTANTALLOY', 'ANY_RESISTANTALLOY = new DictGroup("AnyResistantAlloy", TCALLOY, CDALLOY)', ('INGOT_TCALLOY', 'INGOT_CDALLOY')),
            'ingots_plastic_explosive': ('ANY_PLASTICEXPLOSIVE', '.ingot(ingot_semtex, ingot_c4)', ('INGOT_SEMTEX', 'INGOT_C4')),
            'ingots_bismoid_bronze': ('ANY_BISMOIDBRONZE', 'ANY_BISMOIDBRONZE = new DictGroup("AnyBismoidBronze", BBRONZE, ABRONZE)', ('INGOT_BISMUTH_BRONZE', 'INGOT_ARSENIC_BRONZE')),
            'ingots_copper': ('CU', 'public static final DictFrame CU = new DictFrame("Copper");', ('minecraft:copper_ingot', 'INGOT_COPPER'))}
ITEM_MODEL_NAMES = ('rangefinder',)
# Generated by runData: 15 crafting recipes with their advancements, the four item tags under data/ntm/tags/item/, the rangefinder item model; en_us.json and the stamp change.
GENERATED_ADDED = re.compile(re.escape(GENERATED_ROOT)+r'(?:assets/hbmsntm/models/item/(?:'+'|'.join(ITEM_MODEL_NAMES)+r')\.json|data/hbmsntm/recipe/(?:'+'|'.join(RECIPE_NAMES)+r')\.json|'
                             r'data/hbmsntm/advancement/recipes/[a-z]+/(?:'+'|'.join(RECIPE_NAMES)+r')\.json|data/ntm/tags/item/(?:'+'|'.join(NEW_TAGS)+r')\.json)')
GENERATED_COUNTS = dict(item_models=1, recipes=15, advancements=15, item_tags=4)
REQUIRED_GENERATED = sorted([GENERATED_ROOT+f'assets/hbmsntm/models/item/{n}.json' for n in ITEM_MODEL_NAMES] + [GENERATED_ROOT+f'data/hbmsntm/recipe/{n}.json' for n in RECIPE_NAMES]
                            + [GENERATED_ROOT+f'data/ntm/tags/item/{n}.json' for n in NEW_TAGS])
GENERATED_MODIFIED = [STAMP, EN]
# Language: 4 new keys, all upstream (the rangefinder, the two radars, which had no language entry in NEO, and the plate auto-switch group); nothing changed or removed.
UPSTREAM_KEYS = {'item.hbmsntm.rangefinder': 'item.rangefinder.name', 'block.hbmsntm.machine_radar': 'tile.machine_radar.name',
                 'block.hbmsntm.machine_radar_large': 'tile.machine_radar_large.name', 'autoswitch.plates': 'autoswitch.plates'}
LOCAL_KEYS = []
KEYS = sorted(list(UPSTREAM_KEYS) + LOCAL_KEYS)
REMOVED_KEYS = []
LANG_CHANGED = []
EN_CHANGED = ZH_CHANGED = LANG_CHANGED
LANG_SOURCE = UPSTREAM_KEYS
UPSTREAM_ADDED = 4
LOCAL_ADDED = 0
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal28c-* or GOAL28C-* record is hashed as well.
REPORTS = ['migration/GOAL28C.md', 'migration/GOAL28C-ACCEPTANCE.md', RESOURCE_OWNERSHIP, 'migration/goal28c-static-review.md', 'migration/goal28c-materials-review.json',
           'migration/goal28c-localization-review.json']
LEDGER = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal28c-[^/]+\.(json|md)|GOAL28C-[^/]+\.md)')
GOAL28_RECORD = 'migration/GOAL28.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', GOAL28_RECORD, LOCALIZATION_RECORD]
# Shared records the batch may leave untouched ("if touched" in the handoff; GOAL28D-ACCEPTANCE.md, the 28D master checklist, may also be created; RESOURCE-OWNERSHIP.md is a planned
# file of the freeze).
OPTIONAL_RECORDS = ['migration/GOAL28D-ACCEPTANCE.md', 'migration/RESOURCE-OWNERSHIP.md']
# The records of the other batches and the files no batch of this kind touches: no change is expected.
PLANNING_FROZEN = ['migration/SURVIVAL-PLAYABILITY.md', 'migration/GOAL28-THREAD-PROMPTS.md', 'migration/GOAL28D.md']
# Every Goal 28B and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 27, GOAL28A*, GOAL28B*, goal28a-*, goal28b-*): GOAL24B.md is a start-drift record pinned at its start hash like the others.
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-7]|28A|28B)(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-7]|28a|28b)(?!\d)[a-z]?-[^/]+)')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = (NEW_JAVA + MODIFIED_JAVA + REQUIRED_TEXTURES + REQUIRED_GENERATED + GENERATED_MODIFIED + [ZH_INPUT] + TOOLS + REPORTS
                    + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS])
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-28c] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the
# sessions of the batch. Every top-level handoff-*.md, *-report.md, builder-*.log, builder_*.log and verifier-*.log of OUT is indexed as well.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_head.txt', 'handoff-builder.md', 'handoff-verifier.md',
                  'handoff-packaging.md', 'handoff-reviewer.md', 'chain.sh', 'gw.sh', 'add_zh.py', 'write_ownership.py', 'make_diff.py', 'make_production_diff.py', ASSEMBLER_DIFF)
# Review files under OUT; each must exist and is indexed by the receipt. --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'casting_attribution.py', 'packaging-progress.md', 'packaging-report.md', 'verifier-report.md',
                   'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier-scope/scope-start.txt', 'verifier-scope/scope-end.txt', 'verify-final.out', 'compare.log', 'localization-final.log',
                   'resources-audit-final.log', 'packaged-resources-final.log', ASSEMBLER_DIFF_AFTER, 'production-builder.diff', 'add_zh.log')
CASTING_ATTRIBUTION = 'casting-attribution.json'
CASTING_DIR = OUT/'final/castingsuites'
CASTING_SUITES = ('verify_goal10a', 'verify_goal5a_casting')
FAIL_SET_DIFF = 'final/fail-set-diff.json'
COMPARE_EXITS = ('compare',)
GAMETEST_LOG = 'build/migration/goal28c/gametest-final.log'
NEW_SUITE = 'verify_goal28c_recipes.py --gametest-log build/migration/goal28c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
OLD_SUITE_28B = 'verify_goal28b_worldgen.py --gametest-log build/migration/goal28b/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# features.json: one new group recipe-completion; oil-extraction, materials and the product groups (PRODUCT_GROUPS: the groups of the machines and items this batch makes craftable; the
# handoff names them only as "product-group notes") may change notes / target_paths / target_watch; every group keeps reviewed_source_commit (the original did not move) and its status.
NEW_FEATURE = 'recipe-completion'
PRODUCT_GROUPS = {'basic-assembly', 'chemical-plant', 'industrial-turbine', 'press', 'blueprints', 'fluid-container-transfer', 'electrical-components', 'material-system', 'foundry-casting'}
NOTES_MAY_CHANGE = {'oil-extraction', 'materials', NEW_FEATURE} | PRODUCT_GROUPS
RADIATION_NOTE = 'Goal28C: no new radiation source. '
MELTDOWN_NOTE = 'Goal28C: no new meltdown path. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_AMR = ORIGINAL+'inventory/recipes/AssemblyMachineRecipes.java'
O_CM = ORIGINAL+'main/CraftingManager.java'
O_WR = ORIGINAL+'crafting/WeaponRecipes.java'
O_TR = ORIGINAL+'crafting/ToolRecipes.java'
O_MR = ORIGINAL+'crafting/MineralRecipes.java'
O_CIRCUIT = ORIGINAL+'items/machine/ItemCircuit.java'
O_OREDICT = ORIGINAL+'inventory/OreDictManager.java'
O_MATS = ORIGINAL+'inventory/material/Mats.java'
O_MODITEMS = ORIGINAL+'items/ModItems.java'
O_GENERIC = ORIGINAL+'inventory/recipes/loader/GenericRecipe.java'
O_LANG_EN = O_RES+'lang/en_US.lang'
O_LANG_ZH = O_RES+'lang/zh_CN.lang'
O_BY_KEY = {'CM': O_CM, 'WR': O_WR, 'TR': O_TR, 'MR': O_MR}
O_SOURCES = [O_AMR, O_CM, O_WR, O_TR, O_MR, O_CIRCUIT, O_OREDICT, O_MATS, O_MODITEMS, O_GENERIC, O_LANG_EN, O_LANG_ZH]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'no528': (O_AMR, 'boolean no528 = !GeneralConfig.enable528;'), 'auto_plate': (O_AMR, 'String autoPlate = "autoswitch.plates";'),
    'plate_iron': (O_AMR, 'new GenericRecipe("ass.plateiron")'), 'plate_weaponsteel': (O_AMR, 'new GenericRecipe("ass.plateweaponsteel")'), 'plate_dura': (O_AMR, 'new GenericRecipe("ass.platedura")'),
    'assembler': (O_AMR, 'new GenericRecipe("ass.assembler")'), 'chemplant_alt': (O_AMR, 'new GenericRecipe("ass.chemplantAlt")'), 'pumpjack': (O_AMR, 'new GenericRecipe("ass.pumpjack")'),
    'fracker': (O_AMR, 'new GenericRecipe("ass.fracker")'), 'radar': (O_AMR, 'new GenericRecipe("ass.radar")'), 'radar_large': (O_AMR, 'new GenericRecipe("ass.radarlarge")'),
    'leviturbine': (O_AMR, 'new GenericRecipe("ass.leviturbine")'), 'overdrive_gate': (O_AMR, 'if(no528) {'), 'overdrive1': (O_AMR, 'new GenericRecipe("ass.overdrive1")'),
    'overdrive3': (O_AMR, 'new GenericRecipe("ass.overdrive3")'), 'mine_naval': (O_AMR, 'new GenericRecipe("ass.minenaval")'), 'empty_package': (O_AMR, 'new GenericRecipe("ass.emptypackage")'),
    'pools528_noop': (O_GENERIC, 'public GenericRecipe setPools528('), 'detonator': (O_CM, 'new ItemStack(ModItems.detonator, 1)'), 'detonator_de': (O_CM, 'new ItemStack(ModItems.detonator_de, 1)'),
    'det_cord': (O_CM, 'new ItemStack(ModBlocks.det_cord, 4)'), 'det_nuke': (O_CM, 'new ItemStack(ModBlocks.det_nuke, 1)'), 'det_miner_steel': (O_CM, 'new ItemStack(ModBlocks.det_miner, 12)'),
    'press_preheater': (O_CM, 'new ItemStack(ModBlocks.press_preheater)'), 'mine_ap': (O_WR, 'new ItemStack(ModBlocks.mine_ap, 4)'), 'mine_shrap': (O_WR, 'new ItemStack(ModBlocks.mine_shrap, 1)'),
    'mine_he': (O_WR, 'new ItemStack(ModBlocks.mine_he, 1)'), 'mine_fat': (O_WR, 'new ItemStack(ModBlocks.mine_fat, 1)'), 'rangefinder_recipe': (O_TR, 'new ItemStack(ModItems.rangefinder, 1)'),
    'slag_pair': (O_MR, 'add1To9Pair(new ItemStack(ModBlocks.block_slag)'), 'slag_material': (O_MATS, 'NTMMaterial MAT_SLAG'), 'rangefinder_item': (O_MODITEMS, 'rangefinder = new ItemRangefinder()'),
    'circuit_enum': (O_CIRCUIT, 'public static enum EnumCircuitType'),'tag_resistant_alloy': (O_OREDICT, NEW_TAGS['ingots_resistant_alloy'][1]), 'tag_plastic_explosive': (O_OREDICT, NEW_TAGS['ingots_plastic_explosive'][1]),
    'tag_bismoid_bronze': (O_OREDICT, NEW_TAGS['ingots_bismoid_bronze'][1]), 'tag_copper': (O_OREDICT, NEW_TAGS['ingots_copper'][1]),
}
# Expected figures of the handoff and the task book (every value is also computed from the sources).
EXPECTED = dict(assembler_rows_start=58, assembler_rows_added=24, plate_rows=12, crafting_recipes=15, item_tags=4, imported_assets=1, language_added=4, language_changed=0, deferred_entries=106,
                en_total=3015, zh_total=2909, map_total=3015, original_assembler_rows=355)
KNOWN_DIFFERENCES = {
    'expensive_lists': 'the inputItemsEx (expensive mode) lists are not migrated: every one of them uses item_expensive, which NEO does not have (original ModItems.java:342); with enableExpensiveMode NEO uses the normal lists',
    'pools528': 'no row calls setPools528: the original ass.pumpjack and ass.fracker 528 pools (AssemblyMachineRecipes.java:301-308) are not migrated, like ass.crackingtower, since NEO has no 528 blueprint source in survival',
    'plate_inputs': 'IRON.ingot() and GOLD.ingot() are the c:ingots/iron and gold tags (the vanilla ingots, as NEO\'s press uses); CU.ingot() is the new ntm:ingots_copper (the vanilla copper ingot and NEO\'s own ingot_copper, which c:ingots/copper does not hold); the other plate rows take NEO\'s own ingots as plain items (they have no c:ingots tag)',
    'plate_weaponsteel': 'ass.plateweaponsteel (AssemblyMachineRecipes.java:77) is not registered: NEO has no plate_weaponsteel',
    'circuits': 'the original circuit meta items map to NEO\'s separate circuit items: BASIC -> circuit_integrated_board, ADVANCED -> circuit_military_grade_board, CAPACITOR -> circuit_capacitor, CAPACITOR_BOARD -> circuit_capacitor_board, BISMOID -> circuit_versatile_board (ItemCircuit.java:47-67, en_US.lang:2439-2459)',
    'dictionaries': 'ANY_RUBBER -> ntm:any_rubbers, ANY_HARDPLASTIC -> ntm:bars_hard_plastic, ANY_PLASTIC -> ntm:ingots_plastic, ANY_HIGHEXPLOSIVE -> ntm:balls_he (existing NEO tags); ANY_RESISTANTALLOY, ANY_PLASTICEXPLOSIVE, ANY_BISMOIDBRONZE and CU.ingot() are the four new ntm: item tags; ANY_SMOKELESS.dust() is cordite (NEO has no ballistite); STEEL.plateWelded() is the welded steel cast plate',
    'lava_bucket': 'the press preheater takes the lava bucket for the original Fluids.LAVA.getDict(1000) (CraftingManager.java:852); the vanilla bucket\'s crafting remainder returns the empty bucket',
    'not_registered_crafting': 'det_nuke (CraftingManager.java:522, man_core), mine_shrap (WeaponRecipes.java:298, pellet_buckshot) and mine_fat (WeaponRecipes.java:300, ammo_standard) are not registered: their inputs have no NEO item',
    'rangefinder': 'the rangefinder is a plain item (stack size 1, the original setMaxStackSize(1), ModItems.java:3388), a crafting material for the laser detonator only; the original ItemRangefinder ranging function is not migrated',
    'overdrive_reachability': 'the overdrive upgrades are registered outside 528 mode like the original (if(no528)); overdrive I needs saturnite (Goal28D), overdrive II/III need CFT and bismuth bronze ingots, which have no survival source yet',
    'deferred_rows': 'GOAL28 decision 5 rows (bombs, missiles, launch pads, satellites, PWR controller), ass.platemixed (Goal28D), ass.chipBismoid / ass.chipQuantum / ass.atomicClock (GOAL13B B4) and the follow-up candidates (ass.pistonsetstar, five capacitors, ass.alclad, ass.titaniumconstruction) stay unregistered (assembler-diff.json decisions)',
}

# 27A / 27B / 27C / 27D / 28A / 28B ones the receipt carries forward under a new heading.
CARRIED_REPINS = 'repinned_since_'


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal28c release directory: '+rel

def original_blob(path):
    """Bytes of a file in the original repository at the 28C commit (independent of its worktree)."""
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
    """The Goal28C start hash of a frozen path: the merged baseline hashes, or for a build/ record (Git-ignored, so the baseline does not list it) the hash the goal28b receipt
    records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal28b packager protected (built there, through the goal28a packager, from the Goal21A..Goal28A starts and receipts and the goal28b start), plus every path the
    goal28b receipt hashes (base previous_receipt_protected_paths), the paths the older receipts hash (goal21a..goal28a) and every release file of the frozen start (the goal28b package
    included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes, GOAL24B.md with the one ledger
    sentence Goal28A replaced; the GOAL25D / GOAL26D / GOAL27D acceptance checklists) are pinned at their Goal28C start hash instead of any receipt hash or any earlier start hash. One
    path never carries two hashes. Returns (protected, repinned): repinned maps a record to the pin the goal28b packager set (its Goal28B start hash) for the records whose pin changed
    between the starts."""
    goal28b_start = dict(read(GOAL28B_BASELINE))
    goal28b_start['files'] = merged_files(goal28b_start)
    out = dict(goal28b_protected_paths(goal28b_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal28b receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal28b_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    return out, repinned


def start_drift_report(base, repinned, goal28b_start):
    """{path: {receipts, start_sha256, goal28b_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal28b receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal28b receipt') or receipts.get('goal28a receipt') or receipts.get('goal27d receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif p == 'migration/GOAL24B.md':
            explanation = ('Goal28A replaced one ledger sentence of this record (plutonium powder and polonium-210 are reachable with enablePlutoniumNetherOre, default off; the goal28a receipt reported it as '
                           'ledger_edit but does not hash the file); the goal24b receipt hash is older than the start hash. Frozen at the Goal28C start hash (unchanged since the Goal28B start); this '
                           'batch must not change it and the goal24b receipt is not rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21..26 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal27d, goal28a and '
                           'goal28b receipts do not hash it. Frozen at the Goal28C start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the newest receipt that hashes it (the in-game acceptance results of Goal 25, 26 and 27 were recorded in the checklists once the packages existed); that '
                           'receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and no receipt is rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal28b_start_sha256=goal28b_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal28b_start_pin_sha256'] = repinned[p]
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
    return (f'Goal28C (the third batch of Goal 28, recipes for creative-only content and the missing assembly machine rows; original 4f5924e2b, unchanged since Goal28A): 24 assembly machine rows '
            f'(the pumpjack, the fracking tower, the radar and the large radar, the Leviathan turbine, the assembly machine, the chemical plant alternative row, the overdrive upgrades I-III outside '
            f'528 mode, the naval mine, the empty fluid pack and 12 metal-plate rows in the alt. blueprint pool and the autoswitch.plates group), 15 crafting recipes (the press preheater, the '
            f'detonator, multi, laser, dead man\'s and dead man\'s explosive detonators, the detonator cord, the charge, two mining charge rows, the AP and HE mines, the rangefinder and the slag '
            f'block 9:1 pair), four item tags (ntm:ingots_resistant_alloy, ntm:ingots_plastic_explosive, ntm:ingots_bismoid_bronze, ntm:ingots_copper), the rangefinder item with its texture, four language keys and '
            f'{tests} RecipeCompletionGameTests ({total_tests} GameTests in total). '
            f'Gameplay impact: the pumpjack, fracking tower, radar, large radar, Leviathan turbine, assembly machine, chemical plant (alternative row), overdrive upgrades, naval mine, empty fluid '
            f'pack and 12 metal-plate rows (alt. blueprint pool, auto-switch group) are now in the assembly machine; the press preheater, detonators (single, multi, laser, dead man\'s, dead man\'s '
            f'explosive), detonator cord, charges, mining charges, AP and HE mines, the rangefinder (crafting material only) and the slag block 9:1 pair are craftable; overdrive I needs saturnite '
            f'(28D), overdrive II/III need CFT ingots that have no survival source yet, and the dead man\'s detonators need the defuser, which has no recipe in NEO.')


def group(p, imported):
    if p in NEW_JAVA: return 'gametest-new'
    if p in EDITED_GAMETESTS or p in EDITED_EXTRA: return 'gametest-edit'
    if p in MODIFIED_JAVA or p in OPTIONAL_JAVA: return 'production'
    if p in imported: return 'production-resource-imported'
    if p == ZH_INPUT: return 'language'
    if p in GENERATED_MODIFIED or GENERATED_ADDED.fullmatch(p): return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p) or p == TASK_BOOK: return 'reports'
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records'
    return None


def owner_of(p):
    return OWNER


def generated_json(path):
    return read(ROOT/path) if (ROOT/path).is_file() else None


def paren_body(text, open_index):
    """The text between the parenthesis at text[open_index] and its matching close parenthesis (string and character literals skipped); None when it does not close."""
    assert text[open_index] == '(', text[open_index:open_index+20]
    depth, i, quote = 0, open_index, None
    while i < len(text):
        c = text[i]
        if quote:
            if c == '\\':
                i += 2
                continue
            if c == quote: quote = None
        elif c in '"\'': quote = c
        elif c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0: return text[open_index+1:i]
        i += 1
    return None


def split_args(body):
    """The top-level comma-separated arguments of a Java argument list or array initialiser (parentheses, brackets, braces and literals respected; a trailing comma ignored)."""
    out, depth, quote, cur, i = [], 0, None, '', 0
    while i < len(body):
        c = body[i]
        if quote:
            cur += c
            if c == '\\' and i + 1 < len(body):
                cur += body[i+1]
                i += 2
                continue
            if c == quote: quote = None
        elif c in '"\'':
            quote = c
            cur += c
        elif c in '([{':
            depth += 1
            cur += c
        elif c in ')]}':
            depth -= 1
            cur += c
        elif c == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else: cur += c
        i += 1
    if cur.strip(): out.append(cur.strip())
    return out


COUNT_LITERAL = re.compile(r'(?<![\w.])(\d[\d_]*)(?![\w.])')
RECIPE_START = re.compile(r'new GenericRecipe\("([^"]+)"\)')
REGISTRY_NAME = re.compile(r'public static final Deferred\w+<[^>]+(?:<[^>]*>)?>\s+(\w+)\s*=\s*(?:ITEMS\.register|register\w*)\("([^"]+)"')
CRAFT_LINE = re.compile(r'add(Recipe|Shapeless)Auto\(new ItemStack\(Mod(?:Items|Blocks)\.(\w+)(?:,\s*(\d+))?\),\s*new Object\[\]\s*\{(.*)\}\);')
SLAG_PAIR = re.compile(r'add1To9Pair\(new ItemStack\(ModBlocks\.(\w+)\), new ItemStack\(ModItems\.(\w+), (\d+), (\w+)\.id\)\);')


def stack_count(arg):
    """The stack size an assembler input argument names: its first free integer literal (string literals blanked), 1 when it has none (ComparableStack(item), OreDictStack(dict))."""
    m = COUNT_LITERAL.search(re.sub(r'"[^"]*"', '""', arg))
    return int(m.group(1).replace('_', '')) if m else 1


def blank_line_comments(text):
    """Whole-line // comments blanked and /* */ comments removed with their line breaks kept, so the line numbers stay those of the file."""
    text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)
    return '\n'.join('' if line.lstrip().startswith('//') else line for line in text.split('\n'))


def recipe_rows(text):
    """(rows, order) of every this.register(new GenericRecipe("name")...) statement: rows[name] = dict(line, stmt, pos) with stmt the text from the recipe start to the end of the
    register( call; order lists every name in source order (a repeated name appears twice)."""
    text = blank_line_comments(text)
    rows, order = {}, []
    for m in RECIPE_START.finditer(text):
        reg = text.rfind('this.register(', 0, m.start())
        body = paren_body(text, reg + len('this.register')) if reg >= 0 else None
        stmt = text[m.start():reg + len('this.register') + 1 + len(body)] if body is not None else None
        rows[m.group(1)] = dict(line=text.count('\n', 0, m.start()) + 1, stmt=stmt, pos=m.start())
        order.append(m.group(1))
    return rows, order


def gated_spans(text, opener):
    """[(start, end)] character offsets of the brace blocks that follow every `opener` (comments blanked as recipe_rows does, so the offsets are those of recipe_rows)."""
    text = blank_line_comments(text)
    spans, i = [], text.find(opener)
    while i >= 0:
        j = text.index('{', i)
        depth = 0
        for k in range(j, len(text)):
            if text[k] == '{': depth += 1
            elif text[k] == '}':
                depth -= 1
                if depth == 0:
                    spans.append((j, k))
                    break
        i = text.find(opener, i + 1)
    return spans


def row_facts(stmt, original, registry=None):
    """setup, output (original ModItems / ModBlocks field or NEO registry name) and count, the input count list in order, pools, 528 pools, group and the expensive list of one row."""
    if stmt is None: return None
    setup = re.search(r'\.setup\(([\d_]+),\s*([\d_]+)\)', stmt)
    if original: out = re.search(r'\.outputItems\(new ItemStack\(Mod(?:Items|Blocks)\.(\w+)(?:,\s*(\d+))?\)', stmt)
    else: out = re.search(r'\.outputItems\(new ItemStack\(Ntm(?:Items|Blocks)\.(\w+)\.get\(\)(?:,\s*(\d+))?\)', stmt)
    i = stmt.find('.inputItems(')
    body = paren_body(stmt, i + len('.inputItems')) if i >= 0 else None
    inputs = split_args(body) if body is not None else None
    output = (out.group(1) if original else (registry or {}).get(out.group(1), out.group(1))) if out else None
    return dict(setup=[int(setup.group(1).replace('_', '')), int(setup.group(2).replace('_', ''))] if setup else None, output=output, output_count=int(out.group(2) or 1) if out else None,
                inputs=len(inputs) if inputs is not None else None, input_counts=[stack_count(a) for a in inputs] if inputs is not None else None,
                pools=re.findall(r'\.setPools\(([^)]*)\)', stmt), pools528=re.findall(r'\.setPools528\(([^)]*)\)', stmt), group=re.findall(r'\.setGroup\((\w+|"[^"]*"),\s*this\)', stmt),
                expensive='.inputItemsEx(' in stmt, input_text=[re.sub(r'\s+', ' ', a)[:120] for a in inputs] if inputs is not None else None)


def original_crafting(text, token):
    """dict(kind, product, count, pattern, keys, ingredients) of the original crafting line holding `token` (addRecipeAuto / addShapelessAuto with an Object[] array), None when unparsed."""
    line = next((l for l in text.split('\n') if token in l), None)
    m = CRAFT_LINE.search(line or '')
    if not m: return None
    args = split_args(m.group(4).strip())
    out = dict(kind='shaped' if m.group(1) == 'Recipe' else 'shapeless', product=m.group(2), count=int(m.group(3) or 1))
    if out['kind'] == 'shaped':
        rows = [a[1:-1] for a in args if a.startswith('"')]
        rest = args[len(rows):]
        out.update(pattern=rows, keys=sorted(a[1] for a in rest[0::2] if a.startswith("'")), ingredients={rest[i][1]: rest[i+1] for i in range(0, len(rest) - 1, 2) if rest[i].startswith("'")})
    else:
        out.update(ingredients=args)
    return out


def registry_names():
    """NtmItems / NtmBlocks constant -> registry name (the first registration of a name wins), read from the live sources."""
    names = {}
    for path in (NTM_ITEMS, J+'blocks/NtmBlocks.java'):
        for const, name in REGISTRY_NAME.findall((ROOT/path).read_text(encoding='utf-8')): names.setdefault(const, name)
    return names


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
    goal28b_start = read(GOAL28B_BASELINE)
    goal28b_start['files'] = merged_files(goal28b_start)
    tracked_count = len(base['files'])
    goal28a_receipt = read(ROOT/'build/migration/releases/goal28a/release.json')

    # 1. Heads: the clean original at 4f5924e2b (unchanged since Goal28A), NEO at the start commit 66a00353 (the mod rename, = origin/master at the freeze; Goal28C commits nothing) with the UNCOMMITTED
    # Goal28A-28B delivery in the worktree at the freeze (37 modified, 254 untracked files). The Goal 27 delivery adaf265c is two commits below; migration/ is untracked and Git-ignored (66050453), so
    # the start is `files` (the worktree content of the tracked and the untracked non-ignored files) + `migration_files`.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at 4f5924e2b'
    assert start_head.startswith(START_PREFIX), 'The frozen start is not on the mod rename commit 66a00353'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Rename the mod' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the mod rename commit'
    status_text = START_STATUS.read_text(encoding='utf-8')
    status_lines = [l for l in status_text.splitlines() if l]
    assert status_lines and base['target_status'] == status_text, 'start_status.txt differs from the baseline target status (the frozen start holds the uncommitted Goal28A-28B delivery)'
    assert len(status_lines) == len(base['modified_at_start']) + len(base['untracked_at_start']) and sorted(l[3:] for l in status_lines) == sorted(base['modified_at_start'] + base['untracked_at_start']), \
        'start_status.txt does not list the modified_at_start and untracked_at_start paths of the baseline'
    assert base['target_parent'].startswith(START_PARENT_PREFIX) and base['origin_master'] == start_head, 'The start commit is not origin/master on c1f6f397'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal28b receipt records another original commit than 4f5924e2b (the original must be unmoved)'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal28C (the delivery stays uncommitted until the Goal 28 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2, 3)}
    assert chain[1].startswith(START_PARENT_PREFIX) and chain[2].startswith(UNTRACK_PREFIX) and chain[3].startswith(GOAL27_DELIVERY_PREFIX), \
        'NEO HEAD~1..3 are not c1f6f397, the migration/ untrack commit 66050453 and the Goal 27 delivery adaf265c: '+str(chain)
    committed_files = [l for l in git_ro(ROOT, 'show', '--name-only', '--format=', start_head).splitlines() if l.strip()]
    assert committed_files and not any(p.startswith('build/') for p in committed_files), 'The start commit is empty or holds build/ files'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and 'mod rename' in base['start_content']['committed'] and base['start_content']['uncommitted'].startswith('the Goal28A-28B delivery'), \
        'Baseline start content differs (expected the committed mod rename and the uncommitted Goal28A-28B delivery)'
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
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal28b generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_freeze']
    assert base['target_head'] == start_head and not [p for p in committed_files if p.startswith('migration/')], 'The start commit holds migration/ files (Git-ignored since 66050453)'
    # The start content must be exactly the packaged Goal28A and Goal28B deliveries: every Git-visible path the goal28a or the goal28b receipt lists is in the start status, the status lists no
    # other path, and every such path has the after-hash of the newer receipt that lists it.
    delivery = {c['path']: c for c in goal28a_receipt['changed_files']}
    delivery.update({c['path']: c for c in prior_receipt['changed_files']})
    delivery_visible = sorted(p for p in delivery if not p.startswith(('migration/', 'build/')))
    need(delivery_visible == sorted(base['modified_at_start'] + base['untracked_at_start']),
         'The Git-visible paths of the goal28a and goal28b receipts differ from the 28C start status: only in the receipts %s, only at the start %s' % (
             sorted(set(delivery_visible) - set(base['modified_at_start'] + base['untracked_at_start']))[:4], sorted(set(base['modified_at_start'] + base['untracked_at_start']) - set(delivery_visible))[:4]))
    delivery_moved = sorted(p for p in delivery if p in base['files'] and base['files'][p] != delivery[p]['after_sha256'])
    uncommitted_start = dict(
        status_entries=len(status_lines), status=status_lines, modified=len(base['modified_at_start']), untracked=len(base['untracked_at_start']),
        modified_paths=base['modified_at_start'], untracked_paths=base['untracked_at_start'],
        description='the worktree holds the uncommitted Goal28A-28B delivery (packaged as goal28a and goal28b, never committed): the start content of this batch; baseline `files` hashes the worktree '
                    'content, so every 28A and 28B change is part of the start',
        goal28a_delivery_paths=len(goal28a_receipt['changed_files']), goal28b_delivery_paths=len(prior_receipt['changed_files']), delivery_paths=len(delivery),
        delivery_paths_changed_since_package=delivery_moved,
        committed_delivery=dict(commit=start_head[:8], parent=base['target_parent'][:8], files_in_commit=len(committed_files), untrack_commit=chain[2][:8], goal27_delivery_commit=chain[3][:8],
                                note='66a00353 renames the mod (gradle.properties mod_name / mod_authors -> neoforge.mods.toml) and ignores .claude; c1f6f397 rewrites the README; 66050453 untracks and ignores '
                                     'migration/; adaf265c commits the Goal 27 delivery (27C and 27D) with the small fixes D3 and D5.'),
        migration_dir=dict(tracked_files_hashed=tracked_count, migration_files_hashed=len(base['migration_files']), copied_scope=len(base['copied_scope']),
                           note='migration/ is Git-ignored: `git ls-files` no longer lists it, so the baseline hashes it from disk and this packager finds its changes by walking the directory.'))

    # 2. Previous deliveries: the goal28b package (build/libs at the freeze is byte-identical to it), every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the freeze is not the goal28b package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal28b receipt list + the goal28b package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal28b receipt count + the goal28b release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal28b receipt'
    newer_drift = sorted(base['previous_receipt_evidence_drift'])
    need(newer_drift == [], 'The baseline records drift against the goal28b receipt (expected none: the receipt matches every hash it records): '+str(newer_drift))
    protected, repinned = protected_paths(base)
    need(all(p.endswith('-ACCEPTANCE.md') or p == 'migration/GOAL24B.md' for p in repinned), 'A pin other than an acceptance checklist or GOAL24B.md changed between the Goal28B and Goal28C starts: '+str(sorted(repinned)))
    drift_report = start_drift_report(base, repinned, goal28b_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal28b receipt: '+str(sorted(explained))
    # No small fix lies between the goal28b package and this start: the README lines above the Goal28B line (newest first) must name none. Any that does is listed as packaged with goal28c.
    readme_start = start_bytes(base, 'migration/README.md')
    readme_start_lines = readme_start.decode('utf-8').split('\n') if readme_start else []
    goal28b_line = next((i for i, l in enumerate(readme_start_lines) if l.startswith('2026-10-28 Goal28B')), None)
    need(goal28b_line is not None, 'migration/README.md (start copy) has no "2026-10-28 Goal28B" delivery line')
    small_fixes_after_goal28b = [l[:140] for l in readme_start_lines[:goal28b_line] if l.startswith('2026-10-') and '小修' in l] if goal28b_line is not None else None

    # 3. Changes since the start: each path in the owner table, attributed to goal28c. Everything else equals its start hash (the merged tracked and migration/ hashes).
    changes = changed_since_start(base)
    imported = {p for p in changes if TEXTURE_PATTERN.fullmatch(p)}
    verifier_md = VERIFIER_REPORT_MD.read_text(encoding='utf-8', errors='replace') if VERIFIER_REPORT_MD.is_file() else None
    need(verifier_md is not None, 'evidence missing: build/migration/goal28c/verifier-report.md (the GameTest / verifier session\'s report; it lists the older GameTest lines it edited)')
    if verifier_md is not None:
        for name in sorted(set(re.findall(r'\b(\w+GameTests)\.java', verifier_md))):
            p = J+'gametest/'+name+'.java'
            if p in changes and p in base['files'] and p not in EDITED_GAMETESTS and p != RECIPE_TESTS and p not in EDITED_EXTRA: EDITED_EXTRA.append(p)
    optional_changed = [p for p in OPTIONAL_JAVA if p in changes]
    modified_java = MODIFIED_JAVA + optional_changed
    edited_gametests = EDITED_GAMETESTS + EDITED_EXTRA
    production_java = NEW_JAVA + modified_java + [p for p in edited_gametests if p in changes]
    older_gametests_frozen = sorted(p for p in base['files'] if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p not in OPTIONAL_JAVA and p not in edited_gametests)
    unassigned = sorted(p for p in changes if group(p, imported) is None)
    need(not unassigned, 'Path changed since the Goal28C start that the owner table does not list (production outside the 7 modified Java files, RecipeCompletionGameTests and the older GameTests '
         'verifier-report.md names, a hand-written resource other than the rangefinder texture, a generated file other than the stamp, en_us.json and the recipe / advancement / tag / item model '
         'set, a protected or frozen record, an older tool, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal 28B and earlier records, GOAL28D.md, GOAL28-THREAD-PROMPTS.md or SURVIVAL-PLAYABILITY.md changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal28C start: '+str(deleted)
    for p in MODIFIED_JAVA + EDITED_GAMETESTS + GENERATED_MODIFIED + [ZH_INPUT, TASK_BOOK] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + REQUIRED_TEXTURES + REQUIRED_GENERATED + NEW_TOOLS + REPORTS[1:]:
        assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(production_java) - imported - {ZH_INPUT})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified (+ optional), {len(NEW_JAVA)} new and {len(edited_gametests)} edited GameTest Java files, the rangefinder texture '
         'and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools = OLD_TOOLS_FROZEN + sorted(p for p in base['files'] if p.startswith(FROZEN_TOOL_DIRS))
    frozen_tools_changed = sorted(p for p in frozen_tools if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (package_goal28b.py, verify_goal28b_worldgen.py, package_goal28a.py, verify_goal28a_worldgen.py, the 27A-27D '
         'packagers and verifiers, the casting regression wrapper and compat, the Goal 26C old-suite wrapper, the casting regressions and their folders): '+str(frozen_tools_changed))
    frozen_dir_files = sorted(p for p in base['files'] if p.startswith(UNCHANGED_DIRS) or p.startswith((GENERATED_ROOT+'data/hbmsntm/recipe/', GENERATED_ROOT+'data/hbmsntm/advancement/')))
    unchanged_bad = [p for p in UNCHANGED_JAVA + older_gametests_frozen + frozen_dir_files if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed (GenericRecipe, GenericRecipes, BlueprintFolderItem, NtmBlocks, every block / block entity / menu / '
         'handler/jei class, every other GameTest class, every crafting recipe JSON and advancement of the start): '+str(unchanged_bad[:8]))
    goal28_now = sha(ROOT/GOAL28_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository before the start. The batch ran under the main '
                                               'agent (production review, the migration/ records, zh_cn.json and the mapping) with a production builder (the 28C Java, the rangefinder texture, runData), a '
                                               'GameTest verifier (RecipeCompletionGameTests, any older expectation lines, verify_goal28c_recipes.py, the assembler-diff rerun, runData and the GameTest '
                                               'server), a reviewer and this packaging verifier (the packager, the final runner, the casting-regression attribution) working in the same checkout; each '
                                               'wrote only its named files (the scope snapshots of the verifiers are indexed as evidence).',
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
    # AssemblyMachineRecipes is append-only (handoff): the start file plus import lines in the import section and ONE contiguous block after the last pre-batch row, so the text before the
    # first 28C line (imports aside) and after the block is the start text and the 58 pre-batch rows are byte-identical (line endings aside, reported above).
    assembler_rule = None
    if ASSEMBLER in start_text:
        start_lines, live_lines = lines_of(start_text[ASSEMBLER]), lines_of((ROOT/ASSEMBLER).read_bytes())
        inserted = insertions(start_lines, live_lines)
        imports = [(i, l) for i, l in (inserted or []) if l.strip().startswith('import ')]
        block = [i for i, l in (inserted or []) if not l.strip().startswith('import ')]
        class_line = next((i for i, l in enumerate(live_lines) if re.match(r'\s*public class ', l)), None)
        rule = dict(insert_only=inserted is not None, imports=[l.strip() for _, l in imports], block_lines=len(block), block_at=[block[0] + 1, block[-1] + 1] if block else None)
        if inserted is not None and block:
            first = block[0]
            rule['contiguous'] = block == list(range(block[0], block[-1] + 1))
            rule['imports_in_header'] = class_line is not None and all(i < class_line for i, _ in imports)
            keep = first - len(imports)
            rule['before_block_is_start'] = [l for i, l in enumerate(live_lines[:first]) if i not in {j for j, _ in imports}] == start_lines[:keep]
            rule['after_block_is_start'] = live_lines[block[-1] + 1:] == start_lines[keep:]
            rule['after_last_start_row'] = not any('this.register(' in l for l in start_lines[keep:])
        rule['holds'] = bool(inserted is not None and block and rule.get('contiguous') and rule.get('imports_in_header') and rule.get('before_block_is_start') and rule.get('after_block_is_start')
                             and rule.get('after_last_start_row'))
        assembler_rule = rule
        content_rules[ASSEMBLER] = rule['holds']
        need(rule['holds'], f'{ASSEMBLER} is not the start file plus imports and one appended block after the last pre-batch row: {json.dumps(rule)[:400]}')
    # The other production files only gain lines (handoff: "add ... only"): no start line is removed except a terminator or a call chain that an added line extends.
    for p in MODIFIED_JAVA[1:]:
        if p not in removed_lines: continue
        stray = stray_removals(removed_lines[p], added_lines[p])
        content_rules[p] = not stray
        need(not stray, f'{p} removes start lines that no added line extends: {stray[:4]}')
    # The older GameTests the batch edits by design: the @GameTest methods are the start's; every changed code line is a start line with other integer literals (an expectation such as a row or
    # item count), comments free.
    gametest_edits = {}
    for p in gametest_edit_files:
        if p not in start_text: continue
        now_text, was_text = (ROOT/p).read_text(encoding='utf-8'), start_text[p].decode('utf-8')
        names_now, names_was = GAMETEST_METHOD.findall(now_text), GAMETEST_METHOD.findall(was_text)
        annotations_now, annotations_was = len(GAMETEST_ANNOTATION.findall(now_text)), len(GAMETEST_ANNOTATION.findall(was_text))
        touched = [l.strip() for l in removed_lines[p] + added_lines[p] if '@GameTest' in l or 'public static void' in l]
        code_was = [l for l in lines_of(start_text[p]) if not is_comment(l) and l.strip()]
        code_now = [l for l in lines_of((ROOT/p).read_bytes()) if not is_comment(l) and l.strip()]
        pairs, unpaired = [], []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, code_was, code_now, autojunk=False).get_opcodes():
            if tag == 'equal': continue
            if tag == 'replace' and i2 - i1 == j2 - j1:
                for a, b in zip(code_was[i1:i2], code_now[j1:j2]):
                    (pairs if re.sub(r'\d[\d_]*', '#', a) == re.sub(r'\d[\d_]*', '#', b) else unpaired).append((a.strip()[:160], b.strip()[:160]))
            else: unpaired.append((' | '.join(l.strip()[:80] for l in code_was[i1:i2]), ' | '.join(l.strip()[:80] for l in code_now[j1:j2])))
        entry = dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p), added=len(added_lines[p]), removed=len(removed_lines[p]), game_tests=annotations_now, game_tests_at_start=annotations_was,
                     methods_unchanged=names_now == names_was, rule='only expectations change: every changed code line differs from its start line in integer literals only; comments free',
                     changed_lines=[dict(was=a, now=b) for a, b in pairs], not_literal_only=[dict(was=a, now=b) for a, b in unpaired],
                     rule_holds=bool(pairs) and not unpaired and not touched)
        gametest_edits[p] = entry
        need(entry['rule_holds'] and entry['methods_unchanged'] and annotations_now == annotations_was, f'{p} changed beyond its allowed edit ({entry["rule"]}): {json.dumps(entry, ensure_ascii=False)[:500]}')

    # 4. Recipe completion against the original (EXPECTED holds the handoff figures; every value is computed from the sources; the NEO side is read from the assembler source rows, the
    # generated recipe / tag / model JSON and tolerant source patterns; the behaviour itself is the job of verify_goal28c_recipes.py and RecipeCompletionGameTests).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    facts, bad = {}, []

    def fact(key, value, expected=None, ok=None):
        facts[key] = value if expected is None else dict(value=value, expected=expected)
        if ok is None: ok = expected is None or value == expected
        if not ok: bad.append(key)

    o = {path: original_text(path) for path in O_SOURCES}
    code = lambda p: strip_java_comments(neo_text(p))
    registry = registry_names()
    # 4a. The 24 assembler rows (AssemblyMachineRecipes.java:65-79, 262-268, 301-308, 392-397, 437-439, 629-637, 652-653, 1110-1111): setup, the product and its count, the input count list in the
    # original order, the alt.plates pool and the autoswitch.plates group of the plate rows, no setPools528 in NEO (the original's on the pumpjack and the fracker is not migrated), the overdrive rows inside if(no528) / if(!NtmConfig.enable528()).
    # The expensive lists are not migrated (known_differences). NEO products are compared by registry name with the original ModItems / ModBlocks field.
    o_rows, o_order = recipe_rows(o[O_AMR])
    n_rows, n_order = recipe_rows(neo_text(ASSEMBLER))
    s_rows, s_order = recipe_rows(start_text[ASSEMBLER].decode('utf-8').replace('\r\n', '\n')) if ASSEMBLER in start_text else recipe_rows(start_bytes(base, ASSEMBLER).decode('utf-8').replace('\r\n', '\n'))
    o_gate, n_gate = gated_spans(o[O_AMR], 'if(no528) {'), gated_spans(neo_text(ASSEMBLER), 'if(!NtmConfig.enable528()) {')
    o_plate_var = re.search(r'String (\w+) = "' + re.escape(PLATE_GROUP) + '";', o[O_AMR])
    n_plate_var = re.search(r'String (\w+) = "' + re.escape(PLATE_GROUP) + '";', neo_text(ASSEMBLER))
    rows_facts, rows_ok = {}, True
    for name in ASSEMBLER_ROWS:
        orow, nrow = o_rows.get(name), n_rows.get(name)
        of = row_facts(orow['stmt'], True) if orow else None
        nf = row_facts(nrow['stmt'], False, registry) if nrow else None
        entry = dict(original_line=f'{O_AMR}:{orow["line"]}' if orow else None, original=of, neo_line=f'{ASSEMBLER}:{nrow["line"]}' if nrow else None, neo=nf)
        ok = bool(of and nf)
        if ok:
            plate = name in PLATE_ROWS
            gated_o = any(a < orow['pos'] < b for a, b in o_gate)
            gated_n = any(a < nrow['pos'] < b for a, b in n_gate)
            entry.update(gated_original=gated_o, gated_neo=gated_n)
            ok = (of['setup'] == nf['setup'] and of['output'] == nf['output'] and of['output_count'] == nf['output_count'] and of['input_counts'] == nf['input_counts']
                  and of['pools'] == nf['pools'] and nf['pools528'] == [] and bool(of['group']) == bool(nf['group']) == plate
                  and (not plate or (of['pools'] == ['GenericRecipes.POOL_PREFIX_ALT + "plates"'] and o_plate_var and n_plate_var and of['group'] == [o_plate_var.group(1)] and nf['group'] == [n_plate_var.group(1)]))
                  and gated_o == gated_n == (name in OVERDRIVE_ROWS) and not nf['expensive'] and len(n_order) and n_order.count(name) == 1)
        entry['ok'] = ok
        rows_facts[name] = entry
        rows_ok = rows_ok and ok
    fact('assembler_rows', {k: dict(original_line=v['original_line'], neo_line=v['neo_line'], setup=(v['neo'] or {}).get('setup'), output=(v['neo'] or {}).get('output'),
                                    output_count=(v['neo'] or {}).get('output_count'), input_counts=(v['neo'] or {}).get('input_counts'), pools=(v['neo'] or {}).get('pools'),
                                    pools528=(v['neo'] or {}).get('pools528'), group=PLATE_GROUP if (v['neo'] or {}).get('group') else None, gated_outside_528=v.get('gated_neo'), ok=v['ok'])
                            for k, v in rows_facts.items()}, None, ok=rows_ok and len(ASSEMBLER_ROWS) == EXPECTED['assembler_rows_added'] and len(PLATE_ROWS) == EXPECTED['plate_rows'])
    failed_rows = {k: dict(original=v['original'], neo=v['neo']) for k, v in rows_facts.items() if not v['ok']}
    if failed_rows: facts['assembler_rows_failed'] = failed_rows
    # The table: 58 start rows in their start order, then the 24 rows appended in the handoff order; the original holds 355 rows; ass.plateweaponsteel stays out (NEO has no plate_weaponsteel).
    fact('assembler_table', dict(start_rows=len(s_order), rows=len(n_order), start_order_kept=n_order[:len(s_order)] == s_order, appended=n_order[len(s_order):], original_rows=len(o_order),
                                 group_variable=dict(original=o_plate_var.group(1) if o_plate_var else None, neo=n_plate_var.group(1) if n_plate_var else None),
                                 no528=dict(original='boolean no528 = !GeneralConfig.enable528;' in o[O_AMR], neo=bool(n_gate)),
                                 pools528_noop='public GenericRecipe setPools528(String... pools) { if(GeneralConfig.enable528)' in o[O_GENERIC],
                                 not_registered={n: dict(in_original=n in o_rows, in_neo=n in n_rows, neo_product_registered=(row_facts(o_rows[n]['stmt'], True) or {}).get('output') in set(registry.values()) if n in o_rows else None)
                                                 for n in NOT_REGISTERED_ROWS}),
         dict(start_rows=EXPECTED['assembler_rows_start'], rows=EXPECTED['assembler_rows_start'] + EXPECTED['assembler_rows_added'], start_order_kept=True, appended=list(ASSEMBLER_ROWS),
              original_rows=EXPECTED['original_assembler_rows'], group_variable=dict(original='autoPlate', neo='autoPlate'), no528=dict(original=True, neo=True), pools528_noop=True,
              not_registered={n: dict(in_original=True, in_neo=False, neo_product_registered=False) for n in NOT_REGISTERED_ROWS}))
    # 4b. The 15 crafting recipes (CraftingManager.java:319-323, 520-524, 852, WeaponRecipes.java:297-299, ToolRecipes.java:104, MineralRecipes.java:58): the generated JSON's type, result and count,
    # the shaped pattern rows and key letters exactly the original's, the shapeless ingredient count; the slag pair is add1To9Pair with the slag raw ingot (MAT_SLAG.id = _AS + 11, Mats.java).
    def recipe(name): return generated_json(GENERATED_ROOT+f'data/hbmsntm/recipe/{name}.json')
    slag_as = re.search(r'public static final int _AS = (\d+);', o[O_MATS])
    slag_off = re.search(r'NTMMaterial MAT_SLAG\s*= makeSmeltable\(_AS \+ (\d+),', o[O_MATS])
    slag_meta = int(slag_as.group(1)) + int(slag_off.group(1)) if slag_as and slag_off else None
    meta_of = lambda node: ((node or {}).get('components') or {}).get('hbmsntm:meta')
    crafting, crafting_ok = {}, True
    for name, (src, token, product) in CRAFTING.items():
        r = recipe(name)
        entry = dict(original_line=f'{O_BY_KEY[src]}:{original_line(O_BY_KEY[src], token)}', neo=None)
        if name in ('block_slag', 'ingot_raw_slag'):
            m = SLAG_PAIR.search(next((l for l in o[O_MR].split('\n') if token in l), ''))
            entry['original'] = dict(block=m.group(1), ingot=m.group(2), count=int(m.group(3)), material=m.group(4), meta=slag_meta) if m else None
            ok = bool(m and r and slag_meta is not None)
            if ok:
                res = r.get('result', {})
                if name == 'block_slag':
                    keys = r.get('key', {})
                    ing = next(iter(keys.values())) if len(keys) == 1 else {}
                    pattern = r.get('pattern', [])
                    entry['neo'] = dict(type=r.get('type'), pattern=pattern, ingredient=ing, result=res)
                    ok = (r.get('type') == 'minecraft:crafting_shaped' and len(pattern) == 3 and all(len(row) == 3 for row in pattern) and len(set(''.join(pattern))) == 1 and len(keys) == 1
                          and (ing.get('items') or ing.get('item')) == 'hbmsntm:'+m.group(2) and meta_of(ing) == slag_meta and res.get('id') == 'hbmsntm:'+m.group(1) and res.get('count', 1) == 1)
                else:
                    ings = r.get('ingredients', [])
                    entry['neo'] = dict(type=r.get('type'), ingredients=ings, result=res)
                    ok = (r.get('type') == 'minecraft:crafting_shapeless' and ings == [{'item': 'hbmsntm:'+m.group(1)}] and res.get('id') == 'hbmsntm:'+m.group(2) and res.get('count') == int(m.group(3))
                          and meta_of(res) == slag_meta)
        else:
            orig = original_crafting(o[O_BY_KEY[src]], token)
            entry['original'] = orig
            ok = bool(orig and r)
            if ok:
                res = r.get('result', {})
                kind = 'minecraft:crafting_shaped' if orig['kind'] == 'shaped' else 'minecraft:crafting_shapeless'
                entry['neo'] = dict(type=r.get('type'), pattern=r.get('pattern'), keys=sorted(r.get('key', {})), ingredients=len(r.get('ingredients', [])), result=res)
                ok = (r.get('type') == kind and res.get('id') == 'hbmsntm:'+product and res.get('count', 1) == orig['count'] and orig['product'] == (product if name != 'det_miner_steel' else 'det_miner')
                      and (orig['kind'] != 'shaped' or (r.get('pattern') == orig['pattern'] and sorted(r.get('key', {})) == orig['keys']))
                      and (orig['kind'] != 'shapeless' or len(r.get('ingredients', [])) == len(orig['ingredients'])))
                if name == 'press_preheater':
                    entry['lava'] = dict(original=orig['ingredients'].get('L'), neo=r.get('key', {}).get('L'))
                    ok = ok and orig['ingredients'].get('L') == 'Fluids.LAVA.getDict(1000)' and r.get('key', {}).get('L') == {'item': 'minecraft:lava_bucket'}
        entry['ok'] = ok
        crafting[name] = entry
        crafting_ok = crafting_ok and ok
    fact('crafting_recipes', {k: dict(original_line=v['original_line'], result=(v.get('neo') or {}).get('result'), ok=v['ok']) for k, v in crafting.items()}, None,
         ok=crafting_ok and len(CRAFTING) == EXPECTED['crafting_recipes'] and slag_meta == 41)
    failed_crafting = {k: dict(original=v.get('original'), neo=v.get('neo')) for k, v in crafting.items() if not v['ok']}
    if failed_crafting: facts['crafting_recipes_failed'] = failed_crafting
    fact('crafting_not_registered', {n: dict(original_line=f'{O_BY_KEY[src]}:{original_line(O_BY_KEY[src], token)}', missing_input=inp, input_registered=inp in set(registry.values()),
                                             generated=recipe(n) is not None, at_start=GENERATED_ROOT+f'data/hbmsntm/recipe/{n}.json' in base['files'])
                                     for n, (src, token, inp) in CRAFTING_NOT_REGISTERED.items()},
         {n: dict(original_line=f'{O_BY_KEY[src]}:{original_line(O_BY_KEY[src], token)}', missing_input=inp, input_registered=False, generated=False, at_start=False)
          for n, (src, token, inp) in CRAFTING_NOT_REGISTERED.items()})
    # 4c. The four item tags (OreDictManager.java:311, 313, 502 and CU at :162): the generated tag JSON holds exactly the two NEO members of the original dictionary.
    tags = {}
    for tag, (dictionary, token, members) in NEW_TAGS.items():
        t = generated_json(GENERATED_ROOT+f'data/ntm/tags/item/{tag}.json')
        tags[tag] = dict(original=dictionary, original_line=f'{O_OREDICT}:{original_line(O_OREDICT, token)}', values=sorted((t or {}).get('values', [])) if t else None,
                         expected=sorted(c if ':' in c else 'hbmsntm:'+registry.get(c, '?'+c) for c in members), declared=bool(re.search(r'ItemTags\.create\(ResourceLocation\.fromNamespaceAndPath\("ntm", "'+tag+r'"\)\)', code(ITEM_TAG_PROVIDER))))
    fact('item_tags', tags, None, ok=all(v['values'] == v['expected'] and v['declared'] and not any(e.startswith('hbmsntm:?') for e in v['expected']) for v in tags.values()) and len(tags) == EXPECTED['item_tags'])
    # 4d. The rangefinder (ModItems.java:3388: ItemRangefinder, setMaxStackSize(1)): a plain NEO item with stack size 1, in the missile creative tab after the range designator (the original missileTab), an
    # item/generated model with its own texture; its ranging is not migrated.
    n_items, n_tabs = code(NTM_ITEMS), code(CREATIVE_TABS)
    model = generated_json(GENERATED_ROOT+'assets/hbmsntm/models/item/rangefinder.json')
    fact('rangefinder', dict(original='rangefinder = new ItemRangefinder().setUnlocalizedName("rangefinder").setMaxStackSize(1)' in o[O_MODITEMS],
                             registered=bool(re.search(r'RANGEFINDER = ITEMS\.register\("rangefinder", \(\) -> new Item\(new Item\.Properties\(\)\.stacksTo\(1\)\)\)', n_items)),
                             creative_tab=bool(re.search(r'output\.accept\(NtmItems\.DESIGNATOR_RANGE\);\s*output\.accept\(NtmItems\.RANGEFINDER\);', n_tabs)),
                             model_provider='this.basicItem(NtmItems.RANGEFINDER.get());' in code(ITEM_MODEL_PROVIDER), model=model),
         dict(original=True, registered=True, creative_tab=True, model_provider=True, model={'parent': 'minecraft:item/generated', 'textures': {'layer0': 'hbmsntm:item/rangefinder'}}))
    # 4e. The candidate table (tools/migration/goal28c_assembler_diff.py). assembler-diff.json is the START table (the script run on the baseline-files/ copies: 58 NEO rows, the 24
    # register rows still candidates) and is never rerun over; assembler-diff-after.json is the rerun on the settled tree (--output): 82 NEO rows read from the live table, the 24 rows
    # registered, register [], no candidate undecided, no decision stale.
    start_path, diff_path = OUT/ASSEMBLER_DIFF, OUT/ASSEMBLER_DIFF_AFTER
    sdiff = read(start_path) if start_path.is_file() else None
    adiff = read(diff_path) if diff_path.is_file() else None
    candidate_table = None
    if need(sdiff is not None, 'evidence missing: build/migration/goal28c/'+ASSEMBLER_DIFF+' (the start candidate table)'):
        need(sdiff.get('neo_rows') == EXPECTED['assembler_rows_start'] and sorted(sdiff.get('register') or []) == sorted(ASSEMBLER_ROWS)
             and [r['name'] for r in sdiff.get('neo_table', [])] == s_order and sdiff.get('original_rows') == EXPECTED['original_assembler_rows'],
             f'{ASSEMBLER_DIFF} is not the start table (it must never be rerun over): neo_rows {sdiff.get("neo_rows")} (expected {EXPECTED["assembler_rows_start"]}), register '
             f'{len(sdiff.get("register") or [])} names, differing from the 24: {sorted(set(sdiff.get("register") or []) ^ set(ASSEMBLER_ROWS))[:4]}')
    if need(adiff is not None, 'evidence missing: build/migration/goal28c/'+ASSEMBLER_DIFF_AFTER+' (python -B -X utf8 '+ASSEMBLER_DIFF_TOOL+' --output build/migration/goal28c/'+ASSEMBLER_DIFF_AFTER+' after the final runData)'):
        by_name = {r['name']: r for r in adiff.get('rows', [])}
        live_names = n_order
        current = (adiff.get('neo_rows') == len(live_names) == EXPECTED['assembler_rows_start'] + EXPECTED['assembler_rows_added'] and [r['name'] for r in adiff.get('neo_table', [])] == live_names)
        registered_now = sorted(n for n in ASSEMBLER_ROWS if (by_name.get(n) or {}).get('cls') == 'registered')
        candidate_table = dict(path=diff_path.relative_to(ROOT).as_posix(), sha256=sha(diff_path), tool=ASSEMBLER_DIFF_TOOL, tool_sha256=sha(ROOT/ASSEMBLER_DIFF_TOOL) if (ROOT/ASSEMBLER_DIFF_TOOL).is_file() else None,
                               start=dict(path=start_path.relative_to(ROOT).as_posix(), sha256=sha(start_path), neo_rows=sdiff.get('neo_rows'), register=len(sdiff.get('register') or [])) if sdiff is not None else None,
                               original_rows=adiff.get('original_rows'), neo_rows=adiff.get('neo_rows'), counts=adiff.get('counts'), register=list(ASSEMBLER_ROWS), registered_now=registered_now,
                               undecided=adiff.get('undecided'), stale_decisions=adiff.get('stale_decisions'),
                               deferred_decisions={r['name']: r.get('decision') for r in adiff.get('candidates', []) if r.get('decision') != 'register'},
                               deferred_by_reason=dict(Counter(r.get('decision') for r in adiff.get('candidates', []) if r.get('decision') != 'register')),
                               unregistered=sorted(r['name'] for r in adiff.get('rows', []) if r.get('cls') == 'unregistered'),
                               renamed={r['name']: r.get('neo_names') for r in adiff.get('renamed', [])}, unresolved=[r['name'] for r in adiff.get('unresolved', [])], neo_only=adiff.get('neo_only'),
                               current=current)
        need(current and registered_now == sorted(ASSEMBLER_ROWS) and adiff.get('undecided') == [] and not adiff.get('stale_decisions') and adiff.get('original_rows') == EXPECTED['original_assembler_rows']
             and adiff.get('register') == [],
             f'{ASSEMBLER_DIFF_AFTER} is not the rerun on the settled tree (python -B -X utf8 {ASSEMBLER_DIFF_TOOL} --output build/migration/goal28c/{ASSEMBLER_DIFF_AFTER}): neo_rows {adiff.get("neo_rows")} vs live {len(live_names)}, '
             f'{len(registered_now)}/24 register rows registered, undecided {adiff.get("undecided")}, stale {adiff.get("stale_decisions")}, still candidates {adiff.get("register")[:3] if adiff.get("register") else []}')
    facts['candidate_table'] = {k: v for k, v in (candidate_table or {}).items() if k not in ('deferred_decisions', 'unregistered')}
    facts['original_references'] = original_refs
    need(not bad, 'recipe-completion facts differ from the original or the handoff figures (or the NEO source / generated file is missing or its text differs): '+', '.join(
        f'{k}={json.dumps(facts.get(k + "_failed", facts[k]), ensure_ascii=False, default=str)[:300]}' for k in bad))
    # The materials/reachability record (the main agent's; pending until written): it must say which rows and recipes are reachable and which inputs have no source.
    ledger = read(ROOT/LEDGER) if (ROOT/LEDGER).is_file() else None
    if need(ledger is not None, 'record missing: '+LEDGER):
        need(str(ledger.get('goal')) == '28C', f'{LEDGER} is not the Goal 28C ledger')

    # 5. Resources: the byte imports (original worktree file and stored blob at 4f5924e2b), against migration/goal28c-resource-ownership.json.
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

    # 6. features.json: one new group recipe-completion (partial-unverified at the original commit); every other group keeps reviewed_source_commit (the original did not move) and its status; only
    # oil-extraction, materials, recipe-completion and the product groups (PRODUCT_GROUPS) may change notes / target_paths / target_watch / source lists.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit 4f5924e2b'
    assert (NOTES_MAY_CHANGE - {NEW_FEATURE}) <= set(start_features) and NEW_FEATURE not in start_features, 'The start mapping does not hold the groups the handoff allows to change, or already holds recipe-completion'
    may_change = lambda i: i in NOTES_MAY_CHANGE
    need(set(by_id) == set(start_features) | {NEW_FEATURE}, 'features.json group ids are not the start ids + recipe-completion: '+str(sorted(set(by_id) ^ (set(start_features) | {NEW_FEATURE}))))
    group_recipes = by_id.get(NEW_FEATURE)
    if need(group_recipes is not None, 'migration/features.json lacks the group '+NEW_FEATURE):
        need(group_recipes.get('status') == 'partial-unverified' and group_recipes.get('reviewed_source_commit') == SOURCE_HEAD, f'features.json group {NEW_FEATURE} is not partial-unverified at {SOURCE_HEAD[:8]}')
        unlisted = [p for p in O_SOURCES if not p.startswith(O_RES) and not any(feature_matches(f, 'source', p) for f in features)]
        need(not unlisted, f'features.json lists these original sources in no group (source_paths / source_watch): {unlisted}')
        mapped_java = [p for p in MODIFIED_JAVA if not any(feature_matches(f, 'target', p) for f in features)]
        need(not mapped_java, f'features.json maps these changed Java paths in no group (target_paths / target_watch): {mapped_java[:4]}')
        recipe_paths = [ASSEMBLER, RECIPE_PROVIDER, ITEM_TAG_PROVIDER] + REQUIRED_TEXTURES
        need(all(feature_matches(group_recipes, 'target', p) for p in recipe_paths), f'features.json group {NEW_FEATURE} does not map {[p for p in recipe_paths if not feature_matches(group_recipes, "target", p)]}')
    absent = sorted({p for f in features for p in f.get('source_paths', []) if not (SOURCE/p).is_file()})
    need(not absent, f'features.json source_paths missing in the original: {absent[:6]}')
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    need(all(may_change(i) for i in notes_changed), 'features.json groups whose notes changed beyond oil-extraction / materials / the product groups '+str(sorted(PRODUCT_GROUPS))+
         ' (extend PRODUCT_GROUPS if such a group is a product group of this batch): '+str([i for i in notes_changed if not may_change(i)]))
    paths_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('target_paths') != start_features[i].get('target_paths'))
    need(all(may_change(i) for i in paths_changed), 'features.json groups whose target_paths changed beyond the allowed groups: '+str([i for i in paths_changed if not may_change(i)]))
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    # The allowed groups may also append to their evidence and acceptance lists; every other field of every group stays as it was.
    free = lambda i: ('notes', 'target_watch', 'target_paths', 'reviewed_source_commit', 'source_paths', 'source_watch') + (('evidence', 'acceptance') if may_change(i) else ())
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in free(i)} !=
                          {k: v for k, v in start_features[i].items() if k not in free(i)})
    appended_only = sorted(i for i in by_id if i in start_features and may_change(i) and not all(by_id[i].get(k, [])[:len(start_features[i].get(k, []))] == start_features[i].get(k, [])
                                                                                                 for k in ('evidence', 'acceptance')))
    need(not shrunk and not other_fields and not appended_only, f'features.json previous groups lost target_watch entries {shrunk} or changed other fields {other_fields}'
         + ('' if not appended_only else f' (evidence / acceptance changed other than by appending: {appended_only})'))
    watch_grown = sorted(i for i, f in by_id.items() if i in start_features and set(f.get('target_watch', [])) - set(start_features[i].get('target_watch', [])))
    need(all(may_change(i) for i in watch_grown), 'features.json groups whose target_watch grew beyond the allowed groups: '+str([i for i in watch_grown if not may_change(i)]))
    source_changed = sorted(i for i, f in by_id.items() if i in start_features and (f.get('source_paths') != start_features[i].get('source_paths') or f.get('source_watch') != start_features[i].get('source_watch')))
    need(all(may_change(i) for i in source_changed), 'features.json groups whose source_paths / source_watch changed beyond the allowed groups: '+str([i for i in source_changed if not may_change(i)]))
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped; the main agent adds target_paths / target_watch to recipe-completion): '+str(unmapped[:6]))
    features_record = dict(new_group=NEW_FEATURE, notes_changed=notes_changed, target_paths_changed=paths_changed, target_watch_grown=watch_grown, source_lists_changed=source_changed,
                           product_groups_allowed=sorted(PRODUCT_GROUPS))

    # 7. Language and the generated tree: 4 new keys (all upstream: the rangefinder, the two radars and the plate auto-switch group); nothing changed or removed; the stamp must be current, the
    # generated additions the recipe, advancement, tag and item model set.
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
    need(en_delta == expected_en, 'generated en_us.json delta is not the 4 new keys: '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_zh, 'zh_cn.json delta is not the 4 new keys: '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_map, 'zh_cn-map.json delta is not the 4 new entries: '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal28b totals'
    delta_net = len(KEYS) - len(REMOVED_KEYS)
    need(len(en_now) == totals['en_us'] + delta_net and len(zh_now) == totals['zh_cn'] + delta_net and len(map_now) == totals['zh_cn_map'] + delta_net,
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal28b totals {totals} + {delta_net}')
    map_kinds, start_kinds = dict(Counter(e.get('kind') for e in map_now.values())), dict(Counter(e.get('kind') for e in map_start.values()))
    kinds_added = Counter((map_now.get(k) or {}).get('kind') for k in KEYS)
    expected_kinds = {k: start_kinds.get(k, 0) + kinds_added.get(k, 0) for k in set(start_kinds) | set(kinds_added)}
    expected_kinds = {k: v for k, v in expected_kinds.items() if v}
    need(start_kinds == totals['zh_cn_map_by_kind'] and map_kinds == expected_kinds and map_kinds.get('deferred') == EXPECTED['deferred_entries'],
         f'mapping kinds are {map_kinds}, expected the goal28b kinds {totals["zh_cn_map_by_kind"]} adjusted by the added keys {expected_kinds} (deferred {EXPECTED["deferred_entries"]} unchanged)')
    expected_added_kinds = {k: v for k, v in {'upstream': UPSTREAM_ADDED, 'local': LOCAL_ADDED}.items() if v}
    need(dict(kinds_added) == expected_added_kinds, f'new mapping entries are {dict(kinds_added)}, expected {UPSTREAM_ADDED} upstream (the rangefinder, the two radars and autoswitch.plates) and {LOCAL_ADDED} local')
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
    start_generated = start_stamp['generated']
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    changed_allowed = {EN_ENTRY}
    need(set(generated_changed) == changed_allowed, f'Generated resources changed since the start are not exactly en_us.json (every crafting recipe, advancement and tag of the start must stay byte-identical): {generated_changed[:8]}')
    recipe_added = [p for p in generated_added if GENERATED_ADDED.fullmatch(GENERATED_ROOT+p)]
    need(recipe_added == generated_added, f'Generated additions other than the 15 recipes, their advancements, the four item tags and the rangefinder model: {sorted(set(generated_added) - set(recipe_added))[:6]}')
    counts_added = dict(item_models=len([p for p in generated_added if '/models/item/' in p]), recipes=len([p for p in generated_added if p.startswith('data/hbmsntm/recipe/')]),
                        advancements=len([p for p in generated_added if '/advancement/' in p]), item_tags=len([p for p in generated_added if p.startswith('data/ntm/tags/item/')]))
    need(counts_added == GENERATED_COUNTS, f'generated additions are {counts_added}, the handoff expects {GENERATED_COUNTS}')
    need(sorted(GENERATED_ROOT+p for p in generated_added) == sorted(set(REQUIRED_GENERATED) | {GENERATED_ROOT+p for p in generated_added if '/advancement/' in p}),
         'generated additions differ from the expected set: extra %s, missing %s' % (sorted({GENERATED_ROOT+p for p in generated_added} - set(REQUIRED_GENERATED) - {GENERATED_ROOT+p for p in generated_added if '/advancement/' in p})[:6],
                                                                                    sorted(set(REQUIRED_GENERATED) - {GENERATED_ROOT+p for p in generated_added})[:6]))
    advancements = {n: [p for p in generated_added if re.fullmatch(r'data/hbmsntm/advancement/recipes/[a-z]+/'+n+'\\.json', p)] for n in RECIPE_NAMES}
    need(all(len(v) == 1 for v in advancements.values()), 'generated recipe advancements: exactly one per recipe expected: '+str(advancements))
    for path in (v[0] for v in advancements.values() if v):
        adv = read(ROOT/(GENERATED_ROOT+path))
        need(adv.get('rewards') == {'recipes': ['hbmsntm:'+Path(path).stem]}, f'{path} does not reward its own recipe')
    need(len(stamp['generated']) == prior_receipt['generated_resource_count'] + len(generated_added), f'generated resource count {len(stamp["generated"])} is not the goal28b count {prior_receipt["generated_resource_count"]} + {len(generated_added)}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted([STAMP] + [GENERATED_ROOT+p for p in generated_added] + [GENERATED_ROOT+p for p in generated_changed])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, the stamp additions and the stamp changes: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))

    # 8. Evidence: GameTest log, audits, Gradle logs, diff, the final suite run, the verifier report, the casting attribution, compare and the batch's own scripts and records.
    evidence = {}
    gametest_line = gametest_count = None
    recipe_lines = []
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
    recipe_test_names = sorted(GAMETEST_METHOD.findall((ROOT/RECIPE_TESTS).read_text(encoding='utf-8'))) if (ROOT/RECIPE_TESTS).is_file() else []
    recipe_annotations = annotations(ROOT/RECIPE_TESTS) if (ROOT/RECIPE_TESTS).is_file() else 0
    need(bool(recipe_test_names) and recipe_annotations == len(recipe_test_names), f'{RECIPE_TESTS} holds {recipe_annotations} @GameTest annotations and {len(recipe_test_names)} parsed methods (or the file does not exist yet)')
    need(gametest_added == recipe_annotations, f'GameTest sources grew by {gametest_added} tests, RecipeCompletionGameTests holds {recipe_annotations} (another GameTest class changed its test count, e.g. SmokeTestSupport?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in recipe_test_names), 'GameTest log lacks "[hbm-28c] <name> passed" for: '+str([n for n in recipe_test_names if (GAMETEST_MARKER % n) not in text]))
            recipe_lines = [l.split('[hbm-28c] ', 1)[1].strip() for l in text.splitlines() if '[hbm-28c] ' in l and ' passed' not in l.split('[hbm-28c] ', 1)[1]]
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries, audit_comparison = {}, {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal28c/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad_findings = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad_findings and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad_findings))
        # This batch adds language keys and resources, so the info / review counts may differ from the previous receipt: recorded, not required equal.
        audit_comparison[key] = dict(previous=prior_receipt['audits'][key], now=audit['summary'], equal=audit['summary'] == prior_receipt['audits'][key])
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal28c/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if name == 'production-vs-start.diff':
            if (OUT/name).is_file() and (OUT/name).stat().st_size > 0: evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)  # judged below
            continue
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal28c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    named = list(START_EVIDENCE) + list(REVIEW_EVIDENCE)
    named += sorted(p.name for pattern in ('handoff-*.md', '*-report.md', 'builder-*.log', 'builder_*.log', 'verifier-*.log') for p in OUT.glob(pattern) if p.name not in named)
    for name in named:
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal28c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/FAIL_SET_DIFF).is_file(): evidence[(OUT/FAIL_SET_DIFF).relative_to(ROOT).as_posix()] = sha(OUT/FAIL_SET_DIFF)
    # The casting regressions (goal27a_casting_regression_run.py, unchanged wrapper): one record per suite in the final rerun's own directory; its transcript is hashed with it.
    casting = {}
    for suite in CASTING_SUITES:
        rec_path = CASTING_DIR/f'{suite}-compat.json'
        if not need(rec_path.is_file(), f'evidence missing: build/migration/goal28c/final/castingsuites/{suite}-compat.json (goal27a_casting_regression_run.py {suite}, redirected into final/ by run_final.py)'): continue
        rec = read(rec_path)
        transcript = ROOT/rec['transcript'] if rec.get('transcript') else None
        casting[suite] = dict(record=rec_path.relative_to(ROOT).as_posix(), exit=rec.get('exit'), mode=rec.get('mode'), blockers=rec.get('blockers'), stages=rec.get('stages'),
                              javac_errors_by_attribution=rec.get('javac_errors_by_attribution'), transcript=rec.get('transcript'))
        evidence[rec_path.relative_to(ROOT).as_posix()] = sha(rec_path)
        if need(transcript is not None and transcript.is_file(), f'{rec_path.name} names no existing transcript'): evidence[transcript.relative_to(ROOT).as_posix()] = sha(transcript)
    attribution = None
    if need((OUT/CASTING_ATTRIBUTION).is_file(), 'evidence missing: build/migration/goal28c/'+CASTING_ATTRIBUTION+' (casting_attribution.py, after the final rerun)'):
        att = read(OUT/CASTING_ATTRIBUTION)
        problems = []
        if att.get('mode') != 'compare' or att.get('missing_inputs'): problems.append(f'mode {att.get("mode")!r}, missing inputs {att.get("missing_inputs")}')
        if att.get('baseline_sha256') != sha(BASELINE) or att.get('tool_sha256') != sha(OUT/'casting_attribution.py'): problems.append('written by another baseline or another version of casting_attribution.py')
        if att.get('old_dir') != (GOAL28B_OUT/'final/castingsuites').relative_to(ROOT).as_posix() or att.get('new_dir') != CASTING_DIR.relative_to(ROOT).as_posix(): problems.append(f'compares {att.get("old_dir")} with {att.get("new_dir")}')
        if sorted(att.get('suites', {})) != sorted(CASTING_SUITES): problems.append('suites '+str(sorted(att.get('suites', {}))))
        for suite, entry in att.get('suites', {}).items():
            for side in ('old', 'new'):
                s = entry.get(side) or {}
                if not s.get('parse_matches_record'): problems.append(f'{suite} {side}: the parsed javac errors do not match the record')
                if side == 'new' and suite in casting and s.get('record_sha256') != sha(ROOT/casting[suite]['record']): problems.append(f'{suite}: the new record changed after the attribution')
            for e in entry.get('new_errors', []) + entry.get('moved', []):
                file = e.get('at', '').rsplit(':', 1)[0] if 'at' in e else (e.get('identity') or {}).get('file', '')
                if e.get('attribution') == 'unattributed': problems.append(f'{suite}: unattributed error {e.get("at") or e.get("identity")}')
                elif e.get('attribution') == '28C change' and file not in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed to a 28C change but the file did not change')
                elif e.get('attribution') == 'not 28C' and file in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed "not 28C" but the file changed')
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
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal28c/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files and edited GameTests against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    diffed_modified = [p for p in modified_java + gametest_edit_files if p in changes]
    listed_in_diff = NEW_JAVA + diffed_modified
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal28c/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in diffed_modified) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(p in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([p for p in listed_in_diff if p not in diff_text]))
    final = None
    # The suites of the goal28b final run plus the Goal28C verifier (the two casting regressions are in the goal28b set and run unchanged, redirected into final/; verify_goal28b_worldgen.py is an old suite now).
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal28b final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal28C suite is already in the goal28b final run'
    assert OLD_SUITE_28B in reference_suites, 'The goal28b final run does not hold the Goal28B verifier: '+OLD_SUITE_28B
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal28c/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal28b final set + the Goal28C verifier: '+str(sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal28c/'+VERIFY_REPORT+' (tools/migration/verify_goal28c_recipes.py report; run it with --gametest-log and --jar after the final build)'):
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
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=VERIFY_TOOL,
                        tool_sha256=sha(ROOT/VERIFY_TOOL) if (ROOT/VERIFY_TOOL).is_file() else None, mutations_detected=f'{detected}/{total}', mutations_total=total,
                        checks_passed=summary_part.get('checks_passed'), command=report.get('command'))
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(re.findall(r'(?:AssemblyMachineRecipes|CraftingManager|WeaponRecipes|ToolRecipes|MineralRecipes|ItemCircuit|OreDictManager|Mats|ModItems|ModBlocks|'
                                                    r'GenericRecipe|GenericRecipes|ItemRangefinder|BlueprintFolderItem)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # The compare: the original did not move since the 28A observation point (unchanged in 28B), so ONE compare, against review-4f5924e2b9e1.json (the snapshot is not rewritten). Original 0/0/0.
    # The target set is this batch's own compare-inventory paths (added = absent from the snapshot, modified = present) plus the residual between the snapshot and the start (computed from the
    # snapshot's raw hashes: the snapshot is the Goal28A tree, so the residual is the Goal28B delivery's compare-inventory paths; the 28B compare listed them as its own target set).
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
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal28c/'+COMPARE+' (compare against '+SNAPSHOT+': original 0/0/0, target set of %d paths = this batch\'s %d compare-inventory paths + %d residual)' % (
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

    # 9. JAR: build/libs is what gets packaged; delta against the previous package (goal28b), every entry owned by goal28c or a recompile.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the goal28b package (run the final build)')
    if True:  # --check also runs the delta code (against the current build/libs, which is still the goal28b package until the final build)
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
            need(en_jar == expected_en and zh_jar == expected_zh, 'JAR en_us.json / zh_cn.json differ from the goal28b package by something other than the Goal28C delta: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
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
        need(not unowned, 'JAR entry without an owner (only classes of the owner-table Java sources and the edited older GameTests, the generated additions / changes (the 15 recipes and '
             'advancements, the four item tags, the rangefinder model, en_us.json), zh_cn.json, the imported texture and META-INF/MANIFEST.MF are owned): '+str(unowned[:10]))
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in production_java if p in changes]
        allowed_classes = set(changed_java)
        need(set(class_owners) <= allowed_classes and set(changed_java) <= set(class_owners),
             'Changed Java sources and goal28c JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners))) + '; unexpected: '+str(sorted(set(class_owners) - allowed_classes)))
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

    need(small_fixes_after_goal28b == [], 'migration/README.md (start copy) names small fixes above the Goal28B line (they would be packaged with goal28c; list them in the receipt): '+str(small_fixes_after_goal28b))

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added), generated_modified=generated_changed,
                   generated_added_counts=counts_added, imported_textures=sorted(imported), start_drift=sorted(drift_report), repinned_since_goal28b_start=sorted(repinned),
                   small_fixes_after_goal28b=small_fixes_after_goal28b,
                   language_delta=dict(en=en_delta, zh=zh_delta, map=map_delta), language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, line_endings=line_endings, content_rules=content_rules, assembler_rule=assembler_rule,
                   gametest_edits={p: dict(added=e['added'], removed=e['removed'], rule_holds=e['rule_holds']) for p, e in gametest_edits.items()},
                   recipe_completion={k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v, default=str)) < 200 else f'<{len(v)} items>') for k, v in facts.items()}, recipe_completion_facts_bad=bad,
                   assembler_rows_ok=sorted(k for k, v in rows_facts.items() if v['ok']), crafting_ok=sorted(k for k, v in crafting.items() if v['ok']), features=features_record,
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_recipe_tests=recipe_test_names, final_suites_expected=final_expected,
                   audit_comparison=audit_comparison,
                   casting_regressions={s: dict(exit=c['exit'], mode=c['mode'], blockers=len(c['blockers'] or []), javac_errors_by_attribution=c['javac_errors_by_attribution']) for s, c in casting.items()},
                   casting_attribution=opt(attribution, 'summary'),
                   compare=opt(compare, 'counts'), compare_target_expected=len(expected_target), compare_added_expected=len(expected_added), compare_own_paths=len(own_target),
                   compare_residual=dict(modified=len(residual_modified), added=len(residual_added), removed=len(residual_removed)),
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
    recipe_completion = dict(neo=MODIFIED_JAVA, original=O_SOURCES, facts=facts, expected=EXPECTED, known_differences=KNOWN_DIFFERENCES, original_references=original_refs,
                             assembler_rows={k: dict(original_line=v['original_line'], neo_line=v['neo_line'], original=v['original'], neo=v['neo'], ok=v['ok']) for k, v in rows_facts.items()},
                             assembler_rule=assembler_rule, crafting_recipes=crafting, item_tags=tags, rangefinder=facts.get('rangefinder'), candidate_table=candidate_table,
                             not_registered=dict(assembler=NOT_REGISTERED_ROWS, crafting={n: inp for n, (_, _, inp) in CRAFTING_NOT_REGISTERED.items()}),
                             deferrals=dict(goal28_decision5='bombs, missiles, launch pads, satellites and the PWR controller rows stay out with their systems (assembler-diff.json decisions)',
                                            expensive_lists='the inputItemsEx lists (item_expensive) are not migrated',
                                            rangefinder_ranging='the rangefinder is a crafting material only; ItemRangefinder\'s ranging is not migrated',
                                            radar_behaviour='the radar and large radar get recipes and names only; their behaviour is not completed in this batch',
                                            platemixed='ass.platemixed waits for the Goal28D saturnite plates (GOAL28 decision 4)',
                                            goal13b_b4='ass.chipBismoid, ass.chipQuantum and ass.atomicClock stay deferred with their inputs (GOAL13B B4); ass.atomicClockAlt is registered',
                                            follow_up='ass.pistonsetstar (starmetal ingot), the five capacitor rows (battery_pack subtypes), ass.alclad and ass.titaniumconstruction (part_generic ALCLAD) are follow-up candidates',
                                            weapon_steel_plate='ass.plateweaponsteel: NEO has no plate_weaponsteel',
                                            crafting='det_nuke (man_core), mine_shrap (pellet_buckshot) and mine_fat (ammo_standard) have no NEO input'),
                             language_keys=language_keys, local_language_keys=local_keys, imported_resources=imported_facts, resource_ownership_record=RESOURCE_OWNERSHIP, reachability_record=LEDGER,
                             recipe_lines_from_gametest_log=recipe_lines,
                             note=f'Recipe completion: {EXPECTED["assembler_rows_added"]} assembler rows appended to the {EXPECTED["assembler_rows_start"]} pre-batch rows (setup, product, input counts in the original '
                                  'order, the alt.plates pool and the autoswitch.plates group of the 12 plate rows, 528 pools: none (NEO has no 528 blueprint source), the overdrive rows outside 528 mode); '
                                  f'{EXPECTED["crafting_recipes"]} crafting recipes (shapes and counts of CraftingManager.java:319-323, 520-524, 852, WeaponRecipes.java:297-299, ToolRecipes.java:104 and '
                                  'the MineralRecipes.java:58 slag pair); four ntm: item tags (OreDictManager.java:311, 313, 502 and CU at :162); the rangefinder item (stack size 1, crafting material only) with its '
                                  'original texture; four upstream language keys. The candidate table is tools/migration/goal28c_assembler_diff.py -> assembler-diff.json (the start table) and assembler-diff-after.json (the rerun on the settled tree; decisions recorded per row).')
    casting_record = dict(attribution=attribution, suites=casting, wrapper='tools/migration/goal27a_casting_regression_run.py (unchanged)', policy='tools/migration/goal27a_casting_compat.py (unchanged)',
                          note='The two frozen isolated casting regressions (verify_goal10a.py, verify_goal5a_casting.py) run through the unchanged Goal27A wrapper in the final rerun, redirected into '
                               'build/migration/goal28c/final/castingsuites; both already stopped at javac on the Goal26D to Goal28B trees, so none of their assertions is reached. casting-attribution.json '
                               'pairs the javac errors of the Goal28B final run with the Goal28C run and attributes every new or moved error by file to a Goal28C change or to "not 28C"; it is evidence about javac '
                               'in the frozen stub worlds only.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(recipe_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   uncommitted_start=uncommitted_start,
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, reconstruction=base['reconstruction'], push_commit_parent=chain[1], untrack_commit=chain[2], goal27_delivery_commit=chain[3],
                                      small_fixes_after_goal28b=small_fixes_after_goal28b,
                                      note=f'The start tree is HEAD 66a00353 (the mod rename, = origin/master) with the UNCOMMITTED Goal28A-28B delivery in the worktree ({len(base["modified_at_start"])} modified and '
                                           f'{len(base["untracked_at_start"])} untracked files, packaged as goal28a and goal28b and never committed). migration/ is Git-ignored: freeze_start.py hashed every tracked and '
                                           f'untracked non-ignored file ({tracked_count} baseline hashes, disk content) and every file under migration/ from disk ({len(base["migration_files"])} migration hashes) before '
                                           f'the first 28C write and copied {len(base["copied_scope"])} planned, modified and untracked files (baseline-files). build/libs at the start is the goal28b package '
                                           f'{start_jar_sha[:8]}; no small fix lies between the goal28b package and this start, so the JAR delta against the goal28b package is entirely this batch. The original did '
                                           'not move (4f5924e2b); paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, line_endings=line_endings, content_rules=content_rules, gametest_edits=gametest_edits, start_copies_supplement=[],
                   recipe_completion=recipe_completion, casting_attribution=casting_record, features=features_record,
                   language=dict(changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']), added=dict(en_us=en_delta['added'], zh_cn=zh_delta['added'], zh_cn_map=map_delta['added']),
                                 removed=dict(en_us=en_delta['removed'], zh_cn=zh_delta['removed'], zh_cn_map=map_delta['removed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds), jar_delta=language,
                                 start_sha256={p: base['files'][p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD, LANG_PROVIDER)},
                                 note='Goal28C adds 4 keys, all upstream: item.hbmsntm.rangefinder (item.rangefinder.name), block.hbmsntm.machine_radar and block.hbmsntm.machine_radar_large '
                                      '(tile.machine_radar.name, tile.machine_radar_large.name; the two radar blocks had no language entry in NEO before) and autoswitch.plates (the plate group); '
                                      f'nothing is changed or removed; the {EXPECTED["deferred_entries"]} deferred entries are unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith(CARRIED_REPINS)},
                   repinned_since_goal28b_start={p: dict(goal28b_start_pin_sha256=h, goal28c_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok'), old_machine_suites_through=OLD_MACHINE_SUITES, casting_suites_through=['goal27a_casting_regression_run.py verify_goal10a',
                                                                                                                                                                            'goal27a_casting_regression_run.py verify_goal5a_casting']),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_recipe_tests=recipe_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, RecipeCompletionGameTests (names in new_recipe_tests): what those tests '
                                      'assert about the assembler rows (inputs, outputs, setup, pools, the plate group, the 528 gate), the blueprint pool lists, the template round trip, the crafting '
                                      'recipes through the server RecipeManager (exact and one-wrong inputs, the lava bucket remainder, tag members), the rangefinder item and the four tags; no client '
                                      '(the assembler GUI, the JEI screens, the item icon and the tooltips are not drawn), no real player, no saved world, no survival crafting chain.'),
                   audits=audit_summaries, audit_comparison=audit_comparison, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + [p for p in OPTIONAL_RECORDS if p in changes],
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['overworld_worldgen (the Goal28B-only domain key; Goal28C adds recipe_completion)',
                                 'upstream / compare.old / snapshot.new (the original did not move this batch: no classification, no old compare, no new snapshot; the compare is against review-4f5924e2b9e1)',
                                 'small_fixes / ledger_edit (no small fix and no ledger edit since the goal28b package; start_content.small_fixes_after_goal28b is the empty check)',
                                 'casting_regressions (the Goal27A key; Goal28C carries casting_attribution as Goal27B to Goal28B did: the wrapper and the two suites are unchanged, only their javac errors are attributed)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the assembler candidate table rerun, the final old-suite rerun (the old isolated suites through the goal26c wrapper and the two casting regressions through the '
                            'unchanged goal27a wrapper, whose javac errors are attributed by casting_attribution.py), one compare against the review-4f5924e2b9e1 snapshot, and one static review. No '
                            'in-game client test was run: no recipe was crafted by a real player, the assembly machine GUI, the blueprint folders, the JEI assembler and crafting categories, the '
                            'rangefinder icon and the Chinese UI are not seen on screen; no survival chain (making the inputs and building a pumpjack, radar or turbine) was run; no dedicated server '
                            'beyond GameTest; the Goal 28 acceptance checklist GOAL28C-ACCEPTANCE.md is written, not run.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False, default=str))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal28c JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal28b package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
