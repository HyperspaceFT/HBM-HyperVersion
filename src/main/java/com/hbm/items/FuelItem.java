package com.hbm.items;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

/**
 * Fixed burn time, the NEO side of the original global fuel table (FuelHandler.java:21-66, registered at MainRegistry.java:273),
 * so vanilla furnaces and every ModuleBurnTime machine see it. Block items from that table use the furnace_fuels data map instead
 * (NtmDataMapProvider).
 */
public class FuelItem extends Item {

    private final int burnTime;

    public FuelItem(Properties properties, int burnTime) {
        super(properties);
        this.burnTime = burnTime;
    }

    @Override
    public int getBurnTime(ItemStack stack, net.minecraft.world.item.crafting.RecipeType<?> recipeType) {
        return this.burnTime;
    }
}
