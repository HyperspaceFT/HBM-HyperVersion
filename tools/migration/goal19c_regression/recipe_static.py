"""Goal19C static recipe evidence: original-source parsers, production registration checks, the generated ZIRNOX rod crafting recipes and the
material chains (static data and provider/recipe sources, no execution). Used by verify_goal19c_recipes.py; reads the original repository and the
NEO tree read-only.

Crafting reasoning asserted here (not merely expected): the natural uranium fuel rod result JSON has no "components" block because
EnumMultiItem gives ZirnoxRodItem the default component hbmsntm:meta = 0 (EnumMultiItem.java:26), NATURAL_URANIUM_FUEL is ordinal 0 in both
the original and NEO enum order, and MetaHelper.getMeta falls back to 0, so the datagen patch against the item prototype is empty; every other
ordinal would differ from the default and need an explicit component (the existing recipe/54.json barbed-wire result shows the explicit form for
an item without that default)."""
from pathlib import Path
import json, re

WILDCARD = 32767  # MetaHelper.WILDCARD_VALUE: a plain ComparableStack(item, n) matches any meta (RecipesCommon.java:68-72)
ORIGINAL_ASSEMBLY = 'src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
ORIGINAL_CENTRIFUGE = 'src/main/java/com/hbm/inventory/recipes/CentrifugeRecipes.java'
ORIGINAL_ORE_DICT = 'src/main/java/com/hbm/inventory/OreDictManager.java'
ORIGINAL_ROD_RECIPES = 'src/main/java/com/hbm/crafting/RodRecipes.java'
ORIGINAL_ZIRNOX_ROD = 'src/main/java/com/hbm/items/machine/ItemZirnoxRod.java'
STACK = re.compile(r'new (OreDictStack|ComparableStack)\(([^()]*(?:\([^()]*\))?[^()]*)\)')

# Original expression -> NEO input. The mapping is the port decision under test; the numbers come from the original source.
ASSEMBLY_MAPPING = {
    'STEEL.shell()': ('item', 'SHELL_STEEL'),
    'STEEL.pipe()': ('item', 'PIPE_STEEL'),
    'B.ingot()': ('item', 'INGOT_BORON'),
    'GRAPHITE.ingot()': ('item', 'INGOT_GRAPHITE'),
    'RUBBER.ingot()': ('item', 'INGOT_RUBBER'),
    'ANY_CONCRETE.any()': ('tag', 'ntm:any_concrete'),
    'ModItems.circuit+BASIC': ('item', 'CIRCUIT_INTEGRATED_BOARD'),
}
ASSEMBLY_ORDER = ['STEEL.shell()', 'STEEL.pipe()', 'B.ingot()', 'GRAPHITE.ingot()', 'RUBBER.ingot()', 'ANY_CONCRETE.any()', 'ModItems.circuit+BASIC']
CENTRIFUGE_MAPPING = {'powder_cobalt_tiny': 'POWDER_COBALT_TINY', 'powder_boron_tiny': 'POWDER_BORON_TINY', 'powder_niobium_tiny': 'POWDER_NIOBIUM_TINY', 'nugget_zirconium': 'NUGGET_ZIRCONIUM'}
CENTRIFUGE_INPUT_FIELD = 'RARE_EARTH_ORE_CHUNK'  # original DictFrame.fromOne(ModItems.chunk_ore, EnumChunkType.RARE)

def read(path): return Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n')

def registrations(source_root):
    """field -> registered id for NtmItems and NtmBlocks (register / registerNugget style declarations)."""
    items = (source_root / 'com/hbm/items/NtmItems.java').read_text(encoding='utf-8')
    blocks = (source_root / 'com/hbm/blocks/NtmBlocks.java').read_text(encoding='utf-8')
    return ({m.group(1): m.group(2) for m in re.finditer(r'\b([A-Z][A-Z0-9_]*)\s*=\s*(?:ITEMS\.)?register\w*\("([a-z0-9_]+)"', items)},
            {m.group(1): m.group(2) for m in re.finditer(r'\b([A-Z][A-Z0-9_]*)\s*=\s*register\w*\("([a-z0-9_]+)"', blocks)})

