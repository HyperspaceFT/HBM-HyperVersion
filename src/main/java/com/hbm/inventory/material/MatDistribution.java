package com.hbm.inventory.material;

import static com.hbm.inventory.material.Mats.*;
import static com.hbm.inventory.material.MaterialShapes.*;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.items.ItemEnums.CasingType;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ItemLike;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map.Entry;

/**
 * Fixed crucible smelting entries (hbmCrucibleSmelting.json): recycling for certain objects and ores with byproducts.
 * Upstream registers ores and stone through ore dictionary names; NEO has no such tags, so its defaults list the
 * NEO items instead, and tag entries ("tag" inputs) only come from the config file.
 */
public class MatDistribution extends SerializableRecipe {

    @Override
    public void registerDefaults() {
        //vanilla crap
        // Upstream registerOre("stone") / registerOre("cobblestone") (MatDistribution.java:41-42); NEO lists the two items.
        registerEntry(Items.STONE, MAT_STONE, BLOCK.q(1));
        registerEntry(Items.COBBLESTONE, MAT_STONE, BLOCK.q(1));
        registerEntry(Items.OBSIDIAN, MAT_OBSIDIAN, BLOCK.q(1));
        registerEntry(Items.RAIL, MAT_IRON, INGOT.q(6, 16));
        registerEntry(Items.POWERED_RAIL, MAT_GOLD, INGOT.q(6, 6), MAT_REDSTONE, DUST.q(1, 6));
        registerEntry(Items.DETECTOR_RAIL, MAT_IRON, INGOT.q(6, 6), MAT_REDSTONE, DUST.q(1, 6));
        registerEntry(Items.MINECART, MAT_IRON, INGOT.q(5));

        //castables (MatDistribution.java:50-58)
        // pipes_steel (:59) is not registered: the item is deprecated upstream.
        registerEntry(NtmItems.BLADE_TITANIUM,              MAT_TITANIUM,       INGOT.q(3));
        registerEntry(NtmItems.BLADE_TUNGSTEN,              MAT_TUNGSTEN,       INGOT.q(3));
        registerEntry(NtmItems.BLADES_STEEL,                MAT_STEEL,          INGOT.q(4));
        registerEntry(NtmItems.BLADES_TITANIUM,             MAT_TITANIUM,       INGOT.q(4));
        registerEntry(NtmItems.STAMP_STONE_FLAT,            MAT_STONE,          INGOT.q(3));
        registerEntry(NtmItems.STAMP_IRON_FLAT,             MAT_IRON,           INGOT.q(3));
        registerEntry(NtmItems.STAMP_STEEL_FLAT,            MAT_STEEL,          INGOT.q(3));
        registerEntry(NtmItems.STAMP_TITANIUM_FLAT,         MAT_TITANIUM,       INGOT.q(3));
        registerEntry(NtmItems.STAMP_OBSIDIAN_FLAT,         MAT_OBSIDIAN,       INGOT.q(3));

        // MatDistribution.java:61-66; the second minecart row (:65) repeats :47 and is registered once.
        registerEntry(new ComparableStack(NtmItems.CASING.get(), 1, CasingType.SMALL),          MAT_GUNMETAL,       PLATE.q(1, 4));
        registerEntry(new ComparableStack(NtmItems.CASING.get(), 1, CasingType.SMALL_STEEL),    MAT_WEAPONSTEEL,    PLATE.q(1, 4));
        registerEntry(new ComparableStack(NtmItems.CASING.get(), 1, CasingType.LARGE),          MAT_GUNMETAL,       PLATE.q(1, 2));
        registerEntry(new ComparableStack(NtmItems.CASING.get(), 1, CasingType.LARGE_STEEL),    MAT_WEAPONSTEEL,    PLATE.q(1, 2));
        registerEntry(NtmItems.CHUNK_CRYOLITE, MAT_ALUMINIUM, INGOT.q(1), MAT_SODIUM, INGOT.q(1));

        //actual ores (MatDistribution.java:68-86), one row per NEO ore block of the upstream ore dictionary name.
        // Upstream skips iron, titanium, tungsten and aluminium ores when GT6 is loaded; NEO has no GT6 branch.
        for(ItemLike ore : ores(Items.IRON_ORE, Items.DEEPSLATE_IRON_ORE)) registerEntry(ore, MAT_IRON, INGOT.q(2), MAT_TITANIUM, NUGGET.q(3), MAT_STONE, QUART.q(1));
        for(ItemLike ore : ores(NtmBlocks.ORE_TITANIUM, NtmBlocks.ORE_TITANIUM_DEEPSLATE)) registerEntry(ore, MAT_TITANIUM, INGOT.q(2), MAT_IRON, NUGGET.q(3), MAT_STONE, QUART.q(1));
        for(ItemLike ore : ores(NtmBlocks.ORE_TUNGSTEN, NtmBlocks.ORE_TUNGSTEN_DEEPSLATE)) registerEntry(ore, MAT_TUNGSTEN, INGOT.q(2), MAT_STONE, QUART.q(1));
        for(ItemLike ore : ores(NtmBlocks.ORE_ALUMINIUM, NtmBlocks.ORE_ALUMINIUM_DEEPSLATE)) registerEntry(ore, MAT_ALUMINIUM, INGOT.q(2), MAT_SODIUM, NUGGET.q(3), MAT_STONE, QUART.q(1));

        for(ItemLike ore : ores(Items.COAL_ORE, Items.DEEPSLATE_COAL_ORE)) registerEntry(ore, MAT_CARBON, GEM.q(3), MAT_STONE, QUART.q(1));
        for(ItemLike ore : ores(Items.GOLD_ORE, Items.DEEPSLATE_GOLD_ORE)) registerEntry(ore, MAT_GOLD, INGOT.q(2), MAT_LEAD, NUGGET.q(3), MAT_STONE, QUART.q(1));
        for(ItemLike ore : ores(NtmBlocks.ORE_URANIUM, NtmBlocks.ORE_URANIUM_DEEPSLATE, NtmBlocks.ORE_URANIUM_SCORCHED, NtmBlocks.ORE_GNEISS_URANIUM,
                NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED, NtmBlocks.ORE_NETHER_URANIUM, NtmBlocks.ORE_NETHER_URANIUM_SCORCHED)) {
            registerEntry(ore, MAT_URANIUM, INGOT.q(2), MAT_LEAD, NUGGET.q(3), MAT_STONE, QUART.q(1));
        }
        for(ItemLike ore : ores(NtmBlocks.ORE_THORIUM, NtmBlocks.ORE_THORIUM_DEEPSLATE)) registerEntry(ore, MAT_THORIUM, INGOT.q(2), MAT_URANIUM, NUGGET.q(3), MAT_STONE, QUART.q(1));
        // NEO has no ore_copper of its own; Minecraft's copper ores carry upstream's oreCopper row.
        for(ItemLike ore : ores(Items.COPPER_ORE, Items.DEEPSLATE_COPPER_ORE)) registerEntry(ore, MAT_COPPER, INGOT.q(2), MAT_STONE, QUART.q(1));
        for(ItemLike ore : ores(NtmBlocks.ORE_LEAD, NtmBlocks.ORE_LEAD_DEEPSLATE)) registerEntry(ore, MAT_LEAD, INGOT.q(2), MAT_GOLD, NUGGET.q(1), MAT_STONE, QUART.q(1));
        for(ItemLike ore : ores(NtmBlocks.ORE_BERYLLIUM, NtmBlocks.ORE_BERYLLIUM_DEEPSLATE)) registerEntry(ore, MAT_BERYLLIUM, INGOT.q(2), MAT_STONE, QUART.q(1));
        for(ItemLike ore : ores(NtmBlocks.ORE_COBALT, NtmBlocks.ORE_COBALT_DEEPSLATE)) registerEntry(ore, MAT_COBALT, INGOT.q(1), MAT_STONE, QUART.q(1));
        for(ItemLike ore : ores(Items.REDSTONE_ORE, Items.DEEPSLATE_REDSTONE_ORE)) registerEntry(ore, MAT_REDSTONE, INGOT.q(4), MAT_STONE, QUART.q(1));

        registerEntry(NtmBlocks.RESOURCE_HEMATITE, MAT_HEMATITE, INGOT.q(1));
        registerEntry(NtmBlocks.RESOURCE_MALACHITE, MAT_MALACHITE, INGOT.q(6));

        // MatDistribution.java:88-94
        registerEntry(NtmBlocks.RESOURCE_LIMESTONE, MAT_FLUX, DUST.q(10));
        registerEntry(NtmItems.POWDER_FLUX, MAT_FLUX, DUST.q(1));
        registerEntry(Items.CHARCOAL, MAT_CARBON, NUGGET.q(3));

        registerEntry(NtmItems.POWDER_ASH_WOOD, MAT_CARBON, NUGGET.q(1));
        registerEntry(NtmItems.POWDER_ASH_COAL, MAT_CARBON, NUGGET.q(2));
        registerEntry(NtmItems.POWDER_ASH_MISC, MAT_CARBON, NUGGET.q(1));
    }

