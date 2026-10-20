package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKHeaterBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/** Original RBMKHeater: the fluid heater rbmk_heater. Unlike the control rods it takes a lid. */
public class RBMKHeaterBlock extends RBMKPipedBaseBlock {

    public static final MapCodec<RBMKHeaterBlock> CODEC = simpleCodec(RBMKHeaterBlock::new);

    public RBMKHeaterBlock(Properties properties) {
        super(properties);
    }

    @Override protected MapCodec<RBMKHeaterBlock> codec() { return CODEC; }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        // Original createNewTileEntity (:12-22): the extra block forwards fluids only (TileEntityProxyCombo(false, false, true)).
        return switch(state.getValue(TYPE)) {
            case CORE -> new RBMKHeaterBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid();
            default -> null;
        };
    }
}
