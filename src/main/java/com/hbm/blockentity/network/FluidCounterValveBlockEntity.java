package com.hbm.blockentity.network;

import api.hbm.fluidmk2.FluidNode;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.uninos.UniNodespace;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Counter valve (original TileEntityFluidCounterValve.java:20-97): a valve that adds its network's fluid tracker to a saved
 * counter every tick while open.
 */
public class FluidCounterValveBlockEntity extends FluidValveBlockEntity {

    private long counter;
    private long lastCounterUpdate = -1;

    public FluidCounterValveBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FLUID_COUNTER_VALVE.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        super.updateEntity();

        if(this.level != null && !this.level.isClientSide) {
            this.updateCounter();
            this.networkPackNT(25);
        }
    }

    private void updateCounter() {
        if(this.hasPendingCounterUpdate()) {
            this.counter += this.node.net.fluidTracker;
            this.lastCounterUpdate = this.level.getGameTime();
        }
    }

    private boolean hasPendingCounterUpdate() {
        return this.node != null && this.node.net != null && this.type != Fluids.NONE && this.lastCounterUpdate != this.level.getGameTime();
    }

    public long getCounter() {
        return this.counter;
    }

    /** Closing first books this tick's pending flow, then destroys the node (TileEntityFluidCounterValve.java:54-62). */
    @Override
    public void updateState() {
        if(this.level == null || this.level.isClientSide) return;
        if(!this.isOpen()) {
            // A valve reloaded with its chunk finds its kept node only on its first tick
            if(this.node == null) this.node = (FluidNode) UniNodespace.getNode(this.level, this.worldPosition, this.type.getNetworkProvider());
            this.updateCounter();
        }
        super.updateState();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.counter = tag.getLong("counter");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("counter", this.counter);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.counter);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.counter = Math.max(buf.readLong(), 0);
    }
}
