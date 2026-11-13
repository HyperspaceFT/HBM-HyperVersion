package com.hbm.blockentity.network;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.menus.CraneInserterMenu;
import com.hbm.util.AdjacentInventory;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

/** Original TileEntityCraneInserter: a 21-slot buffer that empties into the inventory on the output side. */
public class CraneInserterBlockEntity extends CraneBaseBlockEntity {

    private static final int[] ACCESS = new int[] { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 };

    /** Original :27: overflow is destroyed by default; the screen says so. */
    public boolean destroyer = true;

    public CraneInserterBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CRANE_INSERTER.get(), pos, state, 21);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.craneInserter");
    }

    /**
     * Original :40-93: without a redstone signal, the first buffer stack that moves at all goes in as a whole; when no whole stack
     * moves, the first stack of which one single item goes in gives that one item.
     */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        if(!this.level.hasNeighborSignal(this.worldPosition)) {
            Direction output = this.getOutputSide();
            BlockPos target = this.worldPosition.relative(output);
            Direction face = output.getOpposite();
            boolean didSomething = false;

            for(int i = 0; i < this.slots.size(); i++) {
                ItemStack stack = this.slots.get(i);

                if(!stack.isEmpty()) {
                    ItemStack ret = AdjacentInventory.insert(this.level, target, face, stack.copy());

                    if(ret.getCount() != stack.getCount()) {
                        this.setItem(i, ret.isEmpty() ? ItemStack.EMPTY : ret);
                        didSomething = true;
                        break;
                    }
                }
            }

            // single items for targets with a stack size limit (original :71-89)
            if(!didSomething) for(int i = 0; i < this.slots.size(); i++) {
                ItemStack stack = this.slots.get(i);

                if(!stack.isEmpty()) {
                    ItemStack ret = AdjacentInventory.insert(this.level, target, face, stack.copyWithCount(1));

                    if(ret.isEmpty()) {
                        this.removeItem(i, 1);
                        break;
                    }
                }
            }
        }

        this.networkPackNT(15);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeBoolean(this.destroyer);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.destroyer = buf.readBoolean();
    }

    /** Original :113-125: every slot from every side. */
    @Override
    public int[] getSlotsForFace(Direction side) {
        return ACCESS;
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return true;
    }

    @Override
    public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction side) {
        return true;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.destroyer = tag.getBoolean("destroyer");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putBoolean("destroyer", this.destroyer);
    }

    /** Original :156-158. */
    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("destroyer")) {
            this.destroyer = !this.destroyer;
            this.setChanged();
        }
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new CraneInserterMenu(containerId, inventory, this);
    }
}
