"""Audit the Goal 8B Stirling engine recipes, anvil entries, imported assets and bilingual text.

Default mode runs after `build.ps1 -Offline runData` and also compares the generated output with the pre-Goal 8B
stamp. `--source-only` skips the generated-output part, for environments that cannot run Gradle.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
JAVA = ROOT / "src/main/java"
OUT = ROOT / "build/migration/goal8"
# Copy of the stamp after the Goal 7B re-run (G8A-0), taken before any Goal 8B source change: 3815 generated files.
BEFORE_STAMP = OUT / "stamp-before-g8b.json"
# Fallback: the Goal 7B commit. Its stamp predates the G8A-0 re-run, so it lacks the three Goal 7B recipes and their
# advancements (3809 files) and the Goal 7B Java sources still count as changed inputs.
FALLBACK_COMMIT = "812c92b52b79a441f12fe7cdfb1a37b27f7c5e3e"
GOAL7B_ADDED = {f"data/hbmsntm/{folder}/{name}.json" for folder in ("recipe", "advancement/recipes/misc")
                for name in ("fluid_duct_neo", "barrel_steel", "barrel_plastic")}
GOAL7B_SOURCES = {f"src/main/java/com/hbm/{name}.java" for name in (
    "datagen/NtmRecipeProvider", "blockentity/machine/storage/BarrelBlockEntity",
    "blockentity/machine/MachineFurnaceCombinationBlockEntity", "blockentity/machine/MachineWoodBurnerBlockEntity")}

# From the datagen code: gear recipe + advancement (NtmRecipeProvider), particle-only block state, block model and
# builtin/entity item model (NtmBlockStateProvider.particleOnlyBlock), gear item model (basicItem) and dropSelf loot.
EXPECTED_ADDED = {
    "data/hbmsntm/recipe/gear_large.json",
    "data/hbmsntm/advancement/recipes/misc/gear_large.json",
    "assets/hbmsntm/blockstates/machine_stirling.json",
    "assets/hbmsntm/models/block/machine_stirling_particle.json",
    "assets/hbmsntm/models/item/machine_stirling.json",
    "assets/hbmsntm/models/item/gear_large.json",
    "data/hbmsntm/loot_table/blocks/machine_stirling.json",
}
# Language keys, the sound definition and the mineable/pickaxe block tag (NtmBlockTagProvider); nothing else.
EXPECTED_MODIFIED = {
    "assets/hbmsntm/lang/en_us.json",
    "assets/hbmsntm/sounds.json",
    "data/minecraft/tags/block/mineable/pickaxe.json",
}
CHANGED_JAVA = {f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/NtmBlockEntityTypes", "blockentity/machine/MachineStirlingBlockEntity",
    "blocks/NtmBlocks", "blocks/machine/MachineStirlingBlock",
    "datagen/NtmBlockLootTableProvider", "datagen/NtmBlockStateProvider", "datagen/NtmBlockTagProvider",
    "datagen/NtmItemModelProvider", "datagen/NtmLanguageProvider", "datagen/NtmRecipeProvider",
    "datagen/NtmSoundDefinitionsProvider", "entity/NtmEntityTypes", "entity/projectile/StrayCog",
    "inventory/NtmCreativeTabs", "inventory/recipes/anvil/AnvilRecipes", "items/NtmItems",
    "main/ClientProxy", "main/ResourceManager", "registry/NtmSoundEvents",
    "render/blockentity/RenderStirling", "render/entity/projectile/RenderStrayCog")}
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
ASSETS = {f"src/main/resources/assets/hbmsntm/{name}" for name in (
    "models/obj/machines/stirling.obj", "textures/models/machines/stirling.png",
    "textures/item/gear_large.png", "sounds/block/warn_overspeed.ogg")}
checks = []
skipped = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digests(path):
    """Raw bytes plus the LF-normalised form: a Windows checkout with core.autocrlf=true materialises text assets
    such as stirling.obj with CRLF, while Git stores LF (see goal8-resource-ownership.json)."""
    data = path.read_bytes()
    return {hashlib.sha256(data).hexdigest(), hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()}


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


def between(text, start, end):
    begin = text.index(start)
    return text[begin:text.index(end, begin)]


def gear_recipe(provider):
    match = re.search(r'ShapedRecipeBuilder\.shaped\(RecipeCategory\.MISC, NtmItems\.GEAR_LARGE\.get\(\), (\d+)\)((?:(?!ShapedRecipeBuilder).)*?)'
                      r'\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\("hbmsntm", "gear_large"\)\);', provider, re.S)
    check(match is not None, "gear_large is defined in NtmRecipeProvider")
    body = match.group(2)
    check(int(match.group(1)) == 1 and re.findall(r'\.pattern\("([^"]*)"\)', body) == ["III", "ICI", "III"],
          "gear_large: pattern III/ICI/III, one gear (original CraftingManager)")
    check(".define('I', NtmItems.PLATE_IRON.get())" in body, "gear_large: I is the iron plate")
    copper = re.search(r"\.define\('C', Ingredient\.of\(([^)]*\)[^)]*)\)\)", body)
    check(copper is not None and {part.strip() for part in copper.group(1).split(",")} == {"NtmItems.INGOT_COPPER.get()", "Items.COPPER_INGOT"},
          "gear_large: C is one Ingredient accepting NEO and Minecraft copper ingots (no shared tag changed)")
    check('.unlockedBy("has_iron_plate", has(NtmItems.PLATE_IRON.get()))' in body, "gear_large unlocks from the iron plate")
    check(len(re.findall(r"shaped\(RecipeCategory\.\w+, NtmItems\.GEAR_LARGE\.get\(\)", provider)) == 1, "no other gear_large crafting recipe")


def anvil_entries():
    source = (JAVA / "com/hbm/inventory/recipes/anvil/AnvilRecipes.java").read_text(encoding="utf-8")
    body = between(source, "private static void registerConstruction() {", "private static void addAnvilRecipe(")
    starts = [m.start() for m in re.finditer(r"CONSTRUCTION_RECIPES\.add\(new AnvilConstructionRecipe\(", body)]
    # Goal 9A appends the heat boiler after the Stirling entries; verify_goal9a_resources checks that entry.
    check(len(starts) >= 6 and "new AnvilOutput(new ItemStack(NtmBlocks.HEAT_BOILER.asItem()))" in body[starts[-1]:],
          "the last explicit entry is the Goal 9A heat boiler")
    end = starts.pop()
    check(len(starts) >= 5, "registerConstruction has at least five explicit entries")
    tail = body[starts[-5]:end]
    check(not re.search(r"\badd(AnvilRecipe|RecycleRecipe)\(", tail),
          "no helper-added construction entry follows the Stirling entries: they are the last five indices")
    blocks = [tail[a - starts[-5]:(b - starts[-5]) if b else None] for a, b in zip(starts[-5:], starts[-4:] + [None])]
    compact = [re.sub(r"\s+", " ", block) for block in blocks]
    build = ["new RecipesCommon.TagStack(ItemTags.PLANKS, 16)", "new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 6)",
             "new ComparableStack(NtmItems.COIL_COPPER.get(), 4)", "new ComparableStack(NtmItems.GEAR_LARGE.get(), 1, 0)",
             "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_STIRLING.asItem()))", ".setTier(2).setOverlay(OverlayType.CONSTRUCTION)"]
    for index, copper, label in ((0, "new ComparableStack(Items.COPPER_INGOT, 8)", "Minecraft"),
                                 (1, "new ComparableStack(NtmItems.INGOT_COPPER.get(), 8)", "NEO")):
        check(all(part in compact[index] for part in build + [copper]),
              f"Stirling construction {index + 1}: 16 planks, 6 steel plates, 8 {label} copper, 4 coils, plain gear (meta 0), tier 2")
    returns = ["new AnvilOutput(new ItemStack(NtmItems.PLATE_STEEL.get(), 6))", "new AnvilOutput(new ItemStack(NtmItems.INGOT_COPPER.get(), 8))",
               "new AnvilOutput(new ItemStack(NtmItems.COIL_COPPER.get(), 4))"]
    gear_out = "new AnvilOutput(new ItemStack(NtmItems.GEAR_LARGE.get(), 1))"
    check("new ComparableStack(NtmBlocks.MACHINE_STIRLING.asItem(), 1, 0)" in compact[2] and all(p in compact[2] for p in returns)
          and gear_out in compact[2] and ".setTier(2).setOverlay(OverlayType.RECYCLING)" in compact[2],
          "recycling with gear: explicit meta 0 input; 6 steel plates, 8 copper, 4 coils and the gear")
    check("new ComparableStack(NtmBlocks.MACHINE_STIRLING.asItem(), 1, 1)" in compact[3] and all(p in compact[3] for p in returns)
          and gear_out not in compact[3] and ".setTier(2).setOverlay(OverlayType.RECYCLING)" in compact[3],
          "recycling without gear: meta 1 input; the same returns without the gear")
    check("new ComparableStack(NtmItems.GEAR_LARGE.get(), 1, 0)" in compact[4]
          and "new AnvilOutput(new ItemStack(NtmItems.PLATE_IRON.get(), 8))" in compact[4]
          and "new AnvilOutput(new ItemStack(NtmItems.INGOT_COPPER.get(), 1))" in compact[4]
          and ".setTier(2).setOverlay(OverlayType.RECYCLING)" in compact[4],
          "gear recycling: explicit meta 0 input; 8 iron plates and 1 copper")
    check(not any("PLANKS" in block for block in compact[2:]), "no recycling returns planks")
    check(not any("MetaHelper" in block for block in compact), "all five outputs are plain stacks (no META component written)")


def source_checks():
    gear_recipe((JAVA / "com/hbm/datagen/NtmRecipeProvider.java").read_text(encoding="utf-8"))
    anvil_entries()

    ownership = record("goal8-resource-ownership.json")
    if ownership is not None:
        original = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
        check(len(ownership["imported_assets"]) == 4, "four imported assets are recorded")
        for asset in ownership["imported_assets"]:
            target = ROOT / asset["target_path"]
            check(target.is_file() and asset["target_sha256"] in digests(target), f"imported target bytes: {asset['target_path']}")
            source = original / asset["source_path"]
            if source.is_file():
                check(asset["source_sha256"] in digests(source)
                      and bool(digests(source) & digests(target)) == asset["identical_to_source"],
                      f"original source bytes: {asset['source_path']}")
        for asset in ownership.get("reused_assets", []):
            check((ROOT / asset["target_path"]).is_file(), f"reused asset present: {asset['target_path']}")
    resources = (JAVA / "com/hbm/main/ResourceManager.java").read_text(encoding="utf-8")
    items = (JAVA / "com/hbm/datagen/NtmItemModelProvider.java").read_text(encoding="utf-8")
    sounds = re.sub(r"\s+", " ", (JAVA / "com/hbm/datagen/NtmSoundDefinitionsProvider.java").read_text(encoding="utf-8"))
    events = (JAVA / "com/hbm/registry/NtmSoundEvents.java").read_text(encoding="utf-8")
    states = (JAVA / "com/hbm/datagen/NtmBlockStateProvider.java").read_text(encoding="utf-8")
    check('"models/obj/machines/stirling.obj"' in resources and '"textures/models/machines/stirling.png"' in resources,
          "ResourceManager loads stirling.obj and stirling.png")
    check("this.basicItem(NtmItems.GEAR_LARGE.get());" in items, "the gear item model uses basicItem (textures/item/gear_large.png)")
    check('WARN_OVERSPEED = reg("block.warn_overspeed")' in events
          and 'this.add(NtmSoundEvents.WARN_OVERSPEED, SoundDefinition.definition() .subtitle("subtitles.block.warn_overspeed") '
              '.with(sound(NuclearTechMod.withDefaultNamespace("block/warn_overspeed")))' in sounds,
          "block.warn_overspeed is defined with its subtitle and the lower-case sounds/block/warn_overspeed.ogg")
    check('this.particleOnlyBlock(NtmBlocks.MACHINE_STIRLING, modLoc("block/block_steel"));' in states,
          "the Stirling block state is particle-only with the retained steel block texture")

    review = record("goal8-localization-review.json")
    if review is not None:
        zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
        mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
        language = (JAVA / "com/hbm/datagen/NtmLanguageProvider.java").read_text(encoding="utf-8")
        for key in review["reviewed_keys"]:
            entry = review["reviewed_entries"][key]
            check(key in zh and key in mapping and mapping[key]["kind"] != "deferred"
                  and mapping[key]["target_zh"] == zh[key] and entry == mapping[key],
                  f"bilingual key: {key}")
            check(json.dumps(entry["target_en"]) in language, f"English for {key} comes from NtmLanguageProvider")
        check(sum(value["kind"] == "deferred" for value in mapping.values()) == 109, "deferred localization count stays 109")
        return review
    return None


def generated_checks(review):
    if BEFORE_STAMP.is_file():
        before, baseline = read(BEFORE_STAMP), str(BEFORE_STAMP.relative_to(ROOT).as_posix())
        expected_added, expected_count, extra_inputs = EXPECTED_ADDED, 3815, set()
    else:
        print(f"{BEFORE_STAMP} is missing: using the Goal 7B commit stamp ({FALLBACK_COMMIT[:7]}), "
              "which lacks the three Goal 7B recipes and their advancements")
        before = json.loads(subprocess.run(["git", "-C", str(ROOT), "show", f"{FALLBACK_COMMIT}:src/generated/resources/.migration-stamp.json"],
                                           capture_output=True, text=True, check=True, encoding="utf-8").stdout)
        baseline = f"git {FALLBACK_COMMIT[:7]}"
        expected_added, expected_count, extra_inputs = EXPECTED_ADDED | GOAL7B_ADDED, 3809, GOAL7B_SOURCES
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(name for name in set(before["generated"]) & set(after["generated"])
                      if before["generated"][name] != after["generated"][name])
    changed_inputs = sorted(name for name in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(name) != after["inputs"].get(name))
    check(len(before["generated"]) == expected_count and len(after["generated"]) == expected_count + len(expected_added),
          f"{len(expected_added)} generated files added to the {expected_count}-file baseline")
    check(set(added) == expected_added and not removed, f"added exactly {sorted(expected_added)}; nothing removed")
    check(set(modified) == EXPECTED_MODIFIED, f"modified exactly {sorted(EXPECTED_MODIFIED)}")
    goal8_inputs = CHANGED_JAVA | {ZH} | ASSETS
    check(goal8_inputs <= set(changed_inputs) <= goal8_inputs | extra_inputs,
          "changed generation inputs are the Goal 8B Java sources, the imported assets and zh_cn.json only")

    recipe = read(GEN / "data/hbmsntm/recipe/gear_large.json")
    copper = recipe["key"].get("C")
    check(recipe["type"] == "minecraft:crafting_shaped" and recipe["pattern"] == ["III", "ICI", "III"]
          and recipe["key"]["I"] == {"item": "hbmsntm:plate_iron"} and isinstance(copper, list)
          and sorted(json.dumps(c, sort_keys=True) for c in copper) == sorted(json.dumps({"item": i}) for i in ("hbmsntm:ingot_copper", "minecraft:copper_ingot"))
          and recipe["result"] == {"count": 1, "id": "hbmsntm:gear_large"}, "generated gear_large recipe")
    advancement = read(GEN / "data/hbmsntm/advancement/recipes/misc/gear_large.json")
    check(advancement["rewards"]["recipes"] == ["hbmsntm:gear_large"]
          and advancement["criteria"]["has_iron_plate"]["conditions"]["items"][0]["items"] == "hbmsntm:plate_iron",
          "gear_large unlocks from hbmsntm:plate_iron")
    loot = read(GEN / "data/hbmsntm/loot_table/blocks/machine_stirling.json")
    check(loot["pools"][0]["entries"][0]["name"] == "hbmsntm:machine_stirling", "machine_stirling drops itself")
    state = read(GEN / "assets/hbmsntm/blockstates/machine_stirling.json")
    particle = read(GEN / "assets/hbmsntm/models/block/machine_stirling_particle.json")
    item_model = read(GEN / "assets/hbmsntm/models/item/machine_stirling.json")
    gear_model = read(GEN / "assets/hbmsntm/models/item/gear_large.json")
    check(state["variants"][""]["model"] == "hbmsntm:block/machine_stirling_particle"
          and particle["textures"]["particle"] == "hbmsntm:block/block_steel"
          and item_model["parent"] == "minecraft:builtin/entity"
          and gear_model["textures"]["layer0"] == "hbmsntm:item/gear_large", "block state, particle model and both item models")
    sounds = read(GEN / "assets/hbmsntm/sounds.json")["block.warn_overspeed"]
    names = [s if isinstance(s, str) else s.get("name") for s in sounds["sounds"]]
    check(names == ["hbmsntm:block/warn_overspeed"] and sounds.get("subtitle") == "subtitles.block.warn_overspeed",
          "sounds.json defines block.warn_overspeed with its subtitle")
    pickaxe = read(GEN / "data/minecraft/tags/block/mineable/pickaxe.json")
    check("hbmsntm:machine_stirling" in pickaxe["values"], "the Stirling engine is mineable with a pickaxe")
    if review is not None:
        english = read(GEN / "assets/hbmsntm/lang/en_us.json")
        for key in review["reviewed_keys"]:
            check(english.get(key) == review["reviewed_entries"][key]["target_en"], f"generated English: {key}")
    return {"baseline": baseline, "generated_added": added, "generated_modified": modified, "generated_removed": removed,
            "changed_inputs": changed_inputs, "generated_count": len(after["generated"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip checks that need a fresh runData")
    args = parser.parse_args()
    review = source_checks()
    report = {"mode": "source-only" if args.source_only else "full"}
    if not args.source_only:
        report.update(generated_checks(review))
    report.update({"checks": len(checks), "assertions": checks, "skipped": skipped,
                   "boundary": "Provider/recipe source, generated resources and source assets only; no Minecraft crafting, anvil, rendering, sound or gameplay run."})
    OUT.mkdir(parents=True, exist_ok=True)
    name = "source-check.json" if args.source_only else "generated-check.json"
    (OUT / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 8 resources ({report['mode']}): {len(checks)} checks passed; report {OUT / name}")


if __name__ == "__main__":
    main()
