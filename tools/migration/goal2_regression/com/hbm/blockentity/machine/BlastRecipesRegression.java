package com.hbm.blockentity.machine;

import com.hbm.inventory.recipes.BlastFurnaceRecipes;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;

public class BlastRecipesRegression {
    private static int checks;
    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        var recipes = BlastFurnaceRecipes.INSTANCE;
        recipes.deleteRecipes();
        check(recipes.recipeOrderedList.isEmpty(), "fixture starts with no registered recipes");
        check(recipes.getRecipe(new ItemStack(Items.IRON_INGOT, 2), new ItemStack(Blocks.SAND)) == null,
                "empty registry cannot return fallback recipe");
        check(!recipes.isItemValid(new ItemStack(Items.IRON_INGOT)), "empty registry rejects formerly valid ingredient");

        recipes.registerDefaults();
        check(recipes.recipeOrderedList.size() == 24, "24 production blast defaults registered");
        check(recipes.getRecipe(new ItemStack(Items.IRON_INGOT, 2), new ItemStack(Blocks.SAND)) != null,
                "iron and sand default matches");
        check(recipes.getRecipe(new ItemStack(Items.IRON_INGOT, 2), new ItemStack(Blocks.RED_SAND)) != null,
                "iron and red sand alternative matches");
        check(recipes.getRecipe(new ItemStack(Blocks.IRON_ORE), new ItemStack(Blocks.RED_SAND)) != null,
                "ore and red sand alternative matches");
        check(recipes.getRecipe(new ItemStack(Blocks.DEEPSLATE_IRON_ORE), new ItemStack(Blocks.SAND)) != null,
                "deepslate ore alternative matches");
        check(recipes.getRecipe(new ItemStack(Blocks.DEEPSLATE_IRON_ORE), new ItemStack(Blocks.RED_SAND)) != null,
                "deepslate ore and red sand alternative matches");
        check(recipes.getRecipe(new ItemStack(Blocks.RED_SAND), new ItemStack(Items.IRON_INGOT, 2)) != null,
                "reversed ingredient order selects recipe");
        check(recipes.getRecipe(new ItemStack(Items.IRON_INGOT), new ItemStack(Blocks.SAND)) != null,
                "recipe candidate lookup ignores counts before machine acceptance");
        var recipe = recipes.getRecipe(new ItemStack(Items.IRON_INGOT), new ItemStack(Blocks.SAND));
        check(!BlastFurnaceRecipes.matchesInputs(recipe, new ItemStack(Items.IRON_INGOT), new ItemStack(Blocks.SAND), false),
                "machine count check rejects one iron");
        check(BlastFurnaceRecipes.matchesInputs(recipe, new ItemStack(Items.IRON_INGOT, 2), new ItemStack(Blocks.SAND), false),
                "machine count check accepts two iron");
        check(BlastFurnaceRecipes.matchesInputs(recipe, new ItemStack(Blocks.SAND), new ItemStack(Items.IRON_INGOT, 2), false),
                "machine count check accepts reversed order");
        check(recipes.isItemValid(new ItemStack(Blocks.RED_SAND)), "registered red sand is valid input");
        recipes.registerDefaults();
        check(recipes.recipeOrderedList.size() == 24, "repeated default registration does not duplicate recipes");

        recipes.deleteRecipes();
        check(recipes.recipeOrderedList.isEmpty(), "delete clears default registry");
        check(recipes.getRecipe(new ItemStack(Items.IRON_INGOT, 2), new ItemStack(Blocks.SAND)) == null,
                "deleted registry has no recipe fallback");
        check(!recipes.isItemValid(new ItemStack(Blocks.RED_SAND)), "deleted registry has no valid red sand input");
        System.out.println("Goal 2 isolated production BlastFurnaceRecipes regression: " + checks + " checks passed");
    }
}
