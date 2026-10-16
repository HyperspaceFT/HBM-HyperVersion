"""Goal20C static recipe/resource evidence: the original RodRecipes, CraftingManager, HazardRegistry, ModItems, FuelPoolRecipes, GUIWasteDrum and
language lines (read-only) against the production provider and registration edits, the frozen Goal20C start copies, the language files and
mapping, the imported assets, the generated files runData published and the custom fuel pool example. Every check takes `ck(condition, label)`
so verify_goal20c_recipes.py can run the same function on an edited copy and expect its AssertionError."""
from collections import Counter
from pathlib import Path
import difflib, hashlib, json, re

from goal20b_regression.recipe_static import read, lf, provider_lang, original_lang, advancement, line_of

ORIGINAL_ROD_RECIPES = 'src/main/java/com/hbm/crafting/RodRecipes.java'
ORIGINAL_CRAFTING = 'src/main/java/com/hbm/main/CraftingManager.java'
ORIGINAL_HAZARD = 'src/main/java/com/hbm/hazard/HazardRegistry.java'
ORIGINAL_MODITEMS = 'src/main/java/com/hbm/items/ModItems.java'
ORIGINAL_FUELPOOL = 'src/main/java/com/hbm/inventory/recipes/FuelPoolRecipes.java'
ORIGINAL_GUI = 'src/main/java/com/hbm/inventory/gui/GUIWasteDrum.java'
ORIGINAL_DEPLETED = 'src/main/java/com/hbm/items/machine/ItemDepletedFuel.java'
ORIGINAL_EN = 'src/main/resources/assets/hbm/lang/en_US.lang'
ORIGINAL_ZH = 'src/main/resources/assets/hbm/lang/zh_CN.lang'
ORIGINAL_FILES = (ORIGINAL_ROD_RECIPES, ORIGINAL_CRAFTING, ORIGINAL_HAZARD, ORIGINAL_MODITEMS, ORIGINAL_FUELPOOL, ORIGINAL_GUI, ORIGINAL_DEPLETED, ORIGINAL_EN, ORIGINAL_ZH)

ITEMS = 'com/hbm/items/NtmItems.java'
BLOCKS = 'com/hbm/blocks/NtmBlocks.java'
PROVIDER = 'com/hbm/datagen/NtmRecipeProvider.java'
LANG = 'com/hbm/datagen/NtmLanguageProvider.java'
HAZARD = 'com/hbm/hazard/HazardRegistry.java'
FUELPOOL = 'com/hbm/inventory/recipes/FuelPoolRecipes.java'
DEPLETED = 'com/hbm/items/machine/DepletedFuelItem.java'
CLIENT = 'com/hbm/main/NuclearTechModClient.java'

# Original Object[] references outside ModItems/ModBlocks -> NEO ids (NEO uses the plain items for the ore dictionary entries).
ORIGINAL_REFS = {'STEEL.plate()': 'hbmsntm:plate_steel', 'PB.plate()': 'hbmsntm:plate_lead', 'PB.ingot()': 'hbmsntm:ingot_lead', 'Blocks.iron_bars': 'minecraft:iron_bars'}
NEO_VANILLA = {'Items.IRON_BARS': 'minecraft:iron_bars'}

# The thirteen Goal20C language keys: key -> (kind, original key or None).
LANG_KEYS = {
    'item.hbmsntm.waste_natural_uranium': ('upstream', 'item.waste_natural_uranium.name'),
    'item.hbmsntm.waste_uranium': ('upstream', 'item.waste_uranium.name'),
    'item.hbmsntm.waste_thorium': ('upstream', 'item.waste_thorium.name'),
    'item.hbmsntm.waste_mox': ('upstream', 'item.waste_mox.name'),
    'item.hbmsntm.waste_plutonium': ('upstream', 'item.waste_plutonium.name'),
    'item.hbmsntm.waste_u233': ('upstream', 'item.waste_u233.name'),
    'item.hbmsntm.waste_u235': ('upstream', 'item.waste_u235.name'),
    'item.hbmsntm.waste_schrabidium': ('upstream', 'item.waste_schrabidium.name'),
    'item.hbmsntm.waste_zfb_mox': ('local', 'item.waste_zfb_mox.name'),
    'desc.item.wasteCooling': ('upstream', 'desc.item.wasteCooling'),
    'block.hbmsntm.machine_waste_drum': ('upstream', 'tile.machine_waste_drum.name'),
    'container.machine_waste_drum': ('upstream', 'container.wasteDrum'),
    'desc.gui.wasteDrum.info': ('local', None),
}
# The two local Chinese texts as frozen at delivery (the English of both is checked against the original).
LOCAL_ZH = {'item.hbmsntm.waste_zfb_mox': '枯竭ZFB MOX燃料', 'desc.gui.wasteDrum.info': '将桶浸入水中可冷却$热核废料。周围的水越多，$冷却越快。'}
TOTALS = {'en': 2357, 'zh': 2249, 'map': 2357, 'deferred': 108}

# NEO asset path under assets/hbmsntm -> original path under assets/hbm.
ASSETS = {
    'textures/item/waste_uranium.png': 'textures/items/waste_uranium.png',
    'textures/item/waste_thorium.png': 'textures/items/waste_thorium.png',
    'textures/item/waste_mox.png': 'textures/items/waste_mox.png',
    'textures/item/waste_plutonium.png': 'textures/items/waste_plutonium.png',
    'textures/item/waste_schrabidium.png': 'textures/items/waste_schrabidium.png',
    'textures/item/waste_zfb_mox.png': 'textures/items/waste_zfb_mox.png',
    'textures/block/waste_drum.png': 'textures/blocks/waste_drum.png',
    'textures/block/waste_drum_side.png': 'textures/blocks/waste_drum_side.png',
    'textures/gui/gui_waste_drum.png': 'textures/gui/gui_waste_drum.png',
}

