package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.CrystallizerRecipeClientSync;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.network.toclient.CrystallizerRecipesPacket;
import net.minecraft.core.registries.BuiltInRegistries;
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
import java.util.List;
import java.util.Set;

/** Goal20A: the five sulfuric acid uranium and thorium ore rows appended to the production crystallizer defaults, the frozen Goal18B rows, sync, the old-custom-table behavior and the merge record. */
public final class Goal20ARecipeRegression {
    private static int checks, scenarios;
    private Goal20ARecipeRegression() { }
    private static void check(boolean condition, String message) { checks++; if(!condition) throw new AssertionError(message); }
    private static void scenario() { scenarios++; }
    private static void rejects(String json, String label) {
        checks++;
        try { CrystallizerRecipes.readSnapshot(json); }
        catch(RuntimeException ex) { return; }
        throw new AssertionError("accepted invalid " + label);
    }
    private static String table(String... rows) { return "{\"recipes\":[" + String.join(",", rows) + "]}"; }
    private static String row(String input, String fluid, String output, String duration, String productivity) {
        return "{\"input\":" + input + ",\"fluid\":" + fluid + ",\"output\":" + output + ",\"duration\":" + duration + (productivity == null ? "" : ",\"productivity\":" + productivity) + "}";
    }

    private static final int FROZEN_ROWS = 36, NEW_ROWS = 5, ROWS = 41;
    /** The five new ore blocks in table order and their crystal; the ids, acid, amount, duration and productivity come from the numbers parsed from the original source (args[3]). */
    private static final Object[][] SPEC = {
        {NtmBlocks.ORE_URANIUM.get(), NtmItems.CRYSTAL_URANIUM}, {NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_URANIUM}, {NtmBlocks.ORE_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM},
        {NtmBlocks.ORE_THORIUM.get(), NtmItems.CRYSTAL_THORIUM}, {NtmBlocks.ORE_THORIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_THORIUM}};
    private static JsonObject expectation;
    private static String acidName;
    private static int amount, duration;
    private static float productivity;
    private static String[] inputIds = new String[NEW_ROWS], outputIds = new String[NEW_ROWS];

    private static String id(Item item) { return BuiltInRegistries.ITEM.getKey(item).toString(); }
    private static String path(String id) { return id.substring(id.indexOf(':') + 1); }
    private static String newKey(int n) { return "item:" + inputIds[n] + ":32767@" + acidName; }
    private static FluidType acid() { return Fluids.SULFURIC_ACID; }
    private static FluidType other() { return Fluids.PEROXIDE; }
    private static Item item(Object value) { return ((ItemLike) value).asItem(); }
    private static ItemStack stack(Object value) { return new ItemStack(item(value)); }
    private static void restoreDefaults() { CrystallizerRecipes handler = new CrystallizerRecipes(); handler.deleteRecipes(); handler.registerDefaults(); }
    private static JsonObject written(CrystallizerRecipe recipe) throws Exception {
        StringWriter out = new StringWriter();
        try(JsonWriter writer = new JsonWriter(out)) { writer.beginObject(); new CrystallizerRecipes().writeRecipe(recipe, writer); writer.endObject(); }
        return JsonParser.parseString(out.toString()).getAsJsonObject();
    }
    private static JsonArray rowsOf(String json) { return JsonParser.parseString(json).getAsJsonObject().getAsJsonArray("recipes"); }
    /** A new row exactly as the production writer formats it, built from the original-derived numbers. */
    private static String newRow(int n) {
        return row("[\"item\",\"" + inputIds[n] + "\",1,32767]", "[\"" + acidName + "\"," + amount + "]", "[\"" + outputIds[n] + "\",1,null]", String.valueOf(duration), expectation.get("productivity").getAsString());
    }

