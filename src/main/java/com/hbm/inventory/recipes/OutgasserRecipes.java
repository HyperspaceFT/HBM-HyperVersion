package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.items.NtmItems;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ItemLike;

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
 * Irradiation channel table (original OutgasserRecipes.java): one input item (exact item/META or tag) turns into a solid output,
 * a gas output into the channel's 64,000 mB tank, or both, once the RBMK flux has filled the channel's progress. Lookups ignore the
 * stack count and any component but META and try the exact item rows before the tag rows (original getOutput :65-83).
 * The original keys its rows on ore dictionary names (lithium, gold, thorium-232, coal, PVC); NEO's default rows use concrete items
 * instead: its datagen registers item tags only for aluminium, its other tables use concrete items for gold and coal
 * (PressRecipes, BlastFurnaceRecipes, CombinationRecipes) and the NeoForge common tags (c:ingots/gold ...) do not hold NEO's own
 * powders. A custom file may still use tag inputs. The three mushroom rows of the original are not part of this version (NEO has
 * neither the glowing mushroom nor the glowing stew). Rows marked fusionOnly are kept for the original's fusion breeder, which is not
 * ported, and never run in the irradiation channel. A custom file replaces the whole table.
 */
public class OutgasserRecipes extends SerializableRecipe {
    public static final int MAX_SYNC_RECIPES = 4096;
    public static final int MAX_SYNC_BYTES = 256 * 1024;
    /** The channel's tank holds 64,000 mB; a row producing more gas could never run. */
    public static final int MAX_GAS = 64_000;
    private static final List<OutgasserRecipe> RECIPES = new ArrayList<>();
    private final List<OutgasserRecipe> table;

    public OutgasserRecipes() { this(RECIPES); }
    private OutgasserRecipes(List<OutgasserRecipe> table) { this.table = table; }

    public static final class OutgasserRecipe {
        /** Exact item (META 32767 is the wildcard) or item tag; exactly one item is consumed per completed cycle. */
        public final AStack input;
        /** {@link ItemStack#EMPTY} when the row has no solid output. */
        public final ItemStack solidOutput;
        /** Null when the row has no gas output; pressure 0. */
        public final FluidStack fluidOutput;
        public final boolean fusionOnly;

        public OutgasserRecipe(AStack input, ItemStack solidOutput, FluidStack fluidOutput, boolean fusionOnly) {
            if(input == null) throw invalid("missing input");
            if(input.stacksize != 1) throw invalid("input count must be 1");
            if(input instanceof ComparableStack comparable) {
                if(comparable.item == null || comparable.item == Items.AIR || comparable.item == NtmItems.NOTHING.get()) throw invalid("input item must be a real item");
                if(comparable.meta < 0) throw invalid("input META must be nonnegative");
                this.input = new ComparableStack(comparable.item, 1, comparable.meta);
            } else if(input instanceof TagStack tagged) {
                if(tagged.tag == null) throw invalid("missing input tag");
                this.input = new TagStack(tagged.tag, 1);
            } else throw invalid("unsupported input kind");
            if(solidOutput == null || solidOutput.isEmpty()) {
                this.solidOutput = ItemStack.EMPTY;
            } else {
                if(solidOutput.getItem() == NtmItems.NOTHING.get()) throw invalid("solid output must be a real item");
                if(solidOutput.getCount() < 1 || solidOutput.getCount() > 64) throw invalid("solid output count must be 1..64");
                this.solidOutput = solidOutput.copy();
            }
            if(fluidOutput == null) {
                this.fluidOutput = null;
            } else {
                if(fluidOutput.type == null || fluidOutput.type == Fluids.NONE) throw invalid("fluid output needs a fluid type");
                if(fluidOutput.fill < 1 || fluidOutput.fill > MAX_GAS) throw invalid("fluid output amount must be 1.." + MAX_GAS);
                if(fluidOutput.pressure != 0) throw invalid("fluid output pressure must be 0");
                this.fluidOutput = new FluidStack(fluidOutput.type, fluidOutput.fill);
            }
            // The original readRecipe (:127-129) silently drops a row without any output.
            if(this.solidOutput.isEmpty() && this.fluidOutput == null) throw invalid("row needs a solid output, a fluid output or both");
            this.fusionOnly = fusionOnly;
        }

