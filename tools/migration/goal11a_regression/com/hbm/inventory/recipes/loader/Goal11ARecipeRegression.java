package com.hbm.inventory.recipes.loader;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.items.CastPlateItem;

import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Goal 11A section 2: the titanium drill and derrick assembler recipes through the production GenericRecipes writer,
 * compared with the original (AssemblyMachineRecipes.java:163-164 ass.titaniumdrill: 100 ticks, 100 HE/t, 1 high-speed
 * steel cast plate, 8 titanium plates; :297-298 ass.derrick: 200 ticks, 100 HE/t, 8 steel plates, 2 copper cast plates,
 * 4 steel pipes, 1 motor, 1 titanium drill) and with the 8a209c35 catalog (goal11a.head.AssemblyMachineRecipes).
 * Goal 11B (migration/GOAL11B.md D6) appends exactly one recipe after the Goal 11A state, ass.tank (original
 * AssemblyMachineRecipes.java:472-474, normal mode: 8 steel plates, 4 steel shells, 200 ticks, 100 HE/t); the catalog
 * comparison accepts exactly that entry at the end and checks it, everything else is compared as before.
 * Goal 11C (migration/GOAL11C.md D1) appends exactly ass.chemplant after ass.tank (original AssemblyMachineRecipes.java:264-265,
 * normal mode); one added check requires exactly that entry there with the original's inputs.
 */
public class Goal11ARecipeRegression {
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

    static JsonObject expected(String name, String output, int duration, JsonArray... inputs) {
        JsonObject o = new JsonObject();
        o.addProperty("name", name);
        JsonArray in = new JsonArray();
        for(JsonArray i : inputs) in.add(i);
        o.add("inputItem", in);
        JsonArray single = new JsonArray();
        single.add("single");
        JsonArray stack = new JsonArray();
        stack.add(output);
        single.add(stack);
        JsonArray out = new JsonArray();
        out.add(single);
        o.add("outputItem", out);
        o.addProperty("duration", duration);
        o.addProperty("power", 100);
        return o;
    }

    public static void main(String[] args) throws Exception {
        try {
            recipes(Path.of(args[0]));
        } catch(AssertionError e) {
            System.out.println("AssertionError in 2. recipes after " + (checks - 1) + " passed checks: " + e.getMessage());
            throw e;
        }
    }

    static void recipes(Path output) throws Exception {
        int wildcard = 32767;
        int dura = CastPlateItem.Type.DURA_STEEL.ordinal(), copper = CastPlateItem.Type.COPPER.ordinal();

        Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);
        Map<String, JsonObject> head = catalog(goal11a.head.AssemblyMachineRecipes.INSTANCE);

        JsonObject drill = expected("ass.drill_titanium", "hbmsntm:drill_titanium", 100,
                item("hbmsntm:cast_plate", 1, dura), item("hbmsntm:plate_titanium", 8, wildcard));
        JsonObject derrick = expected("ass.machine_oil_derrick", "hbmsntm:machine_well", 200,
                item("hbmsntm:cast_plate", 2, copper), item("hbmsntm:plate_steel", 8, wildcard), item("hbmsntm:pipe_steel", 4, wildcard),
                item("hbmsntm:drill_titanium", 1, wildcard), item("hbmsntm:motor", 1, wildcard));
        check(drill.equals(live.get("ass.drill_titanium")),
                "ass.drill_titanium: 100 ticks, 100 HE/t, 1 high-speed steel cast plate (meta " + dura + ") + 8 titanium plates -> 1 titanium drill: "
                        + live.get("ass.drill_titanium"));
        check(derrick.equals(live.get("ass.machine_oil_derrick")),
                "ass.machine_oil_derrick: 200 ticks, 100 HE/t, 2 copper cast plates (meta " + copper + "), 8 steel plates, 4 steel pipes, 1 titanium drill, "
                        + "1 motor -> 1 derrick: " + live.get("ass.machine_oil_derrick"));

