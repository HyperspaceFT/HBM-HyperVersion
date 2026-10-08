package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import api.hbm.block.IToolable.ToolType;
import com.hbm.blockentity.Goal11AProxyAccess;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.boiler.MachineHeatBoilerBlockEntity;
import com.hbm.blockentity.machine.heater.Goal11AHeaterAccess;
import com.hbm.blockentity.machine.heater.HeaterOilburnerBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterOvenBlockEntity;
import com.hbm.blockentity.machine.oil.MachineFrackingTowerBlockEntity;
import com.hbm.blockentity.machine.oil.MachineOilWellBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.machine.storage.BatteryBaseBlockEntity;
import com.hbm.blockentity.machine.storage.BatterySocketBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.Goal11ABlockAccess;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.MachineOilWellBlock;
import com.hbm.blocks.machine.heater.HeaterOilburnerBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.trait.FT_Flammable;
import com.hbm.inventory.fluid.trait.FT_Polluting;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.hbm.world.feature.Goal11AWorldGen;
import com.hbm.world.feature.Goal11AWorldGen.CountingRandom;
import com.hbm.world.feature.Goal11AWorldGen.Region;
import com.hbm.world.feature.Goal11AWorldGen.World;
import com.hbm.world.feature.OilSpot;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.Containers;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.neoforged.neoforge.network.PacketDistributor;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.function.Function;

/**
 * Goal 11A: the derrick's connections and drill depth, the oil bubble's placement, replacement and trial chamber
 * avoidance, the fluid burner (anvil entries, top heat source, settings, pollution, saving), the whole gas -> heat ->
 * steam -> power chain and the drain of a bubble, against real production classes in the Goal 10C machine world.
 * Expected numbers are read from the original at 608fec4, not from the NEO classes under test:
 * TilePortShapes.java:26-30 (horizontal: +X, -X, +Z, -Z, -Y at the core) and TileEntityMachineOilWell.java:40;
 * TileEntityOilDrillBase.java:95-153 (the drill loop and the indicator), :211-213 (depth 5), :236-265 (suckRec, layer > 64);
 * TileEntityMachineFrackingTower.java:77-79 (depth 0); TileEntityMachineOilWell.java:32-38 and :93-105 (100,000 HE,
 * 100 HE/t, 50 ticks, 500 mB oil, 100-500 mB gas, 5% drain); MapGenBubble.java:27-28 (Y 15 + nextInt(25)), :62-63
 * (radius nextInt(max - min) + min, r^2 / 2 as a double), :73-80 (replace stone where x^2 + z^2 + 3y^2 < r^2 / 2);
 * HbmWorld.java:73 (setSize(8, 16)); AnvilRecipes.java:283-289 (burner: 4 steel tanks, 3 steel pipes, 12 titanium
 * ingots, 8 copper ingots, tier 2; no recycling entry); HeaterOilburner.java:31-44 (extras: above the core heat, the
 * sides fluid); TileEntityHeaterOilburner.java:31 (off), :54-79 (burn loop, pollute every 5 ticks while burning),
 * :134-139 (setting 1-10), :173-178 (receiveControl only toggles); TileEntityMachinePolluting.java:38-63 (per call and
 * pollution type ceil(value * 100) mB into a 100 mB tank, the overflow / 100 into the world); PollutionHandler.java:47
 * and Fluids.java:225-242, :270-283, :682-714, :947-955 (soot rates, P_OIL/P_GAS, the fuel heat formula and round()).
 */
