package com.hbm.blockentity.network;

import com.hbm.blockentity.NtmBlockEntityTypes;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/** Heavy duty electricity connector (original TileEntityConnectorSuper.java:6-19). */
public class ConnectorSuperBlockEntity extends ConnectorBlockEntity {

    public ConnectorSuperBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CONNECTOR_SUPER.get(), pos, state);
    }

    @Override
    public Vec3[] getMountPos() {
        Direction dir = this.getFacing();
        return new Vec3[] {new Vec3(0.5 + dir.getStepX() * 0.375, 0.5 + dir.getStepY() * 0.375, 0.5 + dir.getStepZ() * 0.375)};
    }

    @Override public double getMaxWireLength() { return 100; }
}
