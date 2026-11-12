package com.hbm.blockentity.network;

import api.hbm.energymk2.Nodespace;
import com.hbm.blockentity.NtmBlockEntityTypes;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;

/** Power switch and redstone power switch (original TileEntityCableSwitch): a cable that only has a node while ENABLED. */
public class CableSwitchBlockEntity extends CableBaseBlockEntity {

    public CableSwitchBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CABLE_SWITCH.get(), pos, state);
    }

    public boolean isOn() {
        return this.getBlockState().getValue(BlockStateProperties.ENABLED);
    }

    /** Called after the ENABLED state changed: switching off destroys the node, which splits the network (TileEntityCableSwitch.java:7-15). */
    public void updateState() {
        if(this.level == null || this.level.isClientSide) return;
        // By position: a switch reloaded with its chunk finds its kept node only on its first tick
        if(!this.isOn()) {
            Nodespace.destroyNode(this.level, this.getBlockPos());
            this.node = null;
        }
    }

    @Override
    public boolean shouldCreateNode() {
        return this.isOn();
    }
}
