"""Goal20B recipes and resources: assembly ass.gascent, the gas centrifuge pseudo-fluid table and summary rows, the upgrade and enriched ZIRNOX rod crafting
recipes, the fifteen language keys, the six imported assets, the provider/registration edits and the generated files.

Assembly: the production AssemblyMachineRecipes (live) and the frozen Goal20B-start source (package goal20b.base, build/migration/goal20b/baseline-files)
are compiled over the inherited Goal19C recipe-world stand-ins with the existing JDK 21 and Gson and run in both ENABLE_528 modes; the new row's expected
numbers are parsed from the original AssemblyMachineRecipes.java:282-283 (read-only).
Static: the production GasCentrifugeRecipes against the original GasCentrifugeRecipes.java:24-34,94-101; the provider, language provider, zh_cn.json and
mapping against the frozen start and the original language files; the asset copies against the original assets; the generated tree (read at run time;
a missing generated file fails the run with a clear message after every other check).
Mutations (--mutations) are anchored copies under the run directory; each must compile (where compiled) and fail the expected assertion. No Gradle, no game."""
from pathlib import Path
import argparse, json, re, subprocess, sys, uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, sha, jdk, gson, classpath, adapter_hashes, run, write_report
from goal19c_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES
from goal20b_regression import recipe_static as rs

FIXTURE = Path(__file__).resolve().parent / 'goal20b_regression'
GOAL19C_FIXTURE = Path(__file__).resolve().parent / 'goal19c_regression'
OUT = ROOT / 'build/migration/goal20b'
ORIGINAL = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
GEN = ROOT / 'src/generated/resources'
ASSETS = ROOT / 'src/main/resources/assets/hbmsntm'
ZH = ROOT / 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'
MAP = ROOT / 'migration/localization/zh_cn-map.json'
GOAL19C_EXPORT = ROOT / 'migration/goal19c-assembly-recipes.json'
ASSEMBLY = 'com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
GASCENT = 'com/hbm/inventory/recipes/GasCentrifugeRecipes.java'
PROVIDER = 'com/hbm/datagen/NtmRecipeProvider.java'
LANG = 'com/hbm/datagen/NtmLanguageProvider.java'
ROD_ITEM = 'com/hbm/items/machine/ZirnoxRodItem.java'
FQN = 'com.hbm.inventory.recipes.Goal20BRecipeRegression'
EXPECTED_ROWS = {'528=false': (48, 49), '528=true': (44, 45)}  # (frozen start = the Goal19C live table, live)
CONTEXT = tuple(dict.fromkeys(('com/hbm/items/NtmItems.java', 'com/hbm/blocks/NtmBlocks.java', 'com/hbm/inventory/RecipesCommon.java', 'com/hbm/inventory/NtmTags.java',
                               'com/hbm/inventory/MetaHelper.java', GASCENT, PROVIDER, LANG, ROD_ITEM, 'com/hbm/datagen/NtmBlockStateProvider.java',
                               *(p for p in rs.PROVIDER_EDITS))))

checks = []
def ck(condition, label):
    if not condition: raise AssertionError(label)
    checks.append(label)

def run_dir(kind):
    output = OUT / kind / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    return output

def mutated_run(label, directory, text, classes, GSON, java, javac, run_args, fragment, record_list):
    target = directory / ASSEMBLY; target.parent.mkdir(parents=True)
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
    print(f'mutation {label}: detected (compiled; expects "{fragment}")', flush=True)

