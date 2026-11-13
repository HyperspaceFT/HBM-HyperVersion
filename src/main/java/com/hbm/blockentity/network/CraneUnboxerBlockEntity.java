package com.hbm.blockentity.network;

import api.hbm.conveyor.IConveyorBelt;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.inventory.menus.CraneUnboxerMenu;
import com.hbm.items.NtmItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Original TileEntityCraneUnboxer. Slots 0-20 are the buffer, 21 the stack upgrade and 22 the ejector upgrade
 * (ContainerCraneUnboxer.java:21-27).
 */
public class CraneUnboxerBlockEntity extends CraneBaseBlockEntity {

    public static final int SLOT_STACK_UPGRADE = 21;
    public static final int SLOT_EJECTOR_UPGRADE = 22;
    public static final int[] ACCESS = new int[] { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 };

    public CraneUnboxerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CRANE_UNBOXER.get(), pos, state, 23);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.craneUnboxer");
    }

    /** Original :36-43: ticks between actions, 20 or 10/5/2 with the ejector upgrade. */
    public int getDelay() {
        ItemStack upgrade = this.slots.get(SLOT_EJECTOR_UPGRADE);
        if(upgrade.is(NtmItems.UPGRADE_EJECTOR_1.get())) return 10;
        if(upgrade.is(NtmItems.UPGRADE_EJECTOR_2.get())) return 5;
        if(upgrade.is(NtmItems.UPGRADE_EJECTOR_3.get())) return 2;
        return 20;
    }

    /** Original :55-63: items per action, 1 or 4/16/64 with the stack upgrade. */
    public int getAmount() {
        ItemStack upgrade = this.slots.get(SLOT_STACK_UPGRADE);
        if(upgrade.is(NtmItems.UPGRADE_STACK_1.get())) return 4;
        if(upgrade.is(NtmItems.UPGRADE_STACK_2.get())) return 16;
        if(upgrade.is(NtmItems.UPGRADE_STACK_3.get())) return 64;
        return 1;
    }

    /**
     * Original :30-92. When the world time is a multiple of the delay and there is no redstone signal, the first filled buffer slot
     * sends up to the amount onto the belt on the input side (the switcheroo, :65), 0.55 blocks toward it and snapped onto it.
     */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;
        if(this.level.getGameTime() % this.getDelay() != 0 || this.level.hasNeighborSignal(this.worldPosition)) return;

        Direction outputSide = this.getInputSide(); // note the switcheroo!
        BlockPos beltPos = this.worldPosition.relative(outputSide);
        Block b = this.level.getBlockState(beltPos).getBlock();
        if(!(b instanceof IConveyorBelt belt)) return;

        int amount = this.getAmount();

        for(int i = 0; i < 21; i++) {
            ItemStack stack = this.slots.get(i);

            if(!stack.isEmpty()) {
                ItemStack sent = this.removeItem(i, Math.min(amount, stack.getCount()));

                MovingItem moving = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), this.level);
                Vec3 pos = Vec3.atCenterOf(this.worldPosition).add(outputSide.getStepX() * 0.55, outputSide.getStepY() * 0.55, outputSide.getStepZ() * 0.55);
                Vec3 snap = belt.getClosestSnappingPosition(this.level, beltPos, pos);
                moving.moveTo(snap.x, snap.y, snap.z, 0, 0);
                moving.setItemStack(sent);
                this.level.addFreshEntity(moving);
                break;
            }
        }
    }

    /** Original :94-108: the buffer is open from every side for putting in and taking out; the upgrade slots are not. */
    @Override
    public int[] getSlotsForFace(Direction side) {
        return ACCESS;
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return slot >= 0 && slot < 21;
    }

    @Override
    public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction side) {
        return slot >= 0 && slot < 21;
    }

    /** The unboxer has no screen controls. */
    @Override
    public void receiveControl(CompoundTag tag) { }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new CraneUnboxerMenu(containerId, inventory, this);
    }
}
