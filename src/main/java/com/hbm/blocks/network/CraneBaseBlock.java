package com.hbm.blocks.network;

import api.hbm.block.IToolable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.CraneBaseBlockEntity;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.items.tools.ConveyorWandItem;
import com.hbm.items.tools.ToolingItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.minecraft.world.phys.BlockHitResult;

import java.util.List;

/**
 * Original BlockCraneBase, shared by the conveyor cranes. The input and output sides both live in the block state (GOAL31 decision
 * 3); the output side is never the input side, so 30 of the 36 combinations occur. The original keeps the input in the metadata and
 * an overridden output in the tile entity (TileEntityCraneBase.java:42-49,100-110), and only uses the "overridden" flag to choose
 * textures, which here follow from whether the two sides are opposite.
 */
public abstract class CraneBaseBlock extends BaseEntityBlock implements IToolable, ITooltipProvider {

    public static final DirectionProperty INPUT = DirectionProperty.create("input");
    public static final DirectionProperty OUTPUT = DirectionProperty.create("output");

    public CraneBaseBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(INPUT, Direction.DOWN).setValue(OUTPUT, Direction.UP));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(INPUT, OUTPUT);
    }

    @Override
    protected RenderShape getRenderShape(BlockState state) {
        return RenderShape.MODEL;
    }

    /** Original :93-96: the input side faces the placer by BlockPistonBase.determineOrientation, the output side is opposite. */
    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        Direction input = context.getPlayer() == null ? context.getNearestLookingDirection().getOpposite() : determineOrientation(context.getClickedPos(), context.getPlayer());
        return this.defaultBlockState().setValue(INPUT, input).setValue(OUTPUT, input.getOpposite());
    }

    /**
     * 1.7.10 BlockPistonBase.determineOrientation: within two blocks horizontally, a placer whose eyes (feet + 1.82) are more than
     * two blocks above gets UP and one below the block gets DOWN; otherwise the horizontal side toward the placer. The original
     * subtracts in float, which rounds the placer's position a million blocks out; NEO subtracts in double.
     */
    public static Direction determineOrientation(BlockPos pos, LivingEntity placer) {
        if(Math.abs(placer.getX() - pos.getX()) < 2.0D && Math.abs(placer.getZ() - pos.getZ()) < 2.0D) {
            double eyes = placer.getY() + 1.82D;
            if(eyes - pos.getY() > 2.0D) return Direction.UP;
            if(pos.getY() - eyes > 0.0D) return Direction.DOWN;
        }

        return placer.getDirection().getOpposite();
    }

    @Override
    protected BlockState rotate(BlockState state, Rotation rotation) {
        return state.setValue(INPUT, rotation.rotate(state.getValue(INPUT))).setValue(OUTPUT, rotation.rotate(state.getValue(OUTPUT)));
    }

    @Override
    protected BlockState mirror(BlockState state, Mirror mirror) {
        return state.setValue(INPUT, mirror.mirror(state.getValue(INPUT))).setValue(OUTPUT, mirror.mirror(state.getValue(OUTPUT)));
    }

    public static Direction getInputSide(BlockState state) {
        return state.getValue(INPUT);
    }

    public static Direction getOutputSide(BlockState state) {
        return state.getValue(OUTPUT);
    }

    /**
     * TileEntityCraneBase.setOutputOverride (:55-65): clicking the current output side picks its opposite; when the new output lands
     * on the input side, the input moves to the old output side.
     */
    public static BlockState withOutput(BlockState state, Direction direction) {
        Direction input = state.getValue(INPUT);
        Direction oldOutput = state.getValue(OUTPUT);
        if(oldOutput == direction) direction = direction.getOpposite();

        if(direction == input) return state.setValue(INPUT, oldOutput).setValue(OUTPUT, direction);
        return state.setValue(OUTPUT, direction);
    }

    /**
     * TileEntityCraneBase.setInput (:67-78): clicking the current input side picks its opposite; when the new input lands on the
     * output side, the output moves to the old input side.
     */
    public static BlockState withInput(BlockState state, Direction direction) {
        Direction oldInput = state.getValue(INPUT);
        Direction output = state.getValue(OUTPUT);
        if(oldInput == direction) direction = direction.getOpposite();

        if(direction == output) return state.setValue(INPUT, direction).setValue(OUTPUT, oldInput);
        return state.setValue(INPUT, direction);
    }

    /** Original :99-116: only the screwdriver turns the crane; a plain click sets the input side, sneaking sets the output side. */
    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction side, ToolType tool) {
        if(tool != ToolType.SCREWDRIVER) return false;
        if(level.isClientSide) return true;

        BlockState state = level.getBlockState(pos);
        if(!(state.getBlock() instanceof CraneBaseBlock)) return false;

        level.setBlock(pos, player.isShiftKeyDown() ? withOutput(state, side) : withInput(state, side), 3);
        return true;
    }

    /**
     * Original :77-90: any tooling item (not only the screwdriver) and the conveyor wand go to the item, so the wand can start and
     * end a route on the crane's faces; neither opens the screen.
     */
    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {
        if(stack.getItem() instanceof ToolingItem || stack.getItem() instanceof ConveyorWandItem) return ItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;
        return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        if(player.isShiftKeyDown()) return InteractionResult.PASS;
        if(level.isClientSide) return InteractionResult.SUCCESS;

        if(level.getBlockEntity(pos) instanceof MenuProvider menu) {
            player.openMenu(new SimpleMenuProvider(menu, menu.getDisplayName()), pos);
        }

        return InteractionResult.CONSUME;
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(level.isClientSide) return null;
        return (lvl, pos, st, be) -> {
            if(be instanceof ITickable tickable) tickable.updateEntity();
        };
    }

    /**
     * Original dropContents (:271-311): each crane drops only its real slots, the range its block gives, never the phantom filter
     * slots.
     */
    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean movedByPiston) {
        if(!state.is(newState.getBlock()) && level.getBlockEntity(pos) instanceof CraneBaseBlockEntity crane) {
            int[] range = this.getDroppedSlots();

            for(int i = range[0]; i < range[1]; i++) {
                ItemStack stack = crane.getItem(i);
                if(!stack.isEmpty()) {
                    spawnDrop(level, pos, stack.copy());
                    crane.setItem(i, ItemStack.EMPTY);
                }
            }

            level.updateNeighbourForOutputSignal(pos, this);
        }

        super.onRemove(state, level, pos, newState, movedByPiston);
    }

    private static void spawnDrop(Level level, BlockPos pos, ItemStack stack) {
        double x = pos.getX() + level.random.nextFloat() * 0.8F + 0.1F;
        double y = pos.getY() + level.random.nextFloat() * 0.8F + 0.1F;
        double z = pos.getZ() + level.random.nextFloat() * 0.8F + 0.1F;

        while(!stack.isEmpty()) {
            ItemEntity item = new ItemEntity(level, x, y, z, stack.split(level.random.nextInt(21) + 10));
            item.setDeltaMovement(level.random.nextGaussian() * 0.05F, level.random.nextGaussian() * 0.05F + 0.2F, level.random.nextGaussian() * 0.05F);
            level.addFreshEntity(item);
        }
    }

    /** The slots dropped when the crane is removed, start inclusive and end exclusive. */
    protected abstract int[] getDroppedSlots();

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        this.addStandardInfo(tooltip);
    }
}
