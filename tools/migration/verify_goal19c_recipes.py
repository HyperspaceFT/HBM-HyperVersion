"""Goal19C recipes: assembly ass.cirnox, the centrifuge rare earth chunk row, the two generated ZIRNOX rod crafting recipes and the material chains.

Assembly: the production AssemblyMachineRecipes (live) and the frozen Goal19C-start source (package goal19c.base, build/migration/goal19c/baseline-files)
are compiled over the inherited Goal16B recipe-world stand-ins with the existing JDK 21 and Gson and run in both ENABLE_528 modes; the new row's
expected numbers are parsed from the original AssemblyMachineRecipes.java (read-only).
Centrifuge: the production CentrifugeRecipes writer/parser/defaults run against the 76 frozen Goal16B rows (migration/goal16b-centrifuge-recipes.json) plus
one chunk row parsed from the original CentrifugeRecipes.java; player custom files, the template file and the merge example are exercised.
Crafting and materials: static checks of the generated recipe JSON, the provider source and the material chains.
Mutations (--mutations) are anchored copies under the run directory; each must compile (where compiled) and fail the expected assertion. No Gradle, no game."""
from pathlib import Path
import argparse, difflib, hashlib, json, re, shutil, sys, uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, sha, jdk, gson, classpath, adapter_hashes, run, write_report
from goal19c_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES
from goal19c_regression import recipe_static as rs

FIXTURE = Path(__file__).resolve().parent / 'goal19c_regression'
OUT = ROOT / 'build/migration/goal19c'
ORIGINAL = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
GEN = ROOT / 'src/generated/resources'
ASSEMBLY = 'com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
CENTRIFUGE = 'com/hbm/inventory/recipes/CentrifugeRecipes.java'
PROVIDER = 'com/hbm/datagen/NtmRecipeProvider.java'
FQN_ASSEMBLY = 'com.hbm.inventory.recipes.Goal19CRecipeRegression'
FQN_CENTRIFUGE = 'com.hbm.inventory.recipes.loader.Goal19CRecipeCentrifugeRegression'
EXAMPLE = OUT / 'recipes/goal19c-custom-centrifuge-example.json'
EXPECTED_BASE = {'528=false': 47, '528=true': 43}  # the frozen Goal19C-start table sizes; the live table has one more row in each mode
# Files compiled as production sources or read as inputs; any change during the run is an error.
CONTEXT = ('com/hbm/items/NtmItems.java', 'com/hbm/blocks/NtmBlocks.java', 'com/hbm/inventory/RecipesCommon.java', 'com/hbm/inventory/NtmTags.java', 'com/hbm/inventory/MetaHelper.java',
           'com/hbm/items/machine/ZirnoxRodItem.java', PROVIDER, 'com/hbm/datagen/NtmItemTagProvider.java', 'com/hbm/datagen/NtmBlockLootTableProvider.java')

checks = []
def ck(condition, label):
    if not condition: raise AssertionError(label)
    checks.append(label)

def run_dir(kind):
    output = OUT / kind / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    return output

def lf(text): return text.replace('\r\n', '\n')

def hunks(old, new):
    """Opcodes between two texts as (tag, old lines, new lines) without the equal runs."""
    a, b = lf(old).split('\n'), lf(new).split('\n')
    return [(tag, a[i1:i2], b[j1:j2]) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if tag != 'equal']

