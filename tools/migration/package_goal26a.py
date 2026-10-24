"""Package Goal26A (the first batch of Goal 26, hazard system and radiation control: the hazard-system fixes of the radon block (GasRadonBlock), the gas-mask filter reads of ArmorUtil, the unregistered
filter and the null mod slots of ArmorRegistry / ArmorModHandler.pryMods, ArmorModHandler.removeMod keeping the other custom data, the HazmatRegistry.readConfig error handling and ItemModCladding.rad;
the hazard.* tooltip and ten status-effect names in English and Chinese; the Geiger counter, dosimeter, Geiger block, decontaminator and digamma diagnostic recipes; the four radiation absorber blocks
(RadAbsorberBlock) that remove chunk radiation; block_graphite, lead and boron sand and glass; the RBMK lid glass, moderator, moderated fuel channel and moderated control rod recipes; the crystallizer
default row coal block -> graphite block; eight imported textures; 33 language keys and RadiationControlGameTests), cumulatively on the goal25d package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal26a.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal26a/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal26a/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal26a/baseline.json: NEO HEAD 8954b531 (the Goal 26 planning commit, local, parent 5b1bf4db = the Goal 25 close-out commit that committed 25A-25D, then
783b6d13 = the Goal 25 planning commit on the pushed Goal 24 close-out 17c8062f) with a CLEAN worktree (0 status lines): freeze_start.py hashed every tracked file live (10,266 hashes) before the first
26A write and copied the 29 files the batch planned to touch (baseline-files/). There is no uncommitted start delivery and no start_hashes.txt. build/libs at the start AND at the freeze IS the goal25d
package (baseline build_libs_jar_sha256_at_start / _at_freeze). The original HEAD aee05a40f did not move since 24A, so there is no upstream classification and no new snapshot. Between the goal25d
package and this start the Goal 25 close-out and the Goal 26 planning commit changed records only; that set is computed here (the goal25d receipt's final hashes against the 26A baseline, cross-checked
against git diff 783b6d13..8954b531), owned by goal25-closeout-and-goal26-planning, and must still equal the start unless a record this batch writes. The previous-receipt drift recorded at the freeze
(migration/GOAL25D-ACCEPTANCE.md) is explained by that close-out (before / after hashes; the old receipt is not rewritten). Every change since the start is computed from the baseline file hashes (not
from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with their start bytes (baseline-files, else the
start-commit blob). The JAR delta against the goal25d package is attributed per entry (goal26a only); any entry without exactly one owner fails. Counts that records quote (suites, GameTests,
generated resources, classes, releases, language keys) are computed here, never hard-coded; the previous package's SHA-256, size and receipt hashes are read from the files and the baseline.

The receipts that hash records (goal21a..goal25d, the review-g21d-hazard-fix receipt) already differ from some older hashes at the frozen start for the acceptance checklists, GOAL21D.md, GOAL22C.md,
goal21d-static-review.md, the goal24a working notes and (new) migration/GOAL25D-ACCEPTANCE.md; they are listed in the receipt as start drift and must still equal their Goal26A start hash; no receipt
is rewritten and no other protected path may drift. The Goal25 and Goal24 records and GOAL26B-D.md, GOAL26-THREAD-PROMPTS.md and SURVIVAL-PLAYABILITY.md must equal their start hash; migration/GOAL26.md
is edited by the main agent (a shared record), GOAL26A.md is the task book and delivery record (hashed by the receipt) and GOAL26A-ACCEPTANCE.md the batch's acceptance checklist (hashed, written, not run).

Like the earlier packagers of 24B..25D this one has a single compare run (build/migration/goal26a/compare.json against the snapshot review-aee05a40f10f.json taken at the end of 24A:
original 0/0/0, target = exactly the goal25d compare target paths (24A-25D, read from build/migration/goal25d/compare.json) plus this batch's compare-inventory paths), no upstream
classification; it adds the radiation_control constants (checked against the original and NEO source texts, the recipes against the parsed original rows). The Goal25D-only receipt key
rbmk_crane is dropped."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import owner_class
from package_goal19c import tree_files
from package_review_g20_display_fixes import protected_drift as display_protected_drift, split_drift
from migration import BUILD_FILES, matches as feature_matches
from package_goal21d import (LOCALIZATION_RECORD, STAMP, EN, ZH_ENTRY, EN_ENTRY, lang_delta, compare_paths, lines_of,
                             eol_counts, insertions, in_compare_inventory, changed_since_start)
from package_goal22a import annotations, GAMETEST_ANNOTATION
from package_goal22b import (git_ro, edit_counts, stale_diff, receipt_protected, start_drift_paths,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE
from package_goal23b import report_problems
from package_goal24a import original_text, original_line, original_blob, lang_file, provider_keys as base_provider_keys, SOURCE_HEAD
from package_goal24c import captured, normalize_value
from package_goal24e import split_args, OneOf, jsonable
from package_goal25d import OUT as GOAL25D_OUT, BASELINE as GOAL25D_BASELINE, protected_paths as goal25d_protected_paths

OUT = ROOT/'build/migration/goal26a'
BASELINE = OUT/'baseline.json'
STARTUP = OUT/'startup-verification.json'
START_FILES = OUT/'baseline-files'
START_STATUS = OUT/'start_status.txt'
START_HEAD = OUT/'start_head.txt'
REFERENCE_PREVIOUS = GOAL25D_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL25D_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal25d/hbmsntm-198A-goal25d.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal26a'
RELEASE_NAME = 'hbmsntm-198A-goal26a.jar'
OWNER = 'goal26a'
CLOSEOUT_OWNER = 'goal25-closeout-and-goal26-planning'
PLANNING_PREFIX = '8954b531'
GOAL25_CLOSEOUT = '5b1bf4db'
GOAL25_PLANNING = '783b6d13'
GOAL24_CLOSEOUT = '17c8062f'
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'

# Production (owner goal26a), NEW (handoff-packaging.md; builder-report.md names the final classes: if a class is named differently or a helper class is added, edit this
# list, --check reports the difference as an unassigned src/ path).
NEW_JAVA = [J+p+'.java' for p in ('blocks/generic/RadAbsorberBlock', 'gametest/RadiationControlGameTests')]
(ABSORBER_BLOCK, RADIATION_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails; a review fix may add a file: --check reports it
# as an unassigned src/ path instead of failing silently). SmokeGameTests: the crystallizer default row count 46 -> 47 (main agent's scope note, lines 142-143).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blocks/gas/GasRadonBlock', 'util/ArmorUtil', 'util/ArmorRegistry', 'handler/ArmorModHandler', 'handler/HazmatRegistry', 'items/armor/ItemModCladding', 'blocks/NtmBlocks',
    'inventory/NtmCreativeTabs', 'inventory/recipes/CrystallizerRecipes', 'main/NuclearTechModClient', 'datagen/NtmRecipeProvider', 'datagen/NtmBlockStateProvider',
    'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider', 'datagen/NtmLanguageProvider', 'gametest/SmokeGameTests', 'gametest/RBMKControlSteamGameTests',
    'gametest/RBMKReactorGameTests', 'gametest/RBMKCoreGameTests')]
(GAS_RADON, ARMOR_UTIL, ARMOR_REGISTRY, ARMOR_MOD, HAZMAT, CLADDING, BLOCKS, CREATIVE_TABS, CRYSTALLIZER, CLIENT_MOD, RECIPE_PROVIDER, BLOCK_STATE_PROVIDER, LOOT_PROVIDER,
 TAG_PROVIDER, PROVIDER, SMOKE_TESTS, CONTROL_STEAM_TESTS, REACTOR_TESTS, CORE_TESTS) = MODIFIED_JAVA
OPTIONAL_JAVA = []
# Must stay byte-identical to the start (the handoff list: the radiation handler, the hazard registry, the other five gas blocks, the asbestos / coal hazard types, the decontaminator
# block entity, the detectors and the older hazard GameTest).
UNCHANGED_JAVA = [J+p+'.java' for p in (
    'handler/radiation/ChunkRadiationHandlerSimple', 'handler/radiation/ChunkRadiationManager', 'hazard/HazardRegistry', 'blocks/gas/GasRadonDenseBlock', 'blocks/gas/GasMeltdownBlock',
    'blocks/gas/GasMonoxideBlock', 'blocks/gas/GasAsbestosBlock', 'blocks/gas/GasCoalBlock', 'hazard/type/HazardTypeAsbestos', 'hazard/type/HazardTypeCoal',
    'blockentity/machine/DecontaminatorBlockEntity', 'items/tools/GeigerCounterItem', 'items/tools/DosimeterItem', 'gametest/HazardGameTests')]
# Modified sources whose compiled class need not change (comment-only edits); every other modified source must show a modified class in the JAR.
SAME_CLASS_JAVA = []
NO_CLASS_JAVA = []
# JAR classes whose source is unchanged since the start and that differ from the previous package only in recompiled debug names. The Goal26A build
# recompiled RBMKRecyclingGameTests$1 (an anonymous RBMKControlManualBlockEntity) with the constructor's local-variable names arg0 / arg1 back to pos / state,
# the reverse of the Goal25B entry (package_goal25b.py RECOMPILE_ONLY); its source is unchanged since the start and javap shows no other difference.
RECOMPILE_ONLY = {'com/hbm/gametest/RBMKRecyclingGameTests$1.class': ((b'\x01\x00\x03pos', b'\x01\x00\x04arg0'), (b'\x01\x00\x05state', b'\x01\x00\x04arg1'))}
RECOMPILE_OWNER = 'recompile-debug-names'
ANVIL_RECIPES = J+'inventory/recipes/anvil/AnvilRecipes.java'
# Insert-only against the start bytes (registration and datagen lines, the Chinese file and the mapping, the one-line cladding assignment). Every other modified source is held to
# ALLOWED_REMOVED_CODE: the start CODE lines it may drop, by prefix (an empty tuple allows only comment lines to go). Exact lines of the builder's tree; a review fix that touches more
# is reported with the stray lines.
STRICT_INSERT_ONLY = [CLADDING, BLOCKS, CREATIVE_TABS, CLIENT_MOD, BLOCK_STATE_PROVIDER, LOOT_PROVIDER, PROVIDER, ZH_INPUT, LOCALIZATION_RECORD]
ALLOWED_REMOVED_CODE = {
    GAS_RADON: ('if (!ArmorRegistry.hasProtection(livingEntity, EquipmentSlot.HEAD, HazardClass.PARTICLE_FINE)) {',),
    ARMOR_UTIL: ('if (mods[ArmorModHandler.HELMET_ONLY].isEmpty() && mods[ArmorModHandler.HELMET_ONLY].getItem() instanceof IGasMask)', 'CompoundTag attach = new CompoundTag();',
                 'filter.save(level.registryAccess(), attach);', 'tag.put(FILTER_KEY, attach);', 'filter.setDamageValue(filter.getDamageValue() + damage);',
                 'if (filter.getDamageValue() > filter.getMaxDamage()) {'),
    ARMOR_REGISTRY: ('components.add(Component.literal("Hold <")', '.append(Component.literal("LSHIFT")', '.append(Component.literal("> to display protection info")', ');',
                     'if (!filter.isEmpty()) {', 'List<HazardClass> filProt = (List<HazardClass>) hazardClasses.get(filter.getItem()).clone();'),
    ARMOR_MOD: ('if(armor.isEmpty()) return;', 'if(!tag.contains(MOD_COMPOUND_KEY)) tag.put(MOD_COMPOUND_KEY, new CompoundTag());', 'if(mods.isEmpty()) clearMods(armor);',
                'TagsUtil.putCustomData(armor, mods);', 'Optional<ItemStack> stack = ItemStack.parse(level.registryAccess(), cmp);',
                'CompoundTag cmp = new CompoundTag();', 'mod.save(level.registryAccess(), cmp);', 'mods.put(MOD_SLOT_KEY + slot, cmp);'),
    HAZMAT: ('private static HashMap<Item, Double> readConfig(File config) {', 'try {', 'JsonObject json = gson.fromJson(new FileReader(config), JsonObject.class);',
             'JsonObject object = (JsonObject) element;', 'Item item = BuiltInRegistries.ITEM.get(', 'double resistance =', 'conf.put(item, resistance);', '} catch(IOException ex) {',
             'ex.printStackTrace();'),
    TAG_PROVIDER: ('NtmBlocks.SAND_QUARTZ.get()',),
    RECIPE_PROVIDER: (),
    CRYSTALLIZER: ('return "Ore acidizer (crystallizer) recipes.',),
    SMOKE_TESTS: ('check(rows == 46,',),
    # Stale "deliberately not registered" recipe assertions of the older RBMK GameTests, updated by the GameTest verifier (the main agent's scope note): the rbmk_control_mod / rbmk_rod_mod /
    # rbmk_moderator / rbmk_lid_glass recipes are registered by Goal26A, so the not-loaded checks, the all-recipe scans and the log lines change.
    CONTROL_STEAM_TESTS: ('check(level.getRecipeManager().byKey(id("rbmk_control_mod")).isEmpty()', 'for(RecipeHolder<?> holder : level.getRecipeManager().getRecipes()) check(!holder.value()',
                          'LOGGER.info("[hbm-rbmk-cs] recipes and registrations: six rows match,'),
    REACTOR_TESTS: ('check(level.getRecipeManager().byKey(id("rbmk_rod_mod")).isEmpty()', 'check(!holder.value().getResultItem(level.registryAccess()).is(modItem), "recipe " + holder.id() + " produces rbmk_rod_mod");',
                    'LOGGER.info("[hbm-rbmk-reactor] recipes: rbmk_rod C/R/C matches;'),
    CORE_TESTS: ('check(!skipped.contains(result.getItem())', 'LOGGER.info("[hbm-rbmk-core] recipes: ass.rbmk and 7 crafting rows'),
}
# The 8 imported original textures: NEO target -> original path, derived by the layout rules of the ownership record (textures/blocks -> textures/block, lowercase, names kept; the absorber
# blocks point at block/absorber*). block_graphite.png is reused unchanged (Goal21C import).
ASSETS = {ASSETS_ROOT+'textures/block/'+n+'.png': O_RES+'textures/blocks/'+n+'.png'
          for n in ('absorber', 'absorber_red', 'absorber_green', 'absorber_pink', 'sand_lead', 'sand_boron', 'glass_lead', 'glass_boron')}
GRAPHITE_TEXTURE = ASSETS_ROOT+'textures/block/block_graphite.png'
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
PICKAXE_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
SHOVEL_ENTRY = 'data/minecraft/tags/block/mineable/shovel.json'
GENERATED = [STAMP, EN, GENERATED_ROOT+PICKAXE_ENTRY, GENERATED_ROOT+SHOVEL_ENTRY]
# The nine new blocks: registry id -> (NtmBlocks constant, block texture).
BLOCK_TABLE = {'rad_absorber': ('RAD_ABSORBER', 'absorber'), 'rad_absorber_red': ('RAD_ABSORBER_RED', 'absorber_red'), 'rad_absorber_green': ('RAD_ABSORBER_GREEN', 'absorber_green'),
               'rad_absorber_pink': ('RAD_ABSORBER_PINK', 'absorber_pink'), 'block_graphite': ('BLOCK_GRAPHITE', 'block_graphite'), 'sand_lead': ('SAND_LEAD', 'sand_lead'),
               'sand_boron': ('SAND_BORON', 'sand_boron'), 'glass_lead': ('GLASS_LEAD', 'glass_lead'), 'glass_boron': ('GLASS_BORON', 'glass_boron')}
PICKAXE_NEW = sorted('hbmsntm:'+b for b in ('rad_absorber', 'rad_absorber_red', 'rad_absorber_green', 'rad_absorber_pink', 'block_graphite', 'glass_lead', 'glass_boron'))
SHOVEL_NEW = sorted('hbmsntm:'+b for b in ('sand_lead', 'sand_boron'))
# The 20 crafting / smelting recipes (builder-report.md section D): recipe id -> (kind, original path, selector regex of the single original line, NEO result id). The original rows are
# parsed from the stored blobs at aee05a40f, their key expressions translated through KEY_TABLE and compared with the generated JSON.
O_TOOLRECIPES_PATH, O_CRAFTING_PATH, O_SMELTING_PATH = 'crafting/ToolRecipes.java', 'main/CraftingManager.java', 'crafting/SmeltingRecipes.java'
RECIPES = {
    'geiger_counter': ('shaped', O_TOOLRECIPES_PATH, r'addRecipeAuto\(new ItemStack\(ModItems\.geiger_counter, 1\)', 'hbmsntm:geiger_counter'),
    'dosimeter': ('shaped', O_TOOLRECIPES_PATH, r'addRecipeAuto\(new ItemStack\(ModItems\.dosimeter, 1\)', 'hbmsntm:dosimeter'),
    'geiger': ('shapeless', O_TOOLRECIPES_PATH, r'addShapelessAuto\(new ItemStack\(ModBlocks\.geiger\)', 'hbmsntm:geiger'),
    'digamma_diagnostic': ('shapeless', O_TOOLRECIPES_PATH, r'addShapelessAuto\(new ItemStack\(ModItems\.digamma_diagnostic\)', 'hbmsntm:digamma_diagnostic'),
    'rad_absorber': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModBlocks\.rad_absorber, 1, EnumAbsorberTier\.BASE\.ordinal\(\)\),\s*new Object', 'hbmsntm:rad_absorber'),
    'rad_absorber_red': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModBlocks\.rad_absorber, 1, EnumAbsorberTier\.RED\.ordinal\(\)\),\s*new Object', 'hbmsntm:rad_absorber_red'),
    'rad_absorber_green': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModBlocks\.rad_absorber, 1, EnumAbsorberTier\.GREEN\.ordinal\(\)\),\s*new Object', 'hbmsntm:rad_absorber_green'),
    'rad_absorber_pink': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModBlocks\.rad_absorber, 1, EnumAbsorberTier\.PINK\.ordinal\(\)\),\s*new Object', 'hbmsntm:rad_absorber_pink'),
    'decontaminator': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModBlocks\.decon, 1\)', 'hbmsntm:decontaminator'),
    'sand_boron': ('shapeless', O_CRAFTING_PATH, r'addShapelessAuto\(new ItemStack\(ModBlocks\.sand_mix, 8, EnumSandType\.BORON\.ordinal\(\)\)', 'hbmsntm:sand_boron'),
    'sand_lead': ('shapeless', O_CRAFTING_PATH, r'addShapelessAuto\(new ItemStack\(ModBlocks\.sand_mix, 8, EnumSandType\.LEAD\.ordinal\(\)\)', 'hbmsntm:sand_lead'),
    'glass_boron_from_smelting_sand_boron': ('smelting', O_SMELTING_PATH, r'EnumSandType\.BORON\.ordinal\(\)\), new ItemStack\(ModBlocks\.glass_boron\)', 'hbmsntm:glass_boron'),
    'glass_lead_from_smelting_sand_lead': ('smelting', O_SMELTING_PATH, r'EnumSandType\.LEAD\.ordinal\(\)\), new ItemStack\(ModBlocks\.glass_lead\)', 'hbmsntm:glass_lead'),
    'rbmk_lid_glass': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModItems\.rbmk_lid_glass, 4\), new Object\[\] \{ "LLL", "BBB"', 'hbmsntm:rbmk_lid_glass'),
    'rbmk_lid_glass_boron_top': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModItems\.rbmk_lid_glass, 4\), new Object\[\] \{ "BBB", "LLL"', 'hbmsntm:rbmk_lid_glass'),
    'rbmk_moderator': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModBlocks\.rbmk_moderator, 1\)', 'hbmsntm:rbmk_moderator'),
    'rbmk_control_mod': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModBlocks\.rbmk_control_mod, 1\)', 'hbmsntm:rbmk_control_mod'),
    'rbmk_rod_mod': ('shaped', O_CRAFTING_PATH, r'addRecipeAuto\(new ItemStack\(ModBlocks\.rbmk_rod_mod, 1\)', 'hbmsntm:rbmk_rod_mod'),
}
# The 1 <-> 9 pair (MineralRecipes.java:40 add1To9Pair): generated through NEO's addMaterialBlockRecipe as two recipes.
GRAPHITE_PAIR = {'block_graphite_from_9_ingot_graphite': 'shaped', 'ingot_graphite_from_block_graphite': 'shapeless'}
RECIPE_IDS = sorted(list(RECIPES) + list(GRAPHITE_PAIR))
# Recipes that need an ingredient with no survival source in NEO yet (GOAL26 decision 4); recorded in the receipt.
UNREACHABLE = {'digamma_diagnostic': 'billet_polonium (polonium-210 billet)', 'rad_absorber_pink': 'ingot_saturnite and powder_nitan_mix', 'rbmk_control_mod': 'nugget_bismuth (bismuth)',
               'rbmk_rod_mod': 'nugget_bismuth (bismuth)'}
EXPECTED_GENERATED_BASE = sorted(
    [f'assets/hbmsntm/blockstates/{b}.json' for b in BLOCK_TABLE] + [f'assets/hbmsntm/models/block/{b}.json' for b in BLOCK_TABLE] + [f'assets/hbmsntm/models/item/{b}.json' for b in BLOCK_TABLE]
    + [f'data/hbmsntm/loot_table/blocks/{b}.json' for b in BLOCK_TABLE] + [f'data/hbmsntm/recipe/{r}.json' for r in RECIPE_IDS])
ADVANCEMENT = {r: re.compile(r'data/hbmsntm/advancement/recipes/[a-z_]+/'+re.escape(r)+r'\.json') for r in RECIPE_IDS}
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, PICKAXE_ENTRY, SHOVEL_ENTRY])
NEW_TOOLS = ['tools/migration/verify_goal26a_radiation_control.py', 'tools/migration/package_goal26a.py']
TOOLS = NEW_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal26a-* or GOAL26A-* record is hashed as well.
REPORTS = ['migration/GOAL26A.md', 'migration/GOAL26A-ACCEPTANCE.md', 'migration/goal26a-static-review.md', 'migration/goal26a-localization-review.json',
           'migration/goal26a-resource-ownership.json', 'migration/goal26a-materials-review.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal26a-[^/]+\.(json|md)|GOAL26A-[^/]+\.md)')
GOAL26_RECORD = 'migration/GOAL26.md'
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/FOUNDATIONS.md',
                  'migration/RESOURCE-OWNERSHIP.md', GOAL26_RECORD]
# Shared records the batch may leave untouched (RESOURCE-OWNERSHIP.md "if touched"). FOUNDATIONS.md is required by the handoff's shared-record list; relax here if the batch leaves it alone.
OPTIONAL_RECORDS = ['migration/RESOURCE-OWNERSHIP.md']
# The Goal 26 planning documents of the other batches: no change is expected in this batch.
PLANNING_FROZEN = ['migration/GOAL26B.md', 'migration/GOAL26C.md', 'migration/GOAL26D.md', 'migration/GOAL26-THREAD-PROMPTS.md', 'migration/SURVIVAL-PLAYABILITY.md']
FROZEN_RECORD = re.compile(r'migration/(GOAL25[^/]*\.md|goal25[abcd]-[^/]+|GOAL24[^/]*\.md|goal24[^/]*|GOAL26[BCD][^/]*\.md|GOAL26-THREAD-PROMPTS\.md|SURVIVAL-PLAYABILITY\.md)')
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED_BASE + the advancements.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]
# The new language keys: NEO key -> (original key or None, expected map kind). 31 upstream with the original English and Chinese verbatim, 2 local: hazard.gas_inert (the original Chinese
# mistranslates Asphyxiants) and hazard.hold_shift (the original text is hard-coded in ModEventHandlerClient.java:700-705).
SOURCE_KEYS = {
    'block.hbmsntm.rad_absorber': ('tile.rad_absorber.base.name', 'upstream'), 'block.hbmsntm.rad_absorber_red': ('tile.rad_absorber.red.name', 'upstream'),
    'block.hbmsntm.rad_absorber_green': ('tile.rad_absorber.green.name', 'upstream'), 'block.hbmsntm.rad_absorber_pink': ('tile.rad_absorber.pink.name', 'upstream'),
    'block.hbmsntm.block_graphite': ('tile.block_graphite.name', 'upstream'), 'block.hbmsntm.sand_lead': ('tile.sand_lead.name', 'upstream'),
    'block.hbmsntm.sand_boron': ('tile.sand_boron.name', 'upstream'), 'block.hbmsntm.glass_lead': ('tile.glass_lead.name', 'upstream'), 'block.hbmsntm.glass_boron': ('tile.glass_boron.name', 'upstream'),
    'effect.hbmsntm.taint': ('potion.hbm_taint', 'upstream'), 'effect.hbmsntm.radiation': ('potion.hbm_radiation', 'upstream'), 'effect.hbmsntm.bang': ('potion.hbm_bang', 'upstream'),
    'effect.hbmsntm.radx': ('potion.hbm_radx', 'upstream'), 'effect.hbmsntm.lead': ('potion.hbm_lead', 'upstream'), 'effect.hbmsntm.radaway': ('potion.hbm_radaway', 'upstream'),
    'effect.hbmsntm.phosphorus': ('potion.hbm_phosphorus', 'upstream'), 'effect.hbmsntm.stability': ('potion.hbm_stability', 'upstream'),
    'effect.hbmsntm.potionsickness': ('potion.hbm_potionsickness', 'upstream'), 'effect.hbmsntm.death': ('potion.hbm_death', 'upstream'),
    'hazard.protect': ('hazard.prot', 'upstream'), 'hazard.no_protect': ('hazard.noprot', 'upstream'), 'hazard.never_protects': ('hazard.neverProtects', 'upstream'),
    'hazard.bacteria': ('hazard.bacteria', 'upstream'), 'hazard.corrosive': ('hazard.corrosive', 'upstream'), 'hazard.gas_chlorine': ('hazard.gasChlorine', 'upstream'),
    'hazard.gas_inert': ('hazard.gasInert', 'local'), 'hazard.gas_monoxide': ('hazard.gasMonoxide', 'upstream'), 'hazard.light': ('hazard.light', 'upstream'),
    'hazard.nerve_agent': ('hazard.nerveAgent', 'upstream'), 'hazard.particle_coarse': ('hazard.particleCoarse', 'upstream'), 'hazard.particle_fine': ('hazard.particleFine', 'upstream'),
    'hazard.sand': ('hazard.sand', 'upstream'), 'hazard.hold_shift': (None, 'local')}
KEYS = {k: v[0] for k, v in SOURCE_KEYS.items()}
EXPECTED_KINDS = dict(Counter(v[1] for v in SOURCE_KEYS.values()))
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*(?:@\w+(?:\([^)]*\))?\s*)*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-radiation-control] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start or written by the sessions of the batch.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'start_compile.log', 'start_status.txt', 'start_head.txt', 'pre_commit_status.txt',
                  'pre_commit_head.txt', 'planning-commit-msg.txt', 'png_stats.py', 'import_resources.py', 'add_zh.py', 'main-notes.md', 'handoff-builder.md', 'builder-report.md',
                  'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md', 'verifier-report.md', 'review-report.md', 'chain.sh', 'make_production_diff.py')
# Review files under OUT the main agent names when it knows them; each must exist and is indexed by the receipt. Extend this list from the real run; --check lists the top-level OUT files
# that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'packaging-progress.md', 'packaging-report.md',
                   'verifier-pkg/scope-before.txt', 'verifier-pkg/scope-after.txt', 'verifier-gt/scope-before.txt', 'verifier-gt/scope-after.txt', 'builder_compile.log',
                   'builder_rundata.log', 'builder_build.log', 'builder_pre_rundata_generated.txt', 'builder_post_rundata_generated.txt', 'review-diff.patch', 'review-new-files.txt',
                   'verifier-progress.md', 'update_features.py', 'update_features2.py', 'features.before.json', 'new-recipe-adv.txt', 'make_loc_review.py',
                   'make_materials_review.py', 'verify-final.out', 'compare.log', 'localization-final.log', 'resources-audit-final.log', 'packaged-resources-final.log')
GAMETEST_LOG = 'build/migration/goal26a/gametest-final.log'
NEW_SUITE = 'verify_goal26a_radiation_control.py --gametest-log build/migration/goal26a/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_HAZARD, FEATURE_DETECTION = 'hazard-system', 'radiation-detection'
NEW_FEATURES = (FEATURE_HAZARD, FEATURE_DETECTION)
# The groups the snapshot of the end of 24A predates (24B rbmk-fuel, 24C rbmk-reactor, 24D rbmk-control and rbmk-steam, 24E rbmk-console, 25A rbmk-storage and rbmk-recycling,
# 25B rbmk-outgasser, 25C rbmk-autoloader, 25D rbmk-crane).
POST_SNAPSHOT_FEATURES = {'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling', 'rbmk-outgasser', 'rbmk-autoloader', 'rbmk-crane'}
RADIATION_NOTE = ('Goal26A: radon now contaminates unprotected players as in the original; absorber and decontaminator tests stay in a separately authorized disposable world. ')
MELTDOWN_NOTE = 'Goal26A: no new meltdown path; reactor tests stay in disposable worlds. '
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_RADON = ORIGINAL+'blocks/gas/BlockGasRadon.java'
O_ABSORBER = ORIGINAL+'blocks/generic/BlockAbsorber.java'
O_MODBLOCKS = ORIGINAL+'blocks/ModBlocks.java'
O_ARMORUTIL = ORIGINAL+'util/ArmorUtil.java'
O_ARMORREG = ORIGINAL+'util/ArmorRegistry.java'
O_ARMORMOD = ORIGINAL+'handler/ArmorModHandler.java'
O_HAZMAT = ORIGINAL+'handler/HazmatRegistry.java'
O_CLADDING = ORIGINAL+'items/armor/ItemModCladding.java'
O_TOOLRECIPES = ORIGINAL+O_TOOLRECIPES_PATH
O_CRAFTING = ORIGINAL+O_CRAFTING_PATH
O_SMELTING = ORIGINAL+O_SMELTING_PATH
O_MINERAL = ORIGINAL+'crafting/MineralRecipes.java'
O_CRYSTAL = ORIGINAL+'inventory/recipes/CrystallizerRecipes.java'
O_CLIENT_EVENTS = ORIGINAL+'main/ModEventHandlerClient.java'
O_SOURCES = [O_RADON, O_ABSORBER, O_MODBLOCKS, O_ARMORUTIL, O_ARMORREG, O_ARMORMOD, O_HAZMAT, O_CLADDING, O_TOOLRECIPES, O_CRAFTING, O_SMELTING, O_MINERAL, O_CRYSTAL, O_CLIENT_EVENTS,
             O_LANG_EN, O_LANG_ZH]
# The original sources each new mapping group must list (source_paths or source_watch; plus the imported textures for the detection / absorber group).
FEATURE_SOURCES = {FEATURE_HAZARD: [O_RADON, O_ARMORUTIL, O_ARMORREG, O_ARMORMOD, O_HAZMAT, O_CLADDING],
                   FEATURE_DETECTION: [O_ABSORBER, O_TOOLRECIPES] + list(ASSETS.values())}
# The NEO paths each new mapping group must cover (target_paths or target_watch).
FEATURE_TARGETS = {FEATURE_HAZARD: [GAS_RADON, ARMOR_UTIL, ARMOR_REGISTRY, ARMOR_MOD, HAZMAT, CLADDING, RADIATION_TESTS, NEW_TOOLS[0], NEW_TOOLS[1]],
                   FEATURE_DETECTION: [ABSORBER_BLOCK] + list(ASSETS)
                   + [GENERATED_ROOT+p for p in EXPECTED_GENERATED_BASE if any(p.endswith(f'/{b}.json') for b in BLOCK_TABLE) or 'recipe/' in p]}
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'radon_check': (O_RADON, 'if(ArmorRegistry.hasAllProtection(entityLiving, 3, HazardClass.PARTICLE_FINE))'), 'radon_filter': (O_RADON, 'ArmorUtil.damageGasMaskFilter(entityLiving, 1);'),
    'radon_contaminate': (O_RADON, 'ContaminationUtil.contaminate((EntityLivingBase)entity, HazardType.RADIATION, ContaminationType.RAD_BYPASS, 0.05F);'),
    'radon_asbestos': (O_RADON, 'HbmLivingProps.incrementAsbestos((EntityLivingBase)entity, 1);'),
    'absorber_tiers': (O_ABSORBER, 'BASE(2.5F, "absorber"), RED(10F, "absorber_red")'), 'absorber_random': (O_ABSORBER, 'this.setTickRandomly(true);'),
    'absorber_tick_rate': (O_ABSORBER, 'public int tickRate(World world)'), 'absorber_update': (O_ABSORBER, 'ChunkRadiationManager.proxy.decrementRad(world, x, y, z, tier.absorbAmount);'),
    'absorber_reschedule': (O_ABSORBER, 'world.scheduleBlockUpdate(x, y, z, this, tickRate(world));'), 'absorber_added': (O_ABSORBER, 'public void onBlockAdded(World world, int x, int y, int z)'),
    'absorber_registered': (O_MODBLOCKS, 'rad_absorber = new BlockAbsorber(Material.iron)'), 'graphite_registered': (O_MODBLOCKS, 'block_graphite = new BlockGraphite(Material.iron, 30, 5)'),
    'sand_registered': (O_MODBLOCKS, 'sand_mix = new BlockNTMSand(Material.sand)'), 'glass_boron_registered': (O_MODBLOCKS, 'glass_boron = new BlockNTMGlassCT'),
    'glass_lead_registered': (O_MODBLOCKS, 'glass_lead = new BlockNTMGlassCT'),
    'armor_util_damage_entity': (O_ARMORUTIL, 'public static void damageGasMaskFilter(EntityLivingBase entity, int damage)'), 'armor_util_damage_mask': (O_ARMORUTIL, 'public static void damageGasMaskFilter(ItemStack mask, int damage)'),
    'armor_util_recursive': (O_ARMORUTIL, 'mods[ArmorModHandler.helmet_only] != null && mods[ArmorModHandler.helmet_only].getItem() instanceof IGasMask'),
    'armor_registry_protection': (O_ARMORREG, 'public static List<HazardClass> getProtectionFromItem(ItemStack stack, EntityLivingBase entity)'),
    'armor_registry_guard': (O_ARMORREG, 'if(hazardClasses.containsKey(filter.getItem()))'), 'armor_mod_remove': (O_ARMORMOD, 'public static void removeMod(ItemStack armor, int slot)'),
    'armor_mod_pry': (O_ARMORMOD, 'public static ItemStack[] pryMods(ItemStack armor)'), 'hazmat_read_config': (O_HAZMAT, 'private static HashMap<Item, Double> readConfig(File config)'),
    'hazmat_unknown_item': (O_HAZMAT, 'MainRegistry.logger.error("Tried loading unknown item "'), 'hazmat_entry_error': (O_HAZMAT, 'MainRegistry.logger.error("Encountered "'),
    'hazmat_file_error': (O_HAZMAT, 'ex.printStackTrace();'), 'cladding_rad': (O_CLADDING, 'this.rad = rad;'), 'hold_shift_literal': (O_CLIENT_EVENTS, '"> to display protection info"'),
    'geiger_recipe': (O_TOOLRECIPES, 'new ItemStack(ModItems.geiger_counter, 1)'), 'dosimeter_recipe': (O_TOOLRECIPES, 'new ItemStack(ModItems.dosimeter, 1)'),
    'geiger_block_recipe': (O_TOOLRECIPES, 'new ItemStack(ModBlocks.geiger)'), 'digamma_recipe': (O_TOOLRECIPES, 'new ItemStack(ModItems.digamma_diagnostic)'),
    'absorber_base_recipe': (O_CRAFTING, 'EnumAbsorberTier.BASE.ordinal()),new Object'), 'decon_recipe': (O_CRAFTING, 'new ItemStack(ModBlocks.decon, 1)'),
    'sand_boron_recipe': (O_CRAFTING, 'EnumSandType.BORON.ordinal()), new Object'), 'sand_lead_recipe': (O_CRAFTING, 'EnumSandType.LEAD.ordinal()), new Object'),
    'lid_glass_recipe': (O_CRAFTING, 'new ItemStack(ModItems.rbmk_lid_glass, 4)'), 'moderator_recipe': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_moderator, 1)'),
    'control_mod_recipe': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_control_mod, 1)'), 'rod_mod_recipe': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_rod_mod, 1)'),
    'graphite_pair': (O_MINERAL, 'add1To9Pair(ModBlocks.block_graphite, ModItems.ingot_graphite);'), 'glass_boron_smelting': (O_SMELTING, 'new ItemStack(ModBlocks.glass_boron), 0.25F'),
    'glass_lead_smelting': (O_SMELTING, 'new ItemStack(ModBlocks.glass_lead), 0.25F'), 'crystallizer_row': (O_CRYSTAL, 'new CrystallizerRecipe(ModBlocks.block_graphite, baseTime)'),
    'crystallizer_base_time': (O_CRYSTAL, 'final int baseTime = 600;'), 'crystallizer_default_acid': (O_CRYSTAL, 'registerRecipe(input, recipe, new FluidStack(Fluids.PEROXIDE, 500))'),
    'crystallizer_productivity': (O_CRYSTAL, 'public float productivity = 0F;'),
    'lang_prot_en': (O_LANG_EN, 'hazard.prot='), 'lang_never_en': (O_LANG_EN, 'hazard.neverProtects='), 'lang_prot_zh': (O_LANG_ZH, 'hazard.prot='), 'lang_never_zh': (O_LANG_ZH, 'hazard.neverProtects='),
    'lang_potion_taint_en': (O_LANG_EN, 'potion.hbm_taint='), 'lang_potion_taint_zh': (O_LANG_ZH, 'potion.hbm_taint='),
    'lang_absorber_en': (O_LANG_EN, 'tile.rad_absorber.base.name='), 'lang_absorber_zh': (O_LANG_ZH, 'tile.rad_absorber.base.name='),
}
# Constants compared between the original and NEO source texts: id -> (original path, regex, NEO path, regex, expected unique values in order[, expected NEO values when they differ]).
# Numbers are compared as floats (underscores dropped, F / D suffixes dropped), anything else as text. The group-1 value of every match is collected. A NEO regex that finds
# nothing (the class is not written yet, or its text differs from the handoff) is reported as pending with its id.
CONSTANTS = {
    # Radon (BlockGasRadon.java:32-36): protected = hasAllProtection on the head (slot 3 in 1.7.10) for PARTICLE_FINE -> filter damage 1; else RAD_BYPASS 0.05 and asbestos +1.
    'radon_slot': (O_RADON, r'hasAllProtection\(entityLiving, (\d+), HazardClass\.PARTICLE_FINE\)', GAS_RADON, r'hasAllProtection\(livingEntity, EquipmentSlot\.(HEAD), HazardClass\.PARTICLE_FINE\)', [3], ['HEAD']),
    'radon_class': (O_RADON, r'hasAllProtection\(entityLiving, 3, HazardClass\.(\w+)\)', GAS_RADON, r'hasAllProtection\(livingEntity, EquipmentSlot\.HEAD, HazardClass\.(\w+)\)', ['PARTICLE_FINE']),
    'radon_filter_damage': (O_RADON, r'damageGasMaskFilter\(entityLiving, (\d+)\)', GAS_RADON, r'damageGasMaskFilter\(livingEntity, (\d+)\)', [1]),
    'radon_hazard_type': (O_RADON, r'contaminate\(\(EntityLivingBase\)entity, HazardType\.(\w+), ContaminationType\.RAD_BYPASS', GAS_RADON, r'contaminate\(livingEntity, HazardType\.(\w+), ContaminationType\.RAD_BYPASS', ['RADIATION']),
    'radon_contamination_type': (O_RADON, r'ContaminationType\.(RAD_BYPASS), [\d.]+F\)', GAS_RADON, r'ContaminationType\.(RAD_BYPASS), [\d.]+F\)', ['RAD_BYPASS']),
    'radon_rad': (O_RADON, r'ContaminationType\.RAD_BYPASS, ([\d.]+)F\)', GAS_RADON, r'ContaminationType\.RAD_BYPASS, ([\d.]+)F\)', [0.05]),
    'radon_asbestos': (O_RADON, r'incrementAsbestos\(\(EntityLivingBase\)entity, (\d+)\)', GAS_RADON, r'incrementAsbestos\(livingEntity, (\d+)\)', [1]),
    # Absorber (BlockAbsorber.java:20-22,63-78): tiers 2.5 / 10 / 100 / 10,000 with their textures, tick rate 10, random ticks; ModBlocks.java:2307 hardness 5 / resistance 10.
    'absorber_amounts': (O_ABSORBER, r'(?:BASE|RED|GREEN|PINK)\(([\d.]+)F, "absorber', BLOCKS, r'register\("rad_absorber(?:_\w+)?", \(\) -> new RadAbsorberBlock\([^\n]*?, ([\d.]+)F\)\);', [2.5, 10, 100, 10000]),
    'absorber_textures': (O_ABSORBER, r'F, "(absorber\w*)"\)', BLOCK_STATE_PROVIDER, r'modLoc\("block/(absorber\w*)"\)', ['absorber', 'absorber_red', 'absorber_green', 'absorber_pink']),
    'absorber_tick_rate': (O_ABSORBER, r'public int tickRate\(World world\) \{\s*return (\d+);', ABSORBER_BLOCK, r'TICK_RATE = (\d+);', [10]),
    'absorber_reschedule_rate': (O_ABSORBER, r'scheduleBlockUpdate\(x, y, z, this, (tickRate)\(world\)\)', ABSORBER_BLOCK, r'scheduleTick\(pos, this, (TICK_RATE)\)', ['tickRate'], ['TICK_RATE']),
    'absorber_random_ticks': (O_ABSORBER, r'(setTickRandomly)\(true\)', BLOCKS, r'\.(randomTicks)\(\)', ['setTickRandomly'], ['randomTicks']),
    'absorber_hardness': (O_MODBLOCKS, r'rad_absorber = new BlockAbsorber\(Material\.iron\)[^\n]*?setHardness\(([\d.]+)F\)', BLOCKS, r'RAD_ABSORBER = register\("rad_absorber"[^\n]*?strength\(([\d.]+)F, [\d.]+F\)', [5]),
    'absorber_resistance': (O_MODBLOCKS, r'rad_absorber = new BlockAbsorber\(Material\.iron\)[^\n]*?setResistance\(([\d.]+)F\)', BLOCKS, r'RAD_ABSORBER = register\("rad_absorber"[^\n]*?strength\([\d.]+F, ([\d.]+)F\)', [10]),
    # Graphite block (ModBlocks.java:1410): encouragement 30, flammability 5, hardness 5, resistance 10, metal sound.
    'graphite_encouragement': (O_MODBLOCKS, r'new BlockGraphite\(Material\.iron, (\d+), \d+\)', BLOCKS, r'BLOCK_GRAPHITE = register\([^\n]*?\), (\d+), \d+\)\);', [30]),
    'graphite_flammability': (O_MODBLOCKS, r'new BlockGraphite\(Material\.iron, \d+, (\d+)\)', BLOCKS, r'BLOCK_GRAPHITE = register\([^\n]*?\), \d+, (\d+)\)\);', [5]),
    'graphite_hardness': (O_MODBLOCKS, r'block_graphite = new BlockGraphite[^\n]*?setHardness\(([\d.]+)F\)', BLOCKS, r'BLOCK_GRAPHITE = register\([^\n]*?strength\(([\d.]+)F, [\d.]+F\)', [5]),
    'graphite_resistance': (O_MODBLOCKS, r'block_graphite = new BlockGraphite[^\n]*?setResistance\(([\d.]+)F\)', BLOCKS, r'BLOCK_GRAPHITE = register\([^\n]*?strength\([\d.]+F, ([\d.]+)F\)', [10]),
    'graphite_sound': (O_MODBLOCKS, r'block_graphite = new BlockGraphite[^\n]*?setStepSound\(Block\.soundType(\w+)\)', BLOCKS, r'BLOCK_GRAPHITE = register\([^\n]*?sound\(SoundType\.(\w+)\)', ['Metal'], ['METAL']),
    # Sand and glass (ModBlocks.java:1641-1643, SmeltingRecipes.java:132-133): sand hardness 0.5 / sand sound, glass hardness 0.3 / glass sound, smelting experience 0.25.
    'sand_hardness': (O_MODBLOCKS, r'sand_mix = new BlockNTMSand[^\n]*?setHardness\(([\d.]+)F\)', BLOCKS, r'SAND_(?:BORON|LEAD) = register\([^\n]*?strength\(([\d.]+)F\)', [0.5]),
    'sand_sound': (O_MODBLOCKS, r'sand_mix = new BlockNTMSand[^\n]*?setStepSound\(Block\.soundType(\w+)\)', BLOCKS, r'SAND_(?:BORON|LEAD) = register\([^\n]*?sound\(SoundType\.(\w+)\)', ['Sand'], ['SAND']),
    'glass_hardness': (O_MODBLOCKS, r'glass_(?:boron|lead) = new BlockNTMGlassCT[^\n]*?setHardness\(([\d.]+)F\)', BLOCKS, r'GLASS_(?:BORON|LEAD) = register\([^\n]*?strength\(([\d.]+)F\)', [0.3]),
    'glass_sound': (O_MODBLOCKS, r'glass_(?:boron|lead) = new BlockNTMGlassCT[^\n]*?setStepSound\(Block\.soundType(\w+)\)', BLOCKS, r'GLASS_(?:BORON|LEAD) = register\([^\n]*?sound\(SoundType\.(\w+)\)', ['Glass'], ['GLASS']),
    'smelting_xp': (O_SMELTING, r'sand_mix, 1, EnumSandType\.(?:BORON|LEAD)\.ordinal\(\)\), new ItemStack\(ModBlocks\.glass_\w+\), ([\d.]+)F\)', RECIPE_PROVIDER,
                    r'smelting\(Ingredient\.of\(NtmBlocks\.SAND_\w+\.get\(\)\), RecipeCategory\.BUILDING_BLOCKS,\s*NtmBlocks\.GLASS_\w+\.get\(\), ([\d.]+)F, \d+\)', [0.25]),
    # Crystallizer row (CrystallizerRecipes.java:99, :56, :314-316, the recipe class default :328): coal block -> graphite block, hydrogen peroxide 500 mB, 600 ticks, productivity 0.
    'crystallizer_input': (O_CRYSTAL, r'registerRecipe\(new OreDictStack\((COAL)\.block\(\)\)', CRYSTALLIZER, r'new TagStack\(ItemTags\.create\(ResourceLocation\.fromNamespaceAndPath\("c", "storage_blocks/(coal)"\)\)', ['COAL'], ['coal']),
    'crystallizer_output': (O_CRYSTAL, r'new CrystallizerRecipe\(ModBlocks\.(block_graphite), baseTime\)\);', CRYSTALLIZER, r'new ItemStack\(NtmBlocks\.(BLOCK_GRAPHITE)\.get\(\)\), DEFAULT_DURATION, 0F\)\);', ['block_graphite'], ['BLOCK_GRAPHITE']),
    'crystallizer_acid': (O_CRYSTAL, r'recipe, new FluidStack\(Fluids\.(\w+), \d+\)\);', CRYSTALLIZER, r'new FluidStack\(Fluids\.(PEROXIDE), DEFAULT_ACID\), new ItemStack\(NtmBlocks\.BLOCK_GRAPHITE', ['PEROXIDE']),
    'crystallizer_acid_amount': (O_CRYSTAL, r'recipe, new FluidStack\(Fluids\.\w+, (\d+)\)\);', CRYSTALLIZER, r'DEFAULT_ACID = (\d+);', [500]),
    'crystallizer_duration': (O_CRYSTAL, r'final int baseTime = (\d+);', CRYSTALLIZER, r'DEFAULT_DURATION = (\d+);', [600]),
    'crystallizer_productivity': (O_CRYSTAL, r'public float productivity = ([\d.]+)F;', CRYSTALLIZER, r'DEFAULT_DURATION, ([\d.]+)F\)\);', [0]),
    # Hazmat reader (HazmatRegistry.java:265-295) and the cladding constructor (ItemModCladding.java:17).
    'hazmat_unknown_log': (O_HAZMAT, r'logger\.error\("(Tried loading unknown item )" \+ name', HAZMAT, r'LOGGER\.error\("(Tried loading unknown item )" \+ name', ['Tried loading unknown item ']),
    'hazmat_entry_log': (O_HAZMAT, r'logger\.error\("(Encountered )" \+ ex \+ " trying to read hazmat entry " \+ element\.toString\(\)', HAZMAT,
                         r'LOGGER\.error\("(Encountered )" \+ ex \+ " trying to read hazmat entry " \+ element\.toString\(\)', ['Encountered ']),
    'hazmat_config_keys': (O_HAZMAT, r'object\.get\("(\w+)"\)', HAZMAT, r'object\.get\("(\w+)"\)', ['item', 'resistance']),
    'cladding_assignment': (O_CLADDING, r'this\.(rad) = rad;', CLADDING, r'this\.(rad) = rad;', ['rad']),
}
# Occurrence counts in the NEO source texts (expected), with the original count where one exists: id -> (NEO path, regex, expected count[, original path, original regex, original count]).
# The hazard fixes are asserted here as the presence of the corrected form and the absence of the start form.
COUNTS = {
    'armor_util_nonempty_guard': (ARMOR_UTIL, r'if \(!mods\[ArmorModHandler\.HELMET_ONLY\]\.isEmpty\(\) && mods\[ArmorModHandler\.HELMET_ONLY\]\.getItem\(\) instanceof IGasMask\)', 3,
                                  O_ARMORUTIL, r'if\(mods\[ArmorModHandler\.helmet_only\] != null && mods\[ArmorModHandler\.helmet_only\]\.getItem\(\) instanceof IGasMask\)', 3),
    'armor_util_inverted_guard_gone': (ARMOR_UTIL, r'if \(mods\[ArmorModHandler\.HELMET_ONLY\]\.isEmpty\(\) &&', 0),
    'radon_has_all_protection': (GAS_RADON, r'if \(ArmorRegistry\.hasAllProtection\(livingEntity, EquipmentSlot\.HEAD, HazardClass\.PARTICLE_FINE\)\) \{\s*ArmorUtil\.damageGasMaskFilter\(livingEntity, 1\);', 1,
                                 O_RADON, r'if\(ArmorRegistry\.hasAllProtection\(entityLiving, 3, HazardClass\.PARTICLE_FINE\)\) \{\s*ArmorUtil\.damageGasMaskFilter\(entityLiving, 1\);', 1),
    'radon_inverted_check_gone': (GAS_RADON, r'if \(!ArmorRegistry\.hasProtection', 0),
    'radon_else_branch': (GAS_RADON, r'\} else \{\s*ContaminationUtil\.contaminate\(livingEntity, HazardType\.RADIATION, ContaminationType\.RAD_BYPASS, 0\.05F\);\s*HbmLivingAttachments\.incrementAsbestos\(livingEntity, 1\);', 1,
                          O_RADON, r'\} else \{\s*ContaminationUtil\.contaminate\(\(EntityLivingBase\)entity, HazardType\.RADIATION, ContaminationType\.RAD_BYPASS, 0\.05F\);\s*HbmLivingProps\.incrementAsbestos\(\(EntityLivingBase\)entity, 1\);', 1),
    'registry_unknown_filter_guard': (ARMOR_REGISTRY, r'!filter\.isEmpty\(\) && hazardClasses\.containsKey\(filter\.getItem\(\)\)', 1,
                                      O_ARMORREG, r'if\(hazardClasses\.containsKey\(filter\.getItem\(\)\)\)', 1),
    'registry_filter_copy': (ARMOR_REGISTRY, r'new ArrayList<>\(hazardClasses\.get\(filter\.getItem\(\)\)\)', 1, O_ARMORREG, r'hazardClasses\.get\(filter\.getItem\(\)\)\.clone\(\)', 1),
    'registry_clone_gone': (ARMOR_REGISTRY, r'hazardClasses\.get\(filter\.getItem\(\)\)\.clone\(\)', 0),
    'registry_hold_shift_key': (ARMOR_REGISTRY, r'Component\.translatable\("hazard\.hold_shift"', 1),
    'registry_hold_literal_gone': (ARMOR_REGISTRY, r'Component\.literal\("Hold <"\)', 0, O_CLIENT_EVENTS, r'"Hold <"', 2),
    'pry_mods_empty_fill': (ARMOR_MOD, r'Arrays\.fill\(slots, ItemStack\.EMPTY\);', 1),
    'pry_mods_empty_slot_not_parsed': (ARMOR_MOD, r'cmp\.isEmpty\(\) \? Optional\.empty\(\) : ItemStack\.parse\(level\.registryAccess\(\), cmp\)', 1),
    'remove_mod_no_data_guard': (ARMOR_MOD, r'if\(armor\.isEmpty\(\) \|\| !TagsUtil\.hasCustomData\(armor\)\) return;', 1),
    'remove_mod_keeps_outer_tag': (ARMOR_MOD, r'if\(mods\.isEmpty\(\)\) tag\.remove\(MOD_COMPOUND_KEY\);\s*else tag\.put\(MOD_COMPOUND_KEY, mods\);', 1),
    'remove_mod_writes_whole_tag': (ARMOR_MOD, r'else TagsUtil\.putCustomData\(armor, tag\);', 1),
    # ItemStack.save(provider) returns the encoded tag and leaves an argument untouched in 1.21 (1.7.10 writeToNBT filled it): the start code stored an empty compound for the gas-mask filter and
    # for every armor mod; the corrected forms use the returned tag (original ArmorUtil.java:259 and ArmorModHandler.java:91 write into the compound).
    'install_filter_stores_returned_tag': (ARMOR_UTIL, r'tag\.put\(FILTER_KEY, filter\.save\(level\.registryAccess\(\)\)\);', 1, O_ARMORUTIL, r'filter\.writeToNBT\(attach\);', 1),
    'install_mod_stores_returned_tag': (ARMOR_MOD, r'mods\.put\(MOD_SLOT_KEY \+ slot, mod\.save\(level\.registryAccess\(\)\)\);', 1, O_ARMORMOD, r'mod\.writeToNBT\(cmp\);', 1),
    'save_into_argument_gone': (ARMOR_UTIL, r'\.save\(level\.registryAccess\(\), (?:attach|cmp)\)', 0),
    'save_into_argument_gone_mod': (ARMOR_MOD, r'\.save\(level\.registryAccess\(\), (?:attach|cmp)\)', 0),
    # setDamageValue clamps to the maximum in 1.21, so the start test (set, then compare) never removed a used-up filter; the corrected form compares before setting (original ArmorUtil.java:346-352).
    'filter_damage_compare_before_set': (ARMOR_UTIL, r'int newDamage = filter\.getDamageValue\(\) \+ damage;\s*if \(newDamage > filter\.getMaxDamage\(\)\) \{\s*removeFilter\(mask\);', 1,
                                         O_ARMORUTIL, r'filter\.setItemDamage\(filter\.getItemDamage\(\) \+ damage\);\s*if\(filter\.getItemDamage\(\) > filter\.getMaxDamage\(\)\)\s*removeFilter\(mask\);', 1),
    'filter_damage_set_after_compare': (ARMOR_UTIL, r'filter\.setDamageValue\(newDamage\);\s*installGasMaskFilter\(level, mask, filter\);', 1),
    'filter_damage_set_before_compare_gone': (ARMOR_UTIL, r'filter\.setDamageValue\(filter\.getDamageValue\(\) \+ damage\)', 0),
    'remove_mod_whole_tag_overwrite_gone': (ARMOR_MOD, r'TagsUtil\.putCustomData\(armor, mods\);', 0),
    'remove_mod_drops_empty_component': (ARMOR_MOD, r'if\(tag\.isEmpty\(\)\) armor\.remove\(DataComponents\.CUSTOM_DATA\);', 1),
    'read_config_try_with_resources': (HAZMAT, r'try \(FileReader reader = new FileReader\(config\)\)', 1),
    'read_config_unknown_item_skipped': (HAZMAT, r'BuiltInRegistries\.ITEM\.getOptional\(id\)', 1),
    'read_config_air_mapping_gone': (HAZMAT, r'BuiltInRegistries\.ITEM\.get\(ResourceLocation\.parse', 0),
    'read_config_per_entry_catch': (HAZMAT, r'\} catch \(Exception ex\) \{\s*NuclearTechMod\.LOGGER\.error\("Encountered "', 1),
    'read_config_whole_file_catch': (HAZMAT, r'\} catch\(Exception ex\) \{\s*NuclearTechMod\.LOGGER\.error\("Failed to read "', 1),
    'read_config_public': (HAZMAT, r'public static HashMap<Item, Double> readConfig\(File config\)', 1),
    'absorber_on_place_server': (ABSORBER_BLOCK, r'public void onPlace\([^)]*\) \{\s*super\.onPlace\([^)]*\);\s*if \(!level\.isClientSide\) \{\s*level\.scheduleTick\(pos, this, TICK_RATE\);', 1),
    'absorber_tick_decrements': (ABSORBER_BLOCK, r'public void tick\([^)]*\) \{\s*ChunkRadiationManager\.proxy\.decrementRad\(level, pos, absorbAmount\);\s*level\.scheduleTick\(pos, this, TICK_RATE\);', 1),
    'absorber_random_tick_same': (ABSORBER_BLOCK, r'public void randomTick\([^)]*\) \{\s*this\.tick\(state, level, pos, random\);', 1),
    'glass_cutout_layers': (CLIENT_MOD, r'ItemBlockRenderTypes\.setRenderLayer\(NtmBlocks\.GLASS_(?:BORON|LEAD)\.get\(\), RenderType\.cutout\(\)\);', 2),
    'sand_falling_blocks': (BLOCKS, r'(?:SAND_BORON|SAND_LEAD) = register\([^\n]*new ColoredFallingBlock\(', 2),
    'glass_transparent_blocks': (BLOCKS, r'(?:GLASS_BORON|GLASS_LEAD) = register\([^\n]*new TransparentBlock\(', 2),
    'graphite_flammable_block': (BLOCKS, r'BLOCK_GRAPHITE = register\("block_graphite", \(\) -> new FlammableBlock\(', 1),
    'absorber_blocks_use_class': (BLOCKS, r'RAD_ABSORBER(?:_RED|_GREEN|_PINK)? = register\("rad_absorber(?:_\w+)?", \(\) -> new RadAbsorberBlock\(', 4),
    'crystallizer_row_count_doc': (CRYSTALLIZER, r'47 rows', 2),
    'smoke_test_row_count': (SMOKE_TESTS, r'check\(rows == 47, "the default acidizer table has " \+ rows \+ " rows, expected 47"\);', 1),
    'smoke_test_old_count_gone': (SMOKE_TESTS, r'rows == 46', 0),
}
# per-block registration counts (one occurrence each) in creative tabs, loot, tags, block states and the language provider.
for _b, (_c, _t) in BLOCK_TABLE.items():
    COUNTS[f'{_b}_creative_tab'] = (CREATIVE_TABS, rf'output\.accept\(NtmBlocks\.{_c}\);', 1)
    COUNTS[f'{_b}_loot_drop_self'] = (LOOT_PROVIDER, rf'this\.dropSelf\(NtmBlocks\.{_c}\.get\(\)\);', 1)
    COUNTS[f'{_b}_mineable_tag'] = (TAG_PROVIDER, rf'NtmBlocks\.{_c}\.get\(\)', 1)
    COUNTS[f'{_b}_block_state'] = (BLOCK_STATE_PROVIDER, rf'NtmBlocks\.{_c}[,)]', 2 if _b.startswith('rad_absorber') else 1)
    COUNTS[f'{_b}_english_name'] = (PROVIDER, rf'this\.add\(NtmBlocks\.{_c}, "', 1)
# The ten hazard-system fixes of the receipt (eight in the handoff plus the two ItemStack.save findings of the review), one line each (NEO-only; the clamp stays upstream-shared and unchanged).
HAZARD_FIXES = [
    'GasRadonBlock: the radon check is hasAllProtection(HEAD, PARTICLE_FINE) as BlockGasRadon.java:32 (the start had the inverted hasProtection test, so an unprotected entity only wore down a filter)',
    'ArmorUtil: the helmet-mod gas-mask reads use !isEmpty() && instanceof IGasMask at three places (the start tested isEmpty(), so the branch never ran); original ArmorUtil.java:289,323,339',
    'ArmorRegistry.getProtectionFromItem: a filter without registered hazard classes adds nothing (containsKey guard, defensive copy); original ArmorRegistry.java:75-83',
    'ArmorModHandler.pryMods: absent slots are ItemStack.EMPTY, never null, and an empty slot compound is not parsed (the NEO callers call isEmpty(); the original callers null-checked)',
    'ArmorModHandler.removeMod: removes only the mod slot, drops the mod compound when empty and the custom data component when the tag is empty; hfr_Filter, hfr_cladding and other keys survive (original :101-119)',
    'HazmatRegistry.readConfig: unknown items are logged and skipped (not mapped to air), a bad entry is logged and skipped, a broken file is logged and keeps the defaults, the reader is closed; original HazmatRegistry.java:265-295',
    'ItemModCladding: the constructor assigns rad (original ItemModCladding.java:17); the hazard tooltips and the ten status-effect names are localized (hazard.* 14 keys, effect.hbmsntm.* 10 keys) and the hard-coded "Hold <LSHIFT>" text is the key hazard.hold_shift',
    'ArmorUtil.installGasMaskFilter and ArmorModHandler.applyMod: the encoded stack is the tag ItemStack.save(provider) returns (1.21 leaves an argument compound untouched, so the start code stored an empty filter / mod compound); original ArmorUtil.java:259, ArmorModHandler.java:91',
    'ArmorUtil.damageGasMaskFilter: the new damage is compared with the maximum before setDamageValue (which clamps in 1.21), so a used-up filter is removed as in the original ArmorUtil.java:346-352',
    'ChunkRadiationHandlerSimple: the clamp argument order equals the original (ChunkRadiationHandlerSimple.java:98 upstream, :99 NEO); upstream-shared, recorded and left unchanged',
]
# Known source differences the batch deliberately leaves (recorded; not asserted equal, but each is backed by a NEO constant or fact above where it can be).
KNOWN_DIFFERENCES = {
    'absorber_split': 'the original is one block with four META tiers (BlockAbsorber.EnumAbsorberTier); NEO registers four blocks rad_absorber, _red, _green, _pink (item names tile.rad_absorber.* map to block.hbmsntm.rad_absorber*)',
    'absorber_sound': 'the original ModBlocks.java:2307 sets no step sound, so the 1.7.10 default (stone) applies; NEO follows it (SoundType.STONE) although the task book said metal',
    'absorber_random_tick': 'the original random-ticks the block and 1.7.10 runs updateTick for that (setTickRandomly, BlockAbsorber.java:35); NEO randomTick calls the same tick (decrement and reschedule)',
    'glass_connected_textures': 'the original glass is BlockNTMGlassCT with connected textures; NEO uses the non-connected icons on TransparentBlock (faces between identical glass are hidden like BlockBreakable)',
    'glass_drops': 'the original glass drops nothing without silk touch; NEO drops itself (dropSelf, the glass_quartz precedent)',
    'sand_hardness': 'NEO sand_quartz uses 0.6; the new sands use the original 0.5',
    'sand_dust_colour': 'the falling-block dust colours of sand_lead (0xFF858591) and sand_boron (0xFFC9C6A2) are the mean opaque texture colour (png_stats.py); the original has no such value',
    'smelting_time': 'GameRegistry.addSmelting has no time (the 1.7.10 furnace takes 200 ticks); NEO writes 200 explicitly',
    'rubber_tag': 'the original ANY_RUBBER.ingot() (latex / biorubber / rubber) is the NEO tag ntm:any_rubbers (rubber and biorubber), unused by recipes until now; ANY_PLASTIC.ingot() is ntm:ingots_plastic (polymer and bakelite)',
    'recipe_528': 'rbmk_control_mod and rbmk_rod_mod sit in the !enable528 branch (CraftingManager.java:759,992); NEO has no 528 mode and registers them unconditionally',
    'unreachable_inputs': 'digamma_diagnostic (billet_polonium), rad_absorber_pink (ingot_saturnite, powder_nitan_mix), rbmk_control_mod and rbmk_rod_mod (nugget_bismuth) are registered but have no survival source yet (GOAL26 decision 4)',
    'crystallizer_productivity_argument': 'the original line 99 uses the two-argument constructor (productivity 0); NEO DEFAULT_PRODUCTIVITY is the ore rows 0.05, so the new row passes 0F explicitly; the row is appended after the 46 start rows',
    'filter_key': 'the original stores the filter under hfrFilter (ArmorUtil FILTERK_KEY); NEO keeps its own hfr_Filter key (unchanged)',
    'hazard_key_names': 'NEO HazardClass keys are snake_case (hazard.particle_fine ...); hazard.prot is hazard.protect, hazard.noprot hazard.no_protect, hazard.neverProtects hazard.never_protects; hazard.nerve_agent is unused in both',
    'gas_masks_deferred': 'the IGasMask branches (a filter on a real gas mask or a helmet mod) are covered statically only; no NEO item implements IGasMask before 26B',
}
# The recipe key tables: original key expression -> the NEO ingredient (OneOf: several accepted generated forms). Forms follow the generated recipes: items by registry name, tags where the
# provider uses the tag for the same oredict key.
GLASS_PANE = OneOf({'tag': 'c:glass_panes'}, {'item': 'minecraft:glass_pane'})
KEY_TABLE = {
    'GOLD.wireFine()': {'item': 'hbmsntm:wire_gold'}, 'ANY_RUBBER.ingot()': {'tag': 'ntm:any_rubbers'}, 'DictFrame.fromOne(ModItems.circuit, EnumCircuitType.BASIC)': {'item': 'hbmsntm:circuit_integrated_board'},
    'DictFrame.fromOne(ModItems.circuit, EnumCircuitType.VACUUM_TUBE)': {'item': 'hbmsntm:circuit_vacuum_tube'}, 'GOLD.ingot()': OneOf({'item': 'minecraft:gold_ingot'}, {'tag': 'c:ingots/gold'}),
    'STEEL.plate()': OneOf({'tag': 'c:plates/steel'}, {'item': 'hbmsntm:plate_steel'}), 'BE.ingot()': OneOf({'item': 'hbmsntm:ingot_beryllium'}, {'tag': 'c:ingots/beryllium'}),
    'KEY_PLANKS': {'tag': 'minecraft:planks'}, 'KEY_ANYPANE': GLASS_PANE, 'ModItems.geiger_counter': {'item': 'hbmsntm:geiger_counter'}, 'PO210.billet()': {'item': 'hbmsntm:billet_polonium'},
    'ASBESTOS.ingot()': {'item': 'hbmsntm:ingot_asbestos'},
    'CU.ingot()': OneOf([{'item': 'hbmsntm:ingot_copper'}, {'item': 'minecraft:copper_ingot'}], {'item': 'hbmsntm:ingot_copper'}, {'tag': 'c:ingots/copper'}),
    'COAL.dust()': {'item': 'hbmsntm:powder_coal'}, 'PB.dust()': {'item': 'hbmsntm:powder_lead'}, 'TI.ingot()': OneOf({'item': 'hbmsntm:ingot_titanium'}, {'tag': 'c:ingots/titanium'}),
    'ANY_PLASTIC.ingot()': {'tag': 'ntm:ingots_plastic'}, 'ModItems.powder_desh_mix': {'item': 'hbmsntm:powder_desh_mix'}, 'BIGMT.ingot()': {'item': 'hbmsntm:ingot_saturnite'},
    'ModItems.powder_nitan_mix': {'item': 'hbmsntm:powder_nitan_mix'}, 'Blocks.iron_bars': {'item': 'minecraft:iron_bars'}, 'STEEL.ingot()': OneOf({'item': 'hbmsntm:ingot_steel'}, {'tag': 'c:ingots/steel'}),
    'GRAPHITE.block()': {'item': 'hbmsntm:block_graphite'}, 'ModBlocks.rbmk_blank': {'item': 'hbmsntm:rbmk_blank'}, 'ModBlocks.glass_lead': {'item': 'hbmsntm:glass_lead'},
    'ModBlocks.glass_boron': {'item': 'hbmsntm:glass_boron'}, 'ModBlocks.rbmk_control': {'item': 'hbmsntm:rbmk_control'}, 'ModBlocks.rbmk_rod': {'item': 'hbmsntm:rbmk_rod'},
    'ModItems.nugget_bismuth': {'item': 'hbmsntm:nugget_bismuth'}, 'B.dust()': {'item': 'hbmsntm:powder_boron'}, '"sand"': {'tag': 'c:sands'},
    'new ItemStack(ModBlocks.rad_absorber, 1, EnumAbsorberTier.BASE.ordinal())': {'item': 'hbmsntm:rad_absorber'},
    'new ItemStack(ModBlocks.rad_absorber, 1, EnumAbsorberTier.RED.ordinal())': {'item': 'hbmsntm:rad_absorber_red'},
    'new ItemStack(ModBlocks.rad_absorber, 1, EnumAbsorberTier.GREEN.ordinal())': {'item': 'hbmsntm:rad_absorber_green'},
}
SMELT_INPUTS = {'glass_boron_from_smelting_sand_boron': 'hbmsntm:sand_boron', 'glass_lead_from_smelting_sand_lead': 'hbmsntm:sand_lead'}

# The records the Goal 25 close-out commit and the Goal 26 planning commit changed between the goal25d package and this start (computed in main() and asserted equal to these lists): the
# goal25d receipt's final hash differs from the Goal26A start for three records; the planning commit added the Goal 26 documents and modified two shared records.
CLOSEOUT_DRIFT = ['migration/GOAL25.md', 'migration/GOAL25D-ACCEPTANCE.md', 'migration/README.md']
PLANNING_ADDED = sorted('migration/'+n for n in ('GOAL26-THREAD-PROMPTS.md', 'GOAL26.md', 'GOAL26A.md', 'GOAL26B.md', 'GOAL26C.md', 'GOAL26D.md', 'SURVIVAL-PLAYABILITY.md'))
PLANNING_MODIFIED = ['migration/GOAL25.md', 'migration/README.md']
# Recipe id -> the ORIGINAL_REFS entry quoted for it in the receipt.
RECIPE_REFS = {'geiger_counter': 'geiger_recipe', 'dosimeter': 'dosimeter_recipe', 'geiger': 'geiger_block_recipe', 'digamma_diagnostic': 'digamma_recipe',
               'rad_absorber': 'absorber_base_recipe', 'rad_absorber_red': 'absorber_base_recipe', 'rad_absorber_green': 'absorber_base_recipe', 'rad_absorber_pink': 'absorber_base_recipe',
               'decontaminator': 'decon_recipe', 'sand_boron': 'sand_boron_recipe', 'sand_lead': 'sand_lead_recipe', 'glass_boron_from_smelting_sand_boron': 'glass_boron_smelting',
               'glass_lead_from_smelting_sand_lead': 'glass_lead_smelting', 'rbmk_lid_glass': 'lid_glass_recipe', 'rbmk_lid_glass_boron_top': 'lid_glass_recipe',
               'rbmk_moderator': 'moderator_recipe', 'rbmk_control_mod': 'control_mod_recipe', 'rbmk_rod_mod': 'rod_mod_recipe'}


def scope_text(key_count, assets, tests, total_tests):
    return (f'Goal26A (the first batch of Goal 26: radiation and hazard protection closure): the hazard-system fixes of the radon block (GasRadonBlock now acts as BlockGasRadon.java:32-37: a head without '
            f'PARTICLE_FINE protection is contaminated with RAD_BYPASS 0.05 per tick plus one asbestos point, a protected head only wears the gas-mask filter down), the helmet-mod gas-mask reads of ArmorUtil '
            f'(three !isEmpty() tests), the unregistered filter and the null mod slots of ArmorRegistry / ArmorModHandler.pryMods (absent slots are ItemStack.EMPTY), ArmorModHandler.removeMod keeping the other '
            f'custom data, HazmatRegistry.readConfig skipping unknown items and surviving a broken file, ItemModCladding.rad; the hazard.* tooltip texts (14 keys) and ten status-effect names in English and '
            f'Chinese; the Geiger counter, dosimeter, Geiger block, decontaminator and digamma diagnostic recipes; four radiation absorber blocks (rad_absorber, _red, _green, _pink: RadAbsorberBlock, 2.5 / 10 / '
            f'100 / 10,000 chunk radiation removed every 10 ticks and on random ticks); block_graphite, sand_lead, sand_boron, glass_lead and glass_boron with their recipes (8 sand + 1 powder, smelting 0.25 xp); the '
            f'RBMK lid glass, moderator, moderated fuel channel and moderated control rod recipes; the crystallizer default row coal block -> graphite block (hydrogen peroxide 500 mB, 600 ticks, productivity 0; '
            f'47 default rows); {assets} imported textures; {key_count} English keys and {key_count} Chinese entries ({EXPECTED_KINDS.get("upstream", 0)} upstream, {EXPECTED_KINDS.get("local", 0)} local); '
            f'{tests} RadiationControlGameTests ({total_tests} GameTests in total, one batch per test) and the written, not executed acceptance checklist GOAL26A-ACCEPTANCE.md. Gameplay impact: radon now '
            f'contaminates unprotected players and mobs as in the original; the Geiger counter, dosimeter, Geiger block, decontaminator, the absorbers, graphite, lead / boron sand and glass and the RBMK '
            f'graphite moderator and glass lids can be crafted in survival; the pink absorber, the digamma diagnostic and the moderated RBMK control rod and fuel channel are registered but not reachable yet '
            f'(saturnite and nitan mix, polonium-210 billet, bismuth).')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal26a release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 29 scope copies) when it reproduces the baseline hash, else the blob at the start commit (the worktree was clean at the
    start; with CRLF where the working tree had it); None when nothing reproduces the baseline hash."""
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
    """The Goal26A start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does not list it)
    the hash the goal25d receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal25d packager protected (built there from the Goal21A..Goal25C starts and receipts and the goal25d start), plus every path the goal25d receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 26A baseline lists the goal25c receipt among them) and every release file of the frozen start
    (the goal25d package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md, the goal24a working notes and, new,
    GOAL25D-ACCEPTANCE.md) are pinned at their Goal26A start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes.
    Returns (protected, repinned) where repinned maps a record to the pin the goal25d packager set at its Goal25D start hash, for the records that changed between the two starts."""
    goal25d_start = read(GOAL25D_BASELINE)
    out = dict(goal25d_protected_paths(goal25d_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal25d receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal25d_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift.
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal25D and Goal26A starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal25d_start):
    """{path: {receipts, start_sha256, goal25d_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the frozen start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal25d receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal25d receipt')
        if p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the goal24a receipt hash is '
                           'older than the start hash, the later receipts hash the current content. Frozen at the start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif p == 'migration/GOAL25D-ACCEPTANCE.md':
            explanation = ('Edited after the goal25d package was written (the goal25d receipt hash is the pre-close-out text) and committed in the Goal 25 close-out commit 5b1bf4db, which records the '
                           'real-game acceptance as deferred into Goal 26 (GOAL25.md "明确延期", README 2026-10-21 lines). Part of the close-out set owned by '+CLOSEOUT_OWNER+'. Frozen at the start '
                           'hash; this batch must not change it and the goal25d receipt is not rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22, 23 and 24 in-game acceptance results, the O1 record notes or the thorium follow-up section); the goal25d '
                           'receipt does not hash it. Frozen at the Goal26A start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal25d) records the start hash. Frozen at the start hash; this batch must not '
                           'change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal25d package; the goal25d receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it and the goal25d '
                           'receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal25d_start_sha256=goal25d_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal25d_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def group(p):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA or p in OPTIONAL_JAVA: return 'production'
    if p in ASSETS: return 'production-resource'
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


def original_recipe(text, kind, selector):
    """{pattern, key, count} (shaped), {ingredients, count} (shapeless) or {result, experience} (smelting) of the single original line matching the selector, or None when the line is not
    unique or does not parse. A key expression missing from KEY_TABLE maps to None."""
    lines = [l for l in text.replace('\r\n', '\n').split('\n') if re.search(selector, l)]
    if len(lines) != 1: return None
    line = lines[0]
    if kind == 'smelting':
        m = re.search(r'addSmelting\(.*?, new ItemStack\(ModBlocks\.(\w+)\), ([\d.]+)F\)', line)
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
    goal25d_start = read(GOAL25D_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal26A commits nothing), the recorded start: a CLEAN worktree on the Goal 26 planning
    # commit, on the Goal 25 close-out commit, on the Goal 25 planning commit, on the pushed Goal 24 close-out commit.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 26 planning commit'
    assert START_HEAD.read_text(encoding='utf-8').strip() == start_head, 'start_head.txt differs from the baseline target head'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 26 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    status_lines = base['target_status'].splitlines()
    assert status_lines == [] and START_STATUS.read_text(encoding='utf-8').splitlines() == [], 'The frozen start was not a clean worktree (baseline target_status / start_status.txt)'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal25d receipt records another original commit than the frozen start'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal26A: '+head
    chain = {n: git_ro(ROOT, 'rev-parse', f'HEAD~{n}').strip() for n in (1, 2, 3)}
    assert chain[1].startswith(GOAL25_CLOSEOUT) and chain[2].startswith(GOAL25_PLANNING) and chain[3].startswith(GOAL24_CLOSEOUT), \
        'NEO HEAD~1..3 are not the Goal 25 close-out 5b1bf4db, the Goal 25 planning 783b6d13 and the Goal 24 close-out 17c8062f commits: '+str(chain)
    assert set(base['start_content']) == {'committed', 'uncommitted'} and base['start_content']['uncommitted'].startswith('none'), 'Baseline start content differs'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b', 'goal22c', 'goal22d',
                                                          'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b', 'goal24c', 'goal24d', 'goal24e', 'goal25a', 'goal25b', 'goal25c'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256_at_freeze'] == base['build_libs_jar_sha256_at_freeze'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_lines'] == 0 and startup['planning_commit']['hash'] == start_head and startup['planning_commit']['parent'] == GOAL25_CLOSEOUT \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'], \
        'startup-verification.json differs from baseline.json'
    start_stamp = start_json(base, STAMP)
    assert base['stamp_state']['generated_resources_recorded'] == prior_receipt['generated_resource_count'] == len(start_stamp['generated']) \
        and base['stamp_state']['recorded_inputs'] == len(start_stamp['inputs']), 'The start generation stamp does not hold the goal25d generated tree and inputs'
    start_jar_sha = base['build_libs_jar_sha256_at_start']

    # 2. Previous deliveries: the goal25d package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha, 'build/libs at the start is not the goal25d package'
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal25d receipt list + the goal25d package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal25d receipt count + the goal25d release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal25d receipt'
    assert set(base['previous_receipt_evidence_drift']) == {'migration/GOAL25D-ACCEPTANCE.md'}, 'The goal25d receipt drift at the start is not the Goal 25 close-out edit of GOAL25D-ACCEPTANCE.md: '+str(
        list(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal25d_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal25d receipt: '+str(sorted(explained))

    # The Goal 25 close-out commit (5b1bf4db) and the Goal 26 planning commit (8954b531) changed records only between the goal25d package and this start. Computed twice: the goal25d receipt's
    # final hashes against the 26A baseline, and git (read-only) over 783b6d13..8954b531; every drifted receipt path must be named by git, the planning additions are the Goal 26 documents.
    prior_changed = {e['path']: e for e in prior_receipt['changed_files']}
    closeout_drift = sorted(p for p, e in prior_changed.items() if base['files'].get(p) != e['after_sha256'])
    assert closeout_drift == CLOSEOUT_DRIFT, 'The goal25d receipt hashes differ from the Goal26A start for another set than the Goal 25 close-out / Goal 26 planning edits: '+str(closeout_drift)
    git_names = set(git_ro(ROOT, 'diff', '--name-only', GOAL25_PLANNING, start_head).split())
    assert set(closeout_drift) <= git_names, 'Close-out drift paths not named by git diff 783b6d13..8954b531: '+str(sorted(set(closeout_drift) - git_names))
    planning_added = sorted(git_ro(ROOT, 'diff', '--name-only', '--diff-filter=A', GOAL25_CLOSEOUT, start_head).split())
    planning_modified = sorted(git_ro(ROOT, 'diff', '--name-only', '--diff-filter=M', GOAL25_CLOSEOUT, start_head).split())
    assert planning_added == PLANNING_ADDED and planning_modified == PLANNING_MODIFIED, f'The Goal 26 planning commit changed {planning_added} / {planning_modified}, not the expected records'
    closeout_commits = {p: git_ro(ROOT, 'log', '--format=%h', f'{GOAL25_PLANNING}..{start_head}', '--', p).split() for p in closeout_drift}
    closeout_record = dict(
        owner=CLOSEOUT_OWNER, commits=dict(goal25_closeout=chain[1], goal26_planning=start_head),
        note='Between the goal25d package and this start the Goal 25 close-out commit 5b1bf4db (25A-25D and their records committed, real-game acceptance deferred into Goal 26) and the Goal 26 '
             'planning commit 8954b531 changed records only. Computed from the goal25d receipt changed_files hashes against the Goal26A baseline and cross-checked against git diff 783b6d13..8954b531 '
             '(read-only); the old receipt is not rewritten.',
        receipt_hash_differs_from_start={p: dict(goal25d_receipt_after_sha256=prior_changed[p]['after_sha256'], start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p),
                                                 commits_since_goal25_planning=closeout_commits[p],
                                                 changed_since_start=sha(ROOT/p) != base['files'].get(p)) for p in closeout_drift},
        goal26_planning_added={p: dict(start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p), changed_since_start=sha(ROOT/p) != base['files'].get(p)) for p in planning_added},
        goal26_planning_modified={p: dict(start_sha256=base['files'].get(p), current_sha256=sha(ROOT/p), changed_since_start=sha(ROOT/p) != base['files'].get(p)) for p in planning_modified},
        previous_receipt_drift_explained={p: dict(receipt_sha256=d['receipt'], start_sha256=d['now'], explanation=drift_report[p]['explanation']) for p, d in base['previous_receipt_evidence_drift'].items()})

    # 3. Changes since the start: each path in the owner table, attributed to goal26a. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, f'Path changed since the Goal26A start that the owner table does not list (production outside the {len(MODIFIED_JAVA)} modified Java files, the {len(NEW_JAVA)} new classes incl. '
         'RadiationControlGameTests, the 8 textures, zh_cn.json and the mapping, a protected or frozen record, an unknown file): '+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal25 / Goal24 records or the Goal 26B-D planning documents changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal26A start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD, ANVIL_RECIPES] + GENERATED + SHARED_RECORDS + REPORTS[:1]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    need(sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES], f'{ANVIL_RECIPES} changed since the start (Goal26A adds no anvil row)')
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION + OPTIONAL_JAVA if p.startswith('src/')})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified and {len(NEW_JAVA)} new Java files, the 8 textures and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    goal26_now = sha(ROOT/GOAL26_RECORD)
    concurrent_record = dict(sessions=[], note='baseline.json and startup-verification.json record no concurrent session editing the NEO repository. The batch ran under the main agent with a builder, a '
                                               'GameTest verifier (RadiationControlGameTests, verify_goal26a_radiation_control.py, SmokeGameTests count edit, Gradle), this packaging verifier and a '
                                               'read-only reviewer; each wrote only its named files (scope-before / scope-after snapshots of the verifiers are indexed as evidence). The main agent '
                                               'edited migration/ records, zh_cn.json and the mapping and applied the review fixes (HazmatRegistry, ArmorModHandler, a NtmBlocks comment). '
                                               'migration/GOAL26.md and GOAL26A.md are edited by the main agent of this batch.',
                             goal26_md=dict(start_sha256=base['files'][GOAL26_RECORD], current_sha256=goal26_now, owners=[OWNER]),
                             frozen_planning_documents={p: dict(start_sha256=base['files'][p], current_sha256=sha(ROOT/p)) for p in PLANNING_FROZEN})
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, owners=[OWNER], before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal26A takes no new snapshot)'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'] and base['snapshot']['path'] == SNAPSHOT, 'review-aee05a40f10f snapshot changed'
    production_changed = [p for p in PRODUCTION + OPTIONAL_JAVA if p in changes]

    # The modified production files keep their start line endings; new Java files are not mixed.
    start_text = {}
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]:
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
    insert_summary, edit_summary, inserted_lines, added_lines, removed_lines, removed_comments = {}, {}, {}, {}, {}, {}
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]:
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
        elif p in ALLOWED_REMOVED_CODE:
            # Compared stripped: re-indented lines cancel out; what is left was really removed.
            net_removed = list((Counter(l.strip() for l in start_lines) - Counter(l.strip() for l in live_lines)).elements())
            comments = [l for l in net_removed if is_comment(l)]
            code = [l for l in net_removed if not is_comment(l)]
            stray = [l for l in code if not ALLOWED_REMOVED_CODE[p] or not l.startswith(ALLOWED_REMOVED_CODE[p])]
            need(not stray, f'{p} removes start code lines the owner table does not allow: {[l[:90] for l in stray[:4]]}')
            removed_comments[p] = [l for l in comments if l]
        else:
            need(False, f'{p} is neither in STRICT_INSERT_ONLY nor in ALLOWED_REMOVED_CODE (owner table gap)')
    # Language provider: the added lines carry exactly the new keys (blocks through their constants, plain keys); nothing is removed.
    provider_added = []
    if PROVIDER in added_lines:
        keys_added, other = base_provider_keys(added_lines[PROVIDER])
        provider_added = sorted(keys_added)
        stray = [l for l in other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} adds lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(keys_added) == len(set(keys_added)), f'{PROVIDER} adds a language key twice')
        need(provider_added == sorted(KEYS), f'{PROVIDER} adds the language keys differently than expected: missing {sorted(set(KEYS) - set(provider_added))[:6]}, unexpected {sorted(set(provider_added) - set(KEYS))[:6]}')
        need(not base_provider_keys(removed_lines[PROVIDER])[0], f'{PROVIDER} removes language entries: {base_provider_keys(removed_lines[PROVIDER])[0][:4]}')
    # The original, parsed from the stored blobs at the recorded commit (independent of the worktree's line endings).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    neo_text = lambda path: (ROOT/path).read_text(encoding='utf-8').replace('\r\n', '\n') if (ROOT/path).is_file() else ''
    # NEO constants against the original (radon, absorber, graphite, sand, glass, crystallizer row, hazmat reader, cladding).
    constants, constants_bad = {}, []
    for cid, (o_path, o_regex, n_path, n_regex, expected, *neo_expected) in CONSTANTS.items():
        o_values = captured(original_text(o_path), o_regex)
        n_values = captured(neo_text(n_path), n_regex) if (ROOT/n_path).is_file() else None
        assert o_values == [normalize_value(str(e)) for e in expected] or o_values == expected, \
            f'The original constant {cid} ({o_path}) is {o_values}, the owner table expects {expected}'
        wanted = [normalize_value(str(e)) for e in neo_expected[0]] if neo_expected else o_values
        constants[cid] = dict(original=o_values, neo=n_values, original_path=o_path, neo_path=n_path, **(dict(neo_expected=wanted) if neo_expected else {}))
        if n_values != wanted: constants_bad.append(cid)
    need(not constants_bad and all(c['neo'] is not None for c in constants.values()),
         f'NEO constants differ from the original (or the NEO source is missing / its text differs from the handoff): {sorted(set(constants_bad) | {k for k, c in constants.items() if c["neo"] is None})}')
    # Occurrence counts in the NEO texts (the corrected forms present, the start forms gone, the registrations once each) against the original counts where the original has the same line.
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
    # Logical sides: the absorber block (common code) imports nothing from net.minecraft.client; the unchanged files stay byte-identical to the start.
    client_imports = {p: (ROOT/p).is_file() and 'net.minecraft.client' in neo_text(p) for p in (ABSORBER_BLOCK, GAS_RADON, ARMOR_UTIL, ARMOR_MOD, HAZMAT, CLADDING)}
    need(not any(client_imports.values()) and (ROOT/ABSORBER_BLOCK).is_file(), 'common-side classes are missing or import net.minecraft.client: '+str(sorted(p for p, v in client_imports.items() if v)))
    need('extends Block' in neo_text(ABSORBER_BLOCK) and 'ChunkRadiationManager.proxy.decrementRad' in neo_text(ABSORBER_BLOCK), f'{ABSORBER_BLOCK} is not a Block that decrements chunk radiation through ChunkRadiationManager.proxy')
    unchanged_bad = [p for p in UNCHANGED_JAVA if not (ROOT/p).is_file() or sha(ROOT/p) != base['files'].get(p)]
    need(not unchanged_bad, 'files that must stay byte-identical to their start changed: '+str(unchanged_bad))
    # Recipes: the 20 crafting / smelting recipes (computed from the generated JSON) against the original rows; the 1 <-> 9 graphite pair against MineralRecipes.java:40.
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
            wanted = dict(type='minecraft:smelting', ingredient={'item': SMELT_INPUTS[rid]}, result=dict(count=1, id=result_id), experience=o_row['experience'], cookingtime=200)
            ok = all(data.get(k) == v for k, v in wanted.items()) and o_row['result'] == result_id.split(':')[1]
            neo_row = {k: data.get(k) for k in wanted}
        else:
            ok = recipe_matches(kind, data, o_row, result_id)
            neo_row = {k: data.get(k) for k in (('pattern', 'key', 'result') if kind == 'shaped' else ('ingredients', 'result'))}
        crafting[rid] = dict(kind=kind, type=data.get('type'), category=data.get('category'), neo=neo_row, original=jsonable(o_row), original_reference=original_refs.get(RECIPE_REFS.get(rid, ''), None), matches=ok)
        need(ok, f'{recipe_dir}{rid}.json differs from the original row: {neo_row} vs {jsonable(o_row)}')
    pair = {}
    for rid, kind in GRAPHITE_PAIR.items():
        path = ROOT/(recipe_dir+rid+'.json')
        if not path.is_file():
            need(False, 'generated recipe missing: '+recipe_dir+rid+'.json')
            continue
        data = read(path)
        if kind == 'shaped': ok = data.get('type') == 'minecraft:crafting_shaped' and data.get('pattern') == ['XXX', 'XXX', 'XXX'] and data.get('key') == {'X': {'item': 'hbmsntm:ingot_graphite'}} \
                                and data.get('result') == dict(count=1, id='hbmsntm:block_graphite')
        else: ok = data.get('type') == 'minecraft:crafting_shapeless' and data.get('ingredients') == [{'item': 'hbmsntm:block_graphite'}] and data.get('result') == dict(count=9, id='hbmsntm:ingot_graphite')
        pair[rid] = dict(kind=kind, type=data.get('type'), category=data.get('category'), matches=ok, original_reference=original_refs['graphite_pair'])
        need(ok, f'{recipe_dir}{rid}.json differs from the 1 <-> 9 pair of MineralRecipes.java:40 (add1To9Pair: 9 ingots -> 1 block, 1 block -> 9 ingots)')
    crafting_all = {**crafting, **pair}
    # Imported resources: byte for byte equal to the original worktree file and its stored blob, and to the ownership record; block_graphite.png stays unchanged.
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
    need((ROOT/GRAPHITE_TEXTURE).is_file() and sha(ROOT/GRAPHITE_TEXTURE) == base['files'].get(GRAPHITE_TEXTURE), f'{GRAPHITE_TEXTURE} (reused by block_graphite) changed or is missing')
    # features.json: the two new groups, the unchanged status and reviewed_source_commit of the previous groups.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert POST_SNAPSHOT_FEATURES <= set(start_features) and not set(NEW_FEATURES) & set(start_features), \
        'The start mapping does not hold the groups of 24B-25D (rbmk-fuel ... rbmk-crane) and not yet the Goal26A groups'
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
    assert (len(en_start), len(zh_start), len(map_start)) == (totals['en_us'], totals['zh_cn'], totals['zh_cn_map']), 'The start language files are not the goal25d totals'
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal25d totals {totals} + {len(KEYS)}')
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal25d generated tree'
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
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected blockstate, model, loot table, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, the pickaxe and shovel tags and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # The pickaxe and shovel tags: the start list plus the new blocks (7 and 2), in the start order.
    tag_facts = {}
    for entry, new_values in ((PICKAXE_ENTRY, PICKAXE_NEW), (SHOVEL_ENTRY, SHOVEL_NEW)):
        tag_start = start_json(base, GENERATED_ROOT+entry)['values']
        tag_now = read(ROOT/(GENERATED_ROOT+entry))['values'] if (ROOT/(GENERATED_ROOT+entry)).is_file() else []
        tag_inserted = insertions(tag_start, tag_now)
        tag_facts[entry] = dict(start_values=len(tag_start), now_values=len(tag_now), inserted=None if tag_inserted is None else sorted(v for _, v in tag_inserted))
        need(tag_inserted is not None and sorted(v for _, v in tag_inserted) == new_values,
             f'the {Path(entry).name} tag is not the start list plus {new_values}: inserted {None if tag_inserted is None else sorted(v for _, v in tag_inserted)}')
    # The generated block files: cube_all blockstates and models on the imported / reused textures, item models, drop-self loot tables.
    generated_facts = {}
    for b, (_, texture) in BLOCK_TABLE.items():
        bs, bm, im, lt = (GENERATED_ROOT+f'assets/hbmsntm/blockstates/{b}.json', GENERATED_ROOT+f'assets/hbmsntm/models/block/{b}.json', GENERATED_ROOT+f'assets/hbmsntm/models/item/{b}.json',
                          GENERATED_ROOT+f'data/hbmsntm/loot_table/blocks/{b}.json')
        live = {n: read(ROOT/p) if (ROOT/p).is_file() else None for n, p in (('blockstate', bs), ('block_model', bm), ('item_model', im), ('loot', lt))}
        generated_facts[b] = live
        need(live['blockstate'] == {'variants': {'': {'model': f'hbmsntm:block/{b}'}}}, f'generated {bs} is not the single-model blockstate: {live["blockstate"]}')
        need(live['block_model'] is not None and live['block_model'].get('parent') == 'minecraft:block/cube_all' and live['block_model'].get('textures') == {'all': f'hbmsntm:block/{texture}'},
             f'generated {bm} is not cube_all on hbmsntm:block/{texture}: {live["block_model"]}')
        need(live['item_model'] == {'parent': f'hbmsntm:block/{b}'}, f'generated {im} is not the block-model parent: {live["item_model"]}')
        need(live['loot'] is not None and live['loot'].get('type') == 'minecraft:block' and [e.get('name') for pool in live['loot'].get('pools', []) for e in pool.get('entries', [])] == [f'hbmsntm:{b}'],
             f'generated {lt} does not drop hbmsntm:{b}: {live["loot"]}')
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
    radiation_test_names = sorted(GAMETEST_METHOD.findall((ROOT/RADIATION_TESTS).read_text(encoding='utf-8'))) if (ROOT/RADIATION_TESTS).is_file() else []
    radiation_annotations = annotations(ROOT/RADIATION_TESTS) if (ROOT/RADIATION_TESTS).is_file() else 0
    need(bool(radiation_test_names) and radiation_annotations == len(radiation_test_names), f'{RADIATION_TESTS} holds {radiation_annotations} @GameTest annotations and {len(radiation_test_names)} parsed methods')
    need(gametest_added == radiation_annotations, f'GameTest sources grew by {gametest_added} tests, RadiationControlGameTests holds {radiation_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in radiation_test_names), 'GameTest log lacks "[hbm-radiation-control] <name> passed" for: '+str([n for n in radiation_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal26a/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal26a/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal26a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal26a/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal26a/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA + OPTIONAL_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal26a/production-vs-start.diff (make_production_diff.py)') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal25d final run plus the Goal26A verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal25d final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal26A suite is already in the goal25d final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal26a/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal25d final set + the Goal26A verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal26a/'+VERIFY_REPORT+' (tools/migration/verify_goal26a_radiation_control.py report)'):
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
        verifier_references = sorted(set(re.findall(r'(?:BlockGasRadon|BlockAbsorber|ArmorUtil|ArmorRegistry|ArmorModHandler|HazmatRegistry|ItemModCladding|ToolRecipes|CraftingManager|SmeltingRecipes|'
                                                      r'MineralRecipes|CrystallizerRecipes|ModBlocks|ModEventHandlerClient)\.java:\d+(?:-\d+)?', json.dumps(report, ensure_ascii=False))))
        # The verifier ran against the final GameTest log and expected the sources' total.
        gt_extra = (report.get('extra') or {}).get('gametest_log') or {}
        need(Path(str(gt_extra.get('log', ''))).as_posix().endswith(Path(gametest_log or GAMETEST_LOG).as_posix()) and gt_extra.get('expected_total') == gametest_expected
             and gt_extra.get('all_passed') == f'All {gametest_expected} required tests passed', f'{VERIFY_REPORT} was not run against the final GameTest log with the {gametest_expected} sources total: {gt_extra.get("log")}, {gt_extra.get("all_passed")}')
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the goal25d compare target paths (which hold the 24A-25D paths) plus this batch's compare-inventory paths).
    cmp25d = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal25d/compare.json differs from the goal25d receipt'
    c25d_added = sorted(p for p in compare_paths(cmp25d['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c25d_modified = sorted(p for p in compare_paths(cmp25d['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(c25d_added) | set(c25d_modified) | set(own_target))
    expected_added = sorted(set(c25d_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal26a/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24a-25d paths + %d of this batch)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(c25d_added) + len(c25d_modified), len(own_target))):
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
        owner_of_target = lambda p: [OWNER] if p in own_target else ['goal24a-goal25d (goal25d compare inventory)']
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: owner_of_target(p) for p in listed},
                       goal25d_paths=len(c25d_added) + len(c25d_modified), goal26a_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the groups of 24B-25D.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - POST_SNAPSHOT_FEATURES,
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without the groups of 24B-25D)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal26a.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal25d) package (run the final build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 8 textures and every compiled class equal the sources.
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
            recompile_only = set()
            for n, pairs in RECOMPILE_ONLY.items():
                if n not in jar_delta['modified']: continue
                patched = prior.read(n)
                for a, b in pairs:
                    assert patched.count(a) == 1, (n, a)
                    patched = patched.replace(a, b)
                if patched == jar.read(n): recompile_only.add(n)
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        generated_entries = set(generated_added)
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if n.endswith('.class') and owner_class(n) in PRODUCTION_JAVA: owner = [OWNER]
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY, PICKAXE_ENTRY, SHOVEL_ENTRY, 'META-INF/MANIFEST.MF'): owner = [OWNER]
                elif kind == 'added' and (n in asset_entries or n in generated_entries): owner = [OWNER]
                elif kind == 'modified' and n in recompile_only and owner_class(n) not in changes: owner = [RECOMPILE_OWNER]
                if not owner: unowned.append(f'{kind}: {n}' + (' [source ' + owner_class(n) + ' unchanged since the start: a recompile difference, not a source change]' if n.endswith('.class') and owner_class(n) not in changes else ''))
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 8 imported textures, the generated additions and '
             'the modified en_us.json / zh_cn.json / pickaxe and shovel tags / MANIFEST.MF are owned): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class') and n not in recompile_only]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA),
             'Changed Java sources and goal26a JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, PICKAXE_ENTRY, SHOVEL_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')} - {'META-INF/MANIFEST.MF'}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported textures + language + pickaxe and shovel tags + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for p in MODIFIED_JAVA:
            if p in SAME_CLASS_JAVA: continue
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['modified'], outer+'.class is not a modified JAR class')
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
    for p in SHARED_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p
    # Informational (not a pending item): top-level OUT files no evidence list indexes, for the main agent to extend REVIEW_EVIDENCE with.
    indexed = {Path(p).relative_to(OUT.relative_to(ROOT)).as_posix() for p in evidence if p.startswith(OUT.relative_to(ROOT).as_posix()+'/')}
    unindexed = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in indexed and p.name != 'baseline.json')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added),
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal25d_start=sorted(repinned),
                   closeout_and_planning_drift=closeout_drift, closeout_unchanged_since_start={p: d['changed_since_start'] is False for p, d in closeout_record['receipt_hash_differs_from_start'].items()},
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds,
                   insert_lines=insert_summary, edit_counts=edit_summary, removed_comment_lines={p: len(v) for p, v in removed_comments.items()},
                   constants={k: c['neo'] == c.get('neo_expected', c['original']) for k, c in constants.items()}, counts={k: c['neo'] == c['expected'] for k, c in counts.items()},
                   recipes={k: v['matches'] for k, v in crafting_all.items()}, client_imports_in_common_classes=sorted(p for p, v in client_imports.items() if v),
                   gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_radiation_tests=radiation_test_names, final_suites_expected=final_expected,
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
    radiation_control = dict(neo=[GAS_RADON, ABSORBER_BLOCK, ARMOR_UTIL, ARMOR_REGISTRY, ARMOR_MOD, HAZMAT, CLADDING, BLOCKS, CRYSTALLIZER, RECIPE_PROVIDER, SMOKE_TESTS],
                             original=[p for p in O_SOURCES], constants=constants, counts=counts, known_differences=KNOWN_DIFFERENCES, recipes=crafting_all,
                             unreachable_inputs=UNREACHABLE, generated_files=generated_facts, generated_tags=tag_facts, original_references=original_refs, hazard_fixes=HAZARD_FIXES,
                             defaults=dict(radon_filter_damage=1, radon_rad_bypass=0.05, radon_asbestos=1, absorber_tiers='2.5 / 10 / 100 / 10,000', absorber_tick_rate=10, absorber_random_ticks=True,
                                           absorber_hardness=5, absorber_resistance=10, graphite_encouragement=30, graphite_flammability=5, sand_hardness=0.5, glass_hardness=0.3, smelting_xp=0.25,
                                           smelting_time=200, crystallizer_rows=47, crystallizer_new_row='coal block tag -> block_graphite, hydrogen peroxide 500 mB, 600 ticks, productivity 0'),
                             note='The radon block (BlockGasRadon.java:32-37) contaminates every living entity in it whose head is not protected against PARTICLE_FINE (RAD_BYPASS 0.05 per tick, asbestos +1) and '
                                  'only wears the gas-mask filter down by 1 when it is (hasAllProtection on the head); the start NEO test was inverted. The absorbers (BlockAbsorber.java:63-79) remove '
                                  '2.5 / 10 / 100 / 10,000 chunk radiation every 10 ticks and on random ticks. Graphite, sand and glass follow ModBlocks.java:1410,1641-1643; the recipes are the '
                                  'original rows (ToolRecipes.java:113-116, CraftingManager.java:626-630,685-688,753-756,761,992, MineralRecipes.java:40, SmeltingRecipes.java:132-133); the crystallizer row is '
                                  'CrystallizerRecipes.java:99. Not migrated or deferred: connected-texture glass, the OpenComputers/other-mod paths, the IGasMask branches before 26B (static only); four recipes '
                                  'are registered but not reachable yet.')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), len(ASSETS), len(radiation_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=start_head[:8],
                   uncommitted_start=dict(status_entries=len(status_lines), description='none (clean worktree at the Goal 26 planning commit 8954b531)', base_release=previous_rel, status=status_lines,
                                          note='The Goal25A..Goal25D deliveries are committed (5b1bf4db); the start tree is the planning commit 8954b531 itself, hashed live before the first 26A write '
                                               '(freeze_start.py) with no start_hashes.txt.'),
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, build_libs_sha256_at_freeze=base['build_libs_jar_sha256_at_freeze'],
                                      reconstruction=base['reconstruction'], goal25_closeout_commit=chain[1], goal25_planning_commit=chain[2], goal24_closeout_commit=chain[3],
                                      note='The start tree is HEAD 8954b531 (the Goal 26 planning commit, local, not pushed) on top of the Goal 25 close-out commit 5b1bf4db (25A-25D, local) on the Goal 25 '
                                           'planning commit 783b6d13 on the pushed Goal 24 close-out commit 17c8062f; the worktree was CLEAN. build/libs at the start AND at the freeze IS the goal25d '
                                           'package. The original did not move since 24A (aee05a40f). freeze_start.py hashed every tracked file live (baseline files) before the first 26A write and '
                                           'copied the 29 files the batch planned to touch (baseline-files); paths this batch changes record the start hash as before_sha256.'),
                   closeout_and_planning=closeout_record,
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, removed_comment_lines=removed_comments, start_copies_supplement=[],
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   radiation_control=radiation_control,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn=zh_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note=f'{EXPECTED_KINDS.get("upstream", 0)} entries are upstream with the original English and Chinese verbatim (the nine block names tile.*.name, the ten potion.hbm_* effect names and '
                                      f'thirteen hazard.* texts, original en_US.lang / zh_CN.lang); {EXPECTED_KINDS.get("local", 0)} are local: hazard.gas_inert (the original Chinese mistranslates Asphyxiants) and '
                                      'hazard.hold_shift (the original text is hard-coded in ModEventHandlerClient.java:700-705). No existing key changes its English value; no deferred entry is added.'),
                   recipes=dict(assembly=None, crafting=crafting_all, not_registered=[], crystallizer_default_rows=47,
                                anvil_recipes_unchanged=sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES],
                                note='Twenty crafting / smelting recipes (the original rows of ToolRecipes, CraftingManager, MineralRecipes and SmeltingRecipes, each generated JSON equal to its parsed '
                                     'original row; the 1 <-> 9 graphite pair through addMaterialBlockRecipe) and one crystallizer default row. AnvilRecipes stays unchanged. Unreachable inputs: '
                                     +'; '.join(f'{k} needs {v}' for k, v in UNREACHABLE.items())+'.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report,
                   **{k: v for k, v in prior_receipt.items() if k.startswith('repinned_since_')},
                   repinned_since_goal25d_start={p: dict(goal25d_start_pin_sha256=h, goal26a_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   concurrent_session=concurrent_record,
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_radiation_tests=radiation_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per RadiationControlGameTests test: the radon block on '
                                      'protected / unprotected entities and the filter wear, the filter and mod-slot reads, removeMod and readConfig, the absorbers\' tick and random tick, the recipes, '
                                      'hardness and registration; no client (tooltips, glass rendering, falling-sand visuals and effect names are not rendered), no real player, no saved world, no survival chain.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   dropped_keys=['rbmk_crane (the Goal25D-only key; Goal26A adds radiation_control; the crane constants, sync sequences and key facts are not carried)'],
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier with in-memory '
                            'mutations, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and one static review. No in-game client test was run: '
                            'the hazard tooltips and Chinese UI, the glass faces and cutout rendering, falling lead / boron sand, the status-effect names and the block models in game are unverified; no '
                            'survival chain (crafting an absorber or the detectors, standing in a radon cloud) in a world was run; no multiplayer or dedicated server beyond GameTest; the IGasMask '
                            'branches (a filter on a real gas mask or a helmet mod) are covered statically only before 26B; GOAL26A-ACCEPTANCE.md (the real-game checklist) is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest != previous_sha, 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal26a JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal25d package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
