package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipes.ChanceOutput;
import com.hbm.items.component.NtmDataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.item.Item;

import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Goal19C: the production assembly table is the frozen Goal19C-start (delivered Goal19B) table plus exactly one appended row, ass.cirnox,
 * in both 528 modes. Every expected number of the new row is read from original-ass-cirnox.json, which the verifier parses from the original
 * AssemblyMachineRecipes.java:525-527 (Hbm-s-Nuclear-Tech-GIT); the serialisation of the expectation is modelled here from the documented
 * writer contract (item arrays: id, count when not 1 or a meta exists, meta when above 0; tags: id and count when not 1), never by
 * calling the production writer for the new row. Stand-in ids derive from the NtmItems/NtmBlocks field names (stub_id); the verifier
 * proves separately that each field is the production registration of the production id.
 *
 * NEO keeps its machine_zirnox registry id for the original reactor_zirnox, so the output's stub id (field REACTOR_ZIRNOX) differs from its production id.
 */
public final class Goal19CRecipeRegression {
    private static int checks, scenarios;
    private Goal19CRecipeRegression() { }
    private static void check(boolean condition, String message) { checks++; if(!condition) throw new AssertionError(message); }
    private static void scenario() { scenarios++; }

    private static final String NAME = "ass.cirnox";
    private static final String PREVIOUS = "ass.iturbine"; // the Goal19B row, last row of the frozen start table

    /** One captured table: serialised rows in registration order, the registered recipes and the blueprint pool state. */
    private static final class Table {
        final Map<String, String> rows = new LinkedHashMap<>();
        final Map<String, GenericRecipe> recipes = new LinkedHashMap<>();
        final Map<String, List<String>> pools = new HashMap<>();
        final Set<String> pooled = new HashSet<>();
    }

    private static String write(GenericRecipes<GenericRecipe> handler, GenericRecipe recipe) throws Exception {
        StringWriter serialized = new StringWriter();
        try(JsonWriter writer = new JsonWriter(serialized)) { writer.beginObject(); handler.writeRecipe(recipe, writer); writer.endObject(); }
        return serialized.toString();
    }

    private static Table capture(GenericRecipes<GenericRecipe> handler) throws Exception {
        GenericRecipes.clearPools();
        handler.deleteRecipes(); handler.registerDefaults();
        Table table = new Table();
        for(GenericRecipe recipe : handler.recipeOrderedList) {
            check(!table.rows.containsKey(recipe.getInternalName()), "unique registered recipe name " + recipe.getInternalName());
            table.rows.put(recipe.getInternalName(), write(handler, recipe));
            table.recipes.put(recipe.getInternalName(), recipe);
        }
        for(Map.Entry<String, List<String>> pool : GenericRecipes.blueprintPools.entrySet()) table.pools.put(pool.getKey(), new ArrayList<>(pool.getValue()));
        table.pooled.addAll(GenericRecipes.pooledBlueprints.keySet());
        return table;
    }

    private static String idOf(Item item) { return BuiltInRegistries.ITEM.getKey(item).toString(); }

    /** The expectation row from the original data (stand-in ids), formatted by the modelled writer contract. */
    private static JsonObject expectedRow(JsonObject original) {
        JsonObject row = new JsonObject();
        row.addProperty("name", original.get("name").getAsString());
        JsonArray inputs = new JsonArray();
        for(JsonElement element : original.getAsJsonArray("inputs")) {
            JsonObject in = element.getAsJsonObject();
            JsonArray array = new JsonArray();
            int count = in.get("count").getAsInt(), meta = in.get("meta").getAsInt();
            array.add(in.get("kind").getAsString());
            array.add(in.get("stub_id").getAsString());
            if(in.get("kind").getAsString().equals("item")) {
                if(count != 1 || meta > 0) array.add(count);
                if(meta > 0) array.add(meta);
            } else if(count != 1) array.add(count);
            inputs.add(array);
        }
        row.add("inputItem", inputs);
        JsonObject out = original.getAsJsonObject("output");
        JsonArray outputs = new JsonArray();
        // A standard output (chance 1, weight 0) is ["single", [item id, count when not 1]] (SerializableRecipe.writeItemStack nests the stack array).
        JsonArray single = new JsonArray(), stack = new JsonArray();
        single.add("single");
        stack.add(out.get("stub_id").getAsString());
        if(out.get("count").getAsInt() != 1) stack.add(out.get("count").getAsInt());
        single.add(stack);
        outputs.add(single);
        row.add("outputItem", outputs);
        row.addProperty("duration", original.get("duration").getAsInt());
        row.addProperty("power", original.get("power").getAsLong());
        return row;
    }

