"""Goal20A static recipe evidence: original-source parsers, production registration checks, the declared source edits against the frozen
Goal20A start, the yellowcake chemical plant registration, the thorium smelting recipes and the TH232 ZIRNOX rod crafting recipe (static data,
provider and recipe sources, no execution). Used by verify_goal20a_recipes.py; reads the original repository and the NEO tree read-only.

Every check takes a ck(condition, label) callable so the mutation runs can reuse the same assertions on edited copies without counting them."""
from pathlib import Path
import difflib, json, re

ORIGINAL_CRYSTALLIZER = 'src/main/java/com/hbm/inventory/recipes/CrystallizerRecipes.java'
ORIGINAL_ORE_DICT = 'src/main/java/com/hbm/inventory/OreDictManager.java'
ORIGINAL_CHEMICAL_PLANT = 'src/main/java/com/hbm/inventory/recipes/ChemicalPlantRecipes.java'
ORIGINAL_SMELTING = 'src/main/java/com/hbm/crafting/SmeltingRecipes.java'
ORIGINAL_ROD_RECIPES = 'src/main/java/com/hbm/crafting/RodRecipes.java'
ORIGINAL_ZIRNOX_ROD = 'src/main/java/com/hbm/items/machine/ItemZirnoxRod.java'
WILDCARD = 32767  # MetaHelper.WILDCARD_VALUE: a plain ComparableStack(item, n) matches any meta
# The ore blocks of the original U.ore() / TH232.ore() that NEO ported into the default table, in table order; the deepslate variants exist only in NEO.
PORTED_ORES = {'ore_uranium': ['ORE_URANIUM', 'ORE_URANIUM_DEEPSLATE'], 'ore_uranium_scorched': ['ORE_URANIUM_SCORCHED'],
               'ore_thorium': ['ORE_THORIUM', 'ORE_THORIUM_DEEPSLATE']}
NEW_ROWS = 5

def read(path): return Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n')
def lf(text): return text.replace('\r\n', '\n')
def quiet(condition, label):
    if not condition: raise AssertionError(label)

def registrations(source_root):
    """field -> registered id for NtmItems and NtmBlocks (register / registerNugget style declarations)."""
    items = (source_root / 'com/hbm/items/NtmItems.java').read_text(encoding='utf-8')
    blocks = (source_root / 'com/hbm/blocks/NtmBlocks.java').read_text(encoding='utf-8')
    return ({m.group(1): m.group(2) for m in re.finditer(r'\b([A-Z][A-Z0-9_]*)\s*=\s*(?:ITEMS\.)?register\w*\("([a-z0-9_]+)"', items)},
            {m.group(1): m.group(2) for m in re.finditer(r'\b([A-Z][A-Z0-9_]*)\s*=\s*register\w*\("([a-z0-9_]+)"', blocks)})

def hunks(old, new):
    """Opcodes between two texts as (tag, old lines, new lines, old start, new start) without the equal runs."""
    a, b = lf(old).split('\n'), lf(new).split('\n')
    return [(tag, a[i1:i2], b[j1:j2], i1, j1) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if tag != 'equal']

# ---- original facts ------------------------------------------------------------------------------------------------------------------

