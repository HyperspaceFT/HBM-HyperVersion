#!/usr/bin/env python3
"""Survival-source closure: for each item in a list, is there a way to get it in survival, and through what chain?

Run from the NEO root:
  python3 -B -X utf8 tools/migration/acceptance/closure.py --recipes-export build/migration/accept/clients/solo/config/hbmRecipes \\
      hbmsntm:settings_tool hbmsntm:part_generic@0 hbmsntm:fluorite hbmsntm:machine_zirnox
  ... --items-file items.txt --json out.json

Sources, read from the data the mod ships (no game run):
  - every minecraft: item is taken as obtainable (vanilla survival; creative-only vanilla items are not modelled);
  - world generation: blocks placed by the configured features that a placed feature uses and a biome modifier or a
    biome lists, from both src/main/resources and src/generated/resources (the hand-written ores live in the former),
    turned into items by the blocks' loot tables. The config switches (hbmsntm:config_gated_add_features, every key must
    be on) and the config counts and rarities (hbmsntm:config_count, hbmsntm:config_rarity, 0 is off) are read at their
    defaults from CommonConfig.java, and a feature they turn off is no source (the report lists it). Features that place
    their blocks in code (hbmsntm:oil_bubble and the others in CODE_FEATURES) name their blocks here, with the line;
  - loot tables under loot_table/chests and loot_table/entities (taken as reachable; the report names them);
  - crafting and smelting recipe JSON (shaped, shapeless, smelting, blasting, smoking, campfire, stonecutting), with
    item tags from the mod's data, NeoForge's jar (c:) and Minecraft's resources jar (minecraft:);
  - the machine recipe tables, which are defined in Java and only exist as JSON after a game run writes them to
    config/hbmRecipes: --recipes-export names such a directory (a client's or the server's), and the report records it
    with the file hashes and the build that wrote it (--export-build, default: the current build/libs jar);
  - the anvil's construction and smithing recipes, which no game run writes as JSON: --anvil-export takes the file the
    acceptance executor's export step writes (exports/anvil.json in its step directory);
  - the crucible: --crucible-export takes the export step's exports/crucible.json (which items melt into which
    materials, by the crucible's own rule, and what each mold casts from each material); the alloy recipes come from
    _hbmCrucible.json in the machine-recipe export. Materials show up in chains as material:<Name>; melting needs
    the crucible, a cast needs its mold item (the foundry blocks around them are not checked);
  - the gas centrifuge cascades, the combination oven and the RBMK rod disassembly: --machines-export takes the export
    step's exports/machines.json (kind machines);
  - the universal fluid containers (tanks and barrels, filled from and emptied into machine tanks);
  - world-generated blocks as they stand in the world, block:<id> (an oil deposit a derrick drills, say);
  - process sources, the products of machine code and player actions outside any table (a reactor burning a rod, the
    waste drum cooling waste, pumps and wells making fluids): --sources takes a hand-written list (default
    closure_sources.json next to this script), each entry with the NEO and original file:line it rests on.
A recipe makes its outputs obtainable when every ingredient is, fluids included (fluid:<NAME> as the export writes it,
fluid:<NAME>:p<n> when pressurised), and when one of its machines is (MACHINES; a table not listed there is reported).
Items with a meta variant are written id@meta (part_generic@0 is the pneumatic piston); a plain id matches any variant,
and a stack without the meta component is the item's default variant (DEFAULT_META, else 0). Python standard library only.
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import fluidids  # noqa: E402

REPO = common.REPO
DATA_ROOTS = [REPO / 'src' / 'main' / 'resources' / 'data', REPO / 'src' / 'generated' / 'resources' / 'data']
ARTIFACTS = REPO / 'build' / 'moddev' / 'artifacts'
JARS = ['neoforge-21.1.228.jar', 'neoforge-21.1.228-client-extra-aka-minecraft-resources.jar']
WILDCARD = 32767
CONFIG_JAVA = REPO / 'src' / 'main' / 'java' / 'com' / 'hbm' / 'config' / 'CommonConfig.java'
SOURCES = Path(__file__).resolve().parent / 'closure_sources.json'
# Machine recipe file -> the machine items that run it (any one will do); a recipe of a listed file also needs the machine.
CRUCIBLE = 'hbmsntm:machine_crucible'
MACHINES = {
    '_hbmArcFurnace.json': 'hbmsntm:machine_arc_furnace',
    '_hbmArcWelder.json': 'hbmsntm:machine_arc_welder',
    '_hbmAssemblyMachine.json': 'hbmsntm:machine_assembly_machine',
    '_hbmBlastFurnace.json': 'hbmsntm:machine_blast_furnace',
    '_hbmCentrifuge.json': 'hbmsntm:machine_centrifuge',
    '_hbmChemicalPlant.json': 'hbmsntm:machine_chemical_plant',
    '_hbmCoker.json': 'hbmsntm:machine_coker',
    '_hbmCompressor.json': 'hbmsntm:machine_compressor',
    '_hbmCracking.json': 'hbmsntm:machine_catalytic_cracker',
    '_hbmCrucible.json': CRUCIBLE,
    '_hbmCrucibleSmelting.json': CRUCIBLE,
    '_hbmCrystallizer.json': 'hbmsntm:machine_crystallizer',
    '_hbmFractions.json': 'hbmsntm:machine_fraction_tower',
    '_hbmFuelpool.json': 'hbmsntm:machine_waste_drum',
    '_hbmIrradiation.json': 'hbmsntm:rbmk_outgasser',
    '_hbmMixer.json': 'hbmsntm:machine_mixer',
    '_hbmPUREX.json': 'hbmsntm:machine_purex',
    '_hbmPress.json': 'hbmsntm:machine_press',
    '_hbmRotaryFurnace.json': 'hbmsntm:machine_rotary_furnace',
    '_hbmShredder.json': 'hbmsntm:machine_shredder',
    '_hbmSoldering.json': 'hbmsntm:machine_soldering_station',
    '_hbmVacuumRefinery.json': 'hbmsntm:machine_vacuum_distill',
}
GAS_CENTRIFUGE = 'hbmsntm:machine_gas_centrifuge'
COMBINATION = 'hbmsntm:furnace_combination'
RBMK_FUEL_CHANNELS = ('hbmsntm:rbmk_rod', 'hbmsntm:rbmk_rod_mod')
# A stack without the hbmsntm:meta component is the item's default variant: the items whose default is not 0
# (BoltItem.java:14 steel, WireDenseItem.java:14 gold, RawIngotItem.java:14 redstone).
DEFAULT_META = {'hbmsntm:bolt': 30, 'hbmsntm:wire_dense': 7900, 'hbmsntm:ingot_raw': 1}
# Configured feature types that place their blocks in code: type -> [(block, where)]
_F = 'src/main/java/com/hbm/world/feature/'
CODE_FEATURES = {
    'hbmsntm:oil_bubble': [('hbmsntm:ore_oil', _F + 'OilBubbleFeature.java:131'), ('hbmsntm:dirt_oily', _F + 'OilBubbleFeature.java:175'),
                           ('hbmsntm:dirt_dead', _F + 'OilBubbleFeature.java:175'), ('hbmsntm:sand_oily', _F + 'OilBubbleFeature.java:188'), ('hbmsntm:sand_oily_red', _F + 'OilBubbleFeature.java:188'),
                           ('hbmsntm:stone_cracked', _F + 'OilBubbleFeature.java:193'), ('hbmsntm:oil_spill', _F + 'OilBubbleFeature.java:235')],
    'hbmsntm:sand_oil_bubble': [('hbmsntm:ore_oil_sand', _F + 'SandOilBubbleFeature.java:157'),
                                ('hbmsntm:dirt_oily', _F + 'SandOilBubbleFeature.java:202'), ('hbmsntm:dirt_dead', _F + 'SandOilBubbleFeature.java:202'),
                                ('hbmsntm:sand_oily', _F + 'SandOilBubbleFeature.java:213'), ('hbmsntm:sand_oily_red', _F + 'SandOilBubbleFeature.java:213'),
                                ('hbmsntm:stone_cracked', _F + 'SandOilBubbleFeature.java:216'), ('hbmsntm:oil_spill', _F + 'SandOilBubbleFeature.java:251')],
    # the deposit also lays an oil spot on the surface, with mustard willows (BedrockOilDepositFeature.java:47)
    'hbmsntm:bedrock_oil': [('hbmsntm:ore_bedrock_oil', _F + 'BedrockOilDepositFeature.java:39'),
                            ('hbmsntm:dirt_oily', _F + 'OilSpot.java:54'), ('hbmsntm:dirt_dead', _F + 'OilSpot.java:54'),
                            ('hbmsntm:plant_mustard_willow', _F + 'OilSpot.java:58'), ('hbmsntm:sand_oily', _F + 'OilSpot.java:64'),
                            ('hbmsntm:sand_oily_red', _F + 'OilSpot.java:64'), ('hbmsntm:stone_cracked', _F + 'OilSpot.java:68')],
    'hbmsntm:coltan_deposit': [('hbmsntm:ore_coltan', _F + 'ColtanDepositFeature.java:89')],
    'hbmsntm:crashed_bomb': [('hbmsntm:crashed_bomb', _F + 'CrashedBombFeature.java:35')],
    'hbmsntm:landmine': [('hbmsntm:mine_ap', _F + 'LandmineFeature.java:40')],
    'hbmsntm:schist_stratum': [('hbmsntm:stone_gneiss', _F + 'SchistStratumFeature.java:62')],
    'hbmsntm:smoldering_netherrack': [('hbmsntm:ore_nether_smoldering', _F + 'SmolderingNetherrackFeature.java:37')],
}
INPUT_KEYS = ('input', 'inputItem', 'inputs', 'solidInput', 'pcb', 'solder', 'toppings')
# the arc furnace writes its item result under `solid` (ArcFurnaceRecipes.java:121-135)
OUTPUT_KEYS = ('output', 'outputItem', 'outputs', 'byproduct', 'solidOutput', 'solid')
# Fluid stacks are [NAME, amount(, pressure)] or a bare NAME in these keys; the rotary furnace's [Material, amount] output
# is a crucible material (fluid names are upper case, material names are not). `steam` is the rotary furnace's steam.
FLUID_IN_KEYS = ('input', 'inputFluid', 'fluid', 'input1', 'input2')
FLUID_OUT_KEYS = ('output', 'outputFluid', 'fluidOutput', 'output0', 'output1', 'output2', 'output3', 'byproduct', 'outputType')
COOKING = ('minecraft:smelting', 'minecraft:blasting', 'minecraft:smoking', 'minecraft:campfire_cooking', 'minecraft:stonecutting')


def base(item):
    return item.split('@', 1)[0]


def variant(item):
    """A plain item id as a stack: the item's default variant."""
    if '@' in item or item.startswith(('fluid:', 'material:', 'block:', '#', 'stamp:')):
        return item
    return '%s@%d' % (item, DEFAULT_META.get(item, 0))