def resolve(field, kind, items, blocks):
    """(production id, stand-in id): the stand-in registry derives its id from the field name."""
    table = blocks if kind == 'block' else items
    if field not in table: raise SystemExit(f'Production registration of {field} not found')
    return 'hbmsntm:' + table[field], 'hbmsntm:' + field.lower()

def parse_stacks(line):
    result = []
    for kind, inner in STACK.findall(line):
        parts = [p.strip() for p in inner.split(',')]
        key = parts[0] + ('+BASIC' if len(parts) > 2 and 'EnumCircuitType.BASIC' in parts[2] else '')
        result.append({'original': f'{kind}({inner})', 'original_kind': kind, 'key': key, 'count': int(parts[1])})
    return result

def parse_assembly(source, items, blocks):
    """Expected ass.cirnox facts from the original AssemblyMachineRecipes.java (the normal branch only; inputItemsEx is not migrated)."""
    text = read(source / ORIGINAL_ASSEMBLY)
    lines = text.split('\n')
    first = next(i for i, l in enumerate(lines) if 'new GenericRecipe("ass.cirnox")' in l)
    assert text.count('"ass.cirnox"') == 1 and '.inputItems(' in lines[first + 1] and '.inputItemsEx(' in lines[first + 2], 'original ass.cirnox statement not found in the expected shape'
    setup = re.search(r'\.setup\((\d+), (\d+)\)', lines[first]); output = re.search(r'new ItemStack\(ModBlocks\.(\w+), (\d+)\)', lines[first])
    assert setup and output and output.group(1) == 'reactor_zirnox', 'original setup/output not recognised'
    normal = parse_stacks(lines[first + 1])
    assert [s['key'] for s in normal] == ASSEMBLY_ORDER, 'original normal inputs are not the expected expressions in order: ' + str([s['key'] for s in normal])
    rows = []
    for s in normal:
        kind, ident = ASSEMBLY_MAPPING[s['key']]
        if kind == 'tag': rows.append({**s, 'kind': 'tag', 'id': ident, 'stub_id': ident, 'meta': -1, 'field': None})
        else:
            production, stub = resolve(ident, 'item', items, blocks)
            rows.append({**s, 'kind': 'item', 'id': production, 'stub_id': stub, 'meta': WILDCARD, 'field': 'NtmItems.' + ident})
    production, stub = resolve('REACTOR_ZIRNOX', 'block', items, blocks)
    ex = parse_stacks(lines[first + 2])
    return {'source': f'{ORIGINAL_ASSEMBLY}:{first + 1}-{first + 3}', 'source_lines': '\n'.join(lines[first:first + 3]), 'name': 'ass.cirnox',
            'duration': int(setup.group(1)), 'power': int(setup.group(2)),
            'output': {'id': production, 'stub_id': stub, 'count': int(output.group(2)), 'original': 'ModBlocks.' + output.group(1), 'field': 'NtmBlocks.REACTOR_ZIRNOX'},
            'inputs': rows, 'input_items_ex': {'migrated': False, 'reason': 'NEO has no item_expensive (the original expensive branch uses EnumExpensiveType items)', 'stacks': [s['original'] for s in ex]},
            'expected_values': {'duration': 600, 'power': 100, 'counts': [4, 8, 8, 16, 16, 16, 4], 'output_count': 1},
            'expected_base_rows': {'528=false': None, '528=true': None}}