    private static ItemLike[] ores(ItemLike... ores) {
        return ores;
    }

    /** Item keys use meta 0 like upstream's ComparableStack(Item), which is what plain NEO stacks report. */
    public static void registerEntry(Object key, Object... matDef) {
        ComparableStack comp = null;

        if(key instanceof ComparableStack stack) comp = stack;
        else if(key instanceof ItemStack stack) comp = new ComparableStack(stack);
        else if(key instanceof ItemLike item) comp = new ComparableStack(item.asItem(), 1, 0);

        if(comp == null) return;
        if(matDef.length % 2 == 1) return;

        List<MaterialStack> stacks = new ArrayList<>();

        for(int i = 0; i < matDef.length; i += 2) {
            stacks.add(new MaterialStack((NTMMaterial) matDef[i], (int) matDef[i + 1]));
        }

        if(stacks.isEmpty()) return;

        materialEntries.put(comp.makeSingular(), stacks);
    }

    /** Registers materials for every item in a tag, keyed by the tag ID (upstream registerOre with an ore dictionary name). */
    public static void registerOre(String key, Object... matDef) {
        if(matDef.length % 2 == 1) return;

        List<MaterialStack> stacks = new ArrayList<>();

        for(int i = 0; i < matDef.length; i += 2) {
            stacks.add(new MaterialStack((NTMMaterial) matDef[i], (int) matDef[i + 1]));
        }

        if(stacks.isEmpty()) return;

        materialOreEntries.put(key, stacks);
    }

