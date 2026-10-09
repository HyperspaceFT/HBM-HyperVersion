package com.hbm.inventory.recipes;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.items.NtmItems;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;

/**
 * Original ArcFurnaceRecipes, solid outputs only (GOAL13B B1/B7). The liquid outputs need materials and a smelting table
 * NEO does not have yet, so a recipe here is an input and the stack it turns into.
 */
public class ArcFurnaceRecipes extends SerializableRecipe {

    /** All recipes in registration order; the first one matching an input wins. */
    public static List<ArcFurnaceRecipe> recipes = new ArrayList<>();
    /* used for the recipe creation process to cache which inputs are already in use to prevent input collisions */
    private static HashSet<ComparableStack> occupiedSolid = new HashSet<>();

    @Override
    public void registerDefaults() {
        // Original ArcFurnaceRecipes.java:53-65. The ore dictionary entries map to the vanilla quartz gem and block (Forge's
        // gemQuartz / blockQuartz) and to the NEO items the original registers under FIBER, ASBESTOS, QUARTZ.dust() and BORAX.dust().
        register(new TagStack(ItemTags.SAND),                               new ItemStack(NtmItems.NUGGET_SILICON.get()));
        register(new ComparableStack(Items.FLINT),                          new ItemStack(NtmItems.NUGGET_SILICON.get(), 4));
        register(new ComparableStack(Items.QUARTZ),                         new ItemStack(NtmItems.NUGGET_SILICON.get(), 3));
        register(new ComparableStack(NtmItems.POWDER_QUARTZ.get()),         new ItemStack(NtmItems.NUGGET_SILICON.get(), 3));
        register(new ComparableStack(Blocks.QUARTZ_BLOCK),                  new ItemStack(NtmItems.NUGGET_SILICON.get(), 12));
        register(new ComparableStack(NtmItems.INGOT_FIBERGLASS.get()),      new ItemStack(NtmItems.NUGGET_SILICON.get(), 4));
        register(new ComparableStack(NtmBlocks.BLOCK_FIBERGLASS.get()),     new ItemStack(NtmItems.NUGGET_SILICON.get(), 40));
        register(new ComparableStack(NtmItems.INGOT_ASBESTOS.get()),        new ItemStack(NtmItems.NUGGET_SILICON.get(), 4));
        register(new ComparableStack(NtmItems.POWDER_ASBESTOS.get()),       new ItemStack(NtmItems.NUGGET_SILICON.get(), 4));
        register(new ComparableStack(NtmBlocks.BLOCK_ASBESTOS.get()),       new ItemStack(NtmItems.NUGGET_SILICON.get(), 40));

        // Deferred (GOAL13B B7): sand_mix -> glass_quartz (:64), NEO has no sand_mix.
        register(new ComparableStack(NtmItems.POWDER_BORAX.get()),          new ItemStack(NtmItems.POWDER_BORON_TINY.get(), 3));

        // Deferred (GOAL13B B7): the bedrock ore grades (:67-83), the liquid-only material autogen (:85-112) and the solid
        // entries generated from furnace recipes (:115-133), which would need the RecipeManager this early.
    }

    /**
     * Registers the recipe unless one of its inputs is already taken, as the original register (:135-150). Tags are not
     * bound yet when the defaults load, so a tag input only reserves the items it resolves to at that point; the lookup
     * still goes by registration order, so an earlier recipe keeps any input it shares with a later tag.
     */
    public static void register(AStack input, ItemStack solid) {
        List<ItemStack> inputs = input.extractForJEI();
        for(ItemStack stack : inputs) {
            if(occupiedSolid.contains(key(stack))) return;
        }
        recipes.add(new ArcFurnaceRecipe(input, solid));
        for(ItemStack stack : inputs) {
            occupiedSolid.add(key(stack));
        }
    }

    private static ComparableStack key(ItemStack stack) {
        ComparableStack compStack = new ComparableStack(stack).makeSingular();
        if(compStack.meta == MetaHelper.WILDCARD_VALUE) compStack.meta = 0;
        return compStack;
    }

    /**
     * The recipe for the given input, or null. Unlike the original there is no lookup cache: tag contents can change
     * on a data pack reload, and the table is short.
     */
    public static ArcFurnaceRecipe getRecipe(ItemStack stack) {
        if(stack == null || stack.isEmpty()) return null;

        for(ArcFurnaceRecipe recipe : recipes) {
            if(recipe.input.matchesRecipe(stack, true)) return recipe;
        }

        return null;
    }

    /** A copy of the solid output for one input item, or an empty stack. */
    public static ItemStack getSolidOutput(ItemStack input) {
        ArcFurnaceRecipe recipe = getRecipe(input);
        return recipe != null ? recipe.solidOutput.copy() : ItemStack.EMPTY;
    }

    @Override
    public String getFileName() {
        return "hbmArcFurnace.json";
    }

    @Override
    public Object getRecipeObject() {
        return recipes;
    }

    @Override
    public void deleteRecipes() {
        occupiedSolid.clear();
        recipes.clear();
    }

    @Override
    public void readRecipe(JsonElement recipe) {
        JsonObject rec = (JsonObject) recipe;

        AStack input = readAStack(rec.get("input").getAsJsonArray());

        // Entries without a solid output are liquid-only in the original and are skipped until the liquid mode exists.
        if(rec.has("solid")) {
            ItemStack solid = readItemStack(rec.get("solid").getAsJsonArray());
            if(!solid.isEmpty()) register(input, solid);
        }
    }

    @Override
    public void writeRecipe(Object recipe, JsonWriter writer) throws IOException {
        ArcFurnaceRecipe rec = (ArcFurnaceRecipe) recipe;

        writer.name("input");
        writeAStack(rec.input, writer);

        writer.name("solid");
        writeItemStack(rec.solidOutput, writer);
    }

    public static class ArcFurnaceRecipe {

        public final AStack input;
        public final ItemStack solidOutput;

        public ArcFurnaceRecipe(AStack input, ItemStack solidOutput) {
            this.input = input;
            this.solidOutput = solidOutput;
        }
    }
}
