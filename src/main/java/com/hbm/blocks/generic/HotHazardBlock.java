package com.hbm.blocks.generic;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;

/**
 * The original BlockHotHazard (BlockHotHazard.java:11-46): a {@link HazardBlock} that steams in the rain and next to water.
 */
public class HotHazardBlock extends HazardBlock {

    public HotHazardBlock(ExtDisplayEffect extEffect, Properties properties) {
        super(extEffect, properties);
    }

    @Override
    @OnlyIn(Dist.CLIENT)
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        super.animateTick(state, level, pos, random);

        // 1.7.10 canLightningStrikeAt(x, y + 1, z)
        if(level.isRainingAt(pos.above())) {

            float ox = random.nextFloat();
            float oz = random.nextFloat();

            level.addParticle(ParticleTypes.CLOUD, pos.getX() + ox, pos.getY() + 1, pos.getZ() + oz, 0.0D, 0.0D, 0.0D);
        }

        for(Direction dir : Direction.values()) {

            if(dir == Direction.DOWN) continue;

            if(level.getFluidState(pos.relative(dir)).is(FluidTags.WATER)) {

                double ix = pos.getX() + 0.5F + dir.getStepX() + random.nextDouble() - 0.5D;
                double iy = pos.getY() + 0.5F + dir.getStepY() + random.nextDouble() - 0.5D;
                double iz = pos.getZ() + 0.5F + dir.getStepZ() + random.nextDouble() - 0.5D;

                if(dir.getStepX() != 0) ix = pos.getX() + 0.5F + dir.getStepX() * 0.5 + random.nextDouble() * 0.125 * dir.getStepX();
                if(dir.getStepY() != 0) iy = pos.getY() + 0.5F + dir.getStepY() * 0.5 + random.nextDouble() * 0.125 * dir.getStepY();
                if(dir.getStepZ() != 0) iz = pos.getZ() + 0.5F + dir.getStepZ() * 0.5 + random.nextDouble() * 0.125 * dir.getStepZ();

                level.addParticle(ParticleTypes.CLOUD, ix, iy, iz, 0.0, 0.0, 0.0);
            }
        }
    }
}
