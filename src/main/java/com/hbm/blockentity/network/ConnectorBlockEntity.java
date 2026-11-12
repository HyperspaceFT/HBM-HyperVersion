package com.hbm.blockentity.network;

import api.hbm.energymk2.Nodespace.PowerNode;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.phys.Vec3;

/** Electricity connector (original TileEntityConnector.java:11-43): takes a cable only from the block it is attached to. */
public class ConnectorBlockEntity extends PylonBaseBlockEntity {

    public ConnectorBlockEntity(BlockPos pos, BlockState state) {
        this(NtmBlockEntityTypes.CONNECTOR.get(), pos, state);
    }

    protected ConnectorBlockEntity(BlockEntityType<? extends ConnectorBlockEntity> type, BlockPos pos, BlockState state) {
        super(type, pos, state);
    }

    @Override public ConnectionType getConnectionType() { return ConnectionType.SINGLE; }
    @Override public Vec3[] getMountPos() { return new Vec3[] {new Vec3(0.5, 0.5, 0.5)}; }
    @Override public double getMaxWireLength() { return 10; }

    @Override
    public PowerNode createNode() {
        BlockPos pos = this.getBlockPos();
        Direction dir = this.getFacing().getOpposite();
        PowerNode node = new PowerNode(pos).setConnections(
                this.selfLink(),
                new DirPos(pos.getX() + dir.getStepX(), pos.getY() + dir.getStepY(), pos.getZ() + dir.getStepZ(), dir));
        this.addWireLinks(node);
        return node;
    }

    @Override
    public boolean canConnect(Direction dir) {
        return this.getFacing().getOpposite() == dir;
    }

    /** The clicked face it was placed on, the original's metadata. */
    public Direction getFacing() {
        return this.getBlockState().getValue(BlockStateProperties.FACING);
    }
}
