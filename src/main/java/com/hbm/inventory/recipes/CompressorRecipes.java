package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.loader.SerializableRecipe;

import java.io.IOException;
import java.io.Reader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

public class CompressorRecipes extends SerializableRecipe {

    public static final int MAX_SYNC_RECIPES = 4096;
    public static final int MAX_SYNC_BYTES = 256 * 1024;
    public static final Map<RecipeKey, CompressorRecipe> recipes = new LinkedHashMap<>();
    private final Map<RecipeKey, CompressorRecipe> table;

    public CompressorRecipes() { this(recipes); }
    private CompressorRecipes(Map<RecipeKey, CompressorRecipe> table) { this.table = table; }

    public record RecipeKey(FluidType inputType, int inputPressure) {
        public RecipeKey {
            validateType(inputType);
            if(inputPressure < 0 || inputPressure > 4) throw new IllegalArgumentException("Compressor input pressure must be 0..4");
        }
    }

    public record CompressorRecipe(int inputAmount, FluidType outputType, int outputAmount, int outputPressure, int duration) {
        public CompressorRecipe {
            validateType(outputType);
            if(inputAmount <= 0 || outputAmount < 0 || duration <= 0) throw new IllegalArgumentException("Invalid compressor amount or duration");
            if(outputPressure < 0 || outputPressure > 5) throw new IllegalArgumentException("Compressor output pressure must be 0..5");
        }
    }

    /** Only special recipes are stored here; absent entries use the machine's generic compression rule. */
    public static CompressorRecipe getRecipe(FluidType input, int pressure) {
        if(input == null || input == Fluids.NONE || pressure < 0 || pressure > 4) return null;
        return recipes.get(new RecipeKey(input, pressure));
    }

    /** Local display defaults are created independently of an integrated server's authoritative table. */
    public static Map<RecipeKey, CompressorRecipe> getDefaultRecipes() {
        Map<RecipeKey, CompressorRecipe> defaults = new LinkedHashMap<>();
        new CompressorRecipes(defaults).registerDefaults();
        return Collections.unmodifiableMap(defaults);
    }

    @Override
    public void registerDefaults() {
        this.add(Fluids.PETROLEUM, 0, 2000, Fluids.PETROLEUM, 2000, 1, 20);
        this.add(Fluids.PETROLEUM, 1, 2000, Fluids.LPG, 1000, 0, 20);
        this.add(Fluids.BLOOD, 3, 1000, Fluids.HEAVYOIL, 250, 0, 200);
        this.add(Fluids.PERFLUOROMETHYL, 0, 1000, Fluids.PERFLUOROMETHYL, 1000, 1, 50);
        this.add(Fluids.PERFLUOROMETHYL, 1, 1000, Fluids.PERFLUOROMETHYL_COLD, 1000, 0, 50);
    }

    private void add(FluidType input, int pressure, int amount, FluidType output, int outputAmount, int outputPressure, int duration) {
        RecipeKey key = new RecipeKey(input, pressure);
        if(this.table.containsKey(key)) throw new IllegalArgumentException("Duplicate compressor input: " + input.getInternalName() + " at " + pressure);
        if(this.table.size() >= MAX_SYNC_RECIPES) throw new IllegalArgumentException("Too many compressor recipes");
        this.table.put(key, new CompressorRecipe(amount, output, outputAmount, outputPressure, duration));
    }

    @Override public String getFileName() { return "hbmCompressor.json"; }
    @Override public String getComment() { return "Special recipes replace the default table. Missing duration means 100 ticks; generic compression remains available."; }
    @Override public Object getRecipeObject() { return this.table; }
    @Override public void deleteRecipes() { this.table.clear(); }

    @Override
    public void readRecipe(JsonElement recipe) {
        JsonObject row = recipe.getAsJsonObject();
        FluidStack input = readStrictFluid(row.get("input"), 4);
        FluidStack output = readStrictFluid(row.get("output"), 5);
        int duration = row.has("duration") ? readInteger(row.get("duration")) : 100;
        this.add(input.type, input.pressure, input.fill, output.type, output.fill, output.pressure, duration);
    }

