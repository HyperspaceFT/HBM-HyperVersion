package com.hbm.blocks.generic;

import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

/**
 * The original BlockSmolder (smoldering netherrack): sets entities walking on it on fire and shows lava and flame particles when
 * the block above is air. The powder_fire drop is in the block loot table.
 */
public class SmolderBlock extends Block {

    public SmolderBlock(Properties properties) {
        super(properties);
    }

    // Original BlockSmolder.onEntityWalking; 1.7.10 does not call it for a sneaking player, so stepping carefully does not ignite.
    @Override
    public void stepOn(Level level, BlockPos pos, BlockState state, Entity entity) {
        if(!entity.isSteppingCarefully()) entity.igniteForSeconds(3);
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        super.animateTick(state, level, pos, random);

        if(level.getBlockState(pos.above()).isAir()) {
            level.addParticle(ParticleTypes.LAVA, pos.getX() + 0.25 + random.nextDouble() * 0.5, pos.getY() + 1.1, pos.getZ() + 0.25 + random.nextDouble() * 0.5, 0.0, 0.0, 0.0);
            level.addParticle(ParticleTypes.FLAME, pos.getX() + 0.25 + random.nextDouble() * 0.5, pos.getY() + 1.1, pos.getZ() + 0.25 + random.nextDouble() * 0.5, 0.0, 0.0, 0.0);
        }
    }
}
