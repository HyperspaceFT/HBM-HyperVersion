package com.hbm.inventory.recipes.loader;

import com.google.gson.*;
import com.google.gson.stream.JsonWriter;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.ItemStack;
import java.io.StringWriter;
import java.nio.file.*;
import java.util.*;

/** Actual loader and writer against the frozen pre-14A table, with fixture registries. */
public class Goal14ARecipeRegression {
    static int checks;
    static void check(boolean value, String message) {
        if(!value) throw new AssertionError(message);
        checks++;
    }
    static JsonObject write(GenericRecipes<GenericRecipe> table, GenericRecipe recipe) throws Exception {
        StringWriter buffer = new StringWriter();
        JsonWriter writer = new JsonWriter(buffer);
        writer.beginObject(); table.writeRecipe(recipe, writer); writer.endObject(); writer.close();
        return JsonParser.parseString(buffer.toString()).getAsJsonObject();
    }
    static Map<String, JsonObject> defaults(GenericRecipes<GenericRecipe> table) throws Exception {
        table.deleteRecipes(); GenericRecipes.clearPools(); table.registerDefaults();
        Map<String, JsonObject> result = new LinkedHashMap<>();
        for(GenericRecipe recipe : table.recipeOrderedList) result.put(recipe.name, write(table, recipe));
        return result;
    }
    public static void main(String[] args) throws Exception {
        Path work = Path.of(args[0]);
        JsonObject diesel = null;
        for(boolean mode : new boolean[]{false, true}) {
            NtmConfig.COMMON.ENABLE_528.set(mode);
            Map<String, JsonObject> base = defaults(goal14a.base.AssemblyMachineRecipes.INSTANCE);
            Map<String, List<String>> oldPools = new LinkedHashMap<>(GenericRecipes.blueprintPools);
            Map<String, JsonObject> live = defaults(AssemblyMachineRecipes.INSTANCE);
            check(live.size() == base.size() + 1, "assembly delta is exactly one in mode " + mode);
            for(String name : base.keySet()) check(base.get(name).equals(live.get(name)), "old recipe unchanged: " + name + " mode " + mode);
            check(oldPools.equals(GenericRecipes.blueprintPools), "old blueprint pools unchanged in mode " + mode);
            List<String> oldOrder = new ArrayList<>(live.keySet()); oldOrder.remove("ass.dieselgen");
            check(oldOrder.equals(new ArrayList<>(base.keySet())), "relative order of every old recipe unchanged");
            JsonObject current = live.get("ass.dieselgen");
            check(current != null, "diesel assembly exists in both 528 modes");
            if(diesel != null) check(diesel.equals(current), "diesel recipe unchanged by 528 mode");
            diesel = current;
            JsonObject expected = JsonParser.parseString("{\"name\":\"ass.dieselgen\",\"inputItem\":[[\"item\",\"hbmsntm:shell_steel\",1,32767],[\"item\",\"hbmsntm:cast_plate\",2,5],[\"item\",\"hbmsntm:coil_copper\",4,32767]],\"outputItem\":[[\"single\",[\"hbmsntm:machine_diesel\"]]],\"duration\":200,\"power\":100}").getAsJsonObject();
            check(current.equals(expected), "independent exact steel shell, copper META5 plates, copper coils and diesel output");
            GenericRecipe r = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.dieselgen");
            check(r.duration == 200 && r.power == 100, "diesel 200 ticks / 100 HE per tick");
            check(r.inputItem.length == 3 && r.inputItem[0].stacksize == 1 && r.inputItem[1].stacksize == 2 && r.inputItem[2].stacksize == 4, "diesel 1 shell / 2 copper cast plates / 4 coils");
            check(!current.has("blueprintpool") && !current.has("named"), "ordinary unnamed unpooled recipe");
            check(current.getAsJsonArray("outputItem").size() == 1 && current.toString().contains("machine_diesel"), "diesel actual writer output");
            // The production loader replaces defaults rather than merging custom files.
            Path config = work.resolve("config-" + mode); Files.createDirectories(config);
            NuclearTechMod.configDir = config.toFile();
            SerializableRecipe.recipeHandlers.clear(); SerializableRecipe.recipeHandlers.add(AssemblyMachineRecipes.INSTANCE);
            SerializableRecipe.recipeSyncHandlers.clear();
            SerializableRecipe.initialize();
            check(AssemblyMachineRecipes.INSTANCE.recipeNameMap.containsKey("ass.dieselgen"), "no custom file uses defaults");
            Path dir = config.resolve("hbmRecipes");
            Path template = dir.resolve("_" + AssemblyMachineRecipes.INSTANCE.getFileName());
            check(Files.isRegularFile(template), "actual loader writes template");
            Files.copy(template, dir.resolve(AssemblyMachineRecipes.INSTANCE.getFileName()));
            SerializableRecipe.initialize();
            check(AssemblyMachineRecipes.INSTANCE.recipeNameMap.size() == live.size(), "full template roundtrip preserves complete catalog");
            check(write(AssemblyMachineRecipes.INSTANCE, AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.dieselgen")).equals(current), "diesel template read/write roundtrip");
            AssemblyMachineRecipes.INSTANCE.deleteRecipes();
            AssemblyMachineRecipes.INSTANCE.readRecipe(base.values().iterator().next());
            AssemblyMachineRecipes.INSTANCE.writeTemplateFile(dir.resolve(AssemblyMachineRecipes.INSTANCE.getFileName()).toFile());
            SerializableRecipe.initialize();
            check(AssemblyMachineRecipes.INSTANCE.recipeNameMap.size() == 1 && !AssemblyMachineRecipes.INSTANCE.recipeNameMap.containsKey("ass.dieselgen"), "custom table containing only an old recipe replaces defaults, diesel absent");
            AssemblyMachineRecipes.INSTANCE.deleteRecipes(); AssemblyMachineRecipes.INSTANCE.readRecipe(current);
            AssemblyMachineRecipes.INSTANCE.writeTemplateFile(dir.resolve(AssemblyMachineRecipes.INSTANCE.getFileName()).toFile());
            SerializableRecipe.initialize();
            check(AssemblyMachineRecipes.INSTANCE.recipeNameMap.size() == 1 && AssemblyMachineRecipes.INSTANCE.recipeNameMap.containsKey("ass.dieselgen"), "custom diesel entry is loadable alone");
        }
        NtmConfig.COMMON.ENABLE_528.set(false);
        defaults(ChemicalPlantRecipes.INSTANCE);
        GenericRecipe gas = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get("chem.gasoline");
        check(gas.duration == 40 && gas.power == 100, "gasoline 40 tick /100 HE");
        check(gas.inputFluid.length == 1 && gas.inputFluid[0].fill == 1000 && gas.outputFluid.length == 1 && gas.outputFluid[0].fill == 800, "gasoline 1000 naphtha ->800 gasoline");
        Files.writeString(work.resolve("ass.dieselgen.recipe.json"), diesel.toString());
        Files.writeString(work.resolve("chem.gasoline.recipe.json"), write(ChemicalPlantRecipes.INSTANCE, gas).toString());
        System.out.println("Goal14A actual recipe loader/writer: " + checks + " checks passed");
    }
}
