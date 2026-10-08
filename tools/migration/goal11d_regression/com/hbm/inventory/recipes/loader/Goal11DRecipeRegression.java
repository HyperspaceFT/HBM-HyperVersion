package com.hbm.inventory.recipes.loader;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.ArcWelderRecipes;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.SolderingRecipes;

import java.io.File;
import java.io.StringWriter;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.function.Supplier;

/**
 * Goal 11D sections 1-3 (recipe world): the fluid name that SerializableRecipe.writeFluidStack writes into the recipe
 * templates of the four tables that call it (GenericRecipes.writeRecipe for the chemical plant and assembly machine tables,
 * SolderingRecipes.writeRecipe, ArcWelderRecipes.writeRecipe), read back through the production reader.
 *
 * Original (Hbm-s-Nuclear-Tech-GIT): SerializableRecipe.java:421-428 writeFluidStack writes [type.getName(), fill] plus the
 * pressure only when it is not 0; FluidType.java:157-159 getName() is the internal name (stringId, FluidType.java:61);
 * SerializableRecipe.java:400-402 readFluidStack resolves the name with Fluids.fromName (Fluids.java:980-986), whose map is
 * keyed by getName() (Fluids.java:961) and gives NONE for any other string.
 *
 * Two runs of this class: "export DIR" in the world compiled with the post-Goal 11C SerializableRecipe (git 1e29ad29) writes
 * the four templates as the game does (writeTemplateFile); "verify OUT BASELINE REFERENCE" in the world compiled with the
 * production SerializableRecipe runs the sections and reads the post-Goal 11C templates back with the production reader.
 */
public class Goal11DRecipeRegression {
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

    /** A table that calls writeFluidStack: its handler, its recipe list and the fluid stacks of one recipe in write order. */
    record Table(String label, SerializableRecipe handler, Supplier<List<?>> recipes, Function<Object, List<FluidStack>> fluids) {
        File template(File dir) { return new File(dir, "_" + handler.getFileName()); }
        void defaults() { handler.deleteRecipes(); handler.registerDefaults(); }
    }

    static List<FluidStack> generic(GenericRecipes<?> table, Object o) {
        GenericRecipe recipe = (GenericRecipe) o;
        List<FluidStack> out = new ArrayList<>();
        // GenericRecipes.writeRecipe: inputFluid, then outputFluid, each only when the table's limit is above 0.
        if(table.inputFluidLimit() > 0 && recipe.inputFluid != null) out.addAll(List.of(recipe.inputFluid));
        if(table.outputFluidLimit() > 0 && recipe.outputFluid != null) out.addAll(List.of(recipe.outputFluid));
        return out;
    }

    static List<FluidStack> single(FluidStack fluid) {
        return fluid == null ? List.of() : List.of(fluid);
    }

    static List<Table> tables() {
        return List.of(
                new Table("chemical plant", ChemicalPlantRecipes.INSTANCE, () -> ChemicalPlantRecipes.INSTANCE.recipeOrderedList,
                        o -> generic(ChemicalPlantRecipes.INSTANCE, o)),
                new Table("assembly machine", AssemblyMachineRecipes.INSTANCE, () -> AssemblyMachineRecipes.INSTANCE.recipeOrderedList,
                        o -> generic(AssemblyMachineRecipes.INSTANCE, o)),
                new Table("soldering station", new SolderingRecipes(), () -> SolderingRecipes.recipes,
                        o -> single(((SolderingRecipes.SolderingRecipe) o).fluid)),
                new Table("arc welder", new ArcWelderRecipes(), () -> ArcWelderRecipes.recipes,
                        o -> single(((ArcWelderRecipes.ArcWelderRecipe) o).fluid)));
    }

    /** The Fluids field that holds this type; the stand-in FluidType's internal name is its field name (checked by Python). */
    static String fieldName(FluidType type) throws Exception {
        for(Field field : Fluids.class.getFields()) {
            if(Modifier.isStatic(field.getModifiers()) && field.getType() == FluidType.class && field.get(null) == type) return field.getName();
        }
        throw new AssertionError("fluid type without a Fluids field: " + type);
    }

    /** The fluid arrays of one exported recipe object, in the order the writers emit them. */
    static List<JsonArray> fluidArrays(JsonObject recipe) {
        List<JsonArray> out = new ArrayList<>();
        for(String key : List.of("inputFluid", "outputFluid")) {
            if(recipe.has(key)) for(JsonElement e : recipe.getAsJsonArray(key)) out.add(e.getAsJsonArray());
        }
        if(recipe.has("fluid")) out.add(recipe.getAsJsonArray("fluid"));
        return out;
    }

