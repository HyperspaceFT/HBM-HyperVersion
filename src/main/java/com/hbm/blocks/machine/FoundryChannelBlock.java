package com.hbm.blocks.machine;

import api.hbm.block.ICrucibleAcceptor;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.FoundryChannelBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.material.Mats;
import com.hbm.items.CopperScrapsItem;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * Upstream FoundryChannel. The four connection properties replace upstream's per-render canConnectTo lookups; they drive the
 * multipart model, the shape and the molten-metal renderer.
 */
public class FoundryChannelBlock extends BaseEntityBlock implements ICrucibleAcceptor {
    public static final MapCodec<FoundryChannelBlock> CODEC = simpleCodec(FoundryChannelBlock::new);
    public static final BooleanProperty NORTH = BlockStateProperties.NORTH;
    public static final BooleanProperty EAST = BlockStateProperties.EAST;
    public static final BooleanProperty SOUTH = BlockStateProperties.SOUTH;
    public static final BooleanProperty WEST = BlockStateProperties.WEST;

    private static final VoxelShape CENTER = box(5, 0, 5, 11, 8, 11);
    private static final VoxelShape ARM_NORTH = box(5, 0, 0, 11, 8, 5);
    private static final VoxelShape ARM_EAST = box(11, 0, 5, 16, 8, 11);
    private static final VoxelShape ARM_SOUTH = box(5, 0, 11, 11, 8, 16);
    private static final VoxelShape ARM_WEST = box(0, 0, 5, 5, 8, 11);
    private static final VoxelShape[] SHAPES = new VoxelShape[16];

    static {
        for(int i = 0; i < 16; i++) {
            VoxelShape shape = CENTER;
            if((i & 1) != 0) shape = Shapes.or(shape, ARM_NORTH);
            if((i & 2) != 0) shape = Shapes.or(shape, ARM_EAST);
            if((i & 4) != 0) shape = Shapes.or(shape, ARM_SOUTH);
            if((i & 8) != 0) shape = Shapes.or(shape, ARM_WEST);
            SHAPES[i] = shape;
        }
    }

    public FoundryChannelBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(NORTH, false).setValue(EAST, false).setValue(SOUTH, false).setValue(WEST, false));
    }

    @Override public MapCodec<FoundryChannelBlock> codec() { return CODEC; }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new FoundryChannelBlockEntity(pos, state); }
    @Override protected RenderShape getRenderShape(BlockState state) { return RenderShape.MODEL; }
    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(NORTH, EAST, SOUTH, WEST);
    }

    public static BooleanProperty getProperty(Direction dir) {
        return switch(dir) {
            case NORTH -> NORTH;
            case EAST -> EAST;
            case SOUTH -> SOUTH;
            case WEST -> WEST;
            default -> null;
        };
    }

    /** Upstream canConnectTo: channels, foundry_mold, and outlets facing away from this channel. The slag tap is not ported. */
    public static boolean canConnectTo(BlockGetter level, BlockPos pos, Direction dir) {
        if(dir.getAxis() == Direction.Axis.Y) return false;
        BlockState state = level.getBlockState(pos.relative(dir));
        if(state.is(NtmBlocks.FOUNDRY_OUTLET.get()) && state.getValue(FoundryOutletBlock.FACING) == dir) return true;
        return state.is(NtmBlocks.FOUNDRY_CHANNEL.get()) || state.is(NtmBlocks.FOUNDRY_MOLD.get());
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        BlockState state = this.defaultBlockState();
        for(Direction dir : Direction.Plane.HORIZONTAL) {
            state = state.setValue(getProperty(dir), canConnectTo(context.getLevel(), context.getClickedPos(), dir));
        }
        return state;
    }

    @Override
    protected BlockState updateShape(BlockState state, Direction direction, BlockState neighborState, LevelAccessor level, BlockPos pos, BlockPos neighborPos) {
        if(direction.getAxis().isHorizontal()) {
            return state.setValue(getProperty(direction), canConnectTo(level, pos, direction));
        }
        return super.updateShape(state, direction, neighborState, level, pos, neighborPos);
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        int index = (state.getValue(NORTH) ? 1 : 0) | (state.getValue(EAST) ? 2 : 0) | (state.getValue(SOUTH) ? 4 : 0) | (state.getValue(WEST) ? 8 : 0);
        return SHAPES[index];
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        // upstream consumes any shovel click, also on an empty channel
        if(!stack.is(ItemTags.SHOVELS)) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        if(!level.isClientSide && level.getBlockEntity(pos) instanceof FoundryChannelBlockEntity channel && channel.amount > 0) {
            ItemStack scrap = CopperScrapsItem.create(channel.takeContents());
            if(!scrap.isEmpty() && !player.getInventory().add(scrap)) player.drop(scrap, false);
        }
        return ItemInteractionResult.sidedSuccess(level.isClientSide);
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean moving) {
        if(!state.is(newState.getBlock()) && !level.isClientSide
                && level.getBlockEntity(pos) instanceof FoundryChannelBlockEntity channel && channel.amount > 0) {
            popResource(level, pos, CopperScrapsItem.create(channel.takeContents()));
        }
        super.onRemove(state, level, pos, newState, moving);
    }

    @Override
    public boolean canAcceptPartialPour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc && acc.canAcceptPartialPour(level, pos, hit, side, stack);
    }

    @Override
    public Mats.MaterialStack pour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc ? acc.pour(level, pos, hit, side, stack) : stack;
    }

    @Override
    public boolean canAcceptPartialFlow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc && acc.canAcceptPartialFlow(level, pos, side, stack);
    }

    @Override
    public Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc ? acc.flow(level, pos, side, stack) : stack;
    }
}
