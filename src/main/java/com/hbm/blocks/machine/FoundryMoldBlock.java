package com.hbm.blocks.machine;

import api.hbm.block.IToolable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.FoundryMoldBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.items.NtmItems;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.Containers;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

public class FoundryMoldBlock extends BaseEntityBlock implements IToolable, ILookOverlay {
    public static final MapCodec<FoundryMoldBlock> CODEC = simpleCodec(FoundryMoldBlock::new);
    private static final VoxelShape SHAPE = Shapes.or(box(0, 0, 0, 16, 2, 16),
            box(0, 0, 0, 16, 8, 2), box(0, 0, 14, 16, 8, 16),
            box(0, 0, 2, 2, 8, 14), box(14, 0, 2, 16, 8, 14));

    public FoundryMoldBlock(Properties properties) { super(properties); }
    @Override public MapCodec<FoundryMoldBlock> codec() { return CODEC; }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new FoundryMoldBlockEntity(pos, state); }
    @Override protected RenderShape getRenderShape(BlockState state) { return RenderShape.MODEL; }
    @Override protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) { return SHAPE; }
    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    private boolean interact(Level level, BlockPos pos, Player player, ItemStack held) {
        if(!(level.getBlockEntity(pos) instanceof FoundryMoldBlockEntity mold)) return false;
        if(!mold.getItem(1).isEmpty()) {
            if(!level.isClientSide) give(player, mold.removeItem(1, 64));
            return true;
        }
        if((held.is(NtmItems.MOLD_PLATE_CAST.get()) || held.is(NtmItems.MOLD_INGOT.get()) || held.is(NtmItems.MOLD_BLADE.get()))
                && mold.getItem(0).isEmpty() && mold.amount == 0) {
            if(!level.isClientSide) mold.insertMold(held);
            return true;
        }
        if(held.is(ItemTags.SHOVELS)) {
            if(!level.isClientSide) give(player, mold.takeScraps());
            return true;
        }
        return false;
    }

    private static void give(Player player, ItemStack stack) {
        if(!stack.isEmpty() && !player.getInventory().add(stack)) player.drop(stack, false);
    }

    @Override protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos,
            Player player, InteractionHand hand, BlockHitResult hit) {
        return interact(level, pos, player, stack) ? ItemInteractionResult.sidedSuccess(level.isClientSide)
                : ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }
    @Override protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        return interact(level, pos, player, ItemStack.EMPTY) ? InteractionResult.sidedSuccess(level.isClientSide) : InteractionResult.PASS;
    }

    @Override public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool) {
        if(tool != ToolType.SCREWDRIVER || !(level.getBlockEntity(pos) instanceof FoundryMoldBlockEntity mold)
                || mold.amount > 0 || mold.getItem(0).isEmpty()) return false;
        if(!level.isClientSide) give(player, mold.takeMold());
        return true;
    }

    @Override public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean moving) {
        if(!state.is(newState.getBlock()) && !level.isClientSide
                && level.getBlockEntity(pos) instanceof FoundryMoldBlockEntity mold) {
            popResource(level, pos, mold.takeScraps());
            Containers.dropContents(level, pos, mold);
        }
        super.onRemove(state, level, pos, newState, moving);
    }

    @Override @OnlyIn(Dist.CLIENT)
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        if(!(level.getBlockEntity(pos) instanceof FoundryMoldBlockEntity mold)) return;
        List<Component> text = new ArrayList<>();
        text.add(mold.hasMold() ? mold.getItem(0).getHoverName() : Component.translatable("casting.no_mold"));
        if(mold.amount > 0 && mold.type != null) text.add(Component.translatable("casting.contents", mold.type.getName(), mold.amount, mold.getCapacity()));
        if(mold.amount > 0 && mold.amount == mold.getCapacity()) text.add(Component.translatable("casting.cooling", mold.cooloff));
        if(!mold.getItem(1).isEmpty()) text.add(Component.translatable("casting.take_output"));
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xFF4000, 0x401000, text);
    }
}