    /** The original's array form: [internal name, amount] plus the pressure only when it is not 0. */
    static JsonArray expected(FluidStack stack) throws Exception {
        JsonArray a = new JsonArray();
        a.add(fieldName(stack.type));
        a.add(stack.fill);
        if(stack.pressure != 0) a.add(stack.pressure);
        return a;
    }

    static JsonArray parseArray(String text) {
        return JsonParser.parseString(text).getAsJsonArray();
    }

    static JsonArray written(FluidStack stack) throws Exception {
        StringWriter text = new StringWriter();
        JsonWriter writer = new JsonWriter(text);
        SerializableRecipe.writeFluidStack(stack, writer);
        writer.close();
        return parseArray(text.toString());
    }

    static String describe(FluidStack s) throws Exception {
        return fieldName(s.type) + " " + s.fill + " mB" + (s.pressure != 0 ? " pressure " + s.pressure : "");
    }

    /** The recipe list after a read; a recipe the list holds twice in a row (the same object) counts once (see below). */
    static List<Object> collapsed(List<?> list) {
        List<Object> out = new ArrayList<>();
        for(Object o : list) if(out.isEmpty() || out.get(out.size() - 1) != o) out.add(o);
        return out;
    }

    static List<List<FluidStack>> fluidsOf(Table table, List<?> recipes) {
        List<List<FluidStack>> out = new ArrayList<>();
        for(Object o : recipes) out.add(table.fluids().apply(o));
        return out;
    }

    // ---- export mode (post-Goal 11C world) ------------------------------------------------------------------------------

    static void export(File dir) throws Exception {
        dir.mkdirs();
        for(Table table : tables()) {
            table.defaults();
            table.handler().writeTemplateFile(table.template(dir));
            if(!table.template(dir).isFile()) throw new IllegalStateException("no template written for " + table.label());
            System.out.println("post-Goal 11C template: " + table.template(dir).getName() + " (" + table.recipes().get().size() + " recipes)");
        }
    }

    // ---- verify mode (production world) ---------------------------------------------------------------------------------

    static final Map<String, List<List<FluidStack>>> defaults = new LinkedHashMap<>();
    static final Map<String, int[]> counts = new LinkedHashMap<>();

    static void writer(File out) throws Exception {
        // The writer on single stacks, as the original array form (SerializableRecipe.java:421-428).
        check(written(new FluidStack(Fluids.PETROLEUM, 1_000)).equals(parseArray("[\"PETROLEUM\",1000]")),
                "writeFluidStack(PETROLEUM, 1,000 mB) -> [\"PETROLEUM\",1000]: " + written(new FluidStack(Fluids.PETROLEUM, 1_000)));
        check(written(new FluidStack(Fluids.PEROXIDE, 1_000, 5)).equals(parseArray("[\"PEROXIDE\",1000,5]")),
                "writeFluidStack(PEROXIDE, 1,000 mB, pressure 5) -> [\"PEROXIDE\",1000,5]: " + written(new FluidStack(Fluids.PEROXIDE, 1_000, 5)));
        check(!written(new FluidStack(Fluids.PETROLEUM, 1_000)).toString().contains("hbmfluid."),
                "the writer does not write the language key (hbmfluid.petroleum)");

        File dir = new File(out, "production");
        dir.mkdirs();
        int pressured = 0;
        for(Table table : tables()) {
            table.defaults();
            List<?> recipes = new ArrayList<>(table.recipes().get());
            List<List<FluidStack>> fluids = fluidsOf(table, recipes);
            defaults.put(table.label(), fluids);
            table.handler().writeTemplateFile(table.template(dir));
            JsonArray exported = JsonParser.parseString(Files.readString(table.template(dir).toPath(), StandardCharsets.UTF_8))
                    .getAsJsonObject().getAsJsonArray("recipes");
            check(exported.size() == recipes.size(), table.label() + ": the template holds every registered recipe (" + recipes.size() + ")");
            int stacks = 0;
            List<String> wrong = new ArrayList<>();
            for(int i = 0; i < recipes.size(); i++) {
                List<JsonArray> arrays = fluidArrays(exported.get(i).getAsJsonObject());
                List<FluidStack> expectedStacks = fluids.get(i);
                if(arrays.size() != expectedStacks.size()) wrong.add(i + ": " + arrays.size() + " arrays for " + expectedStacks.size() + " stacks");
                for(int j = 0; j < Math.min(arrays.size(), expectedStacks.size()); j++) {
                    FluidStack stack = expectedStacks.get(j);
                    if(!arrays.get(j).equals(expected(stack))) wrong.add(exported.get(i).getAsJsonObject().get("name") + " " + arrays.get(j) + " for " + describe(stack));
                    if(stack.pressure != 0) pressured++;
                    stacks++;
                }
            }
            check(wrong.isEmpty(), table.label() + ": every fluid stack of the template is [internal name, amount(, pressure if not 0)] of its registered stack: "
                    + wrong.subList(0, Math.min(5, wrong.size())));
            check(stacks > 0, table.label() + ": the table has fluid stacks to write (" + stacks + ")");
            counts.put(table.label(), new int[] { recipes.size(), stacks });
            info(table.label() + ": " + recipes.size() + " recipes, " + stacks + " fluid stacks written by the production writer to " + table.template(dir).getName());
        }
        check(pressured > 0, "the tables include stacks with a pressure, written as the third element (" + pressured + ")");
    }

