"""Package Goal26D (the fourth batch of Goal 26, radiation medicine: the Rad-X and SiOX pills (PillItem), RadAway, the IV bag and the blood bag (SimpleConsumableItem), the potionSickness common config key
(default OFF) with its NtmConfig helpers, the two sound events item.syringe and item.radaway, four crafting recipes (SiOX needs bismuth: unreachable), 7 imported resources, 7 language keys,
RadiationMedicineGameTests and the written Goal 26 unified acceptance checklist), cumulatively on the goal26c package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal26d.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal26d/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal26d/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal26d/baseline.json: NEO HEAD 8954b531 (the Goal 26 planning commit, local, parent 5b1bf4db = the Goal 25 close-out commit) PLUS the uncommitted Goal26A, Goal26B and
Goal26C deliveries (packaged as goal26a, goal26b and goal26c) PLUS the planning session's 2026-10-22 supplements to migration/GOAL26D.md and migration/GOAL26-THREAD-PROMPTS.md (316 status lines with
--untracked-files=all): freeze_start.py hashed every tracked file and every untracked start file live (10,537 hashes) before the first 26D write and copied every dirty start file and the files the batch planned
to touch (322 copies in baseline-files/); start_status.txt, start_head.txt and start_hashes.txt (the 316 dirty files) record it. build/libs at the start AND at the freeze IS the goal26c package (baseline
build_libs_jar_sha256_at_start / _at_freeze). The original HEAD aee05a40f did not move since 24A, so there is no upstream classification and no new snapshot. Nothing was committed between the goal26c package
and this start: HEAD must still be 8954b531 and there is no close-out owner. The Goal26A / Goal26B / Goal26C delivery files are owned by goal26a / goal26b / goal26c: their start bytes are the newest receipt's
after-hashes where a receipt records them (asserted; every difference is reported, the shared records the main agent edited after a package are the expected ones); the two supplement files belong to the planning
owner planning-2026-10-22-26d (no receipt hashes them; GOAL26-THREAD-PROMPTS.md must equal its start hash, GOAL26D.md is the task book and delivery record of this batch and hashed by the new receipt). Every change
since the start is computed from the baseline file hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with
their start bytes (baseline-files, else the start-commit blob). The JAR delta against the goal26c package is attributed per entry (goal26d only); any entry without exactly one owner fails. Counts that records
quote (suites, GameTests, generated resources, classes, releases, language keys) are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the files and the
baseline.

The receipts that hash records (goal21a..goal26c, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start for the acceptance checklists, GOAL21D.md, GOAL22C.md,
goal21d-static-review.md, the goal24a working notes and migration/GOAL25D-ACCEPTANCE.md; they are listed in the receipt as start drift and must still equal their Goal26D start hash; no receipt is rewritten
and no other protected path may drift (the goal26c receipt records no drift of its own: previous_receipt_evidence_drift is empty). The Goal26A, Goal26B, Goal26C, Goal25 and Goal24 records and
GOAL26-THREAD-PROMPTS.md and SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL26.md is edited by the main agent (a shared record), GOAL26D.md is the task book and delivery record (hashed
by the receipt) and GOAL26D-ACCEPTANCE.md the Goal 26 unified acceptance checklist (hashed, written, not run; GOAL25D-ACCEPTANCE.md is only referenced by it, never edited).

Like the earlier packagers of 24B..26C this one has a single compare run (build/migration/goal26d/compare.json against the snapshot review-aee05a40f10f.json taken at the end of 24A: original 0/0/0,
target = exactly the goal26c compare target paths (24A-26C, read from build/migration/goal26c/compare.json) plus this batch's compare-inventory paths), no upstream classification; it adds the radiation_medicine
constants (checked against the original and NEO source texts, the recipes against the parsed original rows). The Goal26C-only receipt key hazmat_suits is dropped."""
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
from package_goal26c import OUT as GOAL26C_OUT, BASELINE as GOAL26C_BASELINE, protected_paths as goal26c_protected_paths

OUT = ROOT/'build/migration/goal26d'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
START_HASHES = OUT/'start_hashes.txt'
REFERENCE_PREVIOUS = GOAL26C_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL26C_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal26c/hbmsntm-198A-goal26c.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
MIDDLE_RECEIPT = ROOT/'build/migration/releases/goal26b/release.json'
OLDER_RECEIPT = ROOT/'build/migration/releases/goal26a/release.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal26d'
RELEASE_NAME = 'hbmsntm-198A-goal26d.jar'
OWNER = 'goal26d'
PREVIOUS_OWNER = 'goal26c'
MIDDLE_OWNER = 'goal26b'
OLDER_OWNER = 'goal26a'
PLANNING_OWNER = 'planning-2026-10-22-26d'
PLANNING_PREFIX = '8954b531'
GOAL25_CLOSEOUT = '5b1bf4db'
GOAL25_PLANNING = '783b6d13'
GOAL24_CLOSEOUT = '17c8062f'
START_STATUS_LINES = 316
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
OLDER_RECEIPTS = {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b',
                  'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c', 'goal25d', 'goal26a', 'goal26b'}

# Production (owner goal26d), NEW (handoff-packaging.md; builder-report.md names the final classes: if a class is named differently or a helper class is added, edit this list, --check
# reports the difference as an unassigned src/ path). RadiationMedicineGameTests is the GameTest verifier's class.
NEW_JAVA = [J+p+'.java' for p in ('items/food/PillItem', 'items/special/SimpleConsumableItem', 'gametest/RadiationMedicineGameTests')]
(PILL_ITEM, CONSUMABLE_ITEM, MEDICINE_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails, except an older GameTest the GameTest verifier had to update:
# see OLDER_GAMETEST_REMOVABLE; a review fix may add a file: --check reports it as an unassigned src/ path instead of failing silently).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'config/CommonConfig', 'config/NtmConfig', 'registry/NtmSoundEvents', 'datagen/NtmSoundDefinitionsProvider', 'items/NtmItems', 'inventory/NtmCreativeTabs', 'datagen/NtmRecipeProvider',
    'datagen/NtmItemModelProvider', 'datagen/NtmLanguageProvider')]
(COMMON_CONFIG, NTM_CONFIG, SOUND_EVENTS, SOUND_DEFS, ITEMS, CREATIVE_TABS, RECIPE_PROVIDER, ITEM_MODEL_PROVIDER, PROVIDER) = MODIFIED_JAVA
OPTIONAL_JAVA = []
# The older GameTest sources the GameTest verifier may update when a count or "not registered" assertion of an older test changes because of this batch (verifier-report.md says none were changed):
# any changed existing gametest/*.java source is owned by goal26d as production; the start CODE lines it may drop are assertion and log lines (prefixes below) and every such edit is reported in the receipt.
# The handoff lists HazmatSuitGameTests, GasMaskGameTests, RadiationControlGameTests and HazardGameTests among the files that must stay byte-identical "unless the verifier report names an edit": an edit of one of
# them is reported by --check as a changed byte-identical file until UNCHANGED_JAVA is edited here.
OLDER_GAMETEST_DIR = J+'gametest/'
OLDER_GAMETEST_REMOVABLE = ('check(', 'LOGGER.info(', 'for(', 'for (', 'if(', 'if (', 'helper.')
# Must stay byte-identical to the start (the handoff list: the effect registry and the three effect classes, the living attachments, the hazmat registry, the radon tomb block, the drink item, the tooltip
# interface, ArmorUtil / ContaminationUtil, the mod entry classes and the older hazard GameTests).
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'lib/ModEffect', 'lib/effects/RadawayEffect', 'lib/effects/RadiationEffect', 'lib/effects/GenericEffect', 'extprop/HbmLivingAttachments', 'handler/HazmatRegistry', 'blocks/gas/GasRadonTombBlock',
    'items/food/DrinkItem', 'blocks/ITooltipProvider', 'util/ArmorUtil', 'util/ContaminationUtil', 'main/NuclearTechMod', 'main/CommonEvents', 'gametest/HazmatSuitGameTests', 'gametest/GasMaskGameTests',
    'gametest/RadiationControlGameTests', 'gametest/HazardGameTests')]
# Modified sources whose compiled class need not change (comment-only edits); every other modified source must show a modified class in the JAR.
SAME_CLASS_JAVA = []
NO_CLASS_JAVA = []
# JAR classes whose source is unchanged since the start and that differ from the previous package only in recompiled debug names. RBMKRecyclingGameTests$1 (an anonymous
# RBMKControlManualBlockEntity) flips the constructor's local-variable names between pos / state and arg0 / arg1 on incremental recompiles (Goal25B, Goal26A, Goal26B, Goal26C); the goal26c package holds
# whichever form its build produced, so the entry is accepted in either direction (patched previous bytes must equal the new class bytes; its source is unchanged since the start).
RECOMPILE_ONLY = {'com/hbm/gametest/RBMKRecyclingGameTests$1.class': (((b'\x01\x00\x04arg0', b'\x01\x00\x03pos'), (b'\x01\x00\x04arg1', b'\x01\x00\x05state')),
                                                                    ((b'\x01\x00\x03pos', b'\x01\x00\x04arg0'), (b'\x01\x00\x05state', b'\x01\x00\x04arg1')))}