def parse_boron(source):
    """The mapping B.ingot() -> boron (OreDictManager.java:196)."""
    lines = read(source / ORIGINAL_ORE_DICT).split('\n')
    i = next(n for n, l in enumerate(lines) if re.match(r'\s*public static final DictFrame B = new DictFrame\("Boron"\);', l))
    return {'source': f'{ORIGINAL_ORE_DICT}:{i + 1}', 'text': lines[i].strip()}

def parse_centrifuge(source, items):
    """Expected rare earth chunk row from the original CentrifugeRecipes.java (first recipes.put in registerDefaults)."""
    lines = read(source / ORIGINAL_CENTRIFUGE).split('\n')
    first = next(i for i, l in enumerate(lines) if 'EnumChunkType.RARE' in l and 'recipes.put' in l)
    block = lines[first:first + 5]
    assert 'new ItemStack[] {' in block[0] and block[4].strip().endswith('});'), 'original chunk row not in the expected shape'
    outputs = []
    for line in block[1:]:
        m = re.search(r'new ItemStack\(ModItems\.(\w+), (\d+)\)', line)
        assert m and m.group(1) in CENTRIFUGE_MAPPING, 'unmapped original output: ' + line
        production, stub = resolve(CENTRIFUGE_MAPPING[m.group(1)], 'item', items, {})
        outputs.append({'original': 'ModItems.' + m.group(1), 'id': production, 'stub_id': stub, 'count': int(m.group(2)), 'field': 'NtmItems.' + CENTRIFUGE_MAPPING[m.group(1)]})
    production, stub = resolve(CENTRIFUGE_INPUT_FIELD, 'item', items, {})
    return {'source': f'{ORIGINAL_CENTRIFUGE}:{first + 1}-{first + 5}', 'source_lines': '\n'.join(block),
            'input': {'original': 'ComparableStack(DictFrame.fromOne(ModItems.chunk_ore, EnumChunkType.RARE))', 'id': production, 'stub_id': stub, 'count': 1, 'meta': 0, 'field': 'NtmItems.' + CENTRIFUGE_INPUT_FIELD},
            'outputs': outputs, 'expected_values': {'counts': [2, 2, 2, 3], 'ids': [o['id'] for o in outputs]},
            'note': 'The original registers the chunk row first and as an item-with-META key; NEO appends it last (the 76 frozen rows keep their order) as a plain item (rare_earth_ore_chunk, META 0)'}

def neo_chunk_row(text):
    """The Java statement of the chunk row in the live CentrifugeRecipes source: (comment lines, parsed stacks)."""
    m = re.search(r'private void registerChunkRecipes\(\) \{\n\s*(setRecipe\(.*?\);)\n\s*\}', text, re.S)
    assert m, 'registerChunkRecipes not found in the live CentrifugeRecipes'
    stacks = re.findall(r'stack\(NtmItems\.(\w+)\.get\(\), (\d+)\)', m.group(1))
    return {'statement': m.group(1), 'stacks': [(f, int(n)) for f, n in stacks]}

# ---- crafting (generated JSON) --------------------------------------------------------------------------------------------------------

def zirnox_order(text):
    """Enum constant names in declaration order, from either the original or the NEO ZirnoxType."""
    body = text[text.index('enum ') :]
    body = body[body.index('{') + 1 :]
    names = []
    for m in re.finditer(r'^\s*([A-Z][A-Z0-9_]*)\s*\(', body, re.M):
        names.append(m.group(1))
        if len(names) == 11: break
    return names