    private static String describe(JsonObject in) {
        return in.get("kind").getAsString() + " " + in.get("id").getAsString() + " x" + in.get("count").getAsInt() + (in.get("meta").getAsInt() > 0 && in.get("kind").getAsString().equals("item") ? " meta " + in.get("meta").getAsInt() : "");
    }

    private static void inputsOf(GenericRecipe recipe, JsonObject original, String where) {
        JsonArray inputs = original.getAsJsonArray("inputs");
        check(recipe.inputItem != null && recipe.inputItem.length == inputs.size(), NAME + " has exactly " + inputs.size() + " inputs in the original order, " + where);
        for(int i = 0; i < inputs.size(); i++) {
            JsonObject in = inputs.get(i).getAsJsonObject();
            AStack stack = recipe.inputItem[i];
            String label = NAME + " input " + i + " is " + describe(in) + ", " + where;
            if(in.get("kind").getAsString().equals("tag"))
                check(stack instanceof TagStack t && t.tag.location().toString().equals(in.get("stub_id").getAsString()) && t.stacksize == in.get("count").getAsInt(), label);
            else
                check(stack instanceof ComparableStack c && idOf(c.item).equals(in.get("stub_id").getAsString()) && c.stacksize == in.get("count").getAsInt() && c.meta == in.get("meta").getAsInt(), label);
        }
    }

    private static ComparableStack firstItem(GenericRecipe recipe, String id) {
        for(AStack stack : recipe.inputItem) if(stack instanceof ComparableStack c && idOf(c.item).equals(id)) return c;
        return null;
    }

    private static TagStack firstTag(GenericRecipe recipe, String id) {
        for(AStack stack : recipe.inputItem) if(stack instanceof TagStack t && t.tag.location().toString().equals(id)) return t;
        return null;
    }