def machines_of(m):
    return () if not m else (m,) if isinstance(m, str) else tuple(m)


def config_defaults(path=CONFIG_JAVA):
    """{key: default} of CommonConfig's .define("key", bool) and .defineInRange("key", number, ...)."""
    text = Path(path).read_text(encoding='utf-8') if Path(path).is_file() else ''
    out = {k: v == 'true' for k, v in re.findall(r'\.define\(\s*"(\w+)"\s*,\s*(true|false)\s*\)', text)}
    for k, v in re.findall(r'\.defineInRange\(\s*"(\w+)"\s*,\s*(-?[\d.]+)[DdFfLl]?\s*,', text):
        out[k] = float(v) if '.' in v else int(v)
    return out


class Data:
    def __init__(self):
        self.files = {}      # 'namespace/path' -> json (later roots win, like resource packs)
        self.jar_files = {}

    def load(self):
        for root in DATA_ROOTS:
            if root.is_dir():
                for path in root.rglob('*.json'):
                    self.files[path.relative_to(root).as_posix()] = (json.loads(path.read_text(encoding='utf-8')), common.rel(path))
        for name in JARS:
            jar = ARTIFACTS / name
            if not jar.is_file():
                continue
            with zipfile.ZipFile(jar) as z:
                for entry in z.namelist():
                    if entry.startswith('data/') and '/tags/item' in entry and entry.endswith('.json'):
                        self.jar_files[entry[5:]] = (json.loads(z.read(entry)), '%s!%s' % (name, entry))
        return self

    def under(self, folder):
        """{'ns:path': (json, origin)} for files data/<ns>/<folder>/<path>.json."""
        out = {}
        for key, value in self.files.items():
            ns, _, rest = key.partition('/')
            if rest.startswith(folder + '/'):
                out['%s:%s' % (ns, rest[len(folder) + 1:-5])] = value
        return out

    def tags(self):
        tags = {}
        for source in (self.jar_files, self.files):
            for key, (data, origin) in source.items():
                ns, _, rest = key.partition('/')
                for folder in ('tags/item/', 'tags/items/'):
                    if rest.startswith(folder):
                        name = '%s:%s' % (ns, rest[len(folder):-5])
                        values = tags.setdefault(name, [])
                        if data.get('replace'):
                            values.clear()
                        for v in data.get('values', []):
                            values.append(v['id'] if isinstance(v, dict) else v)
        return tags


