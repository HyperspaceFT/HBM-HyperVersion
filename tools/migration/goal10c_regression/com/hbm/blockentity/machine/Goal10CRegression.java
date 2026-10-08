package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.boiler.MachineHeatBoilerBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterOvenBlockEntity;
import com.hbm.blockentity.machine.storage.BatteryBaseBlockEntity;
import com.hbm.blockentity.machine.storage.BatterySocketBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.Goal10CBlockAccess;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.MachineElectricFurnaceBlock;
import com.hbm.blocks.machine.heater.HeaterOvenBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.SlotSmeltingOutput;
import com.hbm.inventory.menus.MachineElectricFurnaceMenu;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Containers;
import net.minecraft.world.entity.ExperienceOrb;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.BlastingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.SmeltingRecipe;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.event.EventHooks;
import net.neoforged.neoforge.network.PacketDistributor;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/**
 * Goal 10C: the heating oven (anvil entries, removal, heat) and the electric furnace (processing, upgrades, slots, LIT,
 * persistence, experience and menu, power budget), against real production classes in the Goal 10B machine world.
 * Expected numbers are read from the original at 608fec4, not from the NEO classes under test:
 * AnvilRecipes.java:269-274 (oven: 16 firebricks, 4 steel plates, 8 copper ingots, tier 2) and :672-678 (oven recycling:
 * 16 firebricks, 8 copper, tier 2); HeaterOven.java:35-42 (dimensions {0, 0, 1, 1, 1, 1}, offset 1);
 * TileEntityHeaterOven.java:24-71 (500 TU base, time x0.125, 500,000 TU cap, pulls the source below and keeps half);
 * TileEntityFireboxBase.updateEntity (burn loop); TileEntityMachineElectricFurnace.java:40-208 (100,000 HE, 100 ticks,
 * 50 HE/t, the upgrade formulas, cooldown 20, progress reset, the LIT trigger, slots {0, 1, 2}, extraction of slot 2,
 * NBT power/progress, sync power/maxProgress/progress).
 */
