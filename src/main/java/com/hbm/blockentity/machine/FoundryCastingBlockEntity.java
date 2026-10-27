package com.hbm.blockentity.machine;

import com.hbm.inventory.material.Mats;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.machine.MoldItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.NonNullList;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.Container;
import net.minecraft.world.ContainerHelper;
import net.minecraft.world.WorldlyContainer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/**
 * Upstream TileEntityFoundryCastingBase (TileEntityFoundryCastingBase.java:21-224): slot 0 holds the mold, slot 1 the finished cast,
 * which can only be extracted. The capacity is the installed mold's cost; a full block cools for 200 ticks, then casts.
 * <p>
 * Saves keep the format foundry_mold wrote before Goal 27D: {@code type} and {@code amount} (FoundryBaseBlockEntity), {@code cooloff}
 * and the slots in MachineBaseBlockEntity's {@code Items} list. The cooloff starts at 200, not upstream's 100 (NEO since Goal 10A);
 * upstream only uses its initial 100 until the block is first not full.
 */
public abstract class FoundryCastingBlockEntity extends FoundryBaseBlockEntity implements WorldlyContainer {

    public static final int COOLOFF = 200;

    public final NonNullList<ItemStack> slots = NonNullList.withSize(2, ItemStack.EMPTY);
    public int cooloff = COOLOFF;

    public FoundryCastingBlockEntity(BlockEntityType<? extends FoundryCastingBlockEntity> type, BlockPos pos, BlockState state) {
        super(type, pos, state);
    }

    /** 0 for the small molds of foundry_mold, 1 for the large molds of foundry_basin. */
    public abstract int getMoldSize();

    @Override
    public void updateEntity() {
        if(this.level != null && !this.level.isClientSide) {
            int capacity = this.getCapacity();
            int oldCooloff = this.cooloff;

            if(this.amount > capacity) {
                this.amount = capacity;
            }

            if(this.amount == 0) {
                this.type = null;
            }

            MoldItem.Mold mold = this.getInstalledMold();

            if(mold != null && this.amount == capacity && this.slots.get(1).isEmpty()) {
                this.cooloff--;

                if(this.cooloff <= 0) {
                    this.amount = 0;

                    ItemStack out = mold.getOutput(this.type);

                    if(!out.isEmpty()) {
                        this.slots.set(1, out);
                    }

                    this.cooloff = COOLOFF;
                }

            } else {
                this.cooloff = COOLOFF;
            }

            if(oldCooloff != this.cooloff) this.setChanged();
        }

        super.updateEntity();
    }

    /** Slot 0's mold if it is a mold of this block's size, else null. */
    @Nullable
    public MoldItem.Mold getInstalledMold() {
        MoldItem.Mold mold = MoldItem.of(this.slots.get(0));
        return mold != null && mold.size == this.getMoldSize() ? mold : null;
    }

    public boolean hasMold() {
        return this.getInstalledMold() != null;
    }

    /** The installed mold's cost, or 0 without a mold. */
    @Override
    public int getCapacity() {
        MoldItem.Mold mold = this.getInstalledMold();
        return mold == null ? 0 : mold.getCost();
    }

    /**
     * Upstream standardCheck plus: no cast waiting in slot 1, a mold installed and an output of this mold for the material.
     * Server side only (NEO): clients never take material.
     */
    @Override
    public boolean standardCheck(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        if(this.level == null || this.level.isClientSide || stack == null || stack.material == null || stack.amount <= 0) return false;
        if(!super.standardCheck(level, pos, side, stack)) return false;
        if(!this.slots.get(1).isEmpty()) return false;
        MoldItem.Mold mold = this.getInstalledMold();
        if(mold == null) return false;
        return !mold.getOutput(stack.material).isEmpty();
    }

    /** Non-mutating check whether {@link #pour(Mats.MaterialStack)} would take anything; the pour side rule is not applied. */
    public boolean canAccept(Mats.MaterialStack offered) {
        return this.standardCheck(this.level, this.worldPosition, Direction.UP, offered);
    }

