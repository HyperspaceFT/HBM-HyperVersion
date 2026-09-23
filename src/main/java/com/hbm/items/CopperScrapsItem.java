package com.hbm.items;

import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.util.TagsUtil;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;

import java.util.List;

/** Preserves partial copper pours when a casting device is emptied or broken. */
public class CopperScrapsItem extends Item {
    public CopperScrapsItem(Properties properties) {
        super(properties);
    }

    public static ItemStack create(int amount) {
        if(amount <= 0) return ItemStack.EMPTY;
        ItemStack stack = new ItemStack(NtmItems.SCRAPS.get());
        CompoundTag tag = new CompoundTag();
        tag.putInt("material", Mats.MAT_COPPER.id);
        tag.putInt("amount", amount);
        TagsUtil.putCustomData(stack, tag);
        return stack;
    }

    public static int getAmount(ItemStack stack) {
        if(stack.isEmpty() || !stack.is(NtmItems.SCRAPS.get())) return 0;
        CompoundTag tag = TagsUtil.getCustomData(stack);
        int amount = tag.getInt("amount");
        if(tag.getInt("material") != Mats.MAT_COPPER.id || amount <= 0
                || amount > MaterialShapes.BLOCK.q(16)) return 0;
        return amount;
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        tooltip.add(Component.translatable("casting.scraps", getAmount(stack)));
        tooltip.add(Component.translatable("casting.scraps.desc"));
    }
}
