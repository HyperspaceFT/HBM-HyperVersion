package com.hbm.inventory.recipes.loader;

import com.google.gson.*;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.*;
import com.hbm.inventory.RecipesCommon.*;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Complete real assembly writer/parser over declared registry/tag/component stand-ins. */
public final class Goal16BAcquisitionRegression {
    static int checks;
    static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }
    static JsonObject write(GenericRecipes<GenericRecipe> handler, GenericRecipe recipe) throws Exception {
        StringWriter text = new StringWriter();
        try(JsonWriter writer = new JsonWriter(text)) {
            writer.beginObject(); handler.writeRecipe(recipe, writer); writer.endObject();
        }
        return JsonParser.parseString(text.toString()).getAsJsonObject();
    }
    static Map<String, JsonObject> catalog(GenericRecipes<GenericRecipe> handler) throws Exception {
        GenericRecipes.clearPools(); handler.deleteRecipes(); handler.registerDefaults();
        Map<String, JsonObject> rows = new LinkedHashMap<>();
        for(GenericRecipe recipe : handler.recipeOrderedList) {
            check(rows.put(recipe.name, write(handler, recipe)) == null, "distinct default name " + recipe.name);
        }
        return rows;
    }
    static String pools() {
        return new TreeMap<>(GenericRecipes.blueprintPools).toString();
    }
    static void item(AStack ingredient, Item expected, int count) {
        check(ingredient instanceof ComparableStack, "ordinary precise item ingredient");
        ComparableStack actual = (ComparableStack)ingredient;
        check(actual.item == expected && actual.stacksize == count && actual.meta == MetaHelper.WILDCARD_VALUE,
                "exact item identity, count and wildcard META");
        check(actual.matchesRecipe(new ItemStack(expected, count), false), "exact ordinary stack matches");
        if(count > 1) check(!actual.matchesRecipe(new ItemStack(expected, count - 1), false), "undersized ordinary stack rejects");
        check(!actual.matchesRecipe(new ItemStack(NtmItems.INGOT_DURA_STEEL.get(), count), false),
                "different item rejects");
    }
    static void tag(AStack ingredient, String identity, Item[] members, int count) {
        check(ingredient instanceof TagStack, "ordinary tag ingredient");
        TagStack actual = (TagStack)ingredient;
        check(actual.tag.location().toString().equals(identity) && actual.stacksize == count, "exact tag and count");
        RecipesCommon.TAG_MEMBERS.put(identity, List.of(members));
        for(Item member : members) {
            if(!member.tags.contains(identity)) member.tags.add(identity);
            check(actual.matchesRecipe(new ItemStack(member, count), false), "declared tag member matches");
            check(!actual.matchesRecipe(new ItemStack(member, count - 1), false), "undersized tag member rejects");
        }
        check(!actual.matchesRecipe(new ItemStack(NtmItems.MOTOR.get(), count), false), "unrelated item rejects tag");
    }
    static void contract(GenericRecipe recipe, int duration, int inputs, Item output) {
        check(recipe != null && recipe.duration == duration && recipe.power == 100 && !recipe.isPooled(),
                "ordinary ungated duration/power contract");
        check(!recipe.customLocalization && recipe.inputItem.length == inputs && recipe.outputItem.length == 1
                && recipe.inputFluid == null && recipe.outputFluid == null, "no extra localization, inputs, fluids or outputs");
        ItemStack stack = ((GenericRecipes.ChanceOutput)recipe.outputItem[0]).stack;
        check(stack.getItem() == output && stack.getCount() == 1 && !stack.has(NtmDataComponents.META.get()),
                "one plain output with no introduced META component");
    }
    public static void main(String[] args) throws Exception {
        Path out = Path.of(args[0]);
        NuclearTechMod.configDir = out.resolve("scratch-config").toFile();
        NuclearTechMod.configDir.mkdirs();
        check(NtmItems.CENTRIFUGE_ELEMENT.get().id.equals("hbmsntm:centrifuge_element"), "actual registration component id");
        check(NtmBlocks.MACHINE_CENTRIFUGE.asItem().id.equals("hbmsntm:machine_centrifuge"), "existing machine id");
        JsonObject reference = null;
        for(boolean mode : new boolean[]{false, true}) {
            NtmConfig.COMMON.ENABLE_528.set(mode);
            Map<String, JsonObject> base = catalog(goal16b.base.AssemblyMachineRecipes.INSTANCE);
            String oldPools = pools();
            Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);
            String newPools = pools();
            Map<String, JsonObject> retained = new LinkedHashMap<>(live);
            retained.remove("ass.centrifugetower"); retained.remove("ass.centrifuge");
            check(live.size() == base.size() + 2 && retained.equals(base), "frozen default table unchanged plus exactly2,528=" + mode);
            check(new ArrayList<>(retained.keySet()).equals(new ArrayList<>(base.keySet())), "old recipe order unchanged");
            check(oldPools.equals(newPools), "old blueprint pools unchanged");
            GenericRecipe tower = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.centrifugetower");
            contract(tower, 100, 3, NtmItems.CENTRIFUGE_ELEMENT.get());
            item(tower.inputItem[0], NtmItems.PLATE_DURA_STEEL.get(), 4);
            item(tower.inputItem[1], NtmItems.PLATE_TITANIUM.get(), 4);
            item(tower.inputItem[2], NtmItems.MOTOR.get(), 1);
            GenericRecipe machine = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.centrifuge");
            contract(machine, 200, 5, NtmBlocks.MACHINE_CENTRIFUGE.asItem());
            item(machine.inputItem[0], NtmItems.CENTRIFUGE_ELEMENT.get(), 1);
            tag(machine.inputItem[1], "ntm:ingots_plastic", new Item[]{NtmItems.INGOT_POLYMER.get(), NtmItems.INGOT_BAKELITE.get()}, 4);
            tag(machine.inputItem[2], "c:plates/steel", new Item[]{NtmItems.PLATE_STEEL.get()}, 8);
            tag(machine.inputItem[3], "c:plates/copper", new Item[]{NtmItems.PLATE_COPPER.get()}, 4);
            item(machine.inputItem[4], NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1);
            JsonArray rows = new JsonArray(); rows.add(live.get("ass.centrifugetower")); rows.add(live.get("ass.centrifuge"));
            JsonObject merge = new JsonObject(); merge.add("recipes", rows);
            Files.writeString(out.resolve("goal16b-assembly-recipes-528-" + mode + ".json"), merge.toString());
            if(reference == null) reference = merge;
            else check(reference.equals(merge), "real writer merge reference identical both528");
            // The common loader clears the table before custom loading. A two-row file is an authoritative replacement.
            AssemblyMachineRecipes.INSTANCE.deleteRecipes();
            AssemblyMachineRecipes.INSTANCE.readRecipeStream(new StringReader(merge.toString()));
            check(AssemblyMachineRecipes.INSTANCE.recipeOrderedList.size() == 2
                    && !AssemblyMachineRecipes.INSTANCE.recipeNameMap.containsKey("ass.coker"), "custom whole-table replacement retained");
            for(GenericRecipe recipe : AssemblyMachineRecipes.INSTANCE.recipeOrderedList) {
                check(write(AssemblyMachineRecipes.INSTANCE, recipe).equals(live.get(recipe.name)), "real writer/readback row preserved");
            }
            AssemblyMachineRecipes.INSTANCE.deleteRecipes();
            AssemblyMachineRecipes.INSTANCE.readRecipeStream(new StringReader("{\"recipes\":[]}"));
            check(AssemblyMachineRecipes.INSTANCE.recipeOrderedList.isEmpty(), "empty custom assembly disables all rows");
        }
        NtmConfig.COMMON.ENABLE_528.set(false);
        System.out.println("Goal16B acquisition: " + checks + " assertions passed; actual assembly defaults/writer/parser; registry/tag services isolated");
    }
}
