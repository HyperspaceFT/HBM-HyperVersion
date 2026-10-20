"""Package Goal24E (the RBMK console and the Goal 24 master acceptance checklist: the console multiblock rbmk_console (RBMKConsoleBlock with the {3,0,0,0,2,2} panel plus the {0,0,0,1,2,2}
base row, RBMKConsoleBlockEntity with the 15 x 15 scan every 10 ticks, six configurable screens, the 60-point flux graph, the full sync every 10 ticks and the server-validated
control packets, RBMKConsoleMenu, RBMKConsoleScreen, RenderRBMKConsole with rbmk_console.obj), the linking tool rbmk_tool (RBMKToolItem), the sound block.shutdown, two workbench
recipes, six imported resources, the language keys, RBMKConsoleGameTests and the acceptance checklist GOAL24E-ACCEPTANCE.md) cumulatively on the goal24d package, without replacing any
previous delivery.

python -B -X utf8 tools/migration/package_goal24e.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal24e/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal24e/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal24e/baseline.json: NEO HEAD 1114adf5 (the Goal 24 planning commit on top of the pushed Goal 23 close-out commit 09173669)
with the UNCOMMITTED Goal24A, Goal24B, Goal24C and Goal24D deliveries (754 default status entries). The original HEAD aee05a40f did not move since 24A, so there is no upstream
classification and no new snapshot. build/libs at the start is the goal24d package byte for byte. Every change since the start is computed from the baseline file
hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The modified production files are compared with
their start bytes (baseline-files holds all 47 scope copies). The JAR delta against the goal24d package is attributed per entry (goal24e); any entry without exactly one
owner fails. Counts that records quote (suites, GameTests, generated resources, classes, releases, language keys) are computed here, never hard-coded; the previous
package's SHA-256, size and receipt hashes are read from the files and the baseline, not from literals.

The receipts that hash records (goal21a..goal24c, the review-g21d-hazard-fix receipt) already differ from their older hashes at the frozen start for the acceptance
checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a working notes build/migration/goal24a/main-notes.md (baseline older_receipt_evidence_drift;
the goal24a receipt hashed main-notes.md before the 24A session appended its "Delivered" section, the goal24b..goal24d receipts hash it at its current hash). They
are listed in the receipt as start drift and must still equal their Goal24E start hash; no receipt is rewritten and no other protected path may drift. The goal24d
receipt has no drift of its own at the start (baseline previous_receipt_evidence_drift is empty).

Like the Goal24D packager this one has a single compare run (build/migration/goal24e/compare.json against the snapshot review-aee05a40f10f.json taken at the end of
24A: original 0/0/0, target = exactly the Goal24D compare-inventory paths (read from build/migration/goal24d/compare.json, which already holds the 24B and 24C paths) plus this
batch's), no upstream classification; it adds the rbmk_console constants (checked against the original and NEO source texts). The Goal24D-only receipt key rbmk_control_steam
is dropped."""
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
from package_goal22a import annotations
from package_goal22b import (git_ro, edit_counts, stale_diff, receipt_protected, start_drift_paths,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE
from package_goal23b import report_problems
from package_goal24a import original_text, original_line, original_blob, lang_file, provider_keys as base_provider_keys, SOURCE_HEAD
from package_goal24c import captured, normalize_value
from package_goal24d import (OUT as GOAL24D_OUT, BASELINE as GOAL24D_BASELINE, protected_paths as goal24d_protected_paths)

OUT = ROOT/'build/migration/goal24e'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL24D_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL24D_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal24d/hbmsntm-198A-goal24d.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal24e'
RELEASE_NAME = 'hbmsntm-198A-goal24e.jar'
OWNER = 'goal24e'
PLANNING_PREFIX = '1114adf5'
GOAL23_CLOSEOUT = '09173669'
SNAPSHOT = 'migration/baselines/review-aee05a40f10f.json'
START_STATUS_ENTRIES = 754
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
J = 'src/main/java/com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
CONFIG = J+'config/CommonConfig.java'

# Production (owner goal24e), NEW (handoff-packaging.md; builder-progress.md names the final classes: if the builder names a class differently or adds a helper class, edit this
# list, --check reports the difference as an unassigned src/ path).
NEW_JAVA = [J+p+'.java' for p in (
    'blocks/machine/rbmk/RBMKConsoleBlock', 'blockentity/machine/rbmk/RBMKConsoleBlockEntity', 'inventory/menus/RBMKConsoleMenu', 'inventory/screens/RBMKConsoleScreen',
    'render/blockentity/RenderRBMKConsole', 'items/tools/RBMKToolItem', 'gametest/RBMKConsoleGameTests')]
(CONSOLE_BLOCK, CONSOLE_BE, CONSOLE_MENU, CONSOLE_SCREEN, CONSOLE_RENDERER, TOOL_ITEM, CONSOLE_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (the real set is computed from the tree against the start and every other src/ change fails).
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blocks/NtmBlocks', 'blockentity/NtmBlockEntityTypes', 'inventory/NtmMenuTypes', 'items/NtmItems', 'registry/NtmSoundEvents', 'main/NuclearTechModClient', 'main/ClientProxy',
    'main/ResourceManager', 'inventory/NtmCreativeTabs', 'datagen/NtmBlockStateProvider', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider',
    'datagen/NtmLanguageProvider', 'datagen/NtmRecipeProvider', 'datagen/NtmSoundDefinitionsProvider')]
(BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, ITEMS, SOUND_EVENTS, CLIENT, CLIENT_PROXY, RESOURCE_MANAGER, CREATIVE_TABS, BLOCK_STATE_PROVIDER, LOOT_PROVIDER, TAG_PROVIDER,
 PROVIDER, RECIPE_PROVIDER, SOUND_PROVIDER) = MODIFIED_JAVA
# The handoff expected NtmItemModelProvider to change (the flat rbmk_tool item model); it may stay unchanged if builder-progress.md says another provider path is used.
ITEM_MODEL_PROVIDER = J+'datagen/NtmItemModelProvider.java'
OPTIONAL_JAVA = [ITEM_MODEL_PROVIDER]
# No new package-info and no comment-only edit in this batch: every new Java source compiles to a class and every modified source changes a class file.
NO_CLASS_JAVA = []
SAME_CLASS_JAVA = []
ANVIL_RECIPES = J+'inventory/recipes/anvil/AnvilRecipes.java'
# Registration and datagen files that must stay insert-only against their start bytes. The block state and recipe providers may drop comment lines (a "later batch" marker), nothing else.
STRICT_INSERT_ONLY = [BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, ITEMS, SOUND_EVENTS, CLIENT, CLIENT_PROXY, RESOURCE_MANAGER, CREATIVE_TABS, LOOT_PROVIDER, TAG_PROVIDER, PROVIDER,
                      ITEM_MODEL_PROVIDER, SOUND_PROVIDER, ZH_INPUT]
# For the non-strict files every removed start line must be a comment line or start with one of these (stripped) code prefixes; the removed comments are listed in the receipt.
ALLOWED_REMOVED_CODE = {
    BLOCK_STATE_PROVIDER: (),
    RECIPE_PROVIDER: (),
}
# The 6 imported original resources: NEO target -> original path, derived by the layout rules of the ownership record (textures/blocks -> textures/block, textures/items ->
# textures/item, models/rbmk -> models/obj/rbmk, the model texture, the GUI texture and the sound keep their path).
ASSETS = {ASSETS_ROOT+'models/obj/rbmk/rbmk_console.obj': O_RES+'models/rbmk/rbmk_console.obj',
          ASSETS_ROOT+'textures/models/machines/rbmk_control.png': O_RES+'textures/models/machines/rbmk_control.png',
          ASSETS_ROOT+'textures/gui/reactors/gui_rbmk_console.png': O_RES+'textures/gui/reactors/gui_rbmk_console.png',
          ASSETS_ROOT+'textures/block/rbmk/rbmk_console.png': O_RES+'textures/blocks/rbmk/rbmk_console.png',
          ASSETS_ROOT+'textures/item/rbmk_tool.png': O_RES+'textures/items/rbmk_tool.png',
          ASSETS_ROOT+'sounds/block/shutdown.ogg': O_RES+'sounds/block/shutdown.ogg'}
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_JAVA
PRODUCTION = NEW_JAVA + MODIFIED_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
TAG_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
SOUNDS_ENTRY = 'assets/hbmsntm/sounds.json'
GENERATED = [STAMP, EN, GENERATED_ROOT+TAG_ENTRY, GENERATED_ROOT+SOUNDS_ENTRY]
# Generated by runData for this batch (relative to src/generated/resources): the blockstate, the particle-only block model (rbmk_console_particle), item models and loot table of the console, the two recipes + their advancements.
# The advancement folder (recipes/misc, recipes/tools ...) depends on the recipe category, so the two advancements are matched by name and exactly one each is required.
EXPECTED_GENERATED_BASE = sorted(['assets/hbmsntm/blockstates/rbmk_console.json', 'assets/hbmsntm/models/block/rbmk_console_particle.json', 'assets/hbmsntm/models/item/rbmk_console.json',
                                  'assets/hbmsntm/models/item/rbmk_tool.json', 'data/hbmsntm/loot_table/blocks/rbmk_console.json', 'data/hbmsntm/recipe/rbmk_console.json',
                                  'data/hbmsntm/recipe/rbmk_tool.json'])
