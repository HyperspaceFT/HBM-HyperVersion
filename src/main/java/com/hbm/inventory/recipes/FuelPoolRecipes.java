package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.DepletedFuelItem;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.neoforged.neoforge.registries.DeferredItem;

import java.io.IOException;
import java.io.Reader;
import java.io.StringWriter;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Spent fuel pool drum table (original FuelPoolRecipes.java): one input item with an exact META cools down into one output stack
 * while it sits in a submerged waste drum. The default table holds the nine ZIRNOX waste rows (:27-35), hot waste (META 1) to cool
 * waste (META 0). The original plate, PWR and RBMK rows (:36-50) are not ported because NEO has none of those items yet. A custom
 * file replaces the whole table. Lookups match item and META and ignore the stack count and any other component.
 */
public class FuelPoolRecipes extends SerializableRecipe {
    public static final int MAX_SYNC_RECIPES = 4096;
    public static final int MAX_SYNC_BYTES = 256 * 1024;
    private static final List<FuelPoolRecipe> RECIPES = new ArrayList<>();
    private final List<FuelPoolRecipe> table;

    public FuelPoolRecipes() { this(RECIPES); }
    private FuelPoolRecipes(List<FuelPoolRecipe> table) { this.table = table; }

    public static final class FuelPoolRecipe {
        public final Item input;
        /** Exact META of the input; there is no wildcard. */
        public final int inputMeta;
        public final Item outputItem;
        public final int outputCount;
        public final int outputMeta;

        public FuelPoolRecipe(Item input, int inputMeta, Item outputItem, int outputCount, int outputMeta) {
            if(input == null || input == Items.AIR || input == NtmItems.NOTHING.get()) throw invalid("input item must be a real item");
            if(inputMeta < 0 || inputMeta == MetaHelper.WILDCARD_VALUE) throw invalid("input META must be 0.." + (MetaHelper.WILDCARD_VALUE - 1));
            if(outputItem == null || outputItem == Items.AIR || outputItem == NtmItems.NOTHING.get()) throw invalid("output item must be a real item");
            if(outputCount < 1 || outputCount > 64) throw invalid("output count must be 1..64");
            if(outputMeta < 0) throw invalid("output META must be nonnegative");
            this.input = input;
            this.inputMeta = inputMeta;
            this.outputItem = outputItem;
            this.outputCount = outputCount;
            this.outputMeta = outputMeta;
        }

        /** The input as a single stack, for display. */
        public ItemStack input() { return stack(input, 1, inputMeta); }
        public ItemStack output() { return stack(outputItem, outputCount, outputMeta); }

        public boolean matches(ItemStack stack) {
            return stack != null && !stack.isEmpty() && stack.getItem() == input && MetaHelper.getMeta(stack) == inputMeta;
        }

        public String key() { return BuiltInRegistries.ITEM.getKey(input) + ":" + inputMeta; }

        public boolean sameRecipe(FuelPoolRecipe other) {
            return other != null && input == other.input && inputMeta == other.inputMeta && outputItem == other.outputItem
                    && outputCount == other.outputCount && outputMeta == other.outputMeta;
        }
    }

    /** META equal to the item's default (0 for the waste items, absent for plain items) is not written, so outputs stack with ordinary items. */
    private static ItemStack stack(Item item, int count, int meta) {
        ItemStack stack = new ItemStack(item, count);
        if(MetaHelper.getMeta(stack) != meta) MetaHelper.setMeta(stack, meta);
        return stack;
    }

    public static List<FuelPoolRecipe> getJeiRecipes() { return copyRecipes(RECIPES); }
    public static List<FuelPoolRecipe> getDefaultRecipes() {
        List<FuelPoolRecipe> defaults = new ArrayList<>();
        new FuelPoolRecipes(defaults).registerDefaults();
        return copyRecipes(defaults);
    }
    public static List<FuelPoolRecipe> copyRecipes(List<FuelPoolRecipe> source) {
        List<FuelPoolRecipe> result = new ArrayList<>(source.size());
        for(FuelPoolRecipe recipe : source) result.add(new FuelPoolRecipe(recipe.input, recipe.inputMeta, recipe.outputItem, recipe.outputCount, recipe.outputMeta));
        return result;
    }
    public static boolean isKey(ItemStack stack) { return getRecipe(RECIPES, stack) != null; }
    public static ItemStack getOutput(ItemStack stack) { return getOutput(RECIPES, stack); }
    public static boolean isKey(List<FuelPoolRecipe> source, ItemStack stack) { return getRecipe(source, stack) != null; }
    /** A copy of the matching row's output, or null when the stack is no input of the table. */
    public static ItemStack getOutput(List<FuelPoolRecipe> source, ItemStack stack) {
        FuelPoolRecipe recipe = getRecipe(source, stack);
        return recipe == null ? null : recipe.output();
    }
    public static FuelPoolRecipe getRecipe(List<FuelPoolRecipe> source, ItemStack stack) {
        if(stack == null || stack.isEmpty()) return null;
        for(FuelPoolRecipe recipe : source) if(recipe.matches(stack)) return recipe;
        return null;
    }

