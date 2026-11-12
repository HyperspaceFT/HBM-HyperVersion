package com.hbm.blockentity.network;

import api.hbm.energymk2.IEnergyConductorMK2;
import api.hbm.energymk2.Nodespace;
import api.hbm.energymk2.Nodespace.PowerNode;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.ITickable;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

public class CableBaseBlockEntity extends LoadedBaseBlockEntity implements IEnergyConductorMK2, ITickable {

    public PowerNode node;

    public CableBaseBlockEntity(BlockPos pos, BlockState state) {
        this(NtmBlockEntityTypes.NETWORK_CABLE.get(), pos, state);
    }

    protected CableBaseBlockEntity(BlockEntityType<? extends CableBaseBlockEntity> type, BlockPos pos, BlockState state) {
        super(type, pos, state);
    }

    @Override
    public void updateEntity() {
        if (level == null) return;

        if (!level.isClientSide) {
            if (this.node == null || this.node.expired) {

                if (this.shouldCreateNode()) {
                    this.node = Nodespace.getNode(level, this.getBlockPos());

                    if (this.node == null || this.node.expired) {
                        this.node = this.createNode();
                        Nodespace.createNode(level, this.node);
                    }
                }
            }
        }
    }

    public boolean shouldCreateNode() {
        return true;
    }

    @Override
    public void setRemoved() {
        super.setRemoved();

        // A chunk unload calls onChunkUnloaded first and keeps the node, as the original destroys it only on invalidate; removing the block calls setRemoved alone
        // // A reloaded block entity finds its kept node only on its first tick, so the node is destroyed by position
        if (this.level != null && !this.level.isClientSide && this.isLoaded) {
            Nodespace.destroyNode(level, this.getBlockPos());
        }
    }
}
