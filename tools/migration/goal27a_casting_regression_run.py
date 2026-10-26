"""Run one of the two frozen isolated casting regressions against the Goal27A tree, without editing it.

python -B -X utf8 tools/migration/goal27a_casting_regression_run.py SUITE [--unwrapped]
    SUITE: verify_goal10a (tools/migration/verify_goal10a.py with goal10a_regression/) or
           verify_goal5a_casting (tools/migration/verify_goal5a_casting.py with goal5a_casting_regression/)

Model: tools/migration/goal26c_oldsuite_run.py / goal26c_oldsuite_compat.py. The frozen suite module is imported unchanged and its
main() runs as frozen (every fixture, stand-in, production list and assertion). The runner only

(1) points the suite's run directory (module global OUTPUT, build/migration/goal10a/regression or build/migration/goal5a/casting-regression)
    at build/migration/goal27a/castingsuites/runs/<suite>/, so a run never writes into an older batch directory, and
(2) unless --unwrapped is given, wraps the suite's own stub builder(s) with goal27a_casting_compat.py, which may only ADD stand-in
    classes or fields that a Goal27A production file needs and the frozen world lacks. It never replaces a class or field the world
    already declares, never adds or removes a production source, never touches a frozen suite, its stub modules or its fixtures on disk
    and never changes an assertion. When the 27A production cannot be compiled in the frozen world without replacing a class the suite
    compiles or asserts, compat.blockers() names it and the suite is run unwrapped instead (its by-design failure is recorded).

The record (exit code, mode, what was added, what blocks the wrapped run, the run directory) is written to
build/migration/goal27a/castingsuites/<suite>-compat.json; the suite's own transcript is <run directory>/<uuid>/result.log.
javac and java only; no Gradle, no game.
"""
import importlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BATCH = ROOT / "build/migration/goal27a/castingsuites"
SUITES = ("verify_goal10a", "verify_goal5a_casting")
# The stub-builder globals each frozen suite calls from main() (imported by name into the suite module).
BUILDERS = {"verify_goal10a": ("build_machine_stubs", "build_recipe_stubs"), "verify_goal5a_casting": ("build_stubs",)}


def main():
    args = sys.argv[1:]
    unwrapped = "--unwrapped" in args
    args = [a for a in args if a != "--unwrapped"]
    if len(args) != 1 or args[0] not in SUITES:
        raise SystemExit("usage: goal27a_casting_regression_run.py " + "|".join(SUITES) + " [--unwrapped]")
    name = args[0]
    sys.path.insert(0, str(HERE))
    import goal27a_casting_compat as compat
    suite = importlib.import_module(name)
    runs = BATCH / "runs" / name
    runs.mkdir(parents=True, exist_ok=True)
    assert hasattr(suite, "OUTPUT"), name + " has no OUTPUT global"
    suite.OUTPUT = runs
    source = ROOT / "src/main/java"
    log, blockers = [], []
    mode = "unwrapped (requested)" if unwrapped else "wrapped"
    if not unwrapped:
        blockers = compat.blockers(name, source)
        if blockers:
            mode = "unwrapped (blocked: the 27A production cannot compile in the frozen world without replacing an asserted class)"
        else:
            for attr in BUILDERS[name]:
                assert hasattr(suite, attr), (name, attr)
                setattr(suite, attr, compat.wrap_builder(name, attr, getattr(suite, attr), source, log))
    print(f"goal27a_casting_regression_run {name}: mode {mode}", flush=True)
    for b in blockers:
        print(f"BLOCKER {b}", flush=True)
    before = {p.name for p in runs.iterdir()}
    code = 0
    try:
        suite.main()
    except SystemExit as exit_:
        code = exit_.code if isinstance(exit_.code, int) else (0 if exit_.code is None else 1)
        if not isinstance(exit_.code, int) and exit_.code is not None:
            print(exit_.code, flush=True)
    new_runs = sorted(p for p in runs.iterdir() if p.is_dir() and p.name not in before)
    transcript = new_runs[-1] / "result.log" if len(new_runs) == 1 and (new_runs[-1] / "result.log").is_file() else None
    stages, errors, kinds = [], [], {}
    if transcript is not None:
        text = transcript.read_text(encoding="utf-8", errors="replace")
        labels = re.findall(r"^== (.+) ==$", text, re.M)
        codes = re.findall(r"^returncode: (-?\d+)$", text, re.M)
        stages = [dict(stage=l, returncode=int(c)) for l, c in zip(labels, codes)]
        errors, counter = compat.attribute(transcript)
        kinds = dict(counter)
        for where, kind in errors:
            print(f"ERROR {where}: {kind}", flush=True)
        print(f"javac errors by attribution: {kinds}", flush=True)
    record = dict(suite=name, exit=code, mode=mode, blockers=blockers, compat_log=log, run_directory=runs.relative_to(ROOT).as_posix(),
                  transcript=transcript.relative_to(ROOT).as_posix() if transcript else None, stages=stages,
                  javac_errors=[dict(at=w, attribution=k) for w, k in errors], javac_errors_by_attribution=kinds,
                  note="Isolated stub-world regression compiled with javac; a pass would establish the stub-world assertions only, not in-game behaviour.")
    (BATCH / f"{name}-compat.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"goal27a_casting_regression_run {name}: exit {code}; mode {mode}; compat: {log}", flush=True)
    sys.exit(code)


if __name__ == "__main__":
    main()
