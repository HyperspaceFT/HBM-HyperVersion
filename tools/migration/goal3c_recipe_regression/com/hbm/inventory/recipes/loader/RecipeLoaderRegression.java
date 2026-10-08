package com.hbm.inventory.recipes.loader;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.main.NuclearTechMod;
import net.minecraft.tags.ItemTags;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.io.StringWriter;

public class RecipeLoaderRegression {
    private static int assertions;

    private static void check(boolean value, String description) {
        assertions++;
        if (!value) throw new AssertionError(description);
    }

    private static JsonObject onlyShredder(JsonObject template, int duration) {
        JsonArray entries = template.getAsJsonArray("recipes");
        JsonObject selected = null;
        for (var entry : entries) {
            JsonObject recipe = entry.getAsJsonObject();
            if ("ass.shredder".equals(recipe.get("name").getAsString())) {
                selected = recipe.deepCopy();
                break;
            }
        }
        check(selected != null, "generated template contains ass.shredder");
        selected.addProperty("duration", duration);
        var custom = new JsonObject();
        var recipes = new JsonArray();
        recipes.add(selected);
        custom.add("recipes", recipes);
        return custom;
    }

    private static void write(Path path, JsonObject content) throws Exception {
        Files.writeString(path, new Gson().toJson(content), StandardCharsets.UTF_8);
    }

    private static void ingredientRoundTrips() throws Exception {
        var steelTag = ItemTags.create(ResourceLocation.parse("c:plates/steel"));
        StringWriter taggedText = new StringWriter();
        SerializableRecipe.writeAStack(new TagStack(steelTag, 8), new JsonWriter(taggedText));
        var taggedJson = JsonParser.parseString(taggedText.toString()).getAsJsonArray();
        check(taggedJson.size() == 3 && "tag".equals(taggedJson.get(0).getAsString())
                        && "c:plates/steel".equals(taggedJson.get(1).getAsString())
                        && taggedJson.get(2).getAsInt() == 8,
                "tag serializer keeps id and nondefault count");
        var restored = SerializableRecipe.readAStack(taggedJson);
        check(restored instanceof TagStack tag && tag.stacksize == 8
                        && tag.tag.location().equals(steelTag.location()),
                "tag parser restores id and count");
        var one = SerializableRecipe.readAStack(JsonParser.parseString("[\"tag\",\"c:plates/copper\"]").getAsJsonArray());
        check(one instanceof TagStack tag && tag.stacksize == 1,
                "tag parser defaults omitted count to one");

        Item item = new Item("hbmsntm:legacy_probe");
        StringWriter itemText = new StringWriter();
        SerializableRecipe.writeAStack(new ComparableStack(item, 2, 3), new JsonWriter(itemText));
        var itemJson = JsonParser.parseString(itemText.toString()).getAsJsonArray();
        check(itemJson.size() == 4 && "item".equals(itemJson.get(0).getAsString())
                        && itemJson.get(2).getAsInt() == 2 && itemJson.get(3).getAsInt() == 3,
                "existing item/count/meta serializer stays compatible");
        var itemRestored = SerializableRecipe.readAStack(itemJson);
        check(itemRestored instanceof ComparableStack comparable && comparable.item == item
                        && comparable.stacksize == 2 && comparable.meta == 3,
                "existing item/count/meta parser stays compatible");
    }

