package com.hbm.inventory.recipes.loader;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.inventory.recipes.CentrifugeRecipes.CentrifugeRecipe;
import com.hbm.inventory.recipes.FrozenCentrifugeRecipes;
import net.minecraft.world.item.ItemStack;

import java.io.File;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * Goal19C: the production centrifuge default table is the 76 frozen Goal16B rows (migration/goal16b-centrifuge-recipes.json) followed by
 * exactly one row, the rare earth ore chunk, whose numbers are read from original-centrifuge-chunk-row.json (parsed by the verifier from the
 * original CentrifugeRecipes.java:48-52). The expected snapshot text is modelled here from the documented writer contract
 * (["id",count,META-or-null] arrays), never by calling the production writer on the expectation. A player's custom table stays exactly as
 * written (the chunk row is only in the defaults); the row merged into a Goal16B-style custom file is accepted by the strict parser.
 *
 * Stand-in ids derive from the NtmItems field names (stub_id); the verifier proves each field is the production registration of the production id.
 * Mentioned so the stand-in registry carries the items: NtmItems.RARE_EARTH_ORE_CHUNK NtmItems.POWDER_COBALT_TINY NtmItems.POWDER_BORON_TINY NtmItems.POWDER_NIOBIUM_TINY NtmItems.NUGGET_ZIRCONIUM
 */
public final class Goal19CRecipeCentrifugeRegression {
    private static int checks, scenarios;
    private Goal19CRecipeCentrifugeRegression() { }
    private static void check(boolean condition, String message) { checks++; if(!condition) throw new AssertionError(message); }
    private static void scenario() { scenarios++; }
    private static void load(String json) { new CentrifugeRecipes().readRecipeStream(new StringReader(json)); }
    private static String envelope(String rows) { return "{\"recipes\":[" + rows + "]}"; }

    /** The writer-contract text of the chunk row from the original-derived expectation. */
    private static String modelledRow(JsonObject original) {
        JsonObject in = original.getAsJsonObject("input");
        StringBuilder text = new StringBuilder("{\"input\":[\"" + in.get("stub_id").getAsString() + "\"," + in.get("count").getAsInt() + "," + in.get("meta").getAsInt() + "],\"outputs\":[");
        JsonArray outputs = original.getAsJsonArray("outputs");
        for(int i = 0; i < outputs.size(); i++) {
            JsonObject out = outputs.get(i).getAsJsonObject();
            // Outputs carry no META (null preserves the absent component), like every frozen row.
            text.append(i == 0 ? "" : ",").append("[\"").append(out.get("stub_id").getAsString()).append("\",").append(out.get("count").getAsInt()).append(",null]");
        }
        return text.append("]}").toString();
    }

    private static String describe(JsonObject out) { return out.get("id").getAsString() + " x" + out.get("count").getAsInt(); }

    private static ItemStack chunk(List<CentrifugeRecipe> rows, int index) { return rows.get(index).input; }

