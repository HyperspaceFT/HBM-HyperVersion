package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;
import java.util.function.Supplier;

/** Original RBMKBlank / RBMKModerator / RBMKAbsorber / RBMKReflector: a column whose core holds the given block entity and nothing else. */
public class RBMKPassiveBlock extends RBMKBaseBlock {

    private final Supplier<? extends BlockEntityType<? extends RBMKBaseBlockEntity>> type;

    public RBMKPassiveBlock(Properties properties, Supplier<? extends BlockEntityType<? extends RBMKBaseBlockEntity>> type) {
        super(properties);
        this.type = type;
    }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        // As the original createNewTileEntity (meta >= offset): only the core has a block entity.
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return this.type.get().create(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    public static final MapCodec<RBMKPassiveBlock> CODEC = simpleCodec(properties -> new RBMKPassiveBlock(properties, NtmBlockEntityTypes.RBMK_BLANK));
    @Override protected MapCodec<RBMKPassiveBlock> codec() { return CODEC; }
}
