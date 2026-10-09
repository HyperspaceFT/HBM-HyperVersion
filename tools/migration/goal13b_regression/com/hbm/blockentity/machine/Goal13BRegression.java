package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.Goal12AProxyAccess;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.Goal11ABlockAccess;
import com.hbm.blocks.machine.Goal13BBlockAccess;
import com.hbm.blocks.machine.MachineArcFurnaceBlock;
import com.hbm.inventory.menus.MachineArcFurnaceMenu;
import com.hbm.inventory.recipes.ArcFurnaceRecipes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.items.machine.ArcElectrodeItem;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.main.NuclearTechMod;
import com.hbm.particle.vanilla.NbtParticleOptions;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.hbm.util.particle.ParticleUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Goal 13B machine world: the production MachineArcFurnaceBlock, MachineArcFurnaceBlockEntity, MachineArcFurnaceMenu, ArcElectrodeItem and
 * ArcFurnaceRecipes with the Goal 13A machine world (networks, proxies, the production upgrade manager, the assembler, the Goal 11A block
 * placement model). Expected behaviour is read from the original (Hbm-s-Nuclear-Tech-GIT d7ef2df), not from the NEO classes under test:
 * TileEntityMachineArcFurnaceLarge.java:56-62 (maxPower 2,500,000), :80-82 (input sizes 1 / 4 / 8 / 16 by speed upgrade), :105-110 (upgrades
 * through UpgradeManagerNT slots 4,4), :117-160 (battery slot 3, loadIngredients only while the lid is open, consumption 1,000 x 5^upgrade,
 * a closed lid needed, duration 400 / (2 x upgrade + 1) ticks of 1/duration, process at progress 1, delay 120 / (0.5 x upgrade + 1), the lid
 * moves 1 / (60 / (0.5 x upgrade + 1)) per tick, power must cover the consumption), :162-164 (electrode states, hasMaterial), :187
 * (networkPackNT(150)), :188-258 (client: lid approach, wgh_start loop 0.75 / 15 / 1.0 / 5, wgh_stop once 0 or 1 is reached, electric hum
 * 1.5 / 15 / 0.75 / 5, smoke when the lid rises, flames when it falls), :263-301 (loadIngredients), :303-316 (decideElectrodeState),
 * :318-354 (process: output stack x input count, every electrode damaged, burnt at the maximum), :356-374 (hasIngredients, hasElectrodes),
 * :376-416 (slot rules), :547-564 (ports), :566-624 (serialize / NBT, the liquid mode left out), :708-727 (upgrade info);
 * ItemArcElectrode.java:11-60 (stack size 1, durability, damage, maximum 10 / 100 / 500 / 1500, the bar); MachineArcFurnaceLarge.java:33-65
 * (dimensions {4,0,2,2,2,2}, offset 2, the extra box {4,0,3,-2,1,1}, the six extras); ContainerMachineArcFurnaceLarge.java:26-35 (slots);
 * MultiblockHandlerXR.java rotate and fillSpace. ForgeDirection.getRotation(UP) is Forge 1.7.10's ROTATION_MATRIX[UP] (north -> east).
 */
