package com.hbm.items.special;

import com.hbm.items.NtmItems;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;

import java.util.List;

/**
 * Original ItemRag.
 */
public class RagItem extends Item {

    public RagItem(Properties properties) {
        super(properties);
    }

    // Original ItemRag.java:17-31 checks for water material (source and flowing) at the floored position; the fluid state
    // also counts waterlogged blocks.
    @Override
    public boolean onEntityItemUpdate(ItemStack stack, ItemEntity entity) {

        if(!entity.level().isClientSide() && entity.level().getFluidState(entity.blockPosition()).is(FluidTags.WATER)) {
            entity.setItem(new ItemStack(NtmItems.RAG_DAMP.get(), stack.getCount()));
            return true;
        }

        return false;
    }

    // Original ItemRag.java:33-38. The original discards the rag_piss when the inventory is full; it is dropped here.
    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {

        ItemStack stack = player.getItemInHand(hand);

        if(!level.isClientSide()) {
            stack.consume(1, player);

            ItemStack piss = new ItemStack(NtmItems.RAG_PISS.get());

            if(!player.getInventory().add(piss)) {
                player.drop(piss, false);
            }
        }

        return InteractionResultHolder.sidedSuccess(stack, level.isClientSide());
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag) {
        for(String line : I18nUtil.resolveKeyArray("item.hbmsntm.rag.desc")) {
            components.add(Component.literal(line).withStyle(ChatFormatting.GRAY));
        }
    }
}
