"""Goal 11D regression: the fluid name in the recipe template export (SerializableRecipe.writeFluidStack).

Goal 11D changes one line (SerializableRecipe.java:389): the writer now writes the fluid's internal name
(FluidType.getInternalName) instead of its language key (getUnlocalizedName), as the original writes getName()
(original SerializableRecipe.java:421-428). The reader is unchanged and has no fallback (the user's decision).

Two Java worlds compile real production classes against the same isolated stand-ins (goal11d_regression/stubs.py: the Goal
11C recipe world extended to the soldering and arc welder tables):

* the production world: the production SerializableRecipe, GenericRecipes, GenericRecipe, ChemicalPlantRecipes,
  AssemblyMachineRecipes, SolderingRecipes and ArcWelderRecipes and the fixture
  com.hbm.inventory.recipes.loader.Goal11DRecipeRegression ("verify": sections 1, 2, 3 and 1r);
* the post-Goal 11C world: the same sources, but SerializableRecipe.java from git 1e29ad29 (the delivered post-Goal 11C
  state), whose run ("export") writes the four recipe templates with the post-Goal 11C writer as the game does.

The Python sections 1t, 3t, 4 and 5 read source text, git and the two exported template sets. Every section reports
"N. name: X checks passed"; a failed check prints "AssertionError in <section> ..." and the run fails at the end. Lines
starting with "info:" are observations, not checks.
"""

from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import uuid

from goal11d_regression.stubs import ARC_WELDER, ASSEMBLY, CHEM_RECIPES, GENERIC_RECIPE, GENERIC_RECIPES, SERIALIZABLE, SOLDERING, TABLES, recipe_stubs
from verify_goal10c import Sections, jdk
from verify_goal3c_recipes import GSON


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL = ORIGINAL_ROOT / "src/main/java/com/hbm"
FIXTURE = Path(__file__).with_name("goal11d_regression")
FIXTURE_CLASS = "com/hbm/inventory/recipes/loader/Goal11DRecipeRegression.java"
OUTPUT = ROOT / "build/migration/goal11d/regression"
# Written only for a run on the real production source (not for mutated copies).
RECIPE_REFERENCE = ROOT / "build/migration/goal11d/recipe-reference"
# The delivered post-Goal 11C commit (Goal 11A-11C committed; Goal 11D is the only uncommitted work).
BASE_COMMIT = "1e29ad29b75108b57f22ba246458d7db2abc6a62"
# The Goal 11D commit (Goal 12A builds on it uncommitted); section 5 compares the two commits.
GOAL11D_COMMIT = "e476f5c1cc75e3679177fa997d7104c581a0491a"
PRODUCTION = (SERIALIZABLE, GENERIC_RECIPES, GENERIC_RECIPE) + TABLES
FLUIDS = "com/hbm/inventory/fluid/Fluids.java"
FLUID_TYPE = "com/hbm/inventory/fluid/FluidType.java"
# Production SerializableRecipe.java:389 before and after Goal 11D (build/migration/goal11d/production.diff).
WRITER_LINE = 389
OLD_LINE = "        writer.value(stack.type.getUnlocalizedName());\t//fluid type"
NEW_LINE = "        writer.value(stack.type.getInternalName());\t//fluid type"
# Goal 12B (build/migration/goal12b/production.diff) adds exactly these two lines to SerializableRecipe.java (the
# CrackingRecipes import and its registration after CentrifugeRecipes); section 5 takes them out before its comparisons.
GOAL12B_LINES = ("import com.hbm.inventory.recipes.CrackingRecipes;", "        recipeHandlers.add(new CrackingRecipes());")
CRACKING = "com/hbm/inventory/recipes/CrackingRecipes.java"
TEMPLATES = {"chemical plant":"_hbmChemicalPlant.json", "assembly machine": "_hbmAssemblyMachine.json",
             "soldering station": "_hbmSoldering.json", "arc welder": "_hbmArcWelder.json"}


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=True).stdout


def base_bytes(path):
    """A file as committed at 1e29ad29 (git stores LF)."""
    return git("show", f"{BASE_COMMIT}:{path}")


def lines(data):
    return data.decode("utf-8").replace("\r\n", "\n").split("\n")


def method(text, signature):
    """The text of a method from its signature line to its closing brace (brace counting; LF text)."""
    start = text.find(signature)
    if start < 0 or text.count(signature) != 1:
        raise AssertionError(f"signature not found once: {signature}")
    depth, i = 0, text.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i + 1]
        i += 1