_RECIPES = ('rbmk_console', 'rbmk_tool')
ADVANCEMENT = re.compile(r'data/hbmsntm/advancement/recipes/[a-z_]+/(rbmk_console|rbmk_tool)\.json')
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, TAG_ENTRY, SOUNDS_ENTRY])
NEW_TOOLS = ['tools/migration/verify_goal24e_rbmk_console.py', 'tools/migration/package_goal24e.py']
TOOLS = NEW_TOOLS
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal24e-* or GOAL24E-* record is hashed as well.
REPORTS = ['migration/GOAL24E.md', 'migration/GOAL24E-ACCEPTANCE.md', 'migration/goal24e-static-review.md', 'migration/goal24e-localization-review.json',
           'migration/goal24e-resource-ownership.json']
RESOURCE_OWNERSHIP = REPORTS[4]
BATCH_RECORD = re.compile(r'migration/(goal24e-[^/]+\.(json|md)|GOAL24E-[^/]+\.md)')
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', 'migration/GOAL24.md']
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED_BASE + the advancements.
REQUIRED_CHANGES = PRODUCTION + GENERATED + TOOLS + REPORTS + SHARED_RECORDS
# The new language keys: NEO key -> original key (None: a NEO-local key). Expected from handoff-production.md section H: 23 upstream (the block name, the four rbmk_tool item keys, rbmk.heat,
# rbmk.moderated, rbmk.rod.*, rbmk.screen.* and rbmk.console.assign / none / col_temp / rod_extraction / fuel_depletion / fuel_poison / fuel_temp; rbmk.boiler.* and rbmk.control.* exist
# since 24D; rbmk.console.assign is a local adaptation, see LOCAL_ADAPTED) and 27 NEO-local keys (the hard-coded English of GUIRBMKConsole: the three tooltips, the ten colour group lines and the 14 column type names).
KEYS = {'block.hbmsntm.rbmk_console': 'tile.rbmk_console.name', 'item.hbmsntm.rbmk_tool': 'item.rbmk_tool.name', 'item.hbmsntm.rbmk_tool.desc': 'item.rbmk_tool.desc',
        'item.hbmsntm.rbmk_tool.linked': 'item.rbmk_tool.linked', 'item.hbmsntm.rbmk_tool.set': 'item.rbmk_tool.set'}
KEYS.update({'rbmk.'+t: 'rbmk.'+t for t in ('heat', 'moderated')})
KEYS.update({'rbmk.rod.'+t: 'rbmk.rod.'+t for t in ('depletion', 'xenon', 'coreTemp', 'skinTemp')})
KEYS.update({'rbmk.screen.'+t: 'rbmk.screen.'+t for t in ('core', 'depletion', 'rod', 'temp', 'xenon')})
KEYS.update({'rbmk.console.'+t: 'rbmk.console.'+t for t in ('assign', 'none', 'col_temp', 'rod_extraction', 'fuel_depletion', 'fuel_poison', 'fuel_temp')})
KEYS.update({'rbmk.console.'+t: None for t in ('selectAll', 'deselectAll', 'compressor')})
KEYS.update({f'rbmk.console.group.{c}.{a}': None for c in ('red', 'yellow', 'green', 'blue', 'purple') for a in ('select', 'assign')})
KEYS.update({'rbmk.console.type.'+t: None for t in ('blank', 'fuel', 'fuel_sim', 'control', 'control_auto', 'boiler', 'moderator', 'absorber', 'reflector', 'outgasser', 'breeder',
                                                    'storage', 'cooler', 'heatex')})
# Review A P2-1 (tools/migration/localization.py:186-188, localization_placeholder_mismatch): the original zh_CN.lang:4296 lacks the %s of en_US.lang, so rbmk.console.assign is a LOCAL
# adaptation of an original key: kind local with source_key / source_en / source_zh of the original kept, target_zh with the placeholder, and a reason. key -> expected target_zh.
LOCAL_ADAPTED = {'rbmk.console.assign': '将选定列分配给屏幕 #%s'}
EXPECTED_KINDS = {'upstream': sum(1 for k, v in KEYS.items() if v and k not in LOCAL_ADAPTED), 'local': sum(1 for k, v in KEYS.items() if not v or k in LOCAL_ADAPTED)}
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rbmk-console] %s passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'freeze.log', 'main-notes.md', 'builder-progress.md', 'handoff-production.md',
                  'handoff-gametest.md', 'handoff-verifier.md', 'handoff-review.md', 'handoff-packaging.md', 'make_production_diff.py', 'chain.sh')
# Review files under OUT (for example the two independent static reviews' notes or diffs) the main agent names when it knows them; each must exist and is
# indexed by the receipt. Extend this list from the real run (review notes, the builder's and verifiers' progress and scope files, logs ...);
# --check lists the top-level OUT files that no list indexes.
REVIEW_EVIDENCE = ('make_final_runner.py', 'make_explained.py', 'final_explained.py', 'compare_fail_sets.py', 'packaging-progress.md', 'verifier-pkg/scope-before.txt',
                   'verifier-pkg/scope-after.txt')
GAMETEST_LOG = 'build/migration/goal24e/gametest-final.log'
NEW_SUITE = 'verify_goal24e_rbmk_console.py --gametest-log build/migration/goal24e/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_CONSOLE = 'rbmk-console'
FEATURE_CONTROL, FEATURE_STEAM = 'rbmk-control', 'rbmk-steam'
FEATURE_REACTOR, FEATURE_FUEL = 'rbmk-reactor', 'rbmk-fuel'
RADIATION_NOTE = ('Goal24E: the console only reads and commands an RBMK; reactor radiation and meltdown behaviour are unchanged from Goal24A-24D; the master checklist '
                  'GOAL24E-ACCEPTANCE.md must be run only in a separately authorized disposable world. ')
MELTDOWN_NOTE = ('Goal24E: AZ-5 inserts every manual control rod linked to the console (automatic rods are untouched, and a rod moves at the normal speed with its surge), so it '
                 'does not stop a reactor instantly; meltdown tests only in disposable worlds away from builds. ')
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_CONSOLE = ORIGINAL+'tileentity/machine/rbmk/TileEntityRBMKConsole.java'
O_BLOCK_CONSOLE = ORIGINAL+'blocks/machine/rbmk/RBMKConsole.java'
O_TOOL = ORIGINAL+'items/tool/ItemRBMKTool.java'
O_GUI = ORIGINAL+'inventory/gui/GUIRBMKConsole.java'
O_RENDERER = ORIGINAL+'render/tileentity/RenderRBMKConsole.java'
O_CRAFTING = ORIGINAL+'main/CraftingManager.java'
O_TOOL_RECIPES = ORIGINAL+'crafting/ToolRecipes.java'
O_ANVIL = ORIGINAL+'inventory/recipes/anvil/AnvilRecipes.java'
O_SOUNDS = 'src/main/resources/assets/hbm/sounds.json'
O_SOURCES = [O_CONSOLE, O_BLOCK_CONSOLE, O_TOOL, O_GUI, O_RENDERER, O_CRAFTING, O_TOOL_RECIPES, O_ANVIL, O_SOUNDS]
# The original sources the new mapping group must list (source_paths or source_watch; the group must cover all of them, plus the imported resources).
FEATURE_SOURCES = [O_CONSOLE, O_BLOCK_CONSOLE, O_TOOL, O_GUI, O_RENDERER]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'console_flux_buffer': (O_CONSOLE, 'public static final int fluxDisplayBuffer'), 'console_update': (O_CONSOLE, 'public void updateEntity()'),
    'console_rescan': (O_CONSOLE, 'private void rescan()'), 'console_prepare_screens': (O_CONSOLE, 'private void prepareScreenInfo()'),
    'console_serialize': (O_CONSOLE, 'public void serialize('), 'console_deserialize': (O_CONSOLE, 'public void deserialize('),
    'console_permission': (O_CONSOLE, 'public boolean hasPermission('), 'console_receive_control': (O_CONSOLE, 'public void receiveControl('),
    'console_render_box': (O_CONSOLE, 'public AxisAlignedBB getRenderBoundingBox()'), 'console_rotate': (O_CONSOLE, 'public void rotate()'),
    'console_index_x': (O_CONSOLE, 'public int getXFromIndex('), 'console_index_z': (O_CONSOLE, 'public int getZFromIndex('),
    'console_press_az5': (O_CONSOLE, 'public Object[] pressAZ5('), 'console_screen_types': (O_CONSOLE, 'public static enum ScreenType'),
    'block_dimensions': (O_BLOCK_CONSOLE, 'public int[] getDimensions()'), 'block_fill_space': (O_BLOCK_CONSOLE, 'MultiblockHandlerXR.fillSpace('),
    'block_check_requirement': (O_BLOCK_CONSOLE, 'MultiblockHandlerXR.checkSpace('), 'block_screwdriver': (O_BLOCK_CONSOLE, 'ToolType.SCREWDRIVER'),
    'tool_use': (O_TOOL, 'public boolean onItemUse('), 'tool_attack': (O_TOOL, 'new AttributeModifier(field_111210_e, "Weapon modifier"'),
    'gui_az5': (O_GUI, 'lastPress + 3000'), 'gui_hover_typo': (O_GUI, 'guiTop + 11 + 10150'), 'gui_send_level': (O_GUI, 'control.setDouble("level", 0)'),
    'render_screens': (O_RENDERER, 'glDepthMask(false)'),
    'recipe_rbmk_console': (O_CRAFTING, 'new ItemStack(ModBlocks.rbmk_console, 1)'), 'recipe_rbmk_tool': (O_TOOL_RECIPES, 'new ItemStack(ModItems.rbmk_tool)'),
    'sound_shutdown': (O_SOUNDS, '"block.shutdown"'),
}


