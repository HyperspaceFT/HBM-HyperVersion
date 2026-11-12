package com.hbm.blocks.network;

import api.hbm.block.IToolable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.CablePaintableBlockEntity;
import com.hbm.blockentity.network.IPaintableBlockEntity;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.blocks.states.NtmBlockStateProperties;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.phys.BlockHitResult;

import java.util.List;

/**
 * Paintable red copper cable (original BlockCablePaintable.java:32-134): right-click with a solid block to paint it, a screwdriver
 * clears the paint and a defuser hides the port overlay of a painted cable (original metadata 1, here HIDE_OVERLAY).
 */
public class CablePaintableBlock extends Block implements EntityBlock, IToolable, ITooltipProvider {

    public static final BooleanProperty HIDE_OVERLAY = NtmBlockStateProperties.HIDE_OVERLAY;

    public CablePaintableBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(HIDE_OVERLAY, false));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(HIDE_OVERLAY);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CablePaintableBlockEntity(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        ItemInteractionResult paint = paint(this, stack, level, pos);
        return paint != null ? paint : super.useItemOn(stack, state, level, pos, player, hand, hit);
    }

    /** Paints an unpainted block with the held block (BlockCablePaintable.java:73-100); null when the stack is no allowed paint. */
    static ItemInteractionResult paint(Block self, ItemStack stack, Level level, BlockPos pos) {
        if(!(stack.getItem() instanceof BlockItem blockItem)) return null;
        BlockState paint = blockItem.getBlock().defaultBlockState();
        if(!IPaintableBlockEntity.allowedPaint(paint, self)) return null;
        if(!(level.getBlockEntity(pos) instanceof IPaintableBlockEntity paintable) || paintable.getPaint() != null) return null;
        if(!level.isClientSide) paintable.setPaint(paint);
        return ItemInteractionResult.sidedSuccess(level.isClientSide);
    }

    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool) {
        return screw(level, pos, tool);
    }

    /** Screwdriver clears the paint, defuser toggles HIDE_OVERLAY with a full block update (BlockCablePaintable.java:107-134). */
    static boolean screw(Level level, BlockPos pos, ToolType tool) {
        if(tool == ToolType.SCREWDRIVER) {
            if(level.getBlockEntity(pos) instanceof IPaintableBlockEntity paintable && paintable.getPaint() != null) {
                paintable.setPaint(null);
                return true;
            }
        }

        if(tool == ToolType.DEFUSER) {
            BlockState state = level.getBlockState(pos);
            level.setBlock(pos, state.setValue(HIDE_OVERLAY, !state.getValue(HIDE_OVERLAY)), Block.UPDATE_ALL);
            return true;
        }

        return false;
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        this.addStandardInfo(tooltip);
    }
}