    private static void newRow(Table base, Table live, JsonObject original, int baseRows, String where, List<String> texts) throws Exception {
        List<String> baseOrder = new ArrayList<>(base.rows.keySet()), liveOrder = new ArrayList<>(live.rows.keySet());
        List<String> expectedOrder = new ArrayList<>(baseOrder); expectedOrder.add(NAME);
        check(!base.rows.isEmpty() && !base.rows.containsKey(NAME), "the frozen Goal19C-start table does not carry " + NAME + ", " + where);
        check(base.rows.size() == baseRows && baseOrder.get(baseOrder.size() - 1).equals(PREVIOUS), "the frozen start table has " + baseRows + " rows and ends with " + PREVIOUS + ", " + where);
        check(live.rows.size() == base.rows.size() + 1 && liveOrder.equals(expectedOrder), "live catalog is the base catalog plus exactly one new row " + NAME + " appended last, " + where);
        check(liveOrder.get(liveOrder.size() - 1).equals(NAME) && liveOrder.get(liveOrder.size() - 2).equals(PREVIOUS), NAME + " is the last registered row, right after " + PREVIOUS + ", " + where);
        for(String name : baseOrder) check(live.rows.get(name).equals(base.rows.get(name)), "base row " + name + " is byte-identical in the 18B serialization, " + where);
        check(live.pools.equals(base.pools) && live.pooled.equals(base.pooled) && !live.pooled.contains(NAME), "blueprint pool state is unchanged and " + NAME + " is in no pool, " + where);

        GenericRecipe recipe = live.recipes.get(NAME);
        check(recipe.getInternalName().equals(NAME), "registered under the original name " + NAME + ", " + where);
        check(recipe.duration == original.get("duration").getAsInt(), NAME + " duration " + original.get("duration").getAsInt() + " ticks, " + where);
        check(recipe.power == original.get("power").getAsLong(), NAME + " power " + original.get("power").getAsLong() + " HE/t, " + where);
        check(!recipe.isPooled() && recipe.getPools() == null && recipe.autoSwitchGroup == null && !recipe.writeIcon && !recipe.customLocalization && recipe.nameWrapper == null, NAME + " has no blueprint pool, auto switch, icon or naming, " + where);
        check(recipe.inputFluid == null && recipe.outputFluid == null, NAME + " has no fluids, " + where);
        JsonObject out = original.getAsJsonObject("output");
        check(recipe.outputItem != null && recipe.outputItem.length == 1 && recipe.outputItem[0] instanceof ChanceOutput co && co.chance >= 1F
                && idOf(co.stack.getItem()).equals(out.get("stub_id").getAsString()) && co.stack.getCount() == out.get("count").getAsInt() && !co.stack.has(NtmDataComponents.META.get()),
                NAME + " outputs " + out.get("count").getAsInt() + " x " + out.get("id").getAsString() + " with no meta, " + where);
        inputsOf(recipe, original, where);

        // The new row as the production writer serialises it, against the modelled row (exact tree and exact text).
        String text = live.rows.get(NAME);
        JsonObject expected = expectedRow(original);
        check(JsonParser.parseString(text).equals(expected), NAME + " serialised row equals the original-derived row: " + text);
        check(JsonParser.parseString(text).getAsJsonObject().keySet().equals(Set.of("name", "inputItem", "outputItem", "duration", "power")), NAME + " writes only name, inputItem, outputItem, duration and power, " + where);
        texts.add(text);

        // Plain items resolve exactly as in the neighbouring rows that use the same stacks; the concrete tag is the one the other concrete row uses.
        GenericRecipe iturbine = live.recipes.get(PREVIOUS), coker = live.recipes.get("ass.coker"), turbofan = live.recipes.get("ass.turbofan");
        check(iturbine != null && coker != null && turbofan != null, "the precedent rows " + PREVIOUS + ", ass.coker and ass.turbofan exist, " + where);
        ComparableStack myRubber = firstItem(recipe, "hbmsntm:ingot_rubber"), rubber = firstItem(coker, "hbmsntm:ingot_rubber"), turbineRubber = firstItem(iturbine, "hbmsntm:ingot_rubber");
        check(myRubber != null && rubber != null && turbineRubber != null && rubber.item == myRubber.item && rubber.meta == myRubber.meta && turbineRubber.meta == myRubber.meta,
                "the plain rubber ingot resolves exactly as in ass.coker and " + PREVIOUS + ", " + where);
        ComparableStack myBoard = firstItem(recipe, "hbmsntm:circuit_integrated_board"), board = firstItem(turbofan, "hbmsntm:circuit_integrated_board");
        check(myBoard != null && board != null && board.item == myBoard.item && board.meta == myBoard.meta && MetaHelper.getMeta(board.toStack()) == MetaHelper.getMeta(myBoard.toStack()), "the BASIC circuit is the integrated board as in ass.turbofan, " + where);
        TagStack myConcrete = firstTag(recipe, "ntm:any_concrete");
        String other = null;
        for(Map.Entry<String, GenericRecipe> entry : live.recipes.entrySet()) if(!entry.getKey().equals(NAME) && firstTag(entry.getValue(), "ntm:any_concrete") != null) other = entry.getKey();
        check(myConcrete != null && other != null && firstTag(live.recipes.get(other), "ntm:any_concrete").tag.equals(myConcrete.tag), "the concrete tag is the same ntm:any_concrete key that " + other + " uses, " + where);
        for(AStack stack : recipe.inputItem) if(stack instanceof ComparableStack c) check(BuiltInRegistries.ITEM.containsKey(BuiltInRegistries.ITEM.getKey(c.item)), "the id " + idOf(c.item) + " is a registered item, " + where);
    }

    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[0]), expectedFile = Path.of(args[1]);
        JsonObject original = JsonParser.parseString(Files.readString(expectedFile, StandardCharsets.UTF_8)).getAsJsonObject();
        check(original.get("name").getAsString().equals(NAME) && original.getAsJsonArray("inputs").size() == 7, "the original expectation file describes ass.cirnox with seven normal inputs");
        JsonObject baseRows = original.getAsJsonObject("expected_base_rows");
        List<String> texts = new ArrayList<>();
        JsonObject export = new JsonObject();
        // Mentioned so the stand-in registry carries it for the anchored boron-to-beryllium mutation: NtmItems.INGOT_BERYLLIUM.get()
        for(boolean mode : new boolean[]{false, true}) {
            scenario();
            NtmConfig.COMMON.ENABLE_528.set(mode);
            Table base = capture(goal19c.base.AssemblyMachineRecipes.INSTANCE);
            Table live = capture(AssemblyMachineRecipes.INSTANCE);
            newRow(base, live, original, baseRows.get("528=" + mode).getAsInt(), "528=" + mode, texts);
            JsonObject entry = new JsonObject();
            entry.addProperty("baseRows", base.rows.size()); entry.addProperty("liveRows", live.rows.size());
            entry.add("newRow", JsonParser.parseString(live.rows.get(NAME)));
            JsonArray names = new JsonArray();
            for(String name : live.rows.keySet()) names.add(name);
            entry.add("liveOrder", names);
            export.add("528=" + mode, entry);
        }
        NtmConfig.COMMON.ENABLE_528.set(false);
        scenario();
        check(texts.size() == 2 && texts.get(0).equals(texts.get(1)), NAME + " is serialised identically with 528 off and on (not an enable528 row)");
        Files.writeString(output.resolve("goal19c-assembly-catalog.json"), export.toString(), StandardCharsets.UTF_8);
        System.out.println("Goal19C assembly row: " + checks + " assertions; " + scenarios + " independent scenarios; 0 executed ticks");
    }
}
