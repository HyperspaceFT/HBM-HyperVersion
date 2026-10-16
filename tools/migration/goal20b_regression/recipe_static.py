"""Goal20B static recipe/resource evidence: the original ass.gascent, pseudo-fluid table and language lines (read-only), the production
GasCentrifugeRecipes source, the provider/registration edits against the frozen Goal20B start, the language files and mapping, the imported
assets and the generated files runData publishes. Every check takes a `ck(condition, label)` so the static mutations of
verify_goal20b_recipes.py can run the same function on an edited copy and expect its AssertionError."""
from pathlib import Path
import difflib, hashlib, json, re, struct

ORIGINAL_ASSEMBLY = 'src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
ORIGINAL_GASCENT = 'src/main/java/com/hbm/inventory/recipes/GasCentrifugeRecipes.java'
ORIGINAL_ROD_RECIPES = 'src/main/java/com/hbm/crafting/RodRecipes.java'
ORIGINAL_CRAFTING = 'src/main/java/com/hbm/main/CraftingManager.java'
ORIGINAL_UPGRADE = 'src/main/java/com/hbm/items/machine/ItemMachineUpgrade.java'
ORIGINAL_NEI = 'src/main/java/com/hbm/handler/nei/GasCentrifugeRecipeHandler.java'
ORIGINAL_ZIRNOX_ROD = 'src/main/java/com/hbm/items/machine/ItemZirnoxRod.java'
ORIGINAL_EN = 'src/main/resources/assets/hbm/lang/en_US.lang'
ORIGINAL_ZH = 'src/main/resources/assets/hbm/lang/zh_CN.lang'
ORIGINAL_FILES = (ORIGINAL_ASSEMBLY, ORIGINAL_GASCENT, ORIGINAL_ROD_RECIPES, ORIGINAL_CRAFTING, ORIGINAL_UPGRADE, ORIGINAL_NEI, ORIGINAL_ZIRNOX_ROD, ORIGINAL_EN, ORIGINAL_ZH)

# The five original normal inputs of ass.gascent -> (kind, NEO field or tag id, stand-in id).
GASCENT_INPUTS = {
    'ComparableStack(ModItems.centrifuge_element': ('item', 'CENTRIFUGE_ELEMENT'),
    'OreDictStack(ANY_PLASTIC.ingot()': ('tag', 'ntm:ingots_plastic'),
    'OreDictStack(DESH.ingot()': ('item', 'INGOT_DESH'),
    'OreDictStack(STEEL.plate()': ('tag', 'c:plates/steel'),
    'ComparableStack(ModItems.circuit+ADVANCED': ('item', 'CIRCUIT_MILITARY_GRADE_BOARD'),
}
WILDCARD = 32767

# The fifteen Goal20B language keys: key -> (kind, original key or None, local English when the original text is hardcoded).
LANG_KEYS = {
    'block.hbmsntm.machine_gas_centrifuge': ('upstream', 'tile.machine_gascent.name'),
    'container.machine_gas_centrifuge': ('upstream', 'container.gasCentrifuge'),
    'desc.gui.gasCent.enrichment': ('upstream', 'desc.gui.gasCent.enrichment'),
    'desc.gui.gasCent.output': ('upstream', 'desc.gui.gasCent.output'),
    'hbmpseudofluid.none': ('upstream', 'hbmpseudofluid.none'),
    'hbmpseudofluid.heuf6': ('upstream', 'hbmpseudofluid.heuf6'),
    'hbmpseudofluid.meuf6': ('upstream', 'hbmpseudofluid.meuf6'),
    'hbmpseudofluid.leuf6': ('upstream', 'hbmpseudofluid.leuf6'),
    'hbmpseudofluid.nuf6': ('upstream', 'hbmpseudofluid.nuf6'),
    'hbmpseudofluid.pf6': ('upstream', 'hbmpseudofluid.pf6'),
    'hbmpseudofluid.mud_heavy': ('upstream', 'hbmpseudofluid.mud_heavy'),
    'hbmpseudofluid.mud': ('upstream', 'hbmpseudofluid.mud'),
    'item.hbmsntm.upgrade_gc_speed': ('upstream', 'item.upgrade_gc_speed.name'),
    'item.hbmsntm.upgrade_gc_speed.desc': ('local', None),
    'gas_centrifuge.jei.cascade': ('local', None),
}
# The two local keys: the exact English and Chinese, and the original hardcoded source lines they replace.
LOCAL_TEXT = {
    'item.hbmsntm.upgrade_gc_speed.desc': ('§cGas Centrifuge Upgrade$Allows for total isotopic separation of HEUF6$§ealso your centrifuge goes sicko mode',
                                           '§c气体离心机升级$允许对高浓缩六氟化铀进行完全的同位素分离$§e同时你的离心机会进入狂暴模式'),
    'gas_centrifuge.jei.cascade': ('%s G. Cents', '%s 台气体离心机'),
}
TOTALS = {'en': 2344, 'zh': 2236, 'map': 2344, 'deferred': 108}

# Imported assets: NEO path under assets/hbmsntm -> original path under assets/hbm.
ASSETS = {
    'models/obj/machines/gas_centrifuge.obj': 'models/machines/gascent.obj',
    'textures/models/machines/gas_centrifuge.png': 'textures/models/machines/gascent.png',
    'textures/block/machine_gas_centrifuge.png': 'textures/blocks/machine_gascent.png',
    'textures/gui/processing/gui_centrifuge_gas.png': 'textures/gui/processing/gui_centrifuge_gas.png',
    'textures/item/upgrade_gc_speed.png': 'textures/items/upgrade_gc_speed.png',
    'textures/gui/jei/gui_nei_centrifuge_gas.png': 'textures/gui/nei/gui_nei_centrifuge_gas.png',
}

