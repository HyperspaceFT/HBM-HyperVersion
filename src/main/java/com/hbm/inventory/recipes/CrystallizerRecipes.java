package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
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
import com.hbm.items.component.NtmDataComponents;
import com.hbm.util.TagsUtil;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.TagParser;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;

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
 * Ore acidizer ("crystallizer") table: one input item (exact item/META or tag) plus one acid type and amount produce one
 * output stack after {@code duration} ticks. Rows are keyed on the input identity and the acid type, so the same item may
 * carry different rows for different acids; lookup returns the first registered row whose acid type matches and whose
 * input accepts the stack. The default table holds the fourteen hydrogen peroxide ore groups (Goal 18A) followed by the four
 * sulfuric acid ore groups (titanium, tungsten, cobalt, rare earth; Goal 18B), the sulfuric acid uranium (stone, deepslate,
 * scorched) and thorium (stone, deepslate) ore rows (Goal 20A) and the sulfuric acid nether/schist uranium (and scorched) and
 * nether plutonium ore rows (Goal 22A) and the hydrogen peroxide coal block to graphite block row (Goal 26A), 47 rows. A custom file still replaces the whole table, so an existing custom
 * table does not gain the sulfuric acid rows automatically.
 */
public class CrystallizerRecipes extends SerializableRecipe {
    public static final int MAX_SYNC_RECIPES = 4096;
    public static final int MAX_SYNC_BYTES = 256 * 1024;
    /** The machine's single acid tank holds 8,000 mB; a row needing more could never run. */
    public static final int MAX_ACID = 8_000;
    public static final int MAX_DURATION = 1_000_000;
    public static final int DEFAULT_DURATION = 600;
    public static final int DEFAULT_ACID = 500;
    public static final float DEFAULT_PRODUCTIVITY = 0.05F;
    private static final List<CrystallizerRecipe> RECIPES = new ArrayList<>();
    private final List<CrystallizerRecipe> table;

    public CrystallizerRecipes() { this(RECIPES); }
    private CrystallizerRecipes(List<CrystallizerRecipe> table) { this.table = table; }

    public static final class CrystallizerRecipe {
        /** Exact item (with META, 32767 wildcard) or item tag; {@code stacksize} is the amount consumed per completed cycle. */
        public final AStack input;
        /** Acid type and the full amount consumed per completed cycle (pressure 0). */
        public final FluidStack fluid;
        public final ItemStack output;
        public final int duration;
        /** Chance per Effectiveness level that the input is kept; the acid is always consumed. */
        public final float productivity;

        public CrystallizerRecipe(AStack input, FluidStack fluid, ItemStack output, int duration, float productivity) {
            if(input == null) throw invalid("missing input");
            if(input.stacksize < 1 || input.stacksize > 64) throw invalid("input count must be 1..64");
            if(input instanceof ComparableStack comparable) {
                if(comparable.item == null || comparable.item == Items.AIR || comparable.item == NtmItems.NOTHING.get()) throw invalid("input item must be a real item");
                if(comparable.meta < 0) throw invalid("input META must be nonnegative");
                this.input = new ComparableStack(comparable.item, comparable.stacksize, comparable.meta);
            } else if(input instanceof TagStack tagged) {
                if(tagged.tag == null) throw invalid("missing input tag");
                this.input = new TagStack(tagged.tag, tagged.stacksize);
            } else throw invalid("unsupported input kind");
            if(fluid == null || fluid.type == null || fluid.type == Fluids.NONE) throw invalid("missing acid type");
            if(fluid.fill < 1 || fluid.fill > MAX_ACID) throw invalid("acid amount must be 1.." + MAX_ACID);
            if(fluid.pressure != 0) throw invalid("acid pressure must be 0");
            this.fluid = new FluidStack(fluid.type, fluid.fill);
            if(output == null || output.isEmpty() || output.getCount() < 1 || output.getCount() > 64) throw invalid("output must be 1..64 of a real item");
            this.output = output.copy();
            encodeItem(this.output);
            if(duration < 1 || duration > MAX_DURATION) throw invalid("duration must be 1.." + MAX_DURATION);
            this.duration = duration;
            if(Float.isNaN(productivity) || Float.isInfinite(productivity) || productivity < 0F || productivity > 1F) throw invalid("productivity must be a finite 0..1");
            this.productivity = productivity;
        }

