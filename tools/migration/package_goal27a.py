"""Package Goal27A (the first batch of Goal 27, the material system: the original 109-material table in Mats with the NEO item-to-material registry MaterialEntries,
MatDistribution and its config file hbmCrucibleSmelting.json, multi-material crucible smelting, scraps for every smeltable material with JEI smelting groups,
14 shredder rows completing the original ingot/gem -> dust rule, the seven missing effect icons, 90 language keys, MaterialSystemGameTests), cumulatively on the
goal26d package, without replacing any previous delivery. It also packages the D2 small fix made after goal26d (util/ContaminationUtil.java:101-102 3.6F -> 3.6D,
README small-fix line of 2026-10-23, committed in 0786697d), which no package holds yet.

python -B -X utf8 tools/migration/package_goal27a.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal27a/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal27a/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal27a/baseline.json: NEO HEAD 71c2f660 (the Goal 27 planning commit, local, not pushed; 8 files) on the Goal 26 close-out
0786697d (pushed, = origin/master) with a CLEAN worktree (0 status lines): freeze_start.py hashed every tracked file live (10,573 hashes) before the first 27A
write and copied the 38 files the batch planned to touch into baseline-files/; start_status.txt (empty), start_head.txt and start_hashes.txt (empty) record it.
The start bytes of a file are HEAD = baseline files; there are no uncommitted deliveries (uncommitted_start is recorded empty). build/libs at the start is NOT the
goal26d package: it is the post-D2 small-fix build (61436747...a0d0, baseline build_libs_jar_sha256_at_freeze); ContaminationUtil.java must equal its start bytes
and the D2 class in the JAR delta is owned by the D2 small fix, not by goal27a. The original HEAD aee05a40f did not move since 24A, so there is no upstream
classification and no new snapshot. Every change since the start is computed from the baseline file hashes (not from git diff) and must be in the owner table
below; every other path must still equal its start hash. The modified production files are compared with their start bytes (baseline-files, else the
start-commit blob) and their +/- lines are reported. The JAR delta against the goal26d package is attributed per entry; any entry without exactly one owner
fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys, materials, rows) are computed here from the
original and NEO sources where they can be; the expected material-system figures the handoff states are asserted against those computations.

The receipts that hash records (goal21a..goal26d, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start: the goal26d
receipt for migration/GOAL26D-ACCEPTANCE.md and migration/GOAL25D-ACCEPTANCE.md (filled in by the Goal 26 unified acceptance after the goal26d package and
committed in 0786697d: baseline previous_receipt_evidence_drift), the older receipts for the acceptance checklists, GOAL21D.md, GOAL22C.md,
goal21d-static-review.md and the goal24a working notes (known from earlier batches); they are listed in the receipt as start drift and must still equal their
Goal27A start hash; no receipt is rewritten and no other protected path may drift. GOAL27B/C/D.md, GOAL27-THREAD-PROMPTS.md (the planning documents of
71c2f660), every Goal 26 and earlier record and SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL27.md is a shared record edited by the main
agent, GOAL27A.md the task book and delivery record (hashed by the receipt).

Like the packagers of 24B..26D this one has a single compare run (build/migration/goal27a/compare.json against the snapshot review-aee05a40f10f.json taken at the
end of 24A: original 0/0/0, target = exactly the goal26d compare target paths (24A-26D, read from build/migration/goal26d/compare.json) plus this batch's
compare-inventory paths), no upstream classification; it adds the material_system facts (checked against the original and NEO source texts). The Goal26D-only
receipt key radiation_medicine (and its recipes / sound keys) is dropped."""
from collections import Counter
from pathlib import Path
import argparse
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
from package_goal22b import (git_ro, edit_counts, stale_diff, receipt_protected, start_drift_paths, strip_java_comments,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE
from package_goal23b import report_problems
from package_goal24a import original_text, original_line, original_blob, lang_file, provider_keys as base_provider_keys, SOURCE_HEAD
from package_goal26d import OUT as GOAL26D_OUT, BASELINE as GOAL26D_BASELINE, protected_paths as goal26d_protected_paths

OUT = ROOT/'build/migration/goal27a'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
START_HASHES = OUT/'start_hashes.txt'
REFERENCE_PREVIOUS = GOAL26D_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL26D_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal26d/hbmsntm-198A-goal26d.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal27a'
RELEASE_NAME = 'hbmsntm-198A-goal27a.jar'
OWNER = 'goal27a'
PREVIOUS_OWNER = 'goal26d'
# The D2 small fix after goal26d (README small-fix line of 2026-10-23; committed in 0786697d), first packaged by goal27a.
D2_OWNER = 'small-fix-d2-after-goal26d'
D2_SOURCE = 'src/main/java/com/hbm/util/ContaminationUtil.java'
D2_LIBS_SHA = '61436747e63e30890cde44d947b19f8e37e85ca45aade17de039a3472171a0d0'
PLANNING_PREFIX = '71c2f660'
PLANNING_FILES = 8
GOAL26_CLOSEOUT = '0786697d'
GOAL26_PLANNING = '6bfb7ad2'
START_STATUS_LINES = 0
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a', 'goal26b', 'goal26c'}
# The two records the goal26d receipt hashes that the Goal 26 acceptance filled in and 0786697d committed after the goal26d package (baseline previous_receipt_evidence_drift).
PREVIOUS_DRIFT = {'migration/GOAL26D-ACCEPTANCE.md', 'migration/GOAL25D-ACCEPTANCE.md'}

# Production (owner goal27a), NEW (handoff-packaging.md; builder-report.md and verifier-report.md name the classes: a differently named or extra class is reported
# by --check as an unassigned src/ path). MaterialSystemGameTests is the GameTest verifier's class.
NEW_JAVA = [J+p+'.java' for p in ('inventory/material/MaterialEntries', 'inventory/material/MatDistribution', 'gametest/MaterialSystemGameTests')]
(ENTRIES_JAVA, DISTRIBUTION_JAVA, MATERIAL_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start; every other src/ change fails).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'inventory/material/Mats', 'inventory/material/MaterialShapes', 'inventory/recipes/CopperCastingRecipes', 'inventory/recipes/loader/SerializableRecipe',
    'inventory/recipes/ShredderRecipes', 'blockentity/machine/MachineCrucibleBlockEntity', 'items/CopperScrapsItem', 'inventory/NtmCreativeTabs',
    'datagen/NtmItemModelProvider', 'datagen/NtmLanguageProvider', 'handler/jei/CrucibleSmeltingRecipeHandler', 'handler/jei/NtmJeiPlugin')]
(MATS, SHAPES, CASTING, SERIALIZABLE, SHREDDER, CRUCIBLE, SCRAPS, CREATIVE_TABS, ITEM_MODEL_PROVIDER, PROVIDER, SMELTING_JEI, JEI_PLUGIN) = MODIFIED_JAVA
OPTIONAL_JAVA = []
OLDER_GAMETEST_DIR = J+'gametest/'
# Must stay byte-identical to the start (the handoff list; FoundryMoldBlockEntity's real path is blockentity/machine/), plus every older GameTest class (the
# verifier report names no edit): see older_gametests_frozen in main().
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'lib/ModEffect', 'inventory/recipes/CrucibleRecipes', 'blockentity/machine/FoundryMoldBlockEntity', 'items/CastPlateItem', 'items/WireDenseItem', 'items/BoltItem',
    'items/RawIngotItem', 'inventory/material/NTMMaterial', 'inventory/RecipesCommon', 'inventory/MetaHelper', 'main/NuclearTechModClient', 'main/NuclearTechMod',
    'main/CommonEvents', 'util/ContaminationUtil')]
assert D2_SOURCE in UNCHANGED_JAVA
# Modified sources whose compiled class need not change (comment-only edits); every other modified source must show a modified class in the JAR.
SAME_CLASS_JAVA = []
NO_CLASS_JAVA = []
# JAR classes whose source is unchanged since the start and that differ from the previous package only in recompiled debug names (as in 26A-26D).
RECOMPILE_ONLY = {'com/hbm/gametest/RBMKRecyclingGameTests$1.class': (((b'\x01\x00\x04arg0', b'\x01\x00\x03pos'), (b'\x01\x00\x04arg1', b'\x01\x00\x05state')),
                                                                    ((b'\x01\x00\x03pos', b'\x01\x00\x04arg0'), (b'\x01\x00\x05state', b'\x01\x00\x04arg1')))}
RECOMPILE_OWNER = 'recompile-debug-names'
# Insert-only against the start bytes: the language provider, the loader registration, the Chinese file and the mapping (builder / language reports: pure additions).
STRICT_INSERT_ONLY = [PROVIDER, SERIALIZABLE, ZH_INPUT, LOCALIZATION_RECORD]
# Rewritten or edited in place by the batch (builder-report.md, main-notes.md decisions and review fixes): start lines may be removed; the +/- counts are reported,
# not judged line by line (the material-system facts below judge the content).
REWRITTEN_JAVA = [MATS, SHAPES, CASTING, SHREDDER, CRUCIBLE, SCRAPS, CREATIVE_TABS, ITEM_MODEL_PROVIDER, SMELTING_JEI, JEI_PLUGIN]
assert set(STRICT_INSERT_ONLY[:2]) | set(REWRITTEN_JAVA) == set(MODIFIED_JAVA)
# The added lines of these insert-only files must be exactly the lines of the batch (comments and blanks excepted); the language provider is judged by its key list.
ADDED_CODE_RULES = {
    SERIALIZABLE: re.compile(r'import com\.hbm\.inventory\.material\.MatDistribution;|recipeHandlers\.add\(new MatDistribution\(\)\);'),
}
# Imported original resources (byte imports, migration/goal27a-resource-ownership.json "imported_assets"): NEO target -> original path; scraps.png is imported
# renamed as scraps_plain.png (the uncoloured base for light == dark materials).
ASSETS = {ASSETS_ROOT+'textures/item/scraps_additive.png': O_RES+'textures/items/scraps_additive.png',
          ASSETS_ROOT+'textures/item/scraps_bismuth.png': O_RES+'textures/items/scraps_bismuth.png',
          ASSETS_ROOT+'textures/item/scraps_plain.png': O_RES+'textures/items/scraps.png'}
RENAMED = {ASSETS_ROOT+'textures/item/scraps_plain.png': 'scraps.png -> scraps_plain.png'}
SCRAP_TEXTURES_TOOL = 'tools/migration/goal27a_scrap_textures.py'
EFFECT_ICONS_TOOL = 'tools/migration/goal27a_effect_icons.py'
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
SCRAPS_MODEL_ENTRY = 'assets/hbmsntm/models/item/scraps.json'
GENERATED_SCRAPS_MODEL = GENERATED_ROOT+SCRAPS_MODEL_ENTRY
GENERATED = [STAMP, EN, GENERATED_SCRAPS_MODEL]
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, SCRAPS_MODEL_ENTRY])
SCRAP_MODEL = re.compile(r'assets/hbmsntm/models/item/scraps_[a-z0-9_]+\.json')
NEW_TOOLS = ['tools/migration/verify_goal27a_material_system.py', 'tools/migration/package_goal27a.py', SCRAP_TEXTURES_TOOL, EFFECT_ICONS_TOOL,
             'tools/migration/goal27a_casting_regression_run.py', 'tools/migration/goal27a_casting_compat.py']