RECOMPILE_OWNER = 'recompile-debug-names'
# Insert-only against the start bytes: every modified file of the batch (registration, datagen and config lines, the Chinese file and the mapping). The builder report and the diff show pure additions; a review
# fix that removes or moves a start line is reported with the changed file. ALLOWED_REMOVED_CODE / ALLOWED_REMOVED_EXACT stay empty tables so an older GameTest edit (OLDER_GAMETEST_REMOVABLE) is still judged.
STRICT_INSERT_ONLY = list(MODIFIED_JAVA) + [ZH_INPUT, LOCALIZATION_RECORD]
ALLOWED_REMOVED_CODE = {}
ALLOWED_REMOVED_EXACT = {}
# The added lines of these files must be exactly the lines of the batch: every added CODE line (comments and blanks excepted) must match its pattern. The language provider is judged by its key list instead
# and the recipe provider by the generated recipe JSON against the parsed original rows.
ADDED_CODE_RULES = {
    COMMON_CONFIG: re.compile(r'import net\.neoforged\.neoforge\.common\.ModConfigSpec\.ConfigValue;|public final ConfigValue<String> POTION_SICKNESS;|builder\.pop\(\);|builder\.push\("potion"\);|POTION_SICKNESS = builder'
                                                    r'|\.comment\("Valid configs include \\"NORMAL\\" and \\"TERRARIA\\", otherwise potion sickness is turned off"\)|\.translation\("hbmsntm\.configuration\.potionSickness"\)'
                                                    r'|\.define\("potionSickness", "OFF"\);'),
    NTM_CONFIG: re.compile(r'import (?:com\.hbm\.lib\.ModEffect|net\.minecraft\.world\.effect\.MobEffectInstance|net\.minecraft\.world\.entity\.LivingEntity|java\.util\.Locale);'
                           r'|public static int potionSickness\(\) \{|String mode = NtmConfig\.COMMON\.POTION_SICKNESS\.get\(\)\.toLowerCase\(Locale\.US\);|if\(mode\.equals\("(?:normal|terraria)"\)\) return [12];|return 0;|\}'
                           r'|public static void applyPotionSickness\(LivingEntity entity, int duration\) \{|int mode = potionSickness\(\);|if\(mode == 0\) return;|if\(mode == 2\) duration \*= 12;'
                           r'|MobEffectInstance sickness = new MobEffectInstance\(ModEffect\.POTIONSICKNESS, duration \* 20\);|sickness\.getCures\(\)\.clear\(\);|entity\.addEffect\(sickness\);'
                           r'|public static boolean hasPotionSickness\(LivingEntity entity\) \{ return entity\.hasEffect\(ModEffect\.POTIONSICKNESS\); \}'),
    SOUND_EVENTS: re.compile(r'public static final DeferredHolder<SoundEvent, SoundEvent> (?:SYRINGE|RADAWAY) = reg\("item\.(?:syringe|radaway)"\);.*'),
    SOUND_DEFS: re.compile(r'this\.add\(NtmSoundEvents\.(?:SYRINGE|RADAWAY), SoundDefinition\.definition\(\)\.with\(sound\("hbmsntm:tool/(?:stim|radaway)"\)\)\);'),
    ITEMS: re.compile(r'import com\.hbm\.items\.food\.PillItem;'
                      r'|public static final DeferredItem<Item> (?:RADAWAY|RADX|SIOX|IV_EMPTY|IV_BLOOD) = ITEMS\.register\("(?:radaway|radx|siox|iv_empty|iv_blood)", \(\) -> new (?:SimpleConsumableItem|PillItem)'
                      r'\(new Item\.Properties\(\)(?:, PillItem\.LAMBDA_(?:RADX|SIOX))?\)(?:\.setUseActionServer\(SimpleConsumableItem::(?:radaway|ivEmpty|ivBlood)\))?\);'),
    CREATIVE_TABS: re.compile(r'output\.accept\(NtmItems\.(?:IV_EMPTY|IV_BLOOD|RADAWAY|RADX|SIOX)\);'),
    ITEM_MODEL_PROVIDER: re.compile(r'this\.basicItem\(NtmItems\.(?:RADAWAY|RADX|SIOX|IV_EMPTY|IV_BLOOD)\.get\(\)\);'),
}
# The 7 imported original resources: NEO target -> original path, derived by the layout rules of the ownership record (textures/items -> textures/item, names kept; sounds keep path and name).
ITEM_ICONS = ('radx', 'siox', 'radaway', 'iv_empty', 'iv_blood')
SOUND_FILES = ('tool/stim', 'tool/radaway')
ASSETS = {ASSETS_ROOT+'textures/item/'+n+'.png': O_RES+'textures/items/'+n+'.png' for n in ITEM_ICONS}
ASSETS.update({ASSETS_ROOT+'sounds/'+n+'.ogg': O_RES+'sounds/'+n+'.ogg' for n in SOUND_FILES})
RENAMED = {}
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
SOUNDS_ENTRY = 'assets/hbmsntm/sounds.json'
GENERATED_SOUNDS = GENERATED_ROOT+SOUNDS_ENTRY
GENERATED = [STAMP, EN, GENERATED_SOUNDS]
# The 5 new items: registry id -> NtmItems constant (the item model, the language name, the creative tab entry and the registration are counted per item).
ITEM_TABLE = {n: n.upper() for n in ITEM_ICONS}
# The 4 crafting recipes (builder-report.md): recipe id -> (kind, original path, selector regex of the single original line, NEO result id). The original rows are parsed from the stored
# blobs at aee05a40f, their key expressions translated through KEY_TABLE and compared with the generated JSON.
O_RECIPES_PATH = 'crafting/ConsumableRecipes.java'
RECIPES = {
    'radx': ('shapeless', O_RECIPES_PATH, r'new ItemStack\(ModItems\.radx, 1\)', 'hbmsntm:radx'),
    'siox': ('shapeless', O_RECIPES_PATH, r'new ItemStack\(ModItems\.siox, 8\).*ModItems\.nugget_bismuth', 'hbmsntm:siox'),
    'iv_empty': ('shaped', O_RECIPES_PATH, r'new ItemStack\(ModItems\.iv_empty, 4\)', 'hbmsntm:iv_empty'),
    'radaway': ('shapeless', O_RECIPES_PATH, r'new ItemStack\(ModItems\.radaway, 1\)', 'hbmsntm:radaway'),
}
RECIPE_IDS = sorted(RECIPES)
SMELT_INPUTS = {}
# Recipe id -> the ORIGINAL_REFS entry quoted for it in the receipt.
RECIPE_REFS = {'radx': 'recipe_radx', 'siox': 'recipe_siox', 'iv_empty': 'recipe_iv_empty', 'radaway': 'recipe_radaway'}
EXPECTED_GENERATED_BASE = sorted([f'assets/hbmsntm/models/item/{n}.json' for n in ITEM_ICONS] + [f'data/hbmsntm/recipe/{r}.json' for r in RECIPE_IDS])
ADVANCEMENT = {r: re.compile(r'data/hbmsntm/advancement/recipes/[a-z_]+/'+re.escape(r)+r'\.json') for r in RECIPE_IDS}
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, SOUNDS_ENTRY])
NEW_TOOLS = ['tools/migration/verify_goal26d_medicine.py', 'tools/migration/package_goal26d.py']
TOOLS = NEW_TOOLS
# New tools/migration/goal26d_oldsuite_* files (a shared stand-in the main agent might have to add for the six revived old suites, handoff-packaging.md): optional, owned by goal26d as tools when present.
OLDSUITE_TOOL = re.compile(r'tools/migration/goal26d_oldsuite_[^/]+\.py')
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal26d-* or GOAL26D-* record is hashed as well.
REPORTS = ['migration/GOAL26D.md', 'migration/GOAL26D-ACCEPTANCE.md', 'migration/goal26d-static-review.md', 'migration/goal26d-localization-review.json',
           'migration/goal26d-resource-ownership.json', 'migration/goal26d-materials-review.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal26d-[^/]+\.(json|md)|GOAL26D-[^/]+\.md)')
GOAL26_RECORD = 'migration/GOAL26.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md',
                  'migration/RESOURCE-OWNERSHIP.md', GOAL26_RECORD]
# Shared records the batch may leave untouched (FOUNDATIONS.md and RESOURCE-OWNERSHIP.md "if touched").
OPTIONAL_RECORDS = ['migration/FOUNDATIONS.md', 'migration/RESOURCE-OWNERSHIP.md']
# The Goal 26 planning documents of the other batches: no change is expected in this batch. GOAL26D.md is this batch's task book and delivery record (REPORTS[0]).
PLANNING_FROZEN = ['migration/GOAL26-THREAD-PROMPTS.md', 'migration/SURVIVAL-PLAYABILITY.md']
# The two planning-session supplements of 2026-10-22 in the dirty start (no receipt hashes them).
PLANNING_SUPPLEMENTS = ['migration/GOAL26D.md', 'migration/GOAL26-THREAD-PROMPTS.md']
FROZEN_RECORD = re.compile(r'migration/(GOAL25[^/]*\.md|goal25[abcd]-[^/]+|GOAL24[^/]*\.md|goal24[^/]*|GOAL26[ABC][^/]*\.md|goal26[abc]-[^/]+|GOAL26-THREAD-PROMPTS\.md|SURVIVAL-PLAYABILITY\.md)')
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED_BASE + the advancements.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]
# The shared records the main agent edits after a package (not hashed by a receipt): their receipt after-hash may differ from the start hash (the records written after a package).
SHARED_AFTER_PACKAGE = set(SHARED_RECORDS)
# The 7 new language keys: NEO key -> (original key, expected map kind). Six upstream with the original English and Chinese verbatim (en_US.lang:3243-3244, 4154-4158, 4522-4523, zh_CN.lang:2782-2783,
# 3590-3594, 3936-3937); one local: radx.desc keeps the original English "37%%" but the Chinese "37%" gets the NEO double-percent escape (main-notes 8).
SOURCE_KEYS = {'item.hbmsntm.radaway': ('item.radaway.name', 'upstream'), 'item.hbmsntm.radx': ('item.radx.name', 'upstream'), 'item.hbmsntm.radx.desc': ('item.radx.desc', 'local'),
               'item.hbmsntm.siox': ('item.siox.name', 'upstream'), 'item.hbmsntm.siox.desc': ('item.siox.desc', 'upstream'),
               'item.hbmsntm.iv_empty': ('item.iv_empty.name', 'upstream'), 'item.hbmsntm.iv_blood': ('item.iv_blood.name', 'upstream')}