# Production files edited by Goal20B (outside the new classes) -> the lines the edit must insert (stripped), nothing else may change.
PROVIDER_EDITS = {
    'com/hbm/datagen/NtmBlockStateProvider.java': ['this.particleOnlyBlock(NtmBlocks.MACHINE_GAS_CENTRIFUGE, modLoc("block/block_steel"));'],
    'com/hbm/datagen/NtmItemModelProvider.java': ['this.handheldItem(NtmItems.UPGRADE_GC_SPEED.get());'],
    'com/hbm/datagen/NtmBlockLootTableProvider.java': ['this.dropSelf(NtmBlocks.MACHINE_GAS_CENTRIFUGE.get());'],
    'com/hbm/datagen/NtmBlockTagProvider.java': ['NtmBlocks.MACHINE_GAS_CENTRIFUGE.get(),'],
    'com/hbm/inventory/NtmCreativeTabs.java': ['output.accept(NtmItems.UPGRADE_GC_SPEED);', 'output.accept(NtmBlocks.MACHINE_GAS_CENTRIFUGE);'],
    'com/hbm/blocks/NtmBlocks.java': ['public static final DeferredBlock<Block> MACHINE_GAS_CENTRIFUGE = register("machine_gas_centrifuge", () -> new MachineGasCentrifugeBlock('
                                      'BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.METAL).mapColor(MapColor.METAL)));'],
    'com/hbm/items/NtmItems.java': ['public static final DeferredItem<Item> UPGRADE_GC_SPEED = ITEMS.register("upgrade_gc_speed", () -> new MachineUpgradeItem(new Item.Properties(), '
                                    'MachineUpgradeItem.UpgradeType.GS_SPEED));'],
    'com/hbm/blockentity/NtmBlockEntityTypes.java': ['public static final Supplier<BlockEntityType<MachineGasCentrifugeBlockEntity>> MACHINE_GAS_CENTRIFUGE = BLOCK_ENTITY_TYPES.register(',
                                                     '"machine_gas_centrifuge",', 'MachineGasCentrifugeBlockEntity::new,', 'NtmBlocks.MACHINE_GAS_CENTRIFUGE.get())'],
    'com/hbm/inventory/NtmMenuTypes.java': ['public static final DeferredHolder<MenuType<?>, MenuType<MachineGasCentrifugeMenu>> MACHINE_GAS_CENTRIFUGE = reg("machine_gas_centrifuge", '
                                            'MachineGasCentrifugeMenu::new);'],
    'com/hbm/main/CommonEvents.java': ['import com.hbm.inventory.recipes.GasCentrifugeRecipes;', 'GasCentrifugeRecipes.register();'],
    # The screen is registered from the client-only entry point, so the dedicated server never loads the screen class.
    'com/hbm/main/NuclearTechModClient.java': ['import com.hbm.inventory.screens.MachineGasCentrifugeScreen;',
                                               'event.register(NtmMenuTypes.MACHINE_GAS_CENTRIFUGE.get(), MachineGasCentrifugeScreen::new);'],
    'com/hbm/datagen/NtmRecipeProvider.java': ['ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.UPGRADE_GC_SPEED.get(), 1)', '.pattern("GNG")', '.pattern("RUR")', '.pattern("GMG")',
                                               ".define('G', NtmItems.COIL_GOLD.get())", ".define('N', NtmItems.INGOT_NIOBIUM.get())", ".define('R', NtmItems.INGOT_RUBBER.get())",
                                               ".define('U', NtmItems.UPGRADE_TEMPLATE.get())", ".define('M', NtmItems.MOTOR.get())",
                                               '.save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "upgrade_gc_speed"));',
                                               'ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.URANIUM_FUEL.ordinal()))',
                                               '.requires(NtmItems.BILLET_URANIUM_FUEL.get(), 2)',
                                               'ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.U235_FUEL.ordinal()))',
                                               '.requires(NtmItems.BILLET_U235.get(), 2)'],
}

GENERATED = {
    'upgrade': 'data/hbmsntm/recipe/upgrade_gc_speed.json',
    'rod_uranium': 'data/hbmsntm/recipe/rod_zirnox_uranium_fuel.json',
    'rod_u235': 'data/hbmsntm/recipe/rod_zirnox_u235_fuel.json',
    'adv_upgrade': 'data/hbmsntm/advancement/recipes/misc/upgrade_gc_speed.json',
    'adv_rod_uranium': 'data/hbmsntm/advancement/recipes/misc/rod_zirnox_uranium_fuel.json',
    'adv_rod_u235': 'data/hbmsntm/advancement/recipes/misc/rod_zirnox_u235_fuel.json',
    'blockstate': 'assets/hbmsntm/blockstates/machine_gas_centrifuge.json',
    'particle_model': 'assets/hbmsntm/models/block/machine_gas_centrifuge_particle.json',
    'block_item_model': 'assets/hbmsntm/models/item/machine_gas_centrifuge.json',
    'upgrade_item_model': 'assets/hbmsntm/models/item/upgrade_gc_speed.json',
    'loot': 'data/hbmsntm/loot_table/blocks/machine_gas_centrifuge.json',
    'pickaxe': 'data/minecraft/tags/block/mineable/pickaxe.json',
    'en_us': 'assets/hbmsntm/lang/en_us.json',
}


