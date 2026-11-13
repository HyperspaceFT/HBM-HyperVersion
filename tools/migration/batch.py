#!/usr/bin/env python3
"""Batch delivery steps of the migration workflow: freeze, chain, compare, package, verify-delivery.

One manifest per batch (migration/<batch>-batch.toml, see batch.example.toml) names what the batch owns.
This tool holds the checks of migration/README.md "批次验证链" once, for every batch. It reads both
repositories, starts Gradle and the migration tools only in `chain` and `compare`, and writes only below
build/migration/<batch>/ and build/migration/releases/<batch>/.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from migration import (BUILD_FILES, DEFAULT_SOURCE, DEFAULT_TARGET, MigrationError, load_json,
                       matches as feature_matches, relative_path, validate_manifest)

TOOLS = Path(__file__).resolve().parent
SRC = "src/main/java/"
RES = "src/main/resources/"
GENERATED = "src/generated/resources/"
GAMETESTS = SRC + "com/hbm/gametest/"
STAMP = GENERATED + ".migration-stamp.json"
EN = GENERATED + "assets/hbmsntm/lang/en_us.json"
ZH = RES + "assets/hbmsntm/lang/zh_cn.json"
ZH_MAP = "migration/localization/zh_cn-map.json"
FEATURES = "migration/features.json"
MODS_TOML = "META-INF/neoforge.mods.toml"
CARRIED_OWNER = "carried"
DEBUG_NAME_OWNER = "recompile-debug-names"

# README "批次验证链" item 3 mirrors this list.
EVERGREEN_SUITES = (("verify_goal18a_structures", ()), ("verify_goal19b_structures", ()),
                    ("verify_review_block_lifecycle", ()), ("verify_review_ability_harvest", ()),
                    ("verify_goal7b_resources", ("--source-only",)))
GRADLE_STEPS = (("runData", "rundata.log", "runData"), ("gametest", "gametest.log", "runGameTestServer"),
                ("build", "build.log", "build"))
RECORD_STEPS = (("loc", "localization.log", "localization-audit.json"), ("audit", "resources-audit.log", "resources-audit.json"),
                ("jar", "packaged-resources.log", "packaged-resources.json"), ("validate", "validate.log", None))
TEXT_SUFFIXES = {".java", ".json", ".md", ".py", ".txt", ".lang", ".sh", ".toml", ".properties", ".gradle", ".cfg",
                 ".mcmeta", ".obj", ".fsh", ".vsh", ".xml", ".yml", ".yaml"}
STAMP_TEXT = set("cfg csv fsh gradle java json lang mcmeta md mtl obj properties toml txt vsh xml yaml yml".split())
GAMETEST_PASSED = re.compile(r"All (\d+) required tests passed")
GAMETEST_ANNOTATION = re.compile(r"^\s*@GameTest\(", re.M)
GAMETEST_TAG = re.compile(r'String TAG = "(\[hbm-[^"\]]*\])"')
GAMETEST_MARKER = re.compile(r'passed\("(\w+)"\)')

MANIFEST_DEFAULTS = {"compare": False, "records": [], "optional_records": [], "names_package": [], "row_diff": [],
                     "deleted": [], "optional": [], "carried": {}, "groups": {}, "gametests_new": [],
                     "gametests_changed": {}, "status_changes": [], "language_keys_removed": False, "scope": "", "evidence": "", "gametest_note": "",
                     "radiation_note": "", "meltdown_note": ""}
MANIFEST_REQUIRED = ("batch", "previous", "task_book", "source_head", "start_head", "snapshot")


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def stamp_sha(path: Path) -> str:
    """The hash gradle/migration-resources.gradle records in the stamp: text files with LF line endings."""
    data = path.read_bytes()
    if path.suffix.lstrip(".").lower() in STAMP_TEXT:
        try:
            data = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return sha_bytes(data)


def git_bytes(repo: Path, *args: str) -> bytes:
    """Read-only git: no optional index lock, per-process trust of the selected repository."""
    command = ["git", "--no-optional-locks", "-c", f"safe.directory={repo.as_posix()}", "-C", str(repo), *args]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise MigrationError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def git_text(repo: Path, *args: str) -> str:
    return git_bytes(repo, *args).decode("utf-8")


def git_names(repo: Path, *args: str) -> list[str]:
    return [name for name in git_text(repo, "ls-files", "-z", *args).split("\0") if name]


def is_glob(pattern: str) -> bool:
    return any(char in pattern for char in "*?[")


def eol_counts(data: bytes) -> tuple[int, int]:
    """(CRLF, lone LF)."""
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf


def owner_source(entry: str) -> str:
    """Outer source path of a class entry: com/hbm/X$1.class -> src/main/java/com/hbm/X.java."""
    return SRC + entry[:-len(".class")].split("$", 1)[0] + ".java"


def annotations(path: Path) -> int:
    return len(GAMETEST_ANNOTATION.findall(path.read_text(encoding="utf-8")))


def load_manifest(path: Path, name: str) -> dict:
    if not path.is_file():
        raise MigrationError(f"Batch manifest not found: {path} (copy tools/migration/batch.example.toml)")
    with path.open("rb") as handle:
        manifest = tomllib.load(handle)
    unknown = sorted(set(manifest) - set(MANIFEST_REQUIRED) - set(MANIFEST_DEFAULTS))
    missing = sorted(key for key in MANIFEST_REQUIRED if not manifest.get(key))
    if unknown or missing:
        raise MigrationError(f"{path.name}: unknown keys {unknown}, missing keys {missing}")
    if manifest["batch"] != name:
        raise MigrationError(f"{path.name} is the manifest of {manifest['batch']!r}, not {name!r}")
    manifest = {**MANIFEST_DEFAULTS, **manifest}
    for key in ("carried", "groups"):
        if not all(isinstance(paths, list) for paths in manifest[key].values()):
            raise MigrationError(f"{path.name}: every [{key}] entry is a list of paths")
    literal = [p for paths in manifest["carried"].values() for p in paths]
    literal += manifest["gametests_new"] + list(manifest["gametests_changed"]) + manifest["records"]
    literal += manifest["optional_records"] + manifest["names_package"] + manifest["row_diff"] + manifest["deleted"]
    literal += [manifest["task_book"], manifest["snapshot"]]
    for pattern in literal + manifest["optional"] + [p for paths in manifest["groups"].values() for p in paths]:
        relative_path(pattern)
    globs = sorted(p for p in literal if is_glob(p))
    if globs:
        raise MigrationError(f"{path.name}: only [groups] and optional take patterns: {globs}")
    unexplained = sorted(p for p, reason in manifest["gametests_changed"].items() if not str(reason).strip())
    if unexplained:
        raise MigrationError(f"{path.name}: gametests_changed needs a reason for {unexplained}")
    return manifest


def jar_name(root: Path) -> str:
    properties = dict(line.split("=", 1) for line in (root / "gradle.properties").read_text(encoding="utf-8").splitlines()
                      if "=" in line and not line.lstrip().startswith("#"))
    return f"{properties['mod_id'].strip()}-{properties['mod_version'].strip()}.jar"


class Batch:
    def __init__(self, root: Path, source: Path, name: str, manifest: Path | None = None, work_dir: Path | None = None):
        if not re.fullmatch(r"[a-z][a-z0-9]*", name):
            raise MigrationError(f"Batch names are lower-case letters and digits: {name!r}")
        self.root, self.source, self.name = root.resolve(), source.resolve(), name
        self.manifest_path = (manifest or self.root / f"migration/{name}-batch.toml").resolve()
        self.manifest = load_manifest(self.manifest_path, name)
        self.out = (work_dir or self.root / "build/migration" / name).resolve()
        self.final = self.out / "final"
        self.start_files = self.out / "baseline-files"
        self.jar = self.root / "build/libs" / jar_name(self.root)
        self.releases = self.root / "build/migration/releases"
        self.release = self.releases / name
        self.release_name = f"{self.jar.stem}-{name}.jar"
        previous = self.manifest["previous"]
        self.previous_jar = self.releases / previous / f"{self.jar.stem}-{previous}.jar"
        self.previous_receipt = self.previous_jar.with_name("release.json")
        self.previous_sums = self.previous_jar.with_name("SHA256SUMS.txt")
        self.record_pattern = re.compile(rf"migration/({re.escape(name)}-[^/]+|{re.escape(name.upper())}(-[^/]+)?\.md)")
        self.ownership_record = f"migration/{name}-resource-ownership.json"

    def rel(self, path: Path) -> str:
        path = path.resolve()
        return path.relative_to(self.root).as_posix() if path.is_relative_to(self.root) else path.as_posix()

    def groups_of(self, path: str) -> list[str]:
        return [group for group, patterns in self.manifest["groups"].items()
                if any(path == pattern or (is_glob(pattern) and fnmatch.fnmatchcase(path, pattern)) for pattern in patterns)]

    def carried_group(self, path: str) -> list[str]:
        return [group for group, paths in self.manifest["carried"].items() if path in paths]


def tree_hashes(root: Path) -> dict:
    """Every tracked or untracked-not-ignored file; migration/ and build/ are Git-ignored and not in this map."""
    return {name: sha(root / name) for name in sorted(set(git_names(root, "--cached", "--others", "--exclude-standard")))
            if (root / name).is_file()}


def migration_hashes(root: Path) -> dict:
    return {path.relative_to(root).as_posix(): sha(path) for path in sorted((root / "migration").rglob("*"))
            if path.is_file() and path.name != ".DS_Store"}


def delivered_tree(batch: Batch, receipt: dict) -> dict:
    """The Git-visible tree a package delivered: its start overlaid with its receipt's changes."""
    start = batch.root / receipt["actual_start"]
    if not start.is_file():
        raise MigrationError(f"The start a receipt names is missing: {receipt['actual_start']}")
    expected = dict(read_json(start)["files"])
    for change in receipt["changed_files"]:
        if change["path"].startswith("migration/"):
            continue
        if change.get("change") == "deleted" or change.get("after_sha256") is None:
            expected.pop(change["path"], None)
        else:
            expected[change["path"]] = change["after_sha256"]
    return expected


