package com.hbm.blocks.generic;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.IntegerProperty;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/** Ordinary steel grate only; the wide grate's item/XP pass-through is not part of this block. */
public class SteelGrateBlock extends Block {

    // Retain original metadata: 0..8 are their height steps; 9 is the step below the logical block.
    public static final IntegerProperty HEIGHT = IntegerProperty.create("height", 0, 9);
    private static final VoxelShape[] SHAPES = new VoxelShape[10];

    static {
        for(int value = 0; value <= 9; value++) {
            int height = value == 9 ? -1 : value;
            SHAPES[value] = Block.box(0, height * 2, 0, 16, height * 2 + 2, 16);
        }
    }

    public SteelGrateBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(HEIGHT, 0));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(HEIGHT);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        Direction face = context.getClickedFace();
        double hitY = context.getClickLocation().y - context.getClickedPos().getY();
        int height = face == Direction.DOWN ? 7 : face == Direction.UP ? 0 : (int)Math.floor(hitY * 8D);
        // Side hits at exactly Y=1 produced metadata 8 in the original.
        height = Math.max(0, Math.min(8, height));
        if(context.getPlayer() != null && context.getPlayer().isShiftKeyDown()) {
            BlockPos pos = context.getClickedPos();
            if(height == 0 && !context.getLevel().getBlockState(pos.below()).isAir()
                    && hasOffsetClearance(context.getLevel(), pos, -1)) {
                height = -1;
            } else if(height == 7 && !context.getLevel().getBlockState(pos.above()).isAir()
                    && hasOffsetClearance(context.getLevel(), pos, 8)) {
                height = 8;
            }
        }
        return this.defaultBlockState().setValue(HEIGHT, height == -1 ? 9 : height);
    }

    private static boolean hasOffsetClearance(BlockGetter level, BlockPos pos, int height) {
        BlockPos neighbor = height == -1 ? pos.below() : pos.above();
        VoxelShape collision = level.getBlockState(neighbor).getCollisionShape(level, neighbor);
        if(collision.isEmpty()) return true;
        // Preserve the original strict 0.05 threshold, rather than silently requiring a whole 1/8 gap.
        return height == -1 ? collision.max(Direction.Axis.Y) < 0.95D : collision.min(Direction.Axis.Y) > 0.05D;
    }

    @Override
    public void neighborChanged(BlockState state, Level level, BlockPos pos, Block block, BlockPos fromPos, boolean moving) {
        if(level.isClientSide) return;
        int height = state.getValue(HEIGHT);
        if(height == 9) height = -1;
        if((height == -1 || height == 8) && !hasOffsetClearance(level, pos, height)) {
            level.destroyBlock(pos, true);
        }
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return SHAPES[state.getValue(HEIGHT)];
    }

    @Override
    protected VoxelShape getCollisionShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return SHAPES[state.getValue(HEIGHT)];
    }

    @Override
    protected VoxelShape getBlockSupportShape(BlockState state, BlockGetter level, BlockPos pos) {
        int height = state.getValue(HEIGHT);
        // Only the bottom grate's DOWN face and the top grate's UP face are boundary support faces.
        return height == 0 || height == 7 ? SHAPES[height] : Shapes.empty();
    }
}
