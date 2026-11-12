package com.hbm.blocks.network;

import com.hbm.blockentity.network.FluidValveBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.fluid.FluidType;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.phys.BlockHitResult;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * Fluid valve (original FluidValve.java:21-72): a duct that carries fluid only while ENABLED (open). The fluid identifier sets
 * its type as on any duct; any other click that the identifier did not use toggles it, as the original only toggles after
 * FluidDuctBase.onBlockActivated declined.
 */
public class FluidValveBlock extends FluidDuctBaseBlock implements ILookOverlay {

    public static final BooleanProperty ENABLED = BlockStateProperties.ENABLED;

    public FluidValveBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(ENABLED, false));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(ENABLED);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new FluidValveBlockEntity(pos, state);
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        ItemInteractionResult result = super.useItemOn(stack, state, level, pos, player, hand, hit);
        return result.consumesAction() ? result : ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        if(level.isClientSide) return InteractionResult.SUCCESS;
        if(player.isShiftKeyDown()) return InteractionResult.PASS;

        setOpen(level, pos, state, !state.getValue(ENABLED));
        return InteractionResult.CONSUME;
    }

    /** Opens or closes the valve with the original's sound (FluidValve.java:57-66, CableSwitchBlock.setEnabled) and updates its node. */
    public static void setOpen(Level level, BlockPos pos, BlockState state, boolean open) {
        CableSwitchBlock.setEnabled(level, pos, state, open);
        if(level.getBlockEntity(pos) instanceof FluidValveBlockEntity valve) valve.updateState();
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        if(!(level.getBlockEntity(pos) instanceof PipeBaseBlockEntity duct)) return;

        List<Component> text = new ArrayList<>();
        this.addInfo(duct, text);
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }

    protected void addInfo(PipeBaseBlockEntity duct, List<Component> text) {
        FluidType type = duct.getFluidType();
        text.add(Component.translatable(type.getUnlocalizedName()).withColor(type.getColor()));
    }
}
