"""Goal18B isolated production crystallizer defaults (four sulfuric acid groups), frozen Goal18A rows, sync, merge record and unchanged assembly table; existing JDK/Gson, no Gradle or game."""
from pathlib import Path
import json, re, subprocess, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18b_regression.common import ROOT, SOURCE, FIXTURE, sha, jdk, gson, classpath, adapter_hashes, run_dir, run, write_report
from goal18b_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES

ASSEMBLY = 'com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
CRYSTALLIZER = 'com/hbm/inventory/recipes/CrystallizerRecipes.java'
BASELINE_COMMIT = 'ce94c2aa837ba98cbc19b8574dab486d538afa82'  # Goal18A static-review commit: the last tree without Goal18B
FROZEN_18A = ROOT / 'migration/goal18a-crystallizer-recipes.json'
MERGE_EXAMPLE = ROOT / 'migration/goal18b-custom-crystallizer-merge-example.json'
EXPORT = 'goal18b-crystallizer-recipes.json'
FQN = 'com.hbm.inventory.recipes.Goal18BRecipeRegression'
CONTEXT = ('com/hbm/items/NtmItems.java', 'com/hbm/items/CastPlateItem.java', 'com/hbm/blocks/NtmBlocks.java', 'com/hbm/inventory/RecipesCommon.java',
           'com/hbm/inventory/MetaHelper.java', 'com/hbm/inventory/fluid/Fluids.java', 'com/hbm/config/NtmConfig.java', 'com/hbm/handler/jei/NtmJeiPlugin.java')
# The stand-in registry derives ids from the field names; the production registrations must use exactly those ids.
REGISTRY_IDS = {'com/hbm/blocks/NtmBlocks.java': ('ORE_TITANIUM', 'ORE_TITANIUM_DEEPSLATE', 'ORE_TUNGSTEN', 'ORE_TUNGSTEN_DEEPSLATE', 'ORE_COBALT', 'ORE_COBALT_DEEPSLATE', 'ORE_RARE', 'ORE_RARE_DEEPSLATE'),
                'com/hbm/items/NtmItems.java': ('CRYSTAL_TITANIUM', 'CRYSTAL_TUNGSTEN', 'CRYSTAL_COBALT', 'CRYSTAL_RARE', 'RARE_EARTH_ORE_CHUNK', 'FRAGMENT_COBALT')}
SULFURIC_CALLS = ('        ore(NtmBlocks.ORE_TITANIUM.get(), NtmBlocks.ORE_TITANIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_TITANIUM.get(), Fluids.SULFURIC_ACID);\n'
                  '        ore(NtmBlocks.ORE_TUNGSTEN.get(), NtmBlocks.ORE_TUNGSTEN_DEEPSLATE.get(), NtmItems.CRYSTAL_TUNGSTEN.get(), Fluids.SULFURIC_ACID);\n'
                  '        ore(NtmBlocks.ORE_COBALT.get(), NtmBlocks.ORE_COBALT_DEEPSLATE.get(), NtmItems.CRYSTAL_COBALT.get(), Fluids.SULFURIC_ACID);\n'
                  '        ore(NtmBlocks.ORE_RARE.get(), NtmBlocks.ORE_RARE_DEEPSLATE.get(), NtmItems.CRYSTAL_RARE.get(), Fluids.SULFURIC_ACID);\n')
MUTATIONS = {
    'sulfuric_groups_dropped': (SULFURIC_CALLS, ''),
    'sulfuric_acid_replaced_by_peroxide': (SULFURIC_CALLS, SULFURIC_CALLS.replace('Fluids.SULFURIC_ACID', 'Fluids.PEROXIDE')),
    'sulfuric_amount_halved': ('        FluidStack fluid = new FluidStack(acid, DEFAULT_ACID);\n', '        FluidStack fluid = new FluidStack(acid, acid == Fluids.SULFURIC_ACID ? 250 : DEFAULT_ACID);\n'),
}

def registry_ids():
    found = {}
    for rel, fields in REGISTRY_IDS.items():
        text = (SOURCE / rel).read_text(encoding='utf-8')
        for field in fields:
            match = re.search(r'\b' + field + r'\s*=\s*(?:ITEMS\.)?register\w*\("([a-z0-9_]+)"', text)
            if not match or match.group(1) != field.lower(): raise SystemExit(f'Production id of {field} is not {field.lower()}')
            found[field] = 'hbmsntm:' + match.group(1)
    return found

def row_key(row): return json.dumps(row['input'], separators=(',', ':')) + '@' + row['fluid'][0]

def comparison(old_rows, new_rows):
    old, new = {row_key(r): r for r in old_rows}, {row_key(r): r for r in new_rows}
    if len(old) != len(old_rows) or len(new) != len(new_rows): raise SystemExit('Duplicate input/acid key in an export')
    return {'added': [r for k, r in new.items() if k not in old], 'removed': [r for k, r in old.items() if k not in new],
            'changed': [{'before': old[k], 'after': r} for k, r in new.items() if k in old and old[k] != r]}