TOOLS = NEW_TOOLS
# Older tools that must equal their start bytes (handoff list); every file of the two frozen casting regression folders is added in main().
OLD_TOOLS_FROZEN = ['tools/migration/'+p for p in ('goal26c_oldsuite_run.py', 'goal26c_oldsuite_compat.py', 'verify_goal10a.py', 'verify_goal10a_resources.py',
                                                    'verify_goal5a_casting.py', 'verify_goal5a_casting_resources.py', 'goal10a_scrap_textures.py', 'goal10a_mutation_check.py')]
FROZEN_TOOL_DIRS = ('tools/migration/goal10a_regression/', 'tools/migration/goal5a_casting_regression/')
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal27a-* or GOAL27A-* record is hashed as well.
REPORTS = ['migration/GOAL27A.md', 'migration/GOAL27A-ACCEPTANCE.md', 'migration/goal27a-static-review.md', 'migration/goal27a-localization-review.json',
           'migration/goal27a-resource-ownership.json', 'migration/goal27a-materials-review.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal27a-[^/]+\.(json|md)|GOAL27A-[^/]+\.md)')
GOAL27_RECORD = 'migration/GOAL27.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md',
                  'migration/RESOURCE-OWNERSHIP.md', GOAL27_RECORD]
# Shared records the batch may leave untouched (RESOURCE-OWNERSHIP.md "if touched").
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
# The Goal 27 planning documents of the other batches (planning commit 71c2f660) and SURVIVAL-PLAYABILITY.md: no change is expected in this batch.
PLANNING_FROZEN = ['migration/GOAL27B.md', 'migration/GOAL27C.md', 'migration/GOAL27D.md', 'migration/GOAL27-THREAD-PROMPTS.md', 'migration/SURVIVAL-PLAYABILITY.md']
# Every Goal 26 and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 26).
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-6])(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-6])(?!\d)[a-z]?-[^/]+)')
# Must have changed (or been added) by the time of the real run; the generated additions are checked against the scraps model overrides.
REQUIRED_CHANGES = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD] + GENERATED + TOOLS + REPORTS + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]
# The six local language keys (language-report.md, main-notes 9); every other new key is upstream. Two upstream entries deviate in English, with the original in source_en.
LOCAL_KEYS = {'hbmmat.ilmenite', 'hbmmat.coalcoke', 'hbmmat.lignitecoke', 'hbmmat.ghiorsium336', 'hbmmat.polycarbonate', 'casting.scraps.additive'}
EN_DEVIATIONS = {'hbmmat.mingrade': 'Red Copper', 'hbmmat.cmbsteel': 'CMB Steel'}
EXTRA_KEYS = ['casting.scraps.additive']
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-material] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the sessions of the batch.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'freeze-dry.log', 'start_compile.log', 'start_status.txt', 'start_head.txt',
                  'start_hashes.txt', 'planning-commit-msg.txt', 'main-notes.md', 'handoff-builder.md', 'builder-report.md', 'handoff-resources.md', 'resources-report.md',
                  'handoff-language.md', 'language-report.md', 'handoff-verifier.md', 'verifier-report.md', 'handoff-packaging.md', 'review-report.md', 'chain.sh',
                  'make_production_diff.py', 'inventory_entries.py', 'build_tables.py', 'make_handoff_tables.py', 'make_ledger.py', 'icon_precedent.py', 'icon-precedent.json',
                  'add_foundations.py', 'lang_analyze.py', 'lang_apply.py', 'lang_check.py', 'lang_consistency.py', 'lang_data.py', 'lang_probe.py')
# The batch inventory (json and txt files under inventory/) and the casting-regression records (castingsuites/<suite>-compat.json and the transcripts they name).
INVENTORY_DIR = OUT/'inventory'
CASTING_DIR = OUT/'castingsuites'
CASTING_SUITES = ('verify_goal10a', 'verify_goal5a_casting')
# Review files under OUT the main agent names when it knows them; each must exist and is indexed by the receipt. Extend this list from the real run; --check lists the
# top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_loc_review.py', 'update_features.py', 'make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier-gt/scope-start.txt', 'verifier-gt/scope-end.txt', 'verifier-progress.md',
                   'builder-progress.md', 'builder_compile.log', 'lang_check.log', 'verify-final.out', 'compare.log', 'localization-final.log', 'resources-audit-final.log',
                   'packaged-resources-final.log')
GAMETEST_LOG = 'build/migration/goal27a/gametest-final.log'
NEW_SUITE = 'verify_goal27a_material_system.py --gametest-log build/migration/goal27a/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# Suites other than NEW_SUITE the final rerun adds: the two frozen casting regressions through the Goal27A wrapper (EXTRA in run_final.py; they count in "suites").
EXTRA_FINAL_SUITES = {'goal27a_casting_regression_run.py verify_goal10a', 'goal27a_casting_regression_run.py verify_goal5a_casting'}
FEATURE_MATERIALS = 'material-system'
NEW_FEATURES = (FEATURE_MATERIALS,)
# The previous groups whose notes the batch may change (handoff: crucible-alloying, shredder and the effect-icon group hazard-system).
NOTES_MAY_CHANGE = {'crucible-alloying', 'shredder', 'hazard-system'}
# The groups the snapshot of the end of 24A predates (24B..26D).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser', 'rbmk-autoloader', 'rbmk-crane',
                          'hazard-system', 'radiation-detection', 'gas-masks', 'hazmat-suits', 'radiation-medicine'}
RADIATION_NOTE = 'Goal27A: radioactive ores and scraps now melt in the crucible; handle them only in a disposable world. '
MELTDOWN_NOTE = 'Goal27A: no new meltdown path. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_MATS = ORIGINAL+'inventory/material/Mats.java'
O_NTMMATERIAL = ORIGINAL+'inventory/material/NTMMaterial.java'
O_SHAPES = ORIGINAL+'inventory/material/MaterialShapes.java'
O_DISTRIBUTION = ORIGINAL+'inventory/material/MatDistribution.java'
O_OREDICT = ORIGINAL+'inventory/OreDictManager.java'
O_CRUCIBLE = ORIGINAL+'tileentity/machine/TileEntityCrucible.java'
O_SCRAPS = ORIGINAL+'items/machine/ItemScraps.java'
O_AUTOGEN = ORIGINAL+'items/special/ItemAutogen.java'
O_CRUCIBLE_RECIPES = ORIGINAL+'inventory/recipes/CrucibleRecipes.java'
O_SHREDDER = ORIGINAL+'inventory/recipes/ShredderRecipes.java'
O_SERIALIZABLE = ORIGINAL+'inventory/recipes/loader/SerializableRecipe.java'
O_RECIPES_COMMON = ORIGINAL+'inventory/RecipesCommon.java'
O_MOLD = ORIGINAL+'items/machine/ItemMold.java'
O_POTION = ORIGINAL+'potion/HbmPotion.java'
O_NEI_SMELTING = ORIGINAL+'handler/nei/CrucibleSmeltingHandler.java'
O_POTIONS_ATLAS = O_RES+'textures/gui/potions.png'
O_SOURCES = [O_MATS, O_NTMMATERIAL, O_SHAPES, O_DISTRIBUTION, O_OREDICT, O_CRUCIBLE, O_SCRAPS, O_AUTOGEN, O_CRUCIBLE_RECIPES, O_SHREDDER, O_SERIALIZABLE, O_RECIPES_COMMON,
             O_MOLD, O_POTION, O_NEI_SMELTING, O_LANG_EN, O_LANG_ZH, O_POTIONS_ATLAS]
# The original sources the new mapping group must list (source_paths or source_watch; plus the imported resources).
FEATURE_SOURCES = {FEATURE_MATERIALS: [O_MATS, O_NTMMATERIAL, O_SHAPES, O_DISTRIBUTION, O_OREDICT, O_CRUCIBLE, O_SCRAPS, O_AUTOGEN, O_LANG_EN, O_LANG_ZH]
                   + list(ASSETS.values())}
# Sources of the batch that an existing group already maps (the shredder rows belong to the shredder group, whose notes may change).
EXISTING_GROUP_SOURCES = {'shredder': [O_SHREDDER]}
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'mats_first_declaration': (O_MATS, 'public static final NTMMaterial MAT_WOOD'), 'mats_make_smeltable': (O_MATS, 'public static NTMMaterial makeSmeltable(int id, DictFrame dict, int solidColorLight'),
    'mats_lookup': (O_MATS, 'public static List<MaterialStack> getMaterialsFromItem(ItemStack stack)'), 'mats_ore_entries': (O_MATS, 'List<MaterialStack> oreEntries = materialOreEntries.get(name);'),
    'mats_item_entries': (O_MATS, 'List<MaterialStack> entries = materialEntries.get(new ComparableStack(stack).makeSingular());'),
    'mats_conversion': (O_MATS, '(int) (x.amount * x.material.convOut / x.material.convIn)'),
    'distribution_file': (O_DISTRIBUTION, 'return "hbmCrucibleSmelting.json";'), 'distribution_handler': (O_SERIALIZABLE, 'recipeHandlers.add(new MatDistribution());'),
    'crucible_try_smelt': (O_CRUCIBLE, 'protected boolean trySmelt()'), 'crucible_is_item_smeltable': (O_CRUCIBLE, 'public boolean isItemSmeltable(ItemStack stack)'),
    'scraps_sub_items': (O_SCRAPS, 'public void getSubItems(Item item, CreativeTabs tab, List list)'), 'scraps_additive': (O_SCRAPS, 'Additive, not castable!'),
    'comparable_stack_meta': (O_RECIPES_COMMON, 'this.meta = stack.getItemDamage();'), 'comparable_stack_hash': (O_RECIPES_COMMON, 'result = prime * result + meta;'),
    'mold_fragment': (O_MOLD, 'if(registry.contains("fragment")) continue;'),
    'shredder_wildcard': (O_SHREDDER, 'comp.meta = OreDictionary.WILDCARD_VALUE;'),
    'potion_icons': (O_POTION, 'effect.setIconIndex(x, y);'),
}
EXPECTED = dict(materials=109, conversions=8, scrap_materials=82, entries_rows=375, entries_neo_only=5, entries_materials=98, distribution_rows=60, shredder_rows=14,
                effect_icons=7, language_keys=90, language_upstream=84, language_local=6, imported_assets=3, derived_scrap_textures=71, unchanged_assets=8, plain_scrap_materials=5)