def read(path): return Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n')
def lf(text): return text.replace('\r\n', '\n')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def quiet(condition, label):
    if not condition: raise AssertionError(label)


def registrations(source_root):
    """field -> registered id for NtmItems and NtmBlocks (register / registerNugget style declarations)."""
    items = (source_root / 'com/hbm/items/NtmItems.java').read_text(encoding='utf-8')
    blocks = (source_root / 'com/hbm/blocks/NtmBlocks.java').read_text(encoding='utf-8')
    return ({m.group(1): m.group(2) for m in re.finditer(r'\b([A-Z][A-Z0-9_]*)\s*=\s*(?:ITEMS\.)?register\w*\("([a-z0-9_]+)"', items)},
            {m.group(1): m.group(2) for m in re.finditer(r'\b([A-Z][A-Z0-9_]*)\s*=\s*register\w*\("([a-z0-9_]+)"', blocks)})


def line_of(text, needle):
    lines = [i + 1 for i, l in enumerate(text.split('\n')) if needle in l]
    if len(lines) != 1: raise AssertionError(f'{needle!r} found on {len(lines)} lines (need 1)')
    return lines[0]


# ---- (a) assembly ----------------------------------------------------------------------------------------------------------------------

def parse_original_gascent(source, items, blocks):
    text = read(source / ORIGINAL_ASSEMBLY)
    lines = text.split('\n')
    first = next(i for i, l in enumerate(lines) if 'new GenericRecipe("ass.gascent")' in l)
    assert text.count('"ass.gascent"') == 1 and '.inputItems(' in lines[first + 1] and '.inputItemsEx(' in lines[first + 2], 'original ass.gascent statement not found in the expected shape'
    previous = next(i for i, l in enumerate(lines) if 'new GenericRecipe("ass.centrifuge")' in l)
    setup = re.search(r'\.setup\((\d+), (\d+)\)', lines[first]); output = re.search(r'new ItemStack\(ModBlocks\.(\w+), (\d+)\)', lines[first])
    assert setup and output and output.group(1) == 'machine_gascent', 'original setup/output not recognised'
    inputs = []
    for kind, inner in re.findall(r'new (ComparableStack|OreDictStack)\(([^()]*(?:\([^()]*\))?[^()]*(?:\([^()]*\))?)\)', lines[first + 1]):
        parts = [p.strip() for p in inner.split(',')]
        key = f'{kind}({parts[0]}' + ('+ADVANCED' if len(parts) > 2 and 'EnumCircuitType.ADVANCED' in parts[2] else '')
        if key not in GASCENT_INPUTS: raise AssertionError('unmapped original ass.gascent input: ' + key)
        nkind, target = GASCENT_INPUTS[key]
        row = {'original': f'{kind}({inner})', 'original_kind': kind, 'kind': nkind, 'count': int(parts[1]), 'meta': WILDCARD if nkind == 'item' else 0}
        if nkind == 'item':
            if target not in items: raise AssertionError(f'Production registration of {target} not found')
            row.update(field=target, id='hbmsntm:' + items[target], stub_id='hbmsntm:' + target.lower())
        else:
            row.update(id=target, stub_id=target)
        inputs.append(row)
    if 'MACHINE_GAS_CENTRIFUGE' not in blocks: raise AssertionError('Production registration of MACHINE_GAS_CENTRIFUGE not found')
    return {'name': 'ass.gascent', 'source': f'{ORIGINAL_ASSEMBLY}:{first + 1}-{first + 2}', 'source_lines': [lines[first].strip(), lines[first + 1].strip()],
            'previous_row': {'name': 'ass.centrifuge', 'line': previous + 1}, 'duration': int(setup.group(1)), 'power': int(setup.group(2)), 'inputs': inputs,
            'output': {'original': output.group(1), 'field': 'MACHINE_GAS_CENTRIFUGE', 'id': 'hbmsntm:' + blocks['MACHINE_GAS_CENTRIFUGE'], 'stub_id': 'hbmsntm:machine_gas_centrifuge',
                       'count': int(output.group(2))},
            'input_items_ex': lines[first + 2].strip(), 'pool_528': lines[first + 3].strip() if 'setPools528' in lines[first + 3] else None,
            'plastic_tag': 'ntm:ingots_plastic', 'steel_plate_tag': 'c:plates/steel'}


def check_live_gascent(live, ck):
    """The live AssemblyMachineRecipes statement, as text: right after ass.centrifuge, normal inputs only, no pool."""
    text = lf(live)
    ck(text.count('"ass.gascent"') == 1, 'the live assembly source registers ass.gascent exactly once')
    start = text.index('this.register(new GenericRecipe("ass.gascent")')
    end = text.index(';', start) + 1
    statement = text[start:end]
    centrifuge_end = text.index(';', text.index('this.register(new GenericRecipe("ass.centrifuge")')) + 1
    between = text[centrifuge_end:start]
    ck(all(l.strip() == '' or l.strip().startswith('//') for l in between.split('\n')), 'ass.gascent is registered right after the ass.centrifuge statement (only comments between)')
    ck('.setup(400, 100)' in statement and 'NtmBlocks.MACHINE_GAS_CENTRIFUGE.get(), 1)' in statement and '.inputItemsEx(' not in statement and 'setPools528' not in statement,
       'live ass.gascent: setup(400, 100), output 1 machine_gas_centrifuge, no inputItemsEx, no 528 pool')
    return statement


