package com.hbm.inventory.recipes.crafting;

import com.hbm.inventory.MetaHelper;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.registry.NtmRecipeSerializers;
import net.minecraft.core.HolderLookup;
import net.minecraft.util.Mth;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.CraftingBookCategory;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CustomRecipe;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.level.Level;

/**
 * Original RBMKFuelCraftingHandler: a cold fuel rod alone in the grid is taken apart into 8 pellets of its pellet type, the
 * enrichment grade and xenon in the pellet's meta. The empty rod stays in the grid through the rod's crafting remainder
 * (rbmk_fuel_empty).
 */
public class RBMKRodDisassemblyRecipe extends CustomRecipe {

    public RBMKRodDisassemblyRecipe(CraftingBookCategory category) {
        super(category);
    }

    /**
     * Original matches (:17-26): exactly one stack, a rod with a pellet, hull and core below 50. Enrichment is not tested here, as in
     * the original, so an unburnt rod matches and assemble gives nothing for it.
     */
    @Override
    public boolean matches(CraftingInput input, Level level) {
        ItemStack stack = singleStack(input);
        return stack.getItem() instanceof RBMKRodItem rod && rod.pellet != null
                && RBMKRodItem.getHullHeat(stack) < 50 && RBMKRodItem.getCoreHeat(stack) < 50;
    }

    /** Original getCraftingResult (:34-61); its null results are EMPTY here. */
    @Override
    public ItemStack assemble(CraftingInput input, HolderLookup.Provider registries) {
        ItemStack stack = singleStack(input);

        if(stack.getItem() instanceof RBMKRodItem rod) {

            if(rod.pellet == null) return ItemStack.EMPTY;
            if(RBMKRodItem.getEnrichment(stack) > 0.99D) return ItemStack.EMPTY;

            if(RBMKRodItem.getHullHeat(stack) < 50 && RBMKRodItem.getCoreHeat(stack) < 50) {
                int enrichment = 4 - Mth.clamp((int) Math.ceil(RBMKRodItem.getEnrichment(stack) * 5 - 1), 0, 4);
                int meta = enrichment + (RBMKRodItem.getPoisonLevel(stack) >= 0.5D ? 5 : 0);
                return MetaHelper.newStack(rod.pellet, 8, meta);
            }
        }

        return ItemStack.EMPTY;
    }

    /** The only non-empty stack of the grid, or EMPTY when there are none or several (original hasExactlyOneStack / getFirstStack). */
    private static ItemStack singleStack(CraftingInput input) {
        ItemStack found = ItemStack.EMPTY;

        for(int i = 0; i < input.size(); i++) {
            ItemStack stack = input.getItem(i);
            if(stack.isEmpty()) continue;
            if(!found.isEmpty()) return ItemStack.EMPTY;
            found = stack;
        }

        return found;
    }

    @Override
    public boolean canCraftInDimensions(int width, int height) {
        return width * height >= 1;
    }

    @Override
    public RecipeSerializer<?> getSerializer() {
        return NtmRecipeSerializers.RBMK_ROD_DISASSEMBLY.get();
    }
}
