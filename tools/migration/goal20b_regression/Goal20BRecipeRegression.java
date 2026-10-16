package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.config.NtmConfig;
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
 * Goal20B: the production assembly table is the frozen Goal20B-start table (the Goal19C/20A catalog) plus exactly one row, ass.gascent,
 * inserted right after ass.centrifuge, in both 528 modes. Every expected number of the new row is read from original-ass-gascent.json,
 * which the verifier parses from the original AssemblyMachineRecipes.java:282-283 (Hbm-s-Nuclear-Tech-GIT, normal branch); the
 * serialisation of the expectation is modelled from the documented writer contract (item arrays: kind, id, count when not 1 or a meta
 * exists, meta when above 0; tags: kind, id, count when not 1), never by calling the production writer for the new row. Stand-in ids derive
 * from the NtmItems/NtmBlocks field names (stub_id); the verifier proves separately that each field is the production registration of the
 * production id. Arguments: the run directory and the expectation file.
 */
public final class Goal20BRecipeRegression {
    private static int checks, scenarios;
    private Goal20BRecipeRegression() { }
    private static void check(boolean condition, String message) { checks++; if(!condition) throw new AssertionError(message); }
    private static void scenario() { scenarios++; }

    private static final String NAME = "ass.gascent";
    private static final String PREVIOUS = "ass.centrifuge"; // the original order: ass.centrifuge, then ass.gascent (AssemblyMachineRecipes.java:280-283)

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
        return in.get("kind").getAsString() + " " + in.get("stub_id").getAsString() + " x" + in.get("count").getAsInt();
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

    private static TagStack firstTag(GenericRecipe recipe, String id) {
        for(AStack stack : recipe.inputItem) if(stack instanceof TagStack t && t.tag.location().toString().equals(id)) return t;
        return null;
    }

