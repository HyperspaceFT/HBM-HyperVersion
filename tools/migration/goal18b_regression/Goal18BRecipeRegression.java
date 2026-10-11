package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.handler.CrystallizerRecipeClientSync;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.network.toclient.CrystallizerRecipesPacket;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;

import java.io.StringReader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Goal18B: the four sulfuric acid ore groups appended to the production crystallizer defaults, the frozen Goal18A rows, sync, the merge record and the unchanged assembly table. */
public final class Goal18BRecipeRegression {
    private static int checks, scenarios;
    private Goal18BRecipeRegression() { }
    private static void check(boolean condition, String message) { checks++; if(!condition) throw new AssertionError(message); }
    private static void scenario() { scenarios++; }
    private static String table(String... rows) { return "{\"recipes\":[" + String.join(",", rows) + "]}"; }
    private static String row(String input, String fluid, String output, String duration, String productivity) {
        return "{\"input\":" + input + ",\"fluid\":" + fluid + ",\"output\":" + output + ",\"duration\":" + duration + (productivity == null ? "" : ",\"productivity\":" + productivity) + "}";
    }
    private static String sulfuricRow(String ore, String crystal) {
        return row("[\"item\",\"hbmsntm:" + ore + "\",1,32767]", "[\"SULFURIC_ACID\",500]", "[\"hbmsntm:" + crystal + "\",1,null]", "600", "0.05");
    }

    private static final int PEROXIDE_GROUPS = 14, GROUPS = 18, ROWS = 36, GOAL18A_ROWS = 28;
    /** The fourteen Goal18A hydrogen peroxide groups in their Goal18A order, then the four Goal18B sulfuric acid groups. */
    private static final Object[][] EXPECTED = {
        {Blocks.COAL_ORE, Blocks.DEEPSLATE_COAL_ORE, NtmItems.CRYSTAL_COAL}, {Blocks.IRON_ORE, Blocks.DEEPSLATE_IRON_ORE, NtmItems.CRYSTAL_IRON},
        {Blocks.GOLD_ORE, Blocks.DEEPSLATE_GOLD_ORE, NtmItems.CRYSTAL_GOLD}, {Blocks.REDSTONE_ORE, Blocks.DEEPSLATE_REDSTONE_ORE, NtmItems.CRYSTAL_REDSTONE},
        {Blocks.LAPIS_ORE, Blocks.DEEPSLATE_LAPIS_ORE, NtmItems.CRYSTAL_LAPIS}, {Blocks.DIAMOND_ORE, Blocks.DEEPSLATE_DIAMOND_ORE, NtmItems.CRYSTAL_DIAMOND},
        {NtmBlocks.ORE_SULFUR.get(), NtmBlocks.ORE_SULFUR_DEEPSLATE.get(), NtmItems.CRYSTAL_SULFUR}, {NtmBlocks.ORE_NITER.get(), NtmBlocks.ORE_NITER_DEEPSLATE.get(), NtmItems.CRYSTAL_NITER},
        {Blocks.COPPER_ORE, Blocks.DEEPSLATE_COPPER_ORE, NtmItems.CRYSTAL_COPPER}, {NtmBlocks.ORE_ALUMINIUM.get(), NtmBlocks.ORE_ALUMINIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_ALUMINIUM},
        {NtmBlocks.ORE_FLUORITE.get(), NtmBlocks.ORE_FLUORITE_DEEPSLATE.get(), NtmItems.CRYSTAL_FLUORITE}, {NtmBlocks.ORE_BERYLLIUM.get(), NtmBlocks.ORE_BERYLLIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_BERYLLIUM},
        {NtmBlocks.ORE_LEAD.get(), NtmBlocks.ORE_LEAD_DEEPSLATE.get(), NtmItems.CRYSTAL_LEAD}, {NtmBlocks.ORE_CINNABAR.get(), NtmBlocks.ORE_CINNABAR_DEEPSLATE.get(), NtmItems.CRYSTAL_CINNABAR},
        {NtmBlocks.ORE_TITANIUM.get(), NtmBlocks.ORE_TITANIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_TITANIUM}, {NtmBlocks.ORE_TUNGSTEN.get(), NtmBlocks.ORE_TUNGSTEN_DEEPSLATE.get(), NtmItems.CRYSTAL_TUNGSTEN},
        {NtmBlocks.ORE_COBALT.get(), NtmBlocks.ORE_COBALT_DEEPSLATE.get(), NtmItems.CRYSTAL_COBALT}, {NtmBlocks.ORE_RARE.get(), NtmBlocks.ORE_RARE_DEEPSLATE.get(), NtmItems.CRYSTAL_RARE}};
    /** The eight appended rows exactly as the production writer emits them. */
    private static final String[] NEW_ROWS = {
        sulfuricRow("ore_titanium", "crystal_titanium"), sulfuricRow("ore_titanium_deepslate", "crystal_titanium"),
        sulfuricRow("ore_tungsten", "crystal_tungsten"), sulfuricRow("ore_tungsten_deepslate", "crystal_tungsten"),
        sulfuricRow("ore_cobalt", "crystal_cobalt"), sulfuricRow("ore_cobalt_deepslate", "crystal_cobalt"),
        sulfuricRow("ore_rare", "crystal_rare"), sulfuricRow("ore_rare_deepslate", "crystal_rare")};