def resolve_tag(tags, name, seen=None):
    seen = seen if seen is not None else set()
    if name in seen:
        return set()
    seen.add(name)
    out = set()
    for v in tags.get(name, []):
        out |= resolve_tag(tags, v[1:], seen) if v.startswith('#') else {v}
    return out


def ingredient(tags, value):
    """A recipe JSON ingredient -> set of acceptable items (id or id@meta)."""
    if isinstance(value, list):
        out = set()
        for v in value:
            out |= ingredient(tags, v)
        return out
    if 'tag' in value:
        return resolve_tag(tags, value['tag']) or {'#' + value['tag']}
    if value.get('type') == 'neoforge:components':
        items = value['items'] if isinstance(value['items'], list) else [value['items']]
        meta = value.get('components', {}).get('hbmsntm:meta')
        return {('%s@%s' % (i, meta)) if meta is not None else i for i in items}
    if 'item' in value:
        return {value['item']}
    if 'items' in value:
        return set(value['items'] if isinstance(value['items'], list) else [value['items']])
    return {'?' + json.dumps(value)}


def result_item(value):
    if isinstance(value, str):
        return variant(value) if value in DEFAULT_META else value
    meta = (value.get('components') or {}).get('hbmsntm:meta')
    rid = value.get('id') or value.get('item')
    return '%s@%s' % (rid, meta) if meta is not None else variant(rid) if rid in DEFAULT_META else rid


def crafting_recipes(data, tags):
    recipes = []
    for name, (r, origin) in data.under('recipe').items():
        t = r.get('type')
        if t == 'minecraft:crafting_shaped':
            ings = [ingredient(tags, r['key'][c]) for c in sorted({c for row in r['pattern'] for c in row if c != ' '})]
        elif t == 'minecraft:crafting_shapeless':
            ings = [ingredient(tags, i) for i in r['ingredients']]
        elif t in COOKING:
            ings = [ingredient(tags, r['ingredient'])]
        else:
            continue
        recipes.append(dict(kind=t.split(':')[1], name=name, origin=origin, inputs=ings, outputs={result_item(r['result'])}, machine=None))
    return recipes


def machine_entries(node, found):
    """Ingredient lists inside a machine recipe input: ["item", id, n, meta], ["tag", t, n], ["dict", d, n], [id, n...]."""
    if isinstance(node, list):
        if node and isinstance(node[0], str):
            head = node[0]
            if head == 'item' and len(node) > 1:
                # a missing meta is variant 0 (SerializableRecipe.readAStack); only the wildcard takes any variant
                meta = node[3] if len(node) > 3 and isinstance(node[3], int) else 0
                found.append({node[1] if meta == WILDCARD else '%s@%s' % (node[1], meta)})
                return
            if head in ('tag', 'dict') and len(node) > 1:
                found.append({'#' + node[1]})
                return
            if ':' in head:
                # [id, count, meta]: a missing meta is variant 0, the wildcard any variant
                meta = node[2] if len(node) > 2 and isinstance(node[2], int) else 0
                found.append({head if meta == WILDCARD else '%s@%s' % (head, meta)})
                return
        for child in node:
            machine_entries(child, found)
    elif isinstance(node, dict):
        for child in node.values():
            machine_entries(child, found)


def machine_outputs(node, found):
    """Item ids in a machine recipe output; [id, count, meta] carries a variant in its third place (an int)."""
    if isinstance(node, str):
        if ':' in node:
            found.add(node)
    elif isinstance(node, list):
        if len(node) >= 3 and isinstance(node[0], str) and ':' in node[0] and isinstance(node[2], int) and node[2] != WILDCARD:
            found.add('%s@%s' % (node[0], node[2]))
            return
        for child in node:
            machine_outputs(child, found)
    elif isinstance(node, dict):
        for child in node.values():
            machine_outputs(child, found)


def fluid_stacks(node, found, materials=None):
    """fluid:<NAME> for every fluid stack [NAME, amount(, pressure)] or bare NAME under node; [Material, amount] (a name
    that is not upper case) goes to materials as material:<Material> when materials is given."""
    if isinstance(node, str):
        if ':' not in node and node.isupper():
            found.add('fluid:' + node)
    elif isinstance(node, list):
        if len(node) >= 2 and isinstance(node[0], str) and ':' not in node[0] and isinstance(node[1], (int, float)) \
                and not isinstance(node[1], bool):
            if node[0].isupper():
                p = node[2] if len(node) > 2 and isinstance(node[2], int) else 0
                found.add('fluid:%s%s' % (node[0], ':p%d' % p if p else ''))
            elif materials is not None:
                materials.add('material:' + node[0])
            return
        for child in node:
            fluid_stacks(child, found, materials)


def machine_recipe(path, name, r, tags):
    """One exported machine recipe -> a recipe dict (None when it makes nothing)."""
    ings = []
    for key in INPUT_KEYS:
        if key in r:
            machine_entries(r[key], ings)
    ings = [expand(tags, i) for i in ings]
    if isinstance(r.get('stamp'), str):
        ings.append({'stamp:' + r['stamp']})  # any stamp item of that type, resolved in closure()
    fin = set()
    for key in FLUID_IN_KEYS:
        if key in r:
            fluid_stacks(r[key], fin)
    if isinstance(r.get('steam'), int) and r['steam'] > 0:
        fin.add('fluid:STEAM')
    ings += [{f} for f in sorted(fin)]
    if isinstance(r.get('blueprintpool'), str):
        # a pooled recipe runs only with a blueprint of one of its pools installed (MachineAssemblyMachineBlockEntity.java:336)
        ings.append({'blueprint:' + p for p in r['blueprintpool'].split(':')})
    outs, materials = set(), set()
    for key in OUTPUT_KEYS:
        if key in r:
            machine_outputs(r[key], outs)
    fout = set()
    for key in FLUID_OUT_KEYS:
        if key in r:
            fluid_stacks(r[key], fout, materials)
    outs |= fout | materials
    if not outs:
        return None
    return dict(kind='machine', name='%s#%s' % (path.name, name), origin=common.rel(path), inputs=ings, outputs=outs,
                machine=MACHINES.get(path.name), unknown_machine=path.name not in MACHINES)