    private static void newRow(Table base, Table live, JsonObject original, String where, List<String> texts) throws Exception {
        List<String> baseOrder = new ArrayList<>(base.rows.keySet()), liveOrder = new ArrayList<>(live.rows.keySet());
        List<String> expectedOrder = new ArrayList<>(baseOrder);
        int at = baseOrder.indexOf(PREVIOUS);
        check(at >= 0 && !base.rows.containsKey(NAME), "the frozen Goal20B-start table carries " + PREVIOUS + " and not " + NAME + ", " + where);
        expectedOrder.add(at + 1, NAME);
        check(live.rows.size() == base.rows.size() + 1 && liveOrder.equals(expectedOrder), "live catalog is the base catalog plus exactly one new row " + NAME + " inserted right after "
                + PREVIOUS + ", " + where + " (base " + base.rows.size() + ", live " + live.rows.size() + ")");
        for(String name : baseOrder) check(live.rows.get(name).equals(base.rows.get(name)), "base row " + name + " is byte-identical in the 18B serialization, " + where);
        check(live.pools.equals(base.pools) && live.pooled.equals(base.pooled) && !live.pooled.contains(NAME), "blueprint pool state is unchanged and " + NAME + " is in no pool (the original "
                + "528 pool is not migrated), " + where);

        GenericRecipe recipe = live.recipes.get(NAME);
        check(recipe.getInternalName().equals(NAME), "registered under the original name " + NAME + ", " + where);
        check(recipe.duration == original.get("duration").getAsInt(), NAME + " duration " + original.get("duration").getAsInt() + " ticks, " + where + " (got " + recipe.duration + ")");
        check(recipe.power == original.get("power").getAsLong(), NAME + " power " + original.get("power").getAsLong() + " HE/t, " + where + " (got " + recipe.power + ")");
        check(!recipe.isPooled() && recipe.getPools() == null && recipe.autoSwitchGroup == null && !recipe.writeIcon && !recipe.customLocalization && recipe.nameWrapper == null,
                NAME + " has no blueprint pool, auto switch, icon or naming, " + where);
        check(recipe.inputFluid == null && recipe.outputFluid == null, NAME + " has no fluids, " + where);
        JsonObject out = original.getAsJsonObject("output");
        check(recipe.outputItem != null && recipe.outputItem.length == 1 && recipe.outputItem[0] instanceof ChanceOutput co && co.chance >= 1F
                        && idOf(co.stack.getItem()).equals(out.get("stub_id").getAsString()) && co.stack.getCount() == out.get("count").getAsInt() && !co.stack.has(NtmDataComponents.META.get()),
                NAME + " outputs " + out.get("count").getAsInt() + " x " + out.get("id").getAsString() + " with no meta, " + where);
        inputsOf(recipe, original, where);

        String text = live.rows.get(NAME);
        JsonObject expected = expectedRow(original);
        check(JsonParser.parseString(text).equals(expected), NAME + " serialised row equals the original-derived row: " + text + " != " + expected);
        check(JsonParser.parseString(text).getAsJsonObject().keySet().equals(Set.of("name", "inputItem", "outputItem", "duration", "power")), NAME + " writes only name, inputItem, outputItem, duration and power, " + where);
        texts.add(text);

        // The two tags are the same keys ass.centrifuge uses (plastic ingots, steel plates).
        GenericRecipe centrifuge = live.recipes.get(PREVIOUS);
        for(String tag : new String[] {original.get("plastic_tag").getAsString(), original.get("steel_plate_tag").getAsString()}) {
            TagStack mine = firstTag(recipe, tag), theirs = firstTag(centrifuge, tag);
            check(mine != null && theirs != null && mine.tag.equals(theirs.tag), "the tag " + tag + " is the same key " + PREVIOUS + " uses, " + where);
        }
        for(AStack stack : recipe.inputItem) if(stack instanceof ComparableStack c) check(BuiltInRegistries.ITEM.containsKey(BuiltInRegistries.ITEM.getKey(c.item)), "the id " + idOf(c.item) + " is a registered item, " + where);
    }

    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[0]), expectedFile = Path.of(args[1]);
        JsonObject original = JsonParser.parseString(Files.readString(expectedFile, StandardCharsets.UTF_8)).getAsJsonObject();
        check(original.get("name").getAsString().equals(NAME) && original.getAsJsonArray("inputs").size() == 5, "the original expectation file describes ass.gascent with five normal inputs");
        List<String> texts = new ArrayList<>();
        JsonObject export = new JsonObject();
        // Mentioned so the stand-in registry carries them for the anchored mutations: NtmItems.CIRCUIT_ANALOG_BOARD.get(), NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get()
        for(boolean mode : new boolean[]{false, true}) {
            scenario();
            NtmConfig.COMMON.ENABLE_528.set(mode);
            Table base = capture(goal20b.base.AssemblyMachineRecipes.INSTANCE);
            Table live = capture(AssemblyMachineRecipes.INSTANCE);
            newRow(base, live, original, "528=" + mode, texts);
            JsonObject entry = new JsonObject();
            entry.addProperty("baseRows", base.rows.size()); entry.addProperty("liveRows", live.rows.size());
            entry.addProperty("index", new ArrayList<>(live.rows.keySet()).indexOf(NAME));
            entry.add("newRow", JsonParser.parseString(live.rows.get(NAME)));
            JsonArray names = new JsonArray();
            for(String name : live.rows.keySet()) names.add(name);
            entry.add("liveOrder", names);
            JsonObject rows = new JsonObject();
            for(Map.Entry<String, String> row : live.rows.entrySet()) rows.add(row.getKey(), JsonParser.parseString(row.getValue()));
            entry.add("liveRowsSerialized", rows);
            export.add("528=" + mode, entry);
        }
        NtmConfig.COMMON.ENABLE_528.set(false);
        scenario();
        check(texts.size() == 2 && texts.get(0).equals(texts.get(1)), NAME + " is serialised identically with 528 off and on (registered in both modes)");
        Files.writeString(output.resolve("goal20b-assembly-catalog.json"), export.toString(), StandardCharsets.UTF_8);
        System.out.println("Goal20B assembly row: " + checks + " assertions; " + scenarios + " independent scenarios; 0 executed ticks");
    }
}