    private static void loadExpectation(Path file) throws Exception {
        scenario();
        expectation = JsonParser.parseString(Files.readString(file, StandardCharsets.UTF_8)).getAsJsonObject();
        acidName = expectation.get("acid").getAsString(); amount = expectation.get("amount").getAsInt();
        duration = expectation.get("duration").getAsInt(); productivity = expectation.get("productivity").getAsFloat();
        JsonArray rows = expectation.getAsJsonArray("rows");
        check(rows.size() == NEW_ROWS && SPEC.length == NEW_ROWS, "the original-derived expectation lists five new rows");
        for(int n = 0; n < NEW_ROWS; n++) {
            inputIds[n] = rows.get(n).getAsJsonObject().get("input").getAsString(); outputIds[n] = rows.get(n).getAsJsonObject().get("output").getAsString();
            check(id(item(SPEC[n][0])).equals(inputIds[n]) && id(item(SPEC[n][1])).equals(outputIds[n]), "fixture ore/crystal " + n + " are the expected ids " + inputIds[n] + " -> " + outputIds[n]);
        }
        check(acid().getInternalName().equals(acidName) && amount == 500 && duration == 600 && Float.floatToIntBits(productivity) == Float.floatToIntBits(0.05F), "the original numbers are 500 mB SULFURIC_ACID, 600 ticks, productivity 0.05");
    }

    private static void defaults() {
        scenario();
        List<CrystallizerRecipe> rows = CrystallizerRecipes.getDefaultRecipes();
        Set<String> keys = new HashSet<>();
        for(CrystallizerRecipe recipe : rows) keys.add(recipe.key());
        for(int n = 0; n < NEW_ROWS; n++) check(keys.contains(newKey(n)), "row " + newKey(n) + " is in the default table");
        check(rows.size() == ROWS, "the default table has 41 rows (36 frozen Goal18B rows + 5 Goal20A rows)");
        check(keys.size() == ROWS, "41 distinct input/acid keys");
        for(int n = 0; n < NEW_ROWS; n++) {
            int index = FROZEN_ROWS + n;
            CrystallizerRecipe recipe = rows.get(index);
            Block block = (Block) SPEC[n][0];
            String at = "row " + index + " " + path(inputIds[n]);
            check(recipe.key().equals(newKey(n)) && recipe.input instanceof ComparableStack c && c.item == block.asItem() && c.stacksize == 1 && c.meta == MetaHelper.WILDCARD_VALUE && recipe.itemAmount() == 1, at + ": exactly 1 ore block with the wildcard META, in table order");
            check(recipe.fluid.type == acid() && recipe.acidType() == acid() && recipe.fluid.fill == amount && recipe.acidAmount() == amount && recipe.fluid.pressure == 0, at + ": " + amount + " mB " + acidName);
            check(recipe.output.getItem() == item(SPEC[n][1]) && recipe.output.getCount() == 1 && !recipe.output.has(NtmDataComponents.META.get()), at + ": one plain " + path(outputIds[n]));
            check(recipe.duration == duration && Float.floatToIntBits(recipe.productivity) == Float.floatToIntBits(productivity), at + ": " + duration + " ticks, productivity " + productivity);
            ItemStack ore = new ItemStack(block.asItem());
            check(CrystallizerRecipes.getOutput(rows, ore, acid()) == recipe, at + ": lookup resolves its own row under " + acidName);
            check(CrystallizerRecipes.getOutput(rows, ore, other()) == null, at + ": no row under " + other().getInternalName());
            check(CrystallizerRecipes.getOutput(rows, MetaHelper.newStack(block.asItem(), 1, 5), acid()) == recipe, at + ": the wildcard row accepts any META");
        }
        // Crystals, powders, ingots, the plutonium ore and plain deepslate stay out under both acids.
        List<Item> excluded = List.of(NtmItems.CRYSTAL_URANIUM.get(), NtmItems.CRYSTAL_THORIUM.get(), NtmItems.POWDER_URANIUM.get(), NtmItems.POWDER_THORIUM.get(), NtmItems.INGOT_URANIUM.get(),
            NtmBlocks.ORE_NETHER_PLUTONIUM.get().asItem(), Blocks.DEEPSLATE.asItem(),
            // Registered in NEO but deliberately without a default row (no language key, creative-tab entry or world generation): excluded inputs.
            NtmBlocks.ORE_GNEISS_URANIUM.get().asItem(), NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get().asItem(), NtmBlocks.ORE_NETHER_URANIUM.get().asItem(), NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get().asItem());
        for(Item excludedItem : excluded) {
            ItemStack probe = new ItemStack(excludedItem);
            check(CrystallizerRecipes.getOutput(rows, probe, Fluids.PEROXIDE) == null && CrystallizerRecipes.getOutput(rows, probe, Fluids.SULFURIC_ACID) == null
                    && !CrystallizerRecipes.hasRecipeForAnyAcid(rows, probe), "unlisted input is not accepted under either acid: " + id(excludedItem));
        }
        CrystallizerRecipes handler = new CrystallizerRecipes();
        handler.deleteRecipes(); handler.registerDefaults();
        check(CrystallizerRecipes.getJeiRecipes().size() == ROWS && handler.getFileName().equals("hbmCrystallizer.json"), "static table registers the 41 defaults under hbmCrystallizer.json");
        String comment = handler.getComment();
        check(comment != null && comment.contains("41 rows") && !comment.contains("36 rows") && !comment.contains("45 rows") && comment.contains("uranium"), "the config comment says 45 rows and names the uranium rows");
        ItemStack uranium = stack(NtmBlocks.ORE_URANIUM.get()), coal = stack(Blocks.COAL_ORE), tungsten = stack(NtmBlocks.ORE_TUNGSTEN.get());
        check(CrystallizerRecipes.hasRecipe(uranium, Fluids.SULFURIC_ACID) && !CrystallizerRecipes.hasRecipe(uranium, Fluids.PEROXIDE) && CrystallizerRecipes.hasRecipe(coal, Fluids.PEROXIDE)
                && CrystallizerRecipes.hasRecipe(tungsten, Fluids.SULFURIC_ACID), "the machine lookup filters by the tank's acid type; the older groups still resolve");
    }

