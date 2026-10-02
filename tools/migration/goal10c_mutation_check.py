"""Revert or break each Goal 10C production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile
or only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java is never edited: every mutation is applied to a fresh copy under build/migration/goal10c, and the
source tree's hashes are compared before and after the run.
"""

from pathlib import Path
import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
WORK = ROOT / "build/migration/goal10c"
LOG = WORK / "mutation_check.log"

ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
OVEN = "com/hbm/blocks/machine/heater/HeaterOvenBlock.java"
FURNACE = "com/hbm/blockentity/machine/MachineElectricFurnaceBlockEntity.java"
FURNACE_BLOCK = "com/hbm/blocks/machine/MachineElectricFurnaceBlock.java"
MENU = "com/hbm/inventory/menus/MachineElectricFurnaceMenu.java"
SLOT = "com/hbm/inventory/SlotSmeltingOutput.java"
PROVIDER = "com/hbm/datagen/NtmRecipeProvider.java"

VANILLA_OVEN = """                        new ComparableStack(NtmItems.INGOT_FIREBRICK.get(), 16),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 4),
                        new ComparableStack(Items.COPPER_INGOT, 8)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_OVEN.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));
"""
RECYCLING = """        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new ComparableStack(NtmBlocks.HEATER_OVEN.get()),
                new AnvilOutput[] {
                        new AnvilOutput(new ItemStack(NtmItems.INGOT_FIREBRICK.get(), 16)),
                        new AnvilOutput(new ItemStack(NtmItems.INGOT_COPPER.get(), 8))
                }
        ).setTier(2).setOverlay(OverlayType.RECYCLING));

"""
SERVER_ONLY = """        if(this.player instanceof ServerPlayer serverPlayer && this.removeCount > 0) {
            ServerLevel level = serverPlayer.serverLevel();
            awardExperience(level, serverPlayer, this.removeCount, getSmeltingExperience(level, stack));
        }
"""
ANY_SIDE = """        if(this.removeCount > 0) {
            ServerLevel level = (ServerLevel) this.player.level();
            awardExperience(level, this.player, this.removeCount, getSmeltingExperience(level, stack));
        }
"""
QUICK_CRAFT = "                if(index == MachineElectricFurnaceBlockEntity.SLOT_OUTPUT) slot.onQuickCraft(stack, ret);\n"

# (label, file, [(old, new), ...]). Every anchor must occur exactly once; every file is compiled or read by verify_goal10c.py.
MUTATIONS = [
    ("oven removal range back to -2..2 / -1..2 / -2..2", OVEN,
     [("this.clearMatching(level, center, -1, 1, 0, 0, -1, 1);", "this.clearMatching(level, center, -2, 2, -1, 2, -2, 2);")]),
    ("oven removal: a missing core falls back to the broken position", OVEN,
     [("        if(center == null) return;\n", "        if(center == null) center = pos;\n")]),
    ("oven construction: 15 firebricks instead of 16", ANVIL,
     [(VANILLA_OVEN, VANILLA_OVEN.replace("INGOT_FIREBRICK.get(), 16)", "INGOT_FIREBRICK.get(), 15)"))]),
    ("oven construction: anvil tier 1 instead of 2", ANVIL,
     [(VANILLA_OVEN, VANILLA_OVEN.replace(".setTier(2)", ".setTier(1)"))]),
    ("oven recycling entry removed", ANVIL, [(RECYCLING, "")]),
    ("speed upgrade: 20 ticks per level instead of 25", FURNACE,
     [("this.maxProgress -= speedLevel * 25;", "this.maxProgress -= speedLevel * 20;")]),
    ("power upgrade: -10 HE/t per level instead of -15", FURNACE,
     [("this.consumption -= powerLevel * 15;", "this.consumption -= powerLevel * 10;")]),
    ("no cooldown after a power shortfall (20 -> 0)", FURNACE,
     [("            this.cooldown = COOLDOWN;\n", "            this.cooldown = 0;\n")]),
    ("progress kept when power or output space is missing", FURNACE,
     [("            // Losing power or a blocked output loses the progress, as upstream.\n            this.progress = 0;\n",
       "            // Losing power or a blocked output loses the progress, as upstream.\n")]),
    ("LIT trigger without the progress == 0 condition", FURNACE,
     [("if(this.hasPower() && this.canProcess() && this.progress == 0) {", "if(this.hasPower() && this.canProcess()) {")]),
    ("LIT updated on every tick (flicker between items)", FURNACE,
     [("            trigger = false;\n", "            trigger = true;\n")]),
    ("automation may extract slot 1", FURNACE,
     [("        return index == SLOT_OUTPUT;\n", "        return index == SLOT_OUTPUT || index == SLOT_INPUT;\n")]),
    ("getSlotsForFace includes the upgrade slot 3", FURNACE,
     [("new int[] { SLOT_BATTERY, SLOT_INPUT, SLOT_OUTPUT };", "new int[] { SLOT_BATTERY, SLOT_INPUT, SLOT_OUTPUT, SLOT_UPGRADE };")]),
    ("slot 1 accepts anything", FURNACE,
     [("if(slot == SLOT_INPUT) return !this.getSmeltingResult(stack).isEmpty();", "if(slot == SLOT_INPUT) return true;")]),
    ("output limit: one free spot as upstream (a 2-item result overflows 64)", FURNACE,
     [("return output.getCount() + result.getCount() <= Math.min(output.getMaxStackSize(), this.getMaxStackSize());",
       "return output.getCount() < Math.min(output.getMaxStackSize(), this.getMaxStackSize());")]),
    ("NBT key progress renamed (save and load)", FURNACE,
     [('tag.putInt("progress", this.progress);', 'tag.putInt("prog", this.progress);'),
      ('tag.getInt("progress")', 'tag.getInt("prog")')]),
    ("the block drops its contents on a LIT change", FURNACE_BLOCK,
     [("        if(!state.is(newState.getBlock())) {\n", "        if(true) {\n")]),
    ("experience awarded on the client too", SLOT, [(SERVER_ONLY, ANY_SIDE)]),
    ("the take count is not reset (experience paid again)", SLOT, [("        this.removeCount = 0;\n", "")]),
    ("experience doubled on shift-click", MENU, [(QUICK_CRAFT, QUICK_CRAFT + QUICK_CRAFT)]),
    ("a hotbar-key swap pays no experience (onSwapCraft removed)", SLOT,
     [("    protected void onSwapCraft(int amount) {\n        this.removeCount += amount;\n    }\n",
       "    protected void onSwapCraft(int amount) {\n    }\n")]),
    ("experience of 1 or more per item paid in full (Minecraft 1.21) instead of 1 per item", SLOT,
     [("            amount = count;\n", "            amount = Mth.floor(count * experience);\n")]),
    ("particles behind the lit furnace instead of in front", FURNACE_BLOCK,
     [("dir.getStepX() * 0.52D", "-dir.getStepX() * 0.52D"), ("dir.getStepZ() * 0.52D", "-dir.getStepZ() * 0.52D")]),
    ("furnace recipe pattern changed in the provider", PROVIDER,
     [('                .pattern("WFW")\n                .pattern("RRR")\n                .define(\'B\', NtmItems.INGOT_BERYLLIUM.get())',
       '                .pattern("WFW")\n                .pattern("WRW")\n                .define(\'B\', NtmItems.INGOT_BERYLLIUM.get())')]),
]


