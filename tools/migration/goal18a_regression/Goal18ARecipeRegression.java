package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.handler.CrystallizerRecipeClientSync;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.network.toclient.CrystallizerRecipesPacket;
import com.hbm.util.TagsUtil;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;

import java.io.File;
import java.io.StringReader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Production crystallizer table, strict/lenient readers, writer, snapshot sync, client table, JEI bridge and the assembly row. */
public final class Goal18ARecipeRegression {
    private static int checks, scenarios;
    private Goal18ARecipeRegression() { }
    private static void check(boolean condition, String message) { checks++; if(!condition) throw new AssertionError(message); }
    private static void scenario() { scenarios++; }
    private static void rejects(String json, String label) {
        checks++;
        // Gson syntax errors and the contract's IllegalArgumentException are both RuntimeExceptions: the file loader falls back and the client sync ignores either.
        try { CrystallizerRecipes.readSnapshot(json); }
        catch(RuntimeException ex) { return; }
        throw new AssertionError("accepted invalid " + label);
    }
    private static String table(String... rows) { return "{\"recipes\":[" + String.join(",", rows) + "]}"; }
    private static String row(String input, String fluid, String output, String duration, String productivity) {
        return "{\"input\":" + input + ",\"fluid\":" + fluid + ",\"output\":" + output + ",\"duration\":" + duration + (productivity == null ? "" : ",\"productivity\":" + productivity) + "}";
    }
    private static final String COAL = "[\"item\",\"minecraft:coal_ore\",1,32767]", PEROXIDE = "[\"PEROXIDE\",500]", CRYSTAL_COAL = "[\"hbmsntm:crystal_coal\",1,null]";

    private static final Object[][] EXPECTED = {
        {Blocks.COAL_ORE, Blocks.DEEPSLATE_COAL_ORE, NtmItems.CRYSTAL_COAL}, {Blocks.IRON_ORE, Blocks.DEEPSLATE_IRON_ORE, NtmItems.CRYSTAL_IRON},
        {Blocks.GOLD_ORE, Blocks.DEEPSLATE_GOLD_ORE, NtmItems.CRYSTAL_GOLD}, {Blocks.REDSTONE_ORE, Blocks.DEEPSLATE_REDSTONE_ORE, NtmItems.CRYSTAL_REDSTONE},
        {Blocks.LAPIS_ORE, Blocks.DEEPSLATE_LAPIS_ORE, NtmItems.CRYSTAL_LAPIS}, {Blocks.DIAMOND_ORE, Blocks.DEEPSLATE_DIAMOND_ORE, NtmItems.CRYSTAL_DIAMOND},
        {NtmBlocks.ORE_SULFUR.get(), NtmBlocks.ORE_SULFUR_DEEPSLATE.get(), NtmItems.CRYSTAL_SULFUR}, {NtmBlocks.ORE_NITER.get(), NtmBlocks.ORE_NITER_DEEPSLATE.get(), NtmItems.CRYSTAL_NITER},
        {Blocks.COPPER_ORE, Blocks.DEEPSLATE_COPPER_ORE, NtmItems.CRYSTAL_COPPER}, {NtmBlocks.ORE_ALUMINIUM.get(), NtmBlocks.ORE_ALUMINIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_ALUMINIUM},
        {NtmBlocks.ORE_FLUORITE.get(), NtmBlocks.ORE_FLUORITE_DEEPSLATE.get(), NtmItems.CRYSTAL_FLUORITE}, {NtmBlocks.ORE_BERYLLIUM.get(), NtmBlocks.ORE_BERYLLIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_BERYLLIUM},
        {NtmBlocks.ORE_LEAD.get(), NtmBlocks.ORE_LEAD_DEEPSLATE.get(), NtmItems.CRYSTAL_LEAD}, {NtmBlocks.ORE_CINNABAR.get(), NtmBlocks.ORE_CINNABAR_DEEPSLATE.get(), NtmItems.CRYSTAL_CINNABAR}};