    private static FluidType acid(int group) { return group < PEROXIDE_GROUPS ? Fluids.PEROXIDE : Fluids.SULFURIC_ACID; }
    private static FluidType other(FluidType acid) { return acid == Fluids.PEROXIDE ? Fluids.SULFURIC_ACID : Fluids.PEROXIDE; }
    private static Item item(Object value) { return ((ItemLike) value).asItem(); }
    private static ItemStack stack(Object value) { return new ItemStack(item(value)); }
    private static void restoreDefaults() { CrystallizerRecipes handler = new CrystallizerRecipes(); handler.deleteRecipes(); handler.registerDefaults(); }
    private static JsonObject written(CrystallizerRecipe recipe) throws Exception {
        StringWriter out = new StringWriter();
        try(JsonWriter writer = new JsonWriter(out)) { writer.beginObject(); new CrystallizerRecipes().writeRecipe(recipe, writer); writer.endObject(); }
        return JsonParser.parseString(out.toString()).getAsJsonObject();
    }
    private static JsonArray rowsOf(String json) { return JsonParser.parseString(json).getAsJsonObject().getAsJsonArray("recipes"); }

    private static void defaults() {
        scenario();
        List<CrystallizerRecipe> rows = CrystallizerRecipes.getDefaultRecipes();
        check(rows.size() == ROWS && EXPECTED.length == GROUPS, "eighteen groups as 36 stone/deepslate rows");
        for(int group = 0; group < GROUPS; group++) for(int variant = 0; variant < 2; variant++) {
            CrystallizerRecipe recipe = rows.get(group * 2 + variant);
            Block block = (Block) EXPECTED[group][variant];
            FluidType acid = acid(group);
            String at = group + "/" + variant;
            check(recipe.input instanceof ComparableStack c && c.item == block.asItem() && c.stacksize == 1 && c.meta == MetaHelper.WILDCARD_VALUE && recipe.itemAmount() == 1, "exact ore block input with the wildcard META in table order " + at);
            check(recipe.fluid.type == acid && recipe.acidType() == acid && recipe.fluid.fill == 500 && recipe.acidAmount() == 500 && recipe.fluid.pressure == 0, "500 mB " + acid.getInternalName() + " " + at);
            check(recipe.output.getItem() == item(EXPECTED[group][2]) && recipe.output.getCount() == 1 && !recipe.output.has(NtmDataComponents.META.get()), "one plain crystal " + at);
            check(recipe.duration == 600 && Float.floatToIntBits(recipe.productivity) == Float.floatToIntBits(0.05F), "600 ticks, productivity 0.05 " + at);
            ItemStack ore = new ItemStack(block.asItem());
            check(CrystallizerRecipes.getOutput(rows, ore, acid) == recipe, "lookup resolves its own row under " + acid.getInternalName() + " " + at);
            check(CrystallizerRecipes.getOutput(rows, ore, other(acid)) == null, "no row under " + other(acid).getInternalName() + " " + at);
            check(!recipe.inputKey().contains("lithium") && recipe.output.getItem() != NtmItems.CRYSTAL_LITHIUM.get(), "no lithium ore input or lithium crystal " + at);
        }
        Set<String> keys = new HashSet<>();
        for(CrystallizerRecipe recipe : rows) keys.add(recipe.key());
        check(keys.size() == ROWS && rows.get(GOAL18A_ROWS).key().equals("item:hbmsntm:ore_titanium:32767@SULFURIC_ACID"), "36 distinct input/acid keys");
        // Crystals, raw items, ordinary cobalt/rare-earth drops, fragments, lithium and every other ore variant stay out under both acids.
        List<Item> excluded = new ArrayList<>();
        for(Object[] group : EXPECTED) excluded.add(item(group[2]));
        excluded.addAll(List.of(NtmItems.CRYSTAL_LITHIUM.get(), NtmItems.LITHIUM.get(), NtmItems.POWDER_LITHIUM.get(), NtmBlocks.BLOCK_LITHIUM.get().asItem(),
            Items.RAW_IRON, Items.RAW_COPPER, Items.RAW_GOLD, NtmItems.FRAGMENT_COBALT.get(), NtmItems.RARE_EARTH_ORE_CHUNK.get(), NtmItems.POWDER_COBALT.get(),
            NtmItems.FRAGMENT_NEODYMIUM.get(), NtmItems.FRAGMENT_CERIUM.get(), NtmItems.FRAGMENT_LANTHANIUM.get(), NtmItems.FRAGMENT_NIOBIUM.get(), NtmItems.FRAGMENT_BORON.get(),
            NtmItems.FRAGMENT_ACTINIUM.get(), NtmItems.FRAGMENT_COLTAN.get(), NtmItems.FRAGMENT_METEORITE.get(),
            NtmBlocks.ORE_METEOR_COBALT.get().asItem(), NtmBlocks.ORE_METEOR_RARE.get().asItem(), NtmBlocks.ORE_METEOR_IRON.get().asItem(), NtmBlocks.ORE_METEOR_COPPER.get().asItem(),
            NtmBlocks.ORE_METEOR_ALUMINIUM.get().asItem(), NtmBlocks.ORE_LIGNITE.get().asItem(), NtmBlocks.ORE_DEEPSLATE_LIGNITE.get().asItem(), NtmBlocks.ORE_URANIUM.get().asItem(),
            NtmBlocks.ORE_URANIUM_DEEPSLATE.get().asItem(), NtmBlocks.ORE_THORIUM.get().asItem(), NtmBlocks.ORE_THORIUM_DEEPSLATE.get().asItem(), NtmBlocks.ORE_ASBESTOS.get().asItem(),
            NtmBlocks.ORE_ASBESTOS_DEEPSLATE.get().asItem(), NtmBlocks.ORE_COLTAN.get().asItem(), NtmBlocks.ORE_SCHRABIDIUM.get().asItem(), NtmBlocks.ORE_NETHER_URANIUM.get().asItem(),
            NtmBlocks.ORE_NETHER_PLUTONIUM.get().asItem(), Blocks.NETHER_GOLD_ORE.asItem(), Blocks.NETHER_QUARTZ_ORE.asItem(), Blocks.EMERALD_ORE.asItem(), Blocks.DEEPSLATE_EMERALD_ORE.asItem(), Items.STICK));
        for(Item excludedItem : excluded) {
            ItemStack probe = new ItemStack(excludedItem);
            check(CrystallizerRecipes.getOutput(rows, probe, Fluids.PEROXIDE) == null && CrystallizerRecipes.getOutput(rows, probe, Fluids.SULFURIC_ACID) == null
                    && !CrystallizerRecipes.hasRecipeForAnyAcid(rows, probe), "unlisted input is not accepted under either acid: " + excludedItem.id);
        }
        check(CrystallizerRecipes.getOutput(rows, MetaHelper.newStack(NtmBlocks.ORE_TUNGSTEN.get().asItem(), 1, 5), Fluids.SULFURIC_ACID) == rows.get(30), "the wildcard row accepts any META of the tungsten ore");
        CrystallizerRecipes handler = new CrystallizerRecipes();
        handler.deleteRecipes(); handler.registerDefaults();
        check(CrystallizerRecipes.getJeiRecipes().size() == ROWS && handler.getFileName().equals("hbmCrystallizer.json"), "static table registers the 36 defaults under hbmCrystallizer.json");
        String comment = handler.getComment();
        check(comment != null && comment.contains("peroxide") && comment.contains("sulfuric"), "the config comment names both acids");
        ItemStack tungsten = stack(NtmBlocks.ORE_TUNGSTEN.get()), coal = stack(Blocks.COAL_ORE);
        check(CrystallizerRecipes.hasRecipe(tungsten, Fluids.SULFURIC_ACID) && !CrystallizerRecipes.hasRecipe(tungsten, Fluids.PEROXIDE)
                && CrystallizerRecipes.hasRecipe(coal, Fluids.PEROXIDE) && !CrystallizerRecipes.hasRecipe(coal, Fluids.SULFURIC_ACID), "the machine lookup filters by the tank's acid type");
    }

