package com.hbm.blocks.generic;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

/**
 * The original BlockNetherCoal: an outgassing ore (carbon monoxide, see {@link OutgasBlock#getGas()}) that sets entities walking
 * on it on fire and shows flames and smoke on its exposed faces. The coal_infernal drop is in the block loot table.
 */
public class NetherCoalBlock extends OutgasBlock {

    public NetherCoalBlock(boolean randomTick, boolean onBreak, Properties properties) {
        super(randomTick, onBreak, properties);
    }

    // Original BlockNetherCoal.onEntityWalking: replaces the asbestos branch of BlockOutgas. 1.7.10 does not call it for a
    // sneaking player, so stepping carefully does not ignite here either.
    @Override
    public void stepOn(Level level, BlockPos pos, BlockState state, Entity entity) {
        if(!entity.isSteppingCarefully()) entity.igniteForSeconds(3);
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        super.animateTick(state, level, pos, random);

        for(Direction dir : Direction.values()) {

            if(dir == Direction.DOWN) continue;

            if(level.getBlockState(pos.relative(dir)).isAir()) {

                double ix = pos.getX() + 0.5F + dir.getStepX() + random.nextDouble() - 0.5D;
                double iy = pos.getY() + 0.5F + dir.getStepY() + random.nextDouble() - 0.5D;
                double iz = pos.getZ() + 0.5F + dir.getStepZ() + random.nextDouble() - 0.5D;

                if(dir.getStepX() != 0) ix = pos.getX() + 0.5F + dir.getStepX() * 0.5 + random.nextDouble() * 0.125 * dir.getStepX();
                if(dir.getStepY() != 0) iy = pos.getY() + 0.5F + dir.getStepY() * 0.5 + random.nextDouble() * 0.125 * dir.getStepY();
                if(dir.getStepZ() != 0) iz = pos.getZ() + 0.5F + dir.getStepZ() * 0.5 + random.nextDouble() * 0.125 * dir.getStepZ();

                level.addParticle(ParticleTypes.FLAME, ix, iy, iz, 0.0, 0.0, 0.0);
                level.addParticle(ParticleTypes.SMOKE, ix, iy, iz, 0.0, 0.0, 0.0);
                level.addParticle(ParticleTypes.SMOKE, ix, iy, iz, 0.0, 0.1, 0.0);
            }
        }
    }
}
