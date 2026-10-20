package com.hbm.blockentity.machine.rbmk;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;

/** Original TileEntityRBMKBlank. */
public class RBMKBlankBlockEntity extends RBMKBaseBlockEntity {

    public RBMKBlankBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_BLANK.get(), pos, state);
    }

    @Override
    public void onMelt(int reduce) {

        int count = 1 + level.random.nextInt(2);

        for(int i = 0; i < count; i++) {
            spawnDebris(DebrisType.BLANK);
        }

        super.onMelt(reduce);
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.BLANK;
    }
}
