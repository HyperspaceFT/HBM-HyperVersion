package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.MachineWasteDrumBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.*;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;

/** Spent fuel pool drum (original WasteDrum.java): cools hot nuclear waste while it is next to water. */
public class MachineWasteDrumBlock extends BaseEntityBlock {

    public MachineWasteDrumBlock(Properties properties) {
        super(properties);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new MachineWasteDrumBlockEntity(pos, state);
    }

    // The original updateEntity only worked on the server, so the client gets no ticker.
    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(level.isClientSide) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected RenderShape getRenderShape(BlockState state) {
        return RenderShape.MODEL;
    }

    public static final MapCodec<MachineWasteDrumBlock> CODEC = simpleCodec(MachineWasteDrumBlock::new);
    public MapCodec<MachineWasteDrumBlock> codec() { return CODEC; }

    /** Original randomDisplayTick (:61-86): bubbles rise from every water neighbour except the one below. */
    @Override
    @OnlyIn(Dist.CLIENT)
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        super.animateTick(state, level, pos, random);

        for(Direction dir : Direction.values()) {
            if(dir == Direction.DOWN) continue;
            if(!level.getFluidState(pos.relative(dir)).is(FluidTags.WATER)) continue;

            double ix = pos.getX() + 0.5D + dir.getStepX() + random.nextDouble() - 0.5D;
            double iy = pos.getY() + 0.5D + dir.getStepY() + random.nextDouble() - 0.5D;
            double iz = pos.getZ() + 0.5D + dir.getStepZ() + random.nextDouble() - 0.5D;

            if(dir.getStepX() != 0) ix = pos.getX() + 0.5D + dir.getStepX() * 0.5D + random.nextDouble() * 0.125D * dir.getStepX();
            if(dir.getStepY() != 0) iy = pos.getY() + 0.5D + dir.getStepY() * 0.5D + random.nextDouble() * 0.125D * dir.getStepY();
            if(dir.getStepZ() != 0) iz = pos.getZ() + 0.5D + dir.getStepZ() * 0.5D + random.nextDouble() * 0.125D * dir.getStepZ();

            level.addParticle(ParticleTypes.BUBBLE, ix, iy, iz, 0.0D, 0.2D, 0.0D);
        }
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(!state.is(newState.getBlock())) {

            // Drop inventory contents
            BlockEntity be = level.getBlockEntity(pos);
            if(be instanceof Container container) {
                Containers.dropContents(level, pos, container);

                super.onRemove(state, level, pos, newState, isMoving);
                level.updateNeighbourForOutputSignal(pos, this);
            } else {
                super.onRemove(state, level, pos, newState, isMoving);
            }
        }
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        if(level.isClientSide) return InteractionResult.SUCCESS;

        if(!player.isShiftKeyDown()) {
            BlockEntity be = level.getBlockEntity(pos);
            if(be instanceof MenuProvider menu) player.openMenu(new SimpleMenuProvider(menu, menu.getDisplayName()), pos);
            return InteractionResult.CONSUME;
        }

        return InteractionResult.SUCCESS;
    }
}