def machine_recipes(export, tags):
    recipes, files = [], {}
    if not export:
        return recipes, files
    for path in sorted(Path(export).glob('*.json')):
        files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.name == '_hbmCrucible.json':
            continue  # alloys: crucible_recipes()
        data = json.loads(path.read_text(encoding='utf-8'))
        entries = data.get('recipes', []) if isinstance(data, dict) else data
        for n, r in enumerate(entries if isinstance(entries, list) else []):
            if isinstance(r.get('recipes'), list) and 'outputType' in r:
                # the mixer: one output fluid, several input variants
                for m, sub in enumerate(r['recipes']):
                    rec = machine_recipe(path, '%s/%s' % (r.get('name', n), m), dict(sub, outputType=r['outputType']), tags)
                    if rec:
                        recipes.append(rec)
                continue
            rec = machine_recipe(path, r.get('name', n), r, tags)
            if rec:
                recipes.append(rec)
    return recipes, files


def executor_machine_recipes(path):
    """The export step's exports/machines.json: gas centrifuge cascades, combination oven, RBMK rod disassembly."""
    recipes = []
    if not path:
        return recipes, None
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    origin = common.rel(Path(path))
    for n, r in enumerate(data.get('gas_centrifuge', [])):
        recipes.append(dict(kind='gas centrifuge', name='gas centrifuge %s #%d (%d centrifuges%s)' % (
                            r['fluid'], n, r.get('centrifuges', 1), ', speed upgrade' if r.get('high_speed') else ''),
                            origin=origin, inputs=[{'fluid:' + r['fluid']}] + ([{'hbmsntm:upgrade_gc_speed'}] if r.get('high_speed') else []),
                            outputs={stack_key(s) for s in r['outputs']}, machine=GAS_CENTRIFUGE))
    for n, r in enumerate(data.get('combination', [])):
        outs = set()
        if r.get('output'):
            outs.add(stack_key(r['output']))
        if r.get('fluid'):
            outs.add('fluid:' + r['fluid'][0])
        if outs:
            recipes.append(dict(kind='combination oven', name='combination #%d' % n, origin=origin,
                                inputs=[{stack_key(s) for s in r['inputs']}], outputs=outs, machine=COMBINATION))
    for r in data.get('rbmk_disassembly', []):
        # a fresh rod gives nothing (RBMKRodDisassemblyRecipe.java:45): the rod is burnt in an RBMK fuel channel first, and
        # how far decides the pellet's meta 0-9 (:48-50)
        recipes.append(dict(kind='rbmk disassembly', name='disassemble %s (burnt)' % r['rod'], origin=origin, inputs=[{r['rod']}],
                            outputs={'%s@%d' % (r['pellet'], m) for m in range(10)}, machine=RBMK_FUEL_CHANNELS))
    return recipes, hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fluid_container_flags(path=fluidids.FLUIDS):
    """{fluid name: 'none' | 'lead' | ''}: the FT_NoContainer (NOCON) and FT_LeadContainer (LEADCON) traits of each fluid."""
    text = Path(path).read_text(encoding='utf-8') if Path(path).is_file() else ''
    flags = {}
    for statement in text.split(';'):
        m = re.match(r'\s*([A-Z0-9_]+)\s*(?:=|\.addTraits)', statement)
        if m:
            name = m.group(1)
            if re.search(r'\bNOCON\b', statement):
                flags[name] = 'none'
            elif re.search(r'\bLEADCON\b', statement) and flags.get(name) != 'none':
                flags[name] = 'lead'
    return flags


def container_recipes(ids=None, flags=None):
    """Universal fluid containers (FluidContainerRegistry.java:44-57): a fluid with a container fills a lead tank, and unless it
    needs lead also a tank and a barrel (meta = the fluid's id); emptying one gives the fluid back. Filling is taken to happen in
    the tank of whatever machine holds the fluid."""
    ids = fluidids.fluid_ids() if ids is None else ids
    flags = fluid_container_flags() if flags is None else flags
    where = 'src/main/java/com/hbm/inventory/FluidContainerRegistry.java:44-57'
    recipes = []
    for name, i in ids.items():
        if i == 0 or flags.get(name) == 'none':
            continue
        kinds = [('fluid_tank_lead', 'hbmsntm:fluid_tank_lead_empty')]
        if flags.get(name) != 'lead':
            kinds += [('fluid_tank', 'hbmsntm:fluid_tank_empty'), ('fluid_barrel', 'hbmsntm:fluid_barrel_empty')]
        for kind, empty in kinds:
            full = 'hbmsntm:%s_full@%d' % (kind, i)
            recipes.append(dict(kind='container', name='fill %s with %s' % (kind, name), origin=where, inputs=[{'fluid:' + name}, {empty}],
                                outputs={full}, machine=None))
            recipes.append(dict(kind='container', name='empty %s of %s' % (kind, name), origin=where, inputs=[{full}],
                                outputs={'fluid:' + name}, machine=None))
    return recipes


# Blueprint folder meta -> the pool prefix it draws from (BlueprintFolderItem.java:25-28, GenericRecipes.java:36-40).
BLUEPRINT_FOLDERS = {0: 'alt.', 1: 'discover.', 2: 'secret.'}


def blueprint_recipes(pools):
    """Opening a blueprint folder gives a blueprint of a random pool with its prefix (BlueprintFolderItem.java:59-62); the
    folders come from the blueprint chest's loot (loot_table/chests/blueprints). Enough folders give every such pool."""
    where = 'src/main/java/com/hbm/items/machine/BlueprintFolderItem.java:59-62'
    return [dict(kind='blueprint', name='open blueprint folder %d' % meta, origin=where, inputs=[{'hbmsntm:blueprint_folder@%d' % meta}],
                 outputs={'blueprint:' + pool}, machine=None)
            for pool in pools for meta, prefix in BLUEPRINT_FOLDERS.items() if pool.startswith(prefix)]


def process_recipes(path):
    """The hand-written process sources (closure_sources.json): products of machine code and player actions."""
    recipes = []
    if not path or not Path(path).is_file():
        return recipes, None
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    for n, e in enumerate(data.get('sources', [])):
        recipes.append(dict(kind='process', name=e.get('name') or 'process #%d' % n, origin='%s; original %s' % (e['neo'], e.get('original', '-')),
                            inputs=[set(a) if isinstance(a, list) else {a} for a in e.get('inputs', [])],
                            outputs=set(e['products']), machine=e.get('machine')))
    return recipes, hashlib.sha256(Path(path).read_bytes()).hexdigest()