# Pre-existing production files Goal20C edited -> stripped code lines the edit must insert (each exactly once). NtmItems also replaces the nine
# depleted rod lines (checked separately); every other file differs from its frozen start by insertions only.
EDITS = {
    'com/hbm/blocks/NtmBlocks.java': ['public static final DeferredBlock<Block> MACHINE_WASTE_DRUM = register("machine_waste_drum", () -> new MachineWasteDrumBlock('
                                      'BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops()));'],
    'com/hbm/blockentity/NtmBlockEntityTypes.java': ['public static final Supplier<BlockEntityType<MachineWasteDrumBlockEntity>> MACHINE_WASTE_DRUM = BLOCK_ENTITY_TYPES.register(',
                                                     '"machine_waste_drum",', '() -> BlockEntityType.Builder.of(MachineWasteDrumBlockEntity::new, NtmBlocks.MACHINE_WASTE_DRUM.get()).build(null));'],
    'com/hbm/inventory/NtmMenuTypes.java': ['public static final DeferredHolder<MenuType<?>, MenuType<MachineWasteDrumMenu>> MACHINE_WASTE_DRUM = reg("machine_waste_drum", MachineWasteDrumMenu::new);'],
    'com/hbm/inventory/NtmCreativeTabs.java': ['output.accept(NtmBlocks.MACHINE_WASTE_DRUM);'] + [f'addMetaItems(output, NtmItems.WASTE_{w}.get());' for w in
                                              ('NATURAL_URANIUM', 'URANIUM', 'THORIUM', 'MOX', 'PLUTONIUM', 'U233', 'U235', 'SCHRABIDIUM', 'ZFB_MOX')],
    'com/hbm/main/NuclearTechModClient.java': ['import com.hbm.inventory.screens.MachineWasteDrumScreen;', 'import com.hbm.items.machine.DepletedFuelItem;',
                                               'event.register(NtmMenuTypes.MACHINE_WASTE_DRUM.get(), MachineWasteDrumScreen::new);',
                                               '(stack, tintIndex) -> tintIndex == 0 && DepletedFuelItem.isHot(stack) ? 0xFFFFBFA5 : 0xFFFFFFFF,'],
    'com/hbm/hazard/HazardRegistry.java': ['import static com.hbm.blocks.NtmBlocks.BLOCK_WASTE;', 'import static com.hbm.blocks.NtmBlocks.BLOCK_WASTE_PAINTED;',
                                           'import static com.hbm.blocks.NtmBlocks.BLOCK_WASTE_VITRIFIED;',
                                           'private static void registerOtherWaste(DeferredItem<Item> waste, float base) {'],
    'com/hbm/inventory/recipes/loader/SerializableRecipe.java': ['import com.hbm.inventory.recipes.FuelPoolRecipes;', 'recipeHandlers.add(new FuelPoolRecipes());'],
    'com/hbm/network/NtmNetwork.java': ['registrar.playToClient(FuelPoolRecipesPacket.TYPE, FuelPoolRecipesPacket.STREAM_CODEC, FuelPoolRecipesPacket::handleCommon);'],
    'com/hbm/handler/jei/NtmJeiPlugin.java': ['import com.hbm.handler.FuelPoolRecipeClientSync;', 'import com.hbm.inventory.recipes.FuelPoolRecipes;', 'new FuelPoolRecipeHandler(guiHelper),',
                                              'registration.addRecipes(FuelPoolRecipeHandler.RECIPE_TYPE, this.displayedFuelPoolRecipes);', 'FuelPoolRecipeHandler.RECIPE_TYPE'],
    'com/hbm/datagen/NtmRecipeProvider.java': ['.save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "machine_waste_drum"));', '.pattern("BRB")', ".define('B', Items.IRON_BARS)",
                                               'private void addWasteRecipe(RecipeOutput recipeOutput, Item waste, Item depletedRod) {'],
    'com/hbm/datagen/NtmLanguageProvider.java': ['this.add("desc.item.wasteCooling", "Cool in a Spent Fuel Pool Drum");', 'this.add(NtmBlocks.MACHINE_WASTE_DRUM, "Spent Fuel Pool Drum");',
                                                 'this.add("container.machine_waste_drum", "Spent Fuel Pool Drum");'],
    'com/hbm/datagen/NtmBlockStateProvider.java': ['NtmBlocks.MACHINE_WASTE_DRUM,', 'name(NtmBlocks.MACHINE_WASTE_DRUM),', 'modLoc("block/waste_drum_side"),', 'modLoc("block/waste_drum")'],
    'com/hbm/datagen/NtmItemModelProvider.java': ['this.basicCustomLayerItem(NtmItems.WASTE_NATURAL_URANIUM.get(), "waste_uranium");', 'this.basicItem(NtmItems.WASTE_URANIUM.get());',
                                                  'this.basicCustomLayerItem(NtmItems.WASTE_U233.get(), "waste_uranium");', 'this.basicCustomLayerItem(NtmItems.WASTE_U235.get(), "waste_uranium");'],
    'com/hbm/datagen/NtmBlockLootTableProvider.java': ['this.dropSelf(NtmBlocks.MACHINE_WASTE_DRUM.get());'],
    'com/hbm/datagen/NtmBlockTagProvider.java': ['NtmBlocks.MACHINE_WASTE_DRUM.get(),'],
}
UNCHANGED = ('com/hbm/main/CommonEvents.java',)
BREEDING_IDS = ('rod_empty', 'rod_empty_from_rod_dual_empty', 'rod_dual_empty', 'rod_empty_from_rod_quad_empty', 'rod_quad_empty', 'rod_quad_empty_from_rod_dual_empty')

# Hazard constants shared by the original and NEO HazardRegistry.
CONSTANTS = ('wst', 'wstv', 'nugget', 'ingot', 'block', 'billet')
PLAIN_HAZARDS = ('nuclear_waste', 'billet_nuclear_waste', 'nuclear_waste_vitrified', 'block_waste', 'block_waste_painted', 'block_waste_vitrified')
PLAIN_VALUES = {'nuclear_waste': 15.0, 'billet_nuclear_waste': 7.5, 'nuclear_waste_vitrified': 7.5, 'block_waste': 150.0, 'block_waste_painted': 150.0, 'block_waste_vitrified': 75.0}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---- original facts --------------------------------------------------------------------------------------------------------------------

def original_ref(token, items):
    token = token.strip()
    if token in ORIGINAL_REFS: return ORIGINAL_REFS[token]
    m = re.fullmatch(r'Mod(?:Items|Blocks)\.(\w+)', token)
    if not m: raise AssertionError('unmapped original reference ' + token)
    return 'hbmsntm:' + m.group(1)


