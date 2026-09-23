package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ITooltipProvider;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;

import java.util.List;

public class MachineCrucibleBlock extends DummyableBlock {
    public static final MapCodec<MachineCrucibleBlock> CODEC = simpleCodec(MachineCrucibleBlock::new);

    public MachineCrucibleBlock(Properties properties) {
        super(properties);
        // Keep the original open bowl: dropped input must reach the intake above its floor.
        this.bounding.add(new AABB(-1.5, 0, -1.5, 1.5, 0.5, 1.5));
        this.bounding.add(new AABB(-1.25, 0.5, -1.25, 1.25, 1.5, -1));
        this.bounding.add(new AABB(-1.25, 0.5, -1.25, -1, 1.5, 1.25));
        this.bounding.add(new AABB(-1.25, 0.5, 1, 1.25, 1.5, 1.25));
        this.bounding.add(new AABB(1, 0.5, -1.25, 1.25, 1.5, 1.25));
    }

    @Override public MapCodec<MachineCrucibleBlock> codec() { return CODEC; }
    @Override public int[] getDimensions() { return new int[] {1, 0, 1, 1, 1, 1}; }
    @Override public int getOffset() { return 1; }
    @Override public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        for(String line : ITooltipProvider.getDescription(stack)) tooltip.add(Component.literal(line));
    }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return state.getValue(TYPE) == DummyBlockType.CORE
                ? new MachineCrucibleBlockEntity(pos, state) : new ProxyComboBlockEntity(pos, state).inventory();
    }
    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos,
            Player player, InteractionHand hand, BlockHitResult hit) {
        if(player.isShiftKeyDown() || !stack.is(ItemTags.SHOVELS)) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        BlockPos core = this.findCore(level, pos);
        if(core == null) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        if(!level.isClientSide && level.getBlockEntity(core) instanceof MachineCrucibleBlockEntity crucible) {
            ItemStack scraps = crucible.takeScraps();
            if(!player.getInventory().add(scraps)) player.drop(scraps, false);
        }
        return ItemInteractionResult.sidedSuccess(level.isClientSide);
    }

    @Override protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        return this.standardOpenBehavior(level, pos, player);
    }

    @Override public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean moving) {
        if(!state.is(newState.getBlock()) && !level.isClientSide
                && level.getBlockEntity(pos) instanceof MachineCrucibleBlockEntity crucible) {
            popResource(level, pos, crucible.takeScraps());
        }
        super.onRemove(state, level, pos, newState, moving);
    }
}
