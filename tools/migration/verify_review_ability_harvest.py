"""Verify the tool-ability harvest fix and the drops batch in an isolated, explicitly modeled Java world.

Persistent barrels and crates harvested by an NTM ability tool (silk touch,
luck/fortune, smelter, shredder and the plain harvest of vein/hammer extra
blocks) must drop exactly one body that carries their own fluid or contents
(crate_keep_contents true) or one plain crate plus the loose contents (false).
The same holds for player mining, Level.destroyBlock(pos, true) and an
item-dropping vanilla explosion, which are modeled from contract-checked
NeoForge source including the explosion's stack merging. Ordinary blocks keep
their ability drops.

The drops batch (DropsBatchRegression.java) adds: exactly one body per
DummyableBlock multiblock (a persistent refinery, a loot-table stand-in and the
footprint-clearing centrifuge) for direct ability mining, vein/hammer/flat-hammer
extras and the EXPLOSION ability, with the pre-fix durability; one BreakEvent,
before anything else happens there, for every extra block that passes
breakExtraBlock's checks, honoring cancellation and pre-cancellation; and
BlockProcessorStandard following only emitted loot with spawnAfterBreak, so
crates drop exactly one crate under every drop policy while barrels, infested
blocks, asbestos bricks and ordinary blocks keep their behavior. A follow-up
adds breakExtraBlock's effectiveness gate (an extra must be a block the held tool
is effective for or shears can cut, SILK passes, an empty hand skips every extra,
and a skipped block gets no BreakEvent, removal or wear) and DummyableBlock.onRemove's
core check (a core never removes the same-block neighbour behind it, a dummy still
removes the part toward its core). Neighbor
updates that drive the multiblock removal cascade are modeled on
CollectingNeighborUpdater.

Only copies extracted production methods, stand-ins, classes and logs into a
unique run directory under --out-root (default
build/migration/review-fixes/ability-harvest). No game/Gradle/network. Checks
source contracts in the cached NeoForge 21.1.228 sources JAR (and the order of
ExplosionVNT.explode in the NEO source) before using that order in the
fixtures. This does not compile entire production classes or establish real
gameplay.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile

from review_fixes.ability_harvest_stubs import PRODUCTION, VNT, build_world, method

ROOT = Path(__file__).resolve().parents[2]
NEOFORGE_SOURCES = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"
SOURCE = ROOT / "src/main/java"
FIXTURE = ROOT / "tools/migration/review_fixes/AbilityHarvestRegression.java"
FIXTURES = (FIXTURE, ROOT / "tools/migration/review_fixes/DropsBatchRegression.java")


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
        # Drops batch: creative breaking, the BreakEvent for extra blocks, neighbor updates and the blocks they reach.
        confirm("net/minecraft/server/level/ServerPlayerGameMode.java", "public boolean destroyBlock(",
                ["block.playerWillDestroy(", "if (this.isCreative())", "removeBlock(pos, blockstate, false)", "return true;",
                 "itemstack.mineBlock("])
        confirm("net/minecraft/server/level/ServerPlayerGameMode.java", "public GameType getGameModeForPlayer(",
                ["return this.gameModeForPlayer;"])
        confirm("net/neoforged/neoforge/common/CommonHooks.java", "public static BlockEvent.BreakEvent fireBlockBreak(",
                ["ItemStack itemstack = player.getMainHandItem();", "!itemstack.getItem().canAttackBlock(state, level, pos, player)",
                 "preCancelEvent = true;", "player.blockActionRestricted(level, pos, gameType)", "preCancelEvent = true;",
                 "state.getBlock() instanceof GameMasterBlock && !player.canUseGameMasterBlocks()", "preCancelEvent = true;",
                 "new BlockEvent.BreakEvent(level, pos, state, player)", "event.setCanceled(preCancelEvent)",
                 "NeoForge.EVENT_BUS.post(event)", "if (event.isCanceled())",
                 "player.connection.send(new ClientboundBlockUpdatePacket(pos, state))", "return event;"])
        confirm("net/minecraft/world/entity/player/Player.java", "public boolean blockActionRestricted(",
                ["if (!gameMode.isBlockPlacingRestricted())", "return false;", "gameMode == GameType.SPECTATOR", "return true;",
                 "this.mayBuild()", "return false;", "itemstack.isEmpty() || !itemstack.canBreakBlockInAdventureMode("])
        confirm("net/minecraft/world/entity/player/Player.java", "public boolean hasInfiniteMaterials(",
                ["return this.abilities.instabuild;"])
        confirm("net/minecraft/world/item/Item.java", "public boolean canAttackBlock(", ["return true;"])
        # Follow-up: ToolAbilityItem.canHarvest's harvest check is the event-wrapped vanilla check; the stub models it as the vanilla value.
        confirm("net/neoforged/neoforge/event/EventHooks.java", "public static boolean doPlayerHarvestCheck(",
                ["player.hasCorrectToolForDrops(state)", "new PlayerEvent.HarvestCheck(player, state, level, pos, vanillaValue)", "return event.canHarvest()"])
        confirm("net/minecraft/world/item/ItemStack.java", "public void hurtAndBreak(int amount, LivingEntity entity, EquipmentSlot slot)",
                ["entity.level() instanceof ServerLevel serverlevel", "this.hurtAndBreak("])
        confirm("net/minecraft/world/item/ItemStack.java", "public void hurtAndBreak(int p_220158_, ServerLevel p_346256_, @Nullable LivingEntity p_220160_, Consumer<Item> p_348596_)",
                ["if (this.isDamageableItem())", "getItem().damageItem(this, p_220158_, p_220160_, p_348596_)",
                 "if (p_220160_ == null || !p_220160_.hasInfiniteMaterials())"])
        confirm("net/minecraft/world/level/block/Block.java", "public BlockState playerWillDestroy(",
                ["level.gameEvent(", "return state;"], absent=("dropResources", "popResource"))
        confirm("net/minecraft/world/level/Level.java", "public boolean setBlock(BlockPos pos, BlockState state, int flags, int recursionLeft)",
                ["levelchunk.setBlockState(pos, state, (flags & 64) != 0)",
                 "this.markAndNotifyBlock(pos, levelchunk, blockstate, state, flags, recursionLeft)"])
        confirm("net/minecraft/world/level/Level.java", "public void markAndNotifyBlock(",
                ["if (blockstate1 == p_46606_)", "if ((p_46607_ & 1) != 0)", "this.blockUpdated(p_46605_, blockstate.getBlock())"])
        confirm("net/minecraft/server/level/ServerLevel.java", "public void blockUpdated(", ["this.updateNeighborsAt(pos, block)"])
        confirm("net/minecraft/server/level/ServerLevel.java", "public void updateNeighborsAt(BlockPos pos, Block block)",
                ["EventHooks.onNeighborNotify(", ").isCanceled();", "this.neighborUpdater.updateNeighborsAtExceptFromFacing(pos, block, null)"])
        updater = "net/minecraft/world/level/redstone/CollectingNeighborUpdater.java"
        confirm(updater, "public void updateNeighborsAtExceptFromFacing(",
                ["this.addAndRun(pos, new CollectingNeighborUpdater.MultiNeighborUpdate(pos.immutable(), block, facing))"])
        confirm(updater, "private void addAndRun(",
                ["boolean flag = this.count > 0;", "this.count >= this.maxChainedNeighborUpdates", "this.count++;",
                 "if (flag)", "this.addedThisLayer.add(updates);", "this.stack.push(updates);", "if (!flag)", "this.runUpdates();"])
        confirm(updater, "private void runUpdates(",
                ["for (int i = this.addedThisLayer.size() - 1; i >= 0; i--)", "this.stack.push(this.addedThisLayer.get(i));",
                 "this.addedThisLayer.clear();", "this.stack.peek();", "while (this.addedThisLayer.isEmpty())",
                 ".runNext(this.level)", "this.stack.pop();", "break;", "this.count = 0;"])
        confirm(updater, "MultiNeighborUpdate(BlockPos sourcePos, Block sourceBlock, @Nullable Direction skipDirection)",
                ["if (NeighborUpdater.UPDATE_ORDER[this.idx] == skipDirection)", "this.idx++;"])
        confirm(updater, "public boolean runNext(Level level)",
                ["this.sourcePos.relative(NeighborUpdater.UPDATE_ORDER[this.idx++])", "level.getBlockState(blockpos)",
                 "NeighborUpdater.executeUpdate(level, blockstate, blockpos, this.sourceBlock, this.sourcePos, false)",
                 "this.idx < NeighborUpdater.UPDATE_ORDER.length && NeighborUpdater.UPDATE_ORDER[this.idx] == this.skipDirection",
                 "return this.idx < NeighborUpdater.UPDATE_ORDER.length;"])
        confirm("net/minecraft/world/level/redstone/NeighborUpdater.java", "Direction[] UPDATE_ORDER = new Direction[]",
                ["Direction.WEST", "Direction.EAST", "Direction.DOWN", "Direction.UP", "Direction.NORTH", "Direction.SOUTH"])
        confirm("net/minecraft/world/level/redstone/NeighborUpdater.java", "static void executeUpdate(",
                ["state.handleNeighborChanged(level, pos, neighborBlock, neighborPos, movedByPiston)"])
        confirm("net/minecraft/world/level/block/state/BlockBehaviour.java", "public void handleNeighborChanged(",
                ["this.getBlock().neighborChanged(this.asState(), level, pos, block, fromPos, isMoving)"])
        confirm("net/minecraft/world/level/block/state/BlockBehaviour.java", "protected void neighborChanged(",
                ["DebugPackets.sendNeighborsUpdatePacket(level, pos)"])
        confirm("net/minecraft/world/Containers.java", "public static void dropContentsOnDestroy(",
                ["if (!state.is(newState.getBlock()))", "level.getBlockEntity(pos) instanceof Container container",
                 "dropContents(level, pos, container)"])
        confirm("net/minecraft/world/level/block/InfestedBlock.java", "protected void spawnAfterBreak(",
                ["super.spawnAfterBreak(state, level, pos, stack, dropExperience)", "GameRules.RULE_DOBLOCKDROPS",
                 "EnchantmentTags.PREVENTS_INFESTED_SPAWNS", "this.spawnInfestation(level, pos)"])
    return records


def source_contracts():
    """The NEO-side order the ExplosionVNT stand-in reproduces (production source, not the JAR)."""
    text = (SOURCE / VNT).read_text(encoding="utf-8")
    body = method(text, "public void explode(")
    ordered = ["boolean processBlocks = blockAllocator != null && blockProcessor != null;",
               "if(processBlocks) affectedBlocks = blockAllocator.allocate(this, level, x, y, z, size);",
               "if(processBlocks) this.compat.getToBlow().addAll(affectedBlocks);",
               "if(processBlocks) blockProcessor.process(this, level, x, y, z, affectedBlocks);"]
    position = 0
    for token in ordered:
        position = body.index(token, position) + len(token)
    return [{"source": "src/main/java/" + VNT, "signature": "public void explode(", "ordered": ordered,
             "start_line": text[:text.index("public void explode(")].count("\n") + 1,
             "sha256": hashlib.sha256(body.encode()).hexdigest()}]


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
    for fixture in FIXTURES:
        (target / fixture.name).write_bytes(fixture.read_bytes())
    commands = [
        [str(java_home / "bin/javac.exe"), "-encoding", "UTF-8", "-d", str(target / "classes"),
         str(target / "AbilityHarvestWorld.java")] + [str(target / fixture.name) for fixture in FIXTURES],
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

# Drops batch anchors: code lines only, so rewording the production comments next to them keeps the harness working.
MINE_SKIP_TEST = "state.getBlock() instanceof DummyableBlock dummy && dummy.findCore(level, pos) != null"
MINE_SKIP = "                        if (" + MINE_SKIP_TEST + ") {\n"
MINE_DAMAGE = "                            damageTool(stack, player, 1);\n"
FIRE = "        if (CommonHooks.fireBlockBreak(level, serverPlayer.gameMode.getGameModeForPlayer(), serverPlayer, pos, state).isCanceled()) return;\n"
SAME = "        if (isMinedStructure(level, pos, refPos)) {\n"
SAME_REMOVE_LINE = "            level.removeBlock(pos, false);\n"
SAME_REMOVE = SAME_REMOVE_LINE + "            damageTool(stack, player, 1);\n"
HARVEST_EXTRA = "        preset.harvestAbility.onHarvestBlock(level, pos, player, refPos);\n"
MINED_CORE = "        return core != null && core.equals(dummy.findCore(level, pos));\n"
EXPLOSION_CHANCE = "new BlockProcessorStandard().withChance((explosion, block, at, chance) -> ToolAbilityItem.isMinedStructure(level, at, pos) ? 0F : 1F)"
EMITTED = "                        if (emitted) {\n"
AFTER_BREAK = "                            state.spawnAfterBreak(serverLevel, pos, ItemStack.EMPTY, false);\n"
GET_DROPS = "                        List<ItemStack> drops = state.getDrops(builder);\n"
EMITTED_DECL = "                        boolean emitted = false;\n"
LOOP_HEAD = "            BlockPos pos = iterator.next();\n            BlockState state = level.getBlockState(pos);\n            Block block = state.getBlock();\n"
EXPLODED = "                state.onBlockExploded(level, pos, explosion.compat);\n"
CRATE_SHELL = "    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new CrateBaseBlockEntity(pos, type.slots); }\n"
CRATE_MARKER = (CRATE_SHELL + "    public void onBlockExploded(BlockState state, Level level, BlockPos pos, Explosion explosion) {\n"
                "        if(level.getBlockEntity(pos) instanceof CrateBaseBlockEntity crate) crate.preventDrop();\n"
                "        super.onBlockExploded(state, level, pos, explosion);\n    }\n")
PRE_FIX_MINE = (MINE_SKIP, MINE_SKIP.replace(MINE_SKIP_TEST, "false"))
PRE_FIX_SAME = (SAME, SAME.replace("isMinedStructure(level, pos, refPos)", "false"))
PRE_FIX_EVENT = (FIRE, "")
PRE_FIX_EXPLOSION = (EXPLOSION_CHANCE, "new BlockProcessorStandard().setAllDrop()")
PRE_FIX_PROCESSOR = (EMITTED, EMITTED.replace("emitted", "false"))
MUTATIONS.update({
    "mine-skip-removed": [PRE_FIX_MINE],
    "mine-skip-no-damage": [(MINE_DAMAGE, "")],
    # Skips every DummyableBlock part, coreless ones included.
    "mine-skip-coreless": [(MINE_SKIP, MINE_SKIP.replace(" && dummy.findCore(level, pos) != null", ""))],
    "same-structure-branch-removed": [PRE_FIX_SAME],
    "same-structure-no-damage": [(SAME_REMOVE, SAME_REMOVE_LINE)],
    "same-structure-harvests": [(SAME_REMOVE, "            this.getConfiguration(stack).getActivePreset().harvestAbility.onHarvestBlock(level, pos, player, refPos);\n")],
    "isMinedStructure-ignores-core": [(MINED_CORE, "        return true;\n")],
    "no-break-event": [PRE_FIX_EVENT],
    "event-cancel-ignored": [(FIRE, FIRE.replace("if (CommonHooks", "CommonHooks").replace(".isCanceled()) return;", ";"))],
    "event-after-harvest": [(FIRE, ""),
                            (SAME_REMOVE, SAME_REMOVE + "            CommonHooks.fireBlockBreak(level, serverPlayer.gameMode.getGameModeForPlayer(), serverPlayer, pos, state);\n"),
                            (HARVEST_EXTRA, HARVEST_EXTRA + "        CommonHooks.fireBlockBreak(level, serverPlayer.gameMode.getGameModeForPlayer(), serverPlayer, pos, state);\n")],
    "explosion-ability-all-drop": [PRE_FIX_EXPLOSION],
    "processor-no-after-break": [PRE_FIX_PROCESSOR],
    # Option (i): spawnAfterBreak before the loot pass, whatever the roll.
    "processor-after-break-before-drops": [(GET_DROPS, AFTER_BREAK + GET_DROPS), (EMITTED, EMITTED.replace("emitted", "false"))],
    "processor-after-break-unconditional": [(EMITTED, EMITTED.replace("emitted", "true"))],
    "processor-after-break-after-removal": [(LOOP_HEAD, LOOP_HEAD + "            boolean emitted = false;\n"), (EMITTED_DECL, ""),
                                            (EMITTED, EMITTED.replace("emitted", "false")),
                                            (EXPLODED, EXPLODED + "                if (emitted) state.spawnAfterBreak((ServerLevel) level, pos, ItemStack.EMPTY, false);\n")],
    # Option (ii): no processor follow-up, a crate onBlockExploded marker instead.
    "crate-exploded-marker": [(EMITTED, EMITTED.replace("emitted", "false")), (CRATE_SHELL, CRATE_MARKER)],
    "drops-batch-pre-fix": [PRE_FIX_MINE, PRE_FIX_SAME, PRE_FIX_EVENT, PRE_FIX_EXPLOSION, PRE_FIX_PROCESSOR],
})

# Follow-up anchors: the effectiveness gate of breakExtraBlock and the core check of DummyableBlock.onRemove (code lines only).
GATE = "        if (!(canHarvest(stack, state, player, level, pos) || canShearBlock(state, stack, level, pos))) return;\n"
EMPTY_HAND = "        if (stack.isEmpty()) return;\n"
SILK_PASS = ("        if (this.getConfiguration(stack).getActivePreset().harvestAbility == IToolHarvestAbility.SILK)\n"
             "            return true;\n")
CORE_CHECK = "            if(!safeRem && !isCore(state)) {\n"
PRE_FIX_GATE = (GATE, "")
PRE_FIX_EMPTY_HAND = (EMPTY_HAND, "")
PRE_FIX_CORE = (CORE_CHECK, CORE_CHECK.replace(" && !isCore(state)", ""))
# Each must make the regression fail with an AssertionError.
MUTATIONS.update({
    # A core removes the same-block neighbour behind it again (the pre-fix onRemove).
    "core-removes-neighbor-behind": [PRE_FIX_CORE],
    # Every block that passes the tool check is an extra again, coal gas, glass and plants included.
    "no-effectiveness-gate": [PRE_FIX_GATE],
    # An empty hand no longer stops breakExtraBlock.
    "no-empty-hand-return": [PRE_FIX_EMPTY_HAND],
    "gate-ignores-shears": [(GATE, GATE.replace(" || canShearBlock(state, stack, level, pos)", ""))],
    # SILK no longer passes canHarvest for a block the tool is not effective for.
    "silk-pass-through-removed": [(SILK_PASS, "")],
    # The gate runs after the BreakEvent, so skipped blocks still fire it.
    "gate-after-break-event": [PRE_FIX_GATE, (FIRE, FIRE + GATE)],
    "followup-pre-fix": [PRE_FIX_CORE, PRE_FIX_GATE, PRE_FIX_EMPTY_HAND],
})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, default=Path("C:/Program Files/Java/jdk-21"))
    parser.add_argument("--out-root", type=Path, default=Path("build/migration/review-fixes/ability-harvest"),
                        help="run directory parent, relative to the NEO root unless absolute")
    args = parser.parse_args()
    out_root = args.out_root if args.out_root.is_absolute() else ROOT / args.out_root
    root = out_root / uuid.uuid4().hex
    root.mkdir(parents=True)

    def inputs():
        hashes = {p: digest(SOURCE / p) for p in PRODUCTION}
        for fixture in FIXTURES:
            hashes[fixture.relative_to(ROOT).as_posix()] = digest(fixture)
        return hashes

    before = inputs()
    evidence = contracts() + source_contracts()
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
    after = inputs()
    assert before == after, "production or fixture inputs changed during verification"
    summary = {"evidence": "extracted-production-method harness; not Minecraft runtime", "source_sha256": before,
               "contracts": len(evidence), "normal": normal, "mutation_detection": results,
               "limitations": ["ServerPlayerGameMode.destroyBlock (survival and creative), CommonHooks.fireBlockBreak, Level.setBlock/"
                               "removeBlock/destroyBlock with markAndNotifyBlock's neighbor notification, CollectingNeighborUpdater, "
                               "LevelChunk.setBlockState, Block.getDrops/dropResources, InfestedBlock.spawnAfterBreak and the vanilla "
                               "explosion drop pass (BlockBehaviour.onExplosionHit, IBlockExtension.onBlockExploded, "
                               "Explosion.finalizeExplosion with its stack merging) are modeled by hand; only their source order is "
                               "checked. Shape updates, NeighborNotifyEvent listeners, comparator updates and client sync are not modeled. "
                               "The game shuffles Explosion.toBlow; the regression runs every order.",
                               "RECURSION's Collections.shuffle resolves to a seeded stand-in, so vein orders are reproducible; the drops "
                               "batch runs three seeds and its oracles do not depend on the order.",
                               "ExplosionVNT is a stand-in whose explode() keeps the source-checked order; BlockAllocatorStandard's rays are "
                               "not modeled: each scenario supplies the affected blocks and their processing order (every permutation of "
                               "small sets). Explosion entity damage, effects, decay radius and fire are not modeled. RandomSource.nextFloat "
                               "is scripted (one value per scenario).",
                               "Crates, barrels, destroyBlock(true) and three multiblocks are covered: the refinery (newBlockEntity and "
                               "getDrops extracted, its core block entity's saved tanks a stand-in string), a loot-table stand-in (one plain "
                               "body for any part) and the centrifuge (footprint clearing extracted). Multiblock slot contents are not "
                               "modeled: the real core and ProxyComboBlockEntity are WorldlyContainers whose contents "
                               "DummyableBlock.onRemove drops through Containers.dropContentsOnDestroy; no harness block entity is a Container.",
                               "Crate contents are stub stacks; a crate's contents drop as one Drop per stack where the game spawns several "
                               "item entities, and saveAdditional is a stand-in.",
                               "The ability path fires no BlockDropsEvent and drops no experience, before and after this fix; "
                               "BlockDropsEvent cancellation, external drop-event policy and client prediction are not covered. The "
                               "BreakEvent bus is a list of listeners; NeoForge listener priorities and receiveCanceled are not modeled, "
                               "and the BreakEvent for the mined block itself is assumed uncancelled.",
                               "Loot tables, NBT, enchantment registries, recipes and config are stand-ins; ordinary blocks are "
                               "modeled as a silk/fortune ore and a block whose loot copies its block entity; the infested block's loot "
                               "(empty without silk touch) and the asbestos gas are stand-ins.",
                               "No Minecraft launch; real gameplay, the real neighbor updater, dedicated server and saved worlds are unverified."]}
    (root / "result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(normal["run"]["output"].strip())
    print(f"Source contracts: {len(evidence)}")
    for label, result in results.items():
        print(f"Mutation {label}: AssertionError: {result['first_failure']}")
    print(f"Mutation detection: {len(results)}/{len(MUTATIONS)}")
    print(f"Evidence: {root}")


if __name__ == "__main__":
    main()
