package com.hbm.inventory.recipes;

import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.material.MaterialEntries;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.material.NTMMaterial.SmeltingBehavior;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Crucible smelting lookups and the Goal 5A/10A small cast-plate helpers. What an item melts into is upstream's
 * Mats.getSmeltingMaterialsFromItem, built from {@link MaterialEntries} and MatDistribution. Since Goal 27D mold outputs come
 * from MoldItem and {@link MaterialEntries}; the plate helpers and constants are kept for the old Goal 5A/10A regressions.
 * The class name is kept for the Goal 5A casting regression.
 */
public final class CopperCastingRecipes {
    public static final int INGOT_QUANTA = MaterialShapes.INGOT.q(1);
    public static final int BLOCK_QUANTA = MaterialShapes.BLOCK.q(1);
    public static final int NUGGET_QUANTA = MaterialShapes.NUGGET.q(1);
    public static final int BLADE_QUANTA = 3 * 72;
    public static final int PLATE_QUANTA = MaterialShapes.CASTPLATE.q(1);
    public static final int POUR_QUANTA = MaterialShapes.NUGGET.q(3);

    private CopperCastingRecipes() { }

    /** One item that melts into a single material. */
    public record MeltEntry(Item item, NTMMaterial material, int amount) {
        public Mats.MaterialStack result() { return new Mats.MaterialStack(this.material, this.amount); }
    }

    /** One crucible smelting display recipe: any of the inputs melts into all of the outputs (upstream CrucibleRecipes.getSmeltingRecipes). */
    public record SmeltingRecipe(List<ItemStack> inputs, List<Mats.MaterialStack> outputs) { }

    /**
     * Single-material view of the smelting table, kept for the Goal 5A/10A callers: every item without a meta
     * variant (MeltEntry has no meta) from the material entries, then the fixed item entries, whose smelting result is
     * exactly one material. Computed on each call because the fixed entries reload with the recipe files.
     */
    public static List<MeltEntry> getMeltEntries() {
        List<MeltEntry> entries = new ArrayList<>();
        Set<Item> seen = Collections.newSetFromMap(new IdentityHashMap<>());
        for(MaterialEntries.Entry row : MaterialEntries.getEntries()) {
            if(row.meta() == 0) addMeltEntry(entries, seen, row.item());
        }
        for(ComparableStack key : Mats.materialEntries.keySet()) {
            if(key.meta == 0 || key.meta == MetaHelper.WILDCARD_VALUE) addMeltEntry(entries, seen, key.item);
        }
        return entries;
    }

    private static void addMeltEntry(List<MeltEntry> entries, Set<Item> seen, Item item) {
        if(!seen.add(item)) return;
        List<Mats.MaterialStack> result = getMaterials(new ItemStack(item));
        if(result.size() == 1) entries.add(new MeltEntry(item, result.get(0).material, result.get(0).amount));
    }

    /** Fresh material stacks the item melts into, empty if it does not melt in the crucible. */
    public static List<Mats.MaterialStack> getMaterials(ItemStack stack) {
        return Mats.getSmeltingMaterialsFromItem(stack);
    }

    /** First material of {@link #getMaterials(ItemStack)} for single-material callers, or null if the item does not melt. */
    public static Mats.MaterialStack getMaterial(ItemStack stack) {
        List<Mats.MaterialStack> materials = getMaterials(stack);
        return materials.isEmpty() ? null : materials.get(0);
    }

    /**
     * Upstream CrucibleRecipes.getSmeltingRecipes: one recipe per material and autogen shape with registered items
     * (in material and shape order, output converted through smeltsInto), then the tag entries, then the item entries
     * with their listed, unconverted materials.
     */
    public static List<SmeltingRecipe> getSmeltingRecipes() {
        List<SmeltingRecipe> recipes = new ArrayList<>();

        for(NTMMaterial material : Mats.orderedList) {
            int in = material.convIn;
            int out = material.convOut;
            NTMMaterial convert = material.smeltsInto;
            if(convert.smeltable != SmeltingBehavior.SMELTABLE && convert.smeltable != SmeltingBehavior.ADDITIVE) continue;
            for(MaterialShapes shape : MaterialShapes.allShapes) {
                if(shape.noAutogen) continue;
                List<ItemStack> inputs = new ArrayList<>();
                for(MaterialEntries.Entry entry : MaterialEntries.getEntries(material, shape)) {
                    ItemStack stack = entry.stack(1);
                    // The table repeats some rows (several upstream registrations of one item); show each item once.
                    if(inputs.stream().noneMatch(other -> MetaHelper.compareStacks(other, stack))) inputs.add(stack);
                }
                if(!inputs.isEmpty()) {
                    recipes.add(new SmeltingRecipe(inputs, List.of(new Mats.MaterialStack(convert, (int) (shape.q(1) * out / in)))));
                }
            }
        }

        for(Map.Entry<String, List<Mats.MaterialStack>> entry : Mats.materialOreEntries.entrySet()) {
            List<ItemStack> inputs = new ArrayList<>();
            for(Holder<Item> holder : BuiltInRegistries.ITEM.getTagOrEmpty(ItemTags.create(ResourceLocation.parse(entry.getKey())))) {
                inputs.add(new ItemStack(holder.value()));
            }
            // JEI cannot show a recipe without inputs; upstream lists the ore name even when nothing carries it.
            if(!inputs.isEmpty()) recipes.add(new SmeltingRecipe(inputs, copy(entry.getValue())));
        }

        for(Map.Entry<ComparableStack, List<Mats.MaterialStack>> entry : Mats.materialEntries.entrySet()) {
            ComparableStack key = entry.getKey();
            ItemStack input = key.meta == 0 || key.meta == MetaHelper.WILDCARD_VALUE
                    ? new ItemStack(key.item) : MetaHelper.newStack(key.item, 1, key.meta);
            recipes.add(new SmeltingRecipe(List.of(input), copy(entry.getValue())));
        }

        return recipes;
    }

    private static List<Mats.MaterialStack> copy(List<Mats.MaterialStack> stacks) {
        List<Mats.MaterialStack> copies = new ArrayList<>();
        for(Mats.MaterialStack stack : stacks) if(stack != null) copies.add(stack.copy());
        return copies;
    }

    /** Small cast-plate variant for a material, or null when the mold has no output for it (cobalt). */
    public static CastPlateItem.Type getPlateType(NTMMaterial material) {
        if(material == Mats.MAT_COPPER) return CastPlateItem.Type.COPPER;
        if(material == Mats.MAT_STEEL) return CastPlateItem.Type.STEEL;
        if(material == Mats.MAT_TUNGSTEN) return CastPlateItem.Type.TUNGSTEN;
        if(material == Mats.MAT_DURA) return CastPlateItem.Type.DURA_STEEL;
        return null;
    }

    /** Materials the small cast-plate mold accepts, in material registration order. */
    public static List<NTMMaterial> getCastableMaterials() {
        List<NTMMaterial> castable = new ArrayList<>();
        for(NTMMaterial material : Mats.orderedList) if(getPlateType(material) != null) castable.add(material);
        return castable;
    }

    public static ItemStack getPlate(NTMMaterial material) {
        CastPlateItem.Type type = getPlateType(material);
        return type == null ? ItemStack.EMPTY : NtmItems.castPlate(type, 1);
    }
}
