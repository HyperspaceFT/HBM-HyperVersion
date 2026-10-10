package com.hbm.blockentity.machine.oil;

import com.hbm.blockentity.NtmBlockEntityTypes;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

public class FractionSpacerBlockEntity extends BlockEntity {

    public FractionSpacerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FRACTION_SPACER.get(), pos, state);
    }

    public AABB getRenderBoundingBox() {
        return new AABB(this.worldPosition.getX() - 1, this.worldPosition.getY(), this.worldPosition.getZ() - 1,
                this.worldPosition.getX() + 2, this.worldPosition.getY() + 1, this.worldPosition.getZ() + 2);
    }
}