def provider_facts(text):
    """Static facts of the two ZIRNOX rod statements in NtmRecipeProvider (count of the empty rod, the META ordinal name of the natural rod)."""
    empty = re.search(r'ShapedRecipeBuilder\.shaped\(RecipeCategory\.MISC, NtmItems\.ROD_ZIRNOX_EMPTY\.get\(\), (\d+)\)\s*\.pattern\("([^"]*)"\)\s*\.pattern\("([^"]*)"\)\s*\.pattern\("([^"]*)"\)\s*'
                      r'\.define\(\'Z\', NtmItems\.(\w+)\.get\(\)\)\s*\.define\(\'B\', NtmItems\.(\w+)\.get\(\)\)', text)
    natural = re.search(r'ShapelessRecipeBuilder\.shapeless\(RecipeCategory\.MISC, MetaHelper\.newStack\(NtmItems\.ROD_ZIRNOX\.get\(\), (\d+), ZirnoxType\.(\w+)\.ordinal\(\)\)\)\s*'
                        r'\.requires\(NtmItems\.ROD_ZIRNOX_EMPTY\.get\(\)\)\s*\.requires\(NtmItems\.(\w+)\.get\(\), (\d+)\)', text)
    if not empty or not natural: raise AssertionError('provider ZIRNOX rod statements not found in the expected shape')
    return {'empty': {'count': int(empty.group(1)), 'pattern': [empty.group(2), empty.group(3), empty.group(4)], 'Z': empty.group(5), 'B': empty.group(6)},
            'natural': {'count': int(natural.group(1)), 'type': natural.group(2), 'empty_rod_ingredient': 'ROD_ZIRNOX_EMPTY', 'billet': natural.group(3), 'billet_count': int(natural.group(4))},
            'rod_zirnox_recipe_statements': len(re.findall(r'NtmItems\.ROD_ZIRNOX(?:_\w+)?\.get\(\)', text))}

def parse_original_rods(source):
    text = read(source / ORIGINAL_ROD_RECIPES)
    lines = text.split('\n')
    empty = next(i for i, l in enumerate(lines) if 'ModItems.rod_zirnox_empty, 4' in l)
    natural = next(i for i, l in enumerate(lines) if 'addZIRNOXRod(U, EnumZirnoxType.NATURAL_URANIUM_FUEL)' in l)
    helper = next(i for i, l in enumerate(lines) if 'public static void addZIRNOXRod(DictFrame mat, EnumZirnoxType num)' in l)
    assert re.search(r'"Z Z", "ZBZ", "Z Z", \'Z\', ZR\.nugget\(\), \'B\', BE\.ingot\(\)', lines[empty]), lines[empty]
    assert 'new ItemStack(ModItems.rod_zirnox, 1, num.ordinal())' in lines[helper + 1] and 'ModItems.rod_zirnox_empty, mat.billet(), mat.billet()' in lines[helper + 1]
    assert lines[helper - 1].strip().startswith('/** Fill ZIRNOX rod with two billets with OreDict')
    other_rods = [l.strip() for l in lines if 'addZIRNOXRod(' in l and 'public static' not in l]
    order = zirnox_order(read(source / ORIGINAL_ZIRNOX_ROD)[read(source / ORIGINAL_ZIRNOX_ROD).index('enum EnumZirnoxType'):])
    return {'empty': {'source': f'{ORIGINAL_ROD_RECIPES}:{empty + 1}', 'text': lines[empty].strip(), 'count': 4, 'pattern': ['Z Z', 'ZBZ', 'Z Z'], 'Z': 'ZR.nugget()', 'B': 'BE.ingot()'},
            'natural': {'source': f'{ORIGINAL_ROD_RECIPES}:{natural + 1}', 'text': lines[natural].strip(), 'helper': f'{ORIGINAL_ROD_RECIPES}:{helper + 1}-{helper + 2}', 'billet': 'U.billet()', 'billet_count': 2, 'type': 'NATURAL_URANIUM_FUEL',
                        'ordinal': order.index('NATURAL_URANIUM_FUEL')},
            'all_zirnox_rod_statements': other_rods, 'original_type_order': order}

