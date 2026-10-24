"""Run one of the six old isolated machine suites with the Goal 26C stand-in additions (goal26c_oldsuite_compat.py), without editing it.

python -B -X utf8 tools/migration/goal26c_oldsuite_run.py SUITE    (SUITE: verify_goal16a_machine, verify_goal16b_machine, verify_goal17b_machine,
                                                                     verify_goal18a_machine, verify_goal18b_machine, verify_goal19a_pollution)

The frozen suite module is imported unchanged; the runner (1) wraps the suite's own stub builder so the Items stand-in gains the missing
fully qualified vanilla fields AssemblyMachineRecipes names (STRING, PAPER), and (2) points the suite's run directory at
build/migration/goal26c/oldsuites/runs/<suite>/ instead of the suite's own build/migration/goal1x/... directory. Everything else, every
fixture, assertion and mutation of the suite, runs as frozen. The added fields are written to build/migration/goal26c/oldsuites/<suite>-compat.json.
"""
import importlib
import json
from pathlib import Path
import sys
import types
import uuid as real_uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BATCH = ROOT / "build/migration/goal26c/oldsuites"
SUITES = ("verify_goal16a_machine", "verify_goal16b_machine", "verify_goal17b_machine", "verify_goal18a_machine", "verify_goal18b_machine",
          "verify_goal19a_pollution")


def uuid_shim(relative_prefix):
    """uuid stand-in for suites that build ROOT / 'build/migration/goal1x/machine' / uuid.uuid4().hex: the hex becomes a path into BATCH."""
    def uuid4():
        return types.SimpleNamespace(hex=f"{relative_prefix}/{real_uuid.uuid4().hex}")
    return types.SimpleNamespace(uuid4=uuid4)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SUITES:
        raise SystemExit("usage: goal26c_oldsuite_run.py " + "|".join(SUITES))
    name = sys.argv[1]
    sys.path.insert(0, str(HERE))
    import goal26c_oldsuite_compat as compat
    suite = importlib.import_module(name)
    runs = BATCH / "runs" / name
    runs.mkdir(parents=True, exist_ok=True)
    log = []
    source = ROOT / "src/main/java"
    if name in ("verify_goal16a_machine", "verify_goal16b_machine", "verify_goal17b_machine"):
        suite.machine_stubs = compat.wrap_builder(suite.machine_stubs, source, log)
        # ROOT / 'build/migration/goal1x/machine' / hex -> build/migration/goal26c/oldsuites/runs/<suite>/<hex>
        suite.uuid = uuid_shim(f"../../goal26c/oldsuites/runs/{name}")
    elif name == "verify_goal18a_machine":
        suite.machine_stubs = compat.wrap_builder(suite.machine_stubs, source, log)
        importlib.import_module("goal18a_regression.common").OUT = runs
    elif name == "verify_goal18b_machine":
        suite.machine_stubs = compat.wrap_builder(suite.machine_stubs, source, log)
        suite.OUT = runs
    else:
        suite.BUILDERS = {k: compat.wrap_builder(v, source, log) for k, v in suite.BUILDERS.items()}
        suite.OUT = runs
    code = 0
    try:
        suite.main()
    except SystemExit as exit_:
        code = exit_.code if isinstance(exit_.code, int) else (0 if exit_.code is None else 1)
        if not isinstance(exit_.code, int) and exit_.code is not None:
            print(exit_.code, flush=True)
    record = dict(suite=name, exit=code, qualified_items=compat.qualified_items(source), compat_log=log, run_directory=str(runs.relative_to(ROOT)))
    (BATCH / f"{name}-compat.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"goal26c_oldsuite_run {name}: exit {code}; compat: {log}", flush=True)
    sys.exit(code)


if __name__ == "__main__":
    main()
