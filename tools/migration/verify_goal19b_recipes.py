"""Goal19B assembly recipe ass.iturbine: the live production table is the frozen 70bc9899 table plus exactly one appended row.

Compiles the production AssemblyMachineRecipes (and the inherited recipe-world sources) over the declared stand-ins with the existing JDK 21
and Gson, once for the live source and once for the frozen 70bc9899 source (package goal19b.base), and runs the fixture for both ENABLE_528 modes.
The new row's expected numbers are parsed from the original AssemblyMachineRecipes.java:434-436 (read-only). No Gradle, no game.
Mutations of the production row are applied to temporary copies under the run directory; each must compile and fail the expected assertion."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18b_regression.common import ROOT, SOURCE, sha, jdk, gson, classpath, adapter_hashes, run, write_report
from goal19b_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES
import uuid

FIXTURE = Path(__file__).resolve().parent / 'goal19b_regression'
OUT = ROOT / 'build/migration/goal19b'
ORIGINAL = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
ASSEMBLY = 'com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
ORIGINAL_ASSEMBLY = 'src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
BASELINE_COMMIT = '70bc989982eb0f05f54148158428baf2f37caddb'  # Goal19A commit 3ed0cd5f plus the separate post-19A fix: the last tree without Goal19B
FQN = 'com.hbm.inventory.recipes.Goal19BRecipeRegression'
NAME = 'ass.iturbine'
WILDCARD = 32767  # MetaHelper.WILDCARD_VALUE: a plain ComparableStack(item, n) matches any meta (RecipesCommon.java:68-72)
CONTEXT = ('com/hbm/items/NtmItems.java', 'com/hbm/items/WireDenseItem.java', 'com/hbm/blocks/NtmBlocks.java', 'com/hbm/inventory/RecipesCommon.java', 'com/hbm/inventory/NtmTags.java',
           'com/hbm/inventory/MetaHelper.java', 'com/hbm/inventory/fluid/Fluids.java', 'com/hbm/config/NtmConfig.java')
# Original expression -> (NEO kind, id, meta). The mapping is the port decision under test; the numbers come from the original source.
MAPPING = {
    'STEEL.plate()': ('tag', 'c:plates/steel', -1),
    'RUBBER.ingot()': ('item', 'hbmsntm:ingot_rubber', WILDCARD),
    'ModItems.turbine_titanium': ('item', 'hbmsntm:turbine_titanium', WILDCARD),
    'GOLD.wireDense()': ('item', 'hbmsntm:wire_dense', None),  # meta = the original material id of GOLD (Mats.java MAT_GOLD), checked below
    'DURA.pipe()': ('item', 'hbmsntm:pipe_dura_steel', WILDCARD),
    'ModItems.circuit+BASIC': ('item', 'hbmsntm:circuit_integrated_board', WILDCARD),
}
OUTPUT_MAPPING = {'machine_industrial_turbine': 'hbmsntm:machine_industrial_turbine'}
STACK = re.compile(r'new (OreDictStack|ComparableStack)\(([^()]*(?:\([^()]*\))?[^()]*)\)')

def mutations(text):
    """Anchored mutations of the production row: label -> (anchor, replacement, expected AssertionError fragment). Every anchor must occur exactly once."""
    head = '.outputItems(new ItemStack(NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get(), 1))\n                .inputItems(new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 16),'
    rubber = 'new ComparableStack(NtmItems.INGOT_RUBBER.get(), 4),\n                        new ComparableStack(NtmItems.TURBINE_TITANIUM.get(), 2),'
    wire = 'new ComparableStack(MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 4, WireDenseItem.Type.GOLD.meta)),\n                        new ComparableStack(NtmItems.PIPE_DURA_STEEL.get(), 4),'
    start = text.index('        this.register(new GenericRecipe("ass.iturbine")')
    end = text.index('NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 2)));', start) + len('NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 2)));\n')
    whole = text[start:end]
    return {
        'registration_dropped': (whole, '', 'live catalog is the base catalog plus exactly one new row ass.iturbine appended last'),
        'steel_plates_16_to_15': (head, head.replace('PLATES_STEEL, 16)', 'PLATES_STEEL, 15)'), 'ass.iturbine input 0 is tag c:plates/steel x16'),
        'duration_200_to_100': ('new GenericRecipe("ass.iturbine").setup(200, 100)', 'new GenericRecipe("ass.iturbine").setup(100, 100)', 'ass.iturbine duration 200 ticks'),
        'rubber_ingot_replaced_by_copper_ingot': (rubber, rubber.replace('INGOT_RUBBER', 'INGOT_COPPER'), 'ass.iturbine input 1 is item hbmsntm:ingot_rubber x4'),
        'dense_wire_gold_to_copper': (wire, wire.replace('WireDenseItem.Type.GOLD.meta', 'WireDenseItem.Type.COPPER.meta'), 'ass.iturbine input 3 is item hbmsntm:wire_dense x4 meta 7900'),
        'output_count_1_to_2': ('new ItemStack(NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get(), 1)', 'new ItemStack(NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get(), 2)', 'ass.iturbine outputs 1 x hbmsntm:machine_industrial_turbine with no meta'),
    }

def run_dir(kind):
    output = OUT / kind / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    return output

def git_show(path):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(), 'show', BASELINE_COMMIT + ':' + path], cwd=ROOT)

def parse_original(source):
    """Expected row facts from the original AssemblyMachineRecipes.java (the normal branch only; inputItemsEx is not migrated)."""
    text = (source / ORIGINAL_ASSEMBLY).read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    lines = text.split('\n')
    first = next(i for i, l in enumerate(lines) if 'new GenericRecipe("ass.iturbine")' in l)
    block = '\n'.join(lines[first:first + 3])
    assert text.count('"ass.iturbine"') == 1 and '.inputItems(' in lines[first + 1] and '.inputItemsEx(' in lines[first + 2], 'original ass.iturbine statement not found in the expected shape'
    setup = re.search(r'\.setup\((\d+), (\d+)\)', lines[first]); output = re.search(r'new ItemStack\(ModBlocks\.(\w+), (\d+)\)', lines[first])
    assert setup and output and output.group(1) in OUTPUT_MAPPING, 'original setup/output not recognised'
    normal = lines[first + 1]
    inputs = []
    for kind, inner in STACK.findall(normal):
        parts = [p.strip() for p in inner.split(',')]
        key = parts[0] + ('+BASIC' if len(parts) > 2 and 'EnumCircuitType.BASIC' in parts[2] else '')
        assert key in MAPPING, 'unmapped original input ' + key
        inputs.append({'original': f'{kind}({inner})', 'key': key, 'count': int(parts[1])})
    mats = (source / 'src/main/java/com/hbm/inventory/material/Mats.java').read_text(encoding='utf-8-sig')
    gold = int(re.search(r'MAT_GOLD\s*=\s*makeSmeltable\((\d+),', mats).group(1))
    rows = []
    for item in inputs:
        kind, ident, meta = MAPPING[item['key']]
        rows.append({'original': item['original'], 'kind': kind, 'id': ident, 'count': item['count'], 'meta': gold if meta is None else meta})
    return {'source': f'{ORIGINAL_ASSEMBLY}:{first + 1}-{first + 3}', 'source_lines': block, 'name': NAME, 'duration': int(setup.group(1)), 'power': int(setup.group(2)),
            'output': {'id': OUTPUT_MAPPING[output.group(1)], 'count': int(output.group(2)), 'original': output.group(1)}, 'inputs': rows, 'gold_material_id': gold,
            'expected_values': {'duration': 200, 'power': 100, 'counts': [16, 4, 2, 4, 4, 2]}}

def registry_checks(original):
    """Each NEO id the row uses is a production registration; the stand-in ids derive from the field names, so the field must be the id upper-cased."""
    items = (SOURCE / 'com/hbm/items/NtmItems.java').read_text(encoding='utf-8')
    blocks = (SOURCE / 'com/hbm/blocks/NtmBlocks.java').read_text(encoding='utf-8')
    found = {}
    for field in ('TURBINE_TITANIUM', 'INGOT_RUBBER', 'PIPE_DURA_STEEL', 'WIRE_DENSE', 'CIRCUIT_INTEGRATED_BOARD', 'INGOT_COPPER'):
        m = re.search(r'\b' + field + r'\s*=\s*(?:ITEMS\.)?register\w*\("([a-z0-9_]+)"', items)
        if not m or m.group(1) != field.lower(): raise SystemExit(f'Production id of NtmItems.{field} is not {field.lower()}')
        found['hbmsntm:' + m.group(1)] = f'NtmItems.{field}'
    m = re.search(r'\bMACHINE_INDUSTRIAL_TURBINE\s*=\s*register\w*\("([a-z0-9_]+)"', blocks)
    if not m or m.group(1) != 'machine_industrial_turbine': raise SystemExit('Production id of NtmBlocks.MACHINE_INDUSTRIAL_TURBINE is not machine_industrial_turbine')
    found['hbmsntm:' + m.group(1)] = 'NtmBlocks.MACHINE_INDUSTRIAL_TURBINE'
    for row in original['inputs']:
        if row['kind'] == 'item' and row['id'] not in found: raise SystemExit('Row input id is not a production registration: ' + row['id'])
    if original['output']['id'] not in found: raise SystemExit('Row output id is not a production registration')
    tags = (SOURCE / 'com/hbm/inventory/NtmTags.java').read_text(encoding='utf-8')
    if 'PLATES_STEEL = commonTag("plates/steel")' not in tags or 'ResourceLocation.fromNamespaceAndPath("c", name)' not in tags: raise SystemExit('Production PLATES_STEEL is not c:plates/steel')
    wire = (SOURCE / 'com/hbm/items/WireDenseItem.java').read_text(encoding='utf-8')
    gold = re.search(r'\bGOLD\((\d+),', wire)
    if not gold or int(gold.group(1)) != original['gold_material_id'] or 'GOLD(7900, "hbmmat.gold"' not in wire: raise SystemExit('Production WireDenseItem.Type.GOLD.meta is not the original GOLD material id')
    return found

def static_goal18b():
    """Static (no execution) account of what the new row does to the Goal18B recipe fixture."""
    path = ROOT / 'tools/migration/goal18b_regression/Goal18BRecipeRegression.java'
    lines = path.read_text(encoding='utf-8').split('\n')
    live_use = [i + 1 for i, l in enumerate(lines) if 'catalog(AssemblyMachineRecipes.INSTANCE)' in l]
    start = next(i for i, l in enumerate(lines) if 'private static void assemblyUnchanged()' in l)
    end = next(i for i, l in enumerate(lines) if 'public static void main' in l)
    assembly_checks = [i + 1 for i in range(start, end) if 'check(' in lines[i]]
    ass_mentions = [i + 1 for i, l in enumerate(lines) if '"ass.' in l]
    order_line = next(l for l in lines if 'assemblyUnchanged();' in l and 'defaults();' in l)
    calls = [c.strip() for c in order_line.split(';') if c.strip()]
    if live_use != [306] or lines[306].strip().count('live.equals(baseline)') != 1 or calls[-1] != 'assemblyUnchanged()' or ass_mentions != [309]:
        raise SystemExit('Goal18B recipe fixture no longer has the assembly check structure the static account relies on')
    return {'file': str(path.relative_to(ROOT)), 'live_assembly_catalog_use_lines': live_use, 'assembly_unchanged_check_lines': assembly_checks, 'ass_row_name_mentions': ass_mentions,
            'check_307_text': lines[306].strip(), 'check_308_text': lines[307].strip(), 'check_309_text': lines[308].strip(), 'main_call_order': calls,
            'conclusion': 'Line 307 (live.size() == baseline.size() && live.equals(baseline)) is false once ass.iturbine is appended; it runs last in main after all crystallizer coverage. '
                          'Line 308 (key-order list equality) is violated by the same row but is never reached because 307 throws first; line 309 (ass.acidizer still registered) still holds. '
                          'The Goal18B baseline commit is the Goal18A static-review commit, so every other Goal18B check is independent of the assembly table.'}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--source', type=Path, default=ORIGINAL, help='original Hbm-s-Nuclear-Tech-GIT worktree (default: sibling directory)')
    args = parser.parse_args()
    original_root = args.source.resolve()
    if not (original_root / ORIGINAL_ASSEMBLY).is_file(): raise SystemExit('Original AssemblyMachineRecipes.java not found: ' + str(original_root))
    output = run_dir('recipes')
    java, javac = jdk(); GSON = gson()
    fixture = FIXTURE / 'Goal19BRecipeRegression.java'
    start = json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))
    # Frozen base: the 70bc9899 blob, cross-checked against the recorded start (baseline.json and the frozen copy).
    blob = git_show('src/main/java/' + ASSEMBLY)
    baseline = blob.decode('utf-8').replace('\r\n', '\n')
    key = 'src/main/java/' + ASSEMBLY
    frozen_copy = OUT / 'baseline-files' / key
    base_check = {'commit': BASELINE_COMMIT, 'target_head_recorded': start['target_head'], 'blob_sha256_lf': hashlib.sha256(baseline.encode('utf-8')).hexdigest(),
                  'recorded_worktree_sha256': start['files'][key], 'frozen_copy_sha256': sha(frozen_copy), 'frozen_copy_lf_sha256': hashlib.sha256(frozen_copy.read_bytes().replace(b'\r\n', b'\n')).hexdigest()}
    if start['target_head'] != BASELINE_COMMIT or base_check['recorded_worktree_sha256'] != base_check['frozen_copy_sha256'] or base_check['blob_sha256_lf'] != base_check['frozen_copy_lf_sha256']:
        raise SystemExit('Frozen assembly baseline does not agree with baseline.json: ' + json.dumps(base_check))
    assert baseline.count('package com.hbm.inventory.recipes;') == 1
    baseline = baseline.replace('package com.hbm.inventory.recipes;', 'package goal19b.base;\nimport com.hbm.inventory.recipes.*;', 1)
    # Original expectation and production registrations.
    head = subprocess.run(['git', '-c', 'safe.directory=' + original_root.as_posix(), '-C', str(original_root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    if head != start['source_head']: raise SystemExit(f'Original HEAD {head} is not the recorded baseline {start["source_head"]}')
    original = parse_original(original_root)
    if (original['duration'], original['power'], [r['count'] for r in original['inputs']], original['output']['count']) != (200, 100, [16, 4, 2, 4, 4, 2], 1) or original['gold_material_id'] != 7900:
        raise SystemExit('Original ass.iturbine no longer has the numbers the Goal19B contract records: ' + json.dumps(original['expected_values']))
    ids = registry_checks(original)
    expected_file = output / 'original-ass-iturbine.json'
    expected_file.write_text(json.dumps(original, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    live_text = (SOURCE / ASSEMBLY).read_text(encoding='utf-8')
    stubs = recipe_stubs(SOURCE, [fixture.read_text(encoding='utf-8'), baseline, live_text])
    stubs['goal19b/base/AssemblyMachineRecipes.java'] = baseline
    if set(RECIPE_SOURCES) & set(stubs): raise SystemExit('Production shadowed by a stand-in')
    hashes = {p: sha(SOURCE / p) for p in dict.fromkeys((*RECIPE_SOURCES, *CONTEXT))}
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    generated = {p.relative_to(output).as_posix(): sha(p) for p in paths}
    paths += [SOURCE / p for p in RECIPE_SOURCES] + [fixture]
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    own = [Path(__file__).resolve(), FIXTURE / 'recipe_stubs.py', fixture]
    report = {'evidence': 'Production AssemblyMachineRecipes (live, with ass.iturbine) and the frozen 70bc9899 source over declared registry/tag/component/Gson stand-ins; compile and fixture execution only, not game, JEI, datapack or in-game crafting acceptance',
              'baseline_commit': BASELINE_COMMIT, 'baseline_check': base_check, 'source_sha256': hashes, 'fixture_sha256': {str(p.relative_to(ROOT)): sha(p) for p in own},
              'original_expectation': {'path': str(expected_file.relative_to(ROOT)), 'sha256': sha(expected_file), 'original_head': head, 'source': original['source'], 'source_lines': original['source_lines'],
                                       'original_file_sha256': sha(original_root / ORIGINAL_ASSEMBLY)},
              'cache_sha256': {str(GSON): sha(GSON)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)}, 'registry_ids': ids,
              'generated_stubs_sha256': generated, 'commands': [], 'adapter_sha256': adapter_hashes(),
              'service_boundaries': ['Item/Block registry, tags and data components are stand-ins whose ids derive from the field names; the verifier checks each used id against the production registrations (NtmItems, NtmBlocks), PLATES_STEEL = c:plates/steel and WireDenseItem.Type.GOLD = 7900 against the original GOLD material id',
                                     'The real Gson jar and the production loader base (GenericRecipes/GenericRecipe/SerializableRecipe) are used; the frozen base is the 70bc9899 AssemblyMachineRecipes compiled as goal19b.base',
                                     'The 18B JEI/Crystallizer sources remain in the inherited compile set but are not exercised by this fixture'],
              'goal18b_static_impact': static_goal18b()}
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), FQN, output, expected_file]]
    print(output, flush=True)
    for index, command in enumerate(commands):
        code, text = run(command)
        (output / ('compile.log', 'run.log')[index]).write_text(text, encoding='utf-8')
        report['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': text})
        report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
        write_report(output, report)
        print(text, end='', flush=True)
        if code or not report['source_stable_after_run']: raise SystemExit(code or 'Production changed during check')
        if index:
            counts = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
            if not counts: raise SystemExit('Missing evidence counts')
            report['counts'] = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, counts.groups())))
    catalog = json.loads((output / 'goal19b-assembly-catalog.json').read_text(encoding='utf-8'))
    report['catalog'] = {mode: {k: v for k, v in entry.items() if k != 'newRow'} for mode, entry in catalog.items()}
    # Compiled mutations of the production row: each must compile, then fail the expected behavioural assertion.
    report['mutations'] = []
    for label, (old, new, fragment) in mutations(live_text).items():
        if live_text.count(old) != 1: raise SystemExit('Mutation anchor missing or not unique: ' + label)
        directory = output / 'mutations' / label; target = directory / ASSEMBLY; target.parent.mkdir(parents=True)
        target.write_text(live_text.replace(old, new, 1), encoding='utf-8')
        compiled = directory / 'classes'; compiled.mkdir()
        record = {'label': label, 'expected_fragment': fragment, 'generated_files_sha256': {target.relative_to(ROOT).as_posix(): sha(target)}, 'commands': []}
        report['mutations'].append(record)
        for index, command in enumerate([[javac, '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, target],
                                         [java, '-ea', '-cp', classpath(compiled, classes, GSON), FQN, directory, expected_file]]):
            code, out = run(command)
            (directory / ('compile.log', 'run.log')[index]).write_text(out, encoding='utf-8')
            record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
            report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
            write_report(output, report)
            if not report['source_stable_after_run']: raise SystemExit('Source changed during mutation')
            if index == 0 and code: raise SystemExit('Mutation compile failure is not detection: ' + out)
            if index == 1 and (code == 0 or 'java.lang.AssertionError' not in out or fragment not in out):
                raise SystemExit(f'Mutation not detected by the expected assertion: {label} (expected "{fragment}")\n' + out)
        record['compiled_successfully'] = True; record['detected'] = True
    report['mutations_detected'] = len(report['mutations'])
    report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
    report['source_sha256_after_run'] = {p: sha(SOURCE / p) for p in hashes}
    report['exports'] = {'goal19b-assembly-catalog.json': {'path': str((output / 'goal19b-assembly-catalog.json').relative_to(ROOT)), 'sha256': sha(output / 'goal19b-assembly-catalog.json')}}
    write_report(output, report)
    if not report['source_stable_after_run']: raise SystemExit('Production changed during check')
    c = report['counts']
    print(f"Goal19B recipes: {c['assertions']} assertions; {c['scenarios']} independent scenarios; {c['ticks']} executed ticks")
    print(f"Compiled recipe contract mutations detected: {len(report['mutations'])}/{len(report['mutations'])}")
    print(output / 'report.json')

if __name__ == '__main__': main()
