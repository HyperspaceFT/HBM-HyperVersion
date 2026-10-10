package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.items.FuelAdditiveItem;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.util.TagsUtil;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.TagParser;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.io.IOException;
import java.io.Reader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Output groups and variant order follow the original HBM mixer table. */
public class MixerRecipes extends SerializableRecipe {
    public static final int INPUT_CAPACITY = 16000;
    public static final int OUTPUT_CAPACITY = 24000;
    public static final int MAX_SYNC_GROUPS = 4096;
    public static final int MAX_SYNC_RECIPES = 4096;
    public static final int MAX_VARIANTS_PER_GROUP = 256;
    public static final int MAX_SYNC_BYTES = 256 * 1024;
    public static final Map<FluidType, MixerRecipe[]> recipes = new LinkedHashMap<>();
    private final Map<FluidType, MixerRecipe[]> table;

    public MixerRecipes() { this(recipes); }
    private MixerRecipes(Map<FluidType, MixerRecipe[]> table) { this.table = table; }

    public record MixerRecipe(int output, int processTime, FluidStack input1, FluidStack input2, AStack solidInput) {
        public MixerRecipe {
            if(output <= 0 || output > OUTPUT_CAPACITY) throw invalid("outputAmount must be 1..24000");
            if(processTime <= 0) throw invalid("duration must be a positive int");
            input1 = validatedFluid(input1);
            input2 = validatedFluid(input2);
            if(solidInput != null && !(solidInput instanceof SolidInput)) throw invalid("unsupported solid implementation");
            solidInput = solidInput == null ? null : solidInput.copy();
            if(input1 == null && input2 == null && solidInput == null) throw invalid("a variant needs at least one input");
        }
        @Override public FluidStack input1() { return copyFluid(input1); }
        @Override public FluidStack input2() { return copyFluid(input2); }
        @Override public AStack solidInput() { return solidInput == null ? null : solidInput.copy(); }
    }

    /** Exact components, a bound/declaration-checked tag, or bounded exact item alternatives. */
    public static final class SolidInput extends AStack {
        private final List<ItemStack> alternatives;
        private final TagKey<Item> tag;
        private SolidInput(List<ItemStack> alternatives, TagKey<Item> tag, int amount) {
            if(amount <= 0 || amount > 64) throw invalid("solid count must be 1..64");
            this.stacksize = amount;
            this.tag = tag;
            this.alternatives = alternatives.stream().map(ItemStack::copy).toList();
            if(tag == null && (alternatives.isEmpty() || alternatives.size() > MAX_VARIANTS_PER_GROUP)) throw invalid("invalid solid alternative count");
            for(ItemStack stack : alternatives) {
                if(stack.isEmpty() || stack.getCount() != amount || amount > stack.getMaxStackSize()) throw invalid("solid amount exceeds item stack capacity");
                encodeItem(stack); // Reject components that the array format cannot represent.
            }
        }
        @Override public boolean matchesRecipe(ItemStack stack, boolean ignoreSize) {
            if(stack == null || stack.isEmpty() || (!ignoreSize && stack.getCount() < stacksize)) return false;
            if(tag != null) return stack.is(tag);
            return alternatives.stream().anyMatch(item -> ItemStack.isSameItemSameComponents(item, stack));
        }
        @Override public SolidInput copy() { return new SolidInput(alternatives, tag, stacksize); }
        @Override public SolidInput copy(int amount) {
            return new SolidInput(alternatives.stream().map(stack -> stack.copyWithCount(amount)).toList(), tag, amount);
        }
        @Override public List<ItemStack> extractForJEI() {
            if(tag == null) return alternatives.stream().map(ItemStack::copy).toList();
            List<ItemStack> result = new ArrayList<>();
            for(var item : BuiltInRegistries.ITEM.getTagOrEmpty(tag)) result.add(new ItemStack(item.value(), stacksize));
            return result;
        }
        @Override public int compareTo(AStack other) { return toJson().toString().compareTo(other instanceof SolidInput solid ? solid.toJson().toString() : other.toString()); }
        public JsonArray toJson() {
            JsonArray array = new JsonArray();
            if(tag != null) {
                array.add("tag"); array.add(tag.location().toString());
                if(stacksize != 1) array.add(stacksize);
            } else if(alternatives.size() == 1) return encodeItem(alternatives.getFirst());
            else {
                array.add("any");
                for(ItemStack stack : alternatives) array.add(encodeItem(stack));
            }
            return array;
        }
    }

