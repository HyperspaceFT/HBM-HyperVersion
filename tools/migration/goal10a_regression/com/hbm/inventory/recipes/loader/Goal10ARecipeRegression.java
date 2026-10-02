package com.hbm.inventory.recipes.loader;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.CrucibleRecipe;
import com.hbm.inventory.recipes.CrucibleRecipes;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.ItemStack;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Goal 10A recipe world: the real SerializableRecipe handler list and loader with CrucibleRecipes (hbmCrucible.json,
 * original CrucibleRecipes.java:143-196 for the format) and the real ShredderRecipes (original ShredderRecipes.java:178).
 */
public class Goal10ARecipeRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    private static Path config;

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void run(String name, Runnable body) {
        sectionChecks = 0;
        try {
            body.run();
            System.out.println(name + ": " + sectionChecks + " checks passed");
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            checks--;
        } catch(RuntimeException e) {
            System.out.println("Exception in " + name + " after " + sectionChecks + " passed checks: " + e);
            e.printStackTrace(System.out);
            failures.add(name + ": " + e);
        }
    }

    private static String s(MaterialStack[] stacks) {
        return Arrays.stream(stacks).map(m -> m.material.names[0] + "=" + m.amount).collect(Collectors.joining(","));
    }

    private static String read(Path path) {
        try {
            return Files.readString(path, StandardCharsets.UTF_8);
        } catch(IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static void write(Path path, String text) {
        try {
            Files.writeString(path, text, StandardCharsets.UTF_8);
        } catch(IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String entry(String name, int frequency, String input, String output) {
        return "{\"name\":\"" + name + "\",\"frequency\":" + frequency + ",\"icon\":[\"hbmsntm:ingot_dura_steel\"],\"input\":" + input + ",\"output\":" + output + "}";
    }

    // ---- 5b. Handler registration and hbmCrucible.json -------------------------------------------------------------

    private static void crucibleRecipes() {
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.registerAllHandlers();
        List<SerializableRecipe> handlers = SerializableRecipe.recipeHandlers;
        long crucibles = handlers.stream().filter(h -> h == CrucibleRecipes.INSTANCE).count();
        check(crucibles == 1 && handlers.stream().filter(h -> h instanceof CrucibleRecipes).count() == 1,
                "registerAllHandlers adds CrucibleRecipes.INSTANCE exactly once");
        int chemical = handlers.indexOf(ChemicalPlantRecipes.INSTANCE);
        check(chemical >= 0 && handlers.indexOf(CrucibleRecipes.INSTANCE) == chemical + 1,
                "CrucibleRecipes follows ChemicalPlantRecipes in the handler list");
        check(handlers.size() == 9, "nine recipe handlers: " + handlers.size());

        // Only the crucible handler touches the scratch config from here on.
        handlers.removeIf(h -> h != CrucibleRecipes.INSTANCE);
        NuclearTechMod.configDir = config.toFile();
        Path directory = config.resolve("hbmRecipes");
        Path template = directory.resolve("_hbmCrucible.json");
        Path active = directory.resolve("hbmCrucible.json");
        SerializableRecipe.initialize();
        CrucibleRecipes recipes = CrucibleRecipes.INSTANCE;
        check(recipes.recipeOrderedList.size() == 1 && !recipes.modified, "no hbmCrucible.json: the defaults are registered");
        CrucibleRecipe hss = recipes.recipeNameMap.get("crucible.hss");
        check(hss != null && hss.frequency == 9 && s(hss.input).equals("Steel=40,Tungsten=24,Cobalt=8") && s(hss.output).equals("DuraSteel=72")
                && hss.getIcon().getItem() == NtmItems.INGOT_DURA_STEEL.get() && !hss.customLocalization, "default crucible.hss");
        check(Files.isRegularFile(template) && !Files.exists(active), "the template _hbmCrucible.json is written");
        JsonObject json = JsonParser.parseString(read(template)).getAsJsonObject();
        JsonArray list = json.getAsJsonArray("recipes");
        check(json.has("comment") && list.size() == 1, "template: a comment and one recipe");
        JsonObject written = list.get(0).getAsJsonObject();
        check(written.get("name").getAsString().equals("crucible.hss") && written.get("frequency").getAsInt() == 9
                && written.get("icon").toString().equals("[\"hbmsntm:ingot_dura_steel\"]"), "template: name, frequency and icon " + written);
        check(written.get("input").toString().equals("[[\"Steel\",40],[\"Tungsten\",24],[\"Cobalt\",8]]")
                && written.get("output").toString().equals("[[\"DuraSteel\",72]]"), "template: input and output as [materialName, amount]: " + written);
        check(written.keySet().equals(java.util.Set.of("name", "frequency", "icon", "input", "output")), "template keys: " + written.keySet());

        // Enabled file: the written template reads back to the same recipe.
        write(active, read(template));
        SerializableRecipe.initialize();
        CrucibleRecipe reread = recipes.recipeNameMap.get("crucible.hss");
        check(recipes.modified && recipes.recipeOrderedList.size() == 1 && reread != null && reread != hss,
                "hbmCrucible.json is read instead of the defaults");
        check(reread.frequency == 9 && s(reread.input).equals(s(hss.input)) && s(reread.output).equals(s(hss.output))
                && reread.input[0].material == Mats.MAT_STEEL && reread.output[0].material == Mats.MAT_DURA
                && reread.getIcon().getItem() == NtmItems.INGOT_DURA_STEEL.get() && reread.getIcon().getCount() == 1
                && !reread.customLocalization, "write -> read keeps name, frequency, icon, inputs and outputs");

        // Entries NEO cannot use are skipped with a warning; the rest load.
        int warnings = NuclearTechMod.LOGGER.warnings.size();
        write(active, "{\"recipes\":["
                + entry("crucible.test", 2, "[[\"Steel\",10]]", "[[\"DuraSteel\",10]]") + ","
                + entry("crucible.unknown", 2, "[[\"Bismuth\",10]]", "[[\"DuraSteel\",10]]") + ","
                + entry("crucible.unknownout", 2, "[[\"Steel\",10]]", "[[\"MingradeCopper\",10]]") + ","
                + entry("crucible.zero", 2, "[[\"Steel\",0]]", "[[\"DuraSteel\",10]]") + ","
                + entry("crucible.negative", 2, "[[\"Steel\",10]]", "[[\"DuraSteel\",-1]]") + ","
                + entry("crucible.frequency", 0, "[[\"Steel\",10]]", "[[\"DuraSteel\",10]]") + ","
                + entry("crucible.noinput", 2, "[]", "[[\"DuraSteel\",10]]") + ","
                + entry("crucible.nooutput", 2, "[[\"Steel\",10]]", "[]") + "]}");
        SerializableRecipe.initialize();
        check(recipes.recipeOrderedList.size() == 1 && recipes.recipeNameMap.keySet().equals(java.util.Set.of("crucible.test")),
                "only the usable entry registers: " + recipes.recipeNameMap.keySet());
        check(NuclearTechMod.LOGGER.warnings.size() - warnings == 7, "each skipped entry logs a warning: " + (NuclearTechMod.LOGGER.warnings.size() - warnings));
        CrucibleRecipe test = recipes.recipeNameMap.get("crucible.test");
        check(test.frequency == 2 && s(test.input).equals("Steel=10") && s(test.output).equals("DuraSteel=10"), "the usable entry loads");

        // Structurally malformed entries still fail like other handlers.
        for(String malformed : new String[] {
                "{\"name\":\"a\",\"icon\":[\"hbmsntm:ingot_dura_steel\"],\"input\":[[\"Steel\",1]],\"output\":[[\"DuraSteel\",1]]}",
                "{\"name\":\"b\",\"frequency\":1,\"icon\":[\"hbmsntm:ingot_dura_steel\"],\"input\":\"Steel\",\"output\":[[\"DuraSteel\",1]]}"}) {
            RuntimeException thrown = null;
            try {
                recipes.readRecipe(JsonParser.parseString(malformed));
            } catch(RuntimeException e) {
                thrown = e;
            }
            check(thrown != null, "a structurally malformed entry throws: " + malformed);
        }
        // SerializableRecipe.readRecipeFile does not close its FileReader, so on Windows the enabled file cannot be
        // deleted while this JVM runs; the defaults are restored through the handler instead.
        recipes.deleteRecipes();
        recipes.registerDefaults();
        check(recipes.recipeOrderedList.size() == 1 && recipes.recipeNameMap.containsKey("crucible.hss"), "the defaults register again after deleteRecipes");
    }

    // ---- 11. Shredder ------------------------------------------------------------------------------------------------

    private static void shredder() {
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.recipeHandlers.add(new ShredderRecipes());
        NuclearTechMod.configDir = config.toFile();
        SerializableRecipe.initialize();
        ItemStack result = ShredderRecipes.getShredderResult(new ItemStack(NtmItems.FRAGMENT_COBALT.get()));
        check(ShredderRecipes.hasRecipe(new ItemStack(NtmItems.FRAGMENT_COBALT.get())), "the cobalt fragment has a shredder recipe");
        check(result.getItem() == NtmItems.POWDER_COBALT_TINY.get() && result.getCount() == 1,
                "fragment_cobalt -> 1 powder_cobalt_tiny, found " + (result.isEmpty() ? "empty" : result.getItem().id + " x" + result.getCount()));
        String template = read(config.resolve("hbmRecipes/_hbmShredder.json"));
        JsonArray exported = JsonParser.parseString(template).getAsJsonObject().getAsJsonArray("recipes");
        long fragments = 0;
        for(var element : exported) {
            JsonObject entry = element.getAsJsonObject();
            if(entry.toString().contains("hbmsntm:fragment_cobalt")) {
                fragments++;
                check(entry.toString().contains("hbmsntm:powder_cobalt_tiny"), "the exported fragment entry yields powder_cobalt_tiny: " + entry);
            }
        }
        check(fragments == 1, "the shredder template has one cobalt fragment entry: " + fragments);
    }

    public static void main(String[] args) {
        config = Path.of(args[0]);
        run("5b. alloy recipe registration and hbmCrucible.json", Goal10ARecipeRegression::crucibleRecipes);
        run("11. shredder", Goal10ARecipeRegression::shredder);
        System.out.println("Goal 10A recipe checks: " + checks + " passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
