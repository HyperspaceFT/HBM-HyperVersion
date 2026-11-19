package com.hbm.blocks.generic;

import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.hbm.main.NuclearTechModClient;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;

public class HazardBlock extends Block {

    // Set only when a block is placed, as in the original (BlockHazard.java:120-146): after a restart the saved update
    // finds 0, adds nothing and schedules no next one, so a block placed before the restart is silent until placed again.
    protected float rad = 0.0F;

    private final ExtDisplayEffect extEffect;

    public HazardBlock(Properties properties) {
        this(null, properties);
    }

    public HazardBlock(ExtDisplayEffect extEffect, Properties properties) {
        super(properties);
        this.extEffect = extEffect;
    }

    @Override
    public void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        if(this.rad > 0) {
            ChunkRadiationManager.proxy.incrementRad(level, pos, rad);
            level.scheduleTick(pos, this, 20);
        }
    }

    @Override
    public void onPlace(BlockState state, Level level, BlockPos pos, BlockState oldState, boolean isMoving) {
        rad = HazardSystem.getHazardLevelFromStack(new ItemStack(this), HazardRegistry.RADIATION) * 0.1F;
        if(this.rad > 0) {
            level.scheduleTick(pos, this, 20);
        }
    }

    // Original BlockHazard.randomDisplayTick and sPart (BlockHazard.java:45-108): one particle next to every air neighbour.
    @Override
    @OnlyIn(Dist.CLIENT)
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        super.animateTick(state, level, pos, random);

        if(extEffect == null) return;

        for(Direction dir : Direction.values()) {

            if(!level.getBlockState(pos.relative(dir)).isAir()) continue;

            double ix = pos.getX() + 0.5F + dir.getStepX() + random.nextDouble() * 3 - 1.5D;
            double iy = pos.getY() + 0.5F + dir.getStepY() + random.nextDouble() * 3 - 1.5D;
            double iz = pos.getZ() + 0.5F + dir.getStepZ() + random.nextDouble() * 3 - 1.5D;

            if(dir.getStepX() != 0) ix = pos.getX() + 0.5F + dir.getStepX() * 0.5 + random.nextDouble() * dir.getStepX();
            if(dir.getStepY() != 0) iy = pos.getY() + 0.5F + dir.getStepY() * 0.5 + random.nextDouble() * dir.getStepY();
            if(dir.getStepZ() != 0) iz = pos.getZ() + 0.5F + dir.getStepZ() * 0.5 + random.nextDouble() * dir.getStepZ();

            if(extEffect == ExtDisplayEffect.RADFOG) {
                // 1.7.10 "townaura"
                level.addParticle(ParticleTypes.MYCELIUM, ix, iy, iz, 0.0, 0.0, 0.0);
            }
            if(extEffect == ExtDisplayEffect.SCHRAB) {
                CompoundTag tag = new CompoundTag();
                tag.putString("type", "schrabfog");
                tag.putDouble("posX", ix);
                tag.putDouble("posY", iy);
                tag.putDouble("posZ", iz);
                NuclearTechModClient.effectNT(tag);
            }
        }
    }

    public enum ExtDisplayEffect {
        RADFOG,
        SCHRAB
    }
}