def parse_original_crystallizer(source):
    """The :59 sulfur stack, baseTime, and the U / TH232 / PU rows of the original CrystallizerRecipes.registerDefaults."""
    lines = read(source / ORIGINAL_CRYSTALLIZER).split('\n')
    def find(pattern):
        hits = [i for i, l in enumerate(lines) if re.search(pattern, l)]
        assert len(hits) == 1, f'original line for {pattern} found {len(hits)} times'
        return hits[0]
    sulfur = find(r'FluidStack sulfur = new FluidStack\(Fluids\.SULFURIC_ACID, \d+\);')
    base = find(r'final int baseTime = \d+;')
    rows = {}
    for key, pattern in (('U', r'new OreDictStack\(U\.ore\(\)\)'), ('TH232', r'OreDictManager\.TH232\.all\(MaterialShapes\.ONLY_ORE\)'), ('PU', r'new OreDictStack\(PU\.ore\(\)\)')):
        i = find(pattern)
        m = re.search(r'new CrystallizerRecipe\(ModItems\.(crystal_\w+), baseTime\)\.prod\(([\d.]+)F\)(, sulfur)?\);', lines[i])
        assert m, 'original crystallizer row not in the expected shape: ' + lines[i]
        rows[key] = {'source': f'{ORIGINAL_CRYSTALLIZER}:{i + 1}', 'text': lines[i].strip(), 'crystal': m.group(1), 'productivity': float(m.group(2)), 'uses_sulfur_stack': bool(m.group(3))}
    amount = re.search(r'new FluidStack\(Fluids\.(\w+), (\d+)\)', lines[sulfur])
    return {'sulfur': {'source': f'{ORIGINAL_CRYSTALLIZER}:{sulfur + 1}', 'text': lines[sulfur].strip(), 'acid': amount.group(1), 'amount': int(amount.group(2))},
            'base_time': {'source': f'{ORIGINAL_CRYSTALLIZER}:{base + 1}', 'text': lines[base].strip(), 'duration': int(re.search(r'\d+', lines[base].split('=')[1]).group())},
            'rows': rows}

def parse_original_ore_dict(source):
    """The ore lists of U (OreDictManager.java:347) and TH232 (:351), and the billet/dust items the yellowcake and rod recipes use."""
    lines = read(source / ORIGINAL_ORE_DICT).split('\n')
    def frame(name, pattern):
        i = next(n for n, l in enumerate(lines) if re.match(r'\s*' + name + r'\s+\.', l))
        ore = re.search(r'\.ore\(([^)]*)\)', lines[i]).group(1) if '.ore(' in lines[i] else ''
        return {'source': f'{ORIGINAL_ORE_DICT}:{i + 1}', 'text': lines[i].strip(), 'ores': [p.strip() for p in ore.split(',') if p.strip()],
                'billet': (re.search(r'\.billet\((\w+)\)', lines[i]) or [None, None])[1], 'dust': (re.search(r'\.dust\((\w+)\)', lines[i]) or [None, None])[1]}
    return {'U': frame('U', None), 'TH232': frame('TH232', None), 'S': frame('S', None)}

def expected_crystallizer(original, ore_dict, items, blocks):
    """Expected new default rows from the original numbers; the mapping of the ported ore names to NEO fields is the port decision under test."""
    sulfur, base = original['sulfur'], original['base_time']
    rows, omitted = [], []
    for key, frame in (('U', ore_dict['U']), ('TH232', ore_dict['TH232'])):
        row = original['rows'][key]
        crystal_field = row['crystal'].upper()
        assert crystal_field in items, 'NEO item missing for ' + row['crystal']
        for name in frame['ores']:
            if name in PORTED_ORES:
                for field in PORTED_ORES[name]:
                    rows.append({'original_ore': name, 'neo_only_deepslate_variant': field.endswith('_DEEPSLATE'), 'input': 'hbmsntm:' + blocks[field], 'input_field': field, 'input_stub_id': 'hbmsntm:' + field.lower(),
                                 'output': 'hbmsntm:' + items[crystal_field], 'output_field': crystal_field, 'output_stub_id': 'hbmsntm:' + crystal_field.lower(), 'group': key})
            else:
                field = name.upper()
                omitted.append({'original_ore': name, 'group': key, 'neo_field': field, 'neo_registered_id': ('hbmsntm:' + blocks[field]) if field in blocks else None, 'in_default_table': False})
    return {'acid': sulfur['acid'], 'amount': sulfur['amount'], 'duration': base['duration'], 'productivity': original['rows']['U']['productivity'], 'rows': rows}, omitted

