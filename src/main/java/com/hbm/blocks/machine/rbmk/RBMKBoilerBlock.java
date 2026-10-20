package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBoilerBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/** Original RBMKBoiler: the steam channel rbmk_boiler. Unlike the control rods it takes a lid. */
public class RBMKBoilerBlock extends RBMKPipedBaseBlock {

    public static final MapCodec<RBMKBoilerBlock> CODEC = simpleCodec(RBMKBoilerBlock::new);

    public RBMKBoilerBlock(Properties properties) {
        super(properties);
    }

    @Override protected MapCodec<RBMKBoilerBlock> codec() { return CODEC; }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        // Original createNewTileEntity (:12-22): the extra block forwards fluids only (TileEntityProxyCombo(false, false, true)).
        return switch(state.getValue(TYPE)) {
            case CORE -> new RBMKBoilerBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid();
            default -> null;
        };
    }
}