def previous_release_state(batch: Batch) -> tuple[dict, dict]:
    for path in (batch.previous_jar, batch.previous_receipt, batch.previous_sums):
        if not path.is_file():
            raise MigrationError(f"Previous release file missing: {batch.rel(path)}")
    receipt = read_json(batch.previous_receipt)
    digest = sha(batch.previous_jar)
    if digest != receipt["sha256"] or batch.previous_sums.read_bytes() != f"{digest}  {batch.previous_jar.name}\n".encode("ascii"):
        raise MigrationError(f"The {batch.manifest['previous']} JAR, its receipt and SHA256SUMS.txt disagree")
    state = {"path": batch.rel(batch.previous_jar), "sha256": digest, "bytes": batch.previous_jar.stat().st_size,
             "receipt_sha256": sha(batch.previous_receipt), "sums_sha256": sha(batch.previous_sums)}
    return state, receipt


def repository_state(batch: Batch) -> dict:
    return {"source_head": git_text(batch.source, "rev-parse", "HEAD").strip(),
            "source_status": git_text(batch.source, "status", "--porcelain=v1", "--untracked-files=all"),
            "target_head": git_text(batch.root, "rev-parse", "HEAD").strip(),
            "target_status": git_text(batch.root, "status", "--porcelain=v1", "--untracked-files=all")}


def cmd_freeze(batch: Batch, dry: bool) -> int:
    """Record the start of a batch before its first write."""
    manifest, baseline = batch.manifest, batch.out / "baseline.json"
    if baseline.exists() and not dry:
        raise MigrationError(f"Refusing to overwrite an existing start: {batch.rel(baseline)}")
    state = repository_state(batch)
    previous, receipt = previous_release_state(batch)
    files = tree_hashes(batch.root)
    expected = delivered_tree(batch, receipt)
    delta = sorted(path for path in set(files) | set(expected) if files.get(path) != expected.get(path))
    carried = sorted({path for paths in manifest["carried"].values() for path in paths})
    features = load_json(batch.root / FEATURES)
    problems = []
    if state["source_status"]:
        problems.append("the original worktree is dirty")
    if state["source_head"] != manifest["source_head"]:
        problems.append(f"the original HEAD is {state['source_head']}, the manifest says {manifest['source_head']}")
    if state["target_head"] != manifest["start_head"]:
        problems.append(f"the NEO HEAD is {state['target_head']}, the manifest says {manifest['start_head']}")
    if delta != carried:
        problems.append(f"the tree differs from the {manifest['previous']} delivery in paths [carried] does not list "
                        f"{sorted(set(delta) - set(carried))}; [carried] lists unchanged paths {sorted(set(carried) - set(delta))}")
    missing = validate_manifest(features, batch.source, batch.root)
    if missing:
        problems.append(f"features.json maps missing files: {missing[:6]}")
    migration = migration_hashes(batch.root)
    dirty = sorted(name for name in set(git_names(batch.root, "--modified", "--others", "--exclude-standard")) if (batch.root / name).is_file())
    copied = sorted(set(dirty) | {path for path in migration if not path.startswith("migration/baselines/")})
    snapshot = batch.root / manifest["snapshot"]
    stamp = read_json(batch.root / STAMP)
    report = {"batch": batch.name, "previous": manifest["previous"], "delta_against_previous_delivery": delta,
              "tree_files": len(files), "migration_files": len(migration), "copies": len(copied),
              "validated_features": len(features["features"]), "problems": problems}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if problems:
        return 1
    if dry:
        return 0
    batch.out.mkdir(parents=True, exist_ok=True)
    for path in copied:
        target = batch.start_files / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(batch.root / path, target)
        if sha(target) != {**files, **migration}[path]:
            raise MigrationError(f"{path} changed while the start was being copied; freeze again on a stable tree")
    gametests = sorted((batch.root / GAMETESTS).glob("*.java"))
    record = {"batch": batch.name, "captured_at_utc": datetime.now(timezone.utc).isoformat(), **state,
              "carried": {"groups": manifest["carried"], "hashes": {path: files[path] for path in carried}},
              "files": files, "migration_files": migration, "copied": copied, "previous_release": previous,
              "snapshot": {"path": manifest["snapshot"], "sha256": sha(snapshot) if snapshot.is_file() else None},
              "build_libs_jar_sha256_at_freeze": sha(batch.jar) if batch.jar.is_file() else None,
              "stamp_state": {"sha256": files[STAMP], "generated_resources_recorded": len(stamp["generated"])},
              "gametest_annotations": {batch.rel(path): annotations(path) for path in gametests},
              "validated_features": len(features["features"])}
    with baseline.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Start frozen: {batch.rel(baseline)}")
    return 0


def load_start(batch: Batch) -> dict:
    baseline = batch.out / "baseline.json"
    if not baseline.is_file():
        raise MigrationError(f"No frozen start: {baseline} (run `batch.py freeze --batch {batch.name}` before the first write)")
    return read_json(baseline)


def changed_since_start(batch: Batch, base: dict) -> dict:
    """{path: added|modified|deleted} against the start: the Git-visible files and every file under migration/."""
    start = {**base["files"], **base["migration_files"]}
    now = set(git_names(batch.root, "--cached", "--others", "--exclude-standard"))
    now |= {path.relative_to(batch.root).as_posix() for path in (batch.root / "migration").rglob("*") if path.is_file()}
    result = {}
    for path in sorted(now | set(start)):
        if path.startswith("build/") or path.rsplit("/", 1)[-1] == ".DS_Store":
            continue
        before = start.get(path)
        if not (batch.root / path).is_file():
            if before:
                result[path] = "deleted"
        elif before is None:
            result[path] = "added"
        elif before != sha(batch.root / path):
            result[path] = "modified"
    return result