    public static MixerRecipe[] getOutput(FluidType type) {
        MixerRecipe[] group = recipes.get(type);
        return group == null ? new MixerRecipe[0] : group.clone();
    }
    public static MixerRecipe getOutput(FluidType type, int index) {
        MixerRecipe[] group = getOutput(type);
        return group.length == 0 ? null : group[Math.floorMod(index, group.length)];
    }
    public static Map<FluidType, MixerRecipe[]> getDefaultRecipes() {
        Map<FluidType, MixerRecipe[]> defaults = new LinkedHashMap<>();
        new MixerRecipes(defaults).registerDefaults();
        return Collections.unmodifiableMap(defaults);
    }

    private static SolidInput item(ItemStack stack) { return new SolidInput(List.of(stack), null, stack.getCount()); }
    private static SolidInput item(Item item) { return item(new ItemStack(item)); }
    private static FluidStack fluid(FluidType type, int amount) { return new FluidStack(type, amount); }
    private static MixerRecipe mix(int output, int time, FluidStack first, FluidStack second, AStack solid) { return new MixerRecipe(output, time, first, second, solid); }

    @Override public void registerDefaults() {
        add(Fluids.COOLANT, mix(2000,50,fluid(Fluids.WATER,1800),null,item(NtmItems.NITER.get())));
        add(Fluids.CRYOGEL, mix(2000,50,fluid(Fluids.COOLANT,1800),null,item(NtmItems.POWDER_ICE.get())));
        add(Fluids.NITAN, mix(1000,50,fluid(Fluids.KEROSENE,600),fluid(Fluids.MERCURY,200),item(NtmItems.POWDER_NITAN_MIX.get())));
        add(Fluids.FRACKSOL, mix(1000,20,fluid(Fluids.SULFURIC_ACID,900),fluid(Fluids.PETROLEUM,100),null), mix(1000,20,fluid(Fluids.WATER,1000),fluid(Fluids.PETROLEUM,100),item(NtmItems.SULFUR.get())));
        add(Fluids.ENDERJUICE, mix(100,100,fluid(Fluids.XPJUICE,500),null,item(NtmItems.POWDER_DIAMOND.get())));
        add(Fluids.SALIENT, mix(1000,20,fluid(Fluids.SEEDSLURRY,500),fluid(Fluids.BLOOD,500),null));
        add(Fluids.COLLOID, mix(500,20,fluid(Fluids.WATER,500),null,item(NtmItems.DUST.get())));
        add(Fluids.PHOSGENE, mix(1000,20,fluid(Fluids.UNSATURATEDS,500),fluid(Fluids.CHLORINE,500),null));
        add(Fluids.MUSTARDGAS, mix(1000,20,fluid(Fluids.REFORMGAS,750),fluid(Fluids.CHLORINE,250),item(NtmItems.SULFUR.get())));
        add(Fluids.IONGEL, mix(1000,50,fluid(Fluids.WATER,1000),fluid(Fluids.HYDROGEN,200),item(NtmItems.PELLET_CHARGED.get())));
        add(Fluids.EGG, mix(1000,50,fluid(Fluids.RADIOSOLVENT,500),null,item(Items.EGG)));
        add(Fluids.FISHOIL, mix(100,50,null,null,new SolidInput(List.of(new ItemStack(Items.COD),new ItemStack(Items.SALMON),new ItemStack(Items.TROPICAL_FISH),new ItemStack(Items.PUFFERFISH)),null,1)));
        add(Fluids.SUNFLOWEROIL, mix(100,50,null,null,item(Items.SUNFLOWER)));
        // FULLERENE requires the absent SOOT ash identity; no substitute is registered.
        add(Fluids.SOLVENT, mix(1000,50,fluid(Fluids.NAPHTHA,500),fluid(Fluids.AROMATICS,500),null), mix(1000,50,fluid(Fluids.NAPHTHA_CRACK,500),fluid(Fluids.AROMATICS,500),null), mix(1000,50,fluid(Fluids.NAPHTHA_DS,500),fluid(Fluids.AROMATICS,500),null), mix(1000,50,fluid(Fluids.NAPHTHA_COKER,500),fluid(Fluids.AROMATICS,500),null));
        add(Fluids.SULFURIC_ACID, mix(500,50,fluid(Fluids.PEROXIDE,800),null,item(NtmItems.SULFUR.get())));
        add(Fluids.NITRIC_ACID, mix(1000,50,fluid(Fluids.SULFURIC_ACID,500),null,item(NtmItems.NITER.get())));
        add(Fluids.RADIOSOLVENT, mix(1000,50,fluid(Fluids.REFORMGAS,750),fluid(Fluids.CHLORINE,250),null));
        add(Fluids.SCHRABIDIC, mix(16000,100,fluid(Fluids.SAS3,8000),fluid(Fluids.PEROXIDE,6000),item(NtmItems.PELLET_CHARGED.get())));
        add(Fluids.PETROIL, mix(1000,30,fluid(Fluids.RECLAIMED,800),fluid(Fluids.LUBRICANT,200),null));
        add(Fluids.LUBRICANT, mix(1000,20,fluid(Fluids.HEATINGOIL,500),fluid(Fluids.UNSATURATEDS,500),null), mix(1000,20,fluid(Fluids.FISHOIL,800),fluid(Fluids.ETHANOL,200),null), mix(1000,20,fluid(Fluids.SUNFLOWEROIL,800),fluid(Fluids.ETHANOL,200),null));
        add(Fluids.BIOFUEL, mix(250,20,fluid(Fluids.FISHOIL,500),fluid(Fluids.WOODOIL,500),null), mix(200,20,fluid(Fluids.SUNFLOWEROIL,500),fluid(Fluids.WOODOIL,500),null));
        add(Fluids.NITROGLYCERIN, mix(1000,20,fluid(Fluids.PETROLEUM,1000),fluid(Fluids.NITRIC_ACID,1000),null), mix(1000,20,fluid(Fluids.FISHOIL,500),fluid(Fluids.NITRIC_ACID,500),null));
        add(Fluids.THORIUM_SALT, mix(1000,30,fluid(Fluids.CHLORINE,1000),null,item(NtmItems.POWDER_THORIUM.get())));
        add(Fluids.SYNGAS, mix(1000,50,fluid(Fluids.COALOIL,500),fluid(Fluids.STEAM,500),null));
        add(Fluids.OXYHYDROGEN, mix(1000,50,fluid(Fluids.HYDROGEN,500),fluid(Fluids.AIR,2000),null), mix(1000,50,fluid(Fluids.HYDROGEN,500),fluid(Fluids.OXYGEN,500),null));
        SolidInput antiknock = item(MetaHelper.newStack(NtmItems.FUEL_ADDITIVE.get(), FuelAdditiveItem.Type.ANTIKNOCK));
        add(Fluids.PETROIL_LEADED, mix(12000,40,fluid(Fluids.PETROIL,10000),null,antiknock));
        add(Fluids.GASOLINE_LEADED, mix(12000,40,fluid(Fluids.GASOLINE,10000),null,antiknock));
        add(Fluids.COALGAS_LEADED, mix(12000,40,fluid(Fluids.COALGAS,10000),null,antiknock));
        add(Fluids.DIESEL_REFORM, mix(1000,50,fluid(Fluids.DIESEL,900),fluid(Fluids.REFORMATE,100),null));
        add(Fluids.DIESEL_CRACK_REFORM, mix(1000,50,fluid(Fluids.DIESEL_CRACK,900),fluid(Fluids.REFORMATE,100),null));
        add(Fluids.KEROSENE_REFORM, mix(1000,50,fluid(Fluids.KEROSENE,900),fluid(Fluids.REFORMATE,100),null));
        add(Fluids.CHLOROCALCITE_SOLUTION, mix(500,50,fluid(Fluids.WATER,250),fluid(Fluids.NITRIC_ACID,250),item(NtmItems.POWDER_CHLOROCALCITE.get())));
        add(Fluids.CHLOROCALCITE_MIX, mix(1000,50,fluid(Fluids.CHLOROCALCITE_SOLUTION,500),fluid(Fluids.SULFURIC_ACID,500),item(NtmItems.POWDER_FLUX.get())));
        // PHEROMONE_M requires the absent herbal pill; its upstream system stays deferred.
        add(Fluids.BAUXITE_SOLUTION, mix(300,80,fluid(Fluids.LYE,50),null,item(NtmBlocks.RESOURCE_BAUXITE.asItem())));
        add(Fluids.LYE, mix(100,100,fluid(Fluids.WATER,100),null,item(NtmItems.POWDER_ASH_WOOD.get())));
        add(Fluids.ALUMINA, mix(200,40,fluid(Fluids.SODIUM_ALUMINATE,150),null,item(new ItemStack(NtmItems.FLUORITE.get(),3))), mix(300,40,fluid(Fluids.SODIUM_ALUMINATE,150),null,item(NtmItems.CHUNK_CRYOLITE.get())));
        add(Fluids.PERFLUOROMETHYL, mix(1000,20,fluid(Fluids.PETROLEUM,1000),fluid(Fluids.UNSATURATEDS,500),item(NtmItems.FLUORITE.get())));
        add(Fluids.BITUMEN, mix(50,20,null,null,new SolidInput(List.of(),ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm","any_tars")),1)));
    }

    private void add(FluidType output, MixerRecipe... group) {
        validateType(output);
        if(table.containsKey(output)) throw invalid("duplicate output group: " + output.getInternalName());
        if(group.length == 0 || group.length > MAX_VARIANTS_PER_GROUP) throw invalid("group variants must be 1..256");
        if(table.size() >= MAX_SYNC_GROUPS) throw invalid("too many output groups");
        int total = group.length;
        for(MixerRecipe[] value : table.values()) total += value.length;
        if(total > MAX_SYNC_RECIPES) throw invalid("too many total variants");
        for(MixerRecipe recipe : group) if(recipe == null) throw invalid("null variant");
        table.put(output,group.clone());
    }
    @Override public String getFileName() { return "hbmMixer.json"; }
    @Override public String getComment() { return "Replaces all defaults; an empty recipes array disables mixing. Ordered output groups require at least one variant and each variant needs an input. Inputs <=16000 mB, outputs <=24000 mB; recipe pressure is zero. Item/nbt solid arrays preserve explicit META and custom SNBT; null META represents no META component. any holds exact item arrays; tag needs a known declaration or a current registry binding. Reload only resends memory. Changing selected fluid types clears old tank contents before processing checks."; }
    @Override public Object getRecipeObject() { return table; }
    @Override public void deleteRecipes() { table.clear(); }
    @Override public void readRecipe(JsonElement element) {
        if(element == null || !element.isJsonObject()) throw invalid("expected output group object");
        JsonObject object = element.getAsJsonObject();
        FluidType output = Fluids.fromName(string(object.get("outputType")));
        validateType(output);
        JsonArray variants = array(object.get("recipes"), "group recipes");
        if(variants.isEmpty() || variants.size() > MAX_VARIANTS_PER_GROUP) throw invalid("group variants must be 1..256");
        MixerRecipe[] group = new MixerRecipe[variants.size()];
        for(int i = 0; i < group.length; i++) {
            try {
                if(!variants.get(i).isJsonObject()) throw invalid("expected variant object");
                JsonObject row = variants.get(i).getAsJsonObject();
                group[i] = new MixerRecipe(integer(row.get("outputAmount")),integer(row.get("duration")),row.has("input1") ? readFluid(row.get("input1")) : null,row.has("input2") ? readFluid(row.get("input2")) : null,row.has("solidInput") ? readSolid(row.get("solidInput")) : null);
            } catch(RuntimeException ex) { throw invalid("output " + output.getInternalName() + " variant " + i + ": " + ex.getMessage()); }
        }
        add(output,group);
    }
    @Override public void writeRecipe(Object recipe, JsonWriter writer) throws IOException {
        @SuppressWarnings("unchecked") Map.Entry<FluidType,MixerRecipe[]> entry = (Map.Entry<FluidType,MixerRecipe[]>) recipe;
        validateType(entry.getKey());
        writer.name("outputType").value(entry.getKey().getInternalName());
        writer.name("recipes").beginArray();
        for(MixerRecipe row : entry.getValue()) {
            writer.beginObject().name("duration").value(row.processTime()).name("outputAmount").value(row.output());
            if(row.input1() != null) { writer.name("input1"); writeFluidStack(row.input1(),writer); }
            if(row.input2() != null) { writer.name("input2"); writeFluidStack(row.input2(),writer); }
            if(row.solidInput() != null) { writer.name("solidInput"); gson.toJson(((SolidInput)row.solidInput()).toJson(),writer); }
            writer.endObject();
        }
        writer.endArray();
    }
    @Override public void readRecipeStream(Reader reader) {
        StringBuilder text = new StringBuilder();
        char[] buffer = new char[4096];
        try {
            int amount;
            while((amount = reader.read(buffer)) != -1) {
                if(text.length() + amount > MAX_SYNC_BYTES) throw invalid("configuration exceeds 256 KiB");
                text.append(buffer,0,amount);
            }
        } catch(IOException ex) { throw invalid("unable to read configuration: " + ex.getMessage()); }
        Map<FluidType,MixerRecipe[]> replacement = readSnapshot(text.toString());
        table.clear(); table.putAll(replacement);
    }
    public static String writeSnapshot() throws IOException {
        StringWriter text = new StringWriter();
        try(JsonWriter writer = new JsonWriter(text)) {
            writer.beginObject().name("recipes").beginArray();
            MixerRecipes handler = new MixerRecipes();
            for(var entry : recipes.entrySet()) { writer.beginObject(); handler.writeRecipe(entry,writer); writer.endObject(); }
            writer.endArray().endObject();
        }
        String result = text.toString();
        // Validate public-table changes against the same bounds as incoming data.
        readSnapshot(result);
        return result;
    }
    public static Map<FluidType,MixerRecipe[]> readSnapshot(String json) {
        encodeSnapshot(json);
        return parseTable(gson.fromJson(json,JsonObject.class));
    }
    /** Shared disk/snapshot/packet boundary: never replace an unpaired UTF-16 surrogate on the wire. */
    public static byte[] encodeSnapshot(String json) {
        // Valid UTF-8 uses at least as many bytes as UTF-16 code units; cap before encoder allocation.
        if(json == null || json.length() > MAX_SYNC_BYTES) throw invalid("snapshot exceeds 256 KiB");
        try {
            ByteBuffer encoded = StandardCharsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).encode(CharBuffer.wrap(json));
            if(encoded.remaining() > MAX_SYNC_BYTES) throw invalid("snapshot exceeds 256 KiB");
            byte[] bytes = new byte[encoded.remaining()];
            encoded.get(bytes);
            return bytes;
        } catch(CharacterCodingException ex) { throw invalid("snapshot contains malformed UTF-16 surrogate"); }
    }
    private static Map<FluidType,MixerRecipe[]> parseTable(JsonObject object) {
        if(object == null) throw invalid("missing table object");
        JsonArray rows = array(object.get("recipes"),"table recipes");
        if(rows.size() > MAX_SYNC_GROUPS) throw invalid("too many output groups");
        Map<FluidType,MixerRecipe[]> replacement = new LinkedHashMap<>();
        MixerRecipes handler = new MixerRecipes(replacement);
        for(JsonElement row : rows) handler.readRecipe(row);
        return replacement;
    }
    private static FluidStack readFluid(JsonElement element) {
        JsonArray values = array(element,"fluid");
        if(values.size() < 2 || values.size() > 3) throw invalid("fluid array needs name, amount and optional pressure");
        FluidStack stack = new FluidStack(Fluids.fromName(string(values.get(0))),integer(values.get(1)),values.size() == 3 ? integer(values.get(2)) : 0);
        return validatedFluid(stack);
    }
    private static FluidStack validatedFluid(FluidStack stack) {
        if(stack == null) return null;
        validateType(stack.type);
        if(stack.fill <= 0 || stack.fill > INPUT_CAPACITY || stack.pressure != 0) throw invalid("input fluid must be 1..16000 mB at zero pressure");
        return copyFluid(stack);
    }
    private static SolidInput readSolid(JsonElement element) {
        JsonArray values = array(element,"solid");
        if(values.isEmpty()) throw invalid("empty solid array");
        String kind = string(values.get(0));
        if(kind.equals("item") || kind.equals("nbt")) return item(decodeItem(values));
        if(kind.equals("any")) {
            if(values.size() < 2 || values.size() > MAX_VARIANTS_PER_GROUP + 1) throw invalid("invalid solid alternative count");
            List<ItemStack> choices = new ArrayList<>();
            for(int i = 1; i < values.size(); i++) choices.add(decodeItem(array(values.get(i),"alternative item")));
            return new SolidInput(choices,null,choices.getFirst().getCount());
        }
        if(kind.equals("tag")) {
            if(values.size() < 2 || values.size() > 3) throw invalid("invalid tag array size");
            ResourceLocation id = ResourceLocation.parse(string(values.get(1)));
            TagKey<Item> tag = ItemTags.create(id);
            if(!DECLARED_TAGS.contains(id.toString()) && BuiltInRegistries.ITEM.getTag(tag).isEmpty()) throw invalid("unknown or not yet bound item tag: " + id);
            return new SolidInput(List.of(),tag,values.size() == 3 ? integer(values.get(2)) : 1);
        }
        throw invalid("unknown solid kind: " + kind);
    }
    // These keys are declared by NtmTags.Items / NtmItemTagProvider before runtime tags bind.
    private static final Set<String> DECLARED_TAGS = Set.of("ntm:any_tars","ntm:any_rubbers","ntm:any_concrete","ntm:balls_he","ntm:bars_hard_plastic","ntm:powders_plastic","ntm:ingots_plastic","c:dusts/aluminum","c:ores/aluminum","c:plates/steel","c:plates/copper","hbmsntm:ntm_universal_tank","hbmsntm:ntm_hazard_tank","hbmsntm:ntm_universal_barrel");
    private static ItemStack decodeItem(JsonArray values) {
        if(values.size() < 2 || values.size() > 5) throw invalid("item/nbt array needs kind, ID and optional count, META, SNBT");
        String kind = string(values.get(0));
        if(!kind.equals("item") && !kind.equals("nbt")) throw invalid("alternative must be an exact item/nbt array");
        ResourceLocation id = ResourceLocation.parse(string(values.get(1)));
        if(!BuiltInRegistries.ITEM.containsKey(id)) throw invalid("unknown solid item: " + id);
        ItemStack stack = new ItemStack(BuiltInRegistries.ITEM.get(id),values.size() > 2 ? integer(values.get(2)) : 1);
        if(stack.isEmpty() || stack.getCount() > stack.getMaxStackSize()) throw invalid("invalid solid item count: " + id);
        if(values.size() > 3 && !values.get(3).isJsonNull()) {
            int meta = integer(values.get(3));
            if(meta < 0) throw invalid("META must be nonnegative");
            MetaHelper.setMeta(stack,meta);
        } else if(values.size() > 3) stack.remove(NtmDataComponents.META.get());
        if(values.size() > 4) {
            try { TagsUtil.putCustomData(stack,TagParser.parseTag(string(values.get(4)))); }
            catch(Exception ex) { throw invalid("invalid solid custom-data SNBT: " + ex.getMessage()); }
        }
        return stack;
    }
    private static JsonArray encodeItem(ItemStack stack) {
        JsonArray array = new JsonArray();
        boolean meta = stack.has(NtmDataComponents.META.get());
        boolean custom = TagsUtil.hasCustomData(stack);
        boolean absentDefaultMeta = !meta && new ItemStack(stack.getItem()).has(NtmDataComponents.META.get());
        array.add(custom ? "nbt" : "item");
        array.add(BuiltInRegistries.ITEM.getKey(stack.getItem()).toString());
        if(stack.getCount() != 1 || meta || custom || absentDefaultMeta) array.add(stack.getCount());
        if(meta || custom || absentDefaultMeta) { if(meta) array.add(MetaHelper.getMeta(stack)); else array.add(com.google.gson.JsonNull.INSTANCE); }
        if(custom) array.add(TagsUtil.getCustomData(stack).toString());
        if(!ItemStack.isSameItemSameComponents(stack,decodeItem(array))) throw invalid("solid array cannot represent item components: " + array.get(1));
        return array;
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
    private static void validateType(FluidType type) {
        if(type == null || type == Fluids.NONE || Fluids.fromName(type.getInternalName()) != type) throw invalid("unknown or NONE fluid identity");
    }
    private static FluidStack copyFluid(FluidStack stack) { return stack == null ? null : new FluidStack(stack.type,stack.fill,stack.pressure); }
    private static IllegalArgumentException invalid(String message) { return new IllegalArgumentException("Mixer: " + message); }
}