KEYS = {k: v[0] for k, v in SOURCE_KEYS.items()}
EXPECTED_KINDS = dict(Counter(v[1] for v in SOURCE_KEYS.values()))
CONFIG_TRANSLATION_KEY = 'hbmsntm.configuration.potionSickness'
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-medicine] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the sessions of the batch.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'make_freeze.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_head.txt', 'start_hashes.txt',
                  'import_resources.py', 'add_zh.py', 'main-notes.md', 'handoff-builder.md', 'builder-report.md', 'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md',
                  'verifier-report.md', 'review-report.md', 'chain.sh', 'make_production_diff.py')
# Review files under OUT the main agent names when it knows them (REVIEW_EVIDENCE: review-report.md, review-diff.patch, handoff-review.md); each must exist and is indexed by the receipt. Extend this list
# from the real run; --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('review-diff.patch', 'make_loc_review.py', 'update_features.py', 'make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'packaging-progress.md',
                   'packaging-report.md', 'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier-gt/scope-before.txt', 'verifier-gt/scope-after.txt', 'builder_compile.log',
                   'builder_rundata.log', 'builder_build.log', 'builder_pre_rundata_generated.txt', 'builder_post_rundata_generated.txt', 'verifier-progress.md', 'verify-final.out', 'compare.log',
                   'localization-final.log', 'resources-audit-final.log', 'packaged-resources-final.log')
GAMETEST_LOG = 'build/migration/goal26d/gametest-final.log'
NEW_SUITE = 'verify_goal26d_medicine.py --gametest-log build/migration/goal26d/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
# Suites other than NEW_SUITE the final rerun may add (none known: the six old machine / pollution suites keep their suite names and run through the goal26c wrapper switch of run_final.py).
EXTRA_FINAL_SUITES = set()
FEATURE_MEDICINE = 'radiation-medicine'
NEW_FEATURES = (FEATURE_MEDICINE,)
# The groups the snapshot of the end of 24A predates (24B rbmk-fuel, 24C rbmk-reactor, 24D rbmk-control and rbmk-steam, 24E rbmk-console, 25A rbmk-storage and rbmk-recycling,
# 25B rbmk-outgasser, 25C rbmk-autoloader, 25D rbmk-crane, 26A hazard-system and radiation-detection, 26B gas-masks, 26C hazmat-suits).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser', 'rbmk-autoloader', 'rbmk-crane',
                          'hazard-system', 'radiation-detection', 'gas-masks', 'hazmat-suits'}
RADIATION_NOTE = ('Goal26D: RadAway removes 140 RAD over 7 seconds and Rad-X adds 0.2 radiation resistance for 3 minutes; using an IV bag costs 5 health and kills at 5 or less; radiation tests stay in a '
                  'separately authorized disposable world. ')
