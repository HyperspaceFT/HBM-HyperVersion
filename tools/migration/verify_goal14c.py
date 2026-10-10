"""Goal14C isolated production regressions; existing JDK/cache, no Gradle/game."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import uuid
import zipfile

from goal14c_regression.machine_stubs import machine_stubs, MACHINE_SOURCES
from goal14c_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES
from goal13a_regression.anvil_block import stripped_sources
from verify_goal13a import PRODUCTION as MACHINE_BASE, FIXTURE11A, FIXTURES11A
from goal14a_regression.stubs import NEW_SOURCES
from verify_goal10c import jdk
from verify_goal3c_recipes import GSON

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
FIXTURE = Path(__file__).with_name('goal14c_regression')
BOUNDARY = ROOT / 'build/migration/goal14c/regression'
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
    print(f'Goal14C output: {output}', flush=True)
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
        hashes = {p: hashlib.sha256((SOURCE / p).read_bytes()).hexdigest() for p in production}
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
        summary['worlds'][name] = {'production_sha256': hashes, 'stdout': result}
        (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    if args.world in ('recipe', 'all'):
        fixture = FIXTURE / 'Goal14CRecipeRegression.java'
        world('recipe', recipe_stubs(SOURCE, [fixture.read_text(encoding='utf-8')]), RECIPE_SOURCES, [fixture], 'com.hbm.inventory.recipes.loader.Goal14CRecipeRegression')
    if args.world in ('machine', 'all'):
        fixture = FIXTURE / 'Goal14CMachineRegression.java'
        with zipfile.ZipFile(NEO_SOURCES) as jar:
            tags = jar.read('net/minecraft/data/tags/VanillaBlockTagsProvider.java').decode('utf-8')
        stubs = machine_stubs(SOURCE, [fixture.read_text(encoding='utf-8')], tags, NEO_SOURCES)
        production = tuple(dict.fromkeys((*MACHINE_BASE, *NEW_SOURCES, *MACHINE_SOURCES)))
        world('machine', stubs, production, [FIXTURE11A / p for p in FIXTURES11A] + [fixture], 'com.hbm.blockentity.machine.Goal14CMachineRegression')


if __name__ == '__main__':
    main()
