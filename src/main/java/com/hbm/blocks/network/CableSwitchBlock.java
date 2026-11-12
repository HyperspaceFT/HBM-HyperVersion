package com.hbm.blocks.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.CableSwitchBlockEntity;
import com.hbm.registry.NtmSoundEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.phys.BlockHitResult;

/** Power switch (original CableSwitch.java:15-66): right-click toggles it; only while ENABLED does it carry power. */
public class CableSwitchBlock extends Block implements EntityBlock {

    public static final BooleanProperty ENABLED = BlockStateProperties.ENABLED;

    public CableSwitchBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(ENABLED, false));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(ENABLED);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CableSwitchBlockEntity(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        if(level.isClientSide) return InteractionResult.SUCCESS;
        if(player.isShiftKeyDown()) return InteractionResult.PASS;

        setEnabled(level, pos, state, !state.getValue(ENABLED));
        if(level.getBlockEntity(pos) instanceof CableSwitchBlockEntity sw) sw.updateState();
        return InteractionResult.CONSUME;
    }

    /**
     * Sets ENABLED without notifying neighbours (original setBlockMetadataWithNotify flag 2) and plays the original's
     * "hbm:block.reactorStart" (NEO hbmsntm:block.reactor_start, lowercase as 1.21 requires) at the block's corner, pitch 1.0 when switching on and 0.85 when switching off.
     */
    public static void setEnabled(Level level, BlockPos pos, BlockState state, boolean on) {
        level.setBlock(pos, state.setValue(ENABLED, on), Block.UPDATE_CLIENTS);
        level.playSound(null, pos.getX(), pos.getY(), pos.getZ(), NtmSoundEvents.REACTOR_START.get(), SoundSource.BLOCKS, 1.0F, on ? 1.0F : 0.85F);
    }
}
