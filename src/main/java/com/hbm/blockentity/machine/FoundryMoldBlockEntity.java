package com.hbm.blockentity.machine;

import com.hbm.blockentity.NtmBlockEntityTypes;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Upstream TileEntityFoundryMold (shallow foundry basin): takes the small molds; pours only from above, flows from every side.
 * Before Goal 27D NEO hard-coded three molds (cast plate, Dura ingot, tungsten blade); the mold now decides what is cast.
 */
public class FoundryMoldBlockEntity extends FoundryCastingBlockEntity {

    public FoundryMoldBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FOUNDRY_MOLD.get(), pos, state);
    }

    @Override
    public int getMoldSize() {
        return 0;
    }
}