    public static void main(String[] args) throws Exception {
        var config = Path.of(args[0]);
        var output = Path.of(args[1]);
        NuclearTechMod.configDir = config.toFile();
        ingredientRoundTrips();
        SerializableRecipe.registerAllHandlers();
        long count = SerializableRecipe.recipeHandlers.stream()
                .filter(handler -> handler instanceof AssemblyMachineRecipes).count();
        check(count == 1 && SerializableRecipe.recipeHandlers.contains(AssemblyMachineRecipes.INSTANCE),
                "registration has the singleton assembler exactly once");

        // Other recipe families are peripheral to this isolated loader test.
        SerializableRecipe.recipeHandlers.removeIf(handler -> handler != AssemblyMachineRecipes.INSTANCE);
        var singleton = AssemblyMachineRecipes.INSTANCE;
        var directory = config.resolve("hbmRecipes");
        var underscore = directory.resolve("_hbmAssemblyMachine.json");
        var enabled = directory.resolve("hbmAssemblyMachine.json");

        SerializableRecipe.initialize();
        check(Files.isRegularFile(underscore) && !Files.exists(enabled),
                "missing enabled file creates only underscore template");
        check(singleton.recipeNameMap.containsKey("ass.shredder"),
                "normal defaults load into production singleton");
        var defaultMotor = singleton.recipeNameMap.get("ass.shredder").inputItem[2];
        check(defaultMotor instanceof ComparableStack motor && motor.meta == 32767 && motor.stacksize == 2,
                "registered default motor ingredient retains wildcard metadata and count two");
        int defaultCount = singleton.recipeOrderedList.size();
        check(defaultCount > 1, "default assembler catalog has multiple entries");
        var template = new Gson().fromJson(Files.readString(underscore), JsonObject.class);
        // Goal 11D: the production writer names each fluid of the template by its internal name (the stand-in's "FLUID"),
        // not by its language key ("fluid"), as the original SerializableRecipe.java:424 writes getName().
        java.util.List<String> fluidNames = new java.util.ArrayList<>();
        for (var entry : template.getAsJsonArray("recipes")) {
            JsonObject recipe = entry.getAsJsonObject();
            for (String key : new String[] {"inputFluid", "outputFluid"}) {
                if (recipe.has(key)) for (var fluid : recipe.getAsJsonArray(key)) fluidNames.add(fluid.getAsJsonArray().get(0).getAsString());
            }
        }
        check(!fluidNames.isEmpty() && fluidNames.stream().allMatch("FLUID"::equals),
                "Goal 11D: every fluid of the template is written by its internal name: " + fluidNames);
        var shredderJson = onlyShredder(template, 100);
        Files.writeString(output.resolve("ass-shredder-from-production-writer.json"),
                new Gson().toJson(shredderJson), StandardCharsets.UTF_8);
        check(shredderJson.getAsJsonArray("recipes").get(0).getAsJsonObject().get("duration").getAsInt() == 100,
                "real serializer exports 100-tick shredder recipe");
        var inputs = shredderJson.getAsJsonArray("recipes").get(0).getAsJsonObject().getAsJsonArray("inputItem");
        check(inputs.get(0).getAsJsonArray().get(0).getAsString().equals("tag")
                        && inputs.get(0).getAsJsonArray().get(2).getAsInt() == 8
                        && inputs.get(1).getAsJsonArray().get(0).getAsString().equals("tag")
                        && inputs.get(1).getAsJsonArray().get(2).getAsInt() == 4,
                "generated shredder JSON contains steel and copper tag ingredients");
        check(inputs.get(2).getAsJsonArray().size() == 4
                        && inputs.get(2).getAsJsonArray().get(2).getAsInt() == 2
                        && inputs.get(2).getAsJsonArray().get(3).getAsInt() == 32767,
                "production writer exports motor count and wildcard metadata");

        SerializableRecipe.initialize();
        check(singleton.recipeOrderedList.size() == defaultCount,
                "repeated initialization clears before re-registering defaults");
        check(singleton.recipeNameMap.size() == defaultCount,
                "repeated initialization leaves no duplicate names");

        // An underscore file is not enabled, even if its contents are edited.
        write(underscore, onlyShredder(template, 37));
        SerializableRecipe.initialize();
        check(singleton.recipeOrderedList.size() == defaultCount,
                "edited underscore template does not replace defaults");
        check(singleton.recipeNameMap.get("ass.shredder").duration == 100,
                "underscore changes do not affect active shredder duration");

        // An intentionally empty enabled file must remain empty after loading.
        Files.writeString(enabled, "{\"recipes\":[]}", StandardCharsets.UTF_8);
        byte[] emptyBefore = Files.readAllBytes(enabled);
        SerializableRecipe.initialize();
        check(singleton.recipeOrderedList.isEmpty() && singleton.recipeNameMap.isEmpty(),
                "empty custom table replaces defaults rather than being backfilled");
        check(Arrays.equals(emptyBefore, Files.readAllBytes(enabled)),
                "enabled empty custom file is not rewritten");

        var local = onlyShredder(template, 37);
        write(enabled, local);
        byte[] customBefore = Files.readAllBytes(enabled);
        SerializableRecipe.initialize();
        check(singleton.recipeOrderedList.size() == 1 && singleton.recipeNameMap.containsKey("ass.shredder"),
                "changed enabled custom table is parsed into singleton");
        check(singleton.recipeNameMap.get("ass.shredder").duration == 37,
                "changed custom duration survives production generic parser");
        var customInputs = singleton.recipeNameMap.get("ass.shredder").inputItem;
        check(customInputs.length == 3 && customInputs[0] instanceof TagStack steel && steel.stacksize == 8
                        && customInputs[1] instanceof TagStack copper && copper.stacksize == 4,
                "enabled custom shredder recipe restores both tag ingredient counts");
        check(customInputs[2] instanceof ComparableStack motor && motor.stacksize == 2 && motor.meta == 32767,
                "custom parser restores motor wildcard metadata from writer output");
        check(Arrays.equals(customBefore, Files.readAllBytes(enabled)),
                "enabled custom file is not rewritten");

        var received = onlyShredder(template, 83);
        SerializableRecipe.receiveRecipes("hbmAssemblyMachine.json",
                new Gson().toJson(received).getBytes(StandardCharsets.UTF_8));
        SerializableRecipe.initialize();
        check(singleton.recipeNameMap.get("ass.shredder").duration == 83,
                "simulated received stream wins over enabled local custom file");
        check(Arrays.equals(customBefore, Files.readAllBytes(enabled)),
                "simulated received stream does not rewrite local custom file");
        SerializableRecipe.clearReceivedRecipes();
        check(singleton.recipeNameMap.get("ass.shredder").duration == 37,
                "clearing simulated received stream restores local custom file");

        System.out.println("recipe loader assertions: " + assertions);
    }
}
