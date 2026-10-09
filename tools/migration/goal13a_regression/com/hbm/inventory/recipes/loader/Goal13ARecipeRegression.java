package com.hbm.inventory.recipes.loader;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import com.google.gson.stream.JsonWriter;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;

import java.io.StringWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Goal 13A sections 3 and 8c (recipe world, real Gson): the alt..circuit assembler recipes and the sand tag in the four concrete
 * chemical plant recipes, through the production GenericRecipes and SerializableRecipe writers and readers, compared with the
 * 12f38317 tables (goal13a.head.AssemblyMachineRecipes, goal13a.head.ChemicalPlantRecipes, compiled in the same world).
 *
 * Original (Hbm-s-Nuclear-Tech-GIT d7ef2df): AssemblyMachineRecipes.java:126 (the block exists only when !enable528), :137-138
 * ass.analogAlt setupNamed(200, 250): 4 PCB + 4 any plastic ingots + 8 tungsten fine wire + 1 niobium ingot -> 1 analog circuit
 * board; :139-140 ass.factorioChip setupNamed(300, 20,000): 2 rubber ingots + 4 iron plates + 8 copper fine wire -> 1 basic
 * (integrated) circuit; :141-142 ass.atomicClockAlt setupNamed(300, 20,000): 4 any plastic ingots + 3 microchips + 1 caesium-137
 * powder -> 4 atomic clocks; every one in the pool POOL_PREFIX_ALT + ".circuit" = "alt..circuit" (the double dot), registered
 * after the standard recipes of the block and before ass.flashdrive; ChemicalPlantRecipes.java:140-158 chem.concrete setup(100,
 * 100): 1 cement powder + 8 gravel + 8 KEY_SAND (the ore dictionary "sand") + 2,000 mB water -> 16 smooth concrete; chem.concrete
 * asbestos setup(100, 100): 4 cement + 4 asbestos ingots + 8 sand -> 16 asbestos concrete; chem.ducrete setup(150, 100): 4 cement + 1
 * ferrouranium ingot + 8 sand + 2,000 mB water -> 8 smooth ducrete; chem.liquidconk setup(100, 100): 1 cement + 8 gravel + 8 sand + 2,000
 * mB water -> 16,000 mB liquid concrete. Stack and power values are those of the original; ids are the stand-in registry's
 * (the registered names are read by verify_goal13a.py).
 */
