"""Package Goal23C (the RT generator machine_rtg: MachineRTGBlock, MachineRTGBlockEntity with 15 pellet slots, MachineRTGMenu, MachineRTGScreen and the
OBJ renderer RenderRTG; the plain items thermo_element and rtg_unit; the assembly rows ass.thermoelement, ass.thermoelementsilicon, ass.rtgunit and ass.rtg;
the 23B leftovers: the pellet_rtg_depleted_mercury recycling recipe, the depleted pellets as separate JEI subtypes and the RTGPelletGameTests mercury/nickel
assertions; eight language keys, five imported resources and ten RTGGameTests) cumulatively on the goal23b package, without replacing any previous
delivery. The unified Goal 23 acceptance checklist (GOAL23C-ACCEPTANCE.md) is written by this batch and hashed by the receipt.

python -B -X utf8 tools/migration/package_goal23c.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only
build/migration/releases/goal23c/ (the JAR, SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal23c/gametest-final.log (the
GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes (with None for what is not produced yet in --check) so a
--check run also proves the receipt code; only the real mode writes it.

The frozen start is build/migration/goal23c/baseline.json: NEO HEAD dd69a404 (the Goal 23 planning commit on top of the Goal 22 close-out commit 670d5911)
plus the uncommitted Goal23A and Goal23B delivery paths (decision 15: Goal 23 is committed once at its close-out): the 88 goal23b changed files at the goal23b
receipt's after_sha256 and the 13 Goal23A paths the goal23b receipt left alone at the hash it recorded, except the three records the Goal 23 planning
session revised after the goal23b package (GOAL23.md decision 9 revision, GOAL23C.md, GOAL23-THREAD-PROMPTS.md), which carry their own start hashes
(baseline post_23b_planning). build/libs at the start is the goal23b package byte for byte. Every change since the start is computed from the baseline file
hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. Several Goal23A/23B paths (NtmItems, the
creative tabs, the recipe, item model and language providers, RTGPelletGameTests, zh_cn.json, the zh_cn mapping, en_us.json, the generation stamp, README,
features, UPSTREAM-REVIEWS, LOCALIZATION, GOAL23.md and GOAL23C.md) are modified again here: their before hash is the start hash, their after hash the live one.
The JAR delta against the goal23b package is attributed per entry (goal23c); any entry without exactly one owner fails. Counts that records quote (suites,
GameTests, generated resources, classes, releases, language keys, recipes) are computed here, never hard-coded; the previous package's SHA-256, size and
receipt hashes are read from the files and the baseline, not from literals.

The delivered read-only batch 23D owns exactly migration/RBMK-SCOPE.md and tools/migration/verify_goal23d_rbmk_scope.py (uncommitted since before this
start; baseline concurrent_session). They are listed in the receipt as owner goal23d-concurrent at their start hashes, never packaged, never attributed to
this batch and must not have changed.

The receipts that hash records (goal21a..goal23b and the review-g21d-hazard-fix receipt) were written before later appends to the acceptance checklists,
before the O1 record notes and (goal22c) before the thorium follow-up section of GOAL22C.md; those records already differ from their older receipt hashes at
the frozen start (baseline older_receipt_evidence_drift; the goal23b receipt records their start hash, so previous_receipt_evidence_drift is empty). They
are listed in the receipt as start drift and must still equal their Goal23C start hash; no receipt is rewritten and no other protected path may drift."""
from collections import Counter
from difflib import SequenceMatcher
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
from package_goal21d import (LOCALIZATION_RECORD, STAMP, EN, SNAPSHOT, SOURCE_HEAD, ZH_ENTRY, EN_ENTRY, lang_delta, compare_paths, lines_of,
                             eol_counts, insertions, in_compare_inventory, changed_since_start)
from package_goal22a import annotations
from package_goal22b import (git_ro, original_blob, edit_counts, stale_diff, receipt_protected, start_drift_paths,
                             AUDITS, LOGS, FILES, CHAIN_FILES, CHAIN_COMMANDS, GAMETEST, VERIFY_REPORT, FINAL_SUMMARY, COMPARE)
from package_goal22c import NAMES_RELEASE, J
from package_goal23a import original_line
from package_goal23b import (OUT as GOAL23B_OUT, BASELINE as GOAL23B_BASELINE, protected_paths as goal23b_protected_paths, report_problems, original_text)

OUT = ROOT/'build/migration/goal23c'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
STARTUP = OUT/'startup-verification.json'
REFERENCE_PREVIOUS = GOAL23B_OUT/'final/summary.json'
PREVIOUS_COMPARE = GOAL23B_OUT/'compare.json'
PREVIOUS = ROOT/'build/migration/releases/goal23b/hbmsntm-198A-goal23b.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal23c'
RELEASE_NAME = 'hbmsntm-198A-goal23c.jar'
OWNER = 'goal23c'
OWNER_23B = 'goal23b'
OWNER_23A = 'goal23a'
OWNER_PLANNING = 'goal23-planning'
OWNER_23D = 'goal23d-concurrent'
GOAL22_CLOSEOUT = '670d5911'
PLANNING_PREFIX = 'dd69a404'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
O_RES = RES+'assets/hbm/'

# Production (owner goal23c), NEW: the generator block, block entity, menu, screen, renderer and the GameTest class.
NEW_JAVA = [J+'blocks/machine/MachineRTGBlock.java', J+'blockentity/machine/MachineRTGBlockEntity.java', J+'inventory/menus/MachineRTGMenu.java',
            J+'inventory/screens/MachineRTGScreen.java', J+'render/blockentity/RenderRTG.java', J+'gametest/RTGGameTests.java']
(RTG_BLOCK, RTG_BLOCK_ENTITY, RTG_MENU, RTG_SCREEN, RTG_RENDER, RTG_TESTS) = NEW_JAVA
# Production, MODIFIED existing sources (registration points, items, tabs, assembly rows, datagen providers, JEI, the 23B pellet test).
MODIFIED_JAVA = [J+p+'.java' for p in ('blocks/NtmBlocks', 'blockentity/NtmBlockEntityTypes', 'inventory/NtmMenuTypes', 'main/NuclearTechModClient', 'main/ClientProxy',
                                       'main/ResourceManager', 'items/NtmItems', 'inventory/NtmCreativeTabs', 'inventory/recipes/AssemblyMachineRecipes',
                                       'datagen/NtmRecipeProvider', 'handler/jei/NtmJeiPlugin', 'datagen/NtmBlockLootTableProvider', 'datagen/NtmBlockTagProvider',
                                       'datagen/NtmItemModelProvider', 'datagen/NtmLanguageProvider', 'gametest/RTGPelletGameTests')]
(BLOCKS, BLOCK_ENTITY_TYPES, MENU_TYPES, CLIENT_ENTRY, CLIENT_PROXY, RESOURCE_MANAGER, ITEMS, CREATIVE_TABS, ASSEMBLY, RECIPE_PROVIDER, JEI_PLUGIN, LOOT_PROVIDER,
 TAG_PROVIDER, ITEM_MODEL_PROVIDER, PROVIDER, PELLET_TESTS) = MODIFIED_JAVA
# Insert-only against the frozen start copies. NtmRecipeProvider replaces exactly the two-line mercury comment; RTGPelletGameTests replaces the
# mercury/nickel block of rtg_pellet_recipes and the javadoc phrase (the receipt records the removed lines).
INSERT_ONLY = [p for p in MODIFIED_JAVA if p not in (RECIPE_PROVIDER, PELLET_TESTS)]
# The imported original resources: NEO path -> original path (under the original repository's src/main/resources).
ASSETS = {RES+'assets/hbmsntm/models/obj/machines/rtg.obj': O_RES+'models/machines/rtg.obj',
          RES+'assets/hbmsntm/textures/models/machines/rtg.png': O_RES+'textures/models/machines/rtg.png',
          RES+'assets/hbmsntm/textures/gui/gui_rtg.png': O_RES+'textures/gui/gui_rtg.png',
          RES+'assets/hbmsntm/textures/item/thermo_element.png': O_RES+'textures/items/thermo_element.png',
          RES+'assets/hbmsntm/textures/item/rtg_unit.png': O_RES+'textures/items/rtg_unit.png'}
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA
PRODUCTION = PRODUCTION_JAVA + list(ASSETS) + [ZH_INPUT, LOCALIZATION_RECORD]
GENERATED = [STAMP, EN]
# Generated by runData for this batch (relative to src/generated/resources): added files, and the two existing generated files that change besides the stamp.
TAG_ENTRY = 'data/minecraft/tags/block/mineable/pickaxe.json'
EXPECTED_GENERATED = sorted(['assets/hbmsntm/blockstates/machine_rtg.json', 'assets/hbmsntm/models/block/machine_rtg_particle.json',
                             'assets/hbmsntm/models/item/machine_rtg.json', 'assets/hbmsntm/models/item/thermo_element.json', 'assets/hbmsntm/models/item/rtg_unit.json',
                             'data/hbmsntm/loot_table/blocks/machine_rtg.json', 'data/hbmsntm/recipe/pellet_rtg_depleted_mercury.json',
                             'data/hbmsntm/advancement/recipes/misc/pellet_rtg_depleted_mercury.json'])
EXPECTED_MODIFIED_GENERATED = sorted([EN_ENTRY, TAG_ENTRY])
TOOLS = ['tools/migration/verify_goal23c_rtg_machine.py', 'tools/migration/package_goal23c.py']
# Hashed by the receipt (frozen afterwards): this batch's reports; any further migration/goal23c-* or GOAL23C-* record is hashed as well.
REPORTS = ['migration/GOAL23C.md', 'migration/GOAL23C-ACCEPTANCE.md', 'migration/goal23c-static-review.md', 'migration/goal23c-resource-ownership.json',
           'migration/goal23c-localization-review.json']
