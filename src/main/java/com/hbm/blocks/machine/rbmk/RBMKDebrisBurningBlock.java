package com.hbm.blocks.machine.rbmk;

import com.hbm.blocks.NtmBlocks;
import com.hbm.particle.NtmParticleTypes;
import com.hbm.particle.vanilla.NbtParticleOptions;
import com.hbm.util.SoundUtils;
import com.hbm.util.particle.ParticleUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Original RBMKDebrisBurning: burning wreckage that works on scheduled block ticks every 100 to 119 ticks (tickRate, :21-24),
 * spreads meltdown gas into the air around it and goes out after a while, faster next to foam.
 */
public class RBMKDebrisBurningBlock extends RBMKDebrisBlock {

    public RBMKDebrisBurningBlock(Properties properties) {
        super(properties);
    }

    /** Original tickRate. */
    protected int tickDelay(RandomSource random) {
        return 100 + random.nextInt(20);
    }

    /** The rbmkflame particle the original sends with maxAge 300 to players within 75 blocks. */
    protected static void sendFlame(Level level, double x, double y, double z) {
        CompoundTag tag = new CompoundTag();
        tag.putInt("lifetime", 300);
        ParticleUtil.addParticle(level, new NbtParticleOptions(NtmParticleTypes.RBMK_FLAME.get(), tag), x, y, z, 75);
    }

    protected static void playFire(Level level, BlockPos pos, RandomSource random) {
        SoundUtils.playAtVec3(level, Vec3.atCenterOf(pos), SoundEvents.FIRE_AMBIENT, SoundSource.BLOCKS, 1.0F + random.nextFloat(), random.nextFloat() * 0.7F + 0.3F);
    }

    /** Original updateTick (:26-58). */
    @Override
    protected void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {

        if(random.nextInt(5) == 0) {
            sendFlame(level, pos.getX() + 0.25 + random.nextDouble() * 0.5, pos.getY() + 1.75, pos.getZ() + 0.25 + random.nextDouble() * 0.5);
            playFire(level, pos, random);
        }

        BlockPos side = pos.relative(Direction.from3DDataValue(random.nextInt(6)));
        BlockState sideState = level.getBlockState(side);

        if(random.nextInt(10) == 0 && sideState.isAir()) {
            level.setBlock(side, NtmBlocks.GAS_MELTDOWN.get().defaultBlockState(), 3);
        }

        //Foam helps stop the fire; Boron smothers it. 1.66% chance every 100-120 seconds for one side
        // foam_layer, sand_boron_layer and boron sand_mix are not in NEO yet (deferred with the foam tools and boron sand); only block_foam counts.
        int chance = sideState.is(NtmBlocks.BLOCK_FOAM.get()) ? 10 : 100;

        if(random.nextInt(chance) == 0) {
            level.setBlock(pos, NtmBlocks.PRIBRIS.get().defaultBlockState(), 3);
        } else {
            level.scheduleTick(pos, this, this.tickDelay(level.random));
        }
    }

    /** Original onBlockAdded (:60-74). A same-block state change (the radiating counter) is no new placement. */
    @Override
    protected void onPlace(BlockState state, Level level, BlockPos pos, BlockState oldState, boolean movedByPiston) {
        super.onPlace(state, level, pos, oldState, movedByPiston);
        if(oldState.is(state.getBlock())) return;

        if(!level.isClientSide) {
            if(level.random.nextInt(3) == 0) {
                sendFlame(level, pos.getX() + 0.25 + level.random.nextDouble() * 0.5, pos.getY() + 1.75, pos.getZ() + 0.25 + level.random.nextDouble() * 0.5);
            }
        }

        level.scheduleTick(pos, this, this.tickDelay(level.random));
    }
}
