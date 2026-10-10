"""Goal15A isolated production regressions; existing JDK/cache, no Gradle/game."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import uuid
import zipfile

from goal15a_regression.machine_stubs import machine_stubs, MACHINE_SOURCES
from goal15a_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES
from goal13a_regression.anvil_block import stripped_sources
from verify_goal13a import PRODUCTION as MACHINE_BASE, FIXTURE11A, FIXTURES11A
from goal14a_regression.stubs import NEW_SOURCES
from verify_goal10c import jdk
from verify_goal3c_recipes import GSON

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
FIXTURE = Path(__file__).with_name('goal15a_regression')
BOUNDARY = ROOT / 'build/migration/goal15a/regression'
NEO_SOURCES = ROOT / 'build/moddev/artifacts/neoforge-21.1.228-sources.jar'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world', choices=('machine', 'recipe', 'all'), default='all')
    args = parser.parse_args()
    output = BOUNDARY / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    java, javac = jdk()
    if not GSON.is_file() or not NEO_SOURCES.is_file():
        raise SystemExit('Existing Gson/NeoForge sources cache missing')
    log = output / 'result.log'
    print(f'Goal15A output: {output}', flush=True)
    summary = {'boundary': 'Isolated production source, not game/save/server acceptance', 'worlds': {}}

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        with log.open('a', encoding='utf-8') as stream:
            stream.write(f'{label}\ncommand: {subprocess.list2cmdline(command)}\nreturncode: {result.returncode}\n{result.stdout}{result.stderr}\n')
        print(result.stdout + result.stderr, end='', flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
        return result.stdout

    def world(name, stubs, production, fixtures, main_class):
        overlap = set(stubs) & set(production)
        if overlap:
            raise SystemExit(f'Production shadowed: {sorted(overlap)}')
        directory = output / name
        directory.mkdir()
        extracted = ('com/hbm/items/NtmItems.java','com/hbm/items/BoltItem.java','com/hbm/items/WireDenseItem.java','com/hbm/items/machine/PistonSetItem.java','com/hbm/lib/Library.java','com/hbm/inventory/fluid/Fluids.java','com/hbm/blocks/DummyableBlock.java','com/hbm/inventory/RecipesCommon.java','com/hbm/inventory/MetaHelper.java')
        hashes = {p: hashlib.sha256((SOURCE / p).read_bytes()).hexdigest() for p in dict.fromkeys((*production,*extracted))}
        paths = []
        for rel, content in stubs.items():
            path = directory / 'stubs' / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content + '\n', encoding='utf-8')
            paths.append(path)
        paths += stripped_sources([SOURCE / p for p in production], directory) if name == 'machine' else [SOURCE / p for p in production]
        paths += fixtures
        argfile = directory / 'sources.txt'
        argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
        classes = directory / 'classes'
        classes.mkdir()
        run('Compile ' + name, [str(javac), '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', str(GSON), '-d', str(classes), '@' + str(argfile)])
        result = run('Run ' + name, [str(java), '-Duser.language=en', '-ea', '-cp', f'{classes};{GSON}', main_class, str(directory)])
        if any(hashlib.sha256((SOURCE / p).read_bytes()).hexdigest() != h for p, h in hashes.items()):
            raise SystemExit('Production source changed during check; results are not a stable snapshot')
        summary['worlds'][name] = {'production_sha256': hashes, 'fixture_sha256': {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures}, 'generated_services_sha256':{p:hashlib.sha256(t.encode()).hexdigest() for p,t in stubs.items()}, 'cache_sha256': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (GSON,NEO_SOURCES)}, 'stdout': result}
        (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    if args.world in ('recipe', 'all'):
        fixture = FIXTURE / 'Goal15ARecipeRegression.java'
        baseline = ROOT/'build/migration/goal15a/baseline-files/src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
        baseline_hash = json.loads((ROOT/'build/migration/goal15a/baseline.json').read_text(encoding='utf-8'))['files']['src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java']
        assert hashlib.sha256(baseline.read_bytes()).hexdigest()==baseline_hash, 'Goal15A frozen assembly baseline drift'
        text = baseline.read_text(encoding='utf-8').replace('package com.hbm.inventory.recipes;', 'package goal15a.base;import com.hbm.inventory.recipes.*;')
        stubs = recipe_stubs(SOURCE, [fixture.read_text(encoding='utf-8'),text])
        stubs['goal15a/base/AssemblyMachineRecipes.java'] = text
        world('recipe', stubs, RECIPE_SOURCES, [fixture], 'com.hbm.inventory.recipes.loader.Goal15ARecipeRegression')
        summary['assembly_baseline_sha256'] = baseline_hash
        provider = SOURCE/'com/hbm/datagen/NtmRecipeProvider.java'
        compact = ' '.join(provider.read_text(encoding='utf-8').split())
        import re
        statement = re.search(r'ShapedRecipeBuilder\.shaped\(RecipeCategory.MISC, NtmItems.CANISTER_EMPTY.get\(\), 2\).*?\.save\(recipeOutput, ResourceLocation.fromNamespaceAndPath\("hbmsntm", "canister_empty"\)\);',compact).group()
        for fragment in ('.pattern("S ")','.pattern("AA")',".define('S', NtmTags.Items.PLATES_STEEL)",".define('A', NtmItems.PLATE_ALUMINIUM.get())"):
            assert fragment in statement, ('empty canister source definition',fragment)
        assert statement.count('.pattern("AA")')==2
        summary['canister_static_definition']={'statement':statement,'provider_sha256':hashlib.sha256(provider.read_bytes()).hexdigest(),'boundary':'static datagen statement, parent owns generation and packaged JSON validation'}
        (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    if args.world in ('machine', 'all'):
        fixture = FIXTURE / 'Goal15AMachineRegression.java'
        with zipfile.ZipFile(NEO_SOURCES) as jar:
            tags = jar.read('net/minecraft/data/tags/VanillaBlockTagsProvider.java').decode('utf-8')
        inherited = Path(__file__).with_name('goal14c_regression')/'Goal14CMachineRegression.java'
        stubs = machine_stubs(SOURCE, [fixture.read_text(encoding='utf-8'),inherited.read_text(encoding='utf-8')], tags, NEO_SOURCES)
        production = tuple(dict.fromkeys((*MACHINE_BASE, *NEW_SOURCES, *MACHINE_SOURCES)))
        world('machine', stubs, production, [FIXTURE11A / p for p in FIXTURES11A] + [inherited,fixture], 'com.hbm.blockentity.machine.Goal15AMachineRegression')


if __name__ == '__main__':
    main()

