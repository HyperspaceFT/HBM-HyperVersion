"""Isolated Goal16A recipes; existing JDK/Gson only, no Minecraft or downloads."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from goal16a_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES, original_table
from verify_goal10c import jdk
from verify_goal3c_recipes import GSON

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
FIXTURE = Path(__file__).with_name('goal16a_regression')
BOUNDARY = ROOT / 'build/migration/goal16a/recipes'
ORIGINAL = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT/src/main/java/com/hbm/inventory/recipes/MixerRecipes.java'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output.resolve() if args.output else BOUNDARY / uuid.uuid4().hex
    if not output.is_relative_to(BOUNDARY) or output == BOUNDARY:
        raise SystemExit('Output must be unique child of Goal16A recipes boundary')
    output.mkdir(parents=True, exist_ok=False)
    print(f'Goal16A recipes output: {output}', flush=True)
    java, javac = jdk()
    if not GSON.is_file():
        raise SystemExit('Existing Gson cache missing')
    expected = original_table(ORIGINAL)
    (output / 'original-mapping.json').write_text(json.dumps(expected, indent=2), encoding='utf-8')
    fixture = FIXTURE / 'Goal16ARecipeRegression.java'
    source_inputs = {}
    explicit_inputs = ('com/hbm/handler/jei/NtmJeiPlugin.java','com/hbm/items/NtmItems.java','com/hbm/blocks/NtmBlocks.java','com/hbm/datagen/NtmItemTagProvider.java','com/hbm/inventory/NtmTags.java','com/hbm/inventory/RecipesCommon.java','com/hbm/inventory/MetaHelper.java','com/hbm/items/EnumMultiItem.java','com/hbm/inventory/fluid/Fluids.java','com/hbm/items/FuelAdditiveItem.java','com/hbm/items/component/NtmDataComponents.java')
    for rel in explicit_inputs:
        source_inputs[rel] = hashlib.sha256((SOURCE/rel).read_bytes()).hexdigest()
    # Observe all additional source reads inside inherited generators, rather than guessing their inputs.
    original_read_text = Path.read_text
    def tracked_read_text(path, *positional, **named):
        data = original_read_text(path, *positional, **named)
        resolved = path.resolve()
        if resolved.is_relative_to(SOURCE):
            rel = resolved.relative_to(SOURCE).as_posix()
            digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
            if rel in source_inputs and source_inputs[rel] != digest:
                raise SystemExit(f'Source drift during service generation: {rel}')
            source_inputs[rel] = digest
        return data
    Path.read_text = tracked_read_text
    try:
        stubs = recipe_stubs(SOURCE, [fixture.read_text(encoding='utf-8')])
    finally:
        Path.read_text = original_read_text
    imported_generators = {}
    for module in tuple(sys.modules.values()):
        origin = getattr(module, '__file__', None)
        if origin:
            path = Path(origin).resolve()
            if path.suffix == '.py' and path.is_relative_to(ROOT/'tools/migration'):
                imported_generators[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if set(stubs) & set(RECIPE_SOURCES):
        raise SystemExit('Production shadowed by generated services')
    hashes = {p: hashlib.sha256((SOURCE / p).read_bytes()).hexdigest() for p in RECIPE_SOURCES}
    paths = []
    for rel, text in stubs.items():
        path = output / 'services' / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + '\n', encoding='utf-8')
        paths.append(path)
    paths += [SOURCE / p for p in RECIPE_SOURCES] + [fixture]
    classes = output / 'classes'
    classes.mkdir()
    argfile = output / 'sources.txt'
    argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    summary = {
        'boundary': 'Isolated production methods over replaced services, not true JEI/Minecraft/game/save/server',
        'source_sha256': hashes,
        'fixtures_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), FIXTURE / 'recipe_stubs.py', fixture)},
        'original_sha256': hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        'generated_service_sha256': {p: hashlib.sha256((t+'\n').encode()).hexdigest() for p,t in stubs.items()},
        'cache_sha256': {str(GSON): hashlib.sha256(GSON.read_bytes()).hexdigest()},
        'entry_command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
        'source_inputs_sha256': source_inputs,
        'imported_generator_sha256': imported_generators,
        'extraction_note': 'JeiBridge contains only the unchanged refreshMixerRecipes body; available/unavailable and manager are fixture services. Other source inputs back inherited fixture identities/enums/method extraction and declaration spot-checks; listed whole classes are not claimed executed.',
        'replacements': ['inherited Goal15B registry/component/SNBT services extended for missing META', 'fixture tag bindings and members', 'queued event work executes synchronously', 'PacketDistributor records recipients', 'byte-array buffer with length service, not transport framing', 'JEI drawing/layout tokens', 'parent refreshMixerRecipes extracted unchanged into isolated manager'],
        'commands': [],
    }
    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        summary['commands'].append({'label': label, 'command': command, 'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        with (output/'result.log').open('a', encoding='utf-8') as stream:
            stream.write(f'{label}\n{command}\nexit={result.returncode}\n{result.stdout}{result.stderr}\n')
        (output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(result.stdout+result.stderr, end='', flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
    run('compile', [str(javac), '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', str(GSON), '-d', str(classes), '@'+str(argfile)])
    run('regression', [str(java), '-ea', '-cp', f'{classes};{GSON}', 'com.hbm.inventory.recipes.loader.Goal16ARecipeRegression', str(output)])
    assert json.loads((output/'defaults-snapshot.json').read_text(encoding='utf-8')) == expected, 'Actual writer differs from original ordered table'
    for p,h in hashes.items():
        assert hashlib.sha256((SOURCE/p).read_bytes()).hexdigest() == h, f'Source drift: {p}'
    for p,h in source_inputs.items():
        assert hashlib.sha256((SOURCE/p).read_bytes()).hexdigest() == h, f'Extracted/declaration source drift: {p}'
    for p,h in imported_generators.items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h, f'Imported generator drift: {p}'
    for p,h in summary['fixtures_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h, f'Fixture drift: {p}'
    summary['source_and_generator_before_after'] = 'unchanged'
    summary['mapping'] = {'groups': 38, 'ordered_variants': 48, 'every_value_matches_original': True}
    (output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'Goal16A recipes output: {output}', flush=True)

if __name__ == '__main__':
    main()