def check_crafting(empty_json, natural_json, provider_text, neo_order, original_rods):
    """Generated-recipe assertions; raises AssertionError with a fragment naming the failed fact. Works on copies for the mutation checks."""
    facts = provider_facts(provider_text)
    # empty rod
    assert empty_json['type'] == 'minecraft:crafting_shaped', 'empty rod recipe is shaped'
    assert empty_json['pattern'] == ['Z Z', 'ZBZ', 'Z Z'], 'empty rod pattern is Z Z/ZBZ/Z Z'
    assert empty_json['key'] == {'Z': {'item': 'hbmsntm:nugget_zirconium'}, 'B': {'item': 'hbmsntm:ingot_beryllium'}}, 'empty rod key is Z zirconium nugget, B beryllium ingot'
    assert empty_json['result'] == {'count': 4, 'id': 'hbmsntm:rod_zirnox_empty'}, 'empty rod result is 4 x rod_zirnox_empty'
    assert facts['empty']['count'] == empty_json['result']['count'] == original_rods['empty']['count'], 'provider count of the empty rod equals the generated result count and the original 4'
    assert facts['empty']['pattern'] == original_rods['empty']['pattern'] and facts['empty']['Z'] == 'NUGGET_ZIRCONIUM' and facts['empty']['B'] == 'INGOT_BERYLLIUM', 'provider empty rod pattern and ingredients match the original'
    # natural uranium rod
    assert natural_json['type'] == 'minecraft:crafting_shapeless', 'natural rod recipe is shapeless'
    assert natural_json['ingredients'] == [{'item': 'hbmsntm:rod_zirnox_empty'}, {'item': 'hbmsntm:billet_uranium'}, {'item': 'hbmsntm:billet_uranium'}], 'natural rod ingredients are the empty rod and two uranium billets'
    result = natural_json['result']
    assert result['id'] == 'hbmsntm:rod_zirnox' and result['count'] == 1, 'natural rod result is 1 x rod_zirnox'
    ordinal = neo_order.index(facts['natural']['type'])
    assert facts['natural']['type'] == original_rods['natural']['type'] == 'NATURAL_URANIUM_FUEL', 'provider rod type is NATURAL_URANIUM_FUEL'
    components = result.get('components')
    assert not components or set(components) == {'hbmsntm:meta'}, 'natural rod result carries no component besides hbmsntm:meta and no life data'
    assert ordinal == original_rods['natural']['ordinal'] == 0, 'natural rod META is ordinal 0 in both enums'
    assert 'life' not in json.dumps(result) and 'custom_data' not in json.dumps(result), 'natural rod result has no life custom data'
    assert (components or {}).get('hbmsntm:meta', 0) == ordinal, 'generated META equals the provider ordinal (absent components mean the default component 0)'
    assert facts['natural']['billet'] == 'BILLET_URANIUM' and facts['natural']['billet_count'] == 2 == original_rods['natural']['billet_count'], 'provider requires two uranium billets'
    assert facts['natural']['count'] == result['count'] == 1, 'provider natural rod count is 1'
    assert neo_order == original_rods['original_type_order'], 'NEO ZirnoxType order equals the original EnumZirnoxType order (META ordinals unchanged)'
    return facts

def recipe_results(generated_root):
    """Every generated recipe JSON (any namespace) whose result is a ZIRNOX rod item: {relative path: result}."""
    found = {}
    for path in sorted((generated_root / 'data').rglob('*.json')):
        rel = path.relative_to(generated_root).as_posix()
        if '/recipe/' not in rel: continue
        data = json.loads(path.read_text(encoding='utf-8'))
        result = data.get('result')
        ident = result.get('id') or result.get('item') if isinstance(result, dict) else result
        if isinstance(ident, str) and ident.startswith('hbmsntm:rod_zirnox'): found[rel] = result
    return found

def uses_zirnox(generated_root):
    """Generated recipes that use a ZIRNOX rod as an ingredient (informational)."""
    used = []
    for path in sorted((generated_root / 'data').rglob('*.json')):
        rel = path.relative_to(generated_root).as_posix()
        if '/recipe/' in rel and 'rod_zirnox' in path.read_text(encoding='utf-8') and not rel.endswith(('rod_zirnox_empty.json', 'rod_zirnox_natural_uranium_fuel.json')): used.append(rel)
    return used