def parse_original_chem(source, ore_dict):
    """The original chem.yellowcake registration (:379-382) as items/fluids/output with its OreDict frames mapped through OreDictManager."""
    lines = read(source / ORIGINAL_CHEMICAL_PLANT).split('\n')
    first = next(i for i, l in enumerate(lines) if 'new GenericRecipe("chem.yellowcake")' in l)
    block = lines[first:first + 4]
    setup = re.search(r'\.setup\((\d+), (\d+)\)', block[0])
    stacks = re.findall(r'new OreDictStack\((\w+)\.(billet|dust)\(\), (\d+)\)', block[1])
    fluids = re.findall(r'new FluidStack\(Fluids\.(\w+), (\d+)\)', block[2])
    outputs = re.findall(r'new ItemStack\(ModItems\.(\w+)\)', block[3])
    assert setup and len(stacks) == 2 and len(fluids) == 1 and len(outputs) == 1 and block[3].strip().endswith(');'), 'original chem.yellowcake not in the expected shape'
    frames = {'U': ore_dict['U'], 'S': ore_dict['S']}
    inputs = [{'original': f'OreDictStack({f}.{kind}(), {n})', 'item': frames[f][kind], 'count': int(n)} for f, kind, n in stacks]
    return {'source': f'{ORIGINAL_CHEMICAL_PLANT}:{first + 1}-{first + 4}', 'source_lines': '\n'.join(block), 'setup': [int(setup.group(1)), int(setup.group(2))], 'inputs': inputs,
            'fluids': [[f, int(n)] for f, n in fluids], 'outputs': outputs}

def parse_original_smelting(source):
    lines = read(source / ORIGINAL_SMELTING).split('\n')
    def one(pattern):
        hits = [i for i, l in enumerate(lines) if re.search(pattern, l)]
        assert len(hits) == 1, f'original smelting line for {pattern} found {len(hits)} times'
        i = hits[0]
        return {'source': f'{ORIGINAL_SMELTING}:{i + 1}', 'text': lines[i].strip(), 'experience': float(re.search(r'([\d.]+)F\);', lines[i]).group(1))}
    return {'ore': one(r'addSmelting\(Item\.getItemFromBlock\(ModBlocks\.ore_thorium\), new ItemStack\(ModItems\.ingot_th232\), [\d.]+F\)'),
            'powder': one(r'addSmelting\(ModItems\.powder_thorium, new ItemStack\(ModItems\.ingot_th232\), [\d.]+F\)')}

def zirnox_order(text):
    """Enum constant names in declaration order, from either the original or the NEO ZirnoxType."""
    body = text[text.index('enum '):]
    body = body[body.index('{') + 1:]
    names = []
    for m in re.finditer(r'^\s*([A-Z][A-Z0-9_]*)\s*\(', body, re.M):
        names.append(m.group(1))
        if len(names) == 11: break
    return names

def parse_original_th232_rod(source, ore_dict):
    lines = read(source / ORIGINAL_ROD_RECIPES).split('\n')
    th232 = [i for i, l in enumerate(lines) if 'addZIRNOXRod(TH232, EnumZirnoxType.TH232)' in l]
    helper = [i for i, l in enumerate(lines) if 'public static void addZIRNOXRod(DictFrame mat, EnumZirnoxType num)' in l]
    assert len(th232) == 1 and len(helper) == 1, 'original TH232 rod statement or DictFrame helper not found exactly once'
    i, h = th232[0], helper[0]
    assert 'new ItemStack(ModItems.rod_zirnox, 1, num.ordinal())' in lines[h + 1] and 'ModItems.rod_zirnox_empty, mat.billet(), mat.billet()' in lines[h + 1]
    assert lines[h - 1].strip().startswith('/** Fill ZIRNOX rod with two billets with OreDict')
    text = read(source / ORIGINAL_ZIRNOX_ROD)
    order = zirnox_order(text[text.index('enum EnumZirnoxType'):])
    return {'source': f'{ORIGINAL_ROD_RECIPES}:{i + 1}', 'text': lines[i].strip(), 'helper': f'{ORIGINAL_ROD_RECIPES}:{h + 1}-{h + 2}', 'helper_text': lines[h + 1].strip(),
            'billet': 'TH232.billet()', 'billet_item': ore_dict['TH232']['billet'], 'billet_count': 2, 'type': 'TH232', 'ordinal': order.index('TH232'), 'original_type_order': order,
            'life_tag': False}

# ---- declared edits against the frozen Goal20A start -----------------------------------------------------------------------------------

