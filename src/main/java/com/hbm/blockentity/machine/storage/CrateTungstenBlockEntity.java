package com.hbm.blockentity.machine.storage;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.items.NtmItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.level.block.state.BlockState;

public class CrateTungstenBlockEntity extends CrateBaseBlockEntity {

    public CrateTungstenBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CRATE_TUNGSTEN.get(), pos, state, 27, "gui_crate_tungsten", 9, 3, 8, 18, 8, 86, 176, 168, 8, 10526880, 10526880);
    }

    // ORIG TileEntityCrateTungsten.java:62-76: automation may not pull the polonium billet or anything the furnace would smelt.
    // The original's damaged-crucible clause has no NEO item to apply to.
    @Override
    public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) {
        if(this.isLocked() || this.level == null) return false;
        if(stack.is(NtmItems.BILLET_POLONIUM.get())) return false;

        return this.level.getRecipeManager().getRecipeFor(RecipeType.SMELTING, new SingleRecipeInput(stack), this.level).isEmpty();
    }

    @Override public Component getName() { return Component.translatable("container.crateTungsten"); }
}
