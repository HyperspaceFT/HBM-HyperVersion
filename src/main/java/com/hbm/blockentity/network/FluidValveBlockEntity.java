package com.hbm.blockentity.network;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.uninos.UniNodespace;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;

/** Fluid valve and redstone fluid valve (original TileEntityFluidValve): a duct that only has a node while ENABLED. */
public class FluidValveBlockEntity extends PipeBaseBlockEntity {

    public FluidValveBlockEntity(BlockPos pos, BlockState state) {
        this(NtmBlockEntityTypes.FLUID_VALVE.get(), pos, state);
    }

    protected FluidValveBlockEntity(BlockEntityType<? extends FluidValveBlockEntity> type, BlockPos pos, BlockState state) {
        super(type, pos, state);
    }

    public boolean isOpen() {
        return this.getBlockState().getValue(BlockStateProperties.ENABLED);
    }

    @Override
    public boolean shouldCreateNode() {
        return this.isOpen();
    }

    /** Called after the ENABLED state changed: closing destroys the node, which splits the network (TileEntityFluidValve.java:15-23). */
    public void updateState() {
        if(this.level == null || this.level.isClientSide) return;
        // By position: a valve reloaded with its chunk finds its kept node only on its first tick
        if(!this.isOpen()) {
            UniNodespace.destroyNode(this.level, this.worldPosition, this.type.getNetworkProvider());
            this.node = null;
        }
    }
}
