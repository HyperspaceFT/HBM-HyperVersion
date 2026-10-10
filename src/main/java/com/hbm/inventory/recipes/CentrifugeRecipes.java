package com.hbm.inventory.recipes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.util.TagsUtil;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.TagParser;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;

import java.io.IOException;
import java.io.Reader;
import java.io.StringWriter;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class CentrifugeRecipes extends SerializableRecipe {
    public static final int MAX_SYNC_RECIPES = 4096;
    public static final int MAX_SYNC_BYTES = 256 * 1024;
    private static final List<CentrifugeRecipe> RECIPES = new ArrayList<>();
    private final List<CentrifugeRecipe> table;

    public CentrifugeRecipes() { this(RECIPES); }
    private CentrifugeRecipes(List<CentrifugeRecipe> table) { this.table = table; }

    public static class CentrifugeRecipe {
        public final ItemStack input;
        public final ItemStack[] outputs;

        public CentrifugeRecipe(ItemStack input, ItemStack[] outputs) {
            if(input == null || input.isEmpty() || input.getCount() <= 0) throw invalid("invalid input");
            this.input = input.copyWithCount(1);
            encodeItem(this.input);
            if(outputs == null || outputs.length < 1 || outputs.length > 4) throw invalid("outputs must have 1..4 slots");
            this.outputs = copyOutputs(outputs);
            boolean any = false;
            for(ItemStack output : this.outputs) {
                if(!output.isEmpty()) { encodeItem(output); any = true; }
            }
            if(!any) throw invalid("recipe needs a nonempty output");
        }

        /** Legacy generic inputs ignore unrelated components; custom-data inputs are exact constraints. */
        public boolean matches(ItemStack stack) {
            if(stack == null || stack.isEmpty() || input.getItem() != stack.getItem()) return false;
            int meta = MetaHelper.getMeta(input);
            // Historical candidate META32767 may match distinct concrete-META rows; ordered lookup keeps the first.
            if(meta != MetaHelper.WILDCARD_VALUE && MetaHelper.getMeta(stack) != MetaHelper.WILDCARD_VALUE && meta != MetaHelper.getMeta(stack)) return false;
            if(!TagsUtil.hasCustomData(input)) return true;
            ItemStack expected = input.copy(), actual = stack.copy();
            if(meta == MetaHelper.WILDCARD_VALUE) {
                expected.remove(NtmDataComponents.META.get());
                actual.remove(NtmDataComponents.META.get());
            }
            return ItemStack.isSameItemSameComponents(expected, actual);
        }

        public boolean sameRecipe(CentrifugeRecipe other) {
            if(other == null || !ItemStack.isSameItemSameComponents(input, other.input) || outputs.length != other.outputs.length) return false;
            for(int i = 0; i < outputs.length; i++) {
                if(outputs[i].isEmpty() && other.outputs[i].isEmpty()) continue;
                if(outputs[i].getCount() != other.outputs[i].getCount() || !ItemStack.isSameItemSameComponents(outputs[i], other.outputs[i])) return false;
            }
            return true;
        }
    }

    public static List<CentrifugeRecipe> getJeiRecipes() { return copyRecipes(RECIPES); }
    public static List<CentrifugeRecipe> getDefaultRecipes() {
        List<CentrifugeRecipe> defaults = new ArrayList<>();
        new CentrifugeRecipes(defaults).registerDefaults();
        return copyRecipes(defaults);
    }
    public static List<CentrifugeRecipe> copyRecipes(List<CentrifugeRecipe> source) {
        List<CentrifugeRecipe> result = new ArrayList<>(source.size());
        for(CentrifugeRecipe recipe : source) result.add(new CentrifugeRecipe(recipe.input, recipe.outputs));
        return result;
    }
    public static boolean hasRecipe(ItemStack stack) { return hasRecipe(RECIPES, stack); }
    public static boolean hasRecipe(List<CentrifugeRecipe> source, ItemStack stack) {
        for(CentrifugeRecipe recipe : source) if(recipe.matches(stack)) return true;
        return false;
    }
    public static ItemStack[] getOutput(ItemStack stack) {
        for(CentrifugeRecipe recipe : RECIPES) if(recipe.matches(stack)) return copyOutputs(recipe.outputs);
        return new ItemStack[0];
    }
    public static void setRecipe(ItemStack input, ItemStack... outputs) { new CentrifugeRecipes().addRecipe(input, outputs); }
    private void addRecipe(ItemStack input, ItemStack... outputs) { add(new CentrifugeRecipe(input, outputs)); }
    public static void setRecipe(Block input, ItemStack... outputs) {
        setRecipe(MetaHelper.newStack(input, 1, MetaHelper.WILDCARD_VALUE), outputs);
    }
    private void add(CentrifugeRecipe row) {
        if(table.size() >= MAX_SYNC_RECIPES) throw invalid("too many recipes");
        for(CentrifugeRecipe old : table) {
            if(old.input.getItem() != row.input.getItem()) continue;
            int a = MetaHelper.getMeta(old.input), b = MetaHelper.getMeta(row.input);
            // Reject overlap for ordinary concrete candidates; preserve the historical wildcard-candidate exception.
            if(a != b && a != MetaHelper.WILDCARD_VALUE && b != MetaHelper.WILDCARD_VALUE) continue;
            if(!TagsUtil.hasCustomData(old.input) || !TagsUtil.hasCustomData(row.input)) throw invalid("overlapping input " + BuiltInRegistries.ITEM.getKey(row.input.getItem()));
            ItemStack left = old.input.copy(), right = row.input.copy();
            if(a == MetaHelper.WILDCARD_VALUE || b == MetaHelper.WILDCARD_VALUE) {
                left.remove(NtmDataComponents.META.get()); right.remove(NtmDataComponents.META.get());
            }
            if(ItemStack.isSameItemSameComponents(left, right)) throw invalid("duplicate/overlapping exact input");
        }
        table.add(row);
    }
    private static ItemStack stack(ItemLike item, int count) { return new ItemStack(item, count); }
    private static ItemStack[] copyOutputs(ItemStack[] outputs) {
        ItemStack[] copy = new ItemStack[outputs.length];
        for(int i = 0; i < copy.length; i++) {
            if(outputs[i] == null) throw invalid("null output slot");
            copy[i] = outputs[i].copy();
        }
        return copy;
    }

    private static final class Defaults {
        private final CentrifugeRecipes owner;
        private Defaults(CentrifugeRecipes owner) { this.owner = owner; }
        private void setRecipe(ItemStack input, ItemStack... outputs) { owner.addRecipe(MetaHelper.newStack(input.getItem(), 1, MetaHelper.getMeta(input)), outputs); }
        private void setRecipe(Block input, ItemStack... outputs) { owner.addRecipe(MetaHelper.newStack(input, 1, MetaHelper.WILDCARD_VALUE), outputs); }
    private void registerOreRecipes() {
        setRecipe(Blocks.COAL_ORE, stack(NtmItems.POWDER_COAL.get(), 2), stack(NtmItems.POWDER_COAL.get(), 2), stack(NtmItems.POWDER_COAL.get(), 2), stack(Blocks.STONE, 1));
        setRecipe(Blocks.DEEPSLATE_COAL_ORE, stack(NtmItems.POWDER_COAL.get(), 2), stack(NtmItems.POWDER_COAL.get(), 2), stack(NtmItems.POWDER_COAL.get(), 2), stack(Blocks.STONE, 1));
        setRecipe(Blocks.IRON_ORE, stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.DEEPSLATE_IRON_ORE, stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.GOLD_ORE, stack(NtmItems.POWDER_GOLD.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.DEEPSLATE_GOLD_ORE, stack(NtmItems.POWDER_GOLD.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.DIAMOND_ORE, stack(NtmItems.POWDER_DIAMOND.get(), 1), stack(NtmItems.POWDER_DIAMOND.get(), 1), stack(NtmItems.POWDER_DIAMOND.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.DEEPSLATE_DIAMOND_ORE, stack(NtmItems.POWDER_DIAMOND.get(), 1), stack(NtmItems.POWDER_DIAMOND.get(), 1), stack(NtmItems.POWDER_DIAMOND.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.EMERALD_ORE, stack(NtmItems.POWDER_EMERALD.get(), 1), stack(NtmItems.POWDER_EMERALD.get(), 1), stack(NtmItems.POWDER_EMERALD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.DEEPSLATE_EMERALD_ORE, stack(NtmItems.POWDER_EMERALD.get(), 1), stack(NtmItems.POWDER_EMERALD.get(), 1), stack(NtmItems.POWDER_EMERALD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.COPPER_ORE, stack(NtmItems.POWDER_COPPER.get(), 1), stack(NtmItems.POWDER_COPPER.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.DEEPSLATE_COPPER_ORE, stack(NtmItems.POWDER_COPPER.get(), 1), stack(NtmItems.POWDER_COPPER.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.REDSTONE_ORE, stack(Items.REDSTONE, 3), stack(Items.REDSTONE, 3), stack(NtmItems.NUGGET_MERCURY.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.DEEPSLATE_REDSTONE_ORE, stack(Items.REDSTONE, 3), stack(Items.REDSTONE, 3), stack(NtmItems.NUGGET_MERCURY.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.LAPIS_ORE, stack(NtmItems.POWDER_LAPIS.get(), 6), stack(NtmItems.POWDER_COBALT_TINY.get(), 1), stack(NtmItems.GEM_SODALITE.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.DEEPSLATE_LAPIS_ORE, stack(NtmItems.POWDER_LAPIS.get(), 6), stack(NtmItems.POWDER_COBALT_TINY.get(), 1), stack(NtmItems.GEM_SODALITE.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(Blocks.NETHER_QUARTZ_ORE, stack(NtmItems.POWDER_QUARTZ.get(), 1), stack(NtmItems.POWDER_QUARTZ.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1), stack(Blocks.NETHERRACK, 1));
        setRecipe(Blocks.NETHER_GOLD_ORE, stack(NtmItems.POWDER_GOLD.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(Blocks.NETHERRACK, 1));

        setRecipe(NtmBlocks.ORE_LIGNITE.get(), stack(NtmItems.POWDER_LIGNITE.get(), 2), stack(NtmItems.POWDER_LIGNITE.get(), 2), stack(NtmItems.POWDER_LIGNITE.get(), 2), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_DEEPSLATE_LIGNITE.get(), stack(NtmItems.POWDER_LIGNITE.get(), 2), stack(NtmItems.POWDER_LIGNITE.get(), 2), stack(NtmItems.POWDER_LIGNITE.get(), 2), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_TITANIUM.get(), stack(NtmItems.POWDER_TITANIUM.get(), 1), stack(NtmItems.POWDER_TITANIUM.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_TITANIUM_DEEPSLATE.get(), stack(NtmItems.POWDER_TITANIUM.get(), 1), stack(NtmItems.POWDER_TITANIUM.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_TUNGSTEN.get(), stack(NtmItems.POWDER_TUNGSTEN.get(), 1), stack(NtmItems.POWDER_TUNGSTEN.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_TUNGSTEN_DEEPSLATE.get(), stack(NtmItems.POWDER_TUNGSTEN.get(), 1), stack(NtmItems.POWDER_TUNGSTEN.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_LEAD.get(), stack(NtmItems.POWDER_LEAD.get(), 1), stack(NtmItems.POWDER_LEAD.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_LEAD_DEEPSLATE.get(), stack(NtmItems.POWDER_LEAD.get(), 1), stack(NtmItems.POWDER_LEAD.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_URANIUM.get(), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.NUGGET_RA226.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.NUGGET_RA226.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_URANIUM_SCORCHED.get(), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.NUGGET_RA226.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_NETHER_URANIUM.get(), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.NUGGET_RA226.get(), 1), stack(Blocks.NETHERRACK, 1));
        setRecipe(NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.NUGGET_RA226.get(), 1), stack(Blocks.NETHERRACK, 1));
        setRecipe(NtmBlocks.ORE_GNEISS_URANIUM.get(), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.NUGGET_RA226.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get(), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.NUGGET_RA226.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_THORIUM.get(), stack(NtmItems.POWDER_THORIUM.get(), 1), stack(NtmItems.POWDER_THORIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_THORIUM_DEEPSLATE.get(), stack(NtmItems.POWDER_THORIUM.get(), 1), stack(NtmItems.POWDER_THORIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_BERYLLIUM.get(), stack(NtmItems.POWDER_BERYLLIUM.get(), 1), stack(NtmItems.POWDER_BERYLLIUM.get(), 1), stack(NtmItems.POWDER_EMERALD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_BERYLLIUM_DEEPSLATE.get(), stack(NtmItems.POWDER_BERYLLIUM.get(), 1), stack(NtmItems.POWDER_BERYLLIUM.get(), 1), stack(NtmItems.POWDER_EMERALD.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_ALUMINIUM.get(), stack(NtmItems.CHUNK_CRYOLITE.get(), 2), stack(NtmItems.POWDER_TITANIUM.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_ALUMINIUM_DEEPSLATE.get(), stack(NtmItems.CHUNK_CRYOLITE.get(), 2), stack(NtmItems.POWDER_TITANIUM.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_FLUORITE.get(), stack(NtmItems.FLUORITE.get(), 3), stack(NtmItems.FLUORITE.get(), 3), stack(NtmItems.GEM_SODALITE.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_FLUORITE_DEEPSLATE.get(), stack(NtmItems.FLUORITE.get(), 3), stack(NtmItems.FLUORITE.get(), 3), stack(NtmItems.GEM_SODALITE.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_COBALT.get(), stack(NtmItems.POWDER_COBALT.get(), 2), stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.POWDER_COPPER.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_COBALT_DEEPSLATE.get(), stack(NtmItems.POWDER_COBALT.get(), 2), stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.POWDER_COPPER.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_SCHRABIDIUM.get(), stack(NtmItems.POWDER_SCHRABIDIUM.get(), 1), stack(NtmItems.POWDER_SCHRABIDIUM.get(), 1), stack(NtmItems.NUGGET_SOLINIUM.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_NETHER_SCHRABIDIUM.get(), stack(NtmItems.POWDER_SCHRABIDIUM.get(), 1), stack(NtmItems.POWDER_SCHRABIDIUM.get(), 1), stack(NtmItems.NUGGET_SOLINIUM.get(), 1), stack(Blocks.NETHERRACK, 1));
        setRecipe(NtmBlocks.ORE_GNEISS_SCHRABIDIUM.get(), stack(NtmItems.POWDER_SCHRABIDIUM.get(), 1), stack(NtmItems.POWDER_SCHRABIDIUM.get(), 1), stack(NtmItems.NUGGET_SOLINIUM.get(), 1), stack(Blocks.STONE, 1));
        setRecipe(NtmBlocks.ORE_NETHER_PLUTONIUM.get(), stack(NtmItems.POWDER_PLUTONIUM.get(), 1), stack(NtmItems.POWDER_PLUTONIUM.get(), 1), stack(NtmItems.NUGGET_POLONIUM.get(), 3), stack(Blocks.NETHERRACK, 1));
        setRecipe(NtmBlocks.ORE_TIKITE.get(), stack(NtmItems.POWDER_PLUTONIUM.get(), 1), stack(NtmItems.POWDER_COBALT.get(), 2), stack(NtmItems.POWDER_NIOBIUM.get(), 2), stack(Blocks.NETHERRACK, 1));
        setRecipe(NtmBlocks.GRAVEL_DIAMOND.get(), stack(NtmItems.POWDER_DIAMOND.get(), 3), stack(Blocks.GRAVEL, 1));

        setRecipe(stack(Items.BLAZE_ROD, 1), stack(Items.BLAZE_POWDER, 1), stack(Items.BLAZE_POWDER, 1), stack(NtmItems.POWDER_FIRE.get(), 1), stack(NtmItems.POWDER_FIRE.get(), 1));
    }

    private void registerCrystalRecipes() {
        setRecipe(stack(NtmItems.CRYSTAL_COAL.get(), 1), stack(NtmItems.POWDER_COAL.get(), 3), stack(NtmItems.POWDER_COAL.get(), 3), stack(NtmItems.POWDER_COAL.get(), 3), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_IRON.get(), 1), stack(NtmItems.POWDER_IRON.get(), 2), stack(NtmItems.POWDER_IRON.get(), 2), stack(NtmItems.POWDER_TITANIUM.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_GOLD.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 2), stack(NtmItems.POWDER_GOLD.get(), 2), stack(NtmItems.NUGGET_MERCURY.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_REDSTONE.get(), 1), stack(Items.REDSTONE, 3), stack(Items.REDSTONE, 3), stack(Items.REDSTONE, 3), stack(NtmItems.NUGGET_MERCURY.get(), 3));
        setRecipe(stack(NtmItems.CRYSTAL_LAPIS.get(), 1), stack(NtmItems.POWDER_LAPIS.get(), 4), stack(NtmItems.POWDER_LAPIS.get(), 4), stack(NtmItems.POWDER_COBALT.get(), 1), stack(NtmItems.GEM_SODALITE.get(), 2));
        setRecipe(stack(NtmItems.CRYSTAL_DIAMOND.get(), 1), stack(NtmItems.POWDER_DIAMOND.get(), 1), stack(NtmItems.POWDER_DIAMOND.get(), 1), stack(NtmItems.POWDER_DIAMOND.get(), 1), stack(NtmItems.POWDER_DIAMOND.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_URANIUM.get(), 1), stack(NtmItems.POWDER_URANIUM.get(), 2), stack(NtmItems.POWDER_URANIUM.get(), 2), stack(NtmItems.NUGGET_RA226.get(), 2), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_THORIUM.get(), 1), stack(NtmItems.POWDER_THORIUM.get(), 2), stack(NtmItems.POWDER_THORIUM.get(), 2), stack(NtmItems.POWDER_URANIUM.get(), 1), stack(NtmItems.NUGGET_RA226.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_PLUTONIUM.get(), 1), stack(NtmItems.POWDER_PLUTONIUM.get(), 2), stack(NtmItems.POWDER_PLUTONIUM.get(), 2), stack(NtmItems.POWDER_POLONIUM.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_TITANIUM.get(), 1), stack(NtmItems.POWDER_TITANIUM.get(), 2), stack(NtmItems.POWDER_TITANIUM.get(), 2), stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_SULFUR.get(), 1), stack(NtmItems.SULFUR.get(), 4), stack(NtmItems.SULFUR.get(), 4), stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.NUGGET_MERCURY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_NITER.get(), 1), stack(NtmItems.NITER.get(), 3), stack(NtmItems.NITER.get(), 3), stack(NtmItems.NITER.get(), 3), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_COPPER.get(), 1), stack(NtmItems.POWDER_COPPER.get(), 2), stack(NtmItems.POWDER_COPPER.get(), 2), stack(NtmItems.SULFUR.get(), 1), stack(NtmItems.POWDER_COBALT_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_TUNGSTEN.get(), 1), stack(NtmItems.POWDER_TUNGSTEN.get(), 2), stack(NtmItems.POWDER_TUNGSTEN.get(), 2), stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_ALUMINIUM.get(), 1), stack(NtmItems.CHUNK_CRYOLITE.get(), 3), stack(NtmItems.POWDER_TITANIUM.get(), 1), stack(NtmItems.POWDER_IRON.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_FLUORITE.get(), 1), stack(NtmItems.FLUORITE.get(), 4), stack(NtmItems.FLUORITE.get(), 4), stack(NtmItems.GEM_SODALITE.get(), 2), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_BERYLLIUM.get(), 1), stack(NtmItems.POWDER_BERYLLIUM.get(), 2), stack(NtmItems.POWDER_BERYLLIUM.get(), 2), stack(NtmItems.POWDER_QUARTZ.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_LEAD.get(), 1), stack(NtmItems.POWDER_LEAD.get(), 2), stack(NtmItems.POWDER_LEAD.get(), 2), stack(NtmItems.POWDER_GOLD.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_SCHRARANIUM.get(), 1), stack(NtmItems.NUGGET_SCHRABIDIUM.get(), 2), stack(NtmItems.NUGGET_SCHRABIDIUM.get(), 2), stack(NtmItems.NUGGET_URANIUM.get(), 2), stack(NtmItems.NUGGET_NEPTUNIUM.get(), 2));
        setRecipe(stack(NtmItems.CRYSTAL_SCHRABIDIUM.get(), 1), stack(NtmItems.POWDER_SCHRABIDIUM.get(), 2), stack(NtmItems.POWDER_SCHRABIDIUM.get(), 2), stack(NtmItems.POWDER_PLUTONIUM.get(), 1), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_RARE.get(), 1), stack(NtmItems.POWDER_DESH_MIX.get(), 1), stack(NtmItems.POWDER_DESH_MIX.get(), 1), stack(NtmItems.NUGGET_ZIRCONIUM.get(), 2), stack(NtmItems.NUGGET_ZIRCONIUM.get(), 2));
        setRecipe(stack(NtmItems.CRYSTAL_PHOSPHORUS.get(), 1), stack(NtmItems.POWDER_FIRE.get(), 3), stack(NtmItems.POWDER_FIRE.get(), 3), stack(NtmItems.INGOT_PHOSPHORUS.get(), 2), stack(Items.BLAZE_POWDER, 2));
        setRecipe(stack(NtmItems.CRYSTAL_TRIXITE.get(), 1), stack(NtmItems.POWDER_PLUTONIUM.get(), 2), stack(NtmItems.POWDER_COBALT.get(), 3), stack(NtmItems.POWDER_NIOBIUM.get(), 2), stack(NtmItems.POWDER_NITAN_MIX.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_LITHIUM.get(), 1), stack(NtmItems.POWDER_LITHIUM.get(), 2), stack(NtmItems.POWDER_LITHIUM.get(), 2), stack(NtmItems.POWDER_QUARTZ.get(), 1), stack(NtmItems.FLUORITE.get(), 1));
        setRecipe(stack(NtmItems.CRYSTAL_STARMETAL.get(), 1), stack(NtmItems.POWDER_DURA_STEEL.get(), 3), stack(NtmItems.POWDER_COBALT.get(), 3), stack(NtmItems.POWDER_ASTATINE.get(), 2), stack(NtmItems.NUGGET_MERCURY.get(), 5));
        setRecipe(stack(NtmItems.CRYSTAL_COBALT.get(), 1), stack(NtmItems.POWDER_COBALT.get(), 2), stack(NtmItems.POWDER_IRON.get(), 3), stack(NtmItems.POWDER_COPPER.get(), 3), stack(NtmItems.POWDER_LITHIUM_TINY.get(), 1));
    }

    }

    @Override public String getFileName() { return "hbmCentrifuge.json"; }
    @Override public Object getRecipeObject() { return table; }
    @Override public void registerDefaults() { Defaults defaults = new Defaults(this); defaults.registerOreRecipes(); defaults.registerCrystalRecipes(); }
    @Override public void deleteRecipes() { table.clear(); }
    @Override public String getComment() {
        return "Centrifuge recipes ported from 1.12.2, limited to ore_ blocks, crystal_ items and vanilla ore blocks. Replaces the whole table; empty disables it. Each input consumes one item regardless of configured positive count. Arrays are ID, count, META, custom-data SNBT; omitted META decodes as zero, explicit null preserves absence. Generic inputs match item/META (32767 wildcard); custom-data inputs constrain components. Outputs retain 1..4 ordered slots, including [minecraft:air,0] placeholders; at least one positive output is required.";
    }
    @Override public void readRecipe(JsonElement element) {
        try {
            if(element == null || !element.isJsonObject()) throw invalid("expected recipe object");
            JsonObject row = element.getAsJsonObject();
            ItemStack input = decodeItem(array(row.get("input"), "input"), false);
            JsonArray outputs = array(row.get("outputs"), "outputs");
            if(outputs.size() < 1 || outputs.size() > 4) throw invalid("outputs must have 1..4 slots");
            ItemStack[] result = new ItemStack[outputs.size()];
            for(int i = 0; i < result.length; i++) result[i] = decodeItem(array(outputs.get(i), "output " + i), true);
            addRecipe(input, result);
        } catch(RuntimeException ex) { throw invalid("recipe " + table.size() + ": " + ex.getMessage()); }
    }
    @Override public void writeRecipe(Object value, JsonWriter writer) throws IOException {
        CentrifugeRecipe row = (CentrifugeRecipe) value;
        writer.name("input"); writeItem(row.input.copyWithCount(1), writer);
        writer.name("outputs").beginArray();
        for(ItemStack output : row.outputs) writeItem(output, writer);
        writer.endArray();
    }
    @Override public void readRecipeStream(Reader reader) {
        StringBuilder text = new StringBuilder(); char[] chunk = new char[4096];
        try {
            int count;
            while((count = reader.read(chunk)) != -1) {
                if(text.length() + count > MAX_SYNC_BYTES) throw invalid("configuration exceeds 256 KiB");
                text.append(chunk, 0, count);
            }
        } catch(IOException ex) { throw invalid("cannot read configuration: " + ex.getMessage()); }
        List<CentrifugeRecipe> replacement = readSnapshot(text.toString());
        table.clear(); table.addAll(replacement);
    }
    public static List<CentrifugeRecipe> readSnapshot(String json) {
        encodeSnapshot(json);
        JsonObject root = gson.fromJson(json, JsonObject.class);
        if(root == null) throw invalid("missing table object");
        JsonArray rows = array(root.get("recipes"), "recipes");
        if(rows.size() > MAX_SYNC_RECIPES) throw invalid("too many recipes");
        List<CentrifugeRecipe> result = new ArrayList<>();
        CentrifugeRecipes handler = new CentrifugeRecipes(result);
        for(JsonElement row : rows) handler.readRecipe(row);
        return result;
    }
    public static String writeSnapshot() throws IOException {
        StringWriter text = new StringWriter(); JsonWriter writer = new JsonWriter(text);
        writer.beginObject().name("recipes").beginArray();
        CentrifugeRecipes handler = new CentrifugeRecipes();
        for(CentrifugeRecipe row : RECIPES) { writer.beginObject(); handler.writeRecipe(row, writer); writer.endObject(); }
        writer.endArray().endObject(); writer.close();
        String result = text.toString(); readSnapshot(result); return result;
    }
    public static byte[] encodeSnapshot(String json) {
        if(json == null || json.length() > MAX_SYNC_BYTES) throw invalid("snapshot exceeds 256 KiB");
        try {
            var bytes = StandardCharsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).encode(CharBuffer.wrap(json));
            if(bytes.remaining() > MAX_SYNC_BYTES) throw invalid("snapshot exceeds 256 KiB");
            byte[] result = new byte[bytes.remaining()]; bytes.get(result); return result;
        } catch(CharacterCodingException ex) { throw invalid("malformed UTF-16 surrogate"); }
    }
    private static ItemStack decodeItem(JsonArray values, boolean output) {
        if(values.size() < 1 || values.size() > 4) throw invalid("item array needs ID and optional count, META, SNBT");
        ResourceLocation id = ResourceLocation.parse(string(values.get(0)));
        if(!BuiltInRegistries.ITEM.containsKey(id)) throw invalid("unknown item " + id);
        Item item = BuiltInRegistries.ITEM.get(id);
        int count = values.size() > 1 ? integer(values.get(1)) : 1;
        if(item == Items.AIR) {
            if(!output || count != 0 || values.size() != 2) throw invalid("empty slot must be [minecraft:air,0] output");
            return ItemStack.EMPTY;
        }
        if(count <= 0) throw invalid("item count must be positive");
        ItemStack stack = new ItemStack(item, count);
        if(values.size() > 2 && values.get(2).isJsonNull()) stack.remove(NtmDataComponents.META.get());
        else {
            int meta = values.size() > 2 ? integer(values.get(2)) : 0;
            if(meta < 0) throw invalid("META must be nonnegative");
            MetaHelper.setMeta(stack, meta);
        }
        if(values.size() > 3) {
            try { TagsUtil.putCustomData(stack, TagParser.parseTag(string(values.get(3)))); }
            catch(Exception ex) { throw invalid("invalid custom-data SNBT: " + ex.getMessage()); }
        }
        return stack;
    }
    private static JsonArray encodeItem(ItemStack stack) {
        JsonArray result = new JsonArray();
        if(stack.isEmpty()) { result.add("minecraft:air"); result.add(0); return result; }
        if(stack.getCount() <= 0) throw invalid("invalid stack count");
        result.add(BuiltInRegistries.ITEM.getKey(stack.getItem()).toString());
        result.add(stack.getCount());
        if(stack.has(NtmDataComponents.META.get())) result.add(MetaHelper.getMeta(stack));
        else result.add(com.google.gson.JsonNull.INSTANCE);
        if(TagsUtil.hasCustomData(stack)) result.add(TagsUtil.getCustomData(stack).toString());
        if(!ItemStack.isSameItemSameComponents(stack, decodeItem(result, false))) throw invalid("array cannot represent components: " + result.get(0));
        return result;
    }
    private static void writeItem(ItemStack stack, JsonWriter writer) throws IOException {
        writer.beginArray();
        for(JsonElement value : encodeItem(stack)) {
            if(value.isJsonNull()) writer.nullValue();
            else if(value.getAsJsonPrimitive().isNumber()) writer.value(value.getAsNumber());
            else writer.value(value.getAsString());
        }
        writer.endArray();
    }
    private static JsonArray array(JsonElement value, String name) {
        if(value == null || !value.isJsonArray()) throw invalid("expected " + name + " array");
        return value.getAsJsonArray();
    }
    private static String string(JsonElement value) {
        if(value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isString()) throw invalid("expected string");
        return value.getAsString();
    }
    private static int integer(JsonElement value) {
        if(value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isNumber()) throw invalid("expected integer");
        try { return Integer.parseInt(value.getAsString()); }
        catch(NumberFormatException ex) { throw invalid("expected in-range integer"); }
    }
    private static IllegalArgumentException invalid(String message) { return new IllegalArgumentException("Centrifuge: " + message); }
}