    private static Item item(Object crystal) { return ((net.minecraft.world.level.ItemLike) crystal).asItem(); }

    private static void defaults() {
        scenario();
        List<CrystallizerRecipe> rows = CrystallizerRecipes.getDefaultRecipes();
        check(rows.size() == 28 && EXPECTED.length == 14, "fourteen groups as 28 stone/deepslate rows");
        for(int group = 0; group < 14; group++) for(int variant = 0; variant < 2; variant++) {
            CrystallizerRecipe recipe = rows.get(group * 2 + variant);
            Block block = (Block) EXPECTED[group][variant];
            check(recipe.input instanceof ComparableStack c && c.item == block.asItem() && c.stacksize == 1 && c.meta == MetaHelper.WILDCARD_VALUE, "exact ore block input in original order " + group + "/" + variant);
            check(recipe.fluid.type == Fluids.PEROXIDE && recipe.fluid.fill == 500 && recipe.acidAmount() == 500, "500 mB hydrogen peroxide " + group);
            check(recipe.output.getItem() == item(EXPECTED[group][2]) && recipe.output.getCount() == 1 && !recipe.output.has(NtmDataComponents.META.get()), "one plain crystal " + group);
            check(recipe.duration == 600 && Float.floatToIntBits(recipe.productivity) == Float.floatToIntBits(0.05F), "600 ticks, productivity 0.05 " + group);
            check(CrystallizerRecipes.getOutput(rows, new ItemStack(block.asItem()), Fluids.PEROXIDE) == recipe, "lookup resolves its own row " + group + "/" + variant);
            check(CrystallizerRecipes.getOutput(rows, new ItemStack(block.asItem()), Fluids.SULFURIC_ACID) == null, "no sulfuric row by default " + group);
            check(CrystallizerRecipes.getOutput(rows, new ItemStack(item(EXPECTED[group][2])), Fluids.PEROXIDE) == null, "crystals are not inputs " + group);
        }
        for(Item excluded : new Item[]{Items.RAW_IRON, Items.RAW_COPPER, Items.RAW_GOLD, Blocks.NETHER_GOLD_ORE.asItem(), Items.COAL, Items.REDSTONE, NtmItems.SULFUR.get(), NtmItems.NITER.get(), NtmItems.CINNABAR.get(), NtmBlocks.ORE_LIGNITE.get().asItem(), NtmBlocks.ORE_METEOR_IRON.get().asItem(), Items.STICK}) {
            check(CrystallizerRecipes.getOutput(rows, new ItemStack(excluded), Fluids.PEROXIDE) == null && !CrystallizerRecipes.hasRecipeForAnyAcid(rows, new ItemStack(excluded)), "unlisted variant is not accepted: " + excluded);
        }
        check(CrystallizerRecipes.hasRecipeForAnyAcid(rows, new ItemStack(Blocks.IRON_ORE.asItem())) && !CrystallizerRecipes.hasRecipeForAnyAcid(rows, ItemStack.EMPTY), "any-acid prediction");
        check(CrystallizerRecipes.getOutput(rows, ItemStack.EMPTY, Fluids.PEROXIDE) == null && CrystallizerRecipes.getOutput(rows, new ItemStack(Blocks.IRON_ORE.asItem()), null) == null, "empty stack or null acid resolve nothing");
        CrystallizerRecipes handler = new CrystallizerRecipes();
        handler.deleteRecipes(); handler.registerDefaults();
        check(CrystallizerRecipes.getJeiRecipes().size() == 28 && handler.getFileName().equals("hbmCrystallizer.json") && handler.getComment() != null, "static table registers the 28 defaults under hbmCrystallizer.json");
    }