def static_diffs(frozen_assembly, live_assembly, frozen_centrifuge, live_centrifuge):
    """The live production files differ from the frozen Goal19C start by exactly the declared edits."""
    out = {}
    h = hunks(frozen_assembly, live_assembly)
    ck(len(h) == 1 and h[0][0] == 'insert' and h[0][2][1].strip() == '// Original normal ass.cirnox (AssemblyMachineRecipes.java:524-527), registered in every mode like the original;' and h[0][2][0] == '',
       'AssemblyMachineRecipes differs from the frozen start by exactly one inserted block (the ass.cirnox registration)')
    block = '\n'.join(h[0][2])
    ck(block.count('this.register(') == 1 and block.count('"ass.cirnox"') == 1 and '.inputItemsEx(' not in block, 'the inserted assembly block registers exactly ass.cirnox and has no inputItemsEx')
    out['assembly'] = {'hunks': 1, 'inserted_lines': len(h[0][2])}
    h = hunks(frozen_centrifuge, live_centrifuge)
    ck(len(h) == 3, 'CentrifugeRecipes differs from the frozen start by exactly three hunks: ' + str([(t, len(o), len(n)) for t, o, n in h]))
    insert, defaults, comment = h
    ck(insert[0] == 'insert' and any('registerChunkRecipes' in l for l in insert[2]) and sum('setRecipe(' in l for l in insert[2]) == 1, 'hunk 1 inserts the registerChunkRecipes method with one setRecipe statement')
    ck(any('boron source for ass.cirnox and a' in l for l in insert[2]) and any('further zirconium source for ZIRNOX rods' in l for l in insert[2]), 'the registerChunkRecipes comment names both the ass.cirnox boron source and the ZIRNOX rod zirconium source')
    ck(defaults[0] == 'replace' and defaults[1][0].rstrip().endswith('defaults.registerCrystalRecipes(); }') and defaults[2][0] == defaults[1][0].replace('defaults.registerCrystalRecipes(); }', 'defaults.registerCrystalRecipes(); defaults.registerChunkRecipes(); }'),
       'hunk 2 only appends defaults.registerChunkRecipes() to registerDefaults after registerCrystalRecipes()')
    old_comment, new_comment = comment[1][0], comment[2][0]
    ck(comment[0] == 'replace' and old_comment.count('crystal_ items and vanilla ore blocks') == 1 and new_comment == old_comment.replace('crystal_ items and vanilla ore blocks', 'crystal_ items, the rare earth ore chunk and vanilla ore blocks'),
       'hunk 3 only adds the rare earth ore chunk to the getComment input-range sentence')
    # The 76 frozen setRecipe statements of registerOreRecipes/registerCrystalRecipes are byte-identical (the chunk method sits between them and registerDefaults).
    def statements(text):
        body = lf(text); start = body.index('private void registerOreRecipes()'); end = body.index('// Goal19C') if '// Goal19C' in body else body.index('@Override', start)
        return re.findall(r'^\s*(setRecipe\(.*?;)$', body[start:end], re.M)
    ck(statements(live_centrifuge) == statements(frozen_centrifuge) and len(statements(live_centrifuge)) == 76, 'the 76 frozen setRecipe statements are byte-identical in the live source')
    out['centrifuge'] = {'hunks': 3, 'frozen_statements': 76}
    return out

def compile_and_run(output, java, javac, GSON, classes, argfile, expected_assembly, expected_centrifuge, frozen_json, custom_json, merge_target, report):
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), FQN_ASSEMBLY, output, expected_assembly],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), FQN_CENTRIFUGE, output, expected_centrifuge, frozen_json, custom_json, merge_target]]
    names = ('compile.log', 'run-assembly.log', 'run-centrifuge.log')
    counts = []
    for index, command in enumerate(commands):
        code, text = run(command)
        (output / names[index]).write_text(text, encoding='utf-8')
        report['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': text})
        write_report(output, report)
        print(text, end='', flush=True)
        if code: raise SystemExit(code)
        if index:
            m = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
            if not m: raise SystemExit('Missing evidence counts')
            counts.append(tuple(map(int, m.groups())))
    return counts

