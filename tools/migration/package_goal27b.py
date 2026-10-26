"""Package Goal27B (the second batch of Goal 27, crucible alloys and the tier-4 anvil: the 13 original crucible alloy recipes in CrucibleRecipes (steel, hematite,
malachite, red copper, HSS, ferrouranium, Tc alloy, cadmium alloy, bismuth bronze, arsenic bronze, CMB steel, magnetized tungsten, BSCCO), ferrouranium making the tier-4
anvil reachable through the existing smithing upgrade, the 12 RBMK tier-4 anvil recycling rows in AnvilRecipes, the lead anvil crafting recipe in NtmRecipeProvider, the
CrucibleAlloyGameTests and the anvil assertions of three RBMK GameTest classes), cumulatively on the goal27a package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal27b.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal27b/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal27b/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal27b/baseline.json: NEO HEAD 71c2f660 (the Goal 27 planning commit, local, not pushed; 8 files) on the Goal 26 close-out
0786697d (pushed, = origin/master) with 201 status lines: the uncommitted Goal27A delivery (packaged as goal27a, not committed) plus the 2026-10-26 task-book / thread-
prompt edits (GOAL27B.md, GOAL27C.md, GOAL27D.md, GOAL27-THREAD-PROMPTS.md; GOAL27.md is in the goal27a receipt as a shared record). freeze_start.py hashed every tracked and
dirty file live (10,746 hashes) before the first 27B write and copied the 221 dirty or planned files into baseline-files/; start_status.txt (201 lines), start_head.txt and
start_hashes.txt (201 hashes) record it. The start bytes of a file are the live bytes at the freeze = baseline-files; the 201 dirty start files are exactly the goal27a
receipt's 197 changed files plus the four planning documents, and each equals its goal27a after-hash (only the shared records the goal27a receipt does not hash may
differ: GOAL27.md). build/libs at the start is the goal27a package (baseline build_libs_jar_sha256_at_freeze = the goal27a JAR hash: no small fix in between). The
original HEAD aee05a40f did not move since 24A, so there is no upstream classification and no new snapshot. Every change since the start is computed from the baseline
file hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with
their start bytes (baseline-files) and their +/- lines are reported. The JAR delta against the goal27a package is attributed per entry; any entry without exactly one
owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, recipes, rows) are computed here from the original and NEO sources
where they can be; the expected crucible-alloy figures the handoff states are asserted against those computations (the handoff slips the verifier report confirmed -
ferrouranium takes 3 executions per ingot, not 8; 18 smithing upgrade rows + 5 special rows, not 20 - are asserted in their corrected form).

The receipts that hash records (goal21a..goal27a, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start (the acceptance
checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes, known from earlier batches); they are listed in the receipt as start drift and
must still equal their Goal27B start hash; no receipt is rewritten and no other protected path may drift. The goal27a receipt itself drifts nowhere (baseline
previous_receipt_evidence_drift is empty). GOAL27A.md and every GOAL27A-* / goal27a-* record, GOAL27C.md, GOAL27D.md, GOAL27-THREAD-PROMPTS.md, every Goal 26 and earlier
record, SURVIVAL-PLAYABILITY.md, FOUNDATIONS.md and RESOURCE-OWNERSHIP.md must equal their start hash; migration/GOAL27.md is a shared record, GOAL27B.md the task book and
delivery record (hashed by the receipt).

Like the packagers of 24B..27A this one has a single compare run (build/migration/goal27b/compare.json against the snapshot review-aee05a40f10f.json taken at the
end of 24A: original 0/0/0, target = exactly the goal27a compare target paths (read from build/migration/goal27a/compare.json) plus this batch's compare-inventory
paths, the stamp dropped), no upstream classification; it adds the crucible_alloys facts (checked against the original and NEO source texts). The Goal27A-only receipt keys
material_system, casting_regressions, small_fix_d2, resource_ownership and the resource tables are dropped and the receipt says so; the two old casting regressions run
unchanged through the goal27a wrapper in the final rerun and their javac errors are attributed by casting_attribution.py (casting-attribution.json)."""
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
from package_goal24a import original_text, original_line, SOURCE_HEAD
from package_goal27a import (OUT as GOAL27A_OUT, BASELINE as GOAL27A_BASELINE, protected_paths as goal27a_protected_paths, split_top, is_comment, body_of,
                             OLD_MACHINE_SUITES)

OUT = ROOT/'build/migration/goal27b'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
START_HASHES = OUT/'start_hashes.txt'
REFERENCE_PREVIOUS = GOAL27A_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL27A_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal27a/hbmsntm-198A-goal27a.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal27b'
RELEASE_NAME = 'hbmsntm-198A-goal27b.jar'
OWNER = 'goal27b'
PREVIOUS_OWNER = 'goal27a'
PLANNING_OWNER = 'goal27-planning-edits-2026-10-26'
PLANNING_PREFIX = '71c2f660'
PLANNING_FILES = 8
GOAL26_CLOSEOUT = '0786697d'
GOAL26_PLANNING = '6bfb7ad2'
START_STATUS_LINES = 201
# The planning-session edits of 2026-10-26 that the goal27a receipt does not list (the task books of the other batches and the thread prompts; GOAL27B.md is also this
# batch's task book and delivery record, hashed by the new receipt).
PLANNING_EDITS = ['migration/GOAL27-THREAD-PROMPTS.md', 'migration/GOAL27B.md', 'migration/GOAL27C.md', 'migration/GOAL27D.md']
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a', 'goal26b', 'goal26c', 'goal26d'}

# Production (owner goal27b): the NEW GameTest class, the three MODIFIED production sources, and the three RBMK GameTest classes edited by design (their anvil assertions:
# the old "no row outputs or consumes the columns" check became "exactly the 12 Goal 27B tier-4 RECYCLING rows"; verifier-report.md lists the hunks).
NEW_JAVA = [J+'gametest/CrucibleAlloyGameTests.java']
(ALLOY_TESTS,) = NEW_JAVA
MODIFIED_JAVA = [J+p+'.java' for p in ('inventory/recipes/CrucibleRecipes', 'inventory/recipes/anvil/AnvilRecipes', 'datagen/NtmRecipeProvider')]
(CRUCIBLE_RECIPES, ANVIL_RECIPES, RECIPE_PROVIDER) = MODIFIED_JAVA
EDITED_GAMETESTS = [J+'gametest/'+n+'.java' for n in ('RBMKCoreGameTests', 'RBMKControlSteamGameTests', 'RBMKReactorGameTests')]
OLDER_GAMETEST_DIR = J+'gametest/'
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + EDITED_GAMETESTS
# Must stay byte-identical to the start (the handoff list; FoundryMoldBlockEntity's real path is blockentity/machine/), plus every other GameTest class, every
# handler/jei class and every AnvilSmithing* class: see main().
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'inventory/material/Mats', 'inventory/material/MaterialEntries', 'inventory/material/MatDistribution', 'inventory/material/MaterialShapes', 'inventory/material/NTMMaterial',
    'blockentity/machine/MachineCrucibleBlockEntity', 'blockentity/machine/FoundryMoldBlockEntity', 'inventory/recipes/CopperCastingRecipes', 'inventory/recipes/CrucibleRecipe',
    'inventory/recipes/loader/SerializableRecipe', 'inventory/recipes/ShredderRecipes', 'inventory/recipes/ChemicalPlantRecipes', 'blocks/machine/NTMAnvilBlock',
    'inventory/menus/AnvilMenu', 'network/toserver/AnvilConstructionPacket', 'items/NtmItems', 'blocks/NtmBlocks', 'datagen/NtmLanguageProvider', 'items/CopperScrapsItem',
    'inventory/NtmCreativeTabs', 'util/ContaminationUtil')]
UNCHANGED_FILES = [ZH_INPUT, LOCALIZATION_RECORD, EN]
# Older tools that must equal their start bytes (handoff list); every file of the two frozen casting regression folders is added in main().
OLD_TOOLS_FROZEN = ['tools/migration/'+p for p in ('package_goal27a.py', 'verify_goal27a_material_system.py', 'goal27a_casting_regression_run.py', 'goal27a_casting_compat.py',
                                                    'goal27a_scrap_textures.py', 'goal27a_effect_icons.py', 'goal26c_oldsuite_run.py', 'goal26c_oldsuite_compat.py', 'verify_goal10a.py',
                                                    'verify_goal10a_resources.py', 'verify_goal5a_casting.py', 'verify_goal5a_casting_resources.py', 'goal10a_scrap_textures.py',
                                                    'goal10a_mutation_check.py')]
FROZEN_TOOL_DIRS = ('tools/migration/goal10a_regression/', 'tools/migration/goal5a_casting_regression/')
NEW_TOOLS = ['tools/migration/verify_goal27b_crucible_alloys.py', 'tools/migration/package_goal27b.py']
TOOLS = NEW_TOOLS
# Generated by runData: the new lead anvil recipe, its advancement and the stamp. en_us.json must stay byte-identical (no language key, no crucible.* key).
RECIPE_JSON = 'data/hbmsntm/recipe/anvil_lead.json'
ADVANCEMENT_JSON = 'data/hbmsntm/advancement/recipes/misc/anvil_lead.json'
EXPECTED_GENERATED = sorted([RECIPE_JSON, ADVANCEMENT_JSON])
GENERATED = [STAMP] + [GENERATED_ROOT+p for p in EXPECTED_GENERATED]
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal27b-* or GOAL27B-* record is hashed as well.
REPORTS = ['migration/GOAL27B.md', 'migration/GOAL27B-ACCEPTANCE.md', 'migration/goal27b-static-review.md', 'migration/goal27b-materials-review.json', 'migration/goal27b-localization-review.json']
LEDGER = REPORTS[3]
BATCH_RECORD = re.compile(r'migration/(goal27b-[^/]+\.(json|md)|GOAL27B-[^/]+\.md)')
GOAL27_RECORD = 'migration/GOAL27.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', GOAL27_RECORD]
# Shared records the batch may leave untouched (no language key: LOCALIZATION.md only "if touched" - an assumption, the handoff lists it as changed).
OPTIONAL_RECORDS = ['migration/LOCALIZATION.md']
# The records of the other batches and the files no batch of this kind touches: no change is expected.
PLANNING_FROZEN = ['migration/GOAL27C.md', 'migration/GOAL27D.md', 'migration/GOAL27-THREAD-PROMPTS.md', 'migration/SURVIVAL-PLAYABILITY.md', 'migration/FOUNDATIONS.md',
                   'migration/RESOURCE-OWNERSHIP.md']
