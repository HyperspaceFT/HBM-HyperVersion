package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.trait.FT_Combustible;
import com.hbm.inventory.fluid.trait.FT_Flammable;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.items.NtmItems;
import com.hbm.util.TagsUtil;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.TagParser;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.io.IOException;
import java.io.Reader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

public class CokerRecipes extends SerializableRecipe {

    public static final int MAX_SYNC_RECIPES = 4096;
    public static final int MAX_SYNC_BYTES = 256 * 1024;
    public static final Map<FluidType, CokerRecipe> recipes = new LinkedHashMap<>();
    private final Map<FluidType, CokerRecipe> table;

    public CokerRecipes() { this(recipes); }
    private CokerRecipes(Map<FluidType, CokerRecipe> table) { this.table = table; }

    /** Copies keep display helpers and callers from mutating the authoritative recipe outputs. */
    public record CokerRecipe(int inputAmount, ItemStack itemOutput, FluidStack byproduct) {
        public CokerRecipe {
            if(inputAmount <= 0) throw new IllegalArgumentException("Coker input amount must be positive");
            if(itemOutput != null && itemOutput != ItemStack.EMPTY && itemOutput.getCount() <= 0) throw new IllegalArgumentException("Coker item amount must be positive");
            itemOutput = itemOutput == null ? ItemStack.EMPTY : itemOutput.copy();
            if(byproduct != null) {
                validateType(byproduct.type);
                if(byproduct.fill <= 0 || byproduct.pressure != 0) throw new IllegalArgumentException("Coker byproduct must be positive at zero pressure");
                byproduct = copyFluid(byproduct);
            }
            if(itemOutput.isEmpty() && byproduct == null) throw new IllegalArgumentException("Coker recipe needs an item or fluid output");
        }
        @Override public ItemStack itemOutput() { return this.itemOutput.copy(); }
        @Override public FluidStack byproduct() { return copyFluid(this.byproduct); }
    }

    public static CokerRecipe getRecipe(FluidType type) { return recipes.get(type); }

    /** Independent defaults never clear an integrated server's table. Traits are read only when requested. */
    public static Map<FluidType, CokerRecipe> getDefaultRecipes() {
        Map<FluidType, CokerRecipe> defaults = new LinkedHashMap<>();
        new CokerRecipes(defaults).registerDefaults();
        return Collections.unmodifiableMap(defaults);
    }

