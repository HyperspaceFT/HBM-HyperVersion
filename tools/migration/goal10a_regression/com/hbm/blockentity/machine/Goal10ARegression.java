package com.hbm.blockentity.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.handler.jei.CrucibleAlloyingRecipeHandler;
import com.hbm.handler.jei.CrucibleCastingRecipeHandler;
import com.hbm.handler.jei.CrucibleSmeltingRecipeHandler;
import com.hbm.handler.jei.subtypes.ScrapsSubtypeInterpreter;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.menus.MachineCrucibleMenu;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.inventory.recipes.CrucibleRecipe;
import com.hbm.inventory.recipes.CrucibleRecipes;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.util.TagsUtil;
import mezz.jei.api.gui.builder.IDrawableBuilder;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.builder.IRecipeSlotBuilder;
import mezz.jei.api.gui.builder.IRecipeSlotRichTooltipCallback;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.ingredients.subtypes.UidContext;
import mezz.jei.api.recipe.RecipeIngredientRole;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.neoforged.neoforge.network.handling.IPayloadContext;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Goal 10A machine world: the live crucible, mold, melt table, scraps, alloy recipe, control path and JEI data.
 * Expected numbers are written out from the original at 608fec4, not read from the NEO classes under test:
 * TileEntityCrucible.java:56-69 (two stacks of MaterialShapes.BLOCK.q(16) = 10,368 quanta, processTime 20,000,
 * diffusion 0.25, maxHeat 100,000), :344-406 (heat pull, smelting from maxHeat / 2 with delta (heat - 50,000) * 0.05,
 * routing), :408-434 (alloying every frequency ticks), :455-503 (insertion and the recipeZCapacity ratio),
 * :164-224 and CrucibleUtil.java:51-80 (spouts at 1.875, y + 0.25, six blocks down, 24 quanta, safe mode),
 * CrucibleRecipes.java:91-93 (crucible.hss), Mats.java:104-141 (IDs, names, colours), MaterialShapes (ingot 72,
 * block 648, nugget 8, cast plate 216), OreDictManager.java:398 (fragment_cobalt is nuggetCobalt).
 */
