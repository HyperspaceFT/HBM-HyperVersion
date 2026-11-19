package com.hbm.blocks.machine;

import com.hbm.blockentity.machine.FoundryMoldBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/** Upstream FoundryMold (shallow foundry basin): the small molds; interaction and crucible acceptance in {@link FoundryCastingBlock}. */
public class FoundryMoldBlock extends FoundryCastingBlock {
    public static final MapCodec<FoundryMoldBlock> CODEC = simpleCodec(FoundryMoldBlock::new);
    private static final VoxelShape SHAPE = Shapes.or(box(0, 0, 0, 16, 2, 16),
            box(0, 0, 0, 16, 8, 2), box(0, 0, 14, 16, 8, 16),
            box(0, 0, 2, 2, 8, 14), box(14, 0, 2, 16, 8, 14));

    private static final VoxelShape OUTLINE = box(0, 0, 0, 16, 8, 16);

    public FoundryMoldBlock(Properties properties) { super(properties); }
    @Override public MapCodec<FoundryMoldBlock> codec() { return CODEC; }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new FoundryMoldBlockEntity(pos, state); }
    // ORIG FoundryMold.java:47-78: the hollow basin is the collision only, the block and selection bounds are the solid box
    @Override protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) { return OUTLINE; }
    @Override protected VoxelShape getCollisionShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) { return SHAPE; }
}
