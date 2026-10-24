"""Package Goal26C (the third batch of Goal 26, hazmat suits: the three armor materials hazmat / hazmat_red / hazmat_grey (NtmArmorMaterials), the twelve suit pieces (HazmatArmorItem, and HazmatHelmetItem
implementing IGasMask with an empty blacklist), the three hazmat cloths, the first one from the assembly machine (ass.hazcloth), the HazmatRegistry default rows (the suits and the two gas masks), the three
SAND lines of ArmorUtil, ArmorUtil.checkForHazmat with the checkArmor slot-order correction and the shared eject helper, the HAZMAT branch of ContaminationUtil.contaminate, the client extension for the
hazmat helmets, the armor enchantability item tags, 24 imported resources, 15 language keys and HazmatSuitGameTests), cumulatively on the goal26b package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal26c.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal26c/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal26c/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal26c/baseline.json: NEO HEAD 8954b531 (the Goal 26 planning commit, local, parent 5b1bf4db = the Goal 25 close-out commit) PLUS the uncommitted Goal26A and Goal26B
deliveries (226 files, packaged as goal26a and goal26b) PLUS the planning session's 2026-10-22 supplements to migration/GOAL26C.md and migration/GOAL26-THREAD-PROMPTS.md (228 status lines with
--untracked-files=all): freeze_start.py hashed every tracked file and every untracked start file live (10,452 hashes) before the first 26C write and copied every dirty start file and the files the batch planned
to touch (234 copies in baseline-files/); start_status.txt, start_head.txt and start_hashes.txt (the 228 dirty files) record it. build/libs at the start AND at the freeze IS the goal26b package (baseline
build_libs_jar_sha256_at_start / _at_freeze). The original HEAD aee05a40f did not move since 24A, so there is no upstream classification and no new snapshot. Nothing was committed between the goal26b package
and this start: HEAD must still be 8954b531 and there is no close-out owner. The Goal26A / Goal26B delivery files are owned by goal26a / goal26b: their start bytes are the receipts' after-hashes where a receipt
records them (asserted; every difference is reported, the shared records the main agent edited after a package are the expected ones); the two supplement files belong to the planning owner
planning-2026-10-22 (no receipt hashes them; GOAL26-THREAD-PROMPTS.md must equal its start hash, GOAL26C.md is the task book and delivery record of this batch and hashed by the new receipt). Every change since
the start is computed from the baseline file hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with
their start bytes (baseline-files, else the start-commit blob). The JAR delta against the goal26b package is attributed per entry (goal26c only); any entry without exactly one owner fails. Counts that records
quote (suites, GameTests, generated resources, classes, releases, language keys) are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the files and the
baseline.

The receipts that hash records (goal21a..goal26b, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start for the acceptance checklists, GOAL21D.md, GOAL22C.md,
goal21d-static-review.md, the goal24a working notes and migration/GOAL25D-ACCEPTANCE.md; they are listed in the receipt as start drift and must still equal their Goal26C start hash; no receipt is rewritten
and no other protected path may drift (the goal26b receipt records no drift of its own: previous_receipt_evidence_drift is empty). The Goal26A, Goal26B, Goal25 and Goal24 records and GOAL26D.md,
GOAL26-THREAD-PROMPTS.md and SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL26.md is edited by the main agent (a shared record), GOAL26C.md is the task book and delivery record (hashed
by the receipt) and GOAL26C-ACCEPTANCE.md the batch's acceptance checklist (hashed, written, not run).

Like the earlier packagers of 24B..26B this one has a single compare run (build/migration/goal26c/compare.json against the snapshot review-aee05a40f10f.json taken at the end of 24A: original 0/0/0,
target = exactly the goal26b compare target paths (24A-26B, read from build/migration/goal26b/compare.json) plus this batch's compare-inventory paths), no upstream classification; it adds the hazmat_suits
constants (checked against the original and NEO source texts, the recipes against the parsed original rows, the assembly row against the original). The Goal26B-only receipt key gas_masks is dropped."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
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
from package_goal24c import captured, normalize_value
from package_goal24e import split_args, OneOf, jsonable
from package_goal26b import OUT as GOAL26B_OUT, BASELINE as GOAL26B_BASELINE, protected_paths as goal26b_protected_paths

OUT = ROOT/'build/migration/goal26c'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
START_HASHES = OUT/'start_hashes.txt'
REFERENCE_PREVIOUS = GOAL26B_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL26B_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal26b/hbmsntm-198A-goal26b.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
OLDER_RECEIPT = ROOT/'build/migration/releases/goal26a/release.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal26c'
RELEASE_NAME = 'hbmsntm-198A-goal26c.jar'
OWNER = 'goal26c'
PREVIOUS_OWNER = 'goal26b'
OLDER_OWNER = 'goal26a'
PLANNING_OWNER = 'planning-2026-10-22'
PLANNING_PREFIX = '8954b531'
GOAL25_CLOSEOUT = '5b1bf4db'
GOAL25_PLANNING = '783b6d13'
GOAL24_CLOSEOUT = '17c8062f'
START_STATUS_LINES = 228
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a'}

# Production (owner goal26c), NEW (handoff-packaging.md; builder-report.md names the final classes: if a class is named differently or a helper class is added, edit this list, --check
# reports the difference as an unassigned src/ path). HazmatSuitGameTests is the GameTest verifier's class.
NEW_JAVA = [J+p+'.java' for p in ('items/armor/HazmatArmorItem', 'items/armor/HazmatHelmetItem', 'gametest/HazmatSuitGameTests')]
(HAZMAT_ARMOR_ITEM, HAZMAT_HELMET_ITEM, HAZMAT_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails, except an older GameTest the GameTest verifier had to update:
# see OLDER_GAMETEST_REMOVABLE; a review fix may add a file: --check reports it as an unassigned src/ path instead of failing silently).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'registry/NtmArmorMaterials', 'items/armor/GasMaskItem', 'render/item/GasMaskClientExtensions', 'util/ArmorUtil', 'util/ContaminationUtil', 'handler/HazmatRegistry', 'items/NtmItems',
    'inventory/NtmCreativeTabs', 'inventory/recipes/AssemblyMachineRecipes', 'main/NuclearTechModClient', 'datagen/NtmItemTagProvider', 'datagen/NtmRecipeProvider', 'datagen/NtmItemModelProvider',
    'datagen/NtmLanguageProvider')]
(ARMOR_MATERIALS, GAS_MASK_ITEM, CLIENT_EXTENSIONS, ARMOR_UTIL, CONTAMINATION, HAZMAT_REGISTRY, ITEMS, CREATIVE_TABS, ASSEMBLY, CLIENT_MOD, TAG_PROVIDER, RECIPE_PROVIDER, ITEM_MODEL_PROVIDER,
 PROVIDER) = MODIFIED_JAVA
OPTIONAL_JAVA = []
# The older GameTest sources the GameTest verifier may update when a count or "not registered" assertion of an older test changes because of this batch (handoff-verifier.md): any changed
# existing gametest/*.java source is owned by goal26c as production; the start CODE lines it may drop are assertion and log lines (prefixes below) and every such edit is reported in the receipt.
# The handoff lists GasMaskGameTests, RadiationControlGameTests and HazardGameTests among the files that must stay byte-identical "unless the verifier report names an edit": an edit of one of them
# is reported by --check as a changed byte-identical file until UNCHANGED_JAVA is edited here.
OLDER_GAMETEST_DIR = J+'gametest/'
OLDER_GAMETEST_REMOVABLE = ('check(', 'LOGGER.info(', 'for(', 'for (', 'if(', 'if (', 'helper.')
# Must stay byte-identical to the start (the handoff list: the IGasMask interface, the armor registry and mod handler, the filter item, the rag-mask item class, the two worn models, the mod
# entry classes, the no9 armor, the effect registry and the older hazard GameTests incl. GasMaskGameTests).
UNCHANGED_JAVA = ['src/main/java/api/hbm/item/IGasMask.java'] + [J+p+'.java' for p in (
    'util/ArmorRegistry', 'handler/ArmorModHandler', 'items/tools/GasMaskFilterItem', 'items/armor/ModArmorItem', 'render/model/armor/ModelM65', 'render/model/armor/ModelGasMask', 'main/NuclearTechMod',
    'main/CommonEvents', 'items/armor/ArmorNo9', 'lib/ModEffect', 'gametest/GasMaskGameTests', 'gametest/RadiationControlGameTests', 'gametest/HazardGameTests')]
# Modified sources whose compiled class need not change (comment-only edits); every other modified source must show a modified class in the JAR.
SAME_CLASS_JAVA = []
NO_CLASS_JAVA = []
# JAR classes whose source is unchanged since the start and that differ from the previous package only in recompiled debug names. RBMKRecyclingGameTests$1 (an anonymous
# RBMKControlManualBlockEntity) flips the constructor's local-variable names between pos / state and arg0 / arg1 on incremental recompiles (Goal25B, Goal26A, Goal26B); the goal26b package holds
# whichever form its build produced, so the entry is accepted in either direction (patched previous bytes must equal the new class bytes; its source is unchanged since the start).
RECOMPILE_ONLY = {'com/hbm/gametest/RBMKRecyclingGameTests$1.class': (((b'\x01\x00\x04arg0', b'\x01\x00\x03pos'), (b'\x01\x00\x04arg1', b'\x01\x00\x05state')),
                                                                    ((b'\x01\x00\x03pos', b'\x01\x00\x04arg0'), (b'\x01\x00\x05state', b'\x01\x00\x04arg1')))}
RECOMPILE_OWNER = 'recompile-debug-names'
# Insert-only against the start bytes (registration and datagen lines, the Chinese file and the mapping). The other modified files are held to ALLOWED_REMOVED_CODE (the start CODE lines they may
# drop, by prefix; an empty tuple allows only comment lines) and ALLOWED_REMOVED_EXACT (the exact stripped start code lines they may drop): the sneak-eject body that moved from GasMaskItem.use into
# ArmorUtil.ejectGasMaskFilter, the four reversed slot lines of ArmorUtil.checkArmor, the helmet-only client extension guard and the registerItem line that gained the three hazmat helmets. Exact lines
# of the builder's tree; a review fix that touches more is reported with the stray lines.
STRICT_INSERT_ONLY = [CONTAMINATION, HAZMAT_REGISTRY, ITEMS, CREATIVE_TABS, ASSEMBLY, TAG_PROVIDER, RECIPE_PROVIDER, ITEM_MODEL_PROVIDER, PROVIDER, ZH_INPUT, LOCALIZATION_RECORD]
ALLOWED_REMOVED_CODE = {ARMOR_MATERIALS: (), GAS_MASK_ITEM: (), CLIENT_EXTENSIONS: (), ARMOR_UTIL: (), CLIENT_MOD: ()}
ALLOWED_REMOVED_EXACT = {
    GAS_MASK_ITEM: ('if(player.isShiftKeyDown()) {', 'ItemStack filter = this.getFilter(stack, player);', 'if(!filter.isEmpty()) {', 'if(!level.isClientSide()) {', 'ArmorUtil.removeFilter(stack);',
                    'if(!player.getInventory().add(filter)) {', 'player.drop(filter, true, false);', '}', '}', '}'),
    CLIENT_EXTENSIONS: ('if(slot != EquipmentSlot.HEAD || !(stack.getItem() instanceof GasMaskItem mask)) return original;',),
    ARMOR_UTIL: ('EquipmentSlot.FEET,   // 0', 'EquipmentSlot.LEGS,   // 1', 'EquipmentSlot.CHEST,  // 2', 'EquipmentSlot.HEAD    // 3'),
    CLIENT_MOD: ('event.registerItem(new GasMaskClientExtensions(), NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_M65.get(), NtmItems.GAS_MASK_MONO.get(), NtmItems.GAS_MASK_OLDE.get());',),
}
# The added lines of these files must be exactly the rows / branch of the batch: every added CODE line must match its pattern (the import, the three suit locals, the 14 registerHazmat rows; the one
# HAZMAT early return), and all of them must lie inside the one method that holds them (initDefault, contaminate), so the config contract (writeDefault / readConfig / registerHazmats /
# getResistance) is untouched.
ADDED_CODE_RULES = {
    HAZMAT_REGISTRY: re.compile(r'import com\.hbm\.items\.NtmItems;|double haz(?:Yellow|Red|Gray) = [\d.]+D;.*|HazmatRegistry\.registerHazmat\(NtmItems\.[A-Z_0-9]+\.get\(\), [^;]+\);'),
    CONTAMINATION: re.compile(r'if\(type == ContaminationType\.HAZMAT && ArmorUtil\.checkForHazmat\(player\)\) return;'),
}
ADDED_CODE_METHODS = {HAZMAT_REGISTRY: 'public static void initDefault()', CONTAMINATION: 'public static void contaminate('}
# The 24 imported original resources: NEO target -> original path, derived by the layout rules of the ownership record (textures/items -> textures/item, names kept; the two helmet-model textures
# renamed to lowercase because 1.21 resource paths must be lowercase (Goal 13A precedent); textures/armor and textures/misc keep path and name).
ITEM_ICONS = ('hazmat_cloth', 'hazmat_cloth_red', 'hazmat_cloth_grey') + tuple(f'hazmat_{piece}{tier}' for tier in ('', '_red', '_grey') for piece in ('helmet', 'plate', 'legs', 'boots'))
RENAMED = {ASSETS_ROOT+'textures/models/model_haz_red.png': O_RES+'textures/models/ModelHazRed.png', ASSETS_ROOT+'textures/models/model_haz_grey.png': O_RES+'textures/models/ModelHazGrey.png'}
ASSETS = {ASSETS_ROOT+'textures/item/'+n+'.png': O_RES+'textures/items/'+n+'.png' for n in ITEM_ICONS}
ASSETS.update({ASSETS_ROOT+'textures/armor/'+n+'.png': O_RES+'textures/armor/'+n+'.png' for n in ('hazmat_1', 'hazmat_2', 'hazmat_1_red', 'hazmat_2_red', 'hazmat_1_grey', 'hazmat_2_grey')})
ASSETS.update({ASSETS_ROOT+'textures/misc/overlay_hazmat.png': O_RES+'textures/misc/overlay_hazmat.png'})
ASSETS.update(RENAMED)
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
GENERATED = [STAMP, EN]
# The 15 new items: registry id -> NtmItems constant (the item model, the language name, the creative tab entry and the registration are counted per item).
ITEM_TABLE = {n: n.upper() for n in ITEM_ICONS}
# The 14 crafting recipes (builder-report.md): recipe id -> (kind, original path, selector regex of the single original line, NEO result id). The original rows are parsed from the stored
# blobs at aee05a40f, their key expressions translated through KEY_TABLE and compared with the generated JSON.
O_ARMORRECIPES_PATH, O_CRAFTING_PATH = 'crafting/ArmorRecipes.java', 'main/CraftingManager.java'
RECIPES = {f'hazmat_{piece}{tier}': ('shaped', O_ARMORRECIPES_PATH, rf'addRecipeAuto\(new ItemStack\(ModItems\.hazmat_{piece}{tier}, 1\)', f'hbmsntm:hazmat_{piece}{tier}')
           for tier in ('', '_red', '_grey') for piece in ('helmet', 'plate', 'legs', 'boots')}
RECIPES.update({f'hazmat_cloth{tier}': ('shaped', O_CRAFTING_PATH, rf'addRecipeAuto\(new ItemStack\(ModItems\.hazmat_cloth{tier}, 1\)', f'hbmsntm:hazmat_cloth{tier}') for tier in ('_red', '_grey')})
RECIPE_IDS = sorted(RECIPES)
SMELT_INPUTS = {}
# Recipe id -> the ORIGINAL_REFS entry quoted for it in the receipt.
RECIPE_REFS = {r: ('armor_recipes' if r in RECIPES and RECIPES[r][1] == O_ARMORRECIPES_PATH else 'cloth_recipe'+r[len('hazmat_cloth'):]) for r in RECIPES}
# The six new enchantable item tag files (NtmItemTagProvider ARMOR ENCHANTABILITY block): file -> the NEO item ids it lists (main-notes.md decision 1: the 18 items go into the per-slot enchantable
# tags, durability and equippable, not into minecraft:head_armor etc., which also feed minecraft:trimmable_armor).
MASKS = ('gas_mask', 'gas_mask_m65', 'gas_mask_mono', 'gas_mask_olde', 'mask_rag', 'mask_piss')
HEAD_ITEMS = [f'hbmsntm:{n}' for n in MASKS] + [f'hbmsntm:hazmat_helmet{t}' for t in ('', '_red', '_grey')]
CHEST_ITEMS = [f'hbmsntm:hazmat_plate{t}' for t in ('', '_red', '_grey')]
LEG_ITEMS = [f'hbmsntm:hazmat_legs{t}' for t in ('', '_red', '_grey')]
FOOT_ITEMS = [f'hbmsntm:hazmat_boots{t}' for t in ('', '_red', '_grey')]
ENCHANT_TAGS = {'head_armor': HEAD_ITEMS, 'chest_armor': CHEST_ITEMS, 'leg_armor': LEG_ITEMS, 'foot_armor': FOOT_ITEMS,
                'durability': HEAD_ITEMS + CHEST_ITEMS + LEG_ITEMS + FOOT_ITEMS, 'equippable': HEAD_ITEMS + CHEST_ITEMS + LEG_ITEMS + FOOT_ITEMS}
TAG_FILES = {n: f'data/minecraft/tags/item/enchantable/{n}.json' for n in ENCHANT_TAGS}
EXPECTED_GENERATED_BASE = sorted([f'assets/hbmsntm/models/item/{n}.json' for n in ITEM_ICONS] + [f'data/hbmsntm/recipe/{r}.json' for r in RECIPE_IDS] + list(TAG_FILES.values()))
ADVANCEMENT = {r: re.compile(r'data/hbmsntm/advancement/recipes/[a-z_]+/'+re.escape(r)+r'\.json') for r in RECIPE_IDS}
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY])
NEW_TOOLS = ['tools/migration/verify_goal26c_hazmat.py', 'tools/migration/package_goal26c.py']
TOOLS = NEW_TOOLS
# New tools/migration/goal26c_oldsuite_* files (the GameTest verifier's old-suite revival wrapper, handoff-verifier.md part C): optional, owned by goal26c as tools when present.
OLDSUITE_TOOL = re.compile(r'tools/migration/goal26c_oldsuite_[^/]+\.py')
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal26c-* or GOAL26C-* record is hashed as well.
REPORTS = ['migration/GOAL26C.md', 'migration/GOAL26C-ACCEPTANCE.md', 'migration/goal26c-static-review.md', 'migration/goal26c-localization-review.json',
           'migration/goal26c-resource-ownership.json', 'migration/goal26c-materials-review.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal26c-[^/]+\.(json|md)|GOAL26C-[^/]+\.md)')
GOAL26_RECORD = 'migration/GOAL26.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md',
                  'migration/RESOURCE-OWNERSHIP.md', GOAL26_RECORD]
# Shared records the batch may leave untouched (RESOURCE-OWNERSHIP.md "if touched"). FOUNDATIONS.md is required by the handoff's shared-record list.
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
# The Goal 26 planning documents of the other batches: no change is expected in this batch. GOAL26C.md is this batch's task book and delivery record (REPORTS[0]).
PLANNING_FROZEN = ['migration/GOAL26D.md', 'migration/GOAL26-THREAD-PROMPTS.md', 'migration/SURVIVAL-PLAYABILITY.md']
# The two planning-session supplements of 2026-10-22 in the dirty start (no receipt hashes them).
PLANNING_SUPPLEMENTS = ['migration/GOAL26C.md', 'migration/GOAL26-THREAD-PROMPTS.md']
FROZEN_RECORD = re.compile(r'migration/(GOAL25[^/]*\.md|goal25[abcd]-[^/]+|GOAL24[^/]*\.md|goal24[^/]*|GOAL26[AB][^/]*\.md|goal26[ab]-[^/]+|GOAL26D[^/]*\.md|GOAL26-THREAD-PROMPTS\.md|SURVIVAL-PLAYABILITY\.md)')
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED_BASE + the advancements.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]
# The shared records the main agent edits after a package (not hashed by a receipt): their receipt after-hash may differ from the start hash (the records written after a package).
SHARED_AFTER_PACKAGE = set(SHARED_RECORDS)
# The 15 new language keys: NEO key -> (original key or None, expected map kind). All upstream with the original English and Chinese verbatim (en_US.lang:3029-3049 without the kits and the PaA
# suit, zh_CN.lang:2593-2613); no local key.
SOURCE_KEYS = {f'item.hbmsntm.{n}': (f'item.{n}.name', 'upstream') for n in ITEM_ICONS}
KEYS = {k: v[0] for k, v in SOURCE_KEYS.items()}
EXPECTED_KINDS = dict(Counter(v[1] for v in SOURCE_KEYS.values()))
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-hazmat] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the sessions of the batch.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_head.txt', 'start_hashes.txt',
                  'import_resources.py', 'add_zh.py', 'main-notes.md', 'handoff-builder.md', 'builder-report.md', 'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md',
                  'verifier-report.md', 'review-report.md', 'chain.sh', 'make_production_diff.py', 'oldsuites/report.md')
# Review files under OUT the main agent names when it knows them; each must exist and is indexed by the receipt. Extend this list from the real run; --check lists the top-level OUT files
# that no list indexes.
REVIEW_EVIDENCE = ('make_loc_review.py', 'update_features.py', 'make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier-gt/scope-before.txt', 'verifier-gt/scope-after.txt', 'builder_compile.log',
                   'builder_rundata.log', 'builder_build.log', 'builder_pre_rundata_generated.txt', 'builder_post_rundata_generated.txt', 'review-diff.patch', 'review-new-files.txt',
                   'verifier-progress.md', 'verify-final.out', 'compare.log', 'localization-final.log', 'resources-audit-final.log', 'packaged-resources-final.log')
GAMETEST_LOG = 'build/migration/goal26c/gametest-final.log'
NEW_SUITE = 'verify_goal26c_hazmat.py --gametest-log build/migration/goal26c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# Suites other than NEW_SUITE the GameTest verifier may add to the final rerun (none known; extend from handoff-verifier.md part C / oldsuites/report.md if it adds separate entries; the six
# old machine / pollution suites it revives keep their suite names and run through the wrapper switch of run_final.py).
EXTRA_FINAL_SUITES = set()
FEATURE_HAZMAT = 'hazmat-suits'
NEW_FEATURES = (FEATURE_HAZMAT,)
# The groups the snapshot of the end of 24A predates (24B rbmk-fuel, 24C rbmk-reactor, 24D rbmk-control and rbmk-steam, 24E rbmk-console, 25A rbmk-storage and rbmk-recycling,
# 25B rbmk-outgasser, 25C rbmk-autoloader, 25D rbmk-crane, 26A hazard-system and radiation-detection, 26B gas-masks).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser', 'rbmk-autoloader', 'rbmk-crane',
                          'hazard-system', 'radiation-detection', 'gas-masks'}
RADIATION_NOTE = ('Goal26C: hazmat suits now reduce radiation doses as in the original (full yellow / red / grey about 75 % / 90 % / 99 %); an existing custom hbmRadResist.json still replaces '
                  'the default table, so the suits give no resistance there until rows are added; radiation tests stay in a separately authorized disposable world. ')
MELTDOWN_NOTE = 'Goal26C: no new meltdown path; reactor tests stay in disposable worlds. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_MAINREG = ORIGINAL+'main/MainRegistry.java'
O_HAZREG = ORIGINAL+'handler/HazmatRegistry.java'
O_CONTAM = ORIGINAL+'util/ContaminationUtil.java'
O_HAZMAT = ORIGINAL+'items/armor/ArmorHazmat.java'
O_HAZMASK = ORIGINAL+'items/armor/ArmorHazmatMask.java'
O_MODITEMS = ORIGINAL+'items/ModItems.java'
O_ARMORUTIL = ORIGINAL+'util/ArmorUtil.java'
O_ARMORRECIPES = ORIGINAL+O_ARMORRECIPES_PATH
O_CRAFTING = ORIGINAL+O_CRAFTING_PATH
O_ASSEMBLY = ORIGINAL+'inventory/recipes/AssemblyMachineRecipes.java'
O_SOURCES = [O_MAINREG, O_HAZREG, O_CONTAM, O_HAZMAT, O_HAZMASK, O_MODITEMS, O_ARMORUTIL, O_ARMORRECIPES, O_CRAFTING, O_ASSEMBLY, O_LANG_EN, O_LANG_ZH]
# The original sources the new mapping group must list (source_paths or source_watch; plus the imported resources).
FEATURE_SOURCES = {FEATURE_HAZMAT: [O_MAINREG, O_HAZREG, O_CONTAM, O_HAZMAT, O_HAZMASK, O_MODITEMS, O_ARMORUTIL, O_ARMORRECIPES, O_CRAFTING, O_ASSEMBLY] + list(ASSETS.values())}
# The NEO paths the new mapping group must cover (target_paths or target_watch).
FEATURE_TARGETS = {FEATURE_HAZMAT: NEW_JAVA + [HAZMAT_REGISTRY, CONTAMINATION, ARMOR_UTIL, ARMOR_MATERIALS] + list(ASSETS) + [NEW_TOOLS[0], NEW_TOOLS[1]]
                   + [GENERATED_ROOT+p for p in EXPECTED_GENERATED_BASE]}
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'hazmat_material': (O_MAINREG, 'aMatHaz = EnumHelper.addArmorMaterial("HBM_HAZMAT", 60'), 'hazmat_repair': (O_MAINREG, 'aMatHaz.customCraftingMaterial = ModItems.hazmat_cloth;'),
    'registry_part_factors': (O_HAZREG, 'public static double helmet = 0.2D;'), 'registry_suit_values': (O_HAZREG, 'double hazYellow = 0.6D;'),
    'registry_suit_rows': (O_HAZREG, 'HazmatRegistry.registerHazmat(ModItems.hazmat_helmet, hazYellow * helmet);'),
    'registry_gas_masks': (O_HAZREG, 'HazmatRegistry.registerHazmat(ModItems.gas_mask, 0.07);'),
    'registry_resistance_sum': (O_HAZREG, 'res += getResistance(player.inventory.armorInventory[i]);'), 'registry_radx': (O_HAZREG, 'HbmPotion.radx'),
    'armor_util_sand': (O_ARMORUTIL, 'ArmorRegistry.registerHazard(ModItems.hazmat_helmet, HazardClass.SAND);'), 'armor_util_check_armor': (O_ARMORUTIL, 'checkArmorPiece(entity, armor[i], 3 - i)'),
    'armor_util_check_for_hazmat': (O_ARMORUTIL, 'public static boolean checkForHazmat'),
    'contamination_koeff': (O_CONTAM, 'float koeff = 10.0F;'), 'contamination_hazmat_case': (O_CONTAM, 'case HAZMAT:'),
    'contamination_creative': (O_CONTAM, 'player.capabilities.isCreativeMode && cont != ContaminationType.NONE'),
    'hazmat_mask_blacklist': (O_HAZMASK, 'full hood has no restrictions'), 'hazmat_mask_model': (O_HAZMASK, 'this == ModItems.hazmat_helmet_red'),
    'hazmat_mask_use': (O_HAZMASK, 'public ItemStack onItemRightClick'), 'hazmat_overlay_texture': (O_HAZMAT, 'overlay_hazmat.png'),
    'hazmat_overlay_condition': (O_HAZMAT, 'this != ModItems.hazmat_helmet && this != ModItems.hazmat_paa_helmet'),
    'items_cloth': (O_MODITEMS, 'hazmat_cloth = new Item()'), 'items_helmet': (O_MODITEMS, 'hazmat_helmet = new ArmorHazmatMask('),
    'armor_recipes': (O_ARMORRECIPES, 'new ItemStack(ModItems.hazmat_helmet, 1)'),
    'cloth_recipe_red': (O_CRAFTING, 'new ItemStack(ModItems.hazmat_cloth_red, 1)'), 'cloth_recipe_grey': (O_CRAFTING, 'new ItemStack(ModItems.hazmat_cloth_grey, 1)'),
    'assembly_hazcloth': (O_ASSEMBLY, 'new GenericRecipe("ass.hazcloth")'),
    'lang_hazmat_helmet_en': (O_LANG_EN, 'item.hazmat_helmet.name='), 'lang_hazmat_helmet_zh': (O_LANG_ZH, 'item.hazmat_helmet.name='), 'lang_hazmat_cloth_grey_en': (O_LANG_EN, 'item.hazmat_cloth_grey.name='),
}
# Constants compared between the original and NEO source texts: id -> (original path or None, regex, NEO path, regex, expected, expected NEO values when they differ). `expected` is the exact
# list of distinct normalized values of the original (numbers as floats, underscores and an F / D suffix dropped, anything else as text) in order, or None; a NEO-only constant has no original
# path. The group-1 value of every match is collected. A NEO regex that finds nothing (the class is not written yet, or its text differs from the handoff) is reported as pending with its id.
CONSTANTS = {
    # Materials (MainRegistry.java:132-134): durability factor 60, defense {2,5,4,1} (helmet first; NEO defense(boots, leggings, chestplate, helmet) = 1, 4, 5, 2), enchantability 5, repair cloth per tier
    # (:293-295). Durability per slot = 60 * the vanilla factor 11 / 16 / 15 / 13 = 660 / 960 / 900 / 780 (NtmItems getDurability(60)).
    'hazmat_durability_factor': (O_MAINREG, r'addArmorMaterial\("HBM_HAZMAT\d?", (\d+),', ITEMS, r'HAZMAT\w* = ITEMS\.register\([^\n]*?getDurability\((\d+)\)', [60]),
    'hazmat_defense': (O_MAINREG, r'addArmorMaterial\("HBM_HAZMAT\d?", \d+, new int\[\] \{ ([\d, ]+) \}, \d+\)', ARMOR_MATERIALS,
                       r'register\("hazmat[a-z_]*", \(\) -> new ArmorMaterial\(\s*defense\(([\d, ]+)\),', ['2, 5, 4, 1'], ['1, 4, 5, 2']),
    'hazmat_enchantability': (O_MAINREG, r'addArmorMaterial\("HBM_HAZMAT\d?", \d+, new int\[\] \{[^}]*\}, (\d+)\)', ARMOR_MATERIALS,
                              r'register\("hazmat[a-z_]*", \(\) -> new ArmorMaterial\(\s*defense\([\d, ]+\),\s*(\d+),', [5]),
    'hazmat_repair_items': (O_MAINREG, r'aMatHaz\d?\.customCraftingMaterial = ModItems\.(\w+);', ARMOR_MATERIALS, r'Ingredient\.of\(NtmItems\.(HAZMAT\w*)\.get\(\)\)',
                            ['hazmat_cloth', 'hazmat_cloth_red', 'hazmat_cloth_grey'], ['HAZMAT_CLOTH', 'HAZMAT_CLOTH_RED', 'HAZMAT_CLOTH_GREY']),
    # HazmatRegistry (:34-37 part factors, :56-58 suit values, :110-111 the two gas masks). The original fields are static members, NEO keeps them as locals of initDefault.
    'registry_helmet_factor': (O_HAZREG, r'public static double helmet = ([\d.]+)D;', HAZMAT_REGISTRY, r'double helmet = ([\d.]+)D;', [0.2]),
    'registry_chest_factor': (O_HAZREG, r'public static double chest = ([\d.]+)D;', HAZMAT_REGISTRY, r'double chest = ([\d.]+)D;', [0.4]),
    'registry_legs_factor': (O_HAZREG, r'public static double legs = ([\d.]+)D;', HAZMAT_REGISTRY, r'double legs = ([\d.]+)D;', [0.3]),
    'registry_boots_factor': (O_HAZREG, r'public static double boots = ([\d.]+)D;', HAZMAT_REGISTRY, r'double boots = ([\d.]+)D;', [0.1]),
    'registry_yellow_value': (O_HAZREG, r'double hazYellow = ([\d.]+)D;', HAZMAT_REGISTRY, r'double hazYellow = ([\d.]+)D;', [0.6]),
    'registry_red_value': (O_HAZREG, r'double hazRed = ([\d.]+)D;', HAZMAT_REGISTRY, r'double hazRed = ([\d.]+)D;', [1.0]),
    'registry_grey_value': (O_HAZREG, r'double hazGray = ([\d.]+)D;', HAZMAT_REGISTRY, r'double hazGray = ([\d.]+)D;', [2]),
    'registry_gas_mask_values': (O_HAZREG, r'registerHazmat\(ModItems\.gas_mask(?:_m65)?, ([\d.]+)\);', HAZMAT_REGISTRY, r'registerHazmat\(NtmItems\.GAS_MASK(?:_M65)?\.get\(\), ([\d.]+)\);', [0.07, 0.095]),
    # The dose coefficient (ContaminationUtil.java:36): doses are multiplied by 10^-resistance, so 0.6 / 1.0 / 2.0 give about 0.251 / 0.1 / 0.01.
    'contamination_coefficient': (O_CONTAM, r'float koeff = ([\d.]+)F;', CONTAMINATION, r'float coefficient = ([\d.]+)F;', [10]),
    # The yellow hood draws overlay_hazmat.png (ArmorHazmat.java:19, :27-28); the red and grey hoods do not.
    'overlay_texture': (O_HAZMAT, r'RefStrings\.MODID \+ ":(textures/misc/overlay_hazmat\.png)"', ITEMS, r'withDefaultNamespace\("(textures/misc/overlay_hazmat\.png)"\)', ['textures/misc/overlay_hazmat.png']),
}
# Sequences (every match in source order, original against NEO, compared sorted; the groups of a match are joined by '|', lower case, spaces and an F / D suffix dropped): id -> (original path, regex,
# NEO path, regex, expected match count of the original[, the explicit NEO values when they differ by the renames of the batch]).
SEQUENCES = {
    # The 14 registerHazmat rows of the batch (HazmatRegistry.java:68-79 the twelve suit pieces, :110-111 the two gas masks): item and value expression.
    'registry_rows': (O_HAZREG, r'registerHazmat\(ModItems\.(hazmat_(?:helmet|plate|legs|boots)(?:_red|_grey)?|gas_mask|gas_mask_m65), ([^)]*)\);', HAZMAT_REGISTRY,
                      r'registerHazmat\(NtmItems\.(HAZMAT_(?:HELMET|PLATE|LEGS|BOOTS)(?:_RED|_GREY)?|GAS_MASK|GAS_MASK_M65)\.get\(\), ([^)]*)\);', 14),
    # ArmorUtil.java:57-59: the three SAND lines of the hoods (the PaA line :60 waits for its suit).
    'sand_lines': (O_ARMORUTIL, r'registerHazard\(ModItems\.(hazmat_helmet(?:_red|_grey)?), (HazardClass\.\w+)\);', ARMOR_UTIL,
                   r'registerHazard\(NtmItems\.(HAZMAT_HELMET(?:_RED|_GREY)?)\.get\(\), (HazardClass\.\w+)\);', 3),
    # ModItems.java:4253-4265: material per piece, and the worn texture per piece (the two helmet-model textures are renamed to lowercase, Goal 13A precedent).
    'material_per_piece': (O_MODITEMS, r'new ArmorHazmat(?:Mask)?\(MainRegistry\.(aMatHaz\d?), \d, ', ITEMS, r'new Hazmat(?:Armor|Helmet)Item\(NtmArmorMaterials\.(HAZMAT\w*), ', 12,
                           ['hazmat'] * 4 + ['hazmat_red'] * 4 + ['hazmat_grey'] * 4),
    'worn_textures': (O_MODITEMS, r'new ArmorHazmat(?:Mask)?\(MainRegistry\.aMatHaz\d?, \d, (?:RefStrings\.MODID \+ ":|"hbm:)(textures/[\w/]+\.png)"', ITEMS,
                      r'new Hazmat(?:Armor|Helmet)Item\([^\n]*?withDefaultNamespace\("(textures/[\w/]+\.png)"\)', 12,
                      ['textures/armor/hazmat_1.png', 'textures/armor/hazmat_1.png', 'textures/armor/hazmat_2.png', 'textures/armor/hazmat_1.png',
                       'textures/models/model_haz_red.png', 'textures/armor/hazmat_1_red.png', 'textures/armor/hazmat_2_red.png', 'textures/armor/hazmat_1_red.png',
                       'textures/models/model_haz_grey.png', 'textures/armor/hazmat_1_grey.png', 'textures/armor/hazmat_2_grey.png', 'textures/armor/hazmat_1_grey.png']),
}
# Model cubes: none in this batch (ModelM65 and ModelGasMask are unchanged since the start and held byte-identical).
MODEL_CUBES = {}
# Occurrence counts in the NEO source texts (expected), with the original count where one exists: id -> (NEO path, regex, expected count[, original path, original regex, original count]).
COUNTS = {
    'armor_materials_registered': (ARMOR_MATERIALS, r'ARMOR_MATERIALS\.register\("hazmat(?:_red|_grey)?"', 3, O_MAINREG, r'addArmorMaterial\("HBM_HAZMAT\d?"', 3),
    'armor_material_layers': (ARMOR_MATERIALS, r'new ArmorMaterial\.Layer\(NuclearTechMod\.withDefaultNamespace\("hazmat(?:_red|_grey)?"\)\)', 3),
    'armor_material_equip_sound': (ARMOR_MATERIALS, r'SoundEvents\.ARMOR_EQUIP_LEATHER,', 4),
    'armor_material_no_toughness_knockback': (ARMOR_MATERIALS, r'0F,\s*0F\)\);', 4),
    'hazmat_helmets_registered': (ITEMS, r'new HazmatHelmetItem\(NtmArmorMaterials\.HAZMAT(?:_RED|_GREY)?, ', 3, O_MODITEMS, r'= new ArmorHazmatMask\(MainRegistry\.aMatHaz\d?, 0, ', 3),
    'hazmat_pieces_registered': (ITEMS, r'new HazmatArmorItem\(NtmArmorMaterials\.HAZMAT(?:_RED|_GREY)?, ArmorItem\.Type\.(?:CHESTPLATE|LEGGINGS|BOOTS), ', 9,
                                 O_MODITEMS, r'= new ArmorHazmat\(MainRegistry\.aMatHaz\d?, [123], ', 9),
    'hazmat_cloths_registered': (ITEMS, r'ITEMS\.register\("hazmat_cloth(?:_red|_grey)?", \(\) -> new Item\(new Item\.Properties\(\)\)\)', 3, O_MODITEMS, r'hazmat_cloth(?:_red|_grey)? = new Item\(\)', 3),
    'durability_factor_60_per_piece': (ITEMS, r'ArmorItem\.Type\.(?:HELMET|CHESTPLATE|LEGGINGS|BOOTS)\.getDurability\(60\)', 12),
    'registry_rows_count': (HAZMAT_REGISTRY, r'registerHazmat\(NtmItems\.', 14, O_HAZREG, r'registerHazmat\(ModItems\.(?:hazmat_(?:helmet|plate|legs|boots)(?:_red|_grey)?|gas_mask|gas_mask_m65),', 14),
    'check_armor_slot_order': (ARMOR_UTIL, r'EquipmentSlot\.HEAD,\s*// 0\s*EquipmentSlot\.CHEST,\s*// 1\s*EquipmentSlot\.LEGS,\s*// 2\s*EquipmentSlot\.FEET\s*// 3', 1,
                               O_ARMORUTIL, r'checkArmorPiece\(entity, armor\[i\], 3 - i\)', 1),
    'check_for_hazmat_three_sets': (ARMOR_UTIL, r'checkArmor\(entity, NtmItems\.HAZMAT_HELMET(?:_RED|_GREY)?\.get\(\), NtmItems\.HAZMAT_PLATE(?:_RED|_GREY)?\.get\(\), NtmItems\.HAZMAT_LEGS(?:_RED|_GREY)?\.get\(\), '
                                    r'NtmItems\.HAZMAT_BOOTS(?:_RED|_GREY)?\.get\(\)\)', 3,
                                    O_ARMORUTIL, r'checkArmor\(player, ModItems\.hazmat_helmet(?:_red|_grey)?, ModItems\.hazmat_plate(?:_red|_grey)?, ModItems\.hazmat_legs(?:_red|_grey)?, '
                                    r'ModItems\.hazmat_boots(?:_red|_grey)?\)', 3),
    'check_for_hazmat_no_other_set': (ARMOR_UTIL, r'checkArmor\(entity, NtmItems\.', 3),
    'check_for_hazmat_mutation': (ARMOR_UTIL, r'return entity\.hasEffect\(ModEffect\.MUTATION\);', 1, O_ARMORUTIL, r'player\.isPotionActive\(HbmPotion\.mutation\)\) return true;', 1),
    'contamination_hazmat_before_creative': (CONTAMINATION, r'if\(type == ContaminationType\.HAZMAT && ArmorUtil\.checkForHazmat\(player\)\) return;\s*(?://[^\n]*\n\s*)?if\(\(player\.isCreative\(\) \|\| player\.isSpectator\(\)\)', 1,
                                             O_CONTAM, r'case HAZMAT:\s*if\(ArmorUtil\.checkForHazmat\(player\)\)\s*return false; break;(?:.|\n)*?if\(player\.capabilities\.isCreativeMode', 1),
    'contamination_no_other_branch': (CONTAMINATION, r'type == ContaminationType\.(?:FARADAY|HAZMAT_HEAVY|DIGAMMA)\b', 0),
    'helmet_empty_blacklist': (HAZMAT_HELMET_ITEM, r'return new ArrayList<>\(\); // full hood has no restrictions', 1, O_HAZMASK, r'return new ArrayList\(\); // full hood has no restrictions', 1),
    'helmet_filter_always_applicable': (HAZMAT_HELMET_ITEM, r'public boolean isFilterApplicable\([^)]*\) \{\s*return true;', 1, O_HAZMASK, r'public boolean isFilterApplicable\([^)]*\) \{\s*return true;', 1),
    'helmet_filter_delegations': (HAZMAT_HELMET_ITEM, r'ArmorUtil\.(?:getGasMaskFilter|installGasMaskFilter|damageGasMaskFilter)\(entity\.level\(\), stack', 3,
                                  O_HAZMASK, r'ArmorUtil\.(?:getGasMaskFilter|installGasMaskFilter|damageGasMaskFilter)\(stack', 3),
    'helmet_tooltip_filter_first': (HAZMAT_HELMET_ITEM, r'ArmorUtil\.addGasMaskTooltip\(stack, context, components, flag\);\s*super\.appendHoverText', 1,
                                    O_HAZMASK, r'ArmorUtil\.addGasMaskTooltip\(stack, player, list, ext\);\s*super\.addInformation', 1),
    'helmet_use_shared_eject_helper': (HAZMAT_HELMET_ITEM, r'ArmorUtil\.ejectGasMaskFilter\(this, stack, level, player\)', 1, O_HAZMASK, r'ArmorUtil\.removeFilter\(stack\);', 1),
    'gas_mask_use_shared_eject_helper': (GAS_MASK_ITEM, r'ArmorUtil\.ejectGasMaskFilter\(this, stack, level, player\)', 1),
    'eject_helper_defined_once': (ARMOR_UTIL, r'public static boolean ejectGasMaskFilter\(IGasMask mask, ItemStack stack, Level level, Player player\)', 1),
    'eject_body_in_armor_util_only': (ARMOR_UTIL, r'player\.drop\(filter, true, false\)', 1),
    'eject_body_not_in_gas_mask': (GAS_MASK_ITEM, r'player\.drop\(filter', 0),
    'eject_body_not_in_hazmat_helmet': (HAZMAT_HELMET_ITEM, r'player\.drop\(filter', 0),
    'helmet_m65_model_red_grey': (ITEMS, r'new HazmatHelmetItem\([^\n]*?, true, null\)', 2, O_HAZMASK, r'this == ModItems\.hazmat_helmet_red \|\| this == ModItems\.hazmat_helmet_grey', 1),
    'helmet_overlay_yellow_only': (ITEMS, r'new HazmatHelmetItem\(NtmArmorMaterials\.HAZMAT, [^\n]*?, false, NuclearTechMod\.withDefaultNamespace\("textures/misc/overlay_hazmat\.png"\)\)', 1,
                                   O_HAZMAT, r'this != ModItems\.hazmat_helmet && this != ModItems\.hazmat_paa_helmet', 1),
    'client_extension_registered_for_hoods': (CLIENT_MOD, r'event\.registerItem\(new GasMaskClientExtensions\(\), NtmItems\.GAS_MASK\.get\(\), NtmItems\.GAS_MASK_M65\.get\(\), NtmItems\.GAS_MASK_MONO\.get\(\), '
                                              r'NtmItems\.GAS_MASK_OLDE\.get\(\),\s*NtmItems\.HAZMAT_HELMET\.get\(\), NtmItems\.HAZMAT_HELMET_RED\.get\(\), NtmItems\.HAZMAT_HELMET_GREY\.get\(\)\);', 1),
    'client_extension_m65_for_red_grey': (CLIENT_EXTENSIONS, r'return hood\.isM65Model\(\) \? m65\(living\) : original;', 1),
    'client_extension_fixed_overlay': (CLIENT_EXTENSIONS, r'ResourceLocation tex = hood\.getOverlay\(\);\s*if\(tex != null\) drawOverlay\(guiGraphics, tex\);', 1),
    'assembly_hazcloth_rows': (ASSEMBLY, r'new GenericRecipe\("ass\.hazcloth"\)', 1, O_ASSEMBLY, r'new GenericRecipe\("ass\.hazcloth"\)', 1),
    'creative_tab_cloths': (CREATIVE_TABS, r'output\.accept\(NtmItems\.HAZMAT_CLOTH(?:_RED|_GREY)?\.get\(\)\);', 3),
    'creative_tab_suit_pieces': (CREATIVE_TABS, r'output\.accept\(NtmItems\.HAZMAT_(?:HELMET|PLATE|LEGS|BOOTS)(?:_RED|_GREY)?\);', 12),
    'tag_provider_enchantable_constants': (TAG_PROVIDER, r'ItemTags\.create\(ResourceLocation\.fromNamespaceAndPath\("minecraft", "enchantable/(?:head_armor|chest_armor|leg_armor|foot_armor|durability|equippable)"\)\)', 6),
    'tag_provider_slot_tags_untouched': (TAG_PROVIDER, r'"minecraft", "(?:head_armor|chest_armor|leg_armor|foot_armor|trimmable_armor)"', 0),
    'tag_provider_six_tags_filled': (TAG_PROVIDER, r'this\.tag\(ENCHANTABLE_(?:HEAD_ARMOR|CHEST_ARMOR|LEG_ARMOR|FOOT_ARMOR|DURABILITY|EQUIPPABLE)\)\.add\(', 6),
}
# per-item registration counts (one occurrence each) in creative tabs, the item model provider, the language provider and the registry.
for _n, _c in ITEM_TABLE.items():
    COUNTS[f'{_n}_registered'] = (ITEMS, rf'DeferredItem<Item> {_c} = ITEMS\.register\("{_n}"', 1)
    COUNTS[f'{_n}_item_model'] = (ITEM_MODEL_PROVIDER, rf'this\.basicItem\(NtmItems\.{_c}\.get\(\)\);', 1)
    COUNTS[f'{_n}_english_name'] = (PROVIDER, rf'this\.add\(NtmItems\.{_c}, "', 1)
    COUNTS[f'{_n}_creative_tab'] = (CREATIVE_TABS, rf'output\.accept\(NtmItems\.{_c}(?:\.get\(\))?\);', 1)
# Client-side classes the common code must not reference: the common classes below import nothing from net.minecraft.client and never name the client extension or the models.
COMMON_CLASSES = [HAZMAT_ARMOR_ITEM, HAZMAT_HELMET_ITEM, GAS_MASK_ITEM, ARMOR_MATERIALS, ARMOR_UTIL, CONTAMINATION, HAZMAT_REGISTRY, ITEMS]
CLIENT_ONLY_NAMES = re.compile(r'GasMaskClientExtensions|ModelGasMask|ModelM65|IClientItemExtensions|net\.minecraft\.client|com\.hbm\.render\.')
# The durability per slot (60 * the vanilla factor 11 / 16 / 15 / 13), the dose factors (10^-resistance, resistance = the sum of the four part values) and the HazmatRegistry default table (8 -> 22 rows).
DURABILITY = {'helmet': 60 * 11, 'chestplate': 60 * 16, 'leggings': 60 * 15, 'boots': 60 * 13}
SUIT_VALUES = {'yellow': 0.6, 'red': 1.0, 'grey': 2.0}
PART_FACTORS = {'helmet': 0.2, 'chest': 0.4, 'legs': 0.3, 'boots': 0.1}
DOSE_FACTORS = {tier: round(10 ** -value, 4) for tier, value in SUIT_VALUES.items()}
# Known source differences the batch deliberately leaves (recorded; not asserted equal, but each is backed by a NEO constant or fact above where it can be). main-notes.md 1-8.
KNOWN_DIFFERENCES = {
    'enchantability_tags': 'the six 26B masks and the twelve suit pieces are tagged into minecraft:enchantable/{head,chest,leg,foot}_armor plus enchantable/durability and enchantable/equippable, not into minecraft:head_armor etc. '
                           '(the task book wording): those slot tags also feed minecraft:trimmable_armor, 1.7.10 had no trims and vanilla-UV trims would be drawn over the custom helmet models; the enchantments are the same '
                           'ones #head_armor would give. NO9 stays untagged (main-notes 1; review F2 of 26B)',
    'check_armor_slot_order': 'NEO ArmorUtil.checkArmor mapped armor[0] to the feet (reversed against ArmorUtil.java:82-94, which checks slot 3 - i, i.e. helmet, chestplate, leggings, boots); corrected to HEAD, CHEST, LEGS, FEET '
                              'as a NEO-only fix so checkForHazmat can keep the original argument order; no other caller exists (main-notes 2)',
    'check_for_hazmat': 'the original (ArmorUtil.java:120-135, @Deprecated) also accepts the schrabidium set and checkForHaz2 (PaA, liquidator, euphemium, RPA, FAU, DNS); only the three hazmat sets and the MUTATION effect are migrated, '
                        'and the NEO method is not deprecated',
    'hazmat_branch': 'ContaminationUtil.contaminate returns early for a player in a full set when the type is HAZMAT, before the creative / spectator and tickCount < 200 exemptions (ContaminationUtil.java:278 against :283-287); '
                      'FARADAY, HAZMAT_HEAVY and DIGAMMA are not wired (no migrated armor). No NEO caller passes HAZMAT (neither does the original): the branch is not reachable in game yet',
    'helmet_classes': 'HazmatArmorItem extends ModArmorItem with a constructor only (ArmorHazmat without ArmorFSB: no set-bonus framework is ported, the pieces carry none); HazmatHelmetItem implements IGasMask with an empty '
                      'blacklist (the original "full hood has no restrictions"), isFilterApplicable true, the filter methods delegating to ArmorUtil, the tooltip filter lines first and the shared '
                      'ArmorUtil.ejectGasMaskFilter helper for the sneak-right-click removal (the same body GasMaskItem.use had in 26B; main-notes 3)',
    'client_extension': 'the three hazmat hoods share the GasMaskClientExtensions instance of the masks: the red and grey hoods use the shared ModelM65 with the same filter-visibility rule, the yellow hood keeps the standard helmet '
                        'layer with hazmat_1.png and draws overlay_hazmat.png through the item-level renderHelmetOverlay (the original draws it for the yellow and PaA helmets only); client only, registered from '
                        'NuclearTechModClient (main-notes 4)',
    'materials': 'NtmArmorMaterials HAZMAT / HAZMAT_RED / HAZMAT_GREY: defense boots / leggings / chestplate / helmet 1 / 4 / 5 / 2 (the original {2,5,4,1} is helmet first), enchantment value 5, equip sound ARMOR_EQUIP_LEATHER '
                 '(1.7.10 armor had none), repair Ingredient.of(tier cloth), one layer (never used for rendering), toughness 0, knockback 0; durability getDurability(60) = 660 / 960 / 900 / 780 (main-notes 5)',
    'recipe_inputs': 'KEY_ANYPANE -> c:glass_panes; IRON.plate() -> hbmsntm:plate_iron (no c:plates/iron tag); PB.plate() -> hbmsntm:plate_lead (no lead plate tag); REDSTONE.dust() -> minecraft:redstone; ANY_RUBBER.ingot() -> '
                     'ntm:any_rubbers; PB.dust() of the assembly row -> the item powder_lead (no NEO ass.* row uses an ore-dictionary stack)',
    'creative_tabs': 'the twelve suit pieces sit in the CONSUMABLE tab after mask_piss (26B precedent), the cloths in the PARTS tab after filter_coal (the original partsTab; main-notes 8)',
    'config_contract': 'the 14 new initDefault rows (twelve suit pieces and the gas_mask 0.07 / gas_mask_m65 0.095 rows) enlarge the default table from 8 to 22 rows; writeDefault / readConfig / registerHazmats / getResistance are '
                       'unchanged, so a player\'s existing custom hbmRadResist.json still replaces the whole table and the suits then give no resistance until their rows are added',
    'language': 'the fifteen item names are upstream verbatim (en_US.lang:3029-3049, zh_CN.lang:2593-2613 without the kits and the PaA suit; main-notes 7); no local key',
    'deferred': 'the hazmat kits (hazmat_kit, hazmat_red_kit, hazmat_grey_kit), the PaA suit and its textures, the liquidator / PaA / security / starmetal / steel rows of HazmatRegistry, the asbestos cloth and checkForHaz2 are not migrated',
}
# The recipe key tables: original key expression -> the NEO ingredient (OneOf: several accepted generated forms). Forms follow the generated recipes: items by registry name, tags where the
# provider uses the tag for the same oredict key (main-notes 7).
GLASS_PANE = OneOf({'tag': 'c:glass_panes'}, {'item': 'minecraft:glass_pane'})
KEY_TABLE = {
    'KEY_ANYPANE': GLASS_PANE, 'IRON.plate()': {'item': 'hbmsntm:plate_iron'}, 'PB.plate()': {'item': 'hbmsntm:plate_lead'}, 'ANY_RUBBER.ingot()': {'tag': 'ntm:any_rubbers'},
    'REDSTONE.dust()': {'item': 'minecraft:redstone'}, 'ModItems.hazmat_cloth': {'item': 'hbmsntm:hazmat_cloth'}, 'ModItems.hazmat_cloth_red': {'item': 'hbmsntm:hazmat_cloth_red'},
    'ModItems.hazmat_cloth_grey': {'item': 'hbmsntm:hazmat_cloth_grey'},
}
# ASSEMBLY (AssemblyMachineRecipes.java:118-119): ass.hazcloth, 50 ticks, 100 HE/t, lead dust x4 + string x8 -> hazmat_cloth x4 (PB.dust() is NEO's powder_lead).
ASSEMBLY_ID = 'ass.hazcloth'
ASSEMBLY_EXPECTED = dict(setup=[50, 100], output=['HAZMAT_CLOTH', 4], inputs=[['item', 'POWDER_LEAD', 4], ['vanilla', 'STRING', 8]])
ASSEMBLY_ORIGINAL_ITEMS = {'PB.dust()': ('item', 'POWDER_LEAD')}
# The old isolated machine / pollution suites (handoff-verifier.md part C) that the GameTest verifier tries to revive through a goal26c_oldsuite_* wrapper; recorded in the receipt when the wrapper exists.
OLD_MACHINE_SUITES = ('verify_goal16a_machine', 'verify_goal16b_machine', 'verify_goal17b_machine', 'verify_goal18a_machine', 'verify_goal18b_machine', 'verify_goal19a_pollution')


def scope_text(key_count, assets, tests, total_tests):
    return (f'Goal26C (the third batch of Goal 26: hazmat suits): the three hazmat suit tiers (yellow, red = advanced, grey = high-performance), twelve armor pieces on three new NtmArmorMaterials '
            f'(HazmatArmorItem for the nine body pieces, HazmatHelmetItem for the three helmets; durability 660 / 960 / 900 / 780, defense 2 / 5 / 4 / 1, enchantment value 5, repaired with the tier cloth); '
            f'the three hazmat cloths, the first one from the assembly machine (ass.hazcloth: lead powder x4 + string x8 -> 4 cloths, 50 ticks, 100 HE/t), the red and grey ones by crafting; {len(RECIPES)} '
            f'crafting recipes; the HazmatRegistry default rows for the twelve suit pieces and the two gas masks (part factors 0.2 / 0.4 / 0.3 / 0.1, suits 0.6 / 1.0 / 2.0, gas_mask 0.07, gas_mask_m65 0.095; '
            f'the default table grows from 8 to 22 rows); ArmorUtil.checkForHazmat (the three full sets or the MUTATION effect, with the checkArmor slot-order correction) and the HAZMAT contamination branch '
            f'in ContaminationUtil.contaminate (before the creative exemption); the three helmets take gas-mask filters (empty blacklist), the red and grey helmets use the 26B M65 model, the yellow helmet draws '
            f'the hazmat overlay; armor enchantability tags for the six 26B masks and the twelve suit pieces (minecraft:enchantable/* tags instead of the trimmable slot tags); {assets} imported resources '
            f'(15 item icons, 6 armor textures, 2 helmet-model textures, the overlay); {key_count} English keys and {key_count} Chinese entries ({EXPECTED_KINDS.get("upstream", 0)} upstream, '
            f'{EXPECTED_KINDS.get("local", 0)} local); {tests} HazmatSuitGameTests ({total_tests} GameTests in total, one batch per test) and the written, not executed acceptance checklist '
            f'GOAL26C-ACCEPTANCE.md. Gameplay impact: hazmat suits can be crafted in survival and cut radiation doses to about 25 % / 10 % / 1 % (full yellow / red / grey set); the two gas masks now carry '
            f'a small resistance; a player\'s existing custom hbmRadResist.json still replaces the whole default table; the Goal26A moderated items and the Goal26B masks stay as they were.')

def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal26c release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 234 scope copies: every dirty start file and the clean files the batch planned to touch) when it reproduces the baseline hash,
    else the blob at the start commit (with CRLF where the working tree had it); None when nothing reproduces the baseline hash (a file of the uncommitted Goal26B delivery without a copy)."""
    if (START_FILES/p).is_file():
        data = (START_FILES/p).read_bytes()
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    try: blob = __import__('subprocess').check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT,
                                                      stderr=__import__('subprocess').DEVNULL)
    except Exception: return None
    for data in (blob, blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def start_json(base, p):
    data = start_bytes(base, p)
    assert data is not None, 'No reproducible start bytes for '+p
    return json.loads(data.decode('utf-8-sig'))


def start_pin(base, p):
    """The Goal26C start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does not list it)
    the hash the goal26b receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal26b packager protected (built there from the Goal21A..Goal25D starts and receipts and the goal26b start), plus every path the goal26b receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 26B baseline lists the goal25d receipt among them) and every release file of the frozen start
    (the goal26b package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes, GOAL25D-ACCEPTANCE.md)
    are pinned at their Goal26C start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal26b packager set at its Goal26B start hash, for the records that changed between the two starts."""
    goal26b_start = read(GOAL26B_BASELINE)
    out = dict(goal26b_protected_paths(goal26b_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal26b receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal26b_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift.
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal26B and Goal26C starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal26b_start):
    """{path: {receipts, start_sha256, goal26b_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal26b receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal26b receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif p == 'migration/GOAL25D-ACCEPTANCE.md':
            explanation = ('Edited after the goal25d package was written (the goal25d receipt hash is the pre-close-out text) and committed in the Goal 25 close-out commit 5b1bf4db, which records the '
                           'real-game acceptance as deferred into Goal 26; the goal26b receipt records the start hash. Frozen at the start hash; this batch must not change it and no receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22, 23 and 24 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal26b '
                           'receipt does not hash it. Frozen at the Goal26C start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal26b) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal26b package; the goal26b receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal26b '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal26b_start_sha256=goal26b_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal26b_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def group(p, base):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA or p in OPTIONAL_JAVA: return 'production'
    if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p in base['files'] and p not in UNCHANGED_JAVA: return 'production-older-gametest'
    if p in ASSETS: return 'production-resource'
    if p == ZH_INPUT: return 'production-chinese'
    if p == LOCALIZATION_RECORD: return 'production-localization-record'
    if p.startswith(GENERATED_ROOT): return 'generated'
    if p in NEW_TOOLS or OLDSUITE_TOOL.fullmatch(p): return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    return None


def is_comment(line):
    s = line.strip()
    return not s or s.startswith(('//', '*', '/*', '*/'))


def original_recipe(text, kind, selector):
    """{pattern, key, count} (shaped), {ingredients, count} (shapeless) or {result, experience} (smelting) of the single original line matching the selector, or None when the line is not
    unique or does not parse. A key expression missing from KEY_TABLE maps to None."""
    lines = [l for l in text.replace('\r\n', '\n').split('\n') if re.search(selector, l)]
    if len(lines) != 1: return None
    line = lines[0]
    if kind == 'smelting':
        m = re.search(r'addSmelting\(.*?, new ItemStack\(ModItems\.(\w+)\), ([\d.]+)F\)', line)
        return dict(result=m.group(1), experience=float(m.group(2))) if m else None
    m = re.search(r'Auto\(new ItemStack\((.*?)\),\s*new Object\[\] \{ (.*) \}\);', line)
    if not m: return None
    stack = split_args(m.group(1))
    count = int(stack[1]) if len(stack) > 1 and stack[1].isdigit() else 1
    tokens = split_args(m.group(2))
    if kind == 'shapeless': return dict(ingredients=[KEY_TABLE.get(t) for t in tokens], count=count)
    pattern = [t[1:-1] for t in tokens if t.startswith('"')]
    rest = [t for t in tokens if not t.startswith('"')]
    return dict(pattern=pattern, key={rest[i].strip("'"): KEY_TABLE.get(rest[i+1]) for i in range(0, len(rest)-1, 2)}, count=count)


def ingredient_ok(neo, expected):
    if expected is None: return False
    return neo in expected.forms if isinstance(expected, OneOf) else neo == expected


def shapeless_ok(neo_list, expected_list):
    if not isinstance(neo_list, list) or len(neo_list) != len(expected_list): return False
    pool = list(neo_list)
    for e in expected_list:
        for i, n in enumerate(pool):
            if ingredient_ok(n, e):
                pool.pop(i)
                break
        else: return False
    return True


def recipe_matches(kind, data, o_row, result_id):
    """The generated recipe JSON equals the parsed original row (result id and count from the owner table)."""
    if kind == 'shaped':
        key = data.get('key') or {}
        return (data.get('type') == 'minecraft:crafting_shaped' and data.get('pattern') == o_row['pattern'] and data.get('result') == dict(count=o_row['count'], id=result_id)
                and set(key) == set(o_row['key']) and all(ingredient_ok(key[k], v) for k, v in o_row['key'].items()))
    if kind == 'shapeless':
        return (data.get('type') == 'minecraft:crafting_shapeless' and data.get('result') == dict(count=o_row['count'], id=result_id)
                and shapeless_ok(data.get('ingredients'), o_row['ingredients']))
    return False


def norm_token(value):
    """A source token normalized for original-vs-NEO comparison: spaces and an F / D suffix after a digit dropped, the NEO constant Y_OFFSET read as the original local yOffset, lower case."""
    return re.sub(r'(?<=\d)[FfDd]\b', '', value.replace('Y_OFFSET', 'yOffset').replace(' ', '')).lower()


def sequence(text, regex):
    """Every match of the regex as the '|'-joined normalized groups, in source order (no de-duplication)."""
    return ['|'.join(norm_token(g) for g in m.groups()) for m in re.finditer(regex, text, re.S)]


def model_cubes(text, original):
    """The cubes of a model in source order as (texture offset, addBox arguments, rotation point, rotation angles), normalized. The original builds a ModelRenderer per cube and sets the rotation
    point and angle on it; NEO builds one PartDefinition per cube with PartPose.offsetAndRotation(point..., angle...)."""
    out = []
    if original:
        pattern = (r'new ModelRenderer\(this, (\d+, \d+)\);\s*(?:this\.)?(\w+)\.addBox\(([^)]*)\);\s*(?:this\.)?\2\.setRotationPoint\(([^;]*)\);.*?setRotation\((?:this\.)?\2, ([^)]*)\);')
        for m in re.finditer(pattern, text, re.S):
            out.append((norm_token(m.group(1)), tuple(norm_token(a) for a in split_args(m.group(3))), tuple(norm_token(a) for a in split_args(m.group(4))),
                        tuple(norm_token(a) for a in split_args(m.group(5)))))
    else:
        pattern = r'texOffs\((\d+, \d+)\)\.addBox\(([^)]*)\),\s*PartPose\.offsetAndRotation\(([^;]*?)\)\);'
        for m in re.finditer(pattern, text, re.S):
            pose = [norm_token(a) for a in split_args(m.group(3))]
            out.append((norm_token(m.group(1)), tuple(norm_token(a) for a in split_args(m.group(2))), tuple(pose[:3]), tuple(pose[3:])))
    return out


def statement(text, start_token):
    """The source statement beginning at start_token up to its terminating ';' (None when the token is missing)."""
    i = text.find(start_token)
    if i < 0: return None
    j = text.find(';', i)
    return text[i:j+1] if j > 0 else None


def assembly_row(text, original):
    """The ass.hazcloth row as comparable facts: (duration, power, output (item, count), inputs [(kind, item, count)])."""
    s = statement(text, 'new GenericRecipe("'+ASSEMBLY_ID+'")')
    if s is None: return None
    setup = re.search(r'\.setup\((\d+), (\d+)\)', s)
    if original:
        out = re.search(r'outputItems\(new ItemStack\(ModItems\.(\w+), (\d+)\)', s)
        inputs = [('item', ASSEMBLY_ORIGINAL_ITEMS[m.group(1)][1], int(m.group(2))) for m in re.finditer(r'new OreDictStack\(([\w.()]+), (\d+)\)', s) if m.group(1) in ASSEMBLY_ORIGINAL_ITEMS]
        inputs += [('vanilla', m.group(1).upper(), int(m.group(2))) for m in re.finditer(r'new ComparableStack\(Items\.(\w+), (\d+)\)', s)]
        orig_out = (out.group(1).upper(), int(out.group(2))) if out else None
    else:
        out = re.search(r'outputItems\(new ItemStack\(NtmItems\.(\w+)\.get\(\), (\d+)\)', s)
        inputs = [('item', m.group(1), int(m.group(2))) for m in re.finditer(r'new ComparableStack\(NtmItems\.(\w+)\.get\(\), (\d+)\)', s)]
        inputs += [('vanilla', m.group(1), int(m.group(2))) for m in re.finditer(r'new ComparableStack\(net\.minecraft\.world\.item\.Items\.(\w+), (\d+)\)', s)]
        orig_out = (out.group(1), int(out.group(2))) if out else None
    return dict(setup=[int(setup.group(1)), int(setup.group(2))] if setup else None, output=list(orig_out) if orig_out else None, inputs=sorted([list(i) for i in inputs]))


def recompile_equal(name, previous_bytes, new_bytes):
    """True when the previous class bytes, patched in one of the directions RECOMPILE_ONLY allows (every pattern occurring exactly once), equal the new class bytes: the class differs only in
    recompiled local-variable debug names."""
    for pairs in RECOMPILE_ONLY[name]:
        patched = previous_bytes
        if any(patched.count(a) != 1 for a, b in pairs): continue
        for a, b in pairs: patched = patched.replace(a, b)
        if patched == new_bytes: return True
    return False


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
    goal26b_start = read(GOAL26B_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal26C commits nothing), the recorded start: HEAD 8954b531 (the Goal 26 planning commit) on the
    # Goal 25 close-out commit, on the Goal 25 planning commit, on the pushed Goal 24 close-out commit, PLUS the uncommitted Goal26A and Goal26B deliveries and the two planning supplements (228 status lines).
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 26 planning commit'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 26 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    status_lines = base['target_status'].splitlines()
    assert len(status_lines) == START_STATUS_LINES and START_STATUS.read_text(encoding='utf-8').splitlines() == status_lines, \
        f'The frozen start is not the {START_STATUS_LINES} status lines of the uncommitted Goal26A and Goal26B deliveries plus the two planning supplements (baseline target_status / start_status.txt)'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal26b receipt records another original commit than the frozen start'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal26C (the Goal26A and Goal26B deliveries stay uncommitted until the Goal 26 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2, 3)}
    assert chain[1].startswith(GOAL25_CLOSEOUT) and chain[2].startswith(GOAL25_PLANNING) and chain[3].startswith(GOAL24_CLOSEOUT), \
        'NEO HEAD~1..3 are not the Goal 25 close-out 5b1bf4db, the Goal 25 planning 783b6d13 and the Goal 24 close-out 17c8062f commits: '+str(chain)
    assert set(base['start_content']) == {'committed', 'uncommitted'} and 'Goal26A and Goal26B deliveries' in base['start_content']['uncommitted'], 'Baseline start content differs'
    assert set(base['older_receipt_protected_paths']) == OLDER_RECEIPTS, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256_at_freeze'] == base['build_libs_jar_sha256_at_freeze'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_lines'] == len(status_lines) == startup['dirty_start_files'] \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'], \
        'startup-verification.json differs from baseline.json'
    start_stamp = start_json(base, STAMP)
    assert base['stamp_state']['generated_resources_recorded'] == prior_receipt['generated_resource_count'] == len(start_stamp['generated']) \
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal26b generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_start']

    # The uncommitted deliveries at the start: the 228 dirty start files (start_hashes.txt) are exactly the Goal26A and Goal26B receipts' changed files (the files both batches changed appear once)
    # plus the two planning-session supplements; each start hash is the newest receipt's after-hash that records the file (differences are recorded; only the shared records the main agent edits
    # after a package may differ).
    dirty = {}
    for line in START_HASHES.read_text(encoding='utf-8').splitlines():
        if line.strip():
            h, p = line.split(None, 1)
            dirty[p.strip().lstrip('*')] = h
    older_receipt = read(OLDER_RECEIPT)
    assert older_receipt['sha256'] == prior_receipt['base_release_sha256'], 'The goal26b receipt names another base package than the goal26a receipt'
    older_changed = {e['path']: e for e in older_receipt['changed_files']}
    prior_changed = {e['path']: e for e in prior_receipt['changed_files']}
    delivery_paths = set(older_changed) | set(prior_changed)
    both = sorted(set(older_changed) & set(prior_changed))
    assert not delivery_paths & set(PLANNING_SUPPLEMENTS), 'A planning supplement is in a delivery receipt: '+str(sorted(delivery_paths & set(PLANNING_SUPPLEMENTS)))
    assert set(dirty) == delivery_paths | set(PLANNING_SUPPLEMENTS) and len(dirty) == START_STATUS_LINES, \
        'The 228 dirty start files are not the goal26a and goal26b receipt changed files plus the two supplements: '+str(sorted(set(dirty) ^ (delivery_paths | set(PLANNING_SUPPLEMENTS)))[:6])
    assert all(base['files'].get(p) == h for p, h in dirty.items()), 'start_hashes.txt differs from the baseline hashes'
    dirty_owner = {p: PREVIOUS_OWNER if p in prior_changed else OLDER_OWNER if p in older_changed else PLANNING_OWNER for p in dirty}
    newest_after = {p: (prior_changed[p] if p in prior_changed else older_changed[p])['after_sha256'] for p in delivery_paths}
    delivery_differs = sorted(p for p, h in newest_after.items() if base['files'].get(p) != h)
    assert all(p in SHARED_AFTER_PACKAGE for p in delivery_differs), 'A Goal26A / Goal26B delivery file other than a shared record differs from its newest receipt after-hash at the Goal26C start: '+str(
        [p for p in delivery_differs if p not in SHARED_AFTER_PACKAGE])
    chain_differs = sorted(p for p in both if prior_changed[p]['before_sha256'] != older_changed[p]['after_sha256'])
    assert all(p in SHARED_AFTER_PACKAGE for p in chain_differs), 'A file both batches changed does not start the goal26b batch at the goal26a after-hash: '+str([p for p in chain_differs if p not in SHARED_AFTER_PACKAGE])

    def delivery(owner, receipt_path, changed):
        mine = sorted(p for p in dirty if dirty_owner[p] == owner)
        return dict(owner=owner, receipt=receipt_path.relative_to(ROOT).as_posix(), receipt_changed_files=len(changed), files_owned_at_start=len(mine),
                    equal_to_receipt_after_sha256=sum(1 for p in mine if base['files'].get(p) == changed[p]['after_sha256']),
                    shared_records_differing_from_receipt_after_sha256={p: dict(newest_receipt_after_sha256=newest_after[p], start_sha256=base['files'][p], current_sha256=sha(ROOT/p))
                                                                        for p in delivery_differs if p in mine})
    goal26a_delivery = dict(delivery(OLDER_OWNER, OLDER_RECEIPT, older_changed), also_changed_by_goal26b=len(both),
                            note='Files only the Goal26A batch changed are owned by goal26a (package build/migration/releases/goal26a); a file both batches changed is owned by goal26b at this start.')
    goal26b_delivery = dict(delivery(PREVIOUS_OWNER, PREVIOUS_RECEIPT, prior_changed), files_also_changed_by_goal26a=len(both), before_sha256_differing_from_goal26a_after_sha256=chain_differs,
                            note='The Goal26B delivery is uncommitted at this start (the user rule commits 26A-26D together after the Goal 26 unified acceptance); its files are owned by goal26b '
                                 '(package build/migration/releases/goal26b). A path both batches change records the newest delivery as before_sha256.')
    planning_supplements = {p: dict(owner=PLANNING_OWNER, start_sha256=base['files'][p], current_sha256=sha(ROOT/p),
                                    note='Planning-session supplement of 2026-10-22, uncommitted at the start, in no receipt. '+('GOAL26C.md is also this batch task book and delivery record (hashed by the new receipt).'
                                                                                              if p == 'migration/GOAL26C.md' else 'Must equal its start hash.')) for p in PLANNING_SUPPLEMENTS}

    # 2. Previous deliveries: the goal26b package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the start is not the goal26b package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal26b receipt list + the goal26b package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal26b receipt count + the goal26b release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal26b receipt'
    assert not base['previous_receipt_evidence_drift'], 'The goal26b receipt records evidence drift at the start: '+str(list(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal26b_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal26b receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal26c. Everything else equals its start hash.
    changes = changed_since_start(base)
    older_gametests = sorted(p for p in changes if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p in base['files'] and p not in UNCHANGED_JAVA)
    modified_java = MODIFIED_JAVA + OPTIONAL_JAVA + older_gametests
    production_java = NEW_JAVA + modified_java
    unassigned = sorted(p for p in changes if group(p, base) is None)
    need(not unassigned, f'Path changed since the Goal26C start that the owner table does not list (production outside the {len(MODIFIED_JAVA)} modified Java files, the {len(NEW_JAVA)} new classes incl. '
         f'HazmatSuitGameTests, the {len(ASSETS)} resources, zh_cn.json and the mapping, a protected or frozen record, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal26A / Goal26B / Goal25 / Goal24 records or the Goal 26D planning documents changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal26C start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD] + GENERATED + SHARED_RECORDS + REPORTS[:1]:
        if p in OPTIONAL_RECORDS and p not in base['files']: continue
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION + production_java if p.startswith('src/')})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified and {len(NEW_JAVA)} new Java files, the {len(ASSETS)} resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    goal26_now = sha(ROOT/GOAL26_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository. The batch ran under the main agent with a builder, a '
                                               'GameTest verifier (HazmatSuitGameTests, verify_goal26c_hazmat.py, the old-suite revival, Gradle), this packaging verifier and a read-only reviewer; each wrote only '
                                               'its named files (scope-before / scope-after snapshots of the verifiers are indexed as evidence). The main agent edited migration/ records, zh_cn.json and the '
                                               'mapping and applied any review fixes. migration/GOAL26.md and GOAL26C.md are edited by the main agent of this batch; the planning session of 2026-10-22 had edited '
                                               'GOAL26C.md and GOAL26-THREAD-PROMPTS.md before the start (planning-2026-10-22 owns those start bytes).',
                             goal26_md=dict(start_sha256=base['files'][GOAL26_RECORD], current_sha256=goal26_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p)) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p, base), owner=OWNER, owners=[OWNER], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p),
                        before_owner=dirty_owner.get(p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal26C takes no new snapshot)'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-aee05a40f10f snapshot changed'
    production_changed = [p for p in PRODUCTION + production_java if p in changes]

    # The modified production files keep their start line endings; new Java files are not mixed.
    start_text = {}
    for p in modified_java + [ZH_INPUT, LOCALIZATION_RECORD]:
        if p not in changes: continue
        data = start_bytes(base, p)
        if not need(data is not None, p+' has no reproducible start bytes (not in baseline-files and the start-commit blob does not match the baseline hash)'): continue
        start_text[p] = data
        start_eol, eol = eol_counts(data), eol_counts((ROOT/p).read_bytes())
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}')
    for p in NEW_JAVA:
        if (ROOT/p).is_file():
            eol = eol_counts((ROOT/p).read_bytes())
            need(eol[0] == 0 or eol[1] == 0, f'{p} mixes CRLF and LF line endings: {eol}')

    # Production Java facts: insert-only registration files, every line edit counted, the removed lines of the edited files accounted for.
    insert_summary, edit_summary, inserted_lines, added_lines, removed_lines, removed_comments, removed_code = {}, {}, {}, {}, {}, {}, {}
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
        elif p in ALLOWED_REMOVED_CODE or p in older_gametests:
            allowed = ALLOWED_REMOVED_CODE.get(p, OLDER_GAMETEST_REMOVABLE)
            # Compared stripped: re-indented lines cancel out; what is left was really removed.
            net_removed = list((Counter(l.strip() for l in start_lines) - Counter(l.strip() for l in live_lines)).elements())
            comments = [l for l in net_removed if is_comment(l)]
            code = [l for l in net_removed if not is_comment(l)]
            exact = Counter(ALLOWED_REMOVED_EXACT.get(p, ()))
            stray = []
            for l in code:
                if allowed and l.startswith(allowed): continue
                if exact[l] > 0:
                    exact[l] -= 1
                    continue
                stray.append(l)
            need(not stray, f'{p} removes start code lines the owner table does not allow: {[l[:90] for l in stray[:4]]}')
            removed_comments[p] = [l for l in comments if l]
            removed_code[p] = code
        else:
            need(False, f'{p} is neither in STRICT_INSERT_ONLY nor in ALLOWED_REMOVED_CODE (owner table gap)')
    # Language provider: the added lines carry exactly the new keys (items through their constants, plain keys); nothing is removed.
    provider_added = []
    if PROVIDER in added_lines:
        keys_added, other = base_provider_keys(added_lines[PROVIDER])
        provider_added = sorted(keys_added)
        stray = [l for l in other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} adds lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(keys_added) == len(set(keys_added)), f'{PROVIDER} adds a language key twice')
        need(provider_added == sorted(KEYS), f'{PROVIDER} adds the language keys differently than expected: missing {sorted(set(KEYS) - set(provider_added))[:6]}, unexpected {sorted(set(provider_added) - set(KEYS))[:6]}')
        need(not base_provider_keys(removed_lines[PROVIDER])[0], f'{PROVIDER} removes language entries: {base_provider_keys(removed_lines[PROVIDER])[0][:4]}')
    # Added-code rules: the registry rows and the one HAZMAT branch are the only code the batch adds to HazmatRegistry and ContaminationUtil, each inside its one method (the import excepted).
    added_code_facts = {}
    for p, rule in ADDED_CODE_RULES.items():
        if p not in start_text: continue
        live_lines = lines_of((ROOT/p).read_bytes())
        inserted = insertions(lines_of(start_text[p]), live_lines)
        if inserted is None: continue
        code_lines = [(j, l.strip()) for j, l in inserted if not is_comment(l)]
        stray = [l for _, l in code_lines if not rule.fullmatch(l)]
        need(not stray, f'{p} adds code lines the owner table does not allow (only the batch rows / branch): {[l[:90] for l in stray[:4]]}')
        marker = ADDED_CODE_METHODS[p]
        first = next((k for k, l in enumerate(live_lines) if marker in l), None)
        span = None
        if first is not None:
            indent = len(live_lines[first]) - len(live_lines[first].lstrip())
            last = next((k for k in range(first + 1, len(live_lines)) if live_lines[k].rstrip() == ' '*indent + '}'), None)
            span = (first, last)
        outside = [j + 1 for j, l in code_lines if not l.startswith('import ') and (span is None or span[1] is None or not span[0] < j < span[1])]
        need(span is not None and span[1] is not None and not outside, f'{p} adds code outside the method {marker} (line numbers {outside[:6]})')
        added_code_facts[p] = dict(method=marker, added_code_lines=len(code_lines), method_lines=[span[0] + 1, span[1] + 1] if span and span[1] is not None else None)
    # No caller passes ContaminationType.HAZMAT, in the original (statically: the only reference is the enum itself and the switch case) or in NEO (except the GameTests): the branch is not reachable in game.
    hazmat_type_callers = sorted(p for p in tree_files('src/main/java') if p.endswith('.java') and p != CONTAMINATION and not p.startswith(OLDER_GAMETEST_DIR)
                                 and re.search(r'ContaminationType\.HAZMAT(?![\w])', (ROOT/p).read_text(encoding='utf-8', errors='replace')))
    need(not hazmat_type_callers, 'NEO classes outside ContaminationUtil and the GameTests pass ContaminationType.HAZMAT (the branch is documented as not reachable yet): '+str(hazmat_type_callers))
    o_grep = subprocess.run(['git', '--no-optional-locks', '-c', 'safe.directory='+SOURCE.as_posix(), 'grep', '-l', '-E', r'ContaminationType\.HAZMAT([^A-Za-z0-9_]|$)', SOURCE_HEAD, '--', 'src/main/java'], cwd=SOURCE, capture_output=True)
    o_callers = sorted(l.split(':', 1)[1] for l in o_grep.stdout.decode('utf-8').split() if l.split(':', 1)[1] != O_CONTAM)
    assert o_grep.returncode in (0, 1) and not o_callers, 'The original passes ContaminationType.HAZMAT outside ContaminationUtil (KNOWN_DIFFERENCES hazmat_branch says it does not): '+str(o_callers)
    # The original, parsed from the stored blobs at the recorded commit (independent of the worktree's line endings).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    neo_text = lambda path: (ROOT/path).read_text(encoding='utf-8').replace('\r\n', '\n') if (ROOT/path).is_file() else ''
    # NEO constants against the original (rags material, durabilities, blacklists, overlay frames, worn textures, model constants, rag, sound).
    constants, constants_bad = {}, []
    for cid, (o_path, o_regex, n_path, n_regex, expected, *neo_expected) in CONSTANTS.items():
        o_values = captured(original_text(o_path), o_regex) if o_path else None
        n_values = captured(neo_text(n_path), n_regex) if (ROOT/n_path).is_file() else None
        if o_path: assert o_values == [normalize_value(str(e)) for e in expected] or o_values == expected, \
            f'The original constant {cid} ({o_path}) is {o_values}, the owner table expects {expected}'
        wanted = [normalize_value(str(e)) for e in neo_expected[0]] if neo_expected else (o_values if o_path else [normalize_value(str(e)) for e in expected])
        constants[cid] = dict(original=o_values, neo=n_values, original_path=o_path, neo_path=n_path, **(dict(neo_expected=wanted) if neo_expected or not o_path else {}))
        if n_values != wanted: constants_bad.append(cid)
    need(not constants_bad and all(c['neo'] is not None for c in constants.values()),
         f'NEO constants differ from the original (or the NEO source is missing / its text differs from the handoff): {sorted(set(constants_bad) | {k for k, c in constants.items() if c["neo"] is None})}')
    # Sequences: every match in source order (the nine protection-class lines, the blacklists, the overlay frames, the worn textures), original against NEO, sorted unless the order is part of the
    # fact; the counts are those of the original.
    sequences, sequences_bad = {}, []
    for sid, (o_path, o_regex, n_path, n_regex, count, *neo_expected) in SEQUENCES.items():
        o_seq = sequence(original_text(o_path), o_regex)
        n_seq = sequence(neo_text(n_path), n_regex) if (ROOT/n_path).is_file() else None
        assert len(o_seq) == count, f'The original sequence {sid} ({o_path}) has {len(o_seq)} matches, the owner table expects {count}'
        wanted = [norm_token(w) for w in neo_expected[0]] if neo_expected else o_seq
        sequences[sid] = dict(original=sorted(o_seq), neo=sorted(n_seq) if n_seq is not None else None, original_path=o_path, neo_path=n_path, count=count, **(dict(neo_expected=sorted(wanted)) if neo_expected else {}))
        if n_seq is None or sorted(n_seq) != sorted(wanted): sequences_bad.append(sid)
    need(not sequences_bad, f'NEO sequences differ from the original (or the NEO source is missing / its text differs from the handoff): {sequences_bad}')
    # Model cubes: texture offset, box, rotation point and angles of every cube in source order against the original model.
    cubes, cubes_bad = {}, []
    for mid, (o_path, n_path, count) in MODEL_CUBES.items():
        o_cubes = model_cubes(original_text(o_path), True)
        n_cubes = model_cubes(neo_text(n_path), False) if (ROOT/n_path).is_file() else None
        assert len(o_cubes) == count, f'The original model {mid} ({o_path}) has {len(o_cubes)} cubes, the owner table expects {count}'
        cubes[mid] = dict(original=jsonable(o_cubes), neo=jsonable(n_cubes) if n_cubes is not None else None, original_path=o_path, neo_path=n_path, count=count)
        if n_cubes != o_cubes: cubes_bad.append(mid)
    need(not cubes_bad, f'NEO model cubes differ from the original (or the NEO source is missing / its text differs from the handoff): {cubes_bad}')
    # Occurrence counts in the NEO texts (the corrected forms present, the registrations once each) against the original counts where the original has the same line.
    counts, counts_bad = {}, []
    for cid, (n_path, n_regex, expected, *original) in COUNTS.items():
        n_count = len(re.findall(n_regex, neo_text(n_path))) if (ROOT/n_path).is_file() else None
        entry = dict(neo=n_count, expected=expected, neo_path=n_path)
        if original:
            o_path, o_regex, o_expected = original
            o_count = len(re.findall(o_regex, original_text(o_path)))
            assert o_count == o_expected, f'The original count {cid} ({o_path}) is {o_count}, the owner table expects {o_expected}'
            entry.update(original=o_count, original_path=o_path)
        counts[cid] = entry
        if n_count != expected: counts_bad.append(cid)
    need(not counts_bad, f'NEO occurrence counts differ from the owner table (or the NEO source is missing / its text differs from the handoff): {counts_bad}')
    # The assembly row ass.hazcloth against the original row (setup, output, inputs).
    asm_original = assembly_row(original_text(O_ASSEMBLY), True)
    asm_neo = assembly_row(neo_text(ASSEMBLY), False)
    assembly = dict(original=asm_original, neo=asm_neo, original_reference=original_refs['assembly_hazcloth'], expected=ASSEMBLY_EXPECTED)
    assert asm_original == ASSEMBLY_EXPECTED, f'The original row ass.hazcloth is {asm_original}, the owner table expects {ASSEMBLY_EXPECTED}'
    need(asm_neo is not None and asm_original is not None and asm_neo['setup'] == asm_original['setup'] and asm_neo['output'] == asm_original['output'] and asm_neo['inputs'] == asm_original['inputs'],
         f'ass.hazcloth in {ASSEMBLY} differs from the original row (AssemblyMachineRecipes.java:118-119): neo {asm_neo}, original {asm_original}')
    # Logical sides: the common classes import nothing from net.minecraft.client and never name the client extension, the models or the render package.
    client_refs = {p: bool((ROOT/p).is_file() and CLIENT_ONLY_NAMES.search(strip_java_comments(neo_text(p)))) for p in COMMON_CLASSES}
    need(not any(client_refs.values()) and all((ROOT/p).is_file() for p in COMMON_CLASSES), 'common-side classes are missing or reference client-only classes: '+str(sorted(p for p, v in client_refs.items() if v)))
    unchanged_bad = [p for p in UNCHANGED_JAVA if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed: '+str(unchanged_bad))
    # Recipes: the 14 crafting / smelting recipes (computed from the generated JSON) against the original rows.
    crafting = {}
    recipe_dir = GENERATED_ROOT+'data/hbmsntm/recipe/'
    for rid, (kind, o_path, selector, result_id) in RECIPES.items():
        path = ROOT/(recipe_dir+rid+'.json')
        o_row = original_recipe(original_text(ORIGINAL+o_path), kind, selector)
        assert o_row is not None, f'The original row of {rid} ({o_path}) is not unique or does not parse: {selector}'
        if kind != 'smelting':
            assert all(v is not None for v in (o_row['key'].values() if kind == 'shaped' else o_row['ingredients'])), f'The original row of {rid} has a key expression missing from KEY_TABLE: {jsonable(o_row)}'
        if not path.is_file():
            need(False, 'generated recipe missing: '+recipe_dir+rid+'.json')
            continue
        data = read(path)
        if kind == 'smelting':
            wanted = dict(type='minecraft:smelting', ingredient={'item': SMELT_INPUTS[rid][1]}, result=dict(count=1, id=result_id), experience=o_row['experience'], cookingtime=200)
            ok = all(data.get(k) == v for k, v in wanted.items()) and o_row['result'] == result_id.split(':')[1]
            neo_row = {k: data.get(k) for k in wanted}
        else:
            ok = recipe_matches(kind, data, o_row, result_id)
            neo_row = {k: data.get(k) for k in (('pattern', 'key', 'result') if kind == 'shaped' else ('ingredients', 'result'))}
        crafting[rid] = dict(kind=kind, type=data.get('type'), category=data.get('category'), neo=neo_row, original=jsonable(o_row), original_reference=original_refs.get(RECIPE_REFS.get(rid, ''), None), matches=ok)
        need(ok, f'{recipe_dir}{rid}.json differs from the original row: {neo_row} vs {jsonable(o_row)}')
    # Imported resources: byte for byte equal to the original worktree file and its stored blob, and to the ownership record.
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
        need(checked_out == blob, f'{target} is not byte-identical to the stored blob of {original} at {SOURCE_HEAD[:8]}')
        if entry:
            need(entry.get('blob_sha256') == hashlib.sha256(blob).hexdigest(), f'{RESOURCE_OWNERSHIP} blob_sha256 differs from the stored blob: {target}')
            need(entry.get('source_path') == original and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('bytes') == (ROOT/target).stat().st_size,
                 f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original path: {target}')
    # features.json: the new group, the unchanged status and reviewed_source_commit of the previous groups.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES <= set(start_features) and not set(NEW_FEATURES) & set(start_features), \
        'The start mapping does not hold the groups of 24B-26A (rbmk-fuel ... radiation-detection) and not yet the Goal26C group'
    new_groups = {g: by_id[g] for g in NEW_FEATURES if g in by_id}

    # 4. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = start_json(base, EN), read(ROOT/EN)
    zh_start, zh_now = start_json(base, ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = start_json(base, LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_en = dict(added=sorted(KEYS), removed=[], changed=[])
    expected_zh = dict(added=sorted(KEYS), removed=[], changed=[])
    expected_map = dict(added=sorted(KEYS), removed=[], changed=[])
    need(en_delta == expected_en, f'generated en_us.json delta is not the {len(KEYS)} new keys (no value changed): '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_zh, f'zh_cn.json delta is not the {len(KEYS)} new keys (all old values unchanged): '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_map, f'zh_cn-map.json delta is not the {len(KEYS)} new entries (no old entry changed): '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal26b totals'
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal26b totals {totals} + {len(KEYS)}')
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
    start_generated = start_stamp['generated']
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal26b generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    advancements = sorted(p for p in generated_added if any(a.fullmatch(p) for a in ADVANCEMENT.values()))
    wanted_advancements = {r for r in RECIPE_IDS}
    found_advancements = {r for r, a in ADVANCEMENT.items() if [p for p in advancements if a.fullmatch(p)]}
    EXPECTED_GENERATED = sorted(EXPECTED_GENERATED_BASE + advancements)
    need(found_advancements == wanted_advancements and len(advancements) == len(RECIPE_IDS), 'The generated advancements are not exactly one per recipe (%d): missing %s, found %d' % (
        len(RECIPE_IDS), sorted(wanted_advancements - found_advancements)[:6], len(advancements)))
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected item model, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # The six enchantable item tags (ARMOR ENCHANTABILITY block of NtmItemTagProvider): exactly the listed items, not replacing, the slot tags (head_armor etc.) untouched.
    tag_facts = {}
    for name, rel in TAG_FILES.items():
        path = GENERATED_ROOT+rel
        live = read(ROOT/path) if (ROOT/path).is_file() else None
        tag_facts[name] = dict(path=path, replace=live.get('replace') if live else None, values=live.get('values') if live else None)
        need(live is not None and live.get('replace', False) is False and sorted(live.get('values', [])) == sorted(ENCHANT_TAGS[name]),
             f'generated {path} is not the enchantable tag listing exactly {len(ENCHANT_TAGS[name])} items (not replacing): {live}')
    # The generated item models: the generated parent on the item texture of the same name (and the texture exists).
    generated_facts = {}
    for n in ITEM_ICONS:
        im = GENERATED_ROOT+f'assets/hbmsntm/models/item/{n}.json'
        live = read(ROOT/im) if (ROOT/im).is_file() else None
        generated_facts[n] = dict(item_model=live, texture_exists=(ROOT/(ASSETS_ROOT+f'textures/item/{n}.png')).is_file())
        need(live == {'parent': 'minecraft:item/generated', 'textures': {'layer0': f'hbmsntm:item/{n}'}}, f'generated {im} is not the generated-parent model on hbmsntm:item/{n}: {live}')
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
        if rel in base['files']:
            data = start_bytes(base, rel)
            assert data is not None, 'No reproducible start bytes for '+rel
            total_start += len(GAMETEST_ANNOTATION.findall(data.decode('utf-8')))
    assert total_start == prior_receipt['gametest']['tests'], 'The start GameTest sources do not hold the previous count of '+str(prior_receipt['gametest']['tests'])
    gametest_added = total_now - total_start
    gametest_expected = total_now
    hazmat_test_names = sorted(GAMETEST_METHOD.findall((ROOT/HAZMAT_TESTS).read_text(encoding='utf-8'))) if (ROOT/HAZMAT_TESTS).is_file() else []
    hazmat_annotations = annotations(ROOT/HAZMAT_TESTS) if (ROOT/HAZMAT_TESTS).is_file() else 0
    need(bool(hazmat_test_names) and hazmat_annotations == len(hazmat_test_names), f'{HAZMAT_TESTS} holds {hazmat_annotations} @GameTest annotations and {len(hazmat_test_names)} parsed methods')
    need(gametest_added == hazmat_annotations, f'GameTest sources grew by {gametest_added} tests, HazmatSuitGameTests holds {hazmat_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in hazmat_test_names), 'GameTest log lacks "[hbm-gas-mask] <name> passed" for: '+str([n for n in hazmat_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal26c/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal26c/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal26c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal26c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal26c/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in modified_java if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal26c/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in modified_java if p in changes) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal26b final run plus the Goal26C verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1 + len(EXTRA_FINAL_SUITES)
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal26b final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal26C suite is already in the goal26b final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal26c/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE} | EXTRA_FINAL_SUITES, 'Final run suites differ from the goal26b final set + the Goal26C verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE} | EXTRA_FINAL_SUITES))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal26c/'+VERIFY_REPORT+' (tools/migration/verify_goal26c_hazmat.py report)'):
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
        verifier_references = sorted(set(re.findall(r'(?:HazmatRegistry|ArmorUtil|ContaminationUtil|ArmorHazmatMask|ArmorHazmat|MainRegistry|ModItems|ArmorRecipes|CraftingManager|'
                                                      r'AssemblyMachineRecipes)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        # The verifier ran against the final GameTest log and expected the sources' total.
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal26b compare target paths (which hold the 24A-26A paths) plus this batch's compare-inventory paths).
    cmp26a = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal26b/compare.json differs from the goal26b receipt'
    c26a_added = sorted(p for p in compare_paths(cmp26a['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c26a_modified = sorted(p for p in compare_paths(cmp26a['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(c26a_added) | set(c26a_modified) | set(own_target))
    expected_added = sorted(set(c26a_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal26c/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-26a paths + %d of this batch)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(c26a_added) + len(c26a_modified), len(own_target))):
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
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal26b (goal26b compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal26b_paths=len(c26a_added) + len(c26a_modified), goal26c_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the groups of 24B-26A.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-26A)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal26c.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal26b) package (run the final build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the imported resources and every compiled class equal the sources.
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
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY, 'META-INF/MANIFEST.MF'): owner = [OWNER]
                elif kind == 'added' and (n in asset_entries or n in generated_entries): owner = [OWNER]
                elif kind == 'modified' and n in recompile_only and owner_class(n) not in changes: owner = [RECOMPILE_OWNER]
                if not owner: unowned.append(f'{kind}: {n}' + (' [source ' + owner_class(n) + ' unchanged since the start: a recompile difference, not a source change]' if n.endswith('.class') and owner_class(n) not in changes else ''))
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the imported resources, the generated additions and '
             'the modified en_us.json / zh_cn.json / sounds.json / MANIFEST.MF are owned): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in production_java if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA),
             'Changed Java sources and goal26c JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + generated additions: extra %s, missing %s' % (
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

    # 7. Records: the release name and the batch reports.
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    for p in unnamed: need(False, 'record does not name '+RELEASE_NAME+': '+p)
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS:
        if p not in OPTIONAL_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p
    # Informational (not a pending item): top-level OUT files no evidence list indexes, for the main agent to extend REVIEW_EVIDENCE with.
    indexed = {Path(p).relative_to(OUT.relative_to(ROOT)).as_posix() for p in evidence if p.startswith(OUT.relative_to(ROOT).as_posix()+'/')}
    unindexed = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in indexed and p.name != 'baseline.json')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added),
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal26b_start=sorted(repinned),
                   delivery_files=dict(goal26a_and_goal26b=len(delivery_paths), only_goal26a=len(older_changed) - len(both), only_goal26b=len(prior_changed) - len(both), both=len(both), planning_supplements=len(PLANNING_SUPPLEMENTS)),
                   delivery_shared_records_differing=delivery_differs, older_gametests_changed=older_gametests, added_code=added_code_facts, enchantable_tags=sorted(tag_facts),
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, removed_comment_lines={p: len(v) for p, v in removed_comments.items()},
                   constants={k: c['neo'] == c.get('neo_expected', c['original']) for k, c in constants.items()}, sequences={k: v['neo'] == sorted(v.get('neo_expected', v['original'])) for k, v in sequences.items()},
                   model_cubes={k: v['neo'] == v['original'] for k, v in cubes.items()}, counts={k: c['neo'] == c['expected'] for k, c in counts.items()},
                   recipes={k: v['matches'] for k, v in crafting.items()}, assembly=assembly, client_refs_in_common_classes=sorted(p for p, v in client_refs.items() if v),
                   gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_hazmat_tests=hazmat_test_names, final_suites_expected=final_expected,
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
    hazmat_suits = dict(neo=[p for p in NEW_JAVA + MODIFIED_JAVA], original=[p for p in O_SOURCES], constants=constants, sequences=sequences, model_cubes=cubes, counts=counts,
                        known_differences=KNOWN_DIFFERENCES, recipes=crafting, assembly=assembly, generated_item_models=generated_facts, enchantable_tags=tag_facts, added_code=added_code_facts,
                        contamination_type_hazmat_callers=dict(neo=hazmat_type_callers, original=o_callers), original_references=original_refs,
                        defaults=dict(durability_factor=60, durability_per_slot=DURABILITY, defense_helmet_first='2 / 5 / 4 / 1', enchantability=5, part_factors=PART_FACTORS, suit_values=SUIT_VALUES,
                                      gas_mask_values=dict(gas_mask=0.07, gas_mask_m65=0.095), dose_coefficient=10, dose_factors_by_tier=DOSE_FACTORS, default_table_rows='8 -> 22',
                                      assembly='ass.hazcloth 50 ticks, 100 HE/t, powder_lead x4 + string x8 -> hazmat_cloth x4', recipes='12 armor pieces + the red and grey cloths'),
                        note='The twelve suit pieces are ArmorHazmat / ArmorHazmatMask on the HBM_HAZMAT materials (60 * the vanilla slot factor = 660 / 960 / 900 / 780 durability, defense 2 / 5 / 4 / 1 helmet '
                             'first, enchantability 5, repaired with the tier cloth); HazmatRegistry gets 12 suit rows (part factors 0.2 / 0.4 / 0.3 / 0.1 times 0.6 / 1.0 / 2.0) and the gas_mask 0.07 / '
                             'gas_mask_m65 0.095 rows (default table 8 -> 22 rows; an existing custom hbmRadResist.json still replaces the whole table); ArmorUtil.checkForHazmat accepts the three '
                             'full sets or the MUTATION effect and the HAZMAT contamination branch returns before the creative exemption; the three helmets take gas-mask filters (empty blacklist, '
                             'shared eject helper); the red and grey helmets use the 26B M65 model, the yellow helmet draws overlay_hazmat.png; the 18 armor items are tagged into minecraft:enchantable/* '
                             'instead of the trimmable slot tags. Not migrated or deferred: the hazmat kits, the PaA suit, the liquidator / PaA / security / starmetal / steel registry rows, the '
                             'asbestos cloth, checkForHaz2, FARADAY / HAZMAT_HEAVY / DIGAMMA contamination, and any caller of ContaminationType.HAZMAT (neither side has one), client rendering (GameTest cannot render).')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), len(ASSETS), len(hazmat_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=start_head[:8],
                   uncommitted_start=dict(status_entries=len(status_lines), description='the uncommitted Goal26A and Goal26B deliveries and the 2026-10-22 planning supplements on the Goal 26 planning commit 8954b531',
                                          base_release=previous_rel, status=status_lines,
                                          note=f'The start tree is HEAD 8954b531 plus the uncommitted Goal26A delivery ({len(older_changed)} files, packaged as goal26a) and the uncommitted Goal26B delivery ({len(prior_changed)} files, '
                                               f'packaged as goal26b; {len(both)} files changed by both batches, {len(delivery_paths)} distinct) and the two planning supplements to migration/GOAL26C.md and '
                                               f'migration/GOAL26-THREAD-PROMPTS.md ({len(status_lines)} status lines); every tracked file and every untracked start file was hashed live before the first 26C write (freeze_start.py).'),
                   goal26a_delivery=goal26a_delivery, goal26b_delivery=goal26b_delivery, planning_supplements=planning_supplements,
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, build_libs_sha256_at_freeze=base['build_libs_jar_sha256_at_freeze'],
                                      reconstruction=base['reconstruction'], goal25_closeout_commit=chain[1], goal25_planning_commit=chain[2], goal24_closeout_commit=chain[3],
                                      note=f'The start tree is HEAD 8954b531 (the Goal 26 planning commit, local, not pushed) on top of the Goal 25 close-out commit 5b1bf4db on the Goal 25 planning '
                                           f'commit 783b6d13 on the pushed Goal 24 close-out commit 17c8062f, PLUS the uncommitted Goal26A and Goal26B deliveries and the two planning supplements ({len(status_lines)} '
                                           f'status lines). build/libs at the start AND at the freeze IS the goal26b package. The original did not move since 24A (aee05a40f). freeze_start.py hashed every '
                                           f'tracked and untracked start file live ({len(base["files"])} baseline hashes) before the first 26C write and copied the dirty start files and the files the batch '
                                           f'planned to touch ({len(base["copied_scope"])} baseline-files); paths this batch changes record the start hash as before_sha256 and their before_owner (goal26a / goal26b for the '
                                           f'delivery files, planning-2026-10-22 for the two supplements).'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes], older_gametests_changed=older_gametests,
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, removed_comment_lines=removed_comments, removed_code_lines=removed_code, start_copies_supplement=[],
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   hazmat_suits=hazmat_suits,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note=f'{EXPECTED_KINDS.get("upstream", 0)} entries are upstream with the original English and Chinese verbatim (the fifteen hazmat item names, original '
                                      f'en_US.lang:3029-3049 / zh_CN.lang:2593-2613 without the kits and the PaA suit); {EXPECTED_KINDS.get("local", 0)} are local. No existing key changes its English '
                                      'value; no deferred entry is added.'),
                   recipes=dict(assembly=assembly, crafting=crafting, not_registered=[],
                                note='Fourteen crafting recipes (twelve armor pieces from ArmorRecipes, the red and grey cloths from CraftingManager; each generated JSON equal to its parsed original row) and '
                                     'the assembly machine row ass.hazcloth (equal to AssemblyMachineRecipes.java:118-119; PB.dust() is powder_lead in NEO).'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith('repinned_since_')},
                   repinned_since_goal26b_start={p: dict(goal26b_start_pin_sha256=h, goal26c_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_hazmat_tests=hazmat_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per HazmatSuitGameTests test (names in new_hazmat_tests): what those tests '
                                      'assert about the hazmat items, registry rows, checkForHazmat, the contamination branch and the recipes; no client (worn models, overlay, tooltips, creative tabs are not '
                                      'rendered), no real player, no saved world, no survival chain.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['gas_masks (the Goal26B-only key; Goal26C adds hazmat_suits; the gas-mask constants, protection classes, model cubes and sound facts are not carried)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. No in-game client test was run: '
                            'the worn hazmat armor and the M65-model hoods, the yellow hood overlay, the tooltips and Chinese UI, the item icons, the creative tabs, JEI, enchanting and smithing on '
                            'screen and the Geiger / dosimeter readouts are unverified; no survival chain (crafting a suit, wearing it in a radiation field) in a world was run; no multiplayer or '
                            'dedicated server beyond GameTest; the HAZMAT contamination branch is covered by GameTest only (no gameplay path passes HAZMAT yet); GOAL26C-ACCEPTANCE.md (the '
                            'real-game checklist) is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal26c JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal26b package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