        public boolean hasSolidOutput() { return !solidOutput.isEmpty(); }
        public ItemStack solidOutput() { return solidOutput.copy(); }

        /** Registration key: the input identity (item + META or tag). */
        public String key() {
            if(input instanceof ComparableStack comparable) return "item:" + BuiltInRegistries.ITEM.getKey(comparable.item) + ":" + comparable.meta;
            return "tag:" + ((TagStack) input).tag.location();
        }

        public boolean sameRecipe(OutgasserRecipe other) {
            if(other == null || !key().equals(other.key()) || fusionOnly != other.fusionOnly) return false;
            if(solidOutput.getCount() != other.solidOutput.getCount() || !ItemStack.isSameItemSameComponents(solidOutput, other.solidOutput)) return false;
            if(fluidOutput == null || other.fluidOutput == null) return fluidOutput == other.fluidOutput;
            return fluidOutput.type == other.fluidOutput.type && fluidOutput.fill == other.fluidOutput.fill;
        }
    }

    public static List<OutgasserRecipe> getJeiRecipes() { return copyRecipes(RECIPES); }
    public static List<OutgasserRecipe> getDefaultRecipes() {
        List<OutgasserRecipe> defaults = new ArrayList<>();
        new OutgasserRecipes(defaults).registerDefaults();
        return copyRecipes(defaults);
    }
    public static List<OutgasserRecipe> copyRecipes(List<OutgasserRecipe> source) {
        List<OutgasserRecipe> result = new ArrayList<>(source.size());
        for(OutgasserRecipe recipe : source) result.add(new OutgasserRecipe(recipe.input, recipe.solidOutput, recipe.fluidOutput, recipe.fusionOnly));
        return result;
    }
    public static OutgasserRecipe getOutput(ItemStack stack) { return getOutput(RECIPES, stack); }
    /** The exact item rows first, then the tag rows (original :65-83: the exact stack before the ore dictionary); null if none matches. */
    public static OutgasserRecipe getOutput(List<OutgasserRecipe> source, ItemStack stack) {
        if(stack == null || stack.isEmpty()) return null;
        for(OutgasserRecipe recipe : source) if(recipe.input instanceof ComparableStack && recipe.input.matchesRecipe(stack, true)) return recipe;
        for(OutgasserRecipe recipe : source) if(recipe.input instanceof TagStack && recipe.input.matchesRecipe(stack, true)) return recipe;
        return null;
    }

    private void add(OutgasserRecipe row) {
        if(table.size() >= MAX_SYNC_RECIPES) throw invalid("too many recipes");
        for(OutgasserRecipe old : table) {
            if(old.key().equals(row.key())) throw invalid("duplicate input " + row.key());
        }
        table.add(row);
    }
    private void gas(ItemLike input, FluidType type, int amount) {
        add(new OutgasserRecipe(new ComparableStack(input.asItem(), 1, 0), ItemStack.EMPTY, new FluidStack(type, amount), false));
    }
    private void solid(ItemLike input, ItemLike output) {
        add(new OutgasserRecipe(new ComparableStack(input.asItem(), 1, 0), new ItemStack(output), null, false));
    }
    private void both(ItemLike input, ItemLike output, int count, FluidType type, int amount) {
        add(new OutgasserRecipe(new ComparableStack(input.asItem(), 1, 0), new ItemStack(output, count), new FluidStack(type, amount), false));
    }