# Every Goal 26 and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 26) and every Goal27A record (GOAL27A.md, GOAL27A-*, goal27a-*).
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-6])(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-6])(?!\d)[a-z]?-[^/]+|GOAL27A(?:-[^/]+)?\.md|goal27a-[^/]+)')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = NEW_JAVA + MODIFIED_JAVA + EDITED_GAMETESTS + GENERATED + TOOLS + REPORTS + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-alloy] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the
# sessions of the batch. Every top-level handoff-*.md and *-report.md of OUT is indexed as well.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'start_compile.log', 'prod_compile.log', 'start_status.txt', 'start_head.txt',
                  'start_hashes.txt', 'main-notes.md', 'handoff-verifier.md', 'handoff-packaging.md', 'verifier-report.md', 'chain.sh', 'make_production_diff.py',
                  'production-vs-start-draft.diff')
# Review files under OUT; each must exist and is indexed by the receipt. --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'casting_attribution.py', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-progress.md', 'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier-gt/scope-before.txt', 'verifier-gt/scope-after.txt',
                   'verify-final.out', 'compare.log', 'localization-final.log', 'resources-audit-final.log', 'packaged-resources-final.log')
CASTING_ATTRIBUTION = 'casting-attribution.json'
CASTING_DIR = OUT/'final/castingsuites'
CASTING_SUITES = ('verify_goal10a', 'verify_goal5a_casting')
FAIL_SET_DIFF = 'final/fail-set-diff.json'
GAMETEST_LOG = 'build/migration/goal27b/gametest-final.log'
NEW_SUITE = 'verify_goal27b_crucible_alloys.py --gametest-log build/migration/goal27b/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# JAR classes whose source is unchanged since the start and that differ from the previous package only in recompiled debug names (as in 26A-27A).
RECOMPILE_ONLY = {'com/hbm/gametest/RBMKRecyclingGameTests$1.class': (((b'\x01\x00\x04arg0', b'\x01\x00\x03pos'), (b'\x01\x00\x04arg1', b'\x01\x00\x05state')),
                                                                    ((b'\x01\x00\x03pos', b'\x01\x00\x04arg0'), (b'\x01\x00\x05state', b'\x01\x00\x04arg1')))}
RECOMPILE_OWNER = 'recompile-debug-names'
# features.json: no new group; only these groups' notes / target_paths / target_watch may change (handoff: crucible-alloying, anvil-stamps and the RBMK groups).
NOTES_MAY_CHANGE = {'crucible-alloying', 'anvil-stamps'}
RBMK_GROUP = re.compile(r'rbmk-[a-z]+')
# The groups the snapshot of the end of 24A predates (24B..27A).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser', 'rbmk-autoloader', 'rbmk-crane',
                          'hazard-system', 'radiation-detection', 'gas-masks', 'hazmat-suits', 'radiation-medicine', 'material-system'}
RADIATION_NOTE = 'Goal27B: the crucible now alloys uranium-238 into ferrouranium and technetium-99 into Tc alloy; handle radioactive inputs only in a disposable world. '
MELTDOWN_NOTE = 'Goal27B: no new meltdown path; recycling a column does not touch its reactor. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_CRUCIBLE_RECIPES = ORIGINAL+'inventory/recipes/CrucibleRecipes.java'
O_ANVIL_RECIPES = ORIGINAL+'inventory/recipes/anvil/AnvilRecipes.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_SHAPES = ORIGINAL+'inventory/material/MaterialShapes.java'
O_MATS = ORIGINAL+'inventory/material/Mats.java'
O_ANVIL_BLOCK = ORIGINAL+'blocks/machine/NTMAnvil.java'
O_MODBLOCKS = ORIGINAL+'blocks/ModBlocks.java'
O_SOURCES = [O_CRUCIBLE_RECIPES, O_ANVIL_RECIPES, O_CRAFTING, O_SHAPES, O_MATS, O_ANVIL_BLOCK, O_MODBLOCKS]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'crucible_register_defaults': (O_CRUCIBLE_RECIPES, 'public void registerDefaults()'), 'crucible_gt6_branch': (O_CRUCIBLE_RECIPES, 'if(Compat.isModLoaded(Compat.MOD_GT6))'),
    'crucible_steel': (O_CRUCIBLE_RECIPES, 'new CrucibleRecipe("crucible.steel")'), 'crucible_hematite': (O_CRUCIBLE_RECIPES, 'new CrucibleRecipe("crucible.hematite")'),
    'crucible_ferro': (O_CRUCIBLE_RECIPES, 'new CrucibleRecipe("crucible.ferro")'), 'crucible_tcalloy': (O_CRUCIBLE_RECIPES, 'new CrucibleRecipe("crucible.tcalloy")'),
    'crucible_bscco': (O_CRUCIBLE_RECIPES, 'new CrucibleRecipe("crucible.bscco")'), 'crucible_molds_for_nei_call': (O_CRUCIBLE_RECIPES, 'registerMoldsForNEI();'),
    'anvil_rbmk_first_row': (O_ANVIL_RECIPES, '//RBMK'), 'anvil_rbmk_reasim': (O_ANVIL_RECIPES, 'new ComparableStack(ModBlocks.rbmk_rod_reasim)'),
    'anvil_rbmk_528_branch': (O_ANVIL_RECIPES, 'if(!GeneralConfig.enable528) {'), 'anvil_reactor_research': (O_ANVIL_RECIPES, 'new ComparableStack(ModBlocks.reactor_research)'),
    'anvil_smithing_ferro': (O_ANVIL_RECIPES, 'new ItemStack(ModBlocks.anvil_ferrouranium, 1), new ComparableStack(anvil)'),
    'anvil_lead_recipe': (O_CRAFTING, 'new ItemStack(ModBlocks.anvil_lead, 1)'), 'anvil_murky_recipe': (O_CRAFTING, 'new ItemStack(ModBlocks.anvil_murky, 1)'),
    'anvil_ferro_block': (O_MODBLOCKS, 'anvil_ferrouranium = new NTMAnvil(Material.iron, NTMAnvil.TIER_NUCLEAR)'),
    'anvil_lead_block': (O_MODBLOCKS, 'anvil_lead = new NTMAnvil(Material.iron, NTMAnvil.TIER_IRON)'),
}
# Expected figures of the handoff, with the two slips the verifier report confirmed corrected (ferro executions, smithing rows).
EXPECTED = dict(crucible_recipes=13, gt6_rows=3, rbmk_rows=12, rbmk_original_rows=15, rbmk_not_ported=3, nugget=8, ingot=72, ferro_executions=3, smithing_upgrade_rows=18, smithing_special_rows=5,
                language_keys=0, deferred_entries=106, generated_added=2)
# The original RBMK rows the batch does not port: ReaSim x2 (AnvilRecipes.java:902-913, ReaSim columns deferred) and reactor_research (:952-962, @Deprecated).
RBMK_NOT_PORTED = ['rbmk_rod_reasim', 'rbmk_rod_reasim_mod', 'reactor_research']
KNOWN_DIFFERENCES = {
    'gt6_rows': 'the three GT6-gated steel recipes crucible.steelWrought / steelPig / steelMeteoric (CrucibleRecipes.java:67-76, Compat.MOD_GT6) are not ported: NEO registers the 13 default recipes only',
    'icons': 'hematite and malachite use NEO\'s separate resource blocks (NtmBlocks.RESOURCE_HEMATITE / RESOURCE_MALACHITE) instead of the stone_resource metadata blocks; their worldgen is Goal 28',
    'molds_for_nei': 'registerMoldsForNEI() (CrucibleRecipes.java:127, :251-269, the NEI casting display list over ItemMold molds) is not ported; the casting displays and the general ingot mold are 27D',
    'display_names': 'like upstream no recipe sets a display name (no setNamed), so the GUI shows the icon\'s item name and no crucible.* language key is added (Goal 10A rule)',
    'rbmk_rows': 'the 12 tier-4 RBMK rows use the RECYCLING overlay (upstream\'s 1:many AnvilConstructionRecipe constructor); the ADVANCED circuit is NEO\'s circuit_military_grade_board, the STEEL / COPPER shell and pipe '
                 'metadata items are shell_steel, shell_copper and pipe_copper; the two ReaSim rows and reactor_research are not ported',
    'lead_anvil': 'the lead anvil recipe (CraftingManager.java:295) uses NEO\'s lead ingot and block and meta Variant.LEAD; the murky anvil recipe (:296, needs ModItems.undefined) is not ported',
    'reachability': 'ingots of ferrouranium and Tc alloy come out of the crucible as molten material and only the existing molds cast them (foundry mold casts HSS, tungsten and copper / steel / tungsten / HSS plates until '
                    '27D generalises the molds); cadmium alloy, bismuth bronze, arsenic bronze, CMB steel, magnetized tungsten, BSCCO, hematite and malachite stay creative-only until Goal 28',
}
MATERIAL_STACK = re.compile(r'new MaterialStack\(Mats\.(MAT_\w+),\s*([^)]*)\)')
CRUCIBLE_STATEMENT = re.compile(r'this\.register\(new CrucibleRecipe\("(?P<name>[^"]+)"\)\.setup\((?P<freq>\d+),\s*(?P<icon>.*?)\)\s*\.inputs\((?P<inp>.*?)\)\s*\.outputs\((?P<out>.*?)\)\);', re.S)
ANVIL_ROW = re.compile(r'new AnvilConstructionRecipe\(\s*new ComparableStack\((?P<input>[^)]*(?:\([^)]*\))?)\),\s*new AnvilOutput\[\]\s*\{(?P<outputs>.*?)\}\s*\)(?P<tail>\.setTier\(\d+\)(?:\.setOverlay\(OverlayType\.\w+\))?)\);', re.S)
# 27A ones the receipt carries forward under a new heading.
CARRIED_REPINS = 'repinned_since_'