# ---- (c) pseudo fluids and summary rows -------------------------------------------------------------------------------------------------

PSEUDO = re.compile(r'PseudoFluidType (\w+)\s*=\s*new PseudoFluidType\("(\w+)",\s*(\d+),\s*(\d+),\s*(\w+),\s*(true|false)(.*?)\);')


def item_field(expr):
    """ModItems.nugget_u238 / NtmItems.NUGGET_U238.get() -> NUGGET_U238."""
    m = re.match(r'ModItems\.(\w+)$', expr.strip()) or re.match(r'NtmItems\.(\w+)\.get\(\)$', expr.strip())
    if not m: raise AssertionError('unrecognised item expression ' + expr)
    return m.group(1).upper()


def stacks(text):
    return [(item_field(a), int(b) if b else 1) for a, b in re.findall(r'new ItemStack\((\w+\.\w+(?:\.get\(\))?)(?:, (\d+))?\)', text)]


def parse_pseudo(text):
    rows = []
    for m in PSEUDO.finditer(text):
        rows.append({'field': m.group(1), 'name': m.group(2), 'consumed': int(m.group(3)), 'produced': int(m.group(4)), 'out': m.group(5), 'high_speed': m.group(6) == 'true',
                     'inline_outputs': stacks(m.group(7))})
    return rows


def parse_original_gascent_table(source):
    text = read(source / ORIGINAL_GASCENT)
    lines = text.split('\n')
    rows = parse_pseudo(text)
    for r in rows: r['line'] = 1 + next(i for i, l in enumerate(lines) if re.search(r'PseudoFluidType ' + r['field'] + r'\s*=', l))
    conv = re.findall(r'fluidConversions\.put\(Fluids\.(\w+), PseudoFluidType\.(\w+)\);', text)
    summary = []
    for i, l in enumerate(lines):
        m = re.search(r'gasCent\.put\(new FluidStack\((\d+), Fluids\.(\w+)\), new Object\[\] \{ new ItemStack\[\] \{(.*?)\}, (true|false), (\d+) \}\);', l)
        if m: summary.append({'line': i + 1, 'fluid': m.group(2), 'amount': int(m.group(1)), 'outputs': stacks(m.group(3)), 'high_speed': m.group(4) == 'true', 'centrifuges': int(m.group(5))})
    return {'rows': rows, 'conversions': conv, 'summary': summary, 'source': ORIGINAL_GASCENT}


def parse_neo_gascent_table(text):
    text = lf(text)
    rows = parse_pseudo(text)
    for r in rows:
        m = re.search(r'PseudoFluidType\.' + r['field'] + r'\.output = new ItemStack\[\] \{(.*?)\};', text)
        r['outputs'] = stacks(m.group(1)) if m else []
    conv = re.findall(r'fluidConversions\.put\(Fluids\.(\w+), PseudoFluidType\.(\w+)\);', text)
    summary = []
    for m in re.finditer(r'JEI_RECIPES\.add\(new GasCentrifugeRecipe\(Fluids\.(\w+), (\d+), new ItemStack\[\] \{(.*?)\}, (true|false), (\d+)\)\);', text):
        summary.append({'fluid': m.group(1), 'amount': int(m.group(2)), 'outputs': stacks(m.group(3)), 'high_speed': m.group(4) == 'true', 'centrifuges': int(m.group(5))})
    return {'rows': rows, 'conversions': conv, 'summary': summary}


def check_gascent_table(neo, original, ck):
    o_rows = original['rows']
    ck([r['name'] for r in o_rows] == ['NONE', 'HEUF6', 'MEUF6', 'LEUF6', 'NUF6', 'PF6', 'MUD_HEAVY', 'MUD'] and o_rows[0]['line'] == 24 and o_rows[-1]['line'] == 34,
       'original GasCentrifugeRecipes.java:24-34 declares NONE, HEUF6, MEUF6, LEUF6, NUF6, PF6, MUD_HEAVY, MUD')
    ck([r['name'] for r in neo['rows']] == [r['name'] for r in o_rows], 'the production table declares the eight pseudo fluids in the original order: ' + str([r['name'] for r in neo['rows']]))
    for n, o in zip(neo['rows'], o_rows):
        ck((n['consumed'], n['produced'], n['out'], n['high_speed']) == (o['consumed'], o['produced'], 'null' if o['out'] == 'null' else o['out'], o['high_speed']),
           f'pseudo fluid {o["name"]} consumes {o["consumed"]}, produces {o["produced"]} {o["out"]}, high speed {o["high_speed"]} (original :{o["line"]}; production '
           f'{n["consumed"]}/{n["produced"]}/{n["out"]}/{n["high_speed"]})')
        if o['name'] in ('MUD_HEAVY', 'MUD'):
            ck(n['outputs'] == [], f'pseudo fluid {o["name"]}: the original outputs {o["inline_outputs"]} are deferred (no nuclear_waste_tiny in NEO), production has none')
        else:
            ck(n['outputs'] == o['inline_outputs'], f'pseudo fluid {o["name"]} outputs {o["inline_outputs"]} (original :{o["line"]}; production {n["outputs"]})')
    ck(original['conversions'] == [('UF6', 'NUF6'), ('PUF6', 'PF6'), ('WATZ', 'MUD')] and neo['conversions'] == [('UF6', 'NUF6'), ('PUF6', 'PF6')],
       'conversions: the original UF6 -> NUF6, PUF6 -> PF6, WATZ -> MUD (:94-96); production keeps the first two, WATZ -> MUD is deferred')
    o_sum = [s for s in original['summary'] if s['fluid'] != 'WATZ']
    ck([s['line'] for s in original['summary']] == [98, 99, 100, 101] and len(o_sum) == 3, 'original summary rows :98-101 (the WATZ row :101 is deferred)')
    for i, (n, o) in enumerate(zip(neo['summary'], o_sum)):
        ck(len(neo['summary']) == 3 and {k: n[k] for k in ('fluid', 'amount', 'outputs', 'high_speed', 'centrifuges')} == {k: o[k] for k in ('fluid', 'amount', 'outputs', 'high_speed', 'centrifuges')},
           f'summary row {i + 1} equals the original :{o["line"]}: {o["amount"]} mB {o["fluid"]} -> {o["outputs"]}, high speed {o["high_speed"]}, {o["centrifuges"]} centrifuges (production {n})')
    ck(len(neo['summary']) == 3, 'the production table has exactly three summary rows')