    @Override
    public void writeRecipe(Object recipe, JsonWriter writer) throws IOException {
        @SuppressWarnings("unchecked")
        Map.Entry<RecipeKey, CompressorRecipe> entry = (Map.Entry<RecipeKey, CompressorRecipe>) recipe;
        CompressorRecipe value = entry.getValue();
        writer.name("input"); writeFluidStack(new FluidStack(entry.getKey().inputType(), value.inputAmount(), entry.getKey().inputPressure()), writer);
        writer.name("output"); writeFluidStack(new FluidStack(value.outputType(), value.outputAmount(), value.outputPressure()), writer);
        writer.name("duration").value(value.duration());
    }

    /** Validate a whole replacement before publishing it, including enabled empty custom tables. */
    @Override
    public void readRecipeStream(Reader reader) {
        Map<RecipeKey, CompressorRecipe> replacement = parseTable(gson.fromJson(reader, JsonObject.class));
        this.table.clear();
        this.table.putAll(replacement);
    }

    public static String writeSnapshot() throws IOException {
        if(recipes.size() > MAX_SYNC_RECIPES) throw new IllegalArgumentException("Too many compressor recipes");
        StringWriter text = new StringWriter();
        try(JsonWriter writer = new JsonWriter(text)) {
            writer.beginObject().name("recipes").beginArray();
            CompressorRecipes handler = new CompressorRecipes();
            for(var entry : recipes.entrySet()) {
                writer.beginObject();
                handler.writeRecipe(entry, writer);
                writer.endObject();
            }
            writer.endArray().endObject();
        }
        String result = text.toString();
        checkSnapshotSize(result);
        return result;
    }

    public static Map<RecipeKey, CompressorRecipe> readSnapshot(String text) {
        checkSnapshotSize(text);
        return parseTable(gson.fromJson(text, JsonObject.class));
    }

    private static Map<RecipeKey, CompressorRecipe> parseTable(JsonObject object) {
        if(object == null || !object.has("recipes") || !object.get("recipes").isJsonArray()) throw new IllegalArgumentException("Missing compressor recipes array");
        JsonArray rows = object.getAsJsonArray("recipes");
        if(rows.size() > MAX_SYNC_RECIPES) throw new IllegalArgumentException("Too many compressor recipes");
        Map<RecipeKey, CompressorRecipe> result = new LinkedHashMap<>();
        CompressorRecipes handler = new CompressorRecipes(result);
        for(JsonElement row : rows) handler.readRecipe(row);
        return result;
    }

    private static FluidStack readStrictFluid(JsonElement element, int maxPressure) {
        if(element == null || !element.isJsonArray()) throw new IllegalArgumentException("Invalid compressor fluid array");
        JsonArray array = element.getAsJsonArray();
        if(array.size() < 2 || array.size() > 3 || !array.get(0).isJsonPrimitive() || !array.get(0).getAsJsonPrimitive().isString()) throw new IllegalArgumentException("Invalid compressor fluid array");
        FluidType type = Fluids.fromName(array.get(0).getAsString());
        validateType(type);
        int amount = readInteger(array.get(1));
        int pressure = array.size() == 3 ? readInteger(array.get(2)) : 0;
        if(pressure < 0 || pressure > maxPressure) throw new IllegalArgumentException("Invalid compressor fluid pressure");
        return new FluidStack(type, amount, pressure);
    }

    private static int readInteger(JsonElement element) {
        if(element == null || !element.isJsonPrimitive() || !element.getAsJsonPrimitive().isNumber()) throw new IllegalArgumentException("Expected compressor integer");
        return Integer.parseInt(element.getAsString());
    }

    private static void validateType(FluidType type) {
        if(type == null || type == Fluids.NONE || Fluids.fromName(type.getInternalName()) != type) throw new IllegalArgumentException("Unknown or NONE compressor fluid");
    }

    private static void checkSnapshotSize(String text) {
        if(text == null || text.getBytes(StandardCharsets.UTF_8).length > MAX_SYNC_BYTES) throw new IllegalArgumentException("Compressor snapshot exceeds 256 KiB");
    }
}