def parse_original_recipe(line, items):
    """addRecipeAuto / addShapelessAuto -> normalised {shape, result, count, pattern, keys | ingredients}."""
    m = re.search(r'(addRecipeAuto|addShapelessAuto)\(new ItemStack\(Mod(?:Items|Blocks)\.(\w+)(?:, (\d+))?(?:, (\d+))?\), new Object\[\] \{ (.*) \}\);', line)
    if not m: raise AssertionError('unrecognised original recipe line ' + line)
    out = {'result': 'hbmsntm:' + m.group(2), 'count': int(m.group(3) or 1), 'meta': int(m.group(4)) if m.group(4) else None}
    tokens = [t.strip() for t in m.group(5).split(',')]
    if m.group(1) == 'addRecipeAuto':
        pattern = [t.strip('"') for t in tokens if t.startswith('"')]
        rest = [t for t in tokens if not t.startswith('"')]
        out.update(shape='shaped', pattern=pattern, keys={rest[i].strip("'"): original_ref(rest[i + 1], items) for i in range(0, len(rest), 2)})
    else:
        out.update(shape='shapeless', ingredients=dict(Counter(original_ref(t, items) for t in tokens)))
    return out


def parse_original(source, items):
    rods = read(source / ORIGINAL_ROD_RECIPES).split('\n')
    waste, breeding = [], []
    for i, l in enumerate(rods):
        if 'new ItemStack(ModItems.waste_' in l and 'addShapelessAuto' in l:
            r = parse_original_recipe(l, items); r['line'] = i + 1
            r['rod'] = re.search(r'\{ ModItems\.(\w+) \}', l).group(1)
            waste.append(r)
    start = next(i for i, l in enumerate(rods) if l.strip() == '//Breeding Rods')
    for i in range(start + 1, len(rods)):
        if not rods[i].strip(): break
        r = parse_original_recipe(rods[i], items); r['line'] = i + 1
        breeding.append(r)
    crafting = read(source / ORIGINAL_CRAFTING).split('\n')
    drum_line = next(i for i, l in enumerate(crafting) if 'new ItemStack(ModBlocks.machine_waste_drum' in l)
    drum = parse_original_recipe(crafting[drum_line], items); drum['line'] = drum_line + 1

    hazard_text = read(source / ORIGINAL_HAZARD); hazard = hazard_text.split('\n')
    other_waste = [{'line': i + 1, 'name': m.group(1), 'multiplier': float(m.group(2))} for i, l in enumerate(hazard)
                   for m in [re.search(r'^\s*registerOtherWaste\((waste_\w+), wst \* billet \* ([\d.]+)F\);', l)] if m]
    plain = {}
    for i, l in enumerate(hazard):
        m = re.search(r'HazardSystem\.register\((\w+), makeData\(RADIATION, ([\w *.]+)\)\);', l)
        if m and m.group(1) in PLAIN_HAZARDS: plain[m.group(1)] = {'line': i + 1, 'expr': m.group(2)}
    constants = {n: float(re.search(rf'public static final float {n} = ([\d.]+)F;', hazard_text).group(1)) for n in CONSTANTS}
    body_start = next(i for i, l in enumerate(hazard) if 'private static void registerOtherWaste(Item waste, float base) {' in l)
    body_end = next(i for i in range(body_start, len(hazard)) if hazard[i].strip() == '}')
    body = '\n'.join(hazard[body_start:body_end + 1])

    moditems = read(source / ORIGINAL_MODITEMS).split('\n')
    containers = {m.group(1): i + 1 for i, l in enumerate(moditems)
                  for m in [re.search(r'^\s*(rod_zirnox_\w+_depleted)\s*=\s*new Item\(\)\..*\.setContainerItem\(ModItems\.rod_zirnox_empty\)', l)] if m}
    textures = {m.group(1): (m.group(2), i + 1) for i, l in enumerate(moditems)
                for m in [re.search(r'^\s*(waste_(?!plate)\w+) = new ItemDepletedFuel\(\)\.setUnlocalizedName\("\1"\)\.setCreativeTab\(MainRegistry\.partsTab\)'
                                    r'\.setTextureName\(RefStrings\.MODID \+ ":(\w+)"\);', l)] if m}
    fuelpool = read(source / ORIGINAL_FUELPOOL).split('\n')
    pool = [{'line': i + 1, 'input': m.group(1), 'input_meta': int(m.group(2)), 'output': m.group(3)} for i, l in enumerate(fuelpool)
            for m in [re.search(r'recipes\.put\(new ComparableStack\(ModItems\.(waste_(?!plate)\w+), 1, (\d+)\), new ItemStack\(ModItems\.(\w+)\)\);', l)] if m]
    gui = read(source / ORIGINAL_GUI)
    gui_lines = re.findall(r'"([^"]+)"', re.search(r'String\[\] text = new String\[\] \{(.*?)\};', gui, re.S).group(1))
    depleted = read(source / ORIGINAL_DEPLETED)
    return {'waste_recipes': waste, 'breeding': breeding, 'drum': drum, 'other_waste': other_waste, 'plain_hazards': plain, 'constants': constants,
            'other_waste_body': body, 'other_waste_body_lines': [body_start + 1, body_end + 1], 'containers': containers, 'textures': textures,
            'fuelpool': pool, 'gui_info_lines': gui_lines, 'tint': re.search(r'getItemDamage\(\) > 0 \? (0x[0-9A-Fa-f]+) : (\d+)', depleted).groups(),
            'lang': original_lang(source)}