def anvil_recipes(path):
    """The executor's export of the anvil tables (export step): construction and smithing recipes."""
    recipes = []
    if not path:
        return recipes, None
    data = json.loads(Path(path).read_text(encoding='utf-8'))

    def key(s):
        return stack_key(s)
    for kind in ('construction', 'smithing'):
        for n, r in enumerate(data.get(kind, [])):
            recipes.append(dict(kind='anvil ' + kind, name='anvil %s #%d (tier %s)' % (kind, n, r.get('tier_lower')),
                                origin=common.rel(Path(path)), inputs=[{stack_key(s, exact=True) for s in alts} for alts in r['inputs'] if alts],
                                outputs={key(s) for s in r['outputs']}, machine=None))
    return recipes, hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stack_key(s, exact=False):
    """An exported stack: meta 32767 is the wildcard (any variant). As an output, meta 0 is the plain item; as an exact
    input (exact=True) it is variant 0, which a variant 5 of the same item does not satisfy."""
    if s.get('meta') == WILDCARD:
        return s['id']
    if not s.get('meta') and not exact:
        return s['id']
    return '%s@%s' % (s['id'], s.get('meta') or 0)


def crucible_recipes(path, export):
    """Melting and casting from the executor's crucible export, alloys from the machine export's _hbmCrucible.json."""
    recipes = []
    if export and (Path(export) / '_hbmCrucible.json').is_file():
        alloys = Path(export) / '_hbmCrucible.json'
        for r in json.loads(alloys.read_text(encoding='utf-8')).get('recipes', []):
            recipes.append(dict(kind='crucible alloy', name='_hbmCrucible.json#%s' % r.get('name'), origin=common.rel(alloys),
                                inputs=[{'material:' + m[0]} for m in r.get('input', [])],
                                outputs={'material:' + m[0] for m in r.get('output', [])}, machine=CRUCIBLE))
    if not path:
        return recipes, None
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    origin = common.rel(Path(path))
    for r in data.get('smelting', []):
        item = stack_key(r['item'], exact=True)
        recipes.append(dict(kind='crucible melting', name='melting %s' % item, origin=origin, inputs=[{item}],
                            outputs={'material:' + m[0] for m in r['materials']}, machine=CRUCIBLE))
    for c in data.get('casts', []):
        recipes.append(dict(kind='cast', name='cast %s' % c['material'], origin=origin, inputs=[{'material:' + c['material']}],
                            outputs={stack_key(c['output'])}, machine=c['mold']))
    return recipes, hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expand(tags, alternatives):
    out = set()
    for a in alternatives:
        out |= (resolve_tag(tags, a[1:]) or {a}) if a.startswith('#') else {a}
    return out


def worldgen_sources(data, defaults=None):
    """{block id: [source, ...]} for blocks the world generator places, each source a dict: placed feature, the biome
    modifier or biome naming it with its biomes, the config gates with their defaults, `on` (all gates on by default),
    and the code line for features that place blocks in code."""
    defaults = config_defaults() if defaults is None else defaults
    refs = {}
    for kind, entries in (('biome_modifier', data.under('neoforge/biome_modifier')), ('biome', data.under('worldgen/biome'))):
        for name, (m, origin) in entries.items():
            if isinstance(m, dict) and m.get('type') == 'neoforge:remove_features':
                continue
            gates = [(k, defaults.get(k)) for k in (m.get('config') or [])] if isinstance(m, dict) \
                and m.get('type') == 'hbmsntm:config_gated_add_features' else []
            biomes = m.get('biomes') if isinstance(m, dict) and kind == 'biome_modifier' else name
            for s in collect_strings(m):
                if ':' in s:
                    refs.setdefault(s, []).append(dict(via=origin, biomes=biomes if isinstance(biomes, str) else json.dumps(biomes), gates=gates))
    placed = data.under('worldgen/placed_feature')
    configured = data.under('worldgen/configured_feature')
    out = {}
    for pname, (p, origin) in placed.items():
        if pname not in refs:
            continue
        counts = [(m['config'], defaults.get(m['config'])) for m in p.get('placement', [])
                  if isinstance(m, dict) and m.get('type') in ('hbmsntm:config_count', 'hbmsntm:config_rarity')]
        feature = p.get('feature')
        cf = configured.get(feature)[0] if isinstance(feature, str) and feature in configured else feature
        blocks = [(s, None) for s in states(cf)]
        if isinstance(cf, dict) and cf.get('type') in CODE_FEATURES:
            blocks += CODE_FEATURES[cf['type']]
        for ref in refs[pname]:
            gates = ref['gates'] + counts
            on = all(bool(v) for k, v in gates)
            for block, where in blocks:
                out.setdefault(block, []).append(dict(feature=pname, origin=origin, via=ref['via'], biomes=ref['biomes'],
                                                      gates=[list(g) for g in gates], on=on, code=where))
    return out


def collect_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for c in node:
            yield from collect_strings(c)
    elif isinstance(node, dict):
        for c in node.values():
            yield from collect_strings(c)


def states(node):
    """Block names of every block state in a configured feature (ore targets, state providers)."""
    if isinstance(node, dict):
        if 'Name' in node and isinstance(node['Name'], str):
            yield node['Name']
        for k, c in node.items():
            if k not in ('target', 'predicate'):  # the block an ore replaces is not placed
                yield from states(c)
    elif isinstance(node, list):
        for c in node:
            yield from states(c)


def loot_items(table):
    found = set()

    def walk(n):
        if isinstance(n, dict):
            if n.get('type') == 'minecraft:item' and 'name' in n:
                metas = [f.get('components', {}).get('hbmsntm:meta') for f in n.get('functions', [])
                         if isinstance(f, dict) and f.get('function') == 'minecraft:set_components']
                metas = [m for m in metas if isinstance(m, int)]
                found.add('%s@%s' % (n['name'], metas[-1]) if metas else variant(n['name']) if n['name'] in DEFAULT_META else n['name'])
            for c in n.values():
                walk(c)
        elif isinstance(n, list):
            for c in n:
                walk(c)
    walk(table)
    return found