    private static void frozen18A(Path frozen) throws Exception {
        scenario();
        String frozenText = Files.readString(frozen, StandardCharsets.UTF_8);
        JsonArray old = rowsOf(frozenText);
        restoreDefaults();
        JsonArray live = rowsOf(CrystallizerRecipes.writeSnapshot());
        check(old.size() == GOAL18A_ROWS && live.size() == ROWS && NEW_ROWS.length == ROWS - GOAL18A_ROWS, "frozen Goal18A export has 28 rows, the Goal18B table 36");
        for(int i = 0; i < GOAL18A_ROWS; i++) check(live.get(i).equals(old.get(i)), "Goal18A row " + i + " is unchanged and in place: " + live.get(i));
        for(int i = 0; i < NEW_ROWS.length; i++) check(live.get(GOAL18A_ROWS + i).equals(JsonParser.parseString(NEW_ROWS[i])), "row " + (GOAL18A_ROWS + i) + " is the appended sulfuric acid row: " + live.get(GOAL18A_ROWS + i));
        List<CrystallizerRecipe> frozenRows = CrystallizerRecipes.readSnapshot(frozenText), defaults = CrystallizerRecipes.getDefaultRecipes();
        for(int i = 0; i < GOAL18A_ROWS; i++) check(frozenRows.get(i).sameRecipe(defaults.get(i)), "frozen Goal18A row " + i + " reads back as the same default row");
    }