    private void add(FuelPoolRecipe row) {
        if(table.size() >= MAX_SYNC_RECIPES) throw invalid("too many recipes");
        for(FuelPoolRecipe old : table) {
            if(old.key().equals(row.key())) throw invalid("duplicate input " + row.key());
        }
        table.add(row);
    }
    private void waste(DeferredItem<Item> waste) {
        add(new FuelPoolRecipe(waste.get(), DepletedFuelItem.HOT, waste.get(), 1, DepletedFuelItem.COOL));
    }

    @Override public String getFileName() { return "hbmFuelpool.json"; }
    @Override public Object getRecipeObject() { return table; }
    /** Original registerDefaults (:27-35), in the original order. */
    @Override public void registerDefaults() {
        waste(NtmItems.WASTE_NATURAL_URANIUM);
        waste(NtmItems.WASTE_URANIUM);
        waste(NtmItems.WASTE_THORIUM);
        waste(NtmItems.WASTE_MOX);
        waste(NtmItems.WASTE_PLUTONIUM);
        waste(NtmItems.WASTE_U233);
        waste(NtmItems.WASTE_U235);
        waste(NtmItems.WASTE_SCHRABIDIUM);
        waste(NtmItems.WASTE_ZFB_MOX);
    }
    @Override public void deleteRecipes() { table.clear(); }
    @Override public String getComment() {
        return "Spent fuel pool drum recipes: an item in a waste drum next to water turns into the output after a random time (on average 72000 ticks divided by the number of adjacent water blocks). Replaces the whole table; an empty table makes the drum accept nothing. Each row: input [id, count, META] with count exactly 1 and an exact META (omitted count is 1, omitted META is 0, no wildcard); output [id, count, META] with count 1..64 (omitted count is 1, omitted META is 0). Every input item and META may appear once. The default table holds the nine hot ZIRNOX waste rows (META 1 cools down to META 0); the original plate, PWR fuel and RBMK rod rows are not part of this version because those items do not exist in it.";
    }
    @Override public void readRecipe(JsonElement element) {
        try {
            if(element == null || !element.isJsonObject()) throw invalid("expected recipe object");
            JsonObject row = element.getAsJsonObject();
            JsonArray input = array(row.get("input"), "input");
            JsonArray output = array(row.get("output"), "output");
            if(input.size() < 1 || input.size() > 3) throw invalid("input array needs ID and optional count, META");
            if(output.size() < 1 || output.size() > 3) throw invalid("output array needs ID and optional count, META");
            Item inputItem = item(input.get(0));
            if(input.size() > 1 && integer(input.get(1)) != 1) throw invalid("input count must be 1");
            int inputMeta = input.size() > 2 ? integer(input.get(2)) : 0;
            Item outputItem = item(output.get(0));
            int outputCount = output.size() > 1 ? integer(output.get(1)) : 1;
            int outputMeta = output.size() > 2 ? integer(output.get(2)) : 0;
            add(new FuelPoolRecipe(inputItem, inputMeta, outputItem, outputCount, outputMeta));
        } catch(RuntimeException ex) { throw invalid("recipe " + table.size() + ": " + ex.getMessage()); }
    }
    @Override public void writeRecipe(Object value, JsonWriter writer) throws IOException {
        FuelPoolRecipe row = (FuelPoolRecipe) value;
        writer.name("input").beginArray().value(BuiltInRegistries.ITEM.getKey(row.input).toString()).value(1).value(row.inputMeta).endArray();
        writer.name("output").beginArray().value(BuiltInRegistries.ITEM.getKey(row.outputItem).toString()).value(row.outputCount).value(row.outputMeta).endArray();
    }
    @Override public void readRecipeStream(Reader reader) {
        StringBuilder text = new StringBuilder(); char[] chunk = new char[4096];
        try {
            int count;
            while((count = reader.read(chunk)) != -1) {
                if(text.length() + count > MAX_SYNC_BYTES) throw invalid("configuration exceeds 256 KiB");
                text.append(chunk, 0, count);
            }
        } catch(IOException ex) { throw invalid("cannot read configuration: " + ex.getMessage()); }
        List<FuelPoolRecipe> replacement = readSnapshot(text.toString(), true);
        // A compact file can pass the raw 256 KiB limit while the canonical sync snapshot of its rows would not; the snapshot would
        // then fail to reach the client, which would keep a different table than the server. Reject it here so the defaults load.
        try { encodeSnapshot(writeRows(replacement)); }
        catch(IOException ex) { throw invalid("cannot write the sync snapshot: " + ex.getMessage()); }
        catch(IllegalArgumentException ex) { throw invalid("the canonical sync snapshot of this file exceeds 256 KiB"); }
        table.clear(); table.addAll(replacement);
    }
    public static List<FuelPoolRecipe> readSnapshot(String json) { return readSnapshot(json, false); }
    /** Only the config-file path is lenient (bad rows logged and skipped); sync snapshots and the writeSnapshot self-check stay strict. */
    private static List<FuelPoolRecipe> readSnapshot(String json, boolean lenient) {
        encodeSnapshot(json);
        JsonObject root = gson.fromJson(json, JsonObject.class);
        if(root == null) throw invalid("missing table object");
        JsonArray rows = array(root.get("recipes"), "recipes");
        if(rows.size() > MAX_SYNC_RECIPES) throw invalid("too many recipes");
        List<FuelPoolRecipe> result = new ArrayList<>();
        FuelPoolRecipes handler = new FuelPoolRecipes(result);
        for(int i = 0; i < rows.size(); i++) {
            if(lenient) handler.readRecipeLenient(rows.get(i), i);
            else handler.readRecipe(rows.get(i));
        }
        return result;
    }
    public static String writeSnapshot() throws IOException {
        String result = writeRows(RECIPES); readSnapshot(result); return result;
    }
    private static String writeRows(List<FuelPoolRecipe> rows) throws IOException {
        StringWriter text = new StringWriter(); JsonWriter writer = new JsonWriter(text);
        writer.beginObject().name("recipes").beginArray();
        FuelPoolRecipes handler = new FuelPoolRecipes(rows);
        for(FuelPoolRecipe row : rows) { writer.beginObject(); handler.writeRecipe(row, writer); writer.endObject(); }
        writer.endArray().endObject(); writer.close();
        return text.toString();
    }
    public static byte[] encodeSnapshot(String json) {
        if(json == null || json.length() > MAX_SYNC_BYTES) throw invalid("snapshot exceeds 256 KiB");
        try {
            var bytes = StandardCharsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).encode(CharBuffer.wrap(json));
            if(bytes.remaining() > MAX_SYNC_BYTES) throw invalid("snapshot exceeds 256 KiB");
            byte[] result = new byte[bytes.remaining()]; bytes.get(result); return result;
        } catch(CharacterCodingException ex) { throw invalid("malformed UTF-16 surrogate"); }
    }

    private static Item item(JsonElement value) {
        ResourceLocation id;
        String text = string(value);
        try { id = ResourceLocation.parse(text); }
        catch(RuntimeException ex) { throw invalid("invalid identifier " + text); }
        if(!BuiltInRegistries.ITEM.containsKey(id)) throw invalid("unknown item " + id);
        return BuiltInRegistries.ITEM.get(id);
    }
    private static JsonArray array(JsonElement value, String name) {
        if(value == null || !value.isJsonArray()) throw invalid("expected " + name + " array");
        return value.getAsJsonArray();
    }
    private static String string(JsonElement value) {
        if(value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isString()) throw invalid("expected string");
        return value.getAsString();
    }
    private static int integer(JsonElement value) {
        if(value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isNumber()) throw invalid("expected integer");
        try { return Integer.parseInt(value.getAsString()); }
        catch(NumberFormatException ex) { throw invalid("expected in-range integer"); }
    }
    private static IllegalArgumentException invalid(String message) { return new IllegalArgumentException("Fuel pool: " + message); }
}
