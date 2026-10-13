package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.tile.IHeatSource;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.blockentity.machine.storage.BatterySocketBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.entity.projectile.Goal8CogAccess;
import com.hbm.entity.projectile.StrayCog;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilOutput;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.network.toclient.AuxParticle;
import com.hbm.registry.NtmDamageTypes;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class Goal8Regression {
    private static int checks;
    private static int sectionChecks;
    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());
    private static final Direction[] HORIZONTALS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};
    // Synthetic fuel identities: ModuleBurnTime classifies fuels by registry path, so these take the real solid/rocket rules.
    private static final Item SOLID_FUEL = new Item("hbmsntm:solid_fuel", 64, 3200);
    private static final Item ROCKET_FUEL = new Item("hbmsntm:rocket_fuel", 64, 3200);

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

    /** Controllable heat source; refill keeps the stored heat constant, every useUpHeat call is recorded. */
    static class HeatProbe extends BlockEntity implements IHeatSource {
        int stored;
        final boolean refill;
        int uses;
        long used;

        HeatProbe(BlockPos pos, int stored, boolean refill) {
            super(null, pos, new BlockState());
            this.stored = stored;
            this.refill = refill;
        }

        @Override public int getHeatStored() { return stored; }

        @Override
        public void useUpHeat(int heat) {
            uses++;
            used += heat;
            if(!refill) stored -= heat;
        }
    }

    /** Direct-provision receiver that records the side each tryProvide offers power on. */
    static class Probe extends BlockEntity implements IEnergyReceiverMK2 {
        long power;
        final List<Direction> offered = new ArrayList<>();

        Probe(BlockPos pos) {
            super(null, pos, new BlockState());
        }

        @Override public boolean isLoaded() { return !isRemoved(); }
        @Override public long getPower() { return power; }
        @Override public void setPower(long value) { power = value; }
        @Override public long getMaxPower() { return 1_000_000L; }

        @Override
        public boolean canConnect(Direction dir) {
            offered.add(dir);
            return true;
        }
    }

    static class Target extends LivingEntity {
        final List<Object> damageTypes = new ArrayList<>();
        final List<Float> amounts = new ArrayList<>();
        final boolean armored;

        Target(float health, boolean armored) {
            this.health = health;
            this.armored = armored;
        }

        @Override
        public boolean hurt(DamageSource source, float amount) {
            damageTypes.add(source.type());
            amounts.add(amount);
            if(armored) return false;
            health -= amount;
            return true;
        }

        @Override public float getBbHeight() { return 1.8F; }
    }

    static class Crate extends Entity {
        @Override
        public boolean hurt(DamageSource source, float amount) {
            health -= amount;
            return true;
        }
    }

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        return level;
    }

    static ServerLevel serverLevel() {
        ServerLevel level = new ServerLevel();
        level.manualClock = true;
        return level;
    }

    static void net(Level level) {
        // Two passes let links invalidated in the first pass rejoin, as in the Goal 3B/6 harnesses.
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static void transfer(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static MachineStirlingBlockEntity stirling(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        MachineStirlingBlockEntity engine = new MachineStirlingBlockEntity(pos, state);
        level.put(engine);
        return engine;
    }

    static HeaterFireboxBlockEntity firebox(Level level, BlockPos pos) {
        HeaterFireboxBlockEntity fire = new HeaterFireboxBlockEntity(pos, new BlockState());
        level.put(fire);
        return fire;
    }

    static HeatProbe heat(Level level, BlockPos pos, int stored, boolean refill) {
        HeatProbe probe = new HeatProbe(pos, stored, refill);
        level.put(probe);
        return probe;
    }

    static CableBaseBlockEntity cable(Level level, BlockPos pos) {
        CableBaseBlockEntity wire = new CableBaseBlockEntity(pos, new BlockState());
        level.put(wire);
        wire.updateEntity();
        return wire;
    }

    static BatterySocketBlockEntity socket(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
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
        socket.slots.set(0, MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_REDSTONE.ordinal()));
        return socket;
    }

    static Probe[] probes(Level level, MachineStirlingBlockEntity engine) {
        DirPos[] con = engine.getConPos();
        Probe[] probes = new Probe[con.length];
        for(int i = 0; i < con.length; i++) {
            probes[i] = new Probe(con[i].makeCompat());
            level.put(probes[i]);
        }
        return probes;
    }

    static int sounds(Level level, Object event) {
        int n = 0;
        for(Level.Sound sound : level.sounds) if(sound.event() == event) n++;
        return n;
    }

    static int warnings(Level level) {
        return sounds(level, NtmSoundEvents.WARN_OVERSPEED.get());
    }

    static boolean plain(ItemStack stack) {
        return MetaHelper.getMeta(stack) == 0 && !stack.has(NtmDataComponents.META.get());
    }

    // 1. Heat intake and power -------------------------------------------------------------------------------

    static void heatAndPower() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        HeaterFireboxBlockEntity fire = firebox(level, core.below());
        MachineStirlingBlockEntity engine = stirling(level, core, Direction.NORTH);

        fire.heatEnergy = 12_345;
        int fireDirty = fire.dirty;
        engine.updateEntity();
        check(fire.heatEnergy == 12_345 - 1_234, "the engine pulls (int)(12,345 * 0.1) = 1,234 TU from the firebox directly below the core");
        check(fire.dirty > fireDirty, "the pull goes through useUpHeat, which marks the firebox for saving");
        check(engine.heat == 0, "heat is cleared to 0 at the end of the server tick");
        check(engine.powerBuffer == 617, "the buffer is (long)(1,234 * 0.5) = 617 HE");
        check(engine.getPower() == 617 && engine.getMaxPower() == 617, "getPower and getMaxPower both return the buffer");

        fire.heatEnergy = 3_019;
        engine.updateEntity();
        check(fire.heatEnergy == 3_019 - 301 && engine.powerBuffer == 150, "3,019 TU stored: 301 TU pulled and (long)(301 * 0.5) = 150 HE");

        fire.heatEnergy = 9;
        fireDirty = fire.dirty;
        engine.updateEntity();
        check(fire.heatEnergy == 9 && fire.dirty == fireDirty && engine.powerBuffer == 0,
                "(int)(9 * 0.1) = 0: a real firebox holding 9 TU loses nothing and the engine produces nothing");

        HeatProbe five = heat(level, new BlockPos(10, 0, 0), 5, false);
        MachineStirlingBlockEntity overFive = stirling(level, new BlockPos(10, 1, 0), Direction.NORTH);
        overFive.updateEntity();
        check(five.uses == 0 && five.stored == 5 && overFive.powerBuffer == 0, "5 TU stored truncates to a 0 TU pull: useUpHeat is not called");
        five.stored = 10;
        overFive.updateEntity();
        check(five.uses == 1 && five.used == 1 && five.stored == 9 && overFive.powerBuffer == 0, "10 TU stored: 1 TU is pulled and (long)(0.5) = 0 HE");

        MachineStirlingBlockEntity alone = stirling(level, new BlockPos(20, 1, 0), Direction.NORTH);
        HeatProbe side = heat(level, new BlockPos(21, 1, 0), 10_000, false);
        HeatProbe top = heat(level, new BlockPos(20, 2, 0), 10_000, false);
        HeatProbe diagonal = heat(level, new BlockPos(21, 0, 0), 10_000, false);
        alone.updateEntity();
        check(alone.heat == 0 && alone.powerBuffer == 0, "without a heat source below the core: heat 0 and no power");
        check(side.uses == 0 && top.uses == 0 && diagonal.uses == 0, "heat sources beside, above or diagonally below the core are ignored");
        alone.heat = 5_000;
        alone.updateEntity();
        check(alone.powerBuffer == 2_497 && alone.heat == 0,
                "without a source a pre-set heat decays by max(heat / 1000, 1) before the power step: 4,995 TU -> 2,497 HE, then 0");

        MachineStirlingBlockEntity gearless = stirling(level, new BlockPos(40, 1, 40), Direction.NORTH);
        Probe[] probes = probes(level, gearless);
        HeatProbe under = heat(level, new BlockPos(40, 0, 40), 10_000, false);
        gearless.hasCog = false;
        gearless.powerBuffer = 3;
        long[] seen = new long[4];
        for(int i = 0; i < 4; i++) {
            gearless.updateEntity();
            seen[i] = gearless.powerBuffer;
        }
        check(seen[0] == 2 && seen[1] == 1 && seen[2] == 0 && seen[3] == 0, "without a cog the buffer decays by 1 HE per tick down to 0");
        boolean offered = false;
        for(Probe probe : probes) offered |= !probe.offered.isEmpty();
        check(!offered, "without a cog tryProvide is never called on any connection point");
        check(under.uses == 0 && under.stored == 10_000, "without a cog the engine takes no heat");
        gearless.hasCog = true;
        gearless.updateEntity();
        boolean all = true;
        for(Probe probe : probes) all &= probe.offered.size() == 1;
        check(all && gearless.powerBuffer == 0 && probes[0].power == 500, "with the cog every connection point is offered power; 1,000 TU -> 500 HE go out");
        section("1. heat intake and power");
    }

    // 2. Gear installation ----------------------------------------------------------------------------------

    static void gear() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        MachineStirlingBlockEntity engine = stirling(level, core, Direction.NORTH);
        engine.hasCog = false;

        ItemStack held = new ItemStack(NtmItems.GEAR_LARGE.get(), 3);
        int dirty = engine.dirty;
        check(engine.tryInstallGear(held), "a plain large gear installs");
        check(held.getCount() == 2 && engine.hasCog, "exactly one gear is consumed and the engine has its cog");
        check(engine.dirty == dirty + 1, "installing the gear marks the engine for saving at once");

        dirty = engine.dirty;
        check(!engine.tryInstallGear(held) && held.getCount() == 2 && engine.dirty == dirty, "an engine that has a cog refuses another gear; nothing changes");

        engine.hasCog = false;
        ItemStack plate = new ItemStack(NtmItems.PLATE_IRON.get(), 5);
        check(!engine.tryInstallGear(plate) && plate.getCount() == 5 && !engine.hasCog, "a wrong item is refused");
        ItemStack steelGear = MetaHelper.newStack(NtmItems.GEAR_LARGE.get(), 2, 1);
        check(!engine.tryInstallGear(steelGear) && steelGear.getCount() == 2 && !engine.hasCog && engine.dirty == dirty,
                "a META 1 (steel) gear does not fit the normal engine");
        ItemStack explicitZero = MetaHelper.newStack(NtmItems.GEAR_LARGE.get(), 1, 0);
        check(engine.tryInstallGear(explicitZero) && explicitZero.isEmpty() && engine.hasCog, "a gear carrying an explicit META 0 is the plain gear and fits");

        HeatProbe hot = heat(level, core.below(), 3_010, true);
        for(int i = 0; i < 70; i++) engine.updateEntity();
        check(engine.getOverspeed() == 70 && engine.getWarnCooldown() == 91, "70 ticks at 301 TU/t: overspeed 70, warning cooldown 100 - 9 = 91");
        engine.hasCog = false;
        dirty = engine.dirty;
        engine.updateEntity();
        check(engine.getOverspeed() == 0 && engine.getWarnCooldown() == 0, "without a cog the overspeed counter and the warning cooldown reset to 0");
        check(engine.dirty > dirty, "the overspeed reset marks the engine for saving");
        check(hot.uses == 70, "the gearless engine took no heat");
        section("2. gear installation");
    }

    // 3. Overspeed ------------------------------------------------------------------------------------------

    static void overspeed() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        HeatProbe hot = heat(level, core.below(), 3_010, true);
        MachineStirlingBlockEntity engine = stirling(level, core, Direction.NORTH);
        int dirty = engine.dirty;
        for(int t = 1; t <= 60; t++) engine.updateEntity();
        check(engine.getOverspeed() == 60 && warnings(level) == 0, "60 ticks above 300 TU/t do not warn yet");
        check(engine.dirty == dirty + 60, "every overspeed count change marks the engine for saving");
        engine.updateEntity();
        check(warnings(level) == 1, "the 61st overspeed tick plays the overspeed warning once");
        Level.Sound warn = level.sounds.get(0);
        check(warn.player() == null && warn.x() == 0.5 && warn.y() == 2 && warn.z() == 0.5 && warn.source() == SoundSource.BLOCKS
                && warn.volume() == 2.0F && warn.pitch() == 1.0F,
                "the warning plays for everyone above the core (x+0.5, y+1, z+0.5), BLOCKS, volume 2.0, pitch 1.0");
        check(engine.getWarnCooldown() == 100, "the warning starts a 100 tick cooldown");
        for(int t = 62; t <= 160; t++) engine.updateEntity();
        check(warnings(level) == 1, "the cooldown blocks the next 99 ticks");
        engine.updateEntity();
        check(warnings(level) == 2, "the warning repeats on tick 161, 100 ticks after the first");
        for(int t = 162; t <= 300; t++) engine.updateEntity();
        check(engine.hasCog && level.blasts.isEmpty() && level.added.isEmpty() && engine.getOverspeed() == 300,
                "300 overspeed ticks are survived");
        dirty = engine.dirty;
        engine.updateEntity();
        check(!engine.hasCog, "the 301st overspeed tick destroys the cog");
        check(warnings(level) == 3, "three warnings were played (ticks 61, 161, 261)");
        check(level.blasts.size() == 1, "one explosion");
        Level.Blast blast = level.blasts.get(0);
        check(blast.x() == 0.5 && blast.y() == 2 && blast.z() == 0.5 && blast.strength() == 5F && blast.exploder() == null,
                "the explosion is centred at (x+0.5, y+1, z+0.5) with strength 5");
        check(!blast.fire() && !blast.blockDamage(), "the explosion neither sets fire nor damages blocks");
        check(level.added.size() == 1 && level.added.get(0) instanceof StrayCog, "one stray cog is spawned");
        check(engine.dirty > dirty, "the destruction marks the engine for saving");
        check(engine.powerBuffer == 149, "the destruction tick already skips provision: the 150 HE buffer decays to 149");
        engine.updateEntity();
        check(engine.getOverspeed() == 0 && level.blasts.size() == 1 && level.added.size() == 1 && hot.uses == 301,
                "afterwards the gearless engine idles: no second explosion or cog, no more heat taken");

        int[][] launch = {{-1, 0}, {0, -1}, {1, 0}, {0, 1}};
        for(int f = 0; f < 4; f++) {
            Direction facing = HORIZONTALS[f];
            reset();
            level = level();
            BlockPos at = new BlockPos(10, 5, -7);
            heat(level, at.below(), 3_010, true);
            MachineStirlingBlockEntity e = stirling(level, at, facing);
            for(int t = 1; t <= 301; t++) e.updateEntity();
            check(!e.hasCog && level.added.size() == 1 && level.added.get(0) instanceof StrayCog, facing + ": destroyed on tick 301");
            StrayCog cog = (StrayCog) level.added.get(0);
            check(cog.getX() == 10.5 + facing.getStepX() && cog.getY() == 6 && cog.getZ() == -6.5 + facing.getStepZ(),
                    facing + ": the cog starts one block out on the facing side at y+1");
            check(cog.getOrientation() == facing.get3DDataValue() && cog.getMeta() == 0, facing + ": orientation is the facing's 3D value, meta 0");
            Direction rot = facing.getCounterClockWise();
            Vec3 v = cog.getDeltaMovement();
            check(rot.getStepX() == launch[f][0] && rot.getStepZ() == launch[f][1], facing + ": the launch side is the original DOWN-axis rotation");
            check(v.x == rot.getStepX() && v.y == 1 + (301 - 300) * 0.0001D && v.z == rot.getStepZ(),
                    facing + ": delta movement is (rot.x, 1 + (heat - 300) * 0.0001, rot.z)");
            check(cog.level == level, facing + ": the cog belongs to the engine's level");
        }

        reset();
        level = level();
        heat(level, core.below(), 50_000, true);
        MachineStirlingBlockEntity fast = stirling(level, core, Direction.NORTH);
        for(int t = 1; t <= 301; t++) fast.updateEntity();
        check(level.added.size() == 1 && level.added.get(0).getDeltaMovement().y == 1 + (5_000 - 300) * 0.0001D,
                "the vertical launch speed grows with the heat at destruction (5,000 TU -> 1.47)");

        reset();
        level = level();
        HeatProbe varying = heat(level, core.below(), 3_010, true);
        MachineStirlingBlockEntity cooled = stirling(level, core, Direction.NORTH);
        for(int t = 0; t < 50; t++) cooled.updateEntity();
        varying.stored = 3_000;
        cooled.updateEntity();
        check(cooled.getOverspeed() == 0, "a tick at exactly 300 TU resets the overspeed counter");
        dirty = cooled.dirty;
        for(int t = 0; t < 5; t++) cooled.updateEntity();
        check(cooled.dirty == dirty && cooled.powerBuffer == 150, "steady 300 TU/t neither counts overspeed nor marks the engine every tick");
        varying.stored = 3_010;
        for(int t = 0; t < 60; t++) cooled.updateEntity();
        check(warnings(level) == 0, "after the reset the count starts again: 60 new ticks do not warn");
        cooled.updateEntity();
        check(warnings(level) == 1, "the 61st new tick warns");
        section("3. overspeed");
    }

    // 4. Firebox pairing -------------------------------------------------------------------------------------

    record Pairing(int burnHeat, int maxOverspeed, int overspeedTicks, int warnings, int destroyedAt, int peakPull, boolean steady) {}

    /** Firebox first, engine second, every tick. The steady window is the last 500 ticks of the run. */
    static Pairing pairing(ItemStack fuel, int burnHeat, boolean prefill, int ticks, int steadyPull) {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        HeaterFireboxBlockEntity fire = firebox(level, core.below());
        if(fuel != null) {
            fire.slots.set(0, fuel);
        } else {
            // No stand-in fuel reaches the balefire multiplier (it only applies to BALEFIRE_AND_STEEL, which has no burn time here).
            fire.burnHeat = burnHeat;
            fire.burnTime = fire.maxBurnTime = 1_000_000;
        }
        if(prefill) {
            for(int guard = 0; fire.heatEnergy < HeaterFireboxBlockEntity.maxHeatEnergy && guard < 10_000; guard++) {
                level.time++;
                fire.updateEntity();
            }
        }
        MachineStirlingBlockEntity engine = stirling(level, core, Direction.NORTH);
        int maxOverspeed = 0, overspeedTicks = 0, destroyedAt = -1, peakPull = 0;
        boolean steady = true;
        for(int t = 1; t <= ticks; t++) {
            level.time++;
            fire.updateEntity();
            int before = fire.heatEnergy;
            engine.updateEntity();
            int pulled = before - fire.heatEnergy;
            peakPull = Math.max(peakPull, pulled);
            maxOverspeed = Math.max(maxOverspeed, engine.getOverspeed());
            if(engine.getOverspeed() > 0) overspeedTicks++;
            if(!engine.hasCog) {
                destroyedAt = t;
                break;
            }
            if(t > ticks - 500) steady &= pulled == steadyPull && engine.powerBuffer == steadyPull / 2;
        }
        return new Pairing(fire.burnHeat, maxOverspeed, overspeedTicks, warnings(level), destroyedAt, peakPull, steady);
    }

    static void fireboxPairing() {
        Pairing coal = pairing(new ItemStack(Items.COAL, 64), 0, false, 3_000, 200);
        check(coal.burnHeat() == 200, "coal burns at 200 TU/t in the firebox (burn module x2)");
        check(coal.maxOverspeed() == 0 && coal.warnings() == 0 && coal.destroyedAt() == -1 && coal.peakPull() <= 300,
                "coal, cold start: never overspeeds (peak pull " + coal.peakPull() + " TU)");
        check(coal.steady(), "coal, cold start: steady 200 TU/t -> 100 HE/t");
        System.out.println("  coal cold start: peak pull " + coal.peakPull() + " TU/t, steady 100 HE/t");

        Pairing coalFull = pairing(new ItemStack(Items.COAL, 64), 0, true, 3_000, 200);
        check(coalFull.maxOverspeed() == 44 && coalFull.overspeedTicks() == 44,
                "coal, firebox pre-filled to 100,000 TU: exactly 44 consecutive overspeed ticks (got " + coalFull.overspeedTicks() + ")");
        check(coalFull.warnings() == 0 && coalFull.destroyedAt() == -1, "coal, pre-filled: no warning, no destruction");
        check(coalFull.steady(), "coal, pre-filled: steady 100 HE/t afterwards");
        System.out.println("  coal pre-filled: " + coalFull.overspeedTicks() + " overspeed ticks, peak pull " + coalFull.peakPull() + " TU");

        Pairing solid = pairing(new ItemStack(SOLID_FUEL, 64), 0, false, 3_000, 300);
        check(solid.burnHeat() == 300, "solid fuel burns at 300 TU/t in the firebox (burn module x3)");
        check(solid.peakPull() == 300 && solid.maxOverspeed() == 0 && solid.warnings() == 0 && solid.destroyedAt() == -1,
                "300 TU/t, cold start: the pull reaches exactly 300 TU and never exceeds it");
        check(solid.steady(), "300 TU/t, cold start: steady 150 HE/t");

        Pairing solidFull = pairing(new ItemStack(SOLID_FUEL, 64), 0, true, 3_000, 300);
        check(solidFull.maxOverspeed() == 93 && solidFull.overspeedTicks() == 93,
                "300 TU/t, pre-filled: exactly 93 consecutive overspeed ticks (got " + solidFull.overspeedTicks() + ")");
        check(solidFull.warnings() == 1 && solidFull.destroyedAt() == -1, "300 TU/t, pre-filled: one warning, no destruction");
        check(solidFull.steady(), "300 TU/t, pre-filled: steady 150 HE/t afterwards");
        System.out.println("  300 TU/t pre-filled: " + solidFull.overspeedTicks() + " overspeed ticks, " + solidFull.warnings() + " warning");

        Pairing rocket = pairing(new ItemStack(ROCKET_FUEL, 64), 0, false, 1_000, 0);
        check(rocket.burnHeat() == 500, "rocket fuel burns at 500 TU/t in the firebox (burn module x5)");
        check(rocket.destroyedAt() == 309 && rocket.warnings() == 3,
                "500 TU/t, cold start: destroyed on tick 309 after three warnings (got " + rocket.destroyedAt() + ")");
        Pairing wildfire = pairing(null, 1_500, false, 1_000, 0);
        check(wildfire.destroyedAt() == 303 && wildfire.warnings() == 3,
                "1500 TU/t, cold start: destroyed on tick 303 after three warnings (got " + wildfire.destroyedAt() + ")");
        Pairing rocketFull = pairing(new ItemStack(ROCKET_FUEL, 64), 0, true, 1_000, 0);
        Pairing wildfireFull = pairing(null, 1_500, true, 1_000, 0);
        check(rocketFull.destroyedAt() == 301 && wildfireFull.destroyedAt() == 301,
                "500 and 1500 TU/t, pre-filled: destroyed on tick 301 (got " + rocketFull.destroyedAt() + ", " + wildfireFull.destroyedAt() + ")");
        System.out.println("  destruction ticks: 500 TU/t cold " + rocket.destroyedAt() + ", 1500 TU/t cold " + wildfire.destroyedAt()
                + ", pre-filled " + rocketFull.destroyedAt() + "/" + wildfireFull.destroyedAt());
        section("4. firebox pairing");
    }

    // 5. Connections ----------------------------------------------------------------------------------------

    static void connections() {
        reset();
        Level level = level();
        for(int f = 0; f < 4; f++) {
            Direction facing = HORIZONTALS[f];
            BlockPos at = new BlockPos(100 * f - 3, 4, 17);
            MachineStirlingBlockEntity engine = stirling(level, at, facing);
            DirPos[] con = engine.getConPos();
            int x = at.getX(), y = at.getY(), z = at.getZ();
            check(con.length == 4
                    && con[0].makeCompat().equals(new BlockPos(x + 2, y, z)) && con[0].getDir() == Direction.EAST
                    && con[1].makeCompat().equals(new BlockPos(x - 2, y, z)) && con[1].getDir() == Direction.WEST
                    && con[2].makeCompat().equals(new BlockPos(x, y, z + 2)) && con[2].getDir() == Direction.SOUTH
                    && con[3].makeCompat().equals(new BlockPos(x, y, z - 2)) && con[3].getDir() == Direction.NORTH,
                    facing + ": connection points are x+-2 and z+-2 facing outwards, independent of the facing");
        }

        reset();
        level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        heat(level, core.below(), 3_000, true);
        MachineStirlingBlockEntity engine = stirling(level, core, Direction.NORTH);
        Probe[] probes = probes(level, engine);
        for(int t = 0; t < 3; t++) {
            for(Probe probe : probes) probe.offered.clear();
            engine.updateEntity();
            boolean each = true;
            for(int i = 0; i < 4; i++) each &= probes[i].offered.equals(List.of(engine.getConPos()[i].getDir().getOpposite()));
            check(each, "tick " + t + ": tryProvide reaches all four connection points, each from its outward side");
        }
        check(probes[0].power == 450 && probes[1].power == 0 && probes[2].power == 0 && probes[3].power == 0,
                "direct provision is offered east, west, south, north in that order; the first taker gets the 150 HE each tick");

        reset();
        level = level();
        heat(level, core.below(), 3_000, true);
        engine = stirling(level, core, Direction.NORTH);
        CableBaseBlockEntity[] cables = new CableBaseBlockEntity[4];
        for(int i = 0; i < 4; i++) cables[i] = cable(level, engine.getConPos()[i].makeCompat());
        net(level);
        Set<Object> nets = new HashSet<>();
        for(CableBaseBlockEntity wire : cables) nets.add(wire.node.net);
        check(nets.size() == 4 && !nets.contains(null), "four separate red cables at the connection points form four nets");
        for(int t = 0; t < 3; t++) {
            for(CableBaseBlockEntity wire : cables) wire.node.net.providerEntries.clear();
            engine.updateEntity();
            boolean joined = true;
            for(CableBaseBlockEntity wire : cables) joined &= wire.node.net.providerEntries.containsKey(engine);
            check(joined, "tick " + t + ": the engine joins all four cable nets as a provider");
        }

        for(int side = 0; side < 4; side++) {
            reset();
            level = level();
            HeaterFireboxBlockEntity fire = firebox(level, core.below());
            fire.slots.set(0, new ItemStack(Items.COAL, 64));
            engine = stirling(level, core, Direction.NORTH);
            DirPos con = engine.getConPos()[side];
            Direction out = con.getDir();
            BlockPos first = con.makeCompat();
            BlockPos second = first.relative(out);
            cable(level, first);
            cable(level, second);
            BatterySocketBlockEntity socket = socket(level, second.relative(out), out.getOpposite());
            socket.updateEntity();
            net(level);
            for(int t = 0; t < 600; t++) {
                level.time++;
                fire.updateEntity();
                engine.updateEntity();
                socket.updateEntity();
                transfer(level);
            }
            boolean steady = true;
            for(int t = 0; t < 20; t++) {
                long before = socket.getPower();
                level.time++;
                fire.updateEntity();
                engine.updateEntity();
                socket.updateEntity();
                transfer(level);
                steady &= socket.getPower() - before == 100;
            }
            check(steady, out + " side: a red cable delivers the coal-heated 100 HE/t into a battery socket");
        }

        reset();
        level = level();
        HeaterFireboxBlockEntity fire = firebox(level, core.below());
        fire.slots.set(0, new ItemStack(Items.COAL, 64));
        engine = stirling(level, core, Direction.NORTH);
        engine.hasCog = false;
        cable(level, new BlockPos(2, 1, 0));
        cable(level, new BlockPos(3, 1, 0));
        BatterySocketBlockEntity socket = socket(level, new BlockPos(4, 1, 0), Direction.WEST);
        socket.updateEntity();
        net(level);
        for(int t = 0; t < 600; t++) {
            level.time++;
            fire.updateEntity();
            engine.updateEntity();
            socket.updateEntity();
            transfer(level);
        }
        check(socket.getPower() == 0 && fire.heatEnergy == HeaterFireboxBlockEntity.maxHeatEnergy,
                "without a cog nothing is delivered and the firebox fills up untouched");
        section("5. connections");
    }

    // 6. Save and sync --------------------------------------------------------------------------------------

    static void saveAndSync() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        heat(level, core.below(), 3_010, true);
        MachineStirlingBlockEntity engine = stirling(level, core, Direction.NORTH);
        int packs = engine.packs;
        for(int t = 0; t < 70; t++) engine.updateEntity();
        check(engine.packs == packs + 70 && engine.packRange == 150, "the engine syncs every server tick with range 150");
        engine.heat = 123;
        CompoundTag tag = new CompoundTag();
        engine.saveAdditional(tag, null);
        check(tag.getLong("powerBuffer") == 150 && tag.getBoolean("hasCog") && tag.getInt("overspeed") == 70,
                "save writes powerBuffer, hasCog and overspeed under the original keys");
        check(!tag.contains("heat") && !tag.contains("warnCooldown"), "heat and warnCooldown are not saved");

        MachineStirlingBlockEntity copy = stirling(level, new BlockPos(30, 1, 30), Direction.NORTH);
        copy.hasCog = false;
        copy.loadAdditional(tag, null);
        check(copy.powerBuffer == 150 && copy.hasCog && copy.getOverspeed() == 70 && copy.heat == 0 && copy.getWarnCooldown() == 0,
                "load restores powerBuffer, hasCog and overspeed; heat and cooldown start at 0");

        engine.hasCog = false;
        CompoundTag gearless = new CompoundTag();
        engine.saveAdditional(gearless, null);
        MachineStirlingBlockEntity fresh = stirling(level, new BlockPos(40, 1, 40), Direction.NORTH);
        check(fresh.hasCog, "a new engine block entity starts with its cog");
        fresh.loadAdditional(gearless, null);
        check(!fresh.hasCog, "a saved gearless engine reloads gearless");

        engine.powerBuffer = 150;
        engine.heat = 301;
        engine.hasCog = false;
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        engine.serialize(buf);
        Level clientLevel = level();
        clientLevel.isClientSide = true;
        MachineStirlingBlockEntity client = stirling(clientLevel, core, Direction.NORTH);
        client.deserialize(buf);
        check(client.powerBuffer == 150 && client.heat == 301 && !client.hasCog, "serialize/deserialize round-trips powerBuffer, heat and hasCog");

        client.updateEntity();
        check(client.spin == 25F && client.lastSpin == 0F, "the client spins by powerBuffer * 50 / 300 = 25 degrees per tick");
        for(int t = 0; t < 14; t++) client.updateEntity();
        check(client.spin == 15F && client.lastSpin == -10F, "the spin wraps at 360 degrees (375 -> 15, last 350 -> -10)");
        check(client.powerBuffer == 150 && client.heat == 301 && client.packs == 0, "the client tick only animates; it neither pulls heat nor syncs");
        section("6. save and sync");
    }

    // 7. Items and anvil recipes ----------------------------------------------------------------------------

    static boolean accepts(AnvilConstructionRecipe recipe, ItemStack... offered) {
        for(AStack input : recipe.input) {
            boolean found = false;
            for(ItemStack stack : offered) found |= input.matchesRecipe(stack, false);
            if(!found) return false;
        }
        return true;
    }

    static boolean outputs(AnvilConstructionRecipe recipe, Object[][] expected) {
        if(recipe.output.size() != expected.length) return false;
        for(int i = 0; i < expected.length; i++) {
            AnvilOutput out = recipe.output.get(i);
            if(!out.stack.is((Item) expected[i][0]) || out.stack.getCount() != (int) expected[i][1] || out.chance != 1F || !plain(out.stack)) return false;
        }
        return true;
    }

    static void itemsAndRecipes() {
        Item planks = new Item("minecraft:oak_planks");
        planks.tags.add("planks");
        NtmItems.PLATE_STEEL.get().tags.add((String) NtmTags.Items.PLATES_STEEL);
        Item engineItem = NtmBlocks.MACHINE_STIRLING.asItem();
        Item gearItem = NtmItems.GEAR_LARGE.get();

        List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
        // Goal 9A appends the heat boiler after the Stirling entries; its own suite checks that entry. Goal 9B appends
        // the steam engine after the boiler, so the Stirling entries are anchored on the boiler's index, not the list end.
        int n = -1, boilers = 0;
        for(int i = 0; i < all.size(); i++) {
            if(all.get(i).output.size() == 1 && all.get(i).output.get(0).stack.is(NtmBlocks.HEAT_BOILER.asItem())) {
                n = i;
                boilers++;
            }
        }
        AnvilConstructionRecipe buildVanilla = all.get(Math.max(n - 5, 0)), buildNeo = all.get(Math.max(n - 4, 0));
        AnvilConstructionRecipe withGear = all.get(Math.max(n - 3, 0)), withoutGear = all.get(Math.max(n - 2, 0)), gearRecycling = all.get(Math.max(n - 1, 0));
        check(boilers == 1 && n >= 5 && AnvilRecipes.getConstruction(n - 5) == buildVanilla && AnvilRecipes.getConstruction(n - 1) == gearRecycling,
                "the five Stirling entries directly precede the Goal 9A boiler entry");

        for(AnvilConstructionRecipe build : new AnvilConstructionRecipe[] {buildVanilla, buildNeo}) {
            List<AStack> in = build.input;
            check(in.size() == 5 && in.get(0) instanceof TagStack planksTag && planksTag.tag == ItemTags.PLANKS && planksTag.stacksize == 16
                    && in.get(1) instanceof TagStack plates && plates.tag == NtmTags.Items.PLATES_STEEL && plates.stacksize == 6
                    && in.get(2) instanceof ComparableStack copper && copper.stacksize == 8
                    && in.get(3) instanceof ComparableStack coils && coils.item == NtmItems.COIL_COPPER.get() && coils.stacksize == 4
                    && in.get(4) instanceof ComparableStack gearIn && gearIn.item == gearItem && gearIn.stacksize == 1 && gearIn.meta == 0,
                    "construction inputs: 16 planks (tag), 6 steel plates (tag), 8 copper, 4 copper coils, 1 plain gear");
            check(outputs(build, new Object[][] {{engineItem, 1}}) && build.tierLower == 2 && build.isTierValid(2) && !build.isTierValid(1)
                    && build.getOverlay() == OverlayType.CONSTRUCTION, "construction gives one plain engine at anvil tier 2");
        }
        check(((ComparableStack) buildVanilla.input.get(2)).item == Items.COPPER_INGOT && ((ComparableStack) buildNeo.input.get(2)).item == NtmItems.INGOT_COPPER.get(),
                "the first construction takes Minecraft copper, the second NEO copper");

        ItemStack[] vanillaSet = {new ItemStack(planks, 16), new ItemStack(NtmItems.PLATE_STEEL.get(), 6), new ItemStack(Items.COPPER_INGOT, 8),
                new ItemStack(NtmItems.COIL_COPPER.get(), 4), new ItemStack(gearItem, 1)};
        check(accepts(buildVanilla, vanillaSet) && !accepts(buildNeo, vanillaSet), "the Minecraft copper set matches only the first construction");
        ItemStack[] neoSet = vanillaSet.clone();
        neoSet[2] = new ItemStack(NtmItems.INGOT_COPPER.get(), 8);
        check(accepts(buildNeo, neoSet) && !accepts(buildVanilla, neoSet), "the NEO copper set matches only the second construction");
        ItemStack[] steelGear = vanillaSet.clone();
        steelGear[4] = MetaHelper.newStack(gearItem, 1, 1);
        check(!accepts(buildVanilla, steelGear), "a META 1 gear does not satisfy the construction");
        ItemStack[] fewPlanks = vanillaSet.clone();
        fewPlanks[0] = new ItemStack(planks, 15);
        check(!accepts(buildVanilla, fewPlanks), "15 planks are not enough");

        ItemStack plainEngine = new ItemStack(engineItem);
        ItemStack gearlessEngine = MetaHelper.newStack(engineItem, 1, 1);
        check(withGear.input.size() == 1 && withGear.input.get(0).matchesRecipe(plainEngine, false) && !withGear.input.get(0).matchesRecipe(gearlessEngine, false),
                "'with gear' recycling takes only the plain engine, not the META 1 gearless one");
        check(withoutGear.input.size() == 1 && withoutGear.input.get(0).matchesRecipe(gearlessEngine, false) && !withoutGear.input.get(0).matchesRecipe(plainEngine, false),
                "'without gear' recycling takes only the META 1 gearless engine");
        check(gearRecycling.input.size() == 1 && gearRecycling.input.get(0).matchesRecipe(new ItemStack(gearItem), false)
                        && !gearRecycling.input.get(0).matchesRecipe(MetaHelper.newStack(gearItem, 1, 1), false),
                "gear recycling takes only the plain gear");
        check(outputs(withGear, new Object[][] {{NtmItems.PLATE_STEEL.get(), 6}, {NtmItems.INGOT_COPPER.get(), 8}, {NtmItems.COIL_COPPER.get(), 4}, {gearItem, 1}}),
                "'with gear' recycling returns 6 steel plates, 8 copper, 4 coils and the plain gear");
        check(outputs(withoutGear, new Object[][] {{NtmItems.PLATE_STEEL.get(), 6}, {NtmItems.INGOT_COPPER.get(), 8}, {NtmItems.COIL_COPPER.get(), 4}}),
                "'without gear' recycling returns the same without a gear; neither returns planks");
        check(outputs(gearRecycling, new Object[][] {{NtmItems.PLATE_IRON.get(), 8}, {NtmItems.INGOT_COPPER.get(), 1}}),
                "gear recycling returns 8 iron plates and 1 copper");
        boolean recycling = true;
        for(AnvilConstructionRecipe r : new AnvilConstructionRecipe[] {withGear, withoutGear, gearRecycling})
            recycling &= r.tierLower == 2 && r.getOverlay() == OverlayType.RECYCLING;
        check(recycling, "all three recyclings are tier 2 recycling entries");
        check(ItemStack.isSameItemSameComponents(withGear.output.get(3).stack, new ItemStack(gearItem))
                        && ItemStack.isSameItemSameComponents(buildVanilla.output.get(0).stack, plainEngine),
                "recycled gears and built engines carry no META component, so they stack with plain gears and engines");

        MachineStirlingBlockEntity dropEngine = stirling(level(), new BlockPos(0, 0, 0), Direction.NORTH);
        check(dropEngine.hasCog && dropEngine.getDropMeta() == 0, "an engine with its gear drops as the plain item (meta 0, no component)");
        dropEngine.hasCog = false;
        check(dropEngine.getDropMeta() == 1, "a gearless engine drops as meta 1");
        dropEngine.hasCog = true;
        check(dropEngine.getDropMeta() == 0, "reinstalling the gear restores the plain drop");
        section("7. items and anvil recipes");
    }

    // 8. Stray cog ------------------------------------------------------------------------------------------

    static StrayCog cog(Level level, int orientation, double vx, double vy, double vz) {
        StrayCog cog = new StrayCog(level, 3.5, 70, -2.5);
        cog.setOrientation(orientation);
        cog.setDeltaMovement(vx, vy, vz);
        cog.tickCount = 5;
        return cog;
    }

    static BlockState block(Level level, BlockPos pos, float resistance) {
        BlockState state = new BlockState();
        state.resistance = resistance;
        level.states.put(pos, state);
        return state;
    }

    static void strayCog() {
        reset();
        ServerLevel level = serverLevel();
        StrayCog cog = cog(level, 2, 1, 0, 0);
        Target victim = new Target(20F, false);
        victim.setPos(3, 64, -2);
        Goal8CogAccess.hitEntity(cog, victim);
        check(victim.damageTypes.equals(List.of(NtmDamageTypes.RUBBLE)) && victim.amounts.equals(List.of(1000F)),
                "a living target takes 1000 rubble damage");
        check(PacketDistributor.sent.size() == 1, "a killed living target sends one giblets payload");
        PacketDistributor.Sent sent = PacketDistributor.sent.get(0);
        CompoundTag data = (CompoundTag) ((AuxParticle) sent.payload()).tag;
        double gibY = victim.getY() + victim.getBbHeight() * 0.5;
        check(data.getString("type").equals("giblets") && data.getInt("ent") == victim.getId() && data.getInt("cDiv") == 5,
                "the payload is giblets for the victim with cDiv 5");
        check(sent.level() == level && sent.x() == 3 && sent.y() == gibY && sent.z() == -2 && sent.range() == 150,
                "the payload goes to players within 150 of the victim's mid-height");
        check(level.sounds.size() == 1, "one sound on the kill");
        Level.Sound crunch = level.sounds.get(0);
        check(crunch.event() == SoundEvents.ZOMBIE_BREAK_WOODEN_DOOR && crunch.source() == SoundSource.BLOCKS && crunch.volume() == 2.0F
                        && crunch.pitch() >= 0.95F && crunch.pitch() <= 1.15F && crunch.x() == 3 && crunch.y() == 64 && crunch.z() == -2,
                "the kill plays the wooden-door break sound at the victim, volume 2.0, pitch 0.95-1.15");

        Target tank = new Target(20F, true);
        Goal8CogAccess.hitEntity(cog, tank);
        check(tank.amounts.equals(List.of(1000F)) && PacketDistributor.sent.size() == 1 && level.sounds.size() == 1,
                "a target that survives is hurt but not gibbed");
        Crate crate = new Crate();
        Goal8CogAccess.hitEntity(cog, crate);
        check(!crate.isAlive() && PacketDistributor.sent.size() == 1 && level.sounds.size() == 1, "a killed non-living entity is not gibbed");
        Target corpse = new Target(0F, false);
        Goal8CogAccess.hitEntity(cog, corpse);
        check(corpse.amounts.isEmpty(), "a dead target is ignored");
        Level client = level();
        client.isClientSide = true;
        Target clientVictim = new Target(20F, false);
        Goal8CogAccess.hitEntity(cog(client, 2, 1, 0, 0), clientVictim);
        check(clientVictim.amounts.isEmpty(), "entity hits are server-side only");

        BlockPos wall = new BlockPos(4, 70, -3);
        block(level, wall, 6F);
        StrayCog slow = cog(level, 3, 0.3, -0.4, 0.2);
        Goal8CogAccess.hitBlock(slow, wall, Direction.UP);
        CompoundTag lying = Goal8CogAccess.save(slow);
        check(slow.getOrientation() == 9 && slow.getDeltaMovement().equals(Vec3.ZERO), "below 0.75 speed a top-face hit lays the cog down: orientation + 6, motion zero");
        check(slow.getX() == 4.5 && slow.getY() == 71 && slow.getZ() == -2.5, "the lying cog is moved onto the hit point on top of the block");
        check(lying.getBoolean("inGround") && lying.getInt("xTile") == 4 && lying.getInt("yTile") == 70 && lying.getInt("zTile") == -3,
                "the lying cog is in the ground and remembers the block it lies on");
        check(level.blasts.isEmpty() && level.destroyed.isEmpty(), "lying down neither explodes nor breaks the block");
        StrayCog sideways = cog(level, 3, 0.3, 0.1, 0.2);
        Goal8CogAccess.hitBlock(sideways, wall, Direction.EAST);
        check(sideways.getOrientation() == 3 && sideways.getDeltaMovement().equals(Vec3.ZERO) && !Goal8CogAccess.save(sideways).getBoolean("inGround")
                        && sideways.getX() == 3.5 && level.blasts.isEmpty(),
                "a slow side-face hit only cancels the motion: the cog stays upright, unstuck and in place (local deviation)");
        check(Goal8CogAccess.gravity(slow) == 0 && Goal8CogAccess.gravity(cog(level, 2, 1, 0, 0)) == 0.03,
                "gravity is 0.03 in flight and 0 in the ground");

        StrayCog fast = cog(level, 2, 1.0, 0.25, -0.5);
        Goal8CogAccess.hitBlock(fast, wall, Direction.EAST);
        Vec3 bounced = fast.getDeltaMovement();
        check(bounced.x == -1.0 && bounced.y == 0.25 && bounced.z == -0.5, "at 0.75 or more an east-face hit negates the x velocity");
        check(fast.getOrientation() == 2 && !Goal8CogAccess.save(fast).getBoolean("inGround"), "a bouncing cog keeps flying");
        check(level.blasts.size() == 1, "the bounce causes one explosion");
        Level.Blast blast = level.blasts.get(0);
        check(blast.exploder() == fast && blast.x() == 3.5 && blast.y() == 70 && blast.z() == -2.5 && blast.strength() == 3F
                && !blast.fire() && !blast.blockDamage(), "a strength 3 explosion at the cog, without fire or block damage");
        check(level.destroyed.equals(List.of(wall)), "the hit block (resistance 6 < 50) is removed");

        BlockPos hard = new BlockPos(9, 70, -3);
        block(level, hard, 50F);
        Goal8CogAccess.hitBlock(cog(level, 2, 0, -1, 0), hard, Direction.UP);
        check(level.blasts.size() == 2 && level.destroyed.size() == 1, "a block with resistance 50 is not removed");
        BlockPos soft = new BlockPos(10, 70, -3);
        block(level, soft, 49.9F);
        StrayCog down = cog(level, 2, 0, -1, 0);
        Goal8CogAccess.hitBlock(down, soft, Direction.UP);
        check(level.destroyed.size() == 2 && level.destroyed.get(1).equals(soft) && down.getDeltaMovement().y == 1,
                "resistance 49.9 is removed; an up-face hit negates the y velocity");
        StrayCog edge = cog(level, 2, 0.75, 0, 0);
        Goal8CogAccess.hitBlock(edge, hard, Direction.WEST);
        check(edge.getOrientation() == 2 && edge.getDeltaMovement().x == -0.75, "exactly 0.75 already bounces");
        StrayCog young = cog(level, 2, 1, 0, 0);
        young.tickCount = 1;
        int blasts = level.blasts.size();
        Goal8CogAccess.hitBlock(young, soft, Direction.EAST);
        check(young.getDeltaMovement().x == 1 && young.getOrientation() == 2 && level.blasts.size() == blasts, "block hits in the first tick are ignored");

        for(int t = 0; t < 3; t++) slow.tick();
        check(slow.flightTicks == 0 && slow.baseTicks == 3 && slow.getOrientation() == 9 && Goal8CogAccess.save(slow).getBoolean("inGround"),
                "while its block is unchanged a lying cog only base-ticks: no movement, no hit checks");
        CompoundTag saved = Goal8CogAccess.save(slow);
        StrayCog reloaded = new StrayCog(level, 0, 0, 0);
        Goal8CogAccess.load(reloaded, saved);
        check(reloaded.getOrientation() == 9 && reloaded.getMeta() == 0 && Goal8CogAccess.save(reloaded).getInt("yTile") == 70,
                "NBT keeps rot, meta, inGround and the xTile/yTile/zTile block");
        reloaded.tick();
        check(reloaded.flightTicks == 0 && reloaded.baseTicks == 1, "after a reload the lying cog re-reads its block and stays down");

        block(level, wall, 6F);
        slow.tick();
        check(slow.flightTicks == 1 && !Goal8CogAccess.save(slow).getBoolean("inGround"), "when the block under it changes the cog comes loose");
        slow.tick();
        check(slow.getOrientation() == 9 && slow.flightTicks == 2, "the next tick it is still lying (orientation + 6 kept) and flying again");

        Player player = new Player();
        StrayCog pickup = cog(level, 9, 0, 0, 0);
        InteractionResult result = pickup.interact(player, InteractionHand.MAIN_HAND);
        ItemStack got = player.getInventory().items.get(0);
        check(result == InteractionResult.CONSUME && pickup.isRemoved(), "a server-side right click picks the cog up");
        check(got.is(NtmItems.GEAR_LARGE.get()) && got.getCount() == 1 && plain(got), "the player receives one plain large gear (no META component)");
        pickup.interact(player, InteractionHand.MAIN_HAND);
        check(player.getInventory().items.get(1).isEmpty(), "a removed cog gives nothing more");
        StrayCog steel = cog(level, 9, 0, 0, 0);
        steel.setMeta(1);
        steel.interact(player, InteractionHand.MAIN_HAND);
        ItemStack steelGear = player.getInventory().items.get(1);
        check(steelGear.is(NtmItems.GEAR_LARGE.get()) && MetaHelper.getMeta(steelGear) == 1, "a META 1 cog returns a META 1 gear");
        Player full = new Player();
        full.getInventory().rejectAdd = true;
        StrayCog kept = cog(level, 9, 0, 0, 0);
        kept.interact(full, InteractionHand.MAIN_HAND);
        check(!kept.isRemoved(), "with a full inventory the cog stays");
        StrayCog remote = cog(client, 9, 0, 0, 0);
        Player clientPlayer = new Player();
        check(remote.interact(clientPlayer, InteractionHand.MAIN_HAND) == InteractionResult.SUCCESS && !remote.isRemoved()
                && clientPlayer.getInventory().items.get(0).isEmpty(), "the client only swings; the server hands out the gear");
        CompoundTag steelTag = Goal8CogAccess.save(steel);
        StrayCog steelCopy = new StrayCog(level, 0, 0, 0);
        Goal8CogAccess.load(steelCopy, steelTag);
        check(steelTag.getInt("meta") == 1 && steelCopy.getMeta() == 1 && !steelTag.contains("xTile"), "meta 1 round-trips; a cog that never landed has no xTile");
        check(pickup.isPickable() && pickup.shouldRenderAtSqrDistance(1.0E12), "the cog is pickable and rendered at any distance");
        section("8. stray cog");
    }

    // 9. Whole chain ----------------------------------------------------------------------------------------

    static void wholeChain() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        HeaterFireboxBlockEntity fire = firebox(level, core.below());
        fire.slots.set(0, new ItemStack(Items.COAL, 64));
        MachineStirlingBlockEntity engine = stirling(level, core, Direction.NORTH);
        cable(level, new BlockPos(2, 1, 0));
        cable(level, new BlockPos(3, 1, 0));
        BatterySocketBlockEntity socket = socket(level, new BlockPos(4, 1, 0), Direction.WEST);
        socket.updateEntity();
        net(level);

        long produced = 0;
        int steadyTicks = 0;
        for(int t = 1; t <= 1_200; t++) {
            level.time++;
            fire.updateEntity();
            int before = fire.heatEnergy;
            engine.updateEntity();
            int removed = before - fire.heatEnergy;
            long output = engine.powerBuffer;
            check(output == (long) (removed * 0.5), "tick " + t + ": the engine output is half the heat it removed (truncated)");
            long stored = socket.getPower();
            socket.updateEntity();
            transfer(level);
            check(socket.getPower() - stored == output && engine.powerBuffer == 0, "tick " + t + ": the socket gains exactly the engine output");
            produced += output;
            if(t > 1_000 && output == 100) steadyTicks++;
        }
        check(socket.getPower() == produced && steadyTicks == 200, "the socket holds everything produced; the last 200 ticks are steady 100 HE/t");

        BlockPos socketPos = socket.getBlockPos();
        Level reload = level();
        HeaterFireboxBlockEntity fire2 = firebox(reload, core.below());
        Goal8MachineAccess.load(fire2, Goal8MachineAccess.save(fire));
        MachineStirlingBlockEntity engine2 = stirling(reload, core, Direction.NORTH);
        CompoundTag engineTag = new CompoundTag();
        engine.saveAdditional(engineTag, null);
        engine2.loadAdditional(engineTag, null);
        BatterySocketBlockEntity socket2 = socket(reload, socketPos, Direction.WEST);
        Goal8MachineAccess.load(socket2, Goal8MachineAccess.save(socket));
        check(fire2.heatEnergy == fire.heatEnergy && fire2.burnTime == fire.burnTime && fire2.burnHeat == 200
                        && fire2.slots.get(0).getCount() == fire.slots.get(0).getCount(),
                "the firebox reloads its heat, burn state and remaining coal");
        check(engine2.hasCog && engine2.powerBuffer == engine.powerBuffer && engine2.getOverspeed() == 0, "the engine reloads with its cog and buffer");
        check(socket2.getPower() == socket.getPower() && socket2.redLow == socket.redLow && socket2.redHigh == socket.redHigh,
                "the socket reloads its pack charge and modes");

        reset();
        cable(reload, new BlockPos(2, 1, 0));
        cable(reload, new BlockPos(3, 1, 0));
        socket2.updateEntity();
        net(reload);
        boolean resumed = true;
        for(int t = 0; t < 20; t++) {
            reload.time++;
            fire2.updateEntity();
            engine2.updateEntity();
            long stored = socket2.getPower();
            socket2.updateEntity();
            transfer(reload);
            resumed &= socket2.getPower() - stored == 100;
        }
        check(resumed, "the reloaded chain resumes at 100 HE/t without a warm-up");
        section("9. whole chain");
    }

    public static void main(String[] args) {
        heatAndPower();
        gear();
        overspeed();
        fireboxPairing();
        connections();
        saveAndSync();
        itemsAndRecipes();
        strayCog();
        wholeChain();
        System.out.println("Goal 8 checks: " + checks);
    }
}