    static void roundTrip(File out, File baseline) throws Exception {
        File dir = new File(out, "production");
        for(Table table : tables()) {
            List<List<FluidStack>> expected = defaults.get(table.label());
            // The production template, read back by the production reader.
            table.handler().deleteRecipes();
            table.handler().readRecipeFile(table.template(dir));
            List<?> raw = new ArrayList<>(table.recipes().get());
            List<Object> read = collapsed(raw);
            if(raw.size() != read.size()) {
                // NEO SolderingRecipes.readRecipe added the recipe its SolderingRecipe constructor already added (pre-existing,
                // not Goal 11D; the original constructor does not add itself), so each recipe was the same object twice in a row.
                // Fixed in Goal 12A (migration/GOAL12A.md part 4): readRecipe no longer adds, so this branch no longer prints.
                info(table.label() + ": a read-back recipe list holds every recipe twice in a row (" + raw.size() + " entries for "
                        + read.size() + " recipes; SolderingRecipes.readRecipe and the SolderingRecipe constructor both add it)");
            }
            List<List<FluidStack>> back = fluidsOf(table, read);
            check(back.size() == expected.size(), table.label() + ": every recipe reads back (" + back.size() + " of " + expected.size() + ")");
            List<String> wrong = new ArrayList<>();
            int stacks = 0;
            for(int i = 0; i < expected.size(); i++) {
                List<FluidStack> a = expected.get(i), b = back.get(i);
                if(a.size() != b.size()) { wrong.add(i + ": " + b.size() + " stacks for " + a.size()); continue; }
                for(int j = 0; j < a.size(); j++, stacks++) {
                    if(a.get(j).type != b.get(j).type || a.get(j).fill != b.get(j).fill || a.get(j).pressure != b.get(j).pressure)
                        wrong.add(i + ": " + describe(b.get(j)) + " for " + describe(a.get(j)));
                }
            }
            check(wrong.isEmpty(), table.label() + ": written and read back, every recipe has the registered fluids (type, amount, pressure): "
                    + wrong.subList(0, Math.min(5, wrong.size())));
            info(table.label() + ": round trip compared " + expected.size() + " recipes and " + stacks + " fluid stacks");

            // Baseline: the post-Goal 11C template (language keys), read back by the same production reader.
            table.handler().deleteRecipes();
            table.handler().readRecipeFile(table.template(baseline));
            List<List<FluidStack>> old = fluidsOf(table, collapsed(new ArrayList<>(table.recipes().get())));
            int none = 0, total = 0;
            List<String> kept = new ArrayList<>();
            for(int i = 0; i < Math.min(old.size(), expected.size()); i++) {
                List<FluidStack> a = expected.get(i), b = old.get(i);
                for(int j = 0; j < Math.min(a.size(), b.size()); j++, total++) {
                    if(b.get(j).type == Fluids.NONE && b.get(j).fill == a.get(j).fill && b.get(j).pressure == a.get(j).pressure) none++;
                    else kept.add(describe(b.get(j)));
                }
            }
            check(old.size() == expected.size() && total == stacks && none == stacks && kept.isEmpty(),
                    table.label() + ": baseline, the post-Goal 11C template read back turns all " + stacks + " fluid stacks into NONE (amount and pressure kept): "
                            + none + " NONE of " + total + ", not NONE " + kept.subList(0, Math.min(5, kept.size())));
            info(table.label() + ": baseline (post-Goal 11C writer) read back " + none + " of " + stacks + " fluid stacks as NONE");
            table.defaults();
        }
    }

