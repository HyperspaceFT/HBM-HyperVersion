package com.hbm.blocks.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Coated red copper cable (original WireCoated.java:17-46): a full-block red copper cable. The original draws it with connected
 * textures (IBlockCT); NEO has no connected-texture renderer, so every face shows the plain red_wire_coated texture.
 */
public class WireCoatedBlock extends Block implements EntityBlock {

    public WireCoatedBlock(Properties properties) {
        super(properties);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CableBaseBlockEntity(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }
}
