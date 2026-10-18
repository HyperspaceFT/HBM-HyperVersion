package com.hbm.items.machine;

import com.hbm.inventory.MetaHelper;
import com.hbm.items.IMetaItem;
import com.hbm.items.NuclearWasteItem;
import com.hbm.items.component.NtmDataComponents;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;

import java.util.List;

/**
 * Nuclear waste from a depleted ZIRNOX rod (original ItemDepletedFuel.java:16-42 on top of ItemNuclearWaste.java:12-34).
 * META 1 is hot waste fresh from the rod, META 0 the waste after it cooled down in a spent fuel pool drum.
 */
public class DepletedFuelItem extends NuclearWasteItem implements IMetaItem {

    public static final int COOL = 0;
    public static final int HOT = 1;

    public DepletedFuelItem(Properties properties) {
        // META 0 is the default, so a cool stack never carries a META patch and cool waste from every source stacks together.
        super(properties.component(NtmDataComponents.META.get(), COOL));
    }

    /** Any META above 0 counts as hot, like the original getItemDamage() > 0 (ItemDepletedFuel.java:35,40). */
    public static boolean isHot(ItemStack stack) {
        return MetaHelper.getMeta(stack) > COOL;
    }

    @Override
    public void getSubItems(Item item, List<ItemStack> stacks) {
        stacks.add(MetaHelper.newStack(item, 1, COOL));
        stacks.add(MetaHelper.newStack(item, 1, HOT));
    }

    // Original addInformation (ItemDepletedFuel.java:38-41): only hot waste has a tooltip.
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {
        if(isHot(stack)) tooltipComponents.add(Component.translatable("desc.item.wasteCooling").withStyle(ChatFormatting.GOLD));
    }

}