class OneOf:
    """Several accepted generated forms of one original ingredient (an item and the tag NEO's providers use for the same oredict key)."""

    def __init__(self, *forms):
        self.forms = list(forms)


def jsonable(value):
    if isinstance(value, OneOf): return {'one_of': value.forms}
    if isinstance(value, dict): return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list): return [jsonable(v) for v in value]
    return value


# Original crafting-manager key expressions -> the NEO ingredient (each generated recipe is compared against the parsed original row). Forms follow the existing generated
# recipes: items by registry name, glass panes through the c:glass_panes tag (the original KEY_ANYPANE oredict), boron / lead / iron ingots as the item or the c:ingots tag
# the provider uses for the same oredict key (OneOf: the receipt records the form that was generated).
KEY_TABLE = {'B.ingot()': OneOf({'item': 'hbmsntm:ingot_boron'}, {'tag': 'c:ingots/boron'}), 'ModBlocks.deco_rbmk': {'item': 'hbmsntm:deco_rbmk'},
             'KEY_ANYPANE': OneOf({'tag': 'c:glass_panes'}, {'item': 'minecraft:glass_pane'}),
             'DictFrame.fromOne(ModItems.circuit, EnumCircuitType.ANALOG)': {'item': 'hbmsntm:circuit_analog_board'},
             'PB.ingot()': OneOf({'item': 'hbmsntm:ingot_lead'}, {'tag': 'c:ingots/lead'}), 'IRON.ingot()': OneOf({'item': 'minecraft:iron_ingot'}, {'tag': 'c:ingots/iron'})}
# Constants compared between the original and NEO source texts: id -> (original path, regex, NEO path, regex, expected unique values in order[, expected NEO values when they differ]).
# Numbers are compared as floats (underscores dropped, F / D suffixes dropped), anything else as text. The group-1 value of every match is collected. A NEO regex that finds
# nothing (the class is not written yet, or its text differs from the handoff) is reported as pending with its id.
CONSTANTS = {
    'flux_buffer': (O_CONSOLE, r'fluxDisplayBuffer = (\d+);', CONSOLE_BE, r'fluxDisplayBuffer = (\d+);', [60]),
    'scan_width': (O_CONSOLE, r'new RBMKColumn\[(\d+) \* \d+\]', CONSOLE_BE, r'new RBMKColumn\[(\d+) \* \d+\]', [15]),
    'scan_depth': (O_CONSOLE, r'new RBMKColumn\[\d+ \* (\d+)\]', CONSOLE_BE, r'new RBMKColumn\[\d+ \* (\d+)\]', [15]),
    'grid_width': (O_CONSOLE, r'col % (\d+) - \d+', CONSOLE_BE, r'col % (\d+) - \d+', [15]),
    'grid_centre': (O_CONSOLE, r'col % \d+ - (\d+)', CONSOLE_BE, r'col % \d+ - (\d+)', [7]),
    'screen_count': (O_CONSOLE, r'new RBMKScreen\[(\d+)\]', CONSOLE_BE, r'new RBMKScreen\[(\d+)\]', [6]),
    'scan_period': (O_CONSOLE, r'getTotalWorldTime\(\) % (\d+) == 0', CONSOLE_BE, r'getGameTime\(\) % (\d+) == 0', [10]),
    'sync_range': (O_CONSOLE, r'networkPackNT\((\d+)\)', CONSOLE_BE, r'networkPackNT\((\d+)\)', [50]),
    'permission_distance': (O_CONSOLE, r'lengthVector\(\) < (\d+)', CONSOLE_BE, r'\.length\(\) < (\d+)', [20]),
    'rotation_steps': (O_CONSOLE, r'\(rotation \+ 1\) % (\d+)', CONSOLE_BE, r'\(rotation \+ 1\) % (\d+)', [4]),
    'block_dimensions': (O_BLOCK_CONSOLE, r'getDimensions\(\) \{\s*return new int\[\] \{([\d, ]+)\};', CONSOLE_BLOCK, r'getDimensions\(\) \{\s*return new int\[\] \{([\d, ]+)\};', ['3, 0, 0, 0, 2, 2']),
    'block_offset': (O_BLOCK_CONSOLE, r'getOffset\(\) \{\s*return (\d+);', CONSOLE_BLOCK, r'getOffset\(\) \{\s*return (\d+);', [1]),
    'block_second_box': (O_BLOCK_CONSOLE, r'fillSpace\([^;]*new int\[\] \{([\d, ]+)\}', CONSOLE_BLOCK, r'EXTRA_DIMENSIONS = new int\[\] \{([\d, ]+)\}', ['0, 0, 0, 1, 2, 2']),
    'az5_cooldown_ms': (O_GUI, r'lastPress \+ (\d+) < System\.currentTimeMillis', CONSOLE_SCREEN, r'lastPress \+ (\d+)L? <', [3000]),
    'az5_level': (O_GUI, r'control\.setDouble\("level", ([\d.]+)\)', CONSOLE_BE, r'putDouble\("level", ([\d.]+)D?\)', [0]),
    'tool_attack_damage': (O_TOOL, r'"Weapon modifier", ([\d.]+), 0\)', TOOL_ITEM, r'(?:BASE_ATTACK_DAMAGE_ID|"Weapon modifier")\s*,\s*([\d.]+)D?\s*,', [2]),
}
SCREEN_TYPES = ('NONE', 'COL_TEMP', 'ROD_EXTRACTION', 'FUEL_DEPLETION', 'FUEL_POISON', 'FUEL_TEMP')
COLUMN_TYPES = ('BLANK', 'FUEL', 'FUEL_SIM', 'CONTROL', 'CONTROL_AUTO', 'BOILER', 'MODERATOR', 'ABSORBER', 'REFLECTOR', 'OUTGASSER', 'BREEDER', 'STORAGE', 'COOLER', 'HEATEX')
COLUMN_TYPE_FILE = J+'blockentity/machine/rbmk/RBMKColumnType.java'


def enum_offsets(text, names):
    """{name: offset} of the enum constants `NAME(<int>)` or `NAME(<int> * <int>)` in the text (the product is evaluated), in source order."""
    out = {}
    for name in names:
        m = re.search(r'\b'+name+r'\((\d+)(?: \* (\d+))?\)', text)
        if m: out[name] = int(m.group(1)) * (int(m.group(2)) if m.group(2) else 1)
    return out


def scope_text(key_count, kinds, assets, tests, total_tests):
    return (f'Goal24E (the RBMK console, its linking tool and the Goal 24 master acceptance checklist): the console rbmk_console (RBMKConsoleBlock, a 5 wide x 4 high panel multiblock '
            f'{{3,0,0,0,2,2}} offset 1 plus the 1-deep base row {{0,0,0,1,2,2}} as the original, the screwdriver rotates the scan in four steps; RBMKConsoleBlockEntity scans the 15 x 15 RBMK '
            f'columns around a linked centre every 10 ticks, six configurable screens (NONE, COL_TEMP, ROD_EXTRACTION, FUEL_DEPLETION, FUEL_POISON, FUEL_TEMP) with five averaged readouts, a 60-point '
            f'neutron flux graph and a full sync every 10 ticks; server-validated control packets set the level of selected manual control rods, assign colour groups, cycle steam-channel '
            f'compressors and configure the screens; AZ-5 sets the target of every selected manual rod to 0 with the block.shutdown alarm on the pressing client; RBMKConsoleMenu, RBMKConsoleScreen '
            f'and RenderRBMKConsole with rbmk_console.obj, the column map and the six screen texts), the linking tool rbmk_tool (RBMKToolItem: sneak-use on a column stores its core, on the '
            f'console links it; a +2 attack damage weapon), the sound block.shutdown (shutdown.ogg), the workbench recipes rbmk_console and rbmk_tool (no anvil rows), {assets} imported '
            f'resources (the OBJ, the model texture, the GUI texture, the block icon, the tool icon and the sound), {key_count} language keys ({kinds.get("upstream", 0)} upstream, '
            f'{kinds.get("local", 0)} NEO-local), {tests} RBMKConsoleGameTests ({total_tests} GameTests in total, one batch per test) and the Goal 24 master real-game acceptance '
            f'checklist GOAL24E-ACCEPTANCE.md (sections 0-8, written, not executed). Gameplay impact: the console reads a whole reactor (up to 15 x 15 columns) and commands manual control '
            f'rods by group; AZ-5 inserts every manual rod (automatic rods are untouched); the console only acts within 20 blocks of its core; the linking tool is a +2 attack weapon.')


PROVIDER_ADD_ITEM_SUFFIX = re.compile(r'this\.add\(NtmItems\.(\w+), (?:DESC|"(\.\w+)"), "(.*)"\);$')