def assembly_mutations(text):
    """label -> (anchor, replacement, expected AssertionError fragment). Every anchor must occur exactly once."""
    start = text.index('        this.register(new GenericRecipe("ass.gascent")')
    end = text.index(';', start) + 2
    return {
        'assembly_row_dropped': (text[start:end], '', 'live catalog is the base catalog plus exactly one new row ass.gascent'),
        'assembly_duration_400_to_300': ('new GenericRecipe("ass.gascent").setup(400, 100)', 'new GenericRecipe("ass.gascent").setup(300, 100)', 'ass.gascent duration 400 ticks'),
        'assembly_circuit_analog': ('                        new ComparableStack(NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get(), 1)));',
                                    '                        new ComparableStack(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1)));', 'ass.gascent input 4 is item hbmsntm:circuit_military_grade_board x1'),
    }

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
    report = {'evidence': 'Production AssemblyMachineRecipes (live, with ass.gascent) and the frozen Goal20B-start assembly source over the Goal19C recipe-world registry/tag/component/Gson '
                          'stand-ins, plus static checks of GasCentrifugeRecipes against the original table, the provider/registration edits against the frozen start, the language '
                          'provider, zh_cn.json and mapping against the original language files, the asset copies and the generated JSON; compile and fixture execution only, not game, '
                          'JEI, datapack, resource reload, rendering or in-game crafting/assembly acceptance',
              'output': output.relative_to(ROOT).as_posix(), 'commands': [], 'target_baseline': {'target_head': start['target_head'], 'source_head': start['source_head']}}
    print(output, flush=True)
    hashes = {p: sha(SOURCE / p) for p in dict.fromkeys((*RECIPE_SOURCES, *CONTEXT))}

    # ---- original facts (read-only) ----
    original_head = subprocess.run(['git', '-c', 'safe.directory=' + original_root.as_posix(), '-C', str(original_root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    ck(original_head == start['source_head'], f'Original HEAD {original_head} is the recorded baseline {start["source_head"]}')
    assembly = rs.parse_original_gascent(original_root, items, blocks)
    ck(assembly['source'].endswith(':282-283') and (assembly['duration'], assembly['power'], [r['count'] for r in assembly['inputs']], assembly['output']['count']) == (400, 100, [4, 8, 2, 8, 1], 1),
       'original ass.gascent (AssemblyMachineRecipes.java:282-283) is 400 ticks, 100 HE/t, inputs 4/8/2/8/1, output x1: ' + json.dumps([r['original'] for r in assembly['inputs']]))
    ck([(r['kind'], r['stub_id']) for r in assembly['inputs']] == [('item', 'hbmsntm:centrifuge_element'), ('tag', 'ntm:ingots_plastic'), ('item', 'hbmsntm:ingot_desh'), ('tag', 'c:plates/steel'),
                                                                    ('item', 'hbmsntm:circuit_military_grade_board')],
       'ass.gascent maps to 4 CENTRIFUGE_ELEMENT + 8 tag ntm:ingots_plastic + 2 INGOT_DESH + 8 tag c:plates/steel + 1 CIRCUIT_MILITARY_GRADE_BOARD (circuit ADVANCED)')
    for row in assembly['inputs']:
        if row['kind'] == 'item': ck(row['stub_id'] == row['id'], f'stand-in id equals the production id for {row["field"]}: {row["id"]}')
    ck(assembly['output']['id'] == assembly['output']['stub_id'] == 'hbmsntm:machine_gas_centrifuge', 'the output stand-in id equals the production id machine_gas_centrifuge')
    ck(assembly['previous_row']['line'] == 279 and assembly['pool_528'] is not None and 'gascent' in assembly['pool_528'],
       'in the original, ass.centrifuge (:279) precedes ass.gascent, whose 528 pool (:285) is not migrated')
    table_original = rs.parse_original_gascent_table(original_root)
    lang_original = rs.original_lang(original_root)
    local_sources = rs.check_original_local_sources(original_root, ck)
    crafting_original = rs.parse_original_crafting(original_root)
    expected_assembly = output / 'original-ass-gascent.json'
    expected_assembly.write_text(json.dumps(assembly, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    original_files = list(rs.ORIGINAL_FILES) + ['src/main/resources/assets/hbm/' + p for p in rs.ASSETS.values()]
    report['original_expectation'] = {'original_head': original_head, 'assembly': assembly, 'expectation_path': expected_assembly.relative_to(ROOT).as_posix(),
                                      'expectation_sha256': sha(expected_assembly), 'gas_centrifuge_table': table_original, 'local_text_sources': local_sources,
                                      'crafting': crafting_original, 'original_file_sha256': {p: sha(original_root / p) for p in original_files}}

    # ---- frozen start copies ----
    frozen = {}
    for rel in (ASSEMBLY, LANG, *rs.PROVIDER_EDITS):
        key = 'src/main/java/' + rel
        copy = OUT / 'baseline-files' / key
        ck(sha(copy) == start['files'][key], f'Frozen copy of {rel} has the hash recorded in baseline.json')
        frozen[rel] = copy.read_text(encoding='utf-8')
    frozen_zh_path = OUT / 'baseline-files/src/main/resources/assets/hbmsntm/lang/zh_cn.json'
    frozen_map_path = OUT / 'baseline-files/migration/localization/zh_cn-map.json'
    ck(sha(frozen_zh_path) == start['files']['src/main/resources/assets/hbmsntm/lang/zh_cn.json'] and sha(frozen_map_path) == start['files']['migration/localization/zh_cn-map.json'],
       'the frozen zh_cn.json and zh_cn-map.json have the hashes recorded in baseline.json')
    frozen_en_key = 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
    frozen_en_count = len(json.loads((OUT / 'baseline-files' / frozen_en_key).read_text(encoding='utf-8'))) if (OUT / 'baseline-files' / frozen_en_key).is_file() else 2329
    live = {rel: (SOURCE / rel).read_text(encoding='utf-8') for rel in (ASSEMBLY, GASCENT, PROVIDER, LANG, ROD_ITEM, *rs.PROVIDER_EDITS)}
    records = {p.relative_to(ROOT).as_posix(): sha(p) for p in (OUT / 'baseline.json', frozen_zh_path, frozen_map_path, GOAL19C_EXPORT, ZH, MAP)}

    # ---- (a) assembly source text ----
    report['live_assembly_statement'] = rs.check_live_gascent(live[ASSEMBLY], ck)

    # ---- (c) pseudo fluids and summary rows ----
    neo_table = rs.parse_neo_gascent_table(live[GASCENT])
    rs.check_gascent_table(neo_table, table_original, ck)
    report['gas_centrifuge_table'] = {'production': neo_table, 'deferred': ['MUD_HEAVY and MUD outputs (nuclear_waste_tiny missing)', 'WATZ -> MUD conversion', 'the WATZ summary row :101']}

    # ---- (d) language ----
    zh = json.loads(ZH.read_text(encoding='utf-8')); frozen_zh = json.loads(frozen_zh_path.read_text(encoding='utf-8'))
    mapping = json.loads(MAP.read_text(encoding='utf-8'))['entries']; frozen_mapping = json.loads(frozen_map_path.read_text(encoding='utf-8'))['entries']
    report['language'] = rs.check_language(live[LANG], frozen[LANG], zh, frozen_zh, mapping, frozen_mapping, lang_original, ck)

    # ---- (e) assets ----
    contents = {neo: (ASSETS / neo).read_bytes() for neo in rs.ASSETS}
    report['assets'] = rs.check_assets(ASSETS, original_root / 'src/main/resources/assets/hbm', contents, ck)
    report['asset_sha256'] = {(ASSETS / neo).relative_to(ROOT).as_posix(): sha(ASSETS / neo) for neo in rs.ASSETS}

    # ---- (f) provider and registration edits; provider crafting ----
    report['edits'] = rs.check_edits(frozen, live, ck)
    neo_order = rs.zirnox_order(live[ROD_ITEM][live[ROD_ITEM].index('enum ZirnoxType'):])
    report['provider_crafting'] = rs.check_provider_crafting(live[PROVIDER], neo_order, crafting_original, ck)

    # ---- (a) compile and run the assembly catalog ----
    fixture = FIXTURE / 'Goal20BRecipeRegression.java'
    baseline = frozen[ASSEMBLY].replace('\r\n', '\n')
    ck(baseline.count('package com.hbm.inventory.recipes;') == 1, 'frozen assembly source has one package declaration')
    baseline = baseline.replace('package com.hbm.inventory.recipes;', 'package goal20b.base;\nimport com.hbm.inventory.recipes.*;', 1)
    # The Goal19C fixture text is passed (not compiled) so the inherited stand-in registry carries the ids the Goal19C anchors require.
    stubs = recipe_stubs(SOURCE, [fixture.read_text(encoding='utf-8'), baseline, live[ASSEMBLY], (GOAL19C_FIXTURE / 'Goal19CRecipeRegression.java').read_text(encoding='utf-8')])
    stubs['goal20b/base/AssemblyMachineRecipes.java'] = baseline
    ck(not (set(RECIPE_SOURCES) & set(stubs)), 'no production source is shadowed by a stand-in')
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    generated_stubs = {p.relative_to(output).as_posix(): sha(p) for p in paths}
    paths += [SOURCE / p for p in RECIPE_SOURCES] + [fixture]
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    own = [Path(__file__).resolve(), FIXTURE / 'recipe_static.py', fixture, GOAL19C_FIXTURE / 'Goal19CRecipeRegression.java']
    report.update({'source_sha256': hashes, 'record_sha256': records, 'fixture_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in own}, 'cache_sha256': {str(GSON): sha(GSON)},
                   'jdk_sha256': {str(p): sha(p) for p in (java, javac)}, 'generated_stubs_sha256': generated_stubs, 'adapter_sha256': adapter_hashes(),
                   'service_boundaries': ['Item/Block registry, tags and data components are stand-ins whose ids derive from the field names; each used id is checked against the production registrations',
                                          'The real Gson jar and the production loader base and AssemblyMachineRecipes are used; the frozen base is the Goal20B-start source compiled as goal20b.base',
                                          'The gas centrifuge table, crafting, language, asset and generated-file evidence is static (source text, JSON and bytes), not a loaded recipe manager, '
                                          'resource reload, JEI or a crafting run']})
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), FQN, output, expected_assembly]]
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
    catalog_path = output / 'goal20b-assembly-catalog.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    ck({m: (e['baseRows'], e['liveRows']) for m, e in catalog.items()} == EXPECTED_ROWS, 'the assembly table grows 48 -> 49 (528 off) and 44 -> 45 (528 on): '
       + str({m: (e['baseRows'], e['liveRows']) for m, e in catalog.items()}))
    goal19c = json.loads(GOAL19C_EXPORT.read_text(encoding='utf-8'))
    for mode, entry in catalog.items():
        ck(goal19c['modes'][mode]['live_rows'] == EXPECTED_ROWS[mode][0], f'{mode}: the frozen Goal20B-start table has the Goal19C live row count {goal19c["modes"][mode]["live_rows"]} (no row since)')
        ck(entry['liveRowsSerialized']['ass.cirnox'] == goal19c['recipes'][mode], f'{mode}: ass.cirnox serialises exactly as migration/goal19c-assembly-recipes.json records')
        order = entry['liveOrder']
        ck(order[order.index('ass.centrifuge') + 1] == 'ass.gascent' and entry['index'] == order.index('ass.gascent'), f'{mode}: ass.gascent sits right after ass.centrifuge (index {entry["index"]})')
    export = {'batch': 'Goal20B', 'status': 'partial-unverified', 'source': catalog_path.relative_to(ROOT).as_posix(), 'source_sha256': sha(catalog_path),
              'report': (output / 'report.json').relative_to(ROOT).as_posix(),
              'original': f'Hbm-s-Nuclear-Tech-GIT {original_head[:7]} {assembly["source"]} (normal branch; the expensive inputItemsEx branch and the 528 pool are not migrated: NEO has no item_expensive)',
              'target': f'src/main/java/{ASSEMBLY}:{rs.line_of(live[ASSEMBLY].replace(chr(13), ""), chr(34) + "ass.gascent" + chr(34))} (inserted right after ass.centrifuge)',
              'modes': {m: {'base_rows': e['baseRows'], 'live_rows': e['liveRows'], 'index': e['index']} for m, e in catalog.items()},
              'notes': ['Registered in both ENABLE_528 modes; "recipes" holds the exported row per mode, and the two are identical.',
                        'Input entries are [kind, id, count, meta]; meta 32767 is MetaHelper.WILDCARD_VALUE. Ids are the recipe stand-in ids derived from the field names; every one equals its production id.',
                        'The original 528 blueprint pool (setPools528 POOL_PREFIX_528 + "gascent") is not migrated: with enable528 on, NEO needs no blueprint for this row.',
                        'A custom config/hbmRecipes/hbmAssembler.json does not gain the row; regenerate the template or add it by hand.'],
              'recipes': {m: e['newRow'] for m, e in catalog.items()}}
    export_path = output / 'goal20b-assembly-recipes.json'
    export_path.write_text(json.dumps(export, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report['catalog'] = export['modes']
    report['catalog_new_row'] = export['recipes']['528=false']
    report['exports'] = {n: {'path': (output / n).relative_to(ROOT).as_posix(), 'sha256': sha(output / n)} for n in ('goal20b-assembly-catalog.json', 'goal20b-assembly-recipes.json', 'original-ass-gascent.json')}
    report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
    write_report(output, report)
    if not report['source_stable_after_run']: raise SystemExit('Production changed during check')

    # ---- (b) generated files (read now; runData owns them) ----
    missing = [rel for rel in rs.GENERATED.values() if not (GEN / rel).is_file()]
    live_lang = rs.provider_lang(live[LANG])
    generated = None
    if not missing:
        generated = rs.check_generated(GEN, live_lang, frozen_en_count, ck)
        report['generated_files_sha256'] = {(GEN / rel).relative_to(ROOT).as_posix(): sha(GEN / rel) for rel in rs.GENERATED.values()}
    report['generated_missing'] = missing

    # ---- mutations ----
    report['mutations'] = []
    if args.mutations:
        text = live[ASSEMBLY].replace('\r\n', '\n')
        for label, (old, new, fragment) in assembly_mutations(text).items():
            if text.count(old) != 1: raise SystemExit('Mutation anchor missing or not unique: ' + label)
            directory = output / 'mutations' / label
            mutated_run(label, directory, text.replace(old, new, 1), classes, GSON, java, javac, [directory, expected_assembly], fragment, report['mutations'])
            write_report(output, report)

        def replaced(source, old, new, label):
            source = source.replace('\r\n', '\n')
            if source.count(old) != 1: raise SystemExit('Mutation anchor missing or not unique: ' + label)
            return source.replace(old, new, 1)

        def expect_failure(label, fragment, kind, function):
            try: function()
            except AssertionError as error:
                if fragment not in str(error): raise SystemExit(f'Mutation {label} failed with the wrong assertion: {error}')
                report['mutations'].append({'label': label, 'expected_fragment': fragment, 'detected': True, 'kind': 'static ' + kind, 'message': str(error)})
                print(f'mutation {label}: detected (static; expects "{fragment}")', flush=True)
            else: raise SystemExit('Static mutation not detected: ' + label)
        q = rs.quiet
        gas = live[GASCENT]
        expect_failure('pseudo_meuf6_consumes_250', 'pseudo fluid MEUF6 consumes 200', 'pseudo-fluid table on a GasCentrifugeRecipes source copy',
                       lambda: rs.check_gascent_table(rs.parse_neo_gascent_table(replaced(gas, 'new PseudoFluidType("MEUF6", 200, 100, HEUF6, false);',
                                                                                          'new PseudoFluidType("MEUF6", 250, 100, HEUF6, false);', 'meuf6')), table_original, q))
        expect_failure('summary_row_u238_11_to_10', 'summary row 1 equals the original :98', 'summary rows on a GasCentrifugeRecipes source copy',
                       lambda: rs.check_gascent_table(rs.parse_neo_gascent_table(replaced(gas, 'new ItemStack(NtmItems.NUGGET_U238.get(), 11)', 'new ItemStack(NtmItems.NUGGET_U238.get(), 10)',
                                                                                          'summary')), table_original, q))
        expect_failure('zh_key_removed', 'zh_cn.json adds exactly the fifteen keys', 'language on a zh_cn.json copy',
                       lambda: rs.check_language(live[LANG], frozen[LANG], {k: v for k, v in zh.items() if k != 'hbmpseudofluid.pf6'}, frozen_zh, mapping, frozen_mapping, lang_original, q))
        expect_failure('mapping_kind_local', 'mapping block.hbmsntm.machine_gas_centrifuge has kind upstream', 'language on a zh_cn-map.json copy',
                       lambda: rs.check_language(live[LANG], frozen[LANG], zh, frozen_zh, {**mapping, 'block.hbmsntm.machine_gas_centrifuge': {**mapping['block.hbmsntm.machine_gas_centrifuge'], 'kind': 'local'}},
                                                 frozen_mapping, lang_original, q))
        expect_failure('provider_english_changed', 'item.hbmsntm.upgrade_gc_speed: English and Chinese equal the original', 'language on a NtmLanguageProvider copy',
                       lambda: rs.check_language(replaced(live[LANG], '"Gas Centrifuge Overclocking Upgrade"', '"Gas Centrifuge Overclock Upgrade"', 'lang'), frozen[LANG], zh, frozen_zh, mapping,
                                                 frozen_mapping, lang_original, q))
        gui = 'textures/gui/processing/gui_centrifuge_gas.png'
        corrupted = bytearray(contents[gui]); corrupted[-20] ^= 0xFF
        expect_failure('asset_gui_corrupted', f'asset {gui} is byte-identical', 'assets on a corrupted in-memory copy',
                       lambda: rs.check_assets(ASSETS, original_root / 'src/main/resources/assets/hbm', {**contents, gui: bytes(corrupted)}, q))
        provider = live[PROVIDER]
        expect_failure('rod_billet_count_3_provider', 'provider rod_zirnox_uranium_fuel requires two BILLET_URANIUM_FUEL', 'crafting on a provider-source copy',
                       lambda: rs.check_provider_crafting(replaced(provider, '.requires(NtmItems.BILLET_URANIUM_FUEL.get(), 2)', '.requires(NtmItems.BILLET_URANIUM_FUEL.get(), 3)', 'billet'),
                                                          neo_order, crafting_original, q))
        expect_failure('rod_meta_u233_provider', 'provider rod_zirnox_u235_fuel makes rod type U235_FUEL', 'crafting on a provider-source copy',
                       lambda: rs.check_provider_crafting(replaced(provider, 'ZirnoxType.U235_FUEL.ordinal()', 'ZirnoxType.U233_FUEL.ordinal()', 'meta'), neo_order, crafting_original, q))
        expect_failure('upgrade_pattern_ggg_provider', 'provider upgrade_gc_speed pattern GNG/RUR/GMG', 'crafting on a provider-source copy',
                       lambda: rs.check_provider_crafting(replaced(provider, '.pattern("GNG")', '.pattern("GGG")', 'pattern'), neo_order, crafting_original, q))
        if generated is not None:
            def mutate(source_json, edit):
                copy = json.loads(json.dumps(source_json)); edit(copy); return copy
            expect_failure('rod_billet_count_3_generated', 'rod_zirnox_uranium_fuel.json ingredients are exactly rod_zirnox_empty and two', 'generated recipe on a parsed copy',
                           lambda: rs.check_generated(GEN, live_lang, frozen_en_count, q, {'rod_uranium': mutate(generated['rod_uranium'], lambda d: d['ingredients'].append({'item': 'hbmsntm:billet_uranium_fuel'}))}))
            expect_failure('rod_meta_generated', 'rod_zirnox_u235_fuel.json result is 1 rod_zirnox with hbmsntm:meta 7', 'generated recipe on a parsed copy',
                           lambda: rs.check_generated(GEN, live_lang, frozen_en_count, q, {'rod_u235': mutate(generated['rod_u235'], lambda d: d['result'].__setitem__('components', {'hbmsntm:meta': 6}))}))
            expect_failure('en_us_key_missing', 'en_us.json has hbmpseudofluid.nuf6', 'generated language on a parsed copy',
                           lambda: rs.check_generated(GEN, live_lang, frozen_en_count, q, {'en_us': {k: v for k, v in generated['en_us'].items() if k != 'hbmpseudofluid.nuf6'}}))
        write_report(output, report)
    report['mutations_detected'] = f'{sum(1 for m in report["mutations"] if m.get("detected"))}/{len(report["mutations"])}'
    report['mutations_total'] = len(report['mutations'])
    report['python_assertions'] = len(checks); report['python_assertion_labels'] = checks
    report['source_sha256_after_run'] = {p: sha(SOURCE / p) for p in hashes}
    report['source_stable_after_run'] = hashes == report['source_sha256_after_run']
    report['original_unchanged'] = {p: sha(original_root / p) == report['original_expectation']['original_file_sha256'][p] for p in original_files}
    total = fixture_counts['assertions'] + len(checks)
    report['checks'] = {'total': total, 'assembly_fixture': fixture_counts['assertions'], 'static': len(checks), 'scenarios': fixture_counts['scenarios']}
    write_report(output, report)
    if not report['source_stable_after_run'] or not all(report['original_unchanged'].values()): raise SystemExit('Production or original source changed during check')
    print(f"Goal20B recipes: {total} assertions ({fixture_counts['assertions']} assembly fixture + {len(checks)} static); {fixture_counts['scenarios']} independent scenarios; 0 executed ticks")
    print(f"Compiled and static mutations detected: {report['mutations_detected']}")
    print(f'report: {output / "report.json"}')
    if missing:
        raise SystemExit('FAILED ONLY ON GENERATED FILES: every other check passed, but runData has not published ' + ', '.join('src/generated/resources/' + m for m in missing)
                         + '; rerun after runData (the generated checks and their mutations did not run)')

if __name__ == '__main__': main()