def tree_hash(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def run(source, label, stream):
    command = [sys.executable, "-B", "-X", "utf8", "-c",
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal10c as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(WORK / "mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    failures = [line.strip() for line in output.splitlines() if line.startswith("AssertionError in ")]
    other = next((line.strip() for line in output.splitlines() if line.startswith("Exception in ") or "error:" in line), "")
    stream.write(f"== {label} ==\nreturncode: {result.returncode}\n" + "\n".join(failures or [other]) + "\n")
    stream.flush()
    return result.returncode, failures, other


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="source root to mutate (default src/main/java); e.g. a copy with a proposed fix, for diagnostics")
    parser.add_argument("--log", type=Path, default=LOG)
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    before = tree_hash(args.source)
    detected, missed, broken = 0, [], []
    WORK.mkdir(parents=True, exist_ok=True)
    # The mutated copies live under build/migration/goal10c and are removed afterwards.
    with args.log.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory(dir=WORK) as temp:
        stream.write(f"source: {args.source}\nsource tree sha256 before: {before}\n")
        code, failures, other = run(args.source, "baseline", stream)
        if code or failures:
            raise SystemExit(f"baseline regression fails ({failures or other or 'nonzero exit'}); see {args.log}")
        print("baseline: passed", flush=True)
        for label, name, replacements in MUTATIONS:
            copy = Path(temp) / "java"
            if copy.exists():
                shutil.rmtree(copy)
            shutil.copytree(args.source, copy)
            path = copy / name
            text = path.read_text(encoding="utf-8")
            for old, new in replacements:
                if text.count(old) != 1:
                    raise SystemExit(f"mutation anchor not unique for: {label}: {old[:80]}")
                text = text.replace(old, new)
            path.write_text(text, encoding="utf-8")
            code, failures, other = run(copy, label, stream)
            if failures:
                detected += 1
                print(f"detected: {label} -> {failures[0].removeprefix('AssertionError in ')[:220]}"
                      + (f" (+{len(failures) - 1} more sections)" if len(failures) > 1 else ""), flush=True)
                stream.write("detected: yes\n")
            elif code:
                broken.append(label)
                print(f"ERROR (no assertion; {other or 'nonzero exit'}): {label}", flush=True)
                stream.write("detected: no (did not reach an assertion)\n")
            else:
                missed.append(label)
                print(f"NOT DETECTED: {label}", flush=True)
                stream.write("detected: no\n")
        after = tree_hash(args.source)
        stream.write(f"source tree sha256 after: {after}\n")
    print(f"{detected}/{len(MUTATIONS)} Goal 10C decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
