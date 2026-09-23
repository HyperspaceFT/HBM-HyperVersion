package com.hbm.blockentity.machine;

import com.hbm.inventory.recipes.BlastFurnaceRecipes;
import com.hbm.inventory.recipes.PressRecipes;
import com.hbm.items.machine.StampItem;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.util.InventoryUtil;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

public class Goal2Regression {
    private static int checks;
    private static final BlockPos POS = new BlockPos(0, 64, 0);
    private static final BlockState STATE = new BlockState();

    private static void check(boolean actual, String message) {
        checks++;
        if (!actual) throw new AssertionError(message);
    }

    private static MachinePressBlockEntity press(boolean client) {
        var m = new MachinePressBlockEntity(POS, STATE);
        m.level = new Level();
        m.level.isClientSide = client;
        return m;
    }

    private static MachineBlastFurnaceBlockEntity blast(boolean client) {
        var m = new MachineBlastFurnaceBlockEntity(POS, STATE);
        m.level = new Level();
        m.level.isClientSide = client;
        return m;
    }

    private static void pressCases() {
        var m = press(false);
        var stamp = new StampItem("plate_stamp", "plate", 32);
        m.slots.set(1, new ItemStack(stamp));
        m.slots.set(2, new ItemStack(PressRecipes.input, 3));
        check(!m.canProcess(), "press must require stored fuel");
        m.burnTime = 400;
        check(m.canProcess(), "press accepts a valid recipe");
        m.slots.set(1, new ItemStack(new StampItem("wrong", "wire", 32)));
        check(!m.canProcess(), "wrong stamp must reject recipe");
        m.slots.set(1, new ItemStack(stamp));
        m.slots.set(3, new ItemStack(PressRecipes.output, 64));
        check(!m.canProcess(), "full output must block press");
        m.slots.set(3, new ItemStack(PressRecipes.output, 1).component("other"));
        check(!m.canProcess(), "output component mismatch must block press");
        m.slots.set(3, ItemStack.EMPTY);
        PressRecipes.required = 2;
        m.slots.set(2, new ItemStack(PressRecipes.input));
        check(!m.canProcess(), "press rejects input below recipe count");
        m.slots.set(2, new ItemStack(PressRecipes.input, 3));
        check(m.canProcess(), "press accepts sufficient recipe count");
        PressRecipes.produced = 65;
        check(!m.canProcess(), "press rejects oversized output in empty slot");
        PressRecipes.produced = 1;
        m.slots.set(3, new ItemStack(PressRecipes.output, 63));
        check(m.canProcess(), "press accepts exact output stack boundary");
        m.slots.set(3, ItemStack.EMPTY);
        int initialDirty = m.dirty;
        m.press = 199;
        m.speed = 400;
        m.updateEntity();
        check(m.slots.get(2).getCount() == 1, "press consumes configured input count");
        check(m.slots.get(3).getCount() == 1, "press creates one output");
        check(m.burnTime == 200, "press charges 200 fuel per operation");
        check(m.slots.get(1).getDamageValue() == 1, "press damages stamp once");
        check(m.dirty > initialDirty, "press operation marks saved state dirty");
        for (int i = 0; i < 20; i++) m.updateEntity();
        check(m.slots.get(3).getCount() == 1, "retraction cannot duplicate output");
        PressRecipes.required = 1;

        for (int uses : new int[]{32, 64}) {
            var worn = press(false);
            var tool = new ItemStack(new StampItem("worn_" + uses, "plate", uses));
            tool.setDamageValue(uses - 1);
            worn.slots.set(1, tool);
            worn.slots.set(2, new ItemStack(PressRecipes.input));
            worn.burnTime = 200;
            worn.speed = 400;
            worn.press = 199;
            worn.updateEntity();
            check(worn.slots.get(1).isEmpty(), "stamp breaks after " + uses + " uses");
            check(worn.slots.get(3).getCount() == 1, "last stamp use still outputs at " + uses);
        }

        var client = press(true);
        client.burnTime = 200;
        client.press = 199;
        client.speed = 400;
        client.slots.set(1, new ItemStack(stamp));
        client.slots.set(2, new ItemStack(PressRecipes.input));
        client.updateEntity();
        check(client.slots.get(3).isEmpty() && client.slots.get(2).getCount() == 1, "client tick cannot craft");

        var saved = new CompoundTag();
        m.saveAdditional(saved, null);
        var loaded = press(false);
        loaded.loadAdditional(saved, null);
        check(loaded.press == m.press && loaded.speed == m.speed && loaded.burnTime == m.burnTime && loaded.isRetracting == m.isRetracting,
                "press NBT round-trips operation fields");
    }

