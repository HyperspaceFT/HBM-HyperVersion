package com.hbm.blockentity.machine;

import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.BlastFurnaceRecipe;
import com.hbm.inventory.recipes.BlastFurnaceRecipes;
import com.hbm.inventory.recipes.PressRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.RawIngotItem;
import com.hbm.items.machine.StampItem;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

public class Goal3aRegression {
    private static int checks;
    private static final BlockPos POS = new BlockPos(0, 64, 0);
    private static final BlockState STATE = new BlockState();

    private static void check(boolean result, String message) {
        checks++;
        if (!result) throw new AssertionError(message);
    }

    private static MachinePressBlockEntity press() {
        var machine = new MachinePressBlockEntity(POS, STATE);
        machine.level = new Level();
        return machine;
    }

    private static MachineBlastFurnaceBlockEntity blast() {
        var machine = new MachineBlastFurnaceBlockEntity(POS, STATE);
        machine.level = new Level();
        return machine;
    }

    private static void wire(ItemStack ingredient, ItemStack result) {
        var plate = new ItemStack(new StampItem("plate", "plate", 32));
        var wire = new ItemStack(new StampItem("wire", "wire", 64));
        check(PressRecipes.getOutput(ingredient, wire).is(result.getItem()), "wire recipe item " + result.getItem().id);
        check(PressRecipes.getOutput(ingredient, wire).getCount() == 8, "wire recipe count " + result.getItem().id);
        check(PressRecipes.getInputCount(ingredient, wire) == 1, "wire consumes one ingot");
        check(!PressRecipes.getOutput(ingredient, plate).is(result.getItem()), "plate stamp cannot make wire");
        var machine = press();
        machine.slots.set(1, wire);
        machine.slots.set(2, ingredient.copy());
        machine.burnTime = 200;
        machine.slots.set(3, new ItemStack(result.getItem(), 56));
        check(machine.canProcess(), "56 wire leaves eight slots");
        machine.slots.set(3, new ItemStack(result.getItem(), 57));
        check(!machine.canProcess(), "57 wire blocks eight output");
        machine.slots.set(3, ItemStack.EMPTY);
        machine.press = 199;
        machine.speed = 400;
        machine.updateEntity();
        check(machine.slots.get(2).isEmpty(), "one input consumed");
        check(machine.slots.get(3).is(result.getItem()) && machine.slots.get(3).getCount() == 8,
                "eight wire produced");
        check(machine.burnTime == 0, "200 stored fuel consumed");
        check(machine.slots.get(1).getDamageValue() == 1, "one stamp durability consumed");
    }

    private static BlastFurnaceRecipe copperRecipe(ItemStack redstone) {
        var recipes = BlastFurnaceRecipes.INSTANCE;
        var recipe = recipes.getRecipe(new ItemStack(Items.COPPER_INGOT), redstone);
        check(recipe != null, "vanilla copper has default red-copper recipe");
        check(recipe.duration == 400, "red-copper duration 400");
        check(BlastFurnaceRecipes.matchesInputs(recipe, new ItemStack(Items.COPPER_INGOT), redstone, false),
                "normal material order matches");
        check(BlastFurnaceRecipes.matchesInputs(recipe, redstone, new ItemStack(Items.COPPER_INGOT), false),
                "swapped material order matches");
        check(!BlastFurnaceRecipes.matchesInputs(recipe, new ItemStack(Items.IRON_INGOT), redstone, false),
                "wrong copper material rejected");
        check(!BlastFurnaceRecipes.matchesInputs(recipe, new ItemStack(Items.COPPER_INGOT),
                new ItemStack(Items.GOLD_INGOT), false), "wrong redstone material rejected");
        check(recipe.outputItem.length == 1 && recipe.outputItem[0].collapse().is(NtmItems.INGOT_RED_COPPER.get())
                && recipe.outputItem[0].collapse().getCount() == 2, "two red copper and no slag output");
        var machine = blast();
        machine.fuel = 800;
        machine.slots.set(1, new ItemStack(Items.COPPER_INGOT));
        machine.slots.set(2, redstone.copy());
        machine.slots.set(3, new ItemStack(NtmItems.INGOT_RED_COPPER.get(), 62));
        machine.updateEntity();
        check(machine.isProgressing, "62 red copper permits two output");
        machine.slots.set(3, new ItemStack(NtmItems.INGOT_RED_COPPER.get(), 63));
        machine.updateEntity();
        check(!machine.isProgressing && machine.progress == 0, "63 red copper blocks output");
        machine.slots.set(3, ItemStack.EMPTY);
        machine.slots.set(1, redstone.copy());
        machine.slots.set(2, new ItemStack(Items.COPPER_INGOT));
        machine.progress = 0.999F;
        machine.updateEntity();
        check(machine.slots.get(1).isEmpty() && machine.slots.get(2).isEmpty(), "swapped inputs consumed");
        check(machine.slots.get(3).getCount() == 2 && machine.slots.get(4).isEmpty(), "two ingots without slag");
        check(machine.fuel == 0, "machine consumes its fixed 800 fuel per red-copper operation");
        machine.updateEntity();
        check(machine.slots.get(3).getCount() == 2, "no repeated output after inputs consumed");
        return recipe;
    }

    public static void main(String[] args) {
        var press = new PressRecipes();
        press.deleteRecipes();
        press.registerDefaults();
        wire(new ItemStack(NtmItems.INGOT_COPPER.get()), new ItemStack(NtmItems.WIRE_COPPER.get()));
        wire(new ItemStack(NtmItems.INGOT_RED_COPPER.get()), new ItemStack(NtmItems.WIRE_RED_COPPER.get()));
        wire(new ItemStack(NtmItems.INGOT_TUNGSTEN.get()), new ItemStack(NtmItems.WIRE_TUNGSTEN.get()));
        for (int uses : new int[] {32, 64}) {
            var worn = press();
            var stamp = new ItemStack(new StampItem("worn_wire_" + uses, "wire", uses));
            stamp.setDamageValue(uses - 1);
            worn.slots.set(1, stamp);
            worn.slots.set(2, new ItemStack(NtmItems.INGOT_COPPER.get()));
            worn.burnTime = 200;
            worn.press = 199;
            worn.speed = 400;
            worn.updateEntity();
            check(worn.slots.get(1).isEmpty(), "wire stamp breaks after final use " + uses);
            check(worn.slots.get(3).getCount() == 8, "final wire stamp use still yields eight " + uses);
        }
        var recipes = BlastFurnaceRecipes.INSTANCE;
        recipes.deleteRecipes();
        recipes.registerDefaults();
        copperRecipe(new ItemStack(Items.REDSTONE));
        copperRecipe(MetaHelper.newStack(NtmItems.INGOT_RAW.get(), 1, RawIngotItem.Type.REDSTONE.meta));
        var ingotRecipe = recipes.getRecipe(new ItemStack(Items.COPPER_INGOT),
                MetaHelper.newStack(NtmItems.INGOT_RAW.get(), 1, RawIngotItem.Type.REDSTONE.meta));
        check(!BlastFurnaceRecipes.matchesInputs(ingotRecipe, new ItemStack(Items.COPPER_INGOT),
                MetaHelper.newStack(NtmItems.INGOT_RAW.get(), 1, RawIngotItem.Type.SLAG.meta), false),
                "raw ingot with slag metadata cannot substitute for redstone ingot");
        System.out.println("Goal 3a production machine/recipe regression: " + checks + " checks passed");
    }
}
