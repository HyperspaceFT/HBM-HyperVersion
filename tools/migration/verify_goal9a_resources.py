"""Audit the Goal 9A anvil entry, water containers, boiler/firebox render tables, reused assets and bilingual text.

Default mode runs after `build.ps1 -Offline runData` and also compares the generated output with the pre-Goal 9A
stamp (build/migration/goal9a/stamp-before-g9a.json). `--source-only` skips the generated-output part, for
environments that cannot run Gradle.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
JAVA = ROOT / "src/main/java"
OUT = ROOT / "build/migration/goal9a"
# Copy of the stamp taken before any Goal 9A source change: 3822 generated files (GOAL9A.md, "起点").
BEFORE_STAMP = OUT / "stamp-before-g9a.json"
BEFORE_COUNT = 3822
# The Goal 8 commit: the last change to AnvilRecipes before Goal 9A, and the commit whose generated en_us.json the
# before-stamp records (checked by hash in full mode).
BASELINE_COMMIT = "1d37f11b"
EN_US = "assets/hbmsntm/lang/en_us.json"
DESC_KEY = "block.hbmsntm.heat_boiler.desc"
DESC_EN = "Large boiler that can boil water or heat up oil.$Requires external heat source.$Heat transfer rate: ΔT*0.1 TU/t"
ZH_EXPECTED = {
    "block.hbmsntm.heat_boiler": "大型锅炉",
    "container.heat_boiler": "大型锅炉",
    DESC_KEY: "可以烧水或加热油的大型锅炉$需要外部热源$传热速率：ΔT*0.1 TU/t",
}
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
# Generation inputs Goal 9A changes: the eleven production Java files and zh_cn.json.
CHANGED_INPUTS = {f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/machine/boiler/AbstractBoilerBlockEntity", "blockentity/machine/boiler/MachineHeatBoilerBlockEntity",
    "blockentity/machine/boiler/MachineIndustrialBoilerBlockEntity", "blockentity/machine/storage/BarrelBlockEntity",
    "blocks/machine/MachineHeatBoiler", "datagen/NtmLanguageProvider", "inventory/FluidContainerRegistry",
    "inventory/fluid/tank/FluidLoaderStandard", "inventory/recipes/anvil/AnvilRecipes",
    "render/blockentity/RenderHeatBoiler", "render/blockentity/RenderHeaterFirebox")} | {ZH}
# The Goal 9A anvil block as written in AnvilRecipes (comment, entry and the blank line after it).
BOILER_ENTRY = """        // Steel ingots by item: NEO has no steel ingot tag. The original has no recycling entry for the boiler.
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmItems.INGOT_STEEL.get(), 4),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_COPPER, 16),
                        new ComparableStack(NtmItems.PLATE_POLYMER.get(), 8)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEAT_BOILER.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));

