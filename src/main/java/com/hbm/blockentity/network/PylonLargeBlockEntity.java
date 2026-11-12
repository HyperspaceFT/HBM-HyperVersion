package com.hbm.blockentity.network;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/** Large electricity pylon (original TileEntityPylonLarge.java:7-40); its four facings are 45 degree steps (PylonLarge.java:62-83). */
public class PylonLargeBlockEntity extends PylonBaseBlockEntity {

    public PylonLargeBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.PYLON_LARGE.get(), pos, state);
    }

    @Override public ConnectionType getConnectionType() { return ConnectionType.QUAD; }
    @Override public double getMaxWireLength() { return 100; }

    @Override
    public Vec3[] getMountPos() {
        double topOff = 0.75 + 0.0625;
        double sideOff = 3.375;

        Vec3 vec = new Vec3(sideOff, 0, 0);

        // Vec3.yRot is the same rotation as the original Vec3.rotateAroundY
        switch(this.getBlockState().getValue(DummyableBlock.FACING)) {
            case NORTH -> vec = vec.yRot((float) Math.PI * 0.0F);
            case WEST -> vec = vec.yRot((float) Math.PI * 0.25F);
            case SOUTH -> vec = vec.yRot((float) Math.PI * 0.5F);
            case EAST -> vec = vec.yRot((float) Math.PI * 0.75F);
            default -> { }
        }

        return new Vec3[] {
                new Vec3(0.5 + vec.x, 11.5 + topOff, 0.5 + vec.z),
                new Vec3(0.5 + vec.x, 11.5 - topOff, 0.5 + vec.z),
                new Vec3(0.5 - vec.x, 11.5 + topOff, 0.5 - vec.z),
                new Vec3(0.5 - vec.x, 11.5 - topOff, 0.5 - vec.z),
        };
    }
}
