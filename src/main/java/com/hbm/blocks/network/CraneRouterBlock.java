package com.hbm.blocks.network;

import api.hbm.conveyor.IConveyorBelt;
import api.hbm.conveyor.IConveyorItem;
import api.hbm.conveyor.IConveyorPackage;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.CraneRouterBlockEntity;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.entity.item.MovingPackage;
import com.hbm.items.tools.ConveyorWandItem;
import com.hbm.module.ModulePatternMatcher;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.List;

/**
 * Original CraneRouter, the conveyor sorter: items and packages entering from any side leave through the side their filters pick,
 * onto the belt there or dropped. It has no facing; the six coloured faces are the model's tinted overlays.
 */
public class CraneRouterBlock extends BaseEntityBlock implements IEnterableBlock, ITooltipProvider {

    public static final MapCodec<CraneRouterBlock> CODEC = simpleCodec(CraneRouterBlock::new);

    /** Original colorMultiplier (:78-94), by side: down, up, north, south, west, east. */
    public static final int[] SIDE_COLORS = { 0xff0000, 0xff8000, 0xffff00, 0x00ff00, 0x0080ff, 0x8000ff };

    public CraneRouterBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected MapCodec<CraneRouterBlock> codec() {
        return CODEC;
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CraneRouterBlockEntity(pos, state);
    }

    @Override
    protected RenderShape getRenderShape(BlockState state) {
        return RenderShape.MODEL;
    }

    /** Original :63-76: the conveyor wand goes to the item; every other item, the screwdriver included, opens the screen. */
    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {
        if(stack.getItem() instanceof ConveyorWandItem) return ItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;
        return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }

    /** Original :63-76: sneaking does not open the screen. */
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

    /** Original :119-120: items and packages enter from every side, a diagonal step included. */
    @Override
    public boolean canItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        return true;
    }

    @Override
    public boolean canPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        return true;
    }

    /** Original :122-136: the stack leaves through the side it is sorted to; an unsortable stack drops at the block's centre. */
    @Override
    public void onItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        if(entity == null || !(level.getBlockEntity(pos) instanceof CraneRouterBlockEntity router)) return;

        ItemStack stack = entity.getItemStack().copy();
        if(stack.isEmpty()) return;

        Direction out = getOutputDir(router, stack);

        if(out == null) {
            level.addFreshEntity(new ItemEntity(level, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, stack));
        } else {
            sendOnRoute(level, pos, stack, out);
        }
    }

    /** Original :138-157: onto the belt on that side, 0.55 blocks from the centre and snapped, or dropped at that point. */
    private static void sendOnRoute(Level level, BlockPos pos, ItemStack stack, Direction dir) {
        BlockPos beltPos = pos.relative(dir);
        Vec3 point = exitPoint(pos, dir);

        if(level.getBlockState(beltPos).getBlock() instanceof IConveyorBelt belt) {
            Vec3 snap = belt.getClosestSnappingPosition(level, beltPos, point);
            MovingItem moving = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
            moving.moveTo(snap.x, snap.y, snap.z, 0, 0);
            moving.setItemStack(stack);
            level.addFreshEntity(moving);
        } else {
            level.addFreshEntity(new ItemEntity(level, point.x, point.y, point.z, stack));
        }
    }

    private static Vec3 exitPoint(BlockPos pos, Direction dir) {
        return Vec3.atCenterOf(pos).add(dir.getStepX() * 0.55, dir.getStepY() * 0.55, dir.getStepZ() * 0.55);
    }

    /**
     * Original :159-188: every stack of the package is sorted on its own; the stacks of one side leave as one new package onto the
     * belt there, or drop one by one when that side has no belt. The original skips empty places (null there, :204); NEO's empty
     * places are empty stacks.
     */
    @Override
    public void onPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        if(entity == null || entity.getItemStacks() == null || !(level.getBlockEntity(pos) instanceof CraneRouterBlockEntity router)) return;

        List<List<ItemStack>> sorted = new ArrayList<>();
        for(int i = 0; i < 7; i++) sorted.add(new ArrayList<>());

        for(ItemStack stack : entity.getItemStacks()) {
            if(stack == null || stack.isEmpty()) continue;
            Direction out = getOutputDir(router, stack);
            sorted.get(out == null ? 6 : out.get3DDataValue()).add(stack.copy());
        }

        for(int i = 0; i < 7; i++) {
            List<ItemStack> list = sorted.get(i);
            if(list.isEmpty()) continue;

            if(i == 6) {
                for(ItemStack stack : list) level.addFreshEntity(new ItemEntity(level, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, stack));
                continue;
            }

            Direction d = Direction.from3DDataValue(i);
            BlockPos beltPos = pos.relative(d);
            Vec3 point = exitPoint(pos, d);

            if(level.getBlockState(beltPos).getBlock() instanceof IConveyorBelt belt) {
                Vec3 snap = belt.getClosestSnappingPosition(level, beltPos, point);
                MovingPackage moving = new MovingPackage(NtmEntityTypes.MOVING_PACKAGE.get(), level);
                moving.moveTo(snap.x, snap.y, snap.z, 0, 0);
                moving.setItemStacks(list.toArray(new ItemStack[0]));
                level.addFreshEntity(moving);
            } else {
                for(ItemStack stack : list) level.addFreshEntity(new ItemEntity(level, point.x, point.y, point.z, stack));
            }
        }
    }

    /**
     * Original getOutputDir (:212-261). Sides in whitelist or blacklist mode count when any filled filter slot of theirs matches
     * (whitelist) or none does (blacklist, so a blacklist side with an empty filter always counts); without such a side every
     * wildcard side counts; one of the counted sides is picked with the world's random. Null when no side counts.
     */
    @Nullable
    public static Direction getOutputDir(CraneRouterBlockEntity router, ItemStack stack) {
        List<Direction> valid = new ArrayList<>();

        for(int side = 0; side < 6; side++) {
            int mode = router.modes[side];
            if(mode != CraneRouterBlockEntity.MODE_WHITELIST && mode != CraneRouterBlockEntity.MODE_BLACKLIST) continue;

            ModulePatternMatcher matcher = router.patterns[side];
            boolean matches = false;

            for(int slot = 0; slot < 5; slot++) {
                ItemStack filter = router.getItem(side * 5 + slot);

                if(!filter.isEmpty() && matcher.isValidForFilter(filter, slot, stack)) {
                    matches = true;
                    break;
                }
            }

            if((mode == CraneRouterBlockEntity.MODE_WHITELIST) == matches) valid.add(Direction.from3DDataValue(side));
        }

        if(valid.isEmpty()) {
            for(int side = 0; side < 6; side++) {
                if(router.modes[side] == CraneRouterBlockEntity.MODE_WILDCARD) valid.add(Direction.from3DDataValue(side));
            }
        }

        if(valid.isEmpty() || router.getLevel() == null) return null;
        return valid.get(router.getLevel().random.nextInt(valid.size()));
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        this.addStandardInfo(tooltip);
    }
}