DOC_OLD = ' * sulfuric acid ore groups (titanium, tungsten, cobalt, rare earth; Goal 18B), 36 ore-block rows. A custom file still replaces'
COMMENT_OLD = ('plus the four sulfuric acid ore groups (titanium, tungsten, cobalt, rare earth), 36 rows; a custom file still replaces the whole table, so an existing custom table does not gain the four sulfuric acid groups automatically (append their rows to keep them).')
COMMENT_NEW = ('plus the four sulfuric acid ore groups (titanium, tungsten, cobalt, rare earth) and the sulfuric acid uranium (stone, deepslate, scorched) and thorium (stone, deepslate) ore rows, 41 rows; a custom file still replaces the whole table, so an existing custom table does not gain the sulfuric acid rows automatically (append their rows to keep them).')

def diff_crystallizer(frozen, live, ck):
    h = hunks(frozen, live)
    ck(len(h) == 5, 'CrystallizerRecipes differs from the frozen start by exactly five hunks (class javadoc, single() helper, registerDefaults javadoc, inserted block, getComment): ' + str([(t, len(o), len(n)) for t, o, n, _, _ in h]))
    doc, helper, defaults, block, comment = h
    doc_text = ' '.join(doc[2])
    ck(doc[0] == 'replace' and len(doc[1]) == 2 and doc[1][0] == DOC_OLD and len(doc[2]) == 3 and '41 ore-block' in doc_text and 'Goal 20A' in doc_text and '36' not in doc_text and '45' not in doc_text
       and doc[2][0].startswith(' * sulfuric acid ore groups (titanium, tungsten, cobalt, rare earth; Goal 18B)') and '(stone, deepslate,' in doc_text and 'scorched) and thorium (stone, deepslate)' in doc_text
       and 'does not gain the sulfuric acid rows automatically' in doc[2][2], 'hunk 1 only restates the class javadoc: 41 rows including the Goal 20A uranium (three ores) and thorium rows')
    helper_text = '\n'.join(helper[2])
    ck(helper[0] == 'insert' and helper_text.count('private void single(Block ore, ItemLike crystal, FluidType acid) {') == 1 and helper_text.count('add(new CrystallizerRecipe(new ComparableStack(ore, 1), new FluidStack(acid, DEFAULT_ACID), new ItemStack(crystal), DEFAULT_DURATION, DEFAULT_PRODUCTIVITY));') == 1
       and helper_text.count('{@link #ore}') == 1 and len([l for l in helper[2] if l.strip()]) == 4, 'hunk 2 inserts only the private single() helper (500 mB acid, DEFAULT_DURATION, DEFAULT_PRODUCTIVITY, one ore block)')
    ck(defaults[0] == 'replace' and len(defaults[1]) == 1 and defaults[2][0] == defaults[1][0].replace('then the four sulfuric acid groups; stone', 'then the four sulfuric acid groups, then the sulfuric acid uranium and thorium ores; stone'),
       'hunk 3 only extends the registerDefaults javadoc line')
    new_lines = block[2]
    ck(block[0] == 'insert' and len(new_lines) == 9 and all(l.strip().startswith('//') for l in new_lines[:6]) and not any(l.strip().startswith('//') for l in new_lines[6:]), 'hunk 4 inserts one 9-line block (six comment lines, three statement lines)')
    live_lines = lf(live).split('\n')
    ck('NtmBlocks.ORE_RARE.get(), NtmBlocks.ORE_RARE_DEEPSLATE.get(), NtmItems.CRYSTAL_RARE.get(), Fluids.SULFURIC_ACID' in live_lines[block[4] - 1] and live_lines[block[4] + len(new_lines)].strip() == '}',
       'the inserted block follows the ORE_RARE row and ends registerDefaults')
    statements = [l.strip() for l in new_lines[6:]]
    expected = ['ore(NtmBlocks.ORE_URANIUM.get(), NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);']         + [f'single(NtmBlocks.{f}.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);' for f in ('ORE_URANIUM_SCORCHED',)]         + ['ore(NtmBlocks.ORE_THORIUM.get(), NtmBlocks.ORE_THORIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_THORIUM.get(), Fluids.SULFURIC_ACID);']
    ck(statements == expected and 'CRYSTAL_PLUTONIUM' not in '\n'.join(new_lines), 'the inserted statements are the uranium ore(), the scorched single() row and the thorium ore(), all under SULFURIC_ACID; no plutonium row')
    ck(comment[0] == 'replace' and len(comment[1]) == 1 and COMMENT_OLD in comment[1][0] and comment[2][0] == comment[1][0].replace(COMMENT_OLD, COMMENT_NEW), 'hunk 5 only changes the getComment default-table sentence (36 -> 41 rows)')
    return {'hunks': 5, 'inserted_lines': len(new_lines), 'inserted_block': new_lines, 'helper': helper[2]}