public class Goal10ARegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();

    private static final int CAPACITY = 10_368;
    private static final int MAX_HEAT = 100_000;
    private static final int PROCESS = 20_000;
    private static final int INGOT = 72, BLOCK = 648, NUGGET = 8, PLATE = 216, POUR = 24, COOLOFF = 200;
    private static Path source;

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void run(String name, Runnable body) {
        sectionChecks = 0;
        try {
            body.run();
            System.out.println(name + ": " + sectionChecks + " checks passed");
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            // The failed check is not counted as passed.
            checks--;
        } catch(RuntimeException e) {
            System.out.println("Exception in " + name + " after " + sectionChecks + " passed checks: " + e);
            e.printStackTrace(System.out);
            failures.add(name + ": " + e);
        }
    }

    // ---- Fixture helpers -------------------------------------------------------------------------------------------

    private static Level level() {
        Level level = new Level();
        level.manualClock = true;
        return level;
    }

    private static MachineCrucibleBlockEntity crucible(Level level, BlockPos pos) {
        MachineCrucibleBlockEntity be = new MachineCrucibleBlockEntity(pos, new BlockState());
        level.put(be);
        return be;
    }

    private static FoundryMoldBlockEntity mold(Level level, BlockPos pos, boolean insert) {
        FoundryMoldBlockEntity be = new FoundryMoldBlockEntity(pos, new BlockState());
        level.put(be);
        if(insert) check(be.insertMold(new ItemStack(NtmItems.MOLD_PLATE_CAST.get())), "plate mold inserted");
        return be;
    }

    private static HeaterFireboxBlockEntity firebox(Level level, BlockPos pos) {
        HeaterFireboxBlockEntity be = new HeaterFireboxBlockEntity(pos, new BlockState());
        level.put(be);
        return be;
    }

    private static void face(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
    }

    /** The spout column of the crucible at {@code pos} towards {@code dir}: centre + dir * 1.875 (original TE:166, 196). */
    private static String spout(BlockPos pos, Direction dir) {
        return Level.column(pos.getX() + 0.5D + dir.getStepX() * 1.875D, pos.getZ() + 0.5D + dir.getStepZ() * 1.875D);
    }

    private static void aim(Level level, BlockPos crucible, Direction dir, BlockPos target, Direction side) {
        level.columnHits.put(spout(crucible, dir), new BlockHitResult(HitResult.Type.BLOCK, target, side));
    }

    private static void tick(Level level, ITickable... machines) {
        for(ITickable machine : machines) machine.updateEntity();
        level.time++;
    }

    private static MaterialStack ms(NTMMaterial material, int amount) {
        return new MaterialStack(material, amount);
    }

    private static void set(List<MaterialStack> stack, MaterialStack... entries) {
        stack.clear();
        for(MaterialStack entry : entries) stack.add(entry.copy());
    }

    /** "Steel=40,DuraSteel=72" in list order, with the material's first name. */
    private static String s(List<MaterialStack> stack) {
        return stack.stream().map(m -> m.material.names[0] + "=" + m.amount).collect(Collectors.joining(","));
    }

    private static int total(List<MaterialStack> stack) {
        int sum = 0;
        for(MaterialStack m : stack) sum += m.amount;
        return sum;
    }

    private static CompoundTag control(Object index, Object selection) {
        CompoundTag tag = new CompoundTag();
        if(index instanceof Integer i) tag.putInt("index", i);
        if(selection instanceof String text) tag.putString("selection", text);
        if(selection instanceof Integer i) tag.putInt("selection", i);
        return tag;
    }

    private static void select(MachineCrucibleBlockEntity c, String recipe) {
        c.receiveControl(control(0, recipe));
        check(recipe.equals(c.recipe), "recipe " + recipe + " selected");
    }

    private static ItemStack item(Item item) {
        return new ItemStack(item);
    }

    private static ItemStack item(ItemLike item, int count) {
        return new ItemStack(item, count);
    }

    private static ItemStack scrap(int material, int amount) {
        ItemStack stack = new ItemStack(NtmItems.SCRAPS.get());
        CompoundTag tag = new CompoundTag();
        tag.putInt("material", material);
        tag.putInt("amount", amount);
        TagsUtil.putCustomData(stack, tag);
        return stack;
    }

    /** Melts one item from slot 0 at full heat in one tick (progress 19,999 + 2,500), without a mold under either spout. */
    private static void meltOne(MachineCrucibleBlockEntity c, ItemStack stack) {
        c.slots.set(0, stack);
        c.heat = MAX_HEAT;
        c.progress = PROCESS - 1;
        tick(c.getLevel(), c);
        check(c.slots.get(0).isEmpty() && c.progress == 0, "one item melted on the completing tick");
    }

    private static Player player(Level level) {
        Player player = new Player();
        player.world = level;
        player.level = level;
        Inventory inventory = player.getInventory();
        inventory.player = player;
        return player;
    }

    private static Player viewer(MachineCrucibleBlockEntity c) {
        Player player = player(c.getLevel());
        player.containerMenu = new MachineCrucibleMenu(0, player.getInventory(), c);
        return player;
    }

    private static void save(Object be, CompoundTag tag) {
        invoke(be, "saveAdditional", tag);
    }

    private static void load(Object be, CompoundTag tag) {
        invoke(be, "loadAdditional", tag);
    }

    private static void invoke(Object be, String name, CompoundTag tag) {
        try {
            Method method = be.getClass().getDeclaredMethod(name, CompoundTag.class, net.minecraft.core.HolderLookup.Provider.class);
            method.setAccessible(true);
            method.invoke(be, tag, null);
        } catch(ReflectiveOperationException e) {
            throw new AssertionError(name + " failed", e);
        }
    }

    private static boolean plate(ItemStack stack, int meta) {
        return stack.is(NtmItems.CAST_PLATE.get()) && stack.getCount() == 1 && stack.component().equals(Integer.toString(meta));
    }

    private static boolean liquid(ItemStack stack, NTMMaterial material, int amount) {
        MaterialStack contents = CopperScrapsItem.getMats(stack);
        return contents != null && contents.material == material && contents.amount == amount && CopperScrapsItem.isLiquid(stack);
    }

    // ---- 1. Materials ------------------------------------------------------------------------------------------------

    private static void materials() {
        NTMMaterial[] expected = {Mats.MAT_COPPER, Mats.MAT_TUNGSTEN, Mats.MAT_COBALT, Mats.MAT_STEEL, Mats.MAT_DURA};
        check(Mats.orderedList.equals(List.of(expected)), "orderedList is Copper, Tungsten, Cobalt, Steel, DuraSteel: " + Mats.orderedList.size());
        int[] ids = {2900, 7400, 2700, 30, 33};
        String[] names = {"Copper", "Tungsten", "Cobalt", "Steel", "DuraSteel"};
        String[] keys = {"hbmmat.copper", "hbmmat.tungsten", "hbmmat.cobalt", "hbmmat.steel", "hbmmat.durasteel"};
        int[][] colours = {{0xFDCA88, 0x601E0D, 0xC18336}, {0x868686, 0x000000, 0x977474}, {0xC2D1EE, 0x353554, 0x8F72AE},
                {0xAFAFAF, 0x0F0F0F, 0x4A4A4A}, {0x82A59C, 0x06281E, 0x42665C}};
        for(int i = 0; i < expected.length; i++) {
            NTMMaterial m = expected[i];
            check(m.id == ids[i] && m.names.length == 1 && m.names[0].equals(names[i]), names[i] + " id " + ids[i]);
            check(m.solidColorLight == colours[i][0] && m.solidColorDark == colours[i][1] && m.moltenColor == colours[i][2],
                    names[i] + " light/dark/molten colours");
            check(m.smeltable == NTMMaterial.SmeltingBehavior.SMELTABLE, names[i] + " is SMELTABLE");
            check(Mats.matById.get(ids[i]) == m && Mats.matByName.get(names[i]) == m, names[i] + " found by ID and by name");
            check(m.getDescriptionId().equals(keys[i]) && m.getName().key.equals(keys[i]), names[i] + " language key " + keys[i]);
        }
        check(Mats.matById.size() == 5 && Mats.matByName.size() == 5, "exactly five crucible materials registered");
        check(Mats.matById.get(0) == null && Mats.matById.get(9999) == null && Mats.matByName.get("Bismuth") == null,
                "unknown IDs and names resolve to nothing");
    }

    // ---- 2. Melt table -----------------------------------------------------------------------------------------------

    private static void meltTable() {
        Object[][] expected = {
                {Items.COPPER_INGOT, Mats.MAT_COPPER, INGOT}, {NtmItems.INGOT_COPPER.get(), Mats.MAT_COPPER, INGOT},
                {NtmBlocks.BLOCK_COPPER.get(), Mats.MAT_COPPER, BLOCK}, {Items.COPPER_BLOCK, Mats.MAT_COPPER, BLOCK},
                {NtmItems.INGOT_STEEL.get(), Mats.MAT_STEEL, INGOT}, {NtmBlocks.BLOCK_STEEL.get(), Mats.MAT_STEEL, BLOCK},
                {NtmItems.INGOT_TUNGSTEN.get(), Mats.MAT_TUNGSTEN, INGOT}, {NtmBlocks.BLOCK_TUNGSTEN.get(), Mats.MAT_TUNGSTEN, BLOCK},
                {NtmItems.INGOT_COBALT.get(), Mats.MAT_COBALT, INGOT}, {NtmItems.NUGGET_COBALT.get(), Mats.MAT_COBALT, NUGGET},
                {NtmItems.FRAGMENT_COBALT.get(), Mats.MAT_COBALT, NUGGET},
                {NtmItems.INGOT_DURA_STEEL.get(), Mats.MAT_DURA, INGOT}, {NtmBlocks.BLOCK_DURA_STEEL.get(), Mats.MAT_DURA, BLOCK},
        };
        List<CopperCastingRecipes.MeltEntry> entries = CopperCastingRecipes.getMeltEntries();
        check(entries.size() == 13, "13 melt entries, found " + entries.size());
        for(int i = 0; i < expected.length; i++) {
            Item item = (Item) expected[i][0];
            CopperCastingRecipes.MeltEntry entry = entries.get(i);
            check(entry.item() == item && entry.material() == expected[i][1] && entry.amount() == (int) expected[i][2],
                    "melt entry " + i + " is " + item.id + " -> " + ((NTMMaterial) expected[i][1]).names[0] + " " + expected[i][2]);
            MaterialStack first = CopperCastingRecipes.getMaterial(item(item));
            MaterialStack second = CopperCastingRecipes.getMaterial(item(item));
            check(first != null && first.material == expected[i][1] && first.amount == (int) expected[i][2],
                    item.id + " melts into " + expected[i][2] + " quanta");
            check(first != second, item.id + " returns a fresh stack on each call");
            first.amount = 1;
            check(CopperCastingRecipes.getMaterial(item(item)).amount == (int) expected[i][2], item.id + " table not changed through a returned stack");
        }
        try {
            entries.add(entries.get(0));
            check(false, "melt entry list is unmodifiable");
        } catch(UnsupportedOperationException expectedFailure) {
            check(true, "melt entry list is unmodifiable");
        }
        for(Item item : new Item[] {NtmItems.PLATE_STEEL.get(), NtmItems.POWDER_COBALT.get(), NtmItems.POWDER_COBALT_TINY.get(),
                NtmItems.POWDER_TUNGSTEN.get(), NtmItems.WIRE_COPPER.get(), NtmBlocks.ORE_COBALT.get(), NtmBlocks.ORE_TUNGSTEN.get(),
                NtmItems.CAST_PLATE.get(), NtmItems.MOLD_PLATE_CAST.get(), Items.STICK, Items.COAL}) {
            check(CopperCastingRecipes.getMaterial(item(item)) == null, item.id + " does not melt");
        }
        check(CopperCastingRecipes.getMaterial(NtmItems.castPlate(com.hbm.items.CastPlateItem.Type.STEEL, 1)) == null, "steel cast plate does not melt");
        check(CopperCastingRecipes.getMaterial(ItemStack.EMPTY) == null, "empty stack does not melt");

        // Scraps melt as their stored material; the Goal 5A copper scrap layout is unchanged.
        MaterialStack legacy = CopperCastingRecipes.getMaterial(scrap(2900, 37));
        check(legacy != null && legacy.material == Mats.MAT_COPPER && legacy.amount == 37, "Goal 5A copper scrap {material:2900, amount:37} melts");
        for(NTMMaterial m : Mats.orderedList) {
            MaterialStack melted = CopperCastingRecipes.getMaterial(CopperScrapsItem.create(ms(m, 100)));
            check(melted != null && melted.material == m && melted.amount == 100, m.names[0] + " scrap melts as 100 quanta");
        }
        check(CopperCastingRecipes.getMaterial(scrap(30, 1)).amount == 1 && CopperCastingRecipes.getMaterial(scrap(30, CAPACITY)).amount == CAPACITY,
                "scrap amounts 1 and 10,368 are valid");
        check(CopperCastingRecipes.getMaterial(scrap(30, 0)) == null && CopperCastingRecipes.getMaterial(scrap(30, -1)) == null
                && CopperCastingRecipes.getMaterial(scrap(30, CAPACITY + 1)) == null, "scrap amounts 0, -1 and 10,369 are rejected");
        check(CopperCastingRecipes.getMaterial(scrap(9999, 72)) == null && CopperCastingRecipes.getMaterial(scrap(0, 72)) == null,
                "scraps of an unregistered material are rejected");
        check(CopperCastingRecipes.getMaterial(new ItemStack(NtmItems.SCRAPS.get())) == null, "scraps without data do not melt");
    }

    // ---- 3. Heat, smelting and routing -------------------------------------------------------------------------------

    private static void routing() {
        Level level = level();
        level.time = 1;
        MachineCrucibleBlockEntity c = crucible(level, new BlockPos(0, 1, 0));
        HeaterFireboxBlockEntity fire = firebox(level, new BlockPos(0, 0, 0));
        fire.heatEnergy = 100_000;
        tick(level, c);
        check(c.heat == 25_000 && fire.heatEnergy == 75_000, "heat pull ceil(min(diff, room) * 0.25)");
        c.heat = 99_000; fire.heatEnergy = 150_000;
        tick(level, c);
        check(c.heat == 99_250 && fire.heatEnergy == 149_750, "difference capped to the crucible's room before diffusion");
        level.entities.remove(fire.getBlockPos());
        c.heat = 5_000;
        tick(level, c);
        check(c.heat == 4_995, "without a source heat decays by heat / 1000");
        c.heat = 500;
        tick(level, c);
        check(c.heat == 499, "decay is at least 1");

        // A source at the crucible's own heat neither gives heat nor lets it decay (original TE:353-355).
        level.put(fire);
        c.slots.set(0, item(NtmItems.INGOT_STEEL.get()));
        c.heat = 49_999; fire.heatEnergy = 49_999; c.progress = 700;
        tick(level, c);
        check(c.progress == 0 && c.slots.get(0).getCount() == 1, "below 50,000 heat progress resets");
        c.heat = 50_020; fire.heatEnergy = 50_020;
        tick(level, c);
        check(c.progress == 1 && c.heat == 50_019, "delta (int) ((heat - 50,000) * 0.05) is added to progress and taken from heat");
        c.slots.set(0, ItemStack.EMPTY);
        c.heat = MAX_HEAT; c.progress = 700;
        tick(level, c);
        check(c.progress == 0, "nothing smeltable resets progress");
        c.slots.set(3, item(NtmItems.INGOT_TUNGSTEN.get()));
        c.slots.set(5, item(NtmItems.INGOT_STEEL.get()));
        c.heat = MAX_HEAT; c.progress = PROCESS - 1;
        tick(level, c);
        check(c.slots.get(3).isEmpty() && c.slots.get(5).getCount() == 1 && c.progress == 0 && s(c.wasteStack).equals("Tungsten=72"),
                "progress 20,000 melts one item from the first smeltable slot and resets: " + s(c.wasteStack));
        c.slots.set(5, ItemStack.EMPTY);

        // No recipe: everything goes to the waste stack.
        set(c.wasteStack);
        for(Item item : new Item[] {NtmItems.INGOT_STEEL.get(), NtmItems.INGOT_TUNGSTEN.get(), NtmItems.FRAGMENT_COBALT.get(),
                NtmItems.INGOT_DURA_STEEL.get(), Items.COPPER_INGOT}) meltOne(c, item(item));
        check(c.recipeStack.isEmpty() && s(c.wasteStack).equals("Steel=72,Tungsten=72,Cobalt=8,DuraSteel=72,Copper=72"),
                "without a recipe every material goes to the waste stack: " + s(c.wasteStack));

        // crucible.hss: its inputs and its output go to the recipe stack, copper to the waste stack.
        MachineCrucibleBlockEntity h = crucible(level, new BlockPos(5, 1, 0));
        select(h, "crucible.hss");
        for(Item item : new Item[] {NtmItems.INGOT_STEEL.get(), NtmItems.INGOT_TUNGSTEN.get(), NtmItems.FRAGMENT_COBALT.get(),
                NtmItems.INGOT_DURA_STEEL.get()}) meltOne(h, item(item));
        check(s(h.recipeStack).equals("Steel=72,Tungsten=72,Cobalt=8,DuraSteel=72") && h.wasteStack.isEmpty(),
                "with crucible.hss steel, tungsten, cobalt and DuraSteel go to the recipe stack: " + s(h.recipeStack));
        // Original isItemSmeltable refuses a material the recipe neither consumes nor produces, and getFirstSmeltableSlot
        // uses that test, so copper already sitting in a slot when crucible.hss is selected stays unmelted.
        h.slots.set(0, item(Items.COPPER_INGOT));
        h.heat = MAX_HEAT; h.progress = PROCESS - 1;
        tick(level, h);
        check(h.slots.get(0).getCount() == 1 && h.progress == 0 && h.wasteStack.isEmpty(),
                "a copper item in a slot is not smelted while crucible.hss is selected");
    }

    // ---- 4. Insertion ------------------------------------------------------------------------------------------------

    private static void insertion() {
        Level level = level();
        level.time = 1;
        MachineCrucibleBlockEntity c = crucible(level, new BlockPos(0, 1, 0));
        ItemStack steel = item(NtmItems.INGOT_STEEL.get()), tungsten = item(NtmItems.INGOT_TUNGSTEN.get()),
                cobalt = item(NtmItems.INGOT_COBALT.get()), fragment = item(NtmItems.FRAGMENT_COBALT.get()),
                dura = item(NtmItems.INGOT_DURA_STEEL.get()), copper = item(Items.COPPER_INGOT);

        // No recipe: only the waste stack's capacity limits.
        set(c.wasteStack, ms(Mats.MAT_COPPER, CAPACITY - INGOT));
        check(c.isItemSmeltable(copper) && c.isItemSmeltable(steel), "no recipe: waste 10,296 + 72 fits");
        set(c.wasteStack, ms(Mats.MAT_COPPER, CAPACITY - INGOT + 1));
        check(!c.isItemSmeltable(copper) && !c.isItemSmeltable(steel) && c.isItemSmeltable(fragment), "no recipe: waste 10,297 + 72 is refused, + 8 fits");
        check(!c.isItemSmeltable(item(Items.STICK)) && !c.isItemSmeltable(ItemStack.EMPTY), "items outside the melt table are refused");

        select(c, "crucible.hss");
        set(c.wasteStack);
        check(!c.isItemSmeltable(copper) && !c.canPlaceItem(0, copper), "crucible.hss refuses copper (neither consumed nor produced)");
        check(!c.isItemSmeltable(CopperScrapsItem.create(ms(Mats.MAT_COPPER, 10))), "crucible.hss refuses copper scraps");
        check(c.isItemSmeltable(steel) && c.isItemSmeltable(tungsten) && c.isItemSmeltable(cobalt) && c.isItemSmeltable(fragment)
                && c.isItemSmeltable(dura), "crucible.hss accepts its inputs and output into an empty recipe stack");

        // Maxima: required * 10,368 / 72 -> steel 5,760, tungsten 3,456, cobalt 1,152.
        Object[][] maxima = {{Mats.MAT_STEEL, 5_760, steel, INGOT}, {Mats.MAT_TUNGSTEN, 3_456, tungsten, INGOT},
                {Mats.MAT_COBALT, 1_152, cobalt, INGOT}, {Mats.MAT_COBALT, 1_152, fragment, NUGGET}};
        for(Object[] max : maxima) {
            NTMMaterial m = (NTMMaterial) max[0];
            int limit = (int) max[1], amount = (int) max[3];
            ItemStack stack = (ItemStack) max[2];
            set(c.recipeStack, ms(m, limit - amount));
            check(c.isItemSmeltable(stack) && c.canPlaceItem(0, stack), m.names[0] + " stored " + (limit - amount) + " + " + amount + " reaches the maximum " + limit);
            set(c.recipeStack, ms(m, limit - amount + 1));
            check(!c.isItemSmeltable(stack) && !c.canPlaceItem(0, stack), m.names[0] + " stored " + (limit - amount + 1) + " + " + amount + " exceeds " + limit);
        }
        // Other inputs do not count against one input's maximum.
        set(c.recipeStack, ms(Mats.MAT_STEEL, 5_760), ms(Mats.MAT_COBALT, 1_000));
        check(c.isItemSmeltable(tungsten) && !c.isItemSmeltable(steel), "each input's maximum is checked against its own amount");

        // The output may be put back; only the recipe stack's capacity limits it.
        set(c.recipeStack, ms(Mats.MAT_DURA, CAPACITY - INGOT));
        check(c.isItemSmeltable(dura), "DuraSteel can be put back up to 10,368 in the recipe stack");
        set(c.recipeStack, ms(Mats.MAT_DURA, CAPACITY - INGOT + 1));
        check(!c.isItemSmeltable(dura), "DuraSteel beyond the recipe stack's 10,368 is refused");
        // Both stacks are limited separately.
        set(c.recipeStack, ms(Mats.MAT_STEEL, 5_000), ms(Mats.MAT_DURA, 5_300));
        check(!c.isItemSmeltable(steel), "an input under its maximum is refused when the recipe stack would exceed 10,368");
        set(c.recipeStack);
        set(c.wasteStack, ms(Mats.MAT_COPPER, CAPACITY));
        check(c.isItemSmeltable(steel), "a full waste stack does not block a recipe input");
        set(c.wasteStack);

        // Slots, shift-click and intake use the same rule.
        c.slots.set(0, item(NtmItems.INGOT_STEEL.get()));
        check(!c.canPlaceItem(0, steel) && c.canPlaceItem(1, steel), "an occupied slot refuses, an empty slot accepts");
        c.slots.set(0, ItemStack.EMPTY);
        Player player = viewer(c);
        MachineCrucibleMenu menu = (MachineCrucibleMenu) player.containerMenu;
        player.getInventory().setItem(0, item(Items.COPPER_INGOT, 3));
        check(menu.quickMoveStack(player, menu.slots.size() - 9).isEmpty() && player.getInventory().getItem(0).getCount() == 3,
                "shift-click refuses copper while crucible.hss is selected");
        player.getInventory().setItem(0, item(NtmItems.INGOT_STEEL.get(), 2));
        menu.quickMoveStack(player, menu.slots.size() - 9);
        check(player.getInventory().getItem(0).isEmpty() && c.slots.get(0).is(NtmItems.INGOT_STEEL.get()) && c.slots.get(1).is(NtmItems.INGOT_STEEL.get()),
                "shift-click moves steel into single-item slots");
        c.slots.set(0, ItemStack.EMPTY); c.slots.set(1, ItemStack.EMPTY);
        ItemEntity copperDrop = new ItemEntity(item(Items.COPPER_INGOT, 2));
        ItemEntity steelDrop = new ItemEntity(item(NtmItems.INGOT_STEEL.get(), 1));
        level.dropped.add(copperDrop);
        level.dropped.add(steelDrop);
        level.time = 5;
        c.heat = 0;
        tick(level, c);
        check(copperDrop.isAlive() && copperDrop.getItem().getCount() == 2 && !steelDrop.isAlive() && c.slots.get(0).is(NtmItems.INGOT_STEEL.get()),
                "intake collects steel and leaves copper while crucible.hss is selected");
    }

    // ---- 5. Alloying -------------------------------------------------------------------------------------------------

    private static void alloying() {
        CrucibleRecipe hss = CrucibleRecipes.INSTANCE.recipeNameMap.get("crucible.hss");
        check(hss != null && hss.frequency == 9, "crucible.hss alloys every 9 ticks");
        Level level = level();
        MachineCrucibleBlockEntity c = crucible(level, new BlockPos(0, 1, 0));
        select(c, "crucible.hss");

        set(c.recipeStack, ms(Mats.MAT_STEEL, 40), ms(Mats.MAT_TUNGSTEN, 24), ms(Mats.MAT_COBALT, 8));
        for(long t = 10; t < 18; t++) {
            level.time = t;
            tick(level, c);
            check(s(c.recipeStack).equals("Steel=40,Tungsten=24,Cobalt=8"), "no alloying at game time " + t);
        }
        level.time = 18;
        tick(level, c);
        check(s(c.recipeStack).equals("DuraSteel=72"), "game time 18: 40 + 24 + 8 become 72 DuraSteel, empty entries removed: " + s(c.recipeStack));

        set(c.recipeStack, ms(Mats.MAT_STEEL, 39), ms(Mats.MAT_TUNGSTEN, 24), ms(Mats.MAT_COBALT, 8));
        level.time = 27;
        tick(level, c);
        check(s(c.recipeStack).equals("Steel=39,Tungsten=24,Cobalt=8"), "one steel short: no alloying");
        set(c.recipeStack, ms(Mats.MAT_STEEL, 40), ms(Mats.MAT_TUNGSTEN, 23), ms(Mats.MAT_COBALT, 8));
        level.time = 36;
        tick(level, c);
        check(s(c.recipeStack).equals("Steel=40,Tungsten=23,Cobalt=8"), "one tungsten short: no alloying");
        set(c.recipeStack, ms(Mats.MAT_STEEL, 40), ms(Mats.MAT_TUNGSTEN, 24), ms(Mats.MAT_COBALT, 7));
        level.time = 45;
        tick(level, c);
        check(s(c.recipeStack).equals("Steel=40,Tungsten=24,Cobalt=7"), "one cobalt short: no alloying");

        set(c.recipeStack, ms(Mats.MAT_DURA, 10), ms(Mats.MAT_STEEL, 100), ms(Mats.MAT_TUNGSTEN, 50), ms(Mats.MAT_COBALT, 20));
        level.time = 54;
        tick(level, c);
        check(s(c.recipeStack).equals("DuraSteel=82,Steel=60,Tungsten=26,Cobalt=12"), "one step subtracts 40/24/8 and adds 72 to the existing output: " + s(c.recipeStack));

        // Frequency over a run: ten steps worth of input, game times 1 .. 89 alloy at 9, 18, ..., 81 only.
        set(c.recipeStack, ms(Mats.MAT_STEEL, 400), ms(Mats.MAT_TUNGSTEN, 240), ms(Mats.MAT_COBALT, 80));
        level.time = 1;
        int steps = 0;
        for(int i = 0; i < 89; i++) {
            int before = MachineCrucibleBlockEntity.getQuantaFromType(c.recipeStack, Mats.MAT_DURA);
            boolean due = level.time % 9 == 0;
            tick(level, c);
            int after = MachineCrucibleBlockEntity.getQuantaFromType(c.recipeStack, Mats.MAT_DURA);
            if(after != before) steps++;
            if(due != (after == before + INGOT)) check(false, "alloy step exactly on game times divisible by 9 (time " + (level.time - 1) + ")");
        }
        check(steps == 9 && s(c.recipeStack).equals("Steel=40,Tungsten=24,Cobalt=8,DuraSteel=648"), "nine steps in 89 ticks: " + s(c.recipeStack));
        tick(level, c);
        check(s(c.recipeStack).equals("DuraSteel=720"), "the tenth step at game time 90: " + s(c.recipeStack));

        // 5 steel + 3 tungsten ingots + 1 cobalt ingot = 648 quanta -> 9 steps -> 648 DuraSteel, melted from items.
        MachineCrucibleBlockEntity m = crucible(level, new BlockPos(10, 1, 0));
        select(m, "crucible.hss");
        int slot = 0;
        for(int i = 0; i < 5; i++) m.slots.set(slot++, item(NtmItems.INGOT_STEEL.get()));
        for(int i = 0; i < 3; i++) m.slots.set(slot++, item(NtmItems.INGOT_TUNGSTEN.get()));
        m.slots.set(slot, item(NtmItems.INGOT_COBALT.get()));
        level.time = 1;
        for(int i = 0; i < 400 && MachineCrucibleBlockEntity.getQuantaFromType(m.recipeStack, Mats.MAT_DURA) < BLOCK; i++) {
            m.heat = MAX_HEAT;
            tick(level, m);
            check(total(m.recipeStack) + 72 * (int) m.slots.stream().filter(st -> !st.isEmpty()).count() == BLOCK && m.wasteStack.isEmpty(),
                    "quanta conserved while melting and alloying (tick " + i + ")");
        }
        check(s(m.recipeStack).equals("DuraSteel=648") && m.slots.stream().allMatch(ItemStack::isEmpty),
                "5 steel + 3 tungsten + 1 cobalt ingot alloy into 648 DuraSteel: " + s(m.recipeStack));
    }

    // ---- 6. Pouring --------------------------------------------------------------------------------------------------

    private static final class Rig {
        final Level level = level();
        final BlockPos pos = new BlockPos(100, 1, 0);
        final MachineCrucibleBlockEntity c;
        FoundryMoldBlockEntity front, rear;

        Rig(Direction facing) {
            face(level, pos, facing);
            c = crucible(level, pos);
            front = mold(level, pos.relative(facing, 2).below(), true);
            rear = mold(level, pos.relative(facing.getOpposite(), 2).below(), true);
            aim(level, pos, facing, front.getBlockPos(), Direction.UP);
            aim(level, pos, facing.getOpposite(), rear.getBlockPos(), Direction.UP);
            level.time = 1;
        }

        void freshFront() {
            front = mold(level, front.getBlockPos(), true);
        }

        void freshRear() {
            rear = mold(level, rear.getBlockPos(), true);
        }

        void tick() {
            Goal10ARegression.tick(level, c);
        }
    }

    private static void pouring() {
        Rig r = new Rig(Direction.NORTH);
        set(r.c.wasteStack, ms(Mats.MAT_STEEL, 100));
        r.tick();
        check(s(r.c.wasteStack).equals("Steel=76") && r.rear.amount == 24 && r.rear.type == Mats.MAT_STEEL && r.front.amount == 0,
                "no recipe: the waste stack pours 24 quanta from the rear spout");
        ClipContext rearClip = r.level.clips.get(0);
        check(r.level.clips.size() == 1 && Math.abs(rearClip.start.x() - 100.5) < 1e-9 && Math.abs(rearClip.start.z() - 2.375) < 1e-9
                && Math.abs(rearClip.start.y() - 1.25) < 1e-9 && Math.abs(rearClip.end.y() - (1.25 - 6)) < 1e-9
                && Math.abs(rearClip.end.x() - 100.5) < 1e-9 && Math.abs(rearClip.end.z() - 2.375) < 1e-9
                && rearClip.block == ClipContext.Block.COLLIDER && rearClip.fluid == ClipContext.Fluid.ANY,
                "rear ray: centre - FACING * 1.875, y + 0.25, six blocks straight down, colliders and fluids");
        for(int i = 0; i < 3; i++) r.tick();
        check(s(r.c.wasteStack).equals("Steel=4") && r.rear.amount == 96, "24 quanta per tick");
        r.tick();
        check(r.c.wasteStack.isEmpty() && r.rear.amount == 100, "the last 4 quanta pour and the empty entry is removed");

        // Recipe stack without a recipe (leftovers) pours everything from the front spout.
        r.level.clips.clear();
        set(r.c.recipeStack, ms(Mats.MAT_STEEL, 50));
        r.tick();
        ClipContext frontClip = r.level.clips.get(0);
        check(s(r.c.recipeStack).equals("Steel=26") && r.front.amount == 24 && r.front.type == Mats.MAT_STEEL
                && Math.abs(frontClip.start.z() - (0.5 - 1.875)) < 1e-9 && Math.abs(frontClip.start.x() - 100.5) < 1e-9,
                "recipe \"null\": the recipe stack pours from the front spout (centre + FACING * 1.875)");

        // crucible.hss: only the output leaves the front spout; inputs stay until the recipe is cleared.
        Rig h = new Rig(Direction.NORTH);
        select(h.c, "crucible.hss");
        set(h.c.recipeStack, ms(Mats.MAT_STEEL, 100), ms(Mats.MAT_DURA, 100));
        h.tick();
        check(s(h.c.recipeStack).equals("Steel=100,DuraSteel=76") && h.front.amount == 24 && h.front.type == Mats.MAT_DURA && h.rear.amount == 0,
                "crucible.hss: the front spout pours the output DuraSteel, not the steel before it: " + s(h.c.recipeStack));
        for(int i = 0; i < 10; i++) h.tick();
        check(s(h.c.recipeStack).equals("Steel=100") && h.front.amount == 100, "all DuraSteel poured, steel kept: " + s(h.c.recipeStack));
        h.freshFront();
        for(int i = 0; i < 3; i++) h.tick();
        check(s(h.c.recipeStack).equals("Steel=100") && h.front.amount == 0, "an empty front mold receives no input while crucible.hss is selected");
        select(h.c, "null");
        h.tick();
        check(s(h.c.recipeStack).equals("Steel=76") && h.front.amount == 24 && h.front.type == Mats.MAT_STEEL,
                "after the recipe is cleared the leftover input drains from the front");

        // Both spouts in the same tick.
        Rig b = new Rig(Direction.NORTH);
        select(b.c, "crucible.hss");
        set(b.c.wasteStack, ms(Mats.MAT_COPPER, 30));
        set(b.c.recipeStack, ms(Mats.MAT_DURA, 30));
        b.tick();
        check(b.rear.amount == 24 && b.rear.type == Mats.MAT_COPPER && b.front.amount == 24 && b.front.type == Mats.MAT_DURA
                && s(b.c.wasteStack).equals("Copper=6") && s(b.c.recipeStack).equals("DuraSteel=6"), "rear and front pour in the same tick");

        // List order and mold rules.
        Rig o = new Rig(Direction.NORTH);
        set(o.c.wasteStack, ms(Mats.MAT_TUNGSTEN, 24), ms(Mats.MAT_STEEL, 100));
        o.tick();
        check(o.rear.type == Mats.MAT_TUNGSTEN && o.rear.amount == 24 && s(o.c.wasteStack).equals("Steel=100"),
                "the first material in list order is poured; its emptied entry is removed");
        o.tick();
        check(s(o.c.wasteStack).equals("Steel=100") && o.rear.amount == 24, "a mold holding tungsten refuses steel; steel stays");
        o.freshRear();
        set(o.c.wasteStack, ms(Mats.MAT_COBALT, 50), ms(Mats.MAT_STEEL, 100));
        o.tick();
        check(s(o.c.wasteStack).equals("Cobalt=50,Steel=76") && o.rear.type == Mats.MAT_STEEL,
                "cobalt (no cast plate) is skipped and the next material the mold accepts pours");
        o.freshRear();
        set(o.c.wasteStack, ms(Mats.MAT_COBALT, 50));
        for(int i = 0; i < 5; i++) o.tick();
        check(s(o.c.wasteStack).equals("Cobalt=50") && o.rear.amount == 0, "cobalt the mold rejects stays in the crucible");

        // No target, wrong face, no mold insert, a non-mold block entity: nothing spills.
        Rig n = new Rig(Direction.NORTH);
        set(n.c.wasteStack, ms(Mats.MAT_STEEL, 50));
        n.level.columnHits.clear();
        n.tick();
        check(s(n.c.wasteStack).equals("Steel=50"), "no block below the spout: nothing pours or spills");
        aim(n.level, n.pos, Direction.SOUTH, n.rear.getBlockPos(), Direction.NORTH);
        n.tick();
        check(s(n.c.wasteStack).equals("Steel=50") && n.rear.amount == 0, "a side face is not a pour target");
        HeaterFireboxBlockEntity other = firebox(n.level, new BlockPos(100, 0, 5));
        aim(n.level, n.pos, Direction.SOUTH, other.getBlockPos(), Direction.UP);
        n.tick();
        check(s(n.c.wasteStack).equals("Steel=50"), "a block entity that is not a mold receives nothing");
        FoundryMoldBlockEntity bare = mold(n.level, new BlockPos(100, 0, 6), false);
        aim(n.level, n.pos, Direction.SOUTH, bare.getBlockPos(), Direction.UP);
        n.tick();
        check(s(n.c.wasteStack).equals("Steel=50") && bare.amount == 0, "a mold block without a plate mold receives nothing");

        // Other facings: the rear is always FACING.getOpposite(), the front FACING.
        for(Direction facing : new Direction[] {Direction.EAST, Direction.SOUTH, Direction.WEST}) {
            Rig f = new Rig(facing);
            select(f.c, "crucible.hss");
            set(f.c.wasteStack, ms(Mats.MAT_COPPER, 10));
            set(f.c.recipeStack, ms(Mats.MAT_DURA, 10));
            f.tick();
            check(f.rear.type == Mats.MAT_COPPER && f.rear.amount == 10 && f.front.type == Mats.MAT_DURA && f.front.amount == 10,
                    "facing " + facing + ": waste to the rear, output to the front");
        }
    }

    // ---- 7. Mold -----------------------------------------------------------------------------------------------------

    private static void moldRules() {
        Level level = level();
        Object[][] castable = {{Mats.MAT_COPPER, 5}, {Mats.MAT_STEEL, 11}, {Mats.MAT_TUNGSTEN, 6}, {Mats.MAT_DURA, 12}};
        int x = 0;
        for(Object[] entry : castable) {
            NTMMaterial m = (NTMMaterial) entry[0];
            FoundryMoldBlockEntity mold = mold(level, new BlockPos(x++, 0, 0), true);
            check(mold.getCapacity() == PLATE, "small cast-plate mold holds 216 quanta");
            MaterialStack offered = ms(m, 1_000);
            check(mold.pour(offered) == PLATE && offered.amount == 1_000 && mold.amount == PLATE && mold.type == m,
                    m.names[0] + ": the mold takes 216 of 1,000 without changing the offered stack");
            check(mold.pour(ms(m, 1)) == 0, m.names[0] + ": a full mold takes nothing");
            for(int i = 0; i < COOLOFF - 1; i++) tick(level, mold);
            check(mold.slots.get(1).isEmpty() && mold.cooloff == 1, m.names[0] + ": no plate before 200 ticks");
            tick(level, mold);
            check(plate(mold.slots.get(1), (int) entry[1]) && mold.amount == 0 && mold.type == null && mold.cooloff == COOLOFF,
                    m.names[0] + ": the 200th tick casts the plate with META " + entry[1]);
            check(mold.pour(ms(m, 24)) == 0, m.names[0] + ": an uncollected plate blocks pouring");
            check(!mold.removeItem(1, 1).isEmpty() && mold.pour(ms(m, 24)) == 24, m.names[0] + ": taking the plate reopens the mold");
        }
        FoundryMoldBlockEntity mold = mold(level, new BlockPos(10, 0, 0), true);
        check(mold.pour(ms(Mats.MAT_COBALT, 24)) == 0 && mold.amount == 0 && mold.type == null, "cobalt has no cast plate and is rejected");
        NTMMaterial unregistered = new NTMMaterial();
        unregistered.id = 4242;
        unregistered.names = new String[] {"Unregistered"};
        unregistered.smeltable = NTMMaterial.SmeltingBehavior.SMELTABLE;
        check(mold.pour(ms(unregistered, 24)) == 0 && mold.amount == 0, "an unregistered material is rejected");
        check(mold.pour(ms(Mats.MAT_STEEL, 24)) == 24 && mold.pour(ms(Mats.MAT_COPPER, 24)) == 0 && mold.pour(ms(Mats.MAT_DURA, 24)) == 0,
                "a mold holding steel rejects other materials");
        check(mold.pour(ms(Mats.MAT_STEEL, 0)) == 0 && mold.pour(null) == 0, "nothing or zero quanta is not poured");
        for(int i = 0; i < 300; i++) tick(level, mold);
        check(mold.slots.get(1).isEmpty() && mold.cooloff == COOLOFF && mold.amount == 24, "a partly filled mold does not cool");
        FoundryMoldBlockEntity bare = mold(level, new BlockPos(11, 0, 0), false);
        check(bare.getCapacity() == 0 && bare.pour(ms(Mats.MAT_STEEL, 24)) == 0, "without a plate mold nothing is accepted");

        // Saved type IDs resolve through Mats.matById and need a plate type; Goal 5A copper molds still load.
        CompoundTag saved = new CompoundTag();
        save(mold, saved);
        check(saved.getInt("type") == 30 && saved.getInt("amount") == 24, "a steel mold saves type 30");
        FoundryMoldBlockEntity loaded = mold(level, new BlockPos(12, 0, 0), false);
        load(loaded, saved);
        check(loaded.type == Mats.MAT_STEEL && loaded.amount == 24, "a steel mold loads");
        Object[][] legacy = {{2900, 100, Mats.MAT_COPPER, 100}, {7400, 50, Mats.MAT_TUNGSTEN, 50}, {33, 216, Mats.MAT_DURA, 216},
                {2700, 50, null, 0}, {9999, 50, null, 0}, {-1, 50, null, 0}, {30, 500, Mats.MAT_STEEL, PLATE}};
        for(Object[] entry : legacy) {
            CompoundTag tag = new CompoundTag();
            tag.putInt("type", (int) entry[0]);
            tag.putInt("amount", (int) entry[1]);
            tag.putInt("cooloff", 150);
            load(loaded, tag);
            check(loaded.type == entry[2] && loaded.amount == (int) entry[3],
                    "mold NBT type " + entry[0] + " amount " + entry[1] + " loads as " + (entry[2] == null ? "empty" : ((NTMMaterial) entry[2]).names[0]) + " " + entry[3]);
        }
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        mold.serialize(buf);
        FoundryMoldBlockEntity synced = mold(level(), new BlockPos(13, 0, 0), false);
        synced.deserialize(buf);
        check(synced.type == Mats.MAT_STEEL && synced.amount == 24 && synced.hasMold(), "mold sync carries the material");

        ItemStack scraps = mold.takeScraps();
        MaterialStack contents = CopperScrapsItem.getMats(scraps);
        check(contents != null && contents.material == Mats.MAT_STEEL && contents.amount == 24 && !CopperScrapsItem.isLiquid(scraps)
                && mold.amount == 0 && mold.type == null, "mold scraps carry the material and amount");
        check(mold.takeScraps().isEmpty(), "an empty mold gives no scraps");
    }

    // ---- 8. Recipe selection -----------------------------------------------------------------------------------------

    private static void selection() {
        Level level = level();
        MachineCrucibleBlockEntity c = crucible(level, new BlockPos(0, 1, 0));
        check("null".equals(c.recipe) && c.getLoadedRecipe() == null, "a new crucible has recipe \"null\"");
        set(c.recipeStack, ms(Mats.MAT_STEEL, 10));
        set(c.wasteStack, ms(Mats.MAT_COPPER, 5));
        int dirty = c.dirty;
        c.receiveControl(control(0, "crucible.hss"));
        check("crucible.hss".equals(c.recipe) && c.getLoadedRecipe() == CrucibleRecipes.INSTANCE.recipeNameMap.get("crucible.hss")
                && c.dirty > dirty, "crucible.hss is accepted and marks the crucible changed");
        check(s(c.recipeStack).equals("Steel=10") && s(c.wasteStack).equals("Copper=5"), "selecting keeps both stacks");
        for(CompoundTag tag : new CompoundTag[] {control(0, "crucible.bogus"), control(0, ""), control(0, "CRUCIBLE.HSS"), control(1, "null"),
                control(null, "null"), control(0, null), control(0, 7), null}) {
            c.receiveControl(tag);
            check("crucible.hss".equals(c.recipe), "ignored: " + (tag == null ? "null tag" : "index/selection " + tag.getInt("index") + "/" + tag.getString("selection")));
        }
        c.receiveControl(control(0, "null"));
        check("null".equals(c.recipe) && c.getLoadedRecipe() == null && s(c.recipeStack).equals("Steel=10") && s(c.wasteStack).equals("Copper=5"),
                "\"null\" clears the recipe and keeps both stacks");

        // hasPermission as the assembly machine: server level, same level, this crucible's menu open, still valid.
        Player viewer = viewer(c);
        check(c.hasPermission(viewer), "a player with this crucible's menu open has permission");
        Player none = player(level);
        check(!c.hasPermission(none), "no open menu: no permission");
        MachineCrucibleBlockEntity other = crucible(level, new BlockPos(5, 1, 0));
        Player otherMenu = viewer(other);
        check(!c.hasPermission(otherMenu), "another crucible's menu: no permission");
        Player elsewhere = viewer(c);
        elsewhere.world = level();
        check(!c.hasPermission(elsewhere), "a player in another level: no permission");
        Player far = viewer(c);
        far.inReach = false;
        check(!c.hasPermission(far), "out of reach (stillValid false): no permission");
        Level client = level();
        client.isClientSide = true;
        MachineCrucibleBlockEntity clientCrucible = crucible(client, new BlockPos(0, 1, 0));
        check(!clientCrucible.hasPermission(viewer(clientCrucible)), "a client-side crucible grants no permission");

        // The real CompoundTagControl handler: only a permitted player changes the recipe.
        CompoundTagControl.handleServer(new CompoundTagControl(control(0, "crucible.hss"), c.getBlockPos()), ctx(none));
        check("null".equals(c.recipe), "the payload from a player without the menu changes nothing");
        CompoundTagControl.handleServer(new CompoundTagControl(control(0, "crucible.hss"), c.getBlockPos()), ctx(far));
        check("null".equals(c.recipe), "the payload from a player out of reach changes nothing");
        CompoundTagControl.handleServer(new CompoundTagControl(control(0, "crucible.hss"), c.getBlockPos()), ctx(viewer));
        check("crucible.hss".equals(c.recipe), "the payload from the viewer selects crucible.hss");
        CompoundTagControl.handleServer(new CompoundTagControl(control(0, "crucible.bogus"), c.getBlockPos()), ctx(viewer));
        check("crucible.hss".equals(c.recipe), "the viewer cannot select an unregistered name");
        CompoundTagControl.handleServer(new CompoundTagControl(control(0, "null"), c.getBlockPos()), ctx(viewer));
        check("null".equals(c.recipe), "the viewer clears the recipe");
    }

    private static IPayloadContext ctx(Player player) {
        return () -> player;
    }

    // ---- 9. Save -----------------------------------------------------------------------------------------------------

    private static void saving() {
        Level level = level();
        MachineCrucibleBlockEntity c = crucible(level, new BlockPos(0, 1, 0));
        select(c, "crucible.hss");
        set(c.recipeStack, ms(Mats.MAT_STEEL, 40), ms(Mats.MAT_DURA, 72));
        set(c.wasteStack, ms(Mats.MAT_COPPER, 100), ms(Mats.MAT_COBALT, 8));
        c.progress = 1_234;
        c.heat = 77_777;
        CompoundTag tag = new CompoundTag();
        save(c, tag);
        check(tag.getString("recipe").equals("crucible.hss") && java.util.Arrays.equals(tag.getIntArray("rec"), new int[] {30, 40, 33, 72})
                && java.util.Arrays.equals(tag.getIntArray("was"), new int[] {2900, 100, 2700, 8})
                && tag.getInt("progress") == 1_234 && tag.getInt("heat") == 77_777, "recipe, rec, was, progress and heat are saved");
        check(!tag.contains("copper"), "'copper' is no longer written");
        MachineCrucibleBlockEntity loaded = crucible(level, new BlockPos(5, 1, 0));
        set(loaded.wasteStack, ms(Mats.MAT_TUNGSTEN, 1));
        load(loaded, tag);
        check(loaded.recipe.equals("crucible.hss") && s(loaded.recipeStack).equals("Steel=40,DuraSteel=72")
                && s(loaded.wasteStack).equals("Copper=100,Cobalt=8") && loaded.progress == 1_234 && loaded.heat == 77_777,
                "a saved crucible loads identically and replaces what was there");

        // Goal 5A saves: 'copper' without 'was' becomes waste-stack copper, clamped to 10,368.
        Object[][] legacy = {{300, "Copper=300"}, {99_999, "Copper=10368"}, {CAPACITY, "Copper=10368"}, {0, ""}, {-5, ""}};
        for(Object[] entry : legacy) {
            CompoundTag old = new CompoundTag();
            old.putInt("heat", 60_000);
            old.putInt("progress", 500);
            old.putInt("copper", (int) entry[0]);
            load(loaded, old);
            check(s(loaded.wasteStack).equals(entry[1]) && loaded.recipeStack.isEmpty() && "null".equals(loaded.recipe)
                    && loaded.heat == 60_000 && loaded.progress == 500, "Goal 5A copper " + entry[0] + " loads as waste " + entry[1]);
        }
        CompoundTag both = new CompoundTag();
        both.putIntArray("was", new int[] {30, 10});
        both.putInt("copper", 500);
        load(loaded, both);
        check(s(loaded.wasteStack).equals("Steel=10"), "'copper' is ignored when 'was' exists");

        CompoundTag odd = new CompoundTag();
        odd.putIntArray("rec", new int[] {9999, 50, 30, 100, 33, 0, 7400, -3, 2700, 20_000, 2900});
        odd.putIntArray("was", new int[] {0, 5, 33, 7});
        odd.putString("recipe", "null");
        load(loaded, odd);
        check(s(loaded.recipeStack).equals("Steel=100,Cobalt=10368") && s(loaded.wasteStack).equals("DuraSteel=7"),
                "unknown IDs and non-positive amounts are dropped, amounts clamped to 10,368, a trailing ID ignored: "
                        + s(loaded.recipeStack) + " / " + s(loaded.wasteStack));
        Object[][] clamps = {{-5, -1, 0, 0}, {200_000, 25_000, MAX_HEAT, PROCESS - 1}, {50_000, 19_999, 50_000, 19_999}};
        for(Object[] entry : clamps) {
            CompoundTag t = new CompoundTag();
            t.putInt("heat", (int) entry[0]);
            t.putInt("progress", (int) entry[1]);
            load(loaded, t);
            check(loaded.heat == (int) entry[2] && loaded.progress == (int) entry[3],
                    "heat " + entry[0] + " / progress " + entry[1] + " load as " + entry[2] + " / " + entry[3]);
        }
        CompoundTag numeric = new CompoundTag();
        numeric.putInt("recipe", 5);
        load(loaded, numeric);
        check("null".equals(loaded.recipe) && loaded.recipeStack.isEmpty() && loaded.wasteStack.isEmpty(), "a missing recipe string loads as \"null\"");
    }

    // ---- 9b. Sync ----------------------------------------------------------------------------------------------------

    private static RegistryFriendlyByteBuf payload(int heat, int progress, String recipe, int[] rec, int recSize, int[] was, int wasSize) {
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        buf.writeInt(heat);
        buf.writeInt(progress);
        buf.writeUtf(recipe);
        buf.writeShort(recSize);
        for(int v : rec) buf.writeInt(v);
        buf.writeShort(wasSize);
        for(int v : was) buf.writeInt(v);
        return buf;
    }

    private static void sync() {
        Level level = level();
        MachineCrucibleBlockEntity c = crucible(level, new BlockPos(0, 1, 0));
        select(c, "crucible.hss");
        set(c.recipeStack, ms(Mats.MAT_STEEL, 40), ms(Mats.MAT_DURA, 72));
        set(c.wasteStack, ms(Mats.MAT_COPPER, 100), ms(Mats.MAT_COBALT, 8));
        c.heat = 77_777;
        c.progress = 1_234;
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        c.serialize(buf);
        check(buf.values().equals(List.of(77_777, 1_234, "crucible.hss", (short) 2, 30, 40, 33, 72, (short) 2, 2900, 100, 2700, 8)),
                "payload: int heat, int progress, UTF recipe, short n + n x (int id, int amount) for the recipe then the waste stack: " + buf.values());
        MachineCrucibleBlockEntity client = crucible(level(), new BlockPos(0, 1, 0));
        client.deserialize(buf);
        check(client.heat == 77_777 && client.progress == 1_234 && "crucible.hss".equals(client.recipe)
                && s(client.recipeStack).equals("Steel=40,DuraSteel=72") && s(client.wasteStack).equals("Copper=100,Cobalt=8")
                && buf.readableBytes() == 0, "the payload round-trips and is read completely");

        // Unknown IDs are skipped without losing alignment: both ints of every entry are read. A misaligned read hits a
        // value of another type in the typed stand-in buffer; that is reported as this check failing.
        try {
            client.deserialize(payload(1, 2, "null", new int[] {9999, 5, 30, 100, 33, 0}, 3, new int[] {12345, 77, 2900, 7}, 2));
        } catch(RuntimeException e) {
            check(false, "a payload with unknown IDs is read without misalignment: " + e);
        }
        check(s(client.recipeStack).equals("Steel=100") && s(client.wasteStack).equals("Copper=7") && client.heat == 1 && client.progress == 2,
                "unknown IDs and non-positive amounts are skipped, the following entries stay aligned: " + s(client.recipeStack) + " / " + s(client.wasteStack));

        // Size bound 0..64; a rejected payload leaves both stacks as they were.
        int[] full = new int[128];
        for(int i = 0; i < 64; i++) { full[i * 2] = 30; full[i * 2 + 1] = 1; }
        client.deserialize(payload(1, 2, "null", full, 64, new int[0], 0));
        check(s(client.recipeStack).equals(String.join(",", java.util.Collections.nCopies(64, "Steel=1"))) && client.wasteStack.isEmpty(),
                "64 entries are accepted");
        set(client.recipeStack, ms(Mats.MAT_STEEL, 11));
        set(client.wasteStack, ms(Mats.MAT_COPPER, 22));
        int[] tooMany = new int[130];
        for(int i = 0; i < 65; i++) { tooMany[i * 2] = 30; tooMany[i * 2 + 1] = 1; }
        Object[][] bad = {{tooMany, 65, new int[0], 0, "65 recipe entries"}, {new int[0], -1, new int[0], 0, "-1 recipe entries"},
                {new int[] {30, 5}, 1, tooMany, 65, "65 waste entries after a valid recipe stack"}};
        for(Object[] entry : bad) {
            RuntimeException thrown = null;
            try {
                client.deserialize(payload(3, 4, "crucible.hss", (int[]) entry[0], (int) entry[1], (int[]) entry[2], (int) entry[3]));
            } catch(RuntimeException e) {
                thrown = e;
            }
            check(thrown instanceof IllegalArgumentException, entry[4] + " is rejected by throwing IllegalArgumentException: " + thrown);
            check(s(client.recipeStack).equals("Steel=11") && s(client.wasteStack).equals("Copper=22"), entry[4] + ": both stacks unchanged");
        }
    }

    // ---- 10. Scraps --------------------------------------------------------------------------------------------------

    private static void scraps() {
        Level level = level();
        MachineCrucibleBlockEntity c = crucible(level, new BlockPos(0, 1, 0));
        set(c.recipeStack, ms(Mats.MAT_STEEL, 10), ms(Mats.MAT_DURA, 20));
        set(c.wasteStack, ms(Mats.MAT_COPPER, 5), ms(Mats.MAT_COBALT, 3));
        int dirty = c.dirty;
        List<ItemStack> scraps = c.takeScraps();
        check(scraps.size() == 4, "one scrap per material entry: " + scraps.size());
        NTMMaterial[] order = {Mats.MAT_STEEL, Mats.MAT_DURA, Mats.MAT_COPPER, Mats.MAT_COBALT};
        int[] amounts = {10, 20, 5, 3};
        for(int i = 0; i < 4; i++) {
            MaterialStack contents = CopperScrapsItem.getMats(scraps.get(i));
            check(contents != null && contents.material == order[i] && contents.amount == amounts[i] && !CopperScrapsItem.isLiquid(scraps.get(i))
                    && scraps.get(i).customTag.getInt("material") == order[i].id && scraps.get(i).customTag.getInt("amount") == amounts[i],
                    "scrap " + i + " is " + order[i].names[0] + " " + amounts[i] + " (recipe stack first, then waste stack)");
        }
        check(c.recipeStack.isEmpty() && c.wasteStack.isEmpty() && c.dirty > dirty, "both stacks cleared and the crucible marked changed");
        check(c.takeScraps().isEmpty(), "an empty crucible gives no scraps");

        MachineCrucibleBlockEntity remelt = crucible(level, new BlockPos(5, 1, 0));
        level.time = 1;
        meltOne(remelt, scraps.get(1));
        check(s(remelt.wasteStack).equals("DuraSteel=20"), "a DuraSteel scrap remelts into 20 quanta");

        check(CopperScrapsItem.create(null).isEmpty() && CopperScrapsItem.create(ms(Mats.MAT_STEEL, 0)).isEmpty()
                && CopperScrapsItem.create(ms(null, 5)).isEmpty(), "no scrap for nothing, zero quanta or no material");
        // The registered SCRAPS stand-in is a plain item; a CopperScrapsItem instance supplies the production getName.
        // Its description ID comes from the stand-in Item; the item.hbmsntm.scraps text is checked by the resource script.
        CopperScrapsItem scrapsItem = new CopperScrapsItem(new Item.Properties());
        String key = scrapsItem.getDescriptionId();
        Component name = scrapsItem.getName(CopperScrapsItem.create(ms(Mats.MAT_STEEL, 72)));
        check(name.key.equals(key) && name.args.length == 1 && ((Component) name.args[0]).key.equals("hbmmat.steel"),
                "scrap name is the item's %s pattern filled with the material name");
        Component liquidName = scrapsItem.getName(CopperScrapsItem.create(ms(Mats.MAT_STEEL, 72), true));
        check(liquidName.key.equals("hbmmat.steel"), "a liquid display scrap is named after its material");
        check(scrapsItem.getName(scrap(9999, 5)).key.equals(key + ".generic"), "invalid scraps use the generic name");
    }

    // ---- 12. Chain ---------------------------------------------------------------------------------------------------

    private static void chain() {
        // Steel without a recipe: 3 ingots -> waste stack -> rear mold -> one steel plate.
        Level level = level();
        BlockPos pos = new BlockPos(0, 1, 0);
        HeaterFireboxBlockEntity fire = firebox(level, new BlockPos(0, 0, 0));
        MachineCrucibleBlockEntity c = crucible(level, pos);
        FoundryMoldBlockEntity front = mold(level, new BlockPos(0, 0, -2), true), rear = mold(level, new BlockPos(0, 0, 2), true);
        aim(level, pos, Direction.NORTH, front.getBlockPos(), Direction.UP);
        aim(level, pos, Direction.SOUTH, rear.getBlockPos(), Direction.UP);
        fire.slots.set(0, item(Items.COAL, 4));
        for(int i = 0; i < 3; i++) c.slots.set(i, item(NtmItems.INGOT_STEEL.get()));
        int plates = 0;
        for(int t = 0; t < 6_000 && plates < 1; t++) {
            tick(level, fire, c, front, rear);
            int inputs = (int) c.slots.stream().filter(s -> !s.isEmpty()).count();
            check(inputs * INGOT + total(c.wasteStack) + total(c.recipeStack) + rear.amount + front.amount
                    + (rear.slots.get(1).isEmpty() ? 0 : PLATE) == PLATE, "steel chain conserves 216 quanta at tick " + t);
            if(!rear.slots.get(1).isEmpty()) {
                check(plate(rear.slots.get(1), 11), "the rear mold casts a steel plate (META 11)");
                plates++;
            }
        }
        check(plates == 1 && c.wasteStack.isEmpty() && c.recipeStack.isEmpty() && front.amount == 0 && front.slots.get(1).isEmpty(),
                "3 steel ingots without a recipe make one steel plate at the rear; the front mold stays empty");

        // HSS: select crucible.hss, feed 5 steel + 3 tungsten ingots + 9 cobalt fragments -> 648 DuraSteel -> 3 plates.
        Level hssLevel = level();
        HeaterFireboxBlockEntity hFire = firebox(hssLevel, new BlockPos(0, 0, 0));
        MachineCrucibleBlockEntity h = crucible(hssLevel, pos);
        FoundryMoldBlockEntity hFront = mold(hssLevel, new BlockPos(0, 0, -2), true), hRear = mold(hssLevel, new BlockPos(0, 0, 2), true);
        aim(hssLevel, pos, Direction.NORTH, hFront.getBlockPos(), Direction.UP);
        aim(hssLevel, pos, Direction.SOUTH, hRear.getBlockPos(), Direction.UP);
        CompoundTagControl.handleServer(new CompoundTagControl(control(0, "crucible.hss"), pos), ctx(viewer(h)));
        check("crucible.hss".equals(h.recipe), "crucible.hss selected through the control payload");
        hFire.slots.set(0, item(Items.COAL, 16));
        Deque<ItemStack> feed = new ArrayDeque<>();
        for(int i = 0; i < 5; i++) feed.add(item(NtmItems.INGOT_STEEL.get()));
        for(int i = 0; i < 3; i++) feed.add(item(NtmItems.INGOT_TUNGSTEN.get()));
        for(int i = 0; i < 9; i++) feed.add(item(NtmItems.FRAGMENT_COBALT.get()));
        List<ItemStack> collected = new ArrayList<>();
        int maxDura = 0;
        for(int t = 0; t < 40_000 && collected.size() < 3; t++) {
            // A hopper-like feeder: the next item goes into the first empty slot the crucible accepts.
            for(int slot = 0; slot < 9 && !feed.isEmpty(); slot++) {
                if(h.canPlaceItem(slot, feed.peek())) h.slots.set(slot, feed.poll());
            }
            tick(hssLevel, hFire, h, hFront, hRear);
            int quanta = 0;
            for(ItemStack queued : feed) quanta += CopperCastingRecipes.getMaterial(queued).amount;
            for(ItemStack inSlot : h.slots) if(!inSlot.isEmpty()) quanta += CopperCastingRecipes.getMaterial(inSlot).amount;
            quanta += total(h.recipeStack) + total(h.wasteStack) + hFront.amount + hRear.amount;
            quanta += (hFront.slots.get(1).isEmpty() ? 0 : PLATE) + collected.size() * PLATE;
            check(quanta == BLOCK, "HSS chain conserves 648 quanta at tick " + t + ": " + quanta);
            check(h.wasteStack.isEmpty() && hRear.amount == 0, "nothing reaches the waste stack or the rear mold");
            maxDura = Math.max(maxDura, MachineCrucibleBlockEntity.getQuantaFromType(h.recipeStack, Mats.MAT_DURA));
            if(!hFront.slots.get(1).isEmpty()) {
                check(plate(hFront.slots.get(1), 12), "the front mold casts a high-speed steel plate (META 12)");
                collected.add(hFront.removeItem(1, 1));
            }
        }
        check(collected.size() == 3 && feed.isEmpty() && h.recipeStack.isEmpty() && h.slots.stream().allMatch(ItemStack::isEmpty)
                && hFront.amount == 0, "5 steel + 3 tungsten ingots + 9 cobalt fragments make 3 HSS plates at the front, nothing left");
        check(maxDura > 0 && maxDura <= BLOCK, "DuraSteel in the recipe stack never exceeds 648");
    }

    // ---- 13. JEI data ------------------------------------------------------------------------------------------------

    private static final class Slot {
        final RecipeIngredientRole role;
        final List<ItemStack> stacks = new ArrayList<>();
        final List<IRecipeSlotRichTooltipCallback> tooltips = new ArrayList<>();

        Slot(RecipeIngredientRole role) {
            this.role = role;
        }
    }

    private static final class Layout implements IRecipeLayoutBuilder {
        final List<Slot> slots = new ArrayList<>();

        @Override
        public IRecipeSlotBuilder addSlot(RecipeIngredientRole role, int x, int y) {
            Slot slot = new Slot(role);
            slots.add(slot);
            return new IRecipeSlotBuilder() {
                @Override public IRecipeSlotBuilder addItemStack(ItemStack stack) { slot.stacks.add(stack); return this; }
                @Override public IRecipeSlotBuilder addRichTooltipCallback(IRecipeSlotRichTooltipCallback callback) { slot.tooltips.add(callback); return this; }
            };
        }

        List<Slot> role(RecipeIngredientRole role) {
            return slots.stream().filter(s -> s.role == role).toList();
        }
    }

    private static final class Gui implements IGuiHelper {
        final List<ResourceLocation> textures = new ArrayList<>();
        final List<Item> icons = new ArrayList<>();

        @Override
        public IDrawableBuilder drawableBuilder(ResourceLocation texture, int u, int v, int w, int h) {
            textures.add(texture);
            return new IDrawableBuilder() {
                @Override public IDrawableBuilder setTextureSize(int width, int height) { return this; }
                @Override public IDrawable build() { return new IDrawable() { }; }
            };
        }

        @Override
        public IDrawable createDrawableItemLike(ItemLike item) {
            icons.add(item.asItem());
            return new IDrawable() { };
        }
    }

    private static void jei() {
        // crucible.hss as registered by CrucibleRecipes (original CrucibleRecipes.java:91-93).
        List<CrucibleRecipe> recipes = CrucibleRecipes.INSTANCE.recipeOrderedList;
        check(recipes.size() == 1 && CrucibleRecipes.INSTANCE.recipeNameMap.size() == 1, "exactly one crucible recipe");
        CrucibleRecipe hss = recipes.get(0);
        check(hss.getInternalName().equals("crucible.hss") && hss.frequency == 9 && hss.getIcon().is(NtmItems.INGOT_DURA_STEEL.get())
                && hss.getIcon().getCount() == 1, "crucible.hss: frequency 9, icon one ingot_dura_steel");
        check(s(List.of(hss.input)).equals("Steel=40,Tungsten=24,Cobalt=8") && s(List.of(hss.output)).equals("DuraSteel=72")
                && hss.getInputAmount() == 72, "crucible.hss: Steel 40 + Tungsten 24 + Cobalt 8 -> DuraSteel 72");
        check(!hss.customLocalization && hss.getName().key.equals("item.hbmsntm.ingot_dura_steel"),
                "crucible.hss is not named: it shows the icon's name");
        CrucibleRecipes.INSTANCE.registerDefaults();
        check(recipes.size() == 1, "registerDefaults does not register twice");
        check(CrucibleRecipes.INSTANCE.getFileName().equals("hbmCrucible.json"), "recipe file hbmCrucible.json");

        // Alloying category: inputs and output as liquid scraps, the crucible as catalyst.
        Gui gui = new Gui();
        CrucibleAlloyingRecipeHandler alloying = new CrucibleAlloyingRecipeHandler(gui);
        check(alloying.getRecipeType().namespace().equals("hbmsntm") && alloying.getRecipeType().path().equals("crucible_alloying")
                && alloying.getRecipeType().recipeClass() == CrucibleRecipe.class, "alloying type hbmsntm:crucible_alloying");
        check(alloying.getTitle().key.equals("container.machine_crucible.jei.alloying"), "alloying title key");
        Layout layout = new Layout();
        alloying.setRecipe(layout, hss, null);
        List<Slot> in = layout.role(RecipeIngredientRole.INPUT), out = layout.role(RecipeIngredientRole.OUTPUT), cat = layout.role(RecipeIngredientRole.CATALYST);
        check(in.size() == 3 && liquid(in.get(0).stacks.get(0), Mats.MAT_STEEL, 40) && liquid(in.get(1).stacks.get(0), Mats.MAT_TUNGSTEN, 24)
                && liquid(in.get(2).stacks.get(0), Mats.MAT_COBALT, 8), "alloying inputs are liquid scraps 40/24/8");
        check(out.size() == 1 && liquid(out.get(0).stacks.get(0), Mats.MAT_DURA, 72), "alloying output is liquid DuraSteel 72");
        List<Object> hint = new ArrayList<>();
        cat.get(0).tooltips.get(0).onRichTooltip(null, hint::add);
        check(cat.size() == 1 && cat.get(0).stacks.get(0).is(NtmBlocks.MACHINE_CRUCIBLE.asItem()) && hint.size() == 1
                && ((Component) hint.get(0)).key.equals("container.machine_crucible.jei.select_hint") && ((Component) hint.get(0)).args[0].equals(9),
                "alloying catalyst is the crucible with the selection hint and the frequency");

        // Smelting category: the 13 melt entries.
        CrucibleSmeltingRecipeHandler smelting = new CrucibleSmeltingRecipeHandler(gui);
        check(smelting.getRecipeType().path().equals("crucible_smelting") && smelting.getTitle().key.equals("container.machine_crucible.jei.smelting"),
                "smelting type and title");
        for(CopperCastingRecipes.MeltEntry entry : CopperCastingRecipes.getMeltEntries()) {
            Layout l = new Layout();
            smelting.setRecipe(l, entry, null);
            check(l.role(RecipeIngredientRole.INPUT).get(0).stacks.get(0).is(entry.item())
                    && liquid(l.role(RecipeIngredientRole.OUTPUT).get(0).stacks.get(0), entry.material(), entry.amount())
                    && l.role(RecipeIngredientRole.CATALYST).get(0).stacks.get(0).is(NtmBlocks.MACHINE_CRUCIBLE.asItem()),
                    "smelting shows " + entry.item().id + " -> " + entry.material().names[0] + " " + entry.amount());
        }

        // Casting category: Copper, Tungsten, Steel, DuraSteel, 216 quanta each, with their plates.
        check(CopperCastingRecipes.getCastableMaterials().equals(List.of(Mats.MAT_COPPER, Mats.MAT_TUNGSTEN, Mats.MAT_STEEL, Mats.MAT_DURA)),
                "castable materials in registration order: Copper, Tungsten, Steel, DuraSteel");
        CrucibleCastingRecipeHandler casting = new CrucibleCastingRecipeHandler(gui);
        List<CrucibleCastingRecipeHandler.Casting> castings = CrucibleCastingRecipeHandler.getRecipes();
        int[] metas = {5, 6, 11, 12};
        check(castings.size() == 4 && casting.getRecipeType().path().equals("crucible_casting")
                && casting.getTitle().key.equals("container.machine_crucible.jei.casting"), "casting type, title and four recipes");
        for(int i = 0; i < castings.size(); i++) {
            Layout l = new Layout();
            casting.setRecipe(l, castings.get(i), null);
            NTMMaterial m = castings.get(i).material();
            List<Slot> catalysts = l.role(RecipeIngredientRole.CATALYST);
            check(liquid(l.role(RecipeIngredientRole.INPUT).get(0).stacks.get(0), m, PLATE) && plate(l.role(RecipeIngredientRole.OUTPUT).get(0).stacks.get(0), metas[i])
                    && plate(CopperCastingRecipes.getPlate(m), metas[i])
                    && catalysts.size() == 2 && catalysts.get(0).stacks.get(0).is(NtmItems.MOLD_PLATE_CAST.get())
                    && catalysts.get(1).stacks.get(0).is(NtmBlocks.FOUNDRY_MOLD.asItem()),
                    "casting " + m.names[0] + ": 216 quanta + plate mold -> plate META " + metas[i]);
        }
        check(CopperCastingRecipes.getPlate(Mats.MAT_COBALT).isEmpty() && CopperCastingRecipes.getPlateType(Mats.MAT_COBALT) == null,
                "cobalt has no plate");
        List<String> textures = gui.textures.stream().map(ResourceLocation::toString).toList();
        check(textures.equals(List.of("ResourceLocation[n=hbmsntm, p=textures/gui/jei/gui_nei_crucible.png]",
                "ResourceLocation[n=hbmsntm, p=textures/gui/jei/gui_nei_crucible_smelting.png]",
                "ResourceLocation[n=hbmsntm, p=textures/gui/jei/gui_nei_foundry.png]")), "category backgrounds: " + textures);
        check(gui.icons.equals(List.of(NtmBlocks.MACHINE_CRUCIBLE.asItem(), NtmBlocks.MACHINE_CRUCIBLE.asItem(), NtmBlocks.FOUNDRY_MOLD.asItem())),
                "category icons: crucible, crucible, foundry mold");

        // Subtypes: material ID only.
        ScrapsSubtypeInterpreter subtypes = ScrapsSubtypeInterpreter.INSTANCE;
        for(NTMMaterial m : Mats.orderedList) {
            Object a = subtypes.getSubtypeData(CopperScrapsItem.create(ms(m, 72)), UidContext.Ingredient);
            Object b = subtypes.getSubtypeData(CopperScrapsItem.create(ms(m, 216), true), UidContext.Recipe);
            check(a != null && a.equals(b) && a.equals(m.id), m.names[0] + " scraps share one subtype (the material ID) whatever the amount or liquid flag");
            check(subtypes.getLegacyStringSubtypeInfo(CopperScrapsItem.create(ms(m, 9)), UidContext.Ingredient).equals(Integer.toString(m.id)),
                    m.names[0] + " legacy subtype string is the material ID");
        }
        check(!subtypes.getSubtypeData(CopperScrapsItem.create(ms(Mats.MAT_STEEL, 72)), UidContext.Ingredient)
                .equals(subtypes.getSubtypeData(CopperScrapsItem.create(ms(Mats.MAT_DURA, 72)), UidContext.Ingredient)), "different materials differ");
        check(subtypes.getSubtypeData(new ItemStack(NtmItems.SCRAPS.get()), UidContext.Ingredient) == null
                && subtypes.getSubtypeData(scrap(9999, 5), UidContext.Ingredient) == null
                && subtypes.getLegacyStringSubtypeInfo(scrap(9999, 5), UidContext.Ingredient).isEmpty(), "invalid scraps have no subtype");

        // Source level: JEI stays in com.hbm.handler.jei, and the plugin registers what the data above feeds.
        List<String> outside;
        try(Stream<Path> files = Files.walk(source)) {
            outside = files.filter(p -> p.toString().endsWith(".java")).filter(p -> !source.relativize(p).toString().replace('\\', '/').startsWith("com/hbm/handler/jei/"))
                    .filter(p -> read(p).contains("mezz.jei")).map(p -> source.relativize(p).toString()).toList();
        } catch(IOException e) {
            throw new UncheckedIOException(e);
        }
        check(outside.isEmpty(), "mezz.jei is referenced only under com/hbm/handler/jei: " + outside);
        String plugin = read(source.resolve("com/hbm/handler/jei/NtmJeiPlugin.java")).replaceAll("\\s+", " ");
        for(String expected : new String[] {
                "new CrucibleSmeltingRecipeHandler(guiHelper)", "new CrucibleAlloyingRecipeHandler(guiHelper)", "new CrucibleCastingRecipeHandler(guiHelper)",
                "registration.addRecipes(CrucibleSmeltingRecipeHandler.RECIPE_TYPE, CopperCastingRecipes.getMeltEntries());",
                "registration.addRecipes(CrucibleAlloyingRecipeHandler.RECIPE_TYPE, CrucibleRecipes.INSTANCE.recipeOrderedList);",
                "registration.addRecipes(CrucibleCastingRecipeHandler.RECIPE_TYPE, CrucibleCastingRecipeHandler.getRecipes());",
                "registration.addRecipeCatalyst( NtmBlocks.MACHINE_CRUCIBLE.asItem(), CrucibleSmeltingRecipeHandler.RECIPE_TYPE, CrucibleAlloyingRecipeHandler.RECIPE_TYPE );",
                "registration.addRecipeCatalyst( NtmBlocks.FOUNDRY_MOLD.asItem(), CrucibleCastingRecipeHandler.RECIPE_TYPE );",
                "registration.addRecipeCatalyst( NtmItems.MOLD_PLATE_CAST.get(), CrucibleCastingRecipeHandler.RECIPE_TYPE );",
                "registration.addRecipeClickArea(MachineCrucibleScreen.class, MachineCrucibleScreen.ARROW_X, MachineCrucibleScreen.ARROW_Y, MachineCrucibleScreen.ARROW_WIDTH, MachineCrucibleScreen.ARROW_HEIGHT, CrucibleSmeltingRecipeHandler.RECIPE_TYPE, CrucibleAlloyingRecipeHandler.RECIPE_TYPE);",
                "registration.registerSubtypeInterpreter(NtmItems.SCRAPS.get(), ScrapsSubtypeInterpreter.INSTANCE);"}) {
            check(count(plugin, expected) == 1, "NtmJeiPlugin registers exactly once: " + expected);
        }
        int transfer = plugin.indexOf("public void registerRecipeTransferHandlers(");
        int next = plugin.indexOf("@Override", transfer);
        check(transfer >= 0 && next > transfer && !plugin.substring(transfer, next).contains("Crucible"),
                "no crucible recipe-transfer handler (alloys are chosen only in the crucible's selector)");
    }

    // ---- 13b. Scraps model values, colour and creative tab -------------------------------------------------------------

    private static void scrapsDisplay() {
        float[] expected = {0F, 0.2F, 0.4F, 0.6F, 0.8F};
        NTMMaterial[] order = {Mats.MAT_COPPER, Mats.MAT_TUNGSTEN, Mats.MAT_COBALT, Mats.MAT_STEEL, Mats.MAT_DURA};
        check(CopperScrapsItem.getModelType(new ItemStack(NtmItems.SCRAPS.get())) == 0F, "scraps without data use the base model (0)");
        for(int i = 0; i < order.length; i++) {
            float value = CopperScrapsItem.getModelType(CopperScrapsItem.create(ms(order[i], 72)));
            check(Math.abs(value - expected[i]) < 1e-6, order[i].names[0] + " scraps model value " + expected[i] + ", found " + value);
            float liquidValue = CopperScrapsItem.getModelType(CopperScrapsItem.create(ms(order[i], 72), true));
            check(Math.abs(liquidValue - 1F) < 1e-6, order[i].names[0] + " liquid scraps model value 1.0");
            check(CopperScrapsItem.getColor(CopperScrapsItem.create(ms(order[i], 72))) == 0xFFFFFF
                    && CopperScrapsItem.getColor(CopperScrapsItem.create(ms(order[i], 72), true)) == order[i].moltenColor,
                    order[i].names[0] + ": solid scraps untinted, liquid scraps in the molten colour");
        }
        check(CopperScrapsItem.getModelType(scrap(9999, 5)) == 0F && CopperScrapsItem.getColor(scrap(9999, 5)) == 0xFFFFFF,
                "invalid scraps: base model, untinted");
        List<String> names = CopperScrapsItem.MODEL_MATERIALS.stream().map(CopperScrapsItem::getModelName).toList();
        check(names.equals(List.of("scraps_tungsten", "scraps_cobalt", "scraps_steel", "scraps_durasteel")), "model names " + names);

        // NtmCreativeTabs is not compiled (registries); one 72-quanta scrap per material is checked in its source.
        String tabs = read(source.resolve("com/hbm/inventory/NtmCreativeTabs.java")).replaceAll("\\s+", " ");
        check(count(tabs, "for(NTMMaterial material : Mats.orderedList) { output.accept(CopperScrapsItem.create(new Mats.MaterialStack(material, MaterialShapes.INGOT.q(1)))); }") == 1
                && !tabs.contains("output.accept(NtmItems.SCRAPS.get());"), "the creative tab lists one ingot's worth of scraps per material");
    }

    private static String read(Path path) {
        try {
            return Files.readString(path, StandardCharsets.UTF_8);
        } catch(IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static int count(String text, String part) {
        int n = 0;
        for(int i = text.indexOf(part); i >= 0; i = text.indexOf(part, i + 1)) n++;
        return n;
    }

    public static void main(String[] args) {
        source = Path.of(args[0]);
        CrucibleRecipes.INSTANCE.registerDefaults();
        run("1. materials", Goal10ARegression::materials);
        run("2. melt table", Goal10ARegression::meltTable);
        run("3. heat, smelting and routing", Goal10ARegression::routing);
        run("4. insertion", Goal10ARegression::insertion);
        run("5. alloying", Goal10ARegression::alloying);
        run("6. pouring", Goal10ARegression::pouring);
        run("7. mold", Goal10ARegression::moldRules);
        run("8. recipe selection and permission", Goal10ARegression::selection);
        run("9. save", Goal10ARegression::saving);
        run("9b. sync", Goal10ARegression::sync);
        run("10. scraps", Goal10ARegression::scraps);
        run("12. chain", Goal10ARegression::chain);
        run("13. JEI data", Goal10ARegression::jei);
        run("13b. scraps model, colour and creative tab", Goal10ARegression::scrapsDisplay);
        System.out.println("Goal 10A machine checks: " + checks + " passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