MELTDOWN_NOTE = 'Goal26D: no new meltdown path; reactor tests stay in disposable worlds. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_PILL = ORIGINAL+'items/food/ItemPill.java'
O_CONSUMABLE = ORIGINAL+'items/special/ItemSimpleConsumable.java'
O_VERSATILE = ORIGINAL+'config/VersatileConfig.java'
O_POTIONCFG = ORIGINAL+'config/PotionConfig.java'
O_RECIPES = ORIGINAL+O_RECIPES_PATH
O_MODITEMS = ORIGINAL+'items/ModItems.java'
O_DAMAGEUTIL = ORIGINAL+'util/EntityDamageUtil.java'
O_LIVINGPROPS = ORIGINAL+'extprop/HbmLivingProps.java'
O_SOUNDS = RES+'assets/hbm/sounds.json'
O_SOURCES = [O_PILL, O_CONSUMABLE, O_VERSATILE, O_POTIONCFG, O_RECIPES, O_MODITEMS, O_DAMAGEUTIL, O_LIVINGPROPS, O_SOUNDS, O_LANG_EN, O_LANG_ZH]
# The original sources the new mapping group must list (source_paths or source_watch; plus the imported resources).
FEATURE_SOURCES = {FEATURE_MEDICINE: [O_PILL, O_CONSUMABLE, O_VERSATILE, O_POTIONCFG, O_RECIPES, O_MODITEMS, O_DAMAGEUTIL, O_LIVINGPROPS, O_SOUNDS, O_LANG_EN, O_LANG_ZH] + list(ASSETS.values())}
# The NEO paths the new mapping group must cover (target_paths or target_watch).
FEATURE_TARGETS = {FEATURE_MEDICINE: NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, EN, GENERATED_SOUNDS, NEW_TOOLS[0], NEW_TOOLS[1]] + [GENERATED_ROOT+p for p in EXPECTED_GENERATED_BASE]
                   + [GENERATED_ROOT+f'data/hbmsntm/advancement/recipes/misc/{r}.json' for r in RECIPE_IDS]}
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'pill_food': (O_PILL, 'this.setAlwaysEdible();'), 'pill_sickness': (O_PILL, 'VersatileConfig.applyPotionSickness(player, 5);'), 'pill_radx': (O_PILL, 'if(this == ModItems.radx)'),
    'pill_siox': (O_PILL, 'if(this == ModItems.siox)'), 'pill_use_duration': (O_PILL, 'public int getMaxItemUseDuration'), 'pill_use_gate': (O_PILL, 'VersatileConfig.hasPotionSickness(p_77659_3_)'),
    'pill_tooltip': (O_PILL, 'public void addInformation'),
    'consumable_use': (O_CONSUMABLE, 'public ItemStack onItemRightClick'), 'consumable_give_sound': (O_CONSUMABLE, 'public static void giveSoundAndDecrement'),
    'consumable_add_effect': (O_CONSUMABLE, 'public static void addPotionEffect'), 'consumable_try_add': (O_CONSUMABLE, 'public static void tryAddItem'),
    'consumable_do_radaway': (O_CONSUMABLE, 'public static void doRadaway'), 'iv_empty': (O_CONSUMABLE, 'ModItems.iv_empty = new ItemSimpleConsumable()'),
    'iv_blood': (O_CONSUMABLE, 'ModItems.iv_blood = new ItemSimpleConsumable()'), 'radaway': (O_CONSUMABLE, 'ModItems.radaway = new ItemSimpleConsumable()'),
    'is_real_player': (O_DAMAGEUTIL, 'public static boolean isRealPlayer'), 'max_blacklung': (O_LIVINGPROPS, 'public static final int maxBlacklung'),
    'potion_config': (O_POTIONCFG, '8.S0_potionSickness'), 'potion_parse': (O_POTIONCFG, '"normal".equals(s.toLowerCase(Locale.US))'),
    'versatile_apply': (O_VERSATILE, 'public static void applyPotionSickness'), 'versatile_has': (O_VERSATILE, 'public static boolean hasPotionSickness'),
    'items_radx': (O_MODITEMS, 'radx = new ItemPill(0)'), 'items_siox': (O_MODITEMS, 'siox = new ItemPill(0)'), 'items_registered': (O_MODITEMS, 'GameRegistry.registerItem(iv_empty, '),
    'recipe_radx': (O_RECIPES, 'new ItemStack(ModItems.radx, 1)'), 'recipe_siox': (O_RECIPES, 'ASBESTOS.dust(), ModItems.nugget_bismuth'), 'recipe_siox_lbsm': (O_RECIPES, 'ASBESTOS.dust(), GOLD.nugget()'),
    'recipe_iv_empty': (O_RECIPES, 'new ItemStack(ModItems.iv_empty, 4)'), 'recipe_radaway': (O_RECIPES, 'new ItemStack(ModItems.radaway, 1)'),
    'sounds_syringe': (O_SOUNDS, '"item.syringe"'), 'sounds_radaway': (O_SOUNDS, '"item.radaway"'),
    'lang_radx_en': (O_LANG_EN, 'item.radx.name='), 'lang_radx_zh': (O_LANG_ZH, 'item.radx.name='), 'lang_radx_desc_zh': (O_LANG_ZH, 'item.radx.desc='),
}
# Constants compared between the original and NEO source texts: id -> (original path or None, regex, NEO path, regex, expected, expected NEO values when they differ). `expected` is the exact
# list of distinct normalized values of the original (numbers as floats, underscores and an F / D suffix dropped, anything else as text) in order, or None; a NEO-only constant has no original
# path. The group-1 value of every match is collected. A NEO regex that finds nothing (the class is not written yet, or its text differs from the handoff) is reported as pending with its id.
CONSTANTS = {
    # ItemPill.java:57-59 radx: 3 * 60 * 20 ticks (3 minutes), amplifier 0; :34 potion sickness 5 seconds before the pill effect; :123-125 use duration 10 ticks; ModItems.java:2828-2829 ItemPill(0) = hunger 0.
    'radx_duration': (O_PILL, r'HbmPotion\.radx\.id, ([\d *]+), \d+\)', PILL_ITEM, r'ModEffect\.RADX, ([\d *]+), \d+\)', ['3 * 60 * 20']),
    'radx_amplifier': (O_PILL, r'HbmPotion\.radx\.id, [\d *]+, (\d+)\)', PILL_ITEM, r'ModEffect\.RADX, [\d *]+, (\d+)\)', [0]),
    'pill_sickness_seconds': (O_PILL, r'applyPotionSickness\(player, (\d+)\)', PILL_ITEM, r'applyPotionSickness\(eater, (\d+)\)', [5]),
    'pill_use_duration': (O_PILL, r'getMaxItemUseDuration\([^)]*\) \{\s*return (\d+);', PILL_ITEM, r'getUseDuration\([^)]*\) \{ return (\d+); \}', [10]),
    'pill_hunger': (O_MODITEMS, r'(?:radx|siox) = new ItemPill\((\d+)\)', PILL_ITEM, r'\.nutrition\((\d+)\)', [0]),
    # ItemPill.java:61-64 siox: asbestos 0, black lung min(current, maxBlacklung / 5); HbmLivingProps.java:46 maxBlacklung = 2 * 60 * 60 * 20 = 144,000 (5 -> 28,800).
    'siox_asbestos_value': (O_PILL, r'setAsbestos\(player, (\d+)\)', PILL_ITEM, r'setAsbestos\(eater, (\d+)\)', [0]),
    'siox_blacklung_divisor': (O_PILL, r'maxBlacklung / (\d+)\)', PILL_ITEM, r'maxBlacklung / (\d+)\)', [5]),
    'max_blacklung': (O_LIVINGPROPS, r'maxBlacklung = ([\d *]+);', J+'extprop/HbmLivingAttachments.java', r'maxBlacklung = ([\d *]+);', ['2 * 60 * 60 * 20']),
    # ItemSimpleConsumable.java:139-141 radaway: doRadaway(stack, user, 140), :86-89 amplifier 0; :113-118 iv_empty -5 health (clamped at 0), :120-123 iv_blood heals 5.
    'radaway_duration': (O_CONSUMABLE, r'ModItems\.radaway = new ItemSimpleConsumable\(\)\.setUseActionServer\(\(stack, user\) -> \{\s*doRadaway\(stack, user, (\d+)\);', CONSUMABLE_ITEM,
                         r'public static void radaway\(ItemStack stack, Player user\) \{\s*doRadaway\(stack, user, (\d+)\);', [140]),
    'radaway_amplifier': (O_CONSUMABLE, r'addPotionEffect\(user, HbmPotion\.radaway, duration, (\d+)\)', CONSUMABLE_ITEM, r'addPotionEffect\(user, ModEffect\.RADAWAY, duration, (\d+)\)', [0]),
    'iv_empty_damage': (O_CONSUMABLE, r'user\.setHealth\(Math\.max\(user\.getHealth\(\) - ([\d.]+)F, 0F\)\);', CONSUMABLE_ITEM, r'user\.setHealth\(Math\.max\(user\.getHealth\(\) - ([\d.]+)F, 0F\)\);', [5]),
    'iv_blood_heal': (O_CONSUMABLE, r'user\.heal\(([\d.]+)F\)', CONSUMABLE_ITEM, r'user\.heal\(([\d.]+)F\)', [5]),
    # PotionConfig.java:26 (8.S0_potionSickness, default OFF, the option text) and :28-31 (parse), VersatileConfig.java:9-14 (apply: TERRARIA x12, seconds * 20 ticks).
    'potion_config_default': (O_POTIONCFG, r'"8\.S0_potionSickness", "(?:[^"\\]|\\.)*", "(\w+)"\)', COMMON_CONFIG, r'\.define\("potionSickness", "(\w+)"\)', ['OFF']),
    'potion_config_comment': (O_POTIONCFG, r'"8\.S0_potionSickness", "((?:[^"\\]|\\.)*)"', COMMON_CONFIG, r'\.comment\("((?:[^"\\]|\\.)*)"\)\s*\.translation\("hbmsntm\.configuration\.potionSickness"\)',
                              ['Valid configs include \\"NORMAL\\" and \\"TERRARIA\\", otherwise potion sickness is turned off']),
    'potion_terraria_factor': (O_VERSATILE, r'if\(PotionConfig\.potionSickness == 2\) duration \*= (\d+);', NTM_CONFIG, r'if\(mode == 2\) duration \*= (\d+);', [12]),
    'potion_ticks_per_second': (O_VERSATILE, r'new PotionEffect\(HbmPotion\.potionsickness\.id, duration \* (\d+)\)', NTM_CONFIG, r'new MobEffectInstance\(ModEffect\.POTIONSICKNESS, duration \* (\d+)\)', [20]),
}
# Sequences (every match in source order, original against NEO, compared sorted; the groups of a match are joined by '|', lower case, spaces and an F / D suffix dropped): id -> (original path, regex,
# NEO path, regex, expected match count of the original[, the explicit NEO values when they differ by the renames of the batch]).
SEQUENCES = {
    # PotionConfig.java:28-31: the two accepted option values and the mode each selects.
    'potion_parse': (O_POTIONCFG, r'if\("(\w+)"\.equals\(s\.toLowerCase\(Locale\.US\)\)\)\s*potionSickness = (\d+);', NTM_CONFIG, r'if\(mode\.equals\("(\w+)"\)\) return (\d+);', 2),
    # The sound event and the returned container of each action (ItemSimpleConsumable.java:86-89 doRadaway, :113-118 iv_empty, :120-123 iv_blood); NEO names the sound by its registry constant.
    'do_radaway_sound_container': (O_CONSUMABLE, r'doRadaway\(ItemStack stack, EntityPlayer user, int duration\) \{\s*giveSoundAndDecrement\(stack, user, "hbm:(item\.\w+)", new ItemStack\(ModItems\.(\w+)\)\)',
                                   CONSUMABLE_ITEM, r'doRadaway\(ItemStack stack, Player user, int duration\) \{\s*giveSoundAndDecrement\(stack, user, NtmSoundEvents\.(\w+)\.get\(\), new ItemStack\(NtmItems\.(\w+)\.get\(\)\)\)',
                                   1, ['RADAWAY|IV_EMPTY']),
    'iv_empty_sound_container': (O_CONSUMABLE, r'ModItems\.iv_empty = new ItemSimpleConsumable\(\)\.setUseActionServer\(\(stack, user\) -> \{.*?giveSoundAndDecrement\(stack, user, "hbm:(item\.\w+)", new ItemStack\(ModItems\.(\w+)\)\)',
                                 CONSUMABLE_ITEM, r'public static void ivEmpty\(.*?giveSoundAndDecrement\(stack, user, NtmSoundEvents\.(\w+)\.get\(\), new ItemStack\(NtmItems\.(\w+)\.get\(\)\)\)', 1, ['SYRINGE|IV_BLOOD']),
    'iv_blood_sound_container': (O_CONSUMABLE, r'ModItems\.iv_blood = new ItemSimpleConsumable\(\)\.setUseActionServer\(\(stack, user\) -> \{.*?giveSoundAndDecrement\(stack, user, "hbm:(item\.\w+)", new ItemStack\(ModItems\.(\w+)\)\)',
                                 CONSUMABLE_ITEM, r'public static void ivBlood\(.*?giveSoundAndDecrement\(stack, user, NtmSoundEvents\.(\w+)\.get\(\), new ItemStack\(NtmItems\.(\w+)\.get\(\)\)\)', 1, ['RADAWAY|IV_EMPTY']),
    # sounds.json:117-118: event -> file (the NEO events are item.syringe -> hbmsntm:tool/stim and item.radaway -> hbmsntm:tool/radaway).
    'sound_definitions': (O_SOUNDS, r'"(item\.(?:syringe|radaway))": \{"category": "player", "sounds": \[\{"name": "(tool/\w+)", "stream": false\}\]\}', SOUND_DEFS,
                          r'this\.add\(NtmSoundEvents\.(SYRINGE|RADAWAY), SoundDefinition\.definition\(\)\.with\(sound\("hbmsntm:(tool/\w+)"\)\)\)', 2, ['SYRINGE|tool/stim', 'RADAWAY|tool/radaway']),
}
# Occurrence counts in the NEO source texts (expected), with the original count where one exists: id -> (NEO path, regex, expected count[, original path, original regex, original count]).
COUNTS = {
    'pills_registered': (ITEMS, r'new PillItem\(new Item\.Properties\(\), PillItem\.LAMBDA_(?:RADX|SIOX)\)', 2, O_MODITEMS, r'(?:radx|siox) = new ItemPill\(0\)', 2),
    'simple_consumables_registered': (ITEMS, r'new SimpleConsumableItem\(new Item\.Properties\(\)\)\.setUseActionServer\(SimpleConsumableItem::(?:radaway|ivEmpty|ivBlood)\)', 3,
                                      O_CONSUMABLE, r'ModItems\.(?:radaway|iv_empty|iv_blood) = new ItemSimpleConsumable\(\)\.setUseActionServer', 3),
    'other_consumables_not_registered': (ITEMS, r'DeferredItem<Item> (?:RADAWAY_STRONG|RADAWAY_FLUSH|IV_XP|IV_XP_EMPTY|PILL_IODINE|PILL_RED|PILL_HERBAL|XANAX|FMN|FIVE_HTP)\b', 0),
    'pill_always_edible': (PILL_ITEM, r'\.alwaysEdible\(\)', 1, O_PILL, r'this\.setAlwaysEdible\(\);', 1),
    'pill_sickness_before_effect': (PILL_ITEM, r'applyPotionSickness\(eater, 5\);\s*if\(this\.finishUsingItem != null\) this\.finishUsingItem\.accept\(eater\);', 1,
                                    O_PILL, r'applyPotionSickness\(player, 5\);(?:.|\n)*?if\(this == ModItems\.radx\)', 1),
    'pill_server_only': (PILL_ITEM, r'if\(!level\.isClientSide\) \{\s*NtmConfig\.applyPotionSickness', 1, O_PILL, r'if\(!world\.isRemote\) \{\s*VersatileConfig\.applyPotionSickness', 1),
    'pill_use_gate': (PILL_ITEM, r'if\(NtmConfig\.hasPotionSickness\(player\)\) return InteractionResultHolder\.pass\(player\.getItemInHand\(hand\)\);', 1,
                      O_PILL, r'if\(!VersatileConfig\.hasPotionSickness\(p_77659_3_\)\)\s*p_77659_3_\.setItemInUse', 1),
    'pill_no_other_effects': (PILL_ITEM, r'MobEffects\.|ModEffect\.(?!RADX|POTIONSICKNESS)\w+', 0),
    'consumable_server_gate': (CONSUMABLE_ITEM, r'if\(!level\.isClientSide && this\.useActionServer != null\)', 1, O_CONSUMABLE, r'if\(!world\.isRemote && this\.useActionServer != null\)', 1),
    'consumable_container_drop': (CONSUMABLE_ITEM, r'if\(!player\.getInventory\(\)\.add\(stack\)\) player\.drop\(stack, false\);', 1,
                                  O_CONSUMABLE, r'if\(!player\.inventory\.addItemStackToInventory\(stack\)\) \{\s*player\.dropPlayerItemWithRandomChoice\(stack, false\);', 1),
    'consumable_effect_sum': (CONSUMABLE_ITEM, r'active\.getDuration\(\) \+ duration', 1, O_CONSUMABLE, r'getActivePotionEffect\(effect\)\.getDuration\(\) \+ duration', 1),
    'consumable_container_given_in_creative': (CONSUMABLE_ITEM, r'stack\.consume\(1, entity\);(?:.|\n)*?tryAddItem\(entity, container\);', 1, O_CONSUMABLE, r'stack\.stackSize--;(?:.|\n)*?tryAddItem\(entity, container\);', 1),
    'iv_empty_real_player_gate': (CONSUMABLE_ITEM, r'if\(!isRealPlayer\(user\)\) return;', 1, O_CONSUMABLE, r'ModItems\.iv_empty = new ItemSimpleConsumable\(\)\.setUseActionServer\(\(stack, user\) -> \{\s*if\(!EntityDamageUtil\.isRealPlayer\(user\)\) return;', 1),
    'is_real_player_rule': (CONSUMABLE_ITEM, r'entity instanceof Player && !\(entity instanceof FakePlayer\)', 1, O_DAMAGEUTIL, r'entity instanceof EntityPlayer && !\(entity instanceof FakePlayer\)', 1),
    'iv_empty_death': (CONSUMABLE_ITEM, r'if\(user\.getHealth\(\) <= 0\) user\.die\(user\.damageSources\(\)\.magic\(\)\);', 1, O_CONSUMABLE, r'if\(user\.getHealth\(\) <= 0\) user\.onDeath\(DamageSource\.magic\);', 1),
    'iv_blood_not_gated': (CONSUMABLE_ITEM, r'public static void ivBlood\(ItemStack stack, Player user\) \{\s*giveSoundAndDecrement', 1,
                           O_CONSUMABLE, r'ModItems\.iv_blood = new ItemSimpleConsumable\(\)\.setUseActionServer\(\(stack, user\) -> \{\s*giveSoundAndDecrement', 1),
    'potion_curative_items_cleared': (NTM_CONFIG, r'sickness\.getCures\(\)\.clear\(\);', 1, O_VERSATILE, r'eff\.setCurativeItems\(new ArrayList\(\)\);', 1),
    'potion_sickness_off_by_default': (COMMON_CONFIG, r'\.define\("potionSickness", "OFF"\)', 1, O_POTIONCFG, r'"8\.S0_potionSickness", "(?:[^"\\]|\\.)*", "OFF"\)', 1),
    'potion_config_section': (COMMON_CONFIG, r'builder\.push\("potion"\);', 1),
    'sound_events_registered': (SOUND_EVENTS, r'reg\("item\.(?:syringe|radaway)"\)', 2, O_SOUNDS, r'"item\.(?:syringe|radaway)": \{"category": "player"', 2),
    'creative_tab_block': (CREATIVE_TABS, r'output\.accept\(NtmItems\.IV_EMPTY\);\s*output\.accept\(NtmItems\.IV_BLOOD\);\s*output\.accept\(NtmItems\.RADAWAY\);\s*output\.accept\(NtmItems\.RADX\);\s*output\.accept\(NtmItems\.SIOX\);', 1),
    'recipe_provider_goal26d_block': (RECIPE_PROVIDER, r'ResourceLocation\.fromNamespaceAndPath\("hbmsntm", "(?:radx|siox|iv_empty|radaway)"\)\);', 4),
}
# per-item registration counts (one occurrence each) in creative tabs, the item model provider, the language provider and the registry.
for _n, _c in ITEM_TABLE.items():
    COUNTS[f'{_n}_registered'] = (ITEMS, rf'DeferredItem<Item> {_c} = ITEMS\.register\("{_n}"', 1)
    COUNTS[f'{_n}_item_model'] = (ITEM_MODEL_PROVIDER, rf'this\.basicItem\(NtmItems\.{_c}\.get\(\)\);', 1)
    COUNTS[f'{_n}_english_name'] = (PROVIDER, rf'this\.add\(NtmItems\.{_c}, "', 1)
    COUNTS[f'{_n}_creative_tab'] = (CREATIVE_TABS, rf'output\.accept\(NtmItems\.{_c}(?:\.get\(\))?\);', 1)
