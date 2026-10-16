"""Goal20A recipes: the five sulfuric acid uranium/thorium crystallizer default rows, the yellowcake billet input, the thorium smelting recipes and the TH232 ZIRNOX rod.

Crystallizer: the production CrystallizerRecipes (live, 41 default rows) is compiled over the inherited Goal18A/18B recipe-world stand-ins with the existing
JDK 21 and Gson and run against the frozen Goal18B export (migration/goal18b-crystallizer-recipes.json, 36 rows); the expected numbers of the new rows are
parsed from the original CrystallizerRecipes.java (read-only). Sync, old custom tables, the merge example and the config-file paths are exercised.
Static: the declared edits of the three production sources against the frozen Goal20A start, the chem.yellowcake registration, the generated thorium
smelting and TH232 rod JSON, the provider source and the original lines.
Mutations (--mutations) are anchored copies under the run directory; each must compile (where compiled) and fail the expected assertion. No Gradle, no game."""
from pathlib import Path
import argparse, json, re, subprocess, sys, uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, sha, jdk, gson, classpath, adapter_hashes, run, write_report
from goal18b_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES
from goal20a_regression import recipe_static as rs

FIXTURE = Path(__file__).resolve().parent / 'goal20a_regression'
OUT = ROOT / 'build/migration/goal20a'
ORIGINAL = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
GEN = ROOT / 'src/generated/resources'
CRYSTALLIZER = 'com/hbm/inventory/recipes/CrystallizerRecipes.java'
CHEMICAL = 'com/hbm/inventory/recipes/ChemicalPlantRecipes.java'
PROVIDER = 'com/hbm/datagen/NtmRecipeProvider.java'
LOADER = 'com/hbm/inventory/recipes/loader/SerializableRecipe.java'
ROD_ITEM = 'com/hbm/items/machine/ZirnoxRodItem.java'
FQN = 'com.hbm.inventory.recipes.Goal20ARecipeRegression'
FROZEN_18B = ROOT / 'migration/goal18b-crystallizer-recipes.json'
EXAMPLE = OUT / 'recipes/goal20a-custom-crystallizer-example.json'
EXPORT = 'goal20a-crystallizer-recipes.json'
COMPARISON = 'goal20a-default-comparison.json'
# Files compiled as production sources or read as inputs; any change during the run is an error.
CONTEXT = ('com/hbm/items/NtmItems.java', 'com/hbm/blocks/NtmBlocks.java', 'com/hbm/inventory/RecipesCommon.java', 'com/hbm/inventory/MetaHelper.java', 'com/hbm/inventory/fluid/Fluids.java',
           CHEMICAL, PROVIDER, LOADER, ROD_ITEM)

checks = []
def ck(condition, label):
    if not condition: raise AssertionError(label)
    checks.append(label)

def run_dir(kind):
    output = OUT / kind / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    return output

def example_row(spec, expected):
    return {'input': ['item', spec['input'], 1, rs.WILDCARD], 'fluid': [expected['acid'], expected['amount']], 'output': [spec['output'], 1, None], 'duration': expected['duration'], 'productivity': expected['productivity']}

