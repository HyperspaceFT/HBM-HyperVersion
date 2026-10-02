package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import api.hbm.fluidmk2.IFluidUserMK2;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.boiler.MachineHeatBoilerBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.machine.storage.BatterySocketBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.BarrelBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Coolable;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import io.netty.buffer.ByteBuf;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.server.MinecraftServer;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.ArrayList;
import java.util.List;

public class Goal9BRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    private static final Direction[] HORIZONTALS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};

    // Original numbers, read from the 608fec4 sources and not from the NEO classes under test:
    // TileEntitySteamEngine.java:45-47 (steamCap 2,000, ldsCap 20, efficiency 0.85), Fluids.java:632-634
    // (STEAM: FT_Coolable(SPENTSTEAM, 100, 1, 200), TURBINE 1.0), TileEntityCondenser.java:31-32 (100 / 100).
    private static final int STEAM_CAP = 2_000;
    private static final int SPENT_CAP = 20;
    private static final int STEAM_PER_OP = 100;
    private static final int HEAT_PER_OP = 200;
    private static final long HE_PER_OP = 170; // 200 TU * TURBINE 1.0 * 0.85
    private static final int CONDENSER_TANK = 100;
    // The Goal 9A boiler: 16,000 mB water, 1,600,000 mB steam, 3,200,000 TU cap (checked by the Goal 9A suite).
    private static final int BOILER_WATER = 16_000;
    private static final int BOILER_STEAM = 1_600_000;
    private static final int BOILER_HEAT_CAP = 3_200_000;

    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());
    private static final BarrelBlock BIG = new BarrelBlock(10_000_000);

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

    /**
     * Runs one section; a failed assertion is printed with the section name and the next section still runs, so one
     * defect does not hide the state of the others. Any failure fails the whole run at the end.
     */
    private static void run(String name, Runnable body) {
        try {
            body.run();
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            // The failed check is not counted as passed.
            checks--;
            sectionChecks = 0;
            DummyableBlock.safeRem = false;
        }
    }

    /** Original ForgeDirection.getRotation(UP) (ROTATION_MATRIX row UP = {0, 1, 5, 4, 2, 3, 6}), written out independently. */
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
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        return level;
    }

    static void net(Level level) {
        // Two passes let links invalidated in the first pass rejoin, as in the Goal 3B/6/8 harnesses.
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    /** The networks move fluid and power once per tick, after every block entity has ticked. */
    static void transfer(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static BlockState facing(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        return state;
    }

    static MachineSteamEngineBlockEntity engine(Level level, BlockPos pos, Direction dir) {
        MachineSteamEngineBlockEntity engine = new MachineSteamEngineBlockEntity(pos, facing(level, pos, dir));
        level.put(engine);
        return engine;
    }

    static MachineCondenserBlockEntity condenser(Level level, BlockPos pos) {
        MachineCondenserBlockEntity condenser = new MachineCondenserBlockEntity(pos, new BlockState());
        level.put(condenser);
        return condenser;
    }

    static MachineHeatBoilerBlockEntity boiler(Level level, BlockPos pos, Direction dir) {
        MachineHeatBoilerBlockEntity boiler = new MachineHeatBoilerBlockEntity(pos, facing(level, pos, dir));
        level.put(boiler);
        return boiler;
    }

    static HeaterFireboxBlockEntity firebox(Level level, BlockPos pos) {
        HeaterFireboxBlockEntity fire = new HeaterFireboxBlockEntity(pos, new BlockState());
        level.put(fire);
        return fire;
    }

    static BarrelBlockEntity barrel(Level level, BlockPos pos, Block block, FluidType type, int fill, int mode) {
        BlockState state = new BlockState();
        state.block = block;
        level.states.put(pos, state);
        BarrelBlockEntity barrel = new BarrelBlockEntity(pos, state);
        level.put(barrel);
        barrel.tank.setTankType(type);
        barrel.tank.setFill(fill);
        barrel.mode = (short) mode;
        return barrel;
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    static CableBaseBlockEntity cable(Level level, BlockPos pos) {
        CableBaseBlockEntity wire = new CableBaseBlockEntity(pos, new BlockState());
        level.put(wire);
        wire.updateEntity();
        return wire;
    }

    /** A battery socket with its proxies and a lithium pack: it charges at 100,000 HE/t, above the engine's 3,400. */
    static BatterySocketBlockEntity socket(Level level, BlockPos pos, Direction facing) {
        BlockState state = facing(level, pos, facing);
        BatterySocketBlockEntity socket = new BatterySocketBlockEntity(pos, state);
        level.put(socket);
        BlockPos[] ports = socket.getPortPos();
        for(int i = 1; i < ports.length; i++) {
            // MachineBatterySocketBlock creates EXTRA parts as inventory/power/conductor proxies.
            ProxyComboBlockEntity proxy = new ProxyComboBlockEntity(ports[i], state).inventory().power().conductor();
            proxy.core = socket;
            level.states.put(ports[i], state);
            level.put(proxy);
        }
        socket.slots.set(0, MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_LITHIUM.ordinal()));
        return socket;
    }

    static void line(Level level, FluidType type, BlockPos from, Direction dir, int count) {
        for(int i = 0; i < count; i++) pipe(level, from.relative(dir, i), type);
    }

    // 1. Condenser ---------------------------------------------------------------------------------------------

    static void condenser() {
        reset();
        Level level = level();
        BlockPos at = new BlockPos(0, 10, 0);
        MachineCondenserBlockEntity c = condenser(level, at);
        check(c.tanks.length == 2 && c.tanks[0].getTankType() == Fluids.SPENTSTEAM && c.tanks[0].getMaxFill() == CONDENSER_TANK
                        && c.tanks[1].getTankType() == Fluids.WATER && c.tanks[1].getMaxFill() == CONDENSER_TANK,
                "the condenser holds 100 mB of spent steam and 100 mB of water");
        check(c.getReceivingTanks().length == 1 && c.getReceivingTanks()[0] == c.tanks[0] && c.getSendingTanks().length == 1 && c.getSendingTanks()[0] == c.tanks[1],
                "it receives into the spent steam tank and sends from the water tank");

        int[][] cases = {
                // spent, water -> spent, water: convert = min(spent, 100 - water), 1:1
                {50, 0, 0, 50},
                {100, 30, 30, 100},
                {7, 99, 6, 100},
                {100, 0, 0, 100},
                {0, 0, 0, 0},
                {100, 100, 100, 100},
        };
        for(int[] row : cases) {
            c.tanks[0].setFill(row[0]);
            c.tanks[1].setFill(row[1]);
            c.waterTimer = 0;
            int dirty = c.dirty;
            c.updateEntity();
            int converted = row[0] - row[2];
            check(c.tanks[0].getFill() == row[2] && c.tanks[1].getFill() == row[3],
                    "spent " + row[0] + ", water " + row[1] + ": converts min(spent, water room) = " + converted + " mB 1:1");
            check(c.waterTimer == (converted > 0 ? 20 : 0), "spent " + row[0] + ", water " + row[1] + ": waterTimer " + (converted > 0 ? 20 : 0));
            check(c.dirty - dirty == (converted > 0 ? 1 : 0), "spent " + row[0] + ", water " + row[1] + ": marked for saving only when something converted");
        }

        // waterTimer counts down every tick and is set back to 20 by a conversion in the same tick.
        c.tanks[0].setFill(10);
        c.tanks[1].setFill(0);
        c.updateEntity();
        List<Integer> timer = new ArrayList<>();
        for(int t = 0; t < 22; t++) {
            c.tanks[1].setFill(0);
            c.updateEntity();
            timer.add(c.waterTimer);
        }
        List<Integer> expected = new ArrayList<>();
        for(int t = 19; t >= 0; t--) expected.add(t);
        expected.add(0);
        expected.add(0);
        check(timer.equals(expected), "after a conversion waterTimer counts 19 .. 0 and stays at 0 (got " + timer + ")");
        for(int t = 0; t < 5; t++) c.updateEntity();
        c.tanks[0].setFill(1);
        c.updateEntity();
        check(c.waterTimer == 20, "a conversion during the count-down sets waterTimer back to 20");

        // NBT: the original's reversed keys.
        c.tanks[0].setFill(37);
        c.tanks[1].setFill(64);
        CompoundTag tag = new CompoundTag();
        c.saveAdditional(tag, null);
        check(tag.getInt("water") == 37 && tag.getInt("water_type") == Fluids.SPENTSTEAM.getID() && tag.getInt("water_max") == CONDENSER_TANK,
                "the spent steam tank is saved under \"water\" (original key, reversed)");
        check(tag.getInt("steam") == 64 && tag.getInt("steam_type") == Fluids.WATER.getID() && tag.getInt("steam_max") == CONDENSER_TANK,
                "the water tank is saved under \"steam\" (original key, reversed)");
        MachineCondenserBlockEntity loaded = condenser(level(), at);
        loaded.loadAdditional(tag, null);
        check(loaded.tanks[0].getTankType() == Fluids.SPENTSTEAM && loaded.tanks[0].getFill() == 37
                        && loaded.tanks[1].getTankType() == Fluids.WATER && loaded.tanks[1].getFill() == 64, "load restores both tanks from the reversed keys");

        c.waterTimer = 13;
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        c.serialize(buf);
        check(buf.values().equals(List.of(37, 100, Fluids.SPENTSTEAM.getID(), (short) 0, 64, 100, Fluids.WATER.getID(), (short) 0, (byte) 13)),
                "sync: spent steam tank, water tank, waterTimer (got " + buf.values() + ")");
        Level client = level();
        client.isClientSide = true;
        MachineCondenserBlockEntity copy = condenser(client, at);
        copy.deserialize(buf);
        check(copy.tanks[0].getFill() == 37 && copy.tanks[1].getFill() == 64 && copy.waterTimer == 13, "the client reads both tanks and waterTimer");

        // Real ducts on each face: spent steam in through face d, water out through the opposite face.
        for(Direction d : Direction.values()) {
            reset();
            Level world = level();
            MachineCondenserBlockEntity cond = condenser(world, at);
            BarrelBlockEntity source = barrel(world, at.relative(d, 2), NtmBlocks.BARREL_STEEL.get(), Fluids.SPENTSTEAM, 2_000, 2);
            pipe(world, at.relative(d), Fluids.SPENTSTEAM);
            pipe(world, at.relative(d.getOpposite()), Fluids.WATER);
            BarrelBlockEntity sink = barrel(world, at.relative(d.getOpposite(), 2), NtmBlocks.BARREL_STEEL.get(), Fluids.WATER, 0, 0);
            net(world);
            boolean kept = true;
            for(int t = 0; t < 10; t++) {
                world.time++;
                source.updateEntity();
                cond.updateEntity();
                sink.updateEntity();
                transfer(world);
                kept &= source.tank.getFill() + cond.tanks[0].getFill() + cond.tanks[1].getFill() + sink.tank.getFill() == 2_000;
            }
            check(kept, d + ": spent steam plus water stays 2,000 mB every tick");
            // Tick 1 brings 100 mB in; from tick 2 the condenser converts 100 mB a tick and the water net takes it out.
            check(source.tank.getFill() == 1_000 && cond.tanks[0].getFill() == 100 && cond.tanks[1].getFill() == 0 && sink.tank.getFill() == 900,
                    d + ": a duct on this face delivers 100 mB/t of spent steam and a duct on the opposite face takes 100 mB/t of water"
                            + " (source " + source.tank.getFill() + ", condenser " + cond.tanks[0].getFill() + "/" + cond.tanks[1].getFill() + ", sink " + sink.tank.getFill() + ")");
        }
        section("1. condenser");
    }

    // 2. Steam engine formula ----------------------------------------------------------------------------------

    static void formula() {
        reset();
        Level level = level();
        MachineSteamEngineBlockEntity e = engine(level, new BlockPos(0, 1, 0), Direction.NORTH);
        check(e.tanks[0].getTankType() == Fluids.STEAM && e.tanks[0].getMaxFill() == STEAM_CAP
                        && e.tanks[1].getTankType() == Fluids.SPENTSTEAM && e.tanks[1].getMaxFill() == SPENT_CAP,
                "the engine holds 2,000 mB of steam and 20 mB of spent steam");
        FT_Coolable trait = Fluids.STEAM.getTrait(FT_Coolable.class);
        check(trait != null && trait.coolsTo == Fluids.SPENTSTEAM && trait.amountReq == STEAM_PER_OP && trait.amountProduced == 1
                        && trait.heatEnergy == HEAT_PER_OP && trait.getEfficiency(FT_Coolable.CoolingType.TURBINE) == 1.0D,
                "production Fluids.java gives steam the original cooling trait: 100 mB -> 1 mB spent steam, 200 TU, TURBINE 1.0");

        int[][] cases = {
                // steam, spent -> steam, spent, HE: ops = min(steam / 100, (20 - spent) / 1), 170 HE per op
                {100, 0, 0, 1, 170},
                {2_000, 0, 0, 20, 3_400},
                {2_000, 15, 1_500, 20, 850},
                {2_000, 20, 2_000, 20, 0},
                {99, 0, 99, 0, 0},
                {250, 0, 50, 2, 340},
                {1_999, 0, 99, 19, 3_230},
                {0, 0, 0, 0, 0},
        };
        for(int[] row : cases) {
            e.tanks[0].setFill(row[0]);
            e.tanks[1].setFill(row[1]);
            e.updateEntity();
            check(e.tanks[0].getFill() == row[2] && e.tanks[1].getFill() == row[3] && e.powerBuffer == row[4],
                    "steam " + row[0] + ", spent " + row[1] + " -> steam " + row[2] + ", spent " + row[3] + ", " + row[4] + " HE"
                            + " (got " + e.tanks[0].getFill() + ", " + e.tanks[1].getFill() + ", " + e.powerBuffer + ")");
        }
        boolean exact = true;
        for(int ops = 0; ops <= 20; ops++) {
            e.tanks[0].setFill(ops * STEAM_PER_OP);
            e.tanks[1].setFill(0);
            e.updateEntity();
            exact &= e.powerBuffer == ops * HE_PER_OP && e.tanks[1].getFill() == ops;
        }
        check(exact, "for 0 .. 20 ops the engine makes exactly 170 HE and 1 mB of spent steam per 100 mB of steam (no rounding loss)");

        e.tanks[0].setFill(STEAM_CAP);
        e.tanks[1].setFill(0);
        e.updateEntity();
        int afterFirst = e.tanks[1].getFill();
        e.tanks[0].setFill(STEAM_CAP);
        e.updateEntity();
        check(afterFirst == SPENT_CAP && e.tanks[1].getFill() == SPENT_CAP && e.tanks[0].getFill() == STEAM_CAP && e.powerBuffer == 0,
                "without an outlet the first tick fills the 20 mB spent tank; the next one makes nothing");

        e.powerBuffer = 12_345;
        e.tanks[0].setFill(0);
        e.tanks[1].setFill(0);
        e.updateEntity();
        check(e.powerBuffer == 0, "powerBuffer is reset at the start of every tick (12,345 -> 0 without steam)");
        e.tanks[0].setFill(2_000);
        e.updateEntity();
        e.tanks[0].setFill(100);
        e.tanks[1].setFill(0);
        e.updateEntity();
        check(e.powerBuffer == HE_PER_OP, "undelivered power does not accumulate: 3,400 HE then one op gives 170, not 3,570");

        e.tanks[0].setTankType(Fluids.WATER);
        e.tanks[0].setFill(500);
        e.tanks[1].setTankType(Fluids.NONE);
        e.updateEntity();
        check(e.tanks[0].getTankType() == Fluids.STEAM && e.tanks[1].getTankType() == Fluids.SPENTSTEAM && e.powerBuffer == 0,
                "the tank types are forced back to steam and spent steam every tick");
        section("2. steam engine formula");
    }

    // 3. Rotor, sound, save and sync ---------------------------------------------------------------------------

    static void rotor() {
        reset();
        Level level = level();
        BlockPos at = new BlockPos(5, 7, 9);
        MachineSteamEngineBlockEntity e = engine(level, at, Direction.NORTH);
        Object operate = NtmSoundEvents.STEAM_ENGINE_OPERATE.get();

        // Model of TileEntitySteamEngine.java:106-119 in float arithmetic, as the original computes it.
        float acc = 0F, rot = 0F;
        int sounds = 0, dirtyWhileIdle = 0, dirtyWhileWorking = 0, workingTicks = 0;
        boolean accTracks = true, rotorTracks = true, soundTracks = true, soundShape = true, reached40 = false, held40 = true;
        String first = null;
        for(int t = 1; t <= 1_100; t++) {
            boolean working = t <= 600;
            e.tanks[0].setFill(working ? STEAM_CAP : 0);
            e.tanks[1].setFill(0);
            int before = level.sounds.size(), dirty = e.dirty;
            e.updateEntity();

            acc += working ? 0.1F : -0.1F;
            acc = acc < 0F ? 0F : (acc > 40F ? 40F : acc);
            rot += acc;
            boolean hit = false;
            if(rot >= 360D) {
                rot -= 360D;
                hit = true;
            }
            accTracks &= e.getAcceleration() == acc;
            rotorTracks &= e.rotor == rot;
            int added = level.sounds.size() - before;
            soundTracks &= added == (hit ? 1 : 0);
            if(hit && added == 1) {
                sounds++;
                Level.Sound s = level.sounds.get(before);
                soundShape &= s.player() == null && s.x() == at.getX() && s.y() == at.getY() && s.z() == at.getZ() && s.event() == operate
                        && s.source() == SoundSource.BLOCKS && s.volume() == 1.0F && s.pitch() == 0.5F + acc / 80F;
            }
            if(acc == 40F) reached40 = true;
            if(working && reached40) held40 &= e.getAcceleration() == 40F;
            if(working) {
                workingTicks++;
                dirtyWhileWorking += e.dirty - dirty;
            } else if(t > 1_050) {
                dirtyWhileIdle += e.dirty - dirty;
            }
            if(first == null && !(accTracks && rotorTracks && soundTracks && soundShape)) {
                first = "tick " + t + ": acceleration " + e.getAcceleration() + " (model " + acc + "), rotor " + e.rotor + " (model " + rot + "), sounds +" + added;
            }
        }
        check(accTracks, "acceleration +0.1 per working tick and -0.1 per idle tick, clamped to [0, 40]" + (first == null ? "" : "; " + first));
        check(reached40 && held40, "the acceleration reaches 40 and stays there while the engine works");
        check(e.getAcceleration() == 0F, "500 idle ticks bring the acceleration back to 0");
        check(rotorTracks, "rotor += acceleration every tick, minus 360 at each full turn" + (first == null ? "" : "; " + first));
        check(soundTracks && sounds > 0, "a sound plays exactly when the rotor reaches 360 degrees (" + sounds + " in 1,100 ticks)" + (first == null ? "" : "; " + first));
        check(soundShape, "the sound is block.steam_engine_operate at the block corner (x, y, z), BLOCKS, volume 1.0, pitch 0.5 + acceleration / 80");
        check(level.sounds.stream().anyMatch(s -> s.pitch() == 1.0F), "at full speed the pitch is 0.5 + 40 / 80 = 1.0");
        int quiet = level.sounds.size();
        for(int t = 0; t < 50; t++) e.updateEntity();
        check(level.sounds.size() == quiet && e.rotor == rot, "a stopped engine (acceleration 0) neither turns nor sounds");
        check(dirtyWhileWorking == workingTicks && dirtyWhileIdle == 0,
                "marked for saving on every working tick and not while idle at acceleration 0 (" + dirtyWhileWorking + "/" + workingTicks + ", idle " + dirtyWhileIdle + ")");

        reset();
        Level quietLevel = level();
        MachineSteamEngineBlockEntity muffled = engine(quietLevel, at, Direction.NORTH);
        muffled.muffled = true;
        for(int t = 0; t < 200 && quietLevel.sounds.isEmpty(); t++) {
            muffled.tanks[0].setFill(STEAM_CAP);
            muffled.tanks[1].setFill(0);
            muffled.updateEntity();
        }
        check(!quietLevel.sounds.isEmpty() && quietLevel.sounds.get(0).volume() == 0.1F, "a muffled engine plays at getVolume(1.0) = 0.1");

        // Save: powerBuffer, acceleration and the tanks under "s"/"w"; the rotor is not saved.
        reset();
        level = level();
        MachineSteamEngineBlockEntity saved = engine(level, at, Direction.NORTH);
        for(int t = 0; t < 37; t++) {
            saved.tanks[0].setFill(STEAM_CAP);
            saved.tanks[1].setFill(0);
            saved.updateEntity();
        }
        saved.tanks[0].setFill(1_234);
        saved.tanks[1].setFill(7);
        float savedAcc = saved.getAcceleration();
        CompoundTag tag = new CompoundTag();
        saved.saveAdditional(tag, null);
        check(tag.getLong("powerBuffer") == 3_400 && tag.getFloat("acceleration") == savedAcc && savedAcc > 3F,
                "save writes powerBuffer (3,400) and acceleration (" + savedAcc + ") under the original keys");
        check(tag.getInt("s") == 1_234 && tag.getInt("s_type") == Fluids.STEAM.getID() && tag.getInt("s_max") == STEAM_CAP
                        && tag.getInt("w") == 7 && tag.getInt("w_type") == Fluids.SPENTSTEAM.getID() && tag.getInt("w_max") == SPENT_CAP,
                "the steam tank is saved as \"s\", the spent steam tank as \"w\"");
        check(!tag.contains("rotor") && !tag.contains("syncRotor") && !tag.contains("lastRotor"), "the rotor angle is not saved");
        MachineSteamEngineBlockEntity reloaded = engine(level(), at, Direction.NORTH);
        reloaded.loadAdditional(tag, null);
        check(reloaded.powerBuffer == 3_400 && reloaded.getAcceleration() == savedAcc && reloaded.tanks[0].getFill() == 1_234
                        && reloaded.tanks[1].getFill() == 7 && reloaded.rotor == 0F && saved.rotor != 0F,
                "load restores powerBuffer, acceleration and both tanks; the rotor starts again at 0");

        // Sync: muffled, tilted, then the steam tank as it was before this tick's use, powerBuffer, rotor, spent tank.
        reset();
        level = level();
        MachineSteamEngineBlockEntity server = engine(level, at, Direction.NORTH);
        server.tanks[0].setFill(STEAM_CAP);
        server.tanks[1].setFill(0);
        server.updateEntity();
        ByteBuf previous = server.buf;
        server.tanks[0].setFill(STEAM_CAP);
        server.tanks[1].setFill(0);
        int packs = server.packs;
        server.updateEntity();
        check(previous.releases == 1 && server.buf != previous, "each server tick releases the previous tick's buffer and starts a new one");
        check(server.packs == packs + 1 && server.packRange == 150, "the engine syncs every server tick with range 150");
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        server.serialize(buf);
        float syncRotor = server.rotor;
        List<Object> payload = buf.values();
        check(payload.equals(List.of(false, false, STEAM_CAP, STEAM_CAP, Fluids.STEAM.getID(), (short) 0, 3_400L, syncRotor,
                        SPENT_CAP, SPENT_CAP, Fluids.SPENTSTEAM.getID(), (short) 0)),
                "payload: muffled, tilted, steam tank (2,000 mB, before this tick's use), powerBuffer, rotor, spent tank (got " + payload + ")");
        check(server.tanks[0].getFill() == 0 && server.tanks[1].getFill() == SPENT_CAP, "while the server engine itself has already used the steam");

        Level clientLevel = level();
        clientLevel.isClientSide = true;
        MachineSteamEngineBlockEntity client = engine(clientLevel, at, Direction.NORTH);
        client.rotor = 350F;
        client.deserialize(buf);
        check(client.tanks[0].getFill() == STEAM_CAP && client.powerBuffer == 3_400 && client.tanks[1].getFill() == SPENT_CAP && client.rotor == 350F,
                "the client reads both tanks and powerBuffer; the rotor is not set directly");
        List<Float> path = new ArrayList<>();
        List<Float> last = new ArrayList<>();
        for(int t = 0; t < 4; t++) {
            client.updateEntity();
            path.add(client.rotor);
            last.add(client.lastRotor);
        }
        // From 350 to the synced angle the short way round (forwards, through 360): thirds over three ticks.
        double target = 350D + wrap(syncRotor - 350D);
        check(target > 350D && Math.abs(path.get(0) - (350D + (target - 350D) / 3D)) < 1E-3 && Math.abs(path.get(1) - (350D + 2D * (target - 350D) / 3D)) < 1E-3
                        && Math.abs(path.get(2) - target) < 1E-3,
                "client interpolation: 3 steps from 350 towards the synced " + syncRotor + " through 360, not backwards (got " + path + ")");
        check(path.get(3) == syncRotor && last.get(0) == 350F && last.get(1).equals(path.get(0)) && last.get(3).equals(path.get(2)),
                "after the three steps the rotor is set to the synced angle; lastRotor trails by one tick");
        check(client.packs == 0 && client.tanks[0].getFill() == STEAM_CAP && client.powerBuffer == 3_400, "the client tick only animates");

        MachineSteamEngineBlockEntity plain = engine(clientLevel, new BlockPos(50, 7, 9), Direction.NORTH);
        RegistryFriendlyByteBuf straight = new RegistryFriendlyByteBuf();
        straight.writeBoolean(false);
        straight.writeBoolean(false);
        new FluidTank(Fluids.STEAM, STEAM_CAP).serialize(straight);
        straight.writeLong(0L);
        straight.writeFloat(90F);
        new FluidTank(Fluids.SPENTSTEAM, SPENT_CAP).serialize(straight);
        plain.deserialize(straight);
        List<Float> steps = new ArrayList<>();
        for(int t = 0; t < 4; t++) {
            plain.updateEntity();
            steps.add(plain.rotor);
        }
        check(steps.equals(List.of(30F, 60F, 90F, 90F)), "from 0 to a synced 90 degrees the client turns 30, 60, 90 and holds (got " + steps + ")");
        section("3. rotor, sound, save and sync");
    }

    /** Vanilla Mth.wrapDegrees(double) (Mth.java:275-283), for the expected client path. */
    static double wrap(double value) {
        double d = value % 360.0;
        if(d >= 180.0) d -= 360.0;
        if(d < -180.0) d += 360.0;
        return d;
    }

    // 4. Connections -------------------------------------------------------------------------------------------

    record Rig(Level level, MachineSteamEngineBlockEntity engine, BarrelBlockEntity source, BarrelBlockEntity store, BatterySocketBlockEntity socket) {
        void tick() {
            level.time++;
            source.updateEntity();
            engine.updateEntity();
            store.updateEntity();
            socket.updateEntity();
            transfer(level);
        }
    }

    /** Steam barrel -> duct at steamPort, duct at spentPort -> store, cable at powerPort up and out to a socket; lines leave along out. */
    static Rig rig(Direction facing, BlockPos steamPort, BlockPos spentPort, BlockPos powerPort, Direction out) {
        reset();
        Level level = level();
        MachineSteamEngineBlockEntity engine = engine(level, new BlockPos(0, 1, 0), facing);
        pipe(level, steamPort, Fluids.STEAM);
        BarrelBlockEntity source = barrel(level, steamPort.relative(out), BIG, Fluids.STEAM, 100_000, 2);
        pipe(level, spentPort, Fluids.SPENTSTEAM);
        BarrelBlockEntity store = barrel(level, spentPort.relative(out), NtmBlocks.BARREL_STEEL.get(), Fluids.SPENTSTEAM, 0, 0);
        cable(level, powerPort);
        cable(level, powerPort.above());
        cable(level, powerPort.above(2));
        cable(level, powerPort.above(2).relative(out));
        BatterySocketBlockEntity socket = socket(level, powerPort.above(2).relative(out, 2), out.getOpposite());
        socket.updateEntity();
        net(level);
        return new Rig(level, engine, source, store, socket);
    }

    static void connections() {
        for(Direction facing : HORIZONTALS) {
            BlockPos core = new BlockPos(0, 1, 0);
            Direction rot = originalRot(facing);
            BlockPos p0 = core.relative(rot, 2).above();
            BlockPos[] ports = {p0, p0.relative(facing), p0.relative(facing.getOpposite())};

            reset();
            MachineSteamEngineBlockEntity probe = engine(level(), core, facing);
            DirPos[] con = probe.getConPos();
            boolean shape = con.length == 3 && MachineSteamEngineBlockEntity.getPortSide(facing) == rot;
            for(int i = 0; i < 3 && shape; i++) shape = con[i].makeCompat().equals(ports[i]) && con[i].getDir() == rot;
            check(shape, facing + ": three connections at y+1, core + rot*2 and +-facing, all facing rot = " + rot + " (the clockwise side)");

            for(int p = 0; p < 3; p++) {
                BlockPos steamPort = ports[p], spentPort = ports[(p + 1) % 3], powerPort = ports[(p + 2) % 3];
                Rig rig = rig(facing, steamPort, spentPort, powerPort, rot);
                boolean full = true;
                for(int t = 1; t <= 40; t++) {
                    long stored = rig.socket.getPower();
                    rig.tick();
                    if(t > 5) full &= rig.socket.getPower() - stored == 20 * HE_PER_OP;
                }
                int used = 100_000 - rig.source.tank.getFill() - rig.engine.tanks[0].getFill();
                int spent = rig.store.tank.getFill() + rig.engine.tanks[1].getFill();
                String where = facing + ", steam/spent/power at connections " + p + "/" + (p + 1) % 3 + "/" + (p + 2) % 3;
                check(used > 0 && used % STEAM_PER_OP == 0 && spent == used / STEAM_PER_OP,
                        where + ": steam arrives through the duct and 1 mB of spent steam per 100 mB leaves through the other (" + used + " mB used, " + spent + " mB spent)");
                check(rig.socket.getPower() == used / STEAM_PER_OP * HE_PER_OP,
                        where + ": the battery socket behind the red cable holds 170 HE per 100 mB (" + rig.socket.getPower() + " HE)");
                check(full, where + ": at full speed 3,400 HE/t reach the socket");
            }

            // The mirrored (counter-clockwise) positions are not connections.
            Direction mirror = rot.getOpposite();
            BlockPos q0 = core.relative(mirror, 2).above();
            Rig mirrored = rig(facing, q0, q0.relative(facing), q0.relative(facing.getOpposite()), mirror);
            for(int t = 0; t < 40; t++) mirrored.tick();
            check(mirrored.source.tank.getFill() == 100_000 && mirrored.engine.tanks[0].getFill() == 0 && mirrored.store.tank.getFill() == 0
                            && mirrored.socket.getPower() == 0,
                    facing + ": ducts and cables at the mirrored positions on the " + mirror + " side connect to nothing");
        }

        MachineSteamEngineBlockEntity e = engine(level(), new BlockPos(0, 1, 0), Direction.NORTH);
        boolean sides = true;
        for(Direction d : HORIZONTALS) sides &= e.canConnect(d);
        check(sides && !e.canConnect(Direction.UP) && !e.canConnect(Direction.DOWN) && !e.canConnect((Direction) null),
                "power connects on the four sides only, not up, down or null");
        check(e.canConnect(Fluids.STEAM, Direction.UP) && e.canConnect(Fluids.SPENTSTEAM, Direction.DOWN), "fluids keep the default rule (any side)");
        section("4. connections");
    }

    // 5. Anvil -------------------------------------------------------------------------------------------------

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

    /**
     * Goal 10B corrects seven Goal 8 entries in place (migration/GOAL10B.md D1 and D6): the soldering station takes 4
     * tungsten bolts instead of 1 (original AnvilRecipes.java:387), and the titanium and steel flat stamps make their own
     * plate/wire/circuit stamps instead of each other's (original :592-598). Every other entry must stay identical.
     */
    static String goal10b(String before) {
        if(before.contains("-> 1 hbmsntm:machine_soldering_station @") && before.endsWith(" CONSTRUCTION"))
            return before.replace("item hbmsntm:bolt x1 ", "item hbmsntm:bolt x4 ");
        if(before.startsWith("item hbmsntm:stamp_titanium_flat x1 ")) return before.replace("hbmsntm:stamp_steel_", "hbmsntm:stamp_titanium_");
        if(before.startsWith("item hbmsntm:stamp_steel_flat x1 ")) return before.replace("hbmsntm:stamp_titanium_", "hbmsntm:stamp_steel_");
        return before;
    }

    /**
     * Goal 10C (migration/GOAL10C.md) appends three heating oven entries after the steam engine (original
     * AnvilRecipes.java:269-274 and :672-678): construction with Minecraft copper, with NEO copper, and the recycling.
     * They are required exactly, in this order, after the Goal 9A/9B entries; the Goal 10C suite checks them in detail.
     */
    static final String[] GOAL10C = {
            "item hbmsntm:ingot_firebrick x16 meta " + MetaHelper.WILDCARD_VALUE + "; tag plates/steel x4; item minecraft:copper_ingot x8 meta "
                    + MetaHelper.WILDCARD_VALUE + "; -> 1 hbmsntm:heater_oven @1.0; tier 2--1 CONSTRUCTION",
            "item hbmsntm:ingot_firebrick x16 meta " + MetaHelper.WILDCARD_VALUE + "; tag plates/steel x4; item hbmsntm:ingot_copper x8 meta "
                    + MetaHelper.WILDCARD_VALUE + "; -> 1 hbmsntm:heater_oven @1.0; tier 2--1 CONSTRUCTION",
            "item hbmsntm:heater_oven x1 meta " + MetaHelper.WILDCARD_VALUE + "; -> 16 hbmsntm:ingot_firebrick @1.0; 8 hbmsntm:ingot_copper @1.0; tier 2--1 RECYCLING",
    };

    static void anvil() {
        List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
        List<?> before = goal9b.head.AnvilRecipes.getConstruction();
        int n = before.size();
        check(all.size() == n + 2 + GOAL10C.length, "the live list is the Goal 8 list plus two entries, then the three Goal 10C entries ("
                + n + " -> " + all.size() + ")");
        boolean goal10c = true;
        for(int k = 0; k < GOAL10C.length; k++) goal10c &= describe(all.get(n + 2 + k)).equals(GOAL10C[k]);
        check(goal10c, "exactly the three Goal 10C heating oven entries follow the steam engine, in order");
        int same = 0, corrected = 0;
        String first = null;
        for(int i = 0; i < n; i++) {
            String expected = goal10b(describe(before.get(i)));
            if(!expected.equals(describe(before.get(i)))) corrected++;
            if(describe(all.get(i)).equals(expected)) same++;
            else if(first == null) first = i + ": " + describe(all.get(i)) + " != " + expected;
        }
        check(same == n && corrected == 7, "every Goal 8 entry is unchanged in content and index, except the seven Goal 10B corrections ("
                + corrected + " corrected)" + (first == null ? "" : "; first difference " + first));
        AnvilConstructionRecipe boiler = all.get(n), engine = all.get(n + 1);
        check(boiler.output.size() == 1 && boiler.output.get(0).stack.is(NtmBlocks.HEAT_BOILER.asItem()) && boiler.getOverlay() == OverlayType.CONSTRUCTION,
                "the Goal 9A boiler entry directly follows the Goal 8 list");
        Item engineItem = NtmBlocks.MACHINE_STEAM_ENGINE.asItem();
        check(AnvilRecipes.getConstruction(n + 1) == engine && engine.output.size() == 1 && engine.output.get(0).stack.is(engineItem),
                "the steam engine entry directly follows the boiler");

        Item gear = NtmItems.GEAR_LARGE.get();
        Item stone = NtmBlocks.REINFORCED_STONE.asItem();
        List<AStack> in = engine.input;
        check(in.size() == 5
                        && in.get(0) instanceof ComparableStack s && s.item == stone && s.stacksize == 16
                        && in.get(1) instanceof TagStack plates && plates.tag == NtmTags.Items.PLATES_STEEL && plates.stacksize == 12
                        && in.get(2) instanceof ComparableStack shell && shell.item == NtmItems.SHELL_STEEL.get() && shell.stacksize == 2
                        && in.get(3) instanceof ComparableStack coil && coil.item == NtmItems.COIL_COPPER.get() && coil.stacksize == 4
                        && in.get(4) instanceof ComparableStack g && g.item == gear && g.stacksize == 1 && g.meta == 0,
                "inputs (original AnvilRecipes.java:351-358): 16 dense stone, 12 steel plates (tag), 2 steel shells, 4 copper coils, 1 large gear of meta 0");
        ItemStack out = engine.output.get(0).stack;
        check(out.getCount() == 1 && engine.output.get(0).chance == 1F && MetaHelper.getMeta(out) == 0 && !out.has(com.hbm.items.component.NtmDataComponents.META.get()),
                "output: one plain steam engine");
        check(engine.tierLower == 2 && engine.tierUpper == -1 && engine.isTierValid(2) && engine.isTierValid(3) && !engine.isTierValid(1)
                        && engine.getOverlay() == OverlayType.CONSTRUCTION, "anvil tier 2 and up, construction overlay");

        NtmItems.PLATE_STEEL.get().tags.add((String) NtmTags.Items.PLATES_STEEL);
        ItemStack[] set = {new ItemStack(stone, 16), new ItemStack(NtmItems.PLATE_STEEL.get(), 12), new ItemStack(NtmItems.SHELL_STEEL.get(), 2),
                new ItemStack(NtmItems.COIL_COPPER.get(), 4), new ItemStack(gear, 1)};
        check(accepts(engine, set), "the exact set with a plain large gear is accepted");
        ItemStack[] meta0 = set.clone();
        meta0[4] = MetaHelper.newStack(gear, 1, 0);
        check(accepts(engine, meta0), "a large gear written with META 0 is accepted");
        ItemStack[] meta1 = set.clone();
        meta1[4] = MetaHelper.newStack(gear, 1, 1);
        check(!accepts(engine, meta1), "a large gear with META 1 does not satisfy the gear input");
        int[] counts = {16, 12, 2, 4};
        boolean shortRejected = true;
        for(int i = 0; i < counts.length; i++) {
            ItemStack[] fewer = set.clone();
            fewer[i] = new ItemStack(set[i].getItem(), counts[i] - 1);
            shortRejected &= !accepts(engine, fewer);
        }
        check(shortRejected, "15 dense stone, 11 plates, 1 shell or 3 coils are not enough");
        boolean recycling = false;
        for(AnvilConstructionRecipe r : all) {
            for(AStack input : r.input) recycling |= input instanceof ComparableStack cs && cs.item == engineItem;
        }
        check(!recycling, "no anvil entry takes the steam engine (the original has no recycling entry)");
        section("5. anvil");
    }

    // 6. Closed chain ------------------------------------------------------------------------------------------

    enum Layout { CLOSED, CONDENSER_REMOVED, OUTLET_BLOCKED }

    static final BlockPos FIRE = new BlockPos(0, 0, 0);
    static final BlockPos BOILER = new BlockPos(0, 1, 0);
    static final BlockPos ENGINE = new BlockPos(-10, 0, 0);
    static final BlockPos CONDENSER = new BlockPos(-8, 1, -6);
    static final BlockPos SOCKET = new BlockPos(-8, 1, 3);
    static final BlockPos WATER_BARREL = new BlockPos(3, 1, -6);

    /**
     * Coal firebox under a boiler facing north (ports at x+-2 by Goal 9A); steam duct from the boiler's west port to the
     * engine (facing north, connections at x = -8: steam z 0, spent steam z -1, power z +1); spent steam duct north to
     * the condenser; water duct from the condenser east and south into the boiler's east port; red cable to a socket.
     */
    static final class Cycle {
        final Level level;
        HeaterFireboxBlockEntity fire;
        MachineHeatBoilerBlockEntity boiler;
        MachineSteamEngineBlockEntity engine;
        MachineCondenserBlockEntity condenser;
        BarrelBlockEntity water;
        BatterySocketBlockEntity socket;
        PipeBaseBlockEntity sampleDuct;

        Cycle(Level level) {
            this.level = level;
        }

        /** The engine's ops this tick, from its steam use (nothing flows into it during its own tick). */
        int tick() {
            level.time++;
            fire.updateEntity();
            boiler.updateEntity();
            if(boiler.hasExploded) return -1;
            int steam = engine.tanks[0].getFill();
            engine.updateEntity();
            int ops = (steam - engine.tanks[0].getFill()) / STEAM_PER_OP;
            if(condenser != null) condenser.updateEntity();
            if(water != null) water.updateEntity();
            socket.updateEntity();
            transfer(level);
            return ops;
        }

        /** Water-equivalent fluid in every tank in 1/100 mB of water: 100 x (water + spent steam) + steam. */
        long inventory() {
            long total = 100L * (boiler.tanks[0].getFill() + engine.tanks[1].getFill()) + boiler.tanks[1].getFill() + engine.tanks[0].getFill();
            if(condenser != null) total += 100L * (condenser.tanks[0].getFill() + condenser.tanks[1].getFill());
            if(water != null) total += 100L * water.tank.getFill();
            return total;
        }
    }

    static Cycle cycle(Layout layout, int boilerWater, int barrelWater) {
        reset();
        Cycle c = new Cycle(level());
        Level level = c.level;
        c.fire = firebox(level, FIRE);
        c.fire.slots.set(0, new ItemStack(Items.COAL, 64));
        c.boiler = boiler(level, BOILER, Direction.NORTH);
        c.boiler.tanks[0].setFill(boilerWater);
        c.sampleDuct = pipe(level, new BlockPos(-2, 1, 0), Fluids.STEAM);
        line(level, Fluids.STEAM, new BlockPos(-3, 1, 0), Direction.WEST, 6);
        c.engine = engine(level, ENGINE, Direction.NORTH);
        line(level, Fluids.SPENTSTEAM, new BlockPos(-8, 1, -1), Direction.NORTH, 5);
        cable(level, new BlockPos(-8, 1, 1));
        cable(level, new BlockPos(-8, 1, 2));
        c.socket = socket(level, SOCKET, Direction.NORTH);
        if(layout != Layout.CONDENSER_REMOVED) c.condenser = condenser(level, CONDENSER);
        if(layout == Layout.CLOSED) line(level, Fluids.WATER, new BlockPos(-7, 1, -6), Direction.EAST, 9);
        line(level, Fluids.WATER, new BlockPos(2, 1, -6), Direction.SOUTH, 7);
        if(layout != Layout.CLOSED) c.water = barrel(level, WATER_BARREL, NtmBlocks.BARREL_STEEL.get(), Fluids.WATER, barrelWater, 2);
        c.socket.updateEntity();
        net(level);
        return c;
    }

    record Snapshot(int fire, int heat, int water, int steam, int engineSteam, int engineSpent, float acceleration,
                    int condenserSpent, int condenserWater, int waterTimer, long socket) {}

    static Snapshot snap(Cycle c) {
        return new Snapshot(c.fire.heatEnergy, c.boiler.heat, c.boiler.tanks[0].getFill(), c.boiler.tanks[1].getFill(), c.engine.tanks[0].getFill(),
                c.engine.tanks[1].getFill(), c.engine.getAcceleration(), c.condenser.tanks[0].getFill(), c.condenser.tanks[1].getFill(),
                c.condenser.waterTimer, c.socket.getPower());
    }

    static void chain() {
        Cycle c = cycle(Layout.CLOSED, 2_000, 0);
        check(!(c.sampleDuct instanceof IFluidUserMK2), "ducts have no tank (not IFluidUserMK2): the networks hold no fluid between ticks");
        long total = c.inventory();
        check(total == 200_000L, "the loop starts with 2,000 mB of water in the boiler");
        long delivered = 0, totalOps = 0;
        int steady = 0;
        List<Snapshot> history = new ArrayList<>();
        CompoundTag[] saved = null;
        for(int t = 1; t <= 1_200; t++) {
            long stored = c.socket.getPower();
            int ops = c.tick();
            long gain = c.socket.getPower() - stored;
            check(c.inventory() == total, "tick " + t + ": 100 x (water + spent steam) + steam over all six tanks stays " + total + " (got " + c.inventory() + ")");
            delivered += gain;
            totalOps += ops;
            if(t > 1_000 && ops == 1 && gain == HE_PER_OP) steady++;
            if(t == 600) saved = new CompoundTag[] {Goal9BAccess.save(c.fire), Goal9BAccess.save(c.boiler), Goal9BAccess.save(c.engine),
                    Goal9BAccess.save(c.condenser), Goal9BAccess.save(c.socket)};
            if(t > 600) history.add(snap(c));
        }
        check(totalOps > 0 && delivered == totalOps * HE_PER_OP, "every op's 170 HE reached the socket: " + totalOps + " ops, " + delivered + " HE");
        check(steady == 200, "the last 200 ticks run steady: one op and 170 HE into the socket every tick (" + steady + " of 200)");
        check(!c.boiler.hasExploded && c.engine.tanks[1].getFill() <= SPENT_CAP, "the closed loop never jams");
        System.out.println("  info: closed loop, 1,200 ticks: " + totalOps + " engine ops, " + delivered + " HE delivered; steady 170 HE/t; boiler water "
                + c.boiler.tanks[0].getFill() + " mB, steam " + c.boiler.tanks[1].getFill() + " mB");

        // Reload every machine as saved after tick 600 and compare ticks 601 .. 1,200.
        Cycle r = cycle(Layout.CLOSED, 0, 0);
        Goal9BAccess.load(r.fire, saved[0]);
        Goal9BAccess.load(r.boiler, saved[1]);
        Goal9BAccess.load(r.engine, saved[2]);
        Goal9BAccess.load(r.condenser, saved[3]);
        Goal9BAccess.load(r.socket, saved[4]);
        r.level.time = 600;
        String mismatch = null;
        for(int t = 601; t <= 1_200 && mismatch == null; t++) {
            r.tick();
            Snapshot got = snap(r), want = history.get(t - 601);
            if(!got.equals(want)) mismatch = "tick " + t + ": " + got + " != " + want;
        }
        check(mismatch == null, "the loop saved after tick 600 and reloaded continues identically to tick 1,200" + (mismatch == null ? "" : "; " + mismatch));
        section("6. chain");
    }

    // 7. Failure chain and condenser capacity ------------------------------------------------------------------

    /**
     * Independent model of the jammed loop, written from the formulas: coal firebox +200 TU/t (checked against the live
     * firebox below), the boiler's pull ceil(diff * 0.1) and decay, ops = min(water, steam room / 100, heat / 200), the
     * explosion on a tick without ops and without 100 mB of steam room; the engine's ops = min(steam / 100, spent room);
     * the condenser's 1:1 conversion into a blocked 100 mB water tank; then the networks after every block entity:
     * barrel water into the boiler, boiler steam into the engine, spent steam into the condenser.
     * Returns {explosion tick, engine ops, boiler steam at the explosion}.
     */
    static int[] predictJam(boolean condenser, int boilerWater, int barrelWater) {
        int maxFire = HeaterFireboxBlockEntity.maxHeatEnergy;
        int fire = 0, heat = 0, water = boilerWater, steam = 0, barrel = barrelWater;
        int engineSteam = 0, engineSpent = 0, condSpent = 0, condWater = 0, engineOps = 0;
        for(int t = 1; t <= 200_000; t++) {
            fire = Math.min(fire + 200, maxFire);
            int diff = fire - heat;
            if(diff > 0) {
                int pull = Math.max(0, Math.min((int) Math.ceil(diff * 0.1), BOILER_HEAT_CAP - heat));
                fire -= pull;
                heat += pull;
            } else if(diff < 0) {
                heat = Math.max(heat - Math.max(heat / 1000, 1), 0);
            }
            int room = (BOILER_STEAM - steam) / 100;
            int ops = Math.min(water, Math.min(room, heat / HEAT_PER_OP));
            if(ops > 0) {
                water -= ops;
                steam += 100 * ops;
                heat -= HEAT_PER_OP * ops;
            } else if(room == 0) {
                return new int[] {t, engineOps, steam};
            }
            int engine = Math.min(engineSteam / STEAM_PER_OP, SPENT_CAP - engineSpent);
            engineSteam -= STEAM_PER_OP * engine;
            engineSpent += engine;
            engineOps += engine;
            if(condenser) {
                int convert = Math.min(condSpent, CONDENSER_TANK - condWater);
                condSpent -= convert;
                condWater += convert;
            }
            int refill = Math.min(barrel, BOILER_WATER - water);
            barrel -= refill;
            water += refill;
            int feed = Math.min(steam, STEAM_CAP - engineSteam);
            steam -= feed;
            engineSteam += feed;
            if(condenser) {
                int drain = Math.min(engineSpent, CONDENSER_TANK - condSpent);
                engineSpent -= drain;
                condSpent += drain;
            }
        }
        return new int[] {-1, engineOps, steam};
    }

    static void failure() {
        for(Layout layout : new Layout[] {Layout.CONDENSER_REMOVED, Layout.OUTLET_BLOCKED}) {
            boolean blocked = layout == Layout.OUTLET_BLOCKED;
            int[] model = predictJam(blocked, BOILER_WATER, 16_000);
            // Removed: the engine's 20 mB; blocked: also the condenser's 100 mB of water and then 100 mB of spent steam.
            int expectedOps = blocked ? SPENT_CAP + 2 * CONDENSER_TANK : SPENT_CAP;
            check(model[0] > 16_000 && model[1] == expectedOps && model[2] == BOILER_STEAM,
                    layout + ": the model predicts " + expectedOps + " engine ops and an explosion at 1,600,000 mB of steam (tick " + model[0] + ", " + model[1] + " ops)");

            Cycle c = cycle(layout, BOILER_WATER, 16_000);
            int exploded = -1, ops = 0, lastOp = 0, f = 0;
            boolean fireTracks = true;
            for(int t = 1; t <= model[0] + 5 && exploded < 0; t++) {
                c.level.time++;
                c.fire.updateEntity();
                f = Math.min(f + 200, HeaterFireboxBlockEntity.maxHeatEnergy);
                fireTracks &= c.fire.heatEnergy == f;
                c.boiler.updateEntity();
                f = c.fire.heatEnergy;
                if(c.boiler.hasExploded) {
                    exploded = t;
                    break;
                }
                int steam = c.engine.tanks[0].getFill();
                c.engine.updateEntity();
                int done = (steam - c.engine.tanks[0].getFill()) / STEAM_PER_OP;
                ops += done;
                if(done > 0) lastOp = t;
                if(c.condenser != null) c.condenser.updateEntity();
                c.water.updateEntity();
                c.socket.updateEntity();
                transfer(c.level);
            }
            check(fireTracks, layout + ": the coal firebox adds 200 TU every tick up to its cap, as the model assumes");
            check(ops == expectedOps && c.engine.tanks[1].getFill() == SPENT_CAP && c.engine.tanks[0].getFill() == STEAM_CAP,
                    layout + ": the engine stops after " + expectedOps + " ops with a full 20 mB spent tank and 2,000 mB of steam (got " + ops + " ops, last on tick " + lastOp + ")");
            if(blocked) {
                check(c.condenser.tanks[0].getFill() == CONDENSER_TANK && c.condenser.tanks[1].getFill() == CONDENSER_TANK,
                        layout + ": the condenser fills its water tank, then its spent steam tank");
            }
            check(exploded == model[0], layout + ": the boiler explodes on the predicted tick " + model[0] + " (got " + exploded + ")");
            check(c.boiler.tanks[1].getFill() == BOILER_STEAM && c.level.vnts.size() == 1,
                    layout + ": it explodes with exactly 1,600,000 mB of steam, once");
            System.out.println("  info: " + layout + ": engine stopped after " + ops + " ops (tick " + lastOp + "); boiler exploded on tick " + exploded
                    + " (predicted " + model[0] + ")");
        }

        // One condenser against five and six full-speed engines fed from a large steam barrel.
        for(int engines = 5; engines <= 6; engines++) {
            reset();
            Level level = level();
            MachineSteamEngineBlockEntity[] row = new MachineSteamEngineBlockEntity[engines];
            for(int i = 0; i < engines; i++) {
                // Facing north: steam at (2, 1, 4i - 1), spent steam at (2, 1, 4i + 1).
                row[i] = engine(level, new BlockPos(0, 0, 4 * i), Direction.NORTH);
                pipe(level, new BlockPos(2, 1, 4 * i - 1), Fluids.STEAM);
                pipe(level, new BlockPos(2, 1, 4 * i + 1), Fluids.SPENTSTEAM);
            }
            line(level, Fluids.STEAM, new BlockPos(3, 1, -1), Direction.SOUTH, 4 * engines - 1);
            line(level, Fluids.SPENTSTEAM, new BlockPos(2, 2, 0), Direction.SOUTH, 4 * engines - 1);
            BarrelBlockEntity source = barrel(level, new BlockPos(4, 1, -1), BIG, Fluids.STEAM, 1_000_000, 2);
            MachineCondenserBlockEntity cond = condenser(level, new BlockPos(2, 3, 0));
            pipe(level, new BlockPos(2, 4, 0), Fluids.WATER);
            BarrelBlockEntity sink = barrel(level, new BlockPos(2, 5, 0), BIG, Fluids.WATER, 0, 0);
            net(level);
            boolean fullSpeed = true, congested = true, saturated = true;
            long totalOps = 0;
            for(int t = 1; t <= 40; t++) {
                level.time++;
                source.updateEntity();
                int tickOps = 0;
                boolean each = true;
                for(MachineSteamEngineBlockEntity e : row) {
                    e.updateEntity();
                    tickOps += (int) (e.powerBuffer / HE_PER_OP);
                    each &= e.powerBuffer == 20 * HE_PER_OP;
                }
                cond.updateEntity();
                sink.updateEntity();
                transfer(level);
                totalOps += tickOps;
                if(t >= 3) {
                    fullSpeed &= each;
                    congested &= tickOps <= CONDENSER_TANK && tickOps < 20 * engines;
                    saturated &= cond.throughput == CONDENSER_TANK;
                }
            }
            if(engines == 5) {
                check(fullSpeed, "one condenser keeps five engines at 20 ops and 3,400 HE/t each from tick 3");
                check(saturated && sink.tank.getFill() == 100 * 38, "the condenser turns 100 mB/t of spent steam into water (" + sink.tank.getFill() + " mB in 40 ticks)");
            } else {
                check(congested, "six engines exceed it: from tick 3 at most 100 ops a tick in total, below 120");
                check(saturated, "the condenser stays at its 100 mB/t");
            }
            int spentNow = cond.tanks[0].getFill() + cond.tanks[1].getFill() + sink.tank.getFill();
            for(MachineSteamEngineBlockEntity e : row) spentNow += e.tanks[1].getFill();
            check(spentNow == totalOps, engines + " engines: every op's 1 mB of spent steam is in an engine, the condenser or the water barrel");
            System.out.println("  info: " + engines + " engines on one condenser: " + totalOps + " ops in 40 ticks");
        }
        section("7. failure chain and condenser capacity");
    }

    public static void main(String[] args) {
        run("1. condenser", Goal9BRegression::condenser);
        run("2. steam engine formula", Goal9BRegression::formula);
        run("3. rotor, sound, save and sync", Goal9BRegression::rotor);
        run("4. connections", Goal9BRegression::connections);
        run("5. anvil", Goal9BRegression::anvil);
        run("6. chain", Goal9BRegression::chain);
        run("7. failure chain and condenser capacity", Goal9BRegression::failure);
        System.out.println("Goal 9B checks: " + checks + " passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
