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
 * Goal19B: the production assembly table is the frozen 70bc9899 table plus exactly one appended row, ass.iturbine, in both 528 modes.
 * Every expected number of the new row is read from original-ass-iturbine.json, which the verifier parses from the original
 * AssemblyMachineRecipes.java:434-436 (Hbm-s-Nuclear-Tech-GIT); the serialisation format of the expectation is modelled here from the
 * documented writer contract (item arrays: id, count when not 1 or a meta exists, meta when above 0; tags: id and count when not 1),
 * never by calling the production writer for the new row.
 */
public final class Goal19BRecipeRegression {
    private static int checks, scenarios;
    private Goal19BRecipeRegression() { }
    private static void check(boolean condition, String message) { checks++; if(!condition) throw new AssertionError(message); }
    private static void scenario() { scenarios++; }

    private static final String NAME = "ass.iturbine";

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

    /** The expectation row from the original data, formatted by the modelled writer contract. */
    private static JsonObject expectedRow(JsonObject original) {
        JsonObject row = new JsonObject();
        row.addProperty("name", original.get("name").getAsString());
        JsonArray inputs = new JsonArray();
        for(JsonElement element : original.getAsJsonArray("inputs")) {
            JsonObject in = element.getAsJsonObject();
            JsonArray array = new JsonArray();
            int count = in.get("count").getAsInt(), meta = in.get("meta").getAsInt();
            array.add(in.get("kind").getAsString());
            array.add(in.get("id").getAsString());
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
        stack.add(out.get("id").getAsString());
        if(out.get("count").getAsInt() != 1) stack.add(out.get("count").getAsInt());
        single.add(stack);
        outputs.add(single);
        row.add("outputItem", outputs);
        row.addProperty("duration", original.get("duration").getAsInt());
        row.addProperty("power", original.get("power").getAsLong());
        return row;
    }

    private static String describe(JsonObject in) {
        return in.get("kind").getAsString() + " " + in.get("id").getAsString() + " x" + in.get("count").getAsInt() + (in.get("meta").getAsInt() > 0 ? " meta " + in.get("meta").getAsInt() : "");
    }

    private static void inputsOf(GenericRecipe recipe, JsonObject original, String where) {
        JsonArray inputs = original.getAsJsonArray("inputs");
        check(recipe.inputItem != null && recipe.inputItem.length == inputs.size(), NAME + " has exactly " + inputs.size() + " inputs in the original order, " + where);
        for(int i = 0; i < inputs.size(); i++) {
            JsonObject in = inputs.get(i).getAsJsonObject();
            AStack stack = recipe.inputItem[i];
            String label = NAME + " input " + i + " is " + describe(in) + ", " + where;
            if(in.get("kind").getAsString().equals("tag"))
                check(stack instanceof TagStack t && t.tag.location().toString().equals(in.get("id").getAsString()) && t.stacksize == in.get("count").getAsInt(), label);
            else
                check(stack instanceof ComparableStack c && idOf(c.item).equals(in.get("id").getAsString()) && c.stacksize == in.get("count").getAsInt() && c.meta == in.get("meta").getAsInt(), label);
        }
    }

    private static ComparableStack firstItem(GenericRecipe recipe, String id) {
        for(AStack stack : recipe.inputItem) if(stack instanceof ComparableStack c && idOf(c.item).equals(id)) return c;
        return null;
    }

    private static void newRow(Table base, Table live, JsonObject original, String where, List<String> texts) throws Exception {
        List<String> baseOrder = new ArrayList<>(base.rows.keySet()), liveOrder = new ArrayList<>(live.rows.keySet());
        List<String> expectedOrder = new ArrayList<>(baseOrder); expectedOrder.add(NAME);
        check(!base.rows.isEmpty() && !base.rows.containsKey(NAME), "the frozen 70bc9899 table does not carry " + NAME + ", " + where);
        check(live.rows.size() == base.rows.size() + 1 && liveOrder.equals(expectedOrder), "live catalog is the base catalog plus exactly one new row " + NAME + " appended last, " + where);
        check(liveOrder.get(liveOrder.size() - 1).equals(NAME), NAME + " is the last registered row, " + where);
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
                && idOf(co.stack.getItem()).equals(out.get("id").getAsString()) && co.stack.getCount() == out.get("count").getAsInt() && !co.stack.has(NtmDataComponents.META.get()),
                NAME + " outputs " + out.get("count").getAsInt() + " x " + out.get("id").getAsString() + " with no meta, " + where);
        inputsOf(recipe, original, where);

        // The new row as the production writer serialises it, against the modelled row (exact tree and exact text).
        String text = live.rows.get(NAME);
        JsonObject expected = expectedRow(original);
        check(JsonParser.parseString(text).equals(expected), NAME + " serialised row equals the original-derived row: " + text);
        check(JsonParser.parseString(text).getAsJsonObject().keySet().equals(Set.of("name", "inputItem", "outputItem", "duration", "power")), NAME + " writes only name, inputItem, outputItem, duration and power, " + where);
        texts.add(text);

        // Item ids resolve exactly as in the neighbouring rows that use the same stacks.
        ComparableStack mine = firstItem(recipe, "hbmsntm:wire_dense");
        GenericRecipe turbofan = live.recipes.get("ass.turbofan"), combustion = live.recipes.get("ass.combustiongen"), coker = live.recipes.get("ass.coker");
        check(turbofan != null && combustion != null && coker != null && mine != null, "the precedent rows ass.turbofan, ass.combustiongen and ass.coker exist, " + where);
        ComparableStack wire = firstItem(turbofan, "hbmsntm:wire_dense");
        check(wire != null && wire.item == mine.item && wire.meta == mine.meta && MetaHelper.getMeta(wire.toStack()) == MetaHelper.getMeta(mine.toStack()) && wire.stacksize != mine.stacksize,
                "dense gold wire resolves exactly as in ass.turbofan (same item and meta, own count), " + where);
        ComparableStack pipe = firstItem(turbofan, "hbmsntm:pipe_dura_steel"), myPipe = firstItem(recipe, "hbmsntm:pipe_dura_steel");
        check(pipe != null && myPipe != null && pipe.item == myPipe.item && pipe.meta == myPipe.meta, "dura steel pipe resolves exactly as in ass.turbofan, " + where);
        ComparableStack board = firstItem(turbofan, "hbmsntm:circuit_integrated_board"), myBoard = firstItem(recipe, "hbmsntm:circuit_integrated_board");
        check(board != null && myBoard != null && board.item == myBoard.item && board.meta == myBoard.meta, "the BASIC circuit is the integrated board as in ass.turbofan, " + where);
        ComparableStack rubber = firstItem(coker, "hbmsntm:ingot_rubber"), myRubber = firstItem(recipe, "hbmsntm:ingot_rubber");
        check(rubber != null && myRubber != null && rubber.item == myRubber.item && rubber.meta == myRubber.meta, "the plain rubber ingot resolves exactly as in ass.coker, " + where);
        TagStack plates = null;
        for(AStack stack : combustion.inputItem) if(stack instanceof TagStack t && t.tag.location().toString().equals("c:plates/steel")) plates = t;
        check(plates != null && plates.tag.location().equals(((TagStack) recipe.inputItem[0]).tag.location()), "the steel plate tag is the one ass.combustiongen uses, " + where);
        for(AStack stack : recipe.inputItem) if(stack instanceof ComparableStack c) check(BuiltInRegistries.ITEM.containsKey(BuiltInRegistries.ITEM.getKey(c.item)), "the production id " + idOf(c.item) + " is a registered item, " + where);
    }

    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[0]), expectedFile = Path.of(args[1]);
        JsonObject original = JsonParser.parseString(Files.readString(expectedFile, StandardCharsets.UTF_8)).getAsJsonObject();
        check(original.get("name").getAsString().equals(NAME) && original.getAsJsonArray("inputs").size() == 6, "the original expectation file describes ass.iturbine with six normal inputs");
        List<String> texts = new ArrayList<>();
        JsonObject export = new JsonObject();
        for(boolean mode : new boolean[]{false, true}) {
            scenario();
            NtmConfig.COMMON.ENABLE_528.set(mode);
            Table base = capture(goal19b.base.AssemblyMachineRecipes.INSTANCE);
            Table live = capture(AssemblyMachineRecipes.INSTANCE);
            newRow(base, live, original, "528=" + mode, texts);
            JsonObject entry = new JsonObject();
            entry.addProperty("baseRows", base.rows.size()); entry.addProperty("liveRows", live.rows.size());
            entry.add("newRow", JsonParser.parseString(live.rows.get(NAME)));
            export.add("528=" + mode, entry);
        }
        NtmConfig.COMMON.ENABLE_528.set(false);
        scenario();
        check(texts.size() == 2 && texts.get(0).equals(texts.get(1)), NAME + " is serialised identically with 528 off and on (not an enable528 row)");
        Files.writeString(output.resolve("goal19b-assembly-catalog.json"), export.toString(), StandardCharsets.UTF_8);
        System.out.println("Goal19B recipes: " + checks + " assertions; " + scenarios + " independent scenarios; 0 executed ticks");
    }
}
