package com.hbm.inventory.recipes.loader;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.CrackingRecipes;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.Tuple.Pair;

import java.io.File;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Goal 12B sections 3, 9 and 10 (recipe world, real Gson): chem.coltancleaning, the CrackingRecipes template and loader, and
 * ass.crackingtower, through the production GenericRecipes and SerializableRecipe writers and readers, compared with the
 * 3687da34 tables (goal12b.head.ChemicalPlantRecipes, goal12b.head.AssemblyMachineRecipes, compiled in the same world).
 *
 * Original (Hbm-s-Nuclear-Tech-GIT d7ef2df): ChemicalPlantRecipes.java:311-315 chem.coltancleaning: 2 COLTAN.dust() (crushed
 * coltan ore) + 1 coal dust + 250 mB peroxide + 500 mB hydrogen -> purified tantalite, niobium powder, dust + 500 mB water,
 * 60 ticks, 100 HE/t; AssemblyMachineRecipes.java:316-317 ass.crackingtower, normal mode: 16 steel scaffolds, 6 steel shells,
 * 12 desh ingots, 4 niobium ingots -> 1 catalytic cracking tower, 200 ticks, 100 HE/t (the expensive inputs and the 528 pool
 * are not ported, D6a/D6b); CrackingRecipes.java:23-55 (12 defaults), :57-124 (hbmCracking.json: input, output1, output2;
 * the comment; readRecipe puts the entry).
 */
public class Goal12BRecipeRegression {
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

    // ---- 3. Coltan cleaning ------------------------------------------------------------------------------------------------

    static void cleaning() throws Exception {
        Map<String, JsonObject> live = catalog(ChemicalPlantRecipes.INSTANCE);
        Map<String, JsonObject> head = catalog(goal12b.head.ChemicalPlantRecipes.INSTANCE);
        JsonObject expected = new JsonObject();
        expected.addProperty("name", "chem.coltancleaning");
        expected.add("inputItem", array(item("hbmsntm:powder_coltan_ore", 2, WILDCARD), item("hbmsntm:powder_coal", 1, WILDCARD)));
        expected.add("inputFluid", array(fluid("PEROXIDE", 250), fluid("HYDROGEN", 500)));
        expected.add("outputItem", array(single("hbmsntm:powder_coltan", 1), single("hbmsntm:powder_niobium", 1), single("hbmsntm:dust", 1)));
        expected.add("outputFluid", array(fluid("WATER", 500)));
        expected.addProperty("duration", 60);
        expected.addProperty("power", 100);
        expected.addProperty("named", true);
        check(expected.equals(live.get("chem.coltancleaning")),
                "chem.coltancleaning: 2 crushed coltan ore + 1 coal powder + 250 mB peroxide + 500 mB hydrogen -> purified tantalite, niobium powder, dust + 500 mB water, "
                        + "60 ticks, 100 HE/t, named (original ChemicalPlantRecipes.java:311-315): " + live.get("chem.coltancleaning"));
        JsonObject old = expected.deepCopy();
        old.getAsJsonArray("inputItem").get(0).getAsJsonArray().set(1, new JsonPrimitive("hbmsntm:powder_coltan"));
        check(old.equals(head.get("chem.coltancleaning")),
                "the 3687da34 entry differed only in its first input, purified tantalite (the self-loop B1 removes): " + head.get("chem.coltancleaning"));
        check(new ArrayList<>(live.keySet()).equals(new ArrayList<>(head.keySet())), "every chemical plant recipe keeps its name and order (" + live.size() + " recipes)");
        check(changed(live, head).equals(List.of("chem.coltancleaning")), "only chem.coltancleaning differs from the 3687da34 table: " + changed(live, head));
        GenericRecipe recipe = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get("chem.coltancleaning");
        check(recipe != null && !recipe.isPooled() && recipe.customLocalization, "chem.coltancleaning is not pooled and keeps its named localization");
        ChemicalPlantRecipes.INSTANCE.deleteRecipes();
        ChemicalPlantRecipes.INSTANCE.readRecipe(live.get("chem.coltancleaning"));
        GenericRecipe read = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get("chem.coltancleaning");
        check(read != null && write(ChemicalPlantRecipes.INSTANCE, read).equals(expected), "the export reads back through the production reader and writes the same recipe");
        ChemicalPlantRecipes.INSTANCE.deleteRecipes();
        ChemicalPlantRecipes.INSTANCE.registerDefaults();
    }

