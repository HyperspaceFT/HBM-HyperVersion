"""Audit the Goal 10A scrap textures and models, imported JEI backgrounds, client registrations and bilingual text.

Default mode runs after `build.ps1 -Offline runData` and also checks the generated output against the pre-Goal 10A
stamp (build/migration/goal10a/stamp-before-g10a.json). `--source-only` skips the generated-output part, for
environments that cannot run Gradle.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
JAVA = ROOT / "src/main/java"
OUT = ROOT / "build/migration/goal10a"
# Copy of the stamp taken before any Goal 10A source change, i.e. after the Goal 9B commit: 3838 generated files.
BEFORE_STAMP = OUT / "stamp-before-g10a.json"
BEFORE_COUNT = 3838
# The Goal 9B commit: the last committed generated en_us.json and scraps.json.
BASELINE_COMMIT = "ee8f8d06"
EN_US = "assets/hbmsntm/lang/en_us.json"
SCRAPS_MODEL = "assets/hbmsntm/models/item/scraps.json"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MODELS = ("tungsten", "cobalt", "steel", "durasteel", "liquid")
# Override predicate per model, ascending (CopperScrapsItem.getModelValue: (index + 1) * 0.2, liquid 1.0).
PREDICATES = {"tungsten": 0.2, "cobalt": 0.4, "steel": 0.6, "durasteel": 0.8, "liquid": 1.0}
ADDED = {f"assets/hbmsntm/models/item/scraps_{name}.json" for name in MODELS}
# The 20 Goal 10A keys: 13 new, 6 with new English, casting.take_output with new Chinese only.
EN_EXPECTED = {
    "block.hbmsntm.machine_crucible.desc": "Smelts metals with heat from directly below. The selected alloy pours from the front, everything else from the rear.$Heat transfer rate: ΔT*0.25 TU/t",
    "casting.contents": "%s: %s / %s quanta",
    "casting.scraps": "%s: %s quanta (72 per ingot)",
    "casting.scraps.desc": "Recovered metal; remelt in a crucible.",
    "casting.take_output": "Right-click to take the cast plate.",
    "container.machine_crucible.amount": "%s: %s quanta",
    "container.machine_crucible.empty": "Empty",
    "container.machine_crucible.jei.alloying": "Crucible Alloying",
    "container.machine_crucible.jei.casting": "Crucible Casting",
    "container.machine_crucible.jei.select_hint": "Select the recipe in the crucible's interface; it runs every %s ticks.",
    "container.machine_crucible.jei.smelting": "Crucible Smelting",
    "container.machine_crucible.recipe_pour": "Inputs and product of the selected recipe. Only the product pours, up to 24 quanta/tick; clear the recipe to drain leftover inputs.",
    "container.machine_crucible.recipe_stack": "Recipe stack (front spout): %s / %s quanta",
    "container.machine_crucible.select_recipe": "Select an alloy recipe; while one is selected, materials it does not use are refused.",
    "container.machine_crucible.waste_pour": "Everything outside the selected recipe, up to 24 quanta/tick; 72 quanta per ingot.",
    "container.machine_crucible.waste_stack": "Waste stack (rear spout): %s / %s quanta",
    "hbmmat.cobalt": "Cobalt",
    "item.hbmsntm.scraps": "%s Scraps",
    "item.hbmsntm.scraps.desc": "Recovered metal; remelt in a crucible.",
    "item.hbmsntm.scraps.generic": "Foundry Scraps",
}
NEW_KEYS = {"container.machine_crucible.amount", "container.machine_crucible.empty", "container.machine_crucible.jei.alloying",
            "container.machine_crucible.jei.casting", "container.machine_crucible.jei.select_hint", "container.machine_crucible.jei.smelting",
            "container.machine_crucible.recipe_pour", "container.machine_crucible.recipe_stack", "container.machine_crucible.select_recipe",
            "container.machine_crucible.waste_pour", "container.machine_crucible.waste_stack", "hbmmat.cobalt", "item.hbmsntm.scraps.generic"}
EN_UNCHANGED = {"casting.take_output"}
REMOVED = {"container.machine_crucible.copper", "container.machine_crucible.pour"}
PROVIDER_LINES = {
    "block.hbmsntm.machine_crucible.desc": 'this.add(NtmBlocks.MACHINE_CRUCIBLE, DESC, "{}");',
    "item.hbmsntm.scraps": 'this.add(NtmItems.SCRAPS, "{}");',
}
# Generation inputs Goal 10A changes: the production Java the handoff lists, zh_cn.json and the eight assets.
CHANGED_INPUTS = {f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/machine/FoundryMoldBlockEntity", "blockentity/machine/MachineCrucibleBlockEntity",
    "blocks/machine/FoundryMoldBlock", "blocks/machine/MachineCrucibleBlock", "datagen/NtmItemModelProvider",
    "datagen/NtmLanguageProvider", "handler/jei/CrucibleAlloyingRecipeHandler", "handler/jei/CrucibleCastingRecipeHandler",
    "handler/jei/CrucibleSmeltingRecipeHandler", "handler/jei/NtmJeiPlugin", "handler/jei/subtypes/ScrapsSubtypeInterpreter",
    "inventory/NtmCreativeTabs", "inventory/material/Mats", "inventory/recipes/CopperCastingRecipes",
    "inventory/recipes/CrucibleRecipe", "inventory/recipes/CrucibleRecipes", "inventory/recipes/ShredderRecipes",
    "inventory/recipes/loader/SerializableRecipe", "inventory/screens/MachineCrucibleScreen", "items/CopperScrapsItem",
    "main/NuclearTechModClient")} | {ZH} | {
    f"src/main/resources/assets/hbmsntm/textures/{name}.png" for name in (
        "gui/jei/gui_nei_crucible", "gui/jei/gui_nei_crucible_smelting", "gui/jei/gui_nei_foundry",
        "item/scraps_cobalt", "item/scraps_durasteel", "item/scraps_liquid", "item/scraps_steel", "item/scraps_tungsten")}
checks = []
skipped = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def text(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def compact(source):
    return re.sub(r"\s+", " ", source)


def digests(path):
    """Raw bytes plus the LF-normalised form (a Windows checkout may materialise text assets with CRLF)."""
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


def textures():
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(ROOT / "tools/migration/goal10a_scrap_textures.py"), "--check"],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(result.returncode == 0, f"goal10a_scrap_textures.py --check passes: {result.stdout.strip()} {result.stderr.strip()}")
    for name in MODELS:
        check((MAIN / f"assets/hbmsntm/textures/item/scraps_{name}.png").is_file(), f"textures/item/scraps_{name}.png exists")
    check((MAIN / "assets/hbmsntm/textures/item/scraps.png").is_file(), "the base scraps texture exists")
    # The JEI categories draw these backgrounds (NuclearTechMod.withDefaultNamespace(TEXTURE)).
    for handler in ("CrucibleAlloyingRecipeHandler", "CrucibleSmeltingRecipeHandler", "CrucibleCastingRecipeHandler"):
        source = text(JAVA / f"com/hbm/handler/jei/{handler}.java")
        paths = re.findall(r'private static final String TEXTURE = "([^"]+)";', source)
        check(len(paths) == 1 and (MAIN / "assets/hbmsntm" / paths[0]).is_file()
              and f"NuclearTechMod.withDefaultNamespace(TEXTURE)" in source, f"{handler} background {paths} exists")


def ownership():
    record_ = record("goal10a-resource-ownership.json")
    if record_ is None:
        return
    check(record_["source_commit"].startswith("608fec4"), "the record names the 608fec4 original")
    check(len(record_["imported_assets"]) == 4 and len(record_["derived_assets"]) == 4, "four imported and four derived assets are recorded")
    for asset in record_["imported_assets"] + record_["derived_assets"]:
        target, source = ROOT / asset["target_path"], ORIGINAL / asset["source_path"]
        check(target.is_file() and source.is_file(), f"asset and its original exist: {asset['target_path']}")
        check(asset["target_sha256"] in digests(target) and asset["size"] == target.stat().st_size, f"current NEO bytes and size match the record: {asset['target_path']}")
        check(asset["source_sha256"] in digests(source), f"original bytes match the record: {asset['source_path']}")
        check(asset["identical_to_source"] == bool(digests(source) & digests(target)),
              f"identical_to_source is {asset['identical_to_source']}: {asset['target_path']}")
        last = subprocess.run(["git", "-C", str(ORIGINAL), "log", "-1", "--format=%H", "--", asset["source_path"]],
                              capture_output=True, text=True, check=True).stdout.strip()
        check(last == asset["source_last_commit"], f"original last commit matches the record: {asset['source_path']}")
    for asset in record_["imported_assets"]:
        check(asset["identical_to_source"], f"imported byte-identical: {asset['target_path']}")
    for asset in record_["derived_assets"]:
        check(asset["generator"] == "tools/migration/goal10a_scrap_textures.py" and not asset["identical_to_source"],
              f"derived by the generator script: {asset['target_path']}")
    for asset in record_["reused_assets"]:
        check(asset["target_sha256"] in digests(ROOT / asset["target_path"]), f"reused asset unchanged: {asset['target_path']}")
    recorded = {asset["target_path"] for asset in record_["imported_assets"] + record_["derived_assets"]}
    check(recorded == {name for name in CHANGED_INPUTS if name.endswith(".png")}, "the record covers exactly the eight new textures")


def client_and_providers():
    client = compact(text(JAVA / "com/hbm/main/NuclearTechModClient.java"))
    check(client.count('ItemProperties.register(NtmItems.SCRAPS.get(), NuclearTechMod.withDefaultNamespace("scraps_type"), '
                       '(stack, level, entity, seed) -> CopperScrapsItem.getModelType(stack));') == 1,
          "NuclearTechModClient registers the hbmsntm:scraps_type item property from CopperScrapsItem.getModelType")
    check(client.count("event.register( (stack, tintIndex) -> tintIndex == 0 ? 0xFF000000 | CopperScrapsItem.getColor(stack) : 0xFFFFFFFF, "
                       "NtmItems.SCRAPS.get() );") == 1, "NuclearTechModClient registers the scraps ItemColor from CopperScrapsItem.getColor")
    models = compact(text(JAVA / "com/hbm/datagen/NtmItemModelProvider.java"))
    check("this.registerScraps();" in models and "this.basicItem(NtmItems.SCRAPS.get());" not in models.replace(
        "ItemModelBuilder builder = this.basicItem(NtmItems.SCRAPS.get());", ""), "the item model provider builds scraps with overrides")
    check('.predicate(NuclearTechMod.withDefaultNamespace("scraps_type"), CopperScrapsItem.getModelValue(i))' in models
          and '.predicate(NuclearTechMod.withDefaultNamespace("scraps_type"), CopperScrapsItem.LIQUID_MODEL)' in models,
          "scraps overrides use the scraps_type predicate, the per-material values and the liquid value")
    screen = compact(text(JAVA / "com/hbm/inventory/screens/MachineCrucibleScreen.java"))
    check("RecipeSelectorScreen.openSelector(CrucibleRecipes.INSTANCE, be, be.recipe, 0, null, this);" in screen,
          "the crucible screen opens the recipe selector for CrucibleRecipes with index 0 (original GUICrucible.java:67)")
    for path in ("blockentity/machine/MachineCrucibleBlockEntity.java", "blockentity/machine/FoundryMoldBlockEntity.java",
                 "inventory/recipes/CrucibleRecipe.java", "inventory/recipes/CrucibleRecipes.java", "inventory/recipes/CopperCastingRecipes.java",
                 "items/CopperScrapsItem.java", "inventory/material/Mats.java"):
        source = text(JAVA / "com/hbm" / path)
        check(not any(token in source for token in ("net.minecraft.client", "mezz.jei", "com.hbm.render")), f"{path} has no client-only or JEI reference")


def language(review):
    provider = text(JAVA / "com/hbm/datagen/NtmLanguageProvider.java")
    for key, value in EN_EXPECTED.items():
        line = PROVIDER_LINES.get(key, f'this.add("{key}", "{{}}");').format(value)
        check(provider.count(line) == 1, f"NtmLanguageProvider adds {key} = {value}")
    for key in REMOVED:
        check(f'"{key}"' not in provider, f"NtmLanguageProvider no longer adds {key}")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    for key, value in EN_EXPECTED.items():
        check(key in zh and zh[key].count("%s") == value.count("%s") and "%" not in zh[key].replace("%s", "").replace("%%", ""),
              f"zh_cn.json has {key} with the English %s count ({value.count('%s')})")
    for key in REMOVED:
        check(key not in zh, f"zh_cn.json no longer has {key}")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    check(sum(value["kind"] == "deferred" for value in mapping.values()) == 108, "deferred localization count is still 108")
    for key, value in EN_EXPECTED.items():
        entry = mapping.get(key)
        check(entry is not None and entry["target_en"] == value and entry["target_zh"] == zh[key] and entry["kind"] != "deferred",
              f"zh_cn-map entry for {key} matches the provider English and zh_cn.json")
    for key in REMOVED:
        check(key not in mapping, f"zh_cn-map no longer has {key}")
    if review is None:
        return
    check(set(review["reviewed_keys"]) == set(EN_EXPECTED), "the review covers exactly the 20 Goal 10A keys")
    check(set(review["removed_keys"]) == REMOVED, "the review lists the two removed keys")
    for key in review["reviewed_keys"]:
        entry = review["reviewed_entries"][key]
        check(mapping[key] == entry, f"zh_cn-map entry equals the review: {key}")
    lang = {"en": text(ORIGINAL / "src/main/resources/assets/hbm/lang/en_US.lang"), "zh": text(ORIGINAL / "src/main/resources/assets/hbm/lang/zh_CN.lang")}
    for key, entry in review["reviewed_entries"].items():
        if entry["kind"] == "upstream":
            check(f"{entry['source_key']}={entry['source_en']}\n" in lang["en"] and f"{entry['source_key']}={entry['source_zh']}\n" in lang["zh"],
                  f"the upstream source texts are the original lang lines: {key}")


def scraps_models():
    """Generated scraps.json and the five override models (written by runData from NtmItemModelProvider)."""
    model = read(GEN / SCRAPS_MODEL)
    check(model["parent"] == "minecraft:item/generated" and model["textures"] == {"layer0": "hbmsntm:item/scraps"}, "scraps.json keeps the base texture")
    overrides = model["overrides"]
    values = [o["predicate"]["hbmsntm:scraps_type"] for o in overrides]
    check(len(overrides) == 5 and all(set(o["predicate"]) == {"hbmsntm:scraps_type"} for o in overrides), "scraps.json has five scraps_type overrides")
    check(values == sorted(values) and all(abs(v - PREDICATES[name]) < 1e-6 for v, name in zip(values, MODELS))
          and [o["model"] for o in overrides] == [f"hbmsntm:item/scraps_{name}" for name in MODELS],
          f"overrides ascending: tungsten 0.2, cobalt 0.4, steel 0.6, DuraSteel 0.8, liquid 1.0 ({values})")
    for name in MODELS:
        sub = read(GEN / f"assets/hbmsntm/models/item/scraps_{name}.json")
        check(sub == {"parent": "minecraft:item/generated", "textures": {"layer0": f"hbmsntm:item/scraps_{name}"}}
              and (MAIN / f"assets/hbmsntm/textures/item/scraps_{name}.png").is_file(), f"scraps_{name}.json uses its texture")


def source_checks():
    textures()
    ownership()
    client_and_providers()
    review = record("goal10a-localization-review.json")
    language(review)


def generated_checks():
    before = read(BEFORE_STAMP)
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(name for name in set(before["generated"]) & set(after["generated"])
                      if before["generated"][name] != after["generated"][name])
    changed_inputs = sorted(name for name in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(name) != after["inputs"].get(name))
    check(len(before["generated"]) == BEFORE_COUNT, f"the before-stamp has {BEFORE_COUNT} generated files")
    check(set(added) == ADDED and not removed, "exactly the five scraps override models are added, none removed")
    check(len(after["generated"]) == BEFORE_COUNT + len(ADDED), f"{BEFORE_COUNT + len(ADDED)} generated files")
    check(modified == sorted([EN_US, SCRAPS_MODEL]), f"only en_us.json and scraps.json are modified: {modified}")
    check(set(changed_inputs) == CHANGED_INPUTS, f"changed generation inputs are exactly the Goal 10A files: {sorted(set(changed_inputs) ^ CHANGED_INPUTS)}")
    for name in added + modified:
        check(after["generated"][name] in digests(GEN / name), f"the stamp records the current bytes of {name}")

    old_bytes = git_show(f"{BASELINE_COMMIT}:src/generated/resources/{EN_US}")
    check(hashlib.sha256(old_bytes).hexdigest() == before["generated"][EN_US], f"the before-stamp en_us.json is the {BASELINE_COMMIT} file")
    old = json.loads(old_bytes.decode("utf-8"))
    new = read(GEN / EN_US)
    check(set(new) - set(old) == NEW_KEYS and set(old) - set(new) == REMOVED, "en_us.json gains the 13 new keys and loses the two removed ones")
    changed = {key for key in set(old) & set(new) if old[key] != new[key]}
    check(changed == set(EN_EXPECTED) - NEW_KEYS - EN_UNCHANGED, f"exactly six English values change: {sorted(changed)}")
    check(all(new[key] == value for key, value in EN_EXPECTED.items()), "the generated English values are the provider texts")
    scraps_old = git_show(f"{BASELINE_COMMIT}:src/generated/resources/{SCRAPS_MODEL}")
    check(hashlib.sha256(scraps_old).hexdigest() == before["generated"][SCRAPS_MODEL]
          and json.loads(scraps_old) == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/scraps"}},
          f"the before-stamp scraps.json is the plain {BASELINE_COMMIT} model")
    scraps_models()
    return {"baseline": str(BEFORE_STAMP.relative_to(ROOT).as_posix()), "generated_added": added, "generated_modified": modified,
            "generated_removed": removed, "changed_inputs": changed_inputs, "generated_count": len(after["generated"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip checks that need a fresh runData")
    args = parser.parse_args()
    source_checks()
    report = {"mode": "source-only" if args.source_only else "full"}
    if not args.source_only:
        report.update(generated_checks())
    report.update({"checks": len(checks), "assertions": checks, "skipped": skipped,
                   "boundary": "Provider, client registration and screen source, generated resources and source assets only; "
                               "no Minecraft model baking, JEI display, rendering or gameplay run."})
    OUT.mkdir(parents=True, exist_ok=True)
    name = "source-check.json" if args.source_only else "generated-check.json"
    (OUT / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 10A resources ({report['mode']}): {len(checks)} checks passed; report {OUT / name}")


if __name__ == "__main__":
    main()
