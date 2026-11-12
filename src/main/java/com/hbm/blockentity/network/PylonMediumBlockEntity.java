package com.hbm.blockentity.network;

import api.hbm.energymk2.Nodespace.PowerNode;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Medium wooden and steel pylons, with or without a transformer (original TileEntityPylonMedium.java:13-58). Only the transformer
 * variants take a cable, on the side behind the wires.
 */
public class PylonMediumBlockEntity extends PylonBaseBlockEntity {

    public PylonMediumBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.PYLON_MEDIUM.get(), pos, state);
    }

    @Override public ConnectionType getConnectionType() { return ConnectionType.TRIPLE; }
    @Override public double getMaxWireLength() { return 45; }

    @Override
    public Vec3[] getMountPos() {
        Direction dir = this.getFacing();
        double height = 7.5D;
        return new Vec3[] {
                new Vec3(0.5, height, 0.5),
                new Vec3(0.5 + dir.getStepX(), height, 0.5 + dir.getStepZ()),
                new Vec3(0.5 + dir.getStepX() * 2, height, 0.5 + dir.getStepZ() * 2),
        };
    }

    @Override
    public boolean canConnect(Direction dir) {
        return this.hasTransformer() && this.getFacing().getOpposite() == dir;
    }

    @Override
    public PowerNode createNode() {
        PowerNode node = new PowerNode(this.getBlockPos()).setConnections(this.selfLink());
        this.addWireLinks(node);
        if(this.hasTransformer()) {
            Direction dir = this.getFacing().getOpposite();
            BlockPos pos = this.getBlockPos();
            node.addConnection(new DirPos(pos.getX() + dir.getStepX(), pos.getY(), pos.getZ() + dir.getStepZ(), dir));
        }
        return node;
    }

    /** The core's facing, the original's metadata minus 10. */
    public Direction getFacing() {
        return this.getBlockState().getValue(DummyableBlock.FACING);
    }

    public boolean hasTransformer() {
        BlockState state = this.getBlockState();
        return state.is(NtmBlocks.RED_PYLON_MEDIUM_WOOD_TRANSFORMER.get()) || state.is(NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER.get());
    }
}