    // ---- 9. The cracking template and loader -------------------------------------------------------------------------------

    static String describe(Map<FluidType, Pair<FluidStack, FluidStack>> map) {
        StringBuilder b = new StringBuilder();
        map.forEach((k, v) -> b.append(k.getInternalName()).append("->").append(v.getKey().type.getInternalName()).append(' ').append(v.getKey().fill).append('/')
                .append(v.getKey().pressure).append('+').append(v.getValue().type.getInternalName()).append(' ').append(v.getValue().fill).append('/')
                .append(v.getValue().pressure).append("; "));
        return b.toString();
    }

    static void template(Path dir) throws Exception {
        CrackingRecipes handler = new CrackingRecipes();
        handler.deleteRecipes();
        handler.registerDefaults();
        String defaults = describe(CrackingRecipes.cracking);
        check(CrackingRecipes.cracking.size() == 12 && handler.getFileName().equals("hbmCracking.json") && handler.getRecipeObject() == CrackingRecipes.cracking,
                "12 defaults; the file is hbmCracking.json; the recipe object is the table");
        Files.createDirectories(dir);
        File template = dir.resolve("_hbmCracking.json").toFile();
        handler.writeTemplateFile(template);
        JsonObject json = JsonParser.parseString(Files.readString(template.toPath(), StandardCharsets.UTF_8)).getAsJsonObject();
        JsonArray list = json.getAsJsonArray("recipes");
        List<String> wrong = new ArrayList<>();
        int i = 0;
        for(Map.Entry<FluidType, Pair<FluidStack, FluidStack>> e : CrackingRecipes.cracking.entrySet()) {
            JsonObject entry = list.get(i++).getAsJsonObject();
            JsonObject exp = new JsonObject();
            exp.addProperty("input", e.getKey().getInternalName());
            exp.add("output1", fluid(e.getValue().getKey().type.getInternalName(), e.getValue().getKey().fill));
            exp.add("output2", fluid(e.getValue().getValue().type.getInternalName(), e.getValue().getValue().fill));
            if(!entry.equals(exp)) wrong.add(entry + " != " + exp);
        }
        check(list.size() == 12 && wrong.isEmpty(), "the production writer's template lists the 12 entries in order, each {input: internal name, output1/output2: [name, amount]}: "
                + wrong);
        check(json.has("comment") && json.get("comment").getAsString().equals(handler.getComment())
                        && handler.getComment().equals("Inputs are always 100mB, set output quantities accordingly. The steam in/outputs are fixed, using 200mB of steam per 100mB of input."),
                "the template carries the original comment (CrackingRecipes.java:92-94)");
        check(list.get(6).getAsJsonObject().get("input").getAsString().equals("KEROSENE") && list.get(6).getAsJsonObject().getAsJsonArray("output2").equals(fluid("NONE", 0)),
                "kerosene's empty second output is written as [\"NONE\", 0]");
        handler.deleteRecipes();
        handler.readRecipeFile(template);
        check(describe(CrackingRecipes.cracking).equals(defaults), "the template read back through the production reader gives the same 12 entries (types, amounts, order): "
                + describe(CrackingRecipes.cracking));

        // The loader: no file -> defaults and the template; a custom hbmCracking.json replaces the table.
        Path config = dir.resolve("config");
        Files.createDirectories(config);
        NuclearTechMod.configDir = config.toFile();
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.recipeHandlers.add(handler);
        SerializableRecipe.initialize();
        Path recipes = config.resolve("hbmRecipes");
        check(Files.isRegularFile(recipes.resolve("_hbmCracking.json")) && !handler.modified && describe(CrackingRecipes.cracking).equals(defaults),
                "initialize without hbmCracking.json registers the defaults and writes _hbmCracking.json");
        Path custom = dir.resolve("custom-config");
        Files.createDirectories(custom.resolve("hbmRecipes"));
        Files.writeString(custom.resolve("hbmRecipes/hbmCracking.json"),
                "{\"recipes\":[{\"input\":\"OIL\",\"output1\":[\"CRACKOIL\",70],\"output2\":[\"PETROLEUM\",30]},"
                        + "{\"input\":\"GAS\",\"output1\":[\"PETROLEUM\",30],\"output2\":[\"UNSATURATEDS\",20]}]}", StandardCharsets.UTF_8);
        NuclearTechMod.configDir = custom.toFile();
        SerializableRecipe.initialize();
        Pair<FluidStack, FluidStack> oil = CrackingRecipes.getCracking(Fluids.OIL);
        check(handler.modified && oil != null && oil.getKey().type == Fluids.CRACKOIL && oil.getKey().fill == 70 && oil.getValue().fill == 30
                        && CrackingRecipes.getCracking(Fluids.GAS).getValue().type == Fluids.UNSATURATEDS && CrackingRecipes.cracking.size() == 2
                        && CrackingRecipes.getCracking(Fluids.BITUMEN) == null,
                "a custom hbmCracking.json with a changed crude oil entry wins: crude oil -> 70 cracked oil + 30 petroleum gas, and only its 2 entries exist "
                        + "(CrackingRecipes has no registerPost, as the original): " + describe(CrackingRecipes.cracking));
        handler.deleteRecipes();
        handler.registerDefaults();
        SerializableRecipe.recipeHandlers.clear();
        info("cracking template " + template + ": 12 entries written and read back");
    }