def start_bytes(batch: Batch, base: dict, path: str) -> bytes | None:
    """Start bytes of a file: its copy, the unchanged file, the previous package's JAR entry or the blob at the start commit."""
    want = base["files"].get(path) or base["migration_files"].get(path)
    copy = batch.start_files / path
    if copy.is_file() and sha(copy) == want:
        return copy.read_bytes()
    if (batch.root / path).is_file() and sha(batch.root / path) == want:
        return (batch.root / path).read_bytes()
    for prefix in (RES, GENERATED):
        if path.startswith(prefix):
            with zipfile.ZipFile(batch.previous_jar) as prior:
                try:
                    data = prior.read(path[len(prefix):])
                except KeyError:
                    continue
                if sha_bytes(data) == want:
                    return data
    try:
        blob = git_bytes(batch.root, "show", f"{base['target_head']}:{path}")
    except MigrationError:
        return None
    return blob if sha_bytes(blob) == want else None


def find_javap() -> Path | None:
    candidates = []
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]) / "bin/javap")
    if shutil.which("javap"):
        candidates.append(Path(shutil.which("javap")))
    try:
        home = subprocess.check_output(["/usr/libexec/java_home", "-v", "21"], stderr=subprocess.DEVNULL).decode().strip()
        candidates.append(Path(home) / "bin/javap")
    except (OSError, subprocess.CalledProcessError):
        pass
    return next((candidate for candidate in candidates if candidate.is_file()), None)


LVT_ROW = re.compile(r"^\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)$")
PARAM_ROW = re.compile(r"^(\s+)(\S+)((?:\s+\S+)*)$")
UTF8_ROW = re.compile(r"^(\s+#\d+ = Utf8\s+)(\S+)$")
METHOD_HEADER = re.compile(r"^  (?!#)(\S.*\);)$")
ATTRIBUTE_HEADER = re.compile(r"^\s+(\w+):$")
NAME_TABLES = ("LocalVariableTable", "LocalVariableTypeTable", "MethodParameters")


def class_name_difference(old: bytes, new: bytes, javap: Path) -> tuple[bool, object]:
    """Prove that two class files differ only in local variable and parameter names.

    javac is not deterministic about these names between two builds of unchanged sources. The `javap -v -p`
    output without its header lines must be equal line for line except Utf8 constant-pool rows and rows of a
    name table whose other columns are equal; the renamed constants must be exactly the renamed table names,
    so no other use of a constant changed and every Code section is identical.
    """
    with tempfile.TemporaryDirectory() as temp:
        outputs = []
        for label, data in (("old", old), ("new", new)):
            path = Path(temp) / f"{label}.class"
            path.write_bytes(data)
            text = subprocess.run([str(javap), "-v", "-p", str(path)], capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", check=True).stdout.replace("\r\n", "\n")
            outputs.append([line for line in text.split("\n")
                            if not line.lstrip().startswith(("Classfile ", "Last modified", "SHA-256 checksum"))])
    a, b = outputs
    if len(a) != len(b):
        return False, f"javap -v output differs in length ({len(a)} vs {len(b)} lines)"
    method, section, renamed_utf8, renamed_tables, other, methods = None, None, [], [], [], {}
    for x, y in zip(a, b):
        found = METHOD_HEADER.match(x)
        if found:
            method, section = found.group(1), None
        header = ATTRIBUTE_HEADER.match(x)
        if header:
            section = header.group(1) if header.group(1) in NAME_TABLES else None
        if x == y:
            continue
        ux, uy = UTF8_ROW.match(x), UTF8_ROW.match(y)
        lx, ly = LVT_ROW.match(x), LVT_ROW.match(y)
        px, py = PARAM_ROW.match(x), PARAM_ROW.match(y)
        if ux and uy and ux.group(1) == uy.group(1):
            renamed_utf8.append((ux.group(2), uy.group(2)))
        elif section in NAME_TABLES[:2] and lx and ly and lx.group(1, 2, 3, 5) == ly.group(1, 2, 3, 5) and lx.group(4) != ly.group(4):
            renamed_tables.append((lx.group(4), ly.group(4)))
            methods.setdefault(method or "?", []).append([lx.group(4), ly.group(4)])
        elif section == "MethodParameters" and px and py and px.group(1) == py.group(1) and px.group(3) == py.group(3) and px.group(2) != py.group(2):
            renamed_tables.append((px.group(2), py.group(2)))
            methods.setdefault(method or "?", []).append([px.group(2), py.group(2)])
        else:
            other.append((x.strip()[:80], y.strip()[:80]))
    if other:
        return False, "other differing javap lines: " + str(other[:3])
    if not renamed_tables or sorted(set(renamed_utf8)) != sorted(set(renamed_tables)):
        return False, f"renamed constants {renamed_utf8} are not the renamed table names {renamed_tables}"
    return True, {"renamed_names_by_method": dict(sorted(methods.items())), "renamed_local_variables": sorted(set(renamed_tables)),
                  "differing_lines": len(renamed_utf8) + len(renamed_tables), "bytecode_identical": True}


def run_logged(command: list[str], log: Path, cwd: Path) -> int:
    with log.open("wb") as handle:
        return subprocess.run(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT, check=False).returncode


def read_exits(path: Path) -> dict:
    if not path.is_file():
        return {}
    return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").split())


def chain_steps(batch: Batch, tools_changed: bool) -> list[tuple[str, str, list[str], str]]:
    """(name, log, command, kind) in the order of README "批次验证链" item 2."""
    python = [sys.executable, "-B", "-X", "utf8"]
    jar = batch.rel(batch.jar)
    steps = [(name, log, [str(TOOLS / "build.sh"), "--offline", task], "gradle") for name, log, task in GRADLE_STEPS]
    arguments = {"loc": ["localization"], "audit": ["audit"], "jar": ["audit", "--jar", jar], "validate": ["validate"]}
    for name, log, output in RECORD_STEPS:
        command = python + [str(TOOLS / "migration.py"), "--source", str(batch.source), "--target", str(batch.root), *arguments[name]]
        steps.append((name, log, command + (["--output", str(batch.final / output)] if output else []), "records"))
    for suite, extra in EVERGREEN_SUITES:
        steps.append((suite, f"suite-{suite}.log", python + [str(TOOLS / f"{suite}.py"), *extra], "suite"))
    if tools_changed:
        steps.append(("tools", "tools-unittest.log", python + ["-m", "unittest", "discover", "-s", "tools/migration/tests"], "suite"))
    for script in batch.manifest["row_diff"]:
        steps.append((Path(script).stem, f"rowdiff-{Path(script).stem}.log", python + [str(batch.root / script)], "suite"))
    return steps


def required_chain(batch: Batch, tools_changed: bool) -> list[str]:
    return [name for name, _, _, _ in chain_steps(batch, tools_changed)]


def require_report_root(batch: Batch) -> None:
    """migration.py writes its JSON reports only under TARGET/build/migration."""
    reports = batch.root / "build/migration"
    if not batch.final.is_relative_to(reports):
        raise MigrationError(f"chain and compare write reports through migration.py, which only writes under {reports}: "
                             f"choose a --work-dir there, not {batch.out}")


def cmd_chain(batch: Batch, start_at: str) -> int:
    """Run the final chain (or its tail) and keep every log and exit code in build/migration/<batch>/final/."""
    require_report_root(batch)
    base = load_start(batch)
    tools_changed = any(path.startswith("tools/") for path in changed_since_start(batch, base))
    steps = chain_steps(batch, tools_changed)
    if start_at == "gametest":
        steps = [step for step in steps if step[0] != "runData"]
    elif start_at == "records":
        steps = [step for step in steps if step[3] == "records"]
    batch.final.mkdir(parents=True, exist_ok=True)
    exits_path, done = batch.final / "chain-exits.txt", batch.final / "chain-done.txt"
    exits = read_exits(exits_path) if start_at != "runData" else {}
    done.unlink(missing_ok=True)
    failed = False
    for name, log, command, kind in steps:
        if name == "runData":
            shutil.copyfile(batch.root / STAMP, batch.final / "stamp-before-rundata.json")
        if name == "gametest":
            # The packaging check compares this log's creation time with every source's modification time.
            (batch.final / log).unlink(missing_ok=True)
        print(f"chain: {name}", flush=True)
        code = run_logged(command, batch.final / log, batch.root)
        exits[name] = str(code)
        exits_path.write_text("".join(f"{key}={value}\n" for key, value in exits.items()), encoding="utf-8")
        if name == "build" and code == 0:
            (batch.final / "jar.sha256").write_text(f"{sha(batch.jar)}  {batch.rel(batch.jar)}\n", encoding="utf-8")
        if code:
            failed = True
            print(f"chain: {name} exited {code}, see {batch.rel(batch.final / log)}", flush=True)
            if kind == "gradle":
                break
    else:
        done.write_text("done\n", encoding="utf-8")
    return 1 if failed else 0


def cmd_compare(batch: Batch) -> int:
    """README "批次验证链" item 4: compare against the manifest's snapshot, last, on the settled tree."""
    require_report_root(batch)
    batch.final.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-B", "-X", "utf8", str(TOOLS / "migration.py"), "--source", str(batch.source), "--target", str(batch.root), "compare", "--baseline",
               str(batch.root / batch.manifest["snapshot"]), "--output", str(batch.final / "compare.json")]
    code = run_logged(command, batch.final / "compare.log", batch.root)
    (batch.final / "compare-exit.txt").write_text(f"compare={code}\n", encoding="utf-8")
    print(f"compare exited {code}: {batch.rel(batch.final / 'compare.log')}")
    return code