        // Goal 11B: exactly ass.tank is appended after the 8a209c35 catalog; it is checked here and left out of the
        // comparison below, which stays the Goal 11A one.
        // Goal 11C (migration/GOAL11C.md D1): exactly ass.chemplant follows ass.tank; it is checked by the added check below.
        List<String> goal11b = List.of("ass.tank");
        List<String> goal11c = List.of("ass.chemplant");
        List<String> liveNames = new ArrayList<>(live.keySet());
        JsonObject tank = expected("ass.tank", "hbmsntm:machine_fluid_tank", 200,
                tag("c:plates/steel", 8), item("hbmsntm:shell_steel", 4, wildcard));
        check(liveNames.size() == head.size() + goal11b.size() + goal11c.size()
                        && liveNames.subList(head.size(), head.size() + goal11b.size()).equals(goal11b)
                        && tank.equals(live.get("ass.tank")),
                "Goal 11B entries are exactly these, appended at the end: " + goal11b + " = ass.tank 200 ticks, 100 HE/t, 8 steel plates "
                        + "(c:plates/steel) + 4 steel shells -> 1 fluid tank (" + liveNames.subList(Math.min(head.size(), liveNames.size()), liveNames.size())
                        + ": " + live.get("ass.tank") + ")");
        JsonObject chemplant = expected("ass.chemplant", "hbmsntm:machine_chemical_plant", 200,
                item("hbmsntm:ingot_steel", 8, wildcard), item("hbmsntm:pipe_copper", 2, wildcard), item("hbmsntm:plate_polymer", 16, wildcard),
                item("hbmsntm:motor", 2, wildcard), item("hbmsntm:coil_tungsten", 2, wildcard), item("hbmsntm:circuit_analog_board", 1, wildcard));
        check(liveNames.subList(Math.min(head.size() + goal11b.size(), liveNames.size()), liveNames.size()).equals(goal11c)
                        && chemplant.equals(live.get("ass.chemplant")),
                "Goal 11C entries are exactly these, after the Goal 11B entry: " + goal11c + " = ass.chemplant 200 ticks, 100 HE/t, 8 steel ingots, "
                        + "2 copper pipes, 16 polymer plates, 2 motors, 2 tungsten coils, 1 analog circuit board -> 1 chemical plant "
                        + "(original AssemblyMachineRecipes.java:264-265): " + live.get("ass.chemplant"));
        check(liveNames.subList(0, head.size()).equals(new ArrayList<>(head.keySet())),
                "the catalog keeps every recipe name and its order (" + head.size() + " recipes before the Goal 11B entry)");
        List<String> changed = new ArrayList<>();
        for(String name : head.keySet()) if(!live.get(name).equals(head.get(name))) changed.add(name);
        check(changed.equals(List.of("ass.drill_titanium", "ass.machine_oil_derrick")),
                "only the two Goal 11A recipes differ from 8a209c35: " + changed);
        JsonObject oldDrill = head.get("ass.drill_titanium").deepCopy();
        oldDrill.addProperty("duration", 100);
        check(oldDrill.equals(drill), "the drill recipe differs from 8a209c35 only in its duration (200 -> 100 ticks)");
        JsonObject oldDerrick = head.get("ass.machine_oil_derrick").deepCopy();
        JsonArray oldPlate = oldDerrick.getAsJsonArray("inputItem").get(0).getAsJsonArray();
        check(oldPlate.get(2).getAsInt() == 1, "8a209c35 had one copper cast plate");
        oldPlate.set(2, new com.google.gson.JsonPrimitive(2));
        check(oldDerrick.equals(derrick), "the derrick recipe differs from 8a209c35 only in the copper cast plate count (1 -> 2)");
        // Goal 11D: the production writer names each fluid of the catalog by its internal name (the stand-in's "FLUID"), not
        // by its language key ("fluid"), as the original SerializableRecipe.java:424 writes getName().
        List<String> fluidNames = new ArrayList<>();
        for(JsonObject recipe : live.values()) for(String key : List.of("inputFluid", "outputFluid"))
            if(recipe.has(key)) for(JsonElement fluid : recipe.getAsJsonArray(key)) fluidNames.add(fluid.getAsJsonArray().get(0).getAsString());
        check(!fluidNames.isEmpty() && fluidNames.stream().allMatch("FLUID"::equals), "Goal 11D: every fluid of the catalog is written by its internal name: " + fluidNames);

        Files.createDirectories(output);
        var gson = new GsonBuilder().setPrettyPrinting().create();
        for(JsonObject recipe : List.of(live.get("ass.drill_titanium"), live.get("ass.machine_oil_derrick"))) {
            Path file = output.resolve(recipe.get("name").getAsString() + ".recipe.json");
            Files.writeString(file, gson.toJson((JsonElement) recipe) + "\n", StandardCharsets.UTF_8);
            check(JsonParser.parseString(Files.readString(file)).equals(recipe), "exported " + file.getFileName() + " reads back unchanged");
        }
        System.out.println("2. recipes: " + checks + " checks passed");
    }
}