    @Override
    public void registerDefaults() {
        this.registerAuto(Fluids.HEAVYOIL, Fluids.OIL_COKER);
        this.registerAuto(Fluids.HEAVYOIL_VACUUM, Fluids.REFORMATE);
        this.registerAuto(Fluids.COALCREOSOTE, Fluids.NAPHTHA_COKER);
        this.registerAuto(Fluids.SMEAR, Fluids.OIL_COKER);
        this.registerAuto(Fluids.HEATINGOIL, Fluids.OIL_COKER);
        this.registerAuto(Fluids.HEATINGOIL_VACUUM, Fluids.OIL_COKER);
        this.registerAuto(Fluids.RECLAIMED, Fluids.NAPHTHA_COKER);
        this.registerAuto(Fluids.NAPHTHA, Fluids.NAPHTHA_COKER);
        this.registerAuto(Fluids.NAPHTHA_DS, Fluids.NAPHTHA_COKER);
        this.registerAuto(Fluids.NAPHTHA_CRACK, Fluids.NAPHTHA_COKER);
        this.registerAuto(Fluids.DIESEL, Fluids.NAPHTHA_COKER);
        this.registerAuto(Fluids.DIESEL_REFORM, Fluids.NAPHTHA_COKER);
        this.registerAuto(Fluids.DIESEL_CRACK, Fluids.GAS_COKER);
        this.registerAuto(Fluids.DIESEL_CRACK_REFORM, Fluids.GAS_COKER);
        this.registerAuto(Fluids.LIGHTOIL, Fluids.GAS_COKER);
        this.registerAuto(Fluids.LIGHTOIL_DS, Fluids.GAS_COKER);
        this.registerAuto(Fluids.LIGHTOIL_CRACK, Fluids.GAS_COKER);
        this.registerAuto(Fluids.LIGHTOIL_VACUUM, Fluids.GAS_COKER);
        this.registerAuto(Fluids.BIOFUEL, Fluids.GAS_COKER);
        this.registerAuto(Fluids.AROMATICS, Fluids.GAS_COKER);
        this.registerAuto(Fluids.REFORMATE, Fluids.GAS_COKER);
        this.registerAuto(Fluids.XYLENE, Fluids.GAS_COKER);
        this.registerAuto(Fluids.FISHOIL, Fluids.MERCURY);
        this.registerAuto(Fluids.SUNFLOWEROIL, Fluids.GAS_COKER);
        this.registerAuto(Fluids.WOODOIL, 340_000L, new ItemStack(Items.CHARCOAL), Fluids.GAS_COKER);

        this.add(Fluids.WATZ, 4000, new ItemStack(NtmItems.INGOT_MUD.get(), 4), null);
        this.add(Fluids.REDMUD, 450, new ItemStack(Items.IRON_INGOT), new FluidStack(Fluids.MERCURY, 50));
        this.add(Fluids.BITUMEN, 16_000, new ItemStack(NtmItems.COKE_PETROLEUM.get()), new FluidStack(Fluids.OIL_COKER, 1600));
        this.add(Fluids.LUBRICANT, 12_000, new ItemStack(NtmItems.COKE_PETROLEUM.get()), new FluidStack(Fluids.OIL_COKER, 1200));
        this.add(Fluids.CALCIUM_SOLUTION, 125, new ItemStack(NtmItems.POWDER_CALCIUM.get()), new FluidStack(Fluids.SPENTSTEAM, 100));
        // Only cokable gas to extract sulfur content, as upstream.
        this.add(Fluids.SOURGAS, 1000, new ItemStack(NtmItems.SULFUR.get()), new FluidStack(Fluids.GAS_COKER, 150));
        this.add(Fluids.SLOP, 1000, new ItemStack(NtmItems.POWDER_LIMESTONE.get()), new FluidStack(Fluids.COLLOID, 250));
        this.add(Fluids.VITRIOL, 4000, new ItemStack(NtmItems.POWDER_IRON.get()), new FluidStack(Fluids.SULFURIC_ACID, 500));
    }

    private void registerAuto(FluidType input, FluidType byproduct) {
        // 3200 burntime * 1.25 bonus * 200 TU/t, plus 20000 TU per operation; penalty is one.
        this.registerAuto(input, 820_000L, new ItemStack(NtmItems.COKE_PETROLEUM.get()), byproduct);
    }

    private void registerAuto(FluidType input, long tuPerSF, ItemStack output, FluidType byproduct) {
        long flammable = input.hasTrait(FT_Flammable.class) ? input.getTrait(FT_Flammable.class).getHeatEnergy() : 0;
        long combustible = input.hasTrait(FT_Combustible.class) ? input.getTrait(FT_Combustible.class).getCombustionEnergy() : 0;
        final int amount;
        try { amount = calculateAutoAmount(tuPerSF, Math.max(flammable, combustible)); }
        catch(IllegalArgumentException ex) { throw new IllegalArgumentException("Invalid coker fuel traits for " + input.getInternalName(), ex); }
        this.add(input, amount, output, new FluidStack(byproduct, Math.max(10, amount / 10)));
    }

    public static int calculateAutoAmount(long tuPerSF, long tuPerBucket) {
        if(tuPerSF <= 0 || tuPerBucket <= 0) throw new IllegalArgumentException("Coker fuel energy must be positive");
        final long raw;
        try { raw = Math.multiplyExact(tuPerSF, 1000L) / tuPerBucket; }
        catch(ArithmeticException ex) { throw new IllegalArgumentException("Coker fuel calculation overflow", ex); }
        if(raw <= 0 || raw > Integer.MAX_VALUE) throw new IllegalArgumentException("Coker fuel amount is outside positive integer range");
        int amount = (int) raw;
        if(amount > 10_000) amount -= amount % 1000;
        else if(amount > 1000) amount -= amount % 100;
        else if(amount > 100) amount -= amount % 10;
        return amount;
    }

