"""Goal18A isolated production recipe contract, sync, JEI bridge and assembly row; existing JDK/Gson, no Gradle or game."""
from pathlib import Path
import json, re, subprocess, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, FIXTURE, sha, jdk, gson, classpath, adapter_hashes, run_dir, run, write_report
from goal18a_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES

ASSEMBLY = 'com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
BASELINE_COMMIT = '83b25ff63ae039489096d97cf39205a0010c634d'  # Goal18 planning commit: the last tree without Goal18A
CONTEXT = ('com/hbm/items/NtmItems.java', 'com/hbm/items/CastPlateItem.java', 'com/hbm/blocks/NtmBlocks.java', 'com/hbm/inventory/RecipesCommon.java',
           'com/hbm/inventory/MetaHelper.java', 'com/hbm/inventory/fluid/Fluids.java', 'com/hbm/config/NtmConfig.java', 'com/hbm/handler/jei/NtmJeiPlugin.java')
MUTATIONS = {
    'duplicate_key_accepted': ('            if(old.key().equals(row.key())) throw invalid("duplicate input/acid key " + row.key());\n', '            if(false) throw invalid("duplicate input/acid key " + row.key());\n'),
    'acid_bound_dropped': ('if(fluid.fill < 1 || fluid.fill > MAX_ACID) throw invalid("acid amount must be 1.." + MAX_ACID);', 'if(fluid.fill < 1) throw invalid("acid amount must be 1.." + MAX_ACID);'),
    'acid_type_ignored': ('if(stack == null || stack.isEmpty() || type == null || type != fluid.type) return false;', 'if(stack == null || stack.isEmpty() || type == null) return false;'),
    'omitted_meta_zero': ('int meta = values.size() > 3 ? integer(values.get(3)) : MetaHelper.WILDCARD_VALUE;', 'int meta = values.size() > 3 ? integer(values.get(3)) : 0;'),
}

def main():
    output = run_dir('recipes')
    java, javac = jdk(); GSON = gson()
    fixture = FIXTURE / 'Goal18ARecipeRegression.java'
    baseline = subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(), 'show', BASELINE_COMMIT + ':src/main/java/' + ASSEMBLY], cwd=ROOT).decode('utf-8').replace('\r\n', '\n')
    assert baseline.count('package com.hbm.inventory.recipes;') == 1
    baseline = baseline.replace('package com.hbm.inventory.recipes;', 'package goal18a.base;\nimport com.hbm.inventory.recipes.*;', 1)
    stubs = recipe_stubs(SOURCE, [fixture.read_text(encoding='utf-8'), baseline])
    stubs['goal18a/base/AssemblyMachineRecipes.java'] = baseline
    if set(RECIPE_SOURCES) & set(stubs): raise SystemExit('Production shadowed by a stand-in')
    hashes = {p: sha(SOURCE / p) for p in dict.fromkeys((*RECIPE_SOURCES, *CONTEXT))}
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    paths += [SOURCE / p for p in RECIPE_SOURCES] + [fixture]
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    report = {'evidence': 'Production CrystallizerRecipes/sync/client sync/packet/JEI handler and AssemblyMachineRecipes over registry, component, Gson and JEI-manager services; the frozen baseline is the Goal18 planning commit; not game, config-directory or JEI acceptance',
              'baseline_commit': BASELINE_COMMIT, 'source_sha256': hashes, 'fixture_sha256': {str(fixture.relative_to(ROOT)): sha(fixture)},
              'cache_sha256': {str(GSON): sha(GSON)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
              'generated_stubs_sha256': {p.relative_to(output).as_posix(): sha(p) for p in paths if p.is_relative_to(output)}, 'commands': [],
              'service_boundaries': ['Item/Block registry, tags, data components and SNBT are stand-ins; the real Gson jar and the production loader base are used',
                                     'JEI runtime manager is a counting stand-in bridged through the production refreshCrystallizerRecipes body',
                                     'Network transport is a byte-array buffer stand-in; login/datapack events are not simulated']}
    report['adapter_sha256'] = adapter_hashes()
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), 'com.hbm.inventory.recipes.Goal18ARecipeRegression', output]]
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
    # Compiled behavior mutations of the production contract: each must compile, then fail a behavioral assertion.
    rel = 'com/hbm/inventory/recipes/CrystallizerRecipes.java'; text = (SOURCE / rel).read_text(encoding='utf-8')
    report['mutations'] = []
    for label, (old, new) in MUTATIONS.items():
        if text.count(old) != 1: raise SystemExit('Mutation anchor missing: ' + label)
        directory = output / 'mutations' / label; target = directory / rel; target.parent.mkdir(parents=True)
        target.write_text(text.replace(old, new, 1), encoding='utf-8')
        compiled = directory / 'classes'; compiled.mkdir()
        record = {'label': label, 'expected_behavior_failure': True, 'generated_files_sha256': {target.relative_to(ROOT).as_posix(): sha(target)}, 'commands': []}
        report['mutations'].append(record)
        for index, command in enumerate([[javac, '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, target],
                                         [java, '-ea', '-cp', classpath(compiled, classes, GSON), 'com.hbm.inventory.recipes.Goal18ARecipeRegression', directory]]):
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
    for name in ('goal18a-assembly-recipes.json', 'goal18a-crystallizer-recipes.json'):
        report.setdefault('exports', {})[name] = {'path': str((output / name).relative_to(ROOT)), 'sha256': sha(output / name)}
    write_report(output, report)
    print(f'Compiled recipe contract mutations detected: {len(MUTATIONS)}/{len(MUTATIONS)}')
    print(output / 'report.json')

if __name__ == '__main__': main()
