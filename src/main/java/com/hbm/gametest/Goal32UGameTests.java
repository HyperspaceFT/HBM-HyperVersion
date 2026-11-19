package com.hbm.gametest;

import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.handler.radiation.ChunkRadiationHandler;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.main.NuclearTechMod;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.item.FallingBlockEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.chunk.status.ChunkType;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.phys.AABB;
import net.neoforged.neoforge.event.level.ChunkDataEvent;
import net.neoforged.neoforge.event.level.ChunkEvent;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.registries.DeferredBlock;
import org.slf4j.Logger;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal32U: the chunk radiation kept and saved across a chunk unload, the meltdown gas's dense radon, and the 28 blocks that
 * add radiation to their chunk (storage blocks, waste blocks, the yellowcake block and the schrabidium ore). Same template and conventions as
 * {@link Goal32TGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at 5995e0f7d, cited beside each group of checks (ChunkRadiationHandlerSimple.java:148-183;
 * BlockGasMeltdown.java:71-92; BlockHazard.java:120-146,159-170; BlockNuclearWaste.java:13-23; BlockHazardFalling.java:39-66; BlockOre.java:39-43,
 * 199-226; HazardRegistry.java:84-142,215-217,292-321,474; OreDictManager.java:347-372,875-876; ModBlocks.java:1251,1341-1425,2572-2576;
 * ItemBlockBase.java:83-90), not from the NEO implementation. Two rules have no original counterpart and are asserted as the signed requirement of
 * migration/GOAL32U.md section 1: the unload handler marks the chunk unsaved when its value differs from the last loaded or saved value, and not
 * otherwise. The original's restart behaviour (rad is a field of the block singleton, assigned only when a block is placed) is asserted as signed
 * in section 3 by setting that field to 0 through reflection, which is what a fresh process holds before any placement.
 * <p>
 * Real classes and state: ChunkRadiationManager.proxy's own load, save and unload handlers called with real NeoForge events on the loaded test
 * chunk (the engine's order, the unload event and then the save, is proven by the stability scenario reruns that read the region file, not here);
 * the registered blocks placed with setBlock flag 3 so their onPlace runs, their scheduled tick and random tick called directly with a
 * scripted RandomSource, the level's block tick schedule, a real falling block entity. Each increment is measured on a chunk value first set to 0
 * and read right after the call, in the same server tick, then the chunk value, the blocks and any rad field are restored in a finally block, so
 * no radiation spreads to or destroys the neighbouring tests (block_polonium alone adds 75; world destruction starts at 10). Not evidence: a real
 * client (display effects, steam), a dedicated server with real players, a real chunk unload or server restart, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal32UGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-32u]";

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    private static String name(Block block) {
        return BuiltInRegistries.BLOCK.getKey(block).toString();
    }

    /**
     * A RandomSource that answers nextInt(bound) from a table keyed by the bound and fails the test on any other bound, so a tick's chance
     * rolls are fixed instead of looped on.
     */
    private static final class ScriptedRandom extends LegacyRandomSource {
        private final Map<Integer, Integer> answers;

        ScriptedRandom(Map<Integer, Integer> answers) {
            super(0L);
            this.answers = answers;
        }

        @Override
        public int nextInt(int bound) {
            Integer a = answers.get(bound);
            if(a == null) throw new GameTestAssertException("unexpected nextInt(" + bound + ") with scripted answers " + answers);
            return a;
        }
    }

    private static boolean scheduled(ServerLevel level, BlockPos abs, Block block) {
        return level.getBlockTicks().hasScheduledTick(abs, block);
    }

    private static void clearTicks(ServerLevel level, BlockPos abs) {
        level.getBlockTicks().clearArea(new BoundingBox(abs));
    }

    private static boolean close(float actual, float expected) {
        return Math.abs(actual - expected) <= 1.0E-5F * Math.max(1F, Math.abs(expected));
    }

    // ---------------------------------------------------------------- 1. chunk radiation across an unload

    private static final String KEY = "hfr_simple_radiation";

    private static void load(ChunkRadiationHandler rad, LevelChunk chunk, CompoundTag data) {
        rad.receiveChunkLoad(new ChunkDataEvent.Load(chunk, data, ChunkType.LEVELCHUNK));
    }

    private static CompoundTag stored(float value) {
        CompoundTag tag = new CompoundTag();
        tag.putFloat(KEY, value);
        return tag;
    }

    private static CompoundTag save(ChunkRadiationHandler rad, LevelChunk chunk, ServerLevel level) {
        ChunkDataEvent.Save event = new ChunkDataEvent.Save(chunk, level, new CompoundTag());
        rad.receiveChunkSave(event);
        return event.getData();
    }

    private static void unload(ChunkRadiationHandler rad, LevelChunk chunk) {
        rad.receiveChunkUnload(new ChunkEvent.Unload(chunk));
    }

    // Original ChunkRadiationHandlerSimple.java:148-156 (load puts the saved float, 0 for a missing key, over the table's value), :160-170 (save
    // writes the table's value, 0 for no entry), :174-183 (unload calls radiation.remove(event.getChunk()), a Chunk on a ChunkCoordIntPair map, so
    // the entry stays). The unsaved mark on unload follows migration/GOAL32U.md section 1 (口径 and 改法的方向): marked when the value at unload
    // differs from the value of the last load or save, not marked when equal. The engine's order (ChunkEvent.Unload, then save only if unsaved)
    // is proven by the stability scenario reruns, not by this test, which calls the handlers in that order itself.
    @GameTest(template = TEMPLATE, batch = "hbm32u_chunk_radiation_unload_save", timeoutTicks = 100)
    public static void chunk_radiation_unload_save(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    check(NtmConfig.COMMON.ENABLE_CHUNK_RADS.get(), "chunk radiation is disabled in the common config; the checks need it enabled");
                    ServerLevel level = helper.getLevel();
                    ChunkRadiationHandler rad = ChunkRadiationManager.proxy;
                    BlockPos abs = helper.absolutePos(new BlockPos(8, 1, 8));
                    LevelChunk chunk = level.getChunkAt(abs);
                    float before = rad.getRadiation(level, abs);
                    try {
                        // a. A value that spread to the chunk without marking it: saved on unload, entry kept, read back on the next load.
                        load(rad, chunk, stored(2.0F));
                        check(rad.getRadiation(level, abs) == 2.0F, "load of 2.0 left the table at " + rad.getRadiation(level, abs));
                        rad.setRadiation(level, abs, 7.5F);
                        chunk.setUnsaved(false);
                        unload(rad, chunk);
                        check(chunk.isUnsaved(), "unload with 7.5 against a loaded 2.0 did not mark the chunk unsaved");
                        check(rad.getRadiation(level, abs) == 7.5F, "unload removed or changed the entry: getRadiation " + rad.getRadiation(level, abs));
                        CompoundTag saved = save(rad, chunk, level);
                        check(saved.contains(KEY, Tag.TAG_FLOAT), "save after unload wrote no " + KEY + ": " + saved);
                        check(saved.getFloat(KEY) == 7.5F, "save after unload wrote " + saved.getFloat(KEY) + ", the value before unload was 7.5");
                        check(rad.getRadiation(level, abs) == 7.5F, "save after unload removed the entry: getRadiation " + rad.getRadiation(level, abs));
                        rad.setRadiation(level, abs, 3.0F); // the unloaded chunk's entry keeps spreading and decaying meanwhile
                        load(rad, chunk, saved);
                        check(rad.getRadiation(level, abs) == 7.5F, "reload of the saved 7.5 left the table at " + rad.getRadiation(level, abs));

                        // b. A value that decayed to 0 after a nonzero load: marked and saved as 0, so the old value is not read back.
                        load(rad, chunk, stored(4.0F));
                        rad.setRadiation(level, abs, 0F);
                        chunk.setUnsaved(false);
                        unload(rad, chunk);
                        check(chunk.isUnsaved(), "unload with 0 against a loaded 4.0 did not mark the chunk unsaved");
                        CompoundTag zero = save(rad, chunk, level);
                        check(zero.contains(KEY, Tag.TAG_FLOAT) && zero.getFloat(KEY) == 0F, "save after decay to 0 wrote " + zero);
                        load(rad, chunk, zero);
                        check(rad.getRadiation(level, abs) == 0F, "reload of the saved 0 left the table at " + rad.getRadiation(level, abs));

                        // c. A value equal to the last loaded one: not marked (the engine then skips the save, so the next load reads the same file).
                        load(rad, chunk, stored(5.0F));
                        chunk.setUnsaved(false);
                        unload(rad, chunk);
                        check(!chunk.isUnsaved(), "unload with 5.0 equal to the loaded 5.0 marked the chunk unsaved");
                        check(rad.getRadiation(level, abs) == 5.0F, "unload changed the entry: getRadiation " + rad.getRadiation(level, abs));
                        load(rad, chunk, stored(5.0F));
                        check(rad.getRadiation(level, abs) == 5.0F, "reload of 5.0 left the table at " + rad.getRadiation(level, abs));

                        // d. A missing key loads as 0; a periodic save (no unload) becomes the value compared at the next unload.
                        load(rad, chunk, new CompoundTag());
                        check(rad.getRadiation(level, abs) == 0F, "load without " + KEY + " left the table at " + rad.getRadiation(level, abs));
                        chunk.setUnsaved(false);
                        unload(rad, chunk);
                        check(!chunk.isUnsaved(), "unload with 0 against a loaded 0 (no key) marked the chunk unsaved");
                        load(rad, chunk, new CompoundTag());
                        rad.setRadiation(level, abs, 6.0F);
                        CompoundTag periodic = save(rad, chunk, level);
                        check(periodic.getFloat(KEY) == 6.0F, "periodic save wrote " + periodic.getFloat(KEY) + ", table value 6.0");
                        chunk.setUnsaved(false);
                        unload(rad, chunk);
                        check(!chunk.isUnsaved(), "unload with 6.0 equal to the last saved 6.0 marked the chunk unsaved");
                        load(rad, chunk, periodic);
                        check(rad.getRadiation(level, abs) == 6.0F, "reload of the periodic 6.0 left the table at " + rad.getRadiation(level, abs));
                        LOGGER.info("{} chunk_radiation_unload_save: chunk {} saved 7.5 after unload (marked), 0 after decay (marked), 5.0 and 6.0 unchanged (not marked)", TAG, chunk.getPos());
                    } finally {
                        save(rad, chunk, level); // a throwaway save ends any unload this test left open
                        rad.setRadiation(level, abs, before);
                    }
                    passed("chunk_radiation_unload_save").run();
                }))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. meltdown gas

    // Original BlockGasMeltdown.java:75-79: dir = ForgeDirection.getOrientation(rand.nextInt(6)); on rand.nextInt(7) == 0 and air at x+dir the
    // neighbour (not the gas cell) becomes gas_radon_dense; :85 rand.nextInt(350) == 0 removes the gas (answered 1 here). ForgeDirection's order
    // DOWN, UP, NORTH, SOUTH, WEST, EAST (1.7.10 Forge, not in either repository) is the order of Direction.values(). The gas cell is enclosed in
    // stone except the chosen neighbour, so the movement of GasBaseBlock (level random) finds no air once the radon is there.
    @GameTest(template = TEMPLATE, batch = "hbm32u_meltdown_gas_dense_radon", timeoutTicks = 100)
    public static void meltdown_gas_dense_radon(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    ChunkRadiationHandler rad = ChunkRadiationManager.proxy;
                    BlockPos p = helper.absolutePos(new BlockPos(8, 4, 8));
                    Block gas = NtmBlocks.GAS_MELTDOWN.get();
                    Block radon = NtmBlocks.GAS_RADON_DENSE.get();
                    float before = rad.getRadiation(level, p);
                    try {
                        for(Direction dir : Direction.values()) {
                            BlockPos n = p.relative(dir);

                            // air neighbour, chance hit: dense radon in the neighbour, the gas cell stays meltdown gas
                            enclose(level, p, gas, dir, Blocks.AIR.defaultBlockState());
                            gas.defaultBlockState().tick(level, p, new ScriptedRandom(Map.of(6, dir.ordinal(), 7, 0, 350, 1)));
                            check(level.getBlockState(n).is(radon), "meltdown gas toward " + dir + " (air, nextInt(7) = 0) left " + level.getBlockState(n) + " in the neighbour");
                            check(level.getBlockState(p).is(gas), "meltdown gas toward " + dir + ": the gas cell became " + level.getBlockState(p));
                            for(Direction other : Direction.values()) {
                                if(other != dir) check(level.getBlockState(p.relative(other)).is(Blocks.STONE), "meltdown gas toward " + dir + " changed the " + other + " neighbour to " + level.getBlockState(p.relative(other)));
                            }

                            // non-air neighbour, chance hit: nothing placed
                            enclose(level, p, gas, dir, Blocks.STONE.defaultBlockState());
                            gas.defaultBlockState().tick(level, p, new ScriptedRandom(Map.of(6, dir.ordinal(), 7, 0, 350, 1)));
                            check(level.getBlockState(n).is(Blocks.STONE), "meltdown gas toward a stone " + dir + " neighbour left " + level.getBlockState(n));
                            check(level.getBlockState(p).is(gas), "meltdown gas toward a stone " + dir + " neighbour: the gas cell became " + level.getBlockState(p));

                            // air neighbour, chance missed: no radon anywhere around or in the cell
                            enclose(level, p, gas, dir, Blocks.AIR.defaultBlockState());
                            gas.defaultBlockState().tick(level, p, new ScriptedRandom(Map.of(6, dir.ordinal(), 7, 1, 350, 1)));
                            check(!level.getBlockState(n).is(radon) && !level.getBlockState(p).is(radon), "meltdown gas with nextInt(7) = 1 toward " + dir + " placed dense radon");
                        }
                        LOGGER.info("{} meltdown_gas_dense_radon: dense radon in the chosen air neighbour for all six directions, none into stone or on a missed roll", TAG);
                    } finally {
                        clearAround(level, p);
                        rad.setRadiation(level, p, before);
                    }
                    passed("meltdown_gas_dense_radon").run();
                }))
                .thenSucceed();
    }

    /** Puts {@code center} at p, stone on every side but {@code open}, and {@code openState} on the {@code open} side. */
    private static void enclose(ServerLevel level, BlockPos p, Block center, Direction open, BlockState openState) {
        for(Direction d : Direction.values()) level.setBlock(p.relative(d), d == open ? openState : Blocks.STONE.defaultBlockState(), 3);
        level.setBlock(p, center.defaultBlockState(), 3);
    }

    private static void clearAround(ServerLevel level, BlockPos p) {
        level.setBlock(p, Blocks.AIR.defaultBlockState(), 3);
        for(Direction d : Direction.values()) level.setBlock(p.relative(d), Blocks.AIR.defaultBlockState(), 3);
    }

    // ---------------------------------------------------------------- 3. blocks adding radiation to their chunk

    // Original HazardRegistry.java constants: :84 ra226 7.5, :85 ac227 30, :83 po210 75, :86 th232 0.1, :87 thf 1.75, :88 u 0.35, :89 u233 5,
    // :90 u235 1, :91 u238 0.25, :92 uf 0.5, :94 np237 2.5, :96 pu 7.5, :97 purg 6.25, :98 pu238 10, :99 pu239 5, :100 pu240 7.5, :102 puf 4.25,
    // :107 mox 2.5, :108 sa326 15, :109 sa327 17.5, :110 saf 5.85, :124 sr = sa326 * 0.1, :125 sb = sa326 * 0.1, :128 wst 15, :129 wstv 7.5,
    // :130 yc = u, :138 powder_mult 3, :142 block 10.
    private static final float RA226 = 7.5F, AC227 = 30.0F, PO210 = 75.0F, TH232 = 0.1F, THF = 1.75F, U = 0.35F, U233 = 5.0F, U235 = 1.0F,
            U238 = 0.25F, UF = 0.5F, NP237 = 2.5F, PU = 7.5F, PURG = 6.25F, PU238 = 10.0F, PU239 = 5.0F, PU240 = 7.5F, PUF = 4.25F, MOX = 2.5F,
            SA326 = 15.0F, SA327 = 17.5F, SAF = 5.85F, SR = SA326 * 0.1F, SB = SA326 * 0.1F, WST = 15.0F, WSTV = 7.5F, YC = U,
            POWDER_MULT = 3.0F, BLOCK = 10.0F;

    /** One radiating block and its original item RADIATION level; the chunk increment per update is level * 0.1 (BlockHazard.java:142). */
    private record Emitter(String id, DeferredBlock<Block> block, float level, boolean waste) {
        float perUpdate() {
            return this.level * 0.1F;
        }
    }

    // Item levels: OreDictManager.java:347-372 (.rad(x) ... .block(b), hazMult HazardRegistry.block at :875-876) for the material blocks;
    // HazardRegistry.java:292 uf, :298 puf, :303 thf, :312 mox, :321 saf (each * block) for the fuel blocks, :215-217 wst / wst / wstv * block for
    // the waste blocks, :474 yc * block * powder_mult for block_yellowcake. Classes from ModBlocks.java:1341-1425 (BlockHazard, BlockHotHazard for
    // polonium and pu238, BlockNuclearWaste for the three waste blocks, BlockHazardFalling for yellowcake).
    private static List<Emitter> emitters() {
        return List.of(
                new Emitter("block_uranium", NtmBlocks.BLOCK_URANIUM, U * BLOCK, false),
                new Emitter("block_u233", NtmBlocks.BLOCK_U233, U233 * BLOCK, false),
                new Emitter("block_u235", NtmBlocks.BLOCK_U235, U235 * BLOCK, false),
                new Emitter("block_u238", NtmBlocks.BLOCK_U238, U238 * BLOCK, false),
                new Emitter("block_uranium_fuel", NtmBlocks.BLOCK_URANIUM_FUEL, UF * BLOCK, false),
                new Emitter("block_thorium", NtmBlocks.BLOCK_THORIUM, TH232 * BLOCK, false),
                new Emitter("block_thorium_fuel", NtmBlocks.BLOCK_THORIUM_FUEL, THF * BLOCK, false),
                new Emitter("block_neptunium", NtmBlocks.BLOCK_NEPTUNIUM, NP237 * BLOCK, false),
                new Emitter("block_mox_fuel", NtmBlocks.BLOCK_MOX_FUEL, MOX * BLOCK, false),
                new Emitter("block_plutonium", NtmBlocks.BLOCK_PLUTONIUM, PU * BLOCK, false),
                new Emitter("block_pu239", NtmBlocks.BLOCK_PU239, PU239 * BLOCK, false),
                new Emitter("block_pu240", NtmBlocks.BLOCK_PU240, PU240 * BLOCK, false),
                new Emitter("block_pu_mix", NtmBlocks.BLOCK_PU_MIX, PURG * BLOCK, false),
                new Emitter("block_plutonium_fuel", NtmBlocks.BLOCK_PLUTONIUM_FUEL, PUF * BLOCK, false),
                new Emitter("block_schraranium", NtmBlocks.BLOCK_SCHRARANIUM, SR * BLOCK, false),
                new Emitter("block_schrabidium", NtmBlocks.BLOCK_SCHRABIDIUM, SA326 * BLOCK, false),
                new Emitter("block_schrabidate", NtmBlocks.BLOCK_SCHRABIDATE, SB * BLOCK, false),
                new Emitter("block_solinium", NtmBlocks.BLOCK_SOLINIUM, SA327 * BLOCK, false),
                new Emitter("block_schrabidium_fuel", NtmBlocks.BLOCK_SCHRABIDIUM_FUEL, SAF * BLOCK, false),
                new Emitter("block_ra226", NtmBlocks.BLOCK_RA226, RA226 * BLOCK, false),
                new Emitter("block_actinium", NtmBlocks.BLOCK_ACTINIUM, AC227 * BLOCK, false),
                new Emitter("block_polonium", NtmBlocks.BLOCK_POLONIUM, PO210 * BLOCK, false),
                new Emitter("block_pu238", NtmBlocks.BLOCK_PU238, PU238 * BLOCK, false),
                new Emitter("block_waste", NtmBlocks.BLOCK_WASTE, WST * BLOCK, true),
                new Emitter("block_waste_painted", NtmBlocks.BLOCK_WASTE_PAINTED, WST * BLOCK, true),
                new Emitter("block_waste_vitrified", NtmBlocks.BLOCK_WASTE_VITRIFIED, WSTV * BLOCK, true),
                new Emitter("block_yellowcake", NtmBlocks.BLOCK_YELLOWCAKE, YC * BLOCK * POWDER_MULT, false));
    }

    /** ModBlocks.java:1251 new BlockOre(Material.rock, 0.1F, 0.5F): rad 0.1 from the constructor (BlockOre.java:39-43). */
    private static final float ORE_SCHRABIDIUM_RAD = 0.1F;

    /** No dense radon from a waste block's roll (BlockNuclearWaste.java:18, rand.nextInt(2) == 1 misses). */
    private static ScriptedRandom noRadon() {
        return new ScriptedRandom(Map.of(6, 0, 2, 1));
    }

    /** The block at p on a stone support, placed with flag 3 so onPlace runs. */
    private static BlockState place(ServerLevel level, BlockPos p, Block block) {
        level.setBlock(p.below(), Blocks.STONE.defaultBlockState(), 3);
        level.setBlock(p, block.defaultBlockState(), 3);
        BlockState state = level.getBlockState(p);
        check(state.is(block), name(block) + " was not placed: " + state);
        return state;
    }

    /** The chunk increment of one scheduled tick of the block at p, measured from 0, and whether the tick scheduled the next one. */
    private record Update(float increment, boolean rescheduled) { }

    private static Update tickOnce(ServerLevel level, BlockPos p, BlockState state, ScriptedRandom random) {
        ChunkRadiationHandler rad = ChunkRadiationManager.proxy;
        clearTicks(level, p);
        rad.setRadiation(level, p, 0F);
        state.tick(level, p, random);
        return new Update(rad.getRadiation(level, p), scheduled(level, p, state.getBlock()));
    }

    // Original BlockHazard.java:138-146 (onBlockAdded sets rad to the item's RADIATION * 0.1 and, rad > 0, schedules an update at tickRate 20
    // :130-136) and :121-127 (updateTick, rad > 0: incrementRad(rad) and schedule the next); BlockHazardFalling.java:39-66 the same for yellowcake;
    // BlockNuclearWaste.java:13-23 runs the radon roll and then BlockHazard's update (roll answered as a miss here).
    @GameTest(template = TEMPLATE, batch = "hbm32u_hazard_blocks_emit", timeoutTicks = 100)
    public static void hazard_blocks_emit(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    check(NtmConfig.COMMON.ENABLE_CHUNK_RADS.get(), "chunk radiation is disabled in the common config; the checks need it enabled");
                    ServerLevel level = helper.getLevel();
                    ChunkRadiationHandler rad = ChunkRadiationManager.proxy;
                    BlockPos p = helper.absolutePos(new BlockPos(8, 2, 8));
                    float before = rad.getRadiation(level, p);
                    List<String> seen = new ArrayList<>();
                    try {
                        for(Emitter e : emitters()) {
                            Block block = e.block().get();
                            check(name(block).equals(NuclearTechMod.MODID + ":" + e.id()), "row " + e.id() + " points at " + name(block));
                            BlockState state = place(level, p, block);
                            check(scheduled(level, p, block), e.id() + ": placing it scheduled no update (original onBlockAdded schedules one when rad > 0)");
                            Update u = tickOnce(level, p, state, noRadon());
                            check(close(u.increment(), e.perUpdate()), e.id() + ": one update added " + u.increment() + " to the chunk, original " + e.level() + " * 0.1 = " + e.perUpdate());
                            check(u.rescheduled(), e.id() + ": the update did not schedule the next one");
                            check(level.getBlockState(p).is(block), e.id() + ": the block left its cell after an update: " + level.getBlockState(p));
                            seen.add(e.id() + "=" + u.increment());
                            level.setBlock(p, Blocks.AIR.defaultBlockState(), 3);
                        }
                        LOGGER.info("{} hazard_blocks_emit: {} blocks, increments {}", TAG, seen.size(), seen);
                    } finally {
                        level.setBlock(p, Blocks.AIR.defaultBlockState(), 3);
                        level.setBlock(p.below(), Blocks.AIR.defaultBlockState(), 3);
                        rad.setRadiation(level, p, before);
                    }
                    passed("hazard_blocks_emit").run();
                }))
                .thenSucceed();
    }

    // Original BlockOre.java:39-43 (the rad constructor sets rad and setTickRandomly(true)), :221-226 (onBlockAdded schedules at tickRate 20,
    // :213-219), :199-210 (updateTick, rad > 0: incrementRad(rad) and schedule the next); the 1.7.10 random tick calls updateTick (task book
    // section 3, not verifiable in either repository), so a random tick emits and schedules as well.
    @GameTest(template = TEMPLATE, batch = "hbm32u_ore_schrabidium_emits", timeoutTicks = 100)
    public static void ore_schrabidium_emits(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    ChunkRadiationHandler rad = ChunkRadiationManager.proxy;
                    BlockPos p = helper.absolutePos(new BlockPos(8, 2, 8));
                    Block ore = NtmBlocks.ORE_SCHRABIDIUM.get();
                    float before = rad.getRadiation(level, p);
                    try {
                        BlockState state = place(level, p, ore);
                        check(state.isRandomlyTicking(), "ore_schrabidium does not tick randomly (original setTickRandomly(true))");
                        check(scheduled(level, p, ore), "placing ore_schrabidium scheduled no update");
                        Update u = tickOnce(level, p, state, noRadon());
                        check(close(u.increment(), ORE_SCHRABIDIUM_RAD), "ore_schrabidium's scheduled update added " + u.increment() + ", original 0.1");
                        check(u.rescheduled(), "ore_schrabidium's scheduled update did not schedule the next one");

                        clearTicks(level, p);
                        rad.setRadiation(level, p, 0F);
                        state.randomTick(level, p, noRadon());
                        float random = rad.getRadiation(level, p);
                        check(close(random, ORE_SCHRABIDIUM_RAD), "ore_schrabidium's random tick added " + random + ", original 0.1");
                        check(scheduled(level, p, ore), "ore_schrabidium's random tick did not schedule an update");
                        LOGGER.info("{} ore_schrabidium_emits: scheduled update {}, random tick {}", TAG, u.increment(), random);
                    } finally {
                        level.setBlock(p, Blocks.AIR.defaultBlockState(), 3);
                        level.setBlock(p.below(), Blocks.AIR.defaultBlockState(), 3);
                        rad.setRadiation(level, p, before);
                    }
                    passed("ore_schrabidium_emits").run();
                }))
                .thenSucceed();
    }

    private static Field radField(Block block) {
        for(Class<?> c = block.getClass(); c != null; c = c.getSuperclass()) {
            try {
                Field f = c.getDeclaredField("rad");
                f.setAccessible(true);
                return f;
            } catch(NoSuchFieldException ignored) { }
        }
        throw new GameTestAssertException(name(block) + " has no rad field");
    }

    private static void setRad(Field f, Block block, float value) {
        try {
            f.setFloat(block, value);
        } catch(IllegalAccessException ex) {
            throw new GameTestAssertException("rad of " + name(block) + " not writable: " + ex);
        }
    }

    // Signed rule (migration/GOAL32U.md section 3, 口径: as the original): rad is an instance field of the block singleton assigned only in
    // onBlockAdded (BlockHazard.java:138-146, BlockHazardFalling.java:59-66), 0 in a fresh process, and updateTick does nothing and schedules
    // nothing while rad <= 0 (BlockHazard.java:121-127, BlockHazardFalling.java:39-48). The restart is simulated by setting that field of the block
    // object to 0 through reflection after placing the block and clearing its pending update, then calling the update a saved world would run.
    // BlockHazard has no neighbour-change handler, so a later placement elsewhere does not restart an old block; BlockFalling's neighbour change
    // schedules at tickRate, so an old yellowcake block restarts once another yellowcake was placed in the process (task book section 3).
    @GameTest(template = TEMPLATE, batch = "hbm32u_hazard_blocks_restart", timeoutTicks = 100)
    public static void hazard_blocks_restart(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    ChunkRadiationHandler rad = ChunkRadiationManager.proxy;
                    BlockPos p = helper.absolutePos(new BlockPos(4, 2, 4));
                    BlockPos q = helper.absolutePos(new BlockPos(11, 2, 11));
                    float before = rad.getRadiation(level, p);
                    float beforeQ = rad.getRadiation(level, q);
                    try {
                        for(Emitter e : emitters()) {
                            Block block = e.block().get();
                            Field f = radField(block);
                            BlockState state = place(level, p, block);
                            float placed;
                            try {
                                placed = f.getFloat(block);
                            } catch(IllegalAccessException ex) {
                                throw new GameTestAssertException("rad of " + e.id() + " unreadable: " + ex);
                            }
                            check(close(placed, e.perUpdate()), e.id() + ": rad after placing is " + placed + ", original " + e.perUpdate());
                            try {
                                setRad(f, block, 0F);
                                Update u = tickOnce(level, p, state, noRadon());
                                check(u.increment() == 0F, e.id() + " with rad 0 (restarted process) added " + u.increment() + " to the chunk");
                                check(!u.rescheduled(), e.id() + " with rad 0 (restarted process) scheduled another update");

                                // another block of the same kind placed elsewhere sets rad again; then a neighbour of the old block changes
                                place(level, q, block);
                                clearTicks(level, p);
                                level.setBlock(p.above(), Blocks.STONE.defaultBlockState(), 3);
                                level.setBlock(p.above(), Blocks.AIR.defaultBlockState(), 3);
                                boolean restarted = scheduled(level, p, block);
                                if(e.id().equals("block_yellowcake")) {
                                    check(restarted, "block_yellowcake: a neighbour change after another yellowcake was placed did not schedule the old block (BlockFalling.onNeighborBlockChange)");
                                    Update again = tickOnce(level, p, state, noRadon());
                                    check(close(again.increment(), e.perUpdate()) && again.rescheduled(), "block_yellowcake: the restarted old block added " + again.increment() + ", rescheduled " + again.rescheduled());
                                } else {
                                    check(!restarted, e.id() + ": a neighbour change scheduled an update on the old block (BlockHazard has no neighbour handler)");
                                }
                            } finally {
                                setRad(f, block, placed);
                                level.setBlock(p, Blocks.AIR.defaultBlockState(), 3);
                                level.setBlock(q, Blocks.AIR.defaultBlockState(), 3);
                            }
                        }
                        LOGGER.info("{} hazard_blocks_restart: 27 blocks silent with rad 0; only block_yellowcake restarts on a neighbour change", TAG);
                    } finally {
                        for(BlockPos c : new BlockPos[] { p, p.below(), p.above(), q, q.below() }) level.setBlock(c, Blocks.AIR.defaultBlockState(), 3);
                        rad.setRadiation(level, p, before);
                        rad.setRadiation(level, q, beforeQ);
                    }
                    passed("hazard_blocks_restart").run();
                }))
                .thenSucceed();
    }

    // Original BlockNuclearWaste.java:16-20: dir = ForgeDirection.getOrientation(rand.nextInt(6)); on rand.nextInt(2) == 0 and air at x+dir the
    // neighbour becomes gas_radon_dense; then BlockHazard.updateTick (:22) adds rad. Direction order as in meltdown_gas_dense_radon.
    @GameTest(template = TEMPLATE, batch = "hbm32u_nuclear_waste_dense_radon", timeoutTicks = 100)
    public static void nuclear_waste_dense_radon(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    ChunkRadiationHandler rad = ChunkRadiationManager.proxy;
                    BlockPos p = helper.absolutePos(new BlockPos(8, 4, 8));
                    Block radon = NtmBlocks.GAS_RADON_DENSE.get();
                    float before = rad.getRadiation(level, p);
                    try {
                        for(Emitter e : emitters()) {
                            if(!e.waste()) continue;
                            Block waste = e.block().get();
                            for(Direction dir : Direction.values()) {
                                BlockPos n = p.relative(dir);

                                enclose(level, p, waste, dir, Blocks.AIR.defaultBlockState());
                                Update hit = tickOnce(level, p, level.getBlockState(p), new ScriptedRandom(Map.of(6, dir.ordinal(), 2, 0)));
                                check(level.getBlockState(n).is(radon), e.id() + " toward an air " + dir + " neighbour (nextInt(2) = 0) left " + level.getBlockState(n));
                                check(level.getBlockState(p).is(waste), e.id() + " toward " + dir + ": its own cell became " + level.getBlockState(p));
                                check(close(hit.increment(), e.perUpdate()) && hit.rescheduled(), e.id() + " toward " + dir + ": the update added " + hit.increment() + " (original " + e.perUpdate() + "), rescheduled " + hit.rescheduled());

                                enclose(level, p, waste, dir, Blocks.STONE.defaultBlockState());
                                tickOnce(level, p, level.getBlockState(p), new ScriptedRandom(Map.of(6, dir.ordinal(), 2, 0)));
                                check(level.getBlockState(n).is(Blocks.STONE), e.id() + " toward a stone " + dir + " neighbour left " + level.getBlockState(n));

                                enclose(level, p, waste, dir, Blocks.AIR.defaultBlockState());
                                tickOnce(level, p, level.getBlockState(p), new ScriptedRandom(Map.of(6, dir.ordinal(), 2, 1)));
                                check(level.getBlockState(n).isAir(), e.id() + " toward " + dir + " with nextInt(2) = 1 left " + level.getBlockState(n));
                            }
                        }
                        LOGGER.info("{} nuclear_waste_dense_radon: dense radon in the chosen air neighbour, all six directions, three waste blocks; none into stone or on a miss", TAG);
                    } finally {
                        clearAround(level, p);
                        rad.setRadiation(level, p, before);
                    }
                    passed("nuclear_waste_dense_radon").run();
                }))
                .thenSucceed();
    }

    /** Chunk radiation of the loaded chunks around the test area, read at the start and written back at the end (as RBMKCraneGameTests.Rad). */
    private static final class Rad {
        final ServerLevel level;
        final Map<ChunkPos, Float> before = new LinkedHashMap<>();

        Rad(GameTestHelper helper) {
            this.level = helper.getLevel();
            AABB area = helper.getBounds().inflate(32, 0, 32);
            for(int x = (int) Math.floor(area.minX) >> 4; x <= (int) Math.floor(area.maxX) >> 4; x++) {
                for(int z = (int) Math.floor(area.minZ) >> 4; z <= (int) Math.floor(area.maxZ) >> 4; z++) {
                    if(!level.hasChunk(x, z)) continue;
                    ChunkPos cp = new ChunkPos(x, z);
                    before.put(cp, ChunkRadiationManager.proxy.getRadiation(level, cp.getWorldPosition()));
                }
            }
        }

        void restore() {
            for(Map.Entry<ChunkPos, Float> e : before.entrySet()) ChunkRadiationManager.proxy.setRadiation(level, e.getKey().getWorldPosition(), e.getValue());
        }
    }

    // Original BlockHazardFalling.java:15 (a BlockFalling), :39-48 (updateTick adds rad, schedules, then BlockFalling's fall check), :59-66
    // (onBlockAdded after landing sets rad and schedules); ModBlocks.java:1401 (soundTypeSand). The block placed in the air falls onto the stone,
    // then one update of the landed block adds yc * block * powder_mult * 0.1 = 1.05 and schedules the next. The fall itself runs real ticks, so
    // the chunk radiation around the test is snapshot and restored.
    @GameTest(template = TEMPLATE, batch = "hbm32u_yellowcake_falls_and_emits", timeoutTicks = 200)
    public static void yellowcake_falls_and_emits(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        Block cake = NtmBlocks.BLOCK_YELLOWCAKE.get();
        BlockPos top = new BlockPos(8, 6, 8);
        BlockPos landing = new BlockPos(8, 1, 8);
        Rad snapshot = new Rad(helper);
        helper.startSequence()
                .thenExecute(guard(() -> {
                    helper.setBlock(new BlockPos(8, 0, 8), Blocks.STONE);
                    helper.setBlock(top, cake);
                    check(helper.getBlockState(top).is(cake), "block_yellowcake was not placed in the air: " + helper.getBlockState(top));
                    check(scheduled(level, helper.absolutePos(top), cake), "placing block_yellowcake in the air scheduled no update");
                }))
                .thenWaitUntil(() -> {
                    check(helper.getBlockState(landing).is(cake), "block_yellowcake has not landed yet: " + helper.getBlockState(landing));
                    check(level.getEntitiesOfClass(FallingBlockEntity.class, helper.getBounds()).isEmpty(), "a falling block entity is still in the air");
                })
                .thenExecute(guard(() -> {
                    try {
                        check(helper.getBlockState(top).isAir(), "the cell it fell from holds " + helper.getBlockState(top));
                        BlockPos abs = helper.absolutePos(landing);
                        check(scheduled(level, abs, cake), "the landed block_yellowcake scheduled no update (original onBlockAdded schedules when rad > 0)");
                        float expected = YC * BLOCK * POWDER_MULT * 0.1F;
                        Update u = tickOnce(level, abs, level.getBlockState(abs), noRadon());
                        check(close(u.increment(), expected), "the landed block_yellowcake added " + u.increment() + ", original " + expected);
                        check(u.rescheduled(), "the landed block_yellowcake's update did not schedule the next one");
                        check(helper.getBlockState(landing).is(cake), "the supported block_yellowcake moved during its update: " + helper.getBlockState(landing));
                        LOGGER.info("{} yellowcake_falls_and_emits: fell from y 6 to y 1, landed update {}", TAG, u.increment());
                    } finally {
                        helper.setBlock(landing, Blocks.AIR);
                        helper.setBlock(new BlockPos(8, 0, 8), Blocks.AIR);
                        snapshot.restore();
                    }
                    passed("yellowcake_falls_and_emits").run();
                }))
                .thenSucceed();
    }

    // Original BlockHazard.getRarity (BlockHazard.java:159-170) returns rare for block_schraranium, block_schrabidate, block_solinium and
    // block_schrabidium_fuel and common for every other block; the five SCHRAB blocks' items are ItemBlockBase (ModBlocks.java:2572-2576), whose
    // getRarity asks the block (ItemBlockBase.java:83-90), the others plain ItemBlock (common). ModBlocks.java:1352 block_pu238 setLightLevel(5F/15F)
    // (light (int) (15 * 5/15) = 5), no other of the 27 sets a light level. ModBlocks.java:1401 block_yellowcake setStepSound(soundTypeSand).
    @GameTest(template = TEMPLATE, batch = "hbm32u_hazard_block_properties", timeoutTicks = 100)
    public static void hazard_block_properties(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    Set<String> rare = Set.of("block_schraranium", "block_schrabidate", "block_solinium", "block_schrabidium_fuel");
                    for(Emitter e : emitters()) {
                        Block block = e.block().get();
                        Rarity rarity = new ItemStack(block).getRarity();
                        Rarity expected = rare.contains(e.id()) ? Rarity.RARE : Rarity.COMMON;
                        check(rarity == expected, e.id() + " item rarity is " + rarity + ", original " + expected);
                        int light = block.defaultBlockState().getLightEmission();
                        int expectedLight = e.id().equals("block_pu238") ? 5 : 0;
                        check(light == expectedLight, e.id() + " light is " + light + ", original " + expectedLight);
                    }
                    SoundType sound = NtmBlocks.BLOCK_YELLOWCAKE.get().defaultBlockState().getSoundType();
                    check(sound == SoundType.SAND, "block_yellowcake sound is " + sound + ", original soundTypeSand");
                    LOGGER.info("{} hazard_block_properties: 4 rare, 23 common, block_pu238 light 5, block_yellowcake sand", TAG);
                    passed("hazard_block_properties").run();
                }))
                .thenSucceed();
    }
}
