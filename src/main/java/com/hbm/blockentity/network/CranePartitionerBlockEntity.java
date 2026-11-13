package com.hbm.blockentity.network;

import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Original CranePartitioner.TileEntityCranePartitioner (the acidizer input partitioner). Slots 0-44 queue acidizer inputs, which
 * leave as moving items of exactly one cycle's amount; slots 45-89 hold everything else until a hopper or crane takes it out. It has
 * no screen.
 */
public class CranePartitionerBlockEntity extends MachineBaseBlockEntity {

    public static final int SLOT_COUNT = 45;

    private static final int[] ALL_SLOTS = new int[SLOT_COUNT * 2];

    static {
        for(int i = 0; i < ALL_SLOTS.length; i++) ALL_SLOTS[i] = i;
    }

    public CranePartitionerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CRANE_PARTITIONER.get(), pos, state, SLOT_COUNT * 2);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable(this.getBlockState().getBlock().getDescriptionId());
    }

    /**
     * Original :150-178: the queued stacks, fewest items first, each send moving items of one cycle's amount (the whole stack when
     * the item is no acidizer input, :161) onto the partitioner's own belt until fewer items than that are left. The original never
     * marks the change for saving (its flag stays false, :158,176); NEO does.
     */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        List<ItemStack> stacks = new ArrayList<>();
        for(int i = 0; i < SLOT_COUNT; i++) if(!this.slots.get(i).isEmpty()) stacks.add(this.slots.get(i));
        stacks.sort(Comparator.comparingInt(ItemStack::getCount));

        boolean changed = false;

        for(ItemStack stack : stacks) {
            int amount = CrystallizerRecipes.getInputAmount(stack);
            if(amount <= 0) amount = stack.getCount();

            while(stack.getCount() >= amount) {
                ItemStack sent = stack.copyWithCount(amount);
                stack.shrink(amount);

                MovingItem item = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), this.level);
                item.moveTo(this.worldPosition.getX() + 0.5, this.worldPosition.getY() + 0.25, this.worldPosition.getZ() + 0.5, 0, 0);
                item.setItemStack(sent);
                this.level.addFreshEntity(item);
                changed = true;
            }
        }

        for(int i = 0; i < SLOT_COUNT; i++) if(this.slots.get(i).isEmpty()) this.slots.set(i, ItemStack.EMPTY);
        if(changed) this.setChanged();
    }

    /**
     * Original onItemEnter (:124-138) with InventoryUtil.tryAddItemToInventory (:120-133): acidizer inputs go into slots 0-44,
     * anything else into 45-89, first onto matching stacks, then whole into the first empty slot. Returns what did not fit.
     */
    public ItemStack accept(ItemStack stack) {
        boolean input = CrystallizerRecipes.getInputAmount(stack) > 0;
        int start = input ? 0 : SLOT_COUNT;
        int end = input ? SLOT_COUNT : SLOT_COUNT * 2;

        for(int i = start; i < end && !stack.isEmpty(); i++) {
            ItemStack slot = this.slots.get(i);

            if(!slot.isEmpty() && ItemStack.isSameItemSameComponents(slot, stack)) {
                int transfer = Math.min(stack.getCount(), slot.getMaxStackSize() - slot.getCount());

                if(transfer > 0) {
                    slot.grow(transfer);
                    stack.shrink(transfer);
                }
            }
        }

        if(!stack.isEmpty()) {
            for(int i = start; i < end; i++) {
                if(this.slots.get(i).isEmpty()) {
                    this.slots.set(i, stack);
                    stack = ItemStack.EMPTY;
                    break;
                }
            }
        }

        this.setChanged();
        return stack;
    }

    /** Original :198-209: every side sees all 90 slots. */
    @Override
    public int[] getSlotsForFace(Direction side) {
        return ALL_SLOTS;
    }

    /** Original :194-196: only acidizer inputs, only into the queue. */
    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return slot < SLOT_COUNT && CrystallizerRecipes.getInputAmount(stack) >= 1;
    }

    /** Original :189-191: only the second half can be taken out. */
    @Override
    public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction side) {
        return slot >= SLOT_COUNT;
    }

    @Override
    @Nullable
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return null;
    }
}