    private static void roundTrip() throws Exception {
        scenario();
        restoreDefaults();
        String json = CrystallizerRecipes.writeSnapshot();
        List<CrystallizerRecipe> back = CrystallizerRecipes.readSnapshot(json), live = CrystallizerRecipes.getJeiRecipes();
        check(back.size() == ROWS && live.size() == ROWS, "snapshot carries 36 rows");
        for(int i = 0; i < ROWS; i++) {
            check(back.get(i).sameRecipe(live.get(i)) && back.get(i).key().equals(live.get(i).key()), "row " + i + " survives the writer/reader round trip");
            check(written(back.get(i)).equals(written(live.get(i))), "row " + i + " writes identically after reading back");
        }
        new CrystallizerRecipes().readRecipeStream(new StringReader(json));
        check(CrystallizerRecipes.getJeiRecipes().size() == ROWS && CrystallizerRecipes.writeSnapshot().equals(json), "the read-back table writes a byte-identical snapshot");
        check(CrystallizerRecipes.encodeSnapshot(json).length == json.getBytes(StandardCharsets.UTF_8).length && json.length() <= CrystallizerRecipes.MAX_SYNC_BYTES, "UTF-8 snapshot bytes within the 256 KiB bound");
        restoreDefaults();
    }

    private static void sync(Path frozen) throws Exception {
        scenario();
        restoreDefaults();
        List<CrystallizerRecipe> defaults = CrystallizerRecipes.getDefaultRecipes();
        String json = CrystallizerRecipes.writeSnapshot();
        CrystallizerRecipesPacket packet = new CrystallizerRecipesPacket(json);
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        CrystallizerRecipesPacket.STREAM_CODEC.encode(buf, packet);
        CrystallizerRecipesPacket decoded = CrystallizerRecipesPacket.STREAM_CODEC.decode(buf);
        check(decoded.json().equals(json) && decoded.type() == CrystallizerRecipesPacket.TYPE, "packet codec round trip of the 36-row snapshot");
        RegistryFriendlyByteBuf badBytes = new RegistryFriendlyByteBuf(); badBytes.writeByteArray(new byte[]{(byte) 0xC3, (byte) 0x28});
        checks++; try { CrystallizerRecipesPacket.STREAM_CODEC.decode(badBytes); throw new AssertionError("malformed UTF-8 packet accepted"); } catch(IllegalArgumentException expected) { }
        ItemStack tungsten = stack(NtmBlocks.ORE_TUNGSTEN.get()), titanium = stack(NtmBlocks.ORE_TITANIUM_DEEPSLATE.get()), coal = stack(Blocks.COAL_ORE);
        goal18a.JeiBridge bridge = new goal18a.JeiBridge();
        CrystallizerRecipeClientSync.disconnect(null);
        check(CrystallizerRecipeClientSync.getRecipes().size() == ROWS && CrystallizerRecipeClientSync.hasRecipe(tungsten, Fluids.SULFURIC_ACID), "client defaults before any snapshot carry the four sulfuric acid groups");
        bridge.available();
        check(bridge.runtime.additions == ROWS && bridge.displayedCrystallizerRecipes.size() == ROWS, "JEI runtime shows the 36 default rows");
        check(CrystallizerRecipeClientSync.receive(decoded.json()), "the decoded 36-row snapshot is accepted");
        List<CrystallizerRecipe> client = CrystallizerRecipeClientSync.getRecipes();
        check(client.size() == ROWS, "client table holds 36 recipes");
        for(int i = 0; i < ROWS; i++) check(client.get(i).sameRecipe(defaults.get(i)), "client row " + i + " equals the server default");
        check(CrystallizerRecipeClientSync.hasRecipe(tungsten, Fluids.SULFURIC_ACID) && !CrystallizerRecipeClientSync.hasRecipe(tungsten, Fluids.PEROXIDE), "tungsten ore resolves under sulfuric acid only");
        check(CrystallizerRecipeClientSync.getOutput(titanium, Fluids.SULFURIC_ACID).output.getItem() == NtmItems.CRYSTAL_TITANIUM.get() && CrystallizerRecipeClientSync.hasRecipe(coal, Fluids.PEROXIDE), "client prediction covers both acids");
        check(bridge.runtime.additions == ROWS && bridge.displayedCrystallizerRecipes.size() == ROWS, "identical rows are reused, not re-added to JEI");
        // A server whose table lacks the Goal18B groups (the Goal18A export, like an old custom file) is authoritative.
        check(CrystallizerRecipeClientSync.receive(Files.readString(frozen, StandardCharsets.UTF_8)) && CrystallizerRecipeClientSync.getRecipes().size() == GOAL18A_ROWS
                && !CrystallizerRecipeClientSync.hasRecipe(tungsten, Fluids.SULFURIC_ACID) && CrystallizerRecipeClientSync.hasRecipe(coal, Fluids.PEROXIDE), "a 28-row server table does not gain the sulfuric acid groups on the client");
        check(bridge.displayedCrystallizerRecipes.size() == GOAL18A_ROWS && bridge.runtime.additions == ROWS, "JEI hides the eight sulfuric acid rows");
        check(!CrystallizerRecipeClientSync.receive("{\"recipes\":[") && CrystallizerRecipeClientSync.getRecipes().size() == GOAL18A_ROWS, "a malformed payload is ignored and the previous table kept");
        check(!CrystallizerRecipeClientSync.receive(table(row("[\"item\",\"hbmsntm:ore_tungsten\"]", "[\"NOPE\",500]", "[\"hbmsntm:crystal_tungsten\"]", "600", null)))
                && CrystallizerRecipeClientSync.getRecipes().size() == GOAL18A_ROWS, "an unknown acid rejects the whole snapshot");
        check(CrystallizerRecipeClientSync.receive(table()) && CrystallizerRecipeClientSync.getRecipes().isEmpty() && bridge.displayedCrystallizerRecipes.isEmpty()
                && !CrystallizerRecipeClientSync.hasRecipe(tungsten, Fluids.SULFURIC_ACID), "an empty legal snapshot clears the client table and JEI");
        check(!CrystallizerRecipeClientSync.receive("{\"recipes\":[") && CrystallizerRecipeClientSync.getRecipes().isEmpty(), "a malformed payload keeps the empty table");
        check(CrystallizerRecipeClientSync.receive(json) && CrystallizerRecipeClientSync.getRecipes().size() == ROWS && bridge.runtime.additions == ROWS && bridge.displayedCrystallizerRecipes.size() == ROWS, "the 36 rows return without re-adding");
        check(CrystallizerRecipes.getJeiRecipes().size() == ROWS, "client snapshots never touch the server table");
        bridge.unavailable();
        CrystallizerRecipeClientSync.disconnect(null);
        check(CrystallizerRecipeClientSync.getRecipes().size() == ROWS, "logout restores the 36 defaults");
    }