    private static void defaults(Path out, JsonObject original, String frozenText) throws Exception {
        scenario();
        String row = modelledRow(original);
        check(frozenText.startsWith("{\"recipes\":[{") && frozenText.endsWith("}]}"), "the frozen Goal16B snapshot has the canonical envelope");
        String expected = frozenText.substring(0, frozenText.length() - 2) + "," + row + "]}";
        JsonArray frozenRows = JsonParser.parseString(frozenText).getAsJsonObject().getAsJsonArray("recipes");
        check(frozenRows.size() == 76, "the frozen Goal16B snapshot has 76 rows");

        var handler = new CentrifugeRecipes(); handler.deleteRecipes(); handler.registerDefaults();
        List<CentrifugeRecipe> rows = CentrifugeRecipes.getJeiRecipes();
        check(rows.size() == 77, "default table has 77 rows (76 frozen plus the chunk row)");
        String snapshot = CentrifugeRecipes.writeSnapshot();
        JsonArray liveRows = JsonParser.parseString(snapshot).getAsJsonObject().getAsJsonArray("recipes");
        boolean prefix = liveRows.size() == 77;
        for(int i = 0; prefix && i < 76; i++) prefix = liveRows.get(i).equals(frozenRows.get(i));
        check(prefix, "frozen rows 0..75 are unchanged and in order");
        JsonObject last = liveRows.get(76).getAsJsonObject();
        JsonObject in = original.getAsJsonObject("input");
        JsonArray lastInput = last.getAsJsonArray("input");
        check(lastInput.get(0).getAsString().equals(in.get("stub_id").getAsString()) && lastInput.get(1).getAsInt() == in.get("count").getAsInt() && lastInput.get(2).getAsInt() == in.get("meta").getAsInt(),
                "chunk row input is " + in.get("id").getAsString() + " x" + in.get("count").getAsInt() + " META " + in.get("meta").getAsInt());
        JsonArray outputs = original.getAsJsonArray("outputs"), lastOutputs = last.getAsJsonArray("outputs");
        check(lastOutputs.size() == outputs.size(), "chunk row has " + outputs.size() + " ordered output slots");
        for(int i = 0; i < outputs.size(); i++) {
            JsonObject expectedOutput = outputs.get(i).getAsJsonObject();
            JsonArray actual = lastOutputs.get(i).getAsJsonArray();
            check(actual.get(0).getAsString().equals(expectedOutput.get("stub_id").getAsString()) && actual.get(1).getAsInt() == expectedOutput.get("count").getAsInt() && actual.get(2).isJsonNull(),
                    "chunk row output " + i + " is " + describe(expectedOutput));
        }
        check(snapshot.equals(expected), "default snapshot equals the frozen 76-row text plus the original-derived chunk row, byte for byte: " + snapshot.substring(snapshot.lastIndexOf("{\"input\"")));
        check(CentrifugeRecipes.hasRecipe(new ItemStack(chunk(rows, 76).getItem())), "the chunk is a recipe input");
        ItemStack[] result = CentrifugeRecipes.getOutput(new ItemStack(chunk(rows, 76).getItem()));
        check(result.length == outputs.size(), "getOutput returns the " + outputs.size() + " slots");
        for(int i = 0; i < result.length; i++) check(result[i].getCount() == outputs.get(i).getAsJsonObject().get("count").getAsInt(), "getOutput slot " + i + " count");
        for(int i = 0; i < 77; i++) check(CentrifugeRecipes.hasRecipe(new ItemStack(rows.get(i).input.getItem())), "natural input " + i);

        // The frozen Goal16B class (compiled under another name) still yields the same 76 rows: the first 76 production rows equal it value by value.
        var frozen = new FrozenCentrifugeRecipes(); frozen.deleteRecipes(); frozen.registerDefaults();
        var old = FrozenCentrifugeRecipes.getJeiRecipes();
        check(old.size() == 76, "the Goal16B frozen class has 76 default rows");
        for(int i = 0; i < 76; i++) {
            var a = rows.get(i); var e = old.get(i);
            boolean same = ItemStack.isSameItemSameComponents(a.input, e.input) && a.outputs.length == e.outputs.length;
            for(int j = 0; same && j < a.outputs.length; j++) same = a.outputs[j].getCount() == e.outputs[j].getCount() && ItemStack.isSameItemSameComponents(a.outputs[j], e.outputs[j]);
            check(same, "default row " + i + " equals the frozen class row");
        }

        // Writer -> parser round trip of the whole 77-row table, and the canonical text is stable.
        load(snapshot);
        var round = CentrifugeRecipes.getJeiRecipes();
        check(round.size() == 77, "round trip keeps 77 rows");
        for(int i = 0; i < 77; i++) check(rows.get(i).sameRecipe(round.get(i)), "writer/parser round trip row " + i);
        check(CentrifugeRecipes.writeSnapshot().equals(snapshot), "writer output is stable after the round trip");

        // The template file writer (what a fresh config directory receives) carries the 77 rows and the updated comment.
        File template = out.resolve("_hbmCentrifuge.json").toFile();
        handler.writeTemplateFile(template);
        check(template.isFile(), "the template file was written");
        JsonObject written = JsonParser.parseString(Files.readString(template.toPath(), StandardCharsets.UTF_8)).getAsJsonObject();
        check(written.getAsJsonArray("recipes").equals(JsonParser.parseString(snapshot).getAsJsonObject().getAsJsonArray("recipes")), "template recipes equal the canonical snapshot (77 rows)");
        String comment = handler.getComment();
        check(comment.contains("rare earth ore chunk") && comment.contains("crystal_ items") && comment.contains("vanilla ore blocks") && comment.contains("ore_ blocks") && written.get("comment").getAsString().equals(comment),
                "getComment names the rare earth ore chunk next to the ore_, crystal_ and vanilla inputs, and the template carries it");
        check(CentrifugeRecipes.getDefaultRecipes().size() == 77, "getDefaultRecipes returns 77 rows");
        Files.writeString(out.resolve("goal19c-centrifuge-defaults-snapshot.json"), snapshot, StandardCharsets.UTF_8);
        // The production writer's own row 77 (equal to the modelled text, asserted above); the machine batch fixture decodes this file.
        check(liveRows.get(76).toString().equals(row), "the production writer's row 77 is the modelled row text");
        Files.writeString(out.resolve("goal19c-centrifuge-chunk-row.json"), liveRows.get(76).toString(), StandardCharsets.UTF_8);
    }