def diff_chemical(frozen, live, ck):
    h = hunks(frozen, live)
    ck(len(h) == 2, 'ChemicalPlantRecipes differs from the frozen start by exactly two hunks (comment, one input line): ' + str([(t, len(o), len(n)) for t, o, n, _, _ in h]))
    comment, line = h
    ck(comment[0] == 'insert' and len(comment[2]) == 2 and 'ChemicalPlantRecipes.java:379-382' in comment[2][0] and comment[2][0].strip().startswith('//') and comment[2][1].strip().startswith('//'), 'hunk 1 inserts the two-line comment citing ChemicalPlantRecipes.java:379-382')
    ck(line[0] == 'replace' and len(line[1]) == 1 and len(line[2]) == 1 and 'POWDER_URANIUM' in line[1][0] and line[2][0] == line[1][0].replace('NtmItems.POWDER_URANIUM.get(), 2', 'NtmItems.BILLET_URANIUM.get(), 2'),
       'hunk 2 only replaces 2 POWDER_URANIUM by 2 BILLET_URANIUM in the chem.yellowcake inputItems line')
    ck(lf(frozen).split('\n')[line[3] - 1].lstrip().startswith('this.register(new GenericRecipe("chem.yellowcake")'), 'the replaced line belongs to the chem.yellowcake registration')
    return {'hunks': 2, 'comment': comment[2], 'old_line': line[1][0].strip(), 'new_line': line[2][0].strip()}

def diff_provider(frozen, live, ck):
    h = hunks(frozen, live)
    ck(len(h) == 3, 'NtmRecipeProvider differs from the frozen start by exactly three hunks (rod recipe, thorium ore smelting, thorium powder smelting): ' + str([(t, len(o), len(n)) for t, o, n, _, _ in h]))
    rod, ore, powder = h
    live_lines = lf(live).split('\n')
    ck(rod[0] == 'insert' and len(rod[2]) == 7 and '"rod_zirnox_natural_uranium_fuel"' in live_lines[rod[4] - 1] and rod[2][2].strip().startswith('ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.TH232.ordinal()))')
       and '"rod_zirnox_th232"' in rod[2][6] and 'RodRecipes.java:29' in rod[2][0], 'hunk 1 inserts the TH232 rod statement right after rod_zirnox_natural_uranium_fuel, citing RodRecipes.java:29')
    ck(ore[0] == 'replace' and len(ore[1]) == 1 and len(ore[2]) == 3 and 'SmeltingRecipes.java:30' in ore[2][0] and ore[2][2] == ore[1][0].replace('INGOT_THORIUM_FUEL', 'INGOT_TH232'), 'hunk 2 only retargets the thorium ore smelting to INGOT_TH232 (same 0.7F) and adds a comment citing SmeltingRecipes.java:30')
    # Two comment lines (the second one, added after the static review, notes the 0.7F vs 1.0F experience) and the statement.
    ck(powder[0] == 'insert' and len(powder[2]) == 3 and 'SmeltingRecipes.java:84' in powder[2][0] and powder[2][1].strip().startswith('//') and '0.7F' in powder[2][0] + powder[2][1]
       and powder[2][2].strip() == 'addMaterialSmelting(recipeOutput, NtmItems.POWDER_THORIUM.get(), NtmItems.INGOT_TH232.get());'
       and 'POWDER_TENNESSINE' in live_lines[powder[4] - 1] and 'POWDER_TITANIUM' in live_lines[powder[4] + 3], 'hunk 3 inserts addMaterialSmelting(POWDER_THORIUM, INGOT_TH232) between the TENNESSINE and TITANIUM lines')
    return {'hunks': 3, 'rod_lines': rod[2], 'ore_lines': ore[2], 'powder_lines': powder[2]}

# ---- yellowcake -----------------------------------------------------------------------------------------------------------------------