"""
# Original metadata -> NEO facing (BlockDummyable offsets: 2 north, 3 south, 4 west, 5 east).
META_FACING = {"2": "NORTH", "3": "SOUTH", "4": "WEST", "5": "EAST"}
checks = []
skipped = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def text(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def digests(path):
    """Raw bytes plus the LF-normalised form: a Windows checkout with core.autocrlf=true materialises text assets
    such as boiler.obj with CRLF, while Git stores LF (see goal9a-resource-ownership.json)."""
    data = path.read_bytes()
    return {hashlib.sha256(data).hexdigest(), hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()}


def git_show(spec):
    return subprocess.run(["git", "-C", str(ROOT), "show", spec], capture_output=True, check=True).stdout


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def record(name):
    """Migration records are written by the main agent; a missing one skips its checks with a message."""
    path = ROOT / "migration" / name
    if path.is_file():
        return read(path)
    message = f"migration/{name} is missing; its checks were skipped"
    skipped.append(message)
    print("SKIPPED: " + message)
    return None


def between(source, start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


def anvil_entry():
    source = text(JAVA / "com/hbm/inventory/recipes/anvil/AnvilRecipes.java")
    body = between(source, "private static void registerConstruction() {", "private static void addAnvilRecipe(")
    starts = [m.start() for m in re.finditer(r"CONSTRUCTION_RECIPES\.add\(new AnvilConstructionRecipe\(", body)]
    check(len(starts) >= 6, "registerConstruction has at least six explicit entries")
    # Goal 9B appends the steam engine after the boiler: the boiler block is found by its output, not as the last entry,
    # and later explicit entries are allowed (their own goals check them).
    ends = starts[1:] + [len(body)]
    boilers = [i for i, (a, b) in enumerate(zip(starts, ends)) if "new AnvilOutput(new ItemStack(NtmBlocks.HEAT_BOILER.asItem()))" in body[a:b]]
    index = boilers[0] if len(boilers) == 1 else -1
    check(index >= 5 and not re.search(r"\badd(AnvilRecipe|RecycleRecipe)\(", body[starts[index]:]),
          "one explicit boiler entry after at least five others, and no helper-added construction entry follows it: it keeps its index")
    last = body[starts[index]:ends[index]]
    compact = re.sub(r"\s+", " ", last)
    for part in ("new ComparableStack(NtmItems.INGOT_STEEL.get(), 4)", "new RecipesCommon.TagStack(NtmTags.Items.PLATES_COPPER, 16)",
                 "new ComparableStack(NtmItems.PLATE_POLYMER.get(), 8)", "new AnvilOutput(new ItemStack(NtmBlocks.HEAT_BOILER.asItem()))",
                 ".setTier(2).setOverlay(OverlayType.CONSTRUCTION)"):
        check(part in compact, f"boiler anvil entry contains {part}")
    check(compact.count("new ComparableStack(") == 2 and compact.count("TagStack(") == 1 and "MetaHelper" not in compact,
          "boiler anvil entry: three inputs, a plain output")
    stirling = re.sub(r"\s+", " ", body[starts[index - 5]:starts[index - 4]])
    gear = re.sub(r"\s+", " ", body[starts[index - 1]:starts[index]])
    check("NtmBlocks.MACHINE_STIRLING.asItem()" in stirling and "OverlayType.CONSTRUCTION" in stirling
          and "new ComparableStack(NtmItems.GEAR_LARGE.get(), 1, 0)" in gear and "OverlayType.RECYCLING" in gear,
          "the five Goal 8 Stirling entries directly precede the boiler")
    # Original AnvilRecipes.java:376-381: tier 2, 4 steel ingots, 16 copper plates, 8 insulator plates -> machine_boiler.
    original = re.sub(r"\s+", " ", text(ORIGINAL / "src/main/java/com/hbm/inventory/recipes/anvil/AnvilRecipes.java"))
    check(re.search(r"new OreDictStack\(STEEL\.ingot\(\), 4\), new OreDictStack\(CU\.plate\(\), 16\), new ComparableStack\(ModItems\.plate_polymer, 8\) \}, "
                    r"new AnvilOutput\(new ItemStack\(ModBlocks\.machine_boiler\)\)\)\.setTier\(2\)", original) is not None,
          "the original recipe is tier 2 with 4 steel ingots, 16 copper plates and 8 insulator plates")
    check(source.count(BOILER_ENTRY) == 1, "the boiler entry is the exact Goal 9A block")
    baseline = git_show(f"{BASELINE_COMMIT}:src/main/java/com/hbm/inventory/recipes/anvil/AnvilRecipes.java").decode("utf-8").replace("\r\n", "\n")
    # Entries appended after the boiler by later goals (Goal 9B: the steam engine) are removed with it once they are
    # shown to be explicit construction entries only; everything else must still match the Goal 8 file.
    begin = source.find(BOILER_ENTRY)
    finish = source.find("    }\n\n    private static void addAnvilRecipe(", begin)
    later = source[begin + len(BOILER_ENTRY):finish] if begin >= 0 and finish >= 0 else None
    # Statement-level lines (8-space indent) may only be comments, entry starts or entry ends.
    later_ok = later is not None and not re.search(r"\badd(AnvilRecipe|RecycleRecipe)\(", later) and all(
        line[8:].startswith(("//", "CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(", ").set"))
        for line in later.split("\n") if re.match(r" {8}\S", line))
    check(later_ok and source[:begin] + source[finish:] == baseline,
          f"without the boiler block and the explicit entries after it AnvilRecipes is byte-identical to {BASELINE_COMMIT} (earlier entries unchanged)")


def containers():
    source = text(JAVA / "com/hbm/inventory/FluidContainerRegistry.java")
    register = between(source, "public static void register() {", "public static void registerContainer(")
    bucket = "FluidContainerRegistry.registerContainer(new FluidContainer(new ItemStack(Items.WATER_BUCKET), new ItemStack(Items.BUCKET), Fluids.WATER, 1000));"
    bottle = ("FluidContainerRegistry.registerContainer(new FluidContainer(PotionContents.createItemStack(Items.POTION, Potions.WATER), "
              "new ItemStack(Items.GLASS_BOTTLE), Fluids.WATER, 250));")
    check(register.count(bucket) == 1 and register.count(bottle) == 1, "water bucket (1000 mB) and water bottle (250 mB) are registered")
    check(register.index(bucket) < register.index(bottle) < register.index("FluidType[] fluids = Fluids.getAll();"),
          "both come before the NTM containers, as in the original FluidContainerRegistry.java:33-34")
    original = text(ORIGINAL / "src/main/java/com/hbm/inventory/FluidContainerRegistry.java")
    check("new ItemStack(Items.water_bucket), new ItemStack(Items.bucket), Fluids.WATER, 1000" in original
          and "new ItemStack(Items.potionitem), new ItemStack(Items.glass_bottle), Fluids.WATER, 250" in original,
          "the original registers the same two containers with 1000 and 250 mB")
    loader = text(JAVA / "com/hbm/inventory/fluid/tank/FluidLoaderStandard.java")
    check(loader.index("result.remove(NtmDataComponents.META.get());") < loader.index("FluidContainerRegistry.removeContainerIdentity(input, result);")
          < loader.index("result.applyComponents(registered.getComponentsPatch());"),
          "convertedStack removes META, then the container identity, then applies the registered components")


def renderers():
    table = {"SOUTH": "0F", "EAST": "90F", "NORTH": "180F", "WEST": "270F"}
    originals = {"RenderHeatBoiler": "RenderBoiler", "RenderHeaterFirebox": "RenderFirebox"}
    for name, original_name in originals.items():
        source = text(JAVA / f"com/hbm/render/blockentity/{name}.java")
        switch = between(source, "switch(facing) {", "default -> { }")
        found = dict(re.findall(r"case (\w+) -> RenderContext\.mulPose\(Axis\.YP\.rotationDegrees\(([\d.]+F)\)\);", switch))
        check(found == table, f"{name}: angle table SOUTH 0, EAST 90, NORTH 180, WEST 270")
        original = text(ORIGINAL / f"src/main/java/com/hbm/render/tileentity/{original_name}.java")
        meta = dict(re.findall(r"case (\d): GL11\.glRotatef\((\d+), 0F, 1F, 0F\); break;", original))
        check({META_FACING[k]: f"{v}F" for k, v in meta.items()} == table, f"{name}: the same table as the original {original_name}")
    firebox = text(JAVA / "com/hbm/render/blockentity/RenderHeaterFirebox.java")
    check("default -> { }\n        }\n        RenderContext.mulPose(Axis.YP.rotationDegrees(-90F));" in firebox,
          "RenderHeaterFirebox keeps the original extra -90 degrees after the table")
    boiler = text(JAVA / "com/hbm/render/blockentity/RenderHeatBoiler.java")
    common = between(boiler, "public void renderCommon(ItemStack stack, MultiBufferSource buffer) {", "CompoundTag tag")
    check("RenderContext.mulPose(Axis.YP.rotationDegrees(90F));" in common, "the boiler item render has the original extra 90 degrees (RenderBoiler:68)")


def boiler_block():
    source = text(JAVA / "com/hbm/blocks/machine/MachineHeatBoiler.java")
    check("case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid();" in source and "heatSource" not in source,
          "MachineHeatBoiler: EXTRA proxies are fluid-only, no heatSource")
    fill = between(source, "protected void fillSpace(", "protected InteractionResult useWithoutItem(")
    check("Direction rot = MachineHeatBoilerBlockEntity.getPortAxis(dir);" in fill and "this.makeExtra(level, core.relative(rot));" in fill
          and "this.makeExtra(level, core.relative(rot.getOpposite()));" in fill and "this.makeExtra(level, core.above(3));" in fill,
          "MachineHeatBoiler.fillSpace places proxies at core +-getPortAxis(dir) and core.above(3)")
    check("if(boiler.trySetInputType(type)) {" in source, "the identifier goes through trySetInputType and only messages on success")
    drops = between(source, "protected List<ItemStack> getDrops(", "public void appendHoverText(")
    check("Float radius = params.getOptionalParameter(LootContextParams.EXPLOSION_RADIUS);" in drops
          and "if(radius != null) refund.removeIf(stack -> params.getLevel().random.nextFloat() > 1F / radius);" in drops,
          "the exploded refund keeps each stack with chance 1/radius under a decaying explosion (survives_explosion)")


def language(review):
    provider = text(JAVA / "com/hbm/datagen/NtmLanguageProvider.java")
    forms = {json.dumps(DESC_EN, ensure_ascii=False), json.dumps(DESC_EN)}
    check(any(f'this.add("{DESC_KEY}", {form});' in provider for form in forms), "NtmLanguageProvider adds the boiler description")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    for key, value in ZH_EXPECTED.items():
        check(zh.get(key) == value, f"zh_cn.json {key} = {value}")
    if review is None:
        return
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    check(set(review["reviewed_keys"]) == set(ZH_EXPECTED), "the review covers exactly the three Goal 9A keys")
    for key in review["reviewed_keys"]:
        entry = review["reviewed_entries"][key]
        check(key in mapping and mapping[key] == entry and mapping[key]["kind"] != "deferred" and entry["target_zh"] == zh[key],
              f"zh_cn-map entry equals the review: {key}")
    check(review["reviewed_entries"][DESC_KEY]["target_en"] == DESC_EN, "the reviewed English description is the provider text")
    # Later goals may only release deferred keys (Goal 9B released item.shell_steel: 109 -> 108), never add them.
    check(sum(value["kind"] == "deferred" for value in mapping.values()) <= 109, "deferred localization count does not grow past 109")


def ownership():
    record_ = record("goal9a-resource-ownership.json")
    if record_ is None:
        return
    check(record_["imported_assets"] == [], "no asset is imported")
    check(len(record_["reused_assets"]) == 8, "eight reused assets are recorded")
    for asset in record_["reused_assets"]:
        target, source = ROOT / asset["target_path"], ORIGINAL / asset["source_path"]
        check(target.is_file() and source.is_file(), f"reused asset and its original exist: {asset['target_path']}")
        check(asset["target_sha256"] in digests(target), f"current NEO bytes match the record (raw or LF): {asset['target_path']}")
        check(asset["source_sha256"] in digests(source), f"original bytes match the record (raw or LF): {asset['source_path']}")
        check(bool(digests(source) & digests(target)) == asset["identical_to_source"], f"identical_to_source holds: {asset['target_path']}")
        if "target_sha256_lf" in asset:
            lf = hashlib.sha256(target.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            check(lf == asset["target_sha256_lf"], f"LF-normalised hash matches: {asset['target_path']}")


def source_checks():
    anvil_entry()
    containers()
    renderers()
    boiler_block()
    review = record("goal9a-localization-review.json")
    language(review)
    ownership()
    return review


def generated_checks(review):
    before = read(BEFORE_STAMP)
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(name for name in set(before["generated"]) & set(after["generated"])
                      if before["generated"][name] != after["generated"][name])
    changed_inputs = sorted(name for name in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(name) != after["inputs"].get(name))
    check(len(before["generated"]) == BEFORE_COUNT and len(after["generated"]) == BEFORE_COUNT, f"still {BEFORE_COUNT} generated files")
    check(not added and not removed, "no generated file added or removed")
    check(modified == [EN_US], f"only {EN_US} is modified")
    check(set(changed_inputs) == CHANGED_INPUTS, "changed generation inputs are exactly the Goal 9A production files and zh_cn.json")
    # The baseline en_us.json is the Goal 8 commit's, provided its bytes are the ones the before-stamp records.
    old_bytes = git_show(f"{BASELINE_COMMIT}:src/generated/resources/{EN_US}")
    check(hashlib.sha256(old_bytes).hexdigest() == before["generated"][EN_US], f"git {BASELINE_COMMIT} holds the en_us.json the before-stamp records")
    old, new = json.loads(old_bytes.decode("utf-8")), read(GEN / EN_US)
    check(set(new) - set(old) == {DESC_KEY} and not set(old) - set(new), f"en_us.json gains exactly {DESC_KEY}")
    check(all(new[key] == old[key] for key in old), "every other English value is unchanged")
    check(new[DESC_KEY] == DESC_EN, "the generated description is the provider text")
    if review is not None:
        check(new[DESC_KEY] == review["reviewed_entries"][DESC_KEY]["target_en"], "the generated description equals the reviewed English")
    return {"baseline": str(BEFORE_STAMP.relative_to(ROOT).as_posix()), "generated_added": added, "generated_modified": modified,
            "generated_removed": removed, "changed_inputs": changed_inputs, "generated_count": len(after["generated"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip checks that need a fresh runData")
    args = parser.parse_args()
    review = source_checks()
    report = {"mode": "source-only" if args.source_only else "full"}
    if not args.source_only:
        report.update(generated_checks(review))
    report.update({"checks": len(checks), "assertions": checks, "skipped": skipped,
                   "boundary": "Provider/recipe/renderer source, generated resources and source assets only; no Minecraft anvil, rendering, container or gameplay run."})
    OUT.mkdir(parents=True, exist_ok=True)
    name = "source-check.json" if args.source_only else "generated-check.json"
    (OUT / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 9A resources ({report['mode']}): {len(checks)} checks passed; report {OUT / name}")


if __name__ == "__main__":
    main()