RESOURCE_OWNERSHIP = REPORTS[3]
BATCH_RECORD = re.compile(r'migration/(goal23c-[^/]+\.(json|md)|GOAL23C-[^/]+\.md)')
SHARED_RECORDS = ['migration/GOAL23.md', 'migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md']
# The delivered read-only batch 23D owns exactly these two paths (baseline concurrent_session); never packaged, never attributed to this batch.
CONCURRENT_23D = ['migration/RBMK-SCOPE.md', 'tools/migration/verify_goal23d_rbmk_scope.py']
# The records the Goal 23 planning session revised after the goal23b package (baseline post_23b_planning). GOAL23.md (a shared record) and GOAL23C.md (a
# report) are modified by this batch; GOAL23-THREAD-PROMPTS.md must still equal its start hash.
POST_23B_PLANNING = ['migration/GOAL23.md', 'migration/GOAL23C.md', 'migration/GOAL23-THREAD-PROMPTS.md']
# Must have changed (or been added) by the time of the real run; the generated additions are checked against EXPECTED_GENERATED.
REQUIRED_CHANGES = PRODUCTION + GENERATED + [GENERATED_ROOT+TAG_ENTRY] + TOOLS + REPORTS + SHARED_RECORDS
# The eight language keys: NEO key -> (original key, the original's source is en_US.lang / zh_CN.lang). All upstream.
KEYS = {'block.hbmsntm.machine_rtg': 'tile.machine_rtg_grey.name', 'container.rtg': 'container.rtg', 'desc.gui.rtg.heat': 'desc.gui.rtg.heat',
        'desc.gui.rtg.pellets': 'desc.gui.rtg.pellets', 'desc.gui.rtg.pelletHeat': 'desc.gui.rtg.pelletHeat', 'desc.gui.rtg.pelletPower': 'desc.gui.rtg.pelletPower',
        'item.hbmsntm.thermo_element': 'item.thermo_element.name', 'item.hbmsntm.rtg_unit': 'item.rtg_unit.name'}
EXPECTED_KEY_COUNT, EXPECTED_KINDS = len(KEYS), {'upstream': len(KEYS)}
O_LANG_EN, O_LANG_ZH = RES+'assets/hbm/lang/en_US.lang', RES+'assets/hbm/lang/zh_CN.lang'
PROVIDER_ADD_ITEM = re.compile(r'this\.add\(NtmItems\.(THERMO_ELEMENT|RTG_UNIT), "(.*)"\);$')
PROVIDER_ADD_KEY = re.compile(r'this\.add\("([\w.]+)", ')
NEW_TESTS = ['rtg_place_initial', 'rtg_generation', 'rtg_heat_cap', 'rtg_decay_in_machine', 'rtg_power_network', 'rtg_slot_rules', 'rtg_nbt_and_sync',
             'rtg_break_drops', 'rtg_assembly_rows', 'rtg_slot_semantics']
GAMETEST_METHOD = re.compile(r'@GameTest\([^)]*\)\s*public static void (\w+)\(')
GAMETEST_MARKER = '[hbm-rtg-machine] %s passed'
PELLET_TEST_MARKER = '[hbm-rtg] rtg_pellet_recipes passed'
# Indexed by the receipt as start evidence files of this batch (the Gradle logs, AUDITS and FILES come from the goal22b packager); frozen with the start.
START_EVIDENCE = ('baseline.json', 'startup-verification.json', 'freeze_start.py', 'compile-start.log', 'add_localization.py', 'import_resources.py', 'chain.sh',
                  'handoff-production.md', 'handoff-localization.md', 'handoff-gametest.md', 'handoff-verifier.md', 'handoff-packaging.md')
# Review files under OUT (for example the two independent static reviews' notes or diffs) the main agent names when it knows them; each must exist and is
# indexed by the receipt.
REVIEW_EVIDENCE = ('compile-a-1.log', 'rundata-1.log', 'compile-gt-1.log', 'gametest-gt-1.log', 'make_review_diff.py', 'review-production-1.diff',
                   'make_final_runner.py', 'make-final-runner-2.log', 'make_explained.py', 'final_explained.py', 'final-run.log', 'final-summary.log',
                   'compare.log', 'add_features.py', 'features-notes.json', 'validate-features.log', 'install_records.py', 'fill_results.py',
                   'validate-records.log', 'package-check-2.log')
GAMETEST_LOG = 'build/migration/goal23c/gametest-final.log'
NEW_SUITE = 'verify_goal23c_rtg_machine.py --gametest-log build/migration/goal23c/gametest-final.log --jar build/libs/hbmsntm-198A.jar'
FEATURE_GROUP, FEATURE_ASSEMBLY = 'rtg-power', 'basic-assembly'
RADIATION_NOTE = ('Goal23C: RTG pellets now decay inside the RT generator; handle the lead-209 (15,000 RAD/s), gold-198 and polonium-210 pellets only through '
                  'commands in separately authorized disposable worlds, never in a player\'s inventory. ')
VERIFIER_REFERENCE = re.compile(r'(?:TileEntityMachineRTG|ContainerMachineRTG|GUIMachineRTG|RenderRTGBlock|RenderRTG|MachineRTG|AssemblyMachineRecipes|ModBlocks|'
                                r'ModItems|MineralRecipes|VersatileConfig|RTGUtil)\.java:\d+(?:-\d+)?')
# The original sources (paths in the original repository).
ORIGINAL = 'src/main/java/com/hbm/'
O_TILE, O_BLOCK = ORIGINAL+'tileentity/machine/TileEntityMachineRTG.java', ORIGINAL+'blocks/machine/MachineRTG.java'
O_CONTAINER, O_GUI = ORIGINAL+'inventory/container/ContainerMachineRTG.java', ORIGINAL+'inventory/gui/GUIMachineRTG.java'
O_RENDER, O_ITEM_RENDER = ORIGINAL+'render/tileentity/RenderRTG.java', ORIGINAL+'render/block/RenderRTGBlock.java'
O_ASSEMBLY, O_RECIPES, O_MOD_ITEMS = ORIGINAL+'inventory/recipes/AssemblyMachineRecipes.java', ORIGINAL+'crafting/MineralRecipes.java', ORIGINAL+'items/ModItems.java'
O_SOURCES = [O_BLOCK, O_TILE, O_CONTAINER, O_GUI, O_RENDER, O_ITEM_RENDER]
# The original lines the receipt quotes: id -> (original path, token); the line number is looked up in the stored blob at the recorded commit.
ORIGINAL_REFS = {
    'tile_heat_max': (O_TILE, 'heatMax = VersatileConfig.rtgDecay() ? 600 : 200'),
    'tile_power_max': (O_TILE, 'powerMax = 100000'),
    'tile_slots': (O_TILE, 'super(15)'),
    'tile_heat_times_five': (O_TILE, 'power += heat * 5'),
    'tile_update_rtgs': (O_TILE, 'heat = RTGUtil.updateRTGs(slots, slot_io)'),
    'tile_network_pack': (O_TILE, 'networkPackNT(50)'),
    'tile_nbt_power': (O_TILE, 'nbt.setLong("power", power)'),
    'tile_nbt_heat': (O_TILE, 'nbt.setInteger("heat", heat)'),
    'recycle_mercury': (O_RECIPES, 'DepletedRTGMaterial.MERCURY.ordinal()) });'),
    'ingot_mercury': (O_MOD_ITEMS, 'ingot_mercury = new ItemCustomLore().setUnlocalizedName("nugget_mercury")'),
    'ass.thermoelement': (O_ASSEMBLY, 'new GenericRecipe("ass.thermoelement")'),
    'ass.thermoelementsilicon': (O_ASSEMBLY, 'new GenericRecipe("ass.thermoelementsilicon")'),
    'ass.rtgunit': (O_ASSEMBLY, 'new GenericRecipe("ass.rtgunit")'),
    'ass.rtg': (O_ASSEMBLY, 'new GenericRecipe("ass.rtg")'),
}
ASSEMBLY_IDS = ['ass.thermoelement', 'ass.thermoelementsilicon', 'ass.rtgunit', 'ass.rtg']
# The original ingredient expressions -> the NEO ingredient (the translation table the verifier applies as well).
ASSEMBLY_TRANSLATION = {'STEEL.plate()': ('tag', 'NtmTags.Items.PLATES_STEEL'), 'CU.plate()': ('tag', 'NtmTags.Items.PLATES_COPPER'),
                        'ANY_PLASTIC.ingot()': ('tag', 'ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic"))'),
                        'PB.plateCast()': ('cast', 'LEAD'), 'MINGRADE.wireFine()': ('item', 'WIRE_RED_COPPER'), 'GOLD.wireFine()': ('item', 'WIRE_GOLD'),
                        'NETHERQUARTZ.dust()': ('item', 'POWDER_QUARTZ'), 'SI.billet()': ('item', 'BILLET_SILICON')}
O_RECYCLE_ROW = re.compile(r'addShapelessRecipe\(new ItemStack\(ModItems\.(\w+), (\d+)\), new Object\[\] \{ new ItemStack\(ModItems\.pellet_rtg_depleted, 1, '
                           r'DepletedRTGMaterial\.(\w+)\.ordinal\(\)\) \}\)')
MERCURY_RECIPE = 'pellet_rtg_depleted_mercury'
MERCURY_META = 1  # DepletedRTGMaterial order BISMUTH, MERCURY, NEPTUNIUM, LEAD, ZIRCONIUM, NICKEL (RTGPelletDepletedItem, fixed by Goal 23 decision 9)


def scope_text(key_count, kinds, assets, new_tests, total_tests):
    return (f'Goal23C (the RT generator machine_rtg and its parts): MachineRTGBlock / MachineRTGBlockEntity (15 pellet slots, one pellet per slot; the heat is what '
            f'RTGUtil.updateRTGs returns for the pellets, capped at 600, or 200 with doRTGsDecay off, read at run time; power += heat x 5 up to 100,000 HE after '
            f'the generator offered its power to the six neighbours; GUI slots accept only RTG pellets (a NEO-only tightening), hoppers neither insert nor extract; '
            f'NBT power (long) and heat (int); power and heat synced in the block entity packet), MachineRTGMenu, MachineRTGScreen (gui_rtg.png, the heat and power '
            f'bars and the pellet list tooltip), RenderRTG (rtg.obj part Gen plus four horizontal Connector parts next to connectable neighbours); registered in '
            f'NtmBlocks, NtmBlockEntityTypes, NtmMenuTypes, NuclearTechModClient, ClientProxy, ResourceManager and the MACHINE creative tab, with loot, mineable tag '
            f'and blockstate datagen; the plain items thermo_element (CONTROL tab) and rtg_unit (PARTS tab) with imported textures; the assembly rows '
            f'ass.thermoelement, ass.thermoelementsilicon, ass.rtgunit and ass.rtg; the 23B leftovers (the recycling recipe pellet_rtg_depleted_mercury for 2 '
            f'nugget_mercury, the depleted pellets as separate JEI subtypes, the RTGPelletGameTests mercury and nickel assertions); {key_count} language keys '
            f'({kinds.get("upstream", 0)} upstream with the original Chinese); {assets} imported resources (rtg.obj, rtg.png, gui_rtg.png, thermo_element.png, '
            f'rtg_unit.png); {new_tests} RTGGameTests are added ({total_tests} GameTests in total). Gameplay impact: RTG pellets now decay inside the generator '
            f'(the lead-209 pellet lasts 21,600 ticks, about 18 minutes, then becomes the depleted bismuth pellet); the generator gives 750 HE/t with fifteen '
            f'Pu-238 pellets; the pellets keep their 23B hazards while carried (a pellet inside the generator does not irradiate players).')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal23c release directory: '+rel