public class Goal13BRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    static final MachineArcFurnaceBlock FURNACE = new MachineArcFurnaceBlock(new Block.Properties());
    static final Direction[] HORIZONTALS = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };
    static Path out;
    /** The quartz block as the table registers it (Blocks.QUARTZ_BLOCK), not the stand-in Items class's own object. */
    static final Item QUARTZ_BLOCK = Blocks.QUARTZ_BLOCK.asItem();

    // ---- Original numbers, independent of the NEO constants under test ------------------------------------------------
    static final long MAX_POWER = 2_500_000L;
    static final int[] INPUT_CAP = { 1, 4, 8, 16 };
    static final long[] CONSUMPTION = { 1_000L, 5_000L, 25_000L, 125_000L };
    static final int[] DURATION = { 400, 133, 80, 57 };
    static final int[] DELAY = { 120, 80, 60, 48 };
    static final double[] LID_DIVISOR = { 60, 40, 30, 24 };
    static final int[] ELECTRODE_MAX = { 10, 100, 500, 1500 };
    static final int[][] MAIN_DIM = { { 4, 0, 2, 2, 2, 2 } };
    static final int[] EXTRA_DIM = { 4, 0, 3, -2, 1, 1 };
    static final int OFFSET = 2;

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

    // ---- The original state machine as a float model (the tick counts follow the original's float arithmetic) -------------------------

    /** Ticks until the lid reaches 0 from 1 (original :131: lid -= 1F / (60F / (upgrade * 0.5 + 1)); clamp at 0). */
    static int closeTicks(int u) {
        float lid = 1F;
        int n = 0;
        while(lid > 0) {
            lid -= 1F / (60F / (u * 0.5 + 1));
            if(lid < 0) lid = 0;
            n++;
        }
        return n;
    }

    /** The lid after `ticks` ticks of opening from 0 (original :153-156). */
    static float openLid(int u, int ticks) {
        float lid = 0F;
        for(int i = 0; i < ticks; i++) {
            if(lid < 1) {
                lid += 1F / (60F / (u * 0.5 + 1));
                if(lid > 1) lid = 1;
            }
        }
        return lid;
    }

    /** Ticks of progress += 1F / duration until it reaches 1 (original :137-141). */
    static int processTicks(int u) {
        int duration = 400 / (u * 2 + 1);
        float progress = 0;
        int n = 0;
        do {
            progress += 1F / duration;
            n++;
        } while(progress < 1F);
        return n;
    }

    // ---- World helpers (the Goal 11C / 12B patterns) ---------------------------------------------------------------------------

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache.cache.clear();
        DummyableBlock.safeRem = false;
        Block.DROPS.clear();
        ParticleUtil.ADDED.clear();
        AudioWrapper.CREATED.clear();
        NuclearTechMod.proxy.localSounds.clear();
        NuclearTechMod.proxy.player = null;
        ArcFurnaceRecipes recipes = new ArcFurnaceRecipes();
        recipes.deleteRecipes();
        recipes.registerDefaults();
        Items.SAND.tags.clear();
        Items.RED_SAND.tags.clear();
        Items.SAND.tags.add("minecraft:sand");
        Items.RED_SAND.tags.add("minecraft:sand");
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        level.random.setSeed(12L);
        return level;
    }

    static BlockState facing(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        return state;
    }

    static MachineArcFurnaceBlockEntity bare(Level level, BlockPos pos) {
        MachineArcFurnaceBlockEntity be = new MachineArcFurnaceBlockEntity(pos, facing(level, pos, Direction.NORTH));
        level.put(be);
        return be;
    }

    static void tick(Level level, MachineArcFurnaceBlockEntity be) {
        level.time++;
        be.updateEntity();
    }

    static ItemStack upgrade(int tier) {
        return new ItemStack(new MachineUpgradeItem(new Item.Properties(), UpgradeType.SPEED, tier));
    }

    static ItemStack electrode(int type) {
        return new ItemStack(new Item[] { NtmItems.ARC_ELECTRODE_GRAPHITE.get(), NtmItems.ARC_ELECTRODE_LANTHANIUM.get(), NtmItems.ARC_ELECTRODE_DESH.get(),
                NtmItems.ARC_ELECTRODE_SATURNITE.get() }[type]);
    }

    static Item burnt(int type) {
        return new Item[] { NtmItems.ARC_ELECTRODE_GRAPHITE_BURNT.get(), NtmItems.ARC_ELECTRODE_LANTHANIUM_BURNT.get(), NtmItems.ARC_ELECTRODE_DESH_BURNT.get(),
                NtmItems.ARC_ELECTRODE_SATURNITE_BURNT.get() }[type];
    }

    /** A furnace with three graphite electrodes, a speed upgrade of tier u in slot 4, full power and an open lid. */
    static MachineArcFurnaceBlockEntity ready(Level level, int u) {
        MachineArcFurnaceBlockEntity be = bare(level, new BlockPos(0, 64, 0));
        for(int i = 0; i < 3; i++) be.setItem(i, electrode(0));
        if(u > 0) be.setItem(4, upgrade(u));
        be.power = MAX_POWER;
        be.lid = 1F;
        return be;
    }

    static int durability(ItemStack stack) {
        Object value = stack.get(NtmDataComponents.ARC_ELECTRODE_DURABILITY);
        return value == null ? 0 : (Integer) value;
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

    /** A battery item holding its own charge (the production Library.chargeTEFromItems discharges through IBatteryItem). */
    static class TestBattery extends Item implements IBatteryItem {
        long charge;

        TestBattery(long charge) {
            super("hbmsntm:test_battery");
            this.charge = charge;
        }

        public void chargeBattery(ItemStack stack, long i) { charge += i; }
        public void setCharge(ItemStack stack, long i) { charge = i; }
        public void dischargeBattery(ItemStack stack, long i) { charge -= i; }
        public long getCharge(ItemStack stack) { return charge; }
        public long getMaxCharge(ItemStack stack) { return 1_000_000L; }
        public long getChargeRate(ItemStack stack) { return 1_000L; }
        public long getDischargeRate(ItemStack stack) { return 50_000L; }
    }

    // ---- 3m. Electrodes ----------------------------------------------------------------------------------------------------------

    static void electrodes() {
        reset();
        for(int type = 0; type < 4; type++) {
            ItemStack stack = electrode(type);
            int max = ELECTRODE_MAX[type];
            ArcElectrodeItem item = (ArcElectrodeItem) stack.getItem();
            check(item.getMaxDurability() == max && ArcElectrodeItem.getMaxDurability(stack) == max && stack.getMaxStackSize() == 1,
                    "electrode " + type + " (graphite, lanthanium, desh, saturnite): maximum " + max + " uses and a stack size of 1 (original ItemArcElectrode.java:14, :48-59): "
                            + item.getMaxDurability() + ", stack " + stack.getMaxStackSize());
            check(item.getBurnt() == burnt(type), "electrode " + type + " burns into the matching burnt item");
            check(ArcElectrodeItem.getDurability(stack) == 0 && stack.get(NtmDataComponents.ARC_ELECTRODE_DURABILITY) == null && !item.isBarVisible(stack),
                    "a new electrode carries no component, reads as unused and shows no bar");
            boolean early = false;
            for(int use = 1; use < max; use++) {
                early |= ArcElectrodeItem.damage(stack);
                if(early) break;
            }
            check(!early && ArcElectrodeItem.getDurability(stack) == max - 1 && durability(stack) == max - 1,
                    "damage returns false for the first " + (max - 1) + " uses and counts them in arc_electrode_durability");
            check(ArcElectrodeItem.damage(stack) && durability(stack) == max, "the use number " + max + " returns true (worn out, original damage(): durability >= maximum)");
            check(ArcElectrodeItem.damage(stack) && durability(stack) == max + 1, "a further use still returns true (>=)");
        }
        // The bar (original showDurabilityBar > 0, getDurabilityForDisplay = durability / maximum; vanilla's width 13 - 13 x ratio).
        ItemStack graphite = electrode(0);
        ArcElectrodeItem item = (ArcElectrodeItem) graphite.getItem();
        for(int use = 1; use <= 10; use++) {
            ArcElectrodeItem.damage(graphite);
            int expectedWidth = Math.round(13.0F - 13.0F * use / 10F);
            check(item.isBarVisible(graphite) && item.getBarWidth(graphite) == expectedWidth, "graphite after " + use + " uses: bar visible, width " + expectedWidth + " of 13: " + item.getBarWidth(graphite));
        }
        ItemStack fresh = electrode(0);
        ArcElectrodeItem.damage(fresh);
        check(item.getBarColor(electrode(0)) == 0x00FF00 && item.getBarColor(graphite) == 0xFF0000 && item.getBarColor(fresh) != 0x00FF00 && item.getBarColor(fresh) != 0xFF0000,
                "the bar runs from green (unused) to red (worn out) through the vanilla hue: " + Integer.toHexString(item.getBarColor(fresh)));
        ItemStack lanthanium = electrode(1);
        for(int use = 0; use < 50; use++) ArcElectrodeItem.damage(lanthanium);
        check(lanthanium.getItem().getBarWidth(lanthanium) == Math.round(13.0F - 13.0F * 50 / 100F), "lanthanium after 50 of 100 uses: width " + lanthanium.getItem().getBarWidth(lanthanium));
        // The tooltip: nothing while unused, one wear line with the numbers afterwards.
        List<Component> tooltip = new ArrayList<>();
        electrode(2).getItem().appendHoverText(electrode(2), null, tooltip, null);
        check(tooltip.isEmpty(), "an unused electrode has no tooltip line");
        ItemStack used = electrode(2);
        for(int use = 0; use < 7; use++) ArcElectrodeItem.damage(used);
        used.getItem().appendHoverText(used, null, tooltip, null);
        check(tooltip.size() == 1 && tooltip.get(0).getString().equals("item.hbmsntm.arc_electrode.wear") && tooltip.get(0).args.length == 2 && tooltip.get(0).args[0].equals(7) && tooltip.get(0).args[1].equals(500),
                "a used electrode shows item.hbmsntm.arc_electrode.wear with its uses and its maximum (7, 500): " + tooltip);
        // Copies keep the wear, a plain item of the same kind with another wear is not the same stack.
        ItemStack copy = used.copy();
        check(durability(copy) == 7 && ItemStack.isSameItemSameComponents(copy, used) && !ItemStack.isSameItemSameComponents(used, electrode(2)),
                "a copy keeps the wear; electrodes of different wear do not stack together");
        check(durability(new ItemStack(burnt(0))) == 0 && !(burnt(0) instanceof ArcElectrodeItem) && new ItemStack(burnt(0)).getMaxStackSize() == 64,
                "a burnt electrode is a plain item (stack size 64, as the original burnt electrode)");
        section("3m. electrodes");
    }

    // ---- 5. State machine --------------------------------------------------------------------------------------------------------

    /** Feeds `count` sand into the queue, runs one whole cycle on a furnace that already did `done` cycles and checks every number. */
    static void cycles(int u, int cycles) {
        reset();
        Level level = level();
        MachineArcFurnaceBlockEntity be = ready(level, u);
        int count = INPUT_CAP[u];
        long consumption = CONSUMPTION[u];
        int packs = be.packs;
        int totalTicks = 0;
        for(int cycle = 1; cycle <= cycles; cycle++) {
            be.slots.set(25, new ItemStack(Items.SAND, count));
            long power = be.power;
            // the lid closes
            int closed = 0;
            tick(level, be);
            closed++;
            check(be.slots.get(25).isEmpty() && be.slots.get(5).getItem() == Items.SAND && be.slots.get(5).getCount() == count,
                    "upgrade " + u + ": while the lid is open the queue moves into the first grid slot (" + count + " sand, the input size of the upgrade)");
            while(be.lid > 0 && closed < 1000) {
                check(!be.isProgressing && be.progress == 0F && be.power == power, "upgrade " + u + ": the lid closing draws no power and makes no progress");
                tick(level, be);
                closed++;
            }
            check(closed == closeTicks(u) && be.lid == 0F, "upgrade " + u + ": the lid closes in " + closeTicks(u) + " ticks (1 / (60 / (0.5 x upgrade + 1)) per tick): " + closed);
            totalTicks += closed;
            check(be.hasMaterial, "the furnace reports material while it has some");
            // the arc
            int processing = 0;
            int guard = 0;
            long spent = 0;
            while(be.delay == 0 && guard++ < 5000) {
                // The 2,500,000 HE buffer lasts 20 ticks at upgrade 3 (125,000 HE/t): the network refills it, as it would in the game.
                be.power = MAX_POWER;
                tick(level, be);
                totalTicks++;
                if(be.isProgressing) {
                    processing++;
                    spent += MAX_POWER - be.power;
                }
            }
            check(processing == processTicks(u) && processing >= DURATION[u] && processing <= DURATION[u] + 1,
                    "upgrade " + u + ": processing takes " + processTicks(u) + " ticks (duration " + DURATION[u] + " = 400 / (2 x upgrade + 1), float steps of 1 / duration): " + processing);
            check(spent == processing * consumption,
                    "upgrade " + u + ": it draws " + consumption + " HE per processing tick (1,000 x 5^upgrade): " + spent + " for " + processing + " ticks");
            ItemStack result = be.slots.get(5);
            check(result.getItem() == NtmItems.NUGGET_SILICON.get() && result.getCount() == count && be.progress == 0F && be.delay == DELAY[u],
                    "upgrade " + u + ": " + count + " sand become " + count + " silicon nuggets (1 per sand, output stack x input count) and the delay is " + DELAY[u] + " (120 / (0.5 x upgrade + 1)): "
                            + result + ", delay " + be.delay);
            for(int i = 0; i < 3; i++) {
                check(durability(be.slots.get(i)) == cycle && be.slots.get(i).getItem() == NtmItems.ARC_ELECTRODE_GRAPHITE.get(),
                        "upgrade " + u + ": electrode " + i + " has been used " + cycle + " time(s): " + durability(be.slots.get(i)));
            }
            // the delay runs down while the lid reopens; nothing starts again without material
            for(int i = 0; i < DELAY[u]; i++) {
                tick(level, be);
                totalTicks++;
                check(!be.isProgressing && be.progress == 0F, "no progress without material");
            }
            check(be.delay == 0 && be.lid == openLid(u, DELAY[u]),
                    "upgrade " + u + ": after " + DELAY[u] + " ticks the delay is 0 and the lid has reopened to " + openLid(u, DELAY[u]) + ": " + be.lid);
            check(!be.hasMaterial, "no material after the run");
            // take the nuggets out, as a player would
            be.slots.set(5, ItemStack.EMPTY);
        }
        check(be.packs - packs == totalTicks && be.packRange == 150, "every server tick sends one sync pack of range 150 (networkPackNT(150)): " + (be.packs - packs) + " packs in " + totalTicks + " ticks");
        info("upgrade " + u + ": close " + closeTicks(u) + ", process " + processTicks(u) + " at " + consumption + " HE/t, delay " + DELAY[u] + " ticks");
    }

    static void machine() {
        for(int u = 0; u <= 3; u++) cycles(u, u == 0 ? 3 : 1);

        // No power: nothing at all happens.
        reset();
        Level level = level();
        MachineArcFurnaceBlockEntity be = ready(level, 0);
        be.power = 0;
        be.slots.set(25, new ItemStack(Items.SAND));
        be.lid = 0.5F;
        for(int i = 0; i < 30; i++) tick(level, be);
        check(be.lid == 0.5F && be.progress == 0F && !be.isProgressing && be.slots.get(25).isEmpty() && be.slots.get(5).getItem() == Items.SAND && be.slots.get(5).getCount() == 1
                        && durability(be.slots.get(0)) == 0 && be.delay == 0,
                "no power: the lid stays at 0.5, nothing progresses or wears for 30 ticks; the queue still loads into the grid while the lid is open (original :120 sits outside the power test)");
        // Less power than the consumption: a closed furnace waits.
        be.lid = 0F;
        be.slots.set(5, new ItemStack(Items.SAND));
        be.slots.set(25, ItemStack.EMPTY);
        be.power = CONSUMPTION[0] - 1;
        for(int i = 0; i < 20; i++) tick(level, be);
        check(be.power == CONSUMPTION[0] - 1 && be.progress == 0F && !be.isProgressing && be.slots.get(5).getItem() == Items.SAND,
                "less power than 1,000 HE with a closed lid: no progress, no power used, the sand stays");
        be.power = CONSUMPTION[0];
        tick(level, be);
        check(be.isProgressing && be.power == 0 && be.progress > 0F, "with exactly 1,000 HE it starts, using all of it");
        // A battery in slot 3 feeds the furnace (Library.chargeTEFromItems, at most the discharge rate per tick).
        reset();
        level = level();
        be = bare(level, new BlockPos(0, 64, 0));
        TestBattery battery = new TestBattery(120_000L);
        be.setItem(3, new ItemStack(battery));
        for(int i = 0; i < 3; i++) tick(level, be);
        check(be.power == 120_000L && battery.charge == 0, "a battery gives at most 50,000 HE per tick (its discharge rate) until it is empty: " + be.power);

        // Missing electrodes and burnt electrodes: the lid opens, nothing is processed.
        for(int variant = 0; variant < 5; variant++) {
            reset();
            level = level();
            be = ready(level, 0);
            be.lid = 0F;
            be.slots.set(5, new ItemStack(Items.SAND));
            String what;
            switch(variant) {
                case 0 -> { be.slots.set(0, ItemStack.EMPTY); what = "the first electrode missing"; }
                case 1 -> { be.slots.set(1, ItemStack.EMPTY); what = "the second electrode missing"; }
                case 2 -> { be.slots.set(2, ItemStack.EMPTY); what = "the third electrode missing"; }
                case 3 -> { be.slots.set(1, new ItemStack(burnt(0))); what = "a burnt electrode in the second slot"; }
                default -> { for(int i = 0; i < 3; i++) be.slots.set(i, ItemStack.EMPTY); what = "no electrodes"; }
            }
            check(!be.hasElectrodes(), what + ": hasElectrodes is false");
            for(int i = 0; i < 80; i++) tick(level, be);
            check(be.lid == 1F && be.progress == 0F && !be.isProgressing && be.power == MAX_POWER && be.slots.get(5).getItem() == Items.SAND && be.slots.get(5).getCount() == 1,
                    what + ": the lid opens fully, nothing is processed, no power is used, the sand stays");
        }
        // The queue is not touched while the lid is closed.
        reset();
        level = level();
        be = ready(level, 0);
        be.lid = 0F;
        be.slots.set(25, new ItemStack(Items.SAND));
        be.loadIngredients();
        check(be.slots.get(25).isEmpty() && be.slots.get(5).getItem() == Items.SAND,
                "loadIngredients itself moves the queue (the lid is only checked by the caller)");
        reset();
        level = level();
        be = ready(level, 0);
        be.lid = 0F;
        be.power = 0;
        be.slots.set(25, new ItemStack(Items.SAND));
        tick(level, be);
        check(be.slots.get(25).getCount() == 1 && be.slots.get(5).isEmpty(), "with the lid closed (0) the queue is not loaded in a tick (original :120: if(lid > 0) loadIngredients())");
        section("5. state machine");
    }

    // ---- 5w. Electrode wear and the burnt replacement ------------------------------------------------------------------------------

    static void wear() {
        // Ten full cycles burn graphite electrodes; each cycle adds one use.
        reset();
        Level level = level();
        MachineArcFurnaceBlockEntity be = ready(level, 3);
        List<String> wrong = new ArrayList<>();
        for(int cycle = 1; cycle <= 10; cycle++) {
            be.lid = 1F;
            be.delay = 0;
            be.slots.set(5, ItemStack.EMPTY);
            be.slots.set(25, new ItemStack(Items.SAND));
            int guard = 0;
            while(be.delay == 0 && guard++ < 2000) { be.power = MAX_POWER; tick(level, be); }
            for(int i = 0; i < 3; i++) {
                ItemStack slot = be.slots.get(i);
                if(cycle < 10 && !(slot.getItem() == NtmItems.ARC_ELECTRODE_GRAPHITE.get() && durability(slot) == cycle)) wrong.add("cycle " + cycle + " slot " + i + ": " + slot);
                if(cycle == 10 && !(slot.getItem() == NtmItems.ARC_ELECTRODE_GRAPHITE_BURNT.get() && slot.getCount() == 1)) wrong.add("cycle 10 slot " + i + ": " + slot);
            }
            be.power = MAX_POWER;
        }
        check(wrong.isEmpty(), "graphite electrodes: +1 use per process, burnt graphite electrodes (count 1) replace all three at the 10th: " + wrong);
        check(!be.hasElectrodes() && be.slots.get(5).getItem() == NtmItems.NUGGET_SILICON.get(), "burnt electrodes no longer count as electrodes");
        be.slots.set(5, ItemStack.EMPTY);
        be.slots.set(25, new ItemStack(Items.SAND));
        be.delay = 0;
        be.lid = 0F;
        be.power = MAX_POWER;
        for(int i = 0; i < 100; i++) tick(level, be);
        check(be.lid == 1F && be.slots.get(25).isEmpty() && be.slots.get(5).getItem() == Items.SAND && be.slots.get(5).getCount() == 1 && !be.isProgressing && be.progress == 0F
                        && be.power == MAX_POWER,
                "with burnt electrodes the furnace opens, loads the sand and never processes it (no progress, no power used)");
        // The four materials and the mixed case.
        for(int type = 0; type < 4; type++) {
            reset();
            level = level();
            be = bare(level, new BlockPos(0, 64, 0));
            for(int i = 0; i < 3; i++) {
                ItemStack stack = electrode(type);
                for(int use = 0; use < ELECTRODE_MAX[type] - 1 - (i == 0 ? 0 : 5); use++) ArcElectrodeItem.damage(stack);
                be.slots.set(i, stack);
            }
            be.slots.set(5, new ItemStack(Items.SAND));
            be.lid = 0F;
            be.power = MAX_POWER;
            int guard = 0;
            while(be.delay == 0 && guard++ < 2000) { be.power = MAX_POWER; tick(level, be); }
            check(be.slots.get(0).getItem() == burnt(type) && be.slots.get(0).getCount() == 1,
                    "electrode type " + type + " at " + (ELECTRODE_MAX[type] - 1) + " uses becomes " + burnt(type).getClass().getSimpleName() + " (its own burnt item) at the next process");
            check(be.slots.get(1).getItem() == electrode(type).getItem() && durability(be.slots.get(1)) == ELECTRODE_MAX[type] - 5
                            && be.slots.get(2).getItem() == electrode(type).getItem() && durability(be.slots.get(2)) == ELECTRODE_MAX[type] - 5,
                    "type " + type + ": the other two electrodes are only worn (" + (ELECTRODE_MAX[type] - 6) + " -> " + (ELECTRODE_MAX[type] - 5) + ") and stay electrodes");
        }
        section("5w. electrode wear");
    }

    // ---- 5l. loadIngredients -------------------------------------------------------------------------------------------------------

    /** The original cap (TileEntityMachineArcFurnaceLarge.java:80-82, :271-273): min(input size of the upgrade, maxStackSize of the input / output count). */
    static int cap(int u, ItemStack input, int outputCount) {
        return Math.min(INPUT_CAP[u], input.getMaxStackSize() / outputCount);
    }

    static List<Integer> grid(MachineArcFurnaceBlockEntity be) {
        List<Integer> counts = new ArrayList<>();
        for(int i = 5; i < 25; i++) counts.add(be.slots.get(i).getCount());
        return counts;
    }

    static void loading() {
        Object[][] inputs = {
                { Items.SAND, 1 }, { Items.FLINT, 4 }, { Items.QUARTZ, 3 }, { NtmItems.POWDER_QUARTZ.get(), 3 }, { QUARTZ_BLOCK, 12 }, { NtmItems.INGOT_FIBERGLASS.get(), 4 },
                { NtmBlocks.BLOCK_FIBERGLASS.get(), 40 }, { NtmItems.INGOT_ASBESTOS.get(), 4 }, { NtmItems.POWDER_ASBESTOS.get(), 4 }, { NtmBlocks.BLOCK_ASBESTOS.get(), 40 },
                { NtmItems.POWDER_BORAX.get(), 3 } };
        List<String> wrong = new ArrayList<>();
        for(int u = 0; u <= 3; u++) {
            for(Object[] input : inputs) {
                reset();
                Level level = level();
                MachineArcFurnaceBlockEntity be = ready(level, u);
                tick(level, be); // reads the upgrade
                Item item = (Item) input[0];
                int outputCount = (Integer) input[1];
                int cap = cap(u, new ItemStack(item), outputCount);
                be.slots.set(25, new ItemStack(item, 64));
                be.loadIngredients();
                int slots = 0, total = 0;
                boolean even = true;
                List<Integer> counts = grid(be);
                for(int i = 0; i < counts.size(); i++) {
                    int c = counts.get(i);
                    if(c > cap) even = false;
                    if(c > 0) slots++;
                    total += c;
                }
                int expectedSlots = Math.min(20, (64 + cap - 1) / cap);
                int expectedTotal = Math.min(64, 20 * cap);
                if(!even || slots != expectedSlots || total != expectedTotal || be.slots.get(25).getCount() != 64 - expectedTotal)
                    wrong.add("u" + u + " " + item.id + ": cap " + cap + ", grid " + counts + ", queue " + be.slots.get(25).getCount());
            }
        }
        check(wrong.isEmpty(), "loadIngredients moves min(input size of the upgrade 1/4/8/16, input max stack / output count) per grid slot, into as many free slots as needed (sand 1 up to 16, flint 4: 16, "
                + "quartz block 12: 5, fibreglass / asbestos block 40: 1, borax 3: 21 -> 16): " + wrong);
        // Merging into a started stack, other items and queue order.
        reset();
        Level level = level();
        MachineArcFurnaceBlockEntity be = ready(level, 2);
        tick(level, be);
        be.slots.set(5, new ItemStack(Items.SAND, 3));
        be.slots.set(6, new ItemStack(Items.FLINT, 2));
        be.slots.set(25, new ItemStack(Items.SAND, 10));
        be.slots.set(26, new ItemStack(Items.STONE, 5));
        be.slots.set(27, new ItemStack(Items.FLINT, 7));
        be.loadIngredients();
        check(be.slots.get(5).getCount() == 8 && be.slots.get(7).getItem() == Items.SAND && be.slots.get(7).getCount() == 5 && be.slots.get(25).isEmpty(),
                "the queue tops up a started stack to the cap (3 + 5 = 8 at upgrade 2) and puts the rest into the next free slot (5): " + grid(be));
        check(be.slots.get(26).getItem() == Items.STONE && be.slots.get(26).getCount() == 5, "a queue item without a recipe is left where it is");
        check(be.slots.get(6).getCount() == 8 && be.slots.get(8).getItem() == Items.FLINT && be.slots.get(8).getCount() == 1 && be.slots.get(27).isEmpty(),
                "flint tops up the flint stack (2 + 6 = 8) and the last flint goes to the next free slot: " + grid(be));
        // A full grid keeps the queue.
        reset();
        level = level();
        be = ready(level, 3);
        tick(level, be);
        for(int i = 5; i < 25; i++) be.slots.set(i, new ItemStack(QUARTZ_BLOCK, 5));
        be.slots.set(25, new ItemStack(QUARTZ_BLOCK, 9));
        be.loadIngredients();
        check(be.slots.get(25).getCount() == 9 && grid(be).stream().allMatch(c -> c == 5), "a full grid of capped stacks takes nothing from the queue");
        section("5l. queue loading");
    }

    // ---- 5e. Electrode states, slots, menu -----------------------------------------------------------------------------------------

    static void slots() {
        reset();
        Level level = level();
        MachineArcFurnaceBlockEntity be = bare(level, new BlockPos(0, 64, 0));
        be.setItem(0, electrode(0));
        ItemStack worn = electrode(1);
        ArcElectrodeItem.damage(worn);
        be.setItem(1, worn);
        be.setItem(2, new ItemStack(burnt(2)));
        be.decideElectrodeState();
        check(be.electrodeStates[0] == MachineArcFurnaceBlockEntity.ELECTRODE_FRESH && be.electrodeStates[1] == MachineArcFurnaceBlockEntity.ELECTRODE_USED
                        && be.electrodeStates[2] == MachineArcFurnaceBlockEntity.ELECTRODE_DEPLETED
                        && MachineArcFurnaceBlockEntity.ELECTRODE_NONE == 0 && MachineArcFurnaceBlockEntity.ELECTRODE_FRESH == 1 && MachineArcFurnaceBlockEntity.ELECTRODE_USED == 2
                        && MachineArcFurnaceBlockEntity.ELECTRODE_DEPLETED == 3,
                "decideElectrodeState: a new electrode FRESH (1), one with durability > 0 USED (2), a burnt one DEPLETED (3), NONE is 0 (original :303-316)");
        be.slots.set(0, ItemStack.EMPTY);
        be.slots.set(1, new ItemStack(Items.STONE));
        be.decideElectrodeState();
        check(be.electrodeStates[0] == 0 && be.electrodeStates[1] == 0, "an empty slot or another item is NONE");
        be.slots.set(0, electrode(0));
        be.isProgressing = true;
        be.decideElectrodeState();
        check(be.electrodeStates[0] == MachineArcFurnaceBlockEntity.ELECTRODE_USED, "a new electrode is USED while the furnace is progressing");
        be.isProgressing = false;

        // Slot rules (original isItemValidForSlot / canInsertItem / canExtractItem; slots 3 and 4 follow the arc welder for the menu).
        ItemStack sand = new ItemStack(Items.SAND), stone = new ItemStack(Items.STONE), nugget = new ItemStack(NtmItems.NUGGET_SILICON.get());
        ItemStack battery = new ItemStack(new TestBattery(1));
        check(be.canPlaceItem(0, electrode(3)) && be.canPlaceItem(2, electrode(0)) && !be.canPlaceItem(0, new ItemStack(burnt(0))) && !be.canPlaceItem(1, sand)
                        && be.canPlaceItem(3, battery) && !be.canPlaceItem(3, sand) && be.canPlaceItem(4, upgrade(1)) && !be.canPlaceItem(4, battery)
                        && be.canPlaceItem(5, sand) && be.canPlaceItem(24, new ItemStack(Items.FLINT)) && !be.canPlaceItem(5, stone) && !be.canPlaceItem(5, nugget)
                        && be.canPlaceItem(25, sand) && be.canPlaceItem(29, new ItemStack(Items.QUARTZ)) && !be.canPlaceItem(29, stone),
                "canPlaceItem: electrodes only in 0-2 (not burnt ones), batteries in 3, upgrades in 4, items with a recipe in 5-29");
        check(be.canPlaceItemThroughFace(0, electrode(1), Direction.UP) && !be.canPlaceItemThroughFace(0, sand, Direction.UP) && !be.canPlaceItemThroughFace(0, new ItemStack(burnt(1)), Direction.UP)
                        && !be.canPlaceItemThroughFace(3, battery, Direction.UP) && !be.canPlaceItemThroughFace(4, upgrade(1), Direction.UP)
                        && !be.canPlaceItemThroughFace(5, sand, Direction.UP) && !be.canPlaceItemThroughFace(24, sand, Direction.UP)
                        && be.canPlaceItemThroughFace(25, sand, Direction.UP) && be.canPlaceItemThroughFace(29, new ItemStack(Items.FLINT), Direction.UP) && !be.canPlaceItemThroughFace(25, stone, Direction.UP),
                "automation inserts electrodes into 0-2 and recipe items into the queue 25-29 only (original canInsertItem)");
        be.lid = 1F;
        boolean open = be.canTakeItemThroughFace(0, new ItemStack(burnt(0)), Direction.UP) && !be.canTakeItemThroughFace(0, electrode(0), Direction.UP)
                && be.canTakeItemThroughFace(5, nugget, Direction.UP) && !be.canTakeItemThroughFace(5, sand, Direction.UP)
                && be.canTakeItemThroughFace(25, stone, Direction.UP) && !be.canTakeItemThroughFace(25, sand, Direction.UP) && !be.canTakeItemThroughFace(3, battery, Direction.UP)
                && !be.canTakeItemThroughFace(4, upgrade(1), Direction.UP);
        be.lid = 0.99F;
        boolean almost = !be.canTakeItemThroughFace(0, new ItemStack(burnt(0)), Direction.UP) && be.canTakeItemThroughFace(5, nugget, Direction.UP);
        be.lid = 0F;
        boolean closed = !be.canTakeItemThroughFace(0, new ItemStack(burnt(0)), Direction.UP) && !be.canTakeItemThroughFace(5, nugget, Direction.UP)
                && be.canTakeItemThroughFace(25, stone, Direction.UP) && !be.canTakeItemThroughFace(25, sand, Direction.UP);
        check(open && almost && closed,
                "canTakeItemThroughFace: burnt electrodes only with the lid fully open (1), finished grid items while it is open (> 0), queue items without a recipe always, never an electrode, input or 3-4 "
                        + "(open " + open + ", almost open " + almost + ", closed " + closed + ")");
        int[] expected = new int[28];
        int n = 0;
        for(int i : new int[] { 0, 1, 2 }) expected[n++] = i;
        for(int i = 5; i <= 29; i++) expected[n++] = i;
        for(Direction d : Direction.values()) check(java.util.Arrays.equals(be.getSlotsForFace(d), expected), "getSlotsForFace(" + d + ") is 0-2 and 5-29 (original getAccessibleSlotsFromSide)");
        // The speed upgrade.
        int sounds = level.sounds.size();
        be.setItem(4, upgrade(2));
        check(level.sounds.size() == sounds + 1 && level.sounds.get(level.sounds.size() - 1).event() == NtmSoundEvents.UPGRADE_PLUG.get(), "an upgrade put into slot 4 plays the upgrade plug sound once");
        be.setItem(3, battery);
        check(level.sounds.size() == sounds + 1, "a battery in slot 3 plays none");
        tick(level, be);
        check(be.getUpgradeLevel() == 2 && be.getMaxInputSize() == 8 && be.getConsumption() == CONSUMPTION[2], "the speed upgrade of tier 2 gives input size 8 and 25,000 HE/t");
        check(be.getValidUpgrades().equals(Map.of(UpgradeType.SPEED, 3)) && be.canProvideInfo(UpgradeType.SPEED, 1, null) && !be.canProvideInfo(UpgradeType.POWER, 1, null)
                        && !be.canProvideInfo(UpgradeType.EFFECT, 1, null),
                "only SPEED upgrades are valid, up to tier 3 (original :722-727)");
        for(int lvl = 1; lvl <= 3; lvl++) {
            List<Component> info = new ArrayList<>();
            be.provideInfo(UpgradeType.SPEED, lvl, info, null);
            String delay = "-" + (100 - 100 / (lvl * 2 + 1)) + "%";
            String power = "+" + ((int) Math.pow(5, lvl) * 100 - 100) + "%";
            check(info.size() == 3 && info.get(1).args[0].equals(delay) && info.get(2).args[0].equals(power), "upgrade info for tier " + lvl + ": delay " + delay + ", consumption " + power + " (original :714-719)");
        }

        // The menu: slot positions of the original container.
        Inventory inventory = new Inventory();
        MachineArcFurnaceMenu menu = new MachineArcFurnaceMenu(1, inventory, be);
        List<String> positions = new ArrayList<>();
        for(int i = 0; i < 3; i++) if(slotAt(menu, i, 62 + i * 18, 22)) positions.add("electrode " + i);
        if(slotAt(menu, 3, 8, 108)) positions.add("battery");
        if(slotAt(menu, 4, 152, 108)) positions.add("upgrade");
        for(int i = 0; i < 4; i++) for(int j = 0; j < 5; j++) if(slotAt(menu, 5 + j + i * 5, 44 + j * 18, 54 + i * 18)) positions.add("input " + (5 + j + i * 5));
        for(int i = 0; i < 5; i++) if(slotAt(menu, 25 + i, 44 + i * 18, 129)) positions.add("queue " + (25 + i));
        for(int i = 0; i < 3; i++) for(int j = 0; j < 9; j++) if(slotAt(menu, 30 + j + i * 9, 8 + j * 18, 174 + i * 18)) positions.add("inventory");
        for(int i = 0; i < 9; i++) if(slotAt(menu, 57 + i, 8 + i * 18, 232)) positions.add("hotbar");
        check(menu.slots.size() == 66 && positions.size() == 3 + 1 + 1 + 20 + 5 + 27 + 9,
                "the menu slots are the original container's: electrodes (62 + 18i, 22), battery (8, 108), upgrade (152, 108), the 4 x 5 inputs from (44, 54), the queue from (44, 129), the player inventory from (8, 174) "
                        + "and the hotbar at y 232: " + menu.slots.size() + " slots, " + positions.size() + " in place");
        be.setItem(4, upgrade(0));
        be.setItem(4, ItemStack.EMPTY);
        tick(level, be);
        Slot grid = menu.slots.get(5);
        check(grid.mayPlace(new ItemStack(Items.SAND, 1)) && !grid.mayPlace(new ItemStack(Items.SAND, 2)) && grid.mayPlace(new ItemStack(Items.FLINT, 1)) && !grid.mayPlace(stone) && !grid.getClass().equals(Slot.class)
                        && grid.getMaxStackSize() == 1,
                "without an upgrade a grid slot takes one input item at a time (SlotArcFurnace): sand 1 yes, 2 no, stone no; an empty slot holds 1");
        be.setItem(4, upgrade(3));
        tick(level, be);
        check(grid.mayPlace(new ItemStack(Items.SAND, 16)) && !grid.mayPlace(new ItemStack(Items.SAND, 17)) && grid.mayPlace(new ItemStack(QUARTZ_BLOCK, 5)) && !grid.mayPlace(new ItemStack(QUARTZ_BLOCK, 6))
                        && grid.mayPlace(new ItemStack(NtmBlocks.BLOCK_ASBESTOS.get(), 1)) && !grid.mayPlace(new ItemStack(NtmBlocks.BLOCK_ASBESTOS.get(), 2)),
                "at upgrade 3 (input size 16) a grid slot takes up to 16 sand, 5 quartz blocks (5 x 12 = 60 <= 64, 6 x 12 = 72 is not) and one asbestos block (40 each)");
        be.slots.set(5, new ItemStack(Items.SAND, 3));
        check(grid.getMaxStackSize() == 16, "a filled grid slot shows the upgrade's input size (16)");
        // Shift-click.
        inventory.items.set(0, electrode(2));
        inventory.items.set(1, battery.copy());
        inventory.items.set(2, new ItemStack(Items.FLINT, 5));
        inventory.items.set(3, upgrade(1));
        be.slots.set(0, ItemStack.EMPTY);
        be.slots.set(3, ItemStack.EMPTY);
        be.slots.set(4, ItemStack.EMPTY);
        menu.quickMoveStack(null, 57);
        menu.quickMoveStack(null, 58);
        menu.quickMoveStack(null, 59);
        menu.quickMoveStack(null, 60);
        check(be.slots.get(0).getItem() == electrode(2).getItem() && be.slots.get(3).getItem() instanceof IBatteryItem && be.slots.get(25).getItem() == Items.FLINT && be.slots.get(25).getCount() == 5
                        && be.slots.get(4).getItem() instanceof MachineUpgradeItem,
                "shift-click from the inventory: an electrode goes to the electrode slots, a battery to slot 3, an upgrade to slot 4, other items to the queue");
        menu.quickMoveStack(null, 25);
        check(be.slots.get(25).isEmpty() && inventory.items.stream().anyMatch(s -> s.getItem() == Items.FLINT), "shift-click from the queue moves the items back to the player");
        section("5e. electrode states, slots, menu");
    }

    static boolean slotAt(MachineArcFurnaceMenu menu, int index, int x, int y) {
        Slot slot = menu.slots.get(index);
        return slot.x == x && slot.y == y && slot.getContainerSlot() == (index < 30 ? index : slot.getContainerSlot());
    }

    // ---- 9m. Save, sync, client ----------------------------------------------------------------------------------------------------

    static void sync() {
        reset();
        Level level = level();
        MachineArcFurnaceBlockEntity be = ready(level, 1);
        tick(level, be);
        be.progress = 0.25F;
        be.lid = 0.5F;
        be.delay = 33;
        be.isProgressing = true;
        be.hasMaterial = true;
        be.power = 123_456L;
        be.electrodeStates[0] = 1;
        be.electrodeStates[1] = 2;
        be.electrodeStates[2] = 3;
        CompoundTag tag = new CompoundTag();
        nbt(be, "saveAdditional", tag);
        Set<String> keys = tag.getAllKeys();
        check(keys.containsAll(Set.of("power", "progress", "lid", "delay", "muffled", "tilted")) && tag.getLong("power") == 123_456L && tag.getFloat("progress") == 0.25F && tag.getFloat("lid") == 0.5F
                        && tag.getInt("delay") == 33 && !keys.contains("liquidMode") && !keys.contains("count"),
                "saveAdditional writes power, progress, lid and delay (original :626-641 without the liquid mode and the molten contents) besides the base fields: " + keys);
        MachineArcFurnaceBlockEntity loaded = bare(level, new BlockPos(20, 64, 0));
        nbt(loaded, "loadAdditional", tag);
        check(loaded.power == 123_456L && loaded.progress == 0.25F && loaded.lid == 0.5F && loaded.delay == 33 && loaded.slots.get(0).getItem() == NtmItems.ARC_ELECTRODE_GRAPHITE.get(),
                "loadAdditional reads them back, with the inventory");
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        be.serialize(buf);
        List<Object> values = buf.values();
        List<Object> expectedValues = List.of(false, false, 123_456L, 0.25F, 0.5F, true, true, (byte) 1, (byte) 2, (byte) 3);
        check(values.equals(expectedValues),
                "serialize: muffled, tilted (base), power, progress, lid, isProgressing, hasMaterial and the three electrode states (original :567-576; no liquid mode): " + values);
        MachineArcFurnaceBlockEntity client = bare(level, new BlockPos(40, 64, 0));
        client.deserialize(buf);
        check(buf.readableBytes() == 0 && client.power == 123_456L && client.progress == 0.25F && client.isProgressing && client.hasMaterial
                        && client.electrodeStates[0] == 1 && client.electrodeStates[1] == 2 && client.electrodeStates[2] == 3,
                "deserialize reads them back and consumes the buffer");
        // The client tick: the lid approaches the synced value in two steps when it is neither 0 nor 1.
        Level clientLevel = level();
        clientLevel.isClientSide = true;
        MachineArcFurnaceBlockEntity c = new MachineArcFurnaceBlockEntity(new BlockPos(0, 64, 0), facing(clientLevel, new BlockPos(0, 64, 0), Direction.NORTH));
        clientLevel.put(c);
        RegistryFriendlyByteBuf sent = new RegistryFriendlyByteBuf();
        be.lid = 0.5F;
        be.serialize(sent);
        c.deserialize(sent);
        float[] seen = new float[4];
        for(int i = 0; i < 4; i++) {
            tick(clientLevel, c);
            seen[i] = c.lid;
        }
        check(seen[0] == 0.25F && seen[1] == 0.5F && seen[2] == 0.5F && seen[3] == 0.5F,
                "client: a synced lid of 0.5 is approached in 2 steps (0 -> 0.25 -> 0.5), then held (original :192-197, syncLid / approachNum 2): " + java.util.Arrays.toString(seen));
        check(c.packs == 0, "the client sends no sync pack");
        // A synced 0 or 1 is taken at once (no approach).
        RegistryFriendlyByteBuf jump = new RegistryFriendlyByteBuf();
        be.lid = 1F;
        be.serialize(jump);
        c.deserialize(jump);
        tick(clientLevel, c);
        check(c.lid == 1F, "a synced lid of 1 is taken at once");
        // Audio: the lid loop while the lid moves, the hum while progressing.
        AudioWrapper.CREATED.clear();
        NuclearTechMod.proxy.localSounds.clear();
        MachineArcFurnaceBlockEntity a = new MachineArcFurnaceBlockEntity(new BlockPos(0, 64, 0), facing(clientLevel, new BlockPos(0, 64, 0), Direction.NORTH));
        clientLevel.put(a);
        a.lid = 0.75F;
        RegistryFriendlyByteBuf audio = new RegistryFriendlyByteBuf();
        be.lid = 1F;
        be.isProgressing = true;
        be.serialize(audio);
        a.deserialize(audio);
        tick(clientLevel, a);
        List<AudioWrapper> loops = AudioWrapper.CREATED;
        AudioWrapper lidLoop = loops.stream().filter(w -> w.event == NtmSoundEvents.WGH_START.get()).findFirst().orElse(null);
        AudioWrapper hum = loops.stream().filter(w -> w.event == NtmSoundEvents.ELECTRIC_HUM_LOOP.get()).findFirst().orElse(null);
        check(lidLoop != null && lidLoop.category == SoundSource.BLOCKS && lidLoop.volume == 0.75F && lidLoop.range == 15F && lidLoop.pitch == 1.0F && lidLoop.keepAlive == 5 && lidLoop.started == 1 && lidLoop.keptAlive == 1,
                "the lid loop wgh_start: blocks, volume 0.75, range 15, pitch 1.0, keep-alive 5, started and kept alive while the lid moves (original :201-204)");
        check(hum != null && hum.volume == 1.5F && hum.range == 15F && hum.pitch == 0.75F && hum.keepAlive == 5 && hum.started == 1 && hum.keptAlive == 1,
                "the electric hum while progressing: volume 1.5, range 15, pitch 0.75, keep-alive 5 (original :216-222)");
        check(NuclearTechMod.proxy.localSounds.size() == 1 && NuclearTechMod.proxy.localSounds.get(0).event() == NtmSoundEvents.WGH_STOP.get() && NuclearTechMod.proxy.localSounds.get(0).volume() == 1F,
                "reaching a fully open lid (0.75 -> 1) plays wgh_stop once at volume 1 (original :212-214)");
        tick(clientLevel, a);
        check(lidLoop.stopped == 1 && hum.stopped == 0 && hum.keptAlive == 2 && NuclearTechMod.proxy.localSounds.size() == 1,
                "the next tick the lid is still: its loop stops, the hum is kept alive, no second wgh_stop");
        RegistryFriendlyByteBuf quiet = new RegistryFriendlyByteBuf();
        be.isProgressing = false;
        be.serialize(quiet);
        a.deserialize(quiet);
        tick(clientLevel, a);
        check(hum.stopped == 1, "the hum stops when the furnace stops progressing");
        // wgh_stop is not played for the jump 0 -> 1.
        NuclearTechMod.proxy.localSounds.clear();
        a.lid = 0F;
        RegistryFriendlyByteBuf opening = new RegistryFriendlyByteBuf();
        be.lid = 1F;
        be.serialize(opening);
        a.deserialize(opening);
        tick(clientLevel, a);
        check(a.lid == 1F && NuclearTechMod.proxy.localSounds.isEmpty(), "a jump from 0 to 1 plays no wgh_stop (original :212: !(prevLid == 0 && lid == 1))");
        // Particles: smoke when the lid rises, flames when it falls over material; only near the player.
        Player player = new Player();
        player.px = 0.5;
        player.py = 68;
        player.pz = 0.5;
        NuclearTechMod.proxy.player = player;
        ParticleUtil.ADDED.clear();
        MachineArcFurnaceBlockEntity s = new MachineArcFurnaceBlockEntity(new BlockPos(0, 64, 0), facing(clientLevel, new BlockPos(0, 64, 0), Direction.NORTH));
        clientLevel.put(s);
        s.lid = 0.25F;
        RegistryFriendlyByteBuf rising = new RegistryFriendlyByteBuf();
        be.lid = 0.5F;
        be.isProgressing = false;
        be.hasMaterial = false;
        be.serialize(rising);
        s.deserialize(rising);
        tick(clientLevel, s);
        List<ParticleUtil.Added> smoke = new ArrayList<>(ParticleUtil.ADDED);
        NbtParticleOptions first = smoke.isEmpty() ? null : (NbtParticleOptions) smoke.get(0).options();
        check(smoke.size() == 3 && smoke.stream().allMatch(p -> ((NbtParticleOptions) p.options()).type.equals(com.hbm.particle.NtmParticleTypes.COOLING_TOWER.get()) && p.y() == 68.0) && first.tag.getFloat("lift") == 0.01F
                        && first.tag.getFloat("base") == 0.5F && first.tag.getFloat("max") == 2F && first.tag.getInt("life") >= 70 && first.tag.getInt("life") < 100 && first.tag.getBoolean("noWind")
                        && first.tag.getInt("color") == 0 && first.tag.getFloat("strafe") == 0.05F && first.tag.getFloat("alphaMod") == 0.25F / 0.375F,
                "smoke while the lid rises: 3 cooling tower particles at y + 4 with lift 0.01, base 0.5, max 2, life 70-99, no wind, black, strafe 0.05 (original :230-245): " + smoke.size());
        ParticleUtil.ADDED.clear();
        player.px = 80;
        s.lid = 0.25F;
        RegistryFriendlyByteBuf far = new RegistryFriendlyByteBuf();
        be.serialize(far);
        s.deserialize(far);
        tick(clientLevel, s);
        check(ParticleUtil.ADDED.isEmpty(), "no smoke when the player is 50 or more blocks away");
        player.px = 0.5;
        boolean flames = true;
        for(long seed = 0; seed < 12; seed++) {
            ParticleUtil.ADDED.clear();
            clientLevel.random.setSeed(seed);
            s.lid = 0.75F;
            RegistryFriendlyByteBuf falling = new RegistryFriendlyByteBuf();
            be.lid = 0.6F;
            be.hasMaterial = true;
            be.serialize(falling);
            s.deserialize(falling);
            tick(clientLevel, s);
            boolean hit = new java.util.Random(seed).nextInt(5) == 0;
            // The lid 0.75 -> 0.6 is approached in two steps: 0.675, so it is > 0.5 and falling.
            flames &= hit ? ParticleUtil.ADDED.size() == 2 && ParticleUtil.ADDED.stream().allMatch(p -> ((NbtParticleOptions) p.options()).type.equals(com.hbm.particle.NtmParticleTypes.RBMK_FLAME.get())
                    && p.y() == 66.75 && ((NbtParticleOptions) p.options()).tag.getInt("lifetime") == 50) : ParticleUtil.ADDED.isEmpty();
        }
        check(flames, "flames while the lid falls over material: with probability 1 in 5 per tick (nextInt(5) == 0) two rbmkflame particles at y + 2.75 with lifetime 50, none otherwise (original :247-257)");
        section("9m. save, sync, client");
    }

    // ---- 6. Multiblock -------------------------------------------------------------------------------------------------------------

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

    /** Original getPorts (TileEntityMachineArcFurnaceLarge.java:554-561) and the extras of MachineArcFurnaceLarge.fillSpace (:59-64). */
    static List<DirPos> originalPorts(BlockPos c, Direction dir) {
        Direction rot = forgeRotationUp(dir);
        int dx = dir.getStepX(), dz = dir.getStepZ(), rx = rot.getStepX(), rz = rot.getStepZ(), x = c.getX(), y = c.getY(), z = c.getZ();
        return List.of(
                new DirPos(x + dx * 2 + rx, y, z + dz * 2 + rz, dir),
                new DirPos(x + dx * 2 - rx, y, z + dz * 2 - rz, dir),
                new DirPos(x + rx * 2 + dx, y, z + rz * 2 + dz, rot),
                new DirPos(x + rx * 2 - dx, y, z + rz * 2 - dz, rot),
                new DirPos(x - rx * 2 + dx, y, z - rz * 2 + dz, rot.getOpposite()),
                new DirPos(x - rx * 2 - dx, y, z - rz * 2 - dz, rot.getOpposite()));
    }

    static Set<BlockPos> ofType(Level level, Block block, DummyBlockType type) {
        Set<BlockPos> outSet = new LinkedHashSet<>();
        level.states.forEach((p, s) -> { if(s.getBlock() == block && s.getValue(DummyableBlock.TYPE) == type) outSet.add(p); });
        return outSet;
    }

    static void multiblock() {
        BlockPos origin = new BlockPos(0, 64, 0);
        for(Direction dir : HORIZONTALS) {
            reset();
            Level level = level();
            BlockPos core = Goal11ABlockAccess.place(FURNACE, level, origin, dir);
            Map<BlockPos, Direction> expected = new LinkedHashMap<>();
            originalFill(expected, core, MAIN_DIM[0], dir);
            Map<BlockPos, Direction> main = new LinkedHashMap<>(expected);
            originalFill(expected, core, EXTRA_DIM, dir);
            List<DirPos> ports = originalPorts(core, dir);
            Set<BlockPos> extraExpected = new LinkedHashSet<>();
            for(DirPos p : ports) extraExpected.add(p.makeCompat());
            Set<BlockPos> all = new LinkedHashSet<>();
            level.states.forEach((p, s) -> { if(s.getBlock() == FURNACE) all.add(p); });
            Set<BlockPos> union = new LinkedHashSet<>(expected.keySet());
            union.add(core);
            check(core.equals(origin) && all.equals(union) && ofType(level, FURNACE, DummyBlockType.CORE).equals(Set.of(core)),
                    dir + ": the production placement fills exactly the original's main box {4,0,2,2,2,2} and extra box {4,0,3,-2,1,1}, rotated (" + all.size() + " blocks, expected " + union.size() + ", one core)");
            Set<BlockPos> extraOnly = new LinkedHashSet<>(expected.keySet());
            extraOnly.removeAll(main.keySet());
            check(extraOnly.size() == 15 && all.containsAll(extraOnly) && main.size() == 124,
                    dir + ": the extra box adds " + extraOnly.size() + " blocks outside the 5 x 5 x 5 main box (124 dummies around the core): 15 behind it");
            boolean facings = true;
            for(Map.Entry<BlockPos, Direction> e : expected.entrySet()) facings &= level.getBlockState(e.getKey()).getValue(DummyableBlock.FACING) == e.getValue();
            check(facings, dir + ": every dummy points as the original's fillSpace sets it (later boxes overwrite earlier ones)");
            Set<BlockPos> extra = ofType(level, FURNACE, DummyBlockType.EXTRA);
            check(extra.equals(extraExpected) && extra.size() == 6, dir + ": EXTRA at exactly the 6 original port positions on the core layer: " + extra);
            boolean combos = true, none = true;
            for(BlockPos p : all) {
                BlockEntity b = level.getBlockEntity(p);
                if(extra.contains(p)) combos &= b instanceof ProxyComboBlockEntity combo && Goal12AProxyAccess.flags(combo).equals(
                        Map.of("inventory", true, "power", true, "conductor", false, "fluid", false, "heat", false, "moltenMetal", false));
                else if(!p.equals(core)) none &= b == null;
            }
            check(combos && none && level.getBlockEntity(core) instanceof MachineArcFurnaceBlockEntity,
                    dir + ": each EXTRA is a ProxyComboBlockEntity with the inventory and power flags only (original TileEntityProxyCombo().inventory().power()), the other dummies have no block entity");
            MachineArcFurnaceBlockEntity be = (MachineArcFurnaceBlockEntity) level.getBlockEntity(core);
            DirPos[] con = be.getConPos();
            boolean same = con.length == 6;
            for(int i = 0; i < 6 && same; i++) {
                DirPos p = ports.get(i);
                same = con[i].getDir() == p.getDir() && con[i].makeCompat().equals(p.makeCompat().relative(p.getDir())) && !all.contains(con[i].makeCompat());
            }
            check(same, dir + ": getConPos is the 6 original connections (PortDef.make: one block outward from each port, in its direction), all outside the structure");
            if(dir == Direction.NORTH) {
                List<BlockPos> stage = List.of(core.offset(1, 0, -2), core.offset(-1, 0, -2), core.offset(2, 0, -1), core.offset(2, 0, 1), core.offset(-2, 0, -1), core.offset(-2, 0, 1));
                check(new ArrayList<>(extraExpected).equals(stage), "north: the ports are (+1,0,-2), (-1,0,-2), (+2,0,-1), (+2,0,+1), (-2,0,-1), (-2,0,+1)");
                Set<BlockPos> box = new LinkedHashSet<>();
                for(int x = -2; x <= 2; x++) for(int y = 0; y <= 4; y++) for(int z = -2; z <= 2; z++) box.add(core.offset(x, y, z));
                box.remove(core);
                check(main.keySet().equals(box), "north: the main box is x -2..+2, y 0..+4, z -2..+2 (124 around the core)");
                Set<BlockPos> wing = new LinkedHashSet<>();
                for(int x = -1; x <= 1; x++) for(int y = 0; y <= 4; y++) wing.add(core.offset(x, y, 3));
                check(extraOnly.equals(wing), "north: the extra box x -1..+1, y 0..+4, z +2..+3 adds only the slice z +3 behind the main box (15 blocks; z +2 lies inside it): " + extraOnly.size());
            }
        }
        // checkRequirement: the empty space passes; one block in the main box or in the extra box fails; one outside passes.
        for(Direction dir : HORIZONTALS) {
            BlockPos origin2 = new BlockPos(0, 64, 0);
            BlockPos clicked = origin2.relative(dir, OFFSET);
            List<String> wrong = new ArrayList<>();
            Map<BlockPos, Direction> main = new LinkedHashMap<>();
            originalFill(main, origin2, MAIN_DIM[0], dir);
            Map<BlockPos, Direction> extraCells = new LinkedHashMap<>();
            originalFill(extraCells, origin2, EXTRA_DIM, dir);
            BlockPos extraProbe = null;
            for(BlockPos p : extraCells.keySet()) if(!main.containsKey(p)) { extraProbe = p; }
            List<BlockPos> probes = new ArrayList<>(List.of(main.keySet().iterator().next(), extraProbe));
            probes.add(origin2.offset(0, 4, 0));
            Level empty = level();
            if(!Goal13BBlockAccess.checkRequirement(FURNACE, empty, clicked, dir, -OFFSET)) wrong.add("empty space refused");
            for(BlockPos p : probes) {
                Level l = level();
                l.states.put(p, Blocks.STONE.defaultBlockState());
                if(Goal13BBlockAccess.checkRequirement(FURNACE, l, clicked, dir, -OFFSET)) wrong.add("stone at " + p + " accepted");
            }
            for(BlockPos p : extraCells.keySet()) {
                if(main.containsKey(p)) continue;
                Level l = level();
                l.states.put(p, Blocks.STONE.defaultBlockState());
                if(Goal13BBlockAccess.checkRequirement(FURNACE, l, clicked, dir, -OFFSET)) wrong.add("stone in the extra box at " + p + " accepted");
            }
            Level outside = level();
            outside.states.put(origin2.offset(0, 20, 0), Blocks.STONE.defaultBlockState());
            outside.states.put(origin2.offset(7, 0, 7), Blocks.STONE.defaultBlockState());
            if(!Goal13BBlockAccess.checkRequirement(FURNACE, outside, clicked, dir, -OFFSET)) wrong.add("stone outside refused");
            check(wrong.isEmpty(), dir + ": checkRequirement passes the empty space and blocks outside, fails for a stone block anywhere in the main box or in the extra box: " + wrong);
        }
        // Block shape: dimensions, offset, the block entities by type.
        check(java.util.Arrays.equals(FURNACE.getDimensions(), MAIN_DIM[0]) && FURNACE.getOffset() == OFFSET, "dimensions {4,0,2,2,2,2} and offset 2 (original MachineArcFurnaceLarge.java:34-41)");
        BlockState core = FURNACE.createCoreState(Direction.NORTH);
        BlockState dummy = core.setValue(DummyableBlock.TYPE, DummyBlockType.DUMMY);
        BlockState extra = core.setValue(DummyableBlock.TYPE, DummyBlockType.EXTRA);
        check(FURNACE.newBlockEntity(origin, core) instanceof MachineArcFurnaceBlockEntity && FURNACE.newBlockEntity(origin, extra) instanceof ProxyComboBlockEntity && FURNACE.newBlockEntity(origin, dummy) == null
                        && FURNACE.getTicker(new Level(), core, null) != null && FURNACE.getTicker(new Level(), extra, null) == null,
                "the core creates the furnace and ticks, an extra a proxy, a dummy nothing (original createNewTileEntity: meta >= 12 / >= 6)");
        section("6. multiblock");
    }

    // ---- 7m. The furnace in the chain ------------------------------------------------------------------------------------------------

    static void chain() throws Exception {
        reset();
        Level level = level();
        MachineArcFurnaceBlockEntity be = ready(level, 0);
        be.slots.set(25, new ItemStack(Items.SAND));
        int guard = 0;
        while(be.delay == 0 && guard++ < 2000) { be.power = MAX_POWER; tick(level, be); }
        ItemStack nuggets = be.slots.get(5);
        check(nuggets.getItem() == NtmItems.NUGGET_SILICON.get() && nuggets.getCount() == 1, "one sand in the arc furnace gives one silicon nugget");
        String output = nuggets.getItem().id;
        int outputCount = nuggets.getCount();
        // Six sand in six runs, or one run at upgrade 1 with 4: the nuggets per run for each upgrade.
        reset();
        level = level();
        be = ready(level, 3);
        be.slots.set(25, new ItemStack(Items.SAND, 16));
        guard = 0;
        while(be.delay == 0 && guard++ < 2000) { be.power = MAX_POWER; tick(level, be); }
        check(be.slots.get(5).getItem() == NtmItems.NUGGET_SILICON.get() && be.slots.get(5).getCount() == 16, "an upgrade-3 furnace turns a stack of 16 sand into 16 nuggets in one run");
        String facts = "{\"furnaceOutput\":\"" + output + "\",\"furnaceOutputCount\":" + outputCount + ",\"furnaceUpgrade3Nuggets\":" + be.slots.get(5).getCount() + "}";
        Files.writeString(out.resolve("machine-facts.json"), facts, StandardCharsets.UTF_8);
        section("7m. furnace output");
    }

    public static void main(String[] args) throws Exception {
        out = Path.of(args[0]);
        Files.createDirectories(out);
        run("3m. electrodes", Goal13BRegression::electrodes);
        run("5. state machine", Goal13BRegression::machine);
        run("5w. electrode wear", Goal13BRegression::wear);
        run("5l. queue loading", Goal13BRegression::loading);
        run("5e. electrode states, slots, menu", Goal13BRegression::slots);
        run("9m. save, sync, client", Goal13BRegression::sync);
        run("6. multiblock", Goal13BRegression::multiblock);
        run("7m. furnace output", () -> {
            try {
                chain();
            } catch(Exception e) {
                throw new AssertionError("chain: " + e, e);
            }
        });
        System.out.println("Goal 13B machine world: " + checks + " checks passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