    private static void frozen18B(Path frozen) throws Exception {
        scenario();
        String frozenText = Files.readString(frozen, StandardCharsets.UTF_8);
        JsonArray old = rowsOf(frozenText);
        restoreDefaults();
        JsonArray live = rowsOf(CrystallizerRecipes.writeSnapshot());
        check(old.size() == FROZEN_ROWS && live.size() == ROWS, "frozen Goal18B export has 36 rows, the Goal20A table 41");
        for(int i = 0; i < FROZEN_ROWS; i++) check(live.get(i).equals(old.get(i)), "Goal18B row " + i + " is unchanged and in place: " + live.get(i));
        for(int n = 0; n < NEW_ROWS; n++) check(live.get(FROZEN_ROWS + n).equals(JsonParser.parseString(newRow(n))), "row " + (FROZEN_ROWS + n) + " is the appended sulfuric acid row: " + live.get(FROZEN_ROWS + n));
        List<CrystallizerRecipe> frozenRows = CrystallizerRecipes.readSnapshot(frozenText), defaults = CrystallizerRecipes.getDefaultRecipes();
        for(int i = 0; i < FROZEN_ROWS; i++) check(frozenRows.get(i).sameRecipe(defaults.get(i)), "frozen Goal18B row " + i + " reads back as the same default row");
    }

