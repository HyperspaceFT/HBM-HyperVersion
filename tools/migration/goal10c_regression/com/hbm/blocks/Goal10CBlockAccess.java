package com.hbm.blocks;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;

/** Reaches the protected DummyableBlock.fillSpace from the fixture (same package as the declaring class). */
public class Goal10CBlockAccess {
    /**
     * The server branch of production DummyableBlock.setPlacedBy for a player placing the block at the clicked position:
     * the core goes getOffset() blocks back along the facing, then fillSpace builds the dummies. The item handling and
     * checkSpace (the requirement check) are not run.
     */
    public static BlockPos place(DummyableBlock block, Level level, BlockPos core, Direction dir) {
        BlockPos clicked = core.relative(dir, block.getOffset());
        int offset = -block.getOffset();
        BlockPos corePos = clicked.relative(dir, offset);
        level.setBlock(corePos, block.createCoreState(dir), 3);
        block.fillSpace(level, clicked, dir, offset);
        return corePos;
    }
}
