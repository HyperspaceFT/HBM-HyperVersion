"""Replay affected 14A/14B/G11D and saved-state/lifecycle checks without editing old fixtures.

Adapters only acknowledge the exact new assembly row, handler names and two
compressor fluid-writer calls. New behavior is tested by verify_goal14c.py.
All outputs and copied/adapted fixture text remain in this Goal's unique run.
"""
from pathlib import Path
import contextlib
import hashlib
import json
import subprocess
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).parent
OUT = ROOT / 'build/migration/goal14c/affected'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(name, replacements, run):
    source = TOOLS / (name + '.py')
    text = source.read_text(encoding='utf-8')
    for before, after in replacements:
        assert text.count(before) == 1, (name, before)
        text = text.replace(before, after, 1)
    (run / (name + '-adapted.py')).write_text(text, encoding='utf-8')
    module = types.ModuleType('goal14c_affected_' + name)
    module.__file__ = str(source)
    exec(compile(text, str(source), 'exec'), module.__dict__)
    return module

def add_handler_services(factory, names):
    def wrapped(*args, **kwargs):
        services = factory(*args, **kwargs)
        for name in names:
            path = f'com/hbm/inventory/recipes/{name}.java'
            assert path not in services, path
            services[path] = (
                'package com.hbm.inventory.recipes;import com.hbm.inventory.recipes.loader.*;'
                'import com.google.gson.*;import com.google.gson.stream.*;'
                f'public class {name} extends SerializableRecipe{{'
                f'public String getFileName(){{return "{name}.json";}}'
                'public Object getRecipeObject(){return java.util.List.of();}'
                'public void readRecipe(JsonElement e){}public void writeRecipe(Object o,JsonWriter w){}'
                'public void registerDefaults(){}public void deleteRecipes(){}}')
        return services
    return wrapped

def main():
    allowed = {'verify_goal14a','verify_goal14b','verify_goal11d','verify_review_fluid_saves','verify_review_block_lifecycle'}
    selected = sys.argv[1:] or ['verify_goal14a','verify_goal14b','verify_goal11d','verify_review_fluid_saves','verify_review_block_lifecycle']
    assert set(selected) <= allowed and len(selected) == len(set(selected)), selected
    run = OUT / uuid.uuid4().hex
    run.mkdir(parents=True)
    before = {p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT/'src/main').rglob('*') if p.is_file()}
    old_tools = {p.relative_to(ROOT).as_posix(): digest(p) for p in TOOLS.rglob('*') if p.is_file() and p.suffix in ('.py','.java') and '14c' not in p.as_posix().lower()}
    print(f'Affected check transcript: {run}', flush=True)
    results = {}
    for name in selected:
        replacements = []
        boundary = run / name
        if name == 'verify_goal14a':
            old_fixture = TOOLS/'goal14a_regression/com/hbm/inventory/recipes/loader/Goal14ARecipeRegression.java'
            fixture_text = old_fixture.read_text(encoding='utf-8')
            for old,new in [
                ('live.size() == base.size() + 1', 'live.size() == base.size() + 2 && live.containsKey("ass.compressor")'),
                ('assembly delta is exactly one in mode ', 'assembly delta is exactly diesel plus compressor in mode '),
                ('oldOrder.remove("ass.dieselgen");', 'oldOrder.remove("ass.dieselgen"); oldOrder.remove("ass.compressor");'),
            ]:
                assert fixture_text.count(old) == 1, old
                fixture_text = fixture_text.replace(old,new,1)
            fixture = run/'Goal14ARecipeRegression.java'
            fixture.write_text(fixture_text,encoding='utf-8')
            replacements = [
                ("boundary = ROOT / 'build/migration/goal14a'", f'boundary = Path({str(boundary)!r})'),
                ("(boundary / 'baseline.json').read_text", "(ROOT / 'build/migration/goal14a/baseline.json').read_text"),
                ("fixture = FIXTURE / 'com/hbm/inventory/recipes/loader/Goal14ARecipeRegression.java'", f'fixture = Path({str(fixture)!r})'),
            ]
        elif name == 'verify_goal14b':
            replacements = [("BOUNDARY = ROOT / 'build/migration/goal14b'", f'BOUNDARY = Path({str(boundary)!r})')]
        elif name == 'verify_goal11d':
            replacements = [
                ('sorted([GENERIC_RECIPES, SOLDERING, ARC_WELDER, CRACKING])', "sorted([GENERIC_RECIPES, SOLDERING, ARC_WELDER, CRACKING, 'com/hbm/inventory/recipes/FractionRecipes.java', 'com/hbm/inventory/recipes/CompressorRecipes.java'])"),
                ('len(found) == 6 and sum(rel == CRACKING for rel, _ in found) == 2', "len(found) == 10 and sum(rel == CRACKING for rel, _ in found) == 2 and sum(rel == 'com/hbm/inventory/recipes/FractionRecipes.java' for rel, _ in found) == 2 and sum(rel == 'com/hbm/inventory/recipes/CompressorRecipes.java' for rel, _ in found) == 2"),
                ('CrackingRecipes (verify_goal12b.py): {found}', 'CrackingRecipes (verify_goal12b.py), FractionRecipes (verify_goal14b.py), CompressorRecipes (verify_goal14c.py): {found}'),
                ('(the cracking outputs): {found}', '(the cracking outputs), plus 2 fraction and 2 compressor calls: {found}'),
            ]
        elif name == 'verify_review_fluid_saves':
            replacements = [('ROOT / "build/migration/review-fixes/fluid"', f'Path({str(boundary)!r})')]
        elif name == 'verify_review_block_lifecycle':
            replacements = [('ROOT / "build/migration/review-fixes/blocks"', f'Path({str(boundary)!r})')]
        module = load(name,replacements,run)
        if name in ('verify_goal14a','verify_goal11d'):
            module.recipe_stubs = add_handler_services(module.recipe_stubs,('FractionRecipes','CompressorRecipes'))
        elif name == 'verify_goal14b':
            module.recipe_stubs = add_handler_services(module.recipe_stubs,('CompressorRecipes',))
        if name == 'verify_goal11d':
            module.OUTPUT = boundary/'regression'
            module.RECIPE_REFERENCE = boundary/'recipe-reference'
            module.GOAL13B_LINES += tuple(line for handler in ('FractionRecipes','CompressorRecipes') for line in (f'import com.hbm.inventory.recipes.{handler};',f'        recipeHandlers.add(new {handler}());'))
            module.git = lambda *args: subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}','-C',str(ROOT),*args])
        old_args = sys.argv
        sys.argv = [str(TOOLS/(name+'.py'))]
        rc = 0
        with (run/(name+'.log')).open('w',encoding='utf-8') as log:
            try:
                with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                    module.main()
            except SystemExit as ex:
                rc = ex.code or 0
                log.write(f'\nSystemExit: {rc}\n')
            except Exception:
                import traceback
                traceback.print_exc(file=log)
                rc = 1
            finally:
                sys.argv = old_args
        results[name] = dict(returncode=rc,log=str(run/(name+'.log')),original_script_sha256=digest(TOOLS/(name+'.py')))
        print(f'{name}: {rc}',flush=True)
    assert before == {p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT/'src/main').rglob('*') if p.is_file()}, 'Production changed during checks'
    assert all(digest(ROOT/p)==h for p,h in old_tools.items()), 'Legacy verification source changed'
    (run/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if any(r['returncode'] for r in results.values()):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