def original_lines(path):
    return (ORIGINAL / path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").split("\n")


def table_fluids():
    """The Fluids constants the four tables name."""
    text = "\n".join((SOURCE / t).read_text(encoding="utf-8") for t in TABLES)
    return sorted(set(re.findall(r"Fluids\.([A-Z][A-Z_0-9]*)\b", text)))


# ---- Python section 1t: every caller of the writer is covered ---------------------------------------------------------

def callers(check):
    found = []
    for path in sorted(SOURCE.rglob("*.java")):
        rel = path.relative_to(SOURCE).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            if "writeFluidStack(" in line and "public static void writeFluidStack(" not in line:
                found.append((rel, number))
    files = sorted({rel for rel, _ in found})
    # Goal 12B's CrackingRecipes.writeRecipe writes its two outputs with writeFluidStack; that table is not compiled here,
    # verify_goal12b.py section 9 writes and reads its template with the production writer.
    check(files == sorted([GENERIC_RECIPES, SOLDERING, ARC_WELDER, CRACKING]),
          f"writeFluidStack is called only from GenericRecipes, SolderingRecipes and ArcWelderRecipes, all compiled here, and Goal 12B's "
          f"CrackingRecipes (verify_goal12b.py): {found}")
    check(len(found) == 6 and sum(rel == CRACKING for rel, _ in found) == 2,
          f"4 call sites (GenericRecipes inputFluid and outputFluid, one each in the soldering and arc welder tables) and Goal 12B's 2 "
          f"(the cracking outputs): {found}")
    generic = (SOURCE / GENERIC_RECIPES).read_text(encoding="utf-8")
    users = sorted(p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob("*.java")
                   if re.search(r"extends GenericRecipes<", p.read_text(encoding="utf-8", errors="replace")))
    limits = {}
    for user in users:
        text = (SOURCE / user).read_text(encoding="utf-8")
        values = [int(v) for v in re.findall(r"public int (?:input|output)FluidLimit\(\) \{ return (\d+); \}", text)]
        limits[Path(user).stem] = values
    fluid_tables = sorted(name for name, values in limits.items() if any(values))
    check(fluid_tables == ["AssemblyMachineRecipes", "ChemicalPlantRecipes"] and "SerializableRecipe.writeFluidStack(stack, writer)" in generic,
          f"of the GenericRecipes tables only the assembly machine and chemical plant tables have a fluid limit above 0: {limits}")


# ---- Python section 3t: reader and name map unchanged since 1e29ad29, and the names the stand-ins use ------------------

def reader_source(check):
    live = (SOURCE / SERIALIZABLE).read_bytes().decode("utf-8").replace("\r\n", "\n")
    base = base_bytes("src/main/java/" + SERIALIZABLE).decode("utf-8")
    for signature in ("public static FluidStack readFluidStack(JsonArray array) {", "public static FluidStack[] readFluidArray(JsonArray array) {"):
        check(method(live, signature) == method(base, signature), f"{signature.split('(')[0].split()[-1]} is identical to 1e29ad29 (modulo line ends)")
    fluids_live = (SOURCE / FLUIDS).read_text(encoding="utf-8").replace("\r\n", "\n")
    fluids_base = base_bytes("src/main/java/" + FLUIDS).decode("utf-8")
    from_name = method(fluids_live, "public static FluidType fromName(String name) {")
    check(from_name == method(fluids_base, "public static FluidType fromName(String name) {")
          and "FluidType fluid = nameMapping.get(name);" in from_name and "if (fluid == null) fluid = Fluids.NONE;" in from_name,
          "NEO Fluids.fromName (unchanged since 1e29ad29) looks the name up in nameMapping and gives NONE otherwise, without a fallback")
    check(fluids_live.count("nameMapping.put(fluid.getInternalName(), fluid);") == 2 and "nameMapping.put(fluid.getUnlocalizedName()" not in fluids_live,
          "NEO Fluids.registerSelf and register key nameMapping by getInternalName()")
    fluid_type = (SOURCE / FLUID_TYPE).read_text(encoding="utf-8").replace("\r\n", "\n")
    check("public String getInternalName() {\n        return this.stringId;\n    }" in fluid_type
          and "this.stringId = name;" in fluid_type and 'this.unlocalized = "hbmfluid." + name.toLowerCase(Locale.US);' in fluid_type,
          "NEO FluidType: getInternalName() is the constructor name, the language key is \"hbmfluid.\" + the lower-case name (as the stand-in)")
    # The original's writer, reader and name map (expected values come from here).
    ser = original_lines("inventory/recipes/loader/SerializableRecipe.java")
    check("writer.value(stack.type.getName());" in ser[423] and "if(stack.pressure != 0) writer.value(stack.pressure);" in ser[425]
          and "public static void writeFluidStack(FluidStack stack, JsonWriter writer) throws IOException {" in ser[420],
          "original SerializableRecipe.java:421-428: writeFluidStack writes getName(), the amount, and the pressure only when not 0 (:424, :426)")
    check("FluidType type = Fluids.fromName(array.get(0).getAsString());" in ser[401] and "public static FluidStack readFluidStack(JsonArray array) {" in ser[399],
          "original SerializableRecipe.java:400-402: readFluidStack resolves the name with Fluids.fromName")
    ftype = original_lines("inventory/fluid/FluidType.java")
    check("public String getName() {" in ftype[156] and "return this.stringId;" in ftype[157] and "this.stringId = name;" in ftype[60]
          and 'this.unlocalized = "hbmfluid." + name.toLowerCase(Locale.US);' in ftype[62],
          "original FluidType.java:157-159: getName() is the internal name (stringId, :61); the language key is hbmfluid.<lower-case> (:63)")
    ofluids = original_lines("inventory/fluid/Fluids.java")
    check("nameMapping.put(fluid.getName(), fluid);" in ofluids[960] and "public static FluidType fromName(String name) {" in ofluids[979]
          and "FluidType fluid = nameMapping.get(name);" in ofluids[980] and "fluid = Fluids.NONE;" in ofluids[983],
          "original Fluids.java:961 keys nameMapping by getName(); :980-986 fromName gives NONE for any other string")
    # The stand-in FluidType's internal name is the Fluids field name: so it is in NEO and in the original for every fluid
    # the four tables name.
    wanted = table_fluids()
    neo_missing = [f for f in wanted if not re.search(r"\b" + f + r"\s*=\s*new FluidType\(\"" + f + "\"", fluids_live)]
    check(not neo_missing, f"NEO Fluids.java declares each of the {len(wanted)} table fluids as NAME = new FluidType(\"NAME\", ...): missing {neo_missing}")
    ofluids_text = "\n".join(ofluids)
    original_missing = [f for f in wanted if not re.search(r"\b" + f + r"\s*=\s*new FluidType\(\"" + f + "\"", ofluids_text)]
    check(not original_missing, f"the original Fluids.java declares each of them the same way (internal name = field name): missing {original_missing}")
    print(f"info: fluids named by the four tables: {len(wanted)}", flush=True)


# ---- Python section 4: the export delta --------------------------------------------------------------------------------

def ordered(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=lambda pairs: ("object", pairs))


def walk(old, new, trail, diffs):
    """Collects the differing leaves (trail, old, new); a structural difference is a diff of its own."""
    if isinstance(old, tuple) and isinstance(new, tuple):
        if [k for k, _ in old[1]] != [k for k, _ in new[1]]:
            diffs.append((trail, "keys", [k for k, _ in old[1]], [k for k, _ in new[1]]))
            return
        for (key, a), (_, b) in zip(old[1], new[1]):
            walk(a, b, trail + [key], diffs)
    elif isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            diffs.append((trail, "length", len(old), len(new)))
            return
        for i, (a, b) in enumerate(zip(old, new)):
            walk(a, b, trail + [i], diffs)
    elif type(old) is not type(new) or old != new:
        diffs.append((trail, "value", old, new))


def delta(check, production_dir, baseline_dir, counts):
    for label, name in TEMPLATES.items():
        check(label in counts, f"{label}: the production world counted the stacks it wrote (counts.json: {sorted(counts)})")
        old_path, new_path = baseline_dir / name, production_dir / name
        diffs = []
        walk(ordered(old_path), ordered(new_path), [], diffs)
        # A fluid name is element 0 of an entry of inputFluid/outputFluid (GenericRecipes) or of fluid (soldering, arc welder).
        def fluid_name(trail):
            return (len(trail) >= 5 and trail[-3] in ("inputFluid", "outputFluid") and trail[-1] == 0) or \
                   (len(trail) >= 4 and trail[-2] == "fluid" and trail[-1] == 0)
        other = [d for d in diffs if d[1] != "value" or not fluid_name(d[0])]
        check(not other, f"{label}: the new and the post-Goal 11C export differ only in fluid name strings: {other[:5]}")
        wrong = [d for d in diffs if not (isinstance(d[2], str) and isinstance(d[3], str) and re.fullmatch(r"[A-Z][A-Z_0-9]*", d[3])
                                         and d[2] == "hbmfluid." + d[3].lower())]
        check(not wrong, f"{label}: each old value is the language key hbmfluid.<lower-case> of the new internal name: {wrong[:5]}")
        check(len(diffs) == counts[label]["stacks"],
              f"{label}: one changed name per fluid stack ({len(diffs)} changed, {counts[label]['stacks']} stacks written)")
        old_text, new_text = old_path.read_text(encoding="utf-8"), new_path.read_text(encoding="utf-8")
        replaced = old_text
        for internal in sorted({d[3] for d in diffs}):
            replaced = replaced.replace(json.dumps("hbmfluid." + internal.lower()), json.dumps(internal))
        check(replaced == new_text, f"{label}: text level: the post-Goal 11C file with each key replaced by its name is the new file, "
                                    "order and formatting included")
        names = sorted({d[3] for d in diffs})
        print(f"info: {label} ({name}): {len(diffs)} fluid names changed, {len(names)} distinct fluids, "
              f"e.g. {[(d[2], d[3]) for d in diffs[:2]]}", flush=True)


# ---- Python section 5: the production diff ------------------------------------------------------------------------------

def production_diff(check):
    data = (SOURCE / SERIALIZABLE).read_bytes()
    check(data.count(b"\n") == data.count(b"\r\n") > 0, "SerializableRecipe.java keeps CRLF line ends throughout")
    live, base = lines(data), lines(base_bytes("src/main/java/" + SERIALIZABLE))
    # Goal 12B: the two added lines (GOAL12B_LINES), each exactly once, are taken out; everything below compares the rest.
    check(all(live.count(line) == 1 for line in GOAL12B_LINES), f"Goal 12B: SerializableRecipe.java holds each of its two added lines once: {GOAL12B_LINES}")
    live = [line for line in live if line not in GOAL12B_LINES]
    differing = [i + 1 for i in range(max(len(live), len(base))) if (live[i] if i < len(live) else None) != (base[i] if i < len(base) else None)]
    check(len(live) == len(base) and differing == [WRITER_LINE], f"SerializableRecipe.java differs from 1e29ad29 in exactly line {WRITER_LINE}: {differing[:10]}")
    check(base[WRITER_LINE - 1] == OLD_LINE and live[WRITER_LINE - 1] == NEW_LINE,
          f"line {WRITER_LINE}: getUnlocalizedName() -> getInternalName(), comment and whitespace kept: {live[WRITER_LINE - 1]!r}")
    # The real tree (a mutation run's SOURCE copy is checked through the line above). Goal 12A (migration/GOAL12A.md) changes
    # further files on top of the Goal 11D commit, so the Goal 11D set is checked between the commits: 1e29ad29 -> e476f5c1
    # (Goal 11D) changes exactly SerializableRecipe.java under src/main/java and src/main/resources, and the working copy
    # of SerializableRecipe.java is still the e476f5c1 file (git sees no difference; the blob is the CRLF checkout with LF).
    changed = git("diff", "--name-only", BASE_COMMIT, GOAL11D_COMMIT, "--", "src/main/java", "src/main/resources").decode("utf-8").split()
    check(changed == ["src/main/java/" + SERIALIZABLE],
          f"between 1e29ad29 and the Goal 11D commit {GOAL11D_COMMIT[:8]} no other file under src/main/java or src/main/resources changed (git diff: {changed})")
    worktree = git("diff", "--name-only", GOAL11D_COMMIT, "--", "src/main/java/" + SERIALIZABLE).decode("utf-8").split()
    committed = git("show", f"{GOAL11D_COMMIT}:src/main/java/{SERIALIZABLE}")
    # Goal 12B changes the working copy by exactly its two lines (git now lists the file); without them it is the commit.
    working = (ROOT / "src/main/java" / SERIALIZABLE).read_bytes().replace(b"\r\n", b"\n")
    for line in GOAL12B_LINES:
        working = working.replace(line.encode("utf-8") + b"\n", b"", 1) if working.count(line.encode("utf-8") + b"\n") == 1 else b""
    check(worktree == ["src/main/java/" + SERIALIZABLE] and working == committed,
          f"the working copy of SerializableRecipe.java without the two Goal 12B lines is byte-identical to {GOAL11D_COMMIT[:8]} "
          f"(modulo the CRLF checkout): {worktree}")


def main():
    java_bin, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 11D transcript: {log}", flush=True)
    failed = []

    def run(label, command, stage_failure_ok=False):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                         f"stderr:\n{result.stderr}\n")
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            print(result.stderr, file=sys.stderr, flush=True)
            if not stage_failure_ok:
                raise SystemExit(result.returncode)
            failed.append(label)
            return False
        print(f"{label}: passed", flush=True)
        return True

    def write_sources(root, stubs, extra):
        paths = []
        for stub, content in stubs.items():
            path = root / "stubs" / stub
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content + "\n", encoding="utf-8")
            paths.append(str(path))
        paths.extend(str(p) for p in extra)
        sources = root / "sources.txt"
        # An argument file keeps the command under the Windows length limit when SOURCE is a long temporary copy.
        sources.write_text("".join(f'"{Path(path).as_posix()}"\n' for path in paths), encoding="utf-8")
        classes = root / "classes"
        classes.mkdir()
        return sources, classes

    stubs = recipe_stubs(SOURCE)
    overlap = sorted(set(stubs) & set(PRODUCTION))
    if overlap:
        raise SystemExit(f"Production sources shadowed by stand-ins in the recipe world: {overlap}")
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java_bin}\nsource: {SOURCE}\nbaseline: git {BASE_COMMIT} {SERIALIZABLE}\n"
                     "production sources:\n" + "".join(f"  {source}\n" for source in PRODUCTION))

    # ---- Post-Goal 11C world: the delivered SerializableRecipe (git 1e29ad29) with the same tables and stand-ins ----
    post = run_dir / "post-g11c"
    base_source = post / "baseline" / SERIALIZABLE
    base_source.parent.mkdir(parents=True)
    base_source.write_bytes(base_bytes("src/main/java/" + SERIALIZABLE))
    psources, pclasses = write_sources(post, stubs, [base_source] + [SOURCE / p for p in PRODUCTION if p != SERIALIZABLE] + [FIXTURE / FIXTURE_CLASS])
    run("Compile the post-Goal 11C recipe world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                                   "-cp", str(GSON), "-d", str(pclasses), f"@{psources}"])
    baseline_templates = post / "templates"
    run("Export the post-Goal 11C templates", [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{pclasses};{GSON}",
                                               "com.hbm.inventory.recipes.loader.Goal11DRecipeRegression", "export", str(baseline_templates)])

    # ---- Production world (sections 1, 2, 3, 1r) ----
    production = run_dir / "production"
    sources, classes = write_sources(production, stubs, [SOURCE / p for p in PRODUCTION] + [FIXTURE / FIXTURE_CLASS])
    run("Compile the Goal 11D recipe world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                              "-cp", str(GSON), "-d", str(classes), f"@{sources}"])
    out = production / "out"
    out.mkdir()
    exported = run_dir / "recipe-reference"
    passed = run("Run Goal 11D recipe world (sections 1, 2, 3, 1r)",
                 [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{classes};{GSON}", "com.hbm.inventory.recipes.loader.Goal11DRecipeRegression",
                  "verify", str(out), str(baseline_templates), str(exported)], stage_failure_ok=True)
    if SOURCE == ROOT / "src/main/java" and passed:
        RECIPE_REFERENCE.mkdir(parents=True, exist_ok=True)
        for file in sorted(exported.glob("*.recipe.json")):
            shutil.copyfile(file, RECIPE_REFERENCE / file.name)
            target = RECIPE_REFERENCE / file.name
            print(f"recipe reference: {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}", flush=True)

    sections = Sections()
    sections.run("1t. every caller of the writer is covered", callers)
    sections.run("3t. reader and name map unchanged; the names the stand-ins use", reader_source)
    counts_file = out / "counts.json"
    if counts_file.is_file():
        counts = json.loads(counts_file.read_text(encoding="utf-8"))
        sections.run("4. delta of the export", lambda check: delta(check, out / "production", baseline_templates, counts))
    else:
        print("AssertionError in 4. delta of the export after 0 passed checks: the production world wrote no counts.json", flush=True)
        sections.failures.append("4. delta of the export: no counts.json")
    sections.run("5. production diff", production_diff)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 11D Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 11D regression failed: {failed}")


if __name__ == "__main__":
    main()