    private static void roundTrip() throws Exception {
        scenario();
        restoreDefaults();
        String json = CrystallizerRecipes.writeSnapshot();
        List<CrystallizerRecipe> back = CrystallizerRecipes.readSnapshot(json), live = CrystallizerRecipes.getJeiRecipes();
        check(back.size() == ROWS && live.size() == ROWS, "snapshot carries 41 rows");
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
        check(decoded.json().equals(json) && decoded.type() == CrystallizerRecipesPacket.TYPE, "packet codec round trip of the 41-row snapshot");
        ItemStack uranium = stack(NtmBlocks.ORE_URANIUM.get()), scorched = stack(NtmBlocks.ORE_URANIUM_SCORCHED.get()), thoriumDeep = stack(NtmBlocks.ORE_THORIUM_DEEPSLATE.get());
        ItemStack tungsten = stack(NtmBlocks.ORE_TUNGSTEN.get()), coal = stack(Blocks.COAL_ORE);
        goal18a.JeiBridge bridge = new goal18a.JeiBridge();
        CrystallizerRecipeClientSync.disconnect(null);
        check(CrystallizerRecipeClientSync.getRecipes().size() == ROWS && CrystallizerRecipeClientSync.hasRecipe(uranium, Fluids.SULFURIC_ACID), "client defaults before any snapshot carry the uranium and thorium sulfuric acid rows");
        bridge.available();
        check(bridge.runtime.additions == ROWS && bridge.displayedCrystallizerRecipes.size() == ROWS, "JEI runtime shows the 41 default rows");
        check(CrystallizerRecipeClientSync.receive(decoded.json()), "the decoded 41-row snapshot is accepted");
        List<CrystallizerRecipe> client = CrystallizerRecipeClientSync.getRecipes();
        check(client.size() == ROWS, "client table holds 41 recipes");
        for(int i = 0; i < ROWS; i++) check(client.get(i).sameRecipe(defaults.get(i)), "client row " + i + " equals the server default");
        check(CrystallizerRecipeClientSync.hasRecipe(uranium, Fluids.SULFURIC_ACID) && !CrystallizerRecipeClientSync.hasRecipe(uranium, Fluids.PEROXIDE), "uranium ore resolves under sulfuric acid only");
        check(CrystallizerRecipeClientSync.getOutput(scorched, Fluids.SULFURIC_ACID).output.getItem() == NtmItems.CRYSTAL_URANIUM.get() && CrystallizerRecipeClientSync.getOutput(thoriumDeep, Fluids.SULFURIC_ACID).output.getItem() == NtmItems.CRYSTAL_THORIUM.get()
                && CrystallizerRecipeClientSync.hasRecipe(coal, Fluids.PEROXIDE), "client prediction covers the scorched uranium and deepslate thorium rows and both acids");
        check(bridge.runtime.additions == ROWS && bridge.displayedCrystallizerRecipes.size() == ROWS, "identical rows are reused, not re-added to JEI");
        // A server whose table lacks the Goal20A rows (the Goal18B export, like an old custom file) is authoritative.
        check(CrystallizerRecipeClientSync.receive(Files.readString(frozen, StandardCharsets.UTF_8)) && CrystallizerRecipeClientSync.getRecipes().size() == FROZEN_ROWS
                && !CrystallizerRecipeClientSync.hasRecipe(uranium, Fluids.SULFURIC_ACID) && CrystallizerRecipeClientSync.hasRecipe(tungsten, Fluids.SULFURIC_ACID) && CrystallizerRecipeClientSync.hasRecipe(coal, Fluids.PEROXIDE), "a 36-row server table does not gain the uranium and thorium rows on the client");
        check(bridge.displayedCrystallizerRecipes.size() == FROZEN_ROWS && bridge.runtime.additions == ROWS, "JEI hides the five Goal20A rows");
        check(!CrystallizerRecipeClientSync.receive("{\"recipes\":[") && CrystallizerRecipeClientSync.getRecipes().size() == FROZEN_ROWS, "a malformed payload is ignored and the previous table kept");
        check(CrystallizerRecipeClientSync.receive(table()) && CrystallizerRecipeClientSync.getRecipes().isEmpty() && bridge.displayedCrystallizerRecipes.isEmpty(), "an empty legal snapshot clears the client table and JEI");
        check(CrystallizerRecipeClientSync.receive(json) && CrystallizerRecipeClientSync.getRecipes().size() == ROWS && bridge.runtime.additions == ROWS && bridge.displayedCrystallizerRecipes.size() == ROWS, "the 41 rows return without re-adding");
        check(CrystallizerRecipes.getJeiRecipes().size() == ROWS, "client snapshots never touch the server table");
        bridge.unavailable();
        CrystallizerRecipeClientSync.disconnect(null);
        check(CrystallizerRecipeClientSync.getRecipes().size() == ROWS, "logout restores the 41 defaults");
    }

