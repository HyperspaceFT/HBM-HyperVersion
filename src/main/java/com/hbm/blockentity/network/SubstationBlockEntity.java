package com.hbm.blockentity.network;

import api.hbm.energymk2.Nodespace.PowerNode;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.lib.Library;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Substation (original TileEntitySubstation.java:13-71). The node covers the core and its four diagonal neighbours and takes cables
 * on the X and Z sides of those diagonals, whatever the facing.
 */
public class SubstationBlockEntity extends PylonBaseBlockEntity {

    public SubstationBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.SUBSTATION.get(), pos, state);
    }

    @Override public ConnectionType getConnectionType() { return ConnectionType.QUAD; }
    @Override public double getMaxWireLength() { return 20; }

    @Override
    public Vec3[] getMountPos() {

        double topOff = 5.25;
        Vec3 vec = new Vec3(1, 0, 0);

        switch(this.getBlockState().getValue(DummyableBlock.FACING)) {
            case WEST, EAST -> vec = vec.yRot((float) Math.PI * 0.5F);
            default -> { }
        }

        return new Vec3[] {
                new Vec3(0.5 + vec.x * 0.5, topOff, 0.5 + vec.z * 0.5),
                new Vec3(0.5 + vec.x * 1.5, topOff, 0.5 + vec.z * 1.5),
                new Vec3(0.5 - vec.x * 0.5, topOff, 0.5 - vec.z * 0.5),
                new Vec3(0.5 - vec.x * 1.5, topOff, 0.5 - vec.z * 1.5),
        };
    }

    @Override
    public Vec3 getConnectionPoint() {
        BlockPos pos = this.getBlockPos();
        return new Vec3(pos.getX() + 0.5, pos.getY() + 5.25, pos.getZ() + 0.5);
    }

    @Override
    public PowerNode createNode() {
        BlockPos pos = this.getBlockPos();
        int x = pos.getX(), y = pos.getY(), z = pos.getZ();
        PowerNode node = new PowerNode(pos,
                new BlockPos(x + 1, y, z + 1),
                new BlockPos(x + 1, y, z - 1),
                new BlockPos(x - 1, y, z + 1),
                new BlockPos(x - 1, y, z - 1)).setConnections(
                this.selfLink(),
                new DirPos(x + 2, y, z - 1, Library.POS_X),
                new DirPos(x + 2, y, z + 1, Library.POS_X),
                new DirPos(x - 2, y, z - 1, Library.NEG_X),
                new DirPos(x - 2, y, z + 1, Library.NEG_X),
                new DirPos(x - 1, y, z + 2, Library.POS_Z),
                new DirPos(x + 1, y, z + 2, Library.POS_Z),
                new DirPos(x - 1, y, z - 2, Library.NEG_Z),
                new DirPos(x + 1, y, z - 2, Library.NEG_Z));
        this.addWireLinks(node);
        return node;
    }
}