def closure(targets, export, anvil=None, data=None, crucible=None, machines=None, sources=None, defaults=None, containers=False):
    data = data or Data().load()
    tags = data.tags()
    recipes = crafting_recipes(data, tags)
    mrecipes, export_files = machine_recipes(export, tags)
    recipes += mrecipes
    arecipes, anvil_hash = anvil_recipes(anvil)
    recipes += arecipes
    crecipes, crucible_hash = crucible_recipes(crucible, export)
    recipes += crecipes
    xrecipes, machines_hash = executor_machine_recipes(machines)
    recipes += xrecipes
    precipes, sources_hash = process_recipes(sources)
    recipes += precipes
    if containers:
        recipes += container_recipes()
    pools = sorted({a[len('blueprint:'):] for r in recipes for alts in r['inputs'] for a in alts if a.startswith('blueprint:')})
    recipes += blueprint_recipes(pools)
    known = {base(o) for r in recipes for o in r['outputs']}
    for r in recipes:
        r['inputs'] = [({i for i in known if i.startswith('hbmsntm:stamp_') and i.endswith('_' + next(iter(alts))[6:])}
                        or alts) if len(alts) == 1 and next(iter(alts)).startswith('stamp:') else alts for alts in r['inputs']]
    loot = data.under('loot_table')
    how, order = {}, {}

    def give(item, reason):
        if item not in how:
            how[item] = reason
            order[item] = len(order)
            if '@' in item and base(item) not in how:
                how[base(item)] = reason
            if variant(item) not in how:
                how[variant(item)] = reason  # a stack without the meta component is the default variant

    gen = worldgen_sources(data, defaults)
    off = {}
    for block, found in gen.items():
        live = [f for f in found if f['on']]
        if not live:
            off[block] = found
            continue
        give('block:' + block, dict(kind='worldgen', block=block, features=sorted({f['feature'] for f in live})[:3],
                                    code=next((f['code'] for f in live if f['code']), None), loot=None))
        table = loot.get('%s:blocks/%s' % tuple(block.split(':', 1)))
        drops = loot_items(table[0]) if table else ({block} if block.startswith('minecraft:') else set())
        for item in drops:
            give(item, dict(kind='worldgen', block=block, features=sorted({f['feature'] for f in live})[:3],
                            code=next((f['code'] for f in live if f['code']), None), loot=table[1] if table else None))
    for name, (table, origin) in loot.items():
        if '/chests/' in name.replace(':', '/') or '/entities/' in name.replace(':', '/'):
            for item in loot_items(table):
                give(item, dict(kind='loot', table=name, origin=origin))

    def have(item):
        return item in how or base(item).startswith('minecraft:') or (('@' not in item) and any(k.startswith(item + '@') for k in how))

    def machine_ok(r):
        if r.get('unknown_machine'):
            return False  # a table MACHINES does not name: its machine is unknown, so it is no source
        ms = machines_of(r['machine'])
        return not ms or any(have(m) for m in ms)

    changed = True
    while changed:
        changed = False
        for r in recipes:
            if all(o in how for o in r['outputs']):
                continue
            if not machine_ok(r):
                continue
            if all(any(have(a) for a in alts) for alts in r['inputs']):
                for o in r['outputs']:
                    if o not in how:
                        give(o, dict(kind=r['kind'], recipe=r['name'], origin=r['origin'], machine=r['machine'],
                                     inputs=[sorted(a) for a in r['inputs']]))
                        changed = True

    def reason_of(item):
        return how.get(item) or how.get(base(item)) or how.get(variant(item)) or \
            (next((how[k] for k in sorted(how) if k.startswith(item + '@')), None) if '@' not in item else None)

    def when(item):
        """When the fixpoint first had item (-1 for vanilla): picking the earliest alternative keeps chains acyclic."""
        keys = [item, base(item), variant(item)] + ([k for k in how if k.startswith(item + '@')] if '@' not in item else [])
        found = [order[k] for k in keys if k in order]
        if found:
            return min(found)
        return -1 if base(item).startswith('minecraft:') else None

    def pick(alts):
        ranked = sorted((when(a), a) for a in alts if when(a) is not None)
        return ranked[0][1] if ranked else sorted(alts)[0]

    def machine_pick(reason):
        ms = [m for m in machines_of(reason.get('machine')) if have(m)]
        return [pick(set(ms))] if ms else []

    def chain(item, depth, seen):
        reason = reason_of(item)
        if base(item).startswith('minecraft:') and not reason:
            return dict(item=item, kind='vanilla')
        if not reason:
            return dict(item=item, kind='none')
        node = dict(item=item, **{k: v for k, v in reason.items() if k != 'inputs'})
        if depth > 0 and 'inputs' in reason and item not in seen:
            node['from'] = [chain(pick(alts), depth - 1, seen | {item}) for alts in reason['inputs']]
            node['from'] += [chain(m, depth - 1, seen | {item}) for m in machine_pick(reason)]
        return node

    deps_memo = {}

    def deps(item):
        """Every item, fluid or material the chosen source chain of item goes through (machines included); the earliest
        alternative is always picked, so the chain only goes back in the fixpoint's order and cannot loop."""
        if item in deps_memo:
            return deps_memo[item]
        deps_memo[item] = set()  # guard; never hit while picks go strictly back in order
        reason = reason_of(item)
        out = set()
        if reason:
            for d in [pick(alts) for alts in reason.get('inputs', [])] + machine_pick(reason):
                out.add(d)
                out |= deps(d)
        deps_memo[item] = out
        return out

    report = []
    for t in targets:
        if have(t):
            report.append(dict(item=t, obtainable=True, chain=chain(t, 6, frozenset())))
        else:
            missing = []
            for r in recipes:
                if t in r['outputs'] or base(t) in {base(o) for o in r['outputs']}:
                    missing.append(dict(recipe=r['name'], machine=r['machine'],
                                        machine_missing=not machine_ok(r),
                                        missing=[sorted(a)[:4] for a in r['inputs'] if not any(have(x) for x in a)]))
            entry = dict(item=t, obtainable=False, recipes_without_sources=missing[:5])
            if t in off or base(t) in off:
                entry['worldgen_off_by_default'] = off.get(t) or off.get(base(t))
            report.append(entry)
    unknown = sorted({r['origin'] for r in recipes if r.get('unknown_machine')})
    return dict(targets=report, recipe_count=len(recipes), machine_recipe_count=len(mrecipes), anvil_recipe_count=len(arecipes),
                worldgen_blocks=len(gen), worldgen_off_by_default=sorted(off), export=common.rel(Path(export)) if export else None,
                export_files=export_files, tables_without_machine=unknown,
                anvil_export=common.rel(Path(anvil)) if anvil else None, anvil_export_sha256=anvil_hash,
                crucible_recipe_count=len(crecipes), crucible_export=common.rel(Path(crucible)) if crucible else None,
                crucible_export_sha256=crucible_hash, executor_machine_recipe_count=len(xrecipes),
                machines_export=common.rel(Path(machines)) if machines else None, machines_export_sha256=machines_hash,
                pooled_recipe_count=sum(1 for r in recipes if any(a.startswith('blueprint:') for alts in r['inputs'] for a in alts)),
                process_source_count=len(precipes), sources=common.rel(Path(sources)) if sources else None, sources_sha256=sources_hash,
                _deps=deps, _have=have, _worldgen=gen, _recipes=recipes, _how=how)