public class Goal10CRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    private static final Direction[] HORIZONTALS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};
    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());

    // Original numbers (608fec4), independent of the NEO constants under test.
    private static final int OVEN_BASE_HEAT = 500;
    private static final double OVEN_TIME_MULT = 0.125D;
    private static final int OVEN_MAX_HEAT = 500_000;
    private static final int COAL_BURN = 1_600;          // Minecraft coal
    private static final double COAL_TIME_MOD = 1.25D;  // TileEntityHeaterOven burnModule.setCoalTimeMod(1.25)
    private static final int COAL_HEAT_MOD = 2;          // setCoalHeatMod(2)
    private static final long FURNACE_MAX_POWER = 100_000L;
    private static final int FURNACE_TICKS = 100;
    private static final int FURNACE_HE = 50;
    private static final int FURNACE_COOLDOWN = 20;
    private static final long HE_PER_ENGINE_OP = 170; // Goal 9B: 200 TU * TURBINE 1.0 * 0.85, checked below on the real engine

    // Test items and recipes (Minecraft's own smelting table is not loaded here).
    static final Item RAW_IRON = new Item("minecraft:raw_iron");
    static final Item COBBLESTONE = new Item("minecraft:cobblestone");
    static final Item STONE = new Item("minecraft:stone");
    static final Item RAW_GOLD = new Item("minecraft:raw_gold");
    static final Item DOUBLER = new Item("test:doubler");
    static final Item DOUBLE_OUT = new Item("test:double_out");
    static final Item SMALL_IN = new Item("test:small_in");
    static final Item SMALL_OUT = new Item("test:small_out", 16, 0);
    static final Item BLAST_ONLY = new Item("test:blast_only");
    static final Item STICK = new Item("minecraft:stick");
    static final Item IRON_ORE = new Item("minecraft:iron_ore");
    static final Item DEBRIS = new Item("test:debris");
    static final Item SCRAP = new Item("test:scrap");

    static final MachineElectricFurnaceBlock FURNACE = new MachineElectricFurnaceBlock(new Block.Properties());
    static final HeaterOvenBlock OVEN = new HeaterOvenBlock(new Block.Properties());

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
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

    // ---- World helpers (the Goal 9B/10B patterns) -------------------------------------------------------------------

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
        Block.DROPS.clear();
        Containers.DROPS.clear();
        ExperienceOrb.AWARDS.clear();
        EventHooks.smelted = 0;
        ItemStack.craftedBy = 0;
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        recipes(level);
        return level;
    }

    static ServerLevel serverLevel() {
        ServerLevel level = new ServerLevel();
        level.manualClock = true;
        recipes(level);
        return level;
    }

    static RecipeHolder<?> holder(String id, Object recipe) {
        return new RecipeHolder<>(ResourceLocation.fromNamespaceAndPath("test", id), (net.minecraft.world.item.crafting.Recipe<?>) recipe);
    }

    /**
     * Smelting recipes in registration order. Experience values are binary fractions, so count * experience is exact.
     * raw iron -> iron ingot 0.5; iron ore -> iron ingot 0.75 (a second recipe for the same result, registered later);
     * cobblestone -> stone 0.25; raw gold -> gold ingot 1.0; doubler -> 2 double_out; small_in -> small_out (stacks to 16);
     * debris -> scrap 2.0 (worth more than 1 per item, like Minecraft's ancient debris);
     * blast_only has only a blasting recipe.
     */
    static void recipes(Level level) {
        List<RecipeHolder<?>> r = level.getRecipeManager().recipes;
        r.add(holder("blast_only", new BlastingRecipe(BLAST_ONLY, new ItemStack(Items.IRON_INGOT), 1.0F, 100)));
        r.add(holder("raw_iron", new SmeltingRecipe(RAW_IRON, new ItemStack(Items.IRON_INGOT), 0.5F, 200)));
        r.add(holder("iron_ore", new SmeltingRecipe(IRON_ORE, new ItemStack(Items.IRON_INGOT), 0.75F, 200)));
        r.add(holder("cobblestone", new SmeltingRecipe(COBBLESTONE, new ItemStack(STONE), 0.25F, 200)));
        r.add(holder("raw_gold", new SmeltingRecipe(RAW_GOLD, new ItemStack(Items.GOLD_INGOT), 1.0F, 200)));
        r.add(holder("doubler", new SmeltingRecipe(DOUBLER, new ItemStack(DOUBLE_OUT, 2), 0.5F, 200)));
        r.add(holder("small", new SmeltingRecipe(SMALL_IN, new ItemStack(SMALL_OUT), 0.5F, 200)));
        r.add(holder("debris", new SmeltingRecipe(DEBRIS, new ItemStack(SCRAP), 2.0F, 200)));
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

    /** A battery socket with its conductor proxies and a charged lithium pack, set to output (the Goal 10B rig). */
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
        socket.slots.set(0, pack(1_000_000L));
        socket.redLow = BatteryBaseBlockEntity.mode_output;
        return socket;
    }

    static ItemStack pack(long charge) {
        ItemStack pack = MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_LITHIUM.ordinal());
        PACK.setCharge(pack, charge);
        return pack;
    }

    /** The electric furnace block (default state: north, unlit) with its block entity, as the block would create it. */
    static MachineElectricFurnaceBlockEntity furnace(Level level, BlockPos pos) {
        BlockState state = FURNACE.defaultBlockState();
        level.states.put(pos, state);
        MachineElectricFurnaceBlockEntity be = (MachineElectricFurnaceBlockEntity) FURNACE.newBlockEntity(pos, state);
        level.put(be);
        return be;
    }

    static void tick(MachineElectricFurnaceBlockEntity be) {
        be.getLevel().time++;
        be.updateEntity();
    }

    static boolean lit(Level level, BlockPos pos) {
        BlockState s = level.getBlockState(pos);
        return s.is(FURNACE) && s.getValue(MachineElectricFurnaceBlock.LIT);
    }

    static int cooldown(MachineElectricFurnaceBlockEntity be) {
        try {
            Field f = MachineElectricFurnaceBlockEntity.class.getDeclaredField("cooldown");
            f.setAccessible(true);
            return f.getInt(be);
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("no cooldown field", e);
        }
    }

    static void setCooldown(MachineElectricFurnaceBlockEntity be, int value) {
        try {
            Field f = MachineElectricFurnaceBlockEntity.class.getDeclaredField("cooldown");
            f.setAccessible(true);
            f.setInt(be, value);
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("no cooldown field", e);
        }
    }

    /** The protected production saveAdditional/loadAdditional (most derived declaration, dispatched virtually). */
    static CompoundTag save(BlockEntity be) {
        CompoundTag tag = new CompoundTag();
        invoke(be, "saveAdditional", tag);
        return tag;
    }

    static void load(BlockEntity be, CompoundTag tag) {
        invoke(be, "loadAdditional", tag);
    }

    private static void invoke(BlockEntity be, String name, CompoundTag tag) {
        for(Class<?> type = be.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Method method = type.getDeclaredMethod(name, CompoundTag.class, HolderLookup.Provider.class);
                method.setAccessible(true);
                method.invoke(be, tag, null);
                return;
            } catch(NoSuchMethodException ignored) {
            } catch(ReflectiveOperationException e) {
                throw new AssertionError(name + " failed on " + be.getClass().getName(), e);
            }
        }
        throw new AssertionError("no " + name + " on " + be.getClass().getName());
    }

    @SuppressWarnings("unchecked")
    static Set<String> keys(CompoundTag tag) {
        try {
            Field f = CompoundTag.class.getDeclaredField("m");
            f.setAccessible(true);
            return new TreeSet<>(((Map<String, Object>) f.get(tag)).keySet());
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("cannot read tag keys", e);
        }
    }

    static MachineUpgradeItem upgrade(UpgradeType type, int tier) {
        return new MachineUpgradeItem(new Item.Properties(), type, tier);
    }

    // ---- 1. Heating oven anvil entries ------------------------------------------------------------------------------

    /** A construction entry of either list (live or goal10c.head: distinct classes, read reflectively; Goal 9B format). */
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

    /** The seven Goal 10B corrections applied to a committed (ee8f8d06) descriptor, as the Goal 10B suite does. */
    static String goal10b(String before) {
        if(before.contains("-> 1 hbmsntm:machine_soldering_station @") && before.endsWith(" CONSTRUCTION"))
            return before.replace("item hbmsntm:bolt x1 ", "item hbmsntm:bolt x4 ");
        if(before.startsWith("item hbmsntm:stamp_titanium_flat x1 ")) return before.replace("hbmsntm:stamp_steel_", "hbmsntm:stamp_titanium_");
        if(before.startsWith("item hbmsntm:stamp_steel_flat x1 ")) return before.replace("hbmsntm:stamp_titanium_", "hbmsntm:stamp_steel_");
        return before;
    }

    /** The three Goal 10C entries, appended in this order after the Goal 9B steam engine (the end of the list until Goal 11A, whose two fluid burner entries follow them). */
    static final int W = MetaHelper.WILDCARD_VALUE;
    static final String[] GOAL10C = {
            "item hbmsntm:ingot_firebrick x16 meta " + W + "; tag plates/steel x4; item minecraft:copper_ingot x8 meta " + W + "; -> 1 hbmsntm:heater_oven @1.0; tier 2--1 CONSTRUCTION",
            "item hbmsntm:ingot_firebrick x16 meta " + W + "; tag plates/steel x4; item hbmsntm:ingot_copper x8 meta " + W + "; -> 1 hbmsntm:heater_oven @1.0; tier 2--1 CONSTRUCTION",
            "item hbmsntm:heater_oven x1 meta " + W + "; -> 16 hbmsntm:ingot_firebrick @1.0; 8 hbmsntm:ingot_copper @1.0; tier 2--1 RECYCLING",
    };

    /**
     * Goal 11A (migration/GOAL11A.md) appends two fluid burner entries after the Goal 10C entries (original
     * AnvilRecipes.java:283-289): construction with Minecraft copper and with NEO copper, no recycling entry. They are
     * required exactly, in this order, at the end of the list; the Goal 11A suite checks them in detail.
     */
    static final String[] GOAL11A = {
            "item hbmsntm:tank_steel x4 meta " + W + "; item hbmsntm:pipe_steel x3 meta " + W + "; item hbmsntm:ingot_titanium x12 meta " + W
                    + "; item minecraft:copper_ingot x8 meta " + W + "; -> 1 hbmsntm:heater_oilburner @1.0; tier 2--1 CONSTRUCTION",
            "item hbmsntm:tank_steel x4 meta " + W + "; item hbmsntm:pipe_steel x3 meta " + W + "; item hbmsntm:ingot_titanium x12 meta " + W
                    + "; item hbmsntm:ingot_copper x8 meta " + W + "; -> 1 hbmsntm:heater_oilburner @1.0; tier 2--1 CONSTRUCTION",
    };

    /**
     * Goal 12A (migration/GOAL12A.md) appends four entries after the Goal 11A entries: the industrial boiler with Minecraft
     * and with NEO copper (original AnvilRecipes.java:399-404), the electric pump (:253-260) and the desh motor (:215-217).
     * They are required exactly, in this order, at the end of the list; the Goal 12A suite checks them in detail.
     */
    static final String[] GOAL12A = {
            "item hbmsntm:cast_plate x8 meta 11; item minecraft:copper_ingot x8 meta " + W + "; tag ntm:ingots_plastic x4; -> 1 hbmsntm:machine_industrial_boiler @1.0; tier 3--1 CONSTRUCTION",
            "item hbmsntm:cast_plate x8 meta 11; item hbmsntm:ingot_copper x8 meta " + W + "; tag ntm:ingots_plastic x4; -> 1 hbmsntm:machine_industrial_boiler @1.0; tier 3--1 CONSTRUCTION",
            "item stone_bricks x8 meta " + W + "; tag plates/steel x16; item hbmsntm:pipe_lead x4 meta " + W + "; item hbmsntm:motor x2 meta " + W
                    + "; item hbmsntm:circuit_vacuum_tube x4 meta " + W + "; -> 1 hbmsntm:pump_electric @1.0; tier 3--1 CONSTRUCTION",
            "item hbmsntm:motor x1 meta " + W + "; tag ntm:ingots_plastic x2; item hbmsntm:ingot_desh x2 meta " + W + "; item hbmsntm:wire_dense x1 meta 7900; "
                    + "-> 1 hbmsntm:motor_desh @1.0; tier 3--1 CONSTRUCTION",
    };

    static boolean accepts(AnvilConstructionRecipe recipe, ItemStack... offered) {
        for(AStack input : recipe.input) {
            boolean found = false;
            for(ItemStack stack : offered) found |= input.matchesRecipe(stack, false);
            if(!found) return false;
        }
        return true;
    }

    static boolean plain(ItemStack stack) {
        return MetaHelper.getMeta(stack) == 0 && !stack.has(com.hbm.items.component.NtmDataComponents.META.get());
    }

    static void anvil() {
        List<AnvilConstructionRecipe> live = AnvilRecipes.getConstruction();
        List<?> head = goal10c.head.AnvilRecipes.getConstruction();
        int n = head.size();
        check(n > 0 && live.size() == n + 3 + GOAL11A.length + GOAL12A.length, "the live list is the ee8f8d06 list plus exactly three entries, then the two Goal 11A"
                + " entries and the four Goal 12A entries (" + n + " -> " + live.size() + ")");
        int same = 0, corrected = 0;
        String first = null;
        for(int i = 0; i < n; i++) {
            String before = describe(head.get(i)), expected = goal10b(before), now = describe(live.get(i));
            if(!expected.equals(before)) corrected++;
            if(now.equals(expected)) same++;
            else if(first == null) first = i + ": " + now + " != " + expected;
        }
        check(same == n && corrected == 7, "every earlier entry keeps its content and index, apart from the seven Goal 10B corrections ("
                + corrected + " corrected)" + (first == null ? "" : "; first difference " + first));
        for(int k = 0; k < GOAL10C.length; k++) {
            String now = describe(live.get(n + k));
            check(now.equals(GOAL10C[k]), "entry " + (n + k) + " is Goal 10C entry " + (k + 1) + ": " + GOAL10C[k] + " (got " + now + ")");
        }
        boolean goal11a = true;
        for(int k = 0; k < GOAL11A.length; k++) goal11a &= describe(live.get(n + 3 + k)).equals(GOAL11A[k]);
        check(goal11a, "exactly the two Goal 11A fluid burner entries follow the recycling entry, in order");
        List<String> tail = new ArrayList<>();
        for(int k = 0; k < GOAL12A.length; k++) tail.add(describe(live.get(n + 3 + GOAL11A.length + k)));
        check(tail.equals(List.of(GOAL12A)), "exactly the four Goal 12A entries (industrial boiler x2, electric pump, desh motor) follow the Goal 11A entries, in order: " + tail);
        check(AnvilRecipes.getConstruction(n + 2) == live.get(n + 2) && AnvilRecipes.getConstruction(n + 3 + GOAL11A.length + GOAL12A.length) == null,
                "the recycling entry is the last Goal 10C entry; only the Goal 11A and Goal 12A entries follow it and the index after them is empty");

        AnvilConstructionRecipe vanilla = live.get(n), neo = live.get(n + 1), recycling = live.get(n + 2);
        Item oven = NtmBlocks.HEATER_OVEN.asItem(), firebrick = NtmItems.INGOT_FIREBRICK.get(), copper = NtmItems.INGOT_COPPER.get();
        for(AnvilConstructionRecipe build : new AnvilConstructionRecipe[] {vanilla, neo}) {
            List<AStack> in = build.input;
            check(in.size() == 3
                            && in.get(0) instanceof ComparableStack fb && fb.item == firebrick && fb.stacksize == 16 && fb.meta == MetaHelper.WILDCARD_VALUE
                            && in.get(1) instanceof TagStack plates && plates.tag == NtmTags.Items.PLATES_STEEL && plates.stacksize == 4
                            && in.get(2) instanceof ComparableStack cu && cu.stacksize == 8,
                    "construction inputs: 16 firebricks, 4 steel plates (tag), 8 copper ingots");
            check(build.output.size() == 1 && build.output.get(0).stack.is(oven) && build.output.get(0).stack.getCount() == 1
                            && build.output.get(0).chance == 1F && plain(build.output.get(0).stack),
                    "construction output: one plain heating oven");
            check(build.tierLower == 2 && build.tierUpper == -1 && build.isTierValid(2) && build.isTierValid(3) && !build.isTierValid(1)
                    && build.getOverlay() == OverlayType.CONSTRUCTION, "construction: anvil tier 2 and up, construction overlay");
        }
        check(((ComparableStack) vanilla.input.get(2)).item == Items.COPPER_INGOT && ((ComparableStack) neo.input.get(2)).item == copper,
                "the first construction takes Minecraft copper ingots, the second NEO copper ingots (the firebox pattern)");

        NtmItems.PLATE_STEEL.get().tags.add((String) NtmTags.Items.PLATES_STEEL);
        ItemStack[] vanillaSet = {new ItemStack(firebrick, 16), new ItemStack(NtmItems.PLATE_STEEL.get(), 4), new ItemStack(Items.COPPER_INGOT, 8)};
        ItemStack[] neoSet = {new ItemStack(firebrick, 16), new ItemStack(NtmItems.PLATE_STEEL.get(), 4), new ItemStack(copper, 8)};
        check(accepts(vanilla, vanillaSet) && !accepts(neo, vanillaSet), "the Minecraft copper set matches only the first construction");
        check(accepts(neo, neoSet) && !accepts(vanilla, neoSet), "the NEO copper set matches only the second construction");
        boolean shortRejected = true;
        int[] counts = {16, 4, 8};
        for(ItemStack[] set : new ItemStack[][] {vanillaSet, neoSet}) {
            for(int i = 0; i < 3; i++) {
                ItemStack[] fewer = set.clone();
                fewer[i] = new ItemStack(set[i].getItem(), counts[i] - 1);
                shortRejected &= !accepts(vanilla, fewer) && !accepts(neo, fewer);
            }
        }
        check(shortRejected, "15 firebricks, 3 steel plates or 7 copper ingots are not enough for either construction");
        ItemStack[] ironPlates = vanillaSet.clone();
        ironPlates[1] = new ItemStack(NtmItems.PLATE_IRON.get(), 4);
        ItemStack[] bricks = vanillaSet.clone();
        bricks[0] = new ItemStack(Items.BRICK, 16);
        check(!accepts(vanilla, ironPlates) && !accepts(vanilla, bricks), "iron plates or plain bricks do not stand in for steel plates or firebricks");

        check(recycling.input.size() == 1 && recycling.input.get(0) instanceof ComparableStack ovenIn && ovenIn.item == oven && ovenIn.stacksize == 1
                        && recycling.input.get(0).matchesRecipe(new ItemStack(oven), false),
                "recycling takes one heating oven");
        check(recycling.output.size() == 2
                        && recycling.output.get(0).stack.is(firebrick) && recycling.output.get(0).stack.getCount() == 16 && recycling.output.get(0).chance == 1F
                        && recycling.output.get(1).stack.is(copper) && recycling.output.get(1).stack.getCount() == 8 && recycling.output.get(1).chance == 1F,
                "recycling returns 16 firebricks and 8 NEO copper ingots, always");
        check(recycling.tierLower == 2 && recycling.isTierValid(2) && !recycling.isTierValid(1) && recycling.getOverlay() == OverlayType.RECYCLING,
                "recycling: anvil tier 2, recycling overlay");
        int makes = 0, takes = 0;
        for(AnvilConstructionRecipe r : live) {
            for(var out : r.output) if(out.stack.is(oven)) makes++;
            for(AStack input : r.input) if(input instanceof ComparableStack cs && cs.item == oven) takes++;
        }
        check(makes == 2 && takes == 1, "the heating oven appears only in these three entries (" + makes + " made, " + takes + " taken)");
        section("1. heating oven anvil");
    }

    // ---- 2. Heating oven removal ------------------------------------------------------------------------------------

    static List<BlockPos> footprint(BlockPos core) {
        List<BlockPos> out = new ArrayList<>();
        for(int dx = -1; dx <= 1; dx++) for(int dz = -1; dz <= 1; dz++) out.add(core.offset(dx, 0, dz));
        return out;
    }

    static Map<BlockPos, BlockState> snapshot(Level level, List<BlockPos> positions) {
        Map<BlockPos, BlockState> out = new LinkedHashMap<>();
        for(BlockPos p : positions) out.put(p, level.states.get(p));
        return out;
    }

    static boolean intact(Level level, Map<BlockPos, BlockState> before) {
        for(Map.Entry<BlockPos, BlockState> e : before.entrySet()) {
            BlockState now = level.states.get(e.getKey());
            if(e.getValue() == null || now == null || !now.sameAs(e.getValue())) return false;
        }
        return true;
    }

    static boolean gone(Level level, List<BlockPos> positions) {
        for(BlockPos p : positions) if(level.states.containsKey(p)) return false;
        return true;
    }

    /** ServerPlayerGameMode.destroyBlock: playerWillDestroy on the block, then Level.removeBlock at the position. */
    static void breakByPlayer(Level level, BlockPos pos, Player player) {
        BlockState state = level.getBlockState(pos);
        state.getBlock().playerWillDestroy(level, pos, state, player);
        level.removeBlock(pos, false);
    }

    record Neighbour(String name, BlockPos offset) {}

    static final Neighbour[] NEIGHBOURS = {
            new Neighbour("none", null),
            new Neighbour("touching east", new BlockPos(3, 0, 0)),
            new Neighbour("touching north", new BlockPos(0, 0, -3)),
            new Neighbour("touching diagonally", new BlockPos(3, 0, 3)),
            new Neighbour("one block apart east", new BlockPos(4, 0, 0)),
            new Neighbour("stacked above", new BlockPos(0, 1, 0)),
            new Neighbour("stacked below", new BlockPos(0, -1, 0)),
    };

    static void ovenRemoval() {
        BlockPos core = new BlockPos(0, 64, 0);

        // Placement through the production fillSpace: 3 x 1 x 3, the core in the middle, every dummy finds the core.
        check(Arrays.equals(OVEN.getDimensions(), new int[] {0, 0, 1, 1, 1, 1}) && OVEN.getOffset() == 1,
                "dimensions {0, 0, 1, 1, 1, 1} and offset 1, as the original HeaterOven");
        for(Direction dir : HORIZONTALS) {
            reset();
            Level level = level();
            BlockPos placed = Goal10CBlockAccess.place(OVEN, level, core, dir);
            boolean ok = placed.equals(core) && level.states.size() == 9;
            int cores = 0;
            for(BlockPos p : footprint(core)) {
                BlockState s = level.states.get(p);
                ok &= s != null && s.is(OVEN) && core.equals(OVEN.findCore(level, p));
                if(s != null && s.getValue(DummyableBlock.TYPE) == DummyBlockType.CORE) cores++;
            }
            check(ok && cores == 1 && level.getBlockState(core).getValue(DummyableBlock.TYPE) == DummyBlockType.CORE,
                    dir + ": the oven fills its 3 x 1 x 3 footprint; one core in the middle; every block finds it");
        }

        // A player breaks each block of oven A; oven B stands next to it in seven arrangements.
        for(Neighbour nb : NEIGHBOURS) {
            int passed = 0;
            String firstFailure = null;
            for(boolean creative : new boolean[] {false, true}) {
                for(BlockPos target : footprint(core)) {
                    reset();
                    Level level = level();
                    Goal10CBlockAccess.place(OVEN, level, core, Direction.NORTH);
                    BlockPos other = nb.offset == null ? null : core.offset(nb.offset.getX(), nb.offset.getY(), nb.offset.getZ());
                    if(other != null) Goal10CBlockAccess.place(OVEN, level, other, Direction.EAST);
                    Map<BlockPos, BlockState> b = other == null ? Map.of() : snapshot(level, footprint(other));
                    int statesBefore = level.states.size();
                    level.removals.clear();
                    Player player = new Player();
                    player.creative = creative;
                    breakByPlayer(level, target, player);
                    boolean ok = gone(level, footprint(core)) && intact(level, b) && level.states.size() == statesBefore - 9
                            && !DummyableBlock.safeRem;
                    // One drop at A's core for a survival player (DummyableBlock.playerWillDestroy), none in creative.
                    ok &= creative ? Block.DROPS.isEmpty() : Block.DROPS.equals(List.of(core));
                    // destroyHeater removes the 9 blocks with safeRem set; the player's own removeBlock then finds air.
                    ok &= level.removals.size() == 10 && level.removals.subList(0, 9).stream().allMatch(Level.Removal::safeRem)
                            && !level.removals.get(9).safeRem();
                    if(ok) passed++;
                    else if(firstFailure == null) firstFailure = (creative ? "creative" : "survival") + " break at " + target
                            + ": A left " + (9 - (statesBefore - level.states.size())) + " blocks, B intact " + intact(level, b)
                            + ", drops " + Block.DROPS + ", removals " + level.removals.size();
                }
            }
            check(passed == 18, "oven B " + nb.name + ": breaking any of A's 9 blocks (survival and creative) removes exactly A's 9 blocks, "
                    + "with safeRem set, one drop at A's core in survival; B keeps all 9 blocks (" + passed + "/18)"
                    + (firstFailure == null ? "" : "; first failure: " + firstFailure));
        }

        // Every facing, with B touching on each side in turn.
        boolean facings = true;
        for(Direction dir : HORIZONTALS) {
            for(Direction side : HORIZONTALS) {
                reset();
                Level level = level();
                Goal10CBlockAccess.place(OVEN, level, core, dir);
                BlockPos other = core.relative(side, 3);
                Goal10CBlockAccess.place(OVEN, level, other, dir.getOpposite());
                Map<BlockPos, BlockState> b = snapshot(level, footprint(other));
                breakByPlayer(level, core.relative(side), new Player());
                facings &= gone(level, footprint(core)) && intact(level, b);
            }
        }
        check(facings, "every facing of A and B, B touching on each side: only A goes");

        // Not a player (explosion, /setblock): no playerWillDestroy. onRemove sees air at the position (findCore null), so
        // the DummyableBlock chain (removal towards the core) and the orphan checks of the neighbour updates clear A.
        int passed = 0;
        String firstFailure = null;
        for(Neighbour nb : NEIGHBOURS) {
            for(BlockPos target : footprint(core)) {
                reset();
                Level level = level();
                Goal10CBlockAccess.place(OVEN, level, core, Direction.NORTH);
                BlockPos other = nb.offset == null ? null : core.offset(nb.offset.getX(), nb.offset.getY(), nb.offset.getZ());
                if(other != null) Goal10CBlockAccess.place(OVEN, level, other, Direction.EAST);
                Map<BlockPos, BlockState> b = other == null ? Map.of() : snapshot(level, footprint(other));
                level.removeBlock(target, false);
                boolean ok = gone(level, footprint(core)) && intact(level, b) && Block.DROPS.isEmpty() && !DummyableBlock.safeRem;
                if(ok) passed++;
                else if(firstFailure == null) firstFailure = nb.name + ", removed " + target + ": A gone " + gone(level, footprint(core)) + ", B intact " + intact(level, b);
            }
        }
        check(passed == NEIGHBOURS.length * 9, "removal without a player at any of A's blocks: the dummy chain and orphan checks clear A only ("
                + passed + "/" + NEIGHBOURS.length * 9 + ")" + (firstFailure == null ? "" : "; first failure: " + firstFailure));

        // An orphan dummy (pointing at air, no core) next to oven B: breaking it removes nothing else and drops nothing.
        for(boolean creative : new boolean[] {false, true}) {
            reset();
            Level level = level();
            BlockPos other = new BlockPos(3, 64, 0);
            Goal10CBlockAccess.place(OVEN, level, other, Direction.NORTH);
            Map<BlockPos, BlockState> b = snapshot(level, footprint(other));
            BlockPos orphan = new BlockPos(1, 64, 0);
            // Facing EAST: the core search steps WEST, onto air (B's blocks are east of it).
            level.states.put(orphan, OVEN.defaultBlockState().setValue(DummyableBlock.FACING, Direction.EAST).setValue(DummyableBlock.TYPE, DummyBlockType.DUMMY));
            check(OVEN.findCore(level, orphan) == null, "the orphan has no core");
            Player player = new Player();
            player.creative = creative;
            breakByPlayer(level, orphan, player);
            check(!level.states.containsKey(orphan) && intact(level, b) && level.states.size() == 9 && Block.DROPS.isEmpty(),
                    (creative ? "creative" : "survival") + ": breaking an orphan next to oven B removes only the orphan; B keeps its 9 blocks; no drop");
        }

        // Block entities and tickers by part.
        Level level = level();
        BlockState coreState = OVEN.createCoreState(Direction.NORTH);
        BlockState extra = coreState.setValue(DummyableBlock.TYPE, DummyBlockType.EXTRA);
        BlockState dummy = coreState.setValue(DummyableBlock.TYPE, DummyBlockType.DUMMY);
        check(OVEN.newBlockEntity(core, coreState) instanceof HeaterOvenBlockEntity && OVEN.newBlockEntity(core, extra) instanceof ProxyComboBlockEntity
                        && OVEN.newBlockEntity(core, dummy) == null,
                "the core is the oven block entity, an EXTRA part a proxy, a plain dummy nothing");
        check(OVEN.getTicker(level, coreState, null) != null && OVEN.getTicker(level, dummy, null) == null && OVEN.getTicker(level, extra, null) == null,
                "only the core ticks");
        section("2. heating oven removal");
    }

    // ---- 3. Heating oven heat ---------------------------------------------------------------------------------------

    static HeaterOvenBlockEntity ovenBE(Level level, BlockPos pos) {
        HeaterOvenBlockEntity be = new HeaterOvenBlockEntity(pos, new BlockState());
        level.put(be);
        return be;
    }

    static HeaterFireboxBlockEntity firebox(Level level, BlockPos pos) {
        HeaterFireboxBlockEntity be = new HeaterFireboxBlockEntity(pos, new BlockState());
        level.put(be);
        return be;
    }

    static void ovenHeat() {
        int burn = (int) (COAL_BURN * COAL_TIME_MOD * OVEN_TIME_MULT);
        int heat = OVEN_BASE_HEAT * COAL_HEAT_MOD;
        check(burn == 250 && heat == 1_000, "original numbers: coal burns 1,600 x 1.25 x 0.125 = 250 ticks at 500 x 2 = 1,000 TU/t");
        check(HeaterOvenBlockEntity.baseHeat == OVEN_BASE_HEAT && HeaterOvenBlockEntity.timeMult == OVEN_TIME_MULT
                        && HeaterOvenBlockEntity.maxHeatEnergy == OVEN_MAX_HEAT && HeaterOvenBlockEntity.heatEff == 0.5D,
                "production constants: 500 TU base, x0.125 time, 500,000 TU cap, keeps half of the pulled heat");

        reset();
        Level level = level();
        BlockPos pos = new BlockPos(0, 65, 0);
        HeaterOvenBlockEntity oven = ovenBE(level, pos);
        oven.slots.set(0, new ItemStack(Items.COAL, 2));
        level.time++;
        oven.updateEntity();
        check(oven.burnTime == burn && oven.maxBurnTime == burn && oven.burnHeat == heat && oven.heatEnergy == heat && oven.slots.get(0).getCount() == 1,
                "the first tick lights one coal: 250 ticks at 1,000 TU/t, +1,000 TU (got " + oven.burnTime + " ticks, " + oven.burnHeat + " TU/t, " + oven.heatEnergy + " TU)");
        int ticks = 1;
        while(oven.slots.get(0).getCount() == 1 && ticks < 1_000) {
            level.time++;
            oven.updateEntity();
            ticks++;
        }
        // Lit on tick 1 (burnTime 250), counts down on ticks 2-251, the second coal lights on tick 252: 251 heating ticks
        // per coal, as the original TileEntityFireboxBase loop (light, then decrement while below the cap).
        check(ticks == 252 && oven.heatEnergy == 252 * heat, "the second coal lights on tick 252 after 251 heating ticks; 1,000 TU every tick ("
                + ticks + ", " + oven.heatEnergy + " TU)");

        // The cap: 500,000 TU; at the cap the burn time does not run down.
        oven.heatEnergy = OVEN_MAX_HEAT - 300;
        int before = oven.burnTime;
        level.time++;
        oven.updateEntity();
        check(oven.heatEnergy == OVEN_MAX_HEAT && oven.burnTime == before - 1, "below the cap the burn time runs down and heat is capped at 500,000");
        level.time++;
        oven.updateEntity();
        check(oven.heatEnergy == OVEN_MAX_HEAT && oven.burnTime == before - 1, "at the cap the fuel is not used up");

        // Bottom pull: all the heat of an IHeatSource below (limited by the room left), half of it kept.
        int[][] cases = {
                // source heat, oven heat, oven has fuel (1) -> source after, oven after
                {10_000, 0, 0, 0, 5_000 - 5},                 // no fuel: decay of max(5,000 / 1,000, 1) in the same tick
                {200_000, 0, 1, 0, 100_000 + 1_000},          // fuel: the pull, then the burn heat
                {3, 0, 1, 0, 1 + 1_000},                      // (int) (3 * 0.5) = 1
                {10_000, 499_500, 1, 9_500, OVEN_MAX_HEAT},   // only the 500 TU of room is pulled
                {0, 1_000, 1, 0, 2_000},                      // an empty source gives nothing
        };
        for(int[] c : cases) {
            reset();
            Level l = level();
            HeaterFireboxBlockEntity source = firebox(l, new BlockPos(0, 64, 0));
            HeaterOvenBlockEntity o = ovenBE(l, new BlockPos(0, 65, 0));
            source.heatEnergy = c[0];
            o.heatEnergy = c[1];
            if(c[2] == 1) o.slots.set(0, new ItemStack(Items.COAL, 1));
            l.time++;
            o.updateEntity();
            check(source.heatEnergy == c[3] && o.heatEnergy == c[4], "source " + c[0] + " TU under an oven at " + c[1] + " TU" + (c[2] == 1 ? " lighting coal" : "")
                    + " -> source " + c[3] + ", oven " + c[4] + " (got " + source.heatEnergy + ", " + o.heatEnergy + ")");
        }
        reset();
        Level l = level();
        HeaterOvenBlockEntity lower = ovenBE(l, new BlockPos(0, 64, 0));
        HeaterOvenBlockEntity upper = ovenBE(l, new BlockPos(0, 65, 0));
        lower.heatEnergy = 40_000;
        l.time++;
        upper.updateEntity();
        check(lower.heatEnergy == 0 && upper.heatEnergy == 20_000 - 20, "an oven below is a heat source too: 40,000 TU pulled, 20,000 kept (then decay)");
        reset();
        l = level();
        BatterySocketBlockEntity notASource = new BatterySocketBlockEntity(new BlockPos(0, 64, 0), facing(l, new BlockPos(0, 64, 0), Direction.NORTH));
        l.put(notASource);
        HeaterOvenBlockEntity alone = ovenBE(l, new BlockPos(0, 65, 0));
        alone.heatEnergy = 5_000;
        l.time++;
        alone.updateEntity();
        check(alone.heatEnergy == 5_000 - 5, "a block entity that is not a heat source gives nothing");
        section("3. heating oven heat");
    }

    // ---- 4. Electric furnace processing -----------------------------------------------------------------------------

    static void processing() {
        check(MachineElectricFurnaceBlockEntity.MAX_POWER == FURNACE_MAX_POWER && MachineElectricFurnaceBlockEntity.BASE_PROCESS_TIME == FURNACE_TICKS
                        && MachineElectricFurnaceBlockEntity.BASE_CONSUMPTION == FURNACE_HE && MachineElectricFurnaceBlockEntity.COOLDOWN == FURNACE_COOLDOWN,
                "production constants: 100,000 HE, 100 ticks, 50 HE/t, cooldown 20");
        reset();
        Level level = level();
        BlockPos pos = new BlockPos(0, 64, 0);
        MachineElectricFurnaceBlockEntity f = furnace(level, pos);
        check(f.getContainerSize() == 4 && f.getMaxPower() == FURNACE_MAX_POWER, "4 slots, 100,000 HE buffer");
        f.power = FURNACE_MAX_POWER;
        f.slots.set(1, new ItemStack(RAW_IRON, 3));
        for(int t = 1; t < FURNACE_TICKS; t++) tick(f);
        check(f.progress == 99 && f.slots.get(2).isEmpty() && f.power == FURNACE_MAX_POWER - 99L * FURNACE_HE,
                "after 99 ticks: progress 99, no output, 99 x 50 HE used (" + f.progress + ", " + f.power + ")");
        tick(f);
        check(f.progress == 0 && f.slots.get(2).is(Items.IRON_INGOT) && f.slots.get(2).getCount() == 1 && f.slots.get(1).getCount() == 2
                        && f.power == FURNACE_MAX_POWER - 100L * FURNACE_HE,
                "tick 100: one iron ingot, one raw iron used, progress back to 0, 5,000 HE used");
        for(int t = 0; t < 2 * FURNACE_TICKS; t++) tick(f);
        check(f.slots.get(2).getCount() == 3 && f.slots.get(1).isEmpty() && f.power == FURNACE_MAX_POWER - 300L * FURNACE_HE,
                "three items in 300 ticks for 15,000 HE; the input is used up");
        long idle = f.power;
        for(int t = 0; t < 50; t++) tick(f);
        check(f.power == idle && f.progress == 0, "idle (no input): no power used, no progress");

        // Soot every 20 game ticks while working (game time 20, 40, 60, 80, 100 during one item).
        reset();
        level = level();
        f = furnace(level, pos);
        f.power = FURNACE_MAX_POWER;
        f.slots.set(1, new ItemStack(RAW_IRON, 1));
        for(int t = 0; t < FURNACE_TICKS; t++) tick(f);
        check(PollutionHandler.calls == 5 && Math.abs(PollutionHandler.soot - 5 * PollutionHandler.SOOT_PER_SECOND) < 1e-6F,
                "soot once per 20 game ticks while working: 5 calls in 100 ticks (" + PollutionHandler.calls + ")");

        // Output merge and the stack limit.
        Object[][] limits = {
                // input, output already there, expected output after 300 ticks (3 items offered), description
                {RAW_IRON, new ItemStack(Items.IRON_INGOT, 10), 13, "10 iron ingots + 3 = 13 (merged)"},
                {RAW_IRON, new ItemStack(Items.IRON_INGOT, 62), 64, "62 + 2: stops at 64"},
                {RAW_IRON, new ItemStack(Items.IRON_INGOT, 64), 64, "a full stack: nothing starts"},
                {RAW_IRON, new ItemStack(Items.GOLD_INGOT, 1), 1, "a different item in the output: nothing starts"},
                {DOUBLER, new ItemStack(DOUBLE_OUT, 60), 64, "a 2-item result: 60 + 2 + 2 = 64"},
                {DOUBLER, new ItemStack(DOUBLE_OUT, 63), 63, "a 2-item result does not start on 63 (NEO; the original would make 65)"},
                {SMALL_IN, new ItemStack(SMALL_OUT, 14), 16, "a result that stacks to 16: stops at 16"},
        };
        for(Object[] row : limits) {
            reset();
            level = level();
            f = furnace(level, pos);
            f.power = FURNACE_MAX_POWER;
            f.slots.set(1, new ItemStack((Item) row[0], 3));
            f.slots.set(2, ((ItemStack) row[1]).copy());
            Item outItem = ((ItemStack) row[1]).getItem();
            for(int t = 0; t < 3 * FURNACE_TICKS; t++) tick(f);
            int made = f.slots.get(2).getCount();
            int used = 3 - f.slots.get(1).getCount();
            int perItem = row[0] == DOUBLER ? 2 : 1;
            int startCount = ((ItemStack) row[1]).getCount();
            // Each finished item takes one input, adds its result count and costs 100 x 50 HE; a blocked start costs nothing.
            check(f.slots.get(2).is(outItem) && made == (int) row[2] && made - startCount == used * perItem && f.progress == 0
                            && f.power == FURNACE_MAX_POWER - (long) used * FURNACE_TICKS * FURNACE_HE,
                    row[3] + " (output " + made + ", " + used + " input used, power " + f.power + ")");
        }

        // No recipe, a blasting-only item, and the level-less lookup.
        reset();
        level = level();
        f = furnace(level, pos);
        f.power = FURNACE_MAX_POWER;
        f.slots.set(1, new ItemStack(STICK, 1));
        for(int t = 0; t < 120; t++) tick(f);
        boolean noSmelt = f.progress == 0 && f.power == FURNACE_MAX_POWER && f.slots.get(2).isEmpty();
        f.slots.set(1, new ItemStack(BLAST_ONLY, 1));
        for(int t = 0; t < 120; t++) tick(f);
        check(noSmelt && f.progress == 0 && f.power == FURNACE_MAX_POWER && f.slots.get(2).isEmpty(),
                "no smelting recipe (a stick, an item with only a blasting recipe): nothing happens, no power used");
        check(f.getSmeltingResult(new ItemStack(RAW_IRON)).is(Items.IRON_INGOT) && f.getSmeltingResult(new ItemStack(DOUBLER)).getCount() == 2
                        && f.getSmeltingResult(new ItemStack(STICK)).isEmpty() && f.getSmeltingResult(ItemStack.EMPTY).isEmpty(),
                "getSmeltingResult: the first smelting recipe's result (count 2 for the doubler), empty without a recipe");
        MachineElectricFurnaceBlockEntity loose = new MachineElectricFurnaceBlockEntity(pos, FURNACE.defaultBlockState());
        check(loose.getLevel() == null && loose.getSmeltingResult(new ItemStack(RAW_IRON)).isEmpty() && !loose.canPlaceItem(1, new ItemStack(RAW_IRON)),
                "without a level getSmeltingResult is empty and slot 1 accepts nothing");

        // Power loss: progress is lost and a 20 tick cooldown starts; restored power resumes on the 20th tick.
        reset();
        level = level();
        f = furnace(level, pos);
        f.slots.set(1, new ItemStack(RAW_IRON, 2));
        f.power = 30L * FURNACE_HE + 49;
        for(int t = 0; t < 30; t++) tick(f);
        check(f.progress == 30 && f.power == 49, "30 ticks on 1,549 HE: progress 30, 49 HE left");
        tick(f);
        check(f.progress == 0 && cooldown(f) == FURNACE_COOLDOWN && f.power == 49,
                "49 HE < 50: the progress is lost, cooldown 20, nothing used (" + f.progress + ", " + cooldown(f) + ")");
        f.power = FURNACE_MAX_POWER;
        int first = -1;
        for(int t = 1; t <= 40 && first < 0; t++) {
            tick(f);
            if(f.progress > 0) first = t;
        }
        check(first == FURNACE_COOLDOWN && f.progress == 1 && f.power == FURNACE_MAX_POWER - FURNACE_HE,
                "with power back, ticks 1-19 wait out the cooldown and work resumes on tick 20 (" + first + "), from progress 0");
        for(int t = 0; t < FURNACE_TICKS - 1; t++) tick(f);
        check(f.slots.get(2).getCount() == 1, "the item then takes the full 100 ticks");

        // A blocked output also loses the progress (no cooldown: there is power).
        reset();
        level = level();
        f = furnace(level, pos);
        f.power = FURNACE_MAX_POWER;
        f.slots.set(1, new ItemStack(RAW_IRON, 2));
        for(int t = 0; t < 50; t++) tick(f);
        f.slots.set(2, new ItemStack(Items.IRON_INGOT, 64));
        long p = f.power;
        tick(f);
        check(f.progress == 0 && f.power == p && cooldown(f) == 0, "a full output at progress 50: progress lost, nothing used, no cooldown");
        f.slots.set(2, ItemStack.EMPTY);
        tick(f);
        check(f.progress == 1, "space again: the item starts over from 0");
        section("4. electric furnace processing");
    }

    // ---- 5. Upgrades ------------------------------------------------------------------------------------------------

    /** Original TileEntityMachineElectricFurnace.java:157-168, written out: {maxProgress, consumption}. */
    static int[] formula(int speed, int power) {
        return new int[] {100 - speed * 25 + power * 10, 50 + speed * 50 - power * 15};
    }

    static void upgrades() {
        reset();
        Level level = level();
        BlockPos pos = new BlockPos(0, 64, 0);
        MachineElectricFurnaceBlockEntity f = furnace(level, pos);
        f.power = FURNACE_MAX_POWER;
        check(f.getValidUpgrades().equals(Map.of(UpgradeType.SPEED, 3, UpgradeType.POWER, 3)), "valid upgrades: speed and power, up to level 3");
        check(f.canProvideInfo(UpgradeType.SPEED, 1, null) && f.canProvideInfo(UpgradeType.POWER, 1, null) && !f.canProvideInfo(UpgradeType.OVERDRIVE, 1, null)
                && !f.canProvideInfo(UpgradeType.EFFECT, 1, null), "upgrade tooltips for speed and power only");

        // The original's table, by hand.
        int[][] table = {
                // speed, power, ticks, HE/t
                {0, 0, 100, 50}, {1, 0, 75, 100}, {2, 0, 50, 150}, {3, 0, 25, 200}, {0, 1, 110, 35}, {0, 2, 120, 20}, {0, 3, 130, 5},
        };
        for(int[] row : table) {
            int[] got = formula(row[0], row[1]);
            check(got[0] == row[2] && got[1] == row[3], "formula: speed " + row[0] + ", power " + row[1] + " -> " + row[2] + " ticks, " + row[3] + " HE/t");
        }

        // Reachable in game: one upgrade item in slot 3 (the only upgrade slot), through the production UpgradeManagerNT.
        for(int[] row : table) {
            if(row[0] > 0) f.slots.set(3, new ItemStack(upgrade(UpgradeType.SPEED, row[0])));
            else if(row[1] > 0) f.slots.set(3, new ItemStack(upgrade(UpgradeType.POWER, row[1])));
            else f.slots.set(3, ItemStack.EMPTY);
            tick(f);
            check(f.maxProgress == row[2] && f.consumption == row[3], "slot 3 " + (row[0] > 0 ? "speed " + row[0] : row[1] > 0 ? "power " + row[1] : "empty")
                    + ": " + row[2] + " ticks, " + row[3] + " HE/t (got " + f.maxProgress + ", " + f.consumption + ")");
        }
        // Real runs: speed III makes an item in 25 ticks for 200 HE/t, power III in 130 ticks for 5 HE/t.
        for(int[] row : new int[][] {{3, 0, 25, 200}, {0, 3, 130, 5}, {1, 0, 75, 100}, {0, 1, 110, 35}}) {
            reset();
            level = level();
            f = furnace(level, pos);
            f.power = FURNACE_MAX_POWER;
            f.slots.set(3, new ItemStack(row[0] > 0 ? upgrade(UpgradeType.SPEED, row[0]) : upgrade(UpgradeType.POWER, row[1])));
            f.slots.set(1, new ItemStack(RAW_IRON, 1));
            int t = 0;
            while(f.slots.get(2).isEmpty() && t < 500) {
                tick(f);
                t++;
            }
            check(t == row[2] && f.power == FURNACE_MAX_POWER - (long) row[2] * row[3],
                    (row[0] > 0 ? "speed " + row[0] : "power " + row[1]) + ": one item in " + row[2] + " ticks for " + row[2] * row[3] + " HE (" + t + ", " + (FURNACE_MAX_POWER - f.power) + ")");
        }

        // Every combination of speed 0-3 and power 0-3 (two upgrade types at once cannot be put into the single
        // upgrade slot in game; the levels are set in the production UpgradeManagerNT after its slot cache is warm).
        int combos = 0;
        String bad = null;
        for(int s = 0; s <= 3; s++) {
            for(int pw = 0; pw <= 3; pw++) {
                reset();
                level = level();
                f = furnace(level, pos);
                f.power = FURNACE_MAX_POWER;
                tick(f);
                f.upgradeManager.upgrades.clear();
                if(s > 0) f.upgradeManager.upgrades.put(UpgradeType.SPEED, s);
                if(pw > 0) f.upgradeManager.upgrades.put(UpgradeType.POWER, pw);
                tick(f);
                int[] want = formula(s, pw);
                if(f.maxProgress == want[0] && f.consumption == want[1]) combos++;
                else if(bad == null) bad = "speed " + s + ", power " + pw + ": " + f.maxProgress + "/" + f.consumption + " != " + want[0] + "/" + want[1];
            }
        }
        check(combos == 16, "all 16 combinations of speed 0-3 and power 0-3 follow the formula (" + combos + ")" + (bad == null ? "" : "; " + bad));

        // Levels above 3 are capped by getValidUpgrades; other upgrade types are ignored.
        reset();
        level = level();
        f = furnace(level, pos);
        f.power = FURNACE_MAX_POWER;
        f.slots.set(3, new ItemStack(upgrade(UpgradeType.SPEED, 5)));
        tick(f);
        check(f.maxProgress == 25 && f.consumption == 200 && f.upgradeManager.getLevel(UpgradeType.SPEED) == 3, "a level 5 speed upgrade counts as level 3");
        f.slots.set(3, new ItemStack(upgrade(UpgradeType.POWER, 4)));
        tick(f);
        check(f.maxProgress == 130 && f.consumption == 5, "a level 4 power upgrade counts as level 3");
        boolean ignored = true;
        for(UpgradeType type : new UpgradeType[] {UpgradeType.OVERDRIVE, UpgradeType.EFFECT, UpgradeType.AFTERBURN, UpgradeType.FORTUNE, UpgradeType.LM_SMELTER}) {
            for(int tier = 1; tier <= 3; tier++) {
                f.slots.set(3, new ItemStack(upgrade(type, tier)));
                tick(f);
                ignored &= f.maxProgress == 100 && f.consumption == 50 && f.upgradeManager.upgrades.isEmpty();
            }
        }
        check(ignored, "overdrive, effect, afterburn, fortune and smelter upgrades change nothing");
        f.slots.set(3, new ItemStack(upgrade(UpgradeType.SPEED, 2)));
        tick(f);
        boolean changed = f.maxProgress == 50;
        f.slots.set(3, ItemStack.EMPTY);
        tick(f);
        check(changed && f.maxProgress == 100 && f.consumption == 50, "taking the upgrade out restores 100 ticks and 50 HE/t on the next tick");
        section("5. upgrades");
    }

    // ---- 6. Slots and power ----------------------------------------------------------------------------------------

    static void slots() {
        reset();
        Level level = level();
        BlockPos pos = new BlockPos(0, 64, 0);
        MachineElectricFurnaceBlockEntity f = furnace(level, pos);
        boolean faces = true, take = true;
        ItemStack any = new ItemStack(Items.IRON_INGOT);
        for(Direction d : Direction.values()) {
            faces &= Arrays.equals(f.getSlotsForFace(d), new int[] {0, 1, 2});
            take &= f.canTakeItemThroughFace(2, any, d) && !f.canTakeItemThroughFace(0, pack(5), d) && !f.canTakeItemThroughFace(1, new ItemStack(RAW_IRON), d)
                    && !f.canTakeItemThroughFace(3, new ItemStack(upgrade(UpgradeType.SPEED, 1)), d);
        }
        check(faces, "every face exposes slots {0, 1, 2}; the upgrade slot 3 is not reachable by automation");
        check(take, "automation extracts only slot 2");
        ItemStack battery = pack(1_000);
        ItemStack speed = new ItemStack(upgrade(UpgradeType.SPEED, 1));
        boolean insert = true;
        for(Direction d : Direction.values()) {
            insert &= f.canPlaceItemThroughFace(0, battery, d) && !f.canPlaceItemThroughFace(0, new ItemStack(RAW_IRON), d)
                    && f.canPlaceItemThroughFace(1, new ItemStack(RAW_IRON), d) && f.canPlaceItemThroughFace(1, new ItemStack(DOUBLER), d)
                    && !f.canPlaceItemThroughFace(1, new ItemStack(STICK), d) && !f.canPlaceItemThroughFace(1, new ItemStack(BLAST_ONLY), d)
                    && !f.canPlaceItemThroughFace(1, battery, d)
                    && !f.canPlaceItemThroughFace(2, any, d) && !f.canPlaceItemThroughFace(2, new ItemStack(RAW_IRON), d);
        }
        check(insert, "insertion: batteries into 0, smeltable items into 1, nothing into 2");
        check(f.canPlaceItem(3, speed) && !f.canPlaceItem(3, new ItemStack(RAW_IRON)) && !f.canPlaceItem(2, any),
                "slot 3 takes only upgrades (the menu's slot); slot 2 takes nothing");

        // Battery charging from slot 0: the production Library.chargeTEFromItems rule, lithium discharges 10,000 HE/t.
        long rate = PACK.getDischargeRate(battery);
        check(rate == 10_000L, "a lithium battery discharges 10,000 HE/t");
        f.slots.set(0, pack(1_000_000L));
        f.power = 0;
        tick(f);
        check(f.power == rate && PACK.getCharge(f.slots.get(0)) == 1_000_000L - rate, "an idle tick moves 10,000 HE from the battery");
        f.power = FURNACE_MAX_POWER - 3_000;
        tick(f);
        check(f.power == FURNACE_MAX_POWER && PACK.getCharge(f.slots.get(0)) == 1_000_000L - rate - 3_000, "only the room left is charged (3,000 HE)");
        f.slots.set(0, pack(30));
        f.power = 0;
        f.slots.set(1, new ItemStack(RAW_IRON, 1));
        tick(f);
        check(f.progress == 0 && f.power == 30 && cooldown(f) == FURNACE_COOLDOWN, "30 HE from a nearly empty battery is below 50: no work, cooldown");
        f.slots.set(0, pack(1_000_000L));
        setCooldown(f, 0);
        f.power = 0;
        tick(f);
        check(f.progress == 1 && f.power == rate - FURNACE_HE, "the battery charges before the power check: work starts in the same tick");

        // Six-face subscription: a cable on each face (real energy network, an output battery socket) powers the furnace.
        for(Direction d : Direction.values()) {
            reset();
            Level l = level();
            MachineElectricFurnaceBlockEntity furnace = furnace(l, pos);
            // One cable on the face, then a line leading away (east from the top/bottom cable, so only that one touches
            // the furnace) to an output battery socket whose front faces the last cable.
            Direction away = d.getAxis() == Direction.Axis.VERTICAL ? Direction.EAST : d;
            BlockPos c = pos.relative(d);
            cable(l, c);
            for(int i = 0; i < 3; i++) {
                c = c.relative(away);
                cable(l, c);
            }
            BatterySocketBlockEntity socket = provider(l, c.relative(away), away.getOpposite());
            socket.updateEntity();
            net(l);
            long start = socket.getPower();
            for(int t = 0; t < 40; t++) {
                l.time = t;
                socket.updateEntity();
                furnace.updateEntity();
                transfer(l);
            }
            check(furnace.power > 0 && furnace.power == start - socket.getPower(),
                    d + " face: a cable there powers the furnace (" + furnace.power + " HE, exactly what the socket sent)");
        }
        reset();
        Level l = level();
        MachineElectricFurnaceBlockEntity furnace = furnace(l, pos);
        BlockPos corner = pos.offset(1, 0, 1);
        cable(l, corner);
        cable(l, corner.relative(Direction.EAST));
        BatterySocketBlockEntity socket = provider(l, corner.relative(Direction.EAST, 3), Direction.WEST);
        cable(l, corner.relative(Direction.EAST, 2));
        socket.updateEntity();
        net(l);
        for(int t = 0; t < 40; t++) {
            l.time = t;
            socket.updateEntity();
            furnace.updateEntity();
            transfer(l);
        }
        check(furnace.power == 0, "a cable at a diagonal corner does not connect");
        DirPos[] cons = furnace.getConPos();
        Set<String> sides = new TreeSet<>();
        for(DirPos c : cons) sides.add(c.getDir() + "@" + (c.getX() - pos.getX()) + "," + (c.getY() - pos.getY()) + "," + (c.getZ() - pos.getZ()));
        check(cons.length == 6 && sides.size() == 6 && sides.contains("UP@0,1,0") && sides.contains("DOWN@0,-1,0") && sides.contains("EAST@1,0,0"),
                "six connection points, one per face, each facing away (TilePortShapes.around): " + sides);
        section("6. slots and power");
    }

    // ---- 7. LIT and persistence ------------------------------------------------------------------------------------

    static void litAndPersistence() {
        reset();
        Level level = level();
        BlockPos pos = new BlockPos(0, 64, 0);
        MachineElectricFurnaceBlockEntity f = furnace(level, pos);
        f.power = FURNACE_MAX_POWER;
        f.slots.set(1, new ItemStack(RAW_IRON, 3));
        check(!lit(level, pos), "a new furnace is unlit");
        int setsBefore = level.setBlocks.size();
        List<Integer> onTicks = new ArrayList<>(), offTicks = new ArrayList<>();
        boolean prev = false;
        for(int t = 1; t <= 3 * FURNACE_TICKS + 5; t++) {
            tick(f);
            boolean now = lit(level, pos);
            if(now && !prev) onTicks.add(t);
            if(!now && prev) offTicks.add(t);
            prev = now;
        }
        check(onTicks.equals(List.of(1)) && offTicks.equals(List.of(3 * FURNACE_TICKS)),
                "LIT on at tick 1, stays on across the item boundaries (ticks 100, 200), off at tick 300 when the input is used up (on " + onTicks + ", off " + offTicks + ")");
        check(level.setBlocks.size() - setsBefore == 2, "exactly two block changes for three items: on, off (no flicker between items)");
        check(level.getBlockEntity(pos) == f && !f.isRemoved() && level.getBlockState(pos).is(FURNACE) && Containers.DROPS.isEmpty(),
                "the block entity survives the LIT changes (same block); nothing dropped");
        check(level.getBlockState(pos).getValue(MachineElectricFurnaceBlock.FACING) == Direction.NORTH, "the facing is kept");

        // Power failure turns it off; with power back it lights again after the cooldown.
        f.slots.set(1, new ItemStack(RAW_IRON, 2));
        f.power = 10L * FURNACE_HE;
        for(int t = 0; t < 10; t++) tick(f);
        boolean onBefore = lit(level, pos);
        tick(f);
        check(onBefore && !lit(level, pos) && f.progress == 0, "out of power: LIT off and progress 0");
        f.power = FURNACE_MAX_POWER;
        for(int t = 0; t < 19; t++) tick(f);
        boolean darkDuringCooldown = !lit(level, pos);
        tick(f);
        check(darkDuringCooldown && lit(level, pos), "LIT stays off during the 19 cooldown ticks and comes on when work resumes");

        // A blocked output: LIT off.
        f.slots.set(2, new ItemStack(Items.IRON_INGOT, 64));
        tick(f);
        check(!lit(level, pos), "a full output turns LIT off");

        // Removal drops the contents only when the block really changes.
        f.slots.set(2, new ItemStack(Items.IRON_INGOT, 5));
        f.slots.set(3, new ItemStack(upgrade(UpgradeType.SPEED, 1)));
        BlockState state = level.getBlockState(pos);
        level.setBlock(pos, state.setValue(MachineElectricFurnaceBlock.LIT, !state.getValue(MachineElectricFurnaceBlock.LIT)), 3);
        check(Containers.DROPS.isEmpty() && level.getBlockEntity(pos) == f && !f.isRemoved(), "a property change of the same block drops nothing and keeps the block entity");
        level.removeBlock(pos, false);
        int dropped = 0;
        for(Containers.Drop d : Containers.DROPS) dropped += d.stack().getCount();
        check(Containers.DROPS.size() == 3 && dropped == 2 + 5 + 1 && f.isRemoved() && level.getBlockEntity(pos) == null,
                "removing the block drops the input, output and upgrade (" + Containers.DROPS + ") and removes the block entity");

        // NBT: power and progress only (cooldown is not saved, as upstream); load clamps.
        reset();
        level = level();
        f = furnace(level, pos);
        f.power = 12_345;
        f.progress = 42;
        f.maxProgress = 75;
        f.consumption = 100;
        setCooldown(f, 15);
        f.slots.set(1, new ItemStack(RAW_IRON, 7));
        CompoundTag tag = save(f);
        check(keys(tag).equals(new TreeSet<>(Set.of("Items", "power", "progress"))) && tag.getLong("power") == 12_345 && tag.getInt("progress") == 42,
                "saved keys: Items, power (long), progress (int) - no cooldown, no maxProgress/consumption (" + keys(tag) + ")");
        MachineElectricFurnaceBlockEntity copy = new MachineElectricFurnaceBlockEntity(pos, FURNACE.defaultBlockState());
        load(copy, tag);
        check(copy.power == 12_345 && copy.progress == 42 && cooldown(copy) == 0 && copy.slots.get(1).is(RAW_IRON) && copy.slots.get(1).getCount() == 7,
                "round trip: power, progress and the items come back; the cooldown starts at 0");
        CompoundTag odd = save(f);
        odd.putLong("power", FURNACE_MAX_POWER + 5_000);
        odd.putInt("progress", -3);
        load(copy, odd);
        check(copy.power == FURNACE_MAX_POWER && copy.progress == 0, "load clamps power to 100,000 and a negative progress to 0 (NEO)");

        // Sync: after the base entries, power, maxProgress, progress (upstream) and consumption (NEO).
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        f.serialize(buf);
        List<Object> values = buf.values();
        check(values.size() == 6 && values.get(2).equals(12_345L) && values.get(3).equals(75) && values.get(4).equals(42) && values.get(5).equals(100),
                "sync order: base, then power (long), maxProgress, progress, consumption (" + values + ")");
        MachineElectricFurnaceBlockEntity client = new MachineElectricFurnaceBlockEntity(pos, FURNACE.defaultBlockState());
        client.deserialize(buf);
        check(client.power == 12_345 && client.maxProgress == 75 && client.progress == 42 && client.consumption == 100 && client.hasPower(),
                "the client copy reads them back in that order");
        check(f.getProgressScaled(52) == 42 * 52 / 75 && f.getPowerScaled(52) == 12_345L * 52 / FURNACE_MAX_POWER, "screen scaling: progress / maxProgress, power / 100,000");

        // Upstream randomDisplayTick: smoke then a flame 0.52 in front of the lit face, 0-6/16 up, up to 0.3 sideways.
        Level particleLevel = level();
        BlockPos at = new BlockPos(3, 64, 7);
        FURNACE.animateTick(FURNACE.defaultBlockState(), particleLevel, at, particleLevel.random);
        check(particleLevel.particles.isEmpty(), "an unlit furnace spawns no particles");
        boolean placed = true;
        for(Direction d : new Direction[] { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST }) {
            BlockState litState = FURNACE.defaultBlockState().setValue(MachineElectricFurnaceBlock.FACING, d).setValue(MachineElectricFurnaceBlock.LIT, true);
            for(int i = 0; i < 50; i++) {
                particleLevel.particles.clear();
                FURNACE.animateTick(litState, particleLevel, at, particleLevel.random);
                List<Level.Particle> p = particleLevel.particles;
                if(p.size() != 2 || p.get(0).type() != ParticleTypes.SMOKE || p.get(1).type() != ParticleTypes.FLAME
                        || p.get(0).x() != p.get(1).x() || p.get(0).y() != p.get(1).y() || p.get(0).z() != p.get(1).z()) {
                    placed = false;
                    continue;
                }
                double fx = p.get(0).x() - (at.getX() + 0.5D), fy = p.get(0).y() - at.getY(), fz = p.get(0).z() - (at.getZ() + 0.5D);
                double ahead = fx * d.getStepX() + fz * d.getStepZ();
                double sideways = d.getStepX() == 0 ? fx : fz;
                placed &= Math.abs(ahead - 0.52D) < 1e-9 && sideways >= -0.3D - 1e-6 && sideways < 0.3D + 1e-6 && fy >= 0D && fy < 6.0D / 16.0D;
            }
        }
        check(placed, "a lit furnace spawns smoke then flame at one point 0.52 in front of its facing, up to 0.3 sideways and 0-6/16 up, for all four facings");
        section("7. LIT and persistence");
    }

    // ---- 8. Experience and menu ------------------------------------------------------------------------------------

    static ServerPlayer serverPlayer(ServerLevel level) {
        ServerPlayer player = new ServerPlayer();
        player.world = level;
        player.getInventory().player = player;
        return player;
    }

    static Slot output(MachineElectricFurnaceMenu menu) {
        return menu.slots.get(MachineElectricFurnaceBlockEntity.SLOT_OUTPUT);
    }

    /** A player picks up n items from the slot: Slot.tryRemove/safeTake -> remove(n), then onTake (AbstractContainerMenu PICKUP). */
    static ItemStack take(Slot slot, Player player, int n) {
        ItemStack taken = slot.remove(n);
        slot.onTake(player, taken);
        return taken;
    }

    /** AbstractContainerMenu QUICK_MOVE: repeat quickMoveStack while it moves something and the slot keeps the same item. */
    static void shiftClick(MachineElectricFurnaceMenu menu, Player player, int index) {
        Slot slot = menu.slots.get(index);
        for(ItemStack moved = menu.quickMoveStack(player, index); !moved.isEmpty() && ItemStack.isSameItem(slot.getItem(), moved);
            moved = menu.quickMoveStack(player, index)) {
        }
    }

    static void experience() {
        reset();
        ServerLevel level = serverLevel();
        BlockPos pos = new BlockPos(0, 64, 0);
        MachineElectricFurnaceBlockEntity f = furnace(level, pos);
        ServerPlayer player = serverPlayer(level);
        MachineElectricFurnaceMenu menu = new MachineElectricFurnaceMenu(0, player.getInventory(), f);
        check(menu.slots.size() == 4 + 36 && output(menu) instanceof SlotSmeltingOutput, "4 machine slots, then the 36 player slots; slot 2 is the smelting output");
        check(!output(menu).mayPlace(new ItemStack(Items.IRON_INGOT)) && !output(menu).mayPlace(new ItemStack(RAW_IRON))
                && !menu.slots.get(1).mayPlace(new ItemStack(STICK)) && menu.slots.get(1).mayPlace(new ItemStack(RAW_IRON)),
                "nothing can be put into the output slot; the input slot takes smeltable items only");
        check(SlotSmeltingOutput.getSmeltingExperience(level, new ItemStack(Items.IRON_INGOT)) == 0.5F
                        && SlotSmeltingOutput.getSmeltingExperience(level, new ItemStack(STONE)) == 0.25F
                        && SlotSmeltingOutput.getSmeltingExperience(level, new ItemStack(STICK)) == 0F,
                "experience by result item: the first smelting recipe making it (iron ingot 0.5, not the later 0.75; blasting ignored); 0 without one");

        // Exact amounts (count x experience whole).
        f.slots.set(2, new ItemStack(Items.IRON_INGOT, 10));
        take(output(menu), player, 4);
        check(ExperienceOrb.AWARDS.equals(List.of(2)) && EventHooks.smelted == 1 && ItemStack.craftedBy == 4 && f.slots.get(2).getCount() == 6,
                "taking 4 iron ingots (0.5 each) awards 2 experience once (" + ExperienceOrb.AWARDS + ")");
        take(output(menu), player, 2);
        check(ExperienceOrb.AWARDS.equals(List.of(2, 1)), "the count resets after each take: 2 more ingots award 1 (" + ExperienceOrb.AWARDS + ")");
        f.slots.set(2, new ItemStack(Items.GOLD_INGOT, 3));
        take(output(menu), player, 3);
        check(ExperienceOrb.AWARDS.equals(List.of(2, 1, 3)), "3 gold ingots at 1.0 award 3");
        f.slots.set(2, new ItemStack(STICK, 5));
        take(output(menu), player, 5);
        check(ExperienceOrb.AWARDS.equals(List.of(2, 1, 3)) && EventHooks.smelted == 4, "an item no smelting recipe makes awards nothing (the event still fires)");
        f.slots.set(2, new ItemStack(SCRAP, 3));
        take(output(menu), player, 3);
        check(ExperienceOrb.AWARDS.equals(List.of(2, 1, 3, 3)),
                "3 results worth 2.0 each award 3: upstream pays 1 per item from 1.0 up (Minecraft 1.21's furnace would pay 6) (" + ExperienceOrb.AWARDS + ")");

        // A hotbar-key swap takes the stack without remove() and still pays (upstream's swap went through decrStackSize).
        ExperienceOrb.AWARDS.clear();
        f.slots.set(2, new ItemStack(Items.IRON_INGOT, 4));
        ItemStack swapped = output(menu).swapToEmptyHotbar(player);
        check(swapped.getCount() == 4 && f.slots.get(2).isEmpty() && ExperienceOrb.AWARDS.equals(List.of(2)),
                "a hotbar-key swap of 4 iron ingots (0.5 each) awards 2 experience once (" + ExperienceOrb.AWARDS + ")");

        // The fraction is a chance: 3 x 0.5 = 1.5 -> 1 or 2; 1 x 0.25 -> 0 or 1.
        Map<Integer, Integer> seen = new HashMap<>();
        for(int i = 0; i < 300; i++) {
            ExperienceOrb.AWARDS.clear();
            f.slots.set(2, new ItemStack(Items.IRON_INGOT, 3));
            take(output(menu), player, 3);
            int got = ExperienceOrb.AWARDS.size() == 1 ? ExperienceOrb.AWARDS.get(0) : -1;
            seen.merge(got, 1, Integer::sum);
        }
        check(seen.keySet().equals(Set.of(1, 2)), "1.5 experience: always 1 or 2, both occur in 300 takes (" + seen + ")");
        seen.clear();
        for(int i = 0; i < 400; i++) {
            ExperienceOrb.AWARDS.clear();
            f.slots.set(2, new ItemStack(STONE, 1));
            take(output(menu), player, 1);
            int got = ExperienceOrb.AWARDS.isEmpty() ? 0 : ExperienceOrb.AWARDS.size() == 1 ? ExperienceOrb.AWARDS.get(0) : -1;
            seen.merge(got, 1, Integer::sum);
        }
        check(seen.keySet().equals(Set.of(0, 1)), "0.25 experience: no orb or 1, both occur in 400 takes (" + seen + ")");

        // The client side awards nothing (and does not fail).
        reset();
        Level clientLevel = level();
        clientLevel.isClientSide = true;
        Player clientPlayer = new Player();
        clientPlayer.world = clientLevel;
        clientPlayer.getInventory().player = clientPlayer;
        MachineElectricFurnaceBlockEntity cf = furnace(clientLevel, pos);
        MachineElectricFurnaceMenu clientMenu = new MachineElectricFurnaceMenu(0, clientPlayer.getInventory(), cf);
        cf.slots.set(2, new ItemStack(Items.IRON_INGOT, 4));
        Throwable thrown = null;
        try {
            take(output(clientMenu), clientPlayer, 4);
            cf.slots.set(2, new ItemStack(Items.IRON_INGOT, 4));
            clientMenu.quickMoveStack(clientPlayer, MachineElectricFurnaceBlockEntity.SLOT_OUTPUT);
        } catch(Throwable t) {
            thrown = t;
        }
        check(thrown == null && ExperienceOrb.AWARDS.isEmpty(), "taking or shift-clicking on the client awards no experience"
                + (thrown == null ? "" : " (threw " + thrown + ")"));

        // Shift-click pays once for everything moved.
        reset();
        level = serverLevel();
        f = furnace(level, pos);
        player = serverPlayer(level);
        menu = new MachineElectricFurnaceMenu(0, player.getInventory(), f);
        f.slots.set(2, new ItemStack(Items.IRON_INGOT, 10));
        shiftClick(menu, player, MachineElectricFurnaceBlockEntity.SLOT_OUTPUT);
        int inInventory = 0;
        for(ItemStack s : player.getInventory().items) if(s.is(Items.IRON_INGOT)) inInventory += s.getCount();
        check(ExperienceOrb.AWARDS.equals(List.of(5)) && f.slots.get(2).isEmpty() && inInventory == 10 && EventHooks.smelted == 1,
                "shift-clicking 10 iron ingots moves them all and awards 5 experience once (" + ExperienceOrb.AWARDS + ")");
        // Only 4 fit: one award for the 4 moved, none for the 6 left behind.
        reset();
        player = serverPlayer(level);
        menu = new MachineElectricFurnaceMenu(0, player.getInventory(), f);
        for(int i = 0; i < 36; i++) player.getInventory().items.set(i, new ItemStack(STICK, 64));
        player.getInventory().items.set(0, new ItemStack(Items.IRON_INGOT, 60));
        f.slots.set(2, new ItemStack(Items.IRON_INGOT, 10));
        shiftClick(menu, player, MachineElectricFurnaceBlockEntity.SLOT_OUTPUT);
        check(ExperienceOrb.AWARDS.equals(List.of(2)) && f.slots.get(2).getCount() == 6 && player.getInventory().items.get(0).getCount() == 64,
                "with room for 4: 4 move, 2 experience once, 6 stay (" + ExperienceOrb.AWARDS + ")");

        // Automation gets nothing.
        reset();
        f.slots.set(2, new ItemStack(Items.IRON_INGOT, 10));
        ItemStack pulled = f.canTakeItemThroughFace(2, f.slots.get(2), Direction.DOWN) ? f.removeItem(2, 10) : ItemStack.EMPTY;
        check(pulled.getCount() == 10 && ExperienceOrb.AWARDS.isEmpty(), "a hopper pulling the output gets the items and no experience");

        // quickMoveStack from the player inventory.
        reset();
        player = serverPlayer(level);
        f = furnace(level, new BlockPos(5, 64, 0));
        menu = new MachineElectricFurnaceMenu(0, player.getInventory(), f);
        Object[][] routes = {
                {pack(500), 0, "a battery goes to slot 0"},
                {new ItemStack(upgrade(UpgradeType.SPEED, 1)), 3, "an upgrade goes to slot 3"},
                {new ItemStack(RAW_IRON, 5), 1, "a smeltable item goes to slot 1"},
        };
        for(Object[] row : routes) {
            ItemStack stack = (ItemStack) row[0];
            player.getInventory().items.set(9, stack.copy());
            menu.quickMoveStack(player, 4);
            int slot = (int) row[1];
            check(player.getInventory().items.get(9).isEmpty() && f.slots.get(slot).getItem() == stack.getItem() && f.slots.get(slot).getCount() == stack.getCount(),
                    row[2] + " (player inventory slot 9 = menu index 4)");
        }
        player.getInventory().items.set(9, new ItemStack(STICK, 7));
        ItemStack result = menu.quickMoveStack(player, 4);
        check(result.isEmpty() && player.getInventory().items.get(9).getCount() == 7 && f.slots.get(1).is(RAW_IRON) && f.slots.get(1).getCount() == 5,
                "a non-smeltable item stays in the player inventory");
        player.getInventory().items.set(9, new ItemStack(COBBLESTONE, 3));
        result = menu.quickMoveStack(player, 4);
        check(result.isEmpty() && player.getInventory().items.get(9).getCount() == 3 && f.slots.get(1).is(RAW_IRON),
                "a smeltable item does not displace a different input");
        section("8. experience and menu");
    }

    // ---- 9. Power budget -------------------------------------------------------------------------------------------

    record Chain(Level level, HeaterFireboxBlockEntity heater, MachineHeatBoilerBlockEntity boiler, MachineSteamEngineBlockEntity engine) {
        /** One tick: heater, boiler, then the boiler's steam into the engine tank, the engine, spent steam removed, water refilled. */
        long tick() {
            level.time++;
            heater.updateEntity();
            boiler.updateEntity();
            int steam = boiler.tanks[1].getFill();
            int room = engine.tanks[0].getMaxFill() - engine.tanks[0].getFill();
            int moved = Math.min(steam, room);
            boiler.tanks[1].setFill(steam - moved);
            engine.tanks[0].setFill(engine.tanks[0].getFill() + moved);
            engine.updateEntity();
            long he = engine.powerBuffer;
            engine.tanks[1].setFill(0);
            boiler.tanks[0].setFill(boiler.tanks[0].getMaxFill());
            return he;
        }
    }

    static Chain chain(boolean oven) {
        reset();
        Level level = level();
        HeaterFireboxBlockEntity heater = oven ? ovenBE(level, new BlockPos(0, 64, 0)) : firebox(level, new BlockPos(0, 64, 0));
        heater.slots.set(0, new ItemStack(Items.COAL, 64));
        heater.slots.set(1, new ItemStack(Items.COAL, 64));
        BlockPos boilerPos = new BlockPos(0, 65, 0);
        MachineHeatBoilerBlockEntity boiler = new MachineHeatBoilerBlockEntity(boilerPos, facing(level, boilerPos, Direction.NORTH));
        level.put(boiler);
        boiler.tanks[0].setFill(boiler.tanks[0].getMaxFill());
        BlockPos enginePos = new BlockPos(-10, 64, 0);
        MachineSteamEngineBlockEntity engine = new MachineSteamEngineBlockEntity(enginePos, facing(level, enginePos, Direction.NORTH));
        level.put(engine);
        return new Chain(level, heater, boiler, engine);
    }

    static void budget() {
        // The real engine: 170 HE per 100 mB of steam (Goal 9B), 5 ops in one tick make 850 HE.
        Chain probe = chain(false);
        probe.engine.tanks[0].setFill(100);
        probe.engine.updateEntity();
        long one = probe.engine.powerBuffer;
        probe.engine.tanks[1].setFill(0);
        probe.engine.tanks[0].setFill(500);
        probe.engine.updateEntity();
        check(one == HE_PER_ENGINE_OP && probe.engine.powerBuffer == 5 * HE_PER_ENGINE_OP, "the steam engine: 170 HE for 100 mB, 850 HE for 500 mB in one tick");

        for(boolean oven : new boolean[] {false, true}) {
            Chain c = chain(oven);
            for(int t = 0; t < 4_000; t++) c.tick();
            long total = 0, min = Long.MAX_VALUE, max = 0;
            for(int t = 0; t < 1_000; t++) {
                long he = c.tick();
                total += he;
                min = Math.min(min, he);
                max = Math.max(max, he);
            }
            long expected = oven ? 850 : 170;
            System.out.println("  info: " + (oven ? "heating oven" : "firebox") + " -> heat boiler -> steam engine, ticks 4,001-5,000: " + total
                    + " HE (" + min + "-" + max + " HE/t); heater " + c.heater.heatEnergy + " TU, boiler " + c.boiler.heat + " TU");
            check(total == expected * 1_000, (oven ? "heating oven" : "firebox") + " (coal) -> heat boiler -> steam engine: " + expected
                    + " HE/t over 1,000 steady ticks (" + total + " HE, " + min + "-" + max + " HE/t)");
        }

        // Three base furnaces on the firebox chain's 170 HE/t. Distribution model: each tick the engine's output is split
        // evenly (57, 57, 56) before the furnaces tick, as a network shares power among receivers that all want more; the
        // real cable network is checked in section 6.
        Chain c = chain(false);
        for(int t = 0; t < 4_000; t++) c.tick();
        MachineElectricFurnaceBlockEntity[] furnaces = new MachineElectricFurnaceBlockEntity[3];
        for(int i = 0; i < 3; i++) {
            furnaces[i] = furnace(c.level, new BlockPos(0, 70, i * 2));
            furnaces[i].slots.set(1, new ItemStack(RAW_IRON, 64));
        }
        boolean steady = true;
        String firstStall = null;
        long delivered = 0;
        for(int t = 0; t < 1_000; t++) {
            long he = c.tick();
            delivered += he;
            for(int i = 0; i < 3; i++) {
                MachineElectricFurnaceBlockEntity furnace = furnaces[i];
                furnace.power += he / 3 + (i < he % 3 ? 1 : 0);
                furnace.updateEntity();
                boolean ok = cooldown(furnace) == 0 && furnace.progress == (t + 1) % FURNACE_TICKS && lit(c.level, furnace.getBlockPos());
                if(!ok && firstStall == null) firstStall = "tick " + (t + 1) + " at " + furnace.getBlockPos() + ": cooldown " + cooldown(furnace)
                        + ", lit " + lit(c.level, furnace.getBlockPos()) + ", progress " + furnace.progress + ", power " + furnace.power;
                steady &= ok;
            }
        }
        boolean all = true;
        long stored = 0;
        StringBuilder state = new StringBuilder();
        for(MachineElectricFurnaceBlockEntity furnace : furnaces) {
            all &= furnace.slots.get(2).getCount() == 10;
            stored += furnace.power;
            state.append(furnace.slots.get(2).getCount()).append(" items/").append(furnace.power).append(" HE; ");
        }
        check(steady && all && delivered == 170_000 && stored == delivered - 3 * 1_000 * FURNACE_HE,
                "the firebox chain runs three base furnaces without a pause or a dark tick: 10 items each in 1,000 ticks, 150 HE/t used, "
                        + "20 HE/t left in the buffers (" + state + "delivered " + delivered + ")" + (firstStall == null ? "" : "; first stall: " + firstStall));

        // Exactly 50 HE per tick into an empty buffer still runs without a pause, but the buffer is empty after each tick, so
        // on the completion tick the next item cannot start "with power" and the original rule sets the block unlit for
        // that tick (TileEntityMachineElectricFurnace.java:190-199; NEO keeps the rule).
        reset();
        Level level = level();
        MachineElectricFurnaceBlockEntity tight = furnace(level, new BlockPos(0, 64, 0));
        tight.slots.set(1, new ItemStack(RAW_IRON, 64));
        List<Integer> dark = new ArrayList<>();
        for(int t = 1; t <= 300; t++) {
            tight.power += FURNACE_HE;
            tick(tight);
            if(!lit(level, tight.getBlockPos())) dark.add(t);
        }
        check(tight.slots.get(2).getCount() == 3 && cooldown(tight) == 0 && dark.equals(List.of(100, 200, 300)),
                "50 HE/t with no buffer: 3 items in 300 ticks; unlit only on the completion ticks " + dark);
        check(170 / FURNACE_HE == 3 && 850 / FURNACE_HE == 17, "arithmetic: 170 HE/t feeds 3 furnaces at 50 HE/t, the heating oven chain's 850 HE/t feeds 17");
        section("9. power budget");
    }

    public static void main(String[] args) {
        run("1. heating oven anvil", Goal10CRegression::anvil);
        run("2. heating oven removal", Goal10CRegression::ovenRemoval);
        run("3. heating oven heat", Goal10CRegression::ovenHeat);
        run("4. electric furnace processing", Goal10CRegression::processing);
        run("5. upgrades", Goal10CRegression::upgrades);
        run("6. slots and power", Goal10CRegression::slots);
        run("7. LIT and persistence", Goal10CRegression::litAndPersistence);
        run("8. experience and menu", Goal10CRegression::experience);
        run("9. power budget", Goal10CRegression::budget);
        System.out.println("Goal 10C machine world: " + checks + " checks passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