def check_original(o, ck):
    ck([r['line'] for r in o['waste_recipes']] == list(range(39, 48)) and all(r['count'] == 2 and r['meta'] == 1 for r in o['waste_recipes']),
       'original RodRecipes.java:39-47: nine shapeless recipes, one depleted rod -> 2 waste META 1')
    ck([r['line'] for r in o['breeding']] == list(range(50, 56)), 'original RodRecipes.java:50-55: the six empty breeding rod recipes')
    ck(o['drum']['line'] == 287, 'original CraftingManager.java:287 is the drum recipe')
    ck([r['line'] for r in o['other_waste']] == list(range(255, 264)), 'original HazardRegistry.java:255-263: nine registerOtherWaste calls')
    ck(o['other_waste_body_lines'] == [629, 636], 'original registerOtherWaste body is HazardRegistry.java:629-636')
    ck(sorted(v['line'] for v in o['plain_hazards'].values()) == [209, 211, 213, 215, 216, 217] and len(o['plain_hazards']) == 6,
       'original HazardRegistry.java:208-217 registers nuclear_waste, billet_nuclear_waste, nuclear_waste_vitrified and the three waste blocks')
    ck(len(o['containers']) == 9 and all(2972 <= v <= 2980 for v in o['containers'].values()), 'original ModItems.java:2972-2980: nine depleted rods setContainerItem(rod_zirnox_empty)')
    ck(len(o['textures']) == 9 and all(2982 <= v[1] <= 2990 for v in o['textures'].values()), 'original ModItems.java:2982-2990: nine ItemDepletedFuel waste items in partsTab')
    ck([r['line'] for r in o['fuelpool']] == list(range(27, 36)) and all(r['input'] == r['output'] and r['input_meta'] == 1 for r in o['fuelpool']),
       'original FuelPoolRecipes.java:27-35: nine rows, waste META 1 -> the same waste (damage 0)')
    ck(o['tint'] == ('0xFFBFA5', '16777215'), 'original ItemDepletedFuel tint: 0xFFBFA5 when damage > 0, white otherwise (:31-35)')
    ck(len(o['gui_info_lines']) == 3, 'original GUIWasteDrum.java:31-33 hard-codes three info lines')


# ---- provider -----------------------------------------------------------------------------------------------------------------------------

def neo_ref(token, items, blocks):
    token = token.strip()
    if token in NEO_VANILLA: return NEO_VANILLA[token]
    m = re.fullmatch(r'Ntm(Items|Blocks)\.(\w+)\.get\(\)', token)
    if not m: raise AssertionError('unmapped provider reference ' + token)
    table = items if m.group(1) == 'Items' else blocks
    if m.group(2) not in table: raise AssertionError(f'provider references unregistered {m.group(2)}')
    return 'hbmsntm:' + table[m.group(2)]


def provider_statements(text, items, blocks, wanted):
    """save id -> normalised recipe for the plain ShapedRecipeBuilder / ShapelessRecipeBuilder chains (NtmItems/NtmBlocks results) saved under `wanted` ids."""
    text = lf(text)
    out = {}
    for m in re.finditer(r'(ShapedRecipeBuilder\.shaped|ShapelessRecipeBuilder\.shapeless)\(RecipeCategory\.(\w+), (Ntm(?:Items|Blocks)\.\w+\.get\(\)), (\d+)\)', text):
        end = text.index(';', m.end())
        chain = text[m.end():end]
        save = re.search(r'\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\("hbmsntm", "(\w+)"\)\)$', chain.strip())
        if not save or save.group(1) not in wanted: continue
        if save.group(1) in out: raise AssertionError('recipe id saved twice in the provider: ' + save.group(1))
        unlock = re.search(r'\.unlockedBy\("(\w+)", has\((Ntm(?:Items|Blocks)\.\w+\.get\(\))\)\)', chain)
        r = {'result': neo_ref(m.group(3), items, blocks), 'count': int(m.group(4)), 'category': m.group(2), 'meta': None,
             'criterion': unlock.group(1) if unlock else None, 'criterion_item': neo_ref(unlock.group(2), items, blocks) if unlock else None}
        if m.group(1).startswith('Shaped'):
            r.update(shape='shaped', pattern=re.findall(r'\.pattern\("([^"]*)"\)', chain),
                     keys={k: neo_ref(v, items, blocks) for k, v in re.findall(r"\.define\('(\w)', ((?:Ntm(?:Items|Blocks)\.\w+\.get\(\))|Items\.\w+)\)", chain)})
        else:
            ingredients = Counter()
            for ref, n in re.findall(r'\.requires\((Ntm(?:Items|Blocks)\.\w+\.get\(\))(?:, (\d+))?\)', chain): ingredients[neo_ref(ref, items, blocks)] += int(n or 1)
            r.update(shape='shapeless', ingredients=dict(ingredients))
        out[save.group(1)] = r
    return out


def waste_provider(text, items):
    """addWasteRecipe calls -> [(waste id, rod id)] in order, and the helper body facts."""
    text = lf(text)
    calls = [('hbmsntm:' + items[w], 'hbmsntm:' + items[r]) for w, r in
             re.findall(r'addWasteRecipe\(recipeOutput, NtmItems\.(\w+)\.get\(\), NtmItems\.(\w+)\.get\(\)\);', text)]
    start = text.index('private void addWasteRecipe(RecipeOutput recipeOutput, Item waste, Item depletedRod) {')
    helper = text[start:text.index('\n    }\n', start)]
    m = re.search(r'ShapelessRecipeBuilder\.shapeless\(RecipeCategory\.(\w+), MetaHelper\.newStack\(waste, (\d+), (\d+)\)\)\s*\.requires\(depletedRod\)\s*'
                  r'\.unlockedBy\("has_" \+ rodName, has\(depletedRod\)\)\s*\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\("hbmsntm", wasteName\)\);', helper)
    if not m: raise AssertionError('addWasteRecipe helper body not recognised')
    return calls, {'category': m.group(1), 'count': int(m.group(2)), 'meta': int(m.group(3))}


def comparable(r): return {k: r[k] for k in ('shape', 'result', 'count', 'pattern', 'keys', 'ingredients') if k in r}


def check_provider(provider_text, items, blocks, original, ck):
    statements = provider_statements(provider_text, items, blocks, set(BREEDING_IDS) | {'machine_waste_drum'})
    calls, helper = waste_provider(provider_text, items)
    facts = {'breeding': {}, 'waste': [], 'drum': None}
    expected_breeding = [comparable(r) for r in original['breeding']]
    got = {name: statements.get(name) for name in BREEDING_IDS}
    ck(all(got.values()), 'the provider saves the six empty breeding rod recipes ' + str(BREEDING_IDS))
    ck(sorted(json.dumps(comparable(r), sort_keys=True) for r in got.values()) == sorted(json.dumps(r, sort_keys=True) for r in expected_breeding),
       'the six empty breeding rod recipes equal the original RodRecipes.java:50-55 (result, count, pattern/keys or ingredients)')
    for name, r in got.items():
        ck(r['category'] == 'MISC' and r['meta'] is None, f'{name}: misc category, plain result')
        facts['breeding'][name] = r
    drum = statements.get('machine_waste_drum')
    ck(drum is not None and comparable(drum) == comparable(original['drum']), 'the drum recipe equals the original CraftingManager.java:287 (LRL/BRB/LRL, L lead ingot, B iron bars, R rod_quad_empty): '
       + json.dumps(comparable(drum) if drum else None))
    facts['drum'] = drum
    want = [('hbmsntm:' + r['result'].split(':')[1], 'hbmsntm:' + r['rod']) for r in original['waste_recipes']]
    ck(calls == want, 'the nine addWasteRecipe calls pair each waste with its depleted rod in the original order: ' + str(calls))
    ck(all(r['count'] == helper['count'] == 2 for r in original['waste_recipes']), f'addWasteRecipe makes two waste per depleted rod (original new ItemStack(waste, 2, 1)); got {helper["count"]}')
    ck(all(r['meta'] == helper['meta'] == 1 for r in original['waste_recipes']), f'addWasteRecipe makes hot waste, META 1 (original damage 1); got META {helper["meta"]}')
    ck(helper['category'] == 'MISC', 'addWasteRecipe uses the misc category')
    facts['waste'] = [{'waste': w, 'rod': r, 'count': helper['count'], 'meta': helper['meta']} for w, r in calls]
    return facts