# ---- materials ------------------------------------------------------------------------------------------------------------------------

def recipe_index(generated_root):
    """result item name -> [{file, type, count, ingredients}] over data/hbmsntm/recipe."""
    index = {}
    for path in sorted((generated_root / 'data/hbmsntm/recipe').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        result = data.get('result')
        ident = (result.get('id') or result.get('item')) if isinstance(result, dict) else result
        if not isinstance(ident, str) or not ident.startswith('hbmsntm:'): continue
        ingredients = []
        if 'ingredient' in data: ingredients.append(data['ingredient'])
        if 'ingredients' in data: ingredients.extend(data['ingredients'])
        if 'key' in data: ingredients.extend(data['key'].values())
        index.setdefault(ident[8:], []).append({'file': path.relative_to(generated_root).as_posix(), 'type': data.get('type'), 'count': result.get('count', 1) if isinstance(result, dict) else 1,
                                               'inputs': sorted({ref for i in ingredients for ref in ((i.get('item') or i.get('tag') or json.dumps(i, sort_keys=True)) if isinstance(i, dict) else json.dumps(i, sort_keys=True),)}), 'pattern': data.get('pattern')})
    return index

def find_line(path, needle):
    for i, line in enumerate(path.read_text(encoding='utf-8').split('\n'), 1):
        if needle in line: return i
    return None

def materials(root, generated_root):
    """Static material chains for the ZIRNOX normal-acquisition path. Every claim cites a generated file or a source line; missing links are gaps."""
    source = root / 'src/main/java/com/hbm'
    index = recipe_index(generated_root)
    gaps = []
    def route(item, prefer=None):
        routes = index.get(item, [])
        if not routes: return None
        if prefer: routes = [r for r in routes if prefer in r['file']] or routes
        return routes
    def java(rel, needle):
        line = find_line(source / rel, needle)
        if line is None: gaps.append(f'{rel} does not contain {needle}')
        return f'src/main/java/com/hbm/{rel}:{line}' if line else 'MISSING'
    def gen(rel):
        path = generated_root / rel
        if not path.is_file(): gaps.append('missing generated file ' + rel)
        return 'src/generated/resources/' + rel
    result = {}
    # rare earth ore -> chunk
    loot = {}
    for name in ('ore_rare', 'ore_rare_deepslate'):
        data = json.loads((generated_root / f'data/hbmsntm/loot_table/blocks/{name}.json').read_text(encoding='utf-8'))
        entries = json.dumps(data)
        loot[name] = {'file': gen(f'data/hbmsntm/loot_table/blocks/{name}.json'), 'drops_rare_earth_ore_chunk': 'hbmsntm:rare_earth_ore_chunk' in entries, 'silk_touch_drops_block': f'hbmsntm:{name}' in entries,
                      'fortune_ore_drops': 'minecraft:ore_drops' in entries, 'count': 'uniform 1..1 (set_count) plus fortune ore_drops'}
        if not loot[name]['drops_rare_earth_ore_chunk']: gaps.append(f'{name} loot does not drop rare_earth_ore_chunk')
    result['rare_earth_ore'] = {'loot': loot, 'provider': java('datagen/NtmBlockLootTableProvider.java', 'NtmBlocks.ORE_RARE.get(), block -> this.oreDrop(block, NtmItems.RARE_EARTH_ORE_CHUNK.get())'),
                                'smelting': [r['file'] for r in index.get('rare_earth_ore_chunk', [])],
                                'crystallizer_row': java('inventory/recipes/CrystallizerRecipes.java', 'NtmBlocks.ORE_RARE.get(), NtmBlocks.ORE_RARE_DEEPSLATE.get(), NtmItems.CRYSTAL_RARE.get()')}
    # boron
    tiny = route('powder_boron'); chain = route('powder_boron_tiny'); ingot = route('ingot_boron')
    result['boron'] = {
        'chunk_yield': {'recipe': java('inventory/recipes/CentrifugeRecipes.java', 'stack(NtmItems.RARE_EARTH_ORE_CHUNK.get(), 1)'), 'powder_boron_tiny_per_chunk': 2, 'powder_boron_tiny_per_ingot': 9 * 1, 'chunks_per_ingot_boron': 4.5,
                        'chunks_for_8_ingot_boron': 36.0},
        'nine_tiny_to_powder': {'file': tiny[0]['file'] if tiny else None, 'type': tiny[0]['type'] if tiny else None, 'pattern': tiny[0]['pattern'] if tiny else None, 'inputs': tiny[0]['inputs'] if tiny else None, 'count': tiny[0]['count'] if tiny else None},
        'powder_to_ingot_route': {'file': ingot[0]['file'] if ingot else None, 'type': ingot[0]['type'] if ingot else None, 'inputs': ingot[0]['inputs'] if ingot else None, 'count': ingot[0]['count'] if ingot else None,
                                  'note': 'smelting only (no blasting JSON); the only generated producer of hbmsntm:ingot_boron'},
        'powder_to_tiny_reverse': chain[0]['file'] if chain else None,
    }
    if not (tiny and tiny[0]['pattern'] == ['TTT', 'TTT', 'TTT'] and tiny[0]['count'] == 1): gaps.append('9 powder_boron_tiny -> powder_boron recipe not found as TTT/TTT/TTT')
    if not (ingot and ingot[0]['type'] == 'minecraft:smelting' and ingot[0]['inputs'] == ['hbmsntm:powder_boron']): gaps.append('powder_boron -> ingot_boron smelting not found')
    # uranium
    ore = route('ingot_uranium', 'smelting_ore_uranium')
    smelt = [r for r in index.get('ingot_uranium', []) if r['type'] in ('minecraft:smelting', 'minecraft:blasting')]
    billet = route('billet_uranium', '2_ingot')
    result['uranium'] = {'ore_to_ingot': [{'file': r['file'], 'type': r['type'], 'inputs': r['inputs'], 'count': r['count']} for r in smelt if any('ore_uranium' in i for i in r['inputs'])],
                         'blasting_json_present': any(r['type'] == 'minecraft:blasting' for r in smelt),
                         'ingot_to_billet': {'file': billet[0]['file'], 'pattern': billet[0]['pattern'], 'ratio': '2 ingot_uranium -> 3 billet_uranium', 'count': billet[0]['count']} if billet else None,
                         'rod_needs': '2 billet_uranium per natural rod'}
    if not result['uranium']['ore_to_ingot']: gaps.append('uranium ore -> ingot_uranium smelting not found')
    if not billet or billet[0]['count'] != 3 or billet[0]['pattern'] != ['XX']: gaps.append('2 ingot_uranium -> 3 billet_uranium crafting not found')
    # zirconium nugget
    result['zirconium_nugget'] = {'crafting_producers': [r['file'] for r in index.get('nugget_zirconium', [])],
                                  'crystal_rare_row_18B': java('inventory/recipes/CrystallizerRecipes.java', 'NtmItems.CRYSTAL_RARE.get(), Fluids.SULFURIC_ACID'),
                                  'centrifuge_crystal_rare': java('inventory/recipes/CentrifugeRecipes.java', 'stack(NtmItems.CRYSTAL_RARE.get(), 1)') + ' (2 + 2 nugget_zirconium)',
                                  'centrifuge_chunk_row_19C': java('inventory/recipes/CentrifugeRecipes.java', 'stack(NtmItems.RARE_EARTH_ORE_CHUNK.get(), 1)') + ' (3 nugget_zirconium)',
                                  'ore_free_source_note': 'nugget_zirconium crafting recipes only split ingot/billet zirconium; ingot_zirconium comes from powder_zirconium smelting or the nugget/billet loop, and powder_zirconium from the shredder (circular); the centrifuge rows are the ore-derived source'}
    if not result['zirconium_nugget']['crystal_rare_row_18B']: gaps.append('18B crystal_rare crystallizer row not found')
    # beryllium ingot
    be = index.get('ingot_beryllium', [])
    result['beryllium_ingot'] = {'producers': [{'file': r['file'], 'type': r['type'], 'inputs': r['inputs'], 'count': r['count']} for r in be], 'ore_routes': [r['file'] for r in be if 'ore_beryllium' in r['file']]}
    if not result['beryllium_ingot']['ore_routes']: gaps.append('ingot_beryllium smelting from ore_beryllium not found')
    # the other assembly inputs, one producer each
    graphite = route('ingot_graphite')
    concrete = route('concrete')
    result['graphite_ingot'] = {'producers': [{'file': r['file'], 'type': r['type'], 'inputs': r['inputs'], 'pattern': r['pattern'], 'count': r['count']} for r in graphite or []]}
    result['rubber_ingot'] = {'producer': java('inventory/recipes/ChemicalPlantRecipes.java', 'new GenericRecipe("chem.rubber")') + ' (sulfur + unsaturated hydrocarbons 500 mB -> 2 ingot_rubber; no vanilla crafting JSON produces it)'}
    result['steel_shell'] = {'producer': java('inventory/recipes/anvil/AnvilRecipes.java', 'addAnvilRecipe(NtmItems.PLATE_STEEL.get(), 4, NtmItems.SHELL_STEEL.get(), 1, 1)') + ' (4 plate_steel -> 1 shell_steel at the anvil; no crafting JSON)'}
    result['steel_pipe'] = {'producer': java('inventory/recipes/anvil/AnvilRecipes.java', 'addAnvilRecipe(NtmItems.PLATE_STEEL.get(), 3, NtmItems.PIPE_STEEL.get(), 1, 1)') + ' (3 plate_steel -> 1 pipe_steel at the anvil; no crafting JSON)'}
    result['integrated_circuit'] = {'producer': java('inventory/recipes/SolderingRecipes.java', 'out(NtmItems.CIRCUIT_INTEGRATED_BOARD)') + ' (soldering station; no crafting JSON)'}
    result['concrete'] = {'producer': [{'file': r['file'], 'type': r['type'], 'inputs': r['inputs'], 'count': r['count'], 'pattern': r['pattern']} for r in concrete or []], 'tag': gen('data/ntm/tags/item/any_concrete.json')}
    for name, entry in (('graphite_ingot', graphite), ('concrete', concrete)):
        if not entry: gaps.append(f'{name}: no generated producing recipe')
    result['gaps'] = gaps
    return result

def concrete_members(source, generated_root, blocks):
    """The generated ntm:any_concrete members against the original ANY_CONCRETE members, as data (differences listed, not judged)."""
    text = read(source / ORIGINAL_ORE_DICT)
    plain = re.search(r'ANY_CONCRETE\s*\.any\(([^)]*)\);', text).group(1).replace(' ', '').split(',')
    colored = sorted(set(re.findall(r'ANY_CONCRETE\.any\(new ItemStack\(ModBlocks\.(\w+), 1, i\)\)', text)))
    original = sorted(plain) + [f'{name}[meta 0..15]' for name in colored]
    members = json.loads((generated_root / 'data/ntm/tags/item/any_concrete.json').read_text(encoding='utf-8'))['values']
    neo = sorted(m.split(':', 1)[1] for m in members)
    return {'original': original, 'generated_tag': members, 'in_original_only': sorted(set(original) - set(neo)), 'in_generated_only': sorted(set(neo) - set(original)),
            'neo_registers_coloured_concrete': {name: name.upper() in blocks for name in colored}}
