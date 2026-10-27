package com.hbm.blockentity.machine;

import api.hbm.block.ICrucibleAcceptor;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Upstream TileEntityFoundryBase: base class for foundry channel type blocks - channels, tanks, outlets.
 * Foundry type blocks can only hold one type at a time and usually either store or move it around.
 * <p>
 * Every mutation calls setChanged(): 1.21 only saves chunks that were marked, where upstream relied on markDirty/markBlockForUpdate.
 * Clients receive type and amount through networkPackNT instead of a description packet.
 */
public abstract class FoundryBaseBlockEntity extends LoadedBaseBlockEntity implements ICrucibleAcceptor, ITickable {

    public NTMMaterial type;
    protected NTMMaterial lastType;
    public int amount;
    protected int lastAmount;

    public FoundryBaseBlockEntity(BlockEntityType<? extends FoundryBaseBlockEntity> type, BlockPos pos, BlockState state) {
        super(type, pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        if(this.lastType != this.type || this.lastAmount != this.amount) {
            this.setChanged();
            this.lastType = this.type;
            this.lastAmount = this.amount;
        }

        this.networkPackNT(25);
    }

    public abstract int getCapacity();

    /**
     * Standard check for testing if this material stack can be added to the casting block. Checks:<br>
     * - type matching<br>
     * - amount being at max<br>
     */
    public boolean standardCheck(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        if(this.type != null && this.type != stack.material && this.amount > 0) return false; //reject if there's already a different material
        if(this.amount >= this.getCapacity()) return false; //reject if the buffer is already full
        return true;
    }

    /**
     * Standardized adding of material via pouring or flowing. Does:<br>
     * - sets material to match the input
     * - adds the amount, not exceeding the maximum
     * - returns the amount that cannot be added (the passed stack, reduced) or null when everything was added
     */
    public Mats.MaterialStack standardAdd(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        this.type = stack.material;
        this.setChanged();

        if(stack.amount + this.amount <= this.getCapacity()) {
            this.amount += stack.amount;
            return null;
        }

        int required = this.getCapacity() - this.amount;
        this.amount = this.getCapacity();

        stack.amount -= required;

        return stack;
    }

    /** Standard check with no additional limitations added */
    @Override
    public boolean canAcceptPartialFlow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        return this.standardCheck(level, pos, side, stack);
    }

    /** Standard flow, no special handling required */
    @Override
    public Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        return this.standardAdd(level, pos, side, stack);
    }

    /** Standard check, but with the additional limitation that the only valid source direction is UP */
    @Override
    public boolean canAcceptPartialPour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        if(side != Direction.UP) return false;
        return this.standardCheck(level, pos, side, stack);
    }

    /** Standard flow, no special handling required */
    @Override
    public Mats.MaterialStack pour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        return this.standardAdd(level, pos, side, stack);
    }

    /** Empties this block, e.g. when shoveled out or broken. Returns the removed contents, or null if there were none. */
    public Mats.MaterialStack takeContents() {
        Mats.MaterialStack contents = this.amount > 0 && this.type != null ? new Mats.MaterialStack(this.type, this.amount) : null;
        this.amount = 0;
        this.type = null;
        this.setChanged();
        return contents;
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putInt("type", this.type == null ? -1 : this.type.id);
        tag.putInt("amount", this.amount);
    }

    /** Unknown materials load as empty and the amount is clamped to the capacity (NEO robustness, like FoundryMoldBlockEntity). */
    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.type = Mats.matById.get(tag.getInt("type"));
        this.amount = this.type == null ? 0 : Math.clamp(tag.getInt("amount"), 0, this.getCapacity());
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeInt(this.type == null ? -1 : this.type.id);
        buf.writeInt(this.amount);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.type = Mats.matById.get(buf.readInt());
        this.amount = buf.readInt();
    }
}