# ---- (d) language ---------------------------------------------------------------------------------------------------------------------------

def java_string(literal):
    return re.sub(r'\\(u[0-9a-fA-F]{4}|.)', lambda m: chr(int(m.group(1)[1:], 16)) if m.group(1)[0] == 'u' else
                  {'n': '\n', 't': '\t', '"': '"', '\\': '\\', "'": "'"}[m.group(1)], literal)


def provider_lang(text):
    """key -> English of every this.add(...) in NtmLanguageProvider (string keys and NtmItems/NtmBlocks fields)."""
    out = {}
    for m in re.finditer(r'this\.add\((?:"([^"]+)"|NtmItems\.(\w+)|NtmBlocks\.(\w+)), "((?:[^"\\]|\\.)*)"\);', lf(text)):
        key = m.group(1) or ('item.hbmsntm.' + m.group(2).lower() if m.group(2) else 'block.hbmsntm.' + m.group(3).lower())
        out.setdefault(key, []).append(java_string(m.group(4)))
    return out


def original_lang(source):
    table = {}
    for name, rel in (('en', ORIGINAL_EN), ('zh', ORIGINAL_ZH)):
        for i, line in enumerate(read(source / rel).split('\n')):
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                table.setdefault(name, {}).setdefault(k, (v, i + 1))
    return table


def check_language(provider_text, frozen_provider_text, zh, frozen_zh, mapping, frozen_mapping, original, ck):
    live, frozen = provider_lang(provider_text), provider_lang(frozen_provider_text)
    added = sorted(set(live) - set(frozen))
    ck(added == sorted(LANG_KEYS), 'NtmLanguageProvider adds exactly the fifteen Goal20B keys against the frozen start: ' + str(added))
    ck(all(live[k] == frozen[k] for k in frozen if k in live) and set(frozen) <= set(live), 'no existing NtmLanguageProvider key changed or vanished')
    ck(sorted(set(zh) - set(frozen_zh)) == sorted(LANG_KEYS) and not set(frozen_zh) - set(zh) and all(zh[k] == frozen_zh[k] for k in frozen_zh),
       'zh_cn.json adds exactly the fifteen keys and changes nothing else: ' + str(sorted(set(zh) - set(frozen_zh))))
    ck(sorted(set(mapping) - set(frozen_mapping)) == sorted(LANG_KEYS) and not set(frozen_mapping) - set(mapping) and all(mapping[k] == frozen_mapping[k] for k in frozen_mapping),
       'zh_cn-map.json adds exactly the fifteen entries and changes nothing else')
    facts = {}
    for key, (kind, source_key) in LANG_KEYS.items():
        en = live.get(key, [None])
        ck(len(en) == 1, f'{key} is added once in NtmLanguageProvider')
        en = en[0]
        entry = mapping.get(key, {})
        ck(entry.get('kind') == kind, f'mapping {key} has kind {kind} (got {entry.get("kind")})')
        if kind == 'upstream':
            o_en, en_line = original['en'][source_key]
            o_zh, zh_line = original['zh'][source_key]
            ck(en == o_en and zh.get(key) == o_zh, f'{key}: English and Chinese equal the original {source_key} (en_US.lang:{en_line}, zh_CN.lang:{zh_line})')
            ck(entry.get('source_key') == source_key and entry.get('source_en') == o_en and entry.get('source_zh') == o_zh and entry.get('target_en') == en and entry.get('target_zh') == zh.get(key),
               f'mapping {key}: source_key {source_key}, source_en/source_zh equal the original lines, target_en/target_zh equal the live English and Chinese')
            facts[key] = {'kind': kind, 'source_key': source_key, 'en_US_line': en_line, 'zh_CN_line': zh_line, 'en': en, 'zh': zh.get(key)}
        else:
            want_en, want_zh = LOCAL_TEXT[key]
            ck(en == want_en and zh.get(key) == want_zh, f'{key} (local): English {want_en!r} and Chinese {want_zh!r}')
            ck(entry.get('target_en') == en and entry.get('target_zh') == zh.get(key) and bool(entry.get('reason')) and 'source_key' not in entry,
               f'mapping {key} (local): target_en/target_zh equal the live texts, a reason, no source key')
            facts[key] = {'kind': kind, 'en': en, 'zh': zh.get(key), 'reason': entry.get('reason')}
    deferred = [k for k, v in mapping.items() if v.get('kind') == 'deferred']
    ck(len(zh) == TOTALS['zh'] and len(mapping) == TOTALS['map'] and len(deferred) == TOTALS['deferred'] and set(mapping) - set(zh) == set(deferred),
       f'totals: zh {len(zh)} (want {TOTALS["zh"]}), map {len(mapping)} (want {TOTALS["map"]}), deferred {len(deferred)} (want {TOTALS["deferred"]}) = the map keys without Chinese')
    return facts


