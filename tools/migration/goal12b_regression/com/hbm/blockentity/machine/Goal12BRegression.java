package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import com.hbm.blockentity.Goal12AProxyAccess;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.boiler.MachineHeatBoilerBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterOvenBlockEntity;
import com.hbm.blockentity.machine.oil.MachineCatalyticCrackerBlockEntity;
import com.hbm.blockentity.machine.oil.MachineRefineryBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.Goal11ABlockAccess;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.BarrelBlock;
import com.hbm.blocks.machine.Goal12BBlockAccess;
import com.hbm.blocks.machine.MachineCatalyticCrackerBlock;
import com.hbm.blocks.machine.MachineRefineryBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.CrackingRecipes;
import com.hbm.inventory.recipes.RefineryRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.items.tools.ColtanCompassItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.main.ServerProxy;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.Tuple.Pair;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.hbm.world.feature.ColtanDepositFeature;
import com.hbm.world.feature.Goal11AWorldGen;
import com.hbm.world.feature.Goal12BWorldGen;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.configurations.OreConfiguration;
import net.minecraft.world.level.levelgen.structure.templatesystem.TagMatchTest;
import net.neoforged.neoforge.network.PacketDistributor;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.function.IntUnaryOperator;
import java.util.function.IntSupplier;

/**
 * Goal 12B machine world: the production MachineCatalyticCrackerBlock, MachineCatalyticCrackerBlockEntity, CrackingRecipes,
 * ColtanCompassItem and ColtanDepositFeature with the Goal 12A machine world (networks, pipes, barrels, proxies, the heat
 * boiler with the heating oven, the refinery, the chemical plant and ChemicalPlantRecipes, the Goal 11A worldgen model).
 * Expected behaviour is read from the original (Hbm-s-Nuclear-Tech-GIT d7ef2df), not from the NEO classes under test:
 * HbmWorldGen.java:153-170 (deposit centre Random(seed + 5), nextGaussian * 1500 for X, then Z; 2 x 5 tries per chunk, x =
 * chunk + rand(16), y = rand(25) + 15, z = chunk + rand(16); range 750 / r; inclusive square test; WorldGenMinable(ore_coltan,
 * 4), which centres its vein on x + 8, z + 8); ItemColtanCompass.java:37-66 (client: "<int distance>m" through displayTooltip
 * ID_COMPASS; server: colX / colZ written once from the same centre); TileEntityMachineCatalyticCracker.java:26-33 (tanks
 * bitumen 4,000, steam 8,000, oil 4,000, petroleum gas 4,000, spent steam 800), :35-49 (every 5 ticks), :63-86 (up to two runs:
 * >= 100 mB oil, >= 200 mB steam, room for both outputs and 2 mB spent steam; -100 / -200 / +left / +right / +2), :88-102
 * (setupTanks; NONE for an input without a recipe), :104-118 (tank0..tank4), :122-138 (eight ports, PortDef.make: the
 * connection one block outward), :166-174 (receive 0, 1; send 2, 3, 4); MachineCatalyticCracker.java:32-61 (dims {0,0,3,3,2,3},
 * offset 3, four extra boxes), :63-91 (identifier), :94-122 (checkSpace and fillSpace of the boxes, eight makeExtra);
 * MultiblockHandlerXR.java rotate and fillSpace; CrackingRecipes.java:23-55 (12 defaults); RefineryRecipes.java (hot cracked oil:
 * 40 cracked naphtha, 30 cracked light oil, 15 aromatics, 15 unsaturateds per 100 mB); Fluids.java (cracked oil: 10 TU per mB to
 * hot cracked oil); ChemicalPlantRecipes.java (chem.rubber: 500 mB unsaturateds + 1 sulfur -> 2 rubber; chem.bakelite: 500 mB
 * aromatics + 500 mB petroleum gas -> 1 bakelite). ForgeDirection.getRotation(UP) is Forge 1.7.10's ROTATION_MATRIX[UP] =
 * {0, 1, 5, 4, 2, 3, 6} (north -> east, clockwise from above).
 */
