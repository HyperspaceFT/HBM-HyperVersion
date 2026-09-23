package com.hbm.blockentity.machine;

import api.hbm.energymk2.Nodespace;
import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.items.NtmItems;
import com.hbm.uninos.UniNodespace;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.menus.MachineAssemblyMachineMenu;

import java.util.List;

public class ProcessingRegression {
    private static int checks;
    private static final String SHREDDER = "ass.shredder";

    private static class Battery extends Item implements IBatteryItem {
        Battery() { super("test_battery"); }
    }

    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }

    private static MachineAssemblyMachineBlockEntity assembler(Level level, int x, int z) {
        var be = new MachineAssemblyMachineBlockEntity(new BlockPos(x, 0, z), new BlockState());
        level.put(be);
        return be;
    }

    private static void inputs(MachineAssemblyMachineBlockEntity be) {
        be.slots.set(4, new ItemStack(NtmItems.PLATE_STEEL.get(), 8));
        be.slots.set(5, new ItemStack(NtmItems.PLATE_COPPER.get(), 4));
        be.slots.set(6, new ItemStack(NtmItems.MOTOR.get(), 2));
    }

    private static void select(MachineAssemblyMachineBlockEntity be) {
        var tag = new CompoundTag();
        tag.putInt("index", 0);
        tag.putString("selection", SHREDDER);
        be.receiveControl(tag);
    }

    private static CableBaseBlockEntity cable(Level level, int x, int z) {
        var be = new CableBaseBlockEntity(new BlockPos(x, 0, z), new BlockState());
        level.put(be);
        be.updateEntity();
        return be;
    }

    // Probe the machine's placement contract in menu slot order; MenuBase itself is not compiled here.
    private static int firstAcceptedSlot(MachineAssemblyMachineBlockEntity be, ItemStack stack) {
        for (int slot = 0; slot < 16; slot++) if (be.canPlaceItem(slot, stack)) return slot;
        return -1;
    }

    private static void networkTick(Level level) {
        var server = new MinecraftServer(List.of(level));
        UniNodespace.updateNodespace(server);
        UniNodespace.updateNodespace(server);
    }

    private static void recipeAndChecks() {
        var recipes = AssemblyMachineRecipes.INSTANCE;
        recipes.registerDefaults();
        var recipe = recipes.recipeNameMap.get(SHREDDER);
        check(recipe != null, "real default registry contains ass.shredder");
        check(recipe.duration == 100 && recipe.power == 100, "normal shredder is 100 ticks at 100 HE/t");
        check(recipe.inputItem.length == 3 && recipe.outputItem.length == 1, "three item inputs and one output");
        check(recipe.inputItem[0].matchesRecipe(new ItemStack(NtmItems.PLATE_STEEL.get(), 8), false), "eight steel plates");
        check(!recipe.inputItem[0].matchesRecipe(new ItemStack(NtmItems.PLATE_STEEL.get(), 7), false), "seven steel plates insufficient");
        check(recipe.inputItem[1].matchesRecipe(new ItemStack(NtmItems.PLATE_COPPER.get(), 4), false), "four copper plates");
        var alternativeSteel = new Item("other_mod_steel_plate");
        alternativeSteel.tags.add("plates/steel");
        var alternativeCopper = new Item("other_mod_copper_plate");
        alternativeCopper.tags.add("plates/copper");
        check(recipe.inputItem[0].matchesRecipe(new ItemStack(alternativeSteel, 8), false),
                "steel plate common tag accepts another member");
        check(recipe.inputItem[1].matchesRecipe(new ItemStack(alternativeCopper, 4), false),
                "copper plate common tag accepts another member");
        check(!recipe.inputItem[0].matchesRecipe(new ItemStack(Items.STONE, 8), false),
                "non-tagged wrong item cannot substitute for steel plate");
        check(recipe.inputItem[2].matchesRecipe(new ItemStack(NtmItems.MOTOR.get(), 2), false), "two motors");
        check(recipe.outputItem[0].getSingle().is(NtmBlocks.MACHINE_SHREDDER.get())
                && recipe.outputItem[0].getSingle().getCount() == 1, "one shredder output");
        check(!recipe.isPooled(), "no blueprint pool prerequisite");
        var be = assembler(new Level(), 0, 0);
        select(be);
        inputs(be);
        be.setPower(100);
        check(be.assemblerModule.canProcess(recipe, 1, 1), "valid inputs and 100 HE can process after precharge");
    }

    private static void placementContract() {
        var be = assembler(new Level(), 0, 0);
        var steel = new ItemStack(NtmItems.PLATE_STEEL.get());
        var copper = new ItemStack(NtmItems.PLATE_COPPER.get());
        var motor = new ItemStack(NtmItems.MOTOR.get());
        var battery = new ItemStack(new Battery());
        check(!be.canPlaceItem(0, steel) && !be.canPlaceItem(0, new ItemStack(Items.STONE)),
                "battery slot rejects plates and unrelated items");
        check(be.canPlaceItem(0, battery), "battery slot accepts IBatteryItem implementation");
        check(firstAcceptedSlot(be, battery) == 0, "battery first accepted at auxiliary slot zero");
        select(be);
        check(be.canPlaceItem(4, steel) && be.canPlaceItem(5, copper) && be.canPlaceItem(6, motor),
                "selected shredder admits steel, copper, motor in slots 4, 5, 6");
        check(!be.canPlaceItem(4, copper) && !be.canPlaceItem(5, steel) && !be.canPlaceItem(6, steel),
                "wrong recipe materials rejected in selected input positions");
        check(!be.canPlaceItem(2, steel) && !be.canPlaceItem(3, steel)
                && !be.canPlaceItem(7, steel) && !be.canPlaceItem(16, steel),
                "plates rejected from upgrades, unrelated input and output slots");
        check(firstAcceptedSlot(be, steel) == 4 && firstAcceptedSlot(be, copper) == 5
                && firstAcceptedSlot(be, motor) == 6,
                "slot-order probe reaches selected recipe inputs after auxiliary rejection");
    }

    private static void boundedProcessing() {
        var level = new Level();
        var be = assembler(level, 0, 0);
        var recipe = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(SHREDDER);
        inputs(be);
        select(be);
        check(be.assemblerModule.recipe.equals(SHREDDER), "selection applied");
        be.updateEntity();
        check(be.assemblerModule.progress == 0 && !be.didProcess, "no power resets progress");
        be.setPower(99);
        be.updateEntity();
        check(be.assemblerModule.progress == 0, "below 100 HE cannot progress");
        be.setPower(100);
        be.slots.set(4, new ItemStack(NtmItems.PLATE_STEEL.get(), 7));
        be.updateEntity();
        check(be.assemblerModule.progress == 0, "short first input blocks");
        be.slots.set(4, ItemStack.EMPTY);
        be.slots.set(7, new ItemStack(NtmItems.PLATE_STEEL.get(), 8));
        be.updateEntity();
        check(be.assemblerModule.progress == 0, "right material in wrong input slot blocks");
        be.slots.set(7, ItemStack.EMPTY);
        inputs(be);
        be.slots.set(5, new ItemStack(Items.STONE, 4));
        be.updateEntity();
        check(be.assemblerModule.progress == 0, "wrong second material blocks");
        inputs(be);
        be.slots.set(6, new ItemStack(NtmItems.MOTOR.get()));
        be.updateEntity();
        check(be.assemblerModule.progress == 0, "short motor count blocks");
        inputs(be);
        be.slots.set(16, new ItemStack(NtmBlocks.MACHINE_SHREDDER.get(), 64));
        be.updateEntity();
        check(be.assemblerModule.progress == 0, "full output stack blocks");
        be.slots.set(16, new ItemStack(NtmBlocks.MACHINE_SHREDDER.get(), 63));
        be.updateEntity();
        check(be.assemblerModule.progress > 0, "63 output allows one more");
        be.setPower(0);
        int resetDirty = be.dirty;
        be.updateEntity();
        check(be.assemblerModule.progress == 0 && be.dirty > resetDirty,
                "power loss resets paid progress and persists reset");
        be.setPower(100);
        be.updateEntity();
        check(be.assemblerModule.progress > 0, "restored power restarts recipe from zero");
        be.slots.set(16, new ItemStack(NtmBlocks.MACHINE_SHREDDER.get(), 63).component("different"));
        be.setPower(100);
        long mismatchPower = be.power;
        be.updateEntity();
        check(be.assemblerModule.progress == 0 && be.power == mismatchPower,
                "component mismatch resets progress without spending power");
        check(be.slots.get(4).getCount() == 8 && be.slots.get(5).getCount() == 4
                && be.slots.get(6).getCount() == 2 && be.slots.get(16).getCount() == 63,
                "component mismatch does not consume inputs or overwrite output");
        be.slots.set(16, ItemStack.EMPTY);
        be.setPower(10_000);
        for (int tick = 1; tick <= 99; tick++) be.updateEntity();
        check(be.slots.get(4).getCount() == 8 && be.slots.get(5).getCount() == 4
                && be.slots.get(6).getCount() == 2 && be.slots.get(16).isEmpty(),
                "no item consumed or output before tick 100");
        check(be.power == 100, "99 ticks cost 9900 HE");
        be.updateEntity();
        check(be.slots.get(4).isEmpty() && be.slots.get(5).isEmpty() && be.slots.get(6).isEmpty(),
                "completion consumes exact three inputs");
        check(be.slots.get(16).is(NtmBlocks.MACHINE_SHREDDER.get()) && be.slots.get(16).getCount() == 1,
                "tick 100 produces one shredder");
        check(be.power == 0 && be.assemblerModule.progress == 0, "100 ticks consume 10000 HE and stop");
        be.updateEntity();
        check(be.slots.get(16).getCount() == 1, "no duplicate output after input depletion");
        inputs(be);
        be.slots.set(16, new ItemStack(NtmBlocks.MACHINE_SHREDDER.get(), 63));
        be.setPower(10_000);
        for (int tick = 0; tick < 100; tick++) be.updateEntity();
        check(be.slots.get(16).getCount() == 64 && be.slots.get(4).isEmpty()
                && be.slots.get(5).isEmpty() && be.slots.get(6).isEmpty(),
                "63 output accepts full cycle and ends exactly at 64");
        inputs(be);
        be.setPower(100);
        be.updateEntity();
        check(be.slots.get(16).getCount() == 64 && be.slots.get(4).getCount() == 8
                && be.slots.get(5).getCount() == 4 && be.slots.get(6).getCount() == 2
                && be.power == 100 && be.assemblerModule.progress == 0,
                "full 64 output blocks next cycle without power or input consumption");
    }

    private static void selectionAndPersistence() {
        var level = new Level();
        var be = assembler(level, 0, 0);
        var player = new Player();
        player.world = level;
        check(!be.hasPermission(player), "closed menu rejects control");
        player.containerMenu = new MachineAssemblyMachineMenu(0, player.getInventory(), be);
        check(be.hasPermission(player), "matching menu permits control");
        var other = assembler(level, 10, 0);
        player.containerMenu = new MachineAssemblyMachineMenu(1, player.getInventory(), other);
        check(!be.hasPermission(player), "stale other-machine menu rejects control");
        player.containerMenu = new MachineAssemblyMachineMenu(2, player.getInventory(), be);
        be.valid = false;
        check(!be.hasPermission(player), "removed or distant machine rejects control");
        be.valid = true;
        player.world = new Level();
        check(!be.hasPermission(player), "player in another world rejects control");
        player.world = level;
        level.isClientSide = true;
        check(!be.hasPermission(player), "client side does not grant control");
        level.isClientSide = false;
        var invalid = new CompoundTag();
        invalid.putInt("index", 1);
        invalid.putString("selection", SHREDDER);
        be.receiveControl(invalid);
        check(be.assemblerModule.recipe.equals("null"), "wrong module index ignored");
        invalid.putInt("index", 0);
        invalid.putString("selection", "missing.recipe");
        be.receiveControl(invalid);
        check(be.assemblerModule.recipe.equals("null"), "unknown selection ignored");
        var mistyped = new CompoundTag();
        mistyped.putString("index", "0");
        mistyped.putString("selection", SHREDDER);
        be.receiveControl(mistyped);
        check(be.assemblerModule.recipe.equals("null"), "wrong index tag type ignored");
        select(be);
        inputs(be);
        be.setPower(1000);
        for(int tick = 0; tick < 5; tick++) be.updateEntity();
        check(be.assemblerModule.progress > 0 && be.slots.get(16).isEmpty(),
                "real shredder cycle is in progress before selection change");
        int dirty = be.dirty;
        select(be);
        check(be.assemblerModule.progress > 0 && be.dirty == dirty, "repeat selection preserves progress");
        var boytarget = new CompoundTag();
        boytarget.putInt("index", 0);
        boytarget.putString("selection", "ass.boytarget");
        be.receiveControl(boytarget);
        check(be.assemblerModule.recipe.equals("ass.boytarget") && be.assemblerModule.progress == 0
                && be.dirty > dirty, "changed valid recipe clears prior paid progress");
        inputs(be);
        be.setPower(1000);
        select(be);
        be.updateEntity();
        check(be.assemblerModule.progress < 0.02 && be.slots.get(16).isEmpty()
                && be.slots.get(4).getCount() == 8,
                "returning to shredder cannot use prior recipe progress to craft early");
        var clear = new CompoundTag();
        clear.putInt("index", 0);
        clear.putString("selection", "null");
        be.receiveControl(clear);
        check(be.assemblerModule.progress == 0 && be.assemblerModule.recipe.equals("null") && be.dirty > dirty,
                "selection change resets progress and marks dirty");
        var pooled = new GenericRecipe("fixture.pooled").setup(100, 100)
                .outputItems(new ItemStack(Items.STONE))
                .inputItems(new ComparableStack(NtmItems.MOTOR.get(), 1))
                .setPools("fixture.pool");
        AssemblyMachineRecipes.INSTANCE.register(pooled);
        var poolSelection = new CompoundTag();
        poolSelection.putInt("index", 0);
        poolSelection.putString("selection", "fixture.pooled");
        be.receiveControl(poolSelection);
        check(be.assemblerModule.recipe.equals("null"), "pooled recipe rejected without matching blueprint");
        be.slots.set(1, new ItemStack(new Item("test_blueprint")).component("fixture.pool"));
        be.receiveControl(poolSelection);
        check(be.assemblerModule.recipe.equals("fixture.pooled"), "matching blueprint permits pooled selection");
        be.slots.set(4, new ItemStack(NtmItems.MOTOR.get()));
        be.setPower(500);
        be.updateEntity();
        check(be.assemblerModule.progress > 0, "pooled fixture is processing with blueprint present");
        be.slots.set(1, ItemStack.EMPTY);
        int poolDirty = be.dirty;
        be.updateEntity();
        check(be.assemblerModule.recipe.equals("null") && be.assemblerModule.progress == 0
                && be.dirty > poolDirty, "removed blueprint cancels pooled cycle and saves reset");
        select(be);
        be.assemblerModule.progress = 0.42;
        be.power = 456;
        be.inputTank.setFill(23);
        var tag = new CompoundTag();
        be.saveAdditional(tag, null);
        var loaded = assembler(new Level(), 0, 0);
        loaded.loadAdditional(tag, null);
        check(loaded.power == 456 && loaded.assemblerModule.recipe.equals(SHREDDER)
                && loaded.assemblerModule.progress == 0.42, "power selection progress survive NBT");
        check(loaded.inputTank.getFill() == 23, "tank state survives NBT");
        var buf = new RegistryFriendlyByteBuf();
        be.serialize(buf);
        var synced = assembler(new Level(), 0, 0);
        synced.deserialize(buf);
        check(synced.power == 456 && synced.assemblerModule.recipe.equals(SHREDDER)
                && synced.assemblerModule.progress == 0.42, "power selection progress survive sync");
    }

    private static void integratedBurnerToShredder() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        var level = new Level();
        var be = assembler(level, 0, 0);
        var burner = new MachineWoodBurnerBlockEntity(new BlockPos(4, 0, 0), new BlockState());
        level.put(burner);
        var first = burner.getPowerConPos()[0];
        var wire = cable(level, first.getX(), first.getZ());
        var middle = cable(level, 3, 2);
        cable(level, 2, 2);
        cable(level, 2, 1);
        cable(level, 2, 0);
        networkTick(level);
        check(wire.node.hasValidNet(), "production cable network exists");
        select(be);
        inputs(be);
        burner.slots.set(0, new ItemStack(Items.OAK_LOG));
        burner.isOn = true;
        var server = new MinecraftServer(List.of(level));
        for (int tick = 0; tick < 20; tick++) {
            burner.updateEntity();
            be.updateEntity();
            UniNodespace.updateNodespace(server);
        }
        check(be.assemblerModule.progress > 0 && be.slots.get(16).isEmpty(),
                "network energy advances actual module without early output");
        be.setPower(500);
        middle.setRemoved();
        networkTick(level);
        double beforeStored = be.assemblerModule.progress;
        for (int tick = 0; tick < 5; tick++) {
            burner.updateEntity();
            be.updateEntity();
            UniNodespace.updateNodespace(server);
        }
        check(be.assemblerModule.progress > beforeStored && be.power == 0,
                "disconnected assembler runs five ticks on stored 500 HE");
        burner.updateEntity();
        be.updateEntity();
        UniNodespace.updateNodespace(server);
        check(be.assemblerModule.progress == 0 && be.slots.get(16).isEmpty(),
                "disconnected exhausted assembler resets without consuming inputs");
        var replacement = cable(level, 3, 2);
        networkTick(level);
        check(replacement.node.hasValidNet(), "replacement production cable rejoins power path");
        for (int tick = 0; tick < 110; tick++) {
            burner.updateEntity();
            be.updateEntity();
            UniNodespace.updateNodespace(server);
        }
        check(be.slots.get(16).is(NtmBlocks.MACHINE_SHREDDER.get()),
                "production burner, cables, assembler and module craft shredder");
        check(be.slots.get(16).getCount() == 1 && be.slots.get(4).isEmpty(),
                "integrated run crafts exactly once and consumes inputs");
        check(burner.power >= 0 && be.power >= 0, "network and machine power remain nonnegative");
    }

    public static void main(String[] args) {
        recipeAndChecks();
        placementContract();
        boundedProcessing();
        selectionAndPersistence();
        integratedBurnerToShredder();
        System.out.println("Goal 3C production processing/network regression: " + checks + " checks passed");
    }
}