def main():
    output = run_dir('recipes')
    java, javac = jdk(); GSON = gson()
    fixture = FIXTURE / 'Goal18BRecipeRegression.java'
    ids = registry_ids()
    baseline = subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(), 'show', BASELINE_COMMIT + ':src/main/java/' + ASSEMBLY], cwd=ROOT).decode('utf-8').replace('\r\n', '\n')
    assert baseline.count('package com.hbm.inventory.recipes;') == 1
    baseline = baseline.replace('package com.hbm.inventory.recipes;', 'package goal18b.base;\nimport com.hbm.inventory.recipes.*;', 1)
    stubs = recipe_stubs(SOURCE, [fixture.read_text(encoding='utf-8'), baseline])
    stubs['goal18b/base/AssemblyMachineRecipes.java'] = baseline
    if set(RECIPE_SOURCES) & set(stubs): raise SystemExit('Production shadowed by a stand-in')
    hashes = {p: sha(SOURCE / p) for p in dict.fromkeys((*RECIPE_SOURCES, *CONTEXT))}
    records = {str(p.relative_to(ROOT)): sha(p) for p in (FROZEN_18A, MERGE_EXAMPLE)}
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    paths += [SOURCE / p for p in RECIPE_SOURCES] + [fixture]
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    report = {'evidence': 'Production CrystallizerRecipes (Goal18B defaults)/sync/client sync/packet/JEI handler and AssemblyMachineRecipes over registry, component, Gson and JEI-manager services; the frozen Goal18A rows are the committed Goal18A export and the assembly baseline is the Goal18A commit; not game, config-directory or JEI acceptance',
              'baseline_commit': BASELINE_COMMIT, 'source_sha256': hashes, 'record_sha256': records, 'fixture_sha256': {str(fixture.relative_to(ROOT)): sha(fixture)},
              'cache_sha256': {str(GSON): sha(GSON)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)}, 'registry_ids': ids,
              'generated_stubs_sha256': {p.relative_to(output).as_posix(): sha(p) for p in paths if p.is_relative_to(output)}, 'commands': [],
              'service_boundaries': ['Item/Block registry, tags, data components and SNBT are stand-ins (ids derived from the field names, checked against the production registrations); the real Gson jar and the production loader base are used',
                                     'JEI runtime manager is the Goal18A counting stand-in (goal18a.JeiBridge) bridged through the production refreshCrystallizerRecipes body',
                                     'Network transport is a byte-array buffer stand-in; login/datapack events are not simulated']}
    report['adapter_sha256'] = adapter_hashes()
    arguments = lambda directory: [directory, FROZEN_18A, MERGE_EXAMPLE]
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), FQN, *arguments(output)]]
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
    # Row-level comparison against the frozen Goal18A export, keyed on input identity plus acid type.
    old_rows = json.loads(FROZEN_18A.read_text(encoding='utf-8'))['recipes']
    new_rows = json.loads((output / EXPORT).read_text(encoding='utf-8'))['recipes']
    report['comparison'] = comparison(old_rows, new_rows)
    added = report['comparison']['added']
    if len(old_rows) != 28 or len(new_rows) != 36 or new_rows[:28] != old_rows or added != new_rows[28:] or len(added) != 8 or report['comparison']['removed'] or report['comparison']['changed']:
        raise SystemExit('Goal18B export is not the Goal18A table plus eight appended rows')
    if any(r['fluid'] != ['SULFURIC_ACID', 500] or r['duration'] != 600 or r['productivity'] != 0.05 for r in added): raise SystemExit('Appended rows are not 500 mB sulfuric acid, 600 ticks, 0.05')
    merge = json.loads(MERGE_EXAMPLE.read_text(encoding='utf-8'))
    if list(merge) != ['comment', 'recipes'] or merge['recipes'] != [new_rows[i] for i in (0, 3, *range(28, 36))]: raise SystemExit('Merge record rows are not the exported rows 0, 3 and 28..35')
    report['merge_example'] = {'path': str(MERGE_EXAMPLE.relative_to(ROOT)), 'rows_from_export': [0, 3, *range(28, 36)]}
    write_report(output, report)
    # Compiled behavior mutations of the production defaults: each must compile, then fail a behavioral assertion.
    text = (SOURCE / CRYSTALLIZER).read_text(encoding='utf-8')
    report['mutations'] = []
    for label, (old, new) in MUTATIONS.items():
        if text.count(old) != 1: raise SystemExit('Mutation anchor missing: ' + label)
        directory = output / 'mutations' / label; target = directory / CRYSTALLIZER; target.parent.mkdir(parents=True)
        target.write_text(text.replace(old, new, 1), encoding='utf-8')
        compiled = directory / 'classes'; compiled.mkdir()
        record = {'label': label, 'expected_behavior_failure': True, 'generated_files_sha256': {target.relative_to(ROOT).as_posix(): sha(target)}, 'commands': []}
        report['mutations'].append(record)
        for index, command in enumerate([[javac, '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, target],
                                         [java, '-ea', '-cp', classpath(compiled, classes, GSON), FQN, *arguments(directory)]]):
            code, out = run(command)
            (directory / ('compile.log', 'run.log')[index]).write_text(out, encoding='utf-8')
            record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
            report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
            write_report(output, report)
            if not report['source_stable_after_run']: raise SystemExit('Source changed during mutation')
            if index == 0 and code: raise SystemExit('Mutation compile failure is not detection: ' + out)
            if index == 1 and (code == 0 or 'java.lang.AssertionError' not in out): raise SystemExit('Mutation not detected by behavioral assertion: ' + label + '\n' + out)
        record['compiled_successfully'] = True; record['behavior_mutation_detected'] = True
    report['mutations_detected'] = len(MUTATIONS)
    report['exports'] = {EXPORT: {'path': str((output / EXPORT).relative_to(ROOT)), 'sha256': sha(output / EXPORT)}}
    write_report(output, report)
    print(f'Compiled recipe contract mutations detected: {len(MUTATIONS)}/{len(MUTATIONS)}')
    print(output / 'report.json')

if __name__ == '__main__': main()
