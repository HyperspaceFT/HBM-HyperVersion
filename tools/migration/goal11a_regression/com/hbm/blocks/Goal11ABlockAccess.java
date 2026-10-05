package com.hbm.blocks;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.List;

/** Reaches the protected DummyableBlock.fillSpace from the fixture (same package as the declaring class). */
public class Goal11ABlockAccess {
    /**
     * The server branch of production DummyableBlock.setPlacedBy for a player placing the block (as Goal10CBlockAccess):
     * the core goes getOffset() blocks back along the facing, then the block's fillSpace builds the dummies and extras.
     * Then, as Minecraft does when a block with a block entity is set, every placed position gets the block entity its
     * state asks for (newBlockEntity), so the extras are the proxies the production block creates. The item handling
     * and checkSpace/checkRequirement are not run.
     */
    public static BlockPos place(DummyableBlock block, Level level, BlockPos core, Direction dir) {
        BlockPos clicked = core.relative(dir, block.getOffset());
        int offset = -block.getOffset();
        BlockPos corePos = clicked.relative(dir, offset);
        int before = level.setBlocks.size();
        level.setBlock(corePos, block.createCoreState(dir), 3);
        block.fillSpace(level, clicked, dir, offset);
        List<BlockPos> placed = new ArrayList<>(new java.util.LinkedHashSet<>(level.setBlocks.subList(before, level.setBlocks.size())));
        for(BlockPos p : placed) {
            BlockState s = level.getBlockState(p);
            if(s.getBlock() != block) continue;
            BlockEntity be = block.newBlockEntity(p, s);
            if(be != null) level.put(be);
            else level.entities.remove(p);
        }
        return corePos;
    }

    /** The positions the production placement filled with the block (core, dummies, extras). */
    public static List<BlockPos> parts(DummyableBlock block, Level level) {
        List<BlockPos> out = new ArrayList<>();
        level.states.forEach((p, s) -> { if(s.getBlock() == block) out.add(p); });
        return out;
    }
}
