"""Replay affected 14A/14B/G11D and saved-state/lifecycle checks without editing old fixtures.

Adapters acknowledge four Goal15A rows and Goal15B's single coker row, production
piston/bolt/wire enum declarations, and previous 14B/14C additions. The complete
15A and G9A checks also run. New coker behavior is tested by verify_goal15b.py.
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
from goal10b_regression.stubs import ordinal_enum, meta_enum

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).parent
OUT = ROOT / 'build/migration/goal15b/affected'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(name, replacements, run):
    source = TOOLS / (name + '.py')
    text = source.read_text(encoding='utf-8')
    for before, after in replacements:
        assert text.count(before) == 1, (name, before)
        text = text.replace(before, after, 1)
    (run / (name + '-adapted.py')).write_text(text, encoding='utf-8')
    module = types.ModuleType('goal15b_affected_' + name)
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
    allowed = {'verify_goal14a','verify_goal14b','verify_goal14c','verify_goal11d','verify_review_fluid_saves','verify_review_block_lifecycle','verify_goal15a','verify_goal9a'}
    selected = sys.argv[1:] or ['verify_goal14a','verify_goal14b','verify_goal14c','verify_goal11d','verify_review_fluid_saves','verify_review_block_lifecycle','verify_goal15a','verify_goal9a']
    assert set(selected) <= allowed and len(selected) == len(set(selected)), selected
    run = OUT / uuid.uuid4().hex
    run.mkdir(parents=True)
    before = {p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT/'src/main').rglob('*') if p.is_file()}
    old_tools = {p.relative_to(ROOT).as_posix(): digest(p) for p in TOOLS.rglob('*') if p.is_file() and p.suffix in ('.py','.java') and '15b' not in p.as_posix().lower()}
    print(f'Affected check transcript: {run}', flush=True)
    results = {}
    for name in selected:
        replacements = []
        boundary = run / name
        if name == 'verify_goal14a':
            old_fixture = TOOLS/'goal14a_regression/com/hbm/inventory/recipes/loader/Goal14ARecipeRegression.java'
            fixture_text = old_fixture.read_text(encoding='utf-8')
            for old,new in [
                ('live.size() == base.size() + 1', 'live.size() == base.size() + 7 && live.keySet().containsAll(java.util.List.of("ass.compressor","ass.combustiongen","ass.pistonsetsteel","ass.pistonsetdura","ass.pistonsetdesh","ass.coker"))'),
                ('assembly delta is exactly one in mode ', 'assembly delta is exactly diesel/compressor/four Goal15A rows/one Goal15B coker in mode '),
                ('oldOrder.remove("ass.dieselgen");', 'oldOrder.remove("ass.dieselgen"); for(String n:java.util.List.of("ass.compressor","ass.combustiongen","ass.pistonsetsteel","ass.pistonsetdura","ass.pistonsetdesh","ass.coker")) oldOrder.remove(n);'),
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
        elif name == 'verify_goal14c':
            replacements = [("BOUNDARY = ROOT / 'build/migration/goal14c/regression'", f'BOUNDARY = Path({str(boundary)!r})')]
        elif name == 'verify_goal15a':
            fixture_root=run/'goal15a-fixtures'
            fixture_root.mkdir()
            for filename in ('Goal15ARecipeRegression.java','Goal15AMachineRegression.java'):
                text=(TOOLS/'goal15a_regression'/filename).read_text(encoding='utf-8')
                if filename.startswith('Goal15ARecipe'):
                    old='for(String n:newNames)retained.remove(n);'
                    assert text.count(old)==1
                    text=text.replace(old,old+'retained.remove("ass.coker");')
                    old='live.size()==baseline.size()+4'
                    assert text.count(old)==1
                    text=text.replace(old,'live.size()==baseline.size()+5&&live.containsKey("ass.coker")')
                (fixture_root/filename).write_text(text,encoding='utf-8')
            replacements=[("BOUNDARY = ROOT / 'build/migration/goal15a/regression'",f'BOUNDARY = Path({str(boundary)!r})'),("FIXTURE = Path(__file__).with_name('goal15a_regression')",f'FIXTURE = Path({str(fixture_root)!r})')]
        elif name == 'verify_goal9a':
            replacements=[('OUTPUT = ROOT / "build/migration/goal9a/regression"',f'OUTPUT = Path({str(boundary)!r})'),('["git", "-C", str(ROOT), "show",', '["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT), "show",')]
        elif name == 'verify_goal11d':
            replacements = [
                ('sorted([GENERIC_RECIPES, SOLDERING, ARC_WELDER, CRACKING])', "sorted([GENERIC_RECIPES, SOLDERING, ARC_WELDER, CRACKING, 'com/hbm/inventory/recipes/FractionRecipes.java', 'com/hbm/inventory/recipes/CompressorRecipes.java','com/hbm/inventory/recipes/CokerRecipes.java'])"),
                ('len(found) == 6 and sum(rel == CRACKING for rel, _ in found) == 2', "len(found) == 12 and sum(rel == CRACKING for rel, _ in found) == 2 and sum(rel == 'com/hbm/inventory/recipes/FractionRecipes.java' for rel, _ in found) == 2 and sum(rel == 'com/hbm/inventory/recipes/CompressorRecipes.java' for rel, _ in found) == 2 and sum(rel == 'com/hbm/inventory/recipes/CokerRecipes.java' for rel,_ in found)==2"),
                ('CrackingRecipes (verify_goal12b.py): {found}', 'CrackingRecipes (verify_goal12b.py), FractionRecipes (verify_goal14b.py), CompressorRecipes (verify_goal14c.py), CokerRecipes (verify_goal15b.py): {found}'),
                ('(the cracking outputs): {found}', '(the cracking outputs), plus 2 fraction, 2 compressor and 2 coker calls: {found}'),
            ]
        elif name == 'verify_review_fluid_saves':
            replacements = [('ROOT / "build/migration/review-fixes/fluid"', f'Path({str(boundary)!r})')]
        elif name == 'verify_review_block_lifecycle':
            replacements = [('ROOT / "build/migration/review-fixes/blocks"', f'Path({str(boundary)!r})')]
        module = load(name,replacements,run)
        if name in ('verify_goal14a','verify_goal11d'):
            module.recipe_stubs = add_handler_services(module.recipe_stubs,('FractionRecipes','CompressorRecipes','CokerRecipes'))
        elif name == 'verify_goal14b':
            module.recipe_stubs = add_handler_services(module.recipe_stubs,('CompressorRecipes','CokerRecipes'))
        elif name in ('verify_goal14c','verify_goal15a'):
            module.recipe_stubs = add_handler_services(module.recipe_stubs,('CokerRecipes',))
        if name in ('verify_goal14a','verify_goal14b','verify_goal14c','verify_goal11d'):
            def add_symbols(factory):
                def wrapped(*args,**kwargs):
                    services=factory(*args,**kwargs)
                    for relative,package,cls,constructor in (
                        ('com/hbm/items/machine/PistonSetItem.java','com.hbm.items.machine','PistonSetItem',ordinal_enum),
                        ('com/hbm/items/BoltItem.java','com.hbm.items','BoltItem',meta_enum),
                        ('com/hbm/items/WireDenseItem.java','com.hbm.items','WireDenseItem',meta_enum)):
                        services[relative]=constructor((ROOT/'src/main/java'/relative).read_text(encoding='utf-8'),package,cls,relative)
                    return services
                return wrapped
            module.recipe_stubs=add_symbols(module.recipe_stubs)
            if hasattr(module,'machine_stubs'):
                module.machine_stubs=add_symbols(module.machine_stubs)
        if name == 'verify_goal11d':
            module.OUTPUT = boundary/'regression'
            module.RECIPE_REFERENCE = boundary/'recipe-reference'
            module.GOAL13B_LINES += tuple(line for handler in ('FractionRecipes','CompressorRecipes','CokerRecipes') for line in (f'import com.hbm.inventory.recipes.{handler};',f'        recipeHandlers.add(new {handler}());'))
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
    report={'evidence':'unchanged old assertions; copied adapters; isolated production behavior only',
            'results':results,'source_hashes':{p.removeprefix('src/main/java/'):h for p,h in before.items() if p.startswith('src/main/java/')},
            'fixture_sha256':old_tools,'productionUnchanged':True,'legacyToolsUnchanged':True,
            'adapterNotes':'Goal14A new-row delta7 and old-order filtering; Goal15A retained table removes only ass.coker with delta5; added Coker handler services to old loader worlds; current enum declarations; G11D writer callers12 and new-handler import/registration exclusion; outputs redirected; G9A readonly pinned git show.'}
    (run/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if any(r['returncode'] for r in results.values()):
        raise SystemExit(1)

if __name__ == '__main__':
    main()