public class Goal12BRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    static final MachineCatalyticCrackerBlock CRACKER = new MachineCatalyticCrackerBlock(new Block.Properties());
    static final MachineRefineryBlock REFINERY = new MachineRefineryBlock(new Block.Properties());
    static final BarrelBlock BIG = new BarrelBlock(10_000_000);
    static final Direction[] HORIZONTALS = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };

    // ---- Original numbers, independent of the NEO constants under test ------------------------------------------------
    static final int COL_RANGE = 750, PASSES = 2, RINGS = 5, Y_BASE = 15, Y_RANGE = 25, VEIN = 4, VEIN_SHIFT = 8;
    static final int[] TANKS = { 4_000, 8_000, 4_000, 4_000, 800 };
    static final int OIL_PER_RUN = 100, STEAM_PER_RUN = 200, SPENT_PER_RUN = 2, RUNS = 2, INTERVAL = 5;
    static final int[] MAIN_DIM = { 0, 0, 3, 3, 2, 3 };
    static final int[][] EXTRA_DIMS = { { 8, -1, 3, -1, 2, 0 }, { 13, 0, 0, 3, 2, 1 }, { 14, -13, -1, 2, 1, 0 }, { 3, -1, 2, 3, -1, 3 } };
    static final int OFFSET = 3;
    static final int RUBBER_UNSAT = 500, RUBBER_SULFUR = 1, RUBBER_OUT = 2, BAKELITE_AROMA = 500, BAKELITE_PETRO = 500, BAKELITE_OUT = 1;
    static final int CRACK_NAPHTHA = 40, CRACK_LIGHT = 30, CRACK_AROMA = 15, CRACK_UNSAT = 15, REFINERY_INPUT = 100, CRACKOIL_TU = 10;

    /** Original CrackingRecipes.java:41-55 in registration order: input, output 1, amount, output 2, amount (per 100 mB). */
    static Object[][] originalCracking() {
        return new Object[][] {
                { Fluids.OIL, Fluids.CRACKOIL, 80, Fluids.PETROLEUM, 20 },
                { Fluids.BITUMEN, Fluids.OIL, 80, Fluids.AROMATICS, 20 },
                { Fluids.SMEAR, Fluids.NAPHTHA, 60, Fluids.PETROLEUM, 40 },
                { Fluids.GAS, Fluids.PETROLEUM, 30, Fluids.UNSATURATEDS, 20 },
                { Fluids.DIESEL, Fluids.KEROSENE, 40, Fluids.PETROLEUM, 30 },
                { Fluids.DIESEL_CRACK, Fluids.KEROSENE, 40, Fluids.PETROLEUM, 30 },
                { Fluids.KEROSENE, Fluids.PETROLEUM, 60, Fluids.NONE, 0 },
                { Fluids.WOODOIL, Fluids.HEATINGOIL, 40, Fluids.AROMATICS, 10 },
                { Fluids.XYLENE, Fluids.AROMATICS, 80, Fluids.PETROLEUM, 20 },
                { Fluids.HEATINGOIL_VACUUM, Fluids.HEATINGOIL, 80, Fluids.REFORMGAS, 20 },
                { Fluids.REFORMATE, Fluids.UNSATURATEDS, 40, Fluids.REFORMGAS, 60 },
                { Fluids.BIOGAS, Fluids.PETROLEUM, 20, Fluids.AROMATICS, 20 },
        };
    }

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void info(String message) {
        System.out.println("  info: " + message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

    private static void run(String name, Runnable body) {
        try {
            body.run();
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            checks--;
            sectionChecks = 0;
            DummyableBlock.safeRem = false;
        }
    }

    // ---- World helpers (the Goal 11C/12A patterns) ----------------------------------------------------------------------

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
        Block.DROPS.clear();
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();
        GenericRecipes.blueprintPools.clear();
        ChemicalPlantRecipes.INSTANCE.deleteRecipes();
        ChemicalPlantRecipes.INSTANCE.registerDefaults();
        new CrackingRecipes().deleteRecipes();
        new CrackingRecipes().registerDefaults();
        RefineryRecipes.registerDefaults();
        NuclearTechMod.proxy.tooltips.clear();
        Feature.OreRecorder.PLACED.clear();
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        level.random.setSeed(12L);
        return level;
    }

    static void net(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static void transfer(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static BlockState facing(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        return state;
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        if(level.getBlockEntity(pos) != null || level.states.containsKey(pos)) throw new IllegalStateException("fixture layout: " + pos + " is taken");
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    /** Pipes from a up to height h, along x, along z, then down to b (both ends included). */
    static void route(Level level, FluidType type, BlockPos a, BlockPos b, int h) {
        List<BlockPos> path = new ArrayList<>();
        BlockPos p = a;
        path.add(p);
        while(p.getY() != h) { p = p.offset(0, Integer.signum(h - p.getY()), 0); path.add(p); }
        while(p.getX() != b.getX()) { p = p.offset(Integer.signum(b.getX() - p.getX()), 0, 0); path.add(p); }
        while(p.getZ() != b.getZ()) { p = p.offset(0, 0, Integer.signum(b.getZ() - p.getZ())); path.add(p); }
        while(p.getY() != b.getY()) { p = p.offset(0, Integer.signum(b.getY() - p.getY()), 0); path.add(p); }
        for(BlockPos q : new LinkedHashSet<>(path)) pipe(level, q, type);
    }

    static BarrelBlockEntity barrel(Level level, BlockPos pos, FluidType type, int fill, int mode) {
        BlockState state = new BlockState();
        state.block = BIG;
        level.states.put(pos, state);
        BarrelBlockEntity barrel = new BarrelBlockEntity(pos, state);
        level.put(barrel);
        barrel.tank.setTankType(type);
        barrel.tank.setFill(fill);
        barrel.mode = (short) mode;
        return barrel;
    }

    static Set<BlockPos> parts(Level level, Block block) {
        Set<BlockPos> outSet = new LinkedHashSet<>();
        level.states.forEach((p, s) -> { if(s.getBlock() == block) outSet.add(p); });
        return outSet;
    }

    static Set<BlockPos> ofType(Level level, Block block, DummyBlockType type) {
        Set<BlockPos> outSet = new LinkedHashSet<>();
        level.states.forEach((p, s) -> { if(s.getBlock() == block && s.getValue(DummyableBlock.TYPE) == type) outSet.add(p); });
        return outSet;
    }

    static void nbt(BlockEntity be, String name, CompoundTag tag) {
        for(Class<?> type = be.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Method m = type.getDeclaredMethod(name, CompoundTag.class, HolderLookup.Provider.class);
                m.setAccessible(true);
                m.invoke(be, tag, null);
                return;
            } catch(NoSuchMethodException ignored) {
            } catch(ReflectiveOperationException e) {
                throw new AssertionError(name + " failed on " + be.getClass().getName(), e);
            }
        }
        throw new AssertionError("no " + name + " on " + be.getClass().getName());
    }

    static String tanks(MachineCatalyticCrackerBlockEntity be) {
        StringBuilder b = new StringBuilder("[");
        for(FluidTank t : be.tanks) b.append(t.getTankType()).append(' ').append(t.getFill()).append('/').append(t.getMaxFill()).append(", ");
        return b.append(']').toString();
    }

    // ---- 4. Coltan deposit -------------------------------------------------------------------------------------------------

    /** The original centre (HbmWorldGen.java:153-155): Random(seed + 5), (int) (nextGaussian * 1500), X then Z. */
    static int[] originalCentre(long seed) {
        Random colRand = new Random(seed + 5);
        int colX = (int) (colRand.nextGaussian() * 1500);
        int colZ = (int) (colRand.nextGaussian() * 1500);
        return new int[] { colX, colZ };
    }

    /** The original tries (HbmWorldGen.java:158-170), each draw from `draw` (bound -> value), Y above the world bottom (D5b). */
    static List<BlockPos> originalVeins(long seed, int minY, int chunkX, int chunkZ, IntUnaryOperator draw) {
        int[] c = originalCentre(seed);
        List<BlockPos> out = new ArrayList<>();
        for(int k = 0; k < PASSES; k++) {
            for(int r = 1; r <= RINGS; r++) {
                int x = chunkX + draw.applyAsInt(16);
                int y = draw.applyAsInt(Y_RANGE) + Y_BASE + minY;
                int z = chunkZ + draw.applyAsInt(16);
                int range = COL_RANGE / r;
                if(x <= c[0] + range && x >= c[0] - range && z <= c[1] + range && z >= c[1] - range) out.add(new BlockPos(x + VEIN_SHIFT, y, z + VEIN_SHIFT));
            }
        }
        return out;
    }

    static Goal11AWorldGen.World world(int minY) {
        Goal11AWorldGen.World w = new Goal11AWorldGen.World(p -> Blocks.STONE.defaultBlockState());
        w.minY = minY;
        return w;
    }

    static List<BlockPos> placed() {
        List<BlockPos> out = new ArrayList<>();
        for(Feature.OreRecorder.Placement p : Feature.OreRecorder.PLACED) out.add(p.origin());
        return out;
    }

    /** One production place call over chunk (cx, cz) (block coordinates of its minimum corner) with scripted draws. */
    static List<BlockPos> scripted(long seed, int minY, int chunkX, int chunkZ, int[] draws, List<String> problems) {
        Feature.OreRecorder.PLACED.clear();
        Goal12BWorldGen.Region region = new Goal12BWorldGen.Region(world(minY), Math.floorDiv(chunkX, 16), Math.floorDiv(chunkZ, 16), seed);
        Goal12BWorldGen.ScriptedRandom random = new Goal12BWorldGen.ScriptedRandom(draws);
        boolean result = Goal12BWorldGen.place(region, random, new BlockPos(chunkX, minY, chunkZ));
        List<Integer> expectedBounds = new ArrayList<>();
        for(int i = 0; i < PASSES * RINGS; i++) expectedBounds.addAll(List.of(16, Y_RANGE, 16));
        if(!random.bounds.equals(expectedBounds)) problems.add("draws " + random.bounds);
        if(!random.script.isEmpty()) problems.add(random.script.size() + " scripted draws left");
        if(result != !Feature.OreRecorder.PLACED.isEmpty()) problems.add("place returned " + result + " for " + Feature.OreRecorder.PLACED.size() + " veins");
        if(!region.writes.isEmpty() || region.refusedEnsure != 0) problems.add("the feature wrote " + region.writes.size() + " blocks itself, " + region.refusedEnsure + " refused");
        return placed();
    }

    /** Ten tries, each x = chunkX + dx, y = minY + 15 + dy, z = chunkZ + dz. */
    static int[] same(int dx, int dy, int dz) {
        int[] d = new int[3 * PASSES * RINGS];
        for(int i = 0; i < PASSES * RINGS; i++) { d[3 * i] = dx; d[3 * i + 1] = dy; d[3 * i + 2] = dz; }
        return d;
    }

    /** The draws of same(dx, dy, dz) for the original algorithm: x, y, z in turn. */
    static IntUnaryOperator sameDraws(int dx, int dy, int dz) {
        return new IntUnaryOperator() {
            int i = 0;
            public int applyAsInt(int bound) { int k = i++ % 3; return k == 0 ? dx : k == 1 ? dy : dz; }
        };
    }

    static void deposit() {
        reset();
        long[] seeds = { 0L, 1L, 12_345L, -1L, -987_654_321L, 20_261_008L, Long.MAX_VALUE, Long.MIN_VALUE };
        boolean centres = true;
        List<String> seen = new ArrayList<>();
        for(long seed : seeds) {
            ColtanDepositFeature.DepositCentre c = ColtanDepositFeature.depositCentre(seed);
            int[] o = originalCentre(seed);
            centres &= c.x() == o[0] && c.z() == o[1];
            seen.add(seed + " -> " + c.x() + "," + c.z());
        }
        check(centres, "depositCentre(seed) equals Random(seed + 5) with (int) (nextGaussian * 1500), X then Z, for 8 seeds incl. negative and the long limits: " + seen);
        check(Goal12BWorldGen.constant("VEIN_OFFSET") == VEIN_SHIFT && Goal12BWorldGen.constant("VEIN_SIZE") == VEIN,
                "the vein origin shift is 8 (1.7.10 WorldGenMinable centres its vein on x + 8, z + 8) and the vein size 4");

        long seed = 20_261_008L;
        int[] c = originalCentre(seed);
        int ccx = Math.floorDiv(c[0], 16) * 16, ccz = Math.floorDiv(c[1], 16) * 16;
        List<String> problems = new ArrayList<>();

        // The centre chunk: every try passes (the smallest range, 150, still covers the chunk).
        int[] draws = new int[30];
        for(int i = 0; i < 10; i++) { draws[3 * i] = i; draws[3 * i + 1] = (i * 7) % 25; draws[3 * i + 2] = 15 - i; }
        int[] fixedDraws = draws.clone();
        List<BlockPos> centre = scripted(seed, -64, ccx, ccz, draws, problems);
        List<BlockPos> centreExpected = originalVeins(seed, -64, ccx, ccz, new IntUnaryOperator() {
            int i = 0;
            public int applyAsInt(int bound) { return fixedDraws[i++]; }
        });
        check(problems.isEmpty(), "every place call draws x (16), y (25), z (16) for each of the 10 tries and nothing else, the ore stand-in draws nothing, "
                + "the return value says whether a vein was placed and the feature writes no block itself: " + problems);
        check(centre.size() == 10 && centre.equals(centreExpected),
                "the chunk at the centre: all 10 tries place a vein, at (x + 8, minY + 15 + rand(25), z + 8) of each try: " + centre);
        boolean configs = true, generator = true;
        for(Feature.OreRecorder.Placement p : Feature.OreRecorder.PLACED) {
            OreConfiguration cfg = p.config();
            configs &= cfg.size == VEIN && cfg.targetStates.size() == 1 && cfg.targetStates.get(0).target instanceof TagMatchTest t && t.tag == BlockTags.BASE_STONE_OVERWORLD
                    && cfg.targetStates.get(0).state.getBlock() == NtmBlocks.ORE_COLTAN.get() && cfg.discardChanceOnAirExposure == 0F;
            generator &= p.generator() == Goal12BWorldGen.GENERATOR;
        }
        check(configs && generator, "each vein is Feature.ORE with size 4, one target (TagMatchTest #minecraft:base_stone_overworld -> ore_coltan), no air discard, "
                + "and the context's chunk generator");

        // Heights: the draws 0 and 24 give minY + 15 and minY + 39, for two world bottoms.
        for(int minY : new int[] { -64, 0 }) {
            int[] lo = same(3, 0, 3), hi = same(3, 24, 3);
            List<BlockPos> a = scripted(seed, minY, ccx, ccz, lo, problems), b = scripted(seed, minY, ccx, ccz, hi, problems);
            check(a.stream().allMatch(p -> p.getY() == minY + 15) && b.stream().allMatch(p -> p.getY() == minY + 39) && a.size() == 10 && b.size() == 10,
                    "world bottom " + minY + ": y = bottom + 15 for the draw 0 and bottom + 39 for the draw 24 (" + a.get(0).getY() + ", " + b.get(0).getY() + ")");
        }

        // Distance: a chunk whose tries sit 200 blocks east of the centre (rings 1-3 pass, 187 and 150 do not), then 800.
        for(int[] t : new int[][] { { 200, 6 }, { 800, 0 } }) {
            int vx = c[0] + t[0];
            int ox = Math.floorDiv(vx, 16) * 16;
            List<BlockPos> got = scripted(seed, -64, ox, ccz, same(vx - ox, 5, c[1] - ccz), problems);
            check(got.size() == t[1] && got.equals(originalVeins(seed, -64, ox, ccz, sameDraws(vx - ox, 5, c[1] - ccz))),
                    "tries " + t[0] + " blocks east of the centre: " + got.size() + " veins (expected " + t[1] + ", the original's on the same draws)");
        }

        // Inclusive bounds, both axes and both sides, for each ring: x == centre + range passes, centre + range + 1 does not.
        List<String> bounds = new ArrayList<>();
        for(int axis = 0; axis < 2; axis++) {
            for(int r = 1; r <= RINGS; r++) {
                int range = COL_RANGE / r;
                for(int side : new int[] { 1, -1 }) {
                    for(int extra : new int[] { 0, 1 }) {
                        int v = c[axis] + side * (range + extra);
                        int o = Math.floorDiv(v, 16) * 16;
                        int ox = axis == 0 ? o : ccx, oz = axis == 1 ? o : ccz;
                        int dx = axis == 0 ? v - o : c[0] - ccx, dz = axis == 1 ? v - o : c[1] - ccz;
                        List<BlockPos> got = scripted(seed, -64, ox, oz, same(dx, 1, dz), problems);
                        int expected = 2 * (extra == 0 ? r : r - 1);
                        List<BlockPos> oracle = originalVeins(seed, -64, ox, oz, sameDraws(dx, 1, dz));
                        if(got.size() != expected || !got.equals(oracle)) bounds.add((axis == 0 ? "x" : "z") + " = centre " + (side > 0 ? "+" : "-") + " (" + range + " + " + extra + "): "
                                + got.size() + " veins, expected " + expected);
                    }
                }
            }
        }
        check(bounds.isEmpty() && problems.isEmpty(), "inclusive bounds on both axes and sides for every ring (750, 375, 250, 187, 150): at centre +/- range the ring "
                + "and all larger ones pass (2r veins), at +/- (range + 1) only the larger ones (2(r - 1)): " + bounds + " " + problems);

        // Random draws: the production feature and the original algorithm over chunks from the centre outward, same source.
        int total = 0;
        List<String> diff = new ArrayList<>();
        Map<Integer, Integer> perRing = new LinkedHashMap<>();
        for(int step = 0; step <= 60; step++) {
            int ox = ccx + step * 16, oz = ccz - step * 8;
            long chunkSeed = 31L * step + seed;
            RandomSource a = RandomSource.create();
            a.setSeed(chunkSeed);
            Random b = new Random(chunkSeed);
            Feature.OreRecorder.PLACED.clear();
            Goal12BWorldGen.place(new Goal12BWorldGen.Region(world(-64), Math.floorDiv(ox, 16), Math.floorDiv(oz, 16), seed), a, new BlockPos(ox, -64, oz));
            List<BlockPos> got = placed();
            List<BlockPos> exp = originalVeins(seed, -64, ox, oz, b::nextInt);
            if(!got.equals(exp)) diff.add("chunk " + ox + "," + oz + ": " + got.size() + " / " + exp.size());
            total += got.size();
            perRing.merge(got.size(), 1, Integer::sum);
        }
        check(diff.isEmpty(), "61 chunks from the centre outward (16 blocks east and 8 north per step), each with its own random source: the production veins "
                + "equal the original algorithm's on the same draws: " + diff);
        info("deposit centre for seed " + seed + ": " + c[0] + ", " + c[1] + "; random chunks outward: " + total + " veins, chunks by vein count " + perRing);
        info("Feature.ORE is a recording stand-in (no 1.21.1 OreFeature, no vein shape, no draws of its own); the placed feature's chunk origin and "
                + "WorldgenRandom are not modelled, the fixture passes the chunk corner and the source");
        section("4. coltan deposit");
    }

    // ---- 5. Compass -------------------------------------------------------------------------------------------------------

    static void compass() {
        reset();
        ColtanCompassItem item = new ColtanCompassItem(new Item.Properties().stacksTo(1));
        ItemStack stack = new ItemStack(item);
        Player player = new Player();
        player.setPos(100.5, 64, -200.25);
        check(!ColtanCompassItem.hasTarget(stack), "a new compass has no target");
        ServerLevel server = new ServerLevel();
        server.seed = -4_242_424_242L;
        item.inventoryTick(stack, server, player, 0, true);
        int[] o = originalCentre(server.seed);
        check(ColtanCompassItem.hasTarget(stack) && (int) stack.get(NtmDataComponents.COLTAN_X) == o[0] && (int) stack.get(NtmDataComponents.COLTAN_Z) == o[1],
                "the first server inventoryTick writes COLTAN_X / COLTAN_Z = the original centre of the level seed (" + o[0] + ", " + o[1] + ")");
        ColtanDepositFeature.DepositCentre dc = ColtanDepositFeature.depositCentre(server.seed);
        check(dc.x() == o[0] && dc.z() == o[1], "the compass target is the deposit feature's centre");
        ServerLevel other = new ServerLevel();
        other.seed = 99L;
        item.inventoryTick(stack, server, player, 0, false);
        item.inventoryTick(stack, other, player, 0, false);
        check((int) stack.get(NtmDataComponents.COLTAN_X) == o[0] && (int) stack.get(NtmDataComponents.COLTAN_Z) == o[1],
                "later ticks (also in a level with another seed) keep the stored target, as the original writes colX / colZ only without a tag");
        Level plain = new Level();
        ItemStack fresh = new ItemStack(item);
        item.inventoryTick(fresh, plain, player, 0, true);
        check(!ColtanCompassItem.hasTarget(fresh) && NuclearTechMod.proxy.tooltips.isEmpty(), "a server-side level that is not a ServerLevel writes nothing and shows nothing");

        Level client = new Level();
        client.isClientSide = true;
        item.inventoryTick(fresh, client, player, 0, true);
        check(NuclearTechMod.proxy.tooltips.isEmpty() && !ColtanCompassItem.hasTarget(fresh), "client, no target: no distance line, nothing written");
        item.inventoryTick(stack, client, player, 0, true);
        double dx = player.getX() - o[0], dz = player.getZ() - o[1];
        String expected = ((int) Math.sqrt(dx * dx + dz * dz)) + "m";
        List<NuclearTechMod.Proxy.Tooltip> tips = NuclearTechMod.proxy.tooltips;
        check(tips.size() == 1 && tips.get(0).message().getString().equals(expected) && tips.get(0).id() == ServerProxy.ID_COMPASS && ServerProxy.ID_COMPASS == 2,
                "client with a target: one displayTooltip(\"" + expected + "\", ID_COMPASS = 2), the truncated horizontal distance: " + tips);
        check((int) stack.get(NtmDataComponents.COLTAN_X) == o[0], "the client tick does not change the target");
        section("5. compass");
    }

    // ---- 7. Cracking logic ---------------------------------------------------------------------------------------------------

    static MachineCatalyticCrackerBlockEntity bare(Level level, BlockPos pos) {
        MachineCatalyticCrackerBlockEntity be = new MachineCatalyticCrackerBlockEntity(pos, facing(level, pos, Direction.NORTH));
        level.put(be);
        return be;
    }

    static void tick(Level level, MachineCatalyticCrackerBlockEntity be) {
        level.time++;
        be.updateEntity();
    }

    /** The original crack() on fills: how many of the two loops run (TileEntityMachineCatalyticCracker.java:63-86). */
    static int originalRuns(int[] fill, int[] max, int left, int right) {
        int[] f = fill.clone();
        int runs = 0;
        for(int i = 0; i < RUNS; i++) {
            if(f[0] >= OIL_PER_RUN && f[1] >= STEAM_PER_RUN && f[2] + left <= max[2] && f[3] + right <= max[3] && f[4] + SPENT_PER_RUN <= max[4]) {
                f[0] -= OIL_PER_RUN; f[1] -= STEAM_PER_RUN; f[2] += left; f[3] += right; f[4] += SPENT_PER_RUN;
                runs++;
            }
        }
        return runs;
    }

    static int[] fills(MachineCatalyticCrackerBlockEntity be) {
        int[] f = new int[5];
        for(int i = 0; i < 5; i++) f[i] = be.tanks[i].getFill();
        return f;
    }

    static int[] maxes(MachineCatalyticCrackerBlockEntity be) {
        int[] f = new int[5];
        for(int i = 0; i < 5; i++) f[i] = be.tanks[i].getMaxFill();
        return f;
    }

    /** A fresh cracker of the given input type after one setup tick (no crack), then the fills; returns the deltas of one crack tick. */
    static int[] crackOnce(FluidType input, int[] fill) {
        reset();
        Level level = level();
        MachineCatalyticCrackerBlockEntity be = bare(level, new BlockPos(0, 64, 0));
        be.tanks[0].setTankType(input);
        level.time = 0;
        tick(level, be);
        for(int i = 0; i < 5; i++) be.tanks[i].setFill(fill[i]);
        level.time = INTERVAL - 1;
        int[] before = fills(be);
        tick(level, be);
        int[] after = fills(be);
        int[] d = new int[5];
        for(int i = 0; i < 5; i++) d[i] = after[i] - before[i];
        return d;
    }

    static void cracking() {
        reset();
        Object[][] table = originalCracking();
        List<String> wrong = new ArrayList<>();
        List<Map.Entry<FluidType, Pair<FluidStack, FluidStack>>> entries = new ArrayList<>(CrackingRecipes.cracking.entrySet());
        for(int i = 0; i < Math.max(table.length, entries.size()); i++) {
            if(i >= table.length || i >= entries.size()) { wrong.add("entry " + i + " missing"); continue; }
            Object[] t = table[i];
            Map.Entry<FluidType, Pair<FluidStack, FluidStack>> e = entries.get(i);
            Pair<FluidStack, FluidStack> p = e.getValue();
            if(e.getKey() != t[0] || p.getKey().type != t[1] || p.getKey().fill != (int) t[2] || p.getValue().type != t[3] || p.getValue().fill != (int) t[4]
                    || p.getKey().pressure != 0 || p.getValue().pressure != 0)
                wrong.add(i + ": " + e.getKey() + " -> " + p.getKey().type + " " + p.getKey().fill + " + " + p.getValue().type + " " + p.getValue().fill);
        }
        check(entries.size() == 12 && wrong.isEmpty(), "the 12 default cracking recipes are the original's, in its order, with its amounts (CrackingRecipes.java:41-55): " + wrong);
        check(CrackingRecipes.getCracking(Fluids.WATER) == null && CrackingRecipes.getCracking(Fluids.HOTCRACKOIL) == null, "water and hot cracked oil have no cracking recipe");

        Level level = level();
        MachineCatalyticCrackerBlockEntity be = bare(level, new BlockPos(0, 64, 0));
        FluidType[] types = { Fluids.BITUMEN, Fluids.STEAM, Fluids.OIL, Fluids.PETROLEUM, Fluids.SPENTSTEAM };
        boolean fresh = true;
        for(int i = 0; i < 5; i++) fresh &= be.tanks[i].getTankType() == types[i] && be.tanks[i].getMaxFill() == TANKS[i] && be.tanks[i].getFill() == 0;
        check(fresh, "a new tower: bitumen 4,000, steam 8,000, oil 4,000, petroleum gas 4,000, spent steam 800, all empty: " + tanks(be));

        // Every 5 game ticks, up to two runs.
        be.tanks[0].setTankType(Fluids.OIL);
        tick(level, be);
        check(be.tanks[2].getTankType() == Fluids.CRACKOIL && be.tanks[3].getTankType() == Fluids.PETROLEUM && be.tanks[4].getTankType() == Fluids.SPENTSTEAM
                && be.tanks[1].getTankType() == Fluids.STEAM, "crude oil as input: the outputs become cracked oil and petroleum gas on the next tick");
        be.tanks[0].setFill(4_000);
        be.tanks[1].setFill(8_000);
        level.time = 0;
        List<Long> crackTicks = new ArrayList<>();
        int events = 0;
        for(int t = 0; t < 100; t++) {
            int oil = be.tanks[0].getFill();
            tick(level, be);
            if(be.tanks[0].getFill() != oil) { crackTicks.add(level.time); events++; }
            if(be.tanks[0].getFill() < 200) { be.tanks[0].setFill(4_000); }
            if(be.tanks[1].getFill() < 400) be.tanks[1].setFill(8_000);
            be.tanks[2].setFill(0); be.tanks[3].setFill(0); be.tanks[4].setFill(0);
        }
        check(events == 20 && crackTicks.stream().allMatch(t -> t % INTERVAL == 0), "over 100 ticks the tower cracks on exactly the 20 ticks with gameTime % 5 == 0: " + crackTicks);
        int[] d = crackOnce(Fluids.OIL, new int[] { 4_000, 8_000, 0, 0, 0 });
        check(java.util.Arrays.equals(d, new int[] { -200, -400, 160, 40, 4 }), "one crack tick with full inputs: two runs, -200 oil, -400 steam, +160 cracked oil, +40 petroleum gas, +4 spent steam: "
                + java.util.Arrays.toString(d));
        info("peak: " + (RUNS * OIL_PER_RUN / INTERVAL) + " mB/t input and " + (RUNS * STEAM_PER_RUN / INTERVAL) + " mB/t steam");

        // Each default recipe: one crack tick with plenty of input gives two runs of exactly its outputs.
        List<String> recipes = new ArrayList<>();
        for(Object[] t : table) {
            int left = (int) t[2], right = (int) t[4];
            int[] r = crackOnce((FluidType) t[0], new int[] { 1_000, 1_000, 0, 0, 0 });
            if(!java.util.Arrays.equals(r, new int[] { -200, -400, 2 * left, 2 * right, 4 })) recipes.add(t[0] + ": " + java.util.Arrays.toString(r));
        }
        check(recipes.isEmpty(), "every default recipe cracks two runs of 100 mB with 200 mB steam into its two outputs and 2 mB spent steam per run: " + recipes);

        // Limits: each condition alone stops the second (or the first) run, as the original replayed on the same fills.
        int[][] cases = {
                { 150, 8_000, 0, 0, 0 }, { 99, 8_000, 0, 0, 0 }, { 4_000, 399, 0, 0, 0 }, { 4_000, 199, 0, 0, 0 },
                { 4_000, 8_000, 3_920, 0, 0 }, { 4_000, 8_000, 3_921, 0, 0 }, { 4_000, 8_000, 0, 3_980, 0 }, { 4_000, 8_000, 0, 3_981, 0 },
                { 4_000, 8_000, 0, 0, 796 }, { 4_000, 8_000, 0, 0, 798 }, { 4_000, 8_000, 0, 0, 799 }, { 4_000, 8_000, 0, 0, 800 } };
        int[] expectRuns = { 1, 0, 1, 0, 1, 0, 1, 0, 2, 1, 0, 0 };
        List<String> limits = new ArrayList<>();
        for(int i = 0; i < cases.length; i++) {
            int runs = originalRuns(cases[i], TANKS, 80, 20);
            int[] r = crackOnce(Fluids.OIL, cases[i]);
            int[] exp = { -100 * runs, -200 * runs, 80 * runs, 20 * runs, 2 * runs };
            if(runs != expectRuns[i] || !java.util.Arrays.equals(r, exp)) limits.add(java.util.Arrays.toString(cases[i]) + ": " + java.util.Arrays.toString(r) + " (original " + runs + " runs)");
        }
        check(limits.isEmpty(), "limits (oil < 100, steam < 200, no room in cracked oil, petroleum gas or the 800 mB spent steam tank) stop a run exactly as the original: " + limits);

        // An input without a recipe: outputs NONE, nothing cracks.
        reset();
        level = level();
        be = bare(level, new BlockPos(0, 64, 0));
        be.tanks[0].setTankType(Fluids.WATER);
        be.tanks[0].setFill(1_000);
        be.tanks[1].setFill(1_000);
        level.time = INTERVAL - 1;
        tick(level, be);
        check(be.tanks[2].getTankType() == Fluids.NONE && be.tanks[3].getTankType() == Fluids.NONE && be.tanks[4].getTankType() == Fluids.NONE
                && be.tanks[0].getFill() == 1_000 && be.tanks[1].getFill() == 1_000, "water (no recipe): outputs and spent steam become NONE, nothing cracks on a crack tick: " + tanks(be));

        // The identifier through the production block: the input type changes at once, the outputs on the next tick.
        reset();
        level = level();
        BlockPos core = Goal11ABlockAccess.place(CRACKER, level, new BlockPos(0, 64, 0), Direction.NORTH);
        be = (MachineCatalyticCrackerBlockEntity) level.getBlockEntity(core);
        be.tanks[0].setTankType(Fluids.OIL);
        be.tanks[0].setFill(1_000);
        level.time = 0;
        tick(level, be);
        Player player = new Player();
        ItemStack id = FluidIDMultiItem.createStack(Fluids.GAS);
        player.mainHand = id;
        player.shift = true;
        ItemInteractionResult sneaking = Goal12BBlockAccess.useItemOn(CRACKER, id, level, core.offset(1, 5, 1), player);
        check(sneaking == ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION && be.tanks[0].getTankType() == Fluids.OIL, "sneaking with the identifier passes and changes nothing");
        player.shift = false;
        ItemInteractionResult other = Goal12BBlockAccess.useItemOn(CRACKER, new ItemStack(NtmItems.SULFUR.get()), level, core.offset(1, 5, 1), player);
        check(other == ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION && be.tanks[0].getTankType() == Fluids.OIL, "another item passes and changes nothing");
        ItemInteractionResult used = Goal12BBlockAccess.useItemOn(CRACKER, id, level, core.offset(1, 5, 1), player);
        check(used == ItemInteractionResult.SUCCESS && be.tanks[0].getTankType() == Fluids.GAS && be.tanks[0].getFill() == 0 && be.tanks[2].getTankType() == Fluids.CRACKOIL
                        && player.messages.size() == 1,
                "the identifier on a dummy (server, not sneaking): the input becomes natural gas at once (the tank empties with the type change, FluidTank.setTankType), "
                        + "the outputs stay until the next tick, one chat message: " + tanks(be));
        tick(level, be);
        check(be.tanks[2].getTankType() == Fluids.PETROLEUM && be.tanks[3].getTankType() == Fluids.UNSATURATEDS && be.tanks[4].getTankType() == Fluids.SPENTSTEAM,
                "the next tick switches the outputs to petroleum gas and unsaturated hydrocarbons: " + tanks(be));
        Level clientLevel = level();
        clientLevel.isClientSide = true;
        BlockPos clientCore = Goal11ABlockAccess.place(CRACKER, clientLevel, new BlockPos(0, 64, 0), Direction.NORTH);
        MachineCatalyticCrackerBlockEntity clientBe = (MachineCatalyticCrackerBlockEntity) clientLevel.getBlockEntity(clientCore);
        ItemInteractionResult clientUse = Goal12BBlockAccess.useItemOn(CRACKER, id, clientLevel, clientCore, player);
        check(clientUse == ItemInteractionResult.SUCCESS && clientBe.tanks[0].getTankType() == Fluids.BITUMEN, "on the client the use succeeds without changing the type");
        section("7. cracking logic");
    }

    // ---- 8. Ports and proxies ----------------------------------------------------------------------------------------------

    /** Original MultiblockHandlerXR.rotate. */
    static int[] originalRotate(int[] dim, Direction dir) {
        if(dir == Direction.SOUTH) return dim;
        if(dir == Direction.NORTH) return new int[] { dim[0], dim[1], dim[3], dim[2], dim[5], dim[4] };
        if(dir == Direction.EAST) return new int[] { dim[0], dim[1], dim[5], dim[4], dim[2], dim[3] };
        if(dir == Direction.WEST) return new int[] { dim[0], dim[1], dim[4], dim[5], dim[3], dim[2] };
        return dim;
    }

    /** Original MultiblockHandlerXR.fillSpace: the positions and their dummy facings (later boxes overwrite earlier ones). */
    static void originalFill(Map<BlockPos, Direction> out, BlockPos core, int[] dim, Direction dir) {
        int[] rot = originalRotate(dim, dir);
        int x = core.getX(), y = core.getY(), z = core.getZ();
        for(int a = x - rot[4]; a <= x + rot[5]; a++) for(int b = y - rot[1]; b <= y + rot[0]; b++) for(int c = z - rot[2]; c <= z + rot[3]; c++) {
            Direction f;
            if(b < y) f = Direction.DOWN;
            else if(b > y) f = Direction.UP;
            else if(a < x) f = Direction.WEST;
            else if(a > x) f = Direction.EAST;
            else if(c < z) f = Direction.NORTH;
            else if(c > z) f = Direction.SOUTH;
            else continue;
            out.put(new BlockPos(a, b, c), f);
        }
    }

    /** Forge 1.7.10 ForgeDirection.getRotation(UP) (ROTATION_MATRIX[1] = {0, 1, 5, 4, 2, 3, 6} over D, U, N, S, W, E). */
    static Direction forgeRotationUp(Direction d) {
        return switch(d) {
            case NORTH -> Direction.EAST;
            case SOUTH -> Direction.WEST;
            case WEST -> Direction.NORTH;
            case EAST -> Direction.SOUTH;
            default -> d;
        };
    }

    /** Original getPorts (TileEntityMachineCatalyticCracker.java:127-136): proxy positions with their PortDef directions. */
    static List<DirPos> originalPorts(BlockPos c, Direction dir) {
        Direction rot = forgeRotationUp(dir);
        int dx = dir.getStepX(), dz = dir.getStepZ(), rx = rot.getStepX(), rz = rot.getStepZ(), x = c.getX(), y = c.getY(), z = c.getZ();
        return List.of(
                new DirPos(x + dx * 3 + rx, y, z + dz * 3 + rz, dir),
                new DirPos(x + dx * 3 - rx * 2, y, z + dz * 3 - rz * 2, dir),
                new DirPos(x - dx * 3 + rx, y, z - dz * 3 + rz, dir.getOpposite()),
                new DirPos(x - dx * 3 - rx * 2, y, z - dz * 3 - rz * 2, dir.getOpposite()),
                new DirPos(x + dx * 2 + rx * 2, y, z + dz * 2 + rz * 2, rot),
                new DirPos(x + dx * 2 - rx * 3, y, z + dz * 2 - rz * 3, rot.getOpposite()),
                new DirPos(x - dx * 2 + rx * 2, y, z - dz * 2 + rz * 2, rot),
                new DirPos(x - dx * 2 - rx * 3, y, z - dz * 2 - rz * 3, rot.getOpposite()));
    }

    static void ports() {
        BlockPos origin = new BlockPos(0, 64, 0);
        for(Direction dir : HORIZONTALS) {
            reset();
            Level level = level();
            BlockPos core = Goal11ABlockAccess.place(CRACKER, level, origin, dir);
            Map<BlockPos, Direction> expected = new LinkedHashMap<>();
            originalFill(expected, core, MAIN_DIM, dir);
            for(int[] box : EXTRA_DIMS) originalFill(expected, core, box, dir);
            List<DirPos> ports = originalPorts(core, dir);
            Set<BlockPos> extraExpected = new LinkedHashSet<>();
            for(DirPos p : ports) extraExpected.add(p.makeCompat());
            Set<BlockPos> all = parts(level, CRACKER);
            Set<BlockPos> union = new LinkedHashSet<>(expected.keySet());
            union.add(core);
            check(core.equals(origin) && all.equals(union) && ofType(level, CRACKER, DummyBlockType.CORE).equals(Set.of(core)),
                    dir + ": the production placement fills exactly the original's main box and four extra boxes, rotated (" + all.size() + " blocks, expected " + union.size() + ", one core)");
            boolean facings = true;
            for(Map.Entry<BlockPos, Direction> e : expected.entrySet()) facings &= level.getBlockState(e.getKey()).getValue(DummyableBlock.FACING) == e.getValue();
            check(facings, dir + ": every dummy points as the original's fillSpace sets it (later boxes overwrite earlier ones)");
            Set<BlockPos> extra = ofType(level, CRACKER, DummyBlockType.EXTRA);
            check(extra.equals(extraExpected) && extra.size() == 8, dir + ": EXTRA at exactly the 8 original port positions on the core layer: " + extra);
            boolean fluidOnly = true, none = true;
            for(BlockPos p : all) {
                BlockEntity b = level.getBlockEntity(p);
                if(extra.contains(p)) fluidOnly &= b instanceof ProxyComboBlockEntity combo && Goal12AProxyAccess.flags(combo).equals(
                        Map.of("inventory", false, "power", false, "conductor", false, "fluid", true, "heat", false, "moltenMetal", false));
                else if(!p.equals(core)) none &= b == null;
            }
            check(fluidOnly && none && level.getBlockEntity(core) instanceof MachineCatalyticCrackerBlockEntity,
                    dir + ": each EXTRA is a ProxyComboBlockEntity with only the fluid flag, the other dummies have no block entity");
            MachineCatalyticCrackerBlockEntity be = (MachineCatalyticCrackerBlockEntity) level.getBlockEntity(core);
            DirPos[] con = be.getConPos();
            boolean same = con.length == 8;
            for(int i = 0; i < 8 && same; i++) {
                DirPos p = ports.get(i);
                same = con[i].getDir() == p.getDir() && con[i].makeCompat().equals(p.makeCompat().relative(p.getDir())) && !all.contains(con[i].makeCompat());
            }
            check(same, dir + ": getConPos is the 8 original connections (PortDef.make: one block outward from each port, in its direction), all outside the structure");
            if(dir == Direction.NORTH) {
                List<BlockPos> stage2 = List.of(core.offset(1, 0, -3), core.offset(-2, 0, -3), core.offset(1, 0, 3), core.offset(-2, 0, 3),
                        core.offset(2, 0, -2), core.offset(-3, 0, -2), core.offset(2, 0, 2), core.offset(-3, 0, 2));
                check(new ArrayList<>(extraExpected).equals(stage2), "north: the ports are (+1,0,-3), (-2,0,-3), (+1,0,+3), (-2,0,+3), (+2,0,-2), (-3,0,-2), (+2,0,+2), (-3,0,+2)");
                Set<BlockPos> box = new LinkedHashSet<>();
                originalFill(new LinkedHashMap<>(), core, MAIN_DIM, dir);
                for(int x = -3; x <= 2; x++) for(int z = -3; z <= 3; z++) box.add(core.offset(x, 0, z));
                Map<BlockPos, Direction> mainOnly = new LinkedHashMap<>();
                originalFill(mainOnly, core, MAIN_DIM, dir);
                mainOnly.put(core, null);
                check(mainOnly.keySet().equals(box), "north: the main box is x -3..+2, y 0, z -3..+3 (42 blocks)");
            }
            info(dir + ": " + all.size() + " blocks, " + expected.size() + " dummies/extras around the core");
        }

        // checkRequirement: the empty space passes; one block in the main box or in any extra box fails; one outside passes.
        for(Direction dir : HORIZONTALS) {
            BlockPos clicked = origin.relative(dir, OFFSET);
            List<String> wrong = new ArrayList<>();
            Map<BlockPos, Direction> main = new LinkedHashMap<>();
            originalFill(main, origin, MAIN_DIM, dir);
            List<BlockPos> probes = new ArrayList<>(List.of(main.keySet().iterator().next()));
            for(int[] box : EXTRA_DIMS) {
                Map<BlockPos, Direction> cells = new LinkedHashMap<>();
                originalFill(cells, origin, box, dir);
                BlockPos only = null;
                for(BlockPos p : cells.keySet()) if(!main.containsKey(p)) { only = p; }
                probes.add(only);
            }
            Level empty = level();
            if(!Goal12BBlockAccess.checkRequirement(CRACKER, empty, clicked, dir, -OFFSET)) wrong.add("empty space refused");
            for(BlockPos p : probes) {
                Level l = level();
                l.states.put(p, Blocks.STONE.defaultBlockState());
                if(p == null || Goal12BBlockAccess.checkRequirement(CRACKER, l, clicked, dir, -OFFSET)) wrong.add("stone at " + p + " accepted");
            }
            Level outside = level();
            outside.states.put(origin.offset(0, 20, 0), Blocks.STONE.defaultBlockState());
            if(!Goal12BBlockAccess.checkRequirement(CRACKER, outside, clicked, dir, -OFFSET)) wrong.add("stone outside refused");
            check(wrong.isEmpty(), dir + ": checkRequirement passes the empty space and a block outside, fails for one stone block in the main box or in each extra box "
                    + "(outside the main box): " + wrong);
        }

        // Fluids: tanks 0 and 1 receive at every connection, 2, 3 and 4 send; a pipe next to no connection carries nothing.
        for(Direction dir : HORIZONTALS) {
            List<String> wrong = new ArrayList<>();
            for(int i = 0; i <= 8; i++) {
                for(int role = 0; role < 4; role++) {
                    reset();
                    Level level = level();
                    BlockPos core = Goal11ABlockAccess.place(CRACKER, level, origin, dir);
                    MachineCatalyticCrackerBlockEntity be = (MachineCatalyticCrackerBlockEntity) level.getBlockEntity(core);
                    be.tanks[0].setTankType(Fluids.OIL);
                    tick(level, be);
                    DirPos[] con = be.getConPos();
                    // Off every connection (they lie within 4 blocks of the core on both axes in all facings).
                    BlockPos at = i < 8 ? con[i].makeCompat() : core.offset(7, 0, 7);
                    Direction out = i < 8 ? con[i].getDir() : dir;
                    FluidType type = new FluidType[] { Fluids.OIL, Fluids.STEAM, Fluids.CRACKOIL, Fluids.SPENTSTEAM }[role];
                    int tank = new int[] { 0, 1, 2, 4 }[role];
                    boolean receive = role < 2;
                    pipe(level, at, type);
                    BarrelBlockEntity barrel = barrel(level, at.relative(out), type, receive ? 1_000 : 0, receive ? 2 : 0);
                    if(!receive) be.tanks[tank].setFill(tank == 4 ? 600 : 1_000);
                    // The setup tick looked the connections up before the pipe existed; drop those cached lookups.
                    BlockEntityAccessCache.cache.clear();
                    net(level);
                    level.time = 1;
                    barrel.updateEntity();
                    be.updateEntity();
                    transfer(level);
                    int moved = receive ? be.tanks[tank].getFill() : barrel.tank.getFill();
                    int want = i < 8 ? (receive ? 1_000 : (tank == 4 ? 600 : 1_000)) : 0;
                    if(moved != want) wrong.add((i < 8 ? "connection " + i : "no connection") + " " + type + ": " + moved + " (expected " + want + ")");
                }
            }
            check(wrong.isEmpty(), dir + ": a pipe at each of the 8 connections delivers oil and steam into tanks 0 and 1 and takes cracked oil and spent steam out of tanks 2 and 4; "
                    + "a pipe at no connection moves nothing: " + wrong);
        }
        reset();
        Level level = level();
        MachineCatalyticCrackerBlockEntity be = bare(level, new BlockPos(0, 64, 0));
        check(java.util.Arrays.equals(be.getReceivingTanks(), new FluidTank[] { be.tanks[0], be.tanks[1] })
                        && java.util.Arrays.equals(be.getSendingTanks(), new FluidTank[] { be.tanks[2], be.tanks[3], be.tanks[4] })
                        && be.getAllTanks() == be.tanks && be.getTankToPaste() == be.tanks[0],
                "receiving tanks 0, 1; sending 2, 3, 4 (original :166-174); all tanks; the input tank is the one an identifier copy pastes");
        section("8. ports and proxies");
    }

    // ---- 9m. Save and sync ----------------------------------------------------------------------------------------------------

    static void sync() {
        reset();
        Level level = level();
        MachineCatalyticCrackerBlockEntity be = bare(level, new BlockPos(0, 64, 0));
        be.tanks[0].setTankType(Fluids.GAS);
        tick(level, be);
        int[] fill = { 3_100, 7_200, 1_300, 1_400, 650 };
        for(int i = 0; i < 5; i++) be.tanks[i].setFill(fill[i]);
        CompoundTag tag = new CompoundTag();
        nbt(be, "saveAdditional", tag);
        Set<String> keys = new LinkedHashSet<>(List.of("muffled", "tilted"));
        for(int i = 0; i < 5; i++) keys.addAll(List.of("tank" + i, "tank" + i + "_max", "tank" + i + "_type", "tank" + i + "_p"));
        check(tag.getAllKeys().equals(keys), "saveAdditional writes tank0..tank4 (fill, max, type, pressure) besides the base fields: " + tag.getAllKeys());
        MachineCatalyticCrackerBlockEntity loaded = bare(level, new BlockPos(20, 64, 0));
        nbt(loaded, "loadAdditional", tag);
        boolean same = true;
        for(int i = 0; i < 5; i++) same &= loaded.tanks[i].getFill() == fill[i] && loaded.tanks[i].getTankType() == be.tanks[i].getTankType() && loaded.tanks[i].getMaxFill() == TANKS[i];
        check(same, "loadAdditional reads every tank back (types natural gas, steam, petroleum gas, unsaturateds, spent steam): " + tanks(loaded));
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        be.serialize(buf);
        List<Object> values = buf.values();
        List<Object> expected = new ArrayList<>(List.of(false, false));
        for(int i = 0; i < 5; i++) expected.addAll(List.of(fill[i], TANKS[i], be.tanks[i].getTankType().getID(), (short) 0));
        check(values.equals(expected), "serialize: muffled, tilted (base), then the five tanks in order (fill, max, type, pressure): " + values);
        MachineCatalyticCrackerBlockEntity copy = bare(level, new BlockPos(40, 64, 0));
        copy.deserialize(buf);
        boolean back = buf.readableBytes() == 0;
        for(int i = 0; i < 5; i++) back &= copy.tanks[i].getFill() == fill[i] && copy.tanks[i].getTankType() == be.tanks[i].getTankType();
        check(back, "deserialize reads the five tanks back and consumes the buffer: " + tanks(copy));
        int packs = be.packs;
        tick(level, be);
        check(be.packs == packs + 1 && be.packRange == 25, "every server tick sends one sync pack of range 25 (networkPackNT(25))");
        section("9m. save and sync");
    }

    // ---- 11. Whole chains -----------------------------------------------------------------------------------------------------

    record Flow(String name, IntSupplier source, IntSupplier target) {}

    static void select(MachineChemicalPlantBlockEntity be, String selection) {
        CompoundTag tag = new CompoundTag();
        tag.putInt("index", 0);
        tag.putString("selection", selection);
        be.receiveControl(tag);
    }

    static MachineChemicalPlantBlockEntity plant(Level level, BlockPos pos) {
        BlockState state = new BlockState();
        level.states.put(pos, state);
        MachineChemicalPlantBlockEntity be = new MachineChemicalPlantBlockEntity(pos, state);
        level.put(be);
        return be;
    }

    /** One cracker crack tick checked against the original: returns the number of runs, or -1 if the deltas differ. */
    static int crackShape(int[] before, int[] after, int[] max, int left, int right, boolean crackTick) {
        int runs = crackTick ? originalRuns(before, max, left, right) : 0;
        int[] exp = { before[0] - 100 * runs, before[1] - 200 * runs, before[2] + left * runs, before[3] + right * runs, before[4] + 2 * runs };
        return java.util.Arrays.equals(after, exp) ? runs : -1;
    }

    static void chainRubber() {
        reset();
        Level level = level();
        BlockPos core = Goal11ABlockAccess.place(CRACKER, level, new BlockPos(0, 64, 0), Direction.NORTH);
        MachineCatalyticCrackerBlockEntity cr = (MachineCatalyticCrackerBlockEntity) level.getBlockEntity(core);
        cr.tanks[0].setTankType(Fluids.GAS);
        DirPos[] con = cr.getConPos();
        pipe(level, con[0].makeCompat(), Fluids.GAS);
        BarrelBlockEntity gas = barrel(level, con[0].makeCompat().relative(con[0].getDir()), Fluids.GAS, 9_000_000, 2);
        pipe(level, con[1].makeCompat(), Fluids.STEAM);
        BarrelBlockEntity steam = barrel(level, con[1].makeCompat().relative(con[1].getDir()), Fluids.STEAM, 9_000_000, 2);
        pipe(level, con[2].makeCompat(), Fluids.SPENTSTEAM);
        BarrelBlockEntity spent = barrel(level, con[2].makeCompat().relative(con[2].getDir()), Fluids.SPENTSTEAM, 0, 0);
        pipe(level, con[3].makeCompat(), Fluids.PETROLEUM);
        BarrelBlockEntity petro = barrel(level, con[3].makeCompat().relative(con[3].getDir()), Fluids.PETROLEUM, 0, 0);
        BlockPos plantPos = new BlockPos(30, 64, 0);
        MachineChemicalPlantBlockEntity rubber = plant(level, plantPos);
        select(rubber, "chem.rubber");
        route(level, Fluids.UNSATURATEDS, con[4].makeCompat(), plantPos.offset(-2, 0, 0), 85);
        net(level);
        level.time = 0;

        int ticks = 3_000;
        long gasIn = 0, gasCracked = 0, unsatMade = 0, crackRuns = 0, rubberRuns = 0, rubberOut = 0, sulfurIn = 0, unsatUsed = 0;
        List<String> violations = new ArrayList<>();
        List<Flow> flows = List.of(
                new Flow("natural gas", () -> gas.tank.getFill(), () -> cr.tanks[0].getFill()),
                new Flow("steam", () -> steam.tank.getFill(), () -> cr.tanks[1].getFill()),
                new Flow("petroleum gas", () -> cr.tanks[2].getFill(), () -> petro.tank.getFill()),
                new Flow("unsaturateds", () -> cr.tanks[3].getFill(), () -> rubber.inputTanks[0].getFill()),
                new Flow("spent steam", () -> cr.tanks[4].getFill(), () -> spent.tank.getFill()));
        for(int t = 1; t <= ticks; t++) {
            level.time++;
            if(rubber.slots.get(4).isEmpty()) { rubber.slots.set(4, new ItemStack(NtmItems.SULFUR.get(), RUBBER_SULFUR)); sulfurIn += RUBBER_SULFUR; }
            rubber.power = rubber.maxPower;
            gas.updateEntity();
            steam.updateEntity();
            int[] b = fills(cr);
            cr.updateEntity();
            int runs = crackShape(b, fills(cr), maxes(cr), 30, 20, level.time % INTERVAL == 0);
            if(runs < 0) violations.add(t + ": cracker " + java.util.Arrays.toString(b) + " -> " + java.util.Arrays.toString(fills(cr)));
            else { crackRuns += runs; }
            unsatMade += cr.tanks[3].getFill() - b[3];
            gasCracked += b[0] - cr.tanks[0].getFill();
            int u0 = rubber.inputTanks[0].getFill(), s0 = rubber.slots.get(4).getCount();
            rubber.updateEntity();
            if(rubber.slots.get(7).getCount() > 0) {
                rubberRuns++;
                if(u0 - rubber.inputTanks[0].getFill() != RUBBER_UNSAT || s0 - rubber.slots.get(4).getCount() != RUBBER_SULFUR || !rubber.slots.get(7).is(NtmItems.INGOT_RUBBER.get())
                        || rubber.slots.get(7).getCount() != RUBBER_OUT) violations.add(t + ": rubber run");
                unsatUsed += u0 - rubber.inputTanks[0].getFill();
                rubberOut += rubber.slots.get(7).getCount();
                rubber.slots.set(7, ItemStack.EMPTY);
            } else if(u0 != rubber.inputTanks[0].getFill()) violations.add(t + ": rubber input changed without a run");
            spent.updateEntity();
            petro.updateEntity();
            int[] src = new int[flows.size()], dst = new int[flows.size()];
            for(int i = 0; i < flows.size(); i++) { src[i] = flows.get(i).source().getAsInt(); dst[i] = flows.get(i).target().getAsInt(); }
            int g0 = gas.tank.getFill();
            transfer(level);
            gasIn += g0 - gas.tank.getFill();
            for(int i = 0; i < flows.size(); i++) {
                int left = src[i] - flows.get(i).source().getAsInt(), arrived = flows.get(i).target().getAsInt() - dst[i];
                if(left != arrived) violations.add(t + ": " + flows.get(i).name() + " " + left + " left, " + arrived + " arrived");
            }
        }
        check(violations.isEmpty(), "every tick: the tower cracks only on gameTime % 5 == 0, each crack as the original (up to two runs, -100 / -200 / +30 / +20 / +2), "
                + "every rubber run takes 500 mB unsaturateds and 1 sulfur for 2 rubber, every pipe delivers exactly what leaves its source ("
                + violations.size() + " violations" + (violations.isEmpty() ? "" : ", first " + violations.subList(0, Math.min(3, violations.size()))) + ")");
        check(gasIn == 100L * crackRuns + cr.tanks[0].getFill() && unsatMade == unsatUsed + cr.tanks[3].getFill() + rubber.inputTanks[0].getFill()
                        && 30L * crackRuns == cr.tanks[2].getFill() + petro.tank.getFill() && 2L * crackRuns == cr.tanks[4].getFill() + spent.tank.getFill()
                        && 9_000_000L - steam.tank.getFill() == 200L * crackRuns + cr.tanks[1].getFill(),
                "over " + ticks + " ticks every fluid balances: gas " + gasIn + " = 100 x " + crackRuns + " runs + " + cr.tanks[0].getFill() + "; unsaturateds " + unsatMade
                        + " = " + unsatUsed + " used + stock; petroleum gas, spent steam and steam likewise");
        check(rubberRuns > 0 && rubberOut == RUBBER_OUT * rubberRuns && sulfurIn == rubberRuns * RUBBER_SULFUR + rubber.slots.get(4).getCount(),
                "the chain makes rubber: " + rubberRuns + " runs, " + rubberOut + " rubber, every sulfur accounted for");
        check(gasCracked > 0 && unsatMade * 2_500L == gasCracked * RUBBER_UNSAT && gasIn >= 2_500L * rubberRuns,
                "measured: " + unsatMade + " mB unsaturateds from " + gasCracked + " mB cracked natural gas, i.e. one chem.rubber run (500 mB) per 2,500 mB gas "
                        + "(GOAL12B.md), and the gas taken in covers the runs made");
        info(String.format("rubber chain over %d ticks: %,d mB gas in %d cracking runs (%.2f runs/t), %,d mB unsaturateds, %d rubber runs; the plant (100 ticks a run) is the "
                + "bottleneck once unsaturateds back up", ticks, gasIn, crackRuns, crackRuns / (double) ticks, unsatMade, rubberRuns));
    }

    static void chainBakelite() {
        reset();
        Level level = level();
        BlockPos core = Goal11ABlockAccess.place(CRACKER, level, new BlockPos(0, 64, 0), Direction.NORTH);
        MachineCatalyticCrackerBlockEntity cr = (MachineCatalyticCrackerBlockEntity) level.getBlockEntity(core);
        cr.tanks[0].setTankType(Fluids.OIL);
        DirPos[] con = cr.getConPos();
        pipe(level, con[0].makeCompat(), Fluids.OIL);
        BarrelBlockEntity oil = barrel(level, con[0].makeCompat().relative(con[0].getDir()), Fluids.OIL, 9_000_000, 2);
        pipe(level, con[1].makeCompat(), Fluids.STEAM);
        BarrelBlockEntity steam = barrel(level, con[1].makeCompat().relative(con[1].getDir()), Fluids.STEAM, 9_000_000, 2);
        pipe(level, con[2].makeCompat(), Fluids.SPENTSTEAM);
        BarrelBlockEntity spent = barrel(level, con[2].makeCompat().relative(con[2].getDir()), Fluids.SPENTSTEAM, 0, 0);

        BlockPos boilerPos = new BlockPos(30, 64, 0);
        MachineHeatBoilerBlockEntity boiler = new MachineHeatBoilerBlockEntity(boilerPos, facing(level, boilerPos, Direction.NORTH));
        level.put(boiler);
        check(boiler.trySetInputType(Fluids.CRACKOIL), "the heat boiler accepts cracked oil (FT_Heatable, boiler efficiency above 0)");
        BlockPos ovenPos = boilerPos.below();
        HeaterOvenBlockEntity oven = new HeaterOvenBlockEntity(ovenPos, new BlockState());
        level.states.put(ovenPos, new BlockState());
        level.put(oven);
        final int source = 10_100;
        route(level, Fluids.CRACKOIL, con[4].makeCompat(), boilerPos.offset(-2, 0, 0), 85);

        MachineRefineryBlockEntity rf = (MachineRefineryBlockEntity) level.getBlockEntity(Goal11ABlockAccess.place(REFINERY, level, new BlockPos(50, 64, 0), Direction.NORTH));
        BlockPos r = rf.getBlockPos();
        rf.tanks[0].setTankType(Fluids.HOTCRACKOIL);
        route(level, Fluids.HOTCRACKOIL, boilerPos.offset(2, 0, 0), r.offset(-2, 0, 1), 80);
        pipe(level, r.offset(2, 0, 1), Fluids.NAPHTHA_CRACK);
        BarrelBlockEntity naphtha = barrel(level, r.offset(3, 0, 1), Fluids.NAPHTHA_CRACK, 0, 0);
        pipe(level, r.offset(2, 0, -1), Fluids.LIGHTOIL_CRACK);
        BarrelBlockEntity light = barrel(level, r.offset(3, 0, -1), Fluids.LIGHTOIL_CRACK, 0, 0);
        pipe(level, r.offset(-2, 0, -1), Fluids.UNSATURATEDS);
        BarrelBlockEntity unsat = barrel(level, r.offset(-3, 0, -1), Fluids.UNSATURATEDS, 0, 0);
        BlockPos plantPos = new BlockPos(70, 64, -30);
        MachineChemicalPlantBlockEntity bakelite = plant(level, plantPos);
        select(bakelite, "chem.bakelite");
        route(level, Fluids.AROMATICS, r.offset(1, 0, -2), plantPos.offset(-1, 0, -2), 75);
        route(level, Fluids.PETROLEUM, con[3].makeCompat(), plantPos.offset(1, 0, -2), 90);
        net(level);
        level.time = 0;

        int ticks = 3_000;
        long oilIn = 0, hotUsed = 0, aromaMade = 0, crackRuns = 0, boiled = 0, refineRuns = 0, bakeliteRuns = 0, bakeliteOut = 0, aromaUsed = 0, petroUsed = 0, heatPulled = 0;
        List<String> violations = new ArrayList<>();
        List<Flow> flows = List.of(
                new Flow("crude oil", () -> oil.tank.getFill(), () -> cr.tanks[0].getFill()),
                new Flow("steam", () -> steam.tank.getFill(), () -> cr.tanks[1].getFill()),
                new Flow("cracked oil", () -> cr.tanks[2].getFill(), () -> boiler.tanks[0].getFill()),
                new Flow("petroleum gas", () -> cr.tanks[3].getFill(), () -> bakelite.inputTanks[1].getFill()),
                new Flow("spent steam", () -> cr.tanks[4].getFill(), () -> spent.tank.getFill()),
                new Flow("hot cracked oil", () -> boiler.tanks[1].getFill(), () -> rf.tanks[0].getFill()),
                new Flow("cracked naphtha", () -> rf.tanks[1].getFill(), () -> naphtha.tank.getFill()),
                new Flow("cracked light oil", () -> rf.tanks[2].getFill(), () -> light.tank.getFill()),
                new Flow("aromatics", () -> rf.tanks[3].getFill(), () -> bakelite.inputTanks[0].getFill()),
                new Flow("unsaturateds", () -> rf.tanks[4].getFill(), () -> unsat.tank.getFill()));
        for(int t = 1; t <= ticks; t++) {
            level.time++;
            rf.power = MachineRefineryBlockEntity.MAX_POWER;
            bakelite.power = bakelite.maxPower;
            oil.updateEntity();
            steam.updateEntity();
            int[] b = fills(cr);
            cr.updateEntity();
            int runs = crackShape(b, fills(cr), maxes(cr), 80, 20, level.time % INTERVAL == 0);
            if(runs < 0) violations.add(t + ": cracker " + java.util.Arrays.toString(b) + " -> " + java.util.Arrays.toString(fills(cr)));
            else crackRuns += runs;
            oven.heatEnergy = source;
            int h0 = boiler.heat, bi0 = boiler.tanks[0].getFill(), bo0 = boiler.tanks[1].getFill();
            boiler.updateEntity();
            int pull = source - oven.heatEnergy, used = bi0 - boiler.tanks[0].getFill();
            if(boiler.tanks[1].getFill() - bo0 != used || boiler.heat != h0 + pull - CRACKOIL_TU * used || boiler.hasExploded)
                violations.add(t + ": boiler " + used + " mB cracked oil -> " + (boiler.tanks[1].getFill() - bo0) + " hot, heat " + h0 + " + " + pull + " -> " + boiler.heat);
            boiled += used;
            heatPulled += pull;
            int[] rb = new int[5];
            for(int i = 0; i < 5; i++) rb[i] = rf.tanks[i].getFill();
            rf.updateEntity();
            int[] ra = new int[5];
            for(int i = 0; i < 5; i++) ra[i] = rf.tanks[i].getFill();
            if(ra[0] != rb[0]) {
                refineRuns++;
                hotUsed += rb[0] - ra[0];
                aromaMade += ra[3] - rb[3];
                if(rb[0] - ra[0] != REFINERY_INPUT || ra[1] - rb[1] != CRACK_NAPHTHA || ra[2] - rb[2] != CRACK_LIGHT || ra[3] - rb[3] != CRACK_AROMA || ra[4] - rb[4] != CRACK_UNSAT)
                    violations.add(t + ": refinery run " + java.util.Arrays.toString(rb) + " -> " + java.util.Arrays.toString(ra));
            }
            int a0 = bakelite.inputTanks[0].getFill(), p0 = bakelite.inputTanks[1].getFill();
            bakelite.updateEntity();
            if(bakelite.slots.get(7).getCount() > 0) {
                bakeliteRuns++;
                if(a0 - bakelite.inputTanks[0].getFill() != BAKELITE_AROMA || p0 - bakelite.inputTanks[1].getFill() != BAKELITE_PETRO
                        || !bakelite.slots.get(7).is(NtmItems.INGOT_BAKELITE.get()) || bakelite.slots.get(7).getCount() != BAKELITE_OUT) violations.add(t + ": bakelite run");
                aromaUsed += a0 - bakelite.inputTanks[0].getFill();
                petroUsed += p0 - bakelite.inputTanks[1].getFill();
                bakeliteOut += bakelite.slots.get(7).getCount();
                bakelite.slots.set(7, ItemStack.EMPTY);
            } else if(a0 != bakelite.inputTanks[0].getFill() || p0 != bakelite.inputTanks[1].getFill()) violations.add(t + ": bakelite inputs changed without a run");
            spent.updateEntity();
            naphtha.updateEntity();
            light.updateEntity();
            unsat.updateEntity();
            int[] src = new int[flows.size()], dst = new int[flows.size()];
            for(int i = 0; i < flows.size(); i++) { src[i] = flows.get(i).source().getAsInt(); dst[i] = flows.get(i).target().getAsInt(); }
            int o0 = oil.tank.getFill();
            transfer(level);
            oilIn += o0 - oil.tank.getFill();
            for(int i = 0; i < flows.size(); i++) {
                int left = src[i] - flows.get(i).source().getAsInt(), arrived = flows.get(i).target().getAsInt() - dst[i];
                if(left != arrived) violations.add(t + ": " + flows.get(i).name() + " " + left + " left, " + arrived + " arrived");
            }
        }
        check(violations.isEmpty(), "every tick: the tower cracks as the original (-100 / -200 / +80 cracked oil / +20 petroleum gas / +2), the heat boiler turns cracked oil 1:1 "
                + "into hot cracked oil at 10 TU per mB, every refinery run is -100 hot cracked oil, +40 cracked naphtha, +30 cracked light oil, +15 aromatics, +15 unsaturateds, "
                + "every bakelite run takes 500 mB aromatics and 500 mB petroleum gas for 1 bakelite, every pipe delivers exactly what leaves its source ("
                + violations.size() + " violations" + (violations.isEmpty() ? "" : ", first " + violations.subList(0, Math.min(3, violations.size()))) + ")");
        long crackoilMade = 80L * crackRuns;
        check(oilIn == 100L * crackRuns + cr.tanks[0].getFill() && crackoilMade == boiled + cr.tanks[2].getFill() + boiler.tanks[0].getFill()
                        && boiled == 100L * refineRuns + boiler.tanks[1].getFill() + rf.tanks[0].getFill()
                        && 15L * refineRuns == aromaUsed + rf.tanks[3].getFill() + bakelite.inputTanks[0].getFill()
                        && 20L * crackRuns == petroUsed + cr.tanks[3].getFill() + bakelite.inputTanks[1].getFill()
                        && heatPulled == boiler.heat + CRACKOIL_TU * boiled,
                "over " + ticks + " ticks every fluid balances: crude oil " + oilIn + " = 100 x " + crackRuns + " + stock; cracked oil " + crackoilMade + " = " + boiled
                        + " boiled + stock; hot cracked oil " + boiled + " = 100 x " + refineRuns + " refinery runs + stock; aromatics and petroleum gas into bakelite; heat "
                        + heatPulled + " TU = boiler " + boiler.heat + " + 10 x " + boiled);
        check(bakeliteRuns > 0 && bakeliteOut == bakeliteRuns * BAKELITE_OUT && aromaUsed == 500L * bakeliteRuns && petroUsed == 500L * bakeliteRuns,
                "the chain makes bakelite: " + bakeliteRuns + " runs");
        check(hotUsed > 0 && aromaMade * REFINERY_INPUT == hotUsed * CRACK_AROMA,
                "measured: " + aromaMade + " mB aromatics from " + hotUsed + " mB hot cracked oil, 15 per 100 mB (GOAL12B.md), so one bakelite run needs "
                        + (BAKELITE_AROMA * REFINERY_INPUT / CRACK_AROMA) + " mB hot cracked oil (integer part)");
        info(String.format("bakelite chain over %d ticks: %,d mB crude oil in %d cracking runs, %,d mB boiled, %d refinery runs, %d bakelite runs, %,d mB petroleum gas used",
                ticks, oilIn, crackRuns, boiled, refineRuns, bakeliteRuns, petroUsed));
        info("the steam and crude oil sources are production barrels (mode 2), the sinks barrels (mode 0); the boiler's heat source is a production heating oven whose "
                + "heat the fixture sets to " + source + " TU before every boiler tick; plant and refinery power are refilled by the fixture");
    }

    static void chains() {
        chainRubber();
        chainBakelite();
        section("11. whole chains");
    }

    public static void main(String[] args) {
        run("4. coltan deposit", Goal12BRegression::deposit);
        run("5. compass", Goal12BRegression::compass);
        run("7. cracking logic", Goal12BRegression::cracking);
        run("8. ports and proxies", Goal12BRegression::ports);
        run("9m. save and sync", Goal12BRegression::sync);
        run("11. whole chains", Goal12BRegression::chains);
        System.out.println("Goal 12B machine world: " + checks + " checks passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