def scope_text(tests, total_tests, recipes, rows):
    return (f'Goal27B (the second batch of Goal 27: crucible alloys and the tier-4 anvil): the {recipes} original crucible alloy recipes (steel, hematite, malachite, red copper, HSS, ferrouranium, Tc alloy, '
            f'cadmium alloy, bismuth bronze, arsenic bronze, CMB steel, magnetized tungsten, BSCCO), ferrouranium making the tier-4 anvil reachable through the existing smithing upgrade, {rows} RBMK tier-4 '
            f'anvil recycling rows, the lead anvil crafting recipe; {tests} CrucibleAlloyGameTests ({total_tests} GameTests in total, one batch per test). Gameplay impact: the crucible makes steel (iron + '
            f'carbon + flux) and ferrouranium (steel + uranium-238), Tc alloy, red copper and HSS; ten ferrouranium ingots turn an iron or lead anvil into the tier-4 ferrouranium anvil; RBMK columns can be '
            f'recycled on it; the lead anvil can be crafted; chem.ducrete and the Desh flat stamp become reachable; the other six alloys stay creative-only until Goal 28; ingots of ferrouranium come out of the '
            f'crucible as molten material and only the existing molds cast it (the general ingot mold is 27D).')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal27b release directory: '+rel


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
    """The Goal27B start hash of a frozen path: baseline files, or for a build/ record (Git-ignored, so baseline files does not list it) the hash the goal27a receipt
    records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal27a packager protected (built there from the Goal21A..Goal26D starts and receipts and the goal27a start), plus every path the goal27a receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (goal21a..goal26d) and every release file of the frozen start (the goal27a package
    included). The records that already drifted (the older drift: the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes)
    are pinned at their Goal27B start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal27a packager set at its Goal27A start hash, for the records that changed between the starts."""
    goal27a_start = read(GOAL27A_BASELINE)
    out = dict(goal27a_protected_paths(goal27a_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal27a receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal27a_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    assert all(p.endswith('-ACCEPTANCE.md') for p in repinned), 'A non-checklist pin changed between the Goal27A and Goal27B starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal27a_start):
    """{path: {receipts, start_sha256, goal27a_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal27a receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal27a receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21..26 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal27a '
                           'receipt does not hash it. Frozen at the Goal27B start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal27a) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal27a package; the goal27a receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal27a '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal27a_start_sha256=goal27a_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal27a_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def group(p):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA: return 'production'
    if p in EDITED_GAMETESTS: return 'gametest-edited'
    if p in GENERATED: return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    return None


def recompile_equal(name, previous_bytes, new_bytes):
    """True when the previous class bytes, patched in one of the directions RECOMPILE_ONLY allows (every pattern occurring exactly once), equal the new class bytes."""
    for pairs in RECOMPILE_ONLY[name]:
        patched = previous_bytes
        if any(patched.count(a) != 1 for a, b in pairs): continue
        for a, b in pairs: patched = patched.replace(a, b)
        if patched == new_bytes: return True
    return False


def drop_body(text, signature):
    """The text without the brace-balanced body of the first method whose header contains `signature` (header kept)."""
    body = body_of(text, signature)
    return text.replace(body, '', 1) if body else text


def squeeze(text):
    """Text without blank lines and trailing blanks (for comparing a method body that only gained or lost a call line)."""
    return '\n'.join(l.rstrip() for l in text.split('\n') if l.strip())


def crucible_rows(text, skip_gt6=False):
    """[(name, frequency, icon, inputs, outputs)] of the `this.register(new CrucibleRecipe(...))` statements of a registerDefaults body (comment lines excluded); amounts stay
    symbolic ("n*2", "i"); the GT6-gated block of the original is cut out first (and counted by the caller)."""
    body = body_of(text, 'public void registerDefaults()')
    if skip_gt6: body = body.replace(body_of(body, 'if(Compat.isModLoaded(Compat.MOD_GT6))'), '', 1)
    body = '\n'.join(l for l in body.split('\n') if not l.lstrip().startswith('//'))
    rows = []
    for m in CRUCIBLE_STATEMENT.finditer(body):
        stacks = lambda s: [(mat, re.sub(r'\s+', '', amount)) for mat, amount in MATERIAL_STACK.findall(s)]
        rows.append((m.group('name'), int(m.group('freq')), re.sub(r'\s+', '', m.group('icon')), stacks(m.group('inp')), stacks(m.group('out'))))
    return rows


def amount(expr, nugget, ingot):
    assert re.fullmatch(r'[ni0-9*]+', expr), 'Unexpected amount expression '+expr
    return eval(expr.replace('n', str(nugget)).replace('i', str(ingot)))


def neo_icon(original_icon):
    """The NEO icon expression of an original crucible icon: ModItems.x -> NtmItems.X.get(), stone_resource HEMATITE / MALACHITE -> NtmBlocks.RESOURCE_*.get()."""
    m = re.fullmatch(r'newItemStack\(ModItems\.(\w+)\)', original_icon)
    if m: return f'newItemStack(NtmItems.{m.group(1).upper()}.get())'
    m = re.fullmatch(r'DictFrame\.fromOne\(ModBlocks\.stone_resource,EnumStoneType\.(HEMATITE|MALACHITE)\)', original_icon)
    return f'newItemStack(NtmBlocks.RESOURCE_{m.group(1)}.get())' if m else None


ORIGINAL_SPECIAL_ITEMS = {('circuit', 'EnumCircuitType.ADVANCED.ordinal()'): 'NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get()', ('shell', 'Mats.MAT_STEEL.id'): 'NtmItems.SHELL_STEEL.get()',
                          ('shell', 'Mats.MAT_COPPER.id'): 'NtmItems.SHELL_COPPER.get()', ('pipe', 'Mats.MAT_COPPER.id'): 'NtmItems.PIPE_COPPER.get()'}


def neo_item(original_item, meta):
    """The NEO expression of an original item / block constant (with the NEO names of the metadata items)."""
    item = original_item.strip()
    if item.startswith('Blocks.'): return 'Blocks.'+item[len('Blocks.'):].upper()
    kind, _, name = item.partition('.')
    if meta is not None:
        return ORIGINAL_SPECIAL_ITEMS.get((name, meta.strip()))
    return f'{"NtmBlocks" if kind == "ModBlocks" else "NtmItems"}.{name.upper()}.get()'


def anvil_rows(text, original):
    """[(input, tier, overlay, [(output, count, chance)])] of the AnvilConstructionRecipe statements of `text` whose input is an RBMK column (the original: ModBlocks.rbmk_* and
    reactor_research; NEO: NtmBlocks.RBMK_*), in source order; comment lines excluded. Original items are mapped to the NEO names (None when no mapping exists)."""
    text = '\n'.join(l for l in text.split('\n') if not l.lstrip().startswith('//'))
    rows = []
    for m in ANVIL_ROW.finditer(text):
        raw = re.sub(r'\s+', '', m.group('input'))
        if original:
            mm = re.fullmatch(r'ModBlocks\.(rbmk_\w+|reactor_research)', raw)
            if not mm: continue
            name, column = mm.group(1), f'NtmBlocks.{mm.group(1).upper()}.get()'
        else:
            mm = re.fullmatch(r'NtmBlocks\.(RBMK_\w+)\.get\(\)', raw)
            if not mm: continue
            name, column = mm.group(1).lower(), raw
        tier = int(re.search(r'setTier\((\d+)\)', m.group('tail')).group(1))
        overlay = (re.search(r'OverlayType\.(\w+)', m.group('tail')) or [None, None])[1]
        outputs = []
        for chunk in m.group('outputs').split('new AnvilOutput(')[1:]:
            chunk = chunk.strip().rstrip(',').strip()
            assert chunk.endswith(')'), 'Unexpected AnvilOutput text '+chunk
            chunk = chunk[:-1].strip()
            mm = re.fullmatch(r'new ItemStack\((.*)\)(?:,\s*([\d.]+)F)?', chunk, re.S)
            assert mm, 'Unexpected ItemStack text '+chunk
            args = [a.strip() for a in split_top(mm.group(1))]
            item = neo_item(args[0], args[2] if len(args) > 2 else None) if original else re.sub(r'\s+', '', args[0])
            outputs.append((item, int(args[1]), float(mm.group(2) or 1.0)))
        rows.append((name, column, tier, overlay, outputs))
    return rows


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
    goal27a_start = read(GOAL27A_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal27B commits nothing): HEAD 71c2f660 (the Goal 27 planning commit,
    # 8 files) on the Goal 26 close-out 0786697d (= origin/master) on the Goal 26 planning commit 6bfb7ad2, with the 201 status lines of the uncommitted Goal27A delivery and the
    # 2026-10-26 planning edits.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 27 planning commit'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 27 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    status_lines = base['target_status'].splitlines()
    assert len(status_lines) == START_STATUS_LINES and START_STATUS.read_text(encoding='utf-8').splitlines() == status_lines, \
        f'The frozen start is not the {START_STATUS_LINES} status lines of the uncommitted Goal27A delivery plus the planning edits (baseline target_status / start_status.txt)'
    assert base['target_parent'].startswith(GOAL26_CLOSEOUT) and base['origin_master'] == base['target_parent'], 'The start commit is not on the pushed Goal 26 close-out 0786697d'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal27a receipt records another original commit than the frozen start'
    assert prior_receipt['target_start_commit'] == start_head and prior_receipt['target_head_at_packaging'] == start_head, 'The goal27a package was not built on the same commit as this start'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal27B (the Goal27A and Goal27B deliveries stay uncommitted until the Goal 27 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2)}
    assert chain[1].startswith(GOAL26_CLOSEOUT) and chain[2].startswith(GOAL26_PLANNING), 'NEO HEAD~1..2 are not the Goal 26 close-out 0786697d and the Goal 26 planning 6bfb7ad2 commits: '+str(chain)
    planning_files = [l for l in git_ro(ROOT, 'show', '--name-only', '--format=', start_head).splitlines() if l.strip()]
    assert len(planning_files) == PLANNING_FILES and all(p.startswith('migration/') for p in planning_files), 'The planning commit 71c2f660 is not the 8 migration/ documents: '+str(planning_files)
    assert set(base['start_content']) == {'committed', 'uncommitted'} and 'Goal27A delivery' in base['start_content']['uncommitted'], 'Baseline start content differs (expected the uncommitted Goal27A delivery)'
    assert set(base['older_receipt_protected_paths']) == OLDER_RECEIPTS, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256_at_freeze'] == base['build_libs_jar_sha256_at_freeze'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_lines'] == len(status_lines) == startup['dirty_start_files'] == START_STATUS_LINES \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'], \
        'startup-verification.json differs from baseline.json'
    start_stamp = start_json(base, STAMP)
    assert base['stamp_state']['generated_resources_recorded'] == prior_receipt['generated_resource_count'] == len(start_stamp['generated']) \
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal27a generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_freeze']

    # The uncommitted delivery at the start: the 201 dirty start files (start_hashes.txt) are exactly the goal27a receipt's changed files plus the four planning documents;
    # each start hash is the goal27a after-hash (only the shared records the goal27a receipt does not hash may differ: GOAL27.md).
    dirty = {}
    for line in START_HASHES.read_text(encoding='utf-8').splitlines():
        if line.strip():
            h, p = line.split(None, 1)
            dirty[p.strip().lstrip('*')] = h
    delivery_changed = {e['path']: e for e in prior_receipt['changed_files']}
    assert set(dirty) == set(delivery_changed) | set(PLANNING_EDITS) and not set(delivery_changed) & set(PLANNING_EDITS) and len(dirty) == START_STATUS_LINES, \
        'The 201 dirty start files are not the goal27a receipt changed files plus the four planning documents: '+str(sorted(set(dirty) ^ (set(delivery_changed) | set(PLANNING_EDITS)))[:6])
    assert all(base['files'].get(p) == h for p, h in dirty.items()), 'start_hashes.txt differs from the baseline hashes'
    delivery_differs = sorted(p for p, e in delivery_changed.items() if base['files'].get(p) != e['after_sha256'])
    assert all(p in prior_receipt['records_not_hashed'] for p in delivery_differs), 'A Goal27A delivery file other than a record the goal27a receipt does not hash differs from its receipt after-hash at the Goal27B start: '+str(
        [p for p in delivery_differs if p not in prior_receipt['records_not_hashed']])
    uncommitted_start = dict(
        status_entries=len(status_lines), status=status_lines, description='the uncommitted Goal27A delivery (packaged as goal27a) plus the 2026-10-26 planning edits',
        goal27a_delivery=dict(owner=PREVIOUS_OWNER, receipt=PREVIOUS_RECEIPT.relative_to(ROOT).as_posix(), receipt_changed_files=len(delivery_changed), files_owned_at_start=len(delivery_changed),
                              equal_to_receipt_after_sha256=sum(1 for p, e in delivery_changed.items() if base['files'].get(p) == e['after_sha256']),
                              shared_records_differing_from_receipt_after_sha256={p: dict(receipt_after_sha256=delivery_changed[p]['after_sha256'], start_sha256=base['files'][p], current_sha256=sha(ROOT/p))
                                                                                  for p in delivery_differs},
                              note='The Goal27A delivery is uncommitted at this start (the user rule commits it with the Goal 27 unified acceptance); its files are owned by goal27a (package '
                                   'build/migration/releases/goal27a). A record the receipt does not hash (GOAL27.md) was edited again by the planning session after the package.'),
        planning_edits={p: dict(owner=PLANNING_OWNER, start_sha256=base['files'][p], current_sha256=sha(ROOT/p),
                                note='Planning-session edit of 2026-10-26, uncommitted at the start, in no receipt. '+('GOAL27B.md is also this batch\'s task book and delivery record (hashed by the new receipt).'
                                                                                                                        if p == 'migration/GOAL27B.md' else 'Must equal its start hash.')) for p in PLANNING_EDITS})

    # 2. Previous deliveries: the goal27a package, every old release file and the protected evidence; build/libs at the freeze is the goal27a package itself.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the freeze is not the goal27a package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal27a receipt list + the goal27a package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal27a receipt count + the goal27a release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal27a receipt'
    assert not base['previous_receipt_evidence_drift'], 'The goal27a receipt records evidence drift at the start: '+str(list(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal27a_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal27a receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal27b. Everything else equals its start hash.
    changes = changed_since_start(base)
    older_gametests_frozen = sorted(p for p in base['files'] if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p not in EDITED_GAMETESTS)
    modified_java = MODIFIED_JAVA + EDITED_GAMETESTS
    production_java = NEW_JAVA + modified_java
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal27B start that the owner table does not list (production outside CrucibleRecipes / AnvilRecipes / NtmRecipeProvider, CrucibleAlloyGameTests and the three RBMK GameTest '
         'classes, a generated file other than the stamp and anvil_lead recipe + advancement, a protected or frozen record, an older tool, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal 26 and earlier records, the Goal27A records or GOAL27C/D.md, GOAL27-THREAD-PROMPTS.md, SURVIVAL-PLAYABILITY.md, FOUNDATIONS.md, RESOURCE-OWNERSHIP.md changed since the start '
         '(they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal27B start: '+str(deleted)
    for p in MODIFIED_JAVA + EDITED_GAMETESTS + [STAMP] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS] + REPORTS[:1]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + GENERATED[1:] + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(production_java))
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified production, {len(EDITED_GAMETESTS)} edited and {len(NEW_JAVA)} new GameTest Java files (the batch has no hand-written resource): '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools = OLD_TOOLS_FROZEN + sorted(p for p in base['files'] if p.startswith(FROZEN_TOOL_DIRS))
    frozen_tools_changed = sorted(p for p in frozen_tools if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (package_goal27a.py, verify_goal27a_material_system.py, the casting regression wrapper and compat, the Goal 26C old-suite '
         'wrapper, the casting regressions and their folders): '+str(frozen_tools_changed))
    jei_and_smithing = sorted(p for p in base['files'] if p.startswith(J+'handler/jei/') or re.fullmatch(J+r'inventory/recipes/anvil/AnvilSmithing\w*\.java', p))
    unchanged_bad = [p for p in UNCHANGED_JAVA + UNCHANGED_FILES + older_gametests_frozen + jei_and_smithing if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed (Mats / MaterialEntries / MatDistribution / MaterialShapes / NTMMaterial, the crucible and foundry block entities, CopperCastingRecipes, '
         'CrucibleRecipe, SerializableRecipe, ShredderRecipes, ChemicalPlantRecipes, NTMAnvilBlock, AnvilMenu, AnvilConstructionPacket, every AnvilSmithing* and handler/jei class, NtmItems, NtmBlocks, NtmLanguageProvider, '
         'en_us.json, zh_cn.json, the mapping, every other GameTest class): '+str(unchanged_bad))
    goal27_now = sha(ROOT/GOAL27_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository before the start. The batch ran under the main agent (production, the '
                                               'migration/ records, reviews) with a GameTest verifier (CrucibleAlloyGameTests, the RBMK GameTest assertion edits, verify_goal27b_crucible_alloys.py, runData and the '
                                               'GameTest server) and this packaging verifier (the packager, the final runner, the casting-regression attribution) working in the same checkout; each wrote only its named '
                                               'files (the scope snapshots of the verifiers are indexed as evidence).',
                             goal27_md=dict(start_sha256=base['files'][GOAL27_RECORD], current_sha256=goal27_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p) if (ROOT/p).is_file() else None) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, owners=[OWNER], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal27B takes no new snapshot)'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-aee05a40f10f snapshot changed'
    production_changed = [p for p in production_java if p in changes]

    # The modified production files keep their start line endings (CrucibleRecipes is LF, the others CRLF; reported); new Java files are not mixed.
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

    # Production Java facts: every line edit counted (+/- against the start bytes); the judged edits (the owner table's content rules) follow.
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
    # AnvilRecipes: insert-only (the call and the registerRBMKRecycling method); CrucibleRecipes: the class documentation lines are the only removed lines; NtmRecipeProvider: only comment
    # lines are removed and the added code is exactly the import and the lead anvil recipe.
    if ANVIL_RECIPES in start_text:
        need(ANVIL_RECIPES in insert_summary and edit_summary[ANVIL_RECIPES]['removed'] == 0, f'{ANVIL_RECIPES} is not insert-only against the start copy (a start line was changed, moved or removed)')
    if CRUCIBLE_RECIPES in start_text:
        gone = removed_lines[CRUCIBLE_RECIPES]
        need(all(l.strip().startswith('*') for l in gone) and len(gone) == 2, f'{CRUCIBLE_RECIPES} removes lines other than the two class-documentation lines it rewrote: {[l.strip()[:80] for l in gone][:4]}')
        stray = [l.strip() for l in added_lines[CRUCIBLE_RECIPES] if not is_comment(l) and not re.match(r'import com\.hbm\.blocks\.NtmBlocks;|int i = MaterialShapes\.INGOT\.q\(1\);|this\.register\(new CrucibleRecipe\("crucible\.\w+"\)|\.(inputs|outputs)\(new MaterialStack', l.strip())]
        need(not stray, f'{CRUCIBLE_RECIPES} adds code lines that are not the NtmBlocks import, the ingot quantum or a crucible recipe statement: {[l[:90] for l in stray[:4]]}')
    provider_expected = Counter(['import com.hbm.blocks.machine.NTMAnvilBlock;',
                                 'ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), 1, NTMAnvilBlock.Variant.LEAD.ordinal()))',
                                 '.pattern("III")', '.pattern(" B ")', '.pattern("III")', ".define('I', NtmItems.INGOT_LEAD.get())", ".define('B', NtmBlocks.BLOCK_LEAD.get())",
                                 '.unlockedBy("has_ingot_lead", has(NtmItems.INGOT_LEAD.get()))', '.save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "anvil_lead"));'])
    if RECIPE_PROVIDER in start_text:
        gone = [l for l in removed_lines[RECIPE_PROVIDER] if not is_comment(l)]
        need(not gone, f'{RECIPE_PROVIDER} removes code lines (only the five "not registered" comments may change): {[l.strip()[:90] for l in gone][:4]}')
        added_code = Counter(l.strip() for l in added_lines[RECIPE_PROVIDER] if not is_comment(l))
        need(added_code == provider_expected, f'{RECIPE_PROVIDER} adds code other than the NTMAnvilBlock import and the anvil_lead recipe: extra {dict(added_code - provider_expected)}, missing {dict(provider_expected - added_code)}')
    # The three RBMK GameTest classes: the anvil assertion only - the @GameTest methods and annotations are the start's.
    gametest_edits = {}
    for p in EDITED_GAMETESTS:
        if p not in start_text or not (ROOT/p).is_file(): continue
        start_methods = sorted(GAMETEST_METHOD.findall(start_text[p].decode('utf-8'))); now_methods = sorted(GAMETEST_METHOD.findall((ROOT/p).read_text(encoding='utf-8')))
        gametest_edits[p] = dict(game_tests_start=len(GAMETEST_ANNOTATION.findall(start_text[p].decode('utf-8'))), game_tests_now=annotations(ROOT/p), methods_equal=start_methods == now_methods,
                                 **edit_summary[p])
        need(start_methods == now_methods and gametest_edits[p]['game_tests_start'] == gametest_edits[p]['game_tests_now'], f'{p} changed its @GameTest methods or their count (only the anvil assertion may change): '
             f'{sorted(set(start_methods) ^ set(now_methods))}')
        need(not any('@GameTest(' in l for l in removed_lines[p] + added_lines[p]), f'{p} edits @GameTest annotation lines')

    # 4. The crucible alloys and the anvil against the original (EXPECTED holds the handoff figures; every value is computed from the sources).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    neo_text = lambda path: (ROOT/path).read_text(encoding='utf-8').replace('\r\n', '\n') if (ROOT/path).is_file() else ''
    facts, bad = {}, []

    def fact(key, value, expected=None, ok=None):
        facts[key] = value if expected is None else dict(value=value, expected=expected)
        if ok is None: ok = expected is None or value == expected
        if not ok: bad.append(key)

    o_cr, n_cr = original_text(O_CRUCIBLE_RECIPES), neo_text(CRUCIBLE_RECIPES)
    start_cr = start_text[CRUCIBLE_RECIPES].decode('utf-8').replace('\r\n', '\n') if CRUCIBLE_RECIPES in start_text else ''
    o_nugget = int(re.search(r'NUGGET = new MaterialShapes\((\d+),', original_text(O_SHAPES)).group(1))
    o_ingot = o_nugget*int(re.search(r'INGOT = new MaterialShapes\(NUGGET\.quantity \* (\d+),', original_text(O_SHAPES)).group(1))
    n_shapes = neo_text(J+'inventory/material/MaterialShapes.java')
    n_nugget = int(re.search(r'NUGGET = new MaterialShapes\((\d+),', n_shapes).group(1))
    n_ingot = n_nugget*int(re.search(r'INGOT = new MaterialShapes\(NUGGET\.quantity \* (\d+),', n_shapes).group(1))
    fact('quanta', dict(nugget=n_nugget, ingot=n_ingot), dict(nugget=EXPECTED['nugget'], ingot=EXPECTED['ingot']), ok=(o_nugget, o_ingot) == (n_nugget, n_ingot) == (EXPECTED['nugget'], EXPECTED['ingot']))
    o_rows, n_rows = crucible_rows(o_cr, skip_gt6=True), crucible_rows(n_cr)
    gt6_names = re.findall(r'new CrucibleRecipe\("([^"]+)"\)', body_of(body_of(o_cr, 'public void registerDefaults()'), 'if(Compat.isModLoaded(Compat.MOD_GT6))'))
    fact('recipes_original', len(o_rows), EXPECTED['crucible_recipes'])
    fact('recipes_neo', len(n_rows), EXPECTED['crucible_recipes'])
    fact('gt6_rows_not_ported', dict(original=gt6_names, neo=[n for n in (r[0] for r in n_rows) if n in gt6_names]), None,
         ok=len(gt6_names) == EXPECTED['gt6_rows'] and gt6_names == ['crucible.steelWrought', 'crucible.steelPig', 'crucible.steelMeteoric'] and not [r for r in n_rows if r[0] in gt6_names])
    fact('recipe_names_in_original_order', [r[0] for r in n_rows], None, ok=[r[0] for r in n_rows] == [r[0] for r in o_rows])
    fact('recipe_frequencies', {r[0]: r[1] for r in n_rows}, None, ok=[(r[0], r[1]) for r in n_rows] == [(r[0], r[1]) for r in o_rows])
    fact('recipe_inputs_outputs', len(n_rows), None, ok=[(r[3], r[4]) for r in n_rows] == [(r[3], r[4]) for r in o_rows])
    fact('recipe_amounts', {r[0]: dict(inputs=[(m, amount(a, n_nugget, n_ingot)) for m, a in r[3]], outputs=[(m, amount(a, n_nugget, n_ingot)) for m, a in r[4]]) for r in n_rows}, None,
         ok=all(amount(a, n_nugget, n_ingot) == amount(a, o_nugget, o_ingot) for r in n_rows for m, a in r[3] + r[4]) and all(amount(a, n_nugget, n_ingot) > 0 for r in n_rows for m, a in r[3] + r[4]))
    fact('recipe_icons', {r[0]: r[2] for r in n_rows}, None, ok=all(neo_icon(o[2]) == n[2] and n[2] is not None for o, n in zip(o_rows, n_rows)))
    declared = set(re.findall(r'NTMMaterial (MAT_\w+)\s*=', neo_text(J+'inventory/material/Mats.java')))
    used = sorted({m for r in n_rows for m, _ in r[3] + r[4]})
    fact('materials_declared_in_neo', len(used), None, ok=set(used) <= declared)
    o_defaults, n_defaults = body_of(o_cr, 'public void registerDefaults()'), body_of(n_cr, 'public void registerDefaults()')
    fact('no_display_names', dict(original=o_defaults.count('setNamed'), neo=n_defaults.count('setNamed')), dict(original=0, neo=0))
    fact('registerDefaults_guard', 'if(!this.recipeOrderedList.isEmpty()) return;' in n_defaults, True)
    fact('molds_for_nei_not_ported', dict(original=o_cr.count('registerMoldsForNEI'), neo=n_cr.count('registerMoldsForNEI')), None, ok=o_cr.count('registerMoldsForNEI') >= 2 and n_cr.count('registerMoldsForNEI') == 0)
    # crucible.hss is the Goal 10A recipe: its statement is byte-identical to the start, and everything outside registerDefaults and the class documentation is the start's.
    hss = lambda t: re.search(r'this\.register\(new CrucibleRecipe\("crucible\.hss"\).*?\)\);', body_of(t, 'public void registerDefaults()'), re.S)
    fact('hss_unchanged_since_goal10a', bool(hss(n_cr)) and bool(hss(start_cr)) and hss(n_cr).group(0) == hss(start_cr).group(0), True)
    outside = lambda t: squeeze(re.sub(r'^import .*$', '', re.sub(r'/\*\*.*?\*/', '', drop_body(t, 'public void registerDefaults()'), count=1, flags=re.S), flags=re.M))
    fact('config_and_json_code_unchanged', bool(start_cr) and outside(n_cr) == outside(start_cr), True)
    # The arithmetic of the alloys the handoff names (computed from the NEO statements, equal to the original's by the facts above).
    by_name = {r[0]: r for r in n_rows}
    amounts = lambda r, side: {m: amount(a, n_nugget, n_ingot) for m, a in r[side]}
    arithmetic = {}
    for name in ('crucible.steel', 'crucible.ferro', 'crucible.tcalloy', 'crucible.redcopper', 'crucible.hss'):
        if name in by_name:
            r = by_name[name]
            arithmetic[name] = dict(frequency=r[1], inputs=amounts(r, 3), outputs=amounts(r, 4))
    ferro = arithmetic.get('crucible.ferro', {})
    ferro_out = sum(ferro.get('outputs', {}).values()) or 1
    executions = n_ingot // ferro_out if ferro else None
    fact('ferro_one_ingot', dict(executions=executions, steel=executions*ferro.get('inputs', {}).get('MAT_STEEL', 0) if ferro else None, u238=executions*ferro.get('inputs', {}).get('MAT_U238', 0) if ferro else None,
                                 ticks=executions*ferro.get('frequency', 0) if ferro else None), None,
         ok=bool(ferro) and ferro['inputs'] == {'MAT_STEEL': 16, 'MAT_U238': 8} and ferro['outputs'] == {'MAT_FERRO': 24} and ferro['frequency'] == 3 and executions == EXPECTED['ferro_executions']
         and executions*16 == 48 and executions*8 == 24)
    fact('alloy_arithmetic', arithmetic, None, ok=arithmetic.get('crucible.steel') == dict(frequency=20, inputs={'MAT_IRON': 16, 'MAT_CARBON': 24, 'MAT_FLUX': 8}, outputs={'MAT_STEEL': 16})
         and arithmetic.get('crucible.tcalloy') == dict(frequency=9, inputs={'MAT_STEEL': 64, 'MAT_TECHNETIUM': 8}, outputs={'MAT_TCALLOY': 72})
         and arithmetic.get('crucible.redcopper') == dict(frequency=2, inputs={'MAT_COPPER': 8, 'MAT_REDSTONE': 8}, outputs={'MAT_MINGRADE': 16})
         and arithmetic.get('crucible.hss') == dict(frequency=9, inputs={'MAT_STEEL': 40, 'MAT_TUNGSTEN': 24, 'MAT_COBALT': 8}, outputs={'MAT_DURA': 72}))
    # The documentation cites (CrucibleRecipes.java:58-127 and :67-76): reported, the closing brace of the GT6 block is :77.
    doc_refs = dict(register_defaults=original_line(O_CRUCIBLE_RECIPES, 'public void registerDefaults()'), gt6_branch=original_line(O_CRUCIBLE_RECIPES, 'if(Compat.isModLoaded(Compat.MOD_GT6))'),
                    molds_call=original_line(O_CRUCIBLE_RECIPES, 'registerMoldsForNEI();'))
    fact('class_documentation_refs', doc_refs, None, ok=(doc_refs['register_defaults'], doc_refs['molds_call']) == (58, 127) and doc_refs['gt6_branch'] == 67)
    # No language key: en_us.json, the provider, zh_cn.json and the mapping are the start's (UNCHANGED above); the crucible.* key set is the start's.
    en_start, en_now = start_json(base, EN), read(ROOT/EN)
    fact('crucible_language_keys', sorted(k for k in en_now if k.startswith('crucible.')), None, ok=sorted(k for k in en_now if k.startswith('crucible.')) == sorted(k for k in en_start if k.startswith('crucible.')))
    # The 12 RBMK tier-4 RECYCLING rows (original AnvilRecipes.java:868-962, !enable528 branch from :927).
    o_anvil, n_anvil, start_anvil = original_text(O_ANVIL_RECIPES), neo_text(ANVIL_RECIPES), (start_text[ANVIL_RECIPES].decode('utf-8').replace('\r\n', '\n') if ANVIL_RECIPES in start_text else '')
    o_rbmk = anvil_rows(o_anvil, True)
    n_rbmk = anvil_rows(body_of(n_anvil, 'private static void registerRBMKRecycling()'), False)
    ported = [r for r in o_rbmk if r[0] not in RBMK_NOT_PORTED]
    fact('rbmk_rows_original', len(o_rbmk), EXPECTED['rbmk_original_rows'])
    fact('rbmk_rows_not_ported', [r[0] for r in o_rbmk if r[0] in RBMK_NOT_PORTED], None, ok=sorted(r[0] for r in o_rbmk if r[0] in RBMK_NOT_PORTED) == sorted(RBMK_NOT_PORTED))
    fact('rbmk_rows_neo', len(n_rbmk), EXPECTED['rbmk_rows'])
    fact('rbmk_rows_order_and_inputs', [r[0] for r in n_rbmk], None, ok=[(r[0], r[1]) for r in n_rbmk] == [(r[0], r[1]) for r in ported])
    fact('rbmk_rows_outputs', len(n_rbmk), None, ok=all(None not in [o[0] for o in r[4]] for r in ported) and [r[4] for r in n_rbmk] == [r[4] for r in ported])
    fact('rbmk_rows_tier_and_overlay', sorted({(r[2], r[3]) for r in n_rbmk}), [(4, 'RECYCLING')], ok=sorted({(r[2], r[3]) for r in n_rbmk}) == [(4, 'RECYCLING')] and all(r[2] == 4 for r in o_rbmk))
    fact('rbmk_rows_all_certain', sorted({o[2] for r in n_rbmk for o in r[4]}), [1.0], ok={o[2] for r in n_rbmk for o in r[4]} == {1.0} and {o[2] for r in ported for o in r[4]} == {1.0})
    # The original line ranges the batch's added comments cite (AnvilRecipes.java:a-b in NtmRecipeProvider and AnvilRecipes): each must start at the first line of an original RBMK row (or the
    # ":868" //RBMK header / ":927" enable528 branch) and end at the last line of one (or at the end of the branch :962).
    o_lines = o_anvil.split('\n')
    spans = [(i + 1, next(j + 1 for j in range(i, len(o_lines)) if '.setTier(' in o_lines[j])) for i in range(len(o_lines))
             if 'constructionRecipes.add(new AnvilConstructionRecipe(' in o_lines[i] and re.search(r'ModBlocks\.(rbmk_|reactor_research)', ' '.join(o_lines[i:i + 3]))]
    starts, ends = {s for s, _ in spans} | {original_line(O_ANVIL_RECIPES, '//RBMK'), original_line(O_ANVIL_RECIPES, 'if(!GeneralConfig.enable528) {')}, {e for _, e in spans}
    cited = sorted({(int(a), int(b)) for p in (RECIPE_PROVIDER, ANVIL_RECIPES) for l in added_lines.get(p, []) for a, b in re.findall(r'AnvilRecipes\.java:(\d+)-(\d+)', l)})
    fact('rbmk_original_row_spans', len(spans), EXPECTED['rbmk_original_rows'])
    fact('cited_original_ranges', dict(cited=cited, row_starts=sorted(starts), row_ends=sorted(ends)), None, ok=bool(cited) and all(a in starts and (b in ends or b == spans[-1][1]) and a <= b for a, b in cited))
    fact('rbmk_rows_called_last', bool(re.search(r'registerRBMKRecycling\(\);\s*\}\s*$', body_of(n_anvil, 'private static void registerConstruction()'))), True)
    fact('construction_body_otherwise_unchanged', bool(start_anvil) and squeeze(re.sub(r'registerRBMKRecycling\(\);', '', body_of(n_anvil, 'private static void registerConstruction()'))) ==
         squeeze(body_of(start_anvil, 'private static void registerConstruction()')), True)
    smithing = lambda t: squeeze(body_of(t, 'private static void registerSmithing()')) + squeeze(body_of(t, 'private static void addUpgrade('))
    n_upgrades = re.findall(r'addUpgrade\(NTMAnvilBlock\.Variant\.(IRON|LEAD), NTMAnvilBlock\.Variant\.(\w+), NtmItems\.(\w+)\.get\(\), (\d+)\);', body_of(n_anvil, 'private static void registerSmithing()'))
    n_special = len(re.findall(r'SMITHING_RECIPES\.add\(new AnvilSmithing\w+Recipe\(\)\);', body_of(n_anvil, 'private static void registerSmithing()')))
    fact('smithing_rows_unchanged', dict(upgrade_rows=len(n_upgrades), special_rows=n_special), dict(upgrade_rows=EXPECTED['smithing_upgrade_rows'], special_rows=EXPECTED['smithing_special_rows']),
         ok=bool(start_anvil) and smithing(n_anvil) == smithing(start_anvil) and (len(n_upgrades), n_special) == (EXPECTED['smithing_upgrade_rows'], EXPECTED['smithing_special_rows']))
    fact('smithing_ferrouranium_upgrade', [u for u in n_upgrades if u[1] == 'FERROURANIUM'], [('IRON', 'FERROURANIUM', 'INGOT_FERROURANIUM', '10'), ('LEAD', 'FERROURANIUM', 'INGOT_FERROURANIUM', '10')],
         ok=[u for u in n_upgrades if u[1] == 'FERROURANIUM'] == [('IRON', 'FERROURANIUM', 'INGOT_FERROURANIUM', '10'), ('LEAD', 'FERROURANIUM', 'INGOT_FERROURANIUM', '10')]
         and 'new ComparableStack(ModItems.ingot_ferrouranium, 10)' in o_anvil and 'Block[] anvils = new Block[]{ModBlocks.anvil_iron, ModBlocks.anvil_lead};' in o_anvil)
    n_anvil_block = neo_text(J+'blocks/machine/NTMAnvilBlock.java')
    tier_values = dict(re.findall(r'public static final int (TIER_\w+) = (\d+);', n_anvil_block))
    n_variants = {v: int(tier_values[t]) for v, t in re.findall(r'^\s*(\w+)\((TIER_\w+), "anvil_\w+", "anvil_\w+"\)', n_anvil_block, re.M)}
    fact('anvil_variant_tiers', {v: n_variants.get(v) for v in ('IRON', 'LEAD', 'STEEL', 'DESH', 'FERROURANIUM')}, dict(IRON=1, LEAD=1, STEEL=2, DESH=3, FERROURANIUM=4),
         ok={v: n_variants.get(v) for v in ('IRON', 'LEAD', 'STEEL', 'DESH', 'FERROURANIUM')} == dict(IRON=1, LEAD=1, STEEL=2, DESH=3, FERROURANIUM=4)
         and 'anvil_ferrouranium = new NTMAnvil(Material.iron, NTMAnvil.TIER_NUCLEAR)' in original_text(O_MODBLOCKS) and 'anvil_lead = new NTMAnvil(Material.iron, NTMAnvil.TIER_IRON)' in original_text(O_MODBLOCKS)
         and tier_values.get('TIER_NUCLEAR') == '4')
    # The lead anvil: original CraftingManager.java:295 (PB.ingot() and PB.block(), pattern III / _B_ / III), NEO provider + generated recipe + advancement; no murky anvil.
    o_craft = original_text(O_CRAFTING)
    lead_line = original_line(O_CRAFTING, 'new ItemStack(ModBlocks.anvil_lead, 1)')
    lead_original = re.search(r'anvil_lead, 1\), new Object\[\] \{ "(...)", "(...)", "(...)", \'I\', PB\.ingot\(\), \'B\', PB\.block\(\) \}', o_craft)
    n_provider = neo_text(RECIPE_PROVIDER)
    variants_order = re.findall(r'^\s*(\w+)\(TIER_\w+, "anvil_\w+", "anvil_\w+"\)', n_anvil_block, re.M)
    lead_ordinal = variants_order.index('LEAD') if 'LEAD' in variants_order else None
    fact('lead_anvil_original', dict(line=lead_line, pattern=list(lead_original.groups()) if lead_original else None), dict(line=295, pattern=['III', ' B ', 'III']),
         ok=lead_line == 295 and bool(lead_original) and list(lead_original.groups()) == ['III', ' B ', 'III'] and original_line(O_CRAFTING, 'new ItemStack(ModBlocks.anvil_murky, 1)') == 296)
    recipe_json = read(ROOT/(GENERATED_ROOT+RECIPE_JSON)) if (ROOT/(GENERATED_ROOT+RECIPE_JSON)).is_file() else None
    advancement_json = read(ROOT/(GENERATED_ROOT+ADVANCEMENT_JSON)) if (ROOT/(GENERATED_ROOT+ADVANCEMENT_JSON)).is_file() else None
    fact('lead_anvil_generated_recipe', dict(pattern=opt(recipe_json, 'pattern'), key=opt(recipe_json, 'key'), result=opt(recipe_json, 'result'), lead_ordinal=lead_ordinal), None,
         ok=recipe_json is not None and recipe_json.get('type') == 'minecraft:crafting_shaped' and recipe_json['pattern'] == ['III', ' B ', 'III']
         and recipe_json['key'] == {'I': {'item': 'hbmsntm:ingot_lead'}, 'B': {'item': 'hbmsntm:block_lead'}}
         and recipe_json['result'] == {'count': 1, 'id': 'hbmsntm:anvil', 'components': {'hbmsntm:meta': lead_ordinal}} and lead_ordinal == 1)
    fact('lead_anvil_advancement', opt(advancement_json, 'rewards'), {'recipes': ['hbmsntm:anvil_lead']}, ok=advancement_json is not None and advancement_json['rewards'] == {'recipes': ['hbmsntm:anvil_lead']}
         and 'hbmsntm:ingot_lead' in json.dumps(advancement_json))
    fact('murky_anvil_not_ported', dict(original_line=original_line(O_CRAFTING, 'new ItemStack(ModBlocks.anvil_murky, 1)'), neo_mentions=n_provider.count('anvil_murky')), None,
         ok=n_provider.count('anvil_murky') == 0 and 'ModItems.undefined' in o_craft)
    # The tier-4 chain stated by the handoff: ducrete needs a ferrouranium ingot (ChemicalPlantRecipes unchanged), recorded for the receipt.
    facts['original_references'] = original_refs
    need(not bad, 'crucible-alloy facts differ from the original or the handoff figures (or the NEO source is missing / its text differs): '+', '.join(
        f'{k}={json.dumps(facts[k], ensure_ascii=False)[:200]}' for k in bad))
    # The reachability ledger (the main agent's record; pending until written): ferro, Tc alloy, steel, red copper and HSS reachable; the others "not yet reachable".
    ledger = read(ROOT/LEDGER) if (ROOT/LEDGER).is_file() else None
    reach_ok = lambda name, status: ('reachable' in status and 'not yet reachable' not in status) if name in ('crucible.steel', 'crucible.redcopper', 'crucible.hss', 'crucible.ferro', 'crucible.tcalloy') \
        else status == 'not yet reachable'
    if need(ledger is not None, 'record missing: '+LEDGER+' (the reachability ledger)'):
        entries = {e.get('name'): e for e in ledger.get('crucible_recipes', [])}
        need(sorted(entries) == sorted(r[0] for r in n_rows) and all(reach_ok(n, e.get('reachability', '')) for n, e in entries.items()),
             f'{LEDGER} crucible_recipes are not the 13 recipes with steel / red copper / HSS / ferro / Tc alloy reachable and the others "not yet reachable": '
             f'{sorted(n for n, e in entries.items() if not reach_ok(n, e.get("reachability", "")))[:8]}')
        need((ledger.get('rbmk_recycling_rows') or {}).get('count') == EXPECTED['rbmk_rows'], f'{LEDGER} rbmk_recycling_rows.count is not {EXPECTED["rbmk_rows"]}')
        for name, e in entries.items():
            mm = re.fullmatch(r'CrucibleRecipes\.java:(\d+)-(\d+)', e.get('original', ''))
            statement_line = original_line(O_CRUCIBLE_RECIPES, 'new CrucibleRecipe("'+name+'")')
            need(bool(mm) and int(mm.group(1)) == statement_line, f'{LEDGER} cites {e.get("original")} for {name}, the original statement starts at line {statement_line}')
    # Client-side classes the common code must not reference.
    common_classes = [CRUCIBLE_RECIPES, ANVIL_RECIPES]
    client_refs = {p: bool((ROOT/p).is_file() and re.search(r'net\.minecraft\.client|com\.hbm\.render\.|mezz\.jei', strip_java_comments(neo_text(p)))) for p in common_classes}
    need(not any(client_refs.values()) and all((ROOT/p).is_file() for p in common_classes), 'common-side classes are missing or reference client-only classes: '+str(sorted(p for p, v in client_refs.items() if v)))

    # 5. features.json: no new group; every group keeps status and reviewed_source_commit; only crucible-alloying, anvil-stamps and the RBMK groups may change notes / target_paths / target_watch.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES <= set(start_features), 'The start mapping does not hold the groups of 24B-27A (rbmk-fuel ... material-system)'
    may_change = lambda i: i in NOTES_MAY_CHANGE or bool(RBMK_GROUP.fullmatch(i))
    need(set(by_id) == set(start_features), 'features.json group ids are not the start ids (Goal27B adds no group): '+str(sorted(set(by_id) ^ set(start_features))))
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    need(all(may_change(i) for i in notes_changed), 'features.json groups whose notes changed beyond crucible-alloying, anvil-stamps and the rbmk-* groups: '+str([i for i in notes_changed if not may_change(i)]))
    paths_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('target_paths') != start_features[i].get('target_paths'))
    need(all(may_change(i) for i in paths_changed), 'features.json groups whose target_paths changed beyond crucible-alloying, anvil-stamps and the rbmk-* groups: '+str([i for i in paths_changed if not may_change(i)]))
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in ('notes', 'target_watch', 'target_paths')} !=
                          {k: v for k, v in start_features[i].items() if k not in ('notes', 'target_watch', 'target_paths')})
    need(not shrunk and not other_fields, f'features.json previous groups lost target_watch entries {shrunk} or changed other fields {other_fields}')
    watch_grown = sorted(i for i, f in by_id.items() if i in start_features and set(f.get('target_watch', [])) - set(start_features[i].get('target_watch', [])))
    need(all(may_change(i) for i in watch_grown), 'features.json groups whose target_watch grew beyond crucible-alloying, anvil-stamps and the rbmk-* groups: '+str([i for i in watch_grown if not may_change(i)]))
    for gid, sources in {'crucible-alloying': [O_CRUCIBLE_RECIPES], 'anvil-stamps': [O_ANVIL_RECIPES, O_CRAFTING]}.items():
        missing_source = [p for p in sources if gid not in by_id or not feature_matches(by_id[gid], 'source', p)]
        need(not missing_source, f'features.json group {gid} lists in neither source_paths nor source_watch: {missing_source}')
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped; the main agent adds target_watch, e.g. for anvil_lead.json): '+str(unmapped[:6]))

    # 6. Language and the generated tree: no new key; the stamp must be current; the generated additions are the lead anvil recipe and advancement.
    zh_start, zh_now = start_json(base, ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = start_json(base, LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    no_delta = dict(added=[], removed=[], changed=[])
    need(en_delta == zh_delta == map_delta == no_delta, 'en_us.json / zh_cn.json / zh_cn-map.json changed (Goal27B adds no language key): '+json.dumps(dict(en=en_delta, zh=zh_delta, map=map_delta), ensure_ascii=False)[:500])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal27a totals'
    need((len(en_now), len(zh_now), len(map_now)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal27a totals {totals}')
    map_kinds, start_kinds = dict(Counter(e.get('kind') for e in map_now.values())), dict(Counter(e.get('kind') for e in map_start.values()))
    need(map_kinds == start_kinds == totals['zh_cn_map_by_kind'] and map_kinds.get('deferred') == EXPECTED['deferred_entries'], f'mapping kinds are {map_kinds}, expected the goal27a kinds {totals["zh_cn_map_by_kind"]} (deferred {EXPECTED["deferred_entries"]} unchanged)')
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
    need(generated_added == EXPECTED_GENERATED, f'Generated additions are not the lead anvil recipe and its advancement: extra {sorted(set(generated_added) - set(EXPECTED_GENERATED))[:6]}, missing {sorted(set(EXPECTED_GENERATED) - set(generated_added))[:6]}')
    need(not generated_changed, f'Generated resources changed since the start (en_us.json and every other generated file must stay byte-identical): {generated_changed[:5]}')
    need(len(stamp['generated']) == prior_receipt['generated_resource_count'] + EXPECTED['generated_added'], f'generated resource count {len(stamp["generated"])} is not the goal27a count {prior_receipt["generated_resource_count"]} + {EXPECTED["generated_added"]}')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    need(generated_since == sorted(GENERATED), 'Generated files changed since the start differ from the stamp, the anvil_lead recipe and its advancement: extra %s, missing %s' % (
        sorted(set(generated_since) - set(GENERATED))[:8], sorted(set(GENERATED) - set(generated_since))[:8]))

    # 7. Evidence: GameTest log, audits, Gradle logs, diff, the final suite run, the verifier report, the casting attribution, compare and the batch's own scripts and records.
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
    alloy_test_names = sorted(GAMETEST_METHOD.findall((ROOT/ALLOY_TESTS).read_text(encoding='utf-8'))) if (ROOT/ALLOY_TESTS).is_file() else []
    alloy_annotations = annotations(ROOT/ALLOY_TESTS) if (ROOT/ALLOY_TESTS).is_file() else 0
    need(bool(alloy_test_names) and alloy_annotations == len(alloy_test_names), f'{ALLOY_TESTS} holds {alloy_annotations} @GameTest annotations and {len(alloy_test_names)} parsed methods')
    need(gametest_added == alloy_annotations, f'GameTest sources grew by {gametest_added} tests, CrucibleAlloyGameTests holds {alloy_annotations} (an edited RBMK GameTest class changed its test count?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in alloy_test_names), 'GameTest log lacks "[hbm-alloy] <name> passed" for: '+str([n for n in alloy_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal27b/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad_findings = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad_findings and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad_findings))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]} (no new key, no new resource expected)')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal27b/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if name == 'production-vs-start.diff':
            if (OUT/name).is_file() and (OUT/name).stat().st_size > 0: evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)  # judged below
            continue
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal27b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    named = list(START_EVIDENCE) + list(REVIEW_EVIDENCE)
    named += sorted(p.name for p in OUT.glob('handoff-*.md') if p.name not in named) + sorted(p.name for p in OUT.glob('*-report.md') if p.name not in named)
    for name in named:
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal27b/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/FAIL_SET_DIFF).is_file(): evidence[(OUT/FAIL_SET_DIFF).relative_to(ROOT).as_posix()] = sha(OUT/FAIL_SET_DIFF)
    # The casting regressions (goal27a_casting_regression_run.py, unchanged wrapper): one record per suite in the final rerun's own directory; its transcript is hashed with it.
    casting = {}
    for suite in CASTING_SUITES:
        rec_path = CASTING_DIR/f'{suite}-compat.json'
        if not need(rec_path.is_file(), f'evidence missing: build/migration/goal27b/final/castingsuites/{suite}-compat.json (goal27a_casting_regression_run.py {suite}, redirected into final/ by run_final.py)'): continue
        rec = read(rec_path)
        transcript = ROOT/rec['transcript'] if rec.get('transcript') else None
        casting[suite] = dict(record=rec_path.relative_to(ROOT).as_posix(), exit=rec.get('exit'), mode=rec.get('mode'), blockers=rec.get('blockers'), stages=rec.get('stages'),
                              javac_errors_by_attribution=rec.get('javac_errors_by_attribution'), transcript=rec.get('transcript'))
        evidence[rec_path.relative_to(ROOT).as_posix()] = sha(rec_path)
        if need(transcript is not None and transcript.is_file(), f'{rec_path.name} names no existing transcript'): evidence[transcript.relative_to(ROOT).as_posix()] = sha(transcript)
    attribution = None
    if need((OUT/CASTING_ATTRIBUTION).is_file(), 'evidence missing: build/migration/goal27b/'+CASTING_ATTRIBUTION+' (casting_attribution.py, after the final rerun)'):
        att = read(OUT/CASTING_ATTRIBUTION)
        problems = []
        if att.get('mode') != 'compare' or att.get('missing_inputs'): problems.append(f'mode {att.get("mode")!r}, missing inputs {att.get("missing_inputs")}')
        if att.get('baseline_sha256') != sha(BASELINE) or att.get('tool_sha256') != sha(OUT/'casting_attribution.py'): problems.append('written by another baseline or another version of casting_attribution.py')
        if att.get('old_dir') != (GOAL27A_OUT/'castingsuites').relative_to(ROOT).as_posix() or att.get('new_dir') != CASTING_DIR.relative_to(ROOT).as_posix(): problems.append(f'compares {att.get("old_dir")} with {att.get("new_dir")}')
        if sorted(att.get('suites', {})) != sorted(CASTING_SUITES): problems.append('suites '+str(sorted(att.get('suites', {}))))
        for suite, entry in att.get('suites', {}).items():
            for side in ('old', 'new'):
                s = entry.get(side) or {}
                if not s.get('parse_matches_record'): problems.append(f'{suite} {side}: the parsed javac errors do not match the record')
                if side == 'new' and suite in casting and s.get('record_sha256') != sha(ROOT/casting[suite]['record']): problems.append(f'{suite}: the new record changed after the attribution')
            for e in entry.get('new_errors', []) + entry.get('moved', []):
                file = e.get('at', '').rsplit(':', 1)[0] if 'at' in e else (e.get('identity') or {}).get('file', '')
                if e.get('attribution') == 'unattributed': problems.append(f'{suite}: unattributed error {e.get("at") or e.get("identity")}')
                elif e.get('attribution') == '27B change' and file not in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed to a 27B change but the file did not change')
                elif e.get('attribution') == 'not 27B' and file in changes: problems.append(f'{suite}: {e.get("at") or e.get("identity")} is attributed "not 27B" but the file changed')
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
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal27b/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in modified_java if p in changes]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal27b/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in modified_java if p in changes) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(p in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([p for p in listed_in_diff if p not in diff_text]))
    final = None
    # The suites of the goal27a final run plus the Goal27B verifier (the two casting regressions are in the goal27a set and run unchanged, redirected into final/).
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal27a final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal27B suite is already in the goal27a final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal27b/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal27a final set + the Goal27B verifier: '+str(sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal27b/'+VERIFY_REPORT+' (tools/migration/verify_goal27b_crucible_alloys.py report)'):
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
        verifier_references = sorted(set(re.findall(r'(?:CrucibleRecipes|AnvilRecipes|CraftingManager|MaterialShapes|Mats|NTMAnvil|ModBlocks)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal27a compare target paths plus this batch's compare-inventory paths).
    cmp_prev = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal27a/compare.json differs from the goal27a receipt'
    prev_added = sorted(p for p in compare_paths(cmp_prev['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    prev_modified = sorted(p for p in compare_paths(cmp_prev['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(prev_added) | set(prev_modified) | set(own_target))
    expected_added = sorted(set(prev_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal27b/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-27a paths + the %d of this batch not already among them (%d compare-inventory paths changed)' % (
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
        for g in ('crucible-alloying', 'anvil-stamps'):
            need(any(f.get('id') == g and f.get('state') == 'target-changed' for f in cmp['features']), f'{COMPARE} does not report {g} as target-changed')
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal27a (goal27a compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal27a_paths=len(prev_added) + len(prev_modified), goal27b_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-27A)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 8. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal27b or a recompile.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal27a) package (run the final build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == zh_jar == no_delta, 'JAR en_us.json or zh_cn.json differs from the previous package (Goal27B adds no language key): en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
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
                elif kind == 'modified' and n == 'META-INF/MANIFEST.MF': owner = [OWNER]
                elif kind == 'added' and n in generated_entries: owner = [OWNER]
                elif kind == 'modified' and n in recompile_only and owner_class(n) not in changes: owner = [RECOMPILE_OWNER]
                if not owner: unowned.append(f'{kind}: {n}' + (' [source ' + owner_class(n) + ' unchanged since the start: a recompile difference, not a source change]' if n.endswith('.class') and owner_class(n) not in changes else ''))
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the two generated additions (anvil_lead recipe and advancement) and META-INF/MANIFEST.MF are owned): '+str(unowned[:10]))
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in production_java if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) <= set(class_owners),
             'Changed Java sources and goal27b JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners))) + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == generated_entries, 'JAR non-class delta differs from the generated additions (anvil_lead recipe + advancement): extra %s, missing %s' % (
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

    # 9. Records: the release name and the batch reports.
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    for p in unnamed: need(False, 'record does not name '+RELEASE_NAME+': '+p)
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS:
        if p not in OPTIONAL_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p
    indexed = {Path(p).relative_to(OUT.relative_to(ROOT)).as_posix() for p in evidence if p.startswith(OUT.relative_to(ROOT).as_posix()+'/')}
    unindexed = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in indexed and p.name != 'baseline.json')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=generated_added, generated_modified=generated_changed,
                   start_drift=sorted(drift_report), repinned_since_goal27a_start=sorted(repinned),
                   language_delta=dict(en=en_delta, zh=zh_delta, map=map_delta), language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, line_endings=line_endings, gametest_edits=gametest_edits,
                   crucible_alloys={k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v)) < 200 else f'<{len(v)} items>') for k, v in facts.items()}, crucible_alloy_facts_bad=bad,
                   client_refs_in_common_classes=sorted(p for p, v in client_refs.items() if v),
                   gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added, new_alloy_tests=alloy_test_names, final_suites_expected=final_expected,
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
    crucible_alloys = dict(neo=NEW_JAVA + MODIFIED_JAVA + EDITED_GAMETESTS, original=O_SOURCES, facts=facts, expected=EXPECTED, known_differences=KNOWN_DIFFERENCES, original_references=original_refs,
                           reachability=({e['name']: e['reachability'] for e in ledger.get('crucible_recipes', [])} if ledger else None), reachability_record=LEDGER,
                           handoff_slips_corrected='ferrouranium takes 3 executions per ingot (steel 48 + uranium-238 24; CrucibleRecipes.java:95-97), not 8; the smithing table has 18 upgrade rows + 5 special rows (23), not 20',
                           note=f'The {EXPECTED["crucible_recipes"]} original default crucible recipes in the original order with the original names, frequencies, inputs, outputs and (mapped) icons; the three GT6 rows are '
                                f'not ported and no recipe sets a display name; ferrouranium = steel 16 + uranium-238 8 -> 24 every 3 ticks (one ingot = 48 + 24); {EXPECTED["rbmk_rows"]} RBMK tier-4 RECYCLING rows '
                                '(ReaSim x2 and reactor_research not ported) appended after the existing construction rows; the existing smithing upgrade rows are byte-identical to the start; the lead anvil crafting '
                                'recipe (meta Variant.LEAD) with its advancement; no language key, no resource.')
    casting_record = dict(attribution=attribution, suites=casting, wrapper='tools/migration/goal27a_casting_regression_run.py (unchanged)', policy='tools/migration/goal27a_casting_compat.py (unchanged)',
                          note='The two frozen isolated casting regressions (verify_goal10a.py, verify_goal5a_casting.py) run through the unchanged Goal27A wrapper in the final rerun, redirected into '
                               'build/migration/goal27b/final/castingsuites; both already stopped at javac on the Goal26D and Goal27A trees, so none of their assertions is reached. casting-attribution.json '
                               'pairs the javac errors of the Goal27A final run with the Goal27B run and attributes every new or moved error by file to a Goal27B change or to "not 27B"; it is evidence about javac '
                               'in the frozen stub worlds only.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(alloy_test_names), gametest_expected, EXPECTED['crucible_recipes'], EXPECTED['rbmk_rows']),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=dict(commit=start_head[:8], files=planning_files, note='The Goal 27 planning commit (local, not pushed): task books 27A..27D, GOAL27.md, the thread prompts, the README and GOAL26.md entry lines.'),
                   uncommitted_start=uncommitted_start,
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, reconstruction=base['reconstruction'], goal26_closeout_commit=chain[1], goal26_planning_commit=chain[2],
                                      note=f'The start tree is HEAD 71c2f660 (the Goal 27 planning commit, local, not pushed) on the pushed Goal 26 close-out 0786697d (= origin/master) on the Goal 26 planning commit '
                                           f'6bfb7ad2, with {len(status_lines)} status lines: the uncommitted Goal27A delivery and the 2026-10-26 planning edits. build/libs at the start is the goal27a package '
                                           f'{start_jar_sha[:8]}. The original did not move since 24A (aee05a40f). freeze_start.py hashed every tracked and dirty file live ({len(base["files"])} baseline hashes) before the '
                                           f'first 27B write and copied the dirty or planned files ({len(base["copied_scope"])} baseline-files); paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, line_endings=line_endings, gametest_edits=gametest_edits, start_copies_supplement=[],
                   crucible_alloys=crucible_alloys, casting_attribution=casting_record,
                   language=dict(changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']), added=dict(en_us=en_delta['added'], zh_cn=zh_delta['added'], zh_cn_map=map_delta['added']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds), jar_delta=language,
                                 start_sha256={p: base['files'][p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD, J+'datagen/NtmLanguageProvider.java')},
                                 note='Goal27B adds, removes and changes no language key (no crucible.* key: like upstream no crucible recipe sets a display name, Goal 10A rule); en_us.json, zh_cn.json, the mapping and '
                                      'NtmLanguageProvider are byte-identical to the start; the 106 deferred entries are unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith(CARRIED_REPINS)},
                   repinned_since_goal27a_start={p: dict(goal27a_start_pin_sha256=h, goal27b_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok'), old_machine_suites_through=OLD_MACHINE_SUITES, casting_suites_through=['goal27a_casting_regression_run.py verify_goal10a',
                                                                                                                                                                            'goal27a_casting_regression_run.py verify_goal5a_casting']),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_alloy_tests=alloy_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per CrucibleAlloyGameTests test (names in new_alloy_tests): what those '
                                      'tests assert about the 13 recipes and their order, the crucible acceptance and its own ticker running steel, ferrouranium, Tc alloy and red copper, the smithing upgrade and the menu '
                                      'tiers, the 12 RECYCLING rows executed at tier 4, the lead anvil recipe and the config file round trip; the three edited RBMK GameTest classes assert the same 12 rows; no client '
                                      '(the anvil screen, JEI and the crucible GUI are not drawn), no real player, no saved world, no survival chain.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['material_system (the Goal27A-only domain key; Goal27B adds crucible_alloys)',
                                 'casting_regressions (the Goal27A key; Goal27B carries casting_attribution instead: the wrapper and the two suites are unchanged, only their javac errors are attributed)',
                                 'small_fix_d2 (the D2 ContaminationUtil small fix was packaged by goal27a)',
                                 'resource_ownership / imported_resources / derived_resources / unchanged_resources / generators (Goal27B has no hand-written resource)',
                                 'uncommitted deliveries other than Goal27A (goal26a_delivery .. goal26c_delivery, planning_supplements)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun (the six old isolated suites through the goal26c wrapper and the two casting regressions through the unchanged goal27a wrapper, whose javac '
                            'errors are attributed by casting_attribution.py), compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. No in-game client test was run: '
                            'the anvil screen and its tier-4 recycling overlay, the crucible GUI, JEI, item tooltips and Chinese UI are not seen on screen; no survival chain (mining and smelting the inputs, '
                            'alloying in a crucible, casting, upgrading an anvil with ten ferrouranium ingots, recycling an RBMK column) in a world was run; no dedicated server beyond GameTest; the acceptance '
                            'checklist GOAL27B-ACCEPTANCE.md is written, not run, and merges into the Goal 27D master list.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal27b JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal27a package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