    private void add(FluidType input, int amount, ItemStack output, FluidStack byproduct) {
        validateType(input);
        if(this.table.containsKey(input)) throw new IllegalArgumentException("Duplicate coker input: " + input.getInternalName());
        if(this.table.size() >= MAX_SYNC_RECIPES) throw new IllegalArgumentException("Too many coker recipes");
        this.table.put(input, new CokerRecipe(amount, output, byproduct));
    }

    @Override public String getFileName() { return "hbmCoker.json"; }
    @Override public String getComment() { return "Replaces the whole default table, including an empty table. Inputs and byproducts use zero pressure. Output arrays support item ID, positive count, META and optional custom-data SNBT. Progress consumes heat, not a fixed duration; changing byproduct type clears its tank before input/capacity checks."; }
    @Override public Object getRecipeObject() { return this.table; }
    @Override public void deleteRecipes() { this.table.clear(); }

    @Override
    public void readRecipe(JsonElement recipe) {
        if(recipe == null || !recipe.isJsonObject()) throw new IllegalArgumentException("Invalid coker recipe object");
        JsonObject row = recipe.getAsJsonObject();
        FluidStack input = readStrictFluid(row.get("input"));
        ItemStack output = row.has("output") ? readStrictItem(row.get("output")) : ItemStack.EMPTY;
        FluidStack byproduct = row.has("byproduct") ? readStrictFluid(row.get("byproduct")) : null;
        this.add(input.type, input.fill, output, byproduct);
    }

    @Override
    public void writeRecipe(Object recipe, JsonWriter writer) throws IOException {
        @SuppressWarnings("unchecked") Map.Entry<FluidType, CokerRecipe> entry = (Map.Entry<FluidType, CokerRecipe>) recipe;
        validateType(entry.getKey());
        CokerRecipe value = entry.getValue();
        writer.name("input"); writeFluidStack(new FluidStack(entry.getKey(), value.inputAmount()), writer);
        ItemStack output = value.itemOutput();
        if(!output.isEmpty()) { writer.name("output"); writeStrictItem(output, writer); }
        FluidStack byproduct = value.byproduct();
        if(byproduct != null) { writer.name("byproduct"); writeFluidStack(byproduct, writer); }
    }

    /** Stage the whole custom replacement, so an invalid later row cannot publish an earlier row. */
    @Override
    public void readRecipeStream(Reader reader) {
        Map<FluidType, CokerRecipe> replacement = parseTable(gson.fromJson(reader, JsonObject.class));
        this.table.clear();
        this.table.putAll(replacement);
    }

    public static String writeSnapshot() throws IOException {
        if(recipes.size() > MAX_SYNC_RECIPES) throw new IllegalArgumentException("Too many coker recipes");
        StringWriter text = new StringWriter();
        try(JsonWriter writer = new JsonWriter(text)) {
            writer.beginObject().name("recipes").beginArray();
            CokerRecipes handler = new CokerRecipes();
            for(var entry : recipes.entrySet()) {
                writer.beginObject(); handler.writeRecipe(entry, writer); writer.endObject();
            }
            writer.endArray().endObject();
        }
        String result = text.toString();
        checkSnapshotSize(result);
        return result;
    }

    public static Map<FluidType, CokerRecipe> readSnapshot(String text) {
        checkSnapshotSize(text);
        return parseTable(gson.fromJson(text, JsonObject.class));
    }

    private static Map<FluidType, CokerRecipe> parseTable(JsonObject object) {
        if(object == null || !object.has("recipes") || !object.get("recipes").isJsonArray()) throw new IllegalArgumentException("Missing coker recipes array");
        JsonArray rows = object.getAsJsonArray("recipes");
        if(rows.size() > MAX_SYNC_RECIPES) throw new IllegalArgumentException("Too many coker recipes");
        Map<FluidType, CokerRecipe> replacement = new LinkedHashMap<>();
        CokerRecipes handler = new CokerRecipes(replacement);
        for(JsonElement row : rows) handler.readRecipe(row);
        return replacement;
    }