    @Override
    public String getFileName() {
        return "hbmCrucibleSmelting.json";
    }

    @Override
    public Object getRecipeObject() {
        List<Object> entries = new ArrayList<>();
        entries.addAll(Mats.materialEntries.entrySet());
        entries.addAll(Mats.materialOreEntries.entrySet());
        return entries;
    }

    @Override
    public void readRecipe(JsonElement recipe) {
        JsonObject obj = (JsonObject) recipe;
        AStack input = readAStack(obj.get("input").getAsJsonArray());
        List<MaterialStack> materials = new ArrayList<>();
        JsonArray output = obj.get("output").getAsJsonArray();
        for(int i = 0; i < output.size(); i++) {
            JsonArray entry = output.get(i).getAsJsonArray();
            String mat = entry.get(0).getAsString();
            int amount = entry.get(1).getAsInt();
            NTMMaterial material = Mats.matByName.get(mat);
            // Upstream stores a null material here and fails later in the crucible.
            if(material == null) {
                NuclearTechMod.LOGGER.warn("Skipping unknown material {} in {}", mat, this.getFileName());
                continue;
            }
            materials.add(new MaterialStack(material, amount));
        }

        if(input instanceof ComparableStack comp) {
            // readAStack turns an unknown item into air or the "nothing" placeholder.
            if(comp.item == null || comp.item == Items.AIR || comp.item == NtmItems.NOTHING.get()) {
                throw new IllegalArgumentException("Invalid crucible smelting input " + obj.get("input"));
            }
            if(materials.isEmpty()) {
                NuclearTechMod.LOGGER.warn("Skipping crucible smelting entry {} in {}: no known materials", obj.get("input"), this.getFileName());
                return;
            }
            Mats.materialEntries.put(comp.makeSingular(), materials);
        } else if(input instanceof TagStack tag) {
            if(materials.isEmpty()) {
                NuclearTechMod.LOGGER.warn("Skipping crucible smelting entry {} in {}: no known materials", obj.get("input"), this.getFileName());
                return;
            }
            Mats.materialOreEntries.put(tag.tag.location().toString(), materials);
        }
    }

    @Override
    public void writeRecipe(Object recipe, JsonWriter writer) throws IOException {
        AStack toSmelt = null;
        Entry<?, ?> entry = (Entry<?, ?>) recipe;
        @SuppressWarnings("unchecked")
        List<MaterialStack> materials = (List<MaterialStack>) entry.getValue();
        if(entry.getKey() instanceof String tag) {
            toSmelt = new TagStack(ItemTags.create(ResourceLocation.parse(tag)));
        } else if(entry.getKey() instanceof ComparableStack comp) {
            toSmelt = comp;
        }
        if(toSmelt == null) return;
        writer.name("input");
        writeAStack(toSmelt, writer);
        writer.name("output").beginArray();
        writer.setIndent("");
        for(MaterialStack stack : materials) {
            writer.beginArray();
            writer.value(stack.material.names[0]).value(stack.amount);
            writer.endArray();
        }
        writer.endArray();
        writer.setIndent("  ");
    }

    @Override
    public void deleteRecipes() {
        Mats.materialEntries.clear();
        Mats.materialOreEntries.clear();
    }

    @Override
    public String getComment() {
        return "Defines a set of items that can be smelted. Smelting of the built-in item shapes (prefix + material) comes from the mod's item registry and cannot be "
                + "changed here. This config only changes fixed items (like recycling for certain metallic objects), ores (with variable byproducts) and item tags. "
                + "Amounts used are in quanta (1 quantum is 1/72 of an ingot or 1/8 of a nugget). Material names are the material suffixes, case-sensitive.";
    }
}