# ---- language ------------------------------------------------------------------------------------------------------------------------

def check_language(provider_text, frozen_provider_text, zh, frozen_zh, mapping, frozen_mapping, original, gui_lines, ck):
    live, frozen = provider_lang(provider_text), provider_lang(frozen_provider_text)
    added = sorted(set(live) - set(frozen))
    ck(added == sorted(LANG_KEYS), 'NtmLanguageProvider adds exactly the thirteen Goal20C keys against the frozen start: ' + str(added))
    ck(set(frozen) <= set(live) and all(live[k] == frozen[k] for k in frozen), 'no existing NtmLanguageProvider key changed or vanished')
    ck(sorted(set(zh) - set(frozen_zh)) == sorted(LANG_KEYS) and not set(frozen_zh) - set(zh) and all(zh[k] == frozen_zh[k] for k in frozen_zh),
       'zh_cn.json adds exactly the thirteen keys and changes nothing else: ' + str(sorted(set(zh) - set(frozen_zh))))
    ck(sorted(set(mapping) - set(frozen_mapping)) == sorted(LANG_KEYS) and not set(frozen_mapping) - set(mapping) and all(mapping[k] == frozen_mapping[k] for k in frozen_mapping),
       'zh_cn-map.json adds exactly the thirteen entries and changes nothing else')
    facts = {}
    for key, (kind, source_key) in LANG_KEYS.items():
        en = live.get(key, [None])
        ck(len(en) == 1, f'{key} is added once in NtmLanguageProvider')
        en = en[0]
        entry = mapping.get(key, {})
        ck(entry.get('kind') == kind, f'mapping {key} has kind {kind} (got {entry.get("kind")})')
        if source_key:
            o_en, en_line = original['en'][source_key]
            o_zh, zh_line = original['zh'][source_key]
            ck(en == o_en, f'{key}: English equals the original {source_key} (en_US.lang:{en_line})')
            ck(entry.get('source_key') == source_key and entry.get('source_en') == o_en and entry.get('source_zh') == o_zh,
               f'mapping {key}: source_key {source_key}, source_en/source_zh equal the original lines')
            if kind == 'upstream':
                ck(zh.get(key) == o_zh, f'{key}: Chinese equals the original {source_key} (zh_CN.lang:{zh_line})')
            else:
                ck(zh.get(key) == LOCAL_ZH[key] and zh.get(key) != o_zh and bool(entry.get('reason')), f'{key} (local): Chinese {LOCAL_ZH[key]!r} instead of {o_zh!r}, with a reason')
            facts[key] = {'kind': kind, 'source_key': source_key, 'en_US_line': en_line, 'zh_CN_line': zh_line, 'en': en, 'zh': zh.get(key)}
        else:
            ck(en == '$'.join(gui_lines), f'{key} (local): English is the three original GUIWasteDrum.java:31-33 lines joined by "$"')
            ck(zh.get(key) == LOCAL_ZH[key] and bool(entry.get('reason')) and 'source_key' not in entry, f'{key} (local): Chinese {LOCAL_ZH[key]!r}, a reason, no source key')
            ck(zh.get(key).count('$') == en.count('$'), f'{key}: the Chinese keeps the two "$" line breaks')
            facts[key] = {'kind': kind, 'en': en, 'zh': zh.get(key), 'reason': entry.get('reason')}
        ck(entry.get('target_en') == en and entry.get('target_zh') == zh.get(key), f'mapping {key}: target_en/target_zh equal the live English and Chinese')
    deferred = [k for k, v in mapping.items() if v.get('kind') == 'deferred']
    ck(len(zh) == TOTALS['zh'] and len(mapping) == TOTALS['map'] and len(deferred) == TOTALS['deferred'] and set(mapping) - set(zh) == set(deferred),
       f'totals: zh {len(zh)} (want {TOTALS["zh"]}), map {len(mapping)} (want {TOTALS["map"]}), deferred {len(deferred)} (want {TOTALS["deferred"]}) = the map keys without Chinese')
    return facts


# ---- assets ------------------------------------------------------------------------------------------------------------------------------

def check_assets(original_assets, contents, original_textures, ck):
    facts = {}
    for neo, orig in ASSETS.items():
        a, b = contents[neo], (original_assets / orig).read_bytes()
        ck(hashlib.sha256(a).digest() == hashlib.sha256(b).digest(), f'asset {neo} is byte-identical to the original {orig}')
        facts[neo] = {'original': orig, 'sha256': hashlib.sha256(a).hexdigest(), 'bytes': len(a)}
    used = sorted({t for t, _ in original_textures.values()})
    ck(['textures/item/' + t + '.png' for t in used] == sorted(p for p in ASSETS if p.startswith('textures/item/')),
       'the six item textures are exactly the original setTextureName targets of the nine waste items: ' + str(used))
    return facts


# ---- registrations and hazards ------------------------------------------------------------------------------------------------------------

def edit_ops(frozen, live):
    a, b = lf(frozen).split('\n'), lf(live).split('\n')
    return [(tag, a[i1:i2], b[j1:j2]) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if tag != 'equal']


