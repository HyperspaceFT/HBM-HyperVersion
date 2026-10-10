"""Replay directly affected legacy checks without editing their source or old outputs.

Only output locations and the old recipe world's name-only service list are
adapted. The real new fraction table/transport are tested by verify_goal14b.py.
G11D's historical byte-diff check accounts for the two explicit new handler
registration lines, as it already does for G12B/G13B. No assertion is removed.
"""
from pathlib import Path
import contextlib
import hashlib
import importlib.util
import json
import subprocess
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).parent
OUT = ROOT / "build/migration/goal14b/affected"
FRACTION_LINES = ("import com.hbm.inventory.recipes.FractionRecipes;", "        recipeHandlers.add(new FractionRecipes());")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, replacements, evidence):
    source = TOOLS / (name + ".py")
    text = source.read_text(encoding="utf-8")
    for before, after in replacements:
        assert text.count(before) == 1, (name, before)
        text = text.replace(before, after, 1)
    (evidence / (name + "-adapted.py")).write_text(text, encoding="utf-8")
    module = types.ModuleType("goal14b_affected_" + name)
    # Keep all source/fixture paths rooted at the untouched original module.
    module.__file__ = str(source)
    exec(compile(text, str(source), "exec"), module.__dict__)
    return module


def add_fraction_service(factory):
    def wrapped(*args, **kwargs):
        services = factory(*args, **kwargs)
        services["com/hbm/inventory/recipes/FractionRecipes.java"] = (
            "package com.hbm.inventory.recipes;import com.hbm.inventory.recipes.loader.*;"
            "import com.google.gson.*;import com.google.gson.stream.*;"
            "public class FractionRecipes extends SerializableRecipe{"
            'public String getFileName(){return "FractionRecipes.json";}'
            "public Object getRecipeObject(){return java.util.List.of();}"
            "public void readRecipe(JsonElement e){}public void writeRecipe(Object o,JsonWriter w){}"
            "public void registerDefaults(){}public void deleteRecipes(){}}"
        )
        return services
    return wrapped


def main():
    selected = sys.argv[1:] or ["verify_goal14a", "verify_goal11d", "verify_review_fluid_saves", "verify_review_block_lifecycle"]
    allowed = {"verify_goal14a", "verify_goal11d", "verify_review_fluid_saves", "verify_review_block_lifecycle"}
    assert set(selected) <= allowed and len(set(selected)) == len(selected), selected
    run = OUT / uuid.uuid4().hex
    run.mkdir(parents=True)
    before = {p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT / "src/main").rglob("*") if p.is_file()}
    old_tools = {p.relative_to(ROOT).as_posix(): digest(p) for p in TOOLS.rglob("*")
                 if p.is_file() and p.suffix in (".py", ".java") and "14b" not in p.as_posix().lower()}
    results = {}
    print(f"Affected check transcript: {run}", flush=True)
    for name in selected:
        replacements = []
        if name == "verify_goal14a":
            replacements = [
                ("boundary = ROOT / 'build/migration/goal14a'", "boundary = ROOT / 'build/migration/goal14b/affected/diesel'"),
                ("(boundary / 'baseline.json').read_text", "(ROOT / 'build/migration/goal14a/baseline.json').read_text"),
            ]
        elif name == "verify_goal11d":
            # Extend the exact caller inventory by the two new output writes;
            # every old caller and both new calls must still be present.
            replacements = [
                ("sorted([GENERIC_RECIPES, SOLDERING, ARC_WELDER, CRACKING])",
                 "sorted([GENERIC_RECIPES, SOLDERING, ARC_WELDER, CRACKING, 'com/hbm/inventory/recipes/FractionRecipes.java'])"),
                ("len(found) == 6 and sum(rel == CRACKING for rel, _ in found) == 2",
                 "len(found) == 8 and sum(rel == CRACKING for rel, _ in found) == 2 and sum(rel == 'com/hbm/inventory/recipes/FractionRecipes.java' for rel, _ in found) == 2"),
                ("CrackingRecipes (verify_goal12b.py): {found}",
                 "CrackingRecipes (verify_goal12b.py) and FractionRecipes (verify_goal14b.py): {found}"),
                ("(the cracking outputs): {found}",
                 "(the cracking outputs) plus Goal14B's 2 fraction outputs: {found}"),
            ]
        elif name == "verify_review_fluid_saves":
            replacements = [("ROOT / \"build/migration/review-fixes/fluid\"", "ROOT / \"build/migration/goal14b/affected/fluid\"")]
        elif name == "verify_review_block_lifecycle":
            replacements = [("ROOT / \"build/migration/review-fixes/blocks\"", "ROOT / \"build/migration/goal14b/affected/blocks\"")]
        module = load(name, replacements, run)
        if name in ("verify_goal14a", "verify_goal11d"):
            module.recipe_stubs = add_fraction_service(module.recipe_stubs)
        if name == "verify_goal11d":
            module.OUTPUT = OUT / "loader"
            module.RECIPE_REFERENCE = OUT / "loader-reference"
            module.GOAL13B_LINES += FRACTION_LINES
            module.git = lambda *args: subprocess.check_output(
                ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT), *args])
        previous_args = sys.argv
        sys.argv = [str(TOOLS / (name + ".py"))]
        rc = 0
        with (run / (name + ".log")).open("w", encoding="utf-8") as log:
            try:
                with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    module.main()
            except SystemExit as ex:
                rc = ex.code or 0
                log.write(f"\nSystemExit: {rc}\n")
            except Exception:
                import traceback
                traceback.print_exc(file=log)
                rc = 1
            finally:
                sys.argv = previous_args
        results[name] = {"returncode": rc, "log": str(run / (name + ".log")),
                         "original_script_sha256": digest(TOOLS / (name + ".py"))}
        print(f"{name}: {rc}", flush=True)
    assert before == {p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT / "src/main").rglob("*") if p.is_file()}, "Production changed during checks"
    assert all(digest(ROOT / p) == h for p, h in old_tools.items()), "Legacy verification source changed"
    (run / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if any(result["returncode"] for result in results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
