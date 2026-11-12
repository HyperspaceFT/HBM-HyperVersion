package com.hbm.blockentity.network;

import api.hbm.energymk2.Nodespace.PowerNode;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.lib.Library;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/** Wooden and steel electricity pylon (original TileEntityPylon.java:12-58). */
public class PylonBlockEntity extends PylonBaseBlockEntity {

    public PylonBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.PYLON.get(), pos, state);
    }

    @Override public ConnectionType getConnectionType() { return ConnectionType.SINGLE; }
    @Override public Vec3[] getMountPos() { return new Vec3[] {new Vec3(0.5, 5.5, 0.5)}; }
    @Override public double getMaxWireLength() { return 25; }

    @Override
    public boolean canConnect(Direction dir) {
        return dir != null && dir != Direction.DOWN;
    }

    /** Also takes cables on its four horizontal sides. */
    @Override
    public PowerNode createNode() {
        BlockPos pos = this.getBlockPos();
        int x = pos.getX(), y = pos.getY(), z = pos.getZ();
        PowerNode node = new PowerNode(pos).setConnections(
                this.selfLink(),
                new DirPos(x + 1, y, z, Library.POS_X),
                new DirPos(x - 1, y, z, Library.NEG_X),
                new DirPos(x, y, z + 1, Library.POS_Z),
                new DirPos(x, y, z - 1, Library.NEG_Z));
        this.addWireLinks(node);
        return node;
    }
}