def check_items(items_text, frozen_items_text, original, ck):
    t = lf(items_text)
    facts = {'waste': {}, 'depleted': {}}
    for name in original['textures']:
        field = name.upper()
        line = f'    public static final DeferredItem<Item> {field} = ITEMS.register("{name}", () -> new DepletedFuelItem(new Item.Properties()));'
        ck(t.count(line + '\n') == 1, f'NtmItems registers {field} as "{name}" with DepletedFuelItem')
        facts['waste'][field] = name
    replaced = {}
    for rod in original['containers']:
        field = rod.upper()
        old = f'    public static final DeferredItem<Item> {field} = ITEMS.register("{rod}", () -> new Item(new Item.Properties()));'
        new = f'    public static final DeferredItem<Item> {field} = ITEMS.register("{rod}", () -> new Item(new Item.Properties().craftRemainder(ROD_ZIRNOX_EMPTY.get())));'
        ck(lf(frozen_items_text).count(old + '\n') == 1 and t.count(new + '\n') == 1,
           f'{field} keeps the id "{rod}" and gains craftRemainder(ROD_ZIRNOX_EMPTY) (original setContainerItem(rod_zirnox_empty), ModItems.java:{original["containers"][rod]})')
        replaced[old] = new
        facts['depleted'][field] = rod
    ok, covered, inserted = True, 0, []
    for tag, old_lines, new_lines in edit_ops(frozen_items_text, items_text):
        if tag == 'insert':
            inserted += new_lines
            continue
        # A replaced block starts with the edited rod lines in their old order; anything after them is inserted.
        if tag != 'replace' or len(new_lines) < len(old_lines) or any(l not in replaced for l in old_lines) or [replaced[l] for l in old_lines] != new_lines[:len(old_lines)]:
            ok = False
            break
        covered += len(old_lines)
        inserted += new_lines[len(old_lines):]
    code = [l.strip() for l in inserted if l.strip() and not l.strip().startswith('//')]
    waste_lines = {f'public static final DeferredItem<Item> {n.upper()} = ITEMS.register("{n}", () -> new DepletedFuelItem(new Item.Properties()));' for n in original['textures']}
    ck(ok and covered == len(replaced) and sorted(code) == sorted(waste_lines),
       'NtmItems differs from the frozen start only by the nine depleted rod craftRemainder edits and the nine inserted waste registrations')
    return facts


def hazard_body_facts(body):
    body = lf(body)
    cool = re.search(r'HazardSystem\.register\((?:new ItemStack\(waste, 1, (\d)\)|MetaHelper\.newStack\(waste, 1, (\d)\)), makeData\(RADIATION, base \* ([\d.]+)F\)\);', body)
    entries = re.findall(r'data\.addEntry\(new HazardEntry\((\w+), (base|[\d.]+F)\)\);', body)
    hot = re.search(r'HazardSystem\.register\((?:new ItemStack\(waste, 1, (\d)\)|MetaHelper\.newStack\(waste, 1, (\d)\)), data\);', body)
    if not (cool and hot): raise AssertionError('registerOtherWaste body not recognised')
    return {'cool_meta': int(cool.group(1) or cool.group(2)), 'cool_factor': float(cool.group(3)), 'hot_meta': int(hot.group(1) or hot.group(2)),
            'hot_entries': [(k, v) for k, v in entries], 'registrations': body.count('HazardSystem.register(')}


def check_hazards(hazard_text, frozen_hazard_text, original, ck):
    t = lf(hazard_text)
    constants = {n: float(re.search(rf'public static final float {n} = ([\d.]+)F;', t).group(1)) for n in CONSTANTS}
    ck(constants == original['constants'], f'hazard constants equal the original: {constants}')
    calls = [(m.group(1), float(m.group(2))) for m in re.finditer(r'^\s*registerOtherWaste\((WASTE_\w+), wst \* billet \* ([\d.]+)F\);', t, re.M)]
    want = [(r['name'].upper(), r['multiplier']) for r in original['other_waste']]
    ck(calls == want, 'the nine registerOtherWaste calls carry wst * billet * the original multipliers of HazardRegistry.java:255-263, in order: ' + str(calls))
    start = t.index('private static void registerOtherWaste(DeferredItem<Item> waste, float base) {')
    neo_body = hazard_body_facts(t[start:t.index('\n    }\n', start) + 6])
    orig_body = hazard_body_facts(original['other_waste_body'])
    ck((neo_body['cool_meta'], neo_body['cool_factor']) == (orig_body['cool_meta'], orig_body['cool_factor']) == (0, 0.075),
       f'registerOtherWaste: cool (META 0) RADIATION base * 0.075 like the original :629-636 (got META {neo_body["cool_meta"]}, factor {neo_body["cool_factor"]})')
    ck((neo_body['hot_meta'], neo_body['hot_entries']) == (orig_body['hot_meta'], orig_body['hot_entries']) == (1, [('RADIATION', 'base'), ('HOT', '5F')]),
       f'registerOtherWaste: hot (META 1) RADIATION base plus HOT 5 like the original (got META {neo_body["hot_meta"]}, {neo_body["hot_entries"]})')
    ck(neo_body['registrations'] == orig_body['registrations'] == 2, 'registerOtherWaste registers exactly the two states')
    plain = {}
    for name in PLAIN_HAZARDS:
        kind = 'block' if name.startswith('block_') else 'item'
        m = re.search(rf'HazardSystem\.register\({kind}\({name.upper()}\), makeData\(RADIATION, ([\w *.]+)\)\);', t)
        o = original['plain_hazards'][name]
        ck(m is not None and m.group(1) == o['expr'], f'{name} RADIATION {o["expr"]} like the original HazardRegistry.java:{o["line"]} (got {m.group(1) if m else None})')
        value = eval(o['expr'], {'__builtins__': {}}, constants)
        ck(abs(value - PLAIN_VALUES[name]) < 1e-9, f'{name} radiation {value} = {PLAIN_VALUES[name]}')
        plain[name] = {'expr': o['expr'], 'value': value, 'original_line': o['line']}
    ops = edit_ops(frozen_hazard_text, hazard_text)
    ck(all(tag == 'insert' for tag, _, _ in ops), 'HazardRegistry.java differs from the frozen Goal20C start by insertions only (every pre-existing line unchanged)')
    values = {}
    for field, mult in calls:
        base = constants['wst'] * constants['billet'] * mult
        values[field] = {'multiplier': mult, 'hot_radiation': base, 'hot_fire': 5.0, 'cool_radiation': base * neo_body['cool_factor']}
    return {'calls': calls, 'body': neo_body, 'plain': plain, 'values': values, 'constants': constants}