    @Override public String getFileName() { return "hbmIrradiation.json"; }
    @Override public Object getRecipeObject() { return table; }
    /** Original registerDefaults (:32-63), in the original order. */
    @Override public void registerDefaults() {
        // Lithium to tritium (:35-38).
        gas(NtmBlocks.BLOCK_LITHIUM, Fluids.TRITIUM, 10_000);
        gas(NtmItems.LITHIUM.get(), Fluids.TRITIUM, 1_000);
        gas(NtmItems.POWDER_LITHIUM.get(), Fluids.TRITIUM, 1_000);
        gas(NtmItems.POWDER_LITHIUM_TINY.get(), Fluids.TRITIUM, 100);
        // Gold to gold-198 (:41-43).
        solid(Items.GOLD_INGOT, NtmItems.INGOT_AU198.get());
        solid(Items.GOLD_NUGGET, NtmItems.NUGGET_AU198.get());
        solid(NtmItems.POWDER_GOLD.get(), NtmItems.POWDER_AU198.get());
        // Thorium-232 to thorium fuel (:46-48).
        solid(NtmItems.INGOT_TH232.get(), NtmItems.INGOT_THORIUM_FUEL.get());
        solid(NtmItems.NUGGET_TH232.get(), NtmItems.NUGGET_THORIUM_FUEL.get());
        solid(NtmItems.BILLET_TH232.get(), NtmItems.BILLET_THORIUM_FUEL.get());
        // The mushroom rows (:51-53) are not ported: NEO has neither the glowing mushroom nor the glowing stew.
        // Coal to coal tar and syngas (:55-57).
        both(Items.COAL, NtmItems.OIL_TAR_COAL.get(), 1, Fluids.SYNGAS, 50);
        both(NtmItems.POWDER_COAL.get(), NtmItems.OIL_TAR_COAL.get(), 1, Fluids.SYNGAS, 50);
        both(Items.COAL_BLOCK, NtmItems.OIL_TAR_COAL.get(), 9, Fluids.SYNGAS, 500);
        // PVC (:59).
        both(NtmItems.INGOT_PVC.get(), NtmItems.INGOT_C4.get(), 1, Fluids.COLLOID, 250);
        // Tar (:61-62).
        gas(NtmItems.OIL_TAR_COAL.get(), Fluids.COALOIL, 100);
        gas(NtmItems.OIL_TAR_WAX.get(), Fluids.RADIOSOLVENT, 100);
    }
    @Override public void deleteRecipes() { table.clear(); }
    @Override public String getComment() {
        return "RBMK irradiation channel recipes: the neutron flux turns one input item into a solid output, a gas into the channel's tank, or both. Replaces the whole table; an empty table makes the channel accept nothing. Each row: input [\"item\", id, count, META] (omitted count is 1, omitted META is 0, META 32767 is a wildcard) or [\"tag\", id, count], count exactly 1; optional solidOutput [id, count, META] with count 1..64 (omitted count is 1, omitted META is 0); optional fluidOutput [internal fluid name, mB] with 1..64000 mB; a row needs at least one of the two outputs; optional fusionOnly true/false (default false). Every input item and META or tag may appear once; exact item rows are matched before tag rows. fusionOnly rows are kept but never run in the irradiation channel (the fusion breeder is not part of this version). The original mushroom rows are not part of this version because those items do not exist in it.";
    }
    @Override public void readRecipe(JsonElement element) {
        try {
            if(element == null || !element.isJsonObject()) throw invalid("expected recipe object");
            JsonObject row = element.getAsJsonObject();
            AStack input = decodeInput(array(row.get("input"), "input"));
            ItemStack solid = row.has("solidOutput") ? decodeItem(array(row.get("solidOutput"), "solidOutput")) : ItemStack.EMPTY;
            FluidStack fluid = row.has("fluidOutput") ? decodeFluid(array(row.get("fluidOutput"), "fluidOutput")) : null;
            boolean fusionOnly = row.has("fusionOnly") && bool(row.get("fusionOnly"));
            add(new OutgasserRecipe(input, solid, fluid, fusionOnly));
        } catch(RuntimeException ex) { throw invalid("recipe " + table.size() + ": " + ex.getMessage()); }
    }
    /** Original writeRecipe (:132-150): input, the outputs that are present, and always fusionOnly. */
    @Override public void writeRecipe(Object value, JsonWriter writer) throws IOException {
        OutgasserRecipe row = (OutgasserRecipe) value;
        writer.name("input"); writeInput(row.input, writer);
        if(row.hasSolidOutput()) { writer.name("solidOutput"); writeItem(row.solidOutput, writer); }
        if(row.fluidOutput != null) {
            writer.name("fluidOutput"); writer.beginArray(); writer.value(row.fluidOutput.type.getInternalName()); writer.value(row.fluidOutput.fill); writer.endArray();
        }
        writer.name("fusionOnly").value(row.fusionOnly);
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
        List<OutgasserRecipe> replacement = readSnapshot(text.toString(), true);
        // A compact file can pass the raw 256 KiB limit while the canonical sync snapshot of its rows would not; the snapshot would
        // then fail to reach the client, which would keep a different table than the server. Reject it here so the defaults load.
        try { encodeSnapshot(writeRows(replacement)); }
        catch(IOException ex) { throw invalid("cannot write the sync snapshot: " + ex.getMessage()); }
        catch(IllegalArgumentException ex) { throw invalid("the canonical sync snapshot of this file exceeds 256 KiB"); }
        table.clear(); table.addAll(replacement);
    }
    public static List<OutgasserRecipe> readSnapshot(String json) { return readSnapshot(json, false); }
    /** Only the config-file path is lenient (bad rows logged and skipped); sync snapshots and the writeSnapshot self-check stay strict. */
    private static List<OutgasserRecipe> readSnapshot(String json, boolean lenient) {
        encodeSnapshot(json);
        JsonObject root = gson.fromJson(json, JsonObject.class);
        if(root == null) throw invalid("missing table object");
        JsonArray rows = array(root.get("recipes"), "recipes");
        if(rows.size() > MAX_SYNC_RECIPES) throw invalid("too many recipes");
        List<OutgasserRecipe> result = new ArrayList<>();
        OutgasserRecipes handler = new OutgasserRecipes(result);
        for(int i = 0; i < rows.size(); i++) {
            if(lenient) handler.readRecipeLenient(rows.get(i), i);
            else handler.readRecipe(rows.get(i));
        }
        return result;
    }
    public static String writeSnapshot() throws IOException {
        String result = writeRows(RECIPES); readSnapshot(result); return result;
    }
    private static String writeRows(List<OutgasserRecipe> rows) throws IOException {
        StringWriter text = new StringWriter(); JsonWriter writer = new JsonWriter(text);
        writer.beginObject().name("recipes").beginArray();
        OutgasserRecipes handler = new OutgasserRecipes(rows);
        for(OutgasserRecipe row : rows) { writer.beginObject(); handler.writeRecipe(row, writer); writer.endObject(); }
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

    /** ["item", id, count?, META?] with omitted META meaning 0, or ["tag", id, count?] (the SerializableRecipe.readAStack format). */
    private static AStack decodeInput(JsonArray values) {
        if(values.size() < 2) throw invalid("input needs a kind and an id");
        String kind = string(values.get(0));
        ResourceLocation id = location(string(values.get(1)));
        if("item".equals(kind)) {
            if(values.size() > 4) throw invalid("item input has at most kind, id, count, META");
            if(!BuiltInRegistries.ITEM.containsKey(id)) throw invalid("unknown item " + id);
            Item item = BuiltInRegistries.ITEM.get(id);
            int count = values.size() > 2 ? integer(values.get(2)) : 1;
            int meta = values.size() > 3 ? integer(values.get(3)) : 0;
            if(meta < 0) throw invalid("input META must be nonnegative");
            return new ComparableStack(item, count, meta);
        }
        if("tag".equals(kind)) {
            if(values.size() > 3) throw invalid("tag input has at most kind, id, count");
            int count = values.size() > 2 ? integer(values.get(2)) : 1;
            return new TagStack(ItemTags.create(id), count);
        }
        throw invalid("input kind must be item or tag");
    }
    /** The SerializableRecipe.writeAStack layout (count and META only when they differ from 1 and 0), without its indent changes. */
    private static void writeInput(AStack input, JsonWriter writer) throws IOException {
        writer.beginArray();
        if(input instanceof ComparableStack comparable) {
            writer.value("item"); writer.value(BuiltInRegistries.ITEM.getKey(comparable.item).toString());
            if(comparable.stacksize != 1 || comparable.meta > 0) writer.value(comparable.stacksize);
            if(comparable.meta > 0) writer.value(comparable.meta);
        } else {
            TagStack tagged = (TagStack) input;
            writer.value("tag"); writer.value(tagged.tag.location().toString());
            if(tagged.stacksize != 1) writer.value(tagged.stacksize);
        }
        writer.endArray();
    }
    /** [id, count?, META?] (the SerializableRecipe.readItemStack format without custom data); omitted count is 1, omitted META is 0. */
    private static ItemStack decodeItem(JsonArray values) {
        if(values.size() < 1 || values.size() > 3) throw invalid("solid output needs ID and optional count, META");
        ResourceLocation id = location(string(values.get(0)));
        if(!BuiltInRegistries.ITEM.containsKey(id)) throw invalid("unknown item " + id);
        Item item = BuiltInRegistries.ITEM.get(id);
        if(item == Items.AIR) throw invalid("solid output cannot be empty");
        int count = values.size() > 1 ? integer(values.get(1)) : 1;
        if(count < 1 || count > 64) throw invalid("solid output count must be 1..64");
        int meta = values.size() > 2 ? integer(values.get(2)) : 0;
        if(meta < 0) throw invalid("solid output META must be nonnegative");
        return stack(item, count, meta);
    }
    private static void writeItem(ItemStack stack, JsonWriter writer) throws IOException {
        int meta = MetaHelper.getMeta(stack);
        writer.beginArray();
        writer.value(BuiltInRegistries.ITEM.getKey(stack.getItem()).toString());
        if(stack.getCount() != 1 || meta != 0) writer.value(stack.getCount());
        if(meta != 0) writer.value(meta);
        writer.endArray();
    }
    /** META equal to the item's default (absent for plain items) is not written, so outputs stack with ordinary items. */
    private static ItemStack stack(Item item, int count, int meta) {
        ItemStack stack = new ItemStack(item, count);
        if(MetaHelper.getMeta(stack) != meta) MetaHelper.setMeta(stack, meta);
        return stack;
    }
    /** [internal fluid name, mB, pressure?] (the SerializableRecipe.writeFluidStack format); the pressure must be 0. */
    private static FluidStack decodeFluid(JsonArray values) {
        if(values.size() < 2 || values.size() > 3) throw invalid("fluid output needs the internal fluid name, an amount and an optional pressure");
        String name = string(values.get(0));
        FluidType type = Fluids.fromName(name);
        if(type == null || type == Fluids.NONE || !name.equals(type.getInternalName())) throw invalid("unknown fluid " + name);
        int pressure = values.size() > 2 ? integer(values.get(2)) : 0;
        return new FluidStack(type, integer(values.get(1)), pressure);
    }
    private static ResourceLocation location(String text) {
        try { return ResourceLocation.parse(text); }
        catch(RuntimeException ex) { throw invalid("invalid identifier " + text); }
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
    private static boolean bool(JsonElement value) {
        if(value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isBoolean()) throw invalid("expected true or false");
        return value.getAsBoolean();
    }
    private static IllegalArgumentException invalid(String message) { return new IllegalArgumentException("Irradiation channel: " + message); }
}