# Client-side classes the common code must not reference: the common classes below import nothing from net.minecraft.client and never name the render package.
COMMON_CLASSES = [PILL_ITEM, CONSUMABLE_ITEM, NTM_CONFIG, COMMON_CONFIG, ITEMS]
CLIENT_ONLY_NAMES = re.compile(r'GasMaskClientExtensions|ModelGasMask|ModelM65|IClientItemExtensions|net\.minecraft\.client|com\.hbm\.render\.')
# The black-lung cap (144,000 / 5), the effect durations in ticks and the potion sickness table of the original.
MAX_BLACKLUNG = 2 * 60 * 60 * 20
SIOX_BLACKLUNG_CAP = MAX_BLACKLUNG // 5
RADX_TICKS = 3 * 60 * 20
# Known source differences the batch deliberately leaves (recorded; not asserted equal, but each is backed by a NEO constant or fact above where it can be). main-notes.md 1-13, review-report.md F1-F5.
KNOWN_DIFFERENCES = {
    'config': 'CommonConfig has no potion option: new section "potion", key potionSickness (string, default "OFF"; NORMAL / TERRARIA case-insensitive, anything else off); the original "8.S0_potionSickness" prefix is dropped like every NEO '
              'key; the translation key hbmsntm.configuration.potionSickness has no language entry by design (Goal 25 decision, LOCALIZATION.md); the parse and apply helpers live in NtmConfig because NEO has no VersatileConfig (main-notes 1, 2)',
    'cures': 'MobEffectInstance.getCures().clear() on the potion sickness instance is the 1.21 counterpart of setCurativeItems(new ArrayList()): the milk and totem default cures cannot remove it; an empty cure set is omitted by the codec '
             'and the load constructor clears before re-adding, so it survives save / load (main-notes 3 and 13; the GameTest round trip passes). Honey only cures poison, the NtmConfig comment was corrected (comment only)',
    'consume_in_creative': 'PillItem follows the vanilla eat path (Item.finishUsingItem consumes unless the player has infinite materials); SimpleConsumableItem consumes with ItemStack.consume(1, player) = consume unless creative, '
                           'because 1.7.10 ItemInWorldManager.tryUseItem restored the stack size of a creative player (from knowledge of 1.7.10, the workspace has no vanilla 1.7.10 sources); the container is still given in creative (review F2, main-notes 4)',
    'pill_pass_while_sick': 'PillItem.use returns pass while the player has potion sickness (the original returned the stack unchanged and did not start using): pass lets the other hand act (review F4); the sickness gate reads no config',
    'iv_empty_death': 'iv_empty sets the health to max(health - 5, 0) and calls die(damageSources().magic()) at 0 health, the counterpart of onDeath(DamageSource.magic) which also bypasses armor, totems and invulnerability; no hurt() call, so '
                      'the death message is the generic one (main-notes 5, review F3); Player.die posts LivingDeathEvent twice in NeoForge 21.1.228 (observed by the GameTest, die() is called once)',
    'real_player': 'EntityDamageUtil.isRealPlayer (player and not FakePlayer) is a private helper of SimpleConsumableItem with net.neoforged.neoforge.common.util.FakePlayer; a FakePlayer using iv_empty changes nothing (main-notes 6)',
    'use_result': 'SimpleConsumableItem.use returns sidedSuccess(stack, isClientSide) instead of the unchanged stack (arm swing, NEO-only cosmetic), runs the action only on the server and re-reads player.getItemInHand(hand) afterwards, so a '
                  'container that landed in the emptied hand slot is not cleared by ServerPlayerGameMode (builder-report decisions)',
    'tooltips': 'both classes read the "$"-split <name>.desc lines through ITooltipProvider.getDescriptionOrNull (shown only when the key exists; ItemPill.java:108-120, ItemCustomLore.java:26-52); no P11 keys exist',
    'recipes': 'COAL.dust() -> powder_coal, F.dust() -> fluorite, ASBESTOS.dust() -> powder_asbestos, ANY_RUBBER.ingot() -> ntm:any_rubbers, IRON.plate() -> plate_iron; the SiOX recipe keeps nugget_bismuth, which has no survival source in NEO '
               'yet (unreachable: bismuth); the LBSM gold-nugget variant (ConsumableRecipes.java:127) is not registered (deferred); iv_blood has no recipe, it comes from using iv_empty',
    'effect_names': 'the 26A effect names (Rad-X, Radaway, Potion Sickness and the Chinese names) were re-checked against the behaviour and unchanged (main-notes 10)',
    'creative_tab': 'IV_EMPTY, IV_BLOOD, RADAWAY, RADX, SIOX sit after GAS_MASK_FILTER_PISS in the CONSUMABLE tab, the original GameRegistry order (ModItems.java:5954-5962; main-notes 11)',
    'language': 'six item keys are upstream verbatim; radx.desc is local: the original Chinese "37%" gets "37%%" because NEO language files write a literal percent as "%%" (heater_electric.desc precedent in both files; main-notes 8); '
                'the English "37%%" is verbatim',
    'deferred': 'radaway_strong, radaway_flush, iv_xp / iv_xp_empty, the syringes, iodine / plan_c / red / herbal pills, xanax, chocolate, fmn, five_htp, the SiOX LBSM gold variant and the hit actions of ItemSimpleConsumable are not migrated',
}
# The recipe key tables: original key expression -> the NEO ingredient (OneOf: several accepted generated forms). Forms follow the generated recipes: items by registry name, tags where the
# provider uses the tag for the same oredict key (main-notes 9).
KEY_TABLE = {
    'COAL.dust()': {'item': 'hbmsntm:powder_coal'}, 'F.dust()': {'item': 'hbmsntm:fluorite'}, 'ASBESTOS.dust()': {'item': 'hbmsntm:powder_asbestos'}, 'ModItems.nugget_bismuth': {'item': 'hbmsntm:nugget_bismuth'},
    'ModItems.iv_blood': {'item': 'hbmsntm:iv_blood'}, 'Items.pumpkin_seeds': {'item': 'minecraft:pumpkin_seeds'}, 'ANY_RUBBER.ingot()': {'tag': 'ntm:any_rubbers'}, 'IRON.plate()': {'item': 'hbmsntm:plate_iron'},
}
# The six old isolated machine / pollution suites (GOAL26D.md "必要验收与交付" 2): they keep running through tools/migration/goal26c_oldsuite_run.py in the final rerun; recorded in the receipt.
OLD_MACHINE_SUITES = ('verify_goal16a_machine', 'verify_goal16b_machine', 'verify_goal17b_machine', 'verify_goal18a_machine', 'verify_goal18b_machine', 'verify_goal19a_pollution')