def check_item_class(item_text, client_text, original, ck):
    t = lf(item_text)
    ck('public static final int COOL = 0;' in t and 'public static final int HOT = 1;' in t, 'DepletedFuelItem: COOL 0, HOT 1')
    ck('public static boolean isHot(ItemStack stack) {\n        return MetaHelper.getMeta(stack) > COOL;\n    }' in t, 'DepletedFuelItem.isHot is META > COOL (original getItemDamage() > 0, ItemDepletedFuel.java:35,40)')
    ck('super(properties.component(NtmDataComponents.META.get(), COOL));' in t, 'META 0 (cool) is the item default, so cool stacks carry no META patch')
    ck('stacks.add(MetaHelper.newStack(item, 1, COOL));' in t and 'stacks.add(MetaHelper.newStack(item, 1, HOT));' in t, 'getSubItems lists cool and hot (original :25-29)')
    ck('if(isHot(stack)) tooltipComponents.add(Component.translatable("desc.item.wasteCooling").withStyle(ChatFormatting.GOLD));' in t,
       'only hot waste shows the gold desc.item.wasteCooling tooltip (original :38-41)')
    entity = t[t.index('public @Nullable Entity createEntity('):]
    ck('@Override\n    public int getEntityLifespan(ItemStack itemStack, Level level) {\n        return Integer.MAX_VALUE;\n    }' in t,
       'getEntityLifespan returns Integer.MAX_VALUE, so the dropped item never reaches its despawn age while its age keeps ticking (original ItemNuclearWaste :17-20)')
    ck('item.setInvulnerable(true);' in entity, 'createEntity makes the dropped item invulnerable (original EntityItemWaste :22-30)')
    ck('setUnlimitedLifetime' not in t, 'DepletedFuelItem never calls setUnlimitedLifetime (the lifespan override keeps the age ticking)')
    ck('item.setPickUpDelay(10);' in entity and 'return null;' in entity and 'public boolean hasCustomEntity(ItemStack stack) {\n        return true;' in t,
       'the dropped entity has a 10-tick pickup delay and is adjusted in place, createEntity returns null (original ItemNuclearWaste :17-34)')
    tint = int(original['tint'][0], 16)
    ck(f'0xFF{tint:06X}' in lf(client_text) and '(stack, tintIndex) -> tintIndex == 0 && DepletedFuelItem.isHot(stack) ? 0xFFFFBFA5 : 0xFFFFFFFF,' in lf(client_text),
       f'hot waste is tinted 0x{tint:06X} on layer 0, cool waste is untinted')


def check_edits(frozen, live, ck):
    facts = {}
    for rel, needles in EDITS.items():
        ops = edit_ops(frozen[rel], live[rel])
        ck(all(tag == 'insert' for tag, _, _ in ops), f'{rel} differs from the frozen Goal20C start by insertions only')
        code = [l.strip() for _, _, new in ops for l in new if l.strip() and not l.strip().startswith('//')]
        for needle in needles:
            ck(sum(1 for l in code if l == needle) == 1, f'{rel} inserts {needle!r} exactly once')
        facts[rel] = {'inserted_lines': sum(len(new) for _, _, new in ops), 'code_lines': len(code)}
    return facts


# ---- fuel pool defaults and the example ---------------------------------------------------------------------------------------------------

def check_fuelpool_defaults(fuelpool_text, items, original, ck):
    t = lf(fuelpool_text)
    start = t.index('@Override public void registerDefaults() {')
    rows = re.findall(r'waste\(NtmItems\.(\w+)\);', t[start:t.index('}', start)])
    ck('add(new FuelPoolRecipe(waste.get(), DepletedFuelItem.HOT, waste.get(), 1, DepletedFuelItem.COOL));' in t, 'each default row is waste HOT -> one waste COOL')
    neo = [{'input': 'hbmsntm:' + items[f], 'input_meta': 1, 'output': 'hbmsntm:' + items[f], 'count': 1, 'output_meta': 0} for f in rows]
    want = [{'input': 'hbmsntm:' + r['input'], 'input_meta': r['input_meta'], 'output': 'hbmsntm:' + r['output'], 'count': 1, 'output_meta': 0} for r in original['fuelpool']]
    ck(neo == want, 'the default fuel pool rows equal the original FuelPoolRecipes.java:27-35, in order: ' + str(rows))
    ck(t.count('"hbmFuelpool.json"') == 1, 'the table file is hbmFuelpool.json')
    return neo


def check_example(data, items, defaults, ck):
    """The production row grammar (FuelPoolRecipes.readRecipe) in Python; returns the parsed rows."""
    ck(isinstance(data, dict) and isinstance(data.get('recipes'), list) and isinstance(data.get('comment'), str), 'the example is a {comment, recipes} table')
    known = {'hbmsntm:' + v for v in items.values()}
    rows, keys = [], set()
    for i, row in enumerate(data['recipes']):
        ck(isinstance(row, dict) and isinstance(row.get('input'), list) and isinstance(row.get('output'), list), f'example row {i + 1} has input and output arrays')
        inp, out = row['input'], row['output']
        ck(1 <= len(inp) <= 3 and 1 <= len(out) <= 3, f'example row {i + 1}: input and output have 1..3 elements')
        ck(all(isinstance(x, int) and not isinstance(x, bool) for x in inp[1:] + out[1:]), f'example row {i + 1}: counts and METAs are integers')
        ck(isinstance(inp[0], str) and inp[0] in known and isinstance(out[0], str) and out[0] in known, f'example row {i + 1}: {inp[0]} and {out[0]} are registered NtmItems ids')
        count = inp[1] if len(inp) > 1 else 1
        meta = inp[2] if len(inp) > 2 else 0
        ocount = out[1] if len(out) > 1 else 1
        ometa = out[2] if len(out) > 2 else 0
        ck(count == 1 and 0 <= meta < 32767 and 1 <= ocount <= 64 and ometa >= 0, f'example row {i + 1}: input count 1, exact META (no 32767 wildcard), output count 1..64')
        key = f'{inp[0]}:{meta}'
        ck(key not in keys, f'example row {i + 1}: input {key} appears once')
        keys.add(key)
        rows.append({'input': inp[0], 'input_meta': meta, 'output': out[0], 'count': ocount, 'output_meta': ometa})
    ck(len(rows) <= 4096, 'the example stays within 4096 rows')
    ck(rows[:len(defaults)] == defaults, 'example rows 1-9 equal the default table as writeSnapshot writes it')
    ck(rows[len(defaults):] == [{'input': 'hbmsntm:billet_nuclear_waste', 'input_meta': 0, 'output': 'hbmsntm:nuclear_waste_vitrified', 'count': 1, 'output_meta': 0}],
       'the example appends exactly one illustration row: billet_nuclear_waste -> nuclear_waste_vitrified')
    return rows