# Known source differences the batch deliberately leaves (recorded; not asserted equal). main-notes.md decisions 1-10, review-report.md P2-1..P3-3, the GameTest defect.
KNOWN_DIFFERENCES = {
    'zero_quantum_ores': 'decision 1: upstream isItemSmeltable accepts an ore whose prefix match yields ORE.q(1) = 0 and trySmelt consumes it for 0 (TileEntityCrucible.java:455-503, 375-402); NEO registers no ORE / ORENETHER / ANY '
                         'shape rows, ores melt only through their MatDistribution item entries and zero-yield ores are rejected (NEO-only)',
    'ore_dictionary': 'decision 2: NEO has no ore dictionary; every MatDistribution ore key becomes one identical row per NEO ore item and variant (deepslate, scorched, gneiss, nether), stone / cobblestone '
                      'become Items.STONE / COBBLESTONE, copper ore the vanilla copper ores; config "item" inputs -> Mats.materialEntries, "tag" inputs -> Mats.materialOreEntries keyed by tag id, checked first',
    'registry_table': 'decision 3: MaterialEntries lists the original OreDictManager order, the Forge 1.7.10 vanilla names, the autogen loop mapped to NEO items, then the NEO-only rows (vanilla copper ingot / block '
                      'since Goal 5A, the vanilla iron nugget (decision 10), welded lead and welded HSS plates); items NEO lacks are not registered (inventory/coverage.json "missing")',
    'class_init': 'decision 4: MaterialShapes owns PREFIX_BY_NAME and Mats.prefixByName is that same map, so MaterialShapes\' constructor no longer runs Mats\' static initializer (no prefix or quantity change); '
                  'NEO\'s prefixes stay "ingots", "nuggets", "blocks" (GOAL27A A2)',
    'sync_bound': 'decision 5: MachineCrucibleBlockEntity.MAX_SYNC_ENTRIES 64 -> Mats.orderedList.size(); constants, save keys, the legacy copper key and unknown-ID dropping unchanged',
    'scrap_models': 'decision 6: item-model override value (index + 1) / 256 over the SMELTABLE / ADDITIVE materials except copper in orderedList order, additive liquid 0.75 (scraps_additive), liquid 1 '
                    '(scraps_liquid); 71 derived textures, the four Goal 10A textures unchanged, scraps_bismuth (original override, byte import), scraps_plain (the original uncoloured scraps.png, renamed) for '
                    'light == dark materials, tinted with the molten colour like ItemAutogen; copper keeps the Goal 5A base model',
    'effect_icons': 'decision 7: the seven missing icons are unscaled 18x18 crops of potions.png at (x*18, 198 + y*18), like the four existing ones (icon-precedent.json)',
    'shredder': 'decision 8 (corrected by review P2-2): 14 rows, gems / ingots -> 1 dust (coal, quartz, Th-232 ingot, tantalium gem, lignite, lithium, gold ingot, diamond, emerald) and five ingot_raw metas '
                '(redstone, neodymium, borax, sodium, strontium; slag has no dust); nothing deferred to 27B',
    'language': 'decision 9: 89 hbmmat.* keys and casting.scraps.additive (local); hbmmat.mingrade "Red Copper" and hbmmat.cmbsteel "CMB Steel" follow the NEO item wording with the originals in source_en; the '
                'existing hbmmat.red_copper zh 红铜 against 紫铜 elsewhere is left unchanged (follow-up)',
    'iron_nugget': 'decision 10: minecraft:iron_nugget -> MAT_IRON NUGGET is a NEO-only MaterialEntries row (1.7.10 has no iron nugget; upstream melts any nuggetIron through the prefix rule)',
    'damaged_items': 'review P2-1: upstream keys durable items by their damage (RecipesCommon.java ComparableStack(ItemStack) meta = getItemDamage), so worn blades and stamps miss the meta-0 row; NEO keeps damage '
                     'out of the meta and Mats.getMaterialsFromItem skips the item entries for a damaged stack',
    'preferred_output': 'review P3-1: MaterialEntries.getPreferred follows ItemMold.getOutput (the first hbmsntm row whose id does not contain "fragment", else the first row); no caller yet (27D)',
    'shredder_exact_lookup': 'GameTest defect: NEO ComparableStack.hashCode has no meta and a wildcard matches any meta, so the wildcard retry in ShredderRecipes.getShredderResult / hasRecipe matched another meta\'s '
                             'row (slag ingot_raw -> redstone); upstream\'s hash includes meta (RecipesCommon.java hashCode). The retry was removed; the exact lookup already finds wildcard rows',
    'jei_grid': 'review P3-3: the JEI smelting output grid fits 9 outputs; a config row with more would overflow (no default row has more than 3)',
    'not_migrated': 'casting molds and FoundryMoldBlockEntity (27D), CrucibleRecipes (27B), the remaining crucible recipes, molten metal rendering and other casting devices are not part of this batch',
}
# The six old isolated machine / pollution suites keep running through tools/migration/goal26c_oldsuite_run.py in the final rerun; recorded in the receipt.
OLD_MACHINE_SUITES = ('verify_goal16a_machine', 'verify_goal16b_machine', 'verify_goal17b_machine', 'verify_goal18a_machine', 'verify_goal18b_machine', 'verify_goal19a_pollution')
DECLARATION = re.compile(r'^\s*public static final NTMMaterial (MAT_\w+)\s*=\s*(\w+)\(\s*(.*)$')