def summary(report):
    """A readable summary of the mainline report."""
    m = report['mainline']
    out = ['# Mainline closure', '',
           'Inputs: %s; machine export %s; anvil %s; crucible %s; executor machines %s; process sources %s; export build %s.' % (
               report['mainline_inputs']['items'], report['export'], report['anvil_export'], report['crucible_export'],
               report['machines_export'], report['sources'], report['export_build']), '',
           'Obtainable %(obtainable)d, mainline gaps %(gap)d, outside the mainline %(outside)d.' % m['counts'], '']
    out += ['Attribution warning: ' + w for w in m.get('attribution_warnings', [])] + ([''] if m.get('attribution_warnings') else [])
    for n, g in m['stages'].items():
        out += ['## Stage %s: %s' % (n, g['title']), '']
        for i in g['items']:
            e = m['items'][i]
            if e['result'] == 'obtainable':
                c = e['chain']
                out.append('- %s: obtainable (%s%s)' % (i, c['kind'], ' ' + (c.get('recipe') or c.get('block') or c.get('table') or '')))
            elif e['result'] == 'outside':
                out.append('- %s: outside the mainline, %s%s' % (i, e['attribution']['category'],
                                                                 ' (%s)' % e['attribution']['note'] if e['attribution'].get('note') else ''))
            else:
                miss = [x for r in e['recipes_without_sources'] for alts in r['missing'] for x in alts[:2]]
                out.append('- %s: **GAP**%s' % (i, ', missing ' + ', '.join(sorted(set(miss))[:6]) if miss else ', no recipe or source'))
        given = m['stage_start_items'].get(n) or []
        if given:
            out += ['', 'Handed out at the start: ' + ', '.join('%s (stage %s)' % (g['item'], g['from_stage']) for g in given)]
        out.append('')
    return '\n'.join(out)


def text_chain(node, indent=0):
    pad = '  ' * indent
    k = node['kind']
    if k == 'vanilla':
        line = '%s%s: vanilla' % (pad, node['item'])
    elif k == 'none':
        line = '%s%s: NO SOURCE' % (pad, node['item'])
    elif k == 'worldgen':
        line = '%s%s: world generation, block %s (%s)%s' % (pad, node['item'], node['block'], ', '.join(node['features']),
                                                           ', placed in code at ' + node['code'] if node.get('code') else '')
    elif k == 'loot':
        line = '%s%s: loot table %s' % (pad, node['item'], node['table'])
    else:
        ms = machines_of(node.get('machine'))
        line = '%s%s: %s %s%s%s' % (pad, node['item'], k, node['recipe'], ' in ' + ' or '.join(ms) if ms else '',
                                     ' (%s)' % node['origin'] if k == 'process' else '')
    lines = [line]
    for child in node.get('from', []):
        lines += text_chain(child, indent + 1)
    return lines


# The only "outside the mainline" categories (GOAL32 decision 3 and the user's Goal32A decisions of 2026-11-14 on the closure
# gaps); anything else is a gap until the user decides otherwise.
OUTSIDE = {
    'rbmk-spent-pellets': 'RBMK spent fuel ends at the pellets (no consumer in NEO; the original uses them only in the SILEX)',
    'spent-fuel-isotopes': 'isotopes the original only extracts from spent fuel (SILEX, PUREX of plate, PWR and Watz fuel): americium, plutonium-240 and -241',
    'bismuth': 'bismuth, which the original gets from machines and systems NEO lacks (SILEX, PUREX of PWR and Watz fuel, storage drum decay, bedrock ores)',
    'nether-plutonium-off': 'the nether plutonium ore is off by default (original GeneralConfig.java:99)',
    'polonium': 'polonium, which the original gets from machines and systems NEO lacks (cyclotron, SILEX, PUREX of pile, plate and Watz fuel, electrolyser, bedrock ores)',
    'special-fuels': 'special fuels such as australium and flashgold, each needing a new machine or system',
    'saturnite-pink-absorber': 'the saturnite ingot and the pink radiation absorber block',
    'mode-528': 'differences that only exist in 528 mode',
}


def mainline(result, stages, attribution):
    """The mainline report: every item obtainable (with its chain), a mainline gap, or outside the mainline (by the
    attribution table only). stages: {"<n>": {"title": ..., "ids": [...]}} (the planning checkpoints); an item not listed
    there goes to the earliest stage after which its sources allow it (earliest_stage, counted from the checkpoints), at
    least the first. Every item also gets needs_stage: the earliest stage its own sources need."""
    deps, have, gen = result['_deps'], result['_have'], result['_worldgen']
    targets = {t['item']: t for t in result['targets']}
    order = sorted(stages, key=int)
    stage_of, how_staged = {}, {}
    for n in order:
        for i in stages[n]['ids']:
            if i in targets and i not in stage_of:
                stage_of[i], how_staged[i] = int(n), 'checkpoint'
    checkpoints = dict(stage_of)
    after = earliest_stage(result, checkpoints)
    for i in targets:
        if i not in stage_of:
            stage_of[i], how_staged[i] = max(after.get(i) or 0, int(order[0])), 'earliest its sources allow'
    bad = {i: a for i, a in attribution.items() if a.get('category') not in OUTSIDE}
    if bad:
        raise SystemExit('attribution categories outside OUTSIDE: %s' % sorted(bad))
    warnings = ['%s is attributed but not in the item list' % i for i in sorted(set(attribution) - set(targets))]
    warnings += ['%s is attributed outside the mainline but obtainable' % i for i in sorted(attribution) if targets.get(i, {}).get('obtainable')]
    items = {}
    counts = {'obtainable': 0, 'gap': 0, 'outside': 0}
    for i, t in targets.items():
        if i in attribution:
            res = 'outside'
        else:
            res = 'obtainable' if t['obtainable'] else 'gap'
        counts[res] += 1
        e = dict(stage=stage_of[i], staged=how_staged[i], result=res)
        if res == 'outside':
            e['attribution'] = dict(attribution[i], category_text=OUTSIDE[attribution[i]['category']])
            e['obtainable'] = t['obtainable']
        if t['obtainable']:
            e['chain'] = t['chain']
        else:
            e['recipes_without_sources'] = t['recipes_without_sources']
            if 'worldgen_off_by_default' in t:
                e['worldgen_off_by_default'] = t['worldgen_off_by_default']
        items[i] = e
    # handoff 1: what each stage's scene may hand out at its start (items of earlier stages its own items need)
    given = {}
    for i, e in items.items():
        if e['result'] != 'obtainable':
            continue
        for d in deps(i):
            if d in stage_of and stage_of[d] < e['stage']:
                given.setdefault(str(e['stage']), {}).setdefault(d, stage_of[d])
    # handoff 2: the blocks world generation places, with where they come from and their config gates
    blocks = []
    for block, found in sorted(gen.items()):
        for f in found:
            blocks.append(dict(block=block, biomes=f['biomes'], feature=f['feature'], placed_feature=f['origin'], via=f['via'],
                               code=f['code'], gates=f['gates'], on_by_default=f['on']))
    groups = {n: dict(title=stages[n]['title'], items=sorted(i for i in items if items[i]['stage'] == int(n))) for n in order}
    for i, e in items.items():
        if i in after:
            e['needs_stage'] = after[i]
    return dict(counts=counts, attribution_warnings=warnings, stages=groups, items=items,
                stage_start_items={n: [dict(item=k, from_stage=v) for k, v in sorted(given.get(n, {}).items())] for n in order},
                worldgen_blocks=blocks)


