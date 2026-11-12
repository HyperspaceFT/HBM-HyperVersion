package com.hbm.blocks.network;

import api.hbm.block.IToolable;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blockentity.network.PipePaintableBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.blocks.states.NtmBlockStateProperties;
import com.hbm.inventory.fluid.FluidType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.phys.BlockHitResult;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * Paintable coated universal fluid duct (original FluidDuctPaintable.java:32-180): painted, cleared and stripped of its port
 * overlay like the paintable cable; unpainted, its overlay is tinted with the duct's fluid colour.
 */
public class FluidDuctPaintableBlock extends FluidDuctBaseBlock implements IToolable, ILookOverlay, ITooltipProvider {

    public static final BooleanProperty HIDE_OVERLAY = NtmBlockStateProperties.HIDE_OVERLAY;

    public FluidDuctPaintableBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(HIDE_OVERLAY, false));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(HIDE_OVERLAY);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new PipePaintableBlockEntity(pos, state);
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        ItemInteractionResult paint = CablePaintableBlock.paint(this, stack, level, pos);
        return paint != null ? paint : super.useItemOn(stack, state, level, pos, player, hand, hit);
    }

    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool) {
        return CablePaintableBlock.screw(level, pos, tool);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        this.addStandardInfo(tooltip);
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        if(!(level.getBlockEntity(pos) instanceof PipeBaseBlockEntity duct)) return;

        List<Component> text = new ArrayList<>();
        FluidType type = duct.getFluidType();
        text.add(Component.translatable(type.getUnlocalizedName()).withColor(type.getColor()));
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }
}