    private static void custom(Path out, JsonObject original, String frozenText, String customText, Path mergeTarget) throws Exception {
        String row = modelledRow(original);
        String chunkId = original.getAsJsonObject("input").get("stub_id").getAsString();
        ItemStack chunkStack = new ItemStack(firstDefaultInput().getItem());

        // A player's file without the chunk row stays exactly as written: no row appears, the chunk is not a recipe.
        scenario();
        File frozenFile = Files.writeString(out.resolve("player-frozen76.json"), frozenText, StandardCharsets.UTF_8).toFile();
        var handler = new CentrifugeRecipes(); handler.deleteRecipes();
        check(handler.readRecipeFile(frozenFile), "the frozen 76-row player file loads");
        check(CentrifugeRecipes.getJeiRecipes().size() == 76 && CentrifugeRecipes.writeSnapshot().equals(frozenText), "a player file without the chunk row stays exactly as written (76 rows, same canonical text)");
        check(!CentrifugeRecipes.hasRecipe(chunkStack) && CentrifugeRecipes.getOutput(chunkStack).length == 0, "no chunk recipe appears for a player file that lacks the row");
        scenario();
        File customFile = Files.writeString(out.resolve("player-goal16b-custom.json"), customText, StandardCharsets.UTF_8).toFile();
        handler.deleteRecipes();
        check(handler.readRecipeFile(customFile), "the Goal16B custom example loads");
        check(CentrifugeRecipes.getJeiRecipes().size() == 1 && CentrifugeRecipes.writeSnapshot().equals(customText) && !CentrifugeRecipes.hasRecipe(chunkStack), "the Goal16B custom example stays exactly as written, no chunk row appears");
        scenario();
        File emptyFile = Files.writeString(out.resolve("player-empty.json"), "{\"recipes\":[]}", StandardCharsets.UTF_8).toFile();
        check(handler.readRecipeFile(emptyFile) && CentrifugeRecipes.getJeiRecipes().isEmpty() && !CentrifugeRecipes.hasRecipe(chunkStack), "an empty player table stays empty (disables the machine, no chunk row)");

        // The row merged into a Goal16B-style custom file: strict parser (sync/snapshot path) and the lenient file path both accept it.
        scenario();
        String minimal = envelope(row);
        Files.writeString(mergeTarget, minimal, StandardCharsets.UTF_8);
        List<CentrifugeRecipe> strict = CentrifugeRecipes.readSnapshot(minimal);
        check(strict.size() == 1 && strict.get(0).input.getItem() == chunkStack.getItem(), "the minimal merge example parses in the strict parser");
        handler.deleteRecipes();
        check(handler.readRecipeFile(mergeTarget.toFile()) && CentrifugeRecipes.getJeiRecipes().size() == 1 && CentrifugeRecipes.writeSnapshot().equals(minimal), "the minimal merge example loads as a file and round-trips to the same text");
        check(CentrifugeRecipes.getOutput(chunkStack).length == original.getAsJsonArray("outputs").size(), "the merged row processes the chunk");
        String merged = customText.substring(0, customText.length() - 2) + "," + row + "]}";
        List<CentrifugeRecipe> strictMerged = CentrifugeRecipes.readSnapshot(merged);
        check(strictMerged.size() == 2, "the row appended to the Goal16B custom example parses strictly");
        File mergedFile = Files.writeString(out.resolve("player-goal16b-custom-merged.json"), merged, StandardCharsets.UTF_8).toFile();
        handler.deleteRecipes();
        check(handler.readRecipeFile(mergedFile) && CentrifugeRecipes.getJeiRecipes().size() == 2 && CentrifugeRecipes.writeSnapshot().equals(merged), "the merged player file loads and round-trips");
        check(chunkId.length() > 0 && JsonParser.parseString(Files.readString(mergeTarget, StandardCharsets.UTF_8)).getAsJsonObject().getAsJsonArray("recipes").size() == 1, "the written example has exactly the one new row");
        // Restore the default table so later scenarios start from the shipped defaults.
        handler.deleteRecipes(); handler.registerDefaults();
        check(CentrifugeRecipes.getJeiRecipes().size() == 77, "defaults restored");
    }

    private static ItemStack firstDefaultInput() {
        var handler = new CentrifugeRecipes(); handler.deleteRecipes(); handler.registerDefaults();
        List<CentrifugeRecipe> rows = CentrifugeRecipes.getJeiRecipes();
        return rows.get(rows.size() - 1).input;
    }

    public static void main(String[] args) throws Exception {
        Path out = Path.of(args[0]);
        JsonObject original = JsonParser.parseString(Files.readString(Path.of(args[1]), StandardCharsets.UTF_8)).getAsJsonObject();
        String frozenText = Files.readString(Path.of(args[2]), StandardCharsets.UTF_8), customText = Files.readString(Path.of(args[3]), StandardCharsets.UTF_8);
        check(original.getAsJsonObject("input").get("count").getAsInt() == 1 && original.getAsJsonArray("outputs").size() == 4, "the original expectation file describes one input and four outputs");
        defaults(out, original, frozenText);
        custom(out, original, frozenText, customText, Path.of(args[4]));
        System.out.println("Goal19C centrifuge table: " + checks + " assertions; " + scenarios + " independent scenarios; 0 executed ticks");
    }
}
