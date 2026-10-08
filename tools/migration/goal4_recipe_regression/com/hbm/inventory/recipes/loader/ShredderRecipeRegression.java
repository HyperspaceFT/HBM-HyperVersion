package com.hbm.inventory.recipes.loader;

import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import com.google.gson.JsonArray;
import com.google.gson.JsonParser;

public class ShredderRecipeRegression {
    private static int checks;

    private static void expect(ItemStack input, Item item, int count) {
        ItemStack actual = ShredderRecipes.getShredderResult(input);
        if(actual.getItem() != item || actual.getCount() != count) {
            throw new AssertionError(input.getItem().id + " -> " + (actual.isEmpty() ? "empty" : actual.getItem().id + " x" + actual.getCount())
                    + ", expected " + item.id + " x" + count);
        }
        checks++;
    }

    private static void missing(ItemStack input) {
        if(ShredderRecipes.hasRecipe(input)) throw new AssertionError("unexpected recipe for " + input.getItem().id);
        expect(input, NtmItems.DUST.get(), 1);
    }

    private static void resetAndLoad() {
        SerializableRecipe.initialize();
    }

    public static void main(String[] args) throws Exception {
        Path config = Path.of(args[0]);
        NuclearTechMod.configDir = config.toFile();
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.recipeHandlers.add(new ShredderRecipes());

        resetAndLoad();
        Path directory = config.resolve("hbmRecipes");
        Path template = directory.resolve("_hbmShredder.json");
        Path active = directory.resolve("hbmShredder.json");
        if(!Files.isRegularFile(template) || !Files.readString(template).contains("minecraft:iron_ingot")) {
            throw new AssertionError("default template missing iron ingot");
        }
        checks++;
        JsonArray exported = JsonParser.parseString(Files.readString(template)).getAsJsonObject().getAsJsonArray("recipes");
        JsonArray basics = new JsonArray();
        for(var entry : exported) {
            String id = entry.getAsJsonObject().getAsJsonArray("input").get(0).getAsString();
            if(java.util.Set.of("minecraft:iron_ingot", "minecraft:copper_ingot", "minecraft:iron_ore",
                    "minecraft:deepslate_iron_ore", "minecraft:copper_ore", "minecraft:deepslate_copper_ore").contains(id)) basics.add(entry);
        }
        if(basics.size() != 6) throw new AssertionError("expected six exported basic recipe objects");
        Files.writeString(config.resolve("goal4-shredder-recipes.json"), new com.google.gson.GsonBuilder().setPrettyPrinting().create().toJson(basics) + "\n");
        expect(new ItemStack(Items.IRON_INGOT), NtmItems.POWDER_IRON.get(), 1);
        expect(new ItemStack(Items.COPPER_INGOT), NtmItems.POWDER_COPPER.get(), 1);
        expect(new ItemStack(NtmItems.INGOT_COPPER.get()), NtmItems.POWDER_COPPER.get(), 1);
        expect(new ItemStack(NtmBlocks.ORE_TUNGSTEN.get()), NtmItems.POWDER_TUNGSTEN.get(), 2);
        expect(new ItemStack(NtmBlocks.ORE_TUNGSTEN_DEEPSLATE.get()), NtmItems.POWDER_TUNGSTEN.get(), 2);
        expect(new ItemStack(Blocks.IRON_ORE), NtmItems.POWDER_IRON.get(), 2);
        expect(new ItemStack(Blocks.DEEPSLATE_IRON_ORE), NtmItems.POWDER_IRON.get(), 2);
        expect(new ItemStack(Blocks.COPPER_ORE), NtmItems.POWDER_COPPER.get(), 2);
        expect(new ItemStack(Blocks.DEEPSLATE_COPPER_ORE), NtmItems.POWDER_COPPER.get(), 2);
        expect(new ItemStack(NtmItems.PLATE_IRON.get()), NtmItems.POWDER_IRON.get(), 1);
        expect(new ItemStack(NtmItems.PLATE_COPPER.get()), NtmItems.POWDER_COPPER.get(), 1);
        expect(new ItemStack(NtmItems.PLATE_STEEL.get()), NtmItems.POWDER_STEEL.get(), 1);
        expect(new ItemStack(NtmItems.INGOT_STEEL.get()), NtmItems.POWDER_STEEL.get(), 1);
        missing(new ItemStack(Items.RAW_IRON));
        missing(new ItemStack(Items.RAW_COPPER));
        if(!ShredderRecipes.getShredderResult(ItemStack.EMPTY).isEmpty()) throw new AssertionError("empty input produced dust");
        checks++;

        // The real loader's exported default table must load back without changing these identities.
        Files.copy(template, active);
        resetAndLoad();
        expect(new ItemStack(Items.IRON_INGOT), NtmItems.POWDER_IRON.get(), 1);
        expect(new ItemStack(Blocks.COPPER_ORE), NtmItems.POWDER_COPPER.get(), 2);

        // The active file replaces defaults; post registration restores only material entries.
        Files.writeString(active, "{\"recipes\":[]}");
        resetAndLoad();
        if(!Files.readString(active).equals("{\"recipes\":[]}")) throw new AssertionError("active empty file overwritten");
        checks++;
        expect(new ItemStack(Items.IRON_INGOT), NtmItems.POWDER_IRON.get(), 1);
        expect(new ItemStack(Items.COPPER_INGOT), NtmItems.POWDER_COPPER.get(), 1);
        missing(new ItemStack(Blocks.IRON_ORE));
        missing(new ItemStack(Blocks.COPPER_ORE));
        missing(new ItemStack(Blocks.DEEPSLATE_IRON_ORE));
        missing(new ItemStack(Blocks.DEEPSLATE_COPPER_ORE));
        expect(new ItemStack(NtmBlocks.ORE_TUNGSTEN.get()), NtmItems.POWDER_TUNGSTEN.get(), 2);
        int postSize = ShredderRecipes.getJeiRecipes().size();
        new ShredderRecipes().registerPost();
        if(ShredderRecipes.getJeiRecipes().size() != postSize) throw new AssertionError("post duplicates entries");
        checks++;

        Files.writeString(active, "{\"recipes\":[{\"input\":[\"minecraft:iron_ingot\",1,32767],\"output\":[\"hbmsntm:powder_copper\",3]}]}");
        resetAndLoad();
        expect(new ItemStack(Items.IRON_INGOT), NtmItems.POWDER_COPPER.get(), 3);
        expect(new ItemStack(Items.COPPER_INGOT), NtmItems.POWDER_COPPER.get(), 1);
        if(ShredderRecipes.getJeiRecipes().stream().noneMatch(r -> r.input.getItem() == Items.IRON_INGOT
                && r.output.getItem() == NtmItems.POWDER_COPPER.get() && r.output.getCount() == 3)) {
            throw new AssertionError("JEI table does not reflect explicit override");
        }
        checks++;

        String activeBeforeSync = Files.readString(active);
        SerializableRecipe.receiveRecipes("hbmShredder.json", "{\"recipes\":[{\"input\":[\"minecraft:iron_ingot\"],\"output\":[\"hbmsntm:powder_steel\",2]}]}".getBytes(StandardCharsets.UTF_8));
        resetAndLoad();
        expect(new ItemStack(Items.IRON_INGOT), NtmItems.POWDER_STEEL.get(), 2);
        if(!Files.readString(active).equals(activeBeforeSync)) throw new AssertionError("received stream changed active file");
        checks++;
        SerializableRecipe.clearReceivedRecipes();
        expect(new ItemStack(Items.IRON_INGOT), NtmItems.POWDER_COPPER.get(), 3);
        if(!Files.readString(active).equals(activeBeforeSync)) throw new AssertionError("active override file overwritten");
        checks++;

        Files.writeString(active, "{\"recipes\":[{\"input\":[\"minecraft:iron_ingot\"],\"output\":[\"minecraft:air\",0]}]}");
        resetAndLoad();
        if(!ShredderRecipes.getShredderResult(new ItemStack(Items.IRON_INGOT)).isEmpty()) {
            throw new AssertionError("explicit empty output was replaced");
        }
        checks++;

        // Goal 11D: the production writer names a fluid by its internal name (the stand-in's "FLUID"), not by its language
        // key ("fluid"), as the original SerializableRecipe.java:424 writes getName().
        java.io.StringWriter fluidJson = new java.io.StringWriter();
        com.google.gson.stream.JsonWriter fluidWriter = new com.google.gson.stream.JsonWriter(fluidJson);
        SerializableRecipe.writeFluidStack(new com.hbm.inventory.FluidStack(com.hbm.inventory.fluid.Fluids.NONE, 1_000), fluidWriter);
        fluidWriter.close();
        if(!fluidJson.toString().equals("[\"FLUID\",1000]")) throw new AssertionError("Goal 11D: writeFluidStack writes the internal name: " + fluidJson);
        checks++;
        System.out.println("PASS " + checks + " production recipe assertions");
    }
}