        public int itemAmount() { return input.stacksize; }
        public int acidAmount() { return fluid.fill; }
        public FluidType acidType() { return fluid.type; }
        public ItemStack output() { return output.copy(); }

        /** Acid type must be the tank's current type; the input match ignores the stack count (the machine checks it separately). */
        public boolean matches(ItemStack stack, FluidType type) {
            if(stack == null || stack.isEmpty() || type == null || type != fluid.type) return false;
            return input.matchesRecipe(stack, true);
        }

        /** Registration key: the input identity (item + META or tag) and the acid type; the amounts are values, not keys. */
        public String inputKey() {
            if(input instanceof ComparableStack comparable) return "item:" + BuiltInRegistries.ITEM.getKey(comparable.item) + ":" + comparable.meta;
            return "tag:" + ((TagStack) input).tag.location();
        }
        public String key() { return inputKey() + "@" + fluid.type.getInternalName(); }

        public boolean sameRecipe(CrystallizerRecipe other) {
            return other != null && key().equals(other.key()) && input.stacksize == other.input.stacksize && fluid.fill == other.fluid.fill
                    && duration == other.duration && Float.floatToIntBits(productivity) == Float.floatToIntBits(other.productivity)
                    && output.getCount() == other.output.getCount() && ItemStack.isSameItemSameComponents(output, other.output);
        }
    }

    public static List<CrystallizerRecipe> getJeiRecipes() { return copyRecipes(RECIPES); }
    public static List<CrystallizerRecipe> getDefaultRecipes() {
        List<CrystallizerRecipe> defaults = new ArrayList<>();
        new CrystallizerRecipes(defaults).registerDefaults();
        return copyRecipes(defaults);
    }
    public static List<CrystallizerRecipe> copyRecipes(List<CrystallizerRecipe> source) {
        List<CrystallizerRecipe> result = new ArrayList<>(source.size());
        for(CrystallizerRecipe recipe : source) result.add(new CrystallizerRecipe(recipe.input, recipe.fluid, recipe.output, recipe.duration, recipe.productivity));
        return result;
    }
    public static boolean hasRecipe(ItemStack stack, FluidType type) { return getOutput(RECIPES, stack, type) != null; }
    public static CrystallizerRecipe getOutput(ItemStack stack, FluidType type) { return getOutput(RECIPES, stack, type); }
    /** First registered row in table order whose acid type matches and whose input accepts the stack. */
    public static CrystallizerRecipe getOutput(List<CrystallizerRecipe> source, ItemStack stack, FluidType type) {
        if(stack == null || stack.isEmpty() || type == null) return null;
        for(CrystallizerRecipe recipe : source) if(recipe.matches(stack, type)) return recipe;
        return null;
    }
    /** Whether any row in the table accepts the item with any acid. Table query for tools and the isolation checks; the machine itself filters by the current acid type through {@link #hasRecipe}. */
    public static boolean hasRecipeForAnyAcid(List<CrystallizerRecipe> source, ItemStack stack) {
        if(stack == null || stack.isEmpty()) return false;
        for(CrystallizerRecipe recipe : source) if(recipe.input.matchesRecipe(stack, true)) return true;
        return false;
    }

