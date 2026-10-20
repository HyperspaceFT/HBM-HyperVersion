package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.machine.rbmk.RBMKControlAutoBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/**
 * Original RBMKControlAuto: the automatic control rods rbmk_control_auto. The ReaSim variant rbmk_control_reasim_auto and its bottom
 * texture are not migrated (Goal 26).
 */
public class RBMKControlAutoBlock extends RBMKPipedBaseBlock {

    public static final MapCodec<RBMKControlAutoBlock> CODEC = simpleCodec(RBMKControlAutoBlock::new);

    public RBMKControlAutoBlock(Properties properties) {
        super(properties);
    }

    @Override protected MapCodec<RBMKControlAutoBlock> codec() { return CODEC; }

    @Override
    protected boolean hasOwnLid() {
        return true;
    }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        // Original createNewTileEntity (:34-38): only the core has a block entity, the extra block has no proxy.
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return new RBMKControlAutoBlockEntity(pos, state);
    }
}