def imported_assets(batch: Batch) -> tuple[dict | None, dict]:
    record = batch.root / batch.ownership_record
    if not record.is_file():
        return None, {}
    ownership = read_json(record)
    return ownership, {entry.get("target_path"): entry for entry in ownership.get("imported_assets", [])}


def path_owner(batch: Batch, path: str, change: str, start: dict, identical_imports: set) -> tuple[str, list[str]] | None:
    """(kind, groups) of a changed path, or None when neither the manifest nor a fixed rule owns it."""
    manifest, groups = batch.manifest, batch.groups_of(path)
    if path == STAMP:
        return "stamp", ["datagen"]
    if change == "deleted":
        return ("deleted", groups or ["deleted"]) if path in manifest["deleted"] else None
    if path in (EN, ZH, ZH_MAP):
        return "localization", ["localization"] + groups
    if path == manifest["snapshot"] and path.startswith("migration/baselines/"):
        return ("snapshot", ["records"]) if change == "added" else None
    if path.startswith(GAMETESTS):
        if path in manifest["gametests_new"]:
            return ("gametest-new", ["gametest"]) if change == "added" else None
        if path in manifest["gametests_changed"]:
            return ("gametest-changed", ["gametest"]) if change == "modified" else None
        return None
    if path in identical_imports:
        return "imported", ["imported-assets"] + groups
    if path == manifest["task_book"] or batch.record_pattern.fullmatch(path):
        return "reports", ["records"]
    if path in manifest["records"] or path in manifest["optional_records"]:
        return "records", ["records"]
    if not groups:
        return None
    if path.startswith("tools/"):
        return "tools", groups
    if path.startswith(GENERATED):
        return "generated", groups
    if path.startswith(SRC):
        return ("production" if path in start else "production-new"), groups
    if path.startswith(RES):
        return "resource", groups
    return "other", groups