public class Goal11ARegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    private static final Direction[] HORIZONTALS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};
    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());

    // ---- Original numbers (608fec4), independent of the NEO constants under test -----------------------------------
    /** TilePortShapes.horizontal: POS_X, NEG_X, POS_Z, NEG_Z, NEG_Y, each at the neighbour of the core in that direction. */
    static final Direction[] ORIGINAL_PORTS = {Direction.EAST, Direction.WEST, Direction.SOUTH, Direction.NORTH, Direction.DOWN};
    static final int ORIGINAL_DRILL_DEPTH = 5;      // TileEntityOilDrillBase.getDrillDepth, counted from the bedrock floor Y 0
    static final int ORIGINAL_FRACKING_DEPTH = 0;   // TileEntityMachineFrackingTower.getDrillDepth
    static final int ORIGINAL_DFS_LIMIT = 64;       // suckRec: if(layer > 64) return false
    static final long DERRICK_MAX_POWER = 100_000L;
    static final int DERRICK_HE = 100, DERRICK_DELAY = 50, OIL_PER_SUCK = 500, GAS_MIN = 100, GAS_MAX = 500;
    static final int BUBBLE_MIN_Y = 15, BUBBLE_RANGE_Y = 25, BUBBLE_MIN_SIZE = 8, BUBBLE_MAX_SIZE = 16;
    static final int BURNER_MAX_SETTING = 10;
    static final int BURNER_MAX_HEAT = 100_000;      // TileEntityHeaterOilburner.maxHeatEnergy
    static final float SOOT_PER_SECOND = 1F / 25F;
    static final float SOOT_UNREFINED_OIL = SOOT_PER_SECOND * 0.1F, SOOT_GAS = SOOT_PER_SECOND * 0.005F;
    static final float POLLUTION_TANK = 100F;        // TileEntityMachinePolluting: smoke tanks of `buffer` = 100 mB

    /** Original Fluids.round (Fluids.java:947-955). */
    static long originalRound(long l) {
        if(l > 10_000_000L) return l - (l % 100_000L);
        if(l > 1_000_000L) return l - (l % 10_000L);
        if(l > 100_000L) return l - (l % 1_000L);
        if(l > 10_000L) return l - (l % 100L);
        if(l > 1_000L) return l - (l % 10L);
        return l;
    }

    /** Original registerCalculatedFuel heat values (Fluids.java:682-714: baseline 100,000, flammability, demand, complexity). */
    static final long OIL_HEAT = originalRound((long) (100_000L / 1D * 0.25D * 1.0D));
    static final long GAS_HEAT = originalRound((long) (100_000L / 1D * 1.0D * 0.5D));
    static final long HEATINGOIL_HEAT = originalRound((long) (100_000L / 0.31 * 1.0D * 1.0D * 1.1D * 1.05D * 1.05D));

    /** TileEntityMachinePolluting.pollute at steady state (full 100 mB tank, no outlet): the overflow / 100 per call. */
    static float originalEmission(float value) {
        int fluidAmount = (int) Math.ceil(value * 100);
        float tank = POLLUTION_TANK;
        float overflow = (tank + fluidAmount) - POLLUTION_TANK;
        return overflow / 100F;
    }

    static final MachineOilWellBlock DERRICK = new MachineOilWellBlock(new Block.Properties());
    static final HeaterOilburnerBlock BURNER = new HeaterOilburnerBlock(new Block.Properties());
    static final BlockState STONE = Blocks.STONE.defaultBlockState();
    static final BlockState AIR = Blocks.AIR.defaultBlockState();

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

    /** Runs one section; a failed assertion is printed with the section name and the next section still runs. */
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

    // ---- World helpers (the Goal 9B/10B/10C patterns) ---------------------------------------------------------------

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
        Block.DROPS.clear();
        Containers.DROPS.clear();
        OilSpot.calls = 0;
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        level.random.setSeed(11L);
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

    static CableBaseBlockEntity cable(Level level, BlockPos pos) {
        CableBaseBlockEntity wire = new CableBaseBlockEntity(pos, new BlockState());
        level.put(wire);
        wire.updateEntity();
        return wire;
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    static BarrelBlockEntity barrel(Level level, BlockPos pos, FluidType type) {
        BlockState state = new BlockState();
        state.block = NtmBlocks.BARREL_STEEL.get();
        level.states.put(pos, state);
        BarrelBlockEntity barrel = new BarrelBlockEntity(pos, state);
        level.put(barrel);
        barrel.tank.setTankType(type);
        barrel.tank.setFill(0);
        barrel.mode = 0;
        return barrel;
    }

    /** A battery socket with its conductor proxies and a charged lithium pack, set to output (the Goal 10B/10C rig). */
    static BatterySocketBlockEntity provider(Level level, BlockPos pos, Direction facing) {
        BlockState state = facing(level, pos, facing);
        BatterySocketBlockEntity socket = new BatterySocketBlockEntity(pos, state);
        level.put(socket);
        BlockPos[] ports = socket.getPortPos();
        for(int i = 1; i < ports.length; i++) {
            ProxyComboBlockEntity proxy = new ProxyComboBlockEntity(ports[i], state).inventory().power().conductor();
            proxy.core = socket;
            level.states.put(ports[i], state);
            level.put(proxy);
        }
        ItemStack pack = MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_LITHIUM.ordinal());
        PACK.setCharge(pack, 1_000_000L);
        socket.slots.set(0, pack);
        socket.redLow = BatteryBaseBlockEntity.mode_output;
        return socket;
    }

    static String rel(BlockPos p, BlockPos core) {
        return (p.getX() - core.getX()) + "," + (p.getY() - core.getY()) + "," + (p.getZ() - core.getZ());
    }

    static Set<String> conSet(DirPos[] cons, BlockPos core) {
        Set<String> out = new TreeSet<>();
        for(DirPos c : cons) out.add(c.getDir() + "@" + rel(c.makeCompat(), core));
        return out;
    }

    /** The derrick placed through the production block (core state, MachineOilWellBlock.fillSpace, block entities). */
    static MachineOilWellBlockEntity derrick(Level level, BlockPos core, Direction facing) {
        BlockPos at = Goal11ABlockAccess.place(DERRICK, level, core, facing);
        return (MachineOilWellBlockEntity) level.getBlockEntity(at);
    }

    /** The fluid burner placed through the production block (offset 1, HeaterOilburnerBlock.fillSpace with makeExtra). */
    static HeaterOilburnerBlockEntity burner(Level level, BlockPos core, Direction facing) {
        BlockPos at = Goal11ABlockAccess.place(BURNER, level, core, facing);
        return (HeaterOilburnerBlockEntity) level.getBlockEntity(at);
    }

    // ---- 1. Derrick connection points --------------------------------------------------------------------------------

    static void connections() {
        BlockPos core = new BlockPos(0, 64, 0);
        Set<String> expected = new TreeSet<>();
        for(Direction d : ORIGINAL_PORTS) expected.add(d + "@" + rel(core.relative(d), core));

        for(Direction facing : HORIZONTALS) {
            reset();
            Level level = level();
            MachineOilWellBlockEntity d = derrick(level, core, facing);
            DirPos[] cons = d.getConPos();
            check(cons.length == 5 && conSet(cons, core).equals(expected),
                    facing + ": exactly the five original connections, each facing away from the core (+X, -X, +Z, -Z, -Y): " + conSet(cons, core));
            Set<BlockPos> parts = new HashSet<>(Goal11ABlockAccess.parts(DERRICK, level));
            Set<String> coreLayer = new TreeSet<>();
            for(BlockPos p : parts) if(p.getY() == core.getY() && !p.equals(core)) coreLayer.add(rel(p, core));
            check(coreLayer.equals(new TreeSet<>(List.of("-1,0,-1", "-1,0,1", "1,0,-1", "1,0,1"))),
                    facing + ": the production fillSpace puts the four legs on the core layer's corners: " + coreLayer);
            boolean free = true;
            for(DirPos c : cons) free &= !parts.contains(c.makeCompat());
            check(free, facing + ": no connection point coincides with a block of the derrick (legs, tower, core)");
            check(level.getBlockEntity(core) == d && d.getBlockState().getValue(DummyableBlock.TYPE) == DummyBlockType.CORE,
                    facing + ": the core is the derrick block entity");
        }

        // Power through a real cable on each connection point (the tanks are full, so the derrick spends nothing and
        // keeps exactly what arrives).
        for(Direction side : ORIGINAL_PORTS) {
            reset();
            Level level = level();
            MachineOilWellBlockEntity d = derrick(level, core, Direction.NORTH);
            d.tanks[0].setFill(d.tanks[0].getMaxFill());
            Direction away = side == Direction.DOWN ? Direction.EAST : side;
            BlockPos c = core.relative(side);
            cable(level, c);
            for(int i = 0; i < 3; i++) {
                c = c.relative(away);
                cable(level, c);
            }
            BatterySocketBlockEntity socket = provider(level, c.relative(away), away.getOpposite());
            socket.updateEntity();
            net(level);
            long start = socket.getPower();
            for(int t = 1; t <= 40; t++) {
                level.time = t;
                socket.updateEntity();
                d.updateEntity();
                transfer(level);
            }
            check(d.power > 0 && d.power == start - socket.getPower(),
                    side + " connection: a cable there powers the derrick (" + d.power + " HE, exactly what the socket sent)");
        }

        // Oil and gas out through a real pipe on each side point into a barrel.
        for(Direction side : ORIGINAL_PORTS) {
            if(side == Direction.DOWN) continue;
            for(FluidType type : new FluidType[] {Fluids.OIL, Fluids.GAS}) {
                reset();
                Level level = level();
                MachineOilWellBlockEntity d = derrick(level, core, Direction.NORTH);
                d.tanks[0].setFill(8_000);
                d.tanks[1].setFill(8_000);
                BlockPos c = core.relative(side);
                pipe(level, c, type);
                for(int i = 0; i < 3; i++) {
                    c = c.relative(side);
                    pipe(level, c, type);
                }
                BarrelBlockEntity barrel = barrel(level, c.relative(side), type);
                barrel.updateEntity();
                net(level);
                for(int t = 1; t <= 40; t++) {
                    level.time = t;
                    d.updateEntity();
                    barrel.updateEntity();
                    transfer(level);
                }
                int sent = 8_000 - (type == Fluids.OIL ? d.tanks[0].getFill() : d.tanks[1].getFill());
                check(barrel.tank.getFill() > 0 && barrel.tank.getFill() == sent && barrel.tank.getTankType() == type,
                        side + " connection: " + (type == Fluids.OIL ? "oil" : "gas") + " leaves through a pipe there (" + sent + " mB into the barrel)");
            }
        }

        // The former points (1,0,1)/(1,0,-1): a bare core without legs, so a cable and a pipe can stand there; neither connects.
        reset();
        Level level = level();
        MachineOilWellBlockEntity bare = new MachineOilWellBlockEntity(core, DERRICK.createCoreState(Direction.NORTH));
        level.states.put(core, DERRICK.createCoreState(Direction.NORTH));
        level.put(bare);
        bare.tanks[0].setFill(8_000);
        bare.tanks[1].setFill(8_000);
        BlockPos corner = core.offset(1, 0, 1);
        cable(level, corner);
        cable(level, corner.relative(Direction.SOUTH));
        BatterySocketBlockEntity socket = provider(level, corner.relative(Direction.SOUTH, 2), Direction.NORTH);
        BlockPos other = core.offset(1, 0, -1);
        pipe(level, other, Fluids.OIL);
        pipe(level, other.relative(Direction.NORTH), Fluids.OIL);
        BarrelBlockEntity barrel = barrel(level, other.relative(Direction.NORTH, 2), Fluids.OIL);
        socket.updateEntity();
        net(level);
        for(int t = 1; t <= 40; t++) {
            level.time = t;
            socket.updateEntity();
            bare.updateEntity();
            barrel.updateEntity();
            transfer(level);
        }
        check(bare.power == 0 && barrel.tank.getFill() == 0 && bare.tanks[0].getFill() == 8_000,
                "a cable at (1,0,1) and a pipe at (1,0,-1), the former connection points, get nothing (power " + bare.power + ", oil " + barrel.tank.getFill() + ")");
        section("1. derrick connection points");
    }

    // ---- 3. Bubble placement -------------------------------------------------------------------------------------------

    /** The stone world of the placement checks: stone below Y 62, dirt at 63, grass at 64, air above. */
    static World stoneWorld() {
        BlockState dirt = Blocks.DIRT.defaultBlockState(), grass = Blocks.GRASS_BLOCK.defaultBlockState();
        return new World(p -> p.getY() < -64 ? AIR : p.getY() <= 62 ? STONE : p.getY() == 63 ? dirt : p.getY() == 64 ? grass : AIR);
    }

    /**
     * The bubble NEO must make at (0,0,0): the production loop bounds and, as the original's double comparison
     * rSqr < r * r / 2, the exact integer test 2 * (x^2 + 3y^2 + z^2) < r^2 (NEO kept an integer r^2 / 2 until the Goal 11A
     * review fix, which dropped the shell x^2 + z^2 + 3y^2 == (r^2 - 1) / 2 of every odd radius). Section 3 compares it with
     * originalShape and with the production spawnOil, so it is not trusted on its own.
     */
    static Set<BlockPos> neoShape(int r) {
        Set<BlockPos> out = new HashSet<>();
        for(int x = -r; x < r; x++) for(int y = -r; y < r; y++) for(int z = -r; z < r; z++)
            if(2 * (x * x + 3 * y * y + z * z) < r * r) out.add(new BlockPos(x, y, z));
        return out;
    }

    /** The original's bubble (MapGenBubble.java:62-80): rSqr < radius * radius / 2 as doubles, no fuzz. */
    static Set<BlockPos> originalShape(int r) {
        double radiusSqr = ((double) r * r) / 2;
        Set<BlockPos> out = new HashSet<>();
        for(int x = -r - 1; x <= r + 1; x++) for(int y = -r - 1; y <= r + 1; y++) for(int z = -r - 1; z <= r + 1; z++)
            if(x * x + z * z + y * y * 3 < radiusSqr) out.add(new BlockPos(x, y, z));
        return out;
    }

    static Set<BlockPos> oreRelative(World world, BlockPos origin) {
        Set<BlockPos> out = new HashSet<>();
        world.written.forEach((p, s) -> { if(s.is(NtmBlocks.ORE_OIL.get())) out.add(new BlockPos(p.getX() - origin.getX(), p.getY() - origin.getY(), p.getZ() - origin.getZ())); });
        return out;
    }

    /** The radius the production place() rolls for this seed: after the spawn roll nextInt(rate), 8 + nextInt(8) (replayed). */
    static int replayRadius(long seed, int rate) {
        CountingRandom replay = new CountingRandom(seed);
        if(replay.nextInt(rate) != 0) return -1;
        return BUBBLE_MIN_SIZE + replay.nextInt(BUBBLE_MAX_SIZE - BUBBLE_MIN_SIZE);
    }

    static void bubblePlacement() {
        check(Goal11AWorldGen.constant("BUBBLE_MIN_RADIUS") == BUBBLE_MIN_SIZE && Goal11AWorldGen.constant("BUBBLE_RADIUS_VARIATION") == BUBBLE_MAX_SIZE - BUBBLE_MIN_SIZE,
                "radius = 8 + nextInt(8), the original nextInt(maxSize - minSize) + minSize with setSize(8, 16)");

        // Many placements: each seed that passes the spawn roll places a bubble whose blocks are exactly the shape of the
        // replayed radius; together the radii are exactly 8..15.
        BlockPos origin = new BlockPos(8, -40, 8);
        Map<Integer, Integer> radii = new TreeMap<>();
        boolean shapes = true, consumed = true;
        String firstBad = null;
        for(long seed = 0; radii.values().stream().mapToInt(Integer::intValue).sum() < 400 && seed < 200_000; seed++) {
            int r = replayRadius(seed, 100);
            if(r < 0) continue;
            World world = stoneWorld();
            Region region = new Region(world, 0, 0);
            CountingRandom random = new CountingRandom(seed);
            boolean placed = Goal11AWorldGen.place(region, random, origin);
            Set<BlockPos> ore = oreRelative(world, origin);
            boolean ok = placed && ore.equals(originalShape(r));
            consumed &= random.bounds.size() >= 2 && random.bounds.get(0) == 100 && random.bounds.get(1) == 8;
            if(!ok && firstBad == null) firstBad = "seed " + seed + " radius " + r + ": placed " + placed + ", " + ore.size() + " ore vs " + originalShape(r).size();
            shapes &= ok;
            radii.merge(r, 1, Integer::sum);
        }
        info("radii of 400 placed bubbles: " + radii);
        check(radii.keySet().equals(new TreeSet<>(List.of(8, 9, 10, 11, 12, 13, 14, 15))),
                "the radius takes exactly the values 8..15 over 400 placements: " + radii.keySet());
        check(shapes, "every placed bubble is exactly the original's oblate shape of its radius in all-stone ground" + (firstBad == null ? "" : "; " + firstBad));
        check(consumed, "every placement rolls nextInt(100) (spawn, base rate) and then nextInt(8) (radius) first");

        // The shape against the original's (MapGenBubble.java:62-63, :79: rSqr < radius * radius / 2 in doubles): the production
        // spawnOil makes block for block the original's bubble at every radius 8..15. Odd radii include the shell
        // x^2 + z^2 + 3y^2 == (r^2 - 1) / 2, which an integer r^2 / 2 drops (the defect the Goal 11A review fixed).
        StringBuilder shells = new StringBuilder();
        boolean sameCount = true, sameBlocks = true, shellsIn = true;
        String shapeBad = null;
        Map<Integer, Integer> shellSizes = new TreeMap<>();
        for(int r = 8; r <= 15; r++) {
            World world = stoneWorld();
            Goal11AWorldGen.spawnOil(new Region(world, 0, 0), origin.getX(), origin.getY(), origin.getZ(), r);
            Set<BlockPos> neo = oreRelative(world, origin), original = originalShape(r);
            int shell = (r * r - 1) / 2;
            Set<BlockPos> onShell = new HashSet<>();
            if(r % 2 == 1) for(BlockPos p : original) if(p.getX() * p.getX() + p.getZ() * p.getZ() + 3 * p.getY() * p.getY() == shell) onShell.add(p);
            shellSizes.put(r, onShell.size());
            sameCount &= neo.size() == original.size();
            sameBlocks &= neo.equals(original) && neoShape(r).equals(original);
            shellsIn &= neo.containsAll(onShell);
            if((neo.size() != original.size() || !neo.containsAll(onShell)) && shapeBad == null)
                shapeBad = "radius " + r + ": " + neo.size() + " blocks vs " + original.size() + " (shell " + onShell.size() + ", of it " + onShell.stream().filter(neo::contains).count() + " present)";
            shells.append(r).append(": ").append(neo.size()).append("/").append(original.size()).append("; ");
        }
        info("bubble blocks NEO/original per radius: " + shells);
        info("odd-radius shell x^2 + z^2 + 3y^2 == (r^2 - 1)/2, blocks per radius (all present in NEO): " + shellSizes);
        check(sameCount, "the production spawnOil makes as many oil rock blocks as the original formula at every radius 8..15" + (shapeBad == null ? "" : "; " + shapeBad));
        check(sameBlocks, "and exactly the original's blocks (x^2 + z^2 + 3y^2 < r^2/2 as doubles) at every radius 8..15, odd radii included");
        check(shellsIn && shellSizes.get(9) > 0 && shellSizes.get(13) > 0 && shellSizes.get(15) > 0 && shellSizes.get(11) == 0,
                "the shell x^2 + z^2 + 3y^2 == (r^2 - 1)/2 of the odd radii is included (non-empty at 9, 13 and 15, none at 11): " + shellSizes
                        + (shapeBad == null ? "" : "; " + shapeBad));

        // Replacement: every member of #minecraft:base_stone_overworld becomes oil rock; ores, dirt, gravel, air, water
        // and structure blocks stay.
        Set<String> tagged = new TreeSet<>();
        for(Field f : Blocks.class.getFields()) {
            try {
                if(f.get(null) instanceof Block b && b.defaultBlockState().is(BlockTags.BASE_STONE_OVERWORLD)) tagged.add(b.id);
            } catch(IllegalAccessException e) {
                throw new AssertionError(e);
            }
        }
        check(tagged.equals(new TreeSet<>(BlockTags.BASE_STONE_OVERWORLD_MEMBERS)) && tagged.size() == 6,
                "the stand-in tag holds exactly Minecraft 1.21.1's base_stone_overworld members: " + tagged);
        Block[] members = {Blocks.STONE, Blocks.GRANITE, Blocks.DIORITE, Blocks.ANDESITE, Blocks.TUFF, Blocks.DEEPSLATE};
        Block[] kept = {Blocks.IRON_ORE, Blocks.DEEPSLATE_IRON_ORE, Blocks.COAL_ORE, Blocks.DIRT, Blocks.GRAVEL, Blocks.AIR, Blocks.WATER,
                Blocks.TUFF_BRICKS, Blocks.POLISHED_TUFF, Blocks.CHISELED_TUFF, Blocks.REINFORCED_DEEPSLATE, Blocks.COBBLESTONE,
                Blocks.COPPER_GRATE, Blocks.TUFF_BRICK_SLAB, Blocks.WAXED_COPPER_BLOCK, Blocks.OXIDIZED_CUT_COPPER,
                NtmBlocks.ORE_OIL_EMPTY.get(), NtmBlocks.ORE_BEDROCK_OIL.get()};
        Map<BlockPos, Block> layout = new HashMap<>();
        int i = 0;
        // A 6 x 4 grid around the centre, well inside the radius-15 shape (x^2 + z^2 < 112 at y = 0).
        for(Block b : members) { layout.put(new BlockPos(8 + i % 6 - 3, -40, 8 + i / 6 - 2), b); i++; }
        for(Block b : kept) { layout.put(new BlockPos(8 + i % 6 - 3, -40, 8 + i / 6 - 2), b); i++; }
        World mixed = new World(p -> layout.containsKey(p) ? layout.get(p).defaultBlockState() : STONE);
        Goal11AWorldGen.spawnOil(new Region(mixed, 0, 0), 8, -40, 8, 15);
        boolean converted = true, untouched = true;
        StringBuilder wrong = new StringBuilder();
        for(Map.Entry<BlockPos, Block> e : layout.entrySet()) {
            BlockState now = mixed.get(e.getKey());
            boolean member = Arrays.asList(members).contains(e.getValue());
            if(member && !now.is(NtmBlocks.ORE_OIL.get())) { converted = false; wrong.append(e.getValue()).append(" stayed; "); }
            if(!member && (mixed.written.containsKey(e.getKey()) || !now.is(e.getValue()))) { untouched = false; wrong.append(e.getValue()).append(" replaced; "); }
        }
        check(converted, "stone, granite, diorite, andesite, tuff and deepslate inside the bubble become oil rock " + wrong);
        check(untouched, "ores, dirt, gravel, air, water, tuff bricks/polished/chiseled tuff, reinforced deepslate, cobblestone, copper blocks, "
                + "empty and bedrock oil stay " + wrong);
        int expectedOre = originalShape(15).size() - kept.length;
        check(oreRelative(mixed, new BlockPos(8, -40, 8)).size() == expectedOre, "every other block of the radius-15 shape (all stone) became oil rock (" + expectedOre + ")");
        section("3. bubble placement");
    }

    // ---- 4. Avoidance ----------------------------------------------------------------------------------------------------

    static final Structure TRIAL_CHAMBERS = new Structure("minecraft:trial_chambers");
    static final Structure MINESHAFT = new Structure("minecraft:mineshaft");
    static final Structure STRONGHOLD = new Structure("minecraft:stronghold");
    static final Structure ANCIENT_CITY = new Structure("minecraft:ancient_city");

    /** A seed whose first roll passes the spawn roll (base rate 100) and whose radius roll gives r. */
    static long seedFor(int r) {
        for(long seed = 0; seed < 1_000_000; seed++) if(replayRadius(seed, 100) == r) return seed;
        throw new AssertionError("no seed for radius " + r);
    }

    static int floorDiv16(int v) {
        return Math.floorDiv(v, 16);
    }

    record Outcome(boolean placed, int radius, Set<BlockPos> ore, Map<BlockPos, BlockState> written) {}

    static void avoidance(List<String> avoidTag) {
        // Read range: for every origin in the chunk and every radius, the check reads the references of exactly the
        // chunks under origin +-radius (the loop bounds x - r .. x + r - 1) and nothing outside the 3x3.
        boolean reads = true, within = true, noBlocks = true;
        String firstBad = null;
        for(int lx = 0; lx < 16; lx++) for(int lz = 0; lz < 16; lz++) for(int r = 8; r <= 15; r++) {
            World world = stoneWorld();
            world.avoid.addAll(avoidTag);
            Region region = new Region(world, 0, 0);
            boolean hit = Goal11AWorldGen.touches(region, new BlockPos(lx, -40, lz), r);
            Set<String> expected = new TreeSet<>();
            for(int cx = floorDiv16(lx - r); cx <= floorDiv16(lx + r - 1); cx++)
                for(int cz = floorDiv16(lz - r); cz <= floorDiv16(lz + r - 1); cz++) expected.add(cx + "," + cz);
            boolean ok = !hit && new TreeSet<>(region.referenceReads).equals(expected) && new TreeSet<>(region.chunkReads).equals(expected);
            if(!ok && firstBad == null) firstBad = "origin " + lx + "," + lz + " r " + r + ": read " + region.chunkReads + ", expected " + expected;
            reads &= ok;
            for(String c : region.chunkReads) {
                String[] xz = c.split(",");
                within &= Math.abs(Integer.parseInt(xz[0])) <= 1 && Math.abs(Integer.parseInt(xz[1])) <= 1;
            }
            noBlocks &= region.farReads == 0 && region.writes.isEmpty();
        }
        check(reads, "for all 256 origins and radii 8..15 the check reads the references of exactly the chunks under origin +-radius"
                + (firstBad == null ? "" : "; " + firstBad));
        check(within && noBlocks, "every read stays in the 3x3 around the generating chunk (distance <= 1: the chunks that carry references), no block read or written");

        // Skips: a trial chambers reference in the origin chunk or in any neighbour under the extent.
        long seed12 = seedFor(12);
        int[][] origins = {{8, 8}, {2, 2}, {8, 2}, {13, 2}, {2, 8}, {13, 8}, {2, 13}, {8, 13}, {13, 13}};
        int[][] chunks = {{0, 0}, {-1, -1}, {0, -1}, {1, -1}, {-1, 0}, {1, 0}, {-1, 1}, {0, 1}, {1, 1}};
        boolean skipped = true, clean = true, rolls = true;
        String bad = null;
        for(int k = 0; k < chunks.length; k++) {
            World world = stoneWorld();
            world.avoid.addAll(avoidTag);
            world.reference(chunks[k][0], chunks[k][1], TRIAL_CHAMBERS, false);
            Region region = new Region(world, 0, 0);
            CountingRandom random = new CountingRandom(seed12);
            boolean placed = Goal11AWorldGen.place(region, random, new BlockPos(origins[k][0], -40, origins[k][1]));
            skipped &= !placed;
            clean &= world.written.isEmpty() && region.writes.isEmpty() && region.refusedWrites == 0 && region.farReads == 0;
            rolls &= random.bounds.equals(List.of(100, 8)) && random.others == 0;
            if((placed || !world.written.isEmpty()) && bad == null) bad = "reference in chunk " + Arrays.toString(chunks[k]) + ": placed " + placed + ", " + world.written.size() + " blocks";
        }
        check(skipped, "a trial chambers reference in the origin chunk or in any of the 8 neighbours under the extent: place returns false" + (bad == null ? "" : "; " + bad));
        check(clean, "a skipped bubble writes no block (no oil rock, no surface spot) and reads no block");
        check(rolls, "before a skip the random is used exactly for the spawn roll nextInt(100) and the radius roll nextInt(8), nothing else");

        // Not skipped: a reference outside the extent, other structures, an empty start set, an empty tag.
        long seed8 = seedFor(8);
        World outside = stoneWorld();
        outside.avoid.addAll(avoidTag);
        outside.reference(1, 0, TRIAL_CHAMBERS, false);
        outside.reference(-1, 1, TRIAL_CHAMBERS, false);
        Region outsideRegion = new Region(outside, 0, 0);
        boolean outsidePlaced = Goal11AWorldGen.place(outsideRegion, new CountingRandom(seed8), new BlockPos(8, -40, 8));
        check(outsidePlaced && oreRelative(outside, new BlockPos(8, -40, 8)).equals(originalShape(8)) && outsideRegion.referenceReads.equals(Set.of("0,0")),
                "radius 8 at the chunk centre (extent x/z 0..15): only the origin chunk is checked, a trial chambers reference next door does not skip it");
        World others = stoneWorld();
        others.avoid.addAll(avoidTag);
        for(int cx = -1; cx <= 1; cx++) for(int cz = -1; cz <= 1; cz++) {
            others.reference(cx, cz, MINESHAFT, false);
            others.reference(cx, cz, STRONGHOLD, false);
            others.reference(cx, cz, ANCIENT_CITY, false);
        }
        boolean othersPlaced = Goal11AWorldGen.place(new Region(others, 0, 0), new CountingRandom(seed12), new BlockPos(8, -40, 8));
        check(othersPlaced && oreRelative(others, new BlockPos(8, -40, 8)).equals(originalShape(12)), "only mineshaft, stronghold and ancient city references in all nine chunks: the bubble is generated");
        World emptyStart = stoneWorld();
        emptyStart.avoid.addAll(avoidTag);
        emptyStart.reference(0, 0, TRIAL_CHAMBERS, true);
        check(Goal11AWorldGen.place(new Region(emptyStart, 0, 0), new CountingRandom(seed12), new BlockPos(8, -40, 8)),
                "a trial chambers entry with an empty start set is not a reference: the bubble is generated");
        World emptyTag = stoneWorld();
        emptyTag.reference(0, 0, TRIAL_CHAMBERS, false);
        check(Goal11AWorldGen.place(new Region(emptyTag, 0, 0), new CountingRandom(seed12), new BlockPos(8, -40, 8)),
                "with a tag that has no members, a trial chambers reference does not skip the bubble");
        World pack = stoneWorld();
        pack.avoid.addAll(avoidTag);
        pack.avoid.add(MINESHAFT.id); // a data pack appending minecraft:mineshaft with replace: false
        pack.reference(1, 1, MINESHAFT, false);
        check(!Goal11AWorldGen.place(new Region(pack, 0, 0), new CountingRandom(seed12), new BlockPos(13, -40, 13)) && pack.written.isEmpty(),
                "a data pack that appends a structure to the tag makes bubbles over it skip as well");

        // No state between calls: every field of the feature is a static final constant.
        boolean constantsOnly = true;
        for(Field f : com.hbm.world.feature.OilBubbleFeature.class.getDeclaredFields())
            constantsOnly &= Modifier.isStatic(f.getModifiers()) && Modifier.isFinal(f.getModifiers());
        check(constantsOnly, "OilBubbleFeature keeps no state: all its fields are static final constants");

        // Generation order: the same chunks in two orders give the same decisions, radii and oil rock; spaced chunks give
        // identical worlds; all writes stay in the 3x3 and nothing is refused.
        List<int[]> adjacent = new ArrayList<>();
        for(int cx = 0; cx < 4; cx++) for(int cz = 0; cz < 4; cz++) adjacent.add(new int[] {cx, cz});
        List<int[]> spaced = new ArrayList<>();
        for(int cx = 0; cx < 9; cx += 3) for(int cz = 0; cz < 9; cz += 3) spaced.add(new int[] {cx, cz});
        Function<List<int[]>, Map<String, Object>> generate = order -> {
            World world = stoneWorld();
            world.avoid.addAll(avoidTag);
            world.reference(1, 1, TRIAL_CHAMBERS, false);
            world.reference(6, 3, TRIAL_CHAMBERS, false);
            Map<String, Object> result = new TreeMap<>();
            int far = 0, refused = 0;
            boolean inside = true;
            for(int[] c : order) {
                // A fixed seed per chunk that passes the spawn roll (base rate 100) and rolls a radius 8..15 from the chunk
                // coordinates; the origin is the chunk centre at a height inside the placed feature's Y range.
                long seed = seedFor(8 + Math.floorMod(c[0] * 3 + c[1] * 5, 8));
                CountingRandom random = new CountingRandom(seed);
                BlockPos o = new BlockPos(c[0] * 16 + 8, -64 + BUBBLE_MIN_Y + Math.floorMod(c[0] * 7 + c[1] * 11, BUBBLE_RANGE_Y), c[1] * 16 + 8);
                Region region = new Region(world, c[0], c[1]);
                boolean placed = Goal11AWorldGen.place(region, random, o);
                result.put(c[0] + "," + c[1], placed + "/r" + replayRadius(seed, 100));
                far += region.farReads;
                refused += region.refusedWrites;
                for(BlockPos w : region.writes) inside &= Math.abs((w.getX() >> 4) - c[0]) <= 1 && Math.abs((w.getZ() >> 4) - c[1]) <= 1;
            }
            Set<BlockPos> ore = new HashSet<>();
            world.written.forEach((p, s) -> { if(s.is(NtmBlocks.ORE_OIL.get())) ore.add(p); });
            result.put("~ore", ore);
            // States compare by block (the stand-in BlockState has identity equality).
            Map<BlockPos, String> blocks = new HashMap<>();
            world.written.forEach((p, s) -> blocks.put(p, s.getBlock().id));
            result.put("~world", blocks);
            result.put("~far", far);
            result.put("~refused", refused);
            result.put("~inside", inside);
            return result;
        };
        List<int[]> reversed = new ArrayList<>(adjacent);
        java.util.Collections.reverse(reversed);
        List<int[]> shuffled = new ArrayList<>(adjacent);
        java.util.Collections.shuffle(shuffled, new java.util.Random(3));
        Map<String, Object> a = generate.apply(adjacent), b = generate.apply(reversed), c = generate.apply(shuffled);
        Map<String, Object> decisions = new TreeMap<>(a);
        decisions.keySet().removeIf(k -> k.startsWith("~"));
        info("adjacent 4x4 chunks (trial chambers referenced from chunk 1,1): " + decisions);
        boolean sameDecisions = true;
        for(String k : decisions.keySet()) sameDecisions &= a.get(k).equals(b.get(k)) && a.get(k).equals(c.get(k));
        check(sameDecisions && a.get("~ore").equals(b.get("~ore")) && a.get("~ore").equals(c.get("~ore")),
                "adjacent chunks in three generation orders: the same skip/place decisions and radii, the same oil rock");
        // From the chunk centre a radius r covers chunk offsets floorDiv(8 - r, 16) .. floorDiv(8 + r - 1, 16): only the own
        // chunk for r = 8, the 3x3 for 9..15. A chunk skips exactly when that range holds the referencing chunk 1,1.
        Map<String, Boolean> expectedSkip = new TreeMap<>();
        for(int[] ch : adjacent) {
            int r = BUBBLE_MIN_SIZE + Math.floorMod(ch[0] * 3 + ch[1] * 5, 8);
            int dx = 1 - ch[0], dz = 1 - ch[1];
            expectedSkip.put(ch[0] + "," + ch[1], dx >= floorDiv16(8 - r) && dx <= floorDiv16(8 + r - 1) && dz >= floorDiv16(8 - r) && dz <= floorDiv16(8 + r - 1));
        }
        boolean skips = true;
        for(String k : expectedSkip.keySet()) skips &= ((String) decisions.get(k)).startsWith(expectedSkip.get(k) ? "false" : "true");
        check(skips && expectedSkip.containsValue(true) && expectedSkip.containsValue(false),
                "exactly the chunks whose bubble extent reaches the referencing chunk 1,1 skip (radius 8 at the centre stays in its own chunk): " + expectedSkip);
        info("adjacent chunks, full block maps identical across orders: " + (a.get("~world").equals(b.get("~world")) && a.get("~world").equals(c.get("~world")))
                + " (surface spots of neighbouring bubbles may overlap; pre-existing addSurfaceSpot behaviour)");
        List<int[]> spacedReversed = new ArrayList<>(spaced);
        java.util.Collections.reverse(spacedReversed);
        Map<String, Object> s1 = generate.apply(spaced), s2 = generate.apply(spacedReversed);
        check(s1.get("~world").equals(s2.get("~world")), "chunks three apart in two orders: identical worlds, block for block");
        check((Boolean) a.get("~inside") && (Boolean) s1.get("~inside") && (Integer) a.get("~refused") == 0 && (Integer) s1.get("~refused") == 0,
                "every write stays within the 3x3 around its generating chunk; no write is refused");
        info("surface-spot column reads beyond the 3x3 (read as STRUCTURE_STARTS chunks, nothing written): adjacent " + a.get("~far") + ", spaced " + s1.get("~far"));
        section("4. avoidance");
    }

    // ---- 5. Drill depth -----------------------------------------------------------------------------------------------

    /** One drill action: the clock set to the next multiple of the delay, power full, tanks empty. Returns the oil/gas made. */
    static int[] step(MachineOilWellBlockEntity d) {
        Level level = d.getLevel();
        // Before its first update the derrick has no upgrade levels yet (overLevel 0); without upgrades the delay is getDelay().
        long delay = d.overLevel == 0 ? d.getDelay() : d.getDelayEff();
        level.time = (level.time / delay + 1) * delay;
        d.power = d.getMaxPower();
        d.tanks[0].setFill(0);
        d.tanks[1].setFill(0);
        d.updateEntity();
        return new int[] {d.tanks[0].getFill(), d.tanks[1].getFill()};
    }

    static boolean isPipe(Level level, BlockPos pos) {
        return level.getBlockState(pos).is(NtmBlocks.OIL_PIPE.get());
    }

    static int shaftBottom(Level level, BlockPos core) {
        int y = core.getY() - 1;
        while(isPipe(level, new BlockPos(core.getX(), y, core.getZ()))) y--;
        return y + 1;
    }

    static void fillStone(Level level, int x0, int x1, int y0, int y1, int z0, int z1) {
        for(int x = x0; x <= x1; x++) for(int y = y0; y <= y1; y++) for(int z = z0; z <= z1; z++) level.states.put(new BlockPos(x, y, z), STONE);
    }

    static void drillDepth() {
        reset();
        Level deep = level();
        MachineOilWellBlockEntity probe = derrick(deep, new BlockPos(0, 0, 0), Direction.NORTH);
        check(deep.getMinBuildHeight() == -64 && probe.getDrillDepth() == -64 + ORIGINAL_DRILL_DEPTH,
                "derrick depth = world bottom + 5 (original Y 5 above the bedrock floor): -59 in a -64 world");
        Level flat = level();
        flat.minBuildHeight = 0;
        MachineOilWellBlockEntity probe0 = derrick(flat, new BlockPos(0, 64, 0), Direction.NORTH);
        check(probe0.getDrillDepth() == ORIGINAL_DRILL_DEPTH, "in a world starting at Y 0 the derrick depth is the original Y 5");
        MachineFrackingTowerBlockEntity tower = new MachineFrackingTowerBlockEntity(new BlockPos(0, 64, 0), new BlockState());
        deep.put(tower);
        MachineFrackingTowerBlockEntity tower0 = new MachineFrackingTowerBlockEntity(new BlockPos(0, 64, 0), new BlockState());
        flat.put(tower0);
        check(tower.getDrillDepth() == -64 + ORIGINAL_FRACKING_DEPTH && tower0.getDrillDepth() == ORIGINAL_FRACKING_DEPTH,
                "fracking tower depth = world bottom (original 0): -64 and 0");

        // A real run in a world starting at Y 0: the shaft goes from below the core to Y 5 and then reports "done".
        for(int min : new int[] {0, -64}) {
            reset();
            Level level = level();
            level.minBuildHeight = min;
            BlockPos core = new BlockPos(0, min + 12, 0);
            fillStone(level, 0, 0, min, core.getY() - 1, 0, 0);
            MachineOilWellBlockEntity d = derrick(level, core, Direction.NORTH);
            List<Integer> indicators = new ArrayList<>();
            for(int i = 0; i < 12; i++) {
                step(d);
                indicators.add(d.indicator);
            }
            boolean shaft = true;
            for(int y = core.getY() - 1; y >= min + ORIGINAL_DRILL_DEPTH; y--) shaft &= isPipe(level, new BlockPos(0, y, 0));
            boolean below = true;
            for(int y = min; y < min + ORIGINAL_DRILL_DEPTH; y++) below &= level.getBlockState(new BlockPos(0, y, 0)).is(Blocks.STONE);
            check(shaft && below && indicators.subList(0, 7).stream().allMatch(v -> v == 0) && indicators.subList(7, 12).stream().allMatch(v -> v == 1),
                    "world bottom " + min + ": the shaft reaches Y " + (min + ORIGINAL_DRILL_DEPTH) + " in 7 steps (indicator 0), then the indicator is 1 and "
                            + "nothing below is touched " + indicators);
        }

        // Indicator 2: no power; a block with explosion resistance >= 1000 (bedrock) stops the shaft.
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 0, 0);
        fillStone(level, 0, 0, -10, -1, 0, 0);
        level.states.put(new BlockPos(0, -3, 0), Blocks.BEDROCK.defaultBlockState());
        MachineOilWellBlockEntity d = derrick(level, core, Direction.NORTH);
        level.time = 50;
        d.updateEntity();
        check(d.indicator == 2 && !isPipe(level, core.below()), "without power the indicator is 2 and nothing is drilled");
        for(int i = 0; i < 4; i++) step(d);
        check(d.indicator == 2 && level.getBlockState(new BlockPos(0, -3, 0)).is(Blocks.BEDROCK) && isPipe(level, new BlockPos(0, -2, 0)),
                "bedrock (resistance >= 1000) stops the shaft with indicator 2");

        // An old-style bubble (generated before Goal 11A at absolute Y 0..24 in stone) is passed through and sucked out.
        reset();
        level = level();
        core = new BlockPos(0, 40, 0);
        fillStone(level, -12, 12, -63, 39, -12, 12);
        Goal11AWorldGen.spawnOil(new Goal11AWorldGen.LevelView(level), 0, 12, 0, 10);
        int ore = countOre(level, -12, 12, -63, 39);
        d = derrick(level, core, Direction.NORTH);
        long oil = 0, sucks = 0;
        int steps = 0;
        while(d.indicator != 1 && steps < 200_000) {
            int[] made = step(d);
            oil += made[0];
            if(made[0] > 0) sucks++;
            steps++;
        }
        boolean through = true;
        for(int y = 39; y >= -59; y--) through &= isPipe(level, new BlockPos(0, y, 0));
        info("old-style bubble (radius 10 at Y 12): " + ore + " oil rock, " + sucks + " sucks, " + oil + " mB oil, " + steps + " drill actions, "
                + countOre(level, -12, 12, -63, 39) + " oil rock left");
        check(sucks > 0 && oil == sucks * OIL_PER_SUCK && through && d.indicator == 1 && level.getBlockState(new BlockPos(0, -60, 0)).is(Blocks.STONE),
                "a derrick over an old Y 0..24 bubble sucks it (500 mB per suck) and the shaft then continues to Y -59 (indicator 1)");

        // The depth-first search: 64 steps through empty oil rock reach oil, 65 do not (original suckRec layer > 64).
        for(int length : new int[] {ORIGINAL_DFS_LIMIT, ORIGINAL_DFS_LIMIT + 1}) {
            reset();
            level = level();
            core = new BlockPos(0, 0, 0);
            d = derrick(level, core, Direction.NORTH);
            for(int x = 0; x < length; x++) level.states.put(new BlockPos(x, -1, 0), NtmBlocks.ORE_OIL_EMPTY.get().defaultBlockState());
            level.states.put(new BlockPos(length, -1, 0), NtmBlocks.ORE_OIL.get().defaultBlockState());
            d.tanks[0].setFill(0);
            boolean found = d.trySuck(-1);
            check(found == (length <= ORIGINAL_DFS_LIMIT) && d.tanks[0].getFill() == (found ? OIL_PER_SUCK : 0),
                    "oil " + length + " steps away along empty oil rock: " + (found ? "reached" : "not reached") + " (search depth limit 64)");
        }
        section("5. drill depth");
    }

    static int countOre(Level level, int r, int r1, int y0, int y1) {
        int n = 0;
        for(Map.Entry<BlockPos, BlockState> e : level.states.entrySet()) {
            BlockPos p = e.getKey();
            if(p.getY() >= y0 && p.getY() <= y1 && p.getX() >= r && p.getX() <= r1 && e.getValue().is(NtmBlocks.ORE_OIL.get())) n++;
        }
        return n;
    }

    // ---- 7. Fluid burner ----------------------------------------------------------------------------------------------

    static String describe(Object recipe) {
        try {
            Class<?> c = recipe.getClass();
            StringBuilder b = new StringBuilder();
            for(Object in : (List<?>) c.getField("input").get(recipe)) {
                if(in instanceof ComparableStack cs) b.append("item ").append(cs.item.id).append(" x").append(cs.stacksize).append(" meta ").append(cs.meta);
                else if(in instanceof TagStack ts) b.append("tag ").append(ts.tag).append(" x").append(ts.stacksize);
                else b.append(in.getClass().getName());
                b.append("; ");
            }
            b.append("-> ");
            for(Object out : (List<?>) c.getField("output").get(recipe)) {
                b.append(out.getClass().getField("stack").get(out)).append(" @").append(out.getClass().getField("chance").get(out)).append("; ");
            }
            return b.append("tier ").append(c.getField("tierLower").get(recipe)).append('-').append(c.getField("tierUpper").get(recipe))
                    .append(' ').append(c.getMethod("getOverlay").invoke(recipe)).toString();
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("cannot describe " + recipe, e);
        }
    }

    static boolean accepts(AnvilConstructionRecipe recipe, ItemStack... offered) {
        for(AStack input : recipe.input) {
            boolean found = false;
            for(ItemStack stack : offered) found |= input.matchesRecipe(stack, false);
            if(!found) return false;
        }
        return true;
    }

    static final String[] GOAL11A = {
            "item hbmsntm:tank_steel x4 meta " + MetaHelper.WILDCARD_VALUE + "; item hbmsntm:pipe_steel x3 meta " + MetaHelper.WILDCARD_VALUE
                    + "; item hbmsntm:ingot_titanium x12 meta " + MetaHelper.WILDCARD_VALUE + "; item minecraft:copper_ingot x8 meta " + MetaHelper.WILDCARD_VALUE
                    + "; -> 1 hbmsntm:heater_oilburner @1.0; tier 2--1 CONSTRUCTION",
            "item hbmsntm:tank_steel x4 meta " + MetaHelper.WILDCARD_VALUE + "; item hbmsntm:pipe_steel x3 meta " + MetaHelper.WILDCARD_VALUE
                    + "; item hbmsntm:ingot_titanium x12 meta " + MetaHelper.WILDCARD_VALUE + "; item hbmsntm:ingot_copper x8 meta " + MetaHelper.WILDCARD_VALUE
                    + "; -> 1 hbmsntm:heater_oilburner @1.0; tier 2--1 CONSTRUCTION",
    };

    /**
     * Goal 12A (migration/GOAL12A.md) appends four entries after the fluid burner entries: the industrial boiler with
     * Minecraft and with NEO copper (original AnvilRecipes.java:399-404), the electric pump (:253-260) and the desh motor
     * (:215-217). They are required exactly, in this order, at the end of the list; the Goal 12A suite checks them in detail.
     */
    static final String[] GOAL12A = {
            "item hbmsntm:cast_plate x8 meta 11; item minecraft:copper_ingot x8 meta " + MetaHelper.WILDCARD_VALUE
                    + "; tag ntm:ingots_plastic x4; -> 1 hbmsntm:machine_industrial_boiler @1.0; tier 3--1 CONSTRUCTION",
            "item hbmsntm:cast_plate x8 meta 11; item hbmsntm:ingot_copper x8 meta " + MetaHelper.WILDCARD_VALUE
                    + "; tag ntm:ingots_plastic x4; -> 1 hbmsntm:machine_industrial_boiler @1.0; tier 3--1 CONSTRUCTION",
            "item stone_bricks x8 meta " + MetaHelper.WILDCARD_VALUE + "; tag plates/steel x16; item hbmsntm:pipe_lead x4 meta " + MetaHelper.WILDCARD_VALUE
                    + "; item hbmsntm:motor x2 meta " + MetaHelper.WILDCARD_VALUE + "; item hbmsntm:circuit_vacuum_tube x4 meta " + MetaHelper.WILDCARD_VALUE
                    + "; -> 1 hbmsntm:pump_electric @1.0; tier 3--1 CONSTRUCTION",
            "item hbmsntm:motor x1 meta " + MetaHelper.WILDCARD_VALUE + "; tag ntm:ingots_plastic x2; item hbmsntm:ingot_desh x2 meta " + MetaHelper.WILDCARD_VALUE
                    + "; item hbmsntm:wire_dense x1 meta 7900; -> 1 hbmsntm:motor_desh @1.0; tier 3--1 CONSTRUCTION",
    };

    static void burnerAnvil() {
        List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
        List<?> before = goal11a.head.AnvilRecipes.getConstruction();
        int n = before.size();
        check(all.size() == n + 2 + GOAL12A.length, "the live construction list is the 8a209c35 list plus exactly two entries, then the four Goal 12A entries ("
                + n + " -> " + all.size() + ")");
        List<String> tail = new ArrayList<>();
        for(int k = 0; k < GOAL12A.length; k++) tail.add(describe(all.get(n + 2 + k)));
        check(tail.equals(List.of(GOAL12A)), "exactly the four Goal 12A entries (industrial boiler x2, electric pump, desh motor) follow the two fluid burner entries,"
                + " in order, at the end of the list: " + tail);
        int same = 0;
        String first = null;
        for(int i = 0; i < n; i++) {
            if(describe(all.get(i)).equals(describe(before.get(i)))) same++;
            else if(first == null) first = i + ": " + describe(all.get(i)) + " != " + describe(before.get(i));
        }
        check(same == n, "every committed entry is unchanged in content and index" + (first == null ? "" : "; first difference " + first));
        check(describe(all.get(n)).equals(GOAL11A[0]) && describe(all.get(n + 1)).equals(GOAL11A[1]),
                "the two new entries after the committed list (original AnvilRecipes.java:283-289): 4 steel tanks, 3 steel pipes, 12 titanium ingots, 8 Minecraft / NEO copper ingots "
                        + "-> one plain fluid burner, tier 2 and up, construction overlay: " + describe(all.get(n)) + " | " + describe(all.get(n + 1)));
        AnvilConstructionRecipe vanilla = all.get(n), neo = all.get(n + 1);
        check(vanilla.isTierValid(2) && vanilla.isTierValid(3) && !vanilla.isTierValid(1) && vanilla.getOverlay() == OverlayType.CONSTRUCTION
                        && neo.isTierValid(2) && !neo.isTierValid(1) && neo.getOverlay() == OverlayType.CONSTRUCTION,
                "both: anvil tier 2 and up, construction overlay");
        ItemStack tanks = new ItemStack(NtmItems.TANK_STEEL.get(), 4), pipes = new ItemStack(NtmItems.PIPE_STEEL.get(), 3), ti = new ItemStack(NtmItems.INGOT_TITANIUM.get(), 12);
        ItemStack mcCopper = new ItemStack(Items.COPPER_INGOT, 8), ntmCopper = new ItemStack(NtmItems.INGOT_COPPER.get(), 8);
        check(accepts(vanilla, tanks, pipes, ti, mcCopper) && !accepts(vanilla, tanks, pipes, ti, ntmCopper)
                        && accepts(neo, tanks, pipes, ti, ntmCopper) && !accepts(neo, tanks, pipes, ti, mcCopper),
                "each entry accepts only its own copper ingots");
        check(!accepts(vanilla, new ItemStack(NtmItems.TANK_STEEL.get(), 3), pipes, ti, mcCopper) && !accepts(vanilla, tanks, new ItemStack(NtmItems.PIPE_STEEL.get(), 2), ti, mcCopper)
                        && !accepts(vanilla, tanks, pipes, new ItemStack(NtmItems.INGOT_TITANIUM.get(), 11), mcCopper) && !accepts(vanilla, tanks, pipes, ti, new ItemStack(Items.COPPER_INGOT, 7)),
                "3 tanks, 2 pipes, 11 titanium or 7 copper are not enough");
        int mentions = 0;
        for(AnvilConstructionRecipe r : all) if(describe(r).contains("hbmsntm:heater_oilburner")) mentions++;
        check(mentions == 2, "the burner appears in no other entry (no recycling entry, as the original)");
    }

    static void burnerProxies() {
        for(Direction facing : HORIZONTALS) {
            reset();
            Level level = level();
            BlockPos core = new BlockPos(0, 64, 0);
            HeaterOilburnerBlockEntity b = burner(level, core, facing);
            check(b != null && b.getBlockPos().equals(core), facing + ": the core is the burner block entity");
            b.heatEnergy = 12_345;
            BlockEntity top = level.getBlockEntity(core.above());
            check(top instanceof ProxyComboBlockEntity p && p.getHeatStored() == 12_345 && p.getAllTanks().length == 0
                            && p.transferFluid(Fluids.HEATINGOIL, 0, 100) == 100 && b.tank.getFill() == 0,
                    facing + ": the extra above the core is a heat source (reads the core's 12,345 TU) and takes no fluid");
            boolean sides = true;
            for(Direction d : HORIZONTALS) {
                BlockEntity e = level.getBlockEntity(core.relative(d));
                sides &= e instanceof ProxyComboBlockEntity p && p.getHeatStored() == 0 && p.getAllTanks().length == 1
                        && p.transferFluid(Fluids.HEATINGOIL, 0, 100) == 0;
            }
            check(sides && b.tank.getFill() == 400, facing + ": the four side extras take fluid into the core tank (4 x 100 mB) and give no heat");
            int proxies = 0;
            for(BlockPos p : Goal11ABlockAccess.parts(BURNER, level)) if(level.getBlockEntity(p) instanceof ProxyComboBlockEntity) proxies++;
            check(proxies == 5, facing + ": exactly five proxies (four sides, one top); the other dummies have no block entity");
            ProxyComboBlockEntity p = (ProxyComboBlockEntity) top;
            p.useUpHeat(345);
            check(b.heatEnergy == 12_000, facing + ": heat drawn from the top proxy comes out of the core");
        }

        // An already-placed burner keeps the proxy flags saved with it (NBT "Fluid"/"Heat"): an old top proxy stays fluid.
        ProxyComboBlockEntity old = new ProxyComboBlockEntity(new BlockPos(0, 65, 0), new BlockState()).fluid();
        CompoundTag saved = Goal11AProxyAccess.save(old);
        ProxyComboBlockEntity loaded = new ProxyComboBlockEntity(new BlockPos(0, 65, 0), new BlockState());
        Goal11AProxyAccess.load(loaded, saved);
        check(Goal11AProxyAccess.fluid(loaded) && !Goal11AProxyAccess.heat(loaded),
                "a top proxy saved before Goal 11A loads as fluid and not heat (old burners need re-placing for the heat source)");
    }

    /** A heat consumer on top of the burner; expected maps the heat taken from the burner to what the consumer shows after its tick. */
    record Consumer(String name, BlockEntity be, java.util.function.IntSupplier heat, Runnable tick, java.util.function.IntUnaryOperator expected) {}

    static void burnerHeat() {
        String[] names = {"heat boiler", "Stirling engine", "combination oven", "heating oven", "crucible (production tryPullHeat body)"};
        for(String name : names) {
            reset();
            Level level = level();
            BlockPos core = new BlockPos(0, 64, 0);
            HeaterOilburnerBlockEntity b = burner(level, core, Direction.NORTH);
            b.heatEnergy = 50_000;
            BlockPos at = core.above(2);
            Consumer c = switch(name) {
                case "heat boiler" -> {
                    MachineHeatBoilerBlockEntity e = new MachineHeatBoilerBlockEntity(at, facing(level, at, Direction.NORTH));
                    level.put(e);
                    yield new Consumer(name, e, () -> e.heat, e::updateEntity, lost -> lost);
                }
                case "Stirling engine" -> {
                    MachineStirlingBlockEntity e = new MachineStirlingBlockEntity(at, facing(level, at, Direction.NORTH));
                    level.put(e);
                    e.hasCog = true;
                    // The engine zeroes its heat at the end of each tick; what it pulled shows as powerBuffer = heat x 0.5.
                    yield new Consumer(name, e, () -> (int) e.powerBuffer, e::updateEntity, lost -> (int) (lost * MachineStirlingBlockEntity.EFFICIENCY));
                }
                case "combination oven" -> {
                    MachineFurnaceCombinationBlockEntity e = new MachineFurnaceCombinationBlockEntity(at, facing(level, at, Direction.NORTH));
                    level.put(e);
                    yield new Consumer(name, e, () -> e.heat, e::updateEntity, lost -> lost);
                }
                case "heating oven" -> {
                    HeaterOvenBlockEntity e = new HeaterOvenBlockEntity(at, facing(level, at, Direction.NORTH));
                    level.put(e);
                    // Pull at heatEff 0.5, then the firebox's idle cooling of max(heat / 1000, 1) in the same tick (HeaterFireboxBlockEntity).
                    yield new Consumer(name, e, () -> e.heatEnergy, e::updateEntity, lost -> {
                        int h = (int) (lost * HeaterOvenBlockEntity.heatEff);
                        return h - Math.max(h / 1000, 1);
                    });
                }
                default -> {
                    Goal11ACrucibleProbe e = new Goal11ACrucibleProbe(level, at);
                    yield new Consumer(name, null, () -> e.heat, e::tryPullHeat, lost -> lost);
                }
            };
            level.time = 1;
            int before = b.heatEnergy;
            c.tick.run();
            int gained = c.heat.getAsInt(), lost = before - b.heatEnergy;
            check(level.getBlockEntity(at.below()) instanceof ProxyComboBlockEntity && gained > 0 && lost > 0 && c.expected.applyAsInt(lost) == gained,
                    name + " on top: draws heat through the top proxy (" + lost + " TU out of the burner, " + gained + " TU in)");
        }
    }

    static void burnerSettings() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 64, 0);
        HeaterOilburnerBlockEntity b = burner(level, core, Direction.NORTH);
        check(!b.isOn && b.setting == 1, "a new burner is off with setting 1 (original isOn = false)");
        b.tank.setFill(1_000);
        for(int t = 1; t <= 20; t++) {
            level.time = t;
            b.updateEntity();
        }
        check(b.tank.getFill() == 1_000 && b.heatEnergy == 0, "off: it burns nothing");

        Player player = new Player();
        List<Integer> cycle = new ArrayList<>();
        for(int i = 0; i < 11; i++) {
            boolean used = BURNER.onScrew(level, player, core.relative(Direction.EAST), Direction.UP, ToolType.SCREWDRIVER);
            if(!used) cycle.add(-1);
            cycle.add(b.setting);
        }
        check(cycle.equals(List.of(2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2)), "the screwdriver cycles the setting 1 -> 10 -> 1 (on any part of the burner): " + cycle);
        int at = b.setting;
        boolean refused = true;
        for(ToolType tool : ToolType.values()) if(tool != ToolType.SCREWDRIVER) refused &= !BURNER.onScrew(level, player, core, Direction.UP, tool) && b.setting == at;
        check(refused, "the hand drill and every other tool are refused and change nothing");

        CompoundTag setting = new CompoundTag();
        setting.putInt("setting", 7);
        int dirty = b.dirty;
        b.receiveControl(setting);
        check(b.setting == at && !b.isOn && b.dirty == dirty + 1, "receiveControl ignores \"setting\" (the original only toggles)");
        CompoundTag toggle = new CompoundTag();
        toggle.putBoolean("toggle", true);
        b.receiveControl(toggle);
        check(b.isOn, "receiveControl \"toggle\" switches it on");

        int[][] clamp = {{100, 10}, {11, 10}, {10, 10}, {5, 5}, {1, 1}, {0, 1}, {-3, 1}};
        boolean loads = true, pastes = true;
        for(int[] c : clamp) {
            CompoundTag tag = Goal11AHeaterAccess.save(b);
            tag.putInt("setting", c[0]);
            HeaterOilburnerBlockEntity copy = new HeaterOilburnerBlockEntity(core, b.getBlockState());
            Goal11AHeaterAccess.load(copy, tag);
            loads &= copy.setting == c[1] && copy.isOn && copy.tank.getFill() == b.tank.getFill();
            CompoundTag paste = new CompoundTag();
            paste.putInt("setting", c[0]);
            paste.putBoolean("isOn", false);
            HeaterOilburnerBlockEntity target = new HeaterOilburnerBlockEntity(core, b.getBlockState());
            target.pasteSettings(paste, 0, level, player, core);
            pastes &= target.setting == c[1] && !target.isOn;
        }
        check(loads, "loading clamps the setting to 1..10 (old saves up to 100 -> 10, 0 -> 1), isOn and the tank survive the round trip");
        check(pastes, "pasting settings clamps to 1..10 as well");
        // The copy tool path (DummyableBlock.pasteSettings -> core) does not mark the block entity, so pasteSettings must.
        HeaterOilburnerBlockEntity pasted = burner(level, new BlockPos(20, 64, 0), Direction.NORTH);
        CompoundTag again = new CompoundTag();
        again.putInt("setting", 4);
        again.putBoolean("isOn", true);
        int pastedDirty = pasted.dirty;
        pasted.pasteSettings(again, 0, level, player, pasted.getBlockPos());
        check(pasted.setting == 4 && pasted.isOn && pasted.dirty == pastedDirty + 1, "pasting settings marks the burner for saving (once)");
    }

    static void burnerPollution() {
        FluidType[] fuels = {Fluids.OIL, Fluids.GAS, Fluids.HEATINGOIL};
        long[] heat = {OIL_HEAT, GAS_HEAT, HEATINGOIL_HEAT};
        float[] soot = {SOOT_UNREFINED_OIL, SOOT_GAS, SOOT_UNREFINED_OIL};
        for(int k = 0; k < fuels.length; k++) {
            FluidType fuel = fuels[k];
            check(fuel.getTrait(FT_Flammable.class).getHeatEnergy() == heat[k], Fluids.POLLUTING.get(fuelName(fuel)) + " fuel " + fuelName(fuel)
                    + ": " + heat[k] + " TU per bucket as the original registerCalculatedFuel");
            FT_Polluting trait = fuel.getTrait(FT_Polluting.class);
            check(trait.burnMap.keySet().equals(Set.of(PollutionType.SOOT)) && trait.burnMap.get(PollutionType.SOOT) == soot[k],
                    fuelName(fuel) + " burns into soot only, " + soot[k] + " per call (" + Fluids.POLLUTING.get(fuelName(fuel)) + ")");
            for(int setting : new int[] {1, 10}) {
                reset();
                Level level = level();
                HeaterOilburnerBlockEntity b = burner(level, new BlockPos(0, 64, 0), Direction.NORTH);
                b.isOn = true;
                b.setting = setting;
                b.tank.setTankType(fuel);
                b.tank.setFill(16_000);
                for(int t = 1; t <= 100; t++) {
                    level.time = t;
                    // A consumer that takes all heat: below the 100,000 TU cap the burner burns every tick.
                    b.heatEnergy = 0;
                    b.updateEntity();
                }
                float expected = originalEmission(soot[k]);
                boolean amounts = PollutionHandler.CALLS.stream().allMatch(c -> c.type() == PollutionType.SOOT && c.amount() == expected);
                check(PollutionHandler.CALLS.size() == 20 && amounts && b.tank.getFill() == 16_000 - 100 * setting,
                        fuelName(fuel) + ", setting " + setting + ": one soot call every 5 ticks (20 in 100 ticks) of ceil(" + soot[k] + " x 100) / 100 = "
                                + expected + ", independent of the amount burned (" + PollutionHandler.CALLS.size() + " calls"
                                + (PollutionHandler.CALLS.isEmpty() ? "" : ", " + PollutionHandler.CALLS.get(0).amount()) + ")");
            }
        }
        // Nothing when off, empty, not flammable, or at the heat cap.
        String[] cases = {"off", "empty", "water", "heat cap"};
        for(String c : cases) {
            reset();
            Level level = level();
            HeaterOilburnerBlockEntity b = burner(level, new BlockPos(0, 64, 0), Direction.NORTH);
            b.isOn = !c.equals("off");
            b.setting = 5;
            b.tank.setTankType(c.equals("water") ? Fluids.WATER : Fluids.GAS);
            b.tank.setFill(c.equals("empty") ? 0 : 1_000);
            if(c.equals("heat cap")) b.heatEnergy = BURNER_MAX_HEAT;
            for(int t = 1; t <= 50; t++) {
                level.time = t;
                b.updateEntity();
            }
            check(PollutionHandler.CALLS.isEmpty(), c + ": no pollution");
        }
    }

    static String fuelName(FluidType t) {
        return t == Fluids.OIL ? "OIL" : t == Fluids.GAS ? "GAS" : t == Fluids.HEATINGOIL ? "HEATINGOIL" : "?";
    }

    static void burnerSaving() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 64, 0);
        HeaterOilburnerBlockEntity b = burner(level, core, Direction.NORTH);
        level.time = 1;
        int d0 = b.dirty;
        b.updateEntity();
        check(b.dirty == d0, "an idle tick (off, empty, cold) marks nothing for saving");
        long rest = b.transferFluid(Fluids.HEATINGOIL, 0, 500);
        check(rest == 0 && b.tank.getFill() == 500 && b.dirty == d0 + 1, "a pipe transfer that adds fluid marks the burner for saving (no tick needed)");
        rest = b.transferFluid(Fluids.GAS, 0, 500);
        check(rest == 500 && b.dirty == d0 + 1, "a refused transfer (wrong fluid) marks nothing");
        b.isOn = true;
        level.time = 2;
        b.updateEntity();
        check(b.dirty == d0 + 2 && b.tank.getFill() == 499 && b.heatEnergy > 0, "a tick that burns (fill and heat change) marks it");
        b.isOn = false;
        int heat = b.heatEnergy;
        level.time = 3;
        b.updateEntity();
        check(b.heatEnergy < heat && b.dirty == d0 + 3, "a tick that only cools marks it");
        b.heatEnergy = 0;
        level.time = 4;
        b.slots.set(2, FluidIDMultiItem.createStack(Fluids.GAS));
        b.updateEntity();
        check(b.tank.getTankType() == Fluids.GAS && b.dirty == d0 + 4, "a tick that changes the tank type (identifier in slot 2) marks it");
        level.time = 5;
        b.updateEntity();
        check(b.dirty == d0 + 4, "the next idle tick marks nothing");
    }

    /**
     * TileEntityHeaterOilburner.java:56-83: shouldCool = false is set inside the flammable branch whatever toBurn is, so a burner
     * that is on with a flammable type keeps its heat while the tank is empty; burning and the 5-tick pollution still need
     * toBurn > 0. An off burner, a non-flammable type and a burner at the heat cap behave as before.
     */
    static void burnerKeepsHeat() {
        BlockPos at = new BlockPos(0, 64, 0);
        for(FluidType fuel : new FluidType[] {Fluids.OIL, Fluids.GAS, Fluids.HEATINGOIL}) {
            for(int setting : new int[] {1, 10}) {
                reset();
                Level level = level();
                HeaterOilburnerBlockEntity b = burner(level, at, Direction.NORTH);
                b.isOn = true;
                b.setting = setting;
                b.tank.setTankType(fuel);
                b.tank.setFill(0);
                b.heatEnergy = 5_000;
                int dirty = b.dirty;
                for(int t = 1; t <= 50; t++) {
                    level.time = t;
                    b.updateEntity();
                }
                check(b.heatEnergy == 5_000 && b.tank.getFill() == 0 && PollutionHandler.CALLS.isEmpty() && b.dirty == dirty,
                        "on, " + fuelName(fuel) + ", setting " + setting + ", empty tank, 5,000 TU: after 50 ticks (10 pollution intervals) the heat is kept, no pollution, "
                                + "nothing burned, nothing marked for saving (heat " + b.heatEnergy + ", fill " + b.tank.getFill() + ", " + PollutionHandler.CALLS.size()
                                + " soot calls, " + (b.dirty - dirty) + " marks)");
            }
        }

        // The tick that empties the tank burns what is left, then the heat stays: no cooling afterwards either.
        reset();
        Level level = level();
        HeaterOilburnerBlockEntity b = burner(level, at, Direction.NORTH);
        b.isOn = true;
        b.setting = 10;
        b.tank.setTankType(Fluids.GAS);
        b.tank.setFill(3);
        level.time = 5;
        b.updateEntity();
        int made = b.heatEnergy;
        check(made == 3 * (int) (GAS_HEAT / 1000) && b.tank.getFill() == 0 && PollutionHandler.CALLS.size() == 1,
                "on, GAS, setting 10, 3 mB left: that tick burns 3 mB (" + made + " TU) and, at a multiple of 5, pollutes once (" + PollutionHandler.CALLS.size() + " call)");
        int dirty = b.dirty;
        for(int t = 6; t <= 60; t++) {
            level.time = t;
            b.updateEntity();
        }
        check(b.heatEnergy == made && PollutionHandler.CALLS.size() == 1 && b.dirty == dirty,
                "afterwards the empty burner keeps its " + made + " TU (no cooling, no more pollution, no marks): " + b.heatEnergy);

        // As before: off, a non-flammable type, and the heat cap.
        reset();
        level = level();
        b = burner(level, at, Direction.NORTH);
        b.isOn = false;
        b.tank.setTankType(Fluids.GAS);
        b.tank.setFill(0);
        b.heatEnergy = 5_000;
        dirty = b.dirty;
        level.time = 1;
        b.updateEntity();
        check(b.heatEnergy == 5_000 - 5 && b.dirty == dirty + 1 && PollutionHandler.CALLS.isEmpty(),
                "off, GAS, empty, 5,000 TU: cools by max(heat / 1000, 1) = 5 and is marked (heat " + b.heatEnergy + ")");

        reset();
        level = level();
        b = burner(level, at, Direction.NORTH);
        b.isOn = true;
        b.setting = 5;
        b.tank.setTankType(Fluids.WATER);
        b.tank.setFill(1_000);
        b.heatEnergy = 5_000;
        dirty = b.dirty;
        for(int t = 1; t <= 5; t++) {
            level.time = t;
            b.updateEntity();
        }
        check(b.heatEnergy < 5_000 && b.tank.getFill() == 1_000 && b.dirty == dirty + 5 && PollutionHandler.CALLS.isEmpty(),
                "on, WATER (not flammable), 1,000 mB: cools every tick, burns nothing, no pollution (heat " + b.heatEnergy + ", fill " + b.tank.getFill() + ")");

        reset();
        level = level();
        b = burner(level, at, Direction.NORTH);
        b.isOn = true;
        b.setting = 10;
        b.tank.setTankType(Fluids.GAS);
        b.tank.setFill(1_000);
        b.heatEnergy = BURNER_MAX_HEAT;
        dirty = b.dirty;
        for(int t = 1; t <= 10; t++) {
            level.time = t;
            b.updateEntity();
        }
        check(b.heatEnergy == BURNER_MAX_HEAT && b.tank.getFill() == 1_000 && b.dirty == dirty && PollutionHandler.CALLS.isEmpty(),
                "on, GAS, 1,000 mB, heat at the 100,000 TU cap: neither burns nor cools nor pollutes (heat " + b.heatEnergy + ", fill " + b.tank.getFill() + ")");
    }

    static void burner() {
        burnerAnvil();
        burnerProxies();
        burnerHeat();
        burnerSettings();
        burnerPollution();
        burnerSaving();
        burnerKeepsHeat();
        section("7. fluid burner");
    }

    // ---- 9. Whole chain -----------------------------------------------------------------------------------------------

    static void cableLine(Level level, List<BlockPos> path) {
        for(BlockPos p : path) cable(level, p);
    }

    /** Positions from a to b (inclusive): x first, then y, then z. */
    static List<BlockPos> path(BlockPos a, BlockPos b, boolean yFirst) {
        List<BlockPos> out = new ArrayList<>();
        BlockPos p = a;
        out.add(p);
        if(yFirst) while(p.getY() != b.getY()) { p = p.offset(0, Integer.signum(b.getY() - p.getY()), 0); out.add(p); }
        while(p.getX() != b.getX()) { p = p.offset(Integer.signum(b.getX() - p.getX()), 0, 0); out.add(p); }
        while(p.getZ() != b.getZ()) { p = p.offset(0, 0, Integer.signum(b.getZ() - p.getZ())); out.add(p); }
        while(p.getY() != b.getY()) { p = p.offset(0, Integer.signum(b.getY() - p.getY()), 0); out.add(p); }
        return out;
    }

    static void chain() {
        reset();
        Level level = level();
        // Ground: stone below the derrick down to Y -59, a radius-15 bubble whose top is a few blocks under the core.
        BlockPos dCore = new BlockPos(0, 0, 0);
        fillStone(level, -18, 18, -60, -1, -18, 18);
        Goal11AWorldGen.spawnOil(new Goal11AWorldGen.LevelView(level), 0, -22, 0, 15);
        MachineOilWellBlockEntity derrick = derrick(level, dCore, Direction.NORTH);
        derrick.power = DERRICK_MAX_POWER;

        int setting = 6;
        BlockPos bCore = new BlockPos(20, 0, 0);
        HeaterOilburnerBlockEntity burner = burner(level, bCore, Direction.NORTH);
        burner.tank.setTankType(Fluids.GAS);
        burner.isOn = true;
        burner.setting = setting;
        // Gas: derrick east connection -> pipe -> the burner's west connection (core - 2).
        for(BlockPos p : path(dCore.relative(Direction.EAST), bCore.offset(-2, 0, 0), false)) pipe(level, p, Fluids.GAS);
        // Oil: derrick west connection -> pipe -> a barrel (emptied by the fixture each tick, counted as exported).
        for(BlockPos p : path(dCore.relative(Direction.WEST), dCore.offset(-5, 0, 0), false)) pipe(level, p, Fluids.OIL);
        BarrelBlockEntity oilOut = barrel(level, dCore.offset(-6, 0, 0), Fluids.OIL);

        BlockPos boilerPos = bCore.above(2);
        MachineHeatBoilerBlockEntity boiler = new MachineHeatBoilerBlockEntity(boilerPos, facing(level, boilerPos, Direction.NORTH));
        level.put(boiler);
        boiler.tanks[0].setFill(boiler.tanks[0].getMaxFill());
        BlockPos enginePos = new BlockPos(40, 0, 20);
        MachineSteamEngineBlockEntity engine = new MachineSteamEngineBlockEntity(enginePos, facing(level, enginePos, Direction.NORTH));
        level.put(engine);
        // Power: the engine's first connection -> cables up to Y 12, across, down to the derrick's north connection.
        BlockPos ePort = engine.getConPos()[0].makeCompat();
        BlockPos dPort = dCore.relative(Direction.NORTH);
        List<BlockPos> wire = new ArrayList<>(path(ePort, ePort.offset(0, 12, 0), true));
        wire.addAll(path(ePort.offset(0, 12, 0), new BlockPos(0, 12, -3), false));
        wire.addAll(path(new BlockPos(0, 12, -3), new BlockPos(0, 0, -3), true));
        wire.addAll(path(new BlockPos(0, 0, -3), dPort, false));
        cableLine(level, new ArrayList<>(new java.util.LinkedHashSet<>(wire)));
        oilOut.updateEntity();
        net(level);

        long gasMade = 0, gasPiped = 0, gasBurned = 0, heatMade = 0, heatToBoiler = 0, heMade = 0, heToDerrick = 0, heUsed = 0, oilMade = 0, oilOutTotal = 0;
        long minPower = Long.MAX_VALUE, steamMoved = 0, cooled = 0;
        boolean fluidOk = true, heatOk = true, powerOk = true;
        String firstBad = null;
        int ticks = 40_000, firstGas = -1;
        long[] window = new long[4];
        for(int t = 1; t <= ticks; t++) {
            level.time = t;
            // Derrick: sucked oil/gas show up in its tanks during its own update (the pipe transfer happens in the net step).
            int g0 = derrick.tanks[1].getFill(), o0 = derrick.tanks[0].getFill();
            long p0 = derrick.power;
            derrick.updateEntity();
            int sucked = derrick.tanks[1].getFill() - g0;
            int oilSucked = derrick.tanks[0].getFill() - o0;
            long used = p0 - derrick.power;
            gasMade += sucked;
            oilMade += oilSucked;
            heUsed += used;
            if(sucked > 0 && firstGas < 0) firstGas = t;
            // Burner: burns from its tank, heat goes up; the boiler then pulls through the top proxy.
            int bf0 = burner.tank.getFill(), bh0 = burner.heatEnergy;
            burner.updateEntity();
            int burned = bf0 - burner.tank.getFill();
            int bh1 = burner.heatEnergy;
            gasBurned += burned;
            // A burning tick adds exactly 50 TU per mB of gas (original 50,000 TU per bucket); an idle tick only cools.
            if(burned > 0) {
                heatMade += bh1 - bh0;
                if(bh1 - bh0 != burned * (GAS_HEAT / 1000)) { heatOk = false; if(firstBad == null) firstBad = "tick " + t + ": " + burned + " mB gave " + (bh1 - bh0) + " TU"; }
            } else {
                cooled += bh0 - bh1;
            }
            boiler.updateEntity();
            // The boiler converts part of its heat to steam in the same tick, so only the burner side of the pull is
            // measured: it never goes up.
            int pulled = bh1 - burner.heatEnergy;
            heatToBoiler += pulled;
            if(pulled < 0) { heatOk = false; if(firstBad == null) firstBad = "tick " + t + ": negative pull"; }
            // Steam into the engine tank (the fixture model of the Goal 10C chain), spent steam removed, water refilled.
            int steam = boiler.tanks[1].getFill();
            int room = engine.tanks[0].getMaxFill() - engine.tanks[0].getFill();
            int moved = Math.min(steam, room);
            boiler.tanks[1].setFill(steam - moved);
            engine.tanks[0].setFill(engine.tanks[0].getFill() + moved);
            steamMoved += moved;
            engine.updateEntity();
            long generated = engine.powerBuffer;
            heMade += generated;
            engine.tanks[1].setFill(0);
            boiler.tanks[0].setFill(boiler.tanks[0].getMaxFill());
            oilOut.updateEntity();
            // Network step: gas derrick -> burner, oil derrick -> barrel, power engine -> derrick.
            int dg = derrick.tanks[1].getFill(), bg = burner.tank.getFill(), dOil = derrick.tanks[0].getFill(), barrelOil = oilOut.tank.getFill();
            long dp = derrick.power, eb = engine.powerBuffer;
            transfer(level);
            int gasOut = dg - derrick.tanks[1].getFill(), gasIn = burner.tank.getFill() - bg;
            int oilSent = dOil - derrick.tanks[0].getFill(), oilIn = oilOut.tank.getFill() - barrelOil;
            long sent = eb - engine.powerBuffer, got = derrick.power - dp;
            if(gasOut != gasIn || oilSent != oilIn) { fluidOk = false; if(firstBad == null) firstBad = "tick " + t + ": gas " + gasOut + "/" + gasIn + ", oil " + oilSent + "/" + oilIn; }
            if(sent != got) { powerOk = false; if(firstBad == null) firstBad = "tick " + t + ": power sent " + sent + ", received " + got; }
            gasPiped += gasIn;
            heToDerrick += got;
            oilOutTotal += oilIn;
            oilOut.tank.setFill(0);
            minPower = Math.min(minPower, derrick.power);
            if(t > ticks - 10_000) {
                window[0] += sucked;
                window[1] += burned;
                window[2] += got;
                window[3] += used;
            }
        }
        long gasStock = derrick.tanks[1].getFill() + burner.tank.getFill();
        check(fluidOk && gasMade == gasStock + gasBurned && oilMade == derrick.tanks[0].getFill() + oilOutTotal,
                "fluid: every tick the pipe moves exactly what leaves the derrick; over " + ticks + " ticks gas made " + gasMade + " = burned " + gasBurned
                        + " + stock " + gasStock + ", oil made " + oilMade + " = exported " + oilOutTotal + " + stock " + derrick.tanks[0].getFill()
                        + (firstBad == null ? "" : "; " + firstBad));
        check(heatOk && powerOk && heatMade == gasBurned * (GAS_HEAT / 1000) && heatMade == heatToBoiler + cooled + burner.heatEnergy,
                "heat and power: the burner makes 50 TU per mB of gas, all of it is pulled by the boiler through the top proxy, cooled off or still "
                        + "stored (" + heatMade + " = " + heatToBoiler + " + " + cooled + " + " + burner.heatEnergy + "), and every tick the cable delivers exactly "
                        + "what the engine sends"
                        + (firstBad == null ? "" : "; " + firstBad));
        check(firstGas > 0 && gasBurned > 0 && heToDerrick > 0, "the chain runs: gas from tick " + firstGas + ", " + gasBurned + " mB burned, " + heToDerrick + " HE back to the derrick");
        long last = 10_000;
        info("chain over " + ticks + " ticks (burner setting " + setting + " mB/t): gas " + gasMade + " mB (" + String.format(java.util.Locale.ROOT, "%.2f", gasMade / (double) ticks)
                + " mB/t), oil " + oilMade + " mB, burned " + gasBurned + " mB, heat " + heatMade + " TU, pulled by the boiler " + heatToBoiler + " TU, steam "
                + steamMoved + " mB, engine " + heMade + " HE made / " + heToDerrick + " HE delivered, derrick used " + heUsed + " HE; derrick power min "
                + minPower + ", end " + derrick.power + " HE");
        info("last " + last + " ticks: gas " + String.format(java.util.Locale.ROOT, "%.2f", window[0] / (double) last) + " mB/t made, "
                + String.format(java.util.Locale.ROOT, "%.2f", window[1] / (double) last) + " mB/t burned, " + String.format(java.util.Locale.ROOT, "%.1f", window[2] / (double) last)
                + " HE/t delivered vs " + String.format(java.util.Locale.ROOT, "%.1f", window[3] / (double) last) + " HE/t used; self-sustaining in this run: "
                + (window[2] >= window[3] && derrick.power >= DERRICK_HE ? "yes" : "no") + " (not asserted)");
        section("9. whole chain");
    }

    // ---- 10. Drain ------------------------------------------------------------------------------------------------------

    static void drain() {
        for(int radius : new int[] {8, 15}) for(boolean cave : new boolean[] {false, true}) {
            reset();
            Level level = level();
            int cy = -64 + 25;
            fillStone(level, -18, 18, -62, -1, -18, 18);
            if(cave) for(int x = -18; x <= 18; x++) for(int z = -18; z <= 18; z++) level.states.put(new BlockPos(x, cy, z), AIR);
            Goal11AWorldGen.spawnOil(new Goal11AWorldGen.LevelView(level), 0, cy, 0, radius);
            Set<BlockPos> bubble = new HashSet<>();
            int minY = Integer.MAX_VALUE, maxY = Integer.MIN_VALUE;
            for(Map.Entry<BlockPos, BlockState> e : level.states.entrySet()) if(e.getValue().is(NtmBlocks.ORE_OIL.get())) {
                bubble.add(e.getKey());
                minY = Math.min(minY, e.getKey().getY());
                maxY = Math.max(maxY, e.getKey().getY());
            }
            Map<BlockPos, BlockState> start = new HashMap<>(level.states);
            BlockPos core = new BlockPos(0, 0, 0);
            MachineOilWellBlockEntity d = derrick(level, core, Direction.NORTH);
            Map<BlockPos, BlockState> afterPlace = new HashMap<>(level.states);
            long oil = 0, gas = 0, sucks = 0, descentsInBubble = 0, steps = 0;
            boolean gasRange = true;
            while(steps < 3_000_000) {
                int bottom = shaftBottom(level, core);
                if(bottom < minY || d.indicator == 1) break;
                int[] made = step(d);
                steps++;
                if(made[0] > 0) {
                    sucks++;
                    oil += made[0];
                    gas += made[1];
                    gasRange &= made[1] >= GAS_MIN && made[1] <= GAS_MAX && made[0] == OIL_PER_SUCK;
                }
                int now = shaftBottom(level, core);
                if(now < bottom && now <= maxY) descentsInBubble++;
            }
            int remaining = 0, empty = 0, pipes = 0;
            for(BlockPos p : bubble) {
                BlockState s = level.getBlockState(p);
                if(s.is(NtmBlocks.ORE_OIL.get())) remaining++;
                else if(s.is(NtmBlocks.ORE_OIL_EMPTY.get())) empty++;
                else if(s.is(NtmBlocks.OIL_PIPE.get())) pipes++;
            }
            boolean outside = true;
            for(Map.Entry<BlockPos, BlockState> e : level.states.entrySet()) {
                BlockPos p = e.getKey();
                BlockState was = afterPlace.get(p);
                if(was != null && was.sameAs(e.getValue())) continue;
                outside &= bubble.contains(p) || (p.getX() == 0 && p.getZ() == 0 && p.getY() < 0);
            }
            String label = "radius " + radius + (cave ? " with a 1-block air cut at Y " + cy : "") + " (centre Y " + cy + ", " + bubble.size() + " oil rock, Y " + minY + ".." + maxY + ")";
            info(label + ": " + steps + " drill actions, " + sucks + " sucks, " + oil + " mB oil, " + gas + " mB gas, " + descentsInBubble
                    + " shaft descents inside the bubble, " + remaining + " oil rock left, " + empty + " empty, " + pipes + " turned into shaft; shaft bottom Y "
                    + shaftBottom(level, core) + ", indicator " + d.indicator);
            check(gasRange && oil == sucks * OIL_PER_SUCK && remaining + empty + pipes == bubble.size() && empty + pipes <= sucks,
                    label + ": 500 mB oil and 100-500 mB gas per suck; every oil rock is left, emptied or drilled after emptying (" + remaining + "+" + empty + "+" + pipes
                            + "), and each emptied block cost at least one suck");
            check(outside && start.size() <= level.states.size(), label + ": nothing outside the bubble and the shaft column changed");
            check(shaftBottom(level, core) < minY || d.indicator == 1, label + ": the shaft passes the bubble (or reaches its depth)");
        }
        section("10. drain");
    }

    public static void main(String[] args) {
        List<String> avoidTag = args.length > 0 && !args[0].isEmpty() ? Arrays.asList(args[0].split(",")) : List.of();
        run("1. derrick connection points", Goal11ARegression::connections);
        run("3. bubble placement", Goal11ARegression::bubblePlacement);
        run("4. avoidance", () -> avoidance(avoidTag));
        run("5. drill depth", Goal11ARegression::drillDepth);
        run("7. fluid burner", Goal11ARegression::burner);
        run("9. whole chain", Goal11ARegression::chain);
        run("10. drain", Goal11ARegression::drain);
        System.out.println("Goal 11A machine world: " + checks + " checks passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