def protected_paths(base):
    """What the goal23b packager protected (built there from the Goal21A..Goal23A starts and receipts, the goal23a receipt and the goal23b start), plus every
    path the goal23b receipt hashes (base previous_receipt_protected_paths), the paths the older receipts hash (the 23C baseline lists the goal23a receipt
    among them) and every release file of the frozen start (the goal23b package included). The records that already drifted (the acceptance checklists,
    GOAL21D.md, GOAL22C.md, goal21d-static-review.md) are pinned at their Goal23C start hash (baseline files) instead of any receipt hash or any earlier start
    hash. One path never carries two hashes. Returns (protected, repinned) where repinned maps a record to the pin the goal23b packager set at its Goal23B
    start hash, for the records that changed between the two starts (expected none)."""
    goal23b_start = read(GOAL23B_BASELINE)
    out = dict(goal23b_protected_paths(goal23b_start)[0])
    drift = start_drift_paths(base)
    for p in drift: assert p in base['files'], 'Start drift path is not a frozen file: '+p
    sources = [*base['older_receipt_protected_paths'].values(), base['previous_receipt_protected_paths'], base['old_release_files']]
    for source in sources:
        for p, h in source.items():
            if p not in drift: assert out.setdefault(p, h) == h, 'Two different protected hashes for '+p
    repinned = {}
    for p in drift:
        earlier = out.pop(p, goal23b_start['files'].get(p))
        if earlier is not None and earlier != base['files'][p]: repinned[p] = earlier
        out[p] = base['files'][p]
    assert all(p.endswith('-ACCEPTANCE.md') for p in repinned), 'A non-checklist pin changed between the Goal23B and Goal23C starts: '+str(sorted(repinned))
    return out, repinned


def start_drift_report(base, repinned, goal23b_start):
    """{path: {receipts, start_sha256, goal23b_start_sha256, current_sha256, explanation}} for the records that differ from an older receipt's hash at the start."""
    out = {}
    for p in start_drift_paths(base):
        receipts = {k+' receipt': v[p] for k, v in base['older_receipt_protected_paths'].items() if p in v}
        if p in base['previous_receipt_protected_paths']: receipts['goal23b receipt'] = base['previous_receipt_protected_paths'][p]
        start = base['files'][p]
        newest = receipts.get('goal23b receipt')
        if newest is None:
            explanation = ('Appended to after its older receipt(s) were written (Goal 21 and Goal 22 in-game acceptance result lines, the O1 record notes or the '
                           'thorium follow-up section); the goal23b receipt does not hash it. Frozen at the Goal23C start hash; this batch must not change it and '
                           'no earlier receipt is rewritten.')
        elif newest == start:
            explanation = ('Appended to after its older receipt(s) were written; the newest receipt that hashes it (goal23b) records the start hash. Frozen at '
                           'the start hash; this batch must not change it and no earlier receipt is rewritten.')
        else:
            explanation = ('Changed after the goal23b package; the goal23b receipt hash is older than the start hash. Frozen at the start hash; this batch '
                           'must not change it and the goal23b receipt is not rewritten.')
        entry = dict(receipt_hashes=receipts, start_sha256=start, goal23b_start_sha256=goal23b_start['files'].get(p), current_sha256=sha(ROOT/p), explanation=explanation)
        if p in repinned:
            entry['repinned_from_goal23b_start_pin_sha256'] = repinned[p]
        out[p] = entry
    return out


def group(p):
    if p in NEW_JAVA: return 'production-new'
    if p in MODIFIED_JAVA: return 'production'
    if p in ASSETS: return 'production-resource'
    if p == ZH_INPUT: return 'production-chinese'
    if p == LOCALIZATION_RECORD: return 'production-localization-record'
    if p.startswith(GENERATED_ROOT): return 'generated'
    if p in TOOLS: return 'tools'
    if p in REPORTS or BATCH_RECORD.fullmatch(p): return 'reports'
    if p in SHARED_RECORDS: return 'records'
    return None


def provider_keys(lines):
    """The language keys the given NtmLanguageProvider lines add (the two items through NtmItems constants, plain keys), and the lines that add none."""
    keys, other = [], []
    for raw in lines:
        line = raw.strip()
        m = PROVIDER_ADD_ITEM.match(line)
        if m:
            keys.append('item.hbmsntm.'+m.group(1).lower())
            continue
        m = PROVIDER_ADD_KEY.match(line)
        if m: keys.append(m.group(1)); continue
        other.append(line)
    return keys, other


def replaced_lines(old, new, ranges):
    """(removed start lines, inserted [(index, line)]) when `new` is `old` with only lines inside the given [lo, hi) index ranges of `old` removed and lines
    inserted anywhere; otherwise (None, why)."""
    removed = Counter(old) - Counter(new)
    allowed = Counter(l for lo, hi in ranges for l in old[lo:hi])
    extra = removed - allowed
    if extra: return None, f'removes {sum(extra.values())} start lines outside the allowed block (first: {sorted(extra)[0].strip()[:80]!r})'
    left, drop = Counter(removed), set()
    for i in [i for lo, hi in ranges for i in range(lo, hi)]:
        if left[old[i]] > 0:
            drop.add(i)
            left[old[i]] -= 1
    rest = [l for i, l in enumerate(old) if i not in drop]
    inserted = insertions(rest, new)
    if inserted is None: return None, 'another start line was changed or moved'
    return [old[i] for i in sorted(drop)], inserted


def line_index(lines, token, after=0):
    return next((i for i in range(after, len(lines)) if token in lines[i]), None)


def split_args(text):
    """Top-level comma split of a Java argument list."""
    out, depth, cur = [], 0, ''
    for ch in text:
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
            continue
        if ch in '([{': depth += 1
        elif ch in ')]}': depth -= 1
        cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def recipe_row(text, rid, neo):
    """{setup, output [name, count], inputs [[kind, name, count]], has_ex, count} of `new GenericRecipe("rid")` in NEO (neo=True) or the original source, or None."""
    text = text.replace('\r\n', '\n')
    found = re.findall(r'new GenericRecipe\("%s"\)(.*?);[ \t]*\n' % re.escape(rid), text, re.S)
    if not found: return None
    stmt = found[0]
    setup = re.search(r'\.setup\((\d+), (\d+)\)', stmt)
    out = re.search(r'\.outputItems\(new ItemStack\(([^,]+?), (\d+)\)\)', stmt)
    start = stmt.find('.inputItems(')
    if not (setup and out) or start < 0: return None
    begin, depth, end = start+len('.inputItems'), 0, None
    for i in range(begin, len(stmt)):
        if stmt[i] == '(': depth += 1
        elif stmt[i] == ')':
            depth -= 1
            if depth == 0: end = i; break
    if end is None: return None
    inputs = []
    for arg in split_args(stmt[begin+1:end]):
        if neo:
            m = (re.match(r'^new RecipesCommon\.TagStack\((.+), (\d+)\)$', arg), re.match(r'^new ComparableStack\(NtmItems\.(\w+)\.get\(\), (\d+)\)$', arg),
                 re.match(r'^NtmItems\.castPlateIngredient\(CastPlateItem\.Type\.(\w+), (\d+)\)$', arg))
            if m[0]: inputs.append(['tag', m[0].group(1), int(m[0].group(2))])
            elif m[1]: inputs.append(['item', m[1].group(1), int(m[1].group(2))])
            elif m[2]: inputs.append(['cast', m[2].group(1), int(m[2].group(2))])
            else: inputs.append(['?', arg, 0])
        else:
            m = (re.match(r'^new OreDictStack\((.+), (\d+)\)$', arg), re.match(r'^new ComparableStack\(ModItems\.(\w+), (\d+)\)$', arg))
            if m[0] and m[0].group(1) in ASSEMBLY_TRANSLATION: inputs.append([*ASSEMBLY_TRANSLATION[m[0].group(1)], int(m[0].group(2))])
            elif m[1]: inputs.append(['item', m[1].group(1).upper(), int(m[1].group(2))])
            else: inputs.append(['?', arg, 0])
    name = out.group(1)
    name = re.sub(r'^(?:NtmItems|NtmBlocks)\.(\w+)\.get\(\)$', r'\1', name) if neo else re.sub(r'^Mod(?:Items|Blocks)\.(\w+)$', lambda m: m.group(1).upper(), name)
    return dict(setup=[int(setup.group(1)), int(setup.group(2))], output=[name, int(out.group(2))], inputs=inputs, has_ex='.inputItemsEx(' in stmt, count=len(found))