    /** A custom hbmCrystallizer.json that holds only the old 36 rows replaces the whole table and does not grow. */
    private static void oldCustomTable(Path frozen) throws Exception {
        scenario();
        String frozenText = Files.readString(frozen, StandardCharsets.UTF_8);
        ItemStack uranium = stack(NtmBlocks.ORE_URANIUM.get()), thorium = stack(NtmBlocks.ORE_THORIUM.get()), tungsten = stack(NtmBlocks.ORE_TUNGSTEN.get()), coal = stack(Blocks.COAL_ORE);
        restoreDefaults();
        CrystallizerRecipes handler = new CrystallizerRecipes();
        handler.readRecipeStream(new StringReader(frozenText));
        check(CrystallizerRecipes.getJeiRecipes().size() == FROZEN_ROWS && !CrystallizerRecipes.hasRecipe(uranium, Fluids.SULFURIC_ACID) && !CrystallizerRecipes.hasRecipe(thorium, Fluids.SULFURIC_ACID)
                && CrystallizerRecipes.hasRecipe(tungsten, Fluids.SULFURIC_ACID) && CrystallizerRecipes.hasRecipe(coal, Fluids.PEROXIDE), "a custom table holding only the old 36 rows yields a 36-row table (no automatic growth)");
        restoreDefaults();
        Path dir = Files.createTempDirectory("goal20a-recipes");
        Path file = dir.resolve("hbmCrystallizer.json");
        Files.writeString(file, frozenText, StandardCharsets.UTF_8);
        check(handler.readRecipeFile(file.toFile()) && CrystallizerRecipes.getJeiRecipes().size() == FROZEN_ROWS && !CrystallizerRecipes.hasRecipe(uranium, Fluids.SULFURIC_ACID), "the same file through the config-file path also stays at 36 rows");
        for(int n = 0; n < NEW_ROWS; n++) check(!CrystallizerRecipes.hasRecipe(stack(SPEC[n][0]), Fluids.SULFURIC_ACID), "36-row custom table has no row for " + path(inputIds[n]));
        Files.delete(file); Files.delete(dir);
        restoreDefaults();
        check(CrystallizerRecipes.getJeiRecipes().size() == ROWS, "defaults restore after the old-custom-table scenario");
    }

    private static void mergeExample(Path merge) throws Exception {
        scenario();
        restoreDefaults();
        List<CrystallizerRecipe> defaults = CrystallizerRecipes.getDefaultRecipes();
        String text = Files.readString(merge, StandardCharsets.UTF_8);
        JsonObject record = JsonParser.parseString(text).getAsJsonObject();
        check(record.keySet().equals(Set.of("comment", "recipes")) && record.get("comment").getAsString().contains("SULFURIC_ACID"), "merge record is {comment, recipes} like the Goal18B example");
        int[] expected = new int[2 + NEW_ROWS];
        expected[0] = 0; expected[1] = 3;
        for(int n = 0; n < NEW_ROWS; n++) expected[2 + n] = FROZEN_ROWS + n;
        List<CrystallizerRecipe> rows = CrystallizerRecipes.readSnapshot(text);
        JsonArray raw = record.getAsJsonArray("recipes");
        check(rows.size() == expected.length && raw.size() == expected.length, "two kept rows plus the five Goal20A rows");
        for(int i = 0; i < expected.length; i++) {
            check(rows.get(i).sameRecipe(defaults.get(expected[i])), "merge row " + i + " parses to default row " + expected[i]);
            check(raw.get(i).equals(written(defaults.get(expected[i]))), "merge row " + i + " is the production writer's row " + expected[i]);
        }
        ItemStack gold = stack(Blocks.GOLD_ORE), coal = stack(Blocks.COAL_ORE), deepIron = stack(Blocks.DEEPSLATE_IRON_ORE), iron = stack(Blocks.IRON_ORE), uranium = stack(NtmBlocks.ORE_URANIUM.get()), tungsten = stack(NtmBlocks.ORE_TUNGSTEN.get());
        // Before the merge: the existing custom table (the two kept rows) replaces the defaults and gains nothing automatically.
        CrystallizerRecipes handler = new CrystallizerRecipes();
        handler.readRecipeStream(new StringReader(table(raw.get(0).toString(), raw.get(1).toString())));
        check(CrystallizerRecipes.getJeiRecipes().size() == 2 && !CrystallizerRecipes.hasRecipe(uranium, Fluids.SULFURIC_ACID) && !CrystallizerRecipes.hasRecipe(gold, Fluids.PEROXIDE)
                && CrystallizerRecipes.hasRecipe(coal, Fluids.PEROXIDE), "an existing custom table does not gain the uranium and thorium rows");
        // After the merge: the record loads through the config-file path and carries the five rows beside the kept rows.
        check(handler.readRecipeFile(merge.toFile()) && CrystallizerRecipes.getJeiRecipes().size() == expected.length, "the merged record loads through the config-file path");
        for(int n = 0; n < NEW_ROWS; n++) {
            ItemStack ore = stack(SPEC[n][0]);
            CrystallizerRecipe found = CrystallizerRecipes.getOutput(ore, Fluids.SULFURIC_ACID);
            check(found != null && found.output.getItem() == item(SPEC[n][1]) && !CrystallizerRecipes.hasRecipe(ore, Fluids.PEROXIDE), "merged sulfuric acid row " + path(inputIds[n]));
        }
        check(CrystallizerRecipes.hasRecipe(coal, Fluids.PEROXIDE) && CrystallizerRecipes.hasRecipe(deepIron, Fluids.PEROXIDE) && !CrystallizerRecipes.hasRecipe(iron, Fluids.PEROXIDE)
                && !CrystallizerRecipes.hasRecipe(tungsten, Fluids.SULFURIC_ACID), "the merged table keeps only the player's rows plus the appended rows");
        restoreDefaults();
        check(CrystallizerRecipes.getJeiRecipes().size() == ROWS, "defaults restore after the merge scenario");
    }