    private static JsonObject written(CrystallizerRecipe recipe) throws Exception {
        StringWriter out = new StringWriter();
        try(JsonWriter writer = new JsonWriter(out)) { writer.beginObject(); new CrystallizerRecipes().writeRecipe(recipe, writer); writer.endObject(); }
        return JsonParser.parseString(out.toString()).getAsJsonObject();
    }
    private static void roundTrip() throws Exception {
        scenario();
        new CrystallizerRecipes().deleteRecipes(); new CrystallizerRecipes().registerDefaults();
        String json = CrystallizerRecipes.writeSnapshot();
        List<CrystallizerRecipe> back = CrystallizerRecipes.readSnapshot(json);
        List<CrystallizerRecipe> live = CrystallizerRecipes.getJeiRecipes();
        check(back.size() == 28, "snapshot carries 28 rows");
        for(int i = 0; i < 28; i++) check(back.get(i).sameRecipe(live.get(i)), "row " + i + " survives the writer/reader round trip");
        JsonObject first = written(live.get(0));
        check(first.get("input").toString().equals(COAL) && first.get("fluid").toString().equals(PEROXIDE) && first.get("output").toString().equals(CRYSTAL_COAL)
                && first.get("duration").getAsInt() == 600 && Math.abs(first.get("productivity").getAsFloat() - 0.05F) < 1e-7, "written row shape: " + first);
        check(CrystallizerRecipes.encodeSnapshot(json).length == json.getBytes(StandardCharsets.UTF_8).length, "UTF-8 snapshot bytes");
        // Explicit values, omitted optional values and the custom-component output all round trip exactly.
        scenario();
        String custom = table(
            row("[\"item\",\"minecraft:iron_ore\"]", "[\"SULFURIC_ACID\",8000]", "[\"hbmsntm:crystal_iron\",16,3,\"{note:1}\"]", "1000000", "1"),
            row("[\"item\",\"minecraft:iron_ore\",2,0]", PEROXIDE, "[\"hbmsntm:crystal_iron\"]", "1", null),
            row("[\"tag\",\"c:ores/iron\",3]", PEROXIDE, "[\"hbmsntm:crystal_gold\",2]", "20", "0.5"));
        List<CrystallizerRecipe> rows = CrystallizerRecipes.readSnapshot(custom);
        check(rows.size() == 3, "three custom rows");
        CrystallizerRecipe a = rows.get(0), b = rows.get(1), c = rows.get(2);
        check(a.input instanceof ComparableStack ca && ca.meta == MetaHelper.WILDCARD_VALUE && ca.stacksize == 1 && a.fluid.type == Fluids.SULFURIC_ACID && a.fluid.fill == 8000 && a.duration == 1000000 && a.productivity == 1F, "omitted count/META default to 1 and the wildcard; bounds inclusive");
        check(a.output.getCount() == 16 && MetaHelper.getMeta(a.output) == 3 && TagsUtil.hasCustomData(a.output) && TagsUtil.getCustomData(a.output).getInt("note") == 1, "META and custom data output decoded");
        check(b.input instanceof ComparableStack cb && cb.meta == 0 && cb.stacksize == 2 && b.productivity == 0F && !b.output.has(NtmDataComponents.META.get()), "explicit META 0, count 2, omitted productivity 0, plain output");
        check(c.input instanceof TagStack tc && tc.tag.location().toString().equals("c:ores/iron") && tc.stacksize == 3 && c.output.getCount() == 2, "tag input with count");
        JsonObject wa = written(a), wb = written(b), wc = written(c);
        check(wa.get("input").toString().equals("[\"item\",\"minecraft:iron_ore\",1,32767]") && wa.get("output").toString().equals("[\"hbmsntm:crystal_iron\",16,3,\"{note:1}\"]"), "writer makes the wildcard and components explicit: " + wa);
        check(wb.get("input").toString().equals("[\"item\",\"minecraft:iron_ore\",2,0]") && wb.get("output").toString().equals("[\"hbmsntm:crystal_iron\",1,null]"), "writer keeps META 0 distinct from no META: " + wb);
        check(wc.get("input").toString().equals("[\"tag\",\"c:ores/iron\",3]"), "writer keeps the tag row: " + wc);
        List<CrystallizerRecipe> again = CrystallizerRecipes.readSnapshot(table(wa.toString(), wb.toString(), wc.toString()));
        for(int i = 0; i < 3; i++) check(again.get(i).sameRecipe(rows.get(i)), "custom row " + i + " is stable across a second round trip");
        // Same input, two acids: both rows resolve by the tank type; the first registered row wins among equal keys only if duplicates were allowed, which they are not.
        check(CrystallizerRecipes.getOutput(rows, new ItemStack(Blocks.IRON_ORE.asItem()), Fluids.SULFURIC_ACID) == a && CrystallizerRecipes.getOutput(rows, new ItemStack(Blocks.IRON_ORE.asItem()), Fluids.PEROXIDE) == b, "same input resolves per acid");
        check(CrystallizerRecipes.getOutput(rows, MetaHelper.newStack(Blocks.IRON_ORE.asItem(), 1, 5), Fluids.PEROXIDE) == null && CrystallizerRecipes.getOutput(rows, MetaHelper.newStack(Blocks.IRON_ORE.asItem(), 1, 5), Fluids.SULFURIC_ACID) == a, "META 0 row rejects META 5; wildcard row accepts it");
        // Tag membership binds through the registry service; untagged items stay out.
        Item ironOre = Blocks.IRON_ORE.asItem();
        ironOre.tags.add("c:ores/iron"); RecipesCommon.TAG_MEMBERS.put("c:ores/iron", List.of(ironOre));
        check(c.matches(new ItemStack(ironOre), Fluids.PEROXIDE) && !c.matches(new ItemStack(Items.RAW_IRON), Fluids.PEROXIDE) && !c.matches(new ItemStack(ironOre), Fluids.SULFURIC_ACID), "tag row matches tagged members with the right acid only");
        check(c.input.extractForJEI().size() == 1 && c.input.extractForJEI().get(0).getCount() == 3, "tag JEI display lists the bound member with the row count");
        ironOre.tags.remove("c:ores/iron"); RecipesCommon.TAG_MEMBERS.remove("c:ores/iron");
    }
    private static void strict() {
        scenario();
        rejects(table(row("[\"item\",\"minecraft:does_not_exist\"]", PEROXIDE, CRYSTAL_COAL, "600", "0.05")), "unknown item");
        rejects(table(row("[\"item\",\"minecraft:air\"]", PEROXIDE, CRYSTAL_COAL, "600", null)), "air input");
        rejects(table(row("[\"item\",\"minecraft:coal_ore\",0]", PEROXIDE, CRYSTAL_COAL, "600", null)), "zero input count");
        rejects(table(row("[\"item\",\"minecraft:coal_ore\",65]", PEROXIDE, CRYSTAL_COAL, "600", null)), "input count over 64");
        rejects(table(row("[\"item\",\"minecraft:coal_ore\",1,-1]", PEROXIDE, CRYSTAL_COAL, "600", null)), "negative META");
        rejects(table(row("[\"item\",\"minecraft:coal_ore\",1,32767,\"extra\"]", PEROXIDE, CRYSTAL_COAL, "600", null)), "five item entries");
        rejects(table(row("[\"tag\",\"c:ores/coal\",1,0]", PEROXIDE, CRYSTAL_COAL, "600", null)), "tag with META");
        rejects(table(row("[\"dict\",\"oreCoal\"]", PEROXIDE, CRYSTAL_COAL, "600", null)), "unsupported input kind");
        rejects(table(row("[\"item\"]", PEROXIDE, CRYSTAL_COAL, "600", null)), "input without id");
        rejects(table(row(COAL, "[\"UNOBTAINIUM\",500]", CRYSTAL_COAL, "600", null)), "unknown acid");
        rejects(table(row(COAL, "[\"NONE\",500]", CRYSTAL_COAL, "600", null)), "NONE acid");
        rejects(table(row(COAL, "[\"peroxide\",500]", CRYSTAL_COAL, "600", null)), "acid name must be the internal name");
        rejects(table(row(COAL, "[\"PEROXIDE\",0]", CRYSTAL_COAL, "600", null)), "zero acid");
        rejects(table(row(COAL, "[\"PEROXIDE\",8001]", CRYSTAL_COAL, "600", null)), "acid above the 8,000 mB tank");
        rejects(table(row(COAL, "[\"PEROXIDE\",500,0]", CRYSTAL_COAL, "600", null)), "pressure entry");
        rejects(table(row(COAL, "[\"PEROXIDE\"]", CRYSTAL_COAL, "600", null)), "acid without amount");
        rejects(table(row(COAL, PEROXIDE, "[\"minecraft:air\",1]", "600", null)), "air output");
        rejects(table(row(COAL, PEROXIDE, "[\"hbmsntm:crystal_coal\",0]", "600", null)), "zero output");
        rejects(table(row(COAL, PEROXIDE, "[\"hbmsntm:crystal_coal\",65]", "600", null)), "output over 64");
        rejects(table(row(COAL, PEROXIDE, "[\"hbmsntm:crystal_coal\",1,-2]", "600", null)), "negative output META");
        rejects(table(row(COAL, PEROXIDE, "[\"hbmsntm:crystal_coal\",1,null,\"{broken\"]", "600", null)), "invalid SNBT");
        rejects(table(row(COAL, PEROXIDE, "[\"hbmsntm:nothing_here\"]", "600", null)), "unknown output item");
        rejects(table(row(COAL, PEROXIDE, CRYSTAL_COAL, "0", null)), "zero duration");
        rejects(table(row(COAL, PEROXIDE, CRYSTAL_COAL, "1000001", null)), "duration over the bound");
        rejects(table(row(COAL, PEROXIDE, CRYSTAL_COAL, "60.5", null)), "fractional duration");
        rejects(table(row(COAL, PEROXIDE, CRYSTAL_COAL, "600", "-0.1")), "negative productivity");
        rejects(table(row(COAL, PEROXIDE, CRYSTAL_COAL, "600", "1.5")), "productivity above 1");
        rejects(table(row(COAL, PEROXIDE, CRYSTAL_COAL, "600", "\"0.05\"")), "string productivity");
        rejects(table("{\"input\":" + COAL + ",\"fluid\":" + PEROXIDE + ",\"output\":" + CRYSTAL_COAL + "}"), "missing duration");
        rejects(table("{\"fluid\":" + PEROXIDE + ",\"output\":" + CRYSTAL_COAL + ",\"duration\":600}"), "missing input");
        rejects(table("{\"input\":" + COAL + ",\"output\":" + CRYSTAL_COAL + ",\"duration\":600}"), "missing fluid");
        rejects(table("{\"input\":" + COAL + ",\"fluid\":" + PEROXIDE + ",\"duration\":600}"), "missing output");
        rejects(table("5"), "row is not an object");
        rejects("{\"rows\":[]}", "missing recipes array");
        rejects("[]", "table is not an object");
        rejects(table(row(COAL, PEROXIDE, CRYSTAL_COAL, "600", null), row(COAL, PEROXIDE, "[\"hbmsntm:crystal_iron\"]", "100", null)), "duplicate input/acid key");
        rejects(table(row("[\"item\",\"minecraft:coal_ore\",1,32767]", PEROXIDE, CRYSTAL_COAL, "600", null), row("[\"item\",\"minecraft:coal_ore\",5,32767]", PEROXIDE, CRYSTAL_COAL, "600", null)), "duplicate key with another count");
        StringBuilder many = new StringBuilder("{\"recipes\":[");
        for(int i = 0; i < 4097; i++) { if(i > 0) many.append(','); many.append(row("[\"item\",\"minecraft:coal_ore\",1," + i + "]", PEROXIDE, CRYSTAL_COAL, "600", null)); }
        rejects(many.append("]}").toString(), "4,097 rows");
        rejects("{\"recipes\":[" + " ".repeat(256 * 1024) + "]}", "256 KiB snapshot");
        rejects("{\"recipes\":[],\"comment\":\"\uD800\"}", "lone surrogate");
        check(CrystallizerRecipes.readSnapshot(table()).isEmpty(), "an empty table is a legal, empty snapshot");
        List<CrystallizerRecipe> distinct = CrystallizerRecipes.readSnapshot(table(row(COAL, PEROXIDE, CRYSTAL_COAL, "600", null), row(COAL, "[\"SULFURIC_ACID\",250]", "[\"hbmsntm:crystal_iron\"]", "100", null), row("[\"tag\",\"c:ores/coal\"]", PEROXIDE, CRYSTAL_COAL, "600", null)));
        check(distinct.size() == 3, "same item under another acid and a tag row are distinct keys");
    }
    private static void lenientFile() throws Exception {
        scenario();
        CrystallizerRecipes handler = new CrystallizerRecipes();
        handler.deleteRecipes(); handler.registerDefaults();
        handler.readRecipeStream(new StringReader(table(row(COAL, PEROXIDE, CRYSTAL_COAL, "600", null), row(COAL, "[\"NOPE\",500]", CRYSTAL_COAL, "600", null), row("[\"item\",\"minecraft:iron_ore\"]", PEROXIDE, "[\"hbmsntm:crystal_iron\"]", "300", "0.1"))));
        List<CrystallizerRecipe> live = CrystallizerRecipes.getJeiRecipes();
        check(live.size() == 2 && live.get(1).duration == 300, "the config-file path skips the bad row and replaces the whole table");
        handler.readRecipeStream(new StringReader(table()));
        check(CrystallizerRecipes.getJeiRecipes().isEmpty() && !CrystallizerRecipes.hasRecipe(new ItemStack(Blocks.COAL_ORE.asItem()), Fluids.PEROXIDE), "an empty configured table disables every default");
        Path dir = Files.createTempDirectory("goal18a-recipes");
        File good = dir.resolve("hbmCrystallizer.json").toFile();
        Files.writeString(good.toPath(), table(row(COAL, PEROXIDE, CRYSTAL_COAL, "600", "0.05")));
        check(handler.readRecipeFile(good) && CrystallizerRecipes.getJeiRecipes().size() == 1, "a usable file loads and reports success");
        File bad = dir.resolve("broken.json").toFile();
        Files.writeString(bad.toPath(), "{\"recipes\":[");
        check(!handler.readRecipeFile(bad), "a malformed file reports failure so the loader falls back to the defaults");
        File missingArray = dir.resolve("missing.json").toFile();
        Files.writeString(missingArray.toPath(), "{\"rows\":[]}");
        check(!handler.readRecipeFile(missingArray), "a file without the recipes array reports failure");
        handler.deleteRecipes(); handler.registerDefaults();
        check(CrystallizerRecipes.getJeiRecipes().size() == 28, "defaults restore after the lenient scenarios");
    }
    private static void sync() throws Exception {
        scenario();
        new CrystallizerRecipes().deleteRecipes(); new CrystallizerRecipes().registerDefaults();
        String json = CrystallizerRecipes.writeSnapshot();
        CrystallizerRecipesPacket packet = new CrystallizerRecipesPacket(json);
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        CrystallizerRecipesPacket.STREAM_CODEC.encode(buf, packet);
        CrystallizerRecipesPacket decoded = CrystallizerRecipesPacket.STREAM_CODEC.decode(buf);
        check(decoded.json().equals(json) && decoded.type() == CrystallizerRecipesPacket.TYPE, "packet codec round trip");
        checks++; try { new CrystallizerRecipesPacket("{\"recipes\":[" + " ".repeat(256 * 1024) + "]}"); throw new AssertionError("oversize packet accepted"); } catch(IllegalArgumentException expected) { }
        RegistryFriendlyByteBuf badBytes = new RegistryFriendlyByteBuf(); badBytes.writeByteArray(new byte[]{(byte) 0xC3, (byte) 0x28});
        checks++; try { CrystallizerRecipesPacket.STREAM_CODEC.decode(badBytes); throw new AssertionError("malformed UTF-8 accepted"); } catch(IllegalArgumentException expected) { }
        goal18a.JeiBridge bridge = new goal18a.JeiBridge();
        CrystallizerRecipeClientSync.disconnect(null);
        check(CrystallizerRecipeClientSync.getRecipes().size() == 28 && CrystallizerRecipeClientSync.hasRecipe(new ItemStack(Blocks.COAL_ORE.asItem()), Fluids.PEROXIDE), "client falls back to the defaults before any snapshot");
        bridge.available();
        check(bridge.runtime.additions == 28 && bridge.displayedCrystallizerRecipes.size() == 28, "JEI runtime shows the 28 default rows");
        String one = table(row("[\"item\",\"minecraft:iron_ore\"]", PEROXIDE, "[\"hbmsntm:crystal_iron\"]", "300", "0.1"));
        check(CrystallizerRecipeClientSync.receive(one) && CrystallizerRecipeClientSync.getRecipes().size() == 1, "a valid snapshot replaces the client table");
        check(CrystallizerRecipeClientSync.getOutput(new ItemStack(Blocks.IRON_ORE.asItem()), Fluidsx(Fluids.PEROXIDE)).duration == 300 && !CrystallizerRecipeClientSync.hasRecipe(new ItemStack(Blocks.COAL_ORE.asItem()), Fluids.PEROXIDE), "client prediction follows the received table");
        check(bridge.runtime.additions == 29 && bridge.runtime.hidden == 28 && bridge.displayedCrystallizerRecipes.size() == 1, "JEI hides the defaults and adds the one new row");
        check(!CrystallizerRecipeClientSync.receive(table(row(COAL, "[\"NOPE\",500]", CRYSTAL_COAL, "600", null))) && CrystallizerRecipeClientSync.getRecipes().size() == 1, "a bad snapshot is ignored and the previous table kept");
        check(CrystallizerRecipeClientSync.receive(table()) && CrystallizerRecipeClientSync.getRecipes().isEmpty() && bridge.displayedCrystallizerRecipes.isEmpty(), "an empty snapshot is authoritative and clears the JEI rows");
        check(CrystallizerRecipeClientSync.receive(json) && CrystallizerRecipeClientSync.getRecipes().size() == 28 && bridge.runtime.additions == 29 && bridge.displayedCrystallizerRecipes.size() == 28, "the default rows are reused instead of re-added when they return");
        check(CrystallizerRecipes.getJeiRecipes().size() == 28, "client snapshots never touch the server table");
        bridge.unavailable();
        CrystallizerRecipeClientSync.disconnect(null);
        check(CrystallizerRecipeClientSync.getRecipes().size() == 28, "logout restores the defaults");
    }
    private static FluidType Fluidsx(FluidType t) { return t; }

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
    private static void fixed(GenericRecipe recipe, int index, Item item, int count, Integer meta) {
        AStack actual = recipe.inputItem[index];
        check(actual instanceof ComparableStack input && input.item == item && input.stacksize == count, "fixed identity/count " + recipe.getInternalName() + "/" + index);
        ComparableStack input = (ComparableStack) actual;
        if(meta != null) {
            check(input.meta == meta && input.matchesRecipe(MetaHelper.newStack(item, count, meta), false) && !input.matchesRecipe(MetaHelper.newStack(item, count, meta + 1), false), "component identity " + recipe.getInternalName() + "/" + index);
        }
        check(!input.matchesRecipe(meta == null ? new ItemStack(item, count - 1) : MetaHelper.newStack(item, count - 1, meta), false), "undersized input refused " + recipe.getInternalName() + "/" + index);
    }
    private static void assembly(Path output) throws Exception {
        JsonArray exported = new JsonArray();
        for(boolean mode : new boolean[]{false, true}) {
            scenario();
            NtmConfig.COMMON.ENABLE_528.set(mode);
            GenericRecipes.clearPools();
            Map<String, JsonObject> baseline = catalog(goal18a.base.AssemblyMachineRecipes.INSTANCE);
            GenericRecipes.clearPools();
            Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);
            Map<String, JsonObject> retained = new LinkedHashMap<>(live);
            retained.remove("ass.acidizer");
            check(retained.equals(baseline), "every pre-Goal18A assembly row is retained byte for byte, 528=" + mode);
            check(new ArrayList<>(retained.keySet()).equals(new ArrayList<>(baseline.keySet())), "pre-Goal18A row order retained, 528=" + mode);
            GenericRecipe recipe = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.acidizer");
            check(recipe != null && AssemblyMachineRecipes.INSTANCE.recipeOrderedList.stream().filter(r -> r.getInternalName().equals("ass.acidizer")).count() == 1, "ass.acidizer registered exactly once, 528=" + mode);
            List<String> names = new ArrayList<>(live.keySet());
            check(names.indexOf("ass.acidizer") == names.indexOf("ass.arcfurnace") + 1, "registered directly after ass.arcfurnace like the original order");
            check(recipe.duration == 200 && recipe.power == 100, "200 ticks, 100 HE/t");
            check(recipe.inputItem.length == 5, "five normal inputs, no expensive branch");
            fixed(recipe, 0, NtmItems.CAST_PLATE_WELDED.get(), 2, CastPlateItem.Type.STEEL.ordinal());
            fixed(recipe, 1, NtmItems.SHELL_TITANIUM.get(), 3, null);
            fixed(recipe, 2, NtmItems.INGOT_DESH.get(), 4, null);
            fixed(recipe, 3, NtmItems.MOTOR.get(), 1, null);
            fixed(recipe, 4, NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 2, null);
            check((recipe.inputFluid == null || recipe.inputFluid.length == 0) && (recipe.outputFluid == null || recipe.outputFluid.length == 0), "no fluids");
            check(recipe.outputItem.length == 1 && recipe.outputItem[0].getSingle().getItem() == NtmBlocks.MACHINE_CRYSTALLIZER.asItem() && recipe.outputItem[0].getSingle().getCount() == 1, "one machine_crystallizer");
            check(!(recipe.inputItem[4] instanceof TagStack) && recipe.inputItem[4] instanceof ComparableStack board && board.item != NtmItems.CIRCUIT_ANALOG_BOARD.get(), "BASIC is the integrated board, not the analog board");
            if(!mode) exported.add(live.get("ass.acidizer"));
        }
        NtmConfig.COMMON.ENABLE_528.set(false);
        JsonObject export = new JsonObject(); export.add("recipes", exported);
        Files.writeString(output.resolve("goal18a-assembly-recipes.json"), export.toString());
        // The default crystallizer table export for the merge reference.
        new CrystallizerRecipes().deleteRecipes(); new CrystallizerRecipes().registerDefaults();
        Files.writeString(output.resolve("goal18a-crystallizer-recipes.json"), CrystallizerRecipes.writeSnapshot());
    }
    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[0]);
        defaults(); roundTrip(); strict(); lenientFile(); sync(); assembly(output);
        System.out.println("Goal18A recipes: " + checks + " assertions; " + scenarios + " independent scenarios; 0 executed ticks");
    }
}
