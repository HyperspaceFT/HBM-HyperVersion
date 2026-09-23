package com.hbm.blockentity.machine;

import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.recipes.PressRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.StampItem;
import com.hbm.items.machine.StampItem.StampType;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

public class PressRecipesRegression {
    private static int checks;
    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        var recipes = new PressRecipes();
        recipes.deleteRecipes();
        var plate = new ItemStack(new StampItem("plate", "plate", 32));
        var wire = new ItemStack(new StampItem("wire", "wire", 64));
        check(PressRecipes.getOutput(new ItemStack(Items.IRON_INGOT), plate).isEmpty(), "empty recipe map yields no output");
        recipes.registerDefaults();
        check(PressRecipes.getOutput(new ItemStack(Items.IRON_INGOT), plate).is(NtmItems.PLATE_IRON.get()), "default iron plate");
        check(PressRecipes.getOutput(new ItemStack(Items.COPPER_INGOT), plate).is(NtmItems.PLATE_COPPER.get()), "vanilla copper plate");
        check(PressRecipes.getOutput(new ItemStack(NtmItems.INGOT_COPPER.get()), plate).is(NtmItems.PLATE_COPPER.get()), "NEO copper plate");
        check(PressRecipes.getOutput(new ItemStack(NtmItems.INGOT_STEEL.get()), plate).is(NtmItems.PLATE_STEEL.get()), "steel plate");
        check(PressRecipes.getOutput(new ItemStack(Items.IRON_INGOT), wire).isEmpty(), "wrong stamp has no recipe");
        check(PressRecipes.getInputCount(new ItemStack(Items.IRON_INGOT), plate) == 1, "default recipe consumes one");

        Item custom = new Item("custom");
        Item result = new Item("custom_result");
        PressRecipes.makeRecipe(StampType.PLATE, new ComparableStack(custom, 3), new ItemStack(result, 2));
        check(PressRecipes.getOutput(new ItemStack(custom, 2), plate).isEmpty(), "below configured count has no output");
        check(PressRecipes.getInputCount(new ItemStack(custom, 2), plate) == 0, "below configured count consumes zero");
        check(PressRecipes.getOutput(new ItemStack(custom, 3), plate).getCount() == 2, "configured count yields recipe output");
        check(PressRecipes.getInputCount(new ItemStack(custom, 3), plate) == 3, "configured input count is returned");
        recipes.deleteRecipes();
        check(PressRecipes.getOutput(new ItemStack(custom, 3), plate).isEmpty(), "deletion removes custom recipe");
        System.out.println("Goal 2 isolated production PressRecipes regression: " + checks + " checks passed");
    }
}
