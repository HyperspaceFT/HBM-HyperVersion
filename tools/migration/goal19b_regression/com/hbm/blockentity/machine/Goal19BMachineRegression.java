package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.boiler.MachineHeatBoilerBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.machine.storage.BatterySocketBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.machine.BarrelBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.trait.FT_Coolable;
import com.hbm.inventory.fluid.trait.FT_Coolable.CoolingType;
import com.hbm.inventory.fluid.trait.FT_Heatable;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import io.netty.buffer.ByteBuf;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.server.MinecraftServer;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.neoforged.neoforge.network.PacketDistributor;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Goal 19B: the production industrial steam turbine block entity (and the shared TurbineBaseBlockEntity) in the Goal 9B world.
 * Expected numbers come from the original at d31426c (cited per constant) or from the independent models below, never from
 * the production methods under test. Arguments: the run directory (finite.json is written there) and the sections to run.
 */
public class Goal19BMachineRegression {
    private static int checks, sectionChecks, scenarios, ticks;
    private static final List<String> failures = new ArrayList<>();
    private static final Direction[] HORIZONTALS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};
    private static Path out;
    private static final Map<String, Object> notes = new LinkedHashMap<>();

    // Original TileEntityMachineIndustrialTurbine.java (d31426c): :34 inputTankSize 750,000, :35 outputTankSize 3,000,000,
    // :36 efficiency 1.0, :42 FLYWHEEL_MAX_ENERGY 0.5e8 ("flywheel mass"), :146 consumptionPercent 0.2, :148 resize true.
    static final int IN_CAP = 750_000;
    static final int OUT_CAP = 3_000_000;
    static final double EFF = 1.0D;
    static final double MASS = 0.5e8;
    static final double CONSUMPTION = 0.2D;
    // :93 the 0.05 floor of the power target.
    static final double FLOOR = 0.05D;
    // Fluids.java:637-640: FT_Coolable(coolsTo, amountReq, amountProduced, heatEnergy), TURBINE efficiency 1.0 for all four.
    record Tier(String name, int req, int produced, int heat, int cap0, int cap1, long maxPower) {
        FluidType in() { return switch(name) { case "STEAM" -> Fluids.STEAM; case "HOTSTEAM" -> Fluids.HOTSTEAM; case "SUPERHOTSTEAM" -> Fluids.SUPERHOTSTEAM; default -> Fluids.ULTRAHOTSTEAM; }; }
        FluidType out() { return switch(name) { case "STEAM" -> Fluids.SPENTSTEAM; case "HOTSTEAM" -> Fluids.STEAM; case "SUPERHOTSTEAM" -> Fluids.HOTSTEAM; default -> Fluids.SUPERHOTSTEAM; }; }
    }
    // Tank sizes after 0..3 lever pulls (TileEntityTurbineBase.java:109-117, /10 per step); maxPower = ceil(cap0 * 0.2 / req) * heat * 1.0.
    static final Tier[] TIERS = {
            new Tier("STEAM", 100, 1, 200, 750_000, 3_000_000, 300_000L),
            new Tier("HOTSTEAM", 1, 10, 2, 75_000, 300_000, 30_000L),
            new Tier("SUPERHOTSTEAM", 1, 10, 18, 7_500, 30_000, 27_000L),
            new Tier("ULTRAHOTSTEAM", 1, 10, 120, 750, 3_000, 18_000L),
    };
    static final Tier STEAM = TIERS[0];

    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());
    private static final BarrelBlock BIG = new BarrelBlock(10_000_000);
    static final BlockPos CORE = new BlockPos(0, 1, 0);

    // ---- harness -------------------------------------------------------------------------------------------------

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void run(String name, Runnable body) {
        try {
            body.run();
            System.out.println(name + ": " + sectionChecks + " checks passed");
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            checks--;
        } catch(RuntimeException e) {
            // A crash in production code under a mutation is reported, but is not an assertion (it never counts as a detection).
            System.out.println("Exception in " + name + ": " + e);
            failures.add(name + ": crashed with " + e);
            e.printStackTrace(System.out);
        }
        sectionChecks = 0;
        DummyableBlock.safeRem = false;
    }

    /** Original ForgeDirection.getRotation(UP), written out independently: NORTH -> EAST -> SOUTH -> WEST -> NORTH. */
    static Direction originalRot(Direction dir) {
        return switch(dir) {
            case NORTH -> Direction.EAST;
            case EAST -> Direction.SOUTH;
            case SOUTH -> Direction.WEST;
            case WEST -> Direction.NORTH;
            default -> throw new IllegalArgumentException(dir.toString());
        };
    }

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
        AudioWrapper.CREATED.clear();
        NuclearTechMod.proxy.client = null;
        scenarios++;
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
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

    static MachineIndustrialTurbineBlockEntity turbine(Level level, BlockPos pos, Direction dir) {
        MachineIndustrialTurbineBlockEntity t = new MachineIndustrialTurbineBlockEntity(pos, facing(level, pos, dir));
        level.put(t);
        return t;
    }

    static MachineIndustrialTurbineBlockEntity fresh() {
        reset();
        return turbine(level(), CORE, Direction.NORTH);
    }

    static void tick(MachineIndustrialTurbineBlockEntity t) {
        ticks++;
        t.updateEntity();
    }

    static void feed(MachineIndustrialTurbineBlockEntity t, int steam, int spent) {
        t.tanks[0].setFill(steam);
        t.tanks[1].setFill(spent);
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    static void line(Level level, FluidType type, BlockPos from, Direction dir, int count) {
        for(int i = 0; i < count; i++) pipe(level, from.relative(dir, i), type);
    }

    static CableBaseBlockEntity cable(Level level, BlockPos pos) {
        CableBaseBlockEntity wire = new CableBaseBlockEntity(pos, new BlockState());
        level.put(wire);
        wire.updateEntity();
        return wire;
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

    /** A battery socket with its proxies and a lithium pack (180,000,000 HE, 100,000 HE/t charge), as the Goal 9B world builds it. */
    static BatterySocketBlockEntity socket(Level level, BlockPos pos, Direction facing) {
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
        socket.slots.set(0, MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_LITHIUM.ordinal()));
        return socket;
    }

    /** Red cable from start up two blocks and one out, then a socket facing back (the Goal 9B rig shape). */
    static BatterySocketBlockEntity powerPath(Level level, BlockPos start, Direction out) {
        cable(level, start);
        cable(level, start.above());
        cable(level, start.above(2));
        cable(level, start.above(2).relative(out));
        BatterySocketBlockEntity socket = socket(level, start.above(2).relative(out, 2), out.getOpposite());
        socket.updateEntity();
        return socket;
    }

    // ---- independent model of the original server tick ------------------------------------------------------------

    /**
     * TileEntityTurbineBase.java:55-87 (ops = min((int) (min(ceil(fill * 0.2), fill) / req), room / produced); generatePower only
     * when ops > 0) with TileEntityMachineIndustrialTurbine.java:81-96 (maxPower = (long) (ceil(cap0 * 0.2 / req) * heat * eff),
     * flywheel += power; then spin = flywheel / 0.5e8 before the drain, target = min((long) (max(spin, 0.05) * maxPower), flywheel)).
     */
    static final class Model {
        final Tier tier;
        int fill0, fill1;
        long maxPower, flywheel, lastPowerTarget, powerBuffer;
        double spin;
        boolean operational;

        Model(Tier tier) { this.tier = tier; }

        static int ops(int fill0, int fill1, Tier tier) {
            int inputOps = (int) (Math.min(Math.ceil(fill0 * CONSUMPTION), fill0) / tier.req);
            int outputOps = (tier.cap1 - fill1) / tier.produced;
            return Math.min(inputOps, outputOps);
        }

        int tick() {
            powerBuffer = 0;
            int ops = ops(fill0, fill1, tier);
            if(ops > 0) {
                fill0 -= ops * tier.req;
                fill1 += ops * tier.produced;
                int maxOps = (int) Math.ceil((tier.cap0 * CONSUMPTION) / tier.req);
                maxPower = (long) (maxOps * tier.heat * EFF);
                flywheel += (long) (ops * tier.heat * EFF);
            }
            operational = ops > 0;
            spin = (double) flywheel / MASS;
            lastPowerTarget = Math.min((long) (Math.max(spin, FLOOR) * maxPower), flywheel);
            flywheel -= lastPowerTarget;
            powerBuffer = lastPowerTarget;
            return ops;
        }

        void syncTanks(MachineIndustrialTurbineBlockEntity t) {
            fill0 = t.tanks[0].getFill();
            fill1 = t.tanks[1].getFill();
        }

        String diff(MachineIndustrialTurbineBlockEntity t) {
            if(t.maxPower != maxPower || t.flywheel_energy != flywheel || t.spin != spin || t.lastPowerTarget != lastPowerTarget
                    || t.powerBuffer != powerBuffer || t.operational != operational || t.tanks[0].getFill() != fill0 || t.tanks[1].getFill() != fill1) {
                return "turbine maxPower " + t.maxPower + " flywheel " + t.flywheel_energy + " spin " + t.spin + " target " + t.lastPowerTarget
                        + " buffer " + t.powerBuffer + " operational " + t.operational + " tanks " + t.tanks[0].getFill() + "/" + t.tanks[1].getFill()
                        + " != model " + maxPower + " / " + flywheel + " / " + spin + " / " + lastPowerTarget + " / " + powerBuffer + " / " + operational
                        + " / " + fill0 + "/" + fill1;
            }
            return null;
        }
    }

    // ---- 1. constants and setup -------------------------------------------------------------------------------------

    static void constants() {
        MachineIndustrialTurbineBlockEntity t = fresh();
        check(t.tanks.length == 2 && t.tanks[0].getTankType() == Fluids.STEAM && t.tanks[0].getMaxFill() == IN_CAP && t.tanks[0].getFill() == 0,
                "1. tank 0 holds 750,000 mB of steam (TileEntityMachineIndustrialTurbine.java:34,72; got " + t.tanks[0].getMaxFill() + ")");
        check(t.tanks[1].getTankType() == Fluids.SPENTSTEAM && t.tanks[1].getMaxFill() == OUT_CAP && t.tanks[1].getFill() == 0,
                "1. tank 1 holds 3,000,000 mB of spent steam (:35,73; got " + t.tanks[1].getMaxFill() + ")");
        check(t.getEfficiency() == EFF && t.consumptionPercent() == CONSUMPTION && t.doesResizeCompressor(),
                "1. efficiency 1.0, consumption 0.2 and a resizing compressor (:36,146-148)");
        check(t.spin == 0D && t.maxPower == 0L && t.flywheel_energy == 0L && t.lastPowerTarget == 0L && t.powerBuffer == 0L && !t.operational
                        && t.rotor == 0F && t.lastRotor == 0F, "1. a new turbine starts at rest with maxPower 0");
        check(t.getReceivingTanks().length == 1 && t.getReceivingTanks()[0] == t.tanks[0] && t.getSendingTanks().length == 1
                        && t.getSendingTanks()[0] == t.tanks[1] && t.getAllTanks() == t.tanks, "1. receives into tank 0, sends from tank 1");
        // The parsed production traits are the original Fluids.java:637-640 values.
        for(Tier tier : TIERS) {
            FT_Coolable trait = tier.in().getTrait(FT_Coolable.class);
            check(trait != null && trait.coolsTo == tier.out() && trait.amountReq == tier.req && trait.amountProduced == tier.produced
                            && trait.heatEnergy == tier.heat && trait.getEfficiency(CoolingType.TURBINE) == 1.0D,
                    "1. " + tier.name + " cools to " + tier.out().getID() + ": " + tier.req + " mB -> " + tier.produced + " mB, " + tier.heat + " TU, TURBINE 1.0");
        }
        // Flywheel mass: one op (200 HE) from rest leaves spin = 200 / 0.5e8 for this tick (computed before the drain).
        feed(t, 500, 0);
        tick(t);
        check(t.spin == 200D / 0.5e8 && t.lastPowerTarget == 200L && t.flywheel_energy == 0L,
                "1. flywheel mass 0.5e8: one 200 HE op gives spin 4.0E-6 and all 200 HE out (got spin " + t.spin + ")");
        AABB box = t.getRenderBoundingBox();
        check(box.equals(new AABB(-3, 1, -3, 4, 4, 4)) && t.getRenderBoundingBox() == box,
                "1. render box x-3, y, z-3 .. x+4, y+3, z+4 (:233-247), cached (got " + box + ")");
    }

    // ---- 2. op formula ------------------------------------------------------------------------------------------------

    static void ops() {
        // fill -> ops: min((int) (min(ceil(fill * 0.2), fill) / 100), room); 495 * 0.2 is exactly 99.0 in double, 496 gives 99.2 -> 100.
        int[][] rows = {{0, 0}, {1, 0}, {495, 0}, {496, 1}, {500, 1}, {995, 1}, {996, 2}, {1_000, 2}, {10_000, 20}, {750_000, 1_500}};
        for(int[] row : rows) {
            check(Model.ops(row[0], 0, STEAM) == row[1], "2. op formula model: " + row[0] + " mB -> " + row[1] + " ops");
            MachineIndustrialTurbineBlockEntity t = fresh();
            feed(t, row[0], 0);
            tick(t);
            int ops = row[1];
            check(t.tanks[0].getFill() == row[0] - 100 * ops && t.tanks[1].getFill() == ops && t.flywheel_energy + t.lastPowerTarget == 200L * ops
                            && t.operational == (ops > 0),
                    "2. op formula: " + row[0] + " mB of steam -> " + ops + " ops, 100 mB -> 1 mB spent and 200 HE each (got " + t.tanks[0].getFill() + " / "
                            + t.tanks[1].getFill() + " / " + (t.flywheel_energy + t.lastPowerTarget) + " HE)");
        }
        MachineIndustrialTurbineBlockEntity t = fresh();
        feed(t, 10_000, OUT_CAP);
        tick(t);
        check(t.tanks[0].getFill() == 10_000 && t.tanks[1].getFill() == OUT_CAP && !t.operational && t.maxPower == 0L,
                "2. op formula: a full spent tank gives 0 ops");
        feed(t, 10_000, OUT_CAP - 1);
        tick(t);
        check(t.tanks[0].getFill() == 9_900 && t.tanks[1].getFill() == OUT_CAP && t.operational && t.maxPower == 300_000L,
                "2. op formula: room for 1 mB of spent steam gives exactly 1 op");

        // A non-coolable input (and a coolable one without TURBINE efficiency) is not valid: no ops, tank 1 NONE, maxPower kept.
        for(FluidType bad : new FluidType[] {Fluids.WATER, Fluids.HOTOIL}) {
            t = fresh();
            feed(t, 10_000, 0);
            tick(t);
            long held = t.maxPower;
            t.tanks[0].setTankType(bad);
            t.tanks[0].setFill(10_000);
            tick(t);
            check(held == 300_000L && t.maxPower == held && t.tanks[0].getFill() == 10_000 && t.tanks[0].getTankType() == bad
                            && t.tanks[1].getTankType() == Fluids.NONE && !t.operational,
                    "2. op formula: tank 0 of type " + bad.getID() + " gives no ops, tank 1 becomes NONE and maxPower stays 300,000 (TileEntityTurbineBase.java:66,92)");
        }
        // A valid tick forces tank 1 to the input's coolsTo type (:70).
        t = fresh();
        t.tanks[1].setTankType(Fluids.WATER);
        feed(t, 1_000, 0);
        tick(t);
        check(t.tanks[1].getTankType() == Fluids.SPENTSTEAM && t.tanks[1].getFill() == 2, "2. op formula: tank 1 is set to spent steam on a valid tick");
    }

    // ---- 3. flywheel --------------------------------------------------------------------------------------------------

    static void flywheel() {
        // (a) spool-up with tank 0 refilled to capacity and tank 1 drained every tick.
        MachineIndustrialTurbineBlockEntity t = fresh();
        Model m = new Model(STEAM);
        int floorEnd = -1, near = -1, exact = -1;
        String first = null;
        for(int n = 1; n <= 6_000; n++) {
            feed(t, IN_CAP, 0);
            m.fill0 = IN_CAP;
            m.fill1 = 0;
            tick(t);
            m.tick();
            if(n == 1) check(t.maxPower == 300_000L && t.lastPowerTarget == 15_000L && t.flywheel_energy == 285_000L && t.powerBuffer == 15_000L,
                    "3a. full feed: the first op tick sets maxPower 300,000 before the drain; 0.05 x 300,000 = 15,000 HE out, 285,000 HE stay (got "
                            + t.maxPower + " / " + t.lastPowerTarget + " / " + t.flywheel_energy + ")");
            String d = m.diff(t);
            if(d != null && first == null) first = "tick " + n + ": " + d;
            if(floorEnd < 0 && m.spin >= FLOOR) floorEnd = n;
            if(near < 0 && m.lastPowerTarget >= 297_000L) near = n;
            if(exact < 0 && m.lastPowerTarget == 300_000L) exact = n;
            if(exact > 0 && n >= exact + 100) break;
        }
        check(first == null, "3a. full feed: maxPower, flywheel_energy, spin, lastPowerTarget and powerBuffer equal the model of :81-96 every tick"
                + (first == null ? "" : "; first difference " + first));
        check(exact > 0 && t.lastPowerTarget == 300_000L && t.spin == 1.0D && t.flywheel_energy == 49_700_000L,
                "3a. full feed: spin reaches exactly 1.0 and the output 300,000 HE/t, with 49,700,000 HE left after each drain (got " + t.spin + ", " + t.lastPowerTarget + ")");
        System.out.println("  info: 3a spool-up at 1,500 ops/t: spin >= 0.05 on tick " + floorEnd + ", output >= 99 % on tick " + near + ", exactly 300,000 HE/t on tick " + exact);
        notes.put("spool_up_ticks", Map.of("spin_reaches_0.05", floorEnd, "output_99_percent", near, "output_300000", exact));

        // (b) idle after running: maxPower is held, the flywheel drains to exactly 0.
        first = null;
        int drained = -1;
        for(int n = 1; n <= 3_000 && (drained < 0 || n <= drained + 20); n++) {
            feed(t, 0, 0);
            m.fill0 = 0;
            m.fill1 = 0;
            tick(t);
            m.tick();
            String d = m.diff(t);
            if(d != null && first == null) first = "idle tick " + n + ": " + d;
            if(drained < 0 && m.flywheel == 0L) drained = n;
        }
        check(first == null, "3b. idle drain: maxPower held, flywheel -= min((long) (max(spin, 0.05) * maxPower), flywheel) with spin before the drain, as the model"
                + (first == null ? "" : "; first difference " + first));
        check(drained > 0 && t.flywheel_energy == 0L && t.spin == 0D && t.lastPowerTarget == 0L && t.powerBuffer == 0L && t.maxPower == 300_000L,
                "3b. idle drain: after the flywheel reaches 0 every field stays 0 except maxPower 300,000 (drained on idle tick " + drained + ")");
        System.out.println("  info: 3b idle drain from 300,000 HE/t: flywheel 0 after " + drained + " idle ticks");
        notes.put("idle_drain_ticks", drained);

        // (c) one op per tick: the 0.05 floor target (15,000) exceeds the flywheel, so all 200 HE leave every tick.
        t = fresh();
        boolean steady = true;
        for(int n = 0; n < 100; n++) {
            feed(t, 500, 0);
            tick(t);
            steady &= t.powerBuffer == 200L && t.lastPowerTarget == 200L && t.flywheel_energy == 0L && t.spin == 200D / MASS && t.maxPower == 300_000L;
        }
        check(steady, "3c. low input: one op per tick gives exactly 200 HE out every tick and an empty flywheel");

        // (d) maxPower at capacity for the four tiers.
        for(int k = 0; k < TIERS.length; k++) {
            Tier tier = TIERS[k];
            t = fresh();
            for(int i = 0; i < k; i++) t.onLeverPull();
            Model tm = new Model(tier);
            feed(t, tier.cap0, 0);
            tm.syncTanks(t);
            tick(t);
            tm.tick();
            String d = tm.diff(t);
            check(d == null && t.maxPower == tier.maxPower && t.flywheel_energy + t.lastPowerTarget == tier.maxPower,
                    "3d. " + tier.name + " at capacity: maxPower " + tier.maxPower + " and the same HE produced in one tick (got " + t.maxPower + ")" + (d == null ? "" : "; " + d));
        }
    }

    // ---- 4. lever -----------------------------------------------------------------------------------------------------

    static void lever() {
        MachineIndustrialTurbineBlockEntity t = fresh();
        for(int k = 1; k <= 4; k++) {
            Tier tier = TIERS[k % 4];
            feed(t, 123, 45);
            int dirty = t.dirty;
            t.onLeverPull();
            check(t.tanks[0].getTankType() == tier.in() && t.tanks[0].getMaxFill() == tier.cap0 && t.tanks[0].getFill() == 0
                            && t.tanks[1].getTankType() == tier.out() && t.tanks[1].getMaxFill() == tier.cap1 && t.tanks[1].getFill() == 0 && t.dirty == dirty + 1,
                    "lever " + k + ": -> " + tier.name + " " + tier.cap0 + " / " + tier.cap1 + " mB, fills cleared, marked for saving (TileEntityTurbineBase.java:109-125; got "
                            + t.tanks[0].getMaxFill() + " / " + t.tanks[1].getMaxFill() + ")");
        }
        // Another tank 0 type: STEAM / SPENTSTEAM without resizing (:121-123), also from a resized tier.
        t = fresh();
        t.tanks[0].setTankType(Fluids.WATER);
        t.tanks[0].setFill(500);
        t.tanks[1].setTankType(Fluids.NONE);
        t.onLeverPull();
        check(t.tanks[0].getTankType() == Fluids.STEAM && t.tanks[0].getMaxFill() == IN_CAP && t.tanks[0].getFill() == 0
                        && t.tanks[1].getTankType() == Fluids.SPENTSTEAM && t.tanks[1].getMaxFill() == OUT_CAP, "lever else branch: water -> steam / spent steam, sizes kept");
        t = fresh();
        t.onLeverPull();
        t.tanks[0].setTankType(Fluids.WATER);
        t.onLeverPull();
        check(t.tanks[0].getTankType() == Fluids.STEAM && t.tanks[0].getMaxFill() == 75_000 && t.tanks[1].getTankType() == Fluids.SPENTSTEAM
                        && t.tanks[1].getMaxFill() == 300_000, "lever else branch from a resized tier: types reset, 75,000 / 300,000 kept (no resize)");
    }

    // ---- 5. persistence -------------------------------------------------------------------------------------------------

    record State(int type0, int fill0, int max0, int type1, int fill1, int max1, long maxPower, long flywheel, double spin, long target, long buffer, boolean operational) {}

    static State state(MachineIndustrialTurbineBlockEntity t) {
        return new State(t.tanks[0].getTankType().getID(), t.tanks[0].getFill(), t.tanks[0].getMaxFill(), t.tanks[1].getTankType().getID(), t.tanks[1].getFill(),
                t.tanks[1].getMaxFill(), t.maxPower, t.flywheel_energy, t.spin, t.lastPowerTarget, t.powerBuffer, t.operational);
    }

    /** Deterministic writes for the continuation: on/off feed blocks and a periodic spent drain. */
    static void pattern(MachineIndustrialTurbineBlockEntity t, int n, Tier tier) {
        t.tanks[0].setFill((n / 40) % 2 == 0 ? tier.cap0 * 4 / 5 : 0);
        if(n % 25 == 0) t.tanks[1].setFill(0);
    }

    static void persistence() {
        MachineIndustrialTurbineBlockEntity t = fresh();
        for(int n = 0; n < 300; n++) {
            feed(t, IN_CAP, 0);
            tick(t);
        }
        feed(t, 12_345, 678);
        CompoundTag tag = new CompoundTag();
        t.saveAdditional(tag, null);
        check(tag.getInt("water") == 12_345 && tag.getInt("water_max") == IN_CAP && tag.getInt("water_type") == Fluids.STEAM.getID() && tag.getShort("water_p") == 0
                        && tag.getInt("steam") == 678 && tag.getInt("steam_max") == OUT_CAP && tag.getInt("steam_type") == Fluids.SPENTSTEAM.getID() && tag.getShort("steam_p") == 0
                        && tag.contains("power") && tag.getLong("power") == t.powerBuffer
                        && tag.contains("lastPowerTarget") && tag.getLong("lastPowerTarget") == t.lastPowerTarget
                        && tag.contains("flywheel_energy") && tag.getLong("flywheel_energy") == t.flywheel_energy && t.flywheel_energy > 0
                        && tag.contains("maxPower") && tag.getLong("maxPower") == 300_000L && tag.contains("spin") && tag.getDouble("spin") == t.spin,
                "5. saved keys: water*, steam* (TileEntityTurbineBase.java:157-159), power, lastPowerTarget, flywheel_energy, maxPower, spin (TileEntityMachineIndustrialTurbine.java:192-198)");
        check(!tag.contains("rotor") && !tag.contains("lastRotor") && !tag.contains("operational") && !tag.contains("audioDesync"),
                "5. saved keys: the rotor and the operational flag are not saved");
        MachineIndustrialTurbineBlockEntity loaded = turbine(level(), CORE, Direction.NORTH);
        loaded.loadAdditional(tag, null);
        State a = state(t), b = state(loaded);
        check(a.equals(new State(b.type0(), b.fill0(), b.max0(), b.type1(), b.fill1(), b.max1(), b.maxPower(), b.flywheel(), b.spin(), b.target(), b.buffer(), a.operational()))
                        && loaded.rotor == 0F, "5. reload restores both tanks, power, lastPowerTarget, flywheel_energy, maxPower and spin: " + b);

        // A resized tier survives the reload (the _max key).
        t = fresh();
        t.onLeverPull();
        t.tanks[0].setFill(12_345);
        tag = new CompoundTag();
        t.saveAdditional(tag, null);
        loaded = turbine(level(), CORE, Direction.NORTH);
        loaded.loadAdditional(tag, null);
        check(loaded.tanks[0].getTankType() == Fluids.HOTSTEAM && loaded.tanks[0].getMaxFill() == 75_000 && loaded.tanks[0].getFill() == 12_345
                        && loaded.tanks[1].getTankType() == Fluids.STEAM && loaded.tanks[1].getMaxFill() == 300_000,
                "5. a resized HOTSTEAM tier reloads as 75,000 / 300,000 mB into a fresh 750,000 / 3,000,000 turbine");

        // Continuation: saved after tick 200 and reloaded into a fresh turbine, it runs identically for 250 more ticks.
        for(Tier tier : new Tier[] {TIERS[0], TIERS[1]}) {
            MachineIndustrialTurbineBlockEntity original = fresh();
            if(tier != STEAM) original.onLeverPull();
            for(int n = 1; n <= 200; n++) {
                pattern(original, n, tier);
                tick(original);
            }
            CompoundTag saved = new CompoundTag();
            original.saveAdditional(saved, null);
            MachineIndustrialTurbineBlockEntity copy = turbine(level(), CORE, Direction.NORTH);
            copy.loadAdditional(saved, null);
            String mismatch = null;
            for(int n = 201; n <= 450 && mismatch == null; n++) {
                pattern(original, n, tier);
                pattern(copy, n, tier);
                tick(original);
                tick(copy);
                if(!state(original).equals(state(copy))) mismatch = "tick " + n + ": " + state(copy) + " != " + state(original);
            }
            check(mismatch == null && original.flywheel_energy >= 0, "5. " + tier.name + " saved after tick 200 continues identically to tick 450" + (mismatch == null ? "" : "; " + mismatch));
        }
    }

    // ---- 6. sync ------------------------------------------------------------------------------------------------------

    static void sync() {
        MachineIndustrialTurbineBlockEntity server = fresh();
        server.muffled = true;
        feed(server, 10_000, 0);
        int packs = server.packs;
        tick(server);
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        server.serialize(buf);
        List<Object> payload = buf.values();
        // 20 ops -> 4,000 HE; spin 4,000 / 0.5e8; target min(15,000, 4,000).
        List<Object> expected = List.of(true, false, 10_000, IN_CAP, Fluids.STEAM.getID(), (short) 0, 20, OUT_CAP, Fluids.SPENTSTEAM.getID(), (short) 0,
                4_000L, 4_000D / 0.5e8);
        check(payload.equals(expected), "6. payload: muffled, tilted, tank 0 before the ops, tank 1 after, powerBuffer, spin (TileEntityTurbineBase.java:61,89-90, "
                + "TileEntityMachineIndustrialTurbine.java:171-174) " + expected + " (got " + payload + ")");
        check(server.tanks[0].getFill() == 8_000 && server.packs == packs + 1 && server.packRange == 150,
                "6. the server already used 2,000 mB and synced once with range 150");
        Level clientLevel = level();
        clientLevel.isClientSide = true;
        MachineIndustrialTurbineBlockEntity client = turbine(clientLevel, CORE, Direction.NORTH);
        client.deserialize(buf);
        check(client.muffled && client.tanks[0].getFill() == 10_000 && client.tanks[0].getMaxFill() == IN_CAP && client.tanks[1].getFill() == 20
                        && client.tanks[1].getTankType() == Fluids.SPENTSTEAM && client.powerBuffer == 4_000L && client.spin == 4_000D / 0.5e8 && buf.readableBytes() == 0,
                "6. deserialize restores tanks, powerBuffer and spin and consumes the whole payload");

        ByteBuf previous = server.buf;
        feed(server, 0, 0);
        tick(server);
        check(previous.releases == 1 && server.buf != previous && server.packs == packs + 2, "6. each server tick releases the previous buffer and syncs once");
        // A resized tier carries its capacities; an invalid input still syncs tank 1 before it becomes NONE.
        server.tanks[0].setTankType(Fluids.WATER);
        server.tanks[0].setFill(77);
        tick(server);
        buf = new RegistryFriendlyByteBuf();
        server.serialize(buf);
        List<Object> invalid = buf.values();
        check(invalid.size() == 12 && invalid.get(2).equals(77) && invalid.get(4).equals(Fluids.WATER.getID()) && invalid.get(8).equals(Fluids.SPENTSTEAM.getID())
                        && server.tanks[1].getTankType() == Fluids.NONE, "6. invalid input: tank 1 is synced before it is set to NONE (got " + invalid + ")");
    }

    // ---- 7. dirty marking ---------------------------------------------------------------------------------------------

    static void dirty() {
        MachineIndustrialTurbineBlockEntity t = fresh();
        int d = t.dirty;
        feed(t, 100_000, 0);
        tick(t);
        check(t.dirty == d + 1, "7. op tick: marked once");
        d = t.dirty;
        feed(t, 0, 0);
        tick(t);
        check(t.lastPowerTarget > 0 && t.dirty == d + 1, "7. idle tick while the flywheel delivers power: marked once");
        int guard = 0;
        while(t.flywheel_energy > 0 && guard++ < 10_000) tick(t);
        d = t.dirty;
        double spin = t.spin;
        tick(t);
        check(spin > 0 && t.spin == 0D && t.lastPowerTarget == 0L && t.dirty == d + 1, "7. idle tick where only the spin changes (to 0): marked once");
        d = t.dirty;
        for(int n = 0; n < 20; n++) tick(t);
        check(t.dirty == d, "7. fully idle ticks are not marked");

        d = t.dirty;
        long rest = t.transferFluid(Fluids.STEAM, 0, 1_000);
        check(rest == 0 && t.tanks[0].getFill() == 1_000 && t.dirty == d + 1, "7. transferFluid that accepts fluid marks once");
        d = t.dirty;
        rest = t.transferFluid(Fluids.WATER, 0, 1_000);
        check(rest == 1_000 && t.dirty == d, "7. transferFluid of another type accepts nothing and does not mark");
        t.tanks[0].setFill(IN_CAP);
        d = t.dirty;
        rest = t.transferFluid(Fluids.STEAM, 0, 5);
        check(rest == 5 && t.dirty == d, "7. transferFluid into a full tank does not mark");
        t.tanks[1].setFill(50);
        d = t.dirty;
        t.useUpFluid(Fluids.SPENTSTEAM, 0, 10);
        check(t.tanks[1].getFill() == 40 && t.dirty == d + 1, "7. useUpFluid that removes fluid marks once");
        d = t.dirty;
        t.useUpFluid(Fluids.SPENTSTEAM, 0, 0);
        t.useUpFluid(Fluids.STEAM, 0, 10);
        t.tanks[1].setFill(0);
        t.useUpFluid(Fluids.SPENTSTEAM, 0, 10);
        check(t.dirty == d && t.tanks[0].getFill() == IN_CAP, "7. useUpFluid without effect (0 mB, a type it does not send, an empty tank) does not mark");
        d = t.dirty;
        t.onLeverPull();
        check(t.dirty == d + 1, "7. the lever marks once");
    }

    // ---- 8. client tick -----------------------------------------------------------------------------------------------

    static MachineIndustrialTurbineBlockEntity client(BlockPos pos) {
        reset();
        Level level = level();
        level.isClientSide = true;
        return turbine(level, pos, Direction.NORTH);
    }

    static Player player(BlockPos pos, double dx) {
        Player p = new Player();
        p.atX = pos.getX() + 0.5 + dx;
        p.atY = pos.getY() + 0.5;
        p.atZ = pos.getZ() + 0.5;
        return p;
    }

    static void client() {
        BlockPos at = new BlockPos(5, 64, 9);
        // Rotor (TileEntityMachineIndustrialTurbine.java:101-108) in float arithmetic, as the original.
        double[] spins = {0D, 0.005D, 0.25D, 0.499D, 0.5D, 2.0D};
        for(double s : spins) {
            MachineIndustrialTurbineBlockEntity t = client(at);
            t.spin = s;
            float rot = 0F, last = 0F;
            boolean same = true;
            for(int n = 0; n < 40; n++) {
                last = rot;
                float speed = s >= 0.5 ? 30 : (float) (Math.pow(s * 2, 0.5) * 30);
                rot += speed;
                if(rot >= 360) {
                    last -= 360;
                    rot -= 360;
                }
                tick(t);
                same &= t.rotor == rot && t.lastRotor == last;
            }
            check(same, "8. rotor at spin " + s + ": rotor and lastRotor follow the original float arithmetic for 40 ticks (got " + t.rotor + ", model " + rot + ")");
        }
        MachineIndustrialTurbineBlockEntity t = client(at);
        t.spin = 0.005D;
        tick(t);
        check(t.rotor == 3F, "8. rotor at spin 0.005: sqrt(0.01) * 30 = 3 degrees per tick");
        t = client(at);
        t.spin = 2.0D;
        for(int n = 0; n < 12; n++) tick(t);
        check(t.rotor == 0F && t.lastRotor == -30F, "8. rotor at full speed: 12 x 30 = 360 wraps to 0 and lastRotor to -30");

        // Audio (:110-130).
        t = client(at);
        float desync = Goal19BMachineAccess.desync(t);
        check(desync >= 0F && desync < 0.05F, "8. audio desync in [0, 0.05) (got " + desync + ")");
        NuclearTechMod.proxy.client = player(at, 35D);
        t.spin = 0.25D;
        tick(t);
        float spinNum = (float) Math.min(1F, 0.25D * 2);
        float volume = 0.25F + spinNum * 0.75F;
        float pitch = 0.5F + spinNum * 0.5F + desync;
        check(AudioWrapper.CREATED.size() == 1, "8. player exactly 35 blocks away: one loop created (got " + AudioWrapper.CREATED.size() + ")");
        AudioWrapper w = AudioWrapper.CREATED.get(0);
        check(w.event == NtmSoundEvents.TURBINE_LARGE_LOOP.get() && w.source == SoundSource.BLOCKS && w.be == null
                        && w.x == at.getX() + 0.5F && w.y == at.getY() + 0.5F && w.z == at.getZ() + 0.5F && w.range == 20F && w.keepAlive == 20
                        && w.volume == volume && w.pitch == pitch && w.started == 1,
                "8. the loop is TURBINE_LARGE_LOOP, BLOCKS, at the block centre, range 20, keepAlive 20, volume " + volume + ", pitch " + pitch);
        check(w.keptAlive == 1 && w.pitchUpdates == 1 && w.volumeUpdates == 1 && w.lastPitch == pitch && w.lastVolume == volume,
                "8. keepAlive, updatePitch and updateVolume on the first audible tick");
        for(int n = 0; n < 5; n++) tick(t);
        t.spin = 0.6D;
        tick(t);
        check(AudioWrapper.CREATED.size() == 1 && w.keptAlive == 7 && w.pitchUpdates == 7 && w.volumeUpdates == 7 && w.lastVolume == 1.0F && w.lastPitch == 1.0F + desync
                        && w.stopped == 0, "8. audible ticks keep the same loop alive; at spin >= 0.5 volume 1.0 and pitch 1.0 + desync");
        NuclearTechMod.proxy.client = player(at, 35.001D);
        tick(t);
        check(w.stopped == 1 && w.keptAlive == 7, "8. player just beyond 35 blocks: the loop stops");
        tick(t);
        check(AudioWrapper.CREATED.size() == 1 && w.stopped == 1, "8. and stays stopped without a new loop");
        NuclearTechMod.proxy.client = player(at, 10D);
        tick(t);
        check(AudioWrapper.CREATED.size() == 2 && AudioWrapper.CREATED.get(1).started == 1, "8. back within range a new loop starts");
        NuclearTechMod.proxy.client = null;
        tick(t);
        check(AudioWrapper.CREATED.get(1).stopped == 1 && AudioWrapper.CREATED.size() == 2, "8. no client player: the loop stops, none is created");
        NuclearTechMod.proxy.client = player(at, 0D);
        tick(t);
        t.spin = 0D;
        tick(t);
        tick(t);
        check(AudioWrapper.CREATED.size() == 3 && AudioWrapper.CREATED.get(2).stopped == 1, "8. spin 0 stops and clears the loop");
        t.muffled = true;
        t.spin = 0.25D;
        tick(t);
        check(AudioWrapper.CREATED.size() == 4 && AudioWrapper.CREATED.get(3).volume == volume * 0.1F, "8. muffled: volume getVolume = 10 %");
        t.setRemoved();
        check(AudioWrapper.CREATED.get(3).stopped == 1, "8. setRemoved stops the loop");
        t = client(at);
        NuclearTechMod.proxy.client = player(at, 0D);
        t.spin = 0.25D;
        tick(t);
        t.onChunkUnloaded();
        check(AudioWrapper.CREATED.size() == 1 && AudioWrapper.CREATED.get(0).stopped == 1, "8. onChunkUnloaded stops the loop");

        // The client tick only animates; a server turbine never creates audio.
        t = client(at);
        t.spin = 0.3D;
        t.flywheel_energy = 12_345L;
        t.powerBuffer = 678L;
        t.maxPower = 300_000L;
        feed(t, 4_321, 21);
        int packs = t.packs, dirty = t.dirty;
        for(int n = 0; n < 50; n++) tick(t);
        check(t.flywheel_energy == 12_345L && t.powerBuffer == 678L && t.maxPower == 300_000L && t.spin == 0.3D && t.tanks[0].getFill() == 4_321
                        && t.tanks[1].getFill() == 21 && t.packs == packs && t.dirty == dirty, "8. the client tick never changes tanks, flywheel or power");
        MachineIndustrialTurbineBlockEntity server = fresh();
        NuclearTechMod.proxy.client = player(CORE, 0D);
        for(int n = 0; n < 20; n++) {
            feed(server, IN_CAP, 0);
            tick(server);
        }
        check(AudioWrapper.CREATED.isEmpty() && server.rotor == 0F, "8. the server tick creates no audio and does not turn the rotor");
    }

    // ---- 9. ports and connections ------------------------------------------------------------------------------------

    static BlockPos rel(BlockPos c, Direction d, int nd, Direction r, int nr, int up) {
        return c.relative(d, nd).relative(r, nr).above(up);
    }

    /** Original getFluidPorts (:201-216): the port block and its facing; the connection is the neighbour in that facing. */
    static DirPos[] expectedFluid(BlockPos c, Direction d) {
        Direction r = originalRot(d);
        BlockPos[] ports = {rel(c, d, 3, r, 1, 0), rel(c, d, 3, r, -1, 0), rel(c, d, -1, r, 1, 0), rel(c, d, -1, r, -1, 0), rel(c, d, 3, r, 0, 2), rel(c, d, -1, r, 0, 2)};
        Direction[] faces = {r, r.getOpposite(), r, r.getOpposite(), Direction.UP, Direction.UP};
        DirPos[] result = new DirPos[6];
        for(int i = 0; i < 6; i++) result[i] = new DirPos(ports[i].relative(faces[i]), faces[i]);
        return result;
    }

    /** Original getPowerPorts (:219-226): core - 3 dir + 1 up facing dir.getOpposite(). */
    static DirPos expectedPower(BlockPos c, Direction d) {
        BlockPos port = rel(c, d, -3, originalRot(d), 0, 1);
        return new DirPos(port.relative(d.getOpposite()), d.getOpposite());
    }

    static boolean same(DirPos a, DirPos b) {
        return a.makeCompat().equals(b.makeCompat()) && a.getDir() == b.getDir();
    }

    static String show(DirPos[] p) {
        StringBuilder b = new StringBuilder("[");
        for(DirPos d : p) b.append(d.makeCompat()).append(' ').append(d.getDir()).append("; ");
        return b.append(']').toString();
    }

    record Rig(Level level, MachineIndustrialTurbineBlockEntity t, BarrelBlockEntity source, BarrelBlockEntity store, BatterySocketBlockEntity socket, Model model,
               long[] totals) {
        /** totals: ops, cumulative lastPowerTarget, discarded, socket gain. Returns the ops of this tick. */
        int tick() {
            level.time++;
            source.updateEntity();
            model.syncTanks(t);
            long before = socket.getPower();
            Goal19BMachineRegression.tick(t);
            int ops = model.tick();
            String d = model.diff(t);
            if(d != null) throw new AssertionError("rig turbine leaves the model at level tick " + level.time + ": " + d);
            store.updateEntity();
            socket.updateEntity();
            transfer(level);
            totals[0] += ops;
            totals[1] += t.lastPowerTarget;
            totals[2] += t.powerBuffer;
            totals[3] += socket.getPower() - before;
            return ops;
        }
    }

    static Rig rig(Direction facing, int levers, DirPos steam, DirPos spent, BlockPos powerStart, Direction powerOut, int sourceFill) {
        reset();
        Level level = level();
        MachineIndustrialTurbineBlockEntity t = turbine(level, CORE, facing);
        for(int i = 0; i < levers; i++) t.onLeverPull();
        Tier tier = TIERS[levers];
        pipe(level, steam.makeCompat(), tier.in());
        BarrelBlockEntity source = barrel(level, steam.makeCompat().relative(steam.getDir()), tier.in(), sourceFill, 2);
        pipe(level, spent.makeCompat(), tier.out());
        BarrelBlockEntity store = barrel(level, spent.makeCompat().relative(spent.getDir()), tier.out(), 0, 0);
        BatterySocketBlockEntity socket = powerPath(level, powerStart, powerOut);
        net(level);
        return new Rig(level, t, source, store, socket, new Model(tier), new long[4]);
    }

    static void ports() {
        Set<FluidType> coolable = new HashSet<>(Arrays.asList(Fluids.STEAM, Fluids.HOTSTEAM, Fluids.SUPERHOTSTEAM, Fluids.ULTRAHOTSTEAM, Fluids.SPENTSTEAM, Fluids.HOTOIL));
        FluidType[] types = {Fluids.STEAM, Fluids.HOTSTEAM, Fluids.SUPERHOTSTEAM, Fluids.ULTRAHOTSTEAM, Fluids.SPENTSTEAM, Fluids.HOTOIL, Fluids.WATER, Fluids.NONE, Fluids.OIL};
        for(Direction facing : HORIZONTALS) {
            reset();
            MachineIndustrialTurbineBlockEntity probe = turbine(level(), CORE, facing);
            DirPos[] con = probe.getConPos(), want = expectedFluid(CORE, facing);
            boolean shape = con.length == 6;
            for(int i = 0; i < 6 && shape; i++) shape = same(con[i], want[i]);
            check(shape, "9. " + facing + ": getConPos is the six original fluid ports' neighbours " + show(want) + " (got " + show(con) + ")");
            DirPos[] power = probe.getPowerPos();
            check(power.length == 1 && same(power[0], expectedPower(CORE, facing)),
                    "9. " + facing + ": getPowerPos is core - 4 dir + 1 up facing " + facing.getOpposite() + " (got " + show(power) + ")");
            boolean pc = true;
            for(Direction d : Direction.values()) pc &= probe.canConnect(d) == (d == facing.getOpposite());
            check(pc && !probe.canConnect((Direction) null), "9. " + facing + ": power canConnect only for " + facing.getOpposite() + " (:134-137)");
            boolean fc = true;
            String bad = null;
            for(FluidType type : types) {
                for(Direction d : Direction.values()) {
                    boolean expected = coolable.contains(type) && d != facing && d != facing.getOpposite();
                    if(probe.canConnect(type, d) != expected) {
                        fc = false;
                        if(bad == null) bad = "type " + type.getID() + " side " + d;
                    }
                }
            }
            check(fc, "9. " + facing + ": fluid canConnect only for FT_Coolable types or spent steam, never on " + facing + " or " + facing.getOpposite()
                    + " (:140-144)" + (bad == null ? "" : "; wrong for " + bad));

            // Real networks: steam in at one connection, spent steam out at the next, power through the red cable.
            DirPos pp = expectedPower(CORE, facing);
            for(int p = 0; p < 6; p++) {
                Rig rig = rig(facing, 0, want[p], want[(p + 1) % 6], pp.makeCompat(), pp.getDir(), 200_000);
                for(int n = 0; n < 40; n++) rig.tick();
                int used = 200_000 - rig.source.tank.getFill() - rig.t.tanks[0].getFill();
                int spentNow = rig.store.tank.getFill() + rig.t.tanks[1].getFill();
                String where = "9. " + facing + ", steam at connection " + p + ", spent at " + (p + 1) % 6;
                check(used > 0 && used == 100 * rig.totals[0] && spentNow == rig.totals[0] && rig.store.tank.getFill() > 0,
                        where + ": steam arrives through the duct and spent steam leaves through the other (" + used + " mB used, " + spentNow + " mB spent)");
                check(rig.totals[3] > 0 && rig.totals[3] == rig.socket.getPower() && rig.totals[1] == rig.totals[3] + rig.totals[2]
                                && 200L * rig.totals[0] == rig.t.flywheel_energy + rig.totals[1],
                        where + ": the socket behind the red cable got every HE the flywheel released that the net took (" + rig.socket.getPower() + " HE)");
            }
            // Mirrored (across the core along the facing axis) and one-off positions move nothing.
            Direction r = originalRot(facing);
            DirPos mirrorSteam = new DirPos(rel(CORE, facing, -3, r, 2, 0), r), mirrorSpent = new DirPos(rel(CORE, facing, 1, r, -2, 0), r.getOpposite());
            Rig mirrored = rig(facing, 0, mirrorSteam, mirrorSpent, rel(CORE, facing, 4, r, 0, 1), facing, 200_000);
            for(int n = 0; n < 40; n++) mirrored.tick();
            check(mirrored.source.tank.getFill() == 200_000 && mirrored.t.tanks[0].getFill() == 0 && mirrored.store.tank.getFill() == 0 && mirrored.socket.getPower() == 0,
                    "9. " + facing + ": ducts and cable at the mirrored positions connect to nothing");
            DirPos offSteam = new DirPos(want[0].makeCompat().relative(facing), want[0].getDir());
            DirPos offSpent = new DirPos(want[4].makeCompat().relative(facing.getOpposite()), Direction.UP);
            Rig off = rig(facing, 0, offSteam, offSpent, rel(CORE, facing, -3, r, 0, 1), facing.getOpposite(), 200_000);
            for(int n = 0; n < 40; n++) off.tick();
            check(off.source.tank.getFill() == 200_000 && off.t.tanks[0].getFill() == 0 && off.store.tank.getFill() == 0 && off.socket.getPower() == 0,
                    "9. " + facing + ": ducts and cable one block off the connections (and on the power port block itself) connect to nothing");
        }
    }

    // ---- 10. finite chain ---------------------------------------------------------------------------------------------

    static final BlockPos FIRE = new BlockPos(0, 0, 0);
    static final BlockPos BOILER = new BlockPos(0, 1, 0);
    // Facing north, rot east: P3's connection (core - dir + 2 rot) is (-8, 1, 0), P1's (core + 3 dir + 2 rot) is (-8, 1, -4),
    // the power connection (core - 4 dir + 1 up) is (-10, 2, 3).
    static final BlockPos TURBINE = new BlockPos(-10, 1, -1);
    static final BlockPos CONDENSER = new BlockPos(-8, 1, -6);
    static final int COAL = 2;
    static final int START_WATER = 2_000;
    static final int SAVE_AT = 1_000;

    static final class Chain {
        final Level level;
        HeaterFireboxBlockEntity fire;
        MachineHeatBoilerBlockEntity boiler;
        MachineIndustrialTurbineBlockEntity turbine;
        MachineCondenserBlockEntity condenser;
        BatterySocketBlockEntity socket;
        int pre0, pre1, post0, post1, ops, condensed;
        State after;
        long gain;
        // Heat ledger snapshots, each taken around one entity's own tick: the firebox (heat, burn time, burn heat, coal), the
        // boiler (the firebox heat it pulls from, its heat, water and steam), and the water the network moved from the
        // condenser into the boiler after every entity ticked.
        int fireHeat0, fireHeat1, burn0, burn1, burnHeat0, burnHeat1, maxBurn1, coal0, coal1;
        boolean wasOn;
        int source0, source1, heat0, heat1, water0, water1, steam0, steam1;
        int returned, waterIn;

        Chain(Level level) { this.level = level; }

        int coal() { return fire.slots.get(0).getCount() + fire.slots.get(1).getCount(); }

        void tick() {
            level.time++;
            fireHeat0 = fire.heatEnergy;
            burn0 = fire.burnTime;
            burnHeat0 = fire.burnHeat;
            coal0 = coal();
            fire.updateEntity();
            fireHeat1 = fire.heatEnergy;
            burn1 = fire.burnTime;
            burnHeat1 = fire.burnHeat;
            maxBurn1 = fire.maxBurnTime;
            coal1 = coal();
            wasOn = fire.wasOn;
            source0 = fire.heatEnergy;
            heat0 = boiler.heat;
            water0 = boiler.tanks[0].getFill();
            steam0 = boiler.tanks[1].getFill();
            boiler.updateEntity();
            source1 = fire.heatEnergy;
            heat1 = boiler.heat;
            water1 = boiler.tanks[0].getFill();
            steam1 = boiler.tanks[1].getFill();
            pre0 = turbine.tanks[0].getFill();
            pre1 = turbine.tanks[1].getFill();
            Goal19BMachineRegression.tick(turbine);
            post0 = turbine.tanks[0].getFill();
            post1 = turbine.tanks[1].getFill();
            after = state(turbine);
            ops = (pre0 - post0) / 100;
            int spent = condenser.tanks[0].getFill();
            condenser.updateEntity();
            condensed = spent - condenser.tanks[0].getFill();
            int condWater = condenser.tanks[1].getFill(), boilerWater = boiler.tanks[0].getFill();
            long before = socket.getPower();
            socket.updateEntity();
            transfer(level);
            gain = socket.getPower() - before;
            returned = condWater - condenser.tanks[1].getFill();
            waterIn = boiler.tanks[0].getFill() - boilerWater;
        }

        /** 1/100 mB of water: 100 x (water + spent steam) + steam over every tank in the loop. */
        long inventory() {
            return 100L * (boiler.tanks[0].getFill() + turbine.tanks[1].getFill() + condenser.tanks[0].getFill() + condenser.tanks[1].getFill())
                    + boiler.tanks[1].getFill() + turbine.tanks[0].getFill();
        }

        boolean finished() {
            return fire.slots.get(0).isEmpty() && fire.slots.get(1).isEmpty() && fire.burnTime <= 0 && fire.heatEnergy == 0 && boiler.heat == 0
                    && boiler.tanks[1].getFill() == 0 && turbine.tanks[0].getFill() < 496 && turbine.flywheel_energy == 0L && turbine.spin == 0D;
        }
    }

    static Chain chain(int coal, int water) {
        reset();
        Chain c = new Chain(level());
        Level level = c.level;
        c.fire = new HeaterFireboxBlockEntity(FIRE, new BlockState());
        level.put(c.fire);
        if(coal > 0) c.fire.slots.set(0, new ItemStack(Items.COAL, coal));
        c.boiler = new MachineHeatBoilerBlockEntity(BOILER, facing(level, BOILER, Direction.NORTH));
        level.put(c.boiler);
        c.boiler.tanks[0].setFill(water);
        pipe(level, new BlockPos(-2, 1, 0), Fluids.STEAM);
        line(level, Fluids.STEAM, new BlockPos(-3, 1, 0), Direction.WEST, 6);
        c.turbine = turbine(level, TURBINE, Direction.NORTH);
        line(level, Fluids.SPENTSTEAM, new BlockPos(-8, 1, -4), Direction.NORTH, 2);
        c.condenser = new MachineCondenserBlockEntity(CONDENSER, new BlockState());
        level.put(c.condenser);
        line(level, Fluids.WATER, new BlockPos(-7, 1, -6), Direction.EAST, 9);
        line(level, Fluids.WATER, new BlockPos(2, 1, -6), Direction.SOUTH, 7);
        cable(level, new BlockPos(-10, 2, 3));
        cable(level, new BlockPos(-10, 2, 4));
        c.socket = socket(level, new BlockPos(-10, 2, 5), Direction.NORTH);
        c.socket.updateEntity();
        net(level);
        return c;
    }

    record Snap(int fire, int burn, int coal0, int coal1, int heat, int water, int steam, State turbine, int condSpent, int condWater, int timer, long socket) {}

    static Snap snap(Chain c) {
        return new Snap(c.fire.heatEnergy, c.fire.burnTime, c.fire.slots.get(0).getCount(), c.fire.slots.get(1).getCount(), c.boiler.heat,
                c.boiler.tanks[0].getFill(), c.boiler.tanks[1].getFill(), state(c.turbine), c.condenser.tanks[0].getFill(), c.condenser.tanks[1].getFill(),
                c.condenser.waterTimer, c.socket.getPower());
    }

    static Map<String, Object> stocks(Chain c) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("coal", c.fire.slots.get(0).getCount() + c.fire.slots.get(1).getCount());
        m.put("water_mB", Map.of("boiler", c.boiler.tanks[0].getFill(), "condenser", c.condenser.tanks[1].getFill()));
        m.put("steam_mB", Map.of("boiler", c.boiler.tanks[1].getFill(), "turbine", c.turbine.tanks[0].getFill()));
        m.put("spent_steam_mB", Map.of("turbine", c.turbine.tanks[1].getFill(), "condenser", c.condenser.tanks[0].getFill()));
        m.put("socket_HE", c.socket.getPower());
        m.put("flywheel_HE", c.turbine.flywheel_energy);
        m.put("firebox_heat_TU", c.fire.heatEnergy);
        m.put("boiler_heat_TU", c.boiler.heat);
        return m;
    }

    // Firebox and heat boiler rules written out from the original (TileEntityHeaterFirebox.java:22-38, TileEntityFireboxBase.java:73-124,
    // ModuleBurnTime.java:84-96, TileEntityHeatBoiler.java:52-60,170-227, Fluids.java:626-630 at d31426c), never from the production
    // methods under test. Coal: 1,600 vanilla burn ticks x the 1.25 coal time mod x the 1.0 time mult; 100 base heat x the 2.0 coal heat mod.
    static final int FIRE_CAP = 100_000;
    static final int COAL_BURN = (int) ((int) (1_600 * 1.25D) * 1.0D);
    static final int COAL_HEAT = (int) (100 * 2.0D);
    static final int BOILER_CAP = 3_200_000;
    // Water's first heating step at BOILER efficiency 1.0: 200 TU and 1 mB of water -> 100 mB of steam; the steam tank is 16,000 x 100 mB.
    static final int HEAT_REQ = 200, WATER_REQ = 1, STEAM_PROD = 100, STEAM_CAP = 16_000 * 100;
    static final double HEAT_DIFFUSION = 0.1D;

    /** One firebox tick: offered = burnHeat on every burning tick, produced = the increase after the cap, capped = offered - produced. */
    record FireStep(boolean took, boolean burning, int offered, int produced, int capped, int decayed, int heat, int burnTime, int burnHeat, int coal) {}

    static FireStep fireStep(int heat, int burnTime, int burnHeat, int coal) {
        boolean took = burnTime <= 0 && coal > 0;
        boolean burning = took || burnTime > 0;
        if(took) {
            burnTime = COAL_BURN;
            burnHeat = COAL_HEAT;
            coal--;
        } else if(burning && heat < FIRE_CAP) {
            // Burn time only runs down below the cap (judged on the heat before this tick's burn), and never on the tick fuel is taken.
            burnTime--;
        }
        int offered = burning ? burnHeat : 0;
        int produced = burning ? Math.min(heat + offered, FIRE_CAP) - heat : 0;
        int decayed = burning ? 0 : heat - Math.max(heat - Math.max(heat / 1000, 1), 0);
        if(!burning) burnHeat = 0;
        return new FireStep(took, burning, offered, produced, offered - produced, decayed, heat + produced - decayed, burnTime, burnHeat, coal);
    }

    /** One boiler tick over a heat source: pull (or decay), then boil. capped is the clamp of heat loaded above the cap. */
    record BoilerStep(int moved, int capped, int decayed, int ops, int spent, int boiled, int made, int source, int heat, int water, int steam) {}

    static BoilerStep boilerStep(int source, int heat, int water, int steam) {
        int moved = 0, capped = 0, decayed = 0;
        int diff = source - heat;
        if(diff > 0) {
            // Rounded up: a 31 TU difference pulls 4 TU. Kept in the original's double arithmetic, which equals the integer
            // ceiling (diff + 9) / 10 for every difference up to 3,300,000.
            moved = Math.max(0, Math.min((int) Math.ceil(diff * HEAT_DIFFUSION), BOILER_CAP - heat));
            capped = Math.max(0, heat + moved - BOILER_CAP);
        } else if(diff < 0) {
            decayed = heat - Math.max(heat - Math.max(heat / 1000, 1), 0);
        }
        int pulled = heat + moved - capped - decayed;
        int ops = Math.max(0, Math.min(water / WATER_REQ, Math.min((STEAM_CAP - steam) / STEAM_PROD, pulled / HEAT_REQ)));
        return new BoilerStep(moved, capped, decayed, ops, HEAT_REQ * ops, WATER_REQ * ops, STEAM_PROD * ops, source - moved, pulled - HEAT_REQ * ops,
                water - WATER_REQ * ops, steam + STEAM_PROD * ops);
    }

    record WaterHeat(int heatReq, int req, int produced, boolean steam, double efficiency) {}

    static WaterHeat waterHeat() {
        FT_Heatable trait = Fluids.WATER.getTrait(FT_Heatable.class);
        FT_Heatable.HeatingStep step = trait.getFirstStep();
        return new WaterHeat(step.heatReq, step.amountReq, step.amountProduced, step.typeProduced == Fluids.STEAM, trait.getEfficiency(FT_Heatable.HeatingType.BOILER));
    }

    /** The cap and decay branches the finite chain may not reach, run in isolation against the same rules. */
    static List<String> heatBranches() {
        List<String> cases = new ArrayList<>();
        // Firebox: {heat, burnTime, burnHeat, coal, ticks}.
        int[][] fires = {{FIRE_CAP - 150, 10, COAL_HEAT, 0, 3}, {FIRE_CAP, 0, 0, 0, 1}, {500, 0, 0, 0, 1}, {0, 0, 0, 0, 1}, {FIRE_CAP - 50, 0, 0, 1, 2}};
        for(int[] row : fires) {
            reset();
            Level level = level();
            HeaterFireboxBlockEntity fire = new HeaterFireboxBlockEntity(FIRE, new BlockState());
            level.put(fire);
            fire.heatEnergy = row[0];
            fire.maxBurnTime = fire.burnTime = row[1];
            fire.burnHeat = row[2];
            if(row[3] > 0) fire.slots.set(0, new ItemStack(Items.COAL, row[3]));
            long capped = 0, decayed = 0;
            for(int n = 0; n < row[4]; n++) {
                FireStep want = fireStep(fire.heatEnergy, fire.burnTime, fire.burnHeat, fire.slots.get(0).getCount() + fire.slots.get(1).getCount());
                fire.updateEntity();
                check(fire.heatEnergy == want.heat() && fire.burnTime == want.burnTime() && fire.burnHeat == want.burnHeat() && fire.wasOn == want.burning(),
                        "10. firebox branch " + Arrays.toString(row) + " tick " + (n + 1) + ": heat " + fire.heatEnergy + ", burn " + fire.burnTime + " != rule " + want);
                capped += want.capped();
                decayed += want.decayed();
            }
            cases.add("firebox heat " + row[0] + ", burn " + row[1] + ", coal " + row[3] + ", " + row[4] + " ticks -> heat " + fire.heatEnergy + ", burn " + fire.burnTime
                    + ", capped " + capped + ", decayed " + decayed);
        }
        check(fireStep(FIRE_CAP - 150, 10, COAL_HEAT, 0).capped() == 50 && fireStep(FIRE_CAP, 10, COAL_HEAT, 0).burnTime() == 10
                        && fireStep(FIRE_CAP, 0, 0, 0).decayed() == 100 && fireStep(500, 0, 0, 0).decayed() == 1 && fireStep(0, 0, 0, 0).decayed() == 0,
                "10. firebox rule: 150 TU of room caps 50 of 200, burn time stalls at the cap, decay max(heat / 1000, 1) down to 0");
        // Boiler over a firebox, no water: {source, heat}. Colder source, equal, near the cap, loaded above the cap, 31 TU difference.
        int[][] boilers = {{1_000, 2_000}, {500, 500}, {3_300_000, BOILER_CAP - 10}, {3_400_000, 3_300_000}, {31, 0}};
        for(int[] row : boilers) {
            reset();
            Level level = level();
            HeaterFireboxBlockEntity fire = new HeaterFireboxBlockEntity(FIRE, new BlockState());
            level.put(fire);
            MachineHeatBoilerBlockEntity boiler = new MachineHeatBoilerBlockEntity(BOILER, facing(level, BOILER, Direction.NORTH));
            level.put(boiler);
            fire.heatEnergy = row[0];
            boiler.heat = row[1];
            BoilerStep want = boilerStep(row[0], row[1], 0, 0);
            boiler.updateEntity();
            check(fire.heatEnergy == want.source() && boiler.heat == want.heat() && boiler.heat - row[1] == want.moved() - want.decayed() - want.capped(),
                    "10. boiler branch source " + row[0] + ", heat " + row[1] + ": source " + fire.heatEnergy + ", heat " + boiler.heat + " != rule " + want);
            cases.add("boiler source " + row[0] + ", heat " + row[1] + " -> source " + fire.heatEnergy + ", heat " + boiler.heat + " (moved " + want.moved() + ", decayed "
                    + want.decayed() + ", capped " + want.capped() + ")");
        }
        check(boilerStep(1_000, 2_000, 0, 0).decayed() == 2 && boilerStep(500, 500, 0, 0).heat() == 500 && boilerStep(3_300_000, BOILER_CAP - 10, 0, 0).moved() == 10
                        && boilerStep(3_400_000, 3_300_000, 0, 0).capped() == 100_000 && boilerStep(31, 0, 0, 0).moved() == 4 && boilerStep(30, 0, 0, 0).moved() == 3,
                "10. boiler rule: a colder source decays max(heat / 1000, 1), equal heat holds, the pull stops at the cap, heat loaded above the cap is clamped, ceil(31 x 0.1) == 4");
        return cases;
    }

    static void finite() {
        Chain c = chain(COAL, START_WATER);
        Map<String, Object> start = stocks(c);
        long total = c.inventory();
        check(total == 100L * START_WATER, "10. the loop starts with 2,000 mB of water");
        // Bound: 2 coal x 2,000 burn ticks (1,600 x the firebox's 1.25 coal time) plus the firebox and boiler heat caps decaying
        // at >= 1 TU/t (100,000 each, the boiler never holds more than the firebox gave it) plus 10,000 ticks of slack.
        int bound = COAL * 2_000 + 2 * HeaterFireboxBlockEntity.maxHeatEnergy + 10_000;
        Model m = new Model(STEAM);
        long ops = 0, target = 0, discarded = 0, delivered = 0, steamUsed = 0, spentMade = 0, condensed = 0;
        int end = -1, fuelOut = -1;
        // Heat (TU) and fuel ledger: every term from the rules above applied to the pre-tick snapshot of the entity that ticks.
        int fireStart = c.fire.heatEnergy, boilerStart = c.boiler.heat, steamStart = c.boiler.tanks[1].getFill() + c.turbine.tanks[0].getFill();
        long offered = 0, produced = 0, cappedFire = 0, moved = 0, spentHeat = 0, decayedFire = 0, decayedBoiler = 0, cappedBoiler = 0, boiled = 0, made = 0;
        int items = 0, burning = 0, burnTicksPerItem = -1;
        check(fireStart == 0 && boilerStart == 0 && steamStart == 0, "10. the loop starts with no heat in the firebox or the boiler and no steam");
        List<int[]> perTick = new ArrayList<>();
        List<Snap> history = new ArrayList<>();
        CompoundTag[] saved = null;
        for(int n = 1; n <= bound; n++) {
            c.tick();
            m.fill0 = c.pre0;
            m.fill1 = c.pre1;
            int expectedOps = m.tick();
            // Compared as the turbine left its own tick, before the networks move fluid and power.
            State a = c.after;
            boolean same = a.maxPower() == m.maxPower && a.flywheel() == m.flywheel && a.spin() == m.spin && a.target() == m.lastPowerTarget
                    && a.buffer() == m.powerBuffer && a.operational() == m.operational && c.post0 == m.fill0 && c.post1 == m.fill1;
            if(!same) check(false, "10. tick " + n + ": the turbine leaves the model: " + a + " != model maxPower " + m.maxPower + " flywheel " + m.flywheel
                    + " spin " + m.spin + " target " + m.lastPowerTarget + " tanks " + m.fill0 + "/" + m.fill1);
            check(c.ops == expectedOps && c.pre0 - c.post0 == 100 * c.ops && c.post1 - c.pre1 == c.ops,
                    "10. tick " + n + ": ops from the pre-tick fill, 100 mB of steam -> 1 mB of spent steam each");
            ops += c.ops;
            steamUsed += 100L * c.ops;
            spentMade += c.ops;
            target += c.turbine.lastPowerTarget;
            discarded += c.turbine.powerBuffer;
            delivered += c.gain;
            condensed += c.condensed;
            check(c.inventory() == total, "10. tick " + n + ": (a) 100 x (water + spent steam) + steam stays " + total + " (got " + c.inventory() + ")");
            check(200L * ops == c.turbine.flywheel_energy + target, "10. tick " + n + ": (b) 200 x ops == flywheel + released HE");
            check(target == delivered + discarded && c.turbine.powerBuffer == 0L, "10. tick " + n + ": (c) released HE == socket gain + discarded, nothing discarded while the socket has room");
            check(steamUsed == 100L * ops && spentMade == ops && spentMade == c.turbine.tanks[1].getFill() + c.condenser.tanks[0].getFill() + condensed,
                    "10. tick " + n + ": (d) steam used 100 x ops, spent steam made == ops == turbine + condenser stock + condensed");

            FireStep f = fireStep(c.fireHeat0, c.burn0, c.burnHeat0, c.coal0);
            check(c.fireHeat1 == f.heat() && c.burn1 == f.burnTime() && c.burnHeat1 == f.burnHeat() && c.coal1 == f.coal() && c.wasOn == f.burning()
                            && (!f.took() || c.maxBurn1 == COAL_BURN),
                    "10. tick " + n + ": (e) firebox tick: heat " + c.fireHeat0 + " -> " + c.fireHeat1 + ", burn " + c.burn0 + " -> " + c.burn1 + ", coal " + c.coal0 + " -> " + c.coal1
                            + " != rule " + f);
            BoilerStep b = boilerStep(c.source0, c.heat0, c.water0, c.steam0);
            check(c.source1 == b.source() && c.heat1 == b.heat() && c.water1 == b.water() && c.steam1 == b.steam(),
                    "10. tick " + n + ": (f) boiler tick: source " + c.source0 + " -> " + c.source1 + ", heat " + c.heat0 + " -> " + c.heat1 + ", water " + c.water0 + " -> "
                            + c.water1 + ", steam " + c.steam0 + " -> " + c.steam1 + " != rule " + b);
            offered += f.offered();
            produced += f.produced();
            cappedFire += f.capped();
            decayedFire += f.decayed();
            moved += b.moved();
            cappedBoiler += b.capped();
            decayedBoiler += b.decayed();
            spentHeat += b.spent();
            boiled += b.boiled();
            made += b.made();
            if(f.took()) {
                items++;
                if(burnTicksPerItem < 0) burnTicksPerItem = c.maxBurn1;
            }
            if(f.burning()) burning++;
            // Whole-tick identities: each entity's heat changes only by its own terms, whichever order the entities tick in.
            check(c.fire.heatEnergy - c.fireHeat0 == f.produced() - b.moved() - f.decayed() && f.offered() == f.produced() + f.capped(),
                    "10. tick " + n + ": (g) firebox heat change == produced - moved to the boiler - decayed, offered == produced + capped");
            check(c.boiler.heat - c.heat0 == b.moved() - b.spent() - b.decayed() - b.capped() && b.spent() == HEAT_REQ * (b.boiled() / WATER_REQ)
                            && b.made() == b.boiled() * STEAM_PROD / WATER_REQ,
                    "10. tick " + n + ": (h) boiler heat change == moved - spent on water - decayed - capped, spent == 200 TU x mB boiled, steam == 100 x mB boiled");
            check(c.boiler.tanks[0].getFill() - c.water0 == c.returned - b.boiled() && c.waterIn == c.returned,
                    "10. tick " + n + ": (i) boiler water change == water the condenser returned (" + c.returned + " mB) - water boiled (" + b.boiled() + " mB)");
            check(c.fire.heatEnergy == fireStart + produced - moved - decayedFire && c.boiler.heat == boilerStart + moved - spentHeat - decayedBoiler - cappedBoiler
                            && offered == produced + cappedFire && offered == (long) COAL_HEAT * burning && spentHeat == HEAT_REQ * boiled,
                    "10. tick " + n + ": (j) running heat ledger: firebox and boiler stocks == start + inflows - outflows, offered == burning ticks x " + COAL_HEAT + " TU");
            check(made == steamUsed + c.boiler.tanks[1].getFill() + c.turbine.tanks[0].getFill() - steamStart
                            && c.boiler.tanks[0].getFill() + c.condenser.tanks[1].getFill() == START_WATER - boiled + condensed,
                    "10. tick " + n + ": (k) steam made == turbine steam used + steam in stock, water in stock == 2,000 - boiled + condensed");
            perTick.add(new int[] {c.ops, (int) c.gain});
            if(fuelOut < 0 && c.fire.slots.get(0).isEmpty() && c.fire.burnTime <= 0) fuelOut = n;
            if(n == SAVE_AT) saved = new CompoundTag[] {Goal19BMachineAccess.save(c.fire), Goal19BMachineAccess.save(c.boiler), Goal19BMachineAccess.save(c.turbine),
                    Goal19BMachineAccess.save(c.condenser), Goal19BMachineAccess.save(c.socket)};
            if(n > SAVE_AT) history.add(snap(c));
            if(c.finished()) {
                end = n;
                break;
            }
        }
        check(end > 0, "10. within the computed bound of " + bound + " ticks the fuel ran out, the boiler stopped, the turbine stopped and the flywheel reached 0");
        check(c.fire.slots.get(0).isEmpty() && c.fire.heatEnergy == 0 && c.boiler.heat == 0 && c.turbine.flywheel_energy == 0L && c.turbine.spin == 0D
                        && c.turbine.maxPower == 300_000L && c.turbine.tanks[0].getFill() < 496,
                "10. final: firebox empty, boiler heat decayed, flywheel and spin 0, maxPower held at 300,000, turbine steam below 496 mB");
        check(ops > 0 && delivered == 200L * ops && discarded == 0L, "10. final: HE delivered == 200 x ops exactly (" + ops + " ops, " + delivered + " HE)");
        check(steamUsed == 100L * ops && c.inventory() == total, "10. final: every mB of water is accounted for");
        int fireEnd = c.fire.heatEnergy, boilerEnd = c.boiler.heat;
        check(items == COAL && burnTicksPerItem == COAL_BURN && COAL_BURN == 2_000 && COAL_HEAT == 200,
                "10. final: " + items + " coal burned, " + burnTicksPerItem + " burn ticks each (1,600 x 1.25 x 1.0), " + COAL_HEAT + " TU per burning tick");
        // Each item burns on the tick it is taken plus one tick per burn-time step; burn time only stalls at the firebox cap.
        check(cappedFire > 0 ? burning >= items * (COAL_BURN + 1) : burning == items * (COAL_BURN + 1),
                "10. final: " + burning + " burning ticks for " + items + " items of " + COAL_BURN + " burn ticks (" + cappedFire + " TU capped)");
        check(offered == (long) COAL_HEAT * burning && offered == produced + cappedFire && produced == moved + decayedFire + fireEnd - fireStart
                        && moved == spentHeat + decayedBoiler + cappedBoiler + boilerEnd - boilerStart && spentHeat == HEAT_REQ * boiled && made == STEAM_PROD * boiled,
                "10. final: heat ledger offered " + offered + " == produced " + produced + " + capped " + cappedFire + "; produced == moved " + moved + " + decayed "
                        + decayedFire + " + end - start; moved == spent " + spentHeat + " + decayed " + decayedBoiler + " + capped " + cappedBoiler + " + end - start");
        check(cappedBoiler == 0 && fireEnd == 0 && boilerEnd == 0,
                "10. final: the boiler never pulls past its 3,200,000 TU cap from a 100,000 TU firebox; both heat stocks end at 0");
        check(boiled > 0 && made == steamUsed + c.boiler.tanks[1].getFill() + c.turbine.tanks[0].getFill() - steamStart
                        && c.boiler.tanks[0].getFill() + c.condenser.tanks[1].getFill() == START_WATER - boiled + condensed,
                "10. final: " + boiled + " mB of water boiled into " + made + " mB of steam, all used by the turbine or left in stock");
        WaterHeat wh = waterHeat();
        check(wh.heatReq() == HEAT_REQ && wh.req() == WATER_REQ && wh.produced() == STEAM_PROD && wh.steam() && wh.efficiency() == 1.0D,
                "10. Fluids.WATER FT_Heatable first step: " + wh + " (original Fluids.java:626-630: 200 TU + 1 mB -> 100 mB STEAM, BOILER 1.0)");
        int window = Math.min(1_000, fuelOut > 1 ? fuelOut - 1 : 0);
        long wOps = 0, wHe = 0;
        for(int i = fuelOut - 1 - window; i < fuelOut - 1 && i >= 0; i++) {
            wOps += perTick.get(i)[0];
            wHe += perTick.get(i)[1];
        }
        System.out.println("  info: finite chain: " + end + " ticks, " + ops + " turbine ops, " + delivered + " HE delivered, fuel out on tick " + fuelOut
                + "; residual steam boiler " + c.boiler.tanks[1].getFill() + " mB, turbine " + c.turbine.tanks[0].getFill() + " mB");

        // Reload every machine as saved after tick SAVE_AT and compare to the end (the client-only rotor is not compared).
        Chain r = chain(0, 0);
        Goal19BMachineAccess.load(r.fire, saved[0]);
        Goal19BMachineAccess.load(r.boiler, saved[1]);
        Goal19BMachineAccess.load(r.turbine, saved[2]);
        Goal19BMachineAccess.load(r.condenser, saved[3]);
        Goal19BMachineAccess.load(r.socket, saved[4]);
        r.level.time = SAVE_AT;
        String mismatch = null;
        for(int n = SAVE_AT + 1; n <= end && mismatch == null; n++) {
            r.tick();
            Snap got = snap(r), want = history.get(n - SAVE_AT - 1);
            if(!got.equals(want)) mismatch = "tick " + n + ": " + got + " != " + want;
        }
        check(mismatch == null, "10. the chain saved after tick " + SAVE_AT + " and reloaded continues identically to tick " + end + (mismatch == null ? "" : "; " + mismatch));

        // A full socket: the flywheel still drains by lastPowerTarget each tick and all of it is discarded.
        DirPos[] con = expectedFluid(CORE, Direction.NORTH);
        DirPos pp = expectedPower(CORE, Direction.NORTH);
        Rig full = rig(Direction.NORTH, 0, con[2], con[0], pp.makeCompat(), pp.getDir(), 400_000);
        ItemStack pack = full.socket.slots.get(0);
        PACK.chargeBattery(pack, PACK.getMaxCharge(pack));
        long capacity = full.socket.getPower();
        boolean allDiscarded = true;
        for(int n = 0; n < 60; n++) {
            long fly = full.t.flywheel_energy;
            int o = full.tick();
            allDiscarded &= full.t.powerBuffer == full.t.lastPowerTarget && full.t.flywheel_energy == fly + 200L * o - full.t.lastPowerTarget;
        }
        check(capacity == PACK.getMaxCharge(pack) && capacity > 0 && full.socket.getPower() == capacity && full.totals[1] > 0 && full.totals[2] == full.totals[1]
                        && full.totals[3] == 0 && allDiscarded,
                "10. full socket: the flywheel drains by lastPowerTarget every tick and all " + full.totals[1] + " HE are discarded");

        List<String> branches = heatBranches();

        Map<String, Object> ledger = new LinkedHashMap<>();
        ledger.put("scenario", "coal firebox (" + COAL + " coal) -> heat boiler (north) -> steam duct -> industrial turbine (north, core " + TURBINE
                + ", steam at P3, spent at P1) -> spent duct -> condenser -> water duct -> boiler; red cable from the power port -> lithium battery socket");
        ledger.put("start", start);
        ledger.put("end", stocks(c));
        Map<String, Object> totals = new LinkedHashMap<>();
        totals.put("ticks", end);
        totals.put("coal_burned", COAL - c.fire.slots.get(0).getCount() - c.fire.slots.get(1).getCount());
        totals.put("fuel_out_tick", fuelOut);
        totals.put("turbine_ops", ops);
        totals.put("steam_consumed_mB", steamUsed);
        totals.put("spent_produced_mB", spentMade);
        totals.put("water_condensed_mB", condensed);
        totals.put("he_into_flywheel", 200L * ops);
        totals.put("he_delivered", delivered);
        totals.put("he_discarded", discarded);
        ledger.put("totals", totals);
        ledger.put("residual_steam_mB", Map.of("boiler", c.boiler.tanks[1].getFill(), "turbine", c.turbine.tanks[0].getFill()));
        ledger.put("steady_state", Map.of("window", (fuelOut - 1 - window) + 1 + ".." + (fuelOut - 1), "ops_per_tick", window == 0 ? 0D : (double) wOps / window,
                "he_per_tick", window == 0 ? 0D : (double) wHe / window));
        ledger.put("reload", Map.of("saved_after_tick", SAVE_AT, "compared_ticks", end - SAVE_AT));
        ledger.put("socket_full", Map.of("ticks", 60, "he_released", full.totals[1], "he_discarded", full.totals[2], "he_delivered", full.totals[3]));
        ledger.put("flywheel_model", notes);
        ledger.put("original_anchors", List.of(
                "TileEntityMachineIndustrialTurbine.java:34-36,42 (750,000 / 3,000,000 mB, efficiency 1.0, flywheel 0.5e8)",
                "TileEntityMachineIndustrialTurbine.java:81-96 (generatePower, onServerTick)",
                "TileEntityTurbineBase.java:47-99 (ops, powerBuffer reset, sync order)",
                "Fluids.java:637 (STEAM FT_Coolable(SPENTSTEAM, 100, 1, 200), TURBINE 1.0)"));
        Map<String, Object> fuel = new LinkedHashMap<>();
        fuel.put("items", items);
        fuel.put("item_id", "minecraft:coal");
        fuel.put("burn_ticks_per_item", burnTicksPerItem);
        fuel.put("burning_ticks", burning);
        fuel.put("burn_heat_per_tick", COAL_HEAT);
        fuel.put("fuel_out_tick", fuelOut);
        ledger.put("fuel", fuel);
        Map<String, Object> heat = new LinkedHashMap<>();
        heat.put("burn_heat_offered", offered);
        heat.put("produced", produced);
        heat.put("capped_firebox", cappedFire);
        heat.put("moved_to_boiler", moved);
        heat.put("spent_on_water", spentHeat);
        heat.put("decayed_firebox", decayedFire);
        heat.put("decayed_boiler", decayedBoiler);
        heat.put("capped_boiler", cappedBoiler);
        heat.put("firebox_start", fireStart);
        heat.put("firebox_end", fireEnd);
        heat.put("boiler_start", boilerStart);
        heat.put("boiler_end", boilerEnd);
        ledger.put("heat_TU", heat);
        ledger.put("water_boiled_mB", boiled);
        ledger.put("steam_made_mB", made);
        ledger.put("heat_per_mB_water_TU", HEAT_REQ / WATER_REQ);
        ledger.put("steam_per_mB_water_mB", STEAM_PROD / WATER_REQ);
        ledger.put("heat_identities", List.of(
                "per tick (e): firebox post-tick heat, burn time, burn heat, coal == fireStep(pre-tick snapshot)",
                "per tick (f): boiler post-tick source heat, heat, water, steam == boilerStep(pre-tick snapshot)",
                "per tick (g): delta firebox heat == produced - moved_to_boiler - decayed_firebox; offered == produced + capped_firebox",
                "per tick (h): delta boiler heat == moved_to_boiler - spent_on_water - decayed_boiler - capped_boiler; spent == 200 x mB boiled; steam == 100 x mB boiled",
                "per tick (i): delta boiler water == water returned by the condenser through the duct - water boiled",
                "per tick (j, k) and final: running sums of the above, offered == burning ticks x burn heat, steam made == turbine steam used + steam stock",
                "final: produced == moved + decayed_firebox + firebox end - start; moved == spent + decayed_boiler + capped_boiler + boiler end - start; spent == 200 x water boiled"));
        ledger.put("heat_branches", branches);
        Map<String, Object> neo = new LinkedHashMap<>();
        neo.put("firebox constants (baseHeat 100, timeMult 1.0, maxHeatEnergy 100,000)", "src/main/java/com/hbm/blockentity/machine/heater/HeaterFireboxBlockEntity.java:20-22");
        neo.put("coal time mod 1.25, coal heat mod 2.0", "src/main/java/com/hbm/blockentity/machine/heater/HeaterFireboxBlockEntity.java:24-36");
        neo.put("burn time = (int) (getBurnTime(stack) x getTimeMult()), burnHeat = getBurnHeat(baseHeat, stack)", "src/main/java/com/hbm/blockentity/machine/heater/HeaterFireboxBlockEntity.java:91-112");
        neo.put("getBurnTime = (int) (vanilla burn x time mod), getBurnHeat = (int) (base x heat mod)", "src/main/java/com/hbm/module/ModuleBurnTime.java:40-53");
        neo.put("burnTime-- only while heatEnergy < getMaxHeat()", "src/main/java/com/hbm/blockentity/machine/heater/HeaterFireboxBlockEntity.java:113-118");
        neo.put("produced = min(heat + burnHeat, max) - heat; decayed = max(heat / 1000, 1) floored at 0", "src/main/java/com/hbm/blockentity/machine/heater/HeaterFireboxBlockEntity.java:120-125");
        neo.put("useUpHeat (moved_to_boiler leaves the firebox)", "src/main/java/com/hbm/blockentity/machine/heater/AbstractHeaterMachineBlockEntity.java:43-47");
        neo.put("DIFFUSION 0.1", "src/main/java/com/hbm/blockentity/machine/boiler/AbstractBoilerBlockEntity.java:32");
        neo.put("tryPullHeat: equal holds, pull ceil(diff x 0.1) clamped to the cap, cap clamp, decay max(heat / 1000, 1)", "src/main/java/com/hbm/blockentity/machine/boiler/AbstractBoilerBlockEntity.java:180-207");
        neo.put("tryConvert: heatReq = max(heatReq / BOILER eff, 1), ops = min(water, room / 100, heat / heatReq)", "src/main/java/com/hbm/blockentity/machine/boiler/AbstractBoilerBlockEntity.java:132-149");
        neo.put("steam tank = input capacity x amountProduced / amountReq", "src/main/java/com/hbm/blockentity/machine/boiler/AbstractBoilerBlockEntity.java:117-124");
        neo.put("heat boiler MAX_HEAT 3,200,000, tanks 16,000 / 1,600,000 mB", "src/main/java/com/hbm/blockentity/machine/boiler/MachineHeatBoilerBlockEntity.java:22,25");
        neo.put("FT_Heatable WATER addStep(200, 1, STEAM, 100), BOILER eff_steam_boil 1.0", "src/main/java/com/hbm/inventory/fluid/Fluids.java:600,603-604");
        neo.put("FT_Heatable.addStep(heat, req, type, prod) -> HeatingStep(req, heat, type, prod)", "src/main/java/com/hbm/inventory/fluid/trait/FT_Heatable.java:23-24,71-75");
        neo.put("FT_Coolable STEAM(SPENTSTEAM, 100, 1, 200), TURBINE 1.0", "src/main/java/com/hbm/inventory/fluid/Fluids.java:609,611");
        neo.put("FT_Coolable(coolsTo, amountReq, amountProduced, heatEnergy)", "src/main/java/com/hbm/inventory/fluid/trait/FT_Coolable.java:25-30");
        neo.put("condenser: spent steam -> water 1:1", "src/main/java/com/hbm/blockentity/machine/CondenserBaseBlockEntity.java:42-51");
        ledger.put("neo_anchors", neo);
        Map<String, Object> original = new LinkedHashMap<>();
        original.put("firebox constants (baseHeat 100, timeMult 1.0, maxHeatEnergy 100,000)", "src/main/java/com/hbm/tileentity/machine/TileEntityHeaterFirebox.java:22-24");
        original.put("coal time mod 1.25, coal heat mod 2.0", "src/main/java/com/hbm/tileentity/machine/TileEntityHeaterFirebox.java:26-38");
        original.put("burn time = (int) (getBurnTime(stack) x getTimeMult()), burnHeat = getBurnHeat(baseHeat, stack)", "src/main/java/com/hbm/tileentity/machine/TileEntityFireboxBase.java:73-105");
        original.put("getBurnTime = (int) (burn x time mod), getBurnHeat = (int) (base x heat mod)", "src/main/java/com/hbm/module/ModuleBurnTime.java:84-100");
        original.put("burnTime-- only while heatEnergy < getMaxHeat()", "src/main/java/com/hbm/tileentity/machine/TileEntityFireboxBase.java:106-112");
        original.put("produced = min(heat + burnHeat, max) - heat; decayed = max(heat / 1000, 1) floored at 0", "src/main/java/com/hbm/tileentity/machine/TileEntityFireboxBase.java:119-124");
        original.put("useUpHeat (moved_to_boiler leaves the firebox)", "src/main/java/com/hbm/tileentity/machine/TileEntityFireboxBase.java:231-233");
        original.put("maxHeat 3,200,000, diffusion 0.1", "src/main/java/com/hbm/tileentity/machine/TileEntityHeatBoiler.java:52-53");
        original.put("tanks 16,000 / 16,000 x 100 mB", "src/main/java/com/hbm/tileentity/machine/TileEntityHeatBoiler.java:59-60");
        original.put("tryPullHeat: equal holds, pull ceil(diff x 0.1) clamped to the cap, cap clamp, decay max(heat / 1000, 1)", "src/main/java/com/hbm/tileentity/machine/TileEntityHeatBoiler.java:170-193");
        original.put("tryConvert: heatReq = max(heatReq / BOILER eff, 1), ops = min(water, room / 100, heat / heatReq)", "src/main/java/com/hbm/tileentity/machine/TileEntityHeatBoiler.java:218-227");
        original.put("not modelled: post-impact sky heating (TomSaveData fire > 1e-5), absent in NEO", "src/main/java/com/hbm/tileentity/machine/TileEntityHeatBoiler.java:84-87");
        original.put("FT_Heatable WATER addStep(200, 1, STEAM, 100), BOILER eff_steam_boil 1.0", "src/main/java/com/hbm/inventory/fluid/Fluids.java:626,629-630");
        original.put("FT_Heatable.addStep(heat, req, type, prod) -> HeatingStep(req, heat, type, prod)", "src/main/java/com/hbm/inventory/fluid/trait/FT_Heatable.java:24-25");
        original.put("FT_Coolable STEAM(SPENTSTEAM, 100, 1, 200), TURBINE 1.0", "src/main/java/com/hbm/inventory/fluid/Fluids.java:637");
        original.put("FT_Coolable(coolsTo, amountReq, amountProduced, heatEnergy)", "src/main/java/com/hbm/inventory/fluid/trait/FT_Coolable.java:27");
        original.put("condenser: spent steam -> water 1:1", "src/main/java/com/hbm/tileentity/machine/TileEntityCondenser.java:73-83");
        // "original_anchors" (above) keeps the turbine list; the heat terms at d31426c go under their own key.
        ledger.put("original_heat_anchors", original);
        write("finite.json", json(ledger));
    }

    // ---- 11. high tiers (isolated) -----------------------------------------------------------------------------------

    static void tiers() {
        for(int k = 1; k <= 3; k++) {
            Tier tier = TIERS[k];
            // ops = min((int) min(ceil(fill * 0.2), fill), room / 10): 7 mB -> 2, 1 mB -> 1, 25 mB of room -> 2.
            int[][] rows = {{7, 0, 2}, {1, 0, 1}, {tier.cap0, tier.cap1 - 25, 2}, {tier.cap0, 0, (int) Math.ceil(tier.cap0 * CONSUMPTION)}};
            for(int[] row : rows) {
                MachineIndustrialTurbineBlockEntity t = fresh();
                for(int i = 0; i < k; i++) t.onLeverPull();
                feed(t, row[0], row[1]);
                tick(t);
                check(Model.ops(row[0], row[1], tier) == row[2] && t.tanks[0].getFill() == row[0] - row[2] && t.tanks[1].getFill() == row[1] + 10 * row[2]
                                && t.flywheel_energy + t.lastPowerTarget == (long) tier.heat * row[2] && t.maxPower == tier.maxPower,
                        "11. " + tier.name + ": " + row[0] + " mB in, " + row[1] + " mB out -> " + row[2] + " ops, 1 mB -> 10 mB, " + tier.heat + " HE per op, maxPower " + tier.maxPower);
            }
            DirPos[] con = expectedFluid(CORE, Direction.NORTH);
            DirPos pp = expectedPower(CORE, Direction.NORTH);
            int supply = tier.cap0 * 8;
            Rig rig = rig(Direction.NORTH, k, con[2], con[0], pp.makeCompat(), pp.getDir(), supply);
            for(int n = 0; n < 200; n++) rig.tick();
            int used = supply - rig.source.tank.getFill() - rig.t.tanks[0].getFill();
            int made = rig.store.tank.getFill() + rig.t.tanks[1].getFill();
            check(rig.totals[0] > 0 && used == rig.totals[0] && made == 10 * rig.totals[0] && rig.t.maxPower == tier.maxPower,
                    "11. " + tier.name + " through ducts: " + rig.totals[0] + " ops took " + used + " mB and made " + made + " mB of the lower tier");
            check(tier.heat * rig.totals[0] == rig.t.flywheel_energy + rig.totals[1] && rig.totals[1] == rig.totals[3] + rig.totals[2] && rig.totals[3] > 0,
                    "11. " + tier.name + ": " + tier.heat + " HE per op into the flywheel, released HE == socket gain + discarded (" + rig.totals[3] + " HE delivered)");
            System.out.println("  info: 11 " + tier.name + ": 200 ticks, " + rig.totals[0] + " ops, spin " + rig.t.spin + ", " + rig.totals[3] + " HE delivered");
        }
    }

    // ---- output -------------------------------------------------------------------------------------------------------

    static void write(String name, String text) {
        try {
            Files.writeString(out.resolve(name), text, StandardCharsets.UTF_8);
        } catch(java.io.IOException e) {
            throw new AssertionError("cannot write " + name + ": " + e);
        }
    }

    static String json(Object value) {
        if(value == null) return "null";
        if(value instanceof Map<?, ?> map) {
            StringBuilder b = new StringBuilder("{");
            boolean firstEntry = true;
            for(Map.Entry<?, ?> e : map.entrySet()) {
                if(!firstEntry) b.append(", ");
                firstEntry = false;
                b.append(json(String.valueOf(e.getKey()))).append(": ").append(json(e.getValue()));
            }
            return b.append('}').toString();
        }
        if(value instanceof List<?> list) {
            StringBuilder b = new StringBuilder("[");
            for(int i = 0; i < list.size(); i++) b.append(i == 0 ? "" : ", ").append(json(list.get(i)));
            return b.append(']').toString();
        }
        if(value instanceof Number || value instanceof Boolean) return String.valueOf(value);
        return "\"" + String.valueOf(value).replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    public static void main(String[] args) {
        out = Path.of(args[0]);
        Set<String> only = new HashSet<>(Arrays.asList((args.length > 1 ? args[1] : "constants,ops,flywheel,lever,persistence,sync,dirty,client,ports,finite,tiers").split(",")));
        Map<String, Runnable> sections = new LinkedHashMap<>();
        sections.put("constants", Goal19BMachineRegression::constants);
        sections.put("ops", Goal19BMachineRegression::ops);
        sections.put("flywheel", Goal19BMachineRegression::flywheel);
        sections.put("lever", Goal19BMachineRegression::lever);
        sections.put("persistence", Goal19BMachineRegression::persistence);
        sections.put("sync", Goal19BMachineRegression::sync);
        sections.put("dirty", Goal19BMachineRegression::dirty);
        sections.put("client", Goal19BMachineRegression::client);
        sections.put("ports", Goal19BMachineRegression::ports);
        sections.put("finite", Goal19BMachineRegression::finite);
        sections.put("tiers", Goal19BMachineRegression::tiers);
        int index = 0;
        for(Map.Entry<String, Runnable> e : sections.entrySet()) {
            index++;
            if(only.contains(e.getKey())) run(index + ". " + e.getKey(), e.getValue());
        }
        Objects.requireNonNull(out);
        System.out.println(checks + " assertions; " + scenarios + " independent scenarios; " + ticks + " executed ticks");
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
