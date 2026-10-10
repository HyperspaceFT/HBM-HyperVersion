package com.hbm.inventory.recipes;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.util.Tuple.Pair;

import java.io.IOException;
import java.io.StringWriter;
import java.util.LinkedHashMap;
import java.util.Map;

public class FractionRecipes extends SerializableRecipe {

    public static final Map<FluidType, Pair<FluidStack, FluidStack>> fractions = new LinkedHashMap<>();
    public static final int MAX_SYNC_RECIPES = 4096;
    private final Map<FluidType, Pair<FluidStack, FluidStack>> table;

    public FractionRecipes() { this(fractions); }
    private FractionRecipes(Map<FluidType, Pair<FluidStack, FluidStack>> table) { this.table = table; }

    @Override
    public void registerDefaults() {
        this.add(Fluids.HEAVYOIL, Fluids.BITUMEN, 30, Fluids.SMEAR, 70);
        this.add(Fluids.HEAVYOIL_VACUUM, Fluids.SMEAR, 40, Fluids.HEATINGOIL_VACUUM, 60);
        this.add(Fluids.SMEAR, Fluids.HEATINGOIL, 60, Fluids.LUBRICANT, 40);
        this.add(Fluids.NAPHTHA, Fluids.HEATINGOIL, 40, Fluids.DIESEL, 60);
        this.add(Fluids.NAPHTHA_DS, Fluids.XYLENE, 60, Fluids.DIESEL_REFORM, 40);
        this.add(Fluids.NAPHTHA_CRACK, Fluids.HEATINGOIL, 30, Fluids.DIESEL_CRACK, 70);
        this.add(Fluids.LIGHTOIL, Fluids.DIESEL, 40, Fluids.KEROSENE, 60);
        this.add(Fluids.LIGHTOIL_DS, Fluids.DIESEL_REFORM, 60, Fluids.KEROSENE_REFORM, 40);
        this.add(Fluids.LIGHTOIL_CRACK, Fluids.KEROSENE, 70, Fluids.PETROLEUM, 30);
        this.add(Fluids.COALOIL, Fluids.COALGAS, 30, Fluids.OIL, 70);
        this.add(Fluids.COALCREOSOTE, Fluids.COALOIL, 10, Fluids.BITUMEN, 90);
        this.add(Fluids.REFORMATE, Fluids.AROMATICS, 40, Fluids.XYLENE, 60);
        this.add(Fluids.LIGHTOIL_VACUUM, Fluids.KEROSENE, 70, Fluids.REFORMGAS, 30);
        this.add(Fluids.EGG, Fluids.CHOLESTEROL, 50, Fluids.RADIOSOLVENT, 50);
        this.add(Fluids.OIL_COKER, Fluids.CRACKOIL, 30, Fluids.HEATINGOIL, 70);
        this.add(Fluids.NAPHTHA_COKER, Fluids.NAPHTHA_CRACK, 75, Fluids.LIGHTOIL_CRACK, 25);
        this.add(Fluids.GAS_COKER, Fluids.AROMATICS, 25, Fluids.CARBONDIOXIDE, 75);
        this.add(Fluids.CHLOROCALCITE_MIX, Fluids.CHLOROCALCITE_CLEANED, 50, Fluids.COLLOID, 50);
        this.add(Fluids.BAUXITE_SOLUTION, Fluids.REDMUD, 50, Fluids.SODIUM_ALUMINATE, 50);
    }

    private void add(FluidType input, FluidType first, int left, FluidType second, int right) {
        this.table.put(input, new Pair<>(new FluidStack(first, left), new FluidStack(second, right)));
    }

    public static Pair<FluidStack, FluidStack> getFractions(FluidType input) { return fractions.get(input); }
    @Override public String getFileName() { return "hbmFractions.json"; }
    @Override public String getComment() { return "Inputs are always 100mB, set output quantities accordingly."; }
    @Override public Object getRecipeObject() { return this.table; }
    @Override public void deleteRecipes() { this.table.clear(); }

    @Override
    public void readRecipe(JsonElement recipe) {
        JsonObject obj = recipe.getAsJsonObject();
        FluidType input = Fluids.fromName(obj.get("input").getAsString());
        this.table.put(input, new Pair<>(readFluidStack(obj.getAsJsonArray("output1")), readFluidStack(obj.getAsJsonArray("output2"))));
    }

    @Override
    public void writeRecipe(Object recipe, JsonWriter writer) throws IOException {
        @SuppressWarnings("unchecked")
        Map.Entry<FluidType, Pair<FluidStack, FluidStack>> entry = (Map.Entry<FluidType, Pair<FluidStack, FluidStack>>) recipe;
        writer.name("input").value(entry.getKey().getInternalName());
        writer.name("output1"); writeFluidStack(entry.getValue().getKey(), writer);
        writer.name("output2"); writeFluidStack(entry.getValue().getValue(), writer);
    }

    /** Empty authoritative tables are valid snapshots, unlike default template generation. */
    public static String writeSnapshot() throws IOException {
        if(fractions.size() > MAX_SYNC_RECIPES) throw new IllegalArgumentException("Too many fraction recipes");
        StringWriter text = new StringWriter();
        try(JsonWriter writer = new JsonWriter(text)) {
            writer.beginObject().name("recipes").beginArray();
            FractionRecipes handler = new FractionRecipes();
            for(var entry : fractions.entrySet()) {
                writer.beginObject();
                handler.writeRecipe(entry, writer);
                writer.endObject();
            }
            writer.endArray().endObject();
        }
        return text.toString();
    }

    /** Parse into an isolated table so client updates never clear an integrated server's processing recipes. */
    public static Map<FluidType, Pair<FluidStack, FluidStack>> readSnapshot(String text) {
        JsonObject object = gson.fromJson(text, JsonObject.class);
        var recipes = object.getAsJsonArray("recipes");
        if(recipes.size() > MAX_SYNC_RECIPES) throw new IllegalArgumentException("Too many fraction recipes");
        Map<FluidType, Pair<FluidStack, FluidStack>> result = new LinkedHashMap<>();
        FractionRecipes handler = new FractionRecipes(result);
        for(JsonElement recipe : recipes) {
            JsonObject row = recipe.getAsJsonObject();
            if(!row.get("input").getAsJsonPrimitive().isString()) throw new IllegalArgumentException("Invalid fraction input");
            validateFluidArray(row.getAsJsonArray("output1"));
            validateFluidArray(row.getAsJsonArray("output2"));
            handler.readRecipe(recipe);
        }
        return result;
    }

    private static void validateFluidArray(com.google.gson.JsonArray array) {
        if(array.size() < 2 || array.size() > 3 || !array.get(0).getAsJsonPrimitive().isString()
                || !array.get(1).getAsJsonPrimitive().isNumber()
                || (array.size() == 3 && !array.get(2).getAsJsonPrimitive().isNumber())) {
            throw new IllegalArgumentException("Invalid fraction output array");
        }
        // Validate conversion before the common reader's permissive fallback can mask malformed snapshot data.
        Integer.parseInt(array.get(1).getAsString());
        if(array.size() == 3) Integer.parseInt(array.get(2).getAsString());
    }
}