    private static FluidStack readStrictFluid(JsonElement element) {
        if(element == null || !element.isJsonArray()) throw new IllegalArgumentException("Invalid coker fluid array");
        JsonArray array = element.getAsJsonArray();
        if(array.size() < 2 || array.size() > 3) throw new IllegalArgumentException("Invalid coker fluid array size");
        FluidType type = Fluids.fromName(readString(array.get(0)));
        validateType(type);
        int amount = readInteger(array.get(1));
        int pressure = array.size() == 3 ? readInteger(array.get(2)) : 0;
        if(amount <= 0 || pressure != 0) throw new IllegalArgumentException("Coker fluid amount must be positive; recipe pressure must be zero");
        return new FluidStack(type, amount);
    }

    private static ItemStack readStrictItem(JsonElement element) {
        if(element == null || !element.isJsonArray()) throw new IllegalArgumentException("Invalid coker item array");
        JsonArray array = element.getAsJsonArray();
        if(array.size() < 1 || array.size() > 4) throw new IllegalArgumentException("Invalid coker item array size");
        ResourceLocation id = ResourceLocation.parse(readString(array.get(0)));
        if(!BuiltInRegistries.ITEM.containsKey(id)) throw new IllegalArgumentException("Unknown coker output item: " + id);
        Item item = BuiltInRegistries.ITEM.get(id);
        int count = array.size() > 1 ? readInteger(array.get(1)) : 1;
        int meta = array.size() > 2 ? readInteger(array.get(2)) : 0;
        if(item == Items.AIR || count <= 0 || meta < 0) throw new IllegalArgumentException("Invalid coker item identity, amount or META");
        ItemStack stack = new ItemStack(item, count);
        // Do not add an absent zero META to vanilla/default outputs: component equality controls stacking.
        if(array.size() > 2) MetaHelper.setMeta(stack, meta);
        if(array.size() > 3) {
            try { TagsUtil.putCustomData(stack, TagParser.parseTag(readString(array.get(3)))); }
            catch(Exception ex) { throw new IllegalArgumentException("Invalid coker output custom-data SNBT", ex); }
        }
        return stack;
    }

    private static void writeStrictItem(ItemStack output, JsonWriter writer) throws IOException {
        JsonArray array = new JsonArray();
        array.add(BuiltInRegistries.ITEM.getKey(output.getItem()).toString());
        // Explicit zero META is significant, and must survive the format's round trip.
        boolean meta = output.has(com.hbm.items.component.NtmDataComponents.META.get());
        boolean custom = TagsUtil.hasCustomData(output);
        if(output.getCount() != 1 || meta || custom) array.add(output.getCount());
        if(meta || custom) array.add(MetaHelper.getMeta(output));
        if(custom) array.add(TagsUtil.getCustomData(output).toString());
        ItemStack rebuilt = readStrictItem(array);
        if(!ItemStack.isSameItemSameComponents(output, rebuilt)) throw new IllegalArgumentException("Coker item array cannot represent output components: " + array.get(0));
        // Reject unrepresentable patches rather than silently adding/removing components during synchronization.
        writer.beginArray();
        writer.setIndent("");
        for(JsonElement value : array) {
            if(value.getAsJsonPrimitive().isNumber()) writer.value(value.getAsNumber());
            else writer.value(value.getAsString());
        }
        writer.endArray();
        writer.setIndent("  ");
    }

    private static String readString(JsonElement element) {
        if(element == null || !element.isJsonPrimitive() || !element.getAsJsonPrimitive().isString()) throw new IllegalArgumentException("Expected coker string");
        return element.getAsString();
    }

    private static int readInteger(JsonElement element) {
        if(element == null || !element.isJsonPrimitive() || !element.getAsJsonPrimitive().isNumber()) throw new IllegalArgumentException("Expected coker integer");
        try { return Integer.parseInt(element.getAsString()); }
        catch(NumberFormatException ex) { throw new IllegalArgumentException("Expected in-range coker integer", ex); }
    }

    private static void validateType(FluidType type) {
        if(type == null || type == Fluids.NONE || Fluids.fromName(type.getInternalName()) != type) throw new IllegalArgumentException("Unknown or NONE coker fluid");
    }

    private static FluidStack copyFluid(FluidStack stack) { return stack == null ? null : new FluidStack(stack.type, stack.fill, stack.pressure); }
    private static void checkSnapshotSize(String text) {
        if(text == null || text.getBytes(StandardCharsets.UTF_8).length > MAX_SYNC_BYTES) throw new IllegalArgumentException("Coker snapshot exceeds 256 KiB");
    }
}
