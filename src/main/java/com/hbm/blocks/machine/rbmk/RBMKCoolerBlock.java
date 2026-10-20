package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKCoolerBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/** Original RBMKCooler: a plain column (no pipe stubs, no GUI) rendered like the passive columns, with a lid. */
public class RBMKCoolerBlock extends RBMKBaseBlock {

    public static final MapCodec<RBMKCoolerBlock> CODEC = simpleCodec(RBMKCoolerBlock::new);

    public RBMKCoolerBlock(Properties properties) {
        super(properties);
    }

    @Override protected MapCodec<RBMKCoolerBlock> codec() { return CODEC; }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        // Original createNewTileEntity (:11-16): the extra block forwards fluids (TileEntityProxyCombo().fluid()).
        return switch(state.getValue(TYPE)) {
            case CORE -> new RBMKCoolerBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }
}