    // ---- 10. Assembler ---------------------------------------------------------------------------------------------------

    static void assembler() throws Exception {
        Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);
        Map<String, JsonObject> head = catalog(goal12b.head.AssemblyMachineRecipes.INSTANCE);
        List<String> liveNames = new ArrayList<>(live.keySet()), headNames = new ArrayList<>(head.keySet());
        JsonObject expected = new JsonObject();
        expected.addProperty("name", "ass.crackingtower");
        expected.add("inputItem", array(item("hbmsntm:steel_scaffold", 16, WILDCARD), item("hbmsntm:shell_steel", 6, WILDCARD),
                item("hbmsntm:ingot_desh", 12, WILDCARD), item("hbmsntm:ingot_niobium", 4, WILDCARD)));
        expected.add("outputItem", array(single("hbmsntm:machine_catalytic_cracker", 1)));
        expected.addProperty("duration", 200);
        expected.addProperty("power", 100);
        check(!head.containsKey("ass.crackingtower") && headNames.get(headNames.size() - 1).equals("ass.chemplant"),
                "the 3687da34 catalog has no ass.crackingtower and ends with ass.chemplant (" + headNames.size() + " recipes)");
        check(expected.equals(live.get("ass.crackingtower")), "ass.crackingtower: 200 ticks, 100 HE/t, 16 steel scaffolds, 6 steel shells, 12 desh ingots, 4 niobium ingots "
                + "-> 1 catalytic cracking tower, no other field (no expensive inputs, no pool; original AssemblyMachineRecipes.java:316-317): " + live.get("ass.crackingtower"));
        GenericRecipe recipe = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.crackingtower");
        check(recipe != null && !recipe.isPooled() && recipe.getPools() == null && !recipe.customLocalization && recipe.duration == 200 && recipe.power == 100,
                "not pooled (D6a), not named, 200 ticks and 100 HE/t on the recipe object");
        check(liveNames.size() == headNames.size() + 1 && liveNames.get(liveNames.size() - 1).equals("ass.crackingtower")
                        && liveNames.get(liveNames.size() - 2).equals("ass.chemplant") && liveNames.subList(0, headNames.size()).equals(headNames),
                "exactly one recipe is appended, last, directly after ass.chemplant; every earlier recipe keeps its name and order (" + headNames.size() + " -> " + liveNames.size() + ")");
        check(changed(live, head).isEmpty(), "no 3687da34 assembler recipe changes: " + changed(live, head));
        AssemblyMachineRecipes.INSTANCE.deleteRecipes();
        AssemblyMachineRecipes.INSTANCE.readRecipe(live.get("ass.crackingtower"));
        GenericRecipe read = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.crackingtower");
        check(read != null && write(AssemblyMachineRecipes.INSTANCE, read).equals(expected), "the export reads back through the production reader and writes the same recipe");
        AssemblyMachineRecipes.INSTANCE.deleteRecipes();
        AssemblyMachineRecipes.INSTANCE.registerDefaults();
        info("assembler recipes: " + headNames.size() + " at 3687da34, " + liveNames.size() + " now");
    }

    public static void main(String[] args) {
        Path out = Path.of(args[0]);
        run("3. coltan cleaning", Goal12BRecipeRegression::cleaning);
        run("9. cracking template and loader", () -> template(out));
        run("10. assembler", Goal12BRecipeRegression::assembler);
        System.out.println("Goal 12B recipe world: " + checks + " checks passed");
        if(!failures.isEmpty()) {
            System.out.println("Goal 12B recipe world failed sections: " + failures);
            System.exit(1);
        }
    }
}
