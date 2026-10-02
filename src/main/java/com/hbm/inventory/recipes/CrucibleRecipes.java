package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.ItemStack;

import java.io.IOException;

/**
 * Crucible alloying recipes. Goal 10A ports only {@code crucible.hss}; the other upstream recipes need
 * materials NEO has not registered yet. The JSON format matches upstream's hbmCrucible.json.
 */
public class CrucibleRecipes extends GenericRecipes<CrucibleRecipe> {

    public static final CrucibleRecipes INSTANCE = new CrucibleRecipes();

    @Override public int inputItemLimit() { return 0; }
    @Override public int inputFluidLimit() { return 0; }
    @Override public int outputItemLimit() { return 0; }
    @Override public int outputFluidLimit() { return 0; }
    @Override public boolean hasDuration() { return false; }
    @Override public boolean hasPower() { return false; }
    @Override public String getFileName() { return "hbmCrucible.json"; }
    @Override public CrucibleRecipe instantiateRecipe(String name) { return new CrucibleRecipe(name); }

    /*
     * IMPORTANT: crucibles do not have stack size checks for the recipe's result, meaning that they can overflow if the resulting stacks are
     * bigger than the input stacks, so make sure that material doesn't "expand". very few things do that IRL when alloying anyway.
     */

    @Override
    public void registerDefaults() {
        if(!this.recipeOrderedList.isEmpty()) return;

        int n = MaterialShapes.NUGGET.q(1);

        this.register(new CrucibleRecipe("crucible.hss").setup(9, new ItemStack(NtmItems.INGOT_DURA_STEEL.get()))
                .inputs(new MaterialStack(Mats.MAT_STEEL, n * 5), new MaterialStack(Mats.MAT_TUNGSTEN, n * 3), new MaterialStack(Mats.MAT_COBALT, n * 1))
                .outputs(new MaterialStack(Mats.MAT_DURA, n * 9)));
    }

    @Override
    public String getComment() {
        return "ID must be unique, but not sequential. Order in which the recipes are defined determines the order in which they are displayed in-game. "
                + "Frequency is the amount of ticks between operations, must be at least 1. The names are unlocalized by default, but if they can't be found in "
                + "the lang files the names will be displayed as-is. The icon is what's being displayed when holding shift on the template.";
    }

    @Override
    public void readRecipe(JsonElement recipe) {
        JsonObject obj = (JsonObject) recipe;
        String name = obj.get("name").getAsString();
        int freq = obj.get("frequency").getAsInt();
        ItemStack icon = SerializableRecipe.readItemStack(obj.get("icon").getAsJsonArray());
        MaterialStack[] input = readMaterials(name, obj.get("input").getAsJsonArray());
        MaterialStack[] output = readMaterials(name, obj.get("output").getAsJsonArray());

        // Upstream registers these anyway and fails later in the crucible (division by zero, null materials).
        // NEO skips the entry instead; an upstream hbmCrucible.json names many materials NEO has not registered yet.
        if(input == null || output == null) return;
        if(freq < 1 || input.length == 0 || output.length == 0) {
            NuclearTechMod.LOGGER.warn("Skipping crucible recipe {}: it needs a frequency of at least 1, inputs and outputs", name);
            return;
        }

        this.register(new CrucibleRecipe(name).setup(freq, icon).inputs(input).outputs(output));
    }

    /** Returns null (and logs why) if an entry names an unknown material or a non-positive amount. */
    private static MaterialStack[] readMaterials(String recipe, JsonArray array) {
        MaterialStack[] stacks = new MaterialStack[array.size()];
        for(int i = 0; i < stacks.length; i++) {
            JsonArray entry = array.get(i).getAsJsonArray();
            String matname = entry.get(0).getAsString();
            int amount = entry.get(1).getAsInt();
            NTMMaterial material = Mats.matByName.get(matname);
            if(material == null || amount <= 0) {
                NuclearTechMod.LOGGER.warn("Skipping crucible recipe {}: unknown material or non-positive amount {} x {}", recipe, amount, matname);
                return null;
            }
            stacks[i] = new MaterialStack(material, amount);
        }
        return stacks;
    }

    @Override
    public void writeRecipe(Object recipe, JsonWriter writer) throws IOException {
        CrucibleRecipe rec = (CrucibleRecipe) recipe;
        writer.name("name").value(rec.getInternalName());
        writer.name("frequency").value(rec.frequency);
        writer.name("icon");
        SerializableRecipe.writeItemStack(rec.getIcon(), writer);

        writer.name("input");
        writeMaterials(rec.input, writer);
        writer.name("output");
        writeMaterials(rec.output, writer);
    }

    private static void writeMaterials(MaterialStack[] stacks, JsonWriter writer) throws IOException {
        writer.beginArray();
        for(MaterialStack mat : stacks) {
            writer.beginArray();
            writer.setIndent("");
            writer.value(mat.material.names[0]).value(mat.amount);
            writer.endArray();
            writer.setIndent("  ");
        }
        writer.endArray();
    }
}
