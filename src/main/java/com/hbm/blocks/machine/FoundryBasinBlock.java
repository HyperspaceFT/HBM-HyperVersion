package com.hbm.blocks.machine;

import com.hbm.blockentity.machine.FoundryBasinBlockEntity;
import com.hbm.inventory.material.Mats;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * Upstream FoundryBasin (FoundryBasin.java:21-102): the large molds; takes pours from above and refuses flows. Upstream's selection box
 * stops at 0.999 to work around 1.7.10 item collisions; NEO selects the full block.
 */
public class FoundryBasinBlock extends FoundryCastingBlock {
    public static final MapCodec<FoundryBasinBlock> CODEC = simpleCodec(FoundryBasinBlock::new);
    /** Upstream addCollisionBoxesToList: the 2 px floor and four 2 px walls to full height. */
    private static final VoxelShape COLLISION = Shapes.or(box(0, 0, 0, 16, 2, 16),
            box(0, 0, 0, 16, 16, 2), box(0, 0, 0, 2, 16, 16),
            box(14, 0, 0, 16, 16, 16), box(0, 0, 14, 16, 16, 16));

    public FoundryBasinBlock(Properties properties) { super(properties); }
    @Override public MapCodec<FoundryBasinBlock> codec() { return CODEC; }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new FoundryBasinBlockEntity(pos, state); }
    @Override protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) { return Shapes.block(); }
    @Override protected VoxelShape getCollisionShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) { return COLLISION; }

    @Override public boolean canAcceptPartialFlow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) { return false; }
    @Override public Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) { return stack; }
}