def yellowcake_statement(text):
    text = lf(text)
    assert text.count('"chem.yellowcake"') == 1, 'chem.yellowcake is not registered exactly once'
    m = re.search(r'this\.register\(new GenericRecipe\("chem\.yellowcake"\)\.setupNamed\((\d+), (\d+)L\)\n\s*\.inputItems\((.*?)\)\n\s*\.inputFluids\((.*?)\)\n\s*\.outputItems\((.*?)\)\);', text, re.S)
    assert m, 'chem.yellowcake registration not found in the expected shape'
    return m

def check_yellowcake(live_text, original, items, ck):
    m = yellowcake_statement(live_text)
    inputs = [(f, int(n)) for f, n in re.findall(r'new ComparableStack\(NtmItems\.(\w+)\.get\(\), (\d+)\)', m.group(3))]
    fluids = [(f, int(n)) for f, n in re.findall(r'new FluidStack\(Fluids\.(\w+), (\d+)\)', m.group(4))]
    outputs = re.findall(r'new ItemStack\(NtmItems\.(\w+)\.get\(\)\)', m.group(5))
    mapped = [(row['item'].upper(), row['count']) for row in original['inputs']]
    ck((int(m.group(1)), int(m.group(2))) == tuple(original['setup']) == (250, 500), 'chem.yellowcake setupNamed(250, 500L) equals the original setup(250, 500)')
    ck(inputs == [('BILLET_URANIUM', 2), ('SULFUR', 2)] == mapped, 'chem.yellowcake inputs are 2 BILLET_URANIUM and 2 SULFUR (the original U.billet() and S.dust())')
    ck('POWDER_URANIUM' not in m.group(0), 'no POWDER_URANIUM inside the chem.yellowcake registration')
    ck(fluids == [('PEROXIDE', 500)] == [(f, n) for f, n in original['fluids']], 'chem.yellowcake takes 500 mB PEROXIDE like the original')
    ck(outputs == ['POWDER_YELLOWCAKE'] == [o.upper() for o in original['outputs']] and 'POWDER_YELLOWCAKE' in items, 'chem.yellowcake outputs 1 POWDER_YELLOWCAKE')
    ck(lf(live_text).split('\n')[lf(live_text)[:m.start()].count('\n') - 2].strip().startswith('// Original ChemicalPlantRecipes.java:379-382'), 'the comment above the registration cites the original lines 379-382')
    return {'setup': [int(m.group(1)), int(m.group(2))], 'inputs': inputs, 'fluids': fluids, 'outputs': outputs, 'statement': m.group(0)}

def check_chem_loader(chem_text, loader_text, ck):
    """A custom hbmChemicalPlant.json replaces the whole default table (SerializableRecipe.initialize), so a player's custom table does not change."""
    loader = lf(loader_text)
    ck('@Override public String getFileName() { return "hbmChemicalPlant.json"; }' in lf(chem_text) and 'recipeHandlers.add(ChemicalPlantRecipes.INSTANCE);' in loader, 'ChemicalPlantRecipes is a SerializableRecipe handler for hbmChemicalPlant.json')
    start = loader.index('public static void initialize()')
    body = loader[start:loader.index('private static void notifyRecipeListeners', start)]
    read_at = body.index('if(recipe.readRecipeFile(recFile)) {')
    success = body[read_at:body.index('} else {', read_at)]
    ck(body.index('recipe.deleteRecipes();') < read_at and 'recipe.modified = true;' in success and 'registerDefaults' not in success, 'initialize clears the handler, then a readable custom file is the whole table: no default registration on success')
    ck(body.count('recipe.registerDefaults();') == 2 and 'Falling back to default recipes' in body[read_at:] and 'No recipe file found, registering defaults' in body, 'defaults come back only when the file is unusable or absent')
    return {'file': 'hbmChemicalPlant.json', 'loader': 'SerializableRecipe.initialize'}

# ---- thorium smelting -----------------------------------------------------------------------------------------------------------------