def provider_keys(lines):
    """The 24A reading of the provider lines (items and blocks through their constants, plain keys) plus the item suffix form `this.add(NtmItems.X, DESC | ".suffix", "text")`
    (the rbmk_tool desc / linked / set lines; DESC is the provider constant ".desc"). The suffix form is read first: the 24A item pattern would take it for the item name."""
    keys, other = [], []
    for line in lines:
        m = PROVIDER_ADD_ITEM_SUFFIX.match(line.strip())
        if m: keys.append('item.hbmsntm.'+m.group(1).lower()+(m.group(2) or '.desc'))
        else:
            one_key, one_other = base_provider_keys([line])
            keys += one_key
            other += one_other
    return keys, other


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal24e release directory: '+rel


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy (the 47 scope copies) when it reproduces the baseline hash, otherwise the blob at the start commit (with CRLF
    where the working tree had it) when it reproduces the baseline hash; None when neither does."""
    if (START_FILES/p).is_file():
        data = (START_FILES/p).read_bytes()
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT)
    for data in (blob, blob.replace(b'\n', b'\r\n')):
        if hashlib.sha256(data).hexdigest() == base['files'][p]: return data
    return None


def start_pin(base, p):
    """The Goal24E start hash of a frozen path: baseline files, or for a build/ record that drifted after an older receipt (build/ is Git-ignored, so baseline files does not list
    it) the hash the goal24d receipt records for it (baseline previous_receipt_protected_paths)."""
    if p in base['files']: return base['files'][p]
    return base['previous_receipt_protected_paths'][p]


def protected_paths(base):
    """What the goal24d packager protected (built there from the Goal21A..Goal24C starts and receipts and the goal24d start), plus every path the goal24d receipt hashes
    (base previous_receipt_protected_paths), the paths the older receipts hash (the 24E baseline lists the goal24c receipt among them) and every release file of the frozen
    start (the goal24d package included). The records that already drifted (the acceptance checklists, GOAL21D.md, GOAL22C.md, goal21d-static-review.md and the goal24a
    main-notes.md) are pinned at their Goal24E start hash instead of any receipt hash or any earlier start hash. One path never carries two hashes. Returns (protected,
    repinned) where repinned maps a record to the pin the goal24d packager set at its Goal24D start hash, for the records that changed between the two starts."""
    goal24d_start = read(GOAL24D_BASELINE)
    out = dict(goal24d_protected_paths(goal24d_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'] or p in base['previous_receipt_protected_paths'], 'Start drift path is neither a frozen file nor a record the goal24d receipt hashes: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal24d_start['files'].get(p))
        if earlier is not None and earlier != start_pin(base, p): repinned[p] = earlier
        out[p] = start_pin(base, p)
    # The acceptance checklists (appended to by the in-game acceptance) and any record of previous_receipt_evidence_drift (empty at this start).
    assert all(p.endswith('-ACCEPTANCE.md') or p in base['previous_receipt_evidence_drift'] for p in repinned), 'A non-checklist pin changed between the Goal24D and Goal24E starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal24d_start):
    """{path: {receipts, start_sha256, goal24d_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal24d receipt'] = base['previous_receipt_protected_paths'][p]
        start = start_pin(base, p)
        newest = receipts.get('goal24d receipt')
        if p in base['previous_receipt_evidence_drift']:
            explanation = ('Changed after the goal24d receipt hashed it; the goal24d receipt hash is older than the start hash. Frozen at the start hash; this batch must not '
                           'change it and the goal24d receipt is not rewritten.')
        elif p == 'build/migration/goal24a/main-notes.md':
            explanation = ('The 24A session appended its "Delivered" section to its own working notes 48 seconds after packaging (24B freeze_start.py EXPLAINED_DRIFT); the '
                           'goal24a receipt hash is older than the start hash, the goal24b, goal24c and goal24d receipts hash the current content. Frozen at the start hash; this batch '
                           'must not change it and no earlier receipt is rewritten.')
        elif newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21, 22 and 23 in-game acceptance results, the O1 record notes or the thorium follow-up '
                           'section); the goal24d receipt does not hash it. Frozen at the Goal24E start hash; this batch must not change it and no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal24d) records the start hash. Frozen at the start '
                           'hash; this batch must not change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal24d package; the goal24d receipt hash is older than the start hash. Frozen at the start hash; this batch must not change it '
                           'and the goal24d receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal24d_start_sha256=goal24d_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned: entry['repinned_from_goal24d_start_pin_sha256'] = repinned[p]
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


def split_args(text):
    """The comma-separated arguments of a Java call body at parenthesis depth 0 and outside string literals."""
    out, depth, current, quoted = [], 0, '', False
    for ch in text:
        if ch == '"': quoted = not quoted
        if not quoted:
            if ch == '(': depth += 1
            elif ch == ')': depth -= 1
            elif ch == ',' and depth == 0:
                out.append(current.strip()); current = ''; continue
        current += ch
    out.append(current.strip())
    return [t for t in out if t]


def original_shaped_row(text, kind, output, count):
    """{pattern, key, result} of the single original addRecipeAuto row producing ModBlocks/ModItems `output` x `count` (count defaults to 1 when the ItemStack gives none), or None. A key
    expression missing from KEY_TABLE maps to None."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.search(r'addRecipeAuto\(new ItemStack\(Mod'+kind+r'\.(\w+)(?:, (\d+))?\), new Object\[\] \{ (.*) \}\);', line)
        if not m or m.group(1) != output or int(m.group(2) or 1) != count: continue
        tokens = split_args(m.group(3))
        pattern = [t[1:-1] for t in tokens if t.startswith('"')]
        rest = [t for t in tokens if not t.startswith('"')]
        key = {rest[i].strip("'"): KEY_TABLE.get(rest[i+1]) for i in range(0, len(rest)-1, 2)}
        rows.append(dict(pattern=pattern, key=key, result=dict(count=count, id='hbmsntm:'+output)))
    return rows[0] if len(rows) == 1 else None


def row_matches(neo_row, o_row):
    """The generated row equals the parsed original row; an original ingredient with several accepted forms (OneOf) matches any of them."""
    if neo_row.get('pattern') != o_row['pattern'] or neo_row.get('result') != o_row['result'] or set(neo_row.get('key') or ()) != set(o_row['key']): return False
    return all((neo_row['key'][k] in v.forms) if isinstance(v, OneOf) else neo_row['key'][k] == v for k, v in o_row['key'].items())


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
    goal24d_start = read(GOAL24D_BASELINE)

    # 1. Heads: the clean original at aee05a40f (unchanged since 24A), NEO still at the start commit (Goal24E commits nothing), the recorded start with the uncommitted 24A, 24B, 24C and 24D deliveries.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at aee05a40f'
    assert start_head.startswith(PLANNING_PREFIX), 'The frozen start is not on the Goal 24 planning commit'
    assert base['target_log'].splitlines()[0].startswith(start_head) and 'Goal 24 planning' in base['target_log'].splitlines()[0], 'Baseline target_log does not start with the planning commit'
    # baseline.json stores `status --untracked-files=all` (every untracked file listed); the 754 entries of the handoff are the default `status --porcelain=v1`
    # (untracked directories collapsed) counted by startup-verification.json.
    full_status = [l for l in base['target_status'].splitlines() if l]
    assert full_status and all(l[:2] in ('??', ' M') for l in full_status), 'The frozen start status holds entries other than modified / untracked'
    assert prior_receipt['source_commit'] == SOURCE_HEAD, 'The goal24d receipt records another original commit than the frozen start'
    assert base['pending_small_fixes'] == [], 'The frozen start has a pending small fix'
    assert set(base['start_content']) == {'committed', 'uncommitted'} and all(g in base['start_content']['uncommitted'] for g in ('Goal24A', 'Goal24B', 'Goal24C', 'Goal24D')), \
        'Baseline start content differs'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal24E: '+head
    closeout = git_ro(ROOT, 'rev-parse', 'HEAD~1').strip()
    assert closeout.startswith(GOAL23_CLOSEOUT), 'NEO HEAD~1 is not the Goal 23 close-out commit'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b',
                                                          'goal22c', 'goal22d', 'goal23a', 'goal23b', 'goal23c', 'goal24a', 'goal24b', 'goal24c'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['frozen_file_hashes'] == len(base['files']) and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['old_release_jars'] == len(base['old_releases']) and startup['previous_jar_sha256'] == base['previous_release']['sha256'] \
        and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] and startup['target_head'] == start_head and startup['source_clean'] is True \
        and startup['target_status_entries'] == START_STATUS_ENTRIES and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['source_head'] == SOURCE_HEAD and startup['previous_receipt_evidence_drift'] == base['previous_receipt_evidence_drift'] \
        and startup['older_receipt_evidence_drift'] == base['older_receipt_evidence_drift'] and startup['generated_resources_verified'] == base['stamp_state']['generated_resources_verified'], \
        'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_verified'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal24d generated tree'
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal24d package, every old release file and the protected evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert start_jar_sha == previous_sha and not any(base['build_libs_vs_previous'].values()), 'build/libs at the start is not the previous package byte for byte'
    assert sha(PREVIOUS) == previous_sha and PREVIOUS.stat().st_size == previous_bytes == base['build_libs_jar_bytes'], 'Previous JAR changed'
    assert prior_receipt['sha256'] == previous_sha and prior_receipt['bytes'] == previous_bytes, 'Previous receipt names another JAR'
    previous_receipt_sha = base['old_release_files'][PREVIOUS_RECEIPT.relative_to(ROOT).as_posix()]
    previous_sums_sha = base['old_release_files'][PREVIOUS_SUMS.relative_to(ROOT).as_posix()]
    assert sha(PREVIOUS_RECEIPT) == previous_receipt_sha, 'Previous release.json changed'
    assert sha(PREVIOUS_SUMS) == previous_sums_sha, 'Previous SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (previous_sha+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Previous SHA256SUMS.txt content changed'
    for p, h in base['old_release_files'].items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release file changed: '+p
    previous_rel = PREVIOUS.relative_to(ROOT).as_posix()
    old_releases = dict(base['old_releases'])
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal24d receipt list + the goal24d package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal24d receipt count + the goal24d release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal24d receipt'
    # The goal24d receipt has no record that drifted before the start (it hashes the goal24a main-notes at the hash that file still has).
    assert base['previous_receipt_evidence_drift'] == {}, 'The goal24d receipt evidence drifted at the start: '+str(sorted(base['previous_receipt_evidence_drift']))
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal24d_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal24d receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal24e. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal24E start that the owner table does not list (production outside the 15 modified Java files (NtmItemModelProvider optional), the 7 new '
         'classes incl. RBMKConsoleGameTests, the 6 resources, zh_cn.json and the mapping, a protected record, an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal24E start: '+str(deleted)
    for p in MODIFIED_JAVA + OPTIONAL_JAVA + [ZH_INPUT, LOCALIZATION_RECORD, ANVIL_RECIPES] + GENERATED + SHARED_RECORDS + REPORTS[:1]:
        assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + NEW_TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    need(sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES], f'{ANVIL_RECIPES} changed since the start (the console and the linking tool have no anvil rows; the RBMK anvil rows are tier-4 recycling rows that stay unregistered)')
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION + OPTIONAL_JAVA if p.startswith('src/')})
    need(not outside, 'src/main change outside the 15 modified (+ optional NtmItemModelProvider) and 7 new Java files, the 6 resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}
    assert baselines_now == start_baselines, 'A snapshot was added or changed (Goal24E takes no new snapshot)'
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
            comments = [l for l in removed_lines[p] if l.strip().startswith(('//', '*', '/*'))]
            code = [l for l in removed_lines[p] if l.strip() and l not in comments]
            stray = [l for l in code if not l.strip().startswith(ALLOWED_REMOVED_CODE[p])]
            need(not stray, f'{p} removes start code lines the owner table does not allow: {[l.strip()[:90] for l in stray[:4]]}')
            removed_comments[p] = [l.strip() for l in comments]
    # Language provider: the added lines carry exactly the new keys (blocks and items through constants, plain keys); nothing is removed.
    provider_added = []
    if PROVIDER in added_lines:
        keys_added, other = provider_keys(added_lines[PROVIDER])
        provider_added = sorted(keys_added)
        stray = [l for l in other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} adds lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(keys_added) == len(set(keys_added)), f'{PROVIDER} adds a language key twice')
        need(provider_added == sorted(KEYS), f'{PROVIDER} adds the language keys differently than expected: missing {sorted(set(KEYS) - set(provider_added))[:6]}, unexpected {sorted(set(provider_added) - set(KEYS))[:6]}')
        need(not provider_keys(removed_lines[PROVIDER])[0], f'{PROVIDER} removes language entries: {provider_keys(removed_lines[PROVIDER])[0][:4]}')
    # The original, parsed from the stored blobs at the recorded commit (independent of the worktree's line endings).
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    # NEO constants against the original: scan size and period, sync range, screen count, permission distance, rotation, multiblock dimensions, the AZ-5 cooldown and level, the tool's attack.
    console_constants, constants_bad = {}, []
    for cid, (o_path, o_regex, n_path, n_regex, expected, *neo_expected) in CONSTANTS.items():
        o_values = captured(original_text(o_path), o_regex)
        n_values = captured((ROOT/n_path).read_text(encoding='utf-8').replace('\r\n', '\n'), n_regex) if (ROOT/n_path).is_file() else None
        assert o_values == [normalize_value(str(e)) if not isinstance(e, str) else e for e in expected] or o_values == expected, \
            f'The original constant {cid} ({o_path}) is {o_values}, the owner table expects {expected}'
        wanted = [normalize_value(str(e)) if not isinstance(e, str) else e for e in neo_expected[0]] if neo_expected else o_values
        console_constants[cid] = dict(original=o_values, neo=n_values, original_path=o_path, neo_path=n_path, **(dict(neo_expected=wanted) if neo_expected else {}))
        if n_values != wanted: constants_bad.append(cid)
    need(not constants_bad and all(c['neo'] is not None for c in console_constants.values()),
         f'NEO constants differ from the original (or the NEO source is missing / its text differs from the handoff): {sorted(set(constants_bad) | {k for k, c in console_constants.items() if c["neo"] is None})}')
    # The enum offsets: the six screen types (the icon u in the GUI texture, NEO may write 1 * 18) and the 14 column types (the 24A RBMKColumnType) equal the original's.
    o_console_text = original_text(O_CONSOLE)
    neo_text = lambda path: (ROOT/path).read_text(encoding='utf-8').replace('\r\n', '\n') if (ROOT/path).is_file() else ''
    screen_types = dict(original=enum_offsets(o_console_text, SCREEN_TYPES), neo=enum_offsets(neo_text(CONSOLE_BE), SCREEN_TYPES))
    column_types = dict(original=enum_offsets(o_console_text, COLUMN_TYPES), neo=enum_offsets(neo_text(COLUMN_TYPE_FILE), COLUMN_TYPES))
    assert list(screen_types['original']) == list(SCREEN_TYPES) and list(column_types['original']) == list(COLUMN_TYPES), 'The original ScreenType / ColumnType members are not the owner table\'s'
    need(screen_types['neo'] == screen_types['original'] and list(screen_types['neo']) == list(SCREEN_TYPES),
         f'{CONSOLE_BE} ScreenType members / offsets differ from the original (:538-551): {screen_types["neo"]} vs {screen_types["original"]}')
    need(column_types['neo'] == column_types['original'], f'{COLUMN_TYPE_FILE} members / offsets differ from the original ColumnType (:502-523)')
    # Logical sides: the block entity, block, menu and item (common code) import nothing from net.minecraft.client; the screen and the renderer exist.
    client_imports = {p: (ROOT/p).is_file() and 'net.minecraft.client' in neo_text(p) for p in (CONSOLE_BE, CONSOLE_BLOCK, CONSOLE_MENU, TOOL_ITEM)}
    need(not any(client_imports.values()) and all((ROOT/p).is_file() for p in (CONSOLE_BE, CONSOLE_BLOCK, CONSOLE_MENU, TOOL_ITEM)),
         'common-side console classes are missing or import net.minecraft.client: '+str(sorted(p for p, v in client_imports.items() if v)))
    need('IControlReceiver' in neo_text(CONSOLE_BE) and 'extends DummyableBlock' in neo_text(CONSOLE_BLOCK) and 'IToolable' in neo_text(CONSOLE_BLOCK),
         f'{CONSOLE_BE} does not implement IControlReceiver or {CONSOLE_BLOCK} is not a DummyableBlock + IToolable')
    # Imported resources: byte for byte equal to the original worktree file and, up to line endings (OBJ) or exactly (PNG), its stored blob, and to the ownership record.
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
        if target.endswith('.obj'):
            # The original worktree is clean at SOURCE_HEAD, so its OBJ is the checked-out original; on this Windows checkout it carries CRLF where the stored blob
            # has LF (autocrlf). The blob must match up to that line-ending conversion, and the ownership record's blob fields must say so (goal24a / goal24c precedent).
            normalized = (ROOT/target).read_bytes().replace(b'\r\n', b'\n')
            need(blob.replace(b'\r\n', b'\n') == normalized, f'{target} differs from the {SOURCE_HEAD[:8]} blob of {original} beyond line endings')
            if entry:
                need(entry.get('blob_sha256') == hashlib.sha256(blob).hexdigest() and entry.get('blob_bytes') == len(blob) and entry.get('normalized_sha256') == hashlib.sha256(normalized).hexdigest()
                     and entry.get('normalized_equal_to_blob') is True and entry.get('worktree_crlf_lines') == (ROOT/target).read_bytes().count(b'\r\n'),
                     f'{RESOURCE_OWNERSHIP} blob / CRLF fields differ from the stored blob or the live OBJ: {target}')
        else:
            need(checked_out == blob, f'{target} is not byte-identical to the stored blob of {original} at {SOURCE_HEAD[:8]}')
        if entry:
            need(entry.get('source_path') == original and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') and entry.get('bytes') == (ROOT/target).stat().st_size,
                 f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original path: {target}')
    # features.json: the new rbmk-console group, the unchanged status and reviewed_source_commit of the previous groups.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}
    assert all(f.get('reviewed_source_commit') == SOURCE_HEAD for f in start_features.values()), 'A start mapping group was not at the original commit aee05a40f'
    assert all(g in start_features for g in (FEATURE_FUEL, FEATURE_REACTOR, FEATURE_CONTROL, FEATURE_STEAM)) and FEATURE_CONSOLE not in start_features, \
        'The start mapping does not hold rbmk-fuel (24B), rbmk-reactor (24C), rbmk-control and rbmk-steam (24D) and not yet rbmk-console'
    new_groups = [by_id[g] for g in (FEATURE_CONSOLE,) if g in by_id]

    # 4. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    expected_delta = dict(added=sorted(KEYS), removed=[], changed=[])
    need(en_delta == expected_delta, f'generated en_us.json delta is not the {len(KEYS)} new keys (no value changed): '+json.dumps(en_delta, ensure_ascii=False)[:700])
    need(zh_delta == expected_delta, f'zh_cn.json delta is not the {len(KEYS)} new keys (all old keys unchanged): '+json.dumps(zh_delta, ensure_ascii=False)[:700])
    need(map_delta == expected_delta, f'zh_cn-map.json delta is not the {len(KEYS)} new keys (all old entries unchanged): '+json.dumps(map_delta, ensure_ascii=False)[:700])
    totals = prior_receipt['language']['totals']
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal24d totals {totals} + {len(KEYS)}')
    language_kinds, original_text_checked = {}, False
    if map_delta == expected_delta and en_delta == expected_delta:
        language_kinds = dict(Counter(map_now[k].get('kind') for k in KEYS))
        need(language_kinds == EXPECTED_KINDS, f'zh_cn-map.json kinds of the new entries are {language_kinds}, expected {EXPECTED_KINDS}')
        o_en, o_zh = lang_file(O_LANG_EN), lang_file(O_LANG_ZH)
        bad = []
        for k, source_key in KEYS.items():
            e = map_now[k]
            if e.get('target_en') != en_now.get(k) or e.get('target_zh') != zh_now.get(k): bad.append(k)
            elif k in LOCAL_ADAPTED:
                # Local adaptation of an original key: the original source stays recorded, the Chinese gains the placeholder the original zh lacks.
                if e.get('kind') != 'local' or not e.get('reason') or e.get('source_key') != source_key or e.get('source_en') != e.get('target_en') or e.get('source_en') != o_en.get(source_key)                         or e.get('source_zh') != o_zh.get(source_key) or e.get('target_zh') != LOCAL_ADAPTED[k] or zh_now[k] != LOCAL_ADAPTED[k] or zh_now[k].count('%s') != en_now[k].count('%s')                         or o_zh.get(source_key, '').count('%s') == en_now[k].count('%s'): bad.append(k)
            elif source_key is None:
                # The $ line breaks of the hover lines must survive in the Chinese text.
                if e.get('kind') != 'local' or not e.get('reason') or not zh_now[k] or en_now[k].count('$') != zh_now[k].count('$'): bad.append(k)
            elif e.get('kind') != 'upstream' or e.get('source_key') != source_key or e.get('source_zh') != e.get('target_zh') or e.get('source_en') != e.get('target_en'): bad.append(k)
            elif e.get('source_en') != o_en.get(source_key) or e.get('source_zh') != o_zh.get(source_key): bad.append(k)
        need(not bad, 'zh_cn-map.json entries do not match en_us.json / zh_cn.json, the original en_US.lang / zh_CN.lang values at aee05a40f or the expected kinds: '+str(bad[:8]))
        original_text_checked = not bad
    map_kinds = dict(Counter(e.get('kind') for e in map_now.values()))
    start_kinds = dict(Counter(e.get('kind') for e in map_start.values()))
    need(map_kinds.get('deferred') == start_kinds.get('deferred'), f'deferred mapping entries changed: start {start_kinds.get("deferred")}, now {map_kinds.get("deferred")}')
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h)
    mismatch = sorted(p for p, h in stamp['generated'].items() if normalized_sha(ROOT/'src/generated/resources'/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    stamp_current = not stale and not mismatch and not unrecorded
    need(stamp_current, f'{STAMP} not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, unrecorded {unrecorded[:5]}')
    start_stamp = read(START_FILES/STAMP)
    start_generated = start_stamp['generated']
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal24d generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    advancements = sorted(p for p in generated_added if ADVANCEMENT.fullmatch(p))
    EXPECTED_GENERATED = sorted(EXPECTED_GENERATED_BASE + advancements)
    need(sorted(ADVANCEMENT.fullmatch(p).group(1) for p in advancements) == sorted(_RECIPES), 'The generated advancements are not exactly one for rbmk_console and one for rbmk_tool: '+str(advancements))
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected blockstate, model, loot table, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, the pickaxe tag, sounds.json and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # sounds.json: the only change is the block.shutdown definition (original sounds.json: one stream sound block/shutdown); every other definition equals its start value.
    sounds_start, sounds_now = read(START_FILES/(GENERATED_ROOT+SOUNDS_ENTRY)), read(ROOT/(GENERATED_ROOT+SOUNDS_ENTRY))
    sounds_delta = lang_delta(sounds_start, sounds_now)
    need(sounds_delta == dict(added=['block.shutdown'], removed=[], changed=[]), f'sounds.json delta is not exactly the block.shutdown definition: {json.dumps(sounds_delta)[:300]}')
    shutdown_sounds = (sounds_now.get('block.shutdown') or {}).get('sounds')
    need(isinstance(shutdown_sounds, list) and len(shutdown_sounds) == 1 and (shutdown_sounds[0] == {'name': 'hbmsntm:block/shutdown', 'stream': True}
                                                                             or (isinstance(shutdown_sounds[0], dict) and shutdown_sounds[0].get('name') == 'hbmsntm:block/shutdown' and shutdown_sounds[0].get('stream') is True)),
         f'sounds.json block.shutdown is not the single stream sound hbmsntm:block/shutdown (original sounds.json:7): {shutdown_sounds}')
    # Recipes: the two crafting recipes (computed from the generated JSON) against the original rows; no anvil rows exist for the console or the tool.
    o_crafting, o_tool_recipes = original_text(O_CRAFTING), original_text(O_TOOL_RECIPES)
    o_rows = {'rbmk_console': original_shaped_row(o_crafting, 'Blocks', 'rbmk_console', 1), 'rbmk_tool': original_shaped_row(o_tool_recipes, 'Items', 'rbmk_tool', 1)}
    assert all(row is not None and all(v is not None for v in row['key'].values()) for row in o_rows.values()), \
        f'An original recipe row could not be parsed or translated: {[r for r, row in o_rows.items() if row is None or None in row["key"].values()]}'
    o_anvil = original_text(O_ANVIL)
    anvil_rows = [t for t in ('rbmk_console', 'rbmk_tool') if f'ModBlocks.{t})' in o_anvil or f'ModItems.{t})' in o_anvil]
    assert not anvil_rows, 'The original now has anvil rows for the console or the tool: '+str(anvil_rows)
    crafting = {}
    for r in _RECIPES:
        recipe_path = ROOT/GENERATED_ROOT/f'data/hbmsntm/recipe/{r}.json'
        if recipe_path.is_file():
            data = read(recipe_path)
            neo_row = dict(pattern=data.get('pattern'), key=data.get('key'), result=data.get('result'))
            crafting[r] = dict(type=data.get('type'), neo=neo_row, original=jsonable(o_rows[r]))
            need(data.get('type') == 'minecraft:crafting_shaped' and row_matches(neo_row, o_rows[r]),
                 f'{recipe_path.relative_to(ROOT).as_posix()} differs from the original recipe row: {neo_row} vs {jsonable(o_rows[r])}')
        else:
            need(False, 'generated recipe missing: '+recipe_path.relative_to(ROOT).as_posix())
    # Mapped paths: every changed path inside the compare inventory must be matched by a feature group.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    need(len(new_groups) == 1, f'migration/features.json lacks the group {FEATURE_CONSOLE}')
    if len(new_groups) == 1:
        for group_entry in new_groups:
            need(group_entry.get('status') == 'partial-unverified' and group_entry.get('reviewed_source_commit') == SOURCE_HEAD,
                 f'features.json group {group_entry.get("id")} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in FEATURE_SOURCES + list(ASSETS.values()) if not any(feature_matches(g, 'source', p) for g in new_groups)]
        need(not missing_source, f'features.json group {FEATURE_CONSOLE} lists in neither source_paths nor source_watch: {missing_source[:4]} ({len(missing_source)} paths)')
        missing_target = [p for p in NEW_JAVA if not any(feature_matches(g, 'target', p) for g in new_groups)]
        need(not missing_target, f'features.json group {FEATURE_CONSOLE} lacks the new classes in target_paths/target_watch: {missing_target}')
        watch = list(ASSETS) + [GENERATED_ROOT+p for p in EXPECTED_GENERATED] + [NEW_TOOLS[0]]
        missing_watch = [p for p in watch if not any(feature_matches(g, 'target', p) for g in new_groups)]
        need(not missing_watch, f'features.json group {FEATURE_CONSOLE} lacks the resources, the generated blockstate / models / loot table / recipes or the verifier in target_watch: {missing_watch[:4]} ({len(missing_watch)} paths)')
        for group_entry in new_groups:
            absent = [p for p in group_entry.get('source_paths', []) if not (SOURCE/p).is_file()]
            need(not absent, f'features.json group {group_entry.get("id")} source_paths missing in the original: {absent}')
    need(set(by_id) == set(start_features) | {FEATURE_CONSOLE}, 'features.json group ids are not the start ids + '+FEATURE_CONSOLE+': '+str(
        sorted(set(by_id) ^ (set(start_features) | {FEATURE_CONSOLE}))))
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
        if rel in base['files']: total_start += annotations(START_FILES/rel if base['files'][rel] != sha(p) and (START_FILES/rel).is_file() else p)
    assert total_start == prior_receipt['gametest']['tests'], 'The start GameTest sources do not hold the previous count of '+str(prior_receipt['gametest']['tests'])
    gametest_added = total_now - total_start
    gametest_expected = total_now
    console_test_names = sorted(GAMETEST_METHOD.findall((ROOT/CONSOLE_TESTS).read_text(encoding='utf-8'))) if (ROOT/CONSOLE_TESTS).is_file() else []
    console_annotations = annotations(ROOT/CONSOLE_TESTS) if (ROOT/CONSOLE_TESTS).is_file() else 0
    need(bool(console_test_names) and console_annotations == len(console_test_names), f'{CONSOLE_TESTS} holds {console_annotations} @GameTest annotations and {len(console_test_names)} parsed methods')
    need(gametest_added == console_annotations, f'GameTest sources grew by {gametest_added} tests, RBMKConsoleGameTests holds {console_annotations} (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in console_test_names), 'GameTest log lacks "[hbm-rbmk-console] <name> passed" for: '+str([n for n in console_test_names if (GAMETEST_MARKER % n) not in text]))
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24e/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad))
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal24e/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal24e/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal24e/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal24e/'+name+' (written by the final chain)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start bytes, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    listed_in_diff = NEW_JAVA + [p for p in MODIFIED_JAVA + OPTIONAL_JAVA if p in changes] + [ZH_INPUT, LOCALIZATION_RECORD]
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal24e/production-vs-start.diff') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal24d final run plus the Goal24E verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert sha(REFERENCE_PREVIOUS) == prior_receipt['final_suites']['sha256'] and len(reference_suites) == prior_receipt['final_suites']['suites'], 'The goal24d final summary differs from its receipt'
    assert NEW_SUITE not in reference_suites, 'The Goal24E suite is already in the goal24d final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal24e/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        need(final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop']))
        need(len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites')
        need(set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal24d final set + the Goal24E verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE}))))
        entry = final['suites'].get(NEW_SUITE, {})
        need(entry.get('status') == 'as-expected' and entry.get('exit') == 0, NEW_SUITE+' did not pass in the final run')
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        need(not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final))
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal24e/'+VERIFY_REPORT+' (tools/migration/verify_goal24e_rbmk_console.py report)'):
        report = read(OUT/VERIFY_REPORT)
        problems = report_problems(report, [p for p in production_changed if not p.startswith(RES) or p == ZH_INPUT])
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        mutations = report.get('mutations')
        mutation_entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
        detected = summary_part.get('mutations_detected', sum(1 for e in mutation_entries if isinstance(e, dict) and e.get('detected') is True))
        total = summary_part.get('mutations_total', summary_part.get('mutations_applied', len(mutation_entries)))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=NEW_TOOLS[0],
                        tool_sha256=sha(ROOT/NEW_TOOLS[0]) if (ROOT/NEW_TOOLS[0]).is_file() else None, mutations_detected=f'{detected}/{total}', mutations_total=total)
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(re.findall(r'(?:TileEntityRBMKConsole|RBMKConsole|ItemRBMKTool|GUIRBMKConsole|RenderRBMKConsole|CraftingManager|ToolRecipes|AnvilRecipes|ClientProxy|ResourceManager)'
                                                      r'\.java:\d+(?:-\d+)?|sounds\.json:\d+', json.dumps(report, ensure_ascii=False))))
    # Compare against the snapshot of the end of 24A (original 0/0/0; target = exactly the Goal24D compare paths (which hold the 24B and 24C paths) plus this batch's compare-inventory paths).
    cmp24d = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'build/migration/goal24d/compare.json differs from the goal24d receipt'
    c24d_added = sorted(p for p in compare_paths(cmp24d['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
    c24d_modified = sorted(p for p in compare_paths(cmp24d['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
    own_target = sorted(p for p in changes if in_compare_inventory(p))
    expected_target = sorted(set(c24d_added) | set(c24d_modified) | set(own_target))
    expected_added = sorted(set(c24d_added) | {p for p in own_target if p not in base['files']})
    expected_modified = sorted(set(expected_target) - set(expected_added))
    compare = None
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal24e/'+COMPARE+' (compare against '+SNAPSHOT+'; expected original 0/0/0 and the target set: %d paths, +%d/~%d = the %d goal24b + goal24c + goal24d paths + %d of this batch)' % (
            len(expected_target), len(expected_added), len(expected_modified), len(c24d_added) + len(c24d_modified), len(own_target))):
        cmp = read(OUT/COMPARE)
        need(cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, COMPARE+' is not against the aee05a40f snapshot')
        need(cmp['current_target_state']['commit'] == start_head, COMPARE+' records another target commit than the start commit')
        counts = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(all(v == 0 for v in counts['source'].values()) and counts['target']['removed'] == 0, COMPARE+' original is not 0/0/0 or the target removes paths: '+str(counts))
        listed = sorted(p for p in compare_paths(cmp['changes']['target']['added']) | compare_paths(cmp['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
        need(listed == expected_target, COMPARE+' target set differs: extra %s, missing %s' % (sorted(set(listed) - set(expected_target))[:8], sorted(set(expected_target) - set(listed))[:8]))
        listed_added = sorted(p for p in compare_paths(cmp['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
        need(listed_added == expected_added, f'{COMPARE} target added set differs: extra {sorted(set(listed_added) - set(expected_added))[:6]}, missing {sorted(set(expected_added) - set(listed_added))[:6]}')
        need(not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], COMPARE+' reports unmapped changes: '+str(cmp['unmapped_changes']))
        need(not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], COMPARE+' reports removed features or missing files')
        states = Counter(f.get('state') for f in cmp['features'])
        need(len(cmp['features']) == len(features) and set(states) <= {'target-changed', 'no-observed-file-change'}, f'{COMPARE} feature states are {dict(states)}, expected only target-changed / no-observed-file-change over {len(features)} groups')
        for g in (FEATURE_CONSOLE,):
            need(any(f.get('id') == g and f.get('state') == 'target-changed' for f in cmp['features']), f'{COMPARE} does not report {g} as target-changed')
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts, feature_states=dict(states),
                       target_added_listed=len(listed_added), target_added_expected=len(expected_added), target_owners={p: [OWNER] for p in listed},
                       goal24d_paths=len(c24d_added) + len(c24d_modified), goal24e_paths=len(own_target))
        evidence[compare['path']] = compare['sha256']
    snapshot = None
    if (ROOT/SNAPSHOT).is_file():
        snap = read(ROOT/SNAPSHOT)
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '',
             SNAPSHOT+' is not a clean observation of the original at aee05a40f')
        # The snapshot was taken at the end of 24A: it predates the rbmk-fuel (24B), rbmk-reactor (24C), rbmk-control and rbmk-steam (24D) groups.
        need({f['id'] for f in snap['manifest']['features']} == set(start_features) - {FEATURE_FUEL, FEATURE_REACTOR, FEATURE_CONTROL, FEATURE_STEAM},
             SNAPSHOT+' does not hold the mapping groups of the end of 24A (the start ids without rbmk-fuel, rbmk-reactor, rbmk-control and rbmk-steam)')
        snapshot = dict(path=SNAPSHOT, bytes=(ROOT/SNAPSHOT).stat().st_size, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False, source_commit=snap['source']['commit'])
        assert snapshot['sha256'] == base['snapshot']['sha256'], 'The snapshot differs from the baseline'

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal24e.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal24d) package (run build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 6 resources and every compiled class equal the sources.
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [e for e, t in asset_entries.items() if e not in names or not (ROOT/t).is_file() or jar.read(e) != (ROOT/t).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json, the imported resources or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == en_delta == expected_delta and zh_jar == zh_delta == expected_delta,
                 f'JAR en_us.json or zh_cn.json delta against the previous package is not the {len(KEYS)} new keys: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
            old = {i.filename for i in prior.infolist() if not i.is_dir()}
            new = {i.filename for i in jar.infolist() if not i.is_dir()}
            jar_delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
            old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
            new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
            dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        generated_entries = set(generated_added)
        entry_owners, unowned = {}, []
        for kind, entries in jar_delta.items():
            for n in entries:
                owner = []
                if n.endswith('.class') and owner_class(n) in PRODUCTION_JAVA: owner = [OWNER]
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY, TAG_ENTRY, SOUNDS_ENTRY): owner = [OWNER]
                elif kind == 'added' and (n in asset_entries or n in generated_entries): owner = [OWNER]
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the owner-table Java sources, the 6 imported resources, the generated additions and the modified '
             'en_us.json / zh_cn.json / sounds.json / pickaxe tag are owned; META-INF/MANIFEST.MF is not): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) <= set(changed_java) and set(changed_java) - set(class_owners) <= set(NO_CLASS_JAVA) | set(SAME_CLASS_JAVA),
             'Changed Java sources and goal24e JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners) - set(NO_CLASS_JAVA) - set(SAME_CLASS_JAVA)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, TAG_ENTRY, SOUNDS_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + sounds.json + pickaxe tag + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
        for inner in ('com/hbm/blockentity/machine/rbmk/RBMKConsoleBlockEntity$RBMKColumn.class', 'com/hbm/blockentity/machine/rbmk/RBMKConsoleBlockEntity$RBMKScreen.class',
                      'com/hbm/blockentity/machine/rbmk/RBMKConsoleBlockEntity$ScreenType.class'):
            need(inner in jar_delta['added'], inner+' is not an added JAR class')
        for p in MODIFIED_JAVA:
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
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal24d_start=sorted(repinned),
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                   insert_lines=insert_summary, edit_counts=edit_summary, removed_comment_lines={p: len(v) for p, v in removed_comments.items()},
                   console_constants={k: c['neo'] == c.get('neo_expected', c['original']) for k, c in console_constants.items()},
                   screen_types_equal=screen_types['neo'] == screen_types['original'], column_types_equal=column_types['neo'] == column_types['original'],
                   client_imports_in_common_classes=sorted(p for p, v in client_imports.items() if v),
                   crafting_recipes=len(crafting), gametest=gametest_line, gametest_expected=gametest_expected,
                   gametest_added=gametest_added, new_console_tests=console_test_names, final_suites_expected=final_expected,
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
    rbmk_console = dict(neo=[CONSOLE_BLOCK, CONSOLE_BE, CONSOLE_MENU, CONSOLE_SCREEN, CONSOLE_RENDERER, TOOL_ITEM, COLUMN_TYPE_FILE], original=[p for p in O_SOURCES],
                        constants=console_constants, screen_types=screen_types, column_types=column_types, original_references=original_refs,
                        defaults=dict(scan_columns=15 * 15, scan_period_ticks=10, sync_range=50, full_sync_every_ticks=10, screens=6, flux_buffer_points=60, control_range_blocks=20,
                                      az5_client_cooldown_ms=3000, az5_level=0, multiblock_main=[3, 0, 0, 0, 2, 2], multiblock_offset=1, multiblock_second_box=[0, 0, 0, 1, 2, 2],
                                      screwdriver_rotation_steps=4, tool_attack_damage=2),
                        note='The console scans 15 x 15 = 225 RBMK columns around the linked centre at the centre\'s height every 10 ticks (TileEntityRBMKConsole :87-122, only loaded '
                             'chunks are read) and syncs within range 50: the full packet (225 column types and NBT, the 60-point neutron flux buffer and the six screen readouts) on every '
                             'tick divisible by 10, the six screen types on the others (:191-249). Six screens with the types NONE, COL_TEMP, ROD_EXTRACTION, FUEL_DEPLETION, FUEL_POISON '
                             'and FUEL_TEMP average the selected columns (:125-188). The control packet has five independent groups (:257-337): level of the selected manual rods, screen type '
                             'toggle, screen column list, colour group assignment and steam-channel compressor cycling; NEO validates the level, the indices and the slots on the server. '
                             'The console only acts for a player within 20 blocks of its core corner (hasPermission :251-254). AZ-5 in the GUI sends level 0 for every scanned manual control '
                             'rod (CONTROL columns; automatic rods are never selected) and plays block.shutdown only on the pressing client, with a 3 s cooldown (GUIRBMKConsole :219-241); '
                             'the original pressAZ5 is an OpenComputers callback and is not ported. The multiblock is {3,0,0,0,2,2} with offset 1 plus a second box {0,0,0,1,2,2} in front of '
                             'the core (RBMKConsole :101-130); the screwdriver rotates the scan in four 90 degree steps (:132-144, rotate :386-389). The linking tool stores the core of a '
                             'clicked column and links it to the console (ItemRBMKTool.onItemUse) and is a +2 attack damage weapon (ItemRBMKTool.getAttributeModifiers). Not migrated: the guide-book branch, the '
                             'OpenComputers callbacks (getColumnData, setLevel, setColumnLevel, setColorLevel, setColor, pressAZ5), the crane console and display branches of the tool '
                             '(Goal 25 / 26). NEO-only: the tooltip hit test uses the click bounds (the original hover test has the 10150 height bound and index > 0, GUIRBMKConsole :79-82, '
                             'which hide the top-left column tooltip).')
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), language_kinds, len(ASSETS), len(console_test_names), gametest_expected),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=MELTDOWN_NOTE+prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=prior_receipt['source_commit'], target_start_commit=start_head,
                   planning_commit=prior_receipt['planning_commit'],
                   goal23_closeout=closeout, uncommitted_start=dict(status_entries=START_STATUS_ENTRIES, description=base['start_content']['uncommitted'],
                                                                    base_release=previous_rel, status=[l for l in base['target_status'].splitlines() if l]),
                   commits={}, target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha,
                   base_release_receipt_sha256=previous_receipt_sha, actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha,
                                      note='The start tree is HEAD 1114adf5 (the Goal 24 planning commit on top of the pushed Goal 23 close-out commit 09173669) with the UNCOMMITTED '
                                           'Goal24A, Goal24B, Goal24C and Goal24D deliveries (754 status entries; the goal24a..goal24d packages, not committed by decision 2); no pending small fix; '
                                           'build/libs at the start is the goal24d package byte for byte. The original did not move since 24A. The freeze copied all 47 scope files to '
                                           'baseline-files, so no supplement copy was needed. Paths this batch changes record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, edited_lines=edit_summary, removed_comment_lines=removed_comments, start_copies_supplement=[],
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   rbmk_console=rbmk_console,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 changed=dict(en_us=en_delta['changed'], zh_cn_map=map_delta['changed']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys={k: v for k, v in KEYS.items() if v}, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines=dict(added=len(added_lines.get(PROVIDER, [])), removed=len(removed_lines.get(PROVIDER, []))), jar_delta=language,
                                 note=f'{EXPECTED_KINDS["upstream"]} entries are upstream (the console block name, the four rbmk_tool item texts, the rbmk.heat / rbmk.moderated / rbmk.rod.* / rbmk.screen.* '
                                      'labels of the screens and the rbmk.console.* screen type labels, English and Chinese verbatim from en_US.lang / zh_CN.lang); '
                                      f'{EXPECTED_KINDS["local"]} are NEO-local (the hard-coded English of GUIRBMKConsole: the three tooltips, the ten colour group lines and the 14 column type names, '
                                      'plus rbmk.console.assign: an adaptation of the original key whose Chinese gains the missing screen number placeholder %s, review A P2-1; the original source '
                                      'key, English and Chinese stay recorded in the map entry). '
                                      'No existing key changes its value.'),
                   recipes=dict(crafting=crafting, not_registered=['anvil rows: the original has none for rbmk_console or rbmk_tool'],
                                original_references={k: v for k, v in original_refs.items() if k.startswith(('recipe_', 'anvil_'))},
                                anvil_recipes_unchanged=sha(ROOT/ANVIL_RECIPES) == base['files'][ANVIL_RECIPES],
                                note='The two shaped recipes equal the original rows (CraftingManager rbmk_console, ToolRecipes rbmk_tool); AnvilRecipes holds no row for either, so the file stays '
                                     'unchanged.'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report, repinned_since_goal22d_start=prior_receipt['repinned_since_goal22d_start'],
                   repinned_since_goal23a_start=prior_receipt['repinned_since_goal23a_start'], repinned_since_goal23b_start=prior_receipt['repinned_since_goal23b_start'],
                   repinned_since_goal23c_start=prior_receipt['repinned_since_goal23c_start'], repinned_since_goal24a_start=prior_receipt['repinned_since_goal24a_start'],
                   repinned_since_goal24b_start=prior_receipt['repinned_since_goal24b_start'],
                   repinned_since_goal24c_start=prior_receipt['repinned_since_goal24c_start'],
                   repinned_since_goal24d_start={p: dict(goal24d_start_pin_sha256=h, goal24e_start_sha256=start_pin(base, p)) for p, h in repinned.items()},
                   snapshot=snapshot, compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_console_tests=console_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, one batch per RBMKConsoleGameTests test: the console '
                                      'multiblock, the scan of the linked reactor, the screen readouts, the server-validated control packets, AZ-5, the linking tool and the two recipes; '
                                      'no client (the console screen, the OBJ renderer, the screen text and the block.shutdown sound are not rendered or played), no real player, no '
                                      'saved world, no survival reactor build.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static verifier '
                            'with in-memory mutations, the final old-suite rerun, compare against the review-aee05a40f10f snapshot of the end of 24A, and an independent and a '
                            'redundant static review. No in-game client test was run: the console screen, the OBJ renderer, the screen text in English and Chinese, the colour buttons '
                            'and the block.shutdown sound are unverified; no survival reactor build in a world was run; no multiplayer or dedicated server beyond GameTest; '
                            'GOAL24E-ACCEPTANCE.md (the Goal 24 master checklist) is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, start_jar_sha), 'build/libs JAR is an older JAR'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal24e JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal24d package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