def lang_file(path):
    """key -> value of an original .lang file at the recorded commit (the first of a duplicated key wins, as the original loader keeps the last; both are reported by the verifier)."""
    out = {}
    for line in original_blob(path).decode('utf-8').replace('\r\n', '\n').split('\n'):
        if '=' in line and not line.startswith('#'):
            k, _, v = line.partition('=')
            out[k.strip()] = v
    return out


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
    goal23b_start = read(GOAL23B_BASELINE)

    # 1. Heads: the clean original at 6a11998d, NEO still at the start commit (Goal23C commits nothing), the recorded start: HEAD plus the Goal23A/23B paths.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'Unexpected frozen start: the original was not clean at 6a11998d'
    assert start_head.startswith(PLANNING_PREFIX) and start_head == prior_receipt['target_start_commit'] == prior_receipt['target_head_at_packaging'] \
        == prior_receipt['planning_commit']['id'], 'The frozen start is not the Goal 23 planning commit the goal23b receipt records'
    assert base['pending_small_fixes'] == [], 'The frozen start has a pending small fix'
    concurrent = base['concurrent_session']
    assert concurrent['owned_paths'] == CONCURRENT_23D and concurrent['start_hashes'] == prior_receipt['concurrent_23d']['files'], \
        'The frozen start does not record the delivered 23D batch as the goal23b receipt does'
    assert set(base['start_content']) == {'committed', 'uncommitted'}, 'Baseline start content differs'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal23C: '+head
    assert git_ro(ROOT, 'rev-parse', 'HEAD~1').strip().startswith(GOAL22_CLOSEOUT), 'NEO HEAD~1 is not the Goal 22 close-out commit'
    assert set(base['older_receipt_protected_paths']) == {'goal21a', 'goal21b', 'goal21c', 'goal21d', 'review-g21d-hazard-fix-20261017', 'goal22a', 'goal22b',
                                                          'goal22c', 'goal22d', 'goal23a'}, 'Baseline older receipts differ'
    for n in base['copied_scope']:
        assert sha(START_FILES/n) == base['files'][n], 'Frozen start copy differs from the baseline hash: '+n
    startup = read(STARTUP)
    assert startup['dirty_paths'] == len(base['dirty_paths']) and startup['frozen_file_hashes'] == len(base['files']) \
        and startup['copied_scope'] == len(base['copied_scope']) and startup['old_release_files'] == len(base['old_release_files']) \
        and startup['previous_jar_sha256'] == base['previous_release']['sha256'] and startup['build_libs_jar_sha256'] == base['build_libs_jar_sha256'] \
        and startup['previous_receipt_protected_paths'] == len(base['previous_receipt_protected_paths']) \
        and startup['goal23b_paths_equal_receipt'] == len(base['goal23b_paths']) and startup['goal23a_kept_paths_equal_receipt'] == len(base['goal23a_kept_paths']), \
        'startup-verification.json differs from baseline.json'
    assert base['stamp_state']['stale_inputs'] == [] and base['stamp_state']['generated_resources_verified'] == prior_receipt['generated_resource_count'], \
        'The start generation stamp was not current or does not hold the goal23b generated tree'
    # The start tree is HEAD plus the goal23a and goal23b deliveries, uncommitted: the dirty paths are exactly the goal23b changed files, the 13 goal23a paths 23B
    # left alone, the two 23D paths and the planning records the planning session revised.
    goal23b_paths, goal23a_kept = list(base['goal23b_paths']), list(base['goal23a_kept_paths'])
    planning = base['post_23b_planning']['paths']
    assert sorted(planning) == sorted(POST_23B_PLANNING), 'Baseline post_23b_planning lists other records: '+str(sorted(planning))
    assert sorted(goal23b_paths) == sorted(c['path'] for c in prior_receipt['changed_files']), 'The start goal23b paths are not the goal23b receipt changed files'
    assert sorted(goal23a_kept) == sorted(prior_receipt['goal23a_paths_unchanged']), 'The start goal23a kept paths are not the goal23b receipt list'
    assert sorted(base['dirty_paths']) == sorted(set(goal23b_paths) | set(goal23a_kept) | set(CONCURRENT_23D) | set(planning)), \
        'The start dirty paths are not goal23b + goal23a kept + 23D + the planning records'
    receipt_after = {c['path']: c['after_sha256'] for c in prior_receipt['changed_files']}
    for p in goal23b_paths:
        if p in planning:
            assert base['files'][p] == planning[p]['start'] and planning[p]['goal23b_receipt'] == receipt_after[p], 'Planning record start/receipt hash differs: '+p
        else:
            assert base['files'][p] == receipt_after[p], 'The start copy of a goal23b path differs from the receipt after hash: '+p
    for p, h in prior_receipt['goal23a_paths_unchanged'].items(): assert base['files'][p] == h, 'The start copy of a goal23a path differs from the goal23b receipt: '+p
    for p in planning:
        assert base['files'][p] == planning[p]['start'], 'Planning record start hash differs from baseline files: '+p
    # build/libs at the start is the goal23b package byte for byte.
    start_jar_sha = base['build_libs_jar_sha256']

    # 2. Previous deliveries: the goal23b package, every old release file and the protected evidence.
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
    assert old_releases == {**prior_receipt['old_releases'], previous_rel: previous_sha}, 'Preserved releases are not the goal23b receipt list + the goal23b package'
    assert len(base['old_release_files']) == prior_receipt['preserved_release_files'] + len(list(PREVIOUS.parent.iterdir())), \
        'Preserved release files are not the goal23b receipt count + the goal23b release directory'
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    assert base['previous_receipt_protected_paths'] == receipt_protected(prior_receipt), 'Baseline previous_receipt_protected_paths differs from the goal23b receipt'
    assert base['previous_receipt_evidence_drift'] == [], 'The goal23b receipt evidence had already drifted at the start: '+str(base['previous_receipt_evidence_drift'])
    protected, repinned = protected_paths(base)
    drift_report = start_drift_report(base, repinned, goal23b_start)
    assert all(d['current_sha256'] == d['start_sha256'] for d in drift_report.values()), 'A start-drift record changed since the start: '+str(
        sorted(p for p, d in drift_report.items() if d['current_sha256'] != d['start_sha256']))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    explained, unexplained = split_drift(display_protected_drift())
    assert not unexplained, 'Older receipt evidence drifted: '+str(unexplained)
    assert sorted(explained) == prior_receipt['older_checklist_drift_explained'], 'The older checklist drift list differs from the goal23b receipt: '+str(sorted(explained))

    # 3. Changes since the start: each path in the owner table, attributed to goal23c. Everything else equals its start hash. The 23D paths are listed apart.
    changes = changed_since_start(base)
    concurrent_23d = {}
    for p in CONCURRENT_23D:
        assert p in base['files'] and base['files'][p] == concurrent['start_hashes'][p] and p not in protected, 'A 23D path is not a frozen start file: '+p
        concurrent_23d[p] = sha(ROOT/p) if (ROOT/p).is_file() else None
        need(concurrent_23d[p] == base['files'][p], f'{p} (owner {OWNER_23D}, never packaged) differs from its start hash: it was changed or deleted')
        changes.pop(p, None)
    unassigned = sorted(p for p in changes if group(p) is None)
    need(not unassigned, 'Path changed since the Goal23C start that the owner table does not list (production outside the 22 Java files, the 5 resources, zh_cn.json '
         'and the mapping, a protected record, migration/GOAL23-THREAD-PROMPTS.md, an unknown file): '+str(unassigned))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal23C start: '+str(deleted)
    for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD] + GENERATED + SHARED_RECORDS + REPORTS[:1]: assert p in base['files'], 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + list(ASSETS) + TOOLS + REPORTS[1:]: assert p not in base['files'], 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    outside = sorted(set(since) - {p for p in PRODUCTION if p.startswith('src/')})
    need(not outside, 'src/main change outside the 22 Java files, the 5 resources and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in base['files']: assert base['files'].get(p) == sha(ROOT/p), 'Build file changed: '+p

    def start_owner(p):
        if p in goal23b_paths: return OWNER_23B
        if p in goal23a_kept: return OWNER_23A
        if p in planning: return OWNER_PLANNING
        return None
    change_list = [dict(path=p, change=s, group=group(p), owner=OWNER, before_sha256=base['files'].get(p), after_sha256=sha(ROOT/p),
                        **({'start_owner': start_owner(p)} if start_owner(p) else {})) for p, s in sorted(changes.items())]
    # The goal23b paths and the goal23a kept paths this batch does not modify still equal the start hash (the goal23b receipt after hash, or the goal23a hash it
    # recorded); the planning records keep their own start hash.
    goal23b_unchanged = sorted(p for p in goal23b_paths if p not in changes)
    for p in goal23b_unchanged: assert sha(ROOT/p) == base['files'][p], 'A goal23b path changed without being in the change list: '+p
    goal23a_unchanged = sorted(p for p in goal23a_kept if p not in changes)
    for p in goal23a_unchanged: assert sha(ROOT/p) == prior_receipt['goal23a_paths_unchanged'][p], 'A goal23a path changed without being in the change list: '+p
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    assert baselines_now == {p: h for p, h in base['files'].items() if p.startswith('migration/baselines/')}, 'A snapshot was added or changed'
    assert sha(ROOT/SNAPSHOT) == base['snapshot']['sha256'], 'review-6a11998d5852 snapshot changed'
    production_changed = [p for p in PRODUCTION if p in changes]

    # The modified production files keep their start line endings (the frozen start copies are the baseline files); new Java files are not mixed.
    start_text = {}
    for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]:
        if p not in changes: continue
        if not need(p in base['copied_scope'], p+' has no frozen start copy in baseline-files (not in copied_scope)'): continue
        start_text[p] = (START_FILES/p).read_bytes()
        start_eol, eol = eol_counts(start_text[p]), eol_counts((ROOT/p).read_bytes())
        need((start_eol[0] == 0) <= (eol[0] == 0) and (start_eol[1] == 0) <= (eol[1] == 0), f'{p} line endings differ from the start: start CRLF/LF {start_eol}, now {eol}')
    for p in NEW_JAVA:
        if (ROOT/p).is_file():
            eol = eol_counts((ROOT/p).read_bytes())
            need(eol[0] == 0 or eol[1] == 0, f'{p} mixes CRLF and LF line endings: {eol}')

    # Production Java facts: insert-only registration files, the mercury comment replacement, the RTGPelletGameTests block replacement, every line edit counted.
    insert_summary, edit_summary, replaced_summary, inserted_lines = {}, {}, {}, {}
    for p in MODIFIED_JAVA:
        if p not in start_text: continue
        start_lines, live_lines = lines_of(start_text[p]), lines_of((ROOT/p).read_bytes())
        edit_summary[p] = edit_counts(start_lines, live_lines)
        if p in INSERT_ONLY:
            inserted = insertions(start_lines, live_lines)
            if not need(inserted is not None, f'{p} is not insert-only against the start copy (a start line was changed, moved or removed)'): continue
            insert_summary[p] = len(inserted)
            inserted_lines[p] = [l for _, l in inserted]
            need(edit_summary[p]['removed'] == 0, f'{p} removes {edit_summary[p]["removed"]} start lines (insert-only expected)')
        elif p == RECIPE_PROVIDER:
            first = line_index(start_lines, '// :219, mercury -> 2 ingot_mercury, is not registered')
            if not need(first is not None and 'nugget_mercury' in start_lines[first+1], f'{p} start copy has no two-line mercury comment to replace'): continue
            removed, inserted = replaced_lines(start_lines, live_lines, [(first, first+2)])
            if not need(removed is not None, f'{p} is not the start copy with the two-line mercury comment replaced and lines inserted: {inserted}'): continue
            need(len(removed) == 2, f'{p} removes {len(removed)} start lines, expected exactly the two-line mercury comment')
            replaced_summary[p] = dict(removed_lines=[l.strip() for l in removed], removed=len(removed), inserted_lines=len(inserted))
            inserted_lines[p] = [l for _, l in inserted]
            need(any('DepletedRTGMaterial.MERCURY' in l and 'NUGGET_MERCURY' in l and 'addRTGRecyclingRecipe' in l for l in inserted_lines[p]),
                 f'{p} does not register DepletedRTGMaterial.MERCURY -> NUGGET_MERCURY through addRTGRecyclingRecipe')
        elif p == PELLET_TESTS:
            first = line_index(start_lines, '// The original has no recycling recipe for the mercury and nickel pellets.')
            last = line_index(start_lines, 'check(found.isEmpty(), "the depleted "', first or 0) if first is not None else None
            javadoc = line_index(start_lines, 'the four recycling recipes')
            # The class javadoc also states that no machine is tested here (the RT generator was Goal23C); that two-line sentence is rewritten.
            machine_doc = line_index(start_lines, 'There is no machine here: the RT generator and the betavoltaic generator')
            if not need(None not in (first, last, javadoc, machine_doc), f'{p} start copy lacks the mercury/nickel block of rtg_pellet_recipes or one of the two javadoc phrases'): continue
            removed, inserted = replaced_lines(start_lines, live_lines, [(first, last+2), (javadoc, javadoc+1), (machine_doc, machine_doc+2)])
            if not need(removed is not None, f'{p} changed more than the mercury/nickel block of rtg_pellet_recipes and the two javadoc phrases: {inserted}'): continue
            replaced_summary[p] = dict(removed=len(removed), inserted_lines=len(inserted), block_start_lines=[first+1, last+2], javadoc_lines=[javadoc+1, machine_doc+1, machine_doc+2])
            inserted_lines[p] = [l for _, l in inserted]
    # Language provider: the inserted lines add exactly the batch keys (the two items through NtmItems constants), the rest are comments.
    provider_added = []
    if PROVIDER in inserted_lines:
        provider_added, provider_other = provider_keys(inserted_lines[PROVIDER])
        stray = [l for l in provider_other if l and not l.startswith('//') and not l.startswith('import ')]
        need(not stray, f'{PROVIDER} inserts lines that are neither language entries, comments nor an import: {stray[:3]}')
        need(len(provider_added) == len(set(provider_added)), f'{PROVIDER} adds a language key twice')
    # The JEI plugin adds the depleted pellet to ignoreMeta exactly once.
    if JEI_PLUGIN in inserted_lines:
        need(sum('NtmItems.PELLET_RTG_DEPLETED.get()' in l for l in inserted_lines[JEI_PLUGIN]) == 1, f'{JEI_PLUGIN} does not add NtmItems.PELLET_RTG_DEPLETED.get() exactly once')
    # RTGPelletGameTests: same GameTest methods and annotation count as the start.
    if PELLET_TESTS in start_text and (ROOT/PELLET_TESTS).is_file():
        names_now = set(GAMETEST_METHOD.findall((ROOT/PELLET_TESTS).read_text(encoding='utf-8')))
        names_start = set(GAMETEST_METHOD.findall((START_FILES/PELLET_TESTS).read_text(encoding='utf-8')))
        need(names_now == names_start, f'{PELLET_TESTS} changed its GameTest methods: added {sorted(names_now - names_start)}, lost {sorted(names_start - names_now)}')
        need(annotations(ROOT/PELLET_TESTS) == annotations(START_FILES/PELLET_TESTS), f'{PELLET_TESTS} changed its @GameTest annotation count')
    # The original, parsed from the stored blobs at the recorded commit (independent of the worktree's line endings).
    original_refs = {rid: f'{path}:{original_line(path, token)}' for rid, (path, token) in ORIGINAL_REFS.items()}
    for p in O_SOURCES: assert (SOURCE/p).is_file(), 'Original source missing: '+p
    tile = original_text(O_TILE)
    original_machine = dict(
        heat_max=[int(x) for x in re.search(r'heatMax = VersatileConfig\.rtgDecay\(\) \? (\d+) : (\d+);', tile).groups()],
        power_max=int(re.search(r'powerMax = (\d+);', tile).group(1)), slots=int(re.search(r'super\((\d+)\);', tile).group(1)),
        heat_factor=int(re.search(r'power \+= heat \* (\d+);', tile).group(1)),
        nbt=[re.search(r'nbt\.setLong\("(\w+)", power\)', tile).group(1), re.search(r'nbt\.setInteger\("(\w+)", heat\)', tile).group(1)])
    assert original_machine == dict(heat_max=[600, 200], power_max=100000, slots=15, heat_factor=5, nbt=['power', 'heat']), 'The original TileEntityMachineRTG differs: '+str(original_machine)
    # NEO block entity constants against the original.
    machine = None
    if (ROOT/RTG_BLOCK_ENTITY).is_file():
        text = (ROOT/RTG_BLOCK_ENTITY).read_text(encoding='utf-8').replace('\r\n', '\n')
        parsed = dict(
            max_power=int(m.group(1).replace('_', '')) if (m := re.search(r'MAX_POWER = ([\d_]+)L;', text)) else None,
            heat_max=[int(x) for x in m.groups()] if (m := re.search(r'RTGUtil\.rtgDecay\(\) \? (\d+) : (\d+);', text)) else None,
            heat_factor=int(m.group(1)) if (m := re.search(r'this\.heat \* (\d+)L?;', text)) else None,
            slots=int(m.group(1)) if (m := re.search(r'MACHINE_RTG\.get\(\), pos, state, (\d+)\)', text)) else None,
            max_stack=int(m.group(1)) if (m := re.search(r'getMaxStackSize\(\) \{\s*return (\d+);', text)) else None,
            nbt=[m.group(1) if (m := re.search(r'tag\.putLong\("(\w+)", this\.power\)', text)) else None, m.group(1) if (m := re.search(r'tag\.putInt\("(\w+)", this\.heat\)', text)) else None])
        need(parsed['max_power'] == original_machine['power_max'] and parsed['heat_max'] == original_machine['heat_max'] and parsed['heat_factor'] == original_machine['heat_factor']
             and parsed['slots'] == original_machine['slots'] and parsed['nbt'] == original_machine['nbt'] and parsed['max_stack'] == 1,
             f'{RTG_BLOCK_ENTITY} constants differ from the original TileEntityMachineRTG or the one-pellet-per-slot rule: {parsed} vs {original_machine}')
        machine = dict(neo=RTG_BLOCK_ENTITY, original=O_TILE, constants=parsed, original_constants=original_machine,
                       original_references={k: v for k, v in original_refs.items() if k.startswith('tile_')},
                       note='MAX_POWER 100,000; heat capped at 600 (200 with doRTGsDecay off, read at run time); power += heat x 5; 15 slots, one pellet per slot; NBT '
                            'power (long) and heat (int); power and heat synced in the block entity packet (the original synced only power and sent heat through the container).')
    # Imported resources: byte for byte equal to the original worktree file and, up to line endings (OBJ) or exactly (PNG), its stored blob, and to the ownership record.
    imported = {}
    ownership = None
    if need((ROOT/RESOURCE_OWNERSHIP).is_file(), 'record missing: '+RESOURCE_OWNERSHIP):
        ownership = read(ROOT/RESOURCE_OWNERSHIP)
        entries = {a.get('target_path'): a for a in ownership.get('assets', [])}
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(ASSETS), f'{RESOURCE_OWNERSHIP} does not list the {len(ASSETS)} resources at {SOURCE_HEAD[:8]}')
    for target, original in ASSETS.items():
        if not (ROOT/target).is_file(): continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        entry = {a.get('target_path'): a for a in (ownership or {}).get('assets', [])}.get(target, {})
        imported[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size,
                                original_worktree_sha256=sha(SOURCE/original), original_blob_sha256=hashlib.sha256(blob).hexdigest(), original_blob_bytes=len(blob),
                                line_endings_converted_from_blob=blob != checked_out, source_last_change_commit=entry.get('source_last_change_commit'))
        need((ROOT/target).read_bytes() == checked_out, f'{target} is not byte-identical to the original worktree file {original}')
        if target.endswith('.obj'):
            # The original worktree is clean at SOURCE_HEAD, so its OBJ is the checked-out original; on this Windows checkout it carries CRLF where the stored blob
            # has LF (autocrlf), which earlier batches imported as the worktree bytes. The blob must match up to that line-ending conversion.
            need(blob.replace(b'\r\n', b'\n') == (ROOT/target).read_bytes().replace(b'\r\n', b'\n'), f'{target} differs from the {SOURCE_HEAD[:8]} blob of {original} beyond line endings')
        else:
            need(checked_out == blob, f'{target} is not byte-identical to the stored blob of {original} at {SOURCE_HEAD[:8]}')
        if entry:
            need(entry.get('source_path') == original and entry.get('sha256') == sha(ROOT/target) and entry.get('bytes') == (ROOT/target).stat().st_size,
                 f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original path: {target}')
    # features.json: the rtg-power group (mapped paths) and the basic-assembly notes.
    features_data = read(ROOT/'migration/features.json')
    features = features_data['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in read(START_FILES/'migration/features.json')['features']}

    # 4. Language and the generated tree: the provider's keys in the generated English, the Chinese file and the mapping; the stamp must be current.
    en_start, en_now = read(START_FILES/EN), read(ROOT/EN)
    zh_start, zh_now = read(START_FILES/ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = read(START_FILES/LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    keys = sorted(provider_added)
    need(keys == sorted(KEYS), f'{PROVIDER} adds the language keys {keys}, expected {sorted(KEYS)}')
    expected_delta = dict(added=sorted(KEYS), removed=[], changed=[])
    need(en_delta == expected_delta, 'generated en_us.json delta is not the eight keys (all old keys unchanged): '+json.dumps(en_delta, ensure_ascii=False)[:600])
    need(zh_delta == expected_delta, 'zh_cn.json delta is not the eight keys: '+json.dumps(zh_delta, ensure_ascii=False)[:600])
    need(map_delta == expected_delta, 'zh_cn-map.json delta is not the eight keys: '+json.dumps(map_delta, ensure_ascii=False)[:600])
    totals = prior_receipt['language']['totals']
    need(len(en_now) == totals['en_us'] + len(KEYS) and len(zh_now) == totals['zh_cn'] + len(KEYS) and len(map_now) == totals['zh_cn_map'] + len(KEYS),
         f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} are not the goal23b totals {totals} + {len(KEYS)}')
    language_kinds, original_text_checked = {}, False
    if map_delta == expected_delta:
        language_kinds = dict(Counter(map_now[k].get('kind') for k in KEYS))
        need(language_kinds == EXPECTED_KINDS, f'zh_cn-map.json kinds of the new entries are {language_kinds}, expected {EXPECTED_KINDS}')
        o_en, o_zh = lang_file(O_LANG_EN), lang_file(O_LANG_ZH)
        bad = []
        for k, source_key in KEYS.items():
            e = map_now[k]
            if e.get('target_en') != en_now.get(k) or e.get('target_zh') != zh_now.get(k): bad.append(k)
            elif e.get('kind') != 'upstream' or e.get('source_key') != source_key or e.get('source_zh') != e.get('target_zh') or e.get('source_en') != e.get('target_en'): bad.append(k)
            elif e.get('source_en') != o_en.get(source_key) or e.get('source_zh') != o_zh.get(source_key): bad.append(k)
        need(not bad, 'zh_cn-map.json entries do not match en_us.json / zh_cn.json, the original en_US.lang / zh_CN.lang values or the expected source keys: '+str(bad))
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
    assert len(start_generated) == prior_receipt['generated_resource_count'], 'Start stamp is not the goal23b generated tree'
    generated_added = sorted(set(stamp['generated']) - set(start_generated))
    generated_retired = sorted(set(start_generated) - set(stamp['generated']))
    generated_changed = sorted(p for p, h in start_generated.items() if p in stamp['generated'] and stamp['generated'][p] != h)
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(generated_added == EXPECTED_GENERATED, 'Generated additions differ from the %d expected machine, item, recipe and advancement files: missing %s, unexpected %s' % (
        len(EXPECTED_GENERATED), sorted(set(EXPECTED_GENERATED) - set(generated_added))[:8], sorted(set(generated_added) - set(EXPECTED_GENERATED))[:8]))
    need(generated_changed == EXPECTED_MODIFIED_GENERATED, f'Generated resources changed since the start: {generated_changed[:5]} (expected {EXPECTED_MODIFIED_GENERATED})')
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted(GENERATED + [GENERATED_ROOT+TAG_ENTRY] + [GENERATED_ROOT+p for p in EXPECTED_GENERATED])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, en_us.json, the block tag file and the expected additions: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))
    # Recipes: the mercury recycling recipe (computed from the generated JSON) against the original MineralRecipes row and ModItems alias; no nickel recipe.
    mineral, mod_items = original_text(O_RECIPES), original_text(O_MOD_ITEMS)
    original_recycle = {m.group(3): (m.group(1), int(m.group(2))) for m in O_RECYCLE_ROW.finditer(mineral)}
    assert original_recycle.get('MERCURY') == ('ingot_mercury', 2), 'The original mercury recycling row differs: '+str(original_recycle.get('MERCURY'))
    assert 'ingot_mercury = new ItemCustomLore().setUnlocalizedName("nugget_mercury")' in mod_items, 'The original ingot_mercury is no longer the nugget_mercury item'
    mercury = None
    path = ROOT/GENERATED_ROOT/'data/hbmsntm/recipe'/(MERCURY_RECIPE+'.json')
    if path.is_file():
        data = read(path)
        ingredients = []
        for ing in data.get('ingredients', []):
            if 'item' in ing: ingredients.append(ing['item'])
            else: ingredients.append(ing.get('items', '?')+json.dumps(ing.get('components', {}), sort_keys=True)+('' if ing.get('strict') is not True else ' strict'))
        mercury = dict(id=MERCURY_RECIPE, type=data.get('type'), ingredients=ingredients, result=data.get('result'), original=original_refs['recycle_mercury'],
                       original_item=original_refs['ingot_mercury'])
        need(mercury['type'] == 'minecraft:crafting_shapeless' and ingredients == ['hbmsntm:pellet_rtg_depleted'+json.dumps({'hbmsntm:meta': MERCURY_META}, sort_keys=True)]
             and mercury['result'] == {'count': original_recycle['MERCURY'][1], 'id': 'hbmsntm:nugget_mercury'},
             f'recipe {MERCURY_RECIPE} differs from the original mercury recycling row (2 x ingot_mercury = NEO nugget_mercury, meta {MERCURY_META}): {mercury}')
    need(not (ROOT/GENERATED_ROOT/'data/hbmsntm/recipe/pellet_rtg_depleted_nickel.json').exists(), 'a nickel recycling recipe exists: NEO has no nickel (Goal 23 decision 9)')
    # The four assembly rows: NEO source against the original rows through the ingredient translation table.
    assembly = {}
    neo_assembly = (ROOT/ASSEMBLY).read_text(encoding='utf-8') if (ROOT/ASSEMBLY).is_file() else ''
    o_assembly = original_text(O_ASSEMBLY)
    for rid in ASSEMBLY_IDS:
        o_row, n_row = recipe_row(o_assembly, rid, False), recipe_row(neo_assembly, rid, True)
        assert o_row is not None and not o_row['has_ex'] or rid != 'ass.rtg', 'The original '+rid+' row is missing or carries an inputItemsEx branch'
        assert o_row is not None and o_row['count'] == 1 and all(i[0] != '?' for i in o_row['inputs']), f'The original {rid} row could not be parsed: {o_row}'
        o_row['output'] = [o_row['output'][0], o_row['output'][1]]
        if not need(n_row is not None and n_row['count'] == 1, f'{ASSEMBLY} has no single GenericRecipe("{rid}") row that parses'): continue
        need(n_row['setup'] == o_row['setup'] and n_row['output'] == o_row['output'] and n_row['inputs'] == o_row['inputs'] and not n_row['has_ex'],
             f'{ASSEMBLY} row {rid} differs from the original (through the translation table): {n_row} vs {o_row}')
        assembly[rid] = dict(neo=n_row, original=o_row, original_reference=original_refs[rid])
    # Mapped paths: every changed path inside the compare inventory must be matched by a feature group.
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    if need(FEATURE_GROUP in by_id, 'migration/features.json has no group '+FEATURE_GROUP):
        group_entry = by_id[FEATURE_GROUP]
        need(group_entry.get('status') == 'partial-unverified' and group_entry.get('reviewed_source_commit') == SOURCE_HEAD,
             f'features.json group {FEATURE_GROUP} is not partial-unverified at {SOURCE_HEAD[:8]}')
        missing_source = [p for p in O_SOURCES + list(ASSETS.values()) if not feature_matches(group_entry, 'source', p)]
        need(not missing_source, f'features.json group {FEATURE_GROUP} lists in neither source_paths nor source_watch: {missing_source[:4]} ({len(missing_source)} paths)')
        missing_target = [p for p in NEW_JAVA if not feature_matches(group_entry, 'target', p)]
        need(not missing_target, f'features.json group {FEATURE_GROUP} lacks the new classes in target_paths/target_watch: {missing_target}')
        watch = [GENERATED_ROOT+p for p in EXPECTED_GENERATED] + [TOOLS[0]]
        missing_watch = [p for p in watch if not feature_matches(group_entry, 'target', p)]
        need(not missing_watch, f'features.json group {FEATURE_GROUP} lacks the generated machine/item/recipe files or the verifier in target_watch: {missing_watch[:4]} ({len(missing_watch)} paths)')
        absent = [p for p in group_entry.get('source_paths', []) if not (SOURCE/p).is_file()]
        need(not absent, f'features.json group {FEATURE_GROUP} source_paths missing in the original: {absent}')
    if need(FEATURE_ASSEMBLY in by_id, 'migration/features.json has no group '+FEATURE_ASSEMBLY):
        notes = ' '.join(by_id[FEATURE_ASSEMBLY].get('notes', []))
        absent_rows = [r for r in ASSEMBLY_IDS if not re.search(re.escape(r)+r'(?![a-z0-9_])', notes)]
        need(not absent_rows, f'migration/features.json group {FEATURE_ASSEMBLY} notes do not mention the assembly rows {absent_rows}')
    need(set(by_id) == set(start_features), 'features.json group ids are not the start ids: '+str(sorted(set(by_id) ^ set(start_features))))
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
        if rel in base['files']: total_start += annotations(START_FILES/rel if base['files'][rel] != sha(p) and rel in base['copied_scope'] else p)
    assert total_start == prior_receipt['gametest']['tests'], 'The start GameTest sources do not hold the previous count of '+str(prior_receipt['gametest']['tests'])
    gametest_added = total_now - total_start
    gametest_expected = total_now
    new_test_names = sorted(GAMETEST_METHOD.findall((ROOT/RTG_TESTS).read_text(encoding='utf-8'))) if (ROOT/RTG_TESTS).is_file() else []
    rtg_annotations = annotations(ROOT/RTG_TESTS) if (ROOT/RTG_TESTS).is_file() else 0
    need(new_test_names == sorted(NEW_TESTS), f'{RTG_TESTS} holds the GameTest methods {new_test_names}, not {sorted(NEW_TESTS)}')
    need(gametest_added == len(new_test_names) == rtg_annotations, f'GameTest sources grew by {gametest_added} tests, RTGGameTests holds {rtg_annotations} annotations and '
         f'{len(new_test_names)} methods (another GameTest file changed?)')
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
            need(all((GAMETEST_MARKER % n) in text for n in new_test_names), 'GameTest log lacks "[hbm-rtg-machine] <name> passed" for: '+str([n for n in new_test_names if (GAMETEST_MARKER % n) not in text]))
            need(PELLET_TEST_MARKER in text, 'GameTest log lacks "'+PELLET_TEST_MARKER+'" (the mercury/nickel assertions of rtg_pellet_recipes)')
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal23c/'+name+' (the final localization / resources / packaged-resources audit)'): continue
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        need(audit['summary'] == prior_receipt['audits'][key], f'{name} summary {audit["summary"]} differs from the previous receipt {prior_receipt["audits"][key]}')
        audit_summaries[key] = audit['summary']
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in LOGS:
        if not need((OUT/name).is_file(), 'evidence missing: build/migration/goal23c/'+name+' (the final Gradle log, ending in BUILD SUCCESSFUL)'): continue
        need('BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in FILES:
        if not need((OUT/name).is_file() and (OUT/name).stat().st_size > 0, 'evidence missing or empty: build/migration/goal23c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    for name in START_EVIDENCE + tuple(REVIEW_EVIDENCE):
        if not need((OUT/name).is_file(), ('review' if name in REVIEW_EVIDENCE else 'start')+' evidence missing: build/migration/goal23c/'+name): continue
        evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # chain.sh output, when the main agent ran it: every command exited 0, and the JAR is the one the chain built.
    if (OUT/'chain-exits-final.txt').is_file():
        exits = dict(l.split('=') for l in (OUT/'chain-exits-final.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'chain-exits-final.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'chain-exits-final.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((OUT/name).is_file(), 'evidence missing: build/migration/goal23c/'+name+' (written by chain.sh final)'): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    if (OUT/'jar-final.sha256').is_file():
        need((OUT/'jar-final.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the chain built it (jar-final.sha256)')
    # production-vs-start.diff must carry every production line change (modified files against their start copies, new Java files in full) and name every file.
    diff_path = OUT/'production-vs-start.diff'
    if need(diff_path.is_file() and diff_path.stat().st_size > 0, 'evidence missing or empty: build/migration/goal23c/production-vs-start.diff') \
            and all(p in start_text for p in MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]) and all((ROOT/p).is_file() for p in NEW_JAVA):
        diff_text = diff_path.read_text(encoding='utf-8-sig')
        message = stale_diff(diff_text, [(p, start_text[p]) for p in start_text] + [(p, None) for p in NEW_JAVA])
        if message: need(False, message)
        listed_in_diff = NEW_JAVA + MODIFIED_JAVA + [ZH_INPUT, LOCALIZATION_RECORD]
        need(all(Path(p).name in diff_text for p in listed_in_diff), 'production-vs-start.diff does not contain hunks for '+str([Path(p).name for p in listed_in_diff if Path(p).name not in diff_text]))
    final = None
    # The suites of the goal23b final run plus the Goal23C verifier.
    reference_suites = set(read(REFERENCE_PREVIOUS)['suites'])
    final_expected = len(reference_suites) + 1
    assert NEW_SUITE not in reference_suites, 'The Goal23C suite is already in the goal23b final run'
    if need((OUT/FINAL_SUMMARY).is_file(), 'evidence missing: build/migration/goal23c/'+FINAL_SUMMARY+' (the final suite rerun: run_final.py run, then summary)'):
        final = read(OUT/FINAL_SUMMARY)
        assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
        assert len(final['suites']) == final_expected, f'Final run did not cover {final_expected} suites'
        assert set(final['suites']) == reference_suites | {NEW_SUITE}, 'Final run suites differ from the goal23b final set + the Goal23C verifier: '+str(
            sorted(set(final['suites']) ^ (reference_suites | {NEW_SUITE})))
        entry = final['suites'][NEW_SUITE]
        assert entry['status'] == 'as-expected' and entry['exit'] == 0, NEW_SUITE+' did not pass in the final run'
        unexplained_final = [n for n, e in final['suites'].items() if e['status'] not in ('unchanged', 'as-expected') and 'explanation' not in e]
        assert not unexplained_final, 'Final suites with an unexplained status: '+str(unexplained_final)
        evidence[(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix()] = sha(OUT/FINAL_SUMMARY)
    verifier = verifier_references = None
    if need((OUT/VERIFY_REPORT).is_file(), 'evidence missing: build/migration/goal23c/'+VERIFY_REPORT+' (tools/migration/verify_goal23c_rtg_machine.py report)'):
        report = read(OUT/VERIFY_REPORT)
        problems = report_problems(report, [p for p in production_changed if not p.startswith(RES) or p == ZH_INPUT])
        need(not problems, VERIFY_REPORT+' is not a passing verifier run: '+'; '.join(problems))
        summary_part = report.get('summary') if isinstance(report.get('summary'), dict) else {}
        mutations = report.get('mutations')
        mutation_entries = list(mutations.values()) if isinstance(mutations, dict) else mutations if isinstance(mutations, list) else []
        detected = summary_part.get('mutations_detected', sum(1 for e in mutation_entries if isinstance(e, dict) and e.get('detected') is True))
        total = summary_part.get('mutations_total', summary_part.get('mutations_applied', len(mutation_entries)))
        verifier = dict(path=(OUT/VERIFY_REPORT).relative_to(ROOT).as_posix(), sha256=sha(OUT/VERIFY_REPORT), tool=TOOLS[0],
                        tool_sha256=sha(ROOT/TOOLS[0]) if (ROOT/TOOLS[0]).is_file() else None, mutations_detected=f'{detected}/{total}', mutations_total=total)
        evidence[verifier['path']] = verifier['sha256']
        verifier_references = sorted(set(VERIFIER_REFERENCE.findall(json.dumps(report, ensure_ascii=False))))
    compare = None
    # Against the review-6a11998d5852 snapshot (the settled Goal21A tree): the original unchanged, the target exactly the goal23b receipt's compare target
    # set plus this batch's paths inside the compare inventory; compare never lists the stamp; no unmapped change. No new snapshot.
    prior_compare = prior_receipt['compare']
    previous_target = set(prior_compare['target_owners'])
    assert prior_compare['snapshot'] == SNAPSHOT and len(previous_target) == sum(prior_compare['counts']['target'][k] for k in ('added', 'modified')), \
        'previous receipt compare target set is incomplete'
    prior_cmp = read(PREVIOUS_COMPARE)
    assert sha(PREVIOUS_COMPARE) == prior_compare['sha256'], 'previous compare.json changed'
    assert compare_paths(prior_cmp['changes']['target']['added']) | compare_paths(prior_cmp['changes']['target']['modified']) == previous_target, \
        'previous compare.json target set differs from its receipt'
    expected_target = sorted(previous_target | {p for p in changes if in_compare_inventory(p)})
    if need((OUT/COMPARE).is_file(), 'evidence missing: build/migration/goal23c/'+COMPARE+' (compare against '+SNAPSHOT+'; expected target set: %d paths)' % len(expected_target)):
        cmp = read(OUT/COMPARE)
        assert cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the 6a11998d snapshot'
        counts = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        assert all(v == 0 for v in counts['source'].values()), 'compare.json source is not 0/0/0: '+str(counts['source'])
        target = cmp['changes']['target']
        assert not target['removed'], 'compare.json target removed: '+str(target['removed'])
        assert not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], 'compare.json reports unmapped changes: '+str(cmp['unmapped_changes'])
        assert not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], 'compare.json reports removed features or missing files'
        listed = sorted(p for p in compare_paths(target['added']) | compare_paths(target['modified']) if not p.endswith('/.migration-stamp.json'))
        assert listed == expected_target, 'compare.json target set differs: extra %s, missing %s' % (
            sorted(set(listed) - set(expected_target)), sorted(set(expected_target) - set(listed)))

        def compare_owners(p):
            return set(prior_compare['target_owners'].get(p, [])) | ({OWNER} if p in changes else set())
        compare = dict(path=(OUT/COMPARE).relative_to(ROOT).as_posix(), sha256=sha(OUT/COMPARE), snapshot=SNAPSHOT, counts=counts,
                       target_owners={p: sorted(compare_owners(p)) for p in listed})
        evidence[compare['path']] = compare['sha256']

    # 6. JAR: build/libs is what gets packaged; delta against the previous package, every entry owned by goal23c.
    jar_delta = dir_delta = entry_owners = class_owners = language = None
    classes = []
    added_classes = removed_classes = 0
    if need(sha(JAR) != previous_sha, 'build/libs/hbmsntm-198A.jar is still the previous (goal23b) package (run build)'):
        classes_root = ROOT/'build/classes/java/main'
        classes = sorted(classes_root.rglob('*.class'))
        asset_entries = {t[len(RES):]: t for t in ASSETS}
        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
            names = jar.namelist()
            assert len(names) == len(set(names)), 'Duplicate archive entries'
            assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
            # The JAR must be the final build of the settled tree: every generated resource, zh_cn.json, the 5 resources and every compiled class equal the sources.
            differs = [p for p in stamp['generated'] if p not in names or jar.read(p) != (ROOT/'src/generated/resources'/p).read_bytes()]
            if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): differs.append(ZH_ENTRY)
            differs += [e for e, t in asset_entries.items() if e not in names or not (ROOT/t).is_file() or jar.read(e) != (ROOT/t).read_bytes()]
            differs += [path.relative_to(classes_root).as_posix() for path in classes
                        if path.relative_to(classes_root).as_posix() not in names or jar.read(path.relative_to(classes_root).as_posix()) != path.read_bytes()]
            need(not differs, f'build/libs JAR differs from the generated resources, zh_cn.json, the imported resources or build/classes ({len(differs)} entries, first: {differs[:5]}); run the final build')
            en_jar = lang_delta(json.loads(prior.read(EN_ENTRY)), json.loads(jar.read(EN_ENTRY)))
            zh_jar = lang_delta(json.loads(prior.read(ZH_ENTRY)), json.loads(jar.read(ZH_ENTRY)))
            need(en_jar == en_delta == expected_delta and zh_jar == zh_delta == expected_delta,
                 f'JAR en_us.json or zh_cn.json delta against the previous package is not the {len(KEYS)} RT generator keys: en '+str(en_jar)[:300]+', zh '+str(zh_jar)[:300])
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
                elif kind == 'modified' and n in (ZH_ENTRY, EN_ENTRY, TAG_ENTRY): owner = [OWNER]
                elif kind == 'added' and (n in asset_entries or n in generated_entries): owner = [OWNER]
                if not owner: unowned.append(f'{kind}: {n}')
                entry_owners[n] = dict(change=kind, owners=owner)
        need(not unowned, 'JAR entry without exactly one owner (only classes of the 22 Java sources, the 5 imported resources, the generated additions and the modified '
             'en_us.json / zh_cn.json / pickaxe tag are owned; META-INF/MANIFEST.MF is not): '+str(unowned[:10]))
        # No directory delta unless an added entry needs it; never a removed directory.
        added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
        need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
        changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
        class_owners = sorted({owner_class(n) for n in changed_classes})
        changed_java = [p for p in PRODUCTION_JAVA if p in changes]
        need(set(class_owners) == set(changed_java), 'Changed Java sources and goal23c JAR classes differ: no class change for '+str(sorted(set(changed_java) - set(class_owners)))
             + '; unexpected: '+str(sorted(set(class_owners) - set(changed_java))))
        need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
        expected_non_class = set(asset_entries) | {ZH_ENTRY, EN_ENTRY, TAG_ENTRY} | generated_entries
        non_class = {n for kind in ('added', 'removed', 'modified') for n in jar_delta[kind] if not n.endswith('.class')}
        need(non_class == expected_non_class, 'JAR non-class delta differs from the imported resources + language + block tag + generated additions: extra %s, missing %s' % (
            sorted(non_class - expected_non_class)[:8], sorted(expected_non_class - non_class)[:8]))
        for p in NEW_JAVA:
            outer = p[len('src/main/java/'):-len('.java')]
            need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
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

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added),
                   generated_modified=generated_changed, start_drift=sorted(drift_report), repinned_since_goal23b_start=sorted(repinned),
                   goal23b_paths_unchanged=len(goal23b_unchanged), goal23a_paths_unchanged=len(goal23a_unchanged), concurrent_23d=concurrent_23d,
                   en_delta=en_delta, zh_delta=zh_delta, map_delta=map_delta, language_kinds=language_kinds, original_lang_values_checked=original_text_checked,
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)),
                   insert_lines=insert_summary, replaced_lines=replaced_summary, edit_counts=edit_summary, machine=opt(machine, 'constants'),
                   mercury_recipe=mercury, assembly_rows=sorted(assembly), gametest=gametest_line, gametest_expected=gametest_expected, gametest_added=gametest_added,
                   new_rtg_tests=new_test_names, final_suites_expected=final_expected, compare=opt(compare, 'counts'), compare_target_expected=len(expected_target),
                   jar_delta={k: len(v) for k, v in jar_delta.items()} if jar_delta else None, jar_directory_delta=dir_delta, class_owners=class_owners,
                   protected_paths=len(protected), old_releases_preserved=len(old_releases), preserved_release_files=len(base['old_release_files']),
                   older_checklist_drift_explained=sorted(explained), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)

    # The receipt: assembled in both modes (None where the evidence does not exist yet in --check); only the real run writes it, and there every need() above raised.
    dest = RELEASE/RELEASE_NAME
    digest = sha(JAR)
    hashes = {p: sha(ROOT/p) for p in reports if (ROOT/p).is_file()}
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(len(KEYS), language_kinds, len(ASSETS), len(new_test_names), gametest_count),
                   radiation_warning=RADIATION_NOTE+prior_receipt['radiation_warning'],
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=start_head, planning_commit=prior_receipt['planning_commit'], commits={},
                   target_head_at_packaging=head, base_release=previous_rel, base_release_sha256=previous_sha, base_release_receipt_sha256=previous_receipt_sha,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(),
                   start_content=dict(base['start_content'], start_build_sha256=start_jar_sha, dirty_paths=base['dirty_paths'],
                                      note='The start tree is HEAD dd69a404 (the Goal 23 planning commit on top of the Goal 22 close-out commit 670d5911) plus the '
                                           'uncommitted Goal23A and Goal23B delivery paths, kept uncommitted by Goal 23 decision 15: the dirty paths are the goal23b '
                                           'receipt\'s 88 changed files at their receipt after-hashes, the 13 Goal23A paths it left alone at the hash it recorded, the two '
                                           'delivered 23D paths, and the two planning records the Goal 23 planning session revised after the goal23b package '
                                           '(GOAL23C.md, GOAL23-THREAD-PROMPTS.md; GOAL23.md is also a goal23b path); build/libs at the start is the goal23b package '
                                           'byte for byte. Paths this batch changes again record the start hash as before_sha256.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed,
                   compiled_classes_verified=len(classes),
                   production=production_changed, production_new=[p for p in NEW_JAVA + list(ASSETS) if p in changes], production_unchanged_optional=[],
                   sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   insert_only_lines=insert_summary, replaced_lines=replaced_summary, edited_lines=edit_summary,
                   resources={}, resource_ownership=RESOURCE_OWNERSHIP, imported_resources=imported,
                   machine=machine,
                   language=dict(keys=dict(en_us_added=en_delta['added'], zh_cn_added=zh_delta['added'], zh_cn_map_added=map_delta['added']),
                                 totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 map_kinds_added=language_kinds, local_keys=[k for k in KEYS if map_now.get(k, {}).get('kind') == 'local'],
                                 original_keys=KEYS, original_values_checked=original_text_checked,
                                 start_sha256={p: base['files'][p] for p in (PROVIDER, EN, ZH_INPUT, LOCALIZATION_RECORD)},
                                 provider_lines_inserted=insert_summary.get(PROVIDER), jar_delta=language,
                                 note='All eight entries are upstream: the original English and Chinese verbatim (tile.machine_rtg_grey.name, container.rtg, '
                                      'desc.gui.rtg.heat, .pellets, .pelletHeat, .pelletPower, item.thermo_element.name, item.rtg_unit.name); no local keys. '
                                      'desc.gui.rtg.pelletHeat is defined by the original but unused by its GUI.'),
                   recipes=dict(mercury=mercury, assembly=assembly, not_registered=['pellet_rtg_depleted_nickel'],
                                original_references={k: v for k, v in original_refs.items() if k.startswith(('recycle_', 'ingot_', 'ass.'))},
                                note='The mercury recycling row (original MineralRecipes.java:219, ingot_mercury = NEO nugget_mercury) moves in from the 23B deferral; the '
                                     'nickel row stays unregistered (NEO has no nickel). The four assembly rows are registered in both enable528 settings, normal inputs '
                                     'only (no inputItemsEx branch, no item_expensive in NEO).'),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), older_checklist_drift_explained=sorted(explained),
                   start_drift_explained=drift_report, repinned_since_goal22d_start=prior_receipt['repinned_since_goal22d_start'],
                   repinned_since_goal23a_start=prior_receipt['repinned_since_goal23a_start'],
                   repinned_since_goal23b_start={p: dict(goal23b_start_pin_sha256=h, goal23c_start_sha256=base['files'][p]) for p, h in repinned.items()},
                   post_23b_planning=dict(paths={p: dict(goal23b_receipt_sha256=d['goal23b_receipt'], start_sha256=d['start'], current_sha256=sha(ROOT/p), owner=OWNER if p in changes else OWNER_PLANNING)
                                                 for p, d in planning.items()}, note=base['post_23b_planning']['note']),
                   goal23b_paths_unchanged={p: base['files'][p] for p in goal23b_unchanged},
                   goal23a_paths_unchanged={p: prior_receipt['goal23a_paths_unchanged'][p] for p in goal23a_unchanged},
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), new_snapshot=False), compare=compare,
                   final_suites=dict(path=(OUT/FINAL_SUMMARY).relative_to(ROOT).as_posix(), sha256=sha(OUT/FINAL_SUMMARY) if (OUT/FINAL_SUMMARY).is_file() else None,
                                     suites=len(final['suites']) if final else None, ok=opt(final, 'ok')),
                   verifier=dict(verifier, original_references=verifier_references) if verifier else None,
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line,
                                 tests=gametest_count, added_tests=gametest_added, new_rtg_tests=new_test_names,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds; the ten RTGGameTests cover the block '
                                      'and its ticker, the production block entity\'s updateEntity (generation, heat cap, in-machine decay, slot semantics), slot rules '
                                      'and hoppers, NBT and packet round trips, a real cable network and battery socket per direction, drops on destroyBlock and the '
                                      'four assembly rows as loaded; rtg_pellet_recipes asserts the mercury row and the missing nickel row; no client (screen, bars, '
                                      'tooltips and OBJ connectors are not rendered), no real player, no saved world, no real 18-minute decay.'),
                   audits=audit_summaries, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, class_owners=class_owners,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS,
                   concurrent_23d=dict(owner=OWNER_23D, files=concurrent_23d, start_hashes=concurrent['start_hashes'],
                                       note='The delivered read-only batch 23D (RBMK scope) owns exactly these two paths (uncommitted since before this start); they are '
                                            'neither packaged nor attributed to Goal23C and equal their start hashes.'),
                   evidence_sha256={**hashes, **evidence, **{p: d['current_sha256'] for p, d in drift_report.items()}, SNAPSHOT: sha(ROOT/SNAPSHOT)},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the static '
                            'verifier with in-memory mutations, the final old-suite rerun, compare against the review-6a11998d5852 snapshot and two independent static '
                            'reviews. No in-game client test was run: the GUI, the heat and power bars, the pellet list tooltip, the OBJ connectors, JEI and the creative '
                            'tab in either language, a real player crafting or assembling the parts, multiplayer or a dedicated server beyond GameTest, and a real '
                            '18-minute decay observation are unverified; GOAL23C-ACCEPTANCE.md is written but not executed.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, start_jar_sha), 'build/libs JAR is an older JAR'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal23c JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal23b package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(old_releases)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