    private static void mergeExample(Path merge) throws Exception {
        scenario();
        restoreDefaults();
        List<CrystallizerRecipe> defaults = CrystallizerRecipes.getDefaultRecipes();
        String text = Files.readString(merge, StandardCharsets.UTF_8);
        JsonObject record = JsonParser.parseString(text).getAsJsonObject();
        check(record.keySet().equals(Set.of("comment", "recipes")) && record.get("comment").getAsString().contains("SULFURIC_ACID"), "merge record is {comment, recipes} like the Goal18A example");
        int[] expected = {0, 3, 28, 29, 30, 31, 32, 33, 34, 35};
        List<CrystallizerRecipe> rows = CrystallizerRecipes.readSnapshot(text);
        JsonArray raw = record.getAsJsonArray("recipes");
        check(rows.size() == expected.length && raw.size() == expected.length, "two kept rows plus the eight Goal18B rows");
        for(int i = 0; i < expected.length; i++) {
            check(rows.get(i).sameRecipe(defaults.get(expected[i])), "merge row " + i + " parses to default row " + expected[i]);
            check(raw.get(i).equals(written(defaults.get(expected[i]))), "merge row " + i + " is the production writer's row " + expected[i]);
        }
        ItemStack tungsten = stack(NtmBlocks.ORE_TUNGSTEN.get()), gold = stack(Blocks.GOLD_ORE), coal = stack(Blocks.COAL_ORE), deepIron = stack(Blocks.DEEPSLATE_IRON_ORE), iron = stack(Blocks.IRON_ORE);
        // Before the merge: the existing custom table (the two kept rows) replaces the defaults and gains nothing automatically.
        CrystallizerRecipes handler = new CrystallizerRecipes();
        handler.readRecipeStream(new StringReader(table(raw.get(0).toString(), raw.get(1).toString())));
        check(CrystallizerRecipes.getJeiRecipes().size() == 2 && !CrystallizerRecipes.hasRecipe(tungsten, Fluids.SULFURIC_ACID) && !CrystallizerRecipes.hasRecipe(gold, Fluids.PEROXIDE)
                && CrystallizerRecipes.hasRecipe(coal, Fluids.PEROXIDE), "an existing custom table does not gain the four sulfuric acid groups");
        // After the merge: the record loads through the config-file path and carries all four groups beside the kept rows.
        check(handler.readRecipeFile(merge.toFile()) && CrystallizerRecipes.getJeiRecipes().size() == expected.length, "the merged record loads through the config-file path");
        for(int group = PEROXIDE_GROUPS; group < GROUPS; group++) for(int variant = 0; variant < 2; variant++) {
            ItemStack ore = stack(EXPECTED[group][variant]);
            check(CrystallizerRecipes.getOutput(ore, Fluids.SULFURIC_ACID) != null && CrystallizerRecipes.getOutput(ore, Fluids.SULFURIC_ACID).output.getItem() == item(EXPECTED[group][2])
                    && !CrystallizerRecipes.hasRecipe(ore, Fluids.PEROXIDE), "merged sulfuric acid row " + group + "/" + variant);
        }
        check(CrystallizerRecipes.hasRecipe(coal, Fluids.PEROXIDE) && CrystallizerRecipes.hasRecipe(deepIron, Fluids.PEROXIDE) && !CrystallizerRecipes.hasRecipe(iron, Fluids.PEROXIDE)
                && !CrystallizerRecipes.hasRecipe(gold, Fluids.PEROXIDE), "the merged table keeps only the player's rows plus the appended groups");
        restoreDefaults();
        check(CrystallizerRecipes.getJeiRecipes().size() == ROWS, "defaults restore after the merge scenario");
    }

