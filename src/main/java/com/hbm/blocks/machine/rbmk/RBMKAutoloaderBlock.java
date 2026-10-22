package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKAutoloaderBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;

/**
 * Original RBMKAutoloader: a nine block tall column placed on top of a fuel channel, drawn by RenderRBMKAutoloader. Breaking it
 * drops the 18 slots once: DummyableBlock.onRemove drops through whichever block goes first (the proxies forward the core's
 * inventory), and Containers.dropItemStack empties the stacks while dropping them.
 */
public class RBMKAutoloaderBlock extends DummyableBlock {

    public static final MapCodec<RBMKAutoloaderBlock> CODEC = simpleCodec(RBMKAutoloaderBlock::new);

    public RBMKAutoloaderBlock(Properties properties) {
        super(properties);
        // Original :18-19: the thin piston shaft, then the loader head.
        this.bounding.add(new AABB(-0.125, 0, -0.125, 0.125, 4, 0.125));
        this.bounding.add(new AABB(-0.5, 4, -0.5, 0.5, 9, 0.5));
    }

    @Override public MapCodec<RBMKAutoloaderBlock> codec() { return CODEC; }
    @Override public int[] getDimensions() { return new int[] {8, 0, 0, 0, 0, 0}; }
    @Override public int getOffset() { return 0; }

    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return state.getValue(TYPE) == DummyBlockType.CORE
                ? new RBMKAutoloaderBlockEntity(pos, state) : new ProxyComboBlockEntity(pos, state).inventory();
    }

    // Both sides: the server moves the piston, the client interpolates it and plays the sounds and steam.
    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        return this.standardOpenBehavior(level, pos, player);
    }
}
