package com.hbm.inventory.recipes.loader;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;

import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Goal 11B section 6: the fluid tank assembler recipe through the production GenericRecipes writer, compared with the
 * original (AssemblyMachineRecipes.java:472-474 ass.tank, normal mode: 200 ticks, 100 HE/t, 8 steel plates (ore
 * dictionary), 4 steel shells -> 1 fluid tank; the expensive inputs of :474 use item_expensive, which NEO does not have)
 * and with the post-Goal 11A catalog (goal11b.base.AssemblyMachineRecipes): exactly ass.tank is appended at the end and
 * every other recipe keeps its name, order and content.
 * Goal 11C (migration/GOAL11C.md D1) appends exactly ass.chemplant after ass.tank (original AssemblyMachineRecipes.java:264-265,
 * normal mode); one added check requires exactly that entry there with the original's inputs.
 * Goal 12B (migration/GOAL12B.md) appends exactly ass.crackingtower after ass.chemplant (original
 * AssemblyMachineRecipes.java:316-317, normal mode); one more added check requires exactly that entry there.
 */
public class Goal11BRecipeRegression {
    private static int checks;

    private static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }

    /** One recipe as the single JSON object the production writer produces. */
    static JsonObject write(GenericRecipes<GenericRecipe> recipes, GenericRecipe recipe) throws Exception {
        StringWriter text = new StringWriter();
        JsonWriter writer = new JsonWriter(text);
        writer.beginObject();
        recipes.writeRecipe(recipe, writer);
        writer.endObject();
        writer.close();
        return JsonParser.parseString(text.toString()).getAsJsonObject();
    }

    static Map<String, JsonObject> catalog(GenericRecipes<GenericRecipe> recipes) throws Exception {
        recipes.deleteRecipes();
        recipes.registerDefaults();
        Map<String, JsonObject> out = new LinkedHashMap<>();
        for(GenericRecipe recipe : recipes.recipeOrderedList) out.put(recipe.getInternalName(), write(recipes, recipe));
        return out;
    }

    static JsonArray item(String id, int count, int meta) {
        JsonArray a = new JsonArray();
        a.add("item");
        a.add(id);
        a.add(count);
        a.add(meta);
        return a;
    }

    static JsonArray tag(String id, int count) {
        JsonArray a = new JsonArray();
        a.add("tag");
        a.add(id);
        a.add(count);
        return a;
    }

    public static void main(String[] args) throws Exception {
        try {
            recipes(Path.of(args[0]));
        } catch(AssertionError e) {
            System.out.println("AssertionError in 6. fluid tank recipe after " + (checks - 1) + " passed checks: " + e.getMessage());
            throw e;
        }
    }

    static void recipes(Path output) throws Exception {
        int wildcard = 32767;
        Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);
        Map<String, JsonObject> base = catalog(goal11b.base.AssemblyMachineRecipes.INSTANCE);

        JsonObject expected = new JsonObject();
        expected.addProperty("name", "ass.tank");
        JsonArray in = new JsonArray();
        in.add(tag("c:plates/steel", 8));
        in.add(item("hbmsntm:shell_steel", 4, wildcard));
        expected.add("inputItem", in);
        JsonArray single = new JsonArray();
        single.add("single");
        JsonArray stack = new JsonArray();
        stack.add("hbmsntm:machine_fluid_tank");
        single.add(stack);
        JsonArray out = new JsonArray();
        out.add(single);
        expected.add("outputItem", out);
        expected.addProperty("duration", 200);
        expected.addProperty("power", 100);

        check(!base.containsKey("ass.tank"), "the post-Goal 11A catalog has no ass.tank");
        check(expected.equals(live.get("ass.tank")),
                "ass.tank: 200 ticks, 100 HE/t, 8 steel plates (c:plates/steel, the original's ore dictionary plate) + 4 steel shells -> 1 fluid tank: "
                        + live.get("ass.tank"));
        List<String> liveNames = new ArrayList<>(live.keySet());
        List<String> baseNames = new ArrayList<>(base.keySet());
        // Goal 11C (migration/GOAL11C.md D1): exactly ass.chemplant follows ass.tank; it is checked by the added check below.
        List<String> goal11c = List.of("ass.chemplant");
        // Goal 12B (migration/GOAL12B.md): exactly ass.crackingtower follows ass.chemplant; one added check below.
        List<String> goal12b = List.of("ass.crackingtower");
        // Goal 13A (migration/GOAL13A.md A4): exactly ass.analogAlt, ass.factorioChip and ass.atomicClockAlt (the pool alt..circuit) follow
        // ass.crackingtower; one added check below (verify_goal13a.py checks their content).
        List<String> goal13a = List.of("ass.analogAlt", "ass.factorioChip", "ass.atomicClockAlt");
        // Goal 13B (migration/GOAL13B.md B4): ass.chip follows ass.crackingtower and comes in front of the Goal 13A entries, ass.arcfurnace comes last;
        // one added check below (verify_goal13b.py checks their content).
        List<String> goal13b = List.of("ass.chip", "ass.arcfurnace");
        check(liveNames.size() == baseNames.size() + 1 + goal11c.size() + goal12b.size() + goal13a.size() + goal13b.size() && liveNames.get(baseNames.size()).equals("ass.tank"),
                "exactly one recipe is added, at the end before the Goal 11C entry (" + baseNames.size() + " -> " + liveNames.size() + ", "
                        + liveNames.subList(Math.min(baseNames.size(), liveNames.size()), liveNames.size()) + ")");
        JsonObject chemplant = new JsonObject();
        chemplant.addProperty("name", "ass.chemplant");
        JsonArray chemIn = new JsonArray();
        chemIn.add(item("hbmsntm:ingot_steel", 8, wildcard));
        chemIn.add(item("hbmsntm:pipe_copper", 2, wildcard));
        chemIn.add(item("hbmsntm:plate_polymer", 16, wildcard));
        chemIn.add(item("hbmsntm:motor", 2, wildcard));
        chemIn.add(item("hbmsntm:coil_tungsten", 2, wildcard));
        chemIn.add(item("hbmsntm:circuit_analog_board", 1, wildcard));
        chemplant.add("inputItem", chemIn);
        JsonArray chemSingle = new JsonArray();
        chemSingle.add("single");
        JsonArray chemStack = new JsonArray();
        chemStack.add("hbmsntm:machine_chemical_plant");
        chemSingle.add(chemStack);
        JsonArray chemOut = new JsonArray();
        chemOut.add(chemSingle);
        chemplant.add("outputItem", chemOut);
        chemplant.addProperty("duration", 200);
        chemplant.addProperty("power", 100);
        check(liveNames.subList(Math.min(baseNames.size() + 1, liveNames.size()), Math.max(liveNames.size() - goal13a.size() - goal13b.size() - goal12b.size(), 0)).equals(goal11c)
                        && chemplant.equals(live.get("ass.chemplant")),
                "Goal 11C entries are exactly these, after ass.tank: " + goal11c + " = ass.chemplant 200 ticks, 100 HE/t, 8 steel ingots, 2 copper pipes, "
                        + "16 polymer plates, 2 motors, 2 tungsten coils, 1 analog circuit board -> 1 chemical plant (original "
                        + "AssemblyMachineRecipes.java:264-265): " + live.get("ass.chemplant"));
        JsonObject cracker = new JsonObject();
        cracker.addProperty("name", "ass.crackingtower");
        JsonArray crackIn = new JsonArray();
        crackIn.add(item("hbmsntm:steel_scaffold", 16, wildcard));
        crackIn.add(item("hbmsntm:shell_steel", 6, wildcard));
        crackIn.add(item("hbmsntm:ingot_desh", 12, wildcard));
        crackIn.add(item("hbmsntm:ingot_niobium", 4, wildcard));
        cracker.add("inputItem", crackIn);
        JsonArray crackSingle = new JsonArray();
        crackSingle.add("single");
        JsonArray crackStack = new JsonArray();
        crackStack.add("hbmsntm:machine_catalytic_cracker");
        crackSingle.add(crackStack);
        JsonArray crackOut = new JsonArray();
        crackOut.add(crackSingle);
        cracker.add("outputItem", crackOut);
        cracker.addProperty("duration", 200);
        cracker.addProperty("power", 100);
        check(liveNames.subList(Math.max(liveNames.size() - goal13a.size() - goal13b.size() - goal12b.size(), 0), Math.max(liveNames.size() - goal13a.size() - goal13b.size(), 0)).equals(goal12b) && cracker.equals(live.get("ass.crackingtower")),
                "Goal 12B entries are exactly these, after ass.chemplant: " + goal12b + " = ass.crackingtower 200 ticks, 100 HE/t, 16 steel scaffolds, "
                        + "6 steel shells, 12 desh ingots, 4 niobium ingots -> 1 catalytic cracking tower (original AssemblyMachineRecipes.java:316-317): "
                        + live.get("ass.crackingtower"));
        check(liveNames.subList(Math.max(liveNames.size() - goal13a.size() - 1, 0), Math.max(liveNames.size() - 1, 0)).equals(goal13a)
                        && goal13a.stream().allMatch(n -> { GenericRecipe r = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(n); return r != null && r.isPooled() && r.getPools().length == 1 && r.getPools()[0].equals("alt..circuit") && r.customLocalization; }),
                "Goal 13A entries are exactly these, after ass.crackingtower: " + goal13a + ", each named and in the pool alt..circuit (migration/GOAL13A.md A4)");
        check(liveNames.get(liveNames.size() - goal13a.size() - 2).equals("ass.chip") && liveNames.get(liveNames.size() - 1).equals("ass.arcfurnace"),
                "Goal 13B entries are exactly these: " + goal13b + ", ass.chip directly after ass.crackingtower and in front of the Goal 13A entries, ass.arcfurnace last (migration/GOAL13B.md B4)");
        check(liveNames.subList(0, baseNames.size()).equals(baseNames), "every post-Goal 11A recipe keeps its name and order");
        List<String> changed = new ArrayList<>();
        for(String name : baseNames) if(!live.get(name).equals(base.get(name))) changed.add(name);
        check(changed.isEmpty(), "no post-Goal 11A recipe changes: " + changed);
        // Goal 11D: the production writer names each fluid of the catalog by its internal name (the stand-in's "FLUID"), not
        // by its language key ("fluid"), as the original SerializableRecipe.java:424 writes getName().
        List<String> fluidNames = new ArrayList<>();
        for(JsonObject entry : live.values()) for(String key : List.of("inputFluid", "outputFluid"))
            if(entry.has(key)) for(JsonElement fluid : entry.getAsJsonArray(key)) fluidNames.add(fluid.getAsJsonArray().get(0).getAsString());
        check(!fluidNames.isEmpty() && fluidNames.stream().allMatch("FLUID"::equals), "Goal 11D: every fluid of the catalog is written by its internal name: " + fluidNames);

        Files.createDirectories(output);
        var gson = new GsonBuilder().setPrettyPrinting().create();
        JsonObject recipe = live.get("ass.tank");
        Path file = output.resolve("ass.tank.recipe.json");
        Files.writeString(file, gson.toJson((JsonElement) recipe) + "\n", StandardCharsets.UTF_8);
        check(JsonParser.parseString(Files.readString(file)).equals(expected), "exported " + file.getFileName() + " reads back as the expected recipe");
        System.out.println("6. fluid tank recipe: " + checks + " checks passed");
    }
}
