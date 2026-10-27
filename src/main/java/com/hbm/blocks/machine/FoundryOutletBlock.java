package com.hbm.blocks.machine;

import api.hbm.block.ICrucibleAcceptor;
import api.hbm.block.IToolable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.FoundryOutletBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.material.Mats;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
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
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * Upstream FoundryOutlet. FACING replaces the direction metadata. CLOSED and FILTERED only pick the lock and filter overlays of the
 * model; the server keeps them in sync with the block entity (see FoundryOutletBlockEntity.updateBlockState), the transfer logic
 * reads the block entity and the live redstone signal.
 */
public class FoundryOutletBlock extends BaseEntityBlock implements ICrucibleAcceptor, ILookOverlay, IToolable {
    public static final MapCodec<FoundryOutletBlock> CODEC = simpleCodec(FoundryOutletBlock::new);
    public static final DirectionProperty FACING = BlockStateProperties.HORIZONTAL_FACING;
    public static final BooleanProperty CLOSED = BooleanProperty.create("closed");
    public static final BooleanProperty FILTERED = BooleanProperty.create("filtered");

    // the trough sits at the back edge, opposite to FACING
    private static final VoxelShape SHAPE_NORTH = box(5, 0, 10, 11, 8, 16);
    private static final VoxelShape SHAPE_SOUTH = box(5, 0, 0, 11, 8, 6);
    private static final VoxelShape SHAPE_WEST = box(10, 0, 5, 16, 8, 11);
    private static final VoxelShape SHAPE_EAST = box(0, 0, 5, 6, 8, 11);

    public FoundryOutletBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.NORTH).setValue(CLOSED, false).setValue(FILTERED, false));
    }

    @Override public MapCodec<FoundryOutletBlock> codec() { return CODEC; }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new FoundryOutletBlockEntity(pos, state); }
    @Override protected RenderShape getRenderShape(BlockState state) { return RenderShape.MODEL; }
    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, CLOSED, FILTERED);
    }

    /**
     * Upstream onBlockPlacedBy maps the yaw quadrant 0 (looking south) to meta 2 (NORTH), 1 (west) to 5 (EAST), 2 (north) to 3 (SOUTH)
     * and 3 (east) to 4 (WEST): the outlet faces the placing player, which is the opposite of the look direction.
     */
    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.defaultBlockState().setValue(FACING, context.getHorizontalDirection().getOpposite())
                .setValue(CLOSED, context.getLevel().hasNeighborSignal(context.getClickedPos()));
    }

    @Override
    public void setPlacedBy(Level level, BlockPos pos, BlockState state, LivingEntity placer, ItemStack stack) {
        super.setPlacedBy(level, pos, state, placer, stack);
        if(level.getBlockEntity(pos) instanceof FoundryOutletBlockEntity outlet) outlet.updateBlockState();
    }

    @Override
    protected void neighborChanged(BlockState state, Level level, BlockPos pos, Block block, BlockPos fromPos, boolean isMoving) {
        super.neighborChanged(state, level, pos, block, fromPos, isMoving);
        if(!level.isClientSide && level.getBlockEntity(pos) instanceof FoundryOutletBlockEntity outlet) outlet.updateBlockState();
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return switch(state.getValue(FACING)) {
            case SOUTH -> SHAPE_SOUTH;
            case WEST -> SHAPE_WEST;
            case EAST -> SHAPE_EAST;
            default -> SHAPE_NORTH;
        };
    }

    /** Upstream onBlockActivated: not sneaking, scraps set the filter and anything else toggles the redstone inversion. */
    private void interact(Level level, BlockPos pos, Player player, ItemStack held) {
        if(level.isClientSide || player.isShiftKeyDown()) return;
        if(!(level.getBlockEntity(pos) instanceof FoundryOutletBlockEntity outlet)) return;

        if(held.is(NtmItems.SCRAPS.get())) {
            Mats.MaterialStack mat = CopperScrapsItem.getMats(held);
            if(mat != null) {
                outlet.filter = mat.material;
            }
        } else {
            outlet.invertRedstone = !outlet.invertRedstone;
        }
        outlet.setChanged();
        outlet.updateBlockState();
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        this.interact(level, pos, player, stack);
        return ItemInteractionResult.sidedSuccess(level.isClientSide);
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        this.interact(level, pos, player, ItemStack.EMPTY);
        return InteractionResult.sidedSuccess(level.isClientSide);
    }

    /**
     * Upstream onScrew: the screwdriver clears the filter and its inversion, the hand drill toggles the inversion. Both return false on
     * the server like upstream, so the tool is not worn; the client returns true.
     */
    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool) {

        if(tool == ToolType.SCREWDRIVER) {
            if(level.isClientSide) return true;

            if(level.getBlockEntity(pos) instanceof FoundryOutletBlockEntity outlet) {
                outlet.filter = null;
                outlet.invertFilter = false;
                outlet.setChanged();
                outlet.updateBlockState();
            }
        }

        if(tool == ToolType.HAND_DRILL) {
            if(level.isClientSide) return true;

            if(level.getBlockEntity(pos) instanceof FoundryOutletBlockEntity outlet) {
                outlet.invertFilter = !outlet.invertFilter;
                outlet.setChanged();
                outlet.updateBlockState();
            }
        }

        return false;
    }

    @Override public boolean canAcceptPartialPour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) { return false; }
    @Override public Mats.MaterialStack pour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) { return stack; }

    @Override
    public boolean canAcceptPartialFlow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc && acc.canAcceptPartialFlow(level, pos, side, stack);
    }

    @Override
    public Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc ? acc.flow(level, pos, side, stack) : stack;
    }

    @Override @OnlyIn(Dist.CLIENT)
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        if(!(level.getBlockEntity(pos) instanceof FoundryOutletBlockEntity outlet)) return;
        List<Component> text = new ArrayList<>();

        if(outlet.filter != null) {
            text.add(Component.translatable("foundry.filter", outlet.filter.getName()).withStyle(ChatFormatting.YELLOW));
        }
        if(outlet.invertFilter) {
            text.add(Component.translatable("foundry.invertFilter").withStyle(ChatFormatting.YELLOW));
        }
        if(outlet.invertRedstone) {
            text.add(Component.translatable("foundry.inverted").withStyle(ChatFormatting.DARK_RED));
        }

        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xFF4000, 0x401000, text);
    }
}
