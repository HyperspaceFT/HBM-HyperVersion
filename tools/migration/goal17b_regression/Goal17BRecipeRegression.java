package com.hbm.inventory.recipes.loader;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.WireDenseItem;
import net.minecraft.world.item.ItemStack;

import java.io.StringWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;

/** Actual Goal17B assembly registration and recipe I/O against the frozen Goal17B baseline. */
public final class Goal17BRecipeRegression {
    private static int checks;
    private static int scenarios;

    private Goal17BRecipeRegression() { }

    private static void check(boolean condition, String message) {
        checks++;
        if (!condition) throw new AssertionError(message);
    }

    private static JsonObject write(GenericRecipes<GenericRecipe> handler, GenericRecipe recipe) throws Exception {
        StringWriter serialized = new StringWriter();
        try (JsonWriter writer = new JsonWriter(serialized)) {
            writer.beginObject();
            handler.writeRecipe(recipe, writer);
            writer.endObject();
        }
        return JsonParser.parseString(serialized.toString()).getAsJsonObject();
    }

    private static Map<String, JsonObject> catalog(GenericRecipes<GenericRecipe> handler) throws Exception {
        handler.deleteRecipes();
        handler.registerDefaults();
        Map<String, JsonObject> recipes = new LinkedHashMap<>();
        for (GenericRecipe recipe : handler.recipeOrderedList) {
            check(!recipes.containsKey(recipe.name), "unique registered recipe name " + recipe.name);
            recipes.put(recipe.name, write(handler, recipe));
        }
        return recipes;
    }

    private static void fixed(GenericRecipe recipe, int index, net.minecraft.world.item.Item item, int count, Integer meta) {
        AStack actual = recipe.inputItem[index];
        check(actual instanceof ComparableStack, "fixed item input " + recipe.name + "/" + index);
        ComparableStack input = (ComparableStack) actual;
        check(input.item == item && input.stacksize == count, "fixed identity/count " + recipe.name + "/" + index);
        if (meta != null) {
            check(input.meta == meta, "fixed material component " + recipe.name + "/" + index);
            check(input.matchesRecipe(MetaHelper.newStack(item, count, meta), false)
                            && !input.matchesRecipe(MetaHelper.newStack(item, count, meta + 1), false),
                    "actual component matching rejects the wrong material " + recipe.name + "/" + index);
        }
        ItemStack undersized = meta == null
                ? new ItemStack(item, count - 1)
                : MetaHelper.newStack(item, count - 1, meta);
        check(!input.matchesRecipe(undersized, false), "undersized fixed input refuses " + recipe.name + "/" + index);
    }

    private static void tag(GenericRecipe recipe, int index, String id, int count) {
        AStack actual = recipe.inputItem[index];
        check(actual instanceof TagStack, "tagged item input " + recipe.name + "/" + index);
        TagStack input = (TagStack) actual;
        check(input.stacksize == count && input.tag.location().toString().equals(id),
                "material tag/count " + recipe.name + "/" + index);
    }

    private static GenericRecipe registered(AssemblyMachineRecipes handler, String name) {
        GenericRecipe recipe = handler.recipeNameMap.get(name);
        check(recipe != null, "registered row " + name);
        check(handler.recipeOrderedList.stream().filter(row -> row.name.equals(name)).count() == 1,
                "exactly one registered row " + name);
        return recipe;
    }

    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[0]);
        JsonArray exported = new JsonArray();
        String[] addedRows = {"ass.turbofan"};

        for (boolean mode : new boolean[]{false, true}) {
            scenarios++;
            NtmConfig.COMMON.ENABLE_528.set(mode);

            GenericRecipes.clearPools();
            Map<String, JsonObject> baseline = catalog(goal17b.base.AssemblyMachineRecipes.INSTANCE);
            GenericRecipes.clearPools();
            Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);

            ArrayList<String> retainedNames = new ArrayList<>(live.keySet());
            for (String name : addedRows) retainedNames.remove(name);
            Map<String, JsonObject> retained = new LinkedHashMap<>(live);
            for (String name : addedRows) retained.remove(name);
            check(retained.equals(baseline), "all pre-Goal17B recipe writer contents retained, 528=" + mode);
            check(retainedNames.equals(new ArrayList<>(baseline.keySet())),
                    "pre-Goal17B recipe ordering retained, 528=" + mode);
            check(live.size() == baseline.size() + addedRows.length, "exactly one new assembly row, 528=" + mode);

            AssemblyMachineRecipes handler = AssemblyMachineRecipes.INSTANCE;
            GenericRecipe fan = registered(handler, "ass.turbofan");
            check(fan.duration == 300 && fan.power == 100 && !fan.isPooled() && fan.getPools() == null,
                    "ordinary 300 tick, 100 HE/t, non-blueprint turbofan row");
            check(fan.outputItem != null && fan.outputItem.length == 1
                            && fan.outputItem[0] instanceof GenericRecipes.ChanceOutput,
                    "single ordinary machine output");
            ItemStack outputStack = ((GenericRecipes.ChanceOutput) fan.outputItem[0]).stack;
            check(outputStack.getItem() == NtmBlocks.MACHINE_TURBOFAN.asItem() && outputStack.getCount() == 1,
                    "one standard turbofan block output");
            check(fan.inputItem != null && fan.inputItem.length == 6, "exactly six standard inputs");
            fixed(fan, 0, NtmItems.SHELL_TITANIUM.get(), 8, null);
            fixed(fan, 1, NtmItems.PIPE_DURA_STEEL.get(), 4, null);
            tag(fan, 2, "ntm:ingots_plastic", 12);
            fixed(fan, 3, NtmItems.TURBINE_TUNGSTEN.get(), 1, null);
            fixed(fan, 4, NtmItems.WIRE_DENSE.get(), 12, WireDenseItem.Type.GOLD.meta);
            fixed(fan, 5, NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 3, null);
            ComparableStack boardInput = (ComparableStack) fan.inputItem[5];
            check(!boardInput.matchesRecipe(new ItemStack(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 3), false),
                    "analog boards do not satisfy the three BASIC integrated-board inputs");

            GenericRecipe chip = handler.recipeNameMap.get("ass.chip");
            if (mode) {
                check(chip == null, "ordinary microchip assembly remains gated when 528 is enabled");
            } else {
                chip = registered(handler, "ass.chip");
                check(chip.duration == 50 && chip.power == 250, "ordinary microchip recipe timing and power");
                check(chip.inputItem != null && chip.inputItem.length == 3, "ordinary microchip has three inputs");
                fixed(chip, 0, NtmItems.PLATE_POLYMER.get(), 1, null);
                fixed(chip, 1, NtmItems.CIRCUIT_PRINTED_SILICON_WAFER.get(), 1, null);
                fixed(chip, 2, NtmItems.WIRE_GOLD.get(), 1, null);
            }

            JsonObject serialized = live.get("ass.turbofan");
            check(serialized != null, "serialized turbofan row exists");
            handler.deleteRecipes();
            handler.readRecipe(serialized);
            check(write(handler, handler.recipeNameMap.get("ass.turbofan")).equals(serialized),
                    "production recipe writer/reader roundtrip for ass.turbofan, 528=" + mode);
            if (!mode) exported.add(serialized);
        }

        NtmConfig.COMMON.ENABLE_528.set(false);
        JsonObject json = new JsonObject();
        json.add("recipes", exported);
        Files.writeString(output.resolve("goal17b-assembly-recipes.json"), json.toString());
        System.out.println("Goal17B actual assembly registration/writer/reader/component matching: "
                + checks + " assertions; " + scenarios + " 528 scenarios; frozen assembly table retained");
    }
}
