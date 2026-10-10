"""Replay the affected previous recipe/loader checks without changing old tests.

The only shared recipe-loader delta is registering MixerRecipes. This adapter
adds an empty mixer service to the old isolated world, keeps every Goal15B
assertion, and redirects its ordinary outputs into this batch. Mixer behavior
is exercised separately by verify_goal16a_recipes.py. Unchanged machine suites
are not repeated; preservation is checked from the real starting-point hashes.
"""
from pathlib import Path
import contextlib
import hashlib
import json
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).parent
OUT = ROOT / 'build/migration/goal16a/affected'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run = OUT / uuid.uuid4().hex
    run.mkdir(parents=True, exist_ok=False)
    production = {p.relative_to(ROOT).as_posix(): sha(p)
                  for p in (ROOT/'src/main').rglob('*') if p.is_file()}
    old_tools = {p.relative_to(ROOT).as_posix(): sha(p) for p in TOOLS.rglob('*')
                 if p.is_file() and p.suffix in ('.py', '.java') and '16a' not in p.as_posix().lower()}
    source = TOOLS/'verify_goal15b.py'
    text = source.read_text(encoding='utf-8')
    needle = "BOUNDARY = ROOT / 'build/migration/goal15b/regression'"
    assert text.count(needle) == 1
    text = text.replace(needle, f'BOUNDARY = Path({str(run / "goal15b")!r})')
    copied = run/'verify_goal15b-adapted.py'
    copied.write_text(text, encoding='utf-8')
    module = types.ModuleType('goal16a_affected_goal15b')
    module.__file__ = str(source)
    exec(compile(text, str(source), 'exec'), module.__dict__)
    factory = module.recipe_stubs

    def services(*args, **kwargs):
        result = factory(*args, **kwargs)
        path = 'com/hbm/inventory/recipes/MixerRecipes.java'
        assert path not in result
        result[path] = (
            'package com.hbm.inventory.recipes;import com.hbm.inventory.recipes.loader.*;'
            'import com.google.gson.*;import com.google.gson.stream.*;'
            'public class MixerRecipes extends SerializableRecipe {'
            'public String getFileName(){return "hbmMixer.json";}'
            'public Object getRecipeObject(){return java.util.List.of();}'
            'public void readRecipe(JsonElement e){}public void writeRecipe(Object o,JsonWriter w){}'
            'public void registerDefaults(){}public void deleteRecipes(){}}')
        return result

    module.recipe_stubs = services
    previous_args = sys.argv
    sys.argv = [str(source), '--world', 'recipe']
    rc = 0
    try:
        with (run/'goal15b-recipe.log').open('w', encoding='utf-8') as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                try:
                    module.main()
                except SystemExit as ex:
                    rc = ex.code or 0
                except Exception:
                    import traceback
                    traceback.print_exc()
                    rc = 1
    finally:
        sys.argv = previous_args
    assert all(sha(ROOT/name) == digest for name, digest in production.items()), 'Production changed during affected checks'
    assert all(sha(ROOT/name) == digest for name, digest in old_tools.items()), 'An old fixture/check changed'
    result = dict(evidence='Unchanged Goal15B recipe assertions, with a bounded loader service adapter; not game execution.',
                  returncode=rc, source_hashes=production, fixture_sha256=old_tools,
                  adapter_sha256=sha(copied), productionUnchanged=True, legacyToolsUnchanged=True,
                  log=(run/'goal15b-recipe.log').relative_to(ROOT).as_posix(),
                  command='verify_goal15b.py --world recipe (in-memory output redirection and empty MixerRecipes loader service)',
                  adapter_notes='No old assertions removed or changed; shared loader adds only MixerRecipes. New mixer processing is checked by its own production-source runners.')
    (run/'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Goal16A affected recipe check: returncode={rc}; output={run}', flush=True)
    raise SystemExit(rc)


if __name__ == '__main__':
    main()
