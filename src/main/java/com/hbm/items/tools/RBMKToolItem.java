package com.hbm.items.tools;

import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.blocks.machine.rbmk.RBMKConsoleBlock;
import com.hbm.util.TagsUtil;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EquipmentSlotGroup;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.component.ItemAttributeModifiers;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;

import java.util.List;

/**
 * Original ItemRBMKTool: the RBMK console linking device. Used on any RBMK column it stores the column's core position, used on a
 * console it links the console to that position. The crane console and rbmk_display branches (:70-100) arrive with those blocks
 * (Goals 25 and 26).
 */
public class RBMKToolItem extends Item {

    public RBMKToolItem(Properties properties) {
        // Original getAttributeModifiers (:112-118): the vanilla weapon modifier, +2 attack damage.
        super(properties.attributes(ItemAttributeModifiers.builder()
                .add(
                        Attributes.ATTACK_DAMAGE,
                        new AttributeModifier(BASE_ATTACK_DAMAGE_ID, 2, AttributeModifier.Operation.ADD_VALUE),
                        EquipmentSlotGroup.MAINHAND
                )
                .build()));
    }

    /** Original onItemUse (:28-103). */
    @Override
    public InteractionResult useOn(UseOnContext context) {
        Player player = context.getPlayer();
        Level level = context.getLevel();
        BlockPos pos = context.getClickedPos();
        ItemStack stack = context.getItemInHand();

        Block b = level.getBlockState(pos).getBlock();

        if(b instanceof RBMKBaseBlock rbmk) {

            BlockPos core = rbmk.findCore(level, pos);

            if(core != null && !level.isClientSide) {

                CompoundTag tag = TagsUtil.getCustomData(stack);
                tag.putInt("posX", core.getX());
                tag.putInt("posY", core.getY());
                tag.putInt("posZ", core.getZ());
                TagsUtil.putCustomData(stack, tag);

                if(player != null) player.displayClientMessage(Component.translatable(this.getDescriptionId() + ".linked").withStyle(ChatFormatting.YELLOW), false);
            }

            return InteractionResult.sidedSuccess(level.isClientSide);
        }

        // NEO-only: the original only asks for any NBT on the stack; without the three keys it would link the console to 0, 0, 0.
        if(b instanceof RBMKConsoleBlock console && hasPosition(stack)) {

            if(!level.isClientSide) {

                BlockPos core = console.findCore(level, pos);

                if(core != null && level.getBlockEntity(core) instanceof RBMKConsoleBlockEntity be) {
                    CompoundTag tag = TagsUtil.getCustomData(stack);
                    be.setTarget(tag.getInt("posX"), tag.getInt("posY"), tag.getInt("posZ"));
                    if(player != null) player.displayClientMessage(Component.translatable(this.getDescriptionId() + ".set").withStyle(ChatFormatting.YELLOW), false);
                }
            }

            return InteractionResult.sidedSuccess(level.isClientSide);
        }

        return InteractionResult.PASS;
    }

    private static boolean hasPosition(ItemStack stack) {
        CompoundTag tag = TagsUtil.getCustomData(stack);
        return tag.contains("posX") && tag.contains("posY") && tag.contains("posZ");
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag) {
        for(String s : I18nUtil.resolveKeyArray(this.getDescriptionId() + ".desc"))
            components.add(Component.literal(s).withStyle(ChatFormatting.YELLOW));
    }
}
