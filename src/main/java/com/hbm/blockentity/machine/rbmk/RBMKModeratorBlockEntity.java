package com.hbm.blockentity.machine.rbmk;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;

/** Original TileEntityRBMKModerator. */
public class RBMKModeratorBlockEntity extends RBMKBaseBlockEntity {

    public RBMKModeratorBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_MODERATOR.get(), pos, state);
    }

    @Override
    public void onMelt(int reduce) {

        int count = 2 + level.random.nextInt(2);

        for(int i = 0; i < count; i++) {
            spawnDebris(DebrisType.GRAPHITE);
        }

        super.onMelt(reduce);
    }

    @Override
    public RBMKType getRBMKType() {
        return RBMKType.MODERATOR;
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.MODERATOR;
    }
}
