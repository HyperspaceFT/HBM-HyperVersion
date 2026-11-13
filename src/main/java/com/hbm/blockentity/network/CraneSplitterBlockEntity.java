package com.hbm.blockentity.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.util.Mth;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Original TileEntityCraneSplitter, on the splitter's core block only. It is no inventory: it only keeps the ratio and where the
 * running split stands, so items that enter in several goes continue the count.
 */
public class CraneSplitterBlockEntity extends LoadedBaseBlockEntity implements ITickable {

    /* false: the left belt (the core's) is next, true: the right belt (the second block's) */
    private boolean position;
    /** How many more items the current side gets before the sides swap. */
    private int remaining;

    public int leftRatio = 1;
    public int rightRatio = 1;

    public CraneSplitterBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CRANE_SPLITTER.get(), pos, state);
    }

    /**
     * Original splitStack (:19-46): the items are counted out to the current side until its share is used up, then to the other
     * side with that side's ratio. Returns the left and the right part, either possibly empty.
     */
    public ItemStack[] splitStack(ItemStack stack) {
        int left = 0;
        int right = 0;
        int count = stack.getCount();

        if(this.remaining <= 0) this.remaining = this.position ? this.rightRatio : this.leftRatio;

        while(count > 0) {
            int toExtract = Math.min(this.remaining, count);

            this.remaining -= toExtract;
            count -= toExtract;
            if(this.position) right += toExtract; else left += toExtract;

            if(this.remaining <= 0) {
                this.position = !this.position;
                this.remaining = this.position ? this.rightRatio : this.leftRatio;
            }
        }

        this.setChanged();
        return new ItemStack[] { stack.copyWithCount(left), stack.copyWithCount(right) };
    }

    /** Original :48-51: the ratio is synced for the look overlay. */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;
        this.networkPackNT(15);
    }

    /** Original :54-63: "pos", "count", "left" and "right"; the ratios read as at least 1 (NEO also at most 16). */
    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.position = tag.getBoolean("pos");
        this.remaining = tag.getByte("count");
        this.leftRatio = Mth.clamp(tag.getByte("left"), 1, 16);
        this.rightRatio = Mth.clamp(tag.getByte("right"), 1, 16);
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putBoolean("pos", this.position);
        tag.putByte("count", (byte) this.remaining);
        tag.putByte("left", (byte) this.leftRatio);
        tag.putByte("right", (byte) this.rightRatio);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeByte(this.leftRatio);
        buf.writeByte(this.rightRatio);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.leftRatio = buf.readByte();
        this.rightRatio = buf.readByte();
    }
}