def earliest_stage(result, stage_of):
    """{item: n}: the earliest stage after whose items it can be made, over every source (not only the chain picked): a
    mainline item stands for its stage, a source needs the latest stage among its inputs and machine, and an item takes its
    best source. Free sources (world generation, loot, vanilla) are stage 0."""
    how = result['_how']
    best = {k: 0 for k, r in how.items() if r.get('kind') in ('worldgen', 'loot')}

    def level(x):
        if x in stage_of:
            return stage_of[x]
        if base(x).startswith('minecraft:') and x not in best:
            return 0
        found = [best[k] for k in (x, base(x), variant(x)) if k in best]
        if '@' not in x:
            found += [v for k, v in best.items() if k.startswith(x + '@')]
        return min(found) if found else None

    changed = True
    while changed:
        changed = False
        for r in result['_recipes']:
            ms = machines_of(r['machine'])
            mlev = [level(m) for m in ms if level(m) is not None]
            if ms and not mlev:
                continue
            lev = [min([level(a) for a in alts if level(a) is not None], default=None) for alts in r['inputs']]
            if any(v is None for v in lev):
                continue
            v = max(lev + ([min(mlev)] if mlev else []) + [0])
            for o in r['outputs']:
                if o not in best or v < best[o]:
                    best[o] = v
                    changed = True
    names = set(stage_of) | {o for r in result['_recipes'] for o in r['outputs']} | set(how)
    out = {}
    for i in names:
        found = [best[k] for k in (i, base(i), variant(i)) if k in best]
        if found:
            out[i] = min(found)
    return out


def public(report):
    """The report without the closure's helper functions (keys starting with _)."""
    return {k: v for k, v in report.items() if not k.startswith('_')}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('items', nargs='*')
    ap.add_argument('--items-file')
    ap.add_argument('--recipes-export', help='a config/hbmRecipes directory written by a game run')
    ap.add_argument('--anvil-export', help='exports/anvil.json written by the executor\'s export step')
    ap.add_argument('--crucible-export', help='exports/crucible.json written by the executor\'s export step (kind crucible)')
    ap.add_argument('--machines-export', help='exports/machines.json written by the executor\'s export step (kind machines)')
    ap.add_argument('--sources', default=common.rel(SOURCES), help='the hand-written process sources (default: %(default)s)')
    ap.add_argument('--export-build', help='text recorded as the build that wrote the export (default: the current build/libs jar hash)')
    ap.add_argument('--json', help='write the full report here')
    ap.add_argument('--stages', help='mainline mode: {"<n>": {"title", "ids"}} of the stage checkpoints')
    ap.add_argument('--attribution', help='mainline mode: {item: {"category", "note"}} for the items outside the mainline')
    ap.add_argument('--summary', help='mainline mode: write a readable summary (Markdown) here')
    args = ap.parse_args(argv)
    items = list(args.items)
    if args.items_file:
        items += [l.strip() for l in Path(args.items_file).read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')]
    if not items:
        raise SystemExit('no items')
    export = common.resolve(args.recipes_export) if args.recipes_export else None
    if export and not export.is_dir():
        raise SystemExit('no export directory ' + str(export))
    anvil = common.resolve(args.anvil_export) if args.anvil_export else None
    crucible = common.resolve(args.crucible_export) if args.crucible_export else None
    machines = common.resolve(args.machines_export) if args.machines_export else None
    sources = common.resolve(args.sources) if args.sources else None
    result = closure(items, export, anvil, crucible=crucible, machines=machines, sources=sources, containers=True)
    report = public(result)
    if args.stages:
        attribution = json.loads(common.resolve(args.attribution).read_text(encoding='utf-8')) if args.attribution else {}
        report['mainline'] = mainline(result, json.loads(common.resolve(args.stages).read_text(encoding='utf-8')), attribution)
        report['mainline_inputs'] = dict(items=args.items_file, stages=args.stages, attribution=args.attribution)
    jars = sorted((REPO / 'build' / 'libs').glob('*.jar'))
    report['export_build'] = args.export_build or ('build/libs %s sha256 %s' % (jars[0].name, common.sha256(jars[0])) if jars else 'unknown')
    for t in report['targets']:
        if t['obtainable']:
            print('\n'.join(text_chain(t['chain'])))
        else:
            print('%s: NO SURVIVAL SOURCE; recipes with missing inputs: %s' % (t['item'], json.dumps(t['recipes_without_sources'])[:500]))
    print('-- %d recipes (%d machine recipes from %s, %d anvil recipes from %s, %d crucible recipes from %s, %d from %s, %d process '
          'sources from %s), %d world-generated blocks (off by default: %s); tables without a machine: %s; export build: %s' % (
              report['recipe_count'], report['machine_recipe_count'], report['export'], report['anvil_recipe_count'], report['anvil_export'],
              report['crucible_recipe_count'], report['crucible_export'], report['executor_machine_recipe_count'], report['machines_export'],
              report['process_source_count'], report['sources'], report['worldgen_blocks'], ', '.join(report['worldgen_off_by_default']) or '-',
              ', '.join(report['tables_without_machine']) or '-', report['export_build']))
    if args.json:
        common.write_json(common.resolve(args.json), report)
    if args.summary and 'mainline' in report:
        common.resolve(args.summary).write_text(summary(report), encoding='utf-8', newline='\n')
    if 'mainline' in report:
        return 0 if report['mainline']['counts']['gap'] == 0 else 1
    return 0 if all(t['obtainable'] for t in report['targets']) else 1


if __name__ == '__main__':
    sys.exit(main())
