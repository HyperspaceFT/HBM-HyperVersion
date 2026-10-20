package com.hbm.items.tools;

import api.hbm.block.IToolable;
import api.hbm.block.IToolable.ToolType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;

public class ToolingItem extends Item {

    protected ToolType type;

    public ToolingItem(ToolType type, Properties properties) {
        // Original ItemCraftingDegradation.java:12-14 (the parent of ItemTooling): stack size 1, no repair.
        super(properties.stacksTo(1).setNoRepair());

        this.type = type;

        type.register(new ItemStack(this));
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        Player player = context.getPlayer();
        Level level = context.getLevel();
        BlockPos usedPos = context.getClickedPos();
        Direction usedDirection = context.getClickedFace();

        if (player == null) return InteractionResult.PASS;

        // Original ItemTooling.java:30-37: only a successful onScrew wears the tool and consumes the click.
        if (level.getBlockState(usedPos).getBlock() instanceof IToolable toolableBlock
                && toolableBlock.onScrew(level, player, usedPos, usedDirection, this.type)) {

            if (this.getMaxDamage(new ItemStack(this)) > 0) {
                context.getItemInHand().hurtAndBreak(1, player, LivingEntity.getSlotForHand(context.getHand()));
            }

            return InteractionResult.sidedSuccess(level.isClientSide);
        }

        return InteractionResult.PASS;
    }
}