    private void add(CrystallizerRecipe row) {
        if(table.size() >= MAX_SYNC_RECIPES) throw invalid("too many recipes");
        for(CrystallizerRecipe old : table) {
            if(old.key().equals(row.key())) throw invalid("duplicate input/acid key " + row.key());
        }
        table.add(row);
    }
    private void ore(Block stone, Block deepslate, ItemLike crystal) { ore(stone, deepslate, crystal, Fluids.PEROXIDE); }
    private void ore(Block stone, Block deepslate, ItemLike crystal, FluidType acid) {
        FluidStack fluid = new FluidStack(acid, DEFAULT_ACID);
        add(new CrystallizerRecipe(new ComparableStack(stone, 1), fluid, new ItemStack(crystal), DEFAULT_DURATION, DEFAULT_PRODUCTIVITY));
        add(new CrystallizerRecipe(new ComparableStack(deepslate, 1), fluid, new ItemStack(crystal), DEFAULT_DURATION, DEFAULT_PRODUCTIVITY));
    }
    /** One ore block without a deepslate twin (the scorched, nether and schist uranium ores, the nether plutonium ore), same numbers as {@link #ore}. */
    private void single(Block ore, ItemLike crystal, FluidType acid) {
        add(new CrystallizerRecipe(new ComparableStack(ore, 1), new FluidStack(acid, DEFAULT_ACID), new ItemStack(crystal), DEFAULT_DURATION, DEFAULT_PRODUCTIVITY));
    }