    /** Server-side config paths for the new rows: custom empty table, strict rejection of a duplicate key, same ore under the other acid. */
    private static void configPaths() throws Exception {
        scenario();
        ItemStack scorched = stack(NtmBlocks.ORE_URANIUM_SCORCHED.get()), coal = stack(Blocks.COAL_ORE), uranium = stack(NtmBlocks.ORE_URANIUM.get());
        String good = newRow(2);
        String duplicate = row("[\"item\",\"" + inputIds[2] + "\"]", "[\"" + acidName + "\",250]", "[\"" + outputIds[2] + "\",2,null]", "300", "0.1");
        restoreDefaults();
        CrystallizerRecipes handler = new CrystallizerRecipes();
        handler.readRecipeStream(new StringReader(table()));
        check(CrystallizerRecipes.getJeiRecipes().isEmpty() && !CrystallizerRecipes.hasRecipe(uranium, Fluids.SULFURIC_ACID) && !CrystallizerRecipes.hasRecipe(coal, Fluids.PEROXIDE), "a custom empty table disables every default, the uranium and thorium rows included");
        rejects(table(good, duplicate), "duplicate ore_uranium_scorched@SULFURIC_ACID key");
        List<CrystallizerRecipe> distinct = CrystallizerRecipes.readSnapshot(table(good, row("[\"item\",\"" + inputIds[2] + "\"]", "[\"PEROXIDE\",500]", "[\"" + outputIds[2] + "\"]", "600", null)));
        check(distinct.size() == 2 && CrystallizerRecipes.getOutput(distinct, scorched, Fluids.PEROXIDE) == distinct.get(1) && CrystallizerRecipes.getOutput(distinct, scorched, Fluids.SULFURIC_ACID) == distinct.get(0), "the same ore under the other acid is a distinct key");
        restoreDefaults();
        check(CrystallizerRecipes.getJeiRecipes().size() == ROWS, "defaults restore after the config-path scenario");
    }

    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[0]), frozen = Path.of(args[1]), merge = Path.of(args[2]), expected = Path.of(args[3]);
        loadExpectation(expected);
        defaults(); frozen18B(frozen); roundTrip(); sync(frozen); oldCustomTable(frozen); mergeExample(merge); configPaths();
        restoreDefaults();
        Files.writeString(output.resolve("goal20a-crystallizer-recipes.json"), CrystallizerRecipes.writeSnapshot());
        System.out.println("Goal20A recipes: " + checks + " assertions; " + scenarios + " independent scenarios; 0 executed ticks");
    }
}