    private static void inventoryCases() {
        Item part = new Item("part");
        Player player = new Player();
        player.getInventory().items.set(0, new ItemStack(part, 2));
        player.getInventory().items.set(1, new ItemStack(part, 3));
        var duplicate = List.of(new AStack(part, 3), new AStack(part, 3));
        check(!InventoryUtil.doesPlayerHaveAStacks(player, duplicate, true), "short duplicate requirements fail");
        check(player.getInventory().items.get(0).getCount() == 2 && player.getInventory().items.get(1).getCount() == 3,
                "failed aggregate requirement removes nothing");
        var enough = List.of(new AStack(part, 2), new AStack(part, 3));
        check(InventoryUtil.doesPlayerHaveAStacks(player, enough, false), "split stacks satisfy repeated requirements");
        check(player.getInventory().items.get(0).getCount() == 2, "dry run preserves inventory");
        check(InventoryUtil.doesPlayerHaveAStacks(player, enough, true), "sufficient aggregate requirement removes items");
        check(player.getInventory().items.get(0).isEmpty() && player.getInventory().items.get(1).isEmpty(),
                "transaction removes exact aggregate from multiple slots");
    }

    private static void blastCases() {
        var m = blast(false);
        m.slots.set(1, new ItemStack(BlastFurnaceRecipes.FIRST, 2));
        m.slots.set(2, new ItemStack(BlastFurnaceRecipes.SECOND));
        m.updateEntity();
        check(!m.isProgressing && m.progress == 0, "blast requires fuel");

        m.slots.set(0, new ItemStack(Items.COAL));
        check(BlastFurnaceRecipes.INSTANCE.getRecipe(m.slots.get(1), m.slots.get(2)) != null, "fixture recipe must match");
        m.updateEntity();
        check(m.fuel == 1600 && m.slots.get(0).isEmpty(), "coal burns into 1600 stored fuel");
        check(m.isProgressing && m.progress > 0, "blast progresses with recipe and fuel: progress=" + m.progress + " input=" + m.slots.get(1).getCount() + "," + m.slots.get(2).getCount());
        check(m.speed == 1.0F, "blast baseline speed is one");
        m.slots.set(3, new ItemStack(BlastFurnaceRecipes.RESULT, 64));
        m.updateEntity();
        check(!m.isProgressing && m.progress == 0, "full output resets progress");
        m.slots.set(3, new ItemStack(BlastFurnaceRecipes.RESULT, 1).component("other"));
        m.updateEntity();
        check(!m.isProgressing, "component mismatch blocks blast");
        m.slots.set(3, ItemStack.EMPTY);
        m.slots.set(4, new ItemStack(BlastFurnaceRecipes.SLAG, 64));
        m.updateEntity();
        check(!m.isProgressing, "full second output blocks blast");
        m.slots.set(4, ItemStack.EMPTY);
        m.slots.set(3, ItemStack.EMPTY);
        m.slots.set(1, new ItemStack(BlastFurnaceRecipes.FIRST));
        m.updateEntity();
        check(!m.isProgressing, "insufficient input count blocks blast");
        m.slots.set(1, new ItemStack(BlastFurnaceRecipes.FIRST, 2));
        m.slots.set(2, new ItemStack(new Item("invalid")));
        m.updateEntity();
        check(!m.isProgressing, "invalid second input blocks blast");
        m.slots.set(2, new ItemStack(BlastFurnaceRecipes.SECOND));
        m.progress = 0.99F;
        m.updateEntity();
        check(m.slots.get(1).isEmpty() && m.slots.get(2).isEmpty(), "blast consumes both inputs once");
        check(m.slots.get(3).getCount() == 2 && m.slots.get(4).getCount() == 1, "blast emits both outputs");
        check(m.fuel == 800 && m.tanks[1].getFill() == 100, "blast charges fuel and emits flue once");
        m.updateEntity();
        check(m.slots.get(3).getCount() == 2, "blast cannot repeat without input");

        var swapped = blast(false);
        swapped.fuel = 800;
        swapped.slots.set(1, new ItemStack(BlastFurnaceRecipes.SECOND));
        swapped.slots.set(2, new ItemStack(BlastFurnaceRecipes.FIRST, 2));
        swapped.progress = 0.99F;
        swapped.updateEntity();
        check(swapped.slots.get(3).getCount() == 2, "reversed input order crafts");
        check(swapped.slots.get(1).isEmpty() && swapped.slots.get(2).isEmpty(), "reversed order consumes correct counts");

        var replaced = blast(false);
        replaced.fuel = 800;
        replaced.slots.set(1, new ItemStack(BlastFurnaceRecipes.FIRST, 2));
        replaced.slots.set(2, new ItemStack(BlastFurnaceRecipes.SECOND));
        replaced.progress = 0.5F;
        replaced.slots.set(2, new ItemStack(new Item("invalid")));
        replaced.updateEntity();
        check(replaced.progress == 0 && !replaced.isProgressing, "midprocess invalid input resets progress");
        check(replaced.slots.get(3).isEmpty(), "midprocess replacement creates no output");

        var air = blast(false);
        air.fuel = 800;
        air.tanks[0].setFill(4000);
        air.slots.set(1, new ItemStack(BlastFurnaceRecipes.FIRST, 2));
        air.slots.set(2, new ItemStack(BlastFurnaceRecipes.SECOND));
        air.updateEntity();
        check(air.speed == 5.0F && air.tanks[0].getFill() == 3999, "airblast boosts speed with fivefold cap and drains one unit");

        var fuel = blast(false);
        fuel.fuel = MachineBlastFurnaceBlockEntity.MAX_FUEL - 1599;
        fuel.slots.set(0, new ItemStack(Items.COAL));
        fuel.updateEntity();
        check(fuel.fuel == MachineBlastFurnaceBlockEntity.MAX_FUEL - 1599 && fuel.slots.get(0).getCount() == 1,
                "blast refuses fuel when whole burn value exceeds capacity");
        fuel.fuel = MachineBlastFurnaceBlockEntity.MAX_FUEL - 1600;
        fuel.updateEntity();
        check(fuel.fuel == MachineBlastFurnaceBlockEntity.MAX_FUEL && fuel.slots.get(0).isEmpty(),
                "blast accepts fuel at exact capacity boundary");

        var timed = blast(false);
        timed.fuel = 800;
        timed.slots.set(1, new ItemStack(BlastFurnaceRecipes.FIRST, 2));
        timed.slots.set(2, new ItemStack(BlastFurnaceRecipes.SECOND));
        var fixtureRecipe = BlastFurnaceRecipes.INSTANCE.recipe;
        BlastFurnaceRecipes.INSTANCE.recipe = new com.hbm.inventory.recipes.BlastFurnaceRecipe(800,
                fixtureRecipe.inputItem, fixtureRecipe.outputItem);
        try {
            for (int tick = 1; tick <= 799; tick++) timed.updateEntity();
            check(timed.slots.get(3).isEmpty() && timed.fuel == 800, "duration 800 cannot finish by tick 799");
            timed.updateEntity();
            check(timed.slots.get(3).getCount() == 2 && timed.fuel == 0, "duration 800 finishes at tick 800");
        } finally {
            BlastFurnaceRecipes.INSTANCE.recipe = fixtureRecipe;
        }

        var client = blast(true);
        client.fuel = 800;
        client.slots.set(1, new ItemStack(BlastFurnaceRecipes.FIRST, 2));
        client.slots.set(2, new ItemStack(BlastFurnaceRecipes.SECOND));
        client.progress = 0.99F;
        client.updateEntity();
        check(client.slots.get(3).isEmpty() && client.fuel == 800, "client tick cannot smelt");

        var saved = new CompoundTag();
        swapped.saveAdditional(saved, null);
        var loaded = blast(false);
        loaded.loadAdditional(saved, null);
        check(loaded.fuel == swapped.fuel && loaded.progress == swapped.progress && loaded.speed == swapped.speed
                && loaded.isProgressing == swapped.isProgressing && loaded.tanks[1].getFill() == swapped.tanks[1].getFill(),
                "blast NBT round-trips operation and tank fields");
    }

    public static void main(String[] args) {
        pressCases();
        blastCases();
        inventoryCases();
        System.out.println("Goal 2 isolated machine regression: " + checks + " checks passed");
    }
}