def write_example(frozen_rows, expected):
    comment = ('Example Goal 20A merge for a custom hbmCrystallizer.json. A custom hbmCrystallizer.json replaces the WHOLE default table, so an existing custom file does NOT gain the Goal 20A '
               'SULFURIC_ACID uranium and thorium ore rows (uranium, deepslate uranium, scorched uranium, thorium, deepslate thorium) '
               'automatically, and the mod never rewrites or appends to a player\'s file. To keep them, append rows 3-7 below (exactly as the default table writes them) to the recipes array of your own file; '
               'rows 1-2 stand for rows you already have (here the stone coal ore and deepslate iron ore hydrogen peroxide defaults). Rows are keyed on input identity plus the acid\'s internal name '
               '(PEROXIDE, SULFURIC_ACID), so do not append a row whose input/acid pair your file already has. Acid amounts are 1..8000 mB; duration 600 completes after 601 effective sub-cycles (duration+1); '
               'productivity 0..1 is the chance per EFFECT upgrade level that the input ore is kept, the acid is always consumed.')
    document = {'comment': comment, 'recipes': [frozen_rows[0], frozen_rows[3]] + [example_row(r, expected) for r in expected['rows']]}
    EXAMPLE.parent.mkdir(parents=True, exist_ok=True)
    EXAMPLE.write_text(json.dumps(document, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return document

def row_key(row): return json.dumps(row['input'], separators=(',', ':')) + '@' + row['fluid'][0]

def comparison(old_rows, new_rows):
    old, new = {row_key(r): r for r in old_rows}, {row_key(r): r for r in new_rows}
    if len(old) != len(old_rows) or len(new) != len(new_rows): raise SystemExit('Duplicate input/acid key in an export')
    return {'added': [r for k, r in new.items() if k not in old], 'removed': [r for k, r in old.items() if k not in new],
            'changed': [{'before': old[k], 'after': r} for k, r in new.items() if k in old and old[k] != r]}

def mutated_run(label, directory, text, classes, GSON, java, javac, run_args, fragment, record_list):
    target = directory / CRYSTALLIZER; target.parent.mkdir(parents=True)
    target.write_text(text, encoding='utf-8')
    compiled = directory / 'classes'; compiled.mkdir()
    record = {'label': label, 'expected_fragment': fragment, 'generated_files_sha256': {target.relative_to(ROOT).as_posix(): sha(target)}, 'commands': []}
    record_list.append(record)
    for index, command in enumerate([[javac, '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, target],
                                     [java, '-ea', '-cp', classpath(compiled, classes, GSON), FQN, *run_args]]):
        code, out = run(command)
        (directory / ('compile.log', 'run.log')[index]).write_text(out, encoding='utf-8')
        record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
        if index == 0 and code: raise SystemExit('Mutation compile failure is not detection: ' + out)
        if index == 1 and (code == 0 or 'java.lang.AssertionError' not in out or fragment not in out):
            raise SystemExit(f'Mutation not detected by the expected assertion: {label} (expected "{fragment}")\n' + out)
    record['compiled_successfully'] = True; record['detected'] = True

def crystallizer_mutations(text):
    """label -> (list of (anchor, replacement), expected AssertionError fragment). Every anchor must occur exactly once."""
    uranium = '        ore(NtmBlocks.ORE_URANIUM.get(), NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);\n'
    scorched = '        single(NtmBlocks.ORE_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);\n'
    thorium = 'NtmItems.CRYSTAL_THORIUM.get(), Fluids.SULFURIC_ACID);'
    ore_helper = '        FluidStack fluid = new FluidStack(acid, DEFAULT_ACID);\n'
    single_helper = 'new ComparableStack(ore, 1), new FluidStack(acid, DEFAULT_ACID), new ItemStack(crystal)'
    present = lambda key: f'row item:hbmsntm:{key}:32767@SULFURIC_ACID is in the default table'
    return {
        'uranium_rows_dropped': ([(uranium, '')], present('ore_uranium')),
        'scorched_row_dropped': ([(scorched, '')], present('ore_uranium_scorched')),
        'thorium_rows_use_peroxide': ([(thorium, thorium.replace('SULFURIC_ACID', 'PEROXIDE'))], present('ore_thorium')),
        'sulfuric_amount_250_new_rows': ([(ore_helper, '        FluidStack fluid = new FluidStack(acid, acid == Fluids.SULFURIC_ACID && (crystal == NtmItems.CRYSTAL_URANIUM.get() || crystal == NtmItems.CRYSTAL_THORIUM.get()) ? 250 : DEFAULT_ACID);\n'),
                                          (single_helper, single_helper.replace('new FluidStack(acid, DEFAULT_ACID)', 'new FluidStack(acid, 250)'))], 'row 36 ore_uranium: 500 mB SULFURIC_ACID'),
    }

def anchored(text, mutations):
    result = {}
    for label, (edits, fragment) in mutations.items():
        mutated = text
        for old, new in edits:
            if mutated.count(old) != 1: raise SystemExit('Mutation anchor missing or not unique: ' + label)
            mutated = mutated.replace(old, new, 1)
        result[label] = (mutated, fragment)
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
    report = {'evidence': 'Production CrystallizerRecipes (live, Goal20A defaults)/sync/client sync/packet/JEI handler over registry, component, Gson and JEI-manager stand-ins and the frozen Goal18B export, plus static checks of the ChemicalPlantRecipes yellowcake registration, the provider source, the generated thorium smelting and TH232 rod JSON and the original source lines; compile and fixture execution only, not game, JEI, config-directory, datapack or in-game crafting/smelting/crystallizer acceptance',
              'output': str(output.relative_to(ROOT)), 'commands': [], 'target_baseline': {'target_head': start['target_head'], 'source_head': start['source_head']}}
    print(output, flush=True)

    # ---- original facts (read-only) ----
    original_head = subprocess.run(['git', '-c', 'safe.directory=' + original_root.as_posix(), '-C', str(original_root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    ck(original_head == start['source_head'] and original_head.startswith('d31426c'), f'Original HEAD {original_head} is the recorded baseline {start["source_head"]}')
    crystal = rs.parse_original_crystallizer(original_root)
    ore_dict = rs.parse_original_ore_dict(original_root)
    sulfur, base = crystal['sulfur'], crystal['base_time']
    ck(sulfur['source'].endswith(':59') and crystal['rows']['U']['source'].endswith(':67') and crystal['rows']['TH232']['source'].endswith(':68') and crystal['rows']['PU']['source'].endswith(':69'),
       'original crystallizer lines are :59 sulfur, :67 U.ore(), :68 TH232 ores, :69 PU: ' + json.dumps({k: v['source'] for k, v in crystal['rows'].items()}))
    ck((sulfur['acid'], sulfur['amount'], base['duration']) == ('SULFURIC_ACID', 500, 600) and all(r['productivity'] == 0.05 and r['uses_sulfur_stack'] for r in crystal['rows'].values()), 'original sulfur stack is 500 mB SULFURIC_ACID, baseTime 600, prod 0.05F on the U, TH232 and PU rows')
    ck(crystal['rows']['U']['crystal'] == 'crystal_uranium' and crystal['rows']['TH232']['crystal'] == 'crystal_thorium', 'original U.ore() maps to crystal_uranium and every TH232 ore to crystal_thorium')
    ck(ore_dict['U']['source'].endswith(':347') and ore_dict['TH232']['source'].endswith(':351') and ore_dict['TH232']['ores'] == ['ore_thorium'], 'OreDictManager.java:347 is U and :351 is TH232 (ore: ore_thorium only)')
    ck(ore_dict['U']['ores'] == ['ore_uranium', 'ore_uranium_scorched', 'ore_gneiss_uranium', 'ore_gneiss_uranium_scorched', 'ore_nether_uranium', 'ore_nether_uranium_scorched', 'ore_sellafield_uranium_scorched'], 'original U.ore() lists seven ores (three ported): ' + str(ore_dict['U']['ores']))
    expected, omitted = rs.expected_crystallizer(crystal, ore_dict, items, blocks)
    ck(len(expected['rows']) == rs.NEW_ROWS == 5 and [r['input_field'] for r in expected['rows']] == ['ORE_URANIUM', 'ORE_URANIUM_DEEPSLATE', 'ORE_URANIUM_SCORCHED', 'ORE_THORIUM', 'ORE_THORIUM_DEEPSLATE'],
       'five expected new rows in table order (the deepslate variants exist only in NEO)')
    ck(all(r['input'] == r['input_stub_id'] and r['output'] == r['output_stub_id'] for r in expected['rows']), 'stand-in ids equal the production registration ids for every new ore and crystal')
    ck([o['original_ore'] for o in omitted] == ['ore_gneiss_uranium', 'ore_gneiss_uranium_scorched', 'ore_nether_uranium', 'ore_nether_uranium_scorched', 'ore_sellafield_uranium_scorched']
       and [o['neo_registered_id'] is not None for o in omitted] == [True, True, True, True, False], 'the original U.ore() ores without a default row are the four gneiss/nether blocks (registered in NEO) and ore_sellafield_uranium_scorched (no NEO block): recorded gaps')
    lang = {}
    for name, path in (('en_us', GEN / 'assets/hbmsntm/lang/en_us.json'), ('zh_cn', ROOT / 'src/main/resources/assets/hbmsntm/lang/zh_cn.json')):
        keys = json.loads(path.read_text(encoding='utf-8'))
        lang[name] = {o['neo_field'].lower(): ('block.hbmsntm.' + o['neo_field'].lower()) in keys for o in omitted if o['neo_registered_id']}
    for o in omitted:
        o['recorded_gap'] = 'no NEO block' if not o['neo_registered_id'] else 'registered but excluded from the default table (language key present: ' + str({k: v[o['neo_field'].lower()] for k, v in lang.items()}) + '; no creative-tab entry or world generation per the main agent)'
    ck(crystal['rows']['PU']['crystal'] == 'crystal_plutonium', 'the :69 plutonium row exists in the original and is deliberately not ported (recorded)')
    expectation_file = output / 'original-crystallizer-expectation.json'
    expectation_file.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    chem_original = rs.parse_original_chem(original_root, ore_dict)
    smelting_original = rs.parse_original_smelting(original_root)
    rod_original = rs.parse_original_th232_rod(original_root, ore_dict)
    ck(chem_original['source'].endswith(':379-382') and rod_original['source'].endswith(':29') and smelting_original['ore']['source'].endswith(':30') and smelting_original['powder']['source'].endswith(':84'),
       'original line numbers: chem.yellowcake :379-382, RodRecipes :29, SmeltingRecipes :30 and :84')
    original_files = [rs.ORIGINAL_CRYSTALLIZER, rs.ORIGINAL_ORE_DICT, rs.ORIGINAL_CHEMICAL_PLANT, rs.ORIGINAL_SMELTING, rs.ORIGINAL_ROD_RECIPES, rs.ORIGINAL_ZIRNOX_ROD]
    report['original_expectation'] = {'original_head': original_head, 'crystallizer': crystal, 'ore_dict': ore_dict, 'expected_new_rows': expected, 'omitted_original_ores': omitted, 'omitted_lang_keys': lang,
                                      'plutonium_row': {'ported': False, **crystal['rows']['PU']}, 'yellowcake': chem_original, 'smelting': smelting_original, 'th232_rod': rod_original,
                                      'expectation_path': str(expectation_file.relative_to(ROOT)), 'expectation_sha256': sha(expectation_file),
                                      'original_file_sha256': {p: sha(original_root / p) for p in original_files}}

    # ---- frozen start and static source diffs ----
    frozen = {}
    for rel in (CRYSTALLIZER, CHEMICAL, PROVIDER):
        key = 'src/main/java/' + rel
        copy = OUT / 'baseline-files' / key
        ck(sha(copy) == start['files'][key], f'Frozen copy of {rel} has the hash recorded in baseline.json')
        frozen[rel] = copy.read_text(encoding='utf-8')
    live = {rel: (SOURCE / rel).read_text(encoding='utf-8') for rel in (CRYSTALLIZER, CHEMICAL, PROVIDER, LOADER, ROD_ITEM)}
    report['static_diffs'] = {'crystallizer': rs.diff_crystallizer(frozen[CRYSTALLIZER], live[CRYSTALLIZER], ck), 'chemical_plant': rs.diff_chemical(frozen[CHEMICAL], live[CHEMICAL], ck), 'provider': rs.diff_provider(frozen[PROVIDER], live[PROVIDER], ck)}

    # ---- yellowcake ----
    report['yellowcake'] = {'live': rs.check_yellowcake(live[CHEMICAL], chem_original, items, ck), 'original': chem_original,
                            'custom_table': rs.check_chem_loader(live[CHEMICAL], live[LOADER], ck),
                            'note': 'A custom hbmChemicalPlant.json replaces the whole table, so a player custom table keeps its own yellowcake input; only the default (no file / unusable file) table changed.'}

    # ---- thorium smelting ----
    smelting = rs.load_smelting(GEN)
    report['thorium_smelting'] = rs.check_smelting(live[PROVIDER], smelting, smelting_original, ck)

    # ---- TH232 rod ----
    rod_json = json.loads((GEN / 'data/hbmsntm/recipe/rod_zirnox_th232.json').read_text(encoding='utf-8'))
    rod_text = live[ROD_ITEM]
    neo_order = rs.zirnox_order(rod_text[rod_text.index('enum ZirnoxType'):])
    ck(len(neo_order) == 11 and neo_order[2] == 'TH232' and rod_original['original_type_order'] == neo_order, 'ZirnoxType has eleven constants, TH232 is ordinal 2 and the order equals the original EnumZirnoxType: ' + str(neo_order))
    report['th232_rod'] = {'provider': rs.check_rod(rod_json, live[PROVIDER], neo_order, rod_original, ck), 'generated_result': rod_json['result'], 'original': rod_original}
    found = rs.recipe_results(GEN)
    ck(sorted(found) == ['data/hbmsntm/recipe/rod_zirnox_empty.json', 'data/hbmsntm/recipe/rod_zirnox_natural_uranium_fuel.json', 'data/hbmsntm/recipe/rod_zirnox_th232.json'], 'exactly three generated recipes produce a ZIRNOX rod item (empty, natural uranium, th232): ' + str(sorted(found)))
    ck(sorted(p.name for p in (GEN / 'data/hbmsntm/recipe').glob('rod_zirnox*.json')) == ['rod_zirnox_empty.json', 'rod_zirnox_natural_uranium_fuel.json', 'rod_zirnox_th232.json'], 'exactly three rod_zirnox recipe JSON files exist')
    ck({p: v['id'] for p, v in found.items()}['data/hbmsntm/recipe/rod_zirnox_th232.json'] == 'hbmsntm:rod_zirnox' and found['data/hbmsntm/recipe/rod_zirnox_th232.json']['components'] == {'hbmsntm:meta': 2}, 'the th232 recipe result is rod_zirnox with hbmsntm:meta 2')
    report['rod_recipe_results_in_generated_tree'] = found

    # ---- generated tree against the frozen start ----
    added, removed, changed = rs.generated_tree(ROOT, GEN, start['files'], OUT / 'baseline-files')
    expected_added = sorted(f'src/generated/resources/data/hbmsntm/{area}/{name}.json' for area in ('recipe', 'advancement/recipes/misc') for name in ('ingot_th232_from_smelting_ore_thorium', 'ingot_th232_from_smelting_ore_thorium_deepslate', 'powder_thorium_to_ingot_th232', 'rod_zirnox_th232'))
    expected_removed = sorted('src/generated/resources/' + p for p in rs.OLD_SMELT_FILES)
    ck(added == expected_added and removed == expected_removed, 'relative to the frozen start the generated tree gains the four new recipes and their four advancements and loses the four old ingot_thorium_fuel smelting files: added ' + str(added) + ' removed ' + str(removed))
    risky = [p for p in changed if '/recipe/' in p or '/advancement/' in p or '/lang/' in p]
    ck(not risky, 'no existing generated recipe, advancement or language file changed: ' + str(risky))
    report['generated_vs_frozen_start'] = {'added': added, 'removed': removed, 'changed_existing': changed}
    generated_read = sorted({f'src/generated/resources/data/hbmsntm/recipe/{n}.json' for n in (*rs.SMELT_FILES.values(), *rs.FUEL_KEPT, 'ingot_th232_from_crystal_thorium', 'rod_zirnox_th232', 'rod_zirnox_natural_uranium_fuel', 'rod_zirnox_empty')})
    report['generated_files_sha256'] = {p: sha(ROOT / p) for p in generated_read}

    # ---- crystallizer fixture: stand-in sources, example, compile and run ----
    fixture = FIXTURE / 'Goal20ARecipeRegression.java'
    frozen_rows = json.loads(FROZEN_18B.read_text(encoding='utf-8'))['recipes']
    ck(len(frozen_rows) == 36 and FROZEN_18B.read_text(encoding='utf-8').count('\n') == 0, 'migration/goal18b-crystallizer-recipes.json holds the 36 canonical compact rows')
    example = write_example(frozen_rows, expected)
    stubs = recipe_stubs(SOURCE, [fixture.read_text(encoding='utf-8')])
    ck(not (set(RECIPE_SOURCES) & set(stubs)), 'no production source is shadowed by a stand-in')
    hashes = {p: sha(SOURCE / p) for p in dict.fromkeys((*RECIPE_SOURCES, *CONTEXT))}
    records = {str(p.relative_to(ROOT)): sha(p) for p in (FROZEN_18B, OUT / 'baseline.json')}
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    generated_stubs = {p.relative_to(output).as_posix(): sha(p) for p in paths}
    paths += [SOURCE / p for p in RECIPE_SOURCES] + [fixture]
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    own = [Path(__file__).resolve(), FIXTURE / 'recipe_static.py', fixture]
    report.update({'source_sha256': hashes, 'record_sha256': records, 'fixture_sha256': {str(p.relative_to(ROOT)): sha(p) for p in own}, 'cache_sha256': {str(GSON): sha(GSON)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
                   'generated_stubs_sha256': generated_stubs, 'adapter_sha256': adapter_hashes(),
                   'service_boundaries': ['Item/Block registry, tags, data components and SNBT are stand-ins (ids derived from the field names, checked against the production registrations); the real Gson jar and the production loader base are used',
                                          'JEI runtime manager is the Goal18A counting stand-in (goal18a.JeiBridge) bridged through the production refreshCrystallizerRecipes body',
                                          'Network transport is a byte-array buffer stand-in; login/datapack events, the config directory and SerializableRecipe.initialize() are not executed (readRecipeFile/readRecipeStream run on real files under a temp directory)',
                                          'The yellowcake, smelting and rod evidence is static (source text and generated JSON), not a loaded recipe manager or a crafting/smelting run']})
    arguments = lambda directory: [directory, FROZEN_18B, EXAMPLE, expectation_file]
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), FQN, *arguments(output)]]
    fixture_counts = None
    for index, command in enumerate(commands):
        code, text = run(command)
        (output / ('compile.log', 'run.log')[index]).write_text(text, encoding='utf-8')
        report['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': text})
        report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
        write_report(output, report)
        print(text, end='', flush=True)
        if code or not report['source_stable_after_run']: raise SystemExit(code or 'Production changed during check')
        if index:
            m = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
            if not m: raise SystemExit('Missing evidence counts')
            fixture_counts = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, m.groups())))
    report['counts_fixture'] = fixture_counts

    # ---- row-level comparison against the frozen Goal18B export ----
    new_rows = json.loads((output / EXPORT).read_text(encoding='utf-8'))['recipes']
    delta = comparison(frozen_rows, new_rows)
    ck(len(frozen_rows) == 36 and len(new_rows) == 41 and new_rows[:36] == frozen_rows and delta['added'] == new_rows[36:] and len(delta['added']) == 5 and not delta['removed'] and not delta['changed'], 'Goal20A export is the Goal18B table plus five appended rows (added 5, removed 0, changed 0)')
    ck(all(r['fluid'] == ['SULFURIC_ACID', 500] and r['duration'] == 600 and r['productivity'] == 0.05 and r['output'][1:] == [1, None] and r['input'][2:] == [1, 32767] for r in delta['added']), 'appended rows are 1 ore block, 500 mB sulfuric acid, 600 ticks, 0.05, one plain crystal')
    ck(list(example) == ['comment', 'recipes'] and example['recipes'] == [new_rows[0], new_rows[3]] + new_rows[36:] and json.loads(EXAMPLE.read_text(encoding='utf-8')) == example, 'the merge example rows are the exported rows 0, 3 and 36..40')
    (output / COMPARISON).write_text(json.dumps({'batch': 'Goal20A', 'baseline': 'migration/goal18b-crystallizer-recipes.json (36 rows, Goal18B export)', 'live': EXPORT + ' (41 rows)', 'added': len(delta['added']), 'removed': len(delta['removed']), 'changed': len(delta['changed']),
                                               'added_rows': delta['added'], 'note': 'Rows matched on input identity plus acid internal name; the 36 Goal18B rows are unchanged in content and order (verified by Goal20ARecipeRegression.frozen18B).'}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    report['comparison'] = {'added': len(delta['added']), 'removed': 0, 'changed': 0}
    report['custom_example'] = {'path': str(EXAMPLE.relative_to(ROOT)), 'sha256': sha(EXAMPLE), 'rows_from_export': [0, 3, *range(36, 41)], 'rows': len(example['recipes'])}
    report['exports'] = {n: {'path': str((output / n).relative_to(ROOT)), 'sha256': sha(output / n)} for n in (EXPORT, COMPARISON, expectation_file.name)}
    write_report(output, report)

    # ---- mutations ----
    report['mutations'] = []
    if args.mutations:
        for label, (text, fragment) in anchored(live[CRYSTALLIZER], crystallizer_mutations(live[CRYSTALLIZER])).items():
            directory = output / 'mutations' / label
            mutated_run(label, directory, text, classes, GSON, java, javac, arguments(directory), fragment, report['mutations'])
            report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
            write_report(output, report)
            if not report['source_stable_after_run']: raise SystemExit('Source changed during mutation')
        # Static mutations on edited copies of the source text or the parsed generated JSON (a regenerated JSON cannot be produced here, so the provider text is
        # checked statically against the generated file and the parsed generated copy is mutated instead).
        def mutate(source_json, edit):
            copy = json.loads(json.dumps(source_json)); edit(copy); return copy
        def expect_failure(label, fragment, kind, function):
            try: function()
            except AssertionError as error:
                if fragment not in str(error): raise SystemExit(f'Mutation {label} failed with the wrong assertion: {error}')
                report['mutations'].append({'label': label, 'expected_fragment': fragment, 'detected': True, 'kind': 'static ' + kind, 'message': str(error)})
            else: raise SystemExit('Static mutation not detected: ' + label)
        chem = live[CHEMICAL]
        yellow_old = 'new ComparableStack(NtmItems.BILLET_URANIUM.get(), 2), new ComparableStack(NtmItems.SULFUR.get(), 2)'
        if chem.count(yellow_old) != 1: raise SystemExit('Mutation anchor missing: yellowcake')
        expect_failure('yellowcake_back_to_powder_uranium', 'chem.yellowcake inputs are 2 BILLET_URANIUM and 2 SULFUR', 'yellowcake registration on a ChemicalPlantRecipes source copy',
                       lambda: rs.check_yellowcake(chem.replace(yellow_old, yellow_old.replace('BILLET_URANIUM', 'POWDER_URANIUM'), 1), chem_original, items, rs.quiet))
        provider = live[PROVIDER]
        rod_old = '.requires(NtmItems.BILLET_TH232.get(), 2)'
        if provider.count(rod_old) != 1: raise SystemExit('Mutation anchor missing: rod billet count')
        expect_failure('rod_billet_count_3_generated', 'rod ingredients are exactly the empty rod and two billet_th232', 'rod recipe on a generated-file copy',
                       lambda: rs.check_rod(mutate(rod_json, lambda d: d['ingredients'].append({'item': 'hbmsntm:billet_th232'})), provider, neo_order, rod_original, rs.quiet))
        expect_failure('rod_billet_count_3_provider', 'provider requires two BILLET_TH232', 'rod recipe on a provider-source copy',
                       lambda: rs.check_rod(rod_json, provider.replace(rod_old, '.requires(NtmItems.BILLET_TH232.get(), 3)', 1), neo_order, rod_original, rs.quiet))
        expect_failure('rod_meta_natural_uranium_fuel_generated', 'rod META equals ZirnoxType.TH232 ordinal', 'rod recipe on a generated-file copy',
                       lambda: rs.check_rod(mutate(rod_json, lambda d: d['result'].__setitem__('components', {'hbmsntm:meta': neo_order.index('NATURAL_URANIUM_FUEL')})), provider, neo_order, rod_original, rs.quiet))
        smelt_old = 'NtmBlocks.ORE_THORIUM_DEEPSLATE.get(), NtmItems.INGOT_TH232.get(), 0.7F);'
        if provider.count(smelt_old) != 1: raise SystemExit('Mutation anchor missing: thorium smelting')
        expect_failure('thorium_ore_smelting_back_to_ingot_thorium_fuel', 'provider ore smelting of ORE_THORIUM and its deepslate targets INGOT_TH232', 'smelting on a provider-source copy',
                       lambda: rs.check_smelting(provider.replace(smelt_old, smelt_old.replace('INGOT_TH232', 'INGOT_THORIUM_FUEL'), 1), smelting, smelting_original, rs.quiet))
        expect_failure('thorium_ore_smelting_json_experience_1', 'ingot_th232_from_smelting_ore_thorium.json is smelting ore_thorium', 'smelting on a generated-file copy',
                       lambda: rs.check_smelting(provider, {**smelting, 'smelting': {**smelting['smelting'], 'ore_thorium': mutate(smelting['smelting']['ore_thorium'], lambda d: d.__setitem__('experience', 1.0))}}, smelting_original, rs.quiet))
        write_report(output, report)
    report['mutations_detected'] = sum(1 for m in report['mutations'] if m.get('detected'))
    report['mutations_total'] = len(report['mutations'])
    report['python_assertions'] = len(checks); report['python_assertion_labels'] = checks
    report['source_sha256_after_run'] = {p: sha(SOURCE / p) for p in hashes}
    report['source_stable_after_run'] = hashes == report['source_sha256_after_run']
    report['original_unchanged'] = {p: sha(original_root / p) == report['original_expectation']['original_file_sha256'][p] for p in original_files}
    total = fixture_counts['assertions'] + len(checks)
    report['checks'] = {'total': total, 'crystallizer_fixture': fixture_counts['assertions'], 'static': len(checks), 'scenarios': fixture_counts['scenarios']}
    write_report(output, report)
    if not report['source_stable_after_run'] or not all(report['original_unchanged'].values()): raise SystemExit('Production or original source changed during check')
    print(f"Goal20A recipes: {total} assertions ({fixture_counts['assertions']} crystallizer fixture + {len(checks)} static); {fixture_counts['scenarios']} independent scenarios; 0 executed ticks")
    print(f"Compiled and static mutations detected: {report['mutations_detected']}/{report['mutations_total']}")
    print(f'report: {output / "report.json"}')

if __name__ == '__main__': main()