# ---- generated files --------------------------------------------------------------------------------------------------------------------

def recipe_json(r, components=None):
    if r['shape'] == 'shaped':
        data = {'type': 'minecraft:crafting_shaped', 'category': 'misc', 'key': {k: {'item': v} for k, v in r['keys'].items()}, 'pattern': r['pattern']}
    else:
        data = {'type': 'minecraft:crafting_shapeless', 'category': 'misc', 'ingredients': sorted(({'item': k} for k, n in r['ingredients'].items() for _ in range(n)), key=json.dumps)}
    result = {'count': r['count'], 'id': r['result']}
    if components: result = {'components': components, **result}
    data['result'] = result
    return data


def normalise(data):
    data = json.loads(json.dumps(data))
    if 'ingredients' in data: data['ingredients'] = sorted(data['ingredients'], key=json.dumps)
    return data


def generated_paths(provider_facts):
    paths = {}
    for name in BREEDING_IDS + ('machine_waste_drum',):
        paths['recipe:' + name] = f'data/hbmsntm/recipe/{name}.json'
        paths['adv:' + name] = f'data/hbmsntm/advancement/recipes/misc/{name}.json'
    for w in provider_facts['waste']:
        name = w['waste'].split(':')[1]
        paths['recipe:' + name] = f'data/hbmsntm/recipe/{name}.json'
        paths['adv:' + name] = f'data/hbmsntm/advancement/recipes/misc/{name}.json'
        paths['model:' + name] = f'assets/hbmsntm/models/item/{name}.json'
    paths.update({'blockstate': 'assets/hbmsntm/blockstates/machine_waste_drum.json', 'block_model': 'assets/hbmsntm/models/block/machine_waste_drum.json',
                  'block_item_model': 'assets/hbmsntm/models/item/machine_waste_drum.json', 'loot': 'data/hbmsntm/loot_table/blocks/machine_waste_drum.json',
                  'pickaxe': 'data/minecraft/tags/block/mineable/pickaxe.json', 'en_us': 'assets/hbmsntm/lang/en_us.json'})
    return paths


def check_generated(gen, paths, provider_facts, original, live_lang, frozen_en, frozen_pickaxe, ck, override=None):
    override = override or {}
    data = {k: override[k] if k in override else json.loads((gen / rel).read_text(encoding='utf-8')) for k, rel in paths.items()}
    for name in BREEDING_IDS + ('machine_waste_drum',):
        r = provider_facts['drum'] if name == 'machine_waste_drum' else provider_facts['breeding'][name]
        ck(normalise(data['recipe:' + name]) == normalise(recipe_json(r)), f'{name}.json equals the provider statement (and so the original recipe)')
        ck(data['adv:' + name] == advancement(name, r['criterion'], r['criterion_item']), f'the {name} advancement unlocks on {r["criterion_item"]}')
    for w in provider_facts['waste']:
        name = w['waste'].split(':')[1]
        want = {'type': 'minecraft:crafting_shapeless', 'category': 'misc', 'ingredients': [{'item': w['rod']}],
                'result': {'components': {'hbmsntm:meta': w['meta']}, 'count': w['count'], 'id': w['waste']}}
        ck(data['recipe:' + name] == want, f'{name}.json: one {w["rod"]} -> {w["count"]} {w["waste"]} with hbmsntm:meta {w["meta"]} (hot)')
        rod = w['rod'].split(':')[1]
        ck(data['adv:' + name] == advancement(name, 'has_' + rod, w['rod']), f'the {name} advancement unlocks on {w["rod"]}')
        texture = original['textures'][name][0]
        ck(data['model:' + name] == {'parent': 'minecraft:item/generated', 'textures': {'layer0': f'hbmsntm:item/{texture}'}},
           f'models/item/{name}.json is item/generated on item/{texture} (original setTextureName {texture})')
    ck(data['blockstate'] == {'variants': {'': {'model': 'hbmsntm:block/machine_waste_drum'}}}, 'blockstates/machine_waste_drum.json is one variant on block/machine_waste_drum')
    ck(data['block_model'] == {'parent': 'minecraft:block/cube_column', 'textures': {'end': 'hbmsntm:block/waste_drum', 'side': 'hbmsntm:block/waste_drum_side'}},
       'models/block/machine_waste_drum.json is cube_column, end waste_drum (top and bottom), side waste_drum_side (original getIcon side 0/1)')
    ck(data['block_item_model'] == {'parent': 'hbmsntm:block/machine_waste_drum'}, 'models/item/machine_waste_drum.json inherits the block model')
    ck(data['loot'] == {'type': 'minecraft:block', 'pools': [{'bonus_rolls': 0.0, 'conditions': [{'condition': 'minecraft:survives_explosion'}],
                                                               'entries': [{'type': 'minecraft:item', 'name': 'hbmsntm:machine_waste_drum'}], 'rolls': 1.0}],
                        'random_sequence': 'hbmsntm:blocks/machine_waste_drum'}, 'the machine_waste_drum loot table drops itself once (dropSelf)')
    values = data['pickaxe']['values']
    ck(values.count('hbmsntm:machine_waste_drum') == 1 and sorted(set(values) - set(frozen_pickaxe['values'])) == ['hbmsntm:machine_waste_drum']
       and set(frozen_pickaxe['values']) <= set(values), 'the pickaxe tag gains exactly hbmsntm:machine_waste_drum')
    en = data['en_us']
    for key in LANG_KEYS:
        ck(en.get(key) == live_lang[key][0], f'en_us.json has {key} = the provider English')
    ck(sorted(set(en) - set(frozen_en)) == sorted(LANG_KEYS) and all(en[k] == frozen_en[k] for k in frozen_en) and len(en) == TOTALS['en'],
       f'en_us.json = the frozen start ({len(frozen_en)}) + the thirteen keys = {TOTALS["en"]} (got {len(en)})')
    return data
