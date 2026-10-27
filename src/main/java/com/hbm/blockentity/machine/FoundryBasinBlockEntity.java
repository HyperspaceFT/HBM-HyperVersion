package com.hbm.blockentity.machine;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.material.Mats;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

/** Upstream TileEntityFoundryBasin (TileEntityFoundryBasin.java:9-27): takes the large molds; pours only from above, no flows. */
public class FoundryBasinBlockEntity extends FoundryCastingBlockEntity {

    public FoundryBasinBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FOUNDRY_BASIN.get(), pos, state);
    }

    @Override
    public int getMoldSize() {
        return 1;
    }

    /* Basin can't accept sideways flowing */
    @Override public boolean canAcceptPartialFlow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) { return false; }
    @Override public Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) { return stack; }
}
