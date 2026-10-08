package com.hbm.inventory.recipes.loader;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;

import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Goal 11C sections 1 and 4 (recipe world): the chemical plant assembler recipe and the polymer recipe through the
 * production GenericRecipes writer, compared with the original and with the post-Goal 11B tables (goal11c.base, the
 * base-g11b copies of AssemblyMachineRecipes and ChemicalPlantRecipes compiled in the same world).
 *
 * Original (Hbm-s-Nuclear-Tech-GIT): AssemblyMachineRecipes.java:264-265 ass.chemplant, normal mode: 200 ticks, 100 HE/t,
 * 8 steel ingots (ore dictionary), 2 copper pipes (ore dictionary), 16 polymer plates, 2 motors, 2 tungsten coils,
 * 1 analog circuit -> 1 chemical plant, no blueprint pool; ChemicalPlantRecipes.java:209-212 chem.polymer: 2 coal powder,
 * 1 fluorite, 1,000 mB petroleum gas -> 4 polymer ingots, 100 ticks, 100 HE/t; :196-201 chem.desh: 1 desh blend,
 * 200 mB light oil, 200 mB mercury -> 1 desh ingot, 100 ticks, 100 HE/t.
 */
public class Goal11CRecipeRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();

    private static void check(boolean condition, String message) {
        if(!condition) throw new AssertionError(message);
        checks++;
        sectionChecks++;
    }

    private static void info(String message) {
        System.out.println("info: " + message);
    }

    interface Body { void run() throws Exception; }

    private static void run(String name, Body body) {
        sectionChecks = 0;
        try {
            body.run();
            System.out.println(name + ": " + sectionChecks + " checks passed");
        } catch(AssertionError e) {
            failures.add(name);
            System.out.println("AssertionError in " + name + " after " + sectionChecks + " passed checks: " + e.getMessage());
        } catch(Exception e) {
            failures.add(name);
            System.out.println("Exception in " + name + ": " + e);
            e.printStackTrace(System.out);
        }
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

    static JsonArray fluid(String name, int fill) {
        JsonArray a = new JsonArray();
        a.add(name);
        a.add(fill);
        return a;
    }

    /**
     * Goal 11D: the expected export with every fluid named by its internal name instead of its language key
     * (hbmfluid.petroleum -> PETROLEUM; the language key is "hbmfluid." + the lower-case internal name, original
     * FluidType.java:61-63), as SerializableRecipe.writeFluidStack writes since Goal 11D (original SerializableRecipe.java:424).
     */
    static JsonObject goal11d(JsonObject withKeys) {
        JsonObject out = withKeys.deepCopy();
        for(String key : List.of("inputFluid", "outputFluid")) {
            if(!out.has(key)) continue;
            for(JsonElement e : out.getAsJsonArray(key)) {
                JsonArray stack = e.getAsJsonArray();
                String name = stack.get(0).getAsString();
                if(name.startsWith("hbmfluid.")) stack.set(0, new JsonPrimitive(name.substring("hbmfluid.".length()).toUpperCase(java.util.Locale.ROOT)));
            }
        }
        return out;
    }

    static JsonArray single(String id, int count) {
        JsonArray stack = new JsonArray();
        stack.add(id);
        if(count != 1) stack.add(count);
        JsonArray single = new JsonArray();
        single.add("single");
        single.add(stack);
        JsonArray out = new JsonArray();
        out.add(single);
        return out;
    }

    static JsonArray array(JsonArray... entries) {
        JsonArray a = new JsonArray();
        for(JsonArray e : entries) a.add(e);
        return a;
    }

    static void export(Path output, JsonObject recipe) throws Exception {
        Files.createDirectories(output);
        var gson = new GsonBuilder().setPrettyPrinting().create();
        Path file = output.resolve(recipe.get("name").getAsString() + ".recipe.json");
        Files.writeString(file, gson.toJson((JsonElement) recipe) + "\n", StandardCharsets.UTF_8);
        check(JsonParser.parseString(Files.readString(file)).equals(recipe), "exported " + file.getFileName() + " reads back as the expected recipe");
    }

    static final int WILDCARD = 32767;

    static void assembly(Path output) throws Exception {
        Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);
        Map<String, JsonObject> base = catalog(goal11c.base.AssemblyMachineRecipes.INSTANCE);
        List<String> liveNames = new ArrayList<>(live.keySet());
        List<String> baseNames = new ArrayList<>(base.keySet());

        JsonObject expected = new JsonObject();
        expected.addProperty("name", "ass.chemplant");
        expected.add("inputItem", array(item("hbmsntm:ingot_steel", 8, WILDCARD), item("hbmsntm:pipe_copper", 2, WILDCARD),
                item("hbmsntm:plate_polymer", 16, WILDCARD), item("hbmsntm:motor", 2, WILDCARD), item("hbmsntm:coil_tungsten", 2, WILDCARD),
                item("hbmsntm:circuit_analog_board", 1, WILDCARD)));
        expected.add("outputItem", single("hbmsntm:machine_chemical_plant", 1));
        expected.addProperty("duration", 200);
        expected.addProperty("power", 100);

        check(!base.containsKey("ass.chemplant") && baseNames.get(baseNames.size() - 1).equals("ass.tank"),
                "the post-Goal 11B catalog has no ass.chemplant and ends with ass.tank (" + baseNames.size() + " recipes)");
        check(expected.equals(live.get("ass.chemplant")),
                "ass.chemplant: 200 ticks, 100 HE/t, 8 steel ingots, 2 copper pipes, 16 polymer plates, 2 motors, 2 tungsten coils, "
                        + "1 analog circuit board -> 1 chemical plant (original AssemblyMachineRecipes.java:264-265): " + live.get("ass.chemplant"));
        GenericRecipe recipe = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.chemplant");
        check(recipe != null && !recipe.isPooled() && recipe.getPools() == null && !live.get("ass.chemplant").has("blueprintpool"),
                "ass.chemplant is not pooled (no blueprint needed, as the original registers it without setPools)");
        check(liveNames.size() == baseNames.size() + 1 && liveNames.get(liveNames.size() - 1).equals("ass.chemplant")
                        && liveNames.get(liveNames.size() - 2).equals("ass.tank"),
                "exactly one recipe is added, ass.chemplant, last and directly after ass.tank (" + baseNames.size() + " -> " + liveNames.size() + ")");
        check(liveNames.subList(0, baseNames.size()).equals(baseNames), "every post-Goal 11B recipe keeps its name and order");
        List<String> changed = new ArrayList<>();
        for(String name : baseNames) if(!live.get(name).equals(base.get(name))) changed.add(name);
        check(changed.isEmpty(), "no post-Goal 11B assembler recipe changes: " + changed);
        export(output, live.get("ass.chemplant"));
        info("assembler recipes: " + baseNames.size() + " post-Goal 11B, " + liveNames.size() + " now");
    }

    static void polymer(Path output) throws Exception {
        Map<String, JsonObject> live = catalog(ChemicalPlantRecipes.INSTANCE);
        Map<String, JsonObject> base = catalog(goal11c.base.ChemicalPlantRecipes.INSTANCE);
        List<String> liveNames = new ArrayList<>(live.keySet());
        List<String> baseNames = new ArrayList<>(base.keySet());

        JsonObject polymer = new JsonObject();
        polymer.addProperty("name", "chem.polymer");
        polymer.add("inputItem", array(item("hbmsntm:powder_coal", 2, WILDCARD), item("hbmsntm:fluorite", 1, WILDCARD)));
        polymer.add("inputFluid", array(fluid("hbmfluid.petroleum", 1000)));
        polymer.add("outputItem", single("hbmsntm:ingot_polymer", 4));
        polymer.addProperty("duration", 100);
        polymer.addProperty("power", 100);
        polymer.addProperty("named", true);
        // The post-Goal 11C export above names the fluid by its language key; since Goal 11D the writer names it PETROLEUM.
        check(goal11d(polymer).equals(live.get("chem.polymer")),
                "chem.polymer: 2 coal powder + 1 fluorite + 1,000 mB petroleum gas -> 4 polymer ingots, 100 ticks, 100 HE/t, named "
                        + "(original ChemicalPlantRecipes.java:209-212): " + live.get("chem.polymer"));
        JsonObject old = goal11d(polymer);
        old.getAsJsonArray("inputFluid").get(0).getAsJsonArray().set(1, new JsonPrimitive(500));
        old.add("outputItem", single("hbmsntm:ingot_polymer", 1));
        check(old.equals(base.get("chem.polymer")),
                "the post-Goal 11B chem.polymer differed only in 500 mB and 1 ingot (name, items, time, power unchanged): " + base.get("chem.polymer"));
        GenericRecipe recipe = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get("chem.polymer");
        check(recipe != null && !recipe.isPooled() && recipe.customLocalization, "chem.polymer is not pooled and keeps its named localization");

        JsonObject desh = new JsonObject();
        desh.addProperty("name", "chem.desh");
        desh.add("inputItem", array(item("hbmsntm:powder_desh_mix", 1, WILDCARD)));
        desh.add("inputFluid", array(fluid("hbmfluid.lightoil", 200), fluid("hbmfluid.mercury", 200)));
        desh.add("outputItem", single("hbmsntm:ingot_desh", 1));
        desh.addProperty("duration", 100);
        desh.addProperty("power", 100);
        desh.addProperty("named", true);
        check(goal11d(desh).equals(live.get("chem.desh")) && !ChemicalPlantRecipes.INSTANCE.recipeNameMap.get("chem.desh").isPooled(),
                "chem.desh (unchanged): 1 desh blend + 200 mB light oil + 200 mB mercury -> 1 desh ingot, 100 ticks, 100 HE/t, not pooled "
                        + "(original ChemicalPlantRecipes.java:196-201, without the LBSM simple-chemistry branch): " + live.get("chem.desh"));
        JsonArray petroleum = array(fluid("PETROLEUM", 1000));
        JsonArray deshFluids = array(fluid("LIGHTOIL", 200), fluid("MERCURY", 200));
        check(live.get("chem.polymer").getAsJsonArray("inputFluid").equals(petroleum) && live.get("chem.desh").getAsJsonArray("inputFluid").equals(deshFluids)
                        && !polymer.getAsJsonArray("inputFluid").equals(petroleum),
                "Goal 11D: the export names the fluids by their internal names, PETROLEUM and LIGHTOIL, MERCURY (the post-Goal 11C export: "
                        + "hbmfluid.petroleum, hbmfluid.lightoil, hbmfluid.mercury): " + live.get("chem.polymer").get("inputFluid") + ", "
                        + live.get("chem.desh").get("inputFluid"));

        check(liveNames.equals(baseNames), "every chemical plant recipe keeps its name and order (" + liveNames.size() + " recipes)");
        List<String> changed = new ArrayList<>();
        for(String name : baseNames) if(!live.get(name).equals(base.get(name))) changed.add(name);
        check(changed.equals(List.of("chem.polymer")), "only chem.polymer differs from the post-Goal 11B table (compiled base-g11b copy): " + changed);
        List<String> pooled = new ArrayList<>();
        for(GenericRecipe r : ChemicalPlantRecipes.INSTANCE.recipeOrderedList) if(r.isPooled()) pooled.add(r.getInternalName() + "=" + String.join(":", r.getPools()));
        info("pooled chemical plant recipes: " + pooled);
        export(output, live.get("chem.polymer"));
    }

    public static void main(String[] args) {
        Path output = Path.of(args[0]);
        run("1. chemical plant assembler recipe", () -> assembly(output));
        run("4. polymer and the chemical plant table", () -> polymer(output));
        if(!failures.isEmpty()) {
            System.out.println("Goal 11C recipe world failed sections: " + failures);
            System.exit(1);
        }
    }
}