    private static JsonObject writeAssembly(GenericRecipes<GenericRecipe> handler, GenericRecipe recipe) throws Exception {
        StringWriter serialized = new StringWriter();
        try(JsonWriter writer = new JsonWriter(serialized)) { writer.beginObject(); handler.writeRecipe(recipe, writer); writer.endObject(); }
        return JsonParser.parseString(serialized.toString()).getAsJsonObject();
    }
    private static Map<String, JsonObject> catalog(GenericRecipes<GenericRecipe> handler) throws Exception {
        handler.deleteRecipes(); handler.registerDefaults();
        Map<String, JsonObject> recipes = new LinkedHashMap<>();
        for(GenericRecipe recipe : handler.recipeOrderedList) {
            check(!recipes.containsKey(recipe.getInternalName()), "unique registered recipe name " + recipe.getInternalName());
            recipes.put(recipe.getInternalName(), writeAssembly(handler, recipe));
        }
        return recipes;
    }
    private static void assemblyUnchanged() throws Exception {
        for(boolean mode : new boolean[]{false, true}) {
            scenario();
            NtmConfig.COMMON.ENABLE_528.set(mode);
            GenericRecipes.clearPools();
            Map<String, JsonObject> baseline = catalog(goal18b.base.AssemblyMachineRecipes.INSTANCE);
            GenericRecipes.clearPools();
            Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);
            check(live.size() == baseline.size() && live.equals(baseline), "every Goal18A assembly row is retained byte for byte and none is added, 528=" + mode);
            check(new ArrayList<>(live.keySet()).equals(new ArrayList<>(baseline.keySet())), "Goal18A assembly row order retained, 528=" + mode);
            check(live.containsKey("ass.acidizer"), "the Goal18A acidizer row is still registered, 528=" + mode);
        }
        NtmConfig.COMMON.ENABLE_528.set(false);
    }

    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[0]), frozen = Path.of(args[1]), merge = Path.of(args[2]);
        defaults(); frozen18A(frozen); roundTrip(); sync(frozen); mergeExample(merge); assemblyUnchanged();
        restoreDefaults();
        Files.writeString(output.resolve("goal18b-crystallizer-recipes.json"), CrystallizerRecipes.writeSnapshot());
        System.out.println("Goal18B recipes: " + checks + " assertions; " + scenarios + " independent scenarios; 0 executed ticks");
    }
}
