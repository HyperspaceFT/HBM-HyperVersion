"""Verify the tool-ability harvest fix in an isolated, explicitly modeled Java world.

Persistent barrels and crates harvested by an NTM ability tool (silk touch,
luck/fortune, smelter, shredder and the plain harvest of vein/hammer extra
blocks) must drop exactly one body that carries their own fluid or contents
(crate_keep_contents true) or one plain crate plus the loose contents (false).
The same holds for player mining, Level.destroyBlock(pos, true) and an
item-dropping vanilla explosion, which are modeled from contract-checked
NeoForge source including the explosion's stack merging. Ordinary blocks keep
their ability drops. Only copies extracted production methods, stand-ins, classes and
logs into a unique build/migration/review-fixes/ability-harvest run directory.
No game/Gradle/network. Checks source contracts in the cached NeoForge 21.1.228
sources JAR before using its break, drop and removal order in
AbilityHarvestRegression.java. This does not compile entire production classes
or establish real gameplay.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile

from review_fixes.ability_harvest_stubs import PRODUCTION, build_world, method

ROOT = Path(__file__).resolve().parents[2]
NEOFORGE_SOURCES = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"
SOURCE = ROOT / "src/main/java"
FIXTURE = ROOT / "tools/migration/review_fixes/AbilityHarvestRegression.java"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contracts():
    records = []
    with zipfile.ZipFile(NEOFORGE_SOURCES) as archive:
        def confirm(path, signature, ordered, absent=()):
            text = archive.read(path).decode("utf-8")
            body = method(text, signature)
            position = 0
            for token in ordered:
                # Each token must follow the previous one.
                position = body.index(token, position) + len(token)
            for token in absent:
                assert token not in body, f"unexpected {token} in {path}"
            records.append({"source": path, "signature": signature, "ordered": ordered, "absent": list(absent),
                            "start_line": text[:text.index(signature)].count("\n") + 1,
                            "sha256": hashlib.sha256(body.encode()).hexdigest()})

        confirm("net/minecraft/server/level/ServerPlayerGameMode.java", "public boolean destroyBlock(",
                ["CommonHooks.fireBlockBreak(", "this.level.getBlockEntity(pos)", "block.playerWillDestroy(",
                 "blockstate.canHarvestBlock(", "itemstack.mineBlock(", "removeBlock(pos, blockstate, flag1)",
                 "if (flag1 && flag)", "block.playerDestroy("])
        confirm("net/minecraft/server/level/ServerPlayerGameMode.java", "private boolean removeBlock(",
                ["state.onDestroyedByPlayer(", "if (removed)", "state.getBlock().destroy("])
        confirm("net/neoforged/neoforge/common/extensions/IBlockExtension.java", "default boolean onDestroyedByPlayer(",
                ["level.isClientSide()", "level.removeBlock(pos, false)"])
        confirm("net/minecraft/world/item/ItemStack.java", "public void mineBlock(",
                ["item.mineBlock(this, level, state, pos, player)"])
        confirm("net/minecraft/world/level/block/Block.java", "public static List<ItemStack> getDrops(\n",
                ["LootContextParams.ORIGIN, Vec3.atCenterOf(pos)", "LootContextParams.TOOL, tool",
                 "LootContextParams.THIS_ENTITY, entity", "LootContextParams.BLOCK_ENTITY, blockEntity", "state.getDrops("])
        confirm("net/minecraft/world/level/block/Block.java", "public static void dropResources(\n",
                ["getDrops(", "stopCapturingDrops()", "CommonHooks.handleBlockDrops("])
        confirm("net/minecraft/world/level/block/Block.java", "public void playerDestroy(",
                ["player.awardStat(", "dropResources(state, level, pos, blockEntity, player, tool)"])
        confirm("net/neoforged/neoforge/common/CommonHooks.java", "public static void handleBlockDrops(",
                ["if (!event.isCanceled())", "level.addFreshEntity(entity)",
                 "state.spawnAfterBreak((ServerLevel) level, pos, tool, false)"])
        confirm("net/minecraft/world/level/Level.java", "public boolean destroyBlock(",
                ["if (dropBlock)", "Block.dropResources(", "ItemStack.EMPTY", "this.setBlock("])
        confirm("net/minecraft/world/level/LevelWriter.java", "default boolean destroyBlock(BlockPos pos, boolean dropBlock)",
                ["this.destroyBlock(pos, dropBlock, null)"])
        confirm("net/minecraft/world/level/LevelWriter.java", "default boolean destroyBlock(BlockPos pos, boolean dropBlock, @Nullable Entity entity)",
                ["this.destroyBlock(pos, dropBlock, entity, 512)"])
        confirm("net/minecraft/world/level/block/state/BlockBehaviour.java", "protected void onExplosionHit(",
                ["state.canDropFromExplosion(", "LootContextParams.TOOL, ItemStack.EMPTY", "state.spawnAfterBreak(serverlevel, pos, ItemStack.EMPTY, flag)",
                 "state.getDrops(", "dropConsumer.accept(", "state.onBlockExploded(level, pos, explosion)"])
        confirm("net/minecraft/world/level/block/state/BlockBehaviour.java", "public void onExplosionHit(",
                ["this.getBlock().onExplosionHit(this.asState(), level, pos, explosion, dropConsumer)"])
        confirm("net/neoforged/neoforge/common/extensions/IBlockExtension.java", "default void onBlockExploded(",
                ["level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3)", "wasExploded("])
        confirm("net/neoforged/neoforge/common/extensions/IBlockExtension.java", "default boolean canDropFromExplosion(",
                ["state.getBlock().dropFromExplosion(explosion)"])
        confirm("net/minecraft/world/level/block/Block.java", "public boolean dropFromExplosion(", ["return true;"])
        confirm("net/neoforged/neoforge/common/extensions/IBlockStateExtension.java", "default void onBlockExploded(",
                ["self().getBlock().onBlockExploded(self(), level, pos, explosion)"])
        confirm("net/neoforged/neoforge/common/extensions/IBlockStateExtension.java", "default boolean canDropFromExplosion(",
                ["self().getBlock().canDropFromExplosion(self(), level, pos, explosion)"])
        confirm("net/minecraft/world/level/Explosion.java", "public void finalizeExplosion(",
                ["onExplosionHit(", "addOrAppendStack(list,", "Block.popResource(this.level, pair.getSecond(), pair.getFirst())"])
        confirm("net/minecraft/world/level/Explosion.java", "private static void addOrAppendStack(",
                ["ItemEntity.areMergable(itemstack, stack)", "ItemEntity.merge(itemstack, stack, 16)", "if (stack.isEmpty())", "drops.add(Pair.of(stack, pos))"])
        confirm("net/minecraft/world/entity/item/ItemEntity.java", "public static boolean areMergable(",
                ["originStack.getCount() + destinationStack.getCount() > originStack.getMaxStackSize()", "ItemStack.isSameItemSameComponents("])
        confirm("net/minecraft/world/entity/item/ItemEntity.java", "public static ItemStack merge(",
                ["Math.min(Math.min(destinationStack.getMaxStackSize(), amount) - destinationStack.getCount(), originStack.getCount())",
                 "destinationStack.copyWithCount(destinationStack.getCount() + i)", "originStack.shrink(i)"])
        confirm("net/minecraft/world/Containers.java", "private static void dropContents(Level level, double x, double y, double z, Container inventory)",
                ["dropItemStack(level, x, y, z, inventory.getItem(i))"])
        confirm("net/minecraft/world/Containers.java", "public static void dropItemStack(",
                ["while (!stack.isEmpty())", "stack.split(", "level.addFreshEntity("])
        confirm("net/minecraft/world/level/Level.java", "public boolean removeBlock(",
                ["this.setBlock(pos, fluidstate.createLegacyBlock(), 3 | (isMoving ? 64 : 0))"])
        confirm("net/minecraft/world/level/Level.java", "public boolean setBlock(BlockPos pos, BlockState state, int flags, int recursionLeft)",
                ["levelchunk.setBlockState(pos, state, (flags & 64) != 0)", "if (blockstate == null)", "return false;"])
        confirm("net/minecraft/world/level/chunk/LevelChunk.java", "public BlockState setBlockState(",
                ["levelchunksection.setBlockState(", "if (blockstate == state)", "return null;",
                 "if (!this.level.isClientSide)", "blockstate.onRemove(this.level, pos, state, isMoving)"])
        confirm("net/minecraft/world/level/block/state/BlockBehaviour.java", "protected void onRemove(",
                ["state.hasBlockEntity() && !state.is(newState.getBlock())", "level.removeBlockEntity(pos)"])
        confirm("net/minecraft/world/level/block/state/BlockBehaviour.java", "public void spawnAfterBreak(",
                ["this.getBlock().spawnAfterBreak(this.asState(), level, pos, stack, dropExperience)"])
        # NeoForge moved ore experience to getExpDrop/BlockDropsEvent; the dropExperience flag pays out nothing here.
        confirm("net/minecraft/world/level/block/DropExperienceBlock.java", "protected void spawnAfterBreak(",
                ["super.spawnAfterBreak("], absent=("tryDropExperience", "popExperience"))
    return records


def first_assertion(output):
    """The label of the first failing regression assertion in a run log, or None."""
    for line in output.splitlines():
        if "java.lang.AssertionError" in line:
            return line.split("java.lang.AssertionError", 1)[1].lstrip(": ").strip()
    return None


def run_world(root, label, world, java_home, expected_success=True):
    target = root / label
    target.mkdir(parents=True)
    (target / "AbilityHarvestWorld.java").write_text(world, encoding="utf-8")
    (target / FIXTURE.name).write_bytes(FIXTURE.read_bytes())
    commands = [
        [str(java_home / "bin/javac.exe"), "-encoding", "UTF-8", "-d", str(target / "classes"),
         str(target / "AbilityHarvestWorld.java"), str(target / FIXTURE.name)],
        [str(java_home / "bin/java.exe"), "-cp", str(target / "classes"), "abilityharvest.AbilityHarvestRegression"],
    ]
    result = {}
    for index, command in enumerate(commands):
        proc = subprocess.run(command, cwd=target, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (target / ("compile.log" if index == 0 else "run.log")).write_text(proc.stdout + proc.stderr, encoding="utf-8")
        result["compile" if index == 0 else "run"] = {"command": command, "returncode": proc.returncode,
                                                       "output": proc.stdout + proc.stderr}
        if index == 0 and proc.returncode:
            raise RuntimeError(f"compile failed: {target / 'compile.log'}\n{proc.stderr}")
        if index == 1 and (proc.returncode == 0) != expected_success:
            raise RuntimeError(f"unexpected regression result: {target / 'run.log'}\n{proc.stdout}{proc.stderr}")
        if index == 1 and not expected_success:
            # A mutation must be caught by a regression assertion, not by a crash or an unrelated failure.
            result["first_failure"] = first_assertion(proc.stdout + proc.stderr)
            if result["first_failure"] is None:
                raise RuntimeError(f"mutation failed without an AssertionError: {target / 'run.log'}\n{proc.stdout}{proc.stderr}")
    return result


MARKER = "        level.getBlockState(pos).spawnAfterBreak((ServerLevel) level, pos, player.getMainHandItem(), false);\n"
REMOVE = "        level.removeBlock(pos, false);\n"
OWN = "Block.getDrops(state, (ServerLevel) level, pos, level.getBlockEntity(pos), player, player.getMainHandItem())"
REF = "Block.getDrops(state, (ServerLevel) level, refPos, level.getBlockEntity(refPos), player, player.getMainHandItem())"
DEFAULT_DROPS = f"        List<ItemStack> drops = {OWN};\n        harvestBlock(level, pos, player, refPos, drops);"
SMELTER_DROPS = f"            List<ItemStack> drops = {OWN};\n            boolean changed = false;"
SMELTER_RETRY = f"harvestBlock(level, pos, player, refPos, {OWN});"

# Each mutation must make the regression fail. "pre-fix" restores the harvest path as it was before this fix.
MUTATIONS = {
    "no-loot-marker": [(MARKER, "")],
    "marker-after-removal": [(MARKER + REMOVE, REMOVE + MARKER)],
    "drops-from-refPos": [(DEFAULT_DROPS, DEFAULT_DROPS.replace(OWN, REF))],
    "smelter-drops-from-refPos": [(SMELTER_DROPS, SMELTER_DROPS.replace(OWN, REF))],
    "pre-fix": [(MARKER, ""), (DEFAULT_DROPS, DEFAULT_DROPS.replace(OWN, REF)),
                (SMELTER_DROPS, SMELTER_DROPS.replace(OWN, REF)), (SMELTER_RETRY, SMELTER_RETRY.replace(OWN, REF))],
    "no-barrel-marker": [("            // destroyBlock(true) emits the persistent loot before removing the block; do not emit it again in onRemove.\n"
                          "            barrel.preventDrop();", "            /* no barrel marker */")],
    "no-crate-marker": [("crate.preventDrop();", "/* no crate marker */")],
    "crate-keep-branch-ignores-marker": [("if(crate.shouldDrop()) for(ItemStack stack : crate.getDrops(this))", "for(ItemStack stack : crate.getDrops(this))")],
    "crate-loose-branch-ignores-marker": [("if(crate.shouldDrop()) Block.popResource(level, pos, new ItemStack(this));", "Block.popResource(level, pos, new ItemStack(this));")],
    "crate-loot-ignores-config": [("        if(!NtmConfig.SERVER.CRATE_KEEP_CONTENTS.get()) return new ArrayList<>(List.of(new ItemStack(this)));\n", "")],
    "marker-empty-tool": [(MARKER, MARKER.replace("player.getMainHandItem(), false)", "ItemStack.EMPTY, false)"))],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, default=Path("C:/Program Files/Java/jdk-21"))
    args = parser.parse_args()
    root = ROOT / "build/migration/review-fixes/ability-harvest" / uuid.uuid4().hex
    root.mkdir(parents=True)
    before = {p: digest(SOURCE / p) for p in PRODUCTION}
    before["tools/migration/review_fixes/AbilityHarvestRegression.java"] = digest(FIXTURE)
    evidence = contracts()
    (root / "source-contracts.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    world = build_world(SOURCE)
    normal = run_world(root, "normal", world, args.java_home)
    results = {}
    for label, edits in MUTATIONS.items():
        mutated = world
        for old, new in edits:
            assert mutated.count(old) == 1, f"mutation anchor count: {label}: {old!r}"
            mutated = mutated.replace(old, new)
        results[label] = run_world(root, label, mutated, args.java_home, False)
    after = {p: digest(SOURCE / p) for p in PRODUCTION}
    after["tools/migration/review_fixes/AbilityHarvestRegression.java"] = digest(FIXTURE)
    assert before == after, "production or fixture inputs changed during verification"
    summary = {"evidence": "extracted-production-method harness; not Minecraft runtime", "source_sha256": before,
               "contracts": len(evidence), "normal": normal, "mutation_detection": results,
               "limitations": ["ServerPlayerGameMode.destroyBlock, Level.setBlock/removeBlock/destroyBlock, LevelChunk.setBlockState, "
                               "Block.getDrops/dropResources and the vanilla explosion drop pass (BlockBehaviour.onExplosionHit, "
                               "IBlockExtension.onBlockExploded, Explosion.finalizeExplosion with its stack merging) are modeled by hand; "
                               "only their source order is checked. The game shuffles Explosion.toBlow; the regression runs every order.",
                               "Crates, barrels and destroyBlock(true) are covered. Crate contents are stub stacks; a crate's contents "
                               "drop as one Drop per stack where the game spawns several item entities, and saveAdditional is a stand-in.",
                               "The ability path fires no BlockDropsEvent and drops no experience, before and after this fix; "
                               "BlockDropsEvent cancellation, external drop-event policy, BreakEvent for extra blocks and client "
                               "prediction are not covered.",
                               "The EXPLOSION area ability (ExplosionVNT) and multiblock DummyableBlock cores are not modeled; "
                               "explosions with a decay radius, an indirect player source or other block-interaction modes are not either.",
                               "Loot tables, NBT, enchantment registries, recipes and config are stand-ins; ordinary blocks are "
                               "modeled as a silk/fortune ore and a block whose loot copies its block entity.",
                               "No Minecraft launch; real gameplay, dedicated server and saved worlds are unverified."]}
    (root / "result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(normal["run"]["output"].strip())
    print(f"Source contracts: {len(evidence)}")
    for label, result in results.items():
        print(f"Mutation {label}: AssertionError: {result['first_failure']}")
    print(f"Mutation detection: {len(results)}/{len(MUTATIONS)}")
    print(f"Evidence: {root}")


if __name__ == "__main__":
    main()