SMELT_FILES = {'ore_thorium': 'ingot_th232_from_smelting_ore_thorium', 'ore_thorium_deepslate': 'ingot_th232_from_smelting_ore_thorium_deepslate', 'powder_thorium': 'powder_thorium_to_ingot_th232'}
OLD_SMELT_FILES = ('data/hbmsntm/recipe/ingot_thorium_fuel_from_smelting_ore_thorium.json', 'data/hbmsntm/recipe/ingot_thorium_fuel_from_smelting_ore_thorium_deepslate.json',
                   'data/hbmsntm/advancement/recipes/misc/ingot_thorium_fuel_from_smelting_ore_thorium.json', 'data/hbmsntm/advancement/recipes/misc/ingot_thorium_fuel_from_smelting_ore_thorium_deepslate.json')
FUEL_KEPT = ('ingot_thorium_fuel_from_nugget_thorium_fuel', 'ingot_thorium_fuel_from_3_billet_thorium_fuel', 'ingot_thorium_fuel_from_block_thorium_fuel')

def load_smelting(generated_root):
    recipes = generated_root / 'data/hbmsntm/recipe'
    def load(name): return json.loads((recipes / (name + '.json')).read_text(encoding='utf-8'))
    return {'smelting': {k: load(v) for k, v in SMELT_FILES.items()}, 'old_present': [p for p in OLD_SMELT_FILES if (generated_root / p).exists()],
            'fuel_kept': {n: load(n) for n in FUEL_KEPT}, 'crystal': load('ingot_th232_from_crystal_thorium')}

def smelting_json(ingredient):
    return {'type': 'minecraft:smelting', 'category': 'misc', 'cookingtime': 200, 'experience': 0.7, 'ingredient': {'item': 'hbmsntm:' + ingredient}, 'result': {'count': 1, 'id': 'hbmsntm:ingot_th232'}}

def check_smelting(provider_text, data, original, ck):
    provider = lf(provider_text)
    for key in ('ore_thorium', 'ore_thorium_deepslate', 'powder_thorium'):
        ck(data['smelting'][key] == smelting_json(key), f'{SMELT_FILES[key]}.json is smelting {key} -> 1 ingot_th232, cookingtime 200, experience 0.7')
    ck(data['old_present'] == [], 'the four old ingot_thorium_fuel_from_smelting_ore_thorium(_deepslate) recipe and advancement files are absent')
    ore_calls = re.findall(r'^\s*addOreSmelting\(recipeOutput, NtmBlocks\.ORE_THORIUM\.get\(\), NtmBlocks\.ORE_THORIUM_DEEPSLATE\.get\(\), NtmItems\.(\w+)\.get\(\), ([\d.]+)F\);$', provider, re.M)
    ck(ore_calls == [('INGOT_TH232', '0.7')], 'provider ore smelting of ORE_THORIUM and its deepslate targets INGOT_TH232 at 0.7F: ' + str(ore_calls))
    ck(not re.search(r'addOreSmelting\([^\n]*INGOT_THORIUM_FUEL', provider), 'the provider has no addOreSmelting line targeting INGOT_THORIUM_FUEL')
    ck(len(re.findall(r'^\s*addMaterialSmelting\(recipeOutput, NtmItems\.POWDER_THORIUM\.get\(\), NtmItems\.INGOT_TH232\.get\(\)\);$', provider, re.M)) == 1, 'the provider smelts POWDER_THORIUM to INGOT_TH232 exactly once')
    for name, recipe in data['fuel_kept'].items():
        ck(recipe['result']['id'] == 'hbmsntm:ingot_thorium_fuel', f'{name}.json still produces ingot_thorium_fuel (identity kept)')
    ck(data['crystal']['type'] == 'minecraft:smelting' and data['crystal']['ingredient'] == {'item': 'hbmsntm:crystal_thorium'} and data['crystal']['result'] == {'count': 2, 'id': 'hbmsntm:ingot_th232'}, 'crystal_thorium smelting to ingot_th232 still exists (2 per crystal)')
    ck(original['ore']['text'].endswith('3.0F);') and original['powder']['text'].endswith('1.0F);') and 0.7 != original['ore']['experience'], 'original experience 3.0F (ore) and 1.0F (powder) differ from NEO uniform 0.7F by design')
    return {'original': original, 'neo_experience': 0.7, 'ore_calls': ore_calls}

# ---- TH232 rod ------------------------------------------------------------------------------------------------------------------------

