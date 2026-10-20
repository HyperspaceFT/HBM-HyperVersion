package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity;
import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/**
 * Original RBMKControl: the manual control rods, plain (rbmk_control) or moderated (rbmk_control_mod). The ReaSim variant
 * rbmk_control_reasim and its bottom texture are not migrated (Goal 26).
 */
public class RBMKControlBlock extends RBMKPipedBaseBlock {

    public static final MapCodec<RBMKControlBlock> CODEC = RecordCodecBuilder.mapCodec(instance -> instance.group(
            propertiesCodec(),
            Codec.BOOL.fieldOf("moderated").forGetter(block -> block.moderated)
    ).apply(instance, RBMKControlBlock::new));

    public final boolean moderated;

    public RBMKControlBlock(Properties properties, boolean moderated) {
        super(properties);
        this.moderated = moderated;
    }

    @Override protected MapCodec<RBMKControlBlock> codec() { return CODEC; }

    @Override
    protected boolean hasOwnLid() {
        return true;
    }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        // Original createNewTileEntity (:41-46): the extra block is a plain `new TileEntityProxyCombo()`, which only forwards RoR.
        return switch(state.getValue(TYPE)) {
            case CORE -> new RBMKControlManualBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state);
            default -> null;
        };
    }
}