def scope_text(key_count, assets, tests, total_tests):
    return (f'Goal26D (the fourth batch of Goal 26: radiation medicine): the Rad-X pill and the SiOX pill (PillItem: always edible, hunger 0, 10 ticks; Rad-X adds the radx effect for 3 minutes at amplifier 0, SiOX sets asbestos to 0 and '
            f'black lung to min(current, 144,000 / 5 = 28,800)), RadAway, the IV bag and the blood bag (SimpleConsumableItem: server action, one item consumed, sound, container returned or dropped; RadAway adds the radaway effect for 140 ticks at '
            f'amplifier 0 and sums with a running effect, the IV bag takes 5 health from a real player and kills at 5 or less, the blood bag heals 5); the potionSickness common config key (section potion, default OFF; NORMAL / TERRARIA) '
            f'with the potion sickness effect after each pill; two sound events (item.syringe = tool/stim, item.radaway = tool/radaway); {len(RECIPES)} crafting recipes (SiOX needs the bismuth nugget: unreachable: bismuth, the LBSM gold '
            f'variant is deferred); {assets} imported resources (5 item icons, 2 sounds); {key_count} English keys and {key_count} Chinese entries ({EXPECTED_KINDS.get("upstream", 0)} upstream, {EXPECTED_KINDS.get("local", 0)} local); '
            f'{tests} RadiationMedicineGameTests ({total_tests} GameTests in total, one batch per test) and the written, not executed Goal 26 unified acceptance checklist GOAL26D-ACCEPTANCE.md, which merges all Goal 25 acceptance '
            f'items. Gameplay impact: RADX and RADAWAY get their first survival source - Rad-X, IV bags and RadAway can be crafted in survival, blood bags come from using an IV bag on yourself (-5 health, deadly at 5 or less), SiOX only '
            f'from the creative tab until bismuth has a source; a new config key in hbmsntm-common.toml.')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal26d release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 234 scope copies: every dirty start file and the clean files the batch planned to touch) when it reproduces the baseline hash,
    else the blob at the start commit (with CRLF where the working tree had it); None when nothing reproduces the baseline hash (a file of the uncommitted Goal26C delivery without a copy)."""
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
    """The Goal26D start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does not list it)
    the hash the goal26c receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal26c packager protected (built there from the Goal21A..Goal25D starts and receipts and the goal26c start), plus every path the goal26c receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 26C baseline lists the goal25d receipt among them) and every release file of the frozen start
    (the goal26c package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes, GOAL25D-ACCEPTANCE.md)
    are pinned at their Goal26D start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal26c packager set at its Goal26C start hash, for the records that changed between the two starts."""
    goal26c_start = read(GOAL26C_BASELINE)
    out = dict(goal26c_protected_paths(goal26c_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal26c receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal26c_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift.
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal26C and Goal26D starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal26c_start):
    """{path: {receipts, start_sha256, goal26c_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal26c receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal26c receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif p == 'migration/GOAL25D-ACCEPTANCE.md':
            explanation = ('Edited after the goal25d package was written (the goal25d receipt hash is the pre-close-out text) and committed in the Goal 25 close-out commit 5b1bf4db, which records the '
                           'real-game acceptance as deferred into Goal 26; the goal26c receipt records the start hash. Frozen at the start hash; this batch must not change it and no receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22, 23 and 24 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal26c '
                           'receipt does not hash it. Frozen at the Goal26D start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal26c) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal26c package; the goal26c receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal26c '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal26c_start_sha256=goal26c_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal26c_start_pin_sha256'] = repinned[p]
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
    goal26c_start = read(GOAL26C_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal26D commits nothing), the recorded start: HEAD 8954b531 (the Goal 26 planning commit) on the
    # Goal 25 close-out commit, on the Goal 25 planning commit, on the pushed Goal 24 close-out commit, PLUS the uncommitted Goal26A, Goal26B and Goal26C deliveries and the two planning supplements
    # (316 status lines).
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 26 planning commit'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 26 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    status_lines = base['target_status'].splitlines()
    assert len(status_lines) == START_STATUS_LINES and START_STATUS.read_text(encoding='utf-8').splitlines() == status_lines, \
        f'The frozen start is not the {START_STATUS_LINES} status lines of the uncommitted Goal26A, Goal26B and Goal26C deliveries plus the two planning supplements (baseline target_status / start_status.txt)'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal26c receipt records another original commit than the frozen start'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal26D (the Goal26A, Goal26B and Goal26C deliveries stay uncommitted until the Goal 26 unified acceptance): '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2, 3)}
    assert chain[1].startswith(GOAL25_CLOSEOUT) and chain[2].startswith(GOAL25_PLANNING) and chain[3].startswith(GOAL24_CLOSEOUT), \
        'NEO HEAD~1..3 are not the Goal 25 close-out 5b1bf4db, the Goal 25 planning 783b6d13 and the Goal 24 close-out 17c8062f commits: '+str(chain)
    assert set(base['start_content']) == {'committed', 'uncommitted'} and 'Goal26A, Goal26B and Goal26C deliveries' in base['start_content']['uncommitted'], 'Baseline start content differs'
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
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal26c generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_start']

    # The uncommitted deliveries at the start: the 316 dirty start files (start_hashes.txt) are exactly the Goal26A, Goal26B and Goal26C receipts' changed files (a file several batches changed appears once)
    # plus the two planning-session supplements; each start hash is the newest receipt's after-hash that records the file (differences are recorded; only the shared records the main agent edits
    # after a package may differ).
    dirty = {}
    for line in START_HASHES.read_text(encoding='utf-8').splitlines():
        if line.strip():
            h, p = line.split(None, 1)
            dirty[p.strip().lstrip('*')] = h
    older_receipt, middle_receipt = read(OLDER_RECEIPT), read(MIDDLE_RECEIPT)
    assert older_receipt['sha256'] == middle_receipt['base_release_sha256'] and middle_receipt['sha256'] == prior_receipt['base_release_sha256'], \
        'The goal26a, goal26b and goal26c receipts do not chain through their base packages'
    deliveries = [(OLDER_OWNER, OLDER_RECEIPT, older_receipt), (MIDDLE_OWNER, MIDDLE_RECEIPT, middle_receipt), (PREVIOUS_OWNER, PREVIOUS_RECEIPT, prior_receipt)]
    changed_by = {owner: {e['path']: e for e in r['changed_files']} for owner, _, r in deliveries}
    delivery_paths = set().union(*changed_by.values())
    changed_by_several = sorted(p for p in delivery_paths if sum(1 for c in changed_by.values() if p in c) > 1)
    assert not delivery_paths & set(PLANNING_SUPPLEMENTS), 'A planning supplement is in a delivery receipt: '+str(sorted(delivery_paths & set(PLANNING_SUPPLEMENTS)))
    assert set(dirty) == delivery_paths | set(PLANNING_SUPPLEMENTS) and len(dirty) == START_STATUS_LINES, \
        'The 316 dirty start files are not the goal26a, goal26b and goal26c receipt changed files plus the two supplements: '+str(sorted(set(dirty) ^ (delivery_paths | set(PLANNING_SUPPLEMENTS)))[:6])
    assert all(base['files'].get(p) == h for p, h in dirty.items()), 'start_hashes.txt differs from the baseline hashes'
    # Oldest receipt first: the newest receipt that records a file owns it at the start and sets its after-hash; a later receipt's before-hash must be the earlier after-hash.
    dirty_owner, newest_after, chain_differs = {}, {}, set()
    for owner, _, _ in deliveries:
        for p, e in changed_by[owner].items():
            if p in newest_after and e.get('before_sha256') != newest_after[p]: chain_differs.add(p)
            newest_after[p] = e['after_sha256']
            dirty_owner[p] = owner
    for p in PLANNING_SUPPLEMENTS: dirty_owner[p] = PLANNING_OWNER
    chain_differs = sorted(chain_differs)
    delivery_differs = sorted(p for p, h in newest_after.items() if base['files'].get(p) != h)
    assert all(p in SHARED_AFTER_PACKAGE for p in delivery_differs), 'A Goal26A / Goal26B / Goal26C delivery file other than a shared record differs from its newest receipt after-hash at the Goal26D start: '+str(
        [p for p in delivery_differs if p not in SHARED_AFTER_PACKAGE])
    assert all(p in SHARED_AFTER_PACKAGE for p in chain_differs), 'A file several batches changed does not start the newer batch at the older after-hash: '+str([p for p in chain_differs if p not in SHARED_AFTER_PACKAGE])

    def delivery(owner, receipt_path, changed):
        mine = sorted(p for p in dirty if dirty_owner[p] == owner)
        return dict(owner=owner, receipt=receipt_path.relative_to(ROOT).as_posix(), receipt_changed_files=len(changed), files_owned_at_start=len(mine),
                    equal_to_receipt_after_sha256=sum(1 for p in mine if base['files'].get(p) == changed[p]['after_sha256']),
                    shared_records_differing_from_receipt_after_sha256={p: dict(newest_receipt_after_sha256=newest_after[p], start_sha256=base['files'][p], current_sha256=sha(ROOT/p))
                                                                        for p in delivery_differs if p in mine})
    goal26a_delivery = dict(delivery(OLDER_OWNER, OLDER_RECEIPT, changed_by[OLDER_OWNER]), also_changed_by_a_later_batch=sum(1 for p in changed_by[OLDER_OWNER] if dirty_owner[p] != OLDER_OWNER),
                            note='Files only the Goal26A batch changed are owned by goal26a (package build/migration/releases/goal26a); a file a later batch changed again is owned by the newest batch at this start.')
    goal26b_delivery = dict(delivery(MIDDLE_OWNER, MIDDLE_RECEIPT, changed_by[MIDDLE_OWNER]), also_changed_by_goal26c=sum(1 for p in changed_by[MIDDLE_OWNER] if dirty_owner[p] == PREVIOUS_OWNER),
                            note='The Goal26B delivery is uncommitted at this start (the user rule commits 26A-26D together after the Goal 26 unified acceptance); the files only it changed are owned by goal26b '
                                 '(package build/migration/releases/goal26b).')
    goal26c_delivery = dict(delivery(PREVIOUS_OWNER, PREVIOUS_RECEIPT, changed_by[PREVIOUS_OWNER]), files_also_changed_by_goal26a_or_goal26b=sum(1 for p in changed_by[PREVIOUS_OWNER] if p in changed_by[OLDER_OWNER] or p in changed_by[MIDDLE_OWNER]),
                            chain_before_sha256_differing_from_older_after_sha256=chain_differs,
                            note='The Goal26C delivery is uncommitted at this start (package build/migration/releases/goal26c); its files are owned by goal26c at this start. A path an earlier batch also changed '
                                 'records the newest delivery as before_sha256.')
    planning_supplements = {p: dict(owner=PLANNING_OWNER, start_sha256=base['files'][p], current_sha256=sha(ROOT/p),
                                    note='Planning-session supplement of 2026-10-22, uncommitted at the start, in no receipt. '+('GOAL26D.md is also this batch task book and delivery record (hashed by the new receipt).'
                                                                                              if p == 'migration/GOAL26D.md' else 'Must equal its start hash.')) for p in PLANNING_SUPPLEMENTS}

    # 2. Previous deliveries: the goal26c package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the start is not the goal26c package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal26c receipt list + the goal26c package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal26c receipt count + the goal26c release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal26c receipt'
    assert not base['previous_receipt_evidence_drift'], 'The goal26c receipt records evidence drift at the start: '+str(list(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal26c_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal26c receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal26d. Everything else equals its start hash.
    changes = changed_since_start(base)
    older_gametests = sorted(p for p in changes if p.startswith(OLDER_GAMETEST_DIR) and p.endswith('.java') and p in base['files'] and p not in UNCHANGED_JAVA)
    modified_java = MODIFIED_JAVA + OPTIONAL_JAVA + older_gametests
    production_java = NEW_JAVA + modified_java
    unassigned = sorted(p for p in changes if group(p, base) is None)
    need(not unassigned, f'Path changed since the Goal26D start that the owner table does not list (production outside the {len(MODIFIED_JAVA)} modified Java files, the {len(NEW_JAVA)} new classes incl. '
         f'RadiationMedicineGameTests, the {len(ASSETS)} resources, zh_cn.json and the mapping, a protected or frozen record, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal26A / Goal26B / Goal26C / Goal25 / Goal24 records or the Goal 26 planning documents (GOAL26-THREAD-PROMPTS.md, SURVIVAL-PLAYABILITY.md) changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal26D start: '+str(deleted)
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
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository (main-notes.md: the linked sessions goal26a / goal26b / goal26c idle). '
                                               'The batch ran under the main agent with a builder (production), a GameTest verifier (RadiationMedicineGameTests, verify_goal26d_medicine.py, Gradle), a read-only '
                                               'reviewer and this packaging verifier; each wrote only its named files (scope-before / scope-after snapshots of the verifiers are indexed as evidence). The main '
                                               'agent edited the migration/ records, zh_cn.json and the mapping and applied the review fixes (a comment-only correction in NtmConfig and the GOAL26D-ACCEPTANCE wording). '
                                               'migration/GOAL26.md and GOAL26D.md are edited by the main agent of this batch; the planning session of 2026-10-22 had edited GOAL26D.md and GOAL26-THREAD-PROMPTS.md '
                                               'before the start (planning-2026-10-22-26d owns those start bytes).',
                             goal26_md=dict(start_sha256=base['files'][GOAL26_RECORD], current_sha256=goal26_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p)) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p, base), owner=OWNER, owners=[OWNER], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p),
                        before_owner=dirty_owner.get(p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal26D takes no new snapshot)'
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
    # Added-code rules: the lines the batch adds to the existing registration, datagen and config files are exactly the lines of the owner table (comments and blank lines excepted); the language provider
    # is judged by its key list above and the recipe provider by the generated recipe JSON against the parsed original rows.
    added_code_facts = {}
    for p, rule in ADDED_CODE_RULES.items():
        if p not in start_text: continue
        live_lines = lines_of((ROOT/p).read_bytes())
        inserted = insertions(lines_of(start_text[p]), live_lines)
        if inserted is None: continue
        code_lines = [l.strip() for _, l in inserted if not is_comment(l)]
        stray = [l for l in code_lines if not rule.fullmatch(l)]
        need(not stray, f'{p} adds code lines the owner table does not allow (only the batch lines): {[l[:90] for l in stray[:4]]}')
        added_code_facts[p] = dict(added_code_lines=len(code_lines), added_comment_or_blank_lines=len(inserted) - len(code_lines))
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
        'The start mapping does not hold the groups of 24B-26C (rbmk-fuel ... hazmat-suits) and not yet the Goal26D group'
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
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal26c totals'
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal26c totals {totals} + {len(KEYS)}')
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal26c generated tree'
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
    # The configuration key has a translation key but no language entry by design (Goal 25 decision, LOCALIZATION.md): it is in none of the three language files, and CommonConfig names it.
    config_translation = dict(key=CONFIG_TRANSLATION_KEY, in_en_us=CONFIG_TRANSLATION_KEY in en_now, in_zh_cn=CONFIG_TRANSLATION_KEY in zh_now, in_map=CONFIG_TRANSLATION_KEY in map_now,
                              named_in_common_config=bool(re.search(r'\.translation\("'+re.escape(CONFIG_TRANSLATION_KEY)+r'"\)', neo_text(COMMON_CONFIG))))
    need(not (config_translation['in_en_us'] or config_translation['in_zh_cn'] or config_translation['in_map']) and config_translation['named_in_common_config'],
         f'the configuration translation key {CONFIG_TRANSLATION_KEY} must be named by CommonConfig and have no language entry: {config_translation}')
    # sounds.json (generated): exactly the two new events, nothing changed or removed; each event plays the imported file of the same name.
    sounds_start, sounds_now = start_json(base, GENERATED_SOUNDS), read(ROOT/GENERATED_SOUNDS)
    sounds_delta = lang_delta(sounds_start, sounds_now)
    need(sounds_delta == dict(added=['item.radaway', 'item.syringe'], removed=[], changed=[]), f'generated sounds.json delta is not the two new events (no event changed): {sounds_delta}')
    sound_events = {k: sounds_now.get(k) for k in ('item.radaway', 'item.syringe')}
    need(sound_events == {'item.radaway': {'sounds': ['hbmsntm:tool/radaway']}, 'item.syringe': {'sounds': ['hbmsntm:tool/stim']}}, f'generated sounds.json events differ from the original sounds.json:117-118: {sound_events}')
    sound_files = {n: dict(exists=(ROOT/(ASSETS_ROOT+'sounds/'+n+'.ogg')).is_file()) for n in SOUND_FILES}
    need(all(v['exists'] for v in sound_files.values()), f'imported sound files missing: {sound_files}')
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

    hazard_notes = ' '.join(by_id.get('hazard-system', {}).get('notes', []))
    need('G26D' in hazard_notes, 'features.json hazard-system notes do not record that RADX / RADAWAY have a source since G26D')

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
    medicine_test_names = sorted(GAMETEST_METHOD.findall((ROOT/MEDICINE_TESTS).read_text(encoding='utf-8'))) if (ROOT/MEDICINE_TESTS).is_file() else []
    medicine_annotations = annotations(ROOT/MEDICINE_TESTS) if (ROOT/MEDICINE_TESTS).is_file() else 0
    need(bool(medicine_test_names) and medicine_annotations == len(medicine_test_names), f'{MEDICINE_TESTS} holds {medicine_annotations} @GameTest annotations and {len(medicine_test_names)} parsed methods')
    need(gametest_added == medicine_annotations, f'GameTest sources grew by {gametest_added} tests, RadiationMedicineGameTests holds {medicine_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in medicine_test_names), 'GameTest log lacks "[hbm-medicine] <name> passed" for: '+str([n for n in medicine_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal26d/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal26d/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal26d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal26d/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal26d/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in modified_java if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal26d/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in modified_java if p in changes) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal26c final run plus the Goal26D verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1 + len(EXTRA_FINAL_SUITES)
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal26c final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal26D suite is already in the goal26c final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal26d/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE} | EXTRA_FINAL_SUITES, 'Final run suites differ from the goal26c final set + the Goal26D verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE} | EXTRA_FINAL_SUITES))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal26d/'+VERIFY_REPORT+' (tools/migration/verify_goal26d_medicine.py report)'):
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
        verifier_references = sorted(set(re.findall(r'(?:ItemPill|ItemSimpleConsumable|VersatileConfig|PotionConfig|ConsumableRecipes|EntityDamageUtil|HbmLivingProps|ModItems)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        # The verifier ran against the final GameTest log and expected the sources' total.
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal26c compare target paths (which hold the 24A-26C paths) plus this batch's compare-inventory paths).
    cmp26a = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal26c/compare.json differs from the goal26c receipt'
    c26a_added = sorted(p for p in compare_paths(cmp26a['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c26a_modified = sorted(p for p in compare_paths(cmp26a['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(c26a_added) | set(c26a_modified) | set(own_target))
    expected_added = sorted(set(c26a_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal26d/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-26c paths + %d of this batch)' % (
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
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal26c (goal26c compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal26c_paths=len(c26a_added) + len(c26a_modified), goal26d_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the groups of 24B-26C.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-26C)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal26d.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal26c) package (run the final build)'):
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
            sounds_jar = lang_delta(json.loads(prior.read(SOUNDS_ENTRY)), json.loads(jar.read(SOUNDS_ENTRY)))
            need(sounds_jar == sounds_delta, f'JAR sounds.json delta against the previous package is not the two new events: {sounds_jar}')
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
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY, SOUNDS_ENTRY, 'META-INF/MANIFEST.MF'): owner = [OWNER]
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
             'Changed Java sources and goal26d JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, SOUNDS_ENTRY} | generated_entries
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal26c_start=sorted(repinned),
                   delivery_files=dict(goal26a_goal26b_goal26c=len(delivery_paths), changed_by_several_batches=len(changed_by_several), owned_at_start={o: d['files_owned_at_start'] for o, d in
                                       (('goal26a', goal26a_delivery), ('goal26b', goal26b_delivery), ('goal26c', goal26c_delivery))}, planning_supplements=len(PLANNING_SUPPLEMENTS)),
                   delivery_shared_records_differing=delivery_differs, older_gametests_changed=older_gametests, added_code=added_code_facts,
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, sounds_delta=sounds_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   config_translation=config_translation,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, removed_comment_lines={p: len(v) for p, v in removed_comments.items()},
                   constants={k: c['neo'] == c.get('neo_expected', c['original']) for k, c in constants.items()}, sequences={k: v['neo'] == sorted(v.get('neo_expected', v['original'])) for k, v in sequences.items()},
                   counts={k: c['neo'] == c['expected'] for k, c in counts.items()},
                   recipes={k: v['matches'] for k, v in crafting.items()}, client_refs_in_common_classes=sorted(p for p, v in client_refs.items() if v),
                   gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_medicine_tests=medicine_test_names, final_suites_expected=final_expected,
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
    radiation_medicine = dict(neo=[p for p in NEW_JAVA + MODIFIED_JAVA], original=[p for p in O_SOURCES], constants=constants, sequences=sequences, counts=counts,
                              known_differences=KNOWN_DIFFERENCES, recipes=crafting, generated_item_models=generated_facts, sound_events=sound_events, sound_files=sound_files,
                              config_translation=config_translation, added_code=added_code_facts, original_references=original_refs,
                              defaults=dict(radx=dict(ticks=RADX_TICKS, amplifier=0, pill_use_duration_ticks=10, hunger=0, always_edible=True), potion_sickness_after_each_pill_seconds=5,
                                            siox=dict(asbestos=0, black_lung_cap=SIOX_BLACKLUNG_CAP, max_black_lung=MAX_BLACKLUNG, divisor=5),
                                            radaway=dict(ticks=140, amplifier=0, sums_with_running_effect=True), iv_empty=dict(health_cost=5, kills_at_or_below=0, real_player_only=True, returns='iv_blood', sound='item.syringe'),
                                            iv_blood=dict(heal=5, returns='iv_empty', sound='item.radaway'), potion_sickness_config=dict(section='potion', key='potionSickness', default='OFF', normal=1, terraria=2, terraria_factor=12),
                                            recipes='radx 2 powder_coal + fluorite; siox x8 powder_coal + powder_asbestos + nugget_bismuth (unreachable: bismuth); iv_empty x4 S/I/S ntm:any_rubbers + plate_iron; radaway iv_blood + powder_coal + pumpkin_seeds'),
                              note='Rad-X and SiOX are PillItem (ItemPill(0): always edible, hunger 0, 10 ticks; potion sickness 5 seconds first, then the effect: radx 3,600 ticks amplifier 0, siox asbestos 0 and black lung '
                                   'min(current, 144,000 / 5 = 28,800)); RadAway, the IV bag and the blood bag are SimpleConsumableItem (server action, one item consumed unless creative, sound at the player, container returned '
                                   'or dropped, radaway 140 ticks amplifier 0 summed with a running effect, iv_empty -5 health for a real player and magic death at 0 with iv_blood returned, iv_blood +5 health with iv_empty returned); '
                                   'the potionSickness common config (section potion, default OFF, NORMAL x1, TERRARIA x12, no curative items) is read through NtmConfig; two sound events item.syringe = tool/stim and item.radaway = '
                                   'tool/radaway; four crafting recipes. Not migrated or deferred: radaway_strong / radaway_flush, iv_xp, the syringes, the other pills, the SiOX LBSM gold recipe, the hit actions, and any '
                                   'client rendering (GameTest cannot render).')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), len(ASSETS), len(medicine_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=start_head[:8],
                   uncommitted_start=dict(status_entries=len(status_lines), description='the uncommitted Goal26A, Goal26B and Goal26C deliveries and the 2026-10-22 planning supplements on the Goal 26 planning commit 8954b531',
                                          base_release=previous_rel, status=status_lines,
                                          note=f'The start tree is HEAD 8954b531 plus the uncommitted Goal26A delivery ({len(changed_by[OLDER_OWNER])} files, packaged as goal26a), the uncommitted Goal26B delivery '
                                               f'({len(changed_by[MIDDLE_OWNER])} files, packaged as goal26b), the uncommitted Goal26C delivery ({len(changed_by[PREVIOUS_OWNER])} files, packaged as goal26c; '
                                               f'{len(changed_by_several)} files changed by more than one batch, {len(delivery_paths)} distinct) and the two planning supplements to migration/GOAL26D.md and '
                                               f'migration/GOAL26-THREAD-PROMPTS.md ({len(status_lines)} status lines); every tracked file and every untracked start file was hashed live before the first 26D write (freeze_start.py).'),
                   goal26a_delivery=goal26a_delivery, goal26b_delivery=goal26b_delivery, goal26c_delivery=goal26c_delivery, planning_supplements=planning_supplements,
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, build_libs_sha256_at_freeze=base['build_libs_jar_sha256_at_freeze'],
                                      reconstruction=base['reconstruction'], goal25_closeout_commit=chain[1], goal25_planning_commit=chain[2], goal24_closeout_commit=chain[3],
                                      note=f'The start tree is HEAD 8954b531 (the Goal 26 planning commit, local, not pushed) on top of the Goal 25 close-out commit 5b1bf4db on the Goal 25 planning '
                                           f'commit 783b6d13 on the pushed Goal 24 close-out commit 17c8062f, PLUS the uncommitted Goal26A, Goal26B and Goal26C deliveries and the two planning supplements ({len(status_lines)} '
                                           f'status lines). build/libs at the start AND at the freeze IS the goal26c package. The original did not move since 24A (aee05a40f). freeze_start.py hashed every '
                                           f'tracked and untracked start file live ({len(base["files"])} baseline hashes) before the first 26D write and copied the dirty start files and the files the batch '
                                           f'planned to touch ({len(base["copied_scope"])} baseline-files); paths this batch changes record the start hash as before_sha256 and their before_owner (goal26a / goal26b / goal26c for the '
                                           f'delivery files, planning-2026-10-22-26d for the two supplements).'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes], older_gametests_changed=older_gametests,
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, removed_comment_lines=removed_comments, removed_code_lines=removed_code, start_copies_supplement=[],
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   radiation_medicine=radiation_medicine,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 configuration_key=config_translation,
                                 note=f'{EXPECTED_KINDS.get("upstream", 0)} entries are upstream with the original English and Chinese verbatim (RadAway, Rad-X, SiOX and its description, IV Bag, Blood Bag; original '
                                      f'en_US.lang:3243-3244, 4154-4158, 4522-4523 / zh_CN.lang:2782-2783, 3590-3594, 3936-3937); {EXPECTED_KINDS.get("local", 0)} is local (item.hbmsntm.radx.desc: the Chinese "37%" becomes "37%%", '
                                      'the NEO escape for a literal percent). No existing key changes its English value; no deferred entry is added; the potionSickness configuration key has no language entry by design.'),
                   recipes=dict(crafting=crafting, not_registered=['siox LBSM gold-nugget variant (ConsumableRecipes.java:127)'],
                                note='Four crafting recipes (radx and radaway shapeless, siox x8 shapeless with the bismuth nugget, iv_empty x4 shaped; each generated JSON equal to its parsed original row from '
                                     'ConsumableRecipes.java). SiOX is unreachable in survival until bismuth has a source (creative tab only); iv_blood has no recipe, it comes from using an IV bag.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith('repinned_since_')},
                   repinned_since_goal26c_start={p: dict(goal26c_start_pin_sha256=h, goal26d_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok'), old_machine_suites_through=OLD_MACHINE_SUITES),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_medicine_tests=medicine_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per RadiationMedicineGameTests test (names in new_medicine_tests): what those tests '
                                      'assert about the pills, RadAway, the IV bags, potion sickness, the recipes and the older effects; the players are a GameTest mock Player and FakePlayers (neither a ServerPlayer on a connection '
                                      'nor a real client), sounds are observed as requests, effects tick by reflection; no client (eating animation, tooltips, creative tabs are not rendered), no real player, no saved world, '
                                      'no survival chain.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['hazmat_suits (the Goal26C-only key; Goal26D adds radiation_medicine; the hazmat constants, registry rows, recipes, enchantable tags and the assembly row are not carried)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun (the six old isolated suites through the goal26c wrapper), compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. '
                            'No in-game client test was run: the eating animation and sounds, effect icons, tooltips and Chinese UI, the item icons, the creative tabs, JEI, the config screen and the Geiger / dosimeter '
                            'readouts are unverified; no survival chain (crafting Rad-X, IV bags and RadAway, taking blood, using RadAway in a radiation field) in a world was run; no multiplayer or dedicated server beyond '
                            'GameTest; the Goal 26 unified acceptance checklist GOAL26D-ACCEPTANCE.md (merging all Goal 25 items) is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal26d JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal26c package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