def provider_rod_facts(text):
    """The ZIRNOX rod shapeless statements of NtmRecipeProvider keyed on the saved recipe id."""
    out = {}
    for m in re.finditer(r'ShapelessRecipeBuilder\.shapeless\(RecipeCategory\.MISC, MetaHelper\.newStack\(NtmItems\.ROD_ZIRNOX\.get\(\), (\d+), ZirnoxType\.(\w+)\.ordinal\(\)\)\)\s*'
                         r'\.requires\(NtmItems\.ROD_ZIRNOX_EMPTY\.get\(\)\)\s*\.requires\(NtmItems\.(\w+)\.get\(\), (\d+)\)\s*\.unlockedBy\([^\n]*\)\s*\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\("hbmsntm", "(\w+)"\)\);', lf(text)):
        out[m.group(5)] = {'count': int(m.group(1)), 'type': m.group(2), 'billet': m.group(3), 'billet_count': int(m.group(4))}
    return out

def check_rod(rod_json, provider_text, neo_order, original, ck):
    facts = provider_rod_facts(provider_text)
    ck(rod_json['type'] == 'minecraft:crafting_shapeless', 'rod_zirnox_th232 recipe is shapeless')
    ck(rod_json['ingredients'] == [{'item': 'hbmsntm:rod_zirnox_empty'}, {'item': 'hbmsntm:billet_th232'}, {'item': 'hbmsntm:billet_th232'}], 'rod ingredients are exactly the empty rod and two billet_th232')
    result = rod_json['result']
    ck(result['id'] == 'hbmsntm:rod_zirnox' and result['count'] == 1, 'rod result is 1 x rod_zirnox')
    ordinal = neo_order.index('TH232')
    ck(ordinal == original['ordinal'] == 2 and neo_order == original['original_type_order'], 'ZirnoxType TH232 is ordinal 2 in NEO and the original enum order is identical')
    ck(result.get('components') == {'hbmsntm:meta': ordinal}, f'rod META equals ZirnoxType.TH232 ordinal {ordinal} and is the only component')
    ck('life' not in json.dumps(result) and 'custom_data' not in json.dumps(result), 'rod result has no life custom data')
    ck(set(facts) == {'rod_zirnox_natural_uranium_fuel', 'rod_zirnox_th232'}, 'the provider has exactly the natural uranium and th232 shapeless rod statements: ' + str(sorted(facts)))
    mine = facts['rod_zirnox_th232']
    ck(mine['type'] == original['type'] == 'TH232' and mine['count'] == result['count'] == 1, 'provider rod type is TH232, count 1')
    ck(mine['billet'] == 'BILLET_TH232' and mine['billet_count'] == original['billet_count'] == 2 and original['billet_item'] == 'billet_th232', 'provider requires two BILLET_TH232')
    return mine

def recipe_results(generated_root):
    """Every generated recipe JSON (any namespace) whose result is a ZIRNOX rod item: {relative path: result}."""
    found = {}
    for path in sorted((generated_root / 'data').rglob('*.json')):
        rel = path.relative_to(generated_root).as_posix()
        if '/recipe/' not in rel: continue
        data = json.loads(path.read_text(encoding='utf-8'))
        result = data.get('result')
        ident = result.get('id') or result.get('item') if isinstance(result, dict) else result
        if isinstance(ident, str) and ident.startswith('hbmsntm:rod_zirnox'): found[rel] = {'id': ident, 'components': result.get('components')}
    return found

def generated_tree(root, generated_root, start_files, copy_root):
    """Generated files now against the frozen start (hash list): added, removed, changed existing. A changed file with a stored copy is compared with CRLF normalised."""
    now = {p.relative_to(root).as_posix() for p in generated_root.rglob('*') if p.is_file()}
    start = {k for k in start_files if k.startswith('src/generated/resources/')}
    import hashlib
    def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    changed = []
    for p in sorted(now & start):
        if sha(root / p) == start_files[p]: continue
        copy = copy_root / p
        if copy.is_file() and (root / p).read_bytes().replace(b'\r\n', b'\n') == copy.read_bytes().replace(b'\r\n', b'\n'): continue
        changed.append(p)
    return sorted(now - start), sorted(start - now), changed