    @Override public String getFileName() { return "hbmCrystallizer.json"; }
    @Override public Object getRecipeObject() { return table; }
    /** Fourteen ordinary peroxide ore groups in the original table order, then the four sulfuric acid groups, then the sulfuric acid uranium and thorium ores, then (Goal 22A) the nether and schist uranium ores and the nether plutonium ore, then (Goal 26A) the coal block to graphite block row; stone and deepslate ore blocks are separate rows. */
    @Override public void registerDefaults() {
        ore(Blocks.COAL_ORE, Blocks.DEEPSLATE_COAL_ORE, NtmItems.CRYSTAL_COAL.get());
        ore(Blocks.IRON_ORE, Blocks.DEEPSLATE_IRON_ORE, NtmItems.CRYSTAL_IRON.get());
        ore(Blocks.GOLD_ORE, Blocks.DEEPSLATE_GOLD_ORE, NtmItems.CRYSTAL_GOLD.get());
        ore(Blocks.REDSTONE_ORE, Blocks.DEEPSLATE_REDSTONE_ORE, NtmItems.CRYSTAL_REDSTONE.get());
        ore(Blocks.LAPIS_ORE, Blocks.DEEPSLATE_LAPIS_ORE, NtmItems.CRYSTAL_LAPIS.get());
        ore(Blocks.DIAMOND_ORE, Blocks.DEEPSLATE_DIAMOND_ORE, NtmItems.CRYSTAL_DIAMOND.get());
        ore(NtmBlocks.ORE_SULFUR.get(), NtmBlocks.ORE_SULFUR_DEEPSLATE.get(), NtmItems.CRYSTAL_SULFUR.get());
        ore(NtmBlocks.ORE_NITER.get(), NtmBlocks.ORE_NITER_DEEPSLATE.get(), NtmItems.CRYSTAL_NITER.get());
        ore(Blocks.COPPER_ORE, Blocks.DEEPSLATE_COPPER_ORE, NtmItems.CRYSTAL_COPPER.get());
        ore(NtmBlocks.ORE_ALUMINIUM.get(), NtmBlocks.ORE_ALUMINIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_ALUMINIUM.get());
        ore(NtmBlocks.ORE_FLUORITE.get(), NtmBlocks.ORE_FLUORITE_DEEPSLATE.get(), NtmItems.CRYSTAL_FLUORITE.get());
        ore(NtmBlocks.ORE_BERYLLIUM.get(), NtmBlocks.ORE_BERYLLIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_BERYLLIUM.get());
        ore(NtmBlocks.ORE_LEAD.get(), NtmBlocks.ORE_LEAD_DEEPSLATE.get(), NtmItems.CRYSTAL_LEAD.get());
        ore(NtmBlocks.ORE_CINNABAR.get(), NtmBlocks.ORE_CINNABAR_DEEPSLATE.get(), NtmItems.CRYSTAL_CINNABAR.get());
        ore(NtmBlocks.ORE_TITANIUM.get(), NtmBlocks.ORE_TITANIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_TITANIUM.get(), Fluids.SULFURIC_ACID);
        ore(NtmBlocks.ORE_TUNGSTEN.get(), NtmBlocks.ORE_TUNGSTEN_DEEPSLATE.get(), NtmItems.CRYSTAL_TUNGSTEN.get(), Fluids.SULFURIC_ACID);
        ore(NtmBlocks.ORE_COBALT.get(), NtmBlocks.ORE_COBALT_DEEPSLATE.get(), NtmItems.CRYSTAL_COBALT.get(), Fluids.SULFURIC_ACID);
        ore(NtmBlocks.ORE_RARE.get(), NtmBlocks.ORE_RARE_DEEPSLATE.get(), NtmItems.CRYSTAL_RARE.get(), Fluids.SULFURIC_ACID);
        // Original CrystallizerRecipes.java:67-68 (Goal 20A): U.ore() (OreDictManager.java:347) and every TH232 ore (:351) under the
        // :59 sulfuric acid stack, baseTime 600, prod 0.05. Ported for the named NEO uranium ores: ore_uranium (plus its deepslate
        // variant) and ore_uranium_scorched (no world generation; nuclear waste contamination turns uranium ore into it since Goal 21C).
        // ore_sellafield_uranium_scorched has no NEO block. TH232 has ore_thorium and its deepslate variant.
        ore(NtmBlocks.ORE_URANIUM.get(), NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);
        single(NtmBlocks.ORE_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);
        ore(NtmBlocks.ORE_THORIUM.get(), NtmBlocks.ORE_THORIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_THORIUM.get(), Fluids.SULFURIC_ACID);
        // Goal 22A: the remaining U.ore() members (OreDictManager.java:347) now that they are named and in the creative tab: the nether and
        // schist uranium ores and their scorched variants (NEO generates none of them; they come from nuclear waste contamination,
        // the creative tab or commands). Then the :69 plutonium row: PU.ore() is only ore_nether_plutonium (OreDictManager.java:352).
        // Appended after the Goal 20A rows so the first 41 rows keep their positions; the input keys are distinct, so order does not
        // change which row matches.
        single(NtmBlocks.ORE_NETHER_URANIUM.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);
        single(NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);
        single(NtmBlocks.ORE_GNEISS_URANIUM.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);
        single(NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);
        single(NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmItems.CRYSTAL_PLUTONIUM.get(), Fluids.SULFURIC_ACID);
        // Goal 26A: original CrystallizerRecipes.java:99 registerRecipe(new OreDictStack(COAL.block()), new CrystallizerRecipe(ModBlocks.block_graphite, baseTime))
        // with the two-argument overload's defaults (:314-316: hydrogen peroxide 500 mB, baseTime 600, productivity 0, one item). The
        // OreDictionary "blockCoal" becomes the c:storage_blocks/coal tag. Appended so the first 46 rows keep their positions; the
        // productivity is passed as 0 because DEFAULT_PRODUCTIVITY is the ore rows' .prod(0.05F), which line 99 does not carry.
        add(new CrystallizerRecipe(new TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "storage_blocks/coal")), 1), new FluidStack(Fluids.PEROXIDE, DEFAULT_ACID), new ItemStack(NtmBlocks.BLOCK_GRAPHITE.get()), DEFAULT_DURATION, 0F));
    }
    @Override public void deleteRecipes() { table.clear(); }
    @Override public String getComment() {
        return "Ore acidizer (crystallizer) recipes. Replaces the whole table; an empty table disables the machine. Each row: input [\"item\", id, count, META] (META 32767 is a wildcard; omitted count is 1, omitted META is the wildcard) or [\"tag\", id, count]; fluid [internal acid name, mB] with 1..8000 mB; output [id, count, META|null, custom-data SNBT] (omitted or null META keeps the item without a META component); duration in ticks 1..1000000 (the machine completes after duration+1 effective sub-cycles); productivity 0..1 is the chance per Effectiveness level that the input is kept, the acid is always consumed. Rows are keyed on input identity plus acid type, so one item may have one row per acid; the first matching row in table order wins. The default table holds the fourteen hydrogen peroxide ore groups plus the four sulfuric acid ore groups (titanium, tungsten, cobalt, rare earth) and the sulfuric acid uranium (stone, deepslate, scorched, nether, scorched nether, schist, scorched schist), thorium (stone, deepslate) and nether plutonium ore rows plus the hydrogen peroxide coal block to graphite block row, 47 rows; a custom file still replaces the whole table, so an existing custom table does not gain the sulfuric acid rows automatically (append their rows to keep them).";
    }
    @Override public void readRecipe(JsonElement element) {
        try {
            if(element == null || !element.isJsonObject()) throw invalid("expected recipe object");
            JsonObject row = element.getAsJsonObject();
            AStack input = decodeInput(array(row.get("input"), "input"));
            FluidStack fluid = decodeFluid(array(row.get("fluid"), "fluid"));
            ItemStack output = decodeItem(array(row.get("output"), "output"));
            int duration = integer(row.get("duration"));
            float productivity = row.has("productivity") && !row.get("productivity").isJsonNull() ? number(row.get("productivity")) : 0F;
            add(new CrystallizerRecipe(input, fluid, output, duration, productivity));
        } catch(RuntimeException ex) { throw invalid("recipe " + table.size() + ": " + ex.getMessage()); }
    }
    @Override public void writeRecipe(Object value, JsonWriter writer) throws IOException {
        CrystallizerRecipe row = (CrystallizerRecipe) value;
        writer.name("input"); writeInput(row.input, writer);
        writer.name("fluid"); writer.beginArray(); writer.value(row.fluid.type.getInternalName()); writer.value(row.fluid.fill); writer.endArray();
        writer.name("output"); writeItem(row.output, writer);
        writer.name("duration").value(row.duration);
        writer.name("productivity").value(row.productivity);
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
        List<CrystallizerRecipe> replacement = readSnapshot(text.toString(), true);
        table.clear(); table.addAll(replacement);
    }
    public static List<CrystallizerRecipe> readSnapshot(String json) { return readSnapshot(json, false); }
    /** Only the config-file path is lenient (bad rows logged and skipped); sync snapshots and the writeSnapshot self-check stay strict. */
    private static List<CrystallizerRecipe> readSnapshot(String json, boolean lenient) {
        encodeSnapshot(json);
        JsonObject root = gson.fromJson(json, JsonObject.class);
        if(root == null) throw invalid("missing table object");
        JsonArray rows = array(root.get("recipes"), "recipes");
        if(rows.size() > MAX_SYNC_RECIPES) throw invalid("too many recipes");
        List<CrystallizerRecipe> result = new ArrayList<>();
        CrystallizerRecipes handler = new CrystallizerRecipes(result);
        for(int i = 0; i < rows.size(); i++) {
            if(lenient) handler.readRecipeLenient(rows.get(i), i);
            else handler.readRecipe(rows.get(i));
        }
        return result;
    }
    public static String writeSnapshot() throws IOException {
        StringWriter text = new StringWriter(); JsonWriter writer = new JsonWriter(text);
        writer.beginObject().name("recipes").beginArray();
        CrystallizerRecipes handler = new CrystallizerRecipes();
        for(CrystallizerRecipe row : RECIPES) { writer.beginObject(); handler.writeRecipe(row, writer); writer.endObject(); }
        writer.endArray().endObject(); writer.close();
        String result = text.toString(); readSnapshot(result); return result;
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

    /** ["item", id, count?, META?] with omitted META meaning the 32767 wildcard, or ["tag", id, count?]. */
    private static AStack decodeInput(JsonArray values) {
        if(values.size() < 2) throw invalid("input needs a kind and an id");
        String kind = string(values.get(0));
        ResourceLocation id = location(string(values.get(1)));
        if("item".equals(kind)) {
            if(values.size() > 4) throw invalid("item input has at most kind, id, count, META");
            if(!BuiltInRegistries.ITEM.containsKey(id)) throw invalid("unknown item " + id);
            Item item = BuiltInRegistries.ITEM.get(id);
            int count = values.size() > 2 ? integer(values.get(2)) : 1;
            int meta = values.size() > 3 ? integer(values.get(3)) : MetaHelper.WILDCARD_VALUE;
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
    private static void writeInput(AStack input, JsonWriter writer) throws IOException {
        writer.beginArray();
        if(input instanceof ComparableStack comparable) {
            writer.value("item"); writer.value(BuiltInRegistries.ITEM.getKey(comparable.item).toString()); writer.value(comparable.stacksize); writer.value(comparable.meta);
        } else {
            TagStack tagged = (TagStack) input;
            writer.value("tag"); writer.value(tagged.tag.location().toString()); writer.value(tagged.stacksize);
        }
        writer.endArray();
    }
    private static FluidStack decodeFluid(JsonArray values) {
        if(values.size() != 2) throw invalid("fluid needs exactly the internal acid name and an amount");
        String name = string(values.get(0));
        FluidType type = Fluids.fromName(name);
        if(type == null || type == Fluids.NONE || !name.equals(type.getInternalName())) throw invalid("unknown acid " + name);
        return new FluidStack(type, integer(values.get(1)));
    }
    /** [id, count?, META|null?, custom-data SNBT?]; omitted or null META keeps the item without a META component. */
    private static ItemStack decodeItem(JsonArray values) {
        if(values.size() < 1 || values.size() > 4) throw invalid("item array needs ID and optional count, META, SNBT");
        ResourceLocation id = location(string(values.get(0)));
        if(!BuiltInRegistries.ITEM.containsKey(id)) throw invalid("unknown item " + id);
        Item item = BuiltInRegistries.ITEM.get(id);
        if(item == Items.AIR) throw invalid("output cannot be empty");
        int count = values.size() > 1 ? integer(values.get(1)) : 1;
        if(count <= 0) throw invalid("item count must be positive");
        ItemStack stack = new ItemStack(item, count);
        if(values.size() > 2 && !values.get(2).isJsonNull()) {
            int meta = integer(values.get(2));
            if(meta < 0) throw invalid("META must be nonnegative");
            MetaHelper.setMeta(stack, meta);
        }
        if(values.size() > 3) {
            try { TagsUtil.putCustomData(stack, TagParser.parseTag(string(values.get(3)))); }
            catch(Exception ex) { throw invalid("invalid custom-data SNBT: " + ex.getMessage()); }
        }
        return stack;
    }
    private static JsonArray encodeItem(ItemStack stack) {
        JsonArray result = new JsonArray();
        if(stack.isEmpty() || stack.getCount() <= 0) throw invalid("invalid output stack");
        result.add(BuiltInRegistries.ITEM.getKey(stack.getItem()).toString());
        result.add(stack.getCount());
        if(stack.has(NtmDataComponents.META.get())) result.add(MetaHelper.getMeta(stack));
        else result.add(JsonNull.INSTANCE);
        if(TagsUtil.hasCustomData(stack)) result.add(TagsUtil.getCustomData(stack).toString());
        if(!ItemStack.isSameItemSameComponents(stack, decodeItem(result))) throw invalid("array cannot represent components: " + result.get(0));
        return result;
    }
    private static void writeItem(ItemStack stack, JsonWriter writer) throws IOException {
        writer.beginArray();
        for(JsonElement value : encodeItem(stack)) {
            if(value.isJsonNull()) writer.nullValue();
            else if(value.getAsJsonPrimitive().isNumber()) writer.value(value.getAsNumber());
            else writer.value(value.getAsString());
        }
        writer.endArray();
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
    private static float number(JsonElement value) {
        if(value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isNumber()) throw invalid("expected number");
        double parsed = value.getAsDouble();
        if(Double.isNaN(parsed) || Double.isInfinite(parsed)) throw invalid("expected finite number");
        return (float) parsed;
    }
    private static IllegalArgumentException invalid(String message) { return new IllegalArgumentException("Crystallizer: " + message); }
}