def cmd_package(batch: Batch, check: bool, gametest_log: str | None) -> int:
    """README "批次验证链" item 7. Both modes run every check; --check writes nothing."""
    pending, failures, notes = [], [], []
    manifest, root = batch.manifest, batch.root

    def need(condition, message):
        """Evidence the real run requires; --check lists it as pending."""
        if condition:
            return True
        if not check:
            raise MigrationError(message)
        pending.append(message)
        return False

    def hard(condition, message):
        """A fact that is wrong now; --check lists it as a FAILURE and exits 1."""
        if condition:
            return True
        if not check:
            raise MigrationError(message)
        failures.append(message)
        return False

    # 1. The start and both repositories.
    base = load_start(batch)
    start = {**base["files"], **base["migration_files"]}
    state = repository_state(batch)
    source_head, start_head = manifest["source_head"], base["target_head"]
    hard(base["source_head"] == source_head == state["source_head"] and not state["source_status"],
         f"the original is not the clean {source_head[:9]} of the start and the manifest: HEAD {state['source_head']}")
    hard(state["target_head"] == start_head == manifest["start_head"],
         f"the NEO HEAD moved during the batch (a delivery stays uncommitted until the Goal's close-out): {state['target_head']}")
    hard(base["carried"]["groups"] == manifest["carried"], "[carried] of the manifest differs from the frozen start")
    broken = sorted(path for path in base["copied"] if not (batch.start_files / path).is_file() or sha(batch.start_files / path) != start[path])
    hard(not broken, "start copies differ from their recorded hashes: " + str(broken[:6]))
    carried = {path: batch.carried_group(path) for path in base["carried"]["hashes"]}

    # 2. The previous delivery: its JAR, receipt and SHA256SUMS.txt are what the start recorded.
    previous, prior_receipt = previous_release_state(batch)
    hard(previous == base["previous_release"], f"the {manifest['previous']} JAR, receipt or SHA256SUMS.txt changed since the start")
    previous_sha = previous["sha256"]

    # 3. Changes since the start: every path has an owner in the manifest; nothing else differs from its start hash.
    changes = changed_since_start(batch, base)
    ownership, import_entries = imported_assets(batch)
    identical_imports = {target for target, entry in import_entries.items() if entry.get("identical_to_source") is True}
    owners = {path: path_owner(batch, path, change, start, identical_imports) for path, change in changes.items()}
    unowned = sorted(path for path, owner in owners.items() if owner is None)
    hard(not unowned, "paths changed since the start that the manifest does not own (add them to a [groups] entry, to records, "
         "gametests_new, gametests_changed or deleted, or undo the change): " + str(unowned))
    for group, patterns in manifest["groups"].items():
        for pattern in patterns:
            matched = pattern in changes if not is_glob(pattern) else any(fnmatch.fnmatchcase(path, pattern) for path in changes)
            optional = any(pattern == item or fnmatch.fnmatchcase(pattern, item) for item in manifest["optional"])
            need(matched or optional, f"[groups] {group}: nothing changed yet for {pattern}")
    for path in manifest["records"] + [target for target in identical_imports]:
        need(path in changes, "change not present yet (still equals the start or absent): " + path)
    for path in manifest["gametests_new"]:
        need(changes.get(path) == "added", "new GameTest class not present yet: " + path)
    for path in manifest["gametests_changed"]:
        need(changes.get(path) == "modified", "gametests_changed lists a GameTest file that equals its start: " + path)
    for path in manifest["deleted"]:
        need(changes.get(path) == "deleted", "deleted lists a path that still exists: " + path)
    baselines = sorted(path for path in changes if path.startswith("migration/baselines/") and changes[path] != "added")
    hard(not baselines, "an existing observation snapshot changed or was deleted: " + str(baselines))
    change_list = [{"path": path, "change": change, "group": owners[path][0] if owners[path] else None,
                    "owners": owners[path][1] if owners[path] else None, "owner": batch.name, "before_sha256": start.get(path),
                    "after_sha256": sha(root / path) if change != "deleted" else None} for path, change in sorted(changes.items())]
    production = sorted(path for path in changes if path.startswith(SRC) and path.endswith(".java") and changes[path] != "deleted")
    tools_changed = any(path.startswith("tools/") for path in changes)

    # 3a. Line endings: a modified file keeps its start style, a new file carries no CRLF. An imported asset keeps the
    # original's bytes, CRLF included; step 3b checks it against the original.
    line_endings, eol_bad = {}, []
    for path, change in sorted(changes.items()):
        if change == "deleted" or Path(path).suffix.lower() not in TEXT_SUFFIXES:
            continue
        now = eol_counts((root / path).read_bytes())
        if change == "added":
            line_endings[path] = {"start_crlf_lf": None, "now_crlf_lf": list(now)}
            if now[0] and path not in import_entries:
                eol_bad.append(f"{path}: new file with CRLF {now}")
            continue
        data = start_bytes(batch, base, path)
        if not need(data is not None, path + " has no reproducible start bytes for the line-ending check"):
            continue
        was = eol_counts(data)
        line_endings[path] = {"start_crlf_lf": list(was), "now_crlf_lf": list(now)}
        if (was[0] == 0 and now[0]) or (was[1] == 0 and now[1]):
            eol_bad.append(f"{path}: start CRLF/LF {was}, now {now}")
    hard(not eol_bad, "line endings differ from the start style: " + "; ".join(eol_bad[:6]))

    # 4. Imported assets: byte copies of the original, in the worktree and at the recorded commit.
    imported_facts = {}
    for target in sorted(identical_imports):
        entry, original = import_entries[target], import_entries[target].get("source_path", "")
        if not need((root / target).is_file() and (batch.source / original).is_file(), f"imported resource {target} or its original {original} does not exist"):
            continue
        blob, checked_out = git_bytes(batch.source, "show", f"{source_head}:{original}"), (batch.source / original).read_bytes()
        last = git_text(batch.source, "log", "-1", "--format=%H|%cs", source_head, "--", original).strip()
        imported_facts[target] = {"original_path": original, "original_commit": source_head, "sha256": sha(root / target),
                                  "bytes": (root / target).stat().st_size, "original_blob_sha256": sha_bytes(blob),
                                  "original_last_commit": last, "replaced": target in start}
        hard((root / target).read_bytes() == checked_out == blob, f"{target} is not byte-identical to the original {original} (worktree and blob at {source_head[:9]})")
        hard(last == f"{entry.get('source_last_commit')}|{entry.get('source_last_commit_date')}", f"{batch.ownership_record} records another last commit for {original}: git says {last}")
        hard(entry.get("target_sha256") == sha(root / target) == entry.get("source_sha256") and entry.get("size") == (root / target).stat().st_size,
             f"{batch.ownership_record} entry differs from the live resource: {target}")
        hard(target not in start or target in (ownership or {}).get("replaced_target_files", []), f"an imported resource replaces a start file the record does not list as replaced: {target}")
    if ownership is not None:
        hard(ownership.get("source_commit") == source_head, f"{batch.ownership_record} is not recorded at the original {source_head[:9]}")

    # 5. features.json: groups are kept, evidence only grows, every changed path is mapped.
    features = read_json(root / FEATURES)["features"]
    by_id = {feature.get("id"): feature for feature in features}
    start_features_data = start_bytes(batch, base, FEATURES)
    start_features = {feature.get("id"): feature for feature in json.loads(start_features_data.decode("utf-8-sig"))["features"]} if start_features_data else {}
    need(start_features_data is not None, "no reproducible start bytes for " + FEATURES)
    kept = [name for name in by_id if name in start_features]
    need(set(start_features) <= set(by_id), "features.json lost start groups: " + str(sorted(set(start_features) - set(by_id))))
    moved = sorted(name for name in kept if by_id[name].get("reviewed_source_commit") not in (source_head, start_features[name].get("reviewed_source_commit")))
    need(not moved, f"features.json groups whose reviewed_source_commit is neither their start value nor {source_head[:9]}: {moved}")
    status_changed = sorted(name for name in kept if by_id[name].get("status") != start_features[name].get("status"))
    need(set(status_changed) <= set(manifest["status_changes"]), "features.json groups changed status without being in status_changes: " + str(status_changed))
    free = ("notes", "target_watch", "target_paths", "reviewed_source_commit", "source_paths", "source_watch", "evidence", "acceptance", "status")
    other_fields = sorted(name for name in kept if {k: v for k, v in by_id[name].items() if k not in free} != {k: v for k, v in start_features[name].items() if k not in free})
    shrunk = sorted(name for name in kept if not set(start_features[name].get("target_watch", [])) <= set(by_id[name].get("target_watch", [])))
    rewritten = sorted(name for name in kept if not all(by_id[name].get(key, [])[:len(start_features[name].get(key, []))] == start_features[name].get(key, []) for key in ("evidence", "acceptance")))
    need(not shrunk and not other_fields and not rewritten, f"features.json groups lost target_watch entries {shrunk}, changed other fields {other_fields} or changed evidence / acceptance other than by appending {rewritten}")
    unmapped = sorted(path for path, change in changes.items() if change != "deleted" and (path.startswith(("src/", "data/")) or path in BUILD_FILES)
                      and ".cache" not in path.split("/") and path != STAMP and not any(feature_matches(feature, "target", path) for feature in features))
    need(not unmapped, "features.json maps these changed paths in no group (compare would report them unmapped): " + str(unmapped[:8]))
    absent = sorted({path for feature in features for path in feature.get("source_paths", []) if not (batch.source / path).is_file()})
    need(not absent, f"features.json source_paths missing in the original: {absent[:6]}")
    snapshot_path, snapshot = root / manifest["snapshot"], None
    if need(snapshot_path.is_file(), "observation snapshot missing: " + manifest["snapshot"]):
        snapshot = read_json(snapshot_path)
        need(snapshot["kind"] == "observed-snapshot-not-parity-acceptance" and snapshot["source"]["commit"] == source_head and snapshot["source"]["dirty_status"] == "",
             f"{manifest['snapshot']} is not a clean observation of the original at {source_head[:9]}")

    # 6. Language: key deltas against the start; the localization audit checks the mapping, the Chinese and the placeholders.
    language = {}
    texts = {path: start_bytes(batch, base, path) for path in (EN, ZH, ZH_MAP)}
    if need(all(data is not None for data in texts.values()), "no reproducible start bytes for a language file: " + str(sorted(p for p, d in texts.items() if d is None))):
        def delta(old, new):
            return {"added": sorted(set(new) - set(old)), "removed": sorted(set(old) - set(new)), "changed": sorted(k for k in set(old) & set(new) if old[k] != new[k])}
        en_now, zh_now, map_now = read_json(root / EN), read_json(root / ZH), read_json(root / ZH_MAP)["entries"]
        en_delta = delta(json.loads(texts[EN].decode("utf-8-sig")), en_now)
        zh_delta = delta(json.loads(texts[ZH].decode("utf-8-sig")), zh_now)
        map_delta = delta(json.loads(texts[ZH_MAP].decode("utf-8-sig"))["entries"], map_now)
        need(manifest["language_keys_removed"] or not (en_delta["removed"] or zh_delta["removed"] or map_delta["removed"]),
             f"language keys were removed since the start: en {en_delta['removed'][:4]} zh {zh_delta['removed'][:4]} map {map_delta['removed'][:4]}")
        need(set(en_delta["added"]) <= set(zh_now) and set(zh_delta["added"]) <= set(en_now),
             f"a new English key has no Chinese text, or a new Chinese key has no English key: en only {sorted(set(en_delta['added']) - set(zh_now))[:4]}, zh only {sorted(set(zh_delta['added']) - set(en_now))[:4]}")
        unrecorded = sorted(key for key in en_delta["added"] if (map_now.get(key) or {}).get("kind") not in ("local", "upstream"))
        need(not unrecorded, "a new English key has no localization record entry of kind local or upstream: " + str(unrecorded[:4]))
        need(not [key for key in en_delta["changed"] if key not in zh_now], "a changed English key has no Chinese text")
        language = {"delta": {"en_us": en_delta, "zh_cn": zh_delta, "zh_cn_map": map_delta},
                    "totals": {"en_us": len(en_now), "zh_cn": len(zh_now), "zh_cn_map": len(map_now), "zh_cn_map_by_kind": dict(Counter(e.get("kind") for e in map_now.values()))}}

    # 7. Generation stamp: current, and every Java source outside com/hbm/gametest/ is among its inputs.
    stamp = read_json(root / STAMP)
    stale = sorted(path for path, digest in stamp["inputs"].items() if not path.startswith(GAMETESTS) and (not (root / path).is_file() or stamp_sha(root / path) != digest))
    mismatch = sorted(path for path, digest in stamp["generated"].items() if not (root / GENERATED / path).is_file() or stamp_sha(root / GENERATED / path) != digest)
    java_now = {batch.rel(path) for path in (root / SRC).rglob("*.java") if not batch.rel(path).startswith(GAMETESTS)}
    unrecorded_java = sorted(java_now - set(stamp["inputs"]))
    need(not stale and not mismatch and not unrecorded_java, f"{STAMP} is not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, Java sources outside com/hbm/gametest/ not among the inputs {unrecorded_java[:5]}")
    start_generated = {path[len(GENERATED):] for path in start if path.startswith(GENERATED) and path != STAMP}
    generated_added = sorted(set(stamp["generated"]) - start_generated)
    generated_retired = sorted(start_generated - set(stamp["generated"]))
    generated_changed = sorted(path for path in start_generated if path in stamp["generated"] and start[GENERATED + path] != sha(root / GENERATED / path))
    need({GENERATED + path for path in generated_retired} <= set(manifest["deleted"]), f"generated resources retired since the start that deleted does not list: {generated_retired[:5]}")
    generated_since = sorted(path for path in changes if path.startswith(GENERATED) and path != STAMP)
    need(generated_since == sorted(GENERATED + path for path in generated_added + generated_changed + generated_retired),
         "files under src/generated/resources changed since the start are not what the stamp records (run runData): " + str(sorted(set(generated_since) ^ {GENERATED + p for p in generated_added + generated_changed + generated_retired})[:8]))

    # 8. The final chain and the GameTest run.
    evidence, final = {}, batch.final
    exits = read_exits(final / "chain-exits.txt")
    required = required_chain(batch, tools_changed)
    need(bool(exits) and set(required) <= set(exits) and all(exits.get(name) == "0" for name in required),
         "final chain: missing or failed steps " + str({name: exits.get(name) for name in required if exits.get(name) != "0"}))
    need((final / "chain-done.txt").is_file(), "final/chain-done.txt is missing (the chain did not finish)")
    logs = [log for _, log, _, _ in chain_steps(batch, tools_changed)] + ["jar.sha256"] + [output for _, _, output in RECORD_STEPS if output]
    for name in logs:
        if need((final / name).is_file(), f"evidence missing: {batch.rel(final / name)} (written by `batch.py chain`)"):
            evidence[batch.rel(final / name)] = sha(final / name)
    for name in ("rundata.log", "build.log"):
        if (final / name).is_file():
            need("BUILD SUCCESSFUL" in (final / name).read_text(encoding="utf-8-sig", errors="replace"), f"final/{name} is not a successful Gradle run")
    if (final / "jar.sha256").is_file() and batch.jar.is_file():
        need((final / "jar.sha256").read_text(encoding="utf-8").split()[:1] == [sha(batch.jar)], "the build/libs JAR differs from final/jar.sha256 (it changed after the chain built it)")
    audit_summaries = {}
    for _, _, name in RECORD_STEPS:
        if name and (final / name).is_file():
            audit = read_json(final / name)
            bad = [finding for finding in audit["findings"] if finding.get("severity", "").lower() in ("error", "warning")]
            need(not bad and audit["summary"]["error"] == 0 and audit["summary"]["warning"] == 0, f"failed audit {name}: {bad[:3]}")
            audit_summaries[name] = audit["summary"]
    prior_audits = prior_receipt.get("audits", {})
    audit_comparison = {name: {"previous": prior_audits.get(name), "now": summary, "equal": summary == prior_audits.get(name)} for name, summary in audit_summaries.items()}
    compare = None
    if manifest["compare"]:
        need(read_exits(final / "compare-exit.txt") == {"compare": "0"}, "final/compare-exit.txt is not compare=0 (run `batch.py compare` last, on the settled tree)")
        if need((final / "compare.json").is_file(), "evidence missing: final/compare.json") and snapshot is not None:
            report = read_json(final / "compare.json")
            counts = {side: {key: len(report["changes"][side][key]) for key in ("added", "modified", "removed")} for side in ("source", "target")}
            states = Counter(feature["state"] for feature in report["features"])
            need(report["kind"] == "migration-delta" and report["baseline_source_commit"] == snapshot["source"]["commit"] and report["current_source_commit"] == source_head,
                 "compare.json is not a comparison of the current original against the manifest's snapshot")
            need(report["current_target_state"]["commit"] == start_head, "compare.json records another NEO commit than the start commit")
            need(not any(counts["source"].values()), f"compare.json reports original changes against the snapshot: {counts['source']}")
            need(counts["target"]["removed"] == 0 or bool(manifest["deleted"]), f"compare.json reports removed NEO paths: {report['changes']['target']['removed'][:6]}")
            need(not report["unmapped_changes"]["source"] and not report["unmapped_changes"]["target"], "compare.json reports unmapped changes: " + str(report["unmapped_changes"])[:300])
            need(not report["removed_feature_ids"] and not report["manifest_missing_files"], "compare.json reports removed features or missing mapped files")
            need(len(report["features"]) == len(features) and set(states) <= {"no-observed-file-change", "target-changed"}, f"compare.json feature states are {dict(states)}")
            settled = max((root / path).stat().st_mtime for path in list(java_now) + [FEATURES, STAMP])
            need((final / "compare.json").stat().st_mtime > settled, "compare.json is older than a source file, the stamp or features.json; run `batch.py compare` again")
            compare = {"path": batch.rel(final / "compare.json"), "sha256": sha(final / "compare.json"), "snapshot": manifest["snapshot"], "counts": counts, "feature_states": dict(states)}
            evidence[compare["path"]] = compare["sha256"]
    gametest_files = sorted((root / GAMETESTS).glob("*.java"))
    counts_now = {batch.rel(path): annotations(path) for path in gametest_files}
    counts_start = base.get("gametest_annotations", {})
    total_now = sum(counts_now.values())
    added_tests = {path: count - counts_start.get(path, 0) for path, count in counts_now.items() if count != counts_start.get(path, 0)}
    stray = sorted(path for path in added_tests if path not in manifest["gametests_new"] and path not in manifest["gametests_changed"])
    hard(not counts_start or not stray, "GameTest files whose @GameTest count differs from the start without being owned: " + str(stray))
    tags, markers = {}, {}
    for path in manifest["gametests_new"]:
        if (root / path).is_file():
            text = (root / path).read_text(encoding="utf-8")
            tag = GAMETEST_TAG.search(text)
            tags[path], markers[path] = tag.group(1) if tag else None, sorted(set(GAMETEST_MARKER.findall(text)))
            need(counts_now.get(path, 0) > 0 and tags[path] and markers[path], f'{path} declares no @GameTest, no TAG "[hbm-...]" or no passed("<name>") marker')
    gametest_result = gametest_count = None
    log = (root / (gametest_log or batch.rel(final / "gametest.log"))).resolve()
    if need(log.is_file(), f"the GameTest log does not exist yet: {log}"):
        text = log.read_text(encoding="utf-8-sig", errors="replace")
        found = GAMETEST_PASSED.findall(text)
        if need(bool(found) and "BUILD SUCCESSFUL" in text and "invalid dist" not in text and "NoClassDefFoundError" not in text,
                f'{batch.rel(log)} did not pass cleanly (needs "All N required tests passed" and BUILD SUCCESSFUL, no "invalid dist" or NoClassDefFoundError)'):
            gametest_count = int(found[-1])
            gametest_result = f"All {gametest_count} required tests passed"
            need(gametest_count == total_now, f"the GameTest server ran {gametest_count} tests, the sources hold {total_now} @GameTest methods")
            missing = [f"{tags[path]} {name}" for path in tags if tags[path] for name in markers[path] if f"{tags[path]} {name} passed" not in text]
            need(not missing, 'the GameTest log lacks "<tag> <name> passed" for: ' + str(missing[:8]))
            evidence[batch.rel(log)] = sha(log)
        created = getattr(log.stat(), "st_birthtime", None)
        if need(created is not None, "the platform gives no creation time for the GameTest log"):
            newest = max(((path.stat().st_mtime, batch.rel(path)) for tree in (SRC, RES, GENERATED) for path in (root / tree).rglob("*") if path.is_file() and path.name != ".DS_Store"), default=(0, None))
            need(created > newest[0], f"the GameTest log was created before {newest[1]} was last modified; run the chain again from runGameTestServer (`batch.py chain --from gametest`)")
    for path in sorted(batch.out.rglob("*")):
        if path.is_file() and batch.start_files not in path.parents and "__pycache__" not in path.parts and path.name != ".DS_Store" and not path.name.startswith("package"):
            evidence.setdefault(batch.rel(path), sha(path))

    # 9. The JAR: build/libs equals the build outputs and their sources; every entry that differs from the previous package has an owner.
    jar_delta, dir_delta, entry_owners, classes = None, None, {}, []
    if need(batch.jar.is_file(), "build/libs holds no JAR yet"):
        need(sha(batch.jar) not in (previous_sha, base.get("build_libs_jar_sha256_at_freeze")), f"{batch.rel(batch.jar)} is still the {manifest['previous']} package or the build of the start (run the final chain)")
        classes_root, resources_root = root / "build/classes/java/main", root / "build/resources/main"
        classes = sorted(classes_root.rglob("*.class"))
        with zipfile.ZipFile(batch.jar) as jar, zipfile.ZipFile(batch.previous_jar) as prior:
            names = jar.namelist()
            hard(len(names) == len(set(names)), "duplicate archive entries in the JAR")
            hard(not any(name.startswith(("tools/", "migration/")) or ".cache/" in name or ".migration-stamp" in name for name in names), "tooling in the JAR")
            expected = {path.relative_to(classes_root).as_posix(): path for path in classes}
            expected.update({path.relative_to(resources_root).as_posix(): path for path in sorted(resources_root.rglob("*")) if path.is_file()})
            differs = [name for name, path in expected.items() if name not in names or jar.read(name) != path.read_bytes()]
            extra = sorted({name for name in names if not name.endswith("/")} - set(expected) - {"META-INF/MANIFEST.MF"})
            sources = [path for path in stamp["generated"] if path not in names or not (root / GENERATED / path).is_file() or jar.read(path) != (root / GENERATED / path).read_bytes()]
            sources += [path[len(RES):] for path in changes if path.startswith(RES) and changes[path] != "deleted" and path[len(RES):] != MODS_TOML
                        and (path[len(RES):] not in names or jar.read(path[len(RES):]) != (root / path).read_bytes())]
            need(not differs and not extra and not sources, f"the build/libs JAR differs from build/classes, build/resources or its sources ({len(differs)} entries differ, first {differs[:4]}; "
                 f"{len(extra)} entries have no build output, first {extra[:4]}; {len(sources)} source differences, first {sources[:4]}); run the final chain")
            old_names = {info.filename for info in prior.infolist() if not info.is_dir()}
            new_names = {info.filename for info in jar.infolist() if not info.is_dir()}
            jar_delta = {"added": sorted(new_names - old_names), "removed": sorted(old_names - new_names), "modified": sorted(name for name in old_names & new_names if prior.read(name) != jar.read(name))}
            old_dirs, new_dirs = {info.filename for info in prior.infolist() if info.is_dir()}, {info.filename for info in jar.infolist() if info.is_dir()}
            dir_delta = {"added": sorted(new_dirs - old_dirs), "removed": sorted(old_dirs - new_dirs)}
            previous_classes = sum(1 for name in old_names if name.endswith(".class"))
            javap, unowned_entries = None, []
            for kind, entries in jar_delta.items():
                for name in entries:
                    candidates = [owner_source(name)] if name.endswith(".class") else [RES + name, GENERATED + name]
                    if name == MODS_TOML:
                        candidates.append("gradle.properties")
                    changed = [path for path in candidates if owners.get(path)]
                    held = [path for path in candidates if path in carried and path not in changes]
                    owner, groups, proof = [], [], None
                    if name == "META-INF/MANIFEST.MF" or changed:
                        owner, groups = [batch.name], sorted({group for path in changed for group in owners[path][1]})
                    elif held:
                        owner, groups = [CARRIED_OWNER], sorted({group for path in held for group in carried[path]})
                    elif kind == "modified" and name.endswith(".class") and (root / candidates[0]).is_file() and start.get(candidates[0]) == sha(root / candidates[0]):
                        javap = javap or find_javap()
                        if need(javap is not None, "javap not found (JAVA_HOME, PATH, /usr/libexec/java_home -v 21): a recompiled class that differs only in debug names cannot be proved"):
                            same, detail = class_name_difference(prior.read(name), jar.read(name), javap)
                            if same:
                                owner, proof = [DEBUG_NAME_OWNER], detail
                    if not owner:
                        unowned_entries.append(f"{kind}: {name}")
                    entry_owners[name] = {"change": kind, "owners": owner, "groups": groups, **({"debug_names": proof} if proof else {})}
        hard(not unowned_entries, f"JAR entries that differ from the {manifest['previous']} package without an owner (a class of a source the manifest owns or [carried] lists, "
             "a resource or generated file the manifest owns, or a recompile that differs only in debug names): " + str(unowned_entries[:10]))
        parents = {kind: {"/".join(name.split("/")[:depth]) + "/" for name in jar_delta[kind] for depth in range(1, len(name.split("/")))} for kind in ("added", "removed")}
        need(set(dir_delta["added"]) <= parents["added"] and set(dir_delta["removed"]) <= parents["removed"], "JAR directories changed without an entry in them: " + str(dir_delta))
        changed_classes = {owner_source(name) for kind in jar_delta for name in jar_delta[kind] if name.endswith(".class")}
        for label, paths in (("owned", production), ("carried", [path for path in carried if path.endswith(".java") and path not in changes])):
            silent = sorted(set(paths) - changed_classes)
            if silent:
                notes.append(f"{label} Java sources without a class change against the {manifest['previous']} JAR (a change the compiler does not emit, such as a comment): {silent}")
        for path in production:
            if changes[path] == "added":
                need(path[len(SRC):-len(".java")] + ".class" in jar_delta["added"], f"{path} has no added class in the JAR")
        need({path[len(RES):] for path in identical_imports} <= set(jar_delta["added"]) | set(jar_delta["modified"]), "imported assets missing from the JAR delta")
        class_delta = sum(1 for name in jar_delta["added"] if name.endswith(".class")) - sum(1 for name in jar_delta["removed"] if name.endswith(".class"))
        need(bool(classes) and len(classes) == previous_classes + class_delta, f"compiled class count {len(classes)} is not the {manifest['previous']} JAR count {previous_classes} {class_delta:+d}")

    # 10. Records: the batch's reports exist; the log records name this package.
    reports = sorted({manifest["task_book"]} | {path for path in changes if batch.record_pattern.fullmatch(path) and changes[path] != "deleted"})
    for path in reports:
        need((root / path).is_file(), "record missing: " + path)
    for path in manifest["names_package"]:
        need((root / path).is_file() and batch.release_name in (root / path).read_text(encoding="utf-8-sig", errors="replace"), f"{path} does not name {batch.release_name} yet")

    digest = sha(batch.jar) if batch.jar.is_file() else None
    report_hashes = {path: sha(root / path) for path in reports if (root / path).is_file()}
    receipt = {
        "schema_version": 2, "file": batch.release_name, "bytes": batch.jar.stat().st_size if digest else None, "sha256": digest,
        "status": "partial-unverified", "scope": manifest["scope"], "evidence": manifest["evidence"],
        "radiation_warning": (manifest["radiation_note"] + " " + prior_receipt.get("radiation_warning", "")).strip(),
        "meltdown_warning": (manifest["meltdown_note"] + " " + prior_receipt.get("meltdown_warning", "")).strip(),
        "source_commit": source_head, "source_snapshot": manifest["snapshot"], "target_start_commit": start_head,
        "target_head_at_packaging": state["target_head"], "manifest": {"path": batch.rel(batch.manifest_path) if batch.manifest_path.is_relative_to(root) else str(batch.manifest_path), "sha256": sha(batch.manifest_path)},
        "actual_start": batch.rel(batch.out / "baseline.json"), "actual_start_sha256": sha(batch.out / "baseline.json"),
        "previous_release": previous, "carried": {"groups": manifest["carried"], "hashes": base["carried"]["hashes"]},
        "changed_files": change_list, "production": production, "changed_gametests": {path: reason for path, reason in manifest["gametests_changed"].items() if path in changes},
        "line_endings": line_endings, "imported_resources": imported_facts,
        "features": {"groups": len(by_id), "added_groups": sorted(set(by_id) - set(start_features)), "status_changed": status_changed},
        "language": language, "generated_resource_count": len(stamp["generated"]), "generated_added": generated_added,
        "generated_modified": generated_changed, "generated_retired": generated_retired, "compiled_classes_verified": len(classes),
        "snapshot": {"path": manifest["snapshot"], "sha256": sha(snapshot_path) if snapshot_path.is_file() else None, "source_commit": source_head}, "compare": compare,
        "chain": {"exits": exits, "log_dir": batch.rel(final)},
        "gametest": {"log": batch.rel(log) if log.is_file() else None, "sha256": sha(log) if log.is_file() else None, "result": gametest_result, "tests": gametest_count,
                     "tests_at_start": sum(counts_start.values()) if counts_start else None, "added_tests_by_file": added_tests, "tags": tags, "marker_names": markers, "note": manifest["gametest_note"]},
        "audits": audit_summaries, "audit_comparison": audit_comparison, "jar_delta": jar_delta, "jar_directory_delta": dir_delta, "jar_delta_owners": entry_owners,
        "reports": reports, "report_sha256": report_hashes, "evidence_sha256": {**report_hashes, **evidence}, "notes": notes}
    summary = {"batch": batch.name, "changes_since_start": len(change_list), "production": len(production), "generated_added": len(generated_added),
               "generated_modified": len(generated_changed), "imported_assets": len(imported_facts), "gametest": gametest_result, "gametest_sources": total_now,
               "added_tests_by_file": added_tests, "chain_exits": exits, "jar_delta": {key: len(value) for key, value in (jar_delta or {}).items()},
               "jar_owner_counts": dict(Counter(owner for entry in entry_owners.values() for owner in entry["owners"])), "jar_sha256": digest}
    if check:
        pending, failures = list(dict.fromkeys(pending)), list(dict.fromkeys(failures))
        print(json.dumps(summary, ensure_ascii=False, default=str))
        print(f"Check finished; nothing written. Pending: {len(pending)}. Failures: {len(failures)}" if pending or failures
              else "Check passed; nothing written. Pending: none. Failures: none")
        for label, items in (("FAILURE", failures), ("pending", pending), ("note", notes)):
            for item in items:
                print(f"  {label}: {item}")
        return 1 if failures else 0

    target = batch.release / batch.release_name
    if target.exists() and sha(target) != digest:
        raise MigrationError(f"Refusing to overwrite a different {batch.name} JAR")
    batch.release.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copyfile(batch.jar, target)
    if not sha(target) == digest == sha(batch.jar):
        raise MigrationError("The packaged JAR is not build/libs")
    (batch.release / "SHA256SUMS.txt").write_text(f"{digest}  {target.name}\n", encoding="ascii", newline="\n")
    (batch.release / "release.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, default=str))
    print(f"Packaged {batch.rel(target)} ({digest})")
    for item in notes:
        print(f"  note: {item}")
    return 0


def cmd_verify_delivery(batch: Batch) -> int:
    """What a planner checks before the next batch starts; lists every path changed after the package."""
    root, problems = batch.root, []
    files = {name: batch.release / name for name in (batch.release_name, "SHA256SUMS.txt", "release.json")}
    missing = sorted(name for name, path in files.items() if not path.is_file())
    if missing:
        raise MigrationError(f"{batch.name} is not packaged: {batch.rel(batch.release)} lacks {missing}")
    receipt = read_json(files["release.json"])
    digest = sha(files[batch.release_name])
    if not (digest == receipt["sha256"] and files["SHA256SUMS.txt"].read_bytes() == f"{digest}  {batch.release_name}\n".encode("ascii")):
        problems.append("the release JAR, release.json and SHA256SUMS.txt disagree")
    state = repository_state(batch)
    if state["target_head"] != receipt["target_head_at_packaging"]:
        problems.append(f"the NEO HEAD is {state['target_head']}, the package was made at {receipt['target_head_at_packaging']}")
    if state["source_head"] != receipt["source_commit"] or state["source_status"]:
        problems.append(f"the original is at {state['source_head']}{' and dirty' if state['source_status'] else ''}, the package was made against {receipt['source_commit']}")
    for path in batch.manifest["names_package"]:
        if not (root / path).is_file() or batch.release_name not in (root / path).read_text(encoding="utf-8-sig", errors="replace"):
            problems.append(f"{path} does not name {batch.release_name}")
    task_book = root / batch.manifest["task_book"]
    if not task_book.is_file() or "交付记录" not in task_book.read_text(encoding="utf-8-sig", errors="replace"):
        problems.append(f"{batch.manifest['task_book']} has no 交付记录 section")
    delivered = delivered_tree(batch, receipt)
    now = tree_hashes(root)
    later = sorted(path for path in set(now) | set(delivered) if now.get(path) != delivered.get(path))
    build_libs = sha(batch.jar) if batch.jar.is_file() else None
    print(json.dumps({"batch": batch.name, "sha256": digest, "build_libs_is_the_package": build_libs == digest,
                      "changed_after_the_package": later, "problems": problems}, ensure_ascii=False, indent=2))
    if later:
        print("Paths changed after the package belong in the next batch's [carried] table, attributed by their log lines.")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    sub = parser.add_subparsers(dest="command", required=True)
    commands = {"freeze": "Record the start before the batch's first write", "chain": "Run the final chain",
                "compare": "Run compare against the manifest's snapshot", "package": "Check and package the delivery",
                "verify-delivery": "Check a packaged delivery and list what changed after it"}
    parsers = {}
    for name, text in commands.items():
        parsers[name] = sub.add_parser(name, help=text)
        parsers[name].add_argument("--batch", required=True, help="Batch name, e.g. goal30c")
        parsers[name].add_argument("--manifest", type=Path, help="Default: TARGET/migration/<batch>-batch.toml")
        parsers[name].add_argument("--work-dir", type=Path, help="Default: TARGET/build/migration/<batch>; chain and compare need it under TARGET/build/migration")
    parsers["freeze"].add_argument("--dry", action="store_true", help="Print the start report and write nothing")
    parsers["chain"].add_argument("--from", dest="start_at", choices=("runData", "gametest", "records"), default="runData",
                                  help="gametest: only com/hbm/gametest/ changed; records: only migration/ records changed")
    parsers["package"].add_argument("--check", action="store_true", help="Run every check and write nothing")
    parsers["package"].add_argument("--gametest-log", help="Default: build/migration/<batch>/final/gametest.log")
    args = parser.parse_args(argv)
    try:
        batch = Batch(args.target, args.source, args.batch, args.manifest, args.work_dir)
        if args.command == "freeze":
            return cmd_freeze(batch, args.dry)
        if args.command == "chain":
            return cmd_chain(batch, args.start_at)
        if args.command == "compare":
            return cmd_compare(batch)
        if args.command == "package":
            return cmd_package(batch, args.check, args.gametest_log)
        return cmd_verify_delivery(batch)
    except (MigrationError, OSError, ValueError, KeyError) as exc:
        print(f"Batch step failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
