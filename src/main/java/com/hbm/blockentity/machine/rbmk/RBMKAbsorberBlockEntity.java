package com.hbm.blockentity.machine.rbmk;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;

/** Original TileEntityRBMKAbsorber. */
public class RBMKAbsorberBlockEntity extends RBMKBaseBlockEntity {

    public RBMKAbsorberBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_ABSORBER.get(), pos, state);
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
    public RBMKType getRBMKType() {
        return RBMKType.ABSORBER;
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.ABSORBER;
    }
}
