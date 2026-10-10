"""Goal14B production-source isolated regressions; no game, Gradle or downloads."""
from pathlib import Path
import argparse
import json
import subprocess
import uuid
import zipfile

from goal14b_regression.machine_stubs import machine_stubs, MACHINE_SOURCES
from goal14b_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES
from goal13a_regression.anvil_block import stripped_sources
from verify_goal13a import PRODUCTION as MACHINE_BASE, FIXTURE11A, FIXTURES11A
from goal14a_regression.stubs import NEW_SOURCES
from verify_goal10c import jdk
from verify_goal3c_recipes import GSON

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
FIXTURE = Path(__file__).with_name('goal14b_regression')
BOUNDARY = ROOT / 'build/migration/goal14b'
NEO_SOURCES = ROOT / 'build/moddev/artifacts/neoforge-21.1.228-sources.jar'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--world', choices=('machine', 'recipe', 'all'), default='all')
    args = parser.parse_args()
    source = args.source.resolve()
    if source != SOURCE and not source.is_relative_to(BOUNDARY / 'mutations'):
        raise SystemExit('Source copies must stay under goal14b/mutations')
    output = (args.output or BOUNDARY / 'regression' / uuid.uuid4().hex).resolve()
    if not any(output.is_relative_to(BOUNDARY / p) for p in ('regression', 'mutations')):
        raise SystemExit('Outputs must stay under goal14b/regression or mutations')
    output.mkdir(parents=True, exist_ok=False)
    java, javac = jdk()
    if not GSON.is_file() or not NEO_SOURCES.is_file():
        raise SystemExit('Existing Gson/NeoForge sources cache missing')
    log = output / 'result.log'
    print(f'Goal14B output: {output}', flush=True)
    summary = {}

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
        paths = []
        for rel, content in stubs.items():
            path = directory / 'stubs' / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content + '\n', encoding='utf-8')
            paths.append(path)
        paths += stripped_sources([source / p for p in production], directory) if name == 'machine' else [source / p for p in production]
        paths += fixtures
        argfile = directory / 'sources.txt'
        argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
        classes = directory / 'classes'
        classes.mkdir()
        with log.open('a', encoding='utf-8') as stream:
            stream.write(name + ' real production sources:\n' + '\n'.join(production) + '\n')
        run('Compile ' + name, [str(javac), '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', str(GSON), '-d', str(classes), '@' + str(argfile)])
        result = run('Run ' + name, [str(java), '-Duser.language=en', '-ea', '-cp', f'{classes};{GSON}', main_class, str(directory)])
        summary[name] = {'production': list(production), 'stdout': result}

    if args.world in ('recipe', 'all'):
        fixture = FIXTURE / 'Goal14BRecipeRegression.java'
        world('recipe', recipe_stubs(source, [fixture.read_text(encoding='utf-8')]), RECIPE_SOURCES, [fixture], 'com.hbm.inventory.recipes.loader.Goal14BRecipeRegression')
    if args.world in ('machine', 'all'):
        fixture = FIXTURE / 'Goal14BMachineRegression.java'
        with zipfile.ZipFile(NEO_SOURCES) as jar:
            tags = jar.read('net/minecraft/data/tags/VanillaBlockTagsProvider.java').decode('utf-8')
        stubs = machine_stubs(source, [fixture.read_text(encoding='utf-8')], tags, NEO_SOURCES)
        production = tuple(dict.fromkeys((*MACHINE_BASE, *NEW_SOURCES, *MACHINE_SOURCES)))
        world('machine', stubs, production, [FIXTURE11A / p for p in FIXTURES11A] + [fixture], 'com.hbm.blockentity.machine.Goal14BMachineRegression')
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