def scope_text(material_count, key_count, tests, total_tests, entries_rows, shredder_rows, icons):
    return (f'Goal27A (the first batch of Goal 27: the material system): the original material table ({material_count} materials) with the NEO item-to-material registry MaterialEntries '
            f'({entries_rows} rows), MatDistribution and its config file hbmCrucibleSmelting.json, multi-material crucible smelting, scraps for every smeltable material with JEI smelting '
            f'groups, {shredder_rows} shredder rows completing the original ingot/gem -> dust rule, the {icons} missing effect icons, {key_count} language keys; {tests} MaterialSystemGameTests '
            f'({total_tests} GameTests in total, one batch per test); also the D2 small fix after goal26d (ContaminationUtil.java:101-102 3.6F -> 3.6D). Gameplay impact: the crucible now melts '
            f'plates, dusts, wires, bolts, billets, blocks, cast and welded plates, dense wires, shells, pipes and vanilla items of every material, and ores with byproducts (iron ore -> iron + '
            f'titanium + stone); damaged blades and stamps are refused; coal shreds into coal powder; new config file hbmCrucibleSmelting.json; Rad-X / RadAway and five other effects show '
            f'their original icons.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal27a release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 38 planned copies) when it reproduces the baseline hash, else the blob at the start commit
    (with CRLF where the working tree had it); None when nothing reproduces the baseline hash (unexpected: the start worktree was clean)."""
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
    """The Goal27A start hash of a frozen path: baseline files, or for a build/ record (Git-ignored, so baseline files does not list it) the hash the goal26d receipt
    records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal26d packager protected (built there from the Goal21A..Goal26C starts and receipts and the goal26d start), plus every path the goal26d receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (goal21a..goal26c) and every release file of the frozen start (the goal26d package
    included). The records that already drifted (baseline previous_receipt_evidence_drift: GOAL26D-ACCEPTANCE.md and GOAL25D-ACCEPTANCE.md; the older drift: the
    acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes, GOAL25D-ACCEPTANCE.md) are pinned at their Goal27A start
    hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal26d packager set at its Goal26D start hash, for the records that changed between the starts."""
    goal26d_start = read(GOAL26D_BASELINE)
    out = dict(goal26d_protected_paths(goal26d_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal26d receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal26d_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal26D and Goal27A starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal26d_start):
    """{path: {receipts, start_sha256, goal26d_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal26d receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal26d receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif p in PREVIOUS_DRIFT:
            explanation = ('Filled in by the Goal 26 unified in-game acceptance after the goal26d package was written (the goal26d receipt hash is the text before the results) and committed in the '
                           'Goal 26 close-out commit 0786697d; baseline previous_receipt_evidence_drift. Frozen at the Goal27A start hash; this batch must not change it and the goal26d receipt is not rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21..25 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal26d '
                           'receipt does not hash it. Frozen at the Goal27A start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal26d) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal26d package; the goal26d receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal26d '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal26d_start_sha256=goal26d_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal26d_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def group(p, base, ownership_assets):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA or p in OPTIONAL_JAVA: return 'production'
    if p in ASSETS: return 'production-resource-imported'
    if p in ownership_assets: return 'production-resource-derived'
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


def split_top(args):
    """Top-level comma split of a Java argument list (parentheses and quotes respected)."""
    out, depth, cur, quote = [], 0, '', False
    for ch in args:
        if ch == '"': quote = not quote
        if not quote:
            if ch == '(': depth += 1
            elif ch == ')':
                if depth == 0: break
                depth -= 1
            elif ch == ',' and depth == 0:
                out.append(cur.strip()); cur = ''; continue
        cur += ch
    out.append(cur.strip())
    return out


def declarations(text):
    """{MAT_X: dict(factory, args (the dict / names argument dropped), tail)} for every `public static final NTMMaterial MAT_X = factory(...)...;` line (comment lines excluded),
    whitespace collapsed; plus the order of the fields."""
    out, order = {}, []
    for raw in text.splitlines():
        m = DECLARATION.match(raw)
        if not m: continue
        field, factory, rest = m.group(1), m.group(2), re.sub(r'\s+', ' ', m.group(3)).strip()
        args = split_top(rest)
        depth, end = 0, None
        for i, ch in enumerate(rest):
            if ch == '(': depth += 1
            elif ch == ')':
                if depth == 0: end = i; break
                depth -= 1
        tail = re.sub(r'//.*$', '', rest[end+1:]).strip() if end is not None else ''
        out[field] = dict(factory=factory, id=args[0].replace(' ', ''), args=[a.replace(' ', '') for a in args[2:]], dict_arg=args[1] if len(args) > 1 else None,
                          tail=re.sub(r'\s+', '', tail))
        order.append(field)
    return out, order


def names_first(dict_arg):
    """names("A", "B") -> "A" (the NEO form); None for an original DictFrame constant."""
    m = re.match(r'names\("([^"]+)"', dict_arg or '')
    return m.group(1) if m else None


def recompile_equal(name, previous_bytes, new_bytes):
    """True when the previous class bytes, patched in one of the directions RECOMPILE_ONLY allows (every pattern occurring exactly once), equal the new class bytes."""
    for pairs in RECOMPILE_ONLY[name]:
        patched = previous_bytes
        if any(patched.count(a) != 1 for a, b in pairs): continue
        for a, b in pairs: patched = patched.replace(a, b)
        if patched == new_bytes: return True
    return False


def body_of(text, signature):
    """The brace-balanced body of the first method whose header contains `signature`, or ''."""
    i = text.find(signature)
    if i < 0: return ''
    j = text.find('{', i)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == '{': depth += 1
        elif text[k] == '}':
            depth -= 1
            if depth == 0: return text[j:k+1]
    return ''


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
    goal26d_start = read(GOAL26D_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal27A commits nothing): HEAD 71c2f660 (the Goal 27 planning commit,
    # 8 files) on the Goal 26 close-out 0786697d (= origin/master) on the rewritten Goal 26 planning commit 6bfb7ad2, with a clean worktree (0 status lines).
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 27 planning commit'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 27 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    status_lines = base['target_status'].splitlines()
    assert len(status_lines) == START_STATUS_LINES and START_STATUS.read_text(encoding='utf-8').splitlines() == status_lines and not START_HASHES.read_text(encoding='utf-8').strip(), \
        'The frozen start is not a clean worktree (baseline target_status / start_status.txt / start_hashes.txt)'
    assert base['target_parent'].startswith(GOAL26_CLOSEOUT) and base['origin_master'] == base['target_parent'], 'The start commit is not on the pushed Goal 26 close-out 0786697d'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal26d receipt records another original commit than the frozen start'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal27A (the delivery stays uncommitted until the Goal 27 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2)}
    assert chain[1].startswith(GOAL26_CLOSEOUT) and chain[2].startswith(GOAL26_PLANNING), 'NEO HEAD~1..2 are not the Goal 26 close-out 0786697d and the Goal 26 planning 6bfb7ad2 commits: '+str(chain)
    planning_files = [l for l in git_ro(ROOT, 'show', '--name-only', '--format=', start_head).splitlines() if l.strip()]
    assert len(planning_files) == PLANNING_FILES and all(p.startswith('migration/') for p in planning_files), 'The planning commit 71c2f660 is not the 8 migration/ documents: '+str(planning_files)
    assert set(base['start_content']) == {'committed', 'uncommitted'} and base['start_content']['uncommitted'].startswith('none'), 'Baseline start content differs (expected no uncommitted delivery)'
    assert set(base['older_receipt_protected_paths']) == OLDER_RECEIPTS, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256_at_freeze'] == base['build_libs_jar_sha256_at_freeze'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_lines'] == len(status_lines) == startup['dirty_start_files'] == 0 \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'], \
        'startup-verification.json differs from baseline.json'
    start_stamp = start_json(base, STAMP)
    assert base['stamp_state']['generated_resources_recorded'] == prior_receipt['generated_resource_count'] == len(start_stamp['generated']) \
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal26d generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_freeze']

    # 2. Previous deliveries: the goal26d package, every old release file and the protected evidence; build/libs at the freeze is the D2 small-fix build, not goal26d.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == D2_LIBS_SHA != previous_sha, 'build/libs at the freeze is not the post-D2 small-fix build 61436747...a0d0 (or it is the goal26d package)'
    readme_start = start_bytes(base, 'migration/README.md').decode('utf-8')
    d2_line = next((l for l in readme_start.splitlines() if l.startswith('2026-10-23') and 'D2' in l and 'ContaminationUtil.java:101-102' in l and D2_LIBS_SHA[:8] in l), None)
    assert d2_line is not None, 'The README of the start has no 2026-10-23 D2 small-fix line naming ContaminationUtil.java:101-102 and 61436747'
    d2_lines = (ROOT/D2_SOURCE).read_text(encoding='utf-8').splitlines()[100:102]
    assert len(d2_lines) == 2 and '3.6D' in d2_lines[0] and '3.6D' in d2_lines[1] and '3.6F' not in ''.join(d2_lines), 'ContaminationUtil.java:101-102 do not carry the D2 3.6D fix: '+str(d2_lines)
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal26d receipt list + the goal26d package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal26d receipt count + the goal26d release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal26d receipt'
    assert set(base['previous_receipt_evidence_drift']) == PREVIOUS_DRIFT and all(
        d['receipt'] == prior_receipt['report_sha256'].get(p, prior_receipt['evidence_sha256'].get(p)) and d['now'] == base['files'][p]
        for p, d in base['previous_receipt_evidence_drift'].items()), 'The goal26d receipt drift at the start is not GOAL26D-ACCEPTANCE.md and GOAL25D-ACCEPTANCE.md (receipt hash -> start hash)'
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal26d_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal26d receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal27a. Everything else equals its start hash.
    ownership = read(ROOT/RESOURCE_OWNERSHIP) if (ROOT/RESOURCE_OWNERSHIP).is_file() else None
    derived = {a['target_path']: a for a in (ownership or {}).get('derived_assets', [])}
    unchanged_assets = {a['target_path']: a for a in (ownership or {}).get('unchanged_assets', [])}
    changes = changed_since_start(base)
    older_gametests_frozen = sorted(p for p in base['files'] if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java'))
    modified_java = MODIFIED_JAVA + OPTIONAL_JAVA
    production_java = NEW_JAVA + modified_java
    production = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + sorted(derived) + [ZH_INPUT, LOCALIZATION_RECORD]
    unassigned = sorted(p for p in changes if group(p, base, derived) is None)
    need(not unassigned, f'Path changed since the Goal27A start that the owner table does not list (production outside the {len(MODIFIED_JAVA)} modified Java files, the {len(NEW_JAVA)} new classes incl. '
         f'MaterialSystemGameTests, the {len(ASSETS)} imported and {len(derived)} derived resources, zh_cn.json and the mapping, a protected or frozen record, an older tool, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal 26 and earlier records or the Goal 27 planning documents (GOAL27B/C/D.md, GOAL27-THREAD-PROMPTS.md, SURVIVAL-PLAYABILITY.md) changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal27A start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD] + GENERATED + SHARED_RECORDS + REPORTS[:1]:
        if p in OPTIONAL_RECORDS and p not in base['files']: continue
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in production + production_java if p.startswith('src/')})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified and {len(NEW_JAVA)} new Java files, the {len(ASSETS) + len(derived)} resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools = OLD_TOOLS_FROZEN + sorted(p for p in base['files'] if p.startswith(FROZEN_TOOL_DIRS))
    frozen_tools_changed = sorted(p for p in frozen_tools if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (the casting regressions, the Goal 26C old-suite wrapper, the Goal 10A scrap tool): '+str(frozen_tools_changed))
    goal27_now = sha(ROOT/GOAL27_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository (main-notes.md: no linked session in this checkout; '
                                               'the parent planning session idle). The batch ran under the main agent with a builder (production), two implementers (resources, language), a GameTest '
                                               'verifier (MaterialSystemGameTests, verify_goal27a_material_system.py, Gradle), a read-only reviewer and this packaging verifier (the packager, the final '
                                               'runner and the casting-regression wrapper); each wrote only its named files (scope snapshots of the verifiers are indexed as evidence). The main agent '
                                               'edited the migration/ records, MaterialEntries / Mats / ShredderRecipes for the review fixes and the GameTest defect, and goal27a-materials-review.json.',
                             goal27_md=dict(start_sha256=base['files'][GOAL27_RECORD], current_sha256=goal27_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p) if (ROOT/p).is_file() else None) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p, base, derived), owner=OWNER, owners=[OWNER], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p))
                   for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal27A takes no new snapshot)'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-aee05a40f10f snapshot changed'
    production_changed = [p for p in production + production_java if p in changes]
    production_changed = list(dict.fromkeys(production_changed))

    # The modified production files keep their start line endings (several are LF in the worktree; reported); new Java files are not mixed.
    start_text, line_endings = {}, {}
    for p in modified_java + [ZH_INPUT, LOCALIZATION_RECORD]:
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

    # Production Java facts: insert-only files, every line edit counted (+/- against the start bytes).
    insert_summary, edit_summary, inserted_lines, added_lines, removed_lines = {}, {}, {}, {}, {}
    for p in modified_java + [ZH_INPUT, LOCALIZATION_RECORD]:
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
        elif p not in REWRITTEN_JAVA:
            need(False, f'{p} is neither in STRICT_INSERT_ONLY nor in REWRITTEN_JAVA (owner table gap)')
    for p in NEW_JAVA:
        if (ROOT/p).is_file(): edit_summary[p] = dict(added=len(lines_of((ROOT/p).read_bytes())), removed=0)
    # Language provider: the added lines carry exactly the new keys (plain keys); nothing is removed.
    provider_added = []
    if PROVIDER in added_lines:
        keys_added, other = base_provider_keys(added_lines[PROVIDER])
        provider_added = sorted(keys_added)
        stray = [l for l in other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} adds lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(keys_added) == len(set(keys_added)), f'{PROVIDER} adds a language key twice')
        need(not base_provider_keys(removed_lines[PROVIDER])[0], f'{PROVIDER} removes language entries: {base_provider_keys(removed_lines[PROVIDER])[0][:4]}')
    added_code_facts = {}
    for p, rule in ADDED_CODE_RULES.items():
        if p not in start_text: continue
        inserted = insertions(lines_of(start_text[p]), lines_of((ROOT/p).read_bytes()))
        if inserted is None: continue
        code_lines = [l.strip() for _, l in inserted if not is_comment(l)]
        stray = [l for l in code_lines if not rule.fullmatch(l)]
        need(not stray, f'{p} adds code lines the owner table does not allow (only the batch lines): {[l[:90] for l in stray[:4]]}')
        added_code_facts[p] = dict(added_code_lines=len(code_lines), added_comment_or_blank_lines=len(inserted) - len(code_lines))
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    neo_text = lambda path: (ROOT/path).read_text(encoding='utf-8').replace('\r\n', '\n') if (ROOT/path).is_file() else ''
    unchanged_bad = [p for p in UNCHANGED_JAVA + older_gametests_frozen if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed (incl. ContaminationUtil.java = the D2 bytes and every older GameTest class): '+str(unchanged_bad))

    # 4. The material system against the original (EXPECTED holds the handoff figures; every value is computed from the sources).
    facts, bad = {}, []

    def fact(key, value, expected=None, ok=None):
        facts[key] = value if expected is None else dict(value=value, expected=expected)
        if ok is None: ok = expected is None or value == expected
        if not ok: bad.append(key)

    o_mats, n_mats = original_text(O_MATS), neo_text(MATS)
    o_decl, o_order = declarations('\n'.join(l for l in o_mats.split('\n') if not l.lstrip().startswith('//')))
    n_decl, n_order = declarations('\n'.join(l for l in n_mats.split('\n') if not l.lstrip().startswith('//')))
    fact('materials_original', len(o_order), EXPECTED['materials'])
    fact('materials_neo', len(n_order), len(o_order))
    fact('materials_same_order', n_order == o_order, True)
    differing = [f for f in o_order if f in n_decl and {k: v for k, v in o_decl[f].items() if k != 'dict_arg'} != {k: v for k, v in n_decl[f].items() if k != 'dict_arg'}]
    fact('declarations_equal_except_names', differing, [])
    ids = [n_decl[f]['id'] for f in n_order]
    fact('material_ids_unique', len(set(ids)) == len(ids), True)
    conv = lambda d, order: [(f, re.findall(r'\.setConversion\(([^)]*)\)', d[f]['tail'])) for f in order if '.setConversion(' in d[f]['tail']]
    fact('conversions', len(conv(n_decl, n_order)), EXPECTED['conversions'], ok=conv(n_decl, n_order) == conv(o_decl, o_order) and len(conv(o_decl, o_order)) == EXPECTED['conversions'])
    smeltable = lambda d, f: d[f]['factory'] in ('makeSmeltable', 'makeAdditive')
    scrap_fields = [f for f in o_order if smeltable(o_decl, f)]
    fact('scrap_materials_original', len(scrap_fields), EXPECTED['scrap_materials'])
    single_colour = [f for f in scrap_fields if len(o_decl[f]['args']) == 1 or (len(o_decl[f]['args']) >= 2 and o_decl[f]['args'][0] == o_decl[f]['args'][1])]
    plain = [f for f in single_colour if f != 'MAT_BISMUTH']
    fact('plain_scrap_materials', sorted(plain), None)
    fact('plain_scrap_material_count', len(plain), EXPECTED['plain_scrap_materials'])
    factories = {n: len(re.findall(r'public static NTMMaterial '+n+r'\(', n_mats)) for n in ('make', 'makeSmeltable', 'makeAdditive', 'makeNonSmeltable')}
    fact('factories', factories, dict(make=1, makeSmeltable=2, makeAdditive=1, makeNonSmeltable=1))
    lookup = body_of(n_mats, 'public static List<MaterialStack> getMaterialsFromItem(ItemStack stack)')
    marks = [lookup.find(t) for t in ('materialOreEntries', 'MaterialEntries.getEntries(stack)', 'materialEntries.get(new ComparableStack(stack).makeSingular())', 'CopperScrapsItem.getMats(stack)')]
    o_lookup = body_of(o_mats, 'public static List<MaterialStack> getMaterialsFromItem(ItemStack stack)')
    o_marks = [o_lookup.find(t) for t in ('materialOreEntries.get(name)', 'prefixByName.entrySet()', 'materialEntries.get(new ComparableStack(stack).makeSingular())', 'ItemScraps.getMats(stack)')]
    fact('lookup_order', marks, None, ok=all(m >= 0 for m in marks + o_marks) and marks == sorted(marks) and o_marks == sorted(o_marks))
    fact('lookup_first_smeltable_prefix', bool(re.search(r'SmeltingBehavior\.SMELTABLE \|\| material\.smeltsInto\.smeltable == SmeltingBehavior\.ADDITIVE\) \{\s*list\.add\(new MaterialStack\(material, entry\.shape\(\)\.q\(1\)\)\);\s*break;', lookup)), True)
    fact('integer_conversion', n_mats.count('(int) (x.amount * x.material.convOut / x.material.convIn)'), 1, ok=n_mats.count('(int) (x.amount * x.material.convOut / x.material.convIn)') == 1 == o_mats.count('(int) (x.amount * x.material.convOut / x.material.convIn)'))
    fact('damaged_items_skip_item_entries', len(re.findall(r'stack\.isDamaged\(\) \? null : materialEntries\.get\(', lookup)), 1)
    fact('prefix_map_shared', bool(re.search(r'prefixByName = MaterialShapes\.PREFIX_BY_NAME', n_mats)), True)
    n_entries = neo_text(ENTRIES_JAVA)
    rows = re.findall(r'^\s*add\((Mats\.MAT_\w+), MaterialShapes\.(\w+), [^;]*\);(.*)$', n_entries, re.M)
    fact('entries_rows', len(rows), EXPECTED['entries_rows'])
    fact('entries_neo_only', sum(1 for r in rows if '// NEO-only' in r[2]), EXPECTED['entries_neo_only'])
    fact('entries_materials', len({r[0] for r in rows}), EXPECTED['entries_materials'])
    fact('entries_iron_nugget_row', len(re.findall(r'add\(Mats\.MAT_IRON, MaterialShapes\.NUGGET, Items\.IRON_NUGGET\);', n_entries)), 1)
    preferred = body_of(n_entries, 'public static ItemStack getPreferred(MaterialShapes shape, NTMMaterial material)')
    fact('preferred_skips_fragments', 'id.getNamespace().equals(NuclearTechMod.MODID) && !id.getPath().contains("fragment")' in preferred
         and original_text(O_MOLD).count('if(registry.contains("fragment")) continue;') == 1, True)
    n_dist = neo_text(DISTRIBUTION_JAVA)
    defaults = body_of(n_dist, 'public void registerDefaults()')
    direct = len(re.findall(r'^\s*registerEntry\((?!ore,)', defaults, re.M))
    looped = sum(len(split_top(m)) for m in re.findall(r'for\(ItemLike ore : ores\((.*?)\)\)\s*(?:\{|registerEntry)', defaults, re.S))
    fact('distribution_rows', direct + looped, EXPECTED['distribution_rows'])
    fact('distribution_file', re.findall(r'return "([^"]+\.json)";', body_of(n_dist, 'public String getFileName()')), re.findall(r'return "([^"]+\.json)";', body_of(original_text(O_DISTRIBUTION), 'public String getFileName()')))
    s_text = neo_text(SERIALIZABLE)
    fact('distribution_after_crucible_recipes', bool(re.search(r'recipeHandlers\.add\(CrucibleRecipes\.INSTANCE\);\s*\n\s*recipeHandlers\.add\(new MatDistribution\(\)\);', s_text)), True)
    fact('distribution_registered_once', s_text.count('recipeHandlers.add(new MatDistribution());'), 1)
    c_text, c_start = neo_text(CRUCIBLE), start_bytes(base, CRUCIBLE).decode('utf-8') if CRUCIBLE in base['files'] else ''
    fact('crucible_sync_bound', bool(re.search(r'private static final int MAX_SYNC_ENTRIES = Mats\.orderedList\.size\(\);', c_text)), True)
    keys = lambda t: sorted(set(re.findall(r'tag\.(?:put|get|contains)\w*\("(\w+)"', t)))
    fact('crucible_save_keys_unchanged', keys(c_text), keys(c_start))
    fact('crucible_legacy_copper_key', bool(re.search(r'if\(!tag\.contains\("was"\) && tag\.contains\("copper", Tag\.TAG_INT\)\)', c_text)), True)
    sc_text = neo_text(SCRAPS)
    fact('scraps_model_value', bool(re.search(r'return \(index \+ 1\) / 256F;', sc_text)), True)
    fact('scraps_liquid_models', re.findall(r'public static final float (ADDITIVE_LIQUID_MODEL|LIQUID_MODEL) = ([\d.]+)F;', sc_text), [('ADDITIVE_LIQUID_MODEL', '0.75'), ('LIQUID_MODEL', '1')])
    fact('scraps_texture_rule', bool(re.search(r'if\(material == Mats\.MAT_BISMUTH\) return "scraps_bismuth";\s*if\(material\.solidColorLight == material\.solidColorDark\) return "scraps_plain";', sc_text)), True)
    fact('scraps_tab_filter', bool(re.search(r'if\(CopperScrapsItem\.isScrapMaterial\(material\)\) output\.accept\(CopperScrapsItem\.create\(new Mats\.MaterialStack\(material, MaterialShapes\.INGOT\.q\(1\)\)\)\);', neo_text(CREATIVE_TABS))), True)
    sh_text = neo_text(SHREDDER)
    shredder_added = [l.strip() for l in (inserted_lines.get(SHREDDER) or added_lines.get(SHREDDER, [])) if l.strip().startswith('registerIfAbsent(')]
    fact('shredder_rows_added', len(shredder_added), EXPECTED['shredder_rows'])
    start_wild = start_bytes(base, SHREDDER).decode('utf-8').count('WILDCARD') if SHREDDER in base['files'] else None
    fact('shredder_exact_lookup', dict(start_wildcard=start_wild, now_wildcard=sh_text.count('WILDCARD')), None, ok=bool(start_wild) and sh_text.count('WILDCARD') == 0)
    fact('jei_smelting_recipes', bool(re.search(r'registration\.addRecipes\(CrucibleSmeltingRecipeHandler\.RECIPE_TYPE, CopperCastingRecipes\.getSmeltingRecipes\(\)\);', neo_text(JEI_PLUGIN))), True)
    # Effect icons: every ModEffect id has a texture; the new ones are the derived crops at (x*18, 198 + y*18).
    effect_ids = re.findall(r'MOB_EFFECTS\.register\("(\w+)"', neo_text(J+'lib/ModEffect.java'))
    start_icons = {p.rsplit('/', 1)[1][:-4] for p in base['files'] if p.startswith(ASSETS_ROOT+'textures/mob_effect/') and p.endswith('.png')}
    new_icons = sorted(set(effect_ids) - start_icons)
    fact('effect_icons_new', new_icons, None, ok=len(new_icons) == EXPECTED['effect_icons'])
    icon_entries = {a['target_path'].rsplit('/', 1)[1][:-4]: a for a in derived.values() if '/textures/mob_effect/' in a['target_path']}
    fact('effect_icon_crops', {n: icon_entries.get(n, {}).get('crop') for n in new_icons}, None,
         ok=sorted(icon_entries) == new_icons and all(e.get('crop') == [e['tile'][0]*18, 198 + e['tile'][1]*18, 18, 18] and e.get('source_path') == O_POTIONS_ATLAS for e in icon_entries.values()))
    fact('effect_icon_files', all((ROOT/(ASSETS_ROOT+f'textures/mob_effect/{n}.png')).is_file() for n in effect_ids), True)
    need(not bad, 'material-system facts differ from the original or the handoff figures (or the NEO source is missing / its text differs): '+', '.join(
        f'{k}={json.dumps(facts[k], ensure_ascii=False)[:160]}' for k in bad))
    # Client-side classes the common code must not reference.
    common_classes = [MATS, SHAPES, ENTRIES_JAVA, DISTRIBUTION_JAVA, CASTING, CRUCIBLE, SCRAPS, SHREDDER]
    client_refs = {p: bool((ROOT/p).is_file() and re.search(r'net\.minecraft\.client|com\.hbm\.render\.|mezz\.jei', strip_java_comments(neo_text(p)))) for p in common_classes}
    need(not any(client_refs.values()) and all((ROOT/p).is_file() for p in common_classes), 'common-side classes are missing or reference client-only classes: '+str(sorted(p for p, v in client_refs.items() if v)))

    # 5. Resources: the 3 byte imports (original worktree file and stored blob), the derived textures and icons (the ownership record and both generator scripts' --check),
    # the unchanged textures (their start bytes).
    imported, derived_facts, unchanged_facts, generators = {}, {}, {}, {}
    if need(ownership is not None, 'record missing: '+RESOURCE_OWNERSHIP):
        entries = {a.get('target_path'): a for a in ownership.get('imported_assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(ASSETS), f'{RESOURCE_OWNERSHIP} imported_assets are not the {len(ASSETS)} byte imports at {SOURCE_HEAD[:8]}: {sorted(set(entries) ^ set(ASSETS))[:4]}')
        need(all(entries.get(t, {}).get('source_path') == o for t, o in ASSETS.items()), f'{RESOURCE_OWNERSHIP} imported source paths differ from the owner table (scraps.png -> scraps_plain.png)')
        scrap_derived = sorted(p for p in derived if '/textures/item/scraps_' in p)
        need(len(scrap_derived) == EXPECTED['derived_scrap_textures'] and len(derived) == EXPECTED['derived_scrap_textures'] + EXPECTED['effect_icons'] and len(unchanged_assets) == EXPECTED['unchanged_assets'],
             f'{RESOURCE_OWNERSHIP} lists {len(scrap_derived)} derived scrap textures, {len(derived) - len(scrap_derived)} icons and {len(unchanged_assets)} unchanged assets')
        expected_scrap_textures = sorted(ASSETS_ROOT+'textures/item/scraps_'+names_first(n_decl[f]['dict_arg']).lower()+'.png' for f in scrap_fields
                                         if f in n_decl and names_first(n_decl[f]['dict_arg']) and f not in single_colour and f != 'MAT_COPPER'
                                         and (ASSETS_ROOT+'textures/item/scraps_'+names_first(n_decl[f]['dict_arg']).lower()+'.png') not in base['files'])
        need(scrap_derived == expected_scrap_textures, 'derived scrap textures are not the SMELTABLE / ADDITIVE materials without a start texture (copper, light == dark and bismuth excluded): '
             f'extra {sorted(set(scrap_derived) - set(expected_scrap_textures))[:4]}, missing {sorted(set(expected_scrap_textures) - set(scrap_derived))[:4]}')
        for t, a in derived.items():
            ok = (ROOT/t).is_file() and sha(ROOT/t) == a.get('target_sha256') and t not in base['files'] and a.get('source_path', '').startswith(O_RES) and (SOURCE/a['source_path']).is_file()
            derived_facts[t] = dict(sha256=sha(ROOT/t) if (ROOT/t).is_file() else None, source_path=a.get('source_path'), generator=a.get('generator'), ok=ok)
        need(all(d['ok'] for d in derived_facts.values()), 'derived resources differ from the ownership record (missing, other bytes, present at the start or no original source): '+str([t for t, d in derived_facts.items() if not d['ok']][:4]))
        for t, a in unchanged_assets.items():
            unchanged_facts[t] = dict(sha256=sha(ROOT/t) if (ROOT/t).is_file() else None, start_sha256=base['files'].get(t), record_sha256=a.get('target_sha256'))
        need(all(d['sha256'] == d['start_sha256'] == d['record_sha256'] for d in unchanged_facts.values()), 'unchanged resources differ from their start bytes or the ownership record: '+str(
            [t for t, d in unchanged_facts.items() if not d['sha256'] == d['start_sha256'] == d['record_sha256']][:4]))
    for tool in (SCRAP_TEXTURES_TOOL, EFFECT_ICONS_TOOL):
        if not need((ROOT/tool).is_file(), 'generator missing: '+tool): continue
        run = subprocess.run([sys.executable, '-B', '-X', 'utf8', tool, '--check'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        generators[tool] = dict(exit=run.returncode, last_line=(run.stdout.strip().splitlines() or [''])[-1][:300], sha256=sha(ROOT/tool))
        need(run.returncode == 0, f'{tool} --check failed (exit {run.returncode}): {(run.stdout + run.stderr).strip()[-300:]}')
    for target, original in ASSETS.items():
        assert (SOURCE/original).is_file(), 'Original resource missing: '+original
        if not (ROOT/target).is_file():
            need(False, 'resource not imported yet: '+target)
            continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        entry = {a.get('target_path'): a for a in (ownership or {}).get('imported_assets', [])}.get(target, {})
        imported[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size, renamed=RENAMED.get(target),
                                original_worktree_sha256=sha(SOURCE/original), original_blob_sha256=hashlib.sha256(blob).hexdigest(), source_last_commit=entry.get('source_last_commit'))
        need((ROOT/target).read_bytes() == checked_out == blob, f'{target} is not byte-identical to the original {original} (worktree and stored blob at {SOURCE_HEAD[:8]})')
        if entry: need(entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('size') == (ROOT/target).stat().st_size,
                       f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original: {target}')
    # features.json: the new group, the unchanged status and reviewed_source_commit of the previous groups; only the named groups' notes may change, target_watch may only grow.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES <= set(start_features) and not set(NEW_FEATURES) & set(start_features), \
        'The start mapping does not hold the groups of 24B-26D (rbmk-fuel ... radiation-medicine) and not yet the Goal27A group'
    new_groups = {g: by_id[g] for g in NEW_FEATURES if g in by_id}

    # 6. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = start_json(base, EN), read(ROOT/EN)
    zh_start, zh_now = start_json(base, ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = start_json(base, LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    o_en, o_zh = lang_file(O_LANG_EN), lang_file(O_LANG_ZH)
    material_keys = sorted({'hbmmat.'+names_first(n_decl[f]['dict_arg']).lower() for f in n_order if names_first(n_decl[f]['dict_arg'])})
    KEYS = sorted(set(k for k in material_keys if k not in en_start) | set(EXTRA_KEYS))
    need(len(KEYS) == EXPECTED['language_keys'], f'expected new language keys: {len(KEYS)} (hbmmat.<names[0]> of the NEO table missing at the start + casting.scraps.additive), the handoff says {EXPECTED["language_keys"]}')
    need(all(k in o_en for k in KEYS if k.startswith('hbmmat.')), 'hbmmat keys without an original en_US.lang entry: '+str([k for k in KEYS if k.startswith('hbmmat.') and k not in o_en][:6]))
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_delta = dict(added=KEYS, removed=[], changed=[])
    need(en_delta == expected_delta, f'generated en_us.json delta is not the {len(KEYS)} new keys (no value changed): '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_delta, f'zh_cn.json delta is not the {len(KEYS)} new keys (all old values unchanged): '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_delta, f'zh_cn-map.json delta is not the {len(KEYS)} new entries (no old entry changed): '+json.dumps(map_delta, ensure_ascii=False)[:700])
    need(not PROVIDER in added_lines or provider_added == KEYS, f'{PROVIDER} adds the language keys differently than expected: missing {sorted(set(KEYS) - set(provider_added))[:6]}, unexpected {sorted(set(provider_added) - set(KEYS))[:6]}')
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal26d totals'
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal26d totals {totals} + {len(KEYS)}')
    expected_kinds = dict(upstream=EXPECTED['language_upstream'], local=EXPECTED['language_local'])
    language_kinds, original_text_checked, en_deviations = {}, False, {}
    if map_delta == expected_delta and en_delta == expected_delta and zh_delta == expected_delta:
        language_kinds = dict(Counter(map_now[k].get('kind') for k in KEYS))
        need(language_kinds == expected_kinds and {k for k in KEYS if map_now[k].get('kind') == 'local'} == LOCAL_KEYS,
             f'zh_cn-map.json kinds of the new entries are {language_kinds}, local {sorted(k for k in KEYS if map_now[k].get("kind") == "local")}; expected {expected_kinds}, local {sorted(LOCAL_KEYS)}')
        bad_lang = []
        for k in KEYS:
            e = map_now[k]
            if e.get('target_en') != en_now.get(k) or e.get('target_zh') != zh_now.get(k) or not zh_now.get(k): bad_lang.append(k)
            elif en_now[k].count('%s') != zh_now[k].count('%s'): bad_lang.append(k)
            elif e.get('kind') == 'local':
                if not e.get('reason'): bad_lang.append(k)
            elif e.get('source_key') != k or e.get('source_en') != o_en.get(k) or e.get('source_zh') != o_zh.get(k) or e.get('source_zh') != e.get('target_zh'): bad_lang.append(k)
            elif e.get('source_en') != e.get('target_en'):
                en_deviations[k] = dict(source_en=e.get('source_en'), target_en=e.get('target_en'))
                if EN_DEVIATIONS.get(k) != e.get('target_en'): bad_lang.append(k)
        need(not bad_lang, 'zh_cn-map.json entries do not match en_us.json / zh_cn.json, the original en_US.lang / zh_CN.lang values at aee05a40f or the expected kinds: '+str(bad_lang[:8]))
        need(sorted(en_deviations) == sorted(EN_DEVIATIONS), f'upstream entries whose English deviates from the original: {sorted(en_deviations)}, expected {sorted(EN_DEVIATIONS)}')
        original_text_checked = not bad_lang
    map_kinds = dict(Counter(e.get('kind') for e in map_now.values()))
    start_kinds = dict(Counter(e.get('kind') for e in map_start.values()))
    expected_kinds_now = {k: start_kinds.get(k, 0) + expected_kinds.get(k, 0) for k in set(start_kinds) | set(expected_kinds)}
    need(map_kinds == expected_kinds_now, f'mapping kinds are {map_kinds}, expected {expected_kinds_now} (upstream +{expected_kinds["upstream"]}, local +{expected_kinds["local"]}, deferred unchanged)')
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
    # The scraps item model: the overrides follow the original orderedList (SMELTABLE / ADDITIVE except copper), value (i + 1) / 256, then scraps_additive 0.75 and scraps_liquid 1;
    # the new generated models are the override models the start tree did not have; each sits on its texture (scraps_plain for light == dark, scraps_bismuth for bismuth).
    scraps_model = read(ROOT/GENERATED_SCRAPS_MODEL)
    overrides = scraps_model.get('overrides', [])
    model_fields = [f for f in scrap_fields if f != 'MAT_COPPER']
    expected_overrides = [dict(model='hbmsntm:item/scraps_'+names_first(n_decl[f]['dict_arg']).lower(), predicate={'hbmsntm:scraps_type': (i + 1) / 256}) for i, f in enumerate(model_fields)
                          if f in n_decl and names_first(n_decl[f]['dict_arg'])] + [dict(model='hbmsntm:item/scraps_additive', predicate={'hbmsntm:scraps_type': 0.75}),
                                                                                    dict(model='hbmsntm:item/scraps_liquid', predicate={'hbmsntm:scraps_type': 1.0})]
    need(overrides == expected_overrides, f'{GENERATED_SCRAPS_MODEL} overrides are not the {len(model_fields)} materials at (i + 1) / 256 + additive 0.75 + liquid 1: {len(overrides)} overrides, first differing '
         + str(next(((i, a, b) for i, (a, b) in enumerate(zip(overrides, expected_overrides)) if a != b), None))[:300])
    override_models = ['assets/hbmsntm/models/item/'+o['model'].split('/', 1)[1]+'.json' for o in expected_overrides]
    EXPECTED_GENERATED = sorted(p for p in override_models if GENERATED_ROOT+p not in base['files'])
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d scrap models the start lacked: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, scraps.json and the expected models: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    model_textures, plain_models = {}, []
    for p in EXPECTED_GENERATED:
        live = read(ROOT/(GENERATED_ROOT+p)) if (ROOT/(GENERATED_ROOT+p)).is_file() else None
        layer = (live or {}).get('textures', {}).get('layer0', '')
        model_textures[p] = layer
        if layer == 'hbmsntm:item/scraps_plain': plain_models.append(p)
        need(live is not None and live.get('parent') == 'minecraft:item/generated' and layer.startswith('hbmsntm:item/scraps_')
             and (ROOT/(ASSETS_ROOT+'textures/item/'+layer.split('/', 1)[1]+'.png')).is_file(), f'generated {p} is not a generated-parent model on an existing scraps texture: {live}')
    expected_plain = sorted('assets/hbmsntm/models/item/scraps_'+names_first(n_decl[f]['dict_arg']).lower()+'.json' for f in plain)
    need(sorted(plain_models) == expected_plain, f'models on scraps_plain are {sorted(plain_models)}, expected the light == dark materials {expected_plain}')
    need(model_textures.get('assets/hbmsntm/models/item/scraps_bismuth.json') == 'hbmsntm:item/scraps_bismuth', 'scraps_bismuth.json is not on the imported scraps_bismuth texture')
    facts['generated_scrap_models'] = len(EXPECTED_GENERATED)
    # Mapped paths: every changed path inside the compare inventory must be matched by a feature group.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    feature_targets = {FEATURE_MATERIALS: NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + sorted(derived) + [ZH_INPUT, EN, GENERATED_SCRAPS_MODEL] + NEW_TOOLS[:1] + [GENERATED_ROOT+p for p in EXPECTED_GENERATED]}
    for gid in NEW_FEATURES:
        entry = new_groups.get(gid)
        if not need(entry is not None, f'migration/features.json lacks the group {gid}'): continue
        need(entry.get('status') == 'partial-unverified' and entry.get('reviewed_source_commit') == SOURCE_HEAD, f'features.json group {gid} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in FEATURE_SOURCES[gid] if not feature_matches(entry, 'source', p)]
        need(not missing_source, f'features.json group {gid} lists in neither source_paths nor source_watch: {missing_source[:4]} ({len(missing_source)} paths)')
        missing_target = [p for p in feature_targets[gid] if not any(feature_matches(f, 'target', p) for f in features)]
        need(not missing_target, f'features.json maps none of these {gid} paths (target_paths / target_watch of any group): {missing_target[:4]} ({len(missing_target)} paths)')
        absent = [p for p in entry.get('source_paths', []) if not (SOURCE/p).is_file()]
        need(not absent, f'features.json group {gid} source_paths missing in the original: {absent}')
    for gid, sources in EXISTING_GROUP_SOURCES.items():
        missing_source = [p for p in sources if gid not in by_id or not feature_matches(by_id[gid], 'source', p)]
        need(not missing_source, f'features.json group {gid} lists in neither source_paths nor source_watch: {missing_source}')
    need(set(by_id) == set(start_features) | set(NEW_FEATURES), 'features.json group ids are not the start ids + '+', '.join(NEW_FEATURES)+': '+str(sorted(set(by_id) ^ (set(start_features) | set(NEW_FEATURES)))))
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    need(set(notes_changed) <= NOTES_MAY_CHANGE, 'features.json groups whose notes changed beyond crucible-alloying, shredder and hazard-system: '+str(sorted(set(notes_changed) - NOTES_MAY_CHANGE)))
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in ('notes', 'target_watch')} != {k: v for k, v in start_features[i].items() if k not in ('notes', 'target_watch')})
    need(not shrunk and not other_fields, f'features.json previous groups lost target_watch entries {shrunk} or changed other fields {other_fields}')

    # 7. Evidence: GameTest log, audits, Gradle logs, diff, the final suite run, the verifier report, compare and the batch's own scripts and records.
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
    material_test_names = sorted(GAMETEST_METHOD.findall((ROOT/MATERIAL_TESTS).read_text(encoding='utf-8'))) if (ROOT/MATERIAL_TESTS).is_file() else []
    material_annotations = annotations(ROOT/MATERIAL_TESTS) if (ROOT/MATERIAL_TESTS).is_file() else 0
    need(bool(material_test_names) and material_annotations == len(material_test_names), f'{MATERIAL_TESTS} holds {material_annotations} @GameTest annotations and {len(material_test_names)} parsed methods')
    need(gametest_added == material_annotations, f'GameTest sources grew by {gametest_added} tests, MaterialSystemGameTests holds {material_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in material_test_names), 'GameTest log lacks "[hbm-material] <name> passed" for: '+str([n for n in material_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal27a/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad_findings = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad_findings and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad_findings))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal27a/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal27a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal27a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    inventory_files = sorted(p for p in INVENTORY_DIR.iterdir() if p.is_file() and p.suffix in ('.json', '.txt')) if INVENTORY_DIR.is_dir() else []
    need(bool(inventory_files), 'evidence missing: build/migration/goal27a/inventory/*.json / *.txt')
    for p in inventory_files: evidence[p.relative_to(ROOT).as_posix()] = sha(p)
    # The casting regressions (goal27a_casting_regression_run.py): one record per suite; its transcript is hashed with it. The final rerun is the last writer.
    casting = {}
    for suite in CASTING_SUITES:
        rec_path = CASTING_DIR/f'{suite}-compat.json'
        if not need(rec_path.is_file(), f'evidence missing: build/migration/goal27a/castingsuites/{suite}-compat.json (goal27a_casting_regression_run.py {suite})'): continue
        rec = read(rec_path)
        transcript = ROOT/rec['transcript'] if rec.get('transcript') else None
        casting[suite] = dict(record=rec_path.relative_to(ROOT).as_posix(), exit=rec.get('exit'), mode=rec.get('mode'), blockers=rec.get('blockers'), stages=rec.get('stages'),
                              javac_errors_by_attribution=rec.get('javac_errors_by_attribution'), transcript=rec.get('transcript'))
        evidence[rec_path.relative_to(ROOT).as_posix()] = sha(rec_path)
        if need(transcript is not None and transcript.is_file(), f'{rec_path.name} names no existing transcript'): evidence[transcript.relative_to(ROOT).as_posix()] = sha(transcript)
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal27a/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in modified_java if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal27a/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in modified_java if p in changes) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(p in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([p for p in listed_in_diff if p not in diff_text]))
    final = None
    # The suites of the goal26d final run plus the two casting regressions and the Goal27A verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1 + len(EXTRA_FINAL_SUITES)
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal26d final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites and not EXTRA_FINAL_SUITES & reference_suites, 'A Goal27A suite is already in the goal26d final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal27a/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE} | EXTRA_FINAL_SUITES, 'Final run suites differ from the goal26d final set + the two casting regressions + the Goal27A verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE} | EXTRA_FINAL_SUITES))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal27a/'+VERIFY_REPORT+' (tools/migration/verify_goal27a_material_system.py report)'):
        report = read(OUT/VERIFY_REPORT)
        required_hashes = [p for p in production_changed if not p.startswith(RES) or p == ZH_INPUT]
        problems = report_problems(report, required_hashes)
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        need(not summary_part.get('checks_pending'), VERIFY_REPORT+' still has pending checks: '+str(summary_part.get('checks_pending'))[:300])
        mutations = report.get('mutations')
        mutation_entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
        detected = summary_part.get('mutations_detected', sum(1 for e in mutation_entries if isinstance(e, dict) and e.get('detected') is True))
        total = summary_part.get('mutations_total', summary_part.get('mutations_applied', len(mutation_entries)))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=NEW_TOOLS[0],
                        tool_sha256=sha(ROOT/NEW_TOOLS[0]) if (ROOT/NEW_TOOLS[0]).is_file() else None, mutations_detected=f'{detected}/{total}', mutations_total=total,
                        checks_passed=summary_part.get('checks_passed'), command=report.get('command'))
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(re.findall(r'(?:Mats|NTMMaterial|MaterialShapes|MatDistribution|OreDictManager|TileEntityCrucible|ItemScraps|ItemAutogen|CrucibleRecipes|ShredderRecipes|RecipesCommon|ItemMold|HbmPotion|ModItems)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal26d compare target paths plus this batch's compare-inventory paths).
    cmp_prev = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal26d/compare.json differs from the goal26d receipt'
    prev_added = sorted(p for p in compare_paths(cmp_prev['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    prev_modified = sorted(p for p in compare_paths(cmp_prev['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(prev_added) | set(prev_modified) | set(own_target))
    expected_added = sorted(set(prev_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal27a/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-26d paths + %d of this batch)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(prev_added) + len(prev_modified), len(own_target))):
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
        for g in NEW_FEATURES:
            need(any(f.get('id') == g and f.get('state') == 'target-changed' for f in cmp['features']), f'{COMPARE} does not report {g} as target-changed')
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal26d (goal26d compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal26d_paths=len(prev_added) + len(prev_modified), goal27a_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-26D)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 8. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal27a, the D2 small fix or a recompile.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    d2_entries = []
    if need(sha(JAR) not in (previous_sha, D2_LIBS_SHA), 'build/libs/hbmsntm-198A.jar is still the previous (goal26d) package or the start D2 build (run the final build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in list(ASSETS) + sorted(derived)}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [e for e, t in asset_entries.items() if e not in names or not (ROOT/t).is_file() or jar.read(e) != (ROOT/t).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json, the 27A resources or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == en_delta == expected_delta and zh_jar == zh_delta == expected_delta,
                 f'JAR en_us.json or zh_cn.json delta against the previous package is not the {len(KEYS)} new keys: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            recompile_only = {n for n in RECOMPILE_ONLY if n in jar_delta['modified'] and recompile_equal(n, prior.read(n), jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        generated_entries = set(generated_added)
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if n.endswith('.class') and owner_class(n) in production_java: owner = [OWNER]
                elif kind == 'modified' and n.endswith('.class') and owner_class(n) == D2_SOURCE and D2_SOURCE not in changes: owner = [D2_OWNER]; d2_entries.append(n)
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY, SCRAPS_MODEL_ENTRY, 'META-INF/MANIFEST.MF'): owner = [OWNER]
                elif kind == 'added' and (n in asset_entries or n in generated_entries): owner = [OWNER]
                elif kind == 'modified' and n in recompile_only and owner_class(n) not in changes: owner = [RECOMPILE_OWNER]
                if not owner: unowned.append(f'{kind}: {n}' + (' [source ' + owner_class(n) + ' unchanged since the start: a recompile difference, not a source change]' if n.endswith('.class') and owner_class(n) not in changes else ''))
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the D2 ContaminationUtil class, the 27A resources, the generated additions and '
             'the modified en_us.json / zh_cn.json / scraps.json / MANIFEST.MF are owned): '+str(unowned[:10]))
        need(bool(d2_entries), 'the JAR delta against goal26d has no modified ContaminationUtil class (the D2 small fix must be in this package)')
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only and n not in d2_entries]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in production_java if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA),
             'Changed Java sources and goal27a JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, SCRAPS_MODEL_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the 27A resources + language + scraps.json + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for p in modified_java:
            if p in SAME_CLASS_JAVA: continue
            outer = p[len('src/main/java/'):-len('.java')]
            if p in changes: need(outer+'.class' in jar_delta['modified'], outer+'.class is not a modified JAR class')
        added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
        removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
        need(bool(classes) and len(classes) == prior_receipt['compiled_classes_verified'] + added_classes - removed_classes,
             f'Compiled class count {len(classes)} is not the previous count {prior_receipt["compiled_classes_verified"]} +{added_classes} -{removed_classes}')
        language = dict(en=en_jar, zh=zh_jar)

    # 9. Records: the release name and the batch reports.
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    for p in unnamed: need(False, 'record does not name '+RELEASE_NAME+': '+p)
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS:
        if p not in OPTIONAL_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p
    indexed = {Path(p).relative_to(OUT.relative_to(ROOT)).as_posix() for p in evidence if p.startswith(OUT.relative_to(ROOT).as_posix()+'/')}
    unindexed = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in indexed and p.name != 'baseline.json')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added),
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal26d_start=sorted(repinned),
                   en_delta=dict(added=len(en_delta['added']), removed=en_delta['removed'], changed=en_delta['changed']), zh_delta=dict(added=len(zh_delta['added']), removed=zh_delta['removed'], changed=zh_delta['changed']),
                   map_delta=dict(added=len(map_delta['added']), removed=map_delta['removed'], changed=map_delta['changed']), language_kinds=language_kinds, en_deviations=en_deviations,
                   original_lang_values_checked=original_text_checked, language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, line_endings=line_endings, added_code=added_code_facts,
                   material_system={k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v)) < 200 else f'<{len(v)} items>') for k, v in facts.items()}, material_facts_bad=bad,
                   generators=generators, client_refs_in_common_classes=sorted(p for p, v in client_refs.items() if v),
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_material_tests=material_test_names, final_suites_expected=final_expected,
                   casting_regressions={s: dict(exit=c['exit'], mode=c['mode'], blockers=len(c['blockers'] or []), javac_errors_by_attribution=c['javac_errors_by_attribution']) for s, c in casting.items()},
                   compare=opt(compare, 'counts'), compare_target_expected=len(expected_target), compare_added_expected=len(expected_added),
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta, class_owners=class_owners, d2_entries=d2_entries,
                   protected_paths=len(protected), old_releases_preserved=len(old_releases), preserved_release_files=len(base['old_release_files']),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)),
                   out_files_not_indexed=unindexed)
    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)

    # The receipt: assembled in both modes (None where the evidence does not exist yet in --check); only the real run writes it, and there every need() above raised.
    dest = RELEASE/RELEASE_NAME
    digest = sha(JAR)
    hashes = {p: sha(ROOT/p) for p in reports if (ROOT/p).is_file()}
    material_system = dict(neo=NEW_JAVA + MODIFIED_JAVA, original=O_SOURCES, facts=facts, expected=EXPECTED, known_differences=KNOWN_DIFFERENCES, original_references=original_refs,
                           decisions='main-notes.md "Decided" 1-10, review-report.md P2-1 (damaged items), P2-2 (ingot_raw shredder rows), P3-1 (getPreferred), P3-3 (JEI grid), the GameTest defect '
                                     '(the shredder wildcard retry removed)',
                           note=f'The original material table ({facts.get("materials_original")} declarations, IDs unique, {EXPECTED["conversions"]} conversions; NEO keeps every declaration verbatim apart from the '
                                f'names(...) argument) with the NEO item-to-material registry MaterialEntries ({EXPECTED["entries_rows"]} rows, {EXPECTED["entries_neo_only"]} NEO-only: vanilla copper ingot / block, '
                                f'iron nugget, welded lead and HSS plates; {EXPECTED["entries_materials"]} materials with rows); MatDistribution ({EXPECTED["distribution_rows"]} default rows, config hbmCrucibleSmelting.json, '
                                'registered right after CrucibleRecipes); the original lookup order (tag entries, the first SMELTABLE / ADDITIVE prefix row at shape.q(1), item entries, scraps) and integer '
                                'conversion; the crucible smelting per material with MAX_SYNC_ENTRIES = the material count and unchanged save keys, legacy copper key and unknown-ID dropping; scraps for the '
                                f'{EXPECTED["scrap_materials"]} SMELTABLE / ADDITIVE materials (model values (i+1)/256, additive liquid 0.75, liquid 1, plain texture for the {EXPECTED["plain_scrap_materials"]} '
                                f'light == dark materials, bismuth override, copper base, molten tint for plain); {EXPECTED["shredder_rows"]} shredder rows and the exact lookup; damaged durable items skip the '
                                f'item entries; getPreferred follows the original fragment rule; {EXPECTED["effect_icons"]} effect icons cropped at (x*18, 198+y*18).')
    casting_record = dict(suites=casting, wrapper='tools/migration/goal27a_casting_regression_run.py', policy='tools/migration/goal27a_casting_compat.py',
                          note='The two frozen isolated casting regressions (verify_goal10a.py with goal10a_regression/, verify_goal5a_casting.py with goal5a_casting_regression/) run through the Goal27A '
                               'wrapper, which may only add stand-ins; on the Goal27A tree it records them as blocked (MaterialEntries needs the frozen NtmItems.Ref stand-in to implement ItemLike, the '
                               'frozen ComparableStack stand-in cannot key Mats.materialEntries, and the Goal 10A fixture passes a MeltEntry to the changed CrucibleSmeltingRecipeHandler) and runs them '
                               'unwrapped: both stop at javac, so none of their assertions (the 5-material orderedList, the 13 melt entries, the 0.2 model steps, the creative-tab and NtmJeiPlugin '
                               'lines, the copper-only table) is reached; part of the compile errors predate 27A (FoundryMoldBlockEntity, CompoundTagControl and CrucibleCastingRecipeHandler use names '
                               'the frozen stand-ins lack). Their Goal 10A / 5A behaviour is covered on the 27A tree by MaterialSystemGameTests (crucible, scraps) only.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(facts.get('materials_original'), len(KEYS), len(material_test_names), gametest_expected, EXPECTED['entries_rows'], EXPECTED['shredder_rows'], len(new_icons)),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=dict(commit=start_head[:8], files=planning_files, note='The Goal 27 planning commit (local, not pushed): task books 27A..27D, GOAL27.md, the thread prompts, the README and GOAL26.md entry lines.'),
                   uncommitted_start=dict(status_entries=0, status=[], description='none: the start worktree was clean (HEAD 71c2f660)'),
                   small_fix_d2=dict(owner=D2_OWNER, source=D2_SOURCE, readme_line=d2_line, build_libs_sha256_at_freeze=start_jar_sha, start_sha256=base['files'][D2_SOURCE], current_sha256=sha(ROOT/D2_SOURCE),
                                     jar_entries=d2_entries, note='Small fix after goal26d (2026-10-23, Goal 26 acceptance defect D2: ContaminationUtil.java:101-102 3.6F -> 3.6D, original ContaminationUtil.java:202-203), committed in '
                                                                  '0786697d, first packaged by goal27a; its class is owned by this fix, not by goal27a.'),
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, reconstruction=base['reconstruction'], goal26_closeout_commit=chain[1], goal26_planning_commit=chain[2],
                                      note=f'The start tree is HEAD 71c2f660 (the Goal 27 planning commit, local, not pushed) on the pushed Goal 26 close-out 0786697d (= origin/master) on the Goal 26 planning commit '
                                           f'6bfb7ad2, with a clean worktree. build/libs at the start is the post-D2 small-fix build {start_jar_sha[:8]}, not the goal26d package. The original did not move since 24A '
                                           f'(aee05a40f). freeze_start.py hashed every tracked file live ({len(base["files"])} baseline hashes) before the first 27A write and copied the files the batch planned to touch '
                                           f'({len(base["copied_scope"])} baseline-files); paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) + sorted(derived) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, line_endings=line_endings, start_copies_supplement=[],
                   resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported, derived_resources=derived_facts, unchanged_resources=unchanged_facts, generators=generators,
                   material_system=material_system, casting_regressions=casting_record,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=sorted(k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'), english_deviations=en_deviations,
                                 original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note=f'{expected_kinds["upstream"]} entries are upstream (hbmmat.<names[0]> with the original English and Chinese of en_US.lang:1616-1733 / the zh_CN.lang hbmmat block; '
                                      f'hbmmat.mingrade "Red Copper" and hbmmat.cmbsteel "CMB Steel" follow the NEO item wording with the originals in source_en); {expected_kinds["local"]} are local '
                                      '(ilmenite, coalcoke, lignitecoke, ghiorsium336, polycarbonate, casting.scraps.additive). No existing key changes its value; no deferred entry is added.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith('repinned_since_')},
                   repinned_since_goal26d_start={p: dict(goal26d_start_pin_sha256=h, goal27a_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok'), old_machine_suites_through=OLD_MACHINE_SUITES, extra_suites=sorted(EXTRA_FINAL_SUITES)),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_material_tests=material_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per MaterialSystemGameTests test (names in new_material_tests): what those '
                                      'tests assert about the material table, the lookup, the crucible (a placed block entity, heat and progress set directly, one updateEntity tick), save / load and the sync codec, '
                                      'the scraps tab, colours and model values, the shredder rows and the effect icon files on the classpath; no client (models, tints, JEI, the creative screen and effect icons '
                                      'are not drawn), no real player, no saved world, no survival chain.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['radiation_medicine (the Goal26D-only key; Goal27A adds material_system; the pill / consumable constants, the four recipes, the sound events and the config key are not carried)',
                                 'recipes (Goal27A adds no crafting recipe)', 'goal26a_delivery / goal26b_delivery / goal26c_delivery / planning_supplements (no uncommitted delivery at this start)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, both resource generators with --check, the final old-suite rerun (the six old isolated suites through the goal26c wrapper and the two casting regressions through '
                            'the goal27a wrapper, which records them as blocked and stopping at javac), compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. No in-game '
                            'client test was run: item models, scrap tints and textures, JEI smelting groups, the creative screen, the effect icons and Chinese UI are not seen on screen; no survival chain '
                            '(mining, smelting ores and scraps in a crucible, casting, shredding coal) in a world was run; no dedicated server beyond GameTest; the acceptance checklist GOAL27A-ACCEPTANCE.md '
                            'is written, not run, and merges into the Goal 27D master list.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, D2_LIBS_SHA), 'build/libs JAR is the previous package or the start D2 build'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal27a JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal26d package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