def mutated_run(label, directory, target_rel, text, classes, GSON, java, javac, fqn, run_args, fragment, record_list):
    target = directory / target_rel; target.parent.mkdir(parents=True)
    target.write_text(text, encoding='utf-8')
    compiled = directory / 'classes'; compiled.mkdir()
    record = {'label': label, 'expected_fragment': fragment, 'generated_files_sha256': {target.relative_to(ROOT).as_posix(): sha(target)}, 'commands': []}
    record_list.append(record)
    for index, command in enumerate([[javac, '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, target],
                                     [java, '-ea', '-cp', classpath(compiled, classes, GSON), fqn, *run_args]]):
        code, out = run(command)
        (directory / ('compile.log', 'run.log')[index]).write_text(out, encoding='utf-8')
        record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
        if index == 0 and code: raise SystemExit('Mutation compile failure is not detection: ' + out)
        if index == 1 and (code == 0 or 'java.lang.AssertionError' not in out or fragment not in out):
            raise SystemExit(f'Mutation not detected by the expected assertion: {label} (expected "{fragment}")\n' + out)
    record['compiled_successfully'] = True; record['detected'] = True

def assembly_mutations(text):
    """Anchored mutations of the production row: label -> (anchor, replacement, expected AssertionError fragment). Every anchor must occur exactly once."""
    boron = 'new ComparableStack(NtmItems.INGOT_BORON.get(), 8)'
    concrete = 'ResourceLocation.fromNamespaceAndPath("ntm", "any_concrete")), 16),\n                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 4)'
    start = text.index('this.register(new GenericRecipe("ass.cirnox")')
    return {
        'boron_replaced_by_beryllium': (boron, boron.replace('INGOT_BORON', 'INGOT_BERYLLIUM'), 'ass.cirnox input 2 is item hbmsntm:ingot_boron x8'),
        'duration_600_to_300': ('new GenericRecipe("ass.cirnox").setup(600, 100)', 'new GenericRecipe("ass.cirnox").setup(300, 100)', 'ass.cirnox duration 600 ticks'),
        'power_100_to_1000': ('new GenericRecipe("ass.cirnox").setup(600, 100)', 'new GenericRecipe("ass.cirnox").setup(600, 1000)', 'ass.cirnox power 100 HE/t'),
        'concrete_16_to_12': (concrete, concrete.replace('"any_concrete")), 16)', '"any_concrete")), 12)'), 'ass.cirnox input 5 is tag ntm:any_concrete x16'),
        'registration_dropped': (text[start:text.index('NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 4)));', start) + len('NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 4)));')], '', 'live catalog is the base catalog plus exactly one new row ass.cirnox appended last'),
    }

def centrifuge_mutations(text):
    boron = 'stack(NtmItems.POWDER_BORON_TINY.get(), 2), stack(NtmItems.POWDER_NIOBIUM_TINY.get(), 2)'
    zirconium = 'stack(NtmItems.NUGGET_ZIRCONIUM.get(), 3));'
    front = 'defaults.registerOreRecipes(); defaults.registerCrystalRecipes(); defaults.registerChunkRecipes();'
    return {
        'chunk_row_boron_2_to_1': (boron, boron.replace('POWDER_BORON_TINY.get(), 2)', 'POWDER_BORON_TINY.get(), 1)'), 'chunk row output 1 is hbmsntm:powder_boron_tiny x2'),
        'chunk_row_zirconium_3_to_2': (zirconium, zirconium.replace('NUGGET_ZIRCONIUM.get(), 3)', 'NUGGET_ZIRCONIUM.get(), 2)'), 'chunk row output 3 is hbmsntm:nugget_zirconium x3'),
        'chunk_row_inserted_at_front': (front, 'defaults.registerChunkRecipes(); defaults.registerOreRecipes(); defaults.registerCrystalRecipes();', 'frozen rows 0..75 are unchanged and in order'),
    }

def anchored(text, mutations):
    result = {}
    for label, (old, new, fragment) in mutations.items():
        if text.count(old) != 1: raise SystemExit('Mutation anchor missing or not unique: ' + label)
        result[label] = (text.replace(old, new, 1), fragment)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--source', type=Path, default=ORIGINAL, help='original Hbm-s-Nuclear-Tech-GIT worktree (default: sibling directory)')
    parser.add_argument('--mutations', action='store_true', help='also run the anchored mutations (each must be detected)')
    args = parser.parse_args()
    original_root = args.source.resolve()
    output = run_dir('recipes')
    java, javac = jdk(); GSON = gson()
    start = json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))
    items, blocks = rs.registrations(SOURCE)
    report = {'evidence': 'Production AssemblyMachineRecipes and CentrifugeRecipes (live, with the Goal19C rows) and the frozen Goal19C-start assembly source over declared registry/tag/component/Gson stand-ins, plus static checks of generated crafting JSON, provider source and material chains; compile and fixture execution only, not game, JEI, datapack or in-game crafting/centrifuge acceptance',
              'output': str(output.relative_to(ROOT)), 'commands': [], 'target_baseline': {'target_head': start['target_head'], 'source_head': start['source_head']}}
    print(output, flush=True)

    # ---- original facts (read-only) ----
    import subprocess
    original_head = subprocess.run(['git', '-c', 'safe.directory=' + original_root.as_posix(), '-C', str(original_root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    ck(original_head == start['source_head'], f'Original HEAD {original_head} is the recorded baseline {start["source_head"]}')
    assembly = rs.parse_assembly(original_root, items, blocks)
    assembly['expected_base_rows'] = dict(EXPECTED_BASE)
    boron = rs.parse_boron(original_root)
    centrifuge = rs.parse_centrifuge(original_root, items)
    ck((assembly['duration'], assembly['power'], [r['count'] for r in assembly['inputs']], assembly['output']['count']) == (600, 100, [4, 8, 8, 16, 16, 16, 4], 1), 'original ass.cirnox numbers are 600 ticks, 100 HE/t, counts 4/8/8/16/16/16/4, output x1: ' + json.dumps(assembly['expected_values']))
    ck([r['original_kind'] for r in assembly['inputs']] == ['OreDictStack'] * 6 + ['ComparableStack'], 'original input kinds are six OreDictStack and one ComparableStack (the circuit)')
    ck(boron['text'] == 'public static final DictFrame B = new DictFrame("Boron");' and assembly['inputs'][2]['id'] == 'hbmsntm:ingot_boron', 'B.ingot() is the boron ingot (OreDictManager.java:196) and maps to hbmsntm:ingot_boron')
    ck(assembly['output']['id'] == 'hbmsntm:machine_zirnox' and assembly['output']['stub_id'] == 'hbmsntm:reactor_zirnox', 'NEO keeps machine_zirnox for the original reactor_zirnox (stand-in id derives from the field name REACTOR_ZIRNOX)')
    for row in assembly['inputs']:
        if row['kind'] == 'item': ck(row['stub_id'] == row['id'], f'stand-in id equals the production id for {row["field"]}: {row["id"]}')
    ck(centrifuge['expected_values']['counts'] == [o['count'] for o in centrifuge['outputs']] == [2, 2, 2, 3] and centrifuge['expected_values']['ids'] == ['hbmsntm:powder_cobalt_tiny', 'hbmsntm:powder_boron_tiny', 'hbmsntm:powder_niobium_tiny', 'hbmsntm:nugget_zirconium'],
       'original chunk row outputs are cobalt tiny 2, boron tiny 2, niobium tiny 2, zirconium nugget 3: ' + json.dumps(centrifuge['expected_values']))
    ck(centrifuge['input']['stub_id'] == centrifuge['input']['id'] == 'hbmsntm:rare_earth_ore_chunk' and all(o['stub_id'] == o['id'] for o in centrifuge['outputs']), 'centrifuge stand-in ids equal the production ids')
    expected_assembly = output / 'original-ass-cirnox.json'; expected_assembly.write_text(json.dumps(assembly, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    expected_centrifuge = output / 'original-centrifuge-chunk-row.json'; expected_centrifuge.write_text(json.dumps(centrifuge, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report['original_expectation'] = {'assembly': {'path': str(expected_assembly.relative_to(ROOT)), 'sha256': sha(expected_assembly), 'source': assembly['source'], 'source_lines': assembly['source_lines'], 'input_items_ex': assembly['input_items_ex']},
                                      'centrifuge': {'path': str(expected_centrifuge.relative_to(ROOT)), 'sha256': sha(expected_centrifuge), 'source': centrifuge['source'], 'source_lines': centrifuge['source_lines'], 'note': centrifuge['note']},
                                      'boron_mapping': boron, 'original_head': original_head,
                                      'original_file_sha256': {rs.ORIGINAL_ASSEMBLY: sha(original_root / rs.ORIGINAL_ASSEMBLY), rs.ORIGINAL_CENTRIFUGE: sha(original_root / rs.ORIGINAL_CENTRIFUGE)}}

    # ---- frozen start and static source diffs ----
    frozen = {}
    for rel in (ASSEMBLY, CENTRIFUGE):
        key = 'src/main/java/' + rel
        copy = OUT / 'baseline-files' / key
        ck(sha(copy) == start['files'][key], f'Frozen copy of {rel} has the hash recorded in baseline.json')
        frozen[rel] = copy.read_text(encoding='utf-8')
    live_text = (SOURCE / ASSEMBLY).read_text(encoding='utf-8'); live_centrifuge = (SOURCE / CENTRIFUGE).read_text(encoding='utf-8')
    report['static_diffs'] = static_diffs(frozen[ASSEMBLY], live_text, frozen[CENTRIFUGE], live_centrifuge)
    row = rs.neo_chunk_row(live_centrifuge)
    ck([f for f, n in row['stacks']] == [centrifuge['input']['field'][len('NtmItems.'):]] + [o['field'][len('NtmItems.'):] for o in centrifuge['outputs']] and [n for f, n in row['stacks']] == [1, 2, 2, 2, 3],
       'the live Java chunk row names the mapped fields and the original counts: ' + row['statement'])
    report['live_centrifuge_statement'] = row['statement']
    ck(live_text.count('.inputItemsEx(') == 0 and frozen[ASSEMBLY].count('.inputItemsEx(') == 0, 'no .inputItemsEx( call exists in the live or frozen NEO assembly source (the original expensive branch is not migrated; only comments mention it)')
    centrifuge_json = ROOT / 'migration/goal16b-centrifuge-recipes.json'; custom_json = ROOT / 'migration/goal16b-custom-centrifuge-example.json'
    frozen16b = json.loads(centrifuge_json.read_text(encoding='utf-8'))
    ck(len(frozen16b['recipes']) == 76 and centrifuge_json.read_text(encoding='utf-8').count('\n') == 0, 'migration/goal16b-centrifuge-recipes.json holds the 76 canonical compact rows')
    report['goal16b_inputs_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in (centrifuge_json, custom_json)}

    # ---- crafting (generated JSON, provider) and materials ----
    recipes_dir = GEN / 'data/hbmsntm/recipe'
    empty_json = json.loads((recipes_dir / 'rod_zirnox_empty.json').read_text(encoding='utf-8'))
    natural_json = json.loads((recipes_dir / 'rod_zirnox_natural_uranium_fuel.json').read_text(encoding='utf-8'))
    provider_text = (SOURCE / PROVIDER).read_text(encoding='utf-8')
    rod_text = (SOURCE / 'com/hbm/items/machine/ZirnoxRodItem.java').read_text(encoding='utf-8')
    neo_order = rs.zirnox_order(rod_text[rod_text.index('enum ZirnoxType'):])
    original_rods = rs.parse_original_rods(original_root)
    facts = rs.check_crafting(empty_json, natural_json, provider_text, neo_order, original_rods); checks.append('generated ZIRNOX rod recipes pass the crafting assertions')
    ck(len(neo_order) == 11 and neo_order[0] == 'NATURAL_URANIUM_FUEL', 'ZirnoxType has eleven constants and NATURAL_URANIUM_FUEL is ordinal 0')
    multi = (SOURCE / 'com/hbm/items/EnumMultiItem.java').read_text(encoding='utf-8')
    ck('super(properties.component(NtmDataComponents.META.get(), 0));' in multi and 'class ZirnoxRodItem extends EnumMultiItem' in rod_text and 'super(properties, ZirnoxType.class, true, true)' in rod_text,
       'ZirnoxRodItem extends EnumMultiItem whose constructor gives every item the default component hbmsntm:meta = 0 (EnumMultiItem.java:26)')
    helper = (SOURCE / 'com/hbm/inventory/MetaHelper.java').read_text(encoding='utf-8')
    ck('stack.getOrDefault(NtmDataComponents.META.get(), 0)' in helper, 'MetaHelper.getMeta falls back to 0 for an absent component (MetaHelper.java:14)')
    barbed = json.loads((recipes_dir / '54.json').read_text(encoding='utf-8'))
    items_text = (SOURCE / 'com/hbm/items/NtmItems.java').read_text(encoding='utf-8')
    ck(barbed['result'].get('components') == {'hbmsntm:meta': 0} and barbed['result']['id'] == 'hbmsntm:barbed_wire', 'recipe/54.json (barbed wire) shows the explicit meta component for a result whose item prototype lacks that default')
    ck(not re.search(r'BARBED_WIRE\s*=\s*ITEMS\.register\("barbed_wire", \(\) -> new (ZirnoxRodItem|EnumMultiItem)', items_text), 'the barbed wire item is not an EnumMultiItem (its prototype has no default meta)')
    found = rs.recipe_results(GEN)
    ck(sorted(found) == ['data/hbmsntm/recipe/rod_zirnox_empty.json', 'data/hbmsntm/recipe/rod_zirnox_natural_uranium_fuel.json'], 'exactly two generated recipes produce a ZIRNOX rod item: ' + str(sorted(found)))
    ck({p: v.get('id') for p, v in found.items()} == {'data/hbmsntm/recipe/rod_zirnox_empty.json': 'hbmsntm:rod_zirnox_empty', 'data/hbmsntm/recipe/rod_zirnox_natural_uranium_fuel.json': 'hbmsntm:rod_zirnox'}, 'no recipe produces another rod_zirnox META, the tritium rod or a depleted rod')
    ck(not any(('tritium' in v.get('id', '') or 'depleted' in v.get('id', '')) for v in found.values()), 'no generated recipe produces the tritium rod or a depleted rod')
    ck(rs.uses_zirnox(GEN) == [], 'no other generated recipe consumes a ZIRNOX rod')
    ck(facts['rod_zirnox_recipe_statements'] == 4, 'the provider mentions the ZIRNOX rod items only in the two rod statements (empty rod result, empty rod ingredient, its unlock, filled rod result): ' + str(facts['rod_zirnox_recipe_statements']))
    ck(provider_text.count('ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ROD_ZIRNOX_EMPTY.get()') == 1 and provider_text.count('MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get()') == 1, 'the provider has exactly one empty-rod and one filled-rod statement')
    # generated tree against the frozen start: only the two recipes and their two advancements are new in the recipe/advancement area
    gen_now = {p.relative_to(ROOT).as_posix() for p in GEN.rglob('*') if p.is_file()}
    gen_start = {k for k in start['files'] if k.startswith('src/generated/resources/')}
    added = sorted(gen_now - gen_start); removed = sorted(gen_start - gen_now)
    changed = sorted(p for p in gen_now & gen_start if sha(ROOT / p) != start['files'][p] and (ROOT / p).read_bytes().replace(b'\r\n', b'\n') != (OUT / 'baseline-files' / p).read_bytes().replace(b'\r\n', b'\n'))
    expected_added = ['src/generated/resources/data/hbmsntm/advancement/recipes/misc/rod_zirnox_empty.json', 'src/generated/resources/data/hbmsntm/advancement/recipes/misc/rod_zirnox_natural_uranium_fuel.json',
                      'src/generated/resources/data/hbmsntm/recipe/rod_zirnox_empty.json', 'src/generated/resources/data/hbmsntm/recipe/rod_zirnox_natural_uranium_fuel.json']
    ck(added == expected_added and not removed, 'relative to the frozen start the generated tree gains exactly the two rod recipes and their two recipe advancements and loses nothing: ' + str(added))
    other_recipe_changes = [p for p in changed if '/recipe' in p or '/advancement/' in p or p.endswith('/tags/item/any_concrete.json')]
    ck(not other_recipe_changes, 'no existing generated recipe, advancement or ntm tag changed: ' + str(other_recipe_changes))
    report['generated_vs_frozen_start'] = {'added': added, 'removed': removed, 'changed_existing': changed}
    mats = rs.materials(ROOT, GEN)
    concrete = rs.concrete_members(original_root, GEN, blocks)
    report['crafting'] = {'provider_facts': facts, 'original_rods': original_rods, 'neo_zirnox_order': neo_order, 'generated_files_sha256': {p: sha(ROOT / p) for p in added},
                          'natural_rod_result': natural_json['result'], 'empty_rod_result': empty_json['result'],
                          'meta_reasoning': 'EnumMultiItem.java:26 default component hbmsntm:meta=0; NATURAL_URANIUM_FUEL ordinal 0 in original EnumZirnoxType and NEO ZirnoxType; MetaHelper.getMeta default 0 (MetaHelper.java:14); the datagen patch against the prototype is empty, so no components block is written; any other ordinal would need an explicit hbmsntm:meta component',
                          'rod_recipe_results_in_generated_tree': found}
    report['materials'] = mats; report['concrete_members'] = concrete
    report['materials_gaps'] = mats['gaps']
    ck(not mats['gaps'], 'no gap in the material chains: ' + str(mats['gaps']))

    # ---- compile and run ----
    fixture_assembly, fixture_centrifuge = FIXTURE / 'Goal19CRecipeRegression.java', FIXTURE / 'Goal19CRecipeCentrifugeRegression.java'
    baseline = frozen[ASSEMBLY]
    baseline = lf(baseline)
    ck(baseline.count('package com.hbm.inventory.recipes;') == 1, 'frozen assembly source has one package declaration')
    baseline = baseline.replace('package com.hbm.inventory.recipes;', 'package goal19c.base;\nimport com.hbm.inventory.recipes.*;', 1)
    stubs = recipe_stubs(SOURCE, [fixture_assembly.read_text(encoding='utf-8'), fixture_centrifuge.read_text(encoding='utf-8'), baseline, live_text])
    stubs['goal19c/base/AssemblyMachineRecipes.java'] = baseline
    ck(not (set(RECIPE_SOURCES) & set(stubs)), 'no production source is shadowed by a stand-in')
    hashes = {p: sha(SOURCE / p) for p in dict.fromkeys((*RECIPE_SOURCES, *CONTEXT))}
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    generated = {p.relative_to(output).as_posix(): sha(p) for p in paths}
    paths += [SOURCE / p for p in RECIPE_SOURCES] + [fixture_assembly, fixture_centrifuge]
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    own = [Path(__file__).resolve(), FIXTURE / 'recipe_stubs.py', FIXTURE / 'recipe_static.py', fixture_assembly, fixture_centrifuge]
    frozen16b_class = ROOT / 'build/migration/goal16b/baseline-files/src/main/java/com/hbm/inventory/recipes/CentrifugeRecipes.java'
    report.update({'source_sha256': hashes, 'fixture_sha256': {str(p.relative_to(ROOT)): sha(p) for p in own}, 'cache_sha256': {str(GSON): sha(GSON)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
                   'frozen_goal16b_centrifuge_class_sha256': sha(frozen16b_class), 'generated_stubs_sha256': generated, 'adapter_sha256': adapter_hashes(),
                   'service_boundaries': ['Item/Block registry, tags and data components are stand-ins whose ids derive from the field names; the verifier checks each used id against the production registrations (NtmItems, NtmBlocks); the only id that differs is the output (field REACTOR_ZIRNOX is registered as machine_zirnox)',
                                          'The real Gson jar and the production loader base (GenericRecipes/GenericRecipe/SerializableRecipe), AssemblyMachineRecipes and CentrifugeRecipes are used; the frozen assembly base is the Goal19C-start source compiled as goal19c.base, the frozen centrifuge comparison class is the Goal16B baseline compiled as FrozenCentrifugeRecipes',
                                          'File loading uses the production SerializableRecipe.readRecipeFile on real files under the run directory; SerializableRecipe.initialize() (config directory handling) is not executed',
                                          'The machine batch runs in the Goal16B machine world: its recipe table is the Goal16B explicit service filled from the production-written chunk row (see machine_batch)']})
    EXAMPLE.parent.mkdir(parents=True, exist_ok=True)
    counts = compile_and_run(output, java, javac, GSON, classes, argfile, expected_assembly, expected_centrifuge, centrifuge_json, custom_json, EXAMPLE, report)
    report['counts_fixtures'] = {'assembly': dict(zip(('assertions', 'scenarios', 'ticks'), counts[0])), 'centrifuge_table': dict(zip(('assertions', 'scenarios', 'ticks'), counts[1]))}
    ck(EXAMPLE.is_file() and len(json.loads(EXAMPLE.read_text(encoding='utf-8'))['recipes']) == 1, 'the custom centrifuge example was written with exactly one row')
    example_text = EXAMPLE.read_text(encoding='utf-8')
    ck(example_text == '{"recipes":[' + (output / 'goal19c-centrifuge-chunk-row.json').read_text(encoding='utf-8') + ']}', 'the example is the minimal envelope around the new row, the same shape as migration/goal16b-custom-centrifuge-example.json')
    ck(json.loads(example_text)['recipes'][0] == json.loads((output / 'goal19c-centrifuge-defaults-snapshot.json').read_text(encoding='utf-8'))['recipes'][76], 'the example row equals row 77 of the production default snapshot')
    report['custom_example'] = {'path': str(EXAMPLE.relative_to(ROOT)), 'sha256': sha(EXAMPLE), 'text': example_text}
    catalog = json.loads((output / 'goal19c-assembly-catalog.json').read_text(encoding='utf-8'))
    report['catalog'] = {mode: {k: v for k, v in entry.items() if k not in ('newRow', 'liveOrder')} for mode, entry in catalog.items()}
    report['catalog_new_row'] = catalog['528=false']['newRow']
    ck({m: e['baseRows'] for m, e in catalog.items()} == EXPECTED_BASE and {m: e['liveRows'] for m, e in catalog.items()} == {m: n + 1 for m, n in EXPECTED_BASE.items()}, 'the assembly table grows 43 -> 44 (528 off) and 47 -> 48 (528 on)')
    report['exports'] = {n: {'path': str((output / n).relative_to(ROOT)), 'sha256': sha(output / n)} for n in ('goal19c-assembly-catalog.json', 'goal19c-centrifuge-defaults-snapshot.json', 'goal19c-centrifuge-chunk-row.json', '_hbmCentrifuge.json')}
    report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
    write_report(output, report)
    if not report['source_stable_after_run']: raise SystemExit('Production changed during check')

    # ---- real machine batch (Goal16B machine world, row decoded from the production writer output) ----
    from goal19c_regression.recipe_machine import run_machine_batch
    report['machine_batch'] = run_machine_batch(output, output / 'goal19c-centrifuge-chunk-row.json', expected_centrifuge)
    write_report(output, report)

    # ---- mutations ----
    report['mutations'] = []
    if args.mutations:
        for label, (text, fragment) in anchored(live_text, assembly_mutations(live_text)).items():
            directory = output / 'mutations' / label
            mutated_run(label, directory, ASSEMBLY, text, classes, GSON, java, javac, FQN_ASSEMBLY, [directory, expected_assembly], fragment, report['mutations'])
            write_report(output, report)
        for label, (text, fragment) in anchored(live_centrifuge, centrifuge_mutations(live_centrifuge)).items():
            directory = output / 'mutations' / label
            mutated_run(label, directory, CENTRIFUGE, text, classes, GSON, java, javac, FQN_CENTRIFUGE, [directory, expected_centrifuge, centrifuge_json, custom_json, directory / 'example.json'], fragment, report['mutations'])
            write_report(output, report)
        # Static mutations of the crafting evidence: the generated JSON and the provider source (a regenerated JSON cannot be produced here, so the
        # provider text is checked statically against the generated file and the parsed generated copy is mutated instead).
        def mutate_json(source_json, edit):
            copy = json.loads(json.dumps(source_json)); edit(copy); return copy
        crafting = {
            'rod_count_3_generated': (mutate_json(empty_json, lambda d: d['result'].__setitem__('count', 3)), natural_json, provider_text, 'empty rod result is 4 x rod_zirnox_empty'),
            'rod_count_3_provider': (empty_json, natural_json, provider_text.replace('NtmItems.ROD_ZIRNOX_EMPTY.get(), 4)', 'NtmItems.ROD_ZIRNOX_EMPTY.get(), 3)', 1), 'provider count of the empty rod equals the generated result count'),
            'natural_meta_1_generated': (empty_json, mutate_json(natural_json, lambda d: d['result'].__setitem__('components', {'hbmsntm:meta': 1})), provider_text, 'generated META equals the provider ordinal'),
            'natural_meta_1_provider': (empty_json, natural_json, provider_text.replace('ZirnoxType.NATURAL_URANIUM_FUEL.ordinal()', 'ZirnoxType.URANIUM_FUEL.ordinal()', 1), 'provider rod type is NATURAL_URANIUM_FUEL'),
        }
        for label, (e, n, p, fragment) in crafting.items():
            if p == provider_text and label.endswith('provider'): raise SystemExit('Provider mutation anchor missing: ' + label)
            try: rs.check_crafting(e, n, p, neo_order, original_rods)
            except AssertionError as error:
                if fragment not in str(error): raise SystemExit(f'Mutation {label} failed with the wrong assertion: {error}')
                report['mutations'].append({'label': label, 'expected_fragment': fragment, 'detected': True, 'kind': 'static crafting evidence on a ' + ('provider-source copy' if label.endswith('provider') else 'generated-file copy'), 'message': str(error)})
            else: raise SystemExit('Static mutation not detected: ' + label)
        write_report(output, report)
    report['mutations_detected'] = sum(1 for m in report['mutations'] if m.get('detected'))
    report['mutations_total'] = len(report['mutations'])
    report['python_assertions'] = len(checks); report['python_assertion_labels'] = checks
    report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
    report['source_sha256_after_run'] = {p: sha(SOURCE / p) for p in hashes}
    write_report(output, report)
    if not report['source_stable_after_run']: raise SystemExit('Production changed during check')
    f = report['counts_fixtures']; mb = report['machine_batch']['counts']
    total = f['assembly']['assertions'] + f['centrifuge_table']['assertions'] + mb['assertions'] + len(checks)
    print(f"Goal19C recipes: {total} assertions ({f['assembly']['assertions']} assembly + {f['centrifuge_table']['assertions']} centrifuge table + {mb['assertions']} machine batch + {len(checks)} static); {f['assembly']['scenarios'] + f['centrifuge_table']['scenarios'] + mb['scenarios']} independent scenarios; {mb['ticks']} executed ticks (machine batch, not counted as assertions)")
    print(f"Compiled and static mutations detected: {report['mutations_detected']}/{report['mutations_total']}")
    print(output / 'report.json')

if __name__ == '__main__': main()