public class Goal13ARecipeRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    static final int WILDCARD = 32767;

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
        GenericRecipes.clearPools();
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
        if(count != 1) a.add(count);
        return a;
    }

    static JsonArray fluid(String name, int fill) {
        JsonArray a = new JsonArray();
        a.add(name);
        a.add(fill);
        return a;
    }

    static JsonArray single(String id, int count) {
        JsonArray stack = new JsonArray();
        stack.add(id);
        if(count != 1) stack.add(count);
        JsonArray single = new JsonArray();
        single.add("single");
        single.add(stack);
        return single;
    }

    static JsonArray array(JsonArray... entries) {
        JsonArray a = new JsonArray();
        for(JsonArray e : entries) a.add(e);
        return a;
    }

    static List<String> changed(Map<String, JsonObject> live, Map<String, JsonObject> head) {
        List<String> out = new ArrayList<>();
        for(String name : head.keySet()) if(!head.get(name).equals(live.get(name))) out.add(name);
        return out;
    }

    static int pooled(AssemblyMachineRecipes table) {
        int n = 0;
        for(GenericRecipe r : table.recipeOrderedList) if(r.isPooled()) n++;
        return n;
    }

    static JsonObject recipe(String name, int duration, int power, JsonArray in, JsonArray out, boolean named, String pool) {
        JsonObject o = new JsonObject();
        o.addProperty("name", name);
        o.add("inputItem", in);
        o.add("outputItem", out);
        o.addProperty("duration", duration);
        o.addProperty("power", power);
        if(named) o.addProperty("named", true);
        if(pool != null) o.addProperty("blueprintpool", pool);
        return o;
    }

    // ---- 3. alt..circuit -----------------------------------------------------------------------------------------------

    static void alt(Path out) throws Exception {
        NtmConfig.COMMON.ENABLE_528.set(false);
        Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);
        Map<String, List<String>> livePools = new LinkedHashMap<>();
        GenericRecipes.blueprintPools.forEach((k, v) -> livePools.put(k, new ArrayList<>(v)));
        int livePooled = pooled(AssemblyMachineRecipes.INSTANCE);
        Map<String, JsonObject> head = catalog(goal13a.head.AssemblyMachineRecipes.INSTANCE);
        int headPooled = 0;
        for(GenericRecipe r : goal13a.head.AssemblyMachineRecipes.INSTANCE.recipeOrderedList) if(r.isPooled()) headPooled++;
        List<String> liveNames = new ArrayList<>(live.keySet()), headNames = new ArrayList<>(head.keySet());
        List<String> alt = List.of("ass.analogAlt", "ass.factorioChip", "ass.atomicClockAlt");

        JsonObject analog = recipe("ass.analogAlt", 200, 250,
                array(item("hbmsntm:circuit_printed_board", 4, WILDCARD), tag("ntm:ingots_plastic", 4), item("hbmsntm:wire_tungsten", 8, WILDCARD), item("hbmsntm:ingot_niobium", 1, WILDCARD)),
                array(single("hbmsntm:circuit_analog_board", 1)), true, "alt..circuit");
        JsonObject factorio = recipe("ass.factorioChip", 300, 20_000,
                array(item("hbmsntm:ingot_rubber", 2, WILDCARD), item("hbmsntm:plate_iron", 4, WILDCARD), item("hbmsntm:wire_copper", 8, WILDCARD)),
                array(single("hbmsntm:circuit_integrated_board", 1)), true, "alt..circuit");
        JsonObject clock = recipe("ass.atomicClockAlt", 300, 20_000,
                array(tag("ntm:ingots_plastic", 4), item("hbmsntm:circuit_microchip", 3, WILDCARD), item("hbmsntm:powder_cs137", 1, WILDCARD)),
                array(single("hbmsntm:circuit_atomic_clock", 4)), true, "alt..circuit");
        check(analog.equals(live.get("ass.analogAlt")),
                "ass.analogAlt: 200 ticks, 250 HE/t, 4 printed circuit boards + 4 of #ntm:ingots_plastic + 8 tungsten wires + 1 niobium ingot -> 1 analog circuit board, named, "
                        + "pool alt..circuit (original AssemblyMachineRecipes.java:137-138): " + live.get("ass.analogAlt"));
        check(factorio.equals(live.get("ass.factorioChip")),
                "ass.factorioChip: 300 ticks, 20,000 HE/t, 2 rubber ingots + 4 iron plates + 8 copper wires -> 1 integrated circuit board, named, pool alt..circuit (:139-140): "
                        + live.get("ass.factorioChip"));
        check(clock.equals(live.get("ass.atomicClockAlt")),
                "ass.atomicClockAlt: 300 ticks, 20,000 HE/t, 4 of #ntm:ingots_plastic + 3 microchips + 1 caesium-137 powder -> 4 atomic clocks, named, pool alt..circuit (:141-142): "
                        + live.get("ass.atomicClockAlt"));
        check(headNames.get(headNames.size() - 1).equals("ass.crackingtower") && !head.containsKey("ass.factorioChip") && !head.containsKey("ass.analogAlt")
                        && !head.containsKey("ass.atomicClockAlt"),
                "the 12f38317 catalog has none of the three and ends with ass.crackingtower (" + headNames.size() + " recipes)");
        // Goal 13B (migration/GOAL13B.md B4) puts ass.chip in front of the three recipes (same !enable528 block) and appends ass.arcfurnace after them (no
        // flag); the check below accepts exactly these two and still requires the three recipes in order directly between them (verify_goal13b.py checks both).
        check(liveNames.size() == headNames.size() + 3 + 2 && liveNames.subList(0, headNames.size()).equals(headNames) && liveNames.get(headNames.size()).equals("ass.chip")
                        && liveNames.subList(headNames.size() + 1, liveNames.size() - 1).equals(alt) && liveNames.get(liveNames.size() - 1).equals("ass.arcfurnace"),
                "exactly the three recipes are appended after ass.crackingtower, in the original order analogAlt, factorioChip, atomicClockAlt; every earlier recipe keeps name and position ("
                        + headNames.size() + " -> " + liveNames.size() + ", Goal 13B's ass.chip in front of them and ass.arcfurnace after them)");
        check(changed(live, head).isEmpty(), "no 12f38317 assembler recipe changes: " + changed(live, head));
        check(livePools.get("alt..circuit") != null && livePools.get("alt..circuit").equals(alt) && livePooled == headPooled + 3,
                "the pool alt..circuit lists the three recipes in registration order and they are the only new pooled recipes (pooled " + headPooled + " -> " + livePooled + "): " + livePools);
        for(String name : alt) {
            GenericRecipe r = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(name);
            check(r != null && r.isPooled() && r.getPools().length == 1 && r.getPools()[0].equals("alt..circuit") && r.isPartOfPool("alt..circuit") && !r.isPartOfPool("alt.circuit")
                            && !r.isPartOfPool("alt..xenonoxy") && r.customLocalization && r.nameWrapper == null,
                    name + " is in the pool \"alt..circuit\" only (double dot, the original's POOL_PREFIX_ALT + \".circuit\") and has a named localization");
        }
        info("assembler recipes: " + headNames.size() + " at 12f38317, " + liveNames.size() + " now; pooled recipes " + headPooled + " -> " + livePooled);

        // 528 mode: the block is not registered (original :126 if(!GeneralConfig.enable528)).
        NtmConfig.COMMON.ENABLE_528.set(true);
        Map<String, JsonObject> mode528 = catalog(AssemblyMachineRecipes.INSTANCE);
        Map<String, List<String>> pools528 = new LinkedHashMap<>(GenericRecipes.blueprintPools);
        NtmConfig.COMMON.ENABLE_528.set(false);
        // Goal 13B's ass.arcfurnace is registered in every mode (original AssemblyMachineRecipes.java:286-288 sits outside the !enable528 block), so the
        // 528 catalog is the 12f38317 catalog plus exactly it.
        List<String> names528 = new ArrayList<>(headNames);
        names528.add("ass.arcfurnace");
        check(new ArrayList<>(mode528.keySet()).equals(names528) && changed(mode528, head).isEmpty() && !pools528.containsKey("alt..circuit") && !AssemblyMachineRecipes.INSTANCE.recipeNameMap.containsKey("ass.factorioChip"),
                "with enable528 the three recipes and the pool alt..circuit are not registered: the catalog is the 12f38317 catalog plus Goal 13B's ass.arcfurnace (" + mode528.size() + " recipes), pools " + pools528.keySet());
        Map<String, JsonObject> again = catalog(AssemblyMachineRecipes.INSTANCE);
        check(new ArrayList<>(again.keySet()).equals(liveNames) && again.get("ass.factorioChip").equals(factorio), "and with the flag off again they are back");

        // The export reads back with its pool.
        AssemblyMachineRecipes.INSTANCE.deleteRecipes();
        GenericRecipes.clearPools();
        for(JsonObject json : live.values()) AssemblyMachineRecipes.INSTANCE.readRecipe(json);
        boolean same = true;
        for(String name : liveNames) same &= write(AssemblyMachineRecipes.INSTANCE, AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(name)).equals(live.get(name));
        GenericRecipe read = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.factorioChip");
        check(same && read != null && read.isPooled() && read.getPools()[0].equals("alt..circuit") && GenericRecipes.blueprintPools.get("alt..circuit").equals(alt),
                "the exported template reads back through the production reader: every recipe writes the same, ass.factorioChip keeps blueprintpool alt..circuit and the pool lists the three recipes");
        check(live.get("ass.factorioChip").get("blueprintpool").getAsString().equals("alt..circuit"), "the exported JSON carries \"blueprintpool\": \"alt..circuit\"");
        AssemblyMachineRecipes.INSTANCE.deleteRecipes();
        GenericRecipes.clearPools();
        AssemblyMachineRecipes.INSTANCE.registerDefaults();
        Files.writeString(out.resolve("assembler-goal13a.json"), JsonParser.parseString(live.get("ass.factorioChip").toString()).toString());
    }

    // ---- 8c. The concrete chemical plant recipes -----------------------------------------------------------------------

    static void chem(Path out) throws Exception {
        Map<String, JsonObject> live = catalog(ChemicalPlantRecipes.INSTANCE);
        Map<String, JsonObject> head = catalog(goal13a.head.ChemicalPlantRecipes.INSTANCE);
        check(new ArrayList<>(live.keySet()).equals(new ArrayList<>(head.keySet())), "every chemical plant recipe keeps its name and order (" + live.size() + " recipes)");
        List<String> names = List.of("chem.concrete", "chem.concreteasbestos", "chem.ducrete", "chem.liquidconk");
        check(changed(live, head).equals(names), "only the four concrete recipes differ from the 12f38317 table: " + changed(live, head));

        JsonObject concrete = recipe("chem.concrete", 100, 100, array(item("hbmsntm:powder_cement", 1, WILDCARD), item("minecraft:gravel", 8, WILDCARD), tag("minecraft:sand", 8)),
                array(single("hbmsntm:concrete_smooth", 16)), true, null);
        concrete.add("inputFluid", array(fluid("WATER", 2000)));
        JsonObject asbestos = recipe("chem.concreteasbestos", 100, 100, array(item("hbmsntm:powder_cement", 4, WILDCARD), item("hbmsntm:ingot_asbestos", 4, WILDCARD), tag("minecraft:sand", 8)),
                array(single("hbmsntm:concrete_asbestos", 16)), true, null);
        asbestos.add("inputFluid", array(fluid("WATER", 2000)));
        JsonObject ducrete = recipe("chem.ducrete", 150, 100, array(item("hbmsntm:powder_cement", 4, WILDCARD), item("hbmsntm:ingot_ferrouranium", 1, WILDCARD), tag("minecraft:sand", 8)),
                array(single("hbmsntm:ducrete_smooth", 8)), true, null);
        ducrete.add("inputFluid", array(fluid("WATER", 2000)));
        JsonObject liquid = new JsonObject();
        liquid.addProperty("name", "chem.liquidconk");
        liquid.add("inputItem", array(item("hbmsntm:powder_cement", 1, WILDCARD), item("minecraft:gravel", 8, WILDCARD), tag("minecraft:sand", 8)));
        liquid.add("inputFluid", array(fluid("WATER", 2000)));
        liquid.add("outputFluid", array(fluid("CONCRETE", 16_000)));
        liquid.addProperty("duration", 100);
        liquid.addProperty("power", 100);
        liquid.addProperty("named", true);
        check(concrete.equals(live.get("chem.concrete")),
                "chem.concrete: 1 cement powder + 8 gravel + 8 of #minecraft:sand + 2,000 mB water -> 16 smooth concrete, 100 ticks, 100 HE/t, named (original ChemicalPlantRecipes.java:140-143): "
                        + live.get("chem.concrete"));
        check(asbestos.equals(live.get("chem.concreteasbestos")),
                "chem.concreteasbestos: 4 cement + 4 asbestos ingots + 8 of #minecraft:sand + 2,000 mB water -> 16 asbestos concrete, 100 ticks, 100 HE/t (:145-148): " + live.get("chem.concreteasbestos"));
        check(ducrete.equals(live.get("chem.ducrete")),
                "chem.ducrete: 4 cement + 1 ferrouranium ingot + 8 of #minecraft:sand + 2,000 mB water -> 8 smooth ducrete, 150 ticks, 100 HE/t (:150-153): " + live.get("chem.ducrete"));
        check(liquid.equals(live.get("chem.liquidconk")),
                "chem.liquidconk: 1 cement + 8 gravel + 8 of #minecraft:sand + 2,000 mB water -> 16,000 mB liquid concrete, 100 ticks, 100 HE/t (:155-158): " + live.get("chem.liquidconk"));
        // The old entry differed only in the sand input: a Minecraft sand block, 8.
        for(String name : names) {
            JsonObject old = head.get(name);
            JsonObject now = live.get(name);
            JsonObject expected = now.deepCopy();
            expected.getAsJsonArray("inputItem").set(2, item("minecraft:sand", 8, WILDCARD));
            check(expected.equals(old), name + ": the 12f38317 entry had the sand block " + old.getAsJsonArray("inputItem").get(2) + " where the tag is now (nothing else differs)");
        }
        for(String name : names) {
            ChemicalPlantRecipes.INSTANCE.deleteRecipes();
            ChemicalPlantRecipes.INSTANCE.readRecipe(live.get(name));
            GenericRecipe read = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get(name);
            check(read != null && write(ChemicalPlantRecipes.INSTANCE, read).equals(live.get(name)) && !read.isPooled(),
                    name + ": the export reads back through the production reader with the sand tag intact");
        }
        ChemicalPlantRecipes.INSTANCE.deleteRecipes();
        GenericRecipes.clearPools();
        ChemicalPlantRecipes.INSTANCE.registerDefaults();
        Files.writeString(out.resolve("chem-concrete.json"), live.get("chem.concrete").toString());
        info("chemical plant recipes: " + live.size() + "; changed " + names);
    }

    public static void main(String[] args) {
        Path out = Path.of(args[0]);
        try {
            Files.createDirectories(out);
        } catch(java.io.IOException e) {
            throw new IllegalStateException(e);
        }
        run("3. alt..circuit assembler recipes", () -> alt(out));
        run("8c. concrete chemical plant recipes", () -> chem(out));
        System.out.println("Goal 13A recipe world: " + checks + " checks passed");
        if(!failures.isEmpty()) {
            System.out.println("Goal 13A recipe world failed sections: " + failures);
            System.exit(1);
        }
    }
}