def check_original_local_sources(source, ck):
    upgrade = read(source / ORIGINAL_UPGRADE)
    ck('list.add(EnumChatFormatting.RED + "Gas Centrifuge Upgrade");' in upgrade and 'list.add("Allows for total isotopic separation of HEUF6");' in upgrade
       and 'list.add(EnumChatFormatting.YELLOW + "also your centrifuge goes sicko mode");' in upgrade, 'the original upgrade tooltip is the hardcoded three lines (red, plain, yellow)')
    nei = read(source / ORIGINAL_NEI)
    ck('String centrifuges = set.centNumber + " G. Cents";' in nei, 'the original NEI handler hardcodes "N G. Cents"')
    return {'upgrade_tooltip_lines': [line_of(upgrade, '"Gas Centrifuge Upgrade"'), line_of(upgrade, '"also your centrifuge goes sicko mode"')],
            'nei_cascade_line': line_of(nei, '" G. Cents"')}


# ---- (e) assets -------------------------------------------------------------------------------------------------------------------------------

def png_size(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR': raise AssertionError('not a PNG')
    return struct.unpack('>II', data[16:24])


def check_assets(neo_assets, original_assets, contents, ck):
    """contents: NEO relative path -> bytes (so a mutation can pass a corrupted copy)."""
    facts = {}
    for neo, orig in ASSETS.items():
        a, b = contents[neo], (original_assets / orig).read_bytes()
        ck(hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest(), f'asset {neo} is byte-identical to the original {orig}')
        facts[neo] = {'original': orig, 'sha256': hashlib.sha256(a).hexdigest()}
    objects = re.findall(r'^o (\S+)', contents['models/obj/machines/gas_centrifuge.obj'].decode('utf-8').replace('\r\n', '\n'), re.M)
    ck(objects == ['Flag', 'Centrifuge'], 'the OBJ has exactly the objects Flag and Centrifuge (RenderCentrifuge.java:40-45): ' + str(objects))
    size = png_size(contents['textures/gui/processing/gui_centrifuge_gas.png'])
    ck(size == (256, 256), f'the GUI PNG is 256x256 (the 206x204 GUI region on a 256 sheet; got {size})')
    ck((neo_assets / 'textures/block/block_steel.png').is_file(), 'the particle texture block/block_steel exists')
    facts['obj_objects'] = objects
    facts['gui_png_size'] = list(size)
    return facts


# ---- (f) provider and registration edits ----------------------------------------------------------------------------------------------------

def inserted_only(frozen, live):
    a, b = lf(frozen).split('\n'), lf(live).split('\n')
    ops = [(tag, a[i1:i2], b[j1:j2]) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if tag != 'equal']
    return all(tag == 'insert' for tag, _, _ in ops), [l.strip() for _, _, new in ops for l in new]


def check_edits(frozen, live, ck):
    facts = {}
    for rel, needles in PROVIDER_EDITS.items():
        only, lines = inserted_only(frozen[rel], live[rel])
        ck(only, f'{rel} differs from the frozen Goal20B start by insertions only')
        code = [l for l in lines if l and not l.startswith('//')]
        for needle in needles:
            ck(sum(1 for l in code if l == needle) == 1, f'{rel} inserts {needle!r} exactly once')
        facts[rel] = {'inserted_lines': len(lines), 'code_lines': len(code)}
    return facts


# ---- (b) generated files ---------------------------------------------------------------------------------------------------------------

def check_upgrade_json(data, ck):
    ck(data.get('type') == 'minecraft:crafting_shaped' and data.get('category') == 'misc', 'upgrade_gc_speed.json is a shaped misc recipe')
    ck(data.get('pattern') == ['GNG', 'RUR', 'GMG'], 'upgrade_gc_speed.json pattern GNG/RUR/GMG (CraftingManager.java:728)')
    ck(data.get('key') == {'G': {'item': 'hbmsntm:coil_gold'}, 'N': {'item': 'hbmsntm:ingot_niobium'}, 'R': {'item': 'hbmsntm:ingot_rubber'}, 'U': {'item': 'hbmsntm:upgrade_template'},
                           'M': {'item': 'hbmsntm:motor'}}, 'upgrade_gc_speed.json keys G coil_gold, N ingot_niobium, R ingot_rubber, U upgrade_template, M motor')
    ck(data.get('result') == {'count': 1, 'id': 'hbmsntm:upgrade_gc_speed'}, 'upgrade_gc_speed.json result is 1 upgrade_gc_speed')


def check_rod_json(name, data, billet, meta, ck):
    ck(data.get('type') == 'minecraft:crafting_shapeless' and data.get('category') == 'misc', f'{name}.json is a shapeless misc recipe')
    ck(data.get('ingredients') == [{'item': 'hbmsntm:rod_zirnox_empty'}, {'item': billet}, {'item': billet}], f'{name}.json ingredients are exactly rod_zirnox_empty and two {billet}')
    ck(data.get('result') == {'components': {'hbmsntm:meta': meta}, 'count': 1, 'id': 'hbmsntm:rod_zirnox'}, f'{name}.json result is 1 rod_zirnox with hbmsntm:meta {meta} and no life')


def advancement(name, criterion, item):
    return {'parent': 'minecraft:recipes/root', 'criteria': {criterion: {'conditions': {'items': [{'items': item}]}, 'trigger': 'minecraft:inventory_changed'},
                                                               'has_the_recipe': {'conditions': {'recipe': f'hbmsntm:{name}'}, 'trigger': 'minecraft:recipe_unlocked'}},
            'requirements': [['has_the_recipe', criterion]], 'rewards': {'recipes': [f'hbmsntm:{name}']}}


def check_generated(gen, live_lang, frozen_en_count, ck, override=None):
    """Every generated file runData publishes for Goal20B. override maps a GENERATED key to replacement data (mutations)."""
    override = override or {}
    data = {}
    for key, rel in GENERATED.items():
        data[key] = override[key] if key in override else json.loads((gen / rel).read_text(encoding='utf-8'))
    check_upgrade_json(data['upgrade'], ck)
    check_rod_json('rod_zirnox_uranium_fuel', data['rod_uranium'], 'hbmsntm:billet_uranium_fuel', 1, ck)
    check_rod_json('rod_zirnox_u235_fuel', data['rod_u235'], 'hbmsntm:billet_u235', 7, ck)
    ck(data['adv_upgrade'] == advancement('upgrade_gc_speed', 'has_upgrade_template', 'hbmsntm:upgrade_template'), 'the upgrade_gc_speed recipe advancement unlocks on the upgrade template')
    for key, name in (('adv_rod_uranium', 'rod_zirnox_uranium_fuel'), ('adv_rod_u235', 'rod_zirnox_u235_fuel')):
        ck(data[key] == advancement(name, 'has_rod_zirnox_empty', 'hbmsntm:rod_zirnox_empty'), f'the {name} recipe advancement unlocks on the empty rod')
    ck(data['blockstate'] == {'variants': {'': {'model': 'hbmsntm:block/machine_gas_centrifuge_particle'}}}, 'blockstates/machine_gas_centrifuge.json is one variant on the particle model')
    ck(data['particle_model'] == {'textures': {'particle': 'hbmsntm:block/block_steel'}}, 'models/block/machine_gas_centrifuge_particle.json: particle block_steel only')
    ck(data['block_item_model'] == {'parent': 'minecraft:builtin/entity', 'gui_light': 'side'}, 'models/item/machine_gas_centrifuge.json is builtin/entity with side light (BEWLR item)')
    ck(data['upgrade_item_model'] == {'parent': 'minecraft:item/handheld', 'textures': {'layer0': 'hbmsntm:item/upgrade_gc_speed'}}, 'models/item/upgrade_gc_speed.json is handheld on item/upgrade_gc_speed')
    ck(data['loot'] == {'type': 'minecraft:block', 'pools': [{'bonus_rolls': 0.0, 'conditions': [{'condition': 'minecraft:survives_explosion'}],
                                                               'entries': [{'type': 'minecraft:item', 'name': 'hbmsntm:machine_gas_centrifuge'}], 'rolls': 1.0}],
                        'random_sequence': 'hbmsntm:blocks/machine_gas_centrifuge'}, 'the machine_gas_centrifuge loot table drops itself once (dropSelf)')
    ck(data['pickaxe']['values'].count('hbmsntm:machine_gas_centrifuge') == 1, "data/minecraft/tags/block/mineable/pickaxe.json lists hbmsntm:machine_gas_centrifuge once")
    en = data['en_us']
    for key in LANG_KEYS:
        ck(en.get(key) == live_lang[key][0], f'en_us.json has {key} = the provider English')
    ck(len(en) == TOTALS['en'] and len(en) == frozen_en_count + len(LANG_KEYS), f'en_us.json has {TOTALS["en"]} keys = the frozen start {frozen_en_count} + 15 (got {len(en)})')
    return data


# ---- provider crafting statements and the original rod/upgrade lines -----------------------------------------------------------------

def zirnox_order(text):
    """Enum constant names in declaration order (original EnumZirnoxType or NEO ZirnoxType)."""
    body = text[text.index('enum '):]
    body = body[body.index('{') + 1:]
    return [m.group(1) for m in re.finditer(r'^\s*([A-Z][A-Z0-9_]*)\s*\(', body, re.M)][:11]


def parse_original_crafting(source):
    rods = read(source / ORIGINAL_ROD_RECIPES).split('\n')
    uranium, u235 = rods[27].strip(), rods[33].strip()
    assert uranium == 'addZIRNOXRod(ModItems.billet_uranium_fuel, EnumZirnoxType.URANIUM_FUEL);' and u235 == 'addZIRNOXRod(U235, EnumZirnoxType.U235_FUEL);', \
        'original RodRecipes.java:28/:34 are not the uranium fuel and U235 rod statements'
    helpers = [l.strip() for l in rods if 'CraftingManager.addShapelessAuto(new ItemStack(ModItems.rod_zirnox, 1, num.ordinal())' in l]
    assert helpers == ['CraftingManager.addShapelessAuto(new ItemStack(ModItems.rod_zirnox, 1, num.ordinal()), new Object[] { ModItems.rod_zirnox_empty, billet, billet });',
                       'CraftingManager.addShapelessAuto(new ItemStack(ModItems.rod_zirnox, 1, num.ordinal()), new Object[] { ModItems.rod_zirnox_empty, mat.billet(), mat.billet() });'], \
        'the original addZIRNOXRod helpers are not "empty rod + two billets"'
    crafting = read(source / ORIGINAL_CRAFTING).split('\n')
    upgrade = crafting[727].strip()
    assert upgrade == ("addRecipeAuto(new ItemStack(ModItems.upgrade_gc_speed, 1), new Object[] {\"GNG\", \"RUR\", \"GMG\", 'R', RUBBER.ingot(), 'M', ModItems.motor, "
                       "'G', ModItems.coil_gold, 'N', NB.ingot(), 'U', ModItems.upgrade_template});"), 'original CraftingManager.java:728 is not the upgrade_gc_speed recipe'
    text = read(source / ORIGINAL_ZIRNOX_ROD)
    order = zirnox_order(text[text.index('enum EnumZirnoxType'):])
    return {'rod_uranium_fuel': f'{ORIGINAL_ROD_RECIPES}:28 {uranium}', 'rod_u235_fuel': f'{ORIGINAL_ROD_RECIPES}:34 {u235}', 'rod_helpers': helpers,
            'upgrade': f'{ORIGINAL_CRAFTING}:728 {upgrade}', 'original_type_order': order}


def check_provider_crafting(provider, neo_order, original, ck):
    text = lf(provider)
    rods = {}
    for m in re.finditer(r'ShapelessRecipeBuilder\.shapeless\(RecipeCategory\.MISC, MetaHelper\.newStack\(NtmItems\.ROD_ZIRNOX\.get\(\), (\d+), ZirnoxType\.(\w+)\.ordinal\(\)\)\)\s*'
                         r'\.requires\(NtmItems\.ROD_ZIRNOX_EMPTY\.get\(\)\)\s*\.requires\(NtmItems\.(\w+)\.get\(\), (\d+)\)\s*\.unlockedBy\([^\n]*\)\s*'
                         r'\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\("hbmsntm", "(\w+)"\)\);', text):
        rods[m.group(5)] = {'count': int(m.group(1)), 'type': m.group(2), 'billet': m.group(3), 'billet_count': int(m.group(4))}
    ck(neo_order == original['original_type_order'] and len(neo_order) == 11 and neo_order.index('URANIUM_FUEL') == 1 and neo_order.index('U235_FUEL') == 7,
       'ZirnoxType equals the original EnumZirnoxType order (URANIUM_FUEL 1, U235_FUEL 7): ' + str(neo_order))
    ck(set(rods) == {'rod_zirnox_natural_uranium_fuel', 'rod_zirnox_th232', 'rod_zirnox_uranium_fuel', 'rod_zirnox_u235_fuel'},
       'the provider has exactly the natural uranium, th232, uranium fuel and U235 shapeless rod statements: ' + str(sorted(rods)))
    for name, kind, billet in (('rod_zirnox_uranium_fuel', 'URANIUM_FUEL', 'BILLET_URANIUM_FUEL'), ('rod_zirnox_u235_fuel', 'U235_FUEL', 'BILLET_U235')):
        r = rods.get(name, {})
        ck(r.get('type') == kind and r.get('count') == 1, f'provider {name} makes rod type {kind}, count 1 (got {r})')
        ck(r.get('billet') == billet and r.get('billet_count') == 2, f'provider {name} requires two {billet} (got {r})')
    up = re.search(r'ShapedRecipeBuilder\.shaped\(RecipeCategory\.MISC, NtmItems\.UPGRADE_GC_SPEED\.get\(\), (\d+)\)\s*\.pattern\("(\w+)"\)\s*\.pattern\("(\w+)"\)\s*\.pattern\("(\w+)"\)'
                   r'((?:\s*\.define\(\'\w\', NtmItems\.\w+\.get\(\)\))+)\s*\.unlockedBy\("has_upgrade_template", has\(NtmItems\.UPGRADE_TEMPLATE\.get\(\)\)\)\s*'
                   r'\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\("hbmsntm", "upgrade_gc_speed"\)\);', text)
    ck(up is not None, 'the provider has the upgrade_gc_speed shaped statement')
    ck([up.group(2), up.group(3), up.group(4)] == ['GNG', 'RUR', 'GMG'] and up.group(1) == '1', 'provider upgrade_gc_speed pattern GNG/RUR/GMG, count 1 (CraftingManager.java:728)')
    defines = dict(re.findall(r"\.define\('(\w)', NtmItems\.(\w+)\.get\(\)\)", up.group(5)))
    ck(defines == {'G': 'COIL_GOLD', 'N': 'INGOT_NIOBIUM', 'R': 'INGOT_RUBBER', 'U': 'UPGRADE_TEMPLATE', 'M': 'MOTOR'},
       'provider upgrade_gc_speed keys G COIL_GOLD, N INGOT_NIOBIUM, R INGOT_RUBBER (RUBBER.ingot()), U UPGRADE_TEMPLATE, M MOTOR: ' + str(defines))
    return {'rods': rods, 'upgrade': {'pattern': [up.group(2), up.group(3), up.group(4)], 'keys': defines}}
