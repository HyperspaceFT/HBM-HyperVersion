"""Verify the ZIRNOX parity fixes recorded after Goal19C (GOAL19C.md "范围外发现", goal19c-static-review.md "范围外的既有问题").

Read-only for both worktrees. Writes only a unique build/migration/review-fixes/zirnox-parity/verify/<id> run directory.
No game, Gradle or network.

- Static: original block hardness/resistance, wreck drops, proxy flags and wreck NBT keys parsed from the read-only original;
  the NEO registrations, providers, generated loot table and pickaxe tag, the generated-tree delta from the frozen start,
  untouched language files, and the stamp.
- Isolated: the production ZirnoxDestroyedBlockEntity field and updateEntity/loadAdditional/saveAdditional bodies verbatim
  over stand-ins (review_fixes/ZirnoxParityRegression.java), compiled and run with the existing JDK 21.
- Mutations: every static check and the isolated regression must reject an anchored regression; the frozen start form of
  the block entity must fail the regression.

python -B -X utf8 tools/migration/verify_review_zirnox_parity.py [--jar build/libs/hbmsntm-198A.jar]
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_fixes.block_stubs import method
from verify_goal9b import jdk

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
BATCH = ROOT / "build/migration/review-fixes/zirnox-parity"
START = BATCH / "baseline-files"
CACHE = ROOT / ".gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar"
FIXTURE = ROOT / "tools/migration/review_fixes/ZirnoxParityRegression.java"
ORIGINAL_HEAD = "d31426cbd97ade3bdd852617413f22c23be4fd82"

BE = "com/hbm/blockentity/machine/ZirnoxDestroyedBlockEntity.java"
BLOCKS = "com/hbm/blocks/NtmBlocks.java"
WRECK_BLOCK = "com/hbm/blocks/machine/ZirnoxDestroyedBlock.java"
REACTOR_BLOCK = "com/hbm/blocks/machine/ReactorZirnoxBlock.java"
LOOT = "com/hbm/datagen/NtmBlockLootTableProvider.java"
TAGS = "com/hbm/datagen/NtmBlockTagProvider.java"
ITEMS = "com/hbm/items/NtmItems.java"
PRODUCTION = (BE, BLOCKS, WRECK_BLOCK, REACTOR_BLOCK, LOOT, TAGS, ITEMS)
GEN_LOOT = "data/hbmsntm/loot_table/blocks/zirnox_destroyed.json"
GEN_REACTOR_LOOT = "data/hbmsntm/loot_table/blocks/machine_zirnox.json"
GEN_PICKAXE = "data/minecraft/tags/block/mineable/pickaxe.json"
GEN_STAMP = ".migration-stamp.json"
LANG = ("src/generated/resources/assets/hbmsntm/lang/en_us.json", "src/main/resources/assets/hbmsntm/lang/zh_cn.json")
# The stamp hashes these suffixes with normalized line endings (same set as the batch freeze script).
TEXT = {".cfg", ".csv", ".fsh", ".gradle", ".java", ".json", ".lang", ".mcmeta", ".md", ".mtl", ".obj", ".properties", ".py", ".toml", ".txt", ".vsh", ".xml", ".yaml", ".yml"}

# Original ZirnoxDestroyed.getDrops stack -> NEO item id; None = no NEO item yet (deferred, must stay unregistered here).
DROP_MAP = {
    ("ModBlocks.concrete_smooth", None): "hbmsntm:concrete_smooth",
    ("ModItems.pipe", "Mats.MAT_STEEL.id"): "hbmsntm:pipe_steel",
    ("ModBlocks.steel_grate", None): "hbmsntm:steel_grate",
    ("ModItems.debris_metal", None): None,
    ("ModItems.debris_graphite", None): None,
    ("ModItems.fallout", None): None,
}
DEFERRED_IDS = {"ModItems.debris_metal": "debris_metal", "ModItems.debris_graphite": "debris_graphite", "ModItems.fallout": "fallout"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm_sha(path):
    data = path.read_bytes()
    if path.suffix.lower() in TEXT:
        try:
            data = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return sha(data)


def read(path):
    return path.read_text(encoding="utf-8")


class Checks:
    def __init__(self):
        self.count = 0

    def __call__(self, condition, label):
        self.count += 1
        if not condition:
            raise AssertionError(label)


# ---------------------------------------------------------------- original facts (read-only)

def original_facts():
    head = subprocess.check_output(["git", "-c", "safe.directory=" + ORIGINAL.as_posix(), "rev-parse", "HEAD"], cwd=ORIGINAL).decode().strip()
    # --no-optional-locks: status must not refresh the original repository's index.
    status = subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + ORIGINAL.as_posix(), "status", "--porcelain=v1"], cwd=ORIGINAL).decode()
    assert head == ORIGINAL_HEAD and status == "", (head, status)
    mod_blocks = read(ORIGINAL / "src/main/java/com/hbm/blocks/ModBlocks.java")
    strength = {}
    for field, name in (("reactor_zirnox", "machine_zirnox"), ("zirnox_destroyed", "zirnox_destroyed")):
        m = re.search(r"\t\t%s = new \w+\(Material\.iron\)\.setBlockName\(\"%s\"\)\.setHardness\(([\d.]+)F\)\.setResistance\(([\d.]+)F\)" % (field, name), mod_blocks)
        assert m, field
        strength[name] = (float(m.group(1)), float(m.group(2)))
    wreck = read(ORIGINAL / "src/main/java/com/hbm/blocks/machine/ZirnoxDestroyed.java")
    drops = [(item, meta, int(count)) for item, count, meta in
             re.findall(r"drops\.add\(new ItemStack\(([\w.]+), (\d+)(?:, ([\w.]+))?\)\);", method(wreck, "public ArrayList<ItemStack> getDrops("))]
    drops = [(item, meta or None, count) for item, meta, count in drops]
    reactor = read(ORIGINAL / "src/main/java/com/hbm/blocks/machine/ReactorZirnox.java")

    def proxy(text):
        m = re.findall(r"if\(meta >= 6\)\s*return new TileEntityProxyCombo\((\w+), (\w+), (\w+)\);", text)
        assert len(m) == 1, m
        return dict(zip(("inventory", "power", "fluid"), (v == "true" for v in m[0])))

    te = read(ORIGINAL / "src/main/java/com/hbm/tileentity/machine/TileEntityZirnoxDestroyed.java")
    keys = dict(read=re.findall(r'onFire = nbt\.getBoolean\("(\w+)"\);', te), write=re.findall(r'nbt\.setBoolean\("(\w+)", onFire\);', te))
    return dict(head=head, strength=strength, drops=drops, proxy=dict(zirnox_destroyed=proxy(wreck), machine_zirnox=proxy(reactor)), nbt_keys=keys)


# ---------------------------------------------------------------- static checks over NEO text

def check_strength(check, facts, blocks):
    for name, (hardness, resistance) in facts["strength"].items():
        m = re.findall(r'register\("%s", \(\) -> new \w+\(BlockBehaviour\.Properties\.of\(\)[^;]*?\.strength\(([\d.]+)F, ([\d.]+)F\)' % name, blocks)
        check(len(m) == 1, f"{name}: one registration with strength(...)")
        check((float(m[0][0]), float(m[0][1])) == (hardness, resistance), f"{name}: strength {m[0]} equals original hardness/resistance {(hardness, resistance)}")
        line = next(l for l in blocks.splitlines() if f'register("{name}"' in l)
        check("requiresCorrectToolForDrops" not in line, f"{name}: drop-tool requirement unchanged (not part of this batch)")


def proxy_chain(text, cls):
    m = re.findall(r"case EXTRA -> new ProxyComboBlockEntity\(pos, state\)((?:\.\w+\(\))*);", text)
    assert len(m) == 1, (cls, m)
    return re.findall(r"\.(\w+)\(\)", m[0])


def check_proxy(check, facts, wreck_block, reactor_block):
    for name, text in (("zirnox_destroyed", wreck_block), ("machine_zirnox", reactor_block)):
        flags = facts["proxy"][name]
        chain = proxy_chain(text, name)
        check(chain == [k for k in ("inventory", "power", "fluid") if flags[k]], f"{name}: proxy chain {chain} matches original {flags}")


def check_nbt_source(check, facts, be):
    check(facts["nbt_keys"] == {"read": ["fire"], "write": ["onFire"]}, "original reads fire and writes onFire (the recorded upstream bug)")
    load = method(be, "protected void loadAdditional(")
    save = method(be, "protected void saveAdditional(")
    check(re.findall(r'tag\.putBoolean\("(\w+)"', save) == ["onFire"], "NEO writes only onFire")
    check(re.findall(r'tag\.(?:contains|getBoolean)\("(\w+)"\)', load) == ["onFire", "onFire", "fire", "fire"], "NEO reads onFire first, fire as fallback")


def loot_entries(table):
    entries = []
    for pool in table["pools"]:
        assert pool["rolls"] == 1.0 and pool["bonus_rolls"] == 0.0, pool
        assert pool.get("conditions") == [{"condition": "minecraft:survives_explosion"}], pool
        assert len(pool["entries"]) == 1, pool
        entry = pool["entries"][0]
        assert entry["type"] == "minecraft:item" and set(entry) == {"type", "name", "functions"}, entry
        assert entry["functions"] == [{"add": False, "count": entry["functions"][0]["count"], "function": "minecraft:set_count"}], entry
        entries.append((entry["name"], entry["functions"][0]["count"]))
    return entries


def check_loot(check, facts, table, reactor_table, items, provider):
    check(facts["drops"] and set((i, m) for i, m, _ in facts["drops"]) == set(DROP_MAP), f"original drop list mapped: {facts['drops']}")
    expected = [(DROP_MAP[(i, m)], float(c)) for i, m, c in facts["drops"] if DROP_MAP[(i, m)]]
    try:
        entries = loot_entries(table)
    except (AssertionError, KeyError, IndexError) as error:
        raise AssertionError(f"wreck loot pool shape: {error}")
    check(table["type"] == "minecraft:block" and table["random_sequence"] == "hbmsntm:blocks/zirnox_destroyed", "wreck loot type and sequence")
    check(entries == expected, f"wreck loot {entries} equals the original stacks NEO has {expected}")
    check(all(name != "hbmsntm:zirnox_destroyed" for name, _ in entries), "the wreck no longer drops itself")
    for symbol, item_id in DEFERRED_IDS.items():
        check(f'register("{item_id}"' not in items, f"{item_id}: still no NEO item; when one is added, port its {symbol} wreck drop")
    reactor = [e["name"] for p in reactor_table["pools"] for e in p["entries"]]
    check(reactor == ["hbmsntm:machine_zirnox"], "the reactor still drops itself")
    check("this.dropSelf(NtmBlocks.ZIRNOX_DESTROYED.get());" not in provider, "provider no longer dropSelfs the wreck")


def check_tag(check, pickaxe, start_pickaxe):
    values, before = pickaxe["values"], start_pickaxe["values"]
    for block in ("hbmsntm:machine_zirnox", "hbmsntm:zirnox_destroyed"):
        check(values.count(block) == 1 and block not in before, f"{block}: newly in mineable/pickaxe once")
    check([v for v in values if v not in ("hbmsntm:machine_zirnox", "hbmsntm:zirnox_destroyed")] == before, "pickaxe tag otherwise unchanged and in order")


def static_suite(facts, texts, generated):
    check = Checks()
    check_strength(check, facts, texts[BLOCKS])
    check_proxy(check, facts, texts[WRECK_BLOCK], texts[REACTOR_BLOCK])
    check_nbt_source(check, facts, texts[BE])
    check_loot(check, facts, generated["loot"], generated["reactor_loot"], texts[ITEMS], texts[LOOT])
    check_tag(check, generated["pickaxe"], generated["start_pickaxe"])
    return check.count


# ---------------------------------------------------------------- generated tree, stamp, language, contracts

def tree_delta(check):
    start_files = {p.relative_to(START / "src/generated/resources").as_posix() for p in (START / "src/generated/resources").rglob("*") if p.is_file()}
    now_files = {p.relative_to(GENERATED).as_posix() for p in GENERATED.rglob("*") if p.is_file()}
    check(start_files == now_files, f"no generated file added or removed: +{sorted(now_files - start_files)} -{sorted(start_files - now_files)}")
    changed = sorted(p for p in now_files if (GENERATED / p).read_bytes() != (START / "src/generated/resources" / p).read_bytes())
    check(changed == sorted([GEN_LOOT, GEN_PICKAXE, GEN_STAMP]), f"generated delta is exactly the wreck loot, the pickaxe tag and the stamp: {changed}")
    stamp = json.loads(read(GENERATED / GEN_STAMP))
    stale = sorted(p for p, h in stamp["inputs"].items() if not (ROOT / p).is_file() or norm_sha(ROOT / p) != h)
    java = {p.relative_to(ROOT).as_posix() for p in SOURCE.rglob("*.java")}
    check(not stale and java <= set(stamp["inputs"]), f"stamp inputs current: stale {stale[:5]}, unrecorded {sorted(java - set(stamp['inputs']))[:5]}")
    mismatch = sorted(p for p, h in stamp["generated"].items() if norm_sha(GENERATED / p) != h)
    check(not mismatch, f"generated tree matches the stamp: {mismatch[:5]}")
    for lang in LANG:
        check((ROOT / lang).read_bytes() == (START / lang).read_bytes(), f"{lang}: unchanged (no player-facing text changed)")
    return dict(changed_generated=changed, stamp_inputs=len(stamp["inputs"]), stamp_generated=len(stamp["generated"]))


def vanilla_contracts(check):
    records = []
    with zipfile.ZipFile(CACHE) as archive:
        def confirm(path, signature, tokens):
            body = method(archive.read(path).decode("utf-8"), signature)
            for token in tokens:
                check(token in body, f"{path} {signature}: {token}")
            records.append(dict(source=path, signature=signature, tokens=tokens, sha256=sha(body.encode())))
        confirm("net/minecraft/nbt/CompoundTag.java", "public boolean contains(String key) {", ["this.tags.containsKey(key)"])
        confirm("net/minecraft/nbt/CompoundTag.java", "public boolean getBoolean(", ["this.getByte(key) != 0"])
        confirm("net/minecraft/nbt/CompoundTag.java", "public byte getByte(", ["this.contains(key, 99)", "return 0;"])
        confirm("net/minecraft/nbt/CompoundTag.java", "public void putBoolean(", ["ByteTag.valueOf(value)"])
        confirm("net/minecraft/world/level/block/state/BlockBehaviour.java", "public BlockBehaviour.Properties strength(float destroyTime, float explosionResistance)",
                ["this.destroyTime(destroyTime).explosionResistance(explosionResistance)"])
        confirm("net/minecraft/data/loot/BlockLootSubProvider.java", "protected <T extends ConditionUserBuilder<T>> T applyExplosionCondition(",
                ["ExplosionCondition.survivesExplosion()"])
    return records


# ---------------------------------------------------------------- isolated regression

def wreck_world(be_text):
    parts = [re.search(r"\n    (public boolean onFire = true;)\n", be_text).group(1)]
    for signature in ("public void updateEntity() {", "protected void loadAdditional(", "protected void saveAdditional("):
        parts.append(method(be_text, signature))
    body = "\n\n    ".join(parts)
    return ("package reviewfixes;\n\n// Production ZirnoxDestroyedBlockEntity members, verbatim; stand-ins in ZirnoxParityRegression.java.\n"
            "class ReviewedZirnoxWreck extends BlockEntityBase {\n    " + body + "\n}\n")


def run_world(root, label, world, java, javac, expect_success, expect_fragment=None):
    target = root / label
    target.mkdir(parents=True)
    (target / "ReviewedZirnoxWreck.java").write_text(world, encoding="utf-8")
    (target / FIXTURE.name).write_bytes(FIXTURE.read_bytes())
    compile_cmd = [str(javac), "-encoding", "UTF-8", "-d", str(target / "classes"), str(target / "ReviewedZirnoxWreck.java"), str(target / FIXTURE.name)]
    proc = subprocess.run(compile_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (target / "compile.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"compile failed: {target / 'compile.log'}\n{proc.stdout}{proc.stderr}")
    run_cmd = [str(java), "-ea", "-cp", str(target / "classes"), "reviewfixes.ZirnoxParityRegression"]
    proc = subprocess.run(run_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = proc.stdout + proc.stderr
    (target / "run.log").write_text(output, encoding="utf-8")
    if (proc.returncode == 0) != expect_success:
        raise RuntimeError(f"unexpected regression result for {label}: {target / 'run.log'}\n{output}")
    if expect_fragment and expect_fragment not in output:
        raise RuntimeError(f"{label}: failed for another reason than '{expect_fragment}':\n{output}")
    return dict(compile=compile_cmd, run=run_cmd, returncode=proc.returncode, output=output.strip()[:2000])


ISOLATED_MUTATIONS = {
    "read_fire_only": ([('        if(tag.contains("onFire")) this.onFire = tag.getBoolean("onFire");\n        else if(tag.contains("fire")) this.onFire = tag.getBoolean("fire");',
                         '        this.onFire = tag.getBoolean("fire");')], "round trip keeps onFire=true"),
    "no_legacy_fallback": ([('\n        else if(tag.contains("fire")) this.onFire = tag.getBoolean("fire");', '')], "load: legacy fire=false"),
    "absent_resets": ([('if(tag.contains("onFire")) this.onFire', 'if(true) this.onFire')], "load: no key keeps the default"),
    "write_fire": ([('tag.putBoolean("onFire", this.onFire);', 'tag.putBoolean("fire", this.onFire);')], "save writes only the onFire key"),
    "no_set_changed": ([('                this.setChanged();\n', '')], "marks the wreck changed exactly once"),
    "roll_gated_by_fire": ([('this.level.random.nextInt(5000) == 0 && onFire', 'onFire && this.level.random.nextInt(5000) == 0')],
                           "the 1/5000 roll still happens every tick"),
}


def static_mutations(facts, texts, generated):
    def text(path, old, new):
        t = dict(texts)
        assert t[path].count(old) == 1, (path, old)
        t[path] = t[path].replace(old, new)
        return t, generated

    def gen(change):
        g = copy.deepcopy(generated)
        change(g)
        return texts, g

    cases = {
        "reactor_hardness_0.6": text(BLOCKS, 'ReactorZirnoxBlock(BlockBehaviour.Properties.of().noOcclusion().strength(5.0F, 100F)',
                                     'ReactorZirnoxBlock(BlockBehaviour.Properties.of().noOcclusion().strength(0.6F, 100F)'),
        "wreck_resistance_100": text(BLOCKS, 'ZirnoxDestroyedBlock(BlockBehaviour.Properties.of().noOcclusion().strength(100.0F, 800.0F)',
                                     'ZirnoxDestroyedBlock(BlockBehaviour.Properties.of().noOcclusion().strength(100.0F, 100F)'),
        "wreck_inventory_proxy": text(WRECK_BLOCK, "new ProxyComboBlockEntity(pos, state).power().fluid();",
                                      "new ProxyComboBlockEntity(pos, state).inventory().power().fluid();"),
        "reactor_no_inventory_proxy": text(REACTOR_BLOCK, "new ProxyComboBlockEntity(pos, state).inventory().power().fluid();",
                                           "new ProxyComboBlockEntity(pos, state).power().fluid();"),
        "nbt_read_fire_only": text(BE, '        else if(tag.contains("fire")) this.onFire = tag.getBoolean("fire");\n', ''),
        "provider_drop_self": text(LOOT, "this.add(NtmBlocks.ZIRNOX_DESTROYED.get(), block -> LootTable.lootTable()",
                                   "this.dropSelf(NtmBlocks.ZIRNOX_DESTROYED.get());\n        this.add(NtmBlocks.ZIRNOX_DESTROYED.get(), block -> LootTable.lootTable()"),
        "deferred_item_registered": text(ITEMS, 'ITEMS.register("pipe_steel"', 'ITEMS.register("debris_metal", null); ITEMS.register("pipe_steel"'),
        "loot_count_5": gen(lambda g: g["loot"]["pools"][0]["entries"][0]["functions"][0].update(count=5.0)),
        "loot_missing_grate": gen(lambda g: g["loot"]["pools"].pop()),
        "loot_no_explosion_condition": gen(lambda g: g["loot"]["pools"][1].pop("conditions")),
        "loot_drop_self": gen(lambda g: g["loot"]["pools"][0]["entries"][0].update(name="hbmsntm:zirnox_destroyed")),
        "pickaxe_missing_wreck": gen(lambda g: g["pickaxe"]["values"].remove("hbmsntm:zirnox_destroyed")),
        "pickaxe_reordered": gen(lambda g: g["pickaxe"]["values"].reverse()),
    }
    results = {}
    for label, (t, g) in cases.items():
        try:
            static_suite(facts, t, g)
        except AssertionError as error:
            results[label] = f"rejected: {error}"[:300]
            continue
        raise RuntimeError(f"static mutation not detected: {label}")
    return results


def check_jar(check, jar):
    with zipfile.ZipFile(jar) as archive:
        for path in (GEN_LOOT, GEN_PICKAXE):
            check(archive.read(path) == (GENERATED / path).read_bytes(), f"JAR {path} equals the generated tree")
        classes = {"com/hbm/blockentity/machine/ZirnoxDestroyedBlockEntity.class", "com/hbm/blocks/machine/ZirnoxDestroyedBlock.class"}
        check(classes <= set(archive.namelist()), "JAR carries the wreck classes")
        info = archive.getinfo("com/hbm/blockentity/machine/ZirnoxDestroyedBlockEntity.class")
        data = archive.read(info)
        # CONSTANT_Utf8 entries: tag 1, u2 length, bytes.
        check(b"\x01\x00\x06onFire" in data and b"\x01\x00\x04fire" in data, "JAR wreck class carries both NBT key constants")
    return dict(path=str(jar.relative_to(ROOT)), sha256=sha(jar.read_bytes()), bytes=jar.stat().st_size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", type=Path, help="also compare the built JAR's wreck loot, pickaxe tag and classes")
    args = parser.parse_args()
    root = BATCH / "verify" / uuid.uuid4().hex
    root.mkdir(parents=True)
    before = {p: sha((SOURCE / p).read_bytes()) for p in PRODUCTION}
    java, javac = jdk()
    check = Checks()

    facts = original_facts()
    texts = {p: read(SOURCE / p) for p in PRODUCTION}
    generated = dict(loot=json.loads(read(GENERATED / GEN_LOOT)), reactor_loot=json.loads(read(GENERATED / GEN_REACTOR_LOOT)),
                     pickaxe=json.loads(read(GENERATED / GEN_PICKAXE)),
                     start_pickaxe=json.loads(read(START / "src/generated/resources" / GEN_PICKAXE)))
    static_count = static_suite(facts, texts, generated)
    delta = tree_delta(check)
    contracts = vanilla_contracts(check)
    jar = check_jar(check, ROOT / args.jar if not args.jar.is_absolute() else args.jar) if args.jar else None

    world = wreck_world(texts[BE])
    normal = run_world(root, "normal", world, java, javac, True)
    start_text = read(START / "src/main/java" / BE)
    start_form = run_world(root, "start_form", wreck_world(start_text), java, javac, False, "round trip keeps onFire=true")
    isolated = {}
    for label, (replacements, fragment) in ISOLATED_MUTATIONS.items():
        mutated = world
        for old, new in replacements:
            assert mutated.count(old) == 1, (label, old)
            mutated = mutated.replace(old, new)
        isolated[label] = run_world(root, label, mutated, java, javac, False, fragment)
    statics = static_mutations(facts, texts, generated)

    after = {p: sha((SOURCE / p).read_bytes()) for p in PRODUCTION}
    assert before == after, "production inputs changed during verification"
    report = dict(evidence="static source/generated checks plus an extracted-production-method harness; not Minecraft runtime",
                  original=facts, production_sha256=before, static_checks=static_count, tree_and_contract_checks=check.count,
                  generated=delta, vanilla_contracts=contracts, jar=jar, isolated=normal, start_form_fails=start_form,
                  isolated_mutations={k: next((l for l in v["output"].splitlines() if "AssertionError" in l), "") for k, v in isolated.items()},
                  static_mutations=statics,
                  limitations=["No game, server or world: hardness, mining speed, explosions and loot are checked as data, not played.",
                               "The deferred wreck drops (6 debris_metal, 2 debris_graphite, 4 fallout) have no NEO item.",
                               "Saved wreck proxies keep their stored Inventory=true flag (ProxyComboBlockEntity loads flags from NBT); "
                               "the wreck core has no Container, so it is inert.",
                               "Wreck radiation, fire damage and foam extinguishing remain deferred."])
    (root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(normal["output"].splitlines()[-1])
    print(f"Static checks: {static_count}; tree/contract/JAR checks: {check.count}")
    print(f"Start form rejected; isolated mutations {len(isolated)}/{len(ISOLATED_MUTATIONS)}; static mutations {len(statics)}/{len(statics)}")
    print(f"Evidence: {root.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