    /** Returns accepted quanta without mutating the caller's material stack. */
    public int pour(Mats.MaterialStack offered) {
        if(!this.canAccept(offered)) return 0;
        int accepted = Math.min(offered.amount, Math.max(0, this.getCapacity() - this.amount));
        if(accepted > 0) {
            this.type = offered.material;
            this.amount += accepted;
            this.setChanged();
        }
        return accepted;
    }

    /** Puts one mold of this block's size from {@code held} into the empty mold slot. */
    public boolean insertMold(ItemStack held) {
        MoldItem.Mold mold = MoldItem.of(held);
        if(mold == null || mold.size != this.getMoldSize() || !this.slots.get(0).isEmpty() || this.amount > 0) return false;
        this.slots.set(0, held.split(1));
        this.setChanged();
        return true;
    }

    /** Removes the mold; nothing while material is held. */
    public ItemStack takeMold() {
        if(this.amount > 0) return ItemStack.EMPTY;
        return this.removeItem(0, 1);
    }

    /** Empties the material as scraps (EMPTY if there was none) and resets the cooloff. */
    public ItemStack takeScraps() {
        ItemStack scraps = this.type != null && this.amount > 0 ? CopperScrapsItem.create(new Mats.MaterialStack(this.type, this.amount)) : ItemStack.EMPTY;
        this.amount = 0;
        this.type = null;
        this.cooloff = COOLOFF;
        this.setChanged();
        return scraps;
    }

    @Override public int getContainerSize() { return this.slots.size(); }
    @Override public ItemStack getItem(int slot) { return this.slots.get(slot); }

    @Override
    public boolean isEmpty() {
        for(ItemStack stack : this.slots) {
            if(!stack.isEmpty()) return false;
        }
        return true;
    }

    @Override
    public ItemStack removeItem(int slot, int amount) {
        ItemStack stack = ContainerHelper.removeItem(this.slots, slot, amount);
        if(!stack.isEmpty()) this.setChanged();
        return stack;
    }

    @Override
    public ItemStack removeItemNoUpdate(int slot) {
        return ContainerHelper.takeItem(this.slots, slot);
    }

    @Override
    public void setItem(int slot, ItemStack stack) {
        this.slots.set(slot, stack);
        stack.limitSize(this.getMaxStackSize(stack));
        this.setChanged();
    }

    @Override public boolean stillValid(Player player) { return Container.stillValidBlockEntity(this, player); }
    @Override public void clearContent() { this.slots.clear(); }

    /** Upstream: no insertion, extraction of the cast only, from every side. */
    @Override public boolean canPlaceItem(int slot, ItemStack stack) { return false; }
    @Override public int[] getSlotsForFace(Direction direction) { return new int[] {1}; }
    @Override public boolean canPlaceItemThroughFace(int index, ItemStack stack, @Nullable Direction direction) { return false; }
    @Override public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return index == 1; }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putInt("cooloff", this.cooloff);
        ContainerHelper.saveAllItems(tag, this.slots, registries);
    }

    /**
     * The slots load first so the capacity the base class clamps the amount to is the installed mold's. A material the installed mold
     * cannot cast (or any material without a mold) loads as empty, as unknown material IDs do.
     */
    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        this.slots.clear();
        ContainerHelper.loadAllItems(tag, this.slots, registries);
        super.loadAdditional(tag, registries);

        MoldItem.Mold mold = this.getInstalledMold();
        if(this.type != null && (mold == null || mold.getOutput(this.type).isEmpty())) this.type = null;
        if(this.type == null) this.amount = 0;
        this.cooloff = tag.contains("cooloff") ? Math.clamp(tag.getInt("cooloff"), 1, COOLOFF) : COOLOFF;
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeInt(this.cooloff);
        ItemStack.OPTIONAL_STREAM_CODEC.encode(buf, this.slots.get(0));
        ItemStack.OPTIONAL_STREAM_CODEC.encode(buf, this.slots.get(1));
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.cooloff = Math.clamp(buf.readInt(), 1, COOLOFF);
        this.slots.set(0, ItemStack.OPTIONAL_STREAM_CODEC.decode(buf));
        this.slots.set(1, ItemStack.OPTIONAL_STREAM_CODEC.decode(buf));
    }
}
