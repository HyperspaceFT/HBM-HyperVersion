package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.items.NtmItems;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

public class RotaryFurnaceRecipes extends SerializableRecipe {

    public static final List<RotaryFurnaceRecipe> recipes = new ArrayList<>();

    /**
     * Original table (RotaryFurnaceRecipes.java:39-54) without the three iron fragment steel rows (no iron bedrock ore fragment item), the titanium
     * row (no titanium tetrachloride fluid) and the weapon steel row (:49), which a later batch owns even though its inputs exist in NEO.
     */
    @Override
    public void registerDefaults() {
        TagStack coke = new TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "gems_coke")), 1);
        TagStack copper = new TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_copper")), 3);

        recipes.add(new RotaryFurnaceRecipe(new MaterialStack(Mats.MAT_STEEL, MaterialShapes.INGOT.q(1)), 100, 100, new ComparableStack(Items.IRON_INGOT), new ComparableStack(Items.COAL)));
        recipes.add(new RotaryFurnaceRecipe(new MaterialStack(Mats.MAT_STEEL, MaterialShapes.INGOT.q(1)), 100, 100, new ComparableStack(Items.IRON_INGOT), coke));

        recipes.add(new RotaryFurnaceRecipe(new MaterialStack(Mats.MAT_DESH, MaterialShapes.INGOT.q(1)), 100, 200, new FluidStack(Fluids.LIGHTOIL, 100), new ComparableStack(NtmItems.POWDER_DESH_READY.get())));

        recipes.add(new RotaryFurnaceRecipe(new MaterialStack(Mats.MAT_GUNMETAL, MaterialShapes.INGOT.q(4)), 200, 100, copper, new ComparableStack(NtmItems.INGOT_ALUMINIUM.get(), 1)));
        recipes.add(new RotaryFurnaceRecipe(new MaterialStack(Mats.MAT_SATURN, MaterialShapes.INGOT.q(2)), 200, 400, new FluidStack(Fluids.REFORMGAS, 250), new ComparableStack(NtmItems.POWDER_DURA_STEEL.get(), 4), new ComparableStack(NtmItems.POWDER_COPPER.get())));
        recipes.add(new RotaryFurnaceRecipe(new MaterialStack(Mats.MAT_SATURN, MaterialShapes.INGOT.q(4)), 200, 300, new FluidStack(Fluids.REFORMGAS, 250), new ComparableStack(NtmItems.POWDER_DURA_STEEL.get(), 4), new ComparableStack(NtmItems.POWDER_COPPER.get()), new ComparableStack(NtmItems.POWDER_BORAX.get())));
        recipes.add(new RotaryFurnaceRecipe(new MaterialStack(Mats.MAT_ALUMINIUM, MaterialShapes.INGOT.q(2)), 100, 400, new FluidStack(Fluids.SODIUM_ALUMINATE, 150)));
        recipes.add(new RotaryFurnaceRecipe(new MaterialStack(Mats.MAT_ALUMINIUM, MaterialShapes.INGOT.q(3)), 40, 200, new FluidStack(Fluids.SODIUM_ALUMINATE, 150), new ComparableStack(NtmItems.POWDER_FLUX.get(), 2)));
    }

    public static RotaryFurnaceRecipe getRecipe(FluidType fluid, ItemStack... inputs) {

        outer:
        for(RotaryFurnaceRecipe recipe : recipes) {

            // never try to match if a fluid is required and our tank doesn't match it
            if(recipe.fluid != null && recipe.fluid.type != fluid) continue;

            List<AStack> recipeList = new ArrayList<>(List.of(recipe.ingredients));

            for(ItemStack inputStack : inputs) {

                if(!inputStack.isEmpty()) {

                    boolean hasMatch = false;
                    Iterator<AStack> iterator = recipeList.iterator();

                    while(iterator.hasNext()) {
                        AStack recipeStack = iterator.next();

                        if(recipeStack.matchesRecipe(inputStack, true) && inputStack.getCount() >= recipeStack.stacksize) {
                            hasMatch = true;
                            iterator.remove();
                            break;
                        }
                    }

                    if(!hasMatch) {
                        continue outer;
                    }
                }
            }

            if(recipeList.isEmpty()) return recipe;
        }

        return null;
    }

    @Override public String getFileName() { return "hbmRotaryFurnace.json"; }
    @Override public Object getRecipeObject() { return recipes; }
    @Override public void deleteRecipes() { recipes.clear(); }

    @Override
    public void readRecipe(JsonElement recipe) {
        JsonObject obj = recipe.getAsJsonObject();

        AStack[] inputs = readAStackArray(obj.get("inputs").getAsJsonArray());
        FluidStack fluid = obj.has("fluid") ? readFluidStack(obj.get("fluid").getAsJsonArray()) : null;

        JsonArray array = obj.get("output").getAsJsonArray();
        MaterialStack stack = new MaterialStack(Mats.matByName.get(array.get(0).getAsString()), array.get(1).getAsInt());
        if(stack.material == null) throw new IllegalArgumentException("unknown material " + array.get(0).getAsString());

        int duration = obj.get("duration").getAsInt();
        int steam = obj.get("steam").getAsInt();

        recipes.add(new RotaryFurnaceRecipe(stack, duration, steam, fluid, inputs));
    }

    @Override
    public void writeRecipe(Object obj, JsonWriter writer) throws IOException {
        RotaryFurnaceRecipe recipe = (RotaryFurnaceRecipe) obj;

        writer.name("inputs").beginArray();
        for(AStack aStack : recipe.ingredients) {
            writeAStack(aStack, writer);
        }
        writer.endArray();

        if(recipe.fluid != null) {
            writer.name("fluid");
            writeFluidStack(recipe.fluid, writer);
        }

        writer.name("output").beginArray();
        writer.setIndent("");
        writer.value(recipe.output.material.names[0]).value(recipe.output.amount);
        writer.endArray();
        writer.setIndent("  ");

        writer.name("duration").value(recipe.duration);
        writer.name("steam").value(recipe.steam);
    }

    public static class RotaryFurnaceRecipe {

        public final AStack[] ingredients;
        public final FluidStack fluid;
        public final MaterialStack output;
        public final int duration;
        public final int steam;

        public RotaryFurnaceRecipe(MaterialStack output, int duration, int steam, FluidStack fluid, AStack... ingredients) {
            this.ingredients = ingredients;
            this.fluid = fluid;
            this.output = output;
            this.duration = duration;
            this.steam = steam;
        }

        public RotaryFurnaceRecipe(MaterialStack output, int duration, int steam, AStack... ingredients) {
            this(output, duration, steam, null, ingredients);
        }
    }
}