    static void reader() throws Exception {
        FluidStack petroleum = SerializableRecipe.readFluidStack(parseArray("[\"PETROLEUM\",1000]"));
        check(petroleum.type == Fluids.PETROLEUM && petroleum.fill == 1_000 && petroleum.pressure == 0,
                "[\"PETROLEUM\",1000] reads as petroleum gas, 1,000 mB, pressure 0");
        FluidStack pressured = SerializableRecipe.readFluidStack(parseArray("[\"PEROXIDE\",1000,5]"));
        check(pressured.type == Fluids.PEROXIDE && pressured.fill == 1_000 && pressured.pressure == 5,
                "[\"PEROXIDE\",1000,5] reads as peroxide, 1,000 mB, pressure 5");
        FluidStack key = SerializableRecipe.readFluidStack(parseArray("[\"hbmfluid.petroleum\",1000]"));
        check(key.type == Fluids.NONE && key.fill == 1_000,
                "a language key [\"hbmfluid.petroleum\",1000] reads as NONE (1,000 mB): the reader has no fallback, as decided");
        FluidStack lower = SerializableRecipe.readFluidStack(parseArray("[\"petroleum\",1000]"));
        check(lower.type == Fluids.NONE, "a lower-case name [\"petroleum\",1000] reads as NONE (the name is matched exactly)");
        FluidStack unknown = SerializableRecipe.readFluidStack(parseArray("[\"NOT_A_FLUID\",7]"));
        check(unknown.type == Fluids.NONE && unknown.fill == 7, "an unknown name [\"NOT_A_FLUID\",7] reads as NONE (7 mB)");
        FluidStack[] array = SerializableRecipe.readFluidArray(parseArray("[[\"LIGHTOIL\",200],[\"hbmfluid.mercury\",200]]"));
        check(array.length == 2 && array[0].type == Fluids.LIGHTOIL && array[0].fill == 200 && array[1].type == Fluids.NONE && array[1].fill == 200,
                "readFluidArray([[\"LIGHTOIL\",200],[\"hbmfluid.mercury\",200]]) -> light oil, NONE");
    }

    static void reference(File referenceDir) throws Exception {
        ChemicalPlantRecipes table = ChemicalPlantRecipes.INSTANCE;
        table.deleteRecipes();
        table.registerDefaults();
        StringWriter text = new StringWriter();
        JsonWriter writer = new JsonWriter(text);
        writer.beginObject();
        table.writeRecipe(table.recipeNameMap.get("chem.polymer"), writer);
        writer.endObject();
        writer.close();
        JsonObject recipe = JsonParser.parseString(text.toString()).getAsJsonObject();
        // The single-recipe reference in the format of the Goal 11C reference (Goal11CRecipeRegression.export).
        Path file = referenceDir.toPath().resolve("chem.polymer.recipe.json");
        Files.createDirectories(referenceDir.toPath());
        Files.writeString(file, new GsonBuilder().setPrettyPrinting().create().toJson((JsonElement) recipe) + "\n", StandardCharsets.UTF_8);
        JsonObject back = JsonParser.parseString(Files.readString(file)).getAsJsonObject();
        check(back.equals(recipe) && back.getAsJsonArray("inputFluid").equals(parseArray("[[\"PETROLEUM\",1000]]")),
                "chem.polymer.recipe.json names its fluid PETROLEUM: " + back.get("inputFluid"));
        table.deleteRecipes();
        table.readRecipe(back);
        GenericRecipe read = table.recipeNameMap.get("chem.polymer");
        check(read != null && read.inputFluid.length == 1 && read.inputFluid[0].type == Fluids.PETROLEUM && read.inputFluid[0].fill == 1_000,
                "chem.polymer.recipe.json read back by the production reader: 1,000 mB petroleum gas");
        table.deleteRecipes();
        table.registerDefaults();
    }

    public static void main(String[] args) throws Exception {
        if(args[0].equals("export")) {
            export(new File(args[1]));
            return;
        }
        File out = new File(args[1]);
        File baseline = new File(args[2]);
        File referenceDir = new File(args[3]);
        run("1. writer", () -> writer(out));
        run("2. round trip", () -> roundTrip(out, baseline));
        run("3. reader unchanged, no fallback", Goal11DRecipeRegression::reader);
        run("1r. chem.polymer reference", () -> reference(referenceDir));
        StringBuilder json = new StringBuilder("{");
        counts.forEach((label, c) -> json.append(json.length() > 1 ? "," : "").append("\"").append(label).append("\":{\"recipes\":")
                .append(c[0]).append(",\"stacks\":").append(c[1]).append("}"));
        Files.writeString(new File(out, "counts.json").toPath(), json.append("}\n").toString(), StandardCharsets.UTF_8);
        if(!failures.isEmpty()) {
            System.out.println("Goal 11D recipe world failed sections: " + failures);
            System.exit(1);
        }
    }
}
