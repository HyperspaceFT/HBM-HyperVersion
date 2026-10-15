package com.hbm.items.machine;

import com.hbm.inventory.MetaHelper;
import com.hbm.items.EnumMultiItem;
import com.hbm.util.BobMathUtil;
import com.hbm.util.EnumUtil;
import com.hbm.util.TagsUtil;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;

import java.util.List;

public class ZirnoxRodItem extends EnumMultiItem {

    public ZirnoxRodItem(Properties properties) {
        super(properties, ZirnoxType.class, true, true);
    }

    public static void incrementLifeTime(ItemStack stack) {

        CompoundTag tag = TagsUtil.getCustomData(stack);
        int time = tag.getInt("life");
        tag.putInt("life", time + 1);
        TagsUtil.putCustomData(stack, tag);
    }

    public static void setLifeTime(ItemStack stack, int time) {

        CompoundTag tag = TagsUtil.getCustomData(stack);
        tag.putInt("life", time);
        TagsUtil.putCustomData(stack, tag);
    }

    public static int getLifeTime(ItemStack stack) {
        return TagsUtil.getCustomData(stack).getInt("life");
    }

    /** Original ItemZirnoxRod.getDurabilityForDisplay (:60-63): used life over the type's max life. */
    public static double getDepletion(ItemStack stack) {
        ZirnoxType num = EnumUtil.grabEnumSafely(ZirnoxType.class, MetaHelper.getMeta(stack));
        return (double) getLifeTime(stack) / (double) num.maxLife;
    }

    // Original showDurabilityBar (:56-58).
    @Override public boolean isBarVisible(ItemStack stack) { return getDepletion(stack) > 0D; }

    // 1.7.10 drew the remaining fraction (1 - durability); clamped so stray life values cannot overflow the bar.
    // The colour follows the vanilla 1.21 hue (green to red), not 1.7.10's linear red/green blend.
    @Override
    public int getBarWidth(ItemStack stack) {
        return Math.round(13F - 13F * (float) Mth.clamp(getDepletion(stack), 0D, 1D));
    }

    @Override
    public int getBarColor(ItemStack stack) {
        return Mth.hsvToRgb(Math.max(0F, 1F - (float) Mth.clamp(getDepletion(stack), 0D, 1D)) / 3F, 1.0F, 1.0F);
    }

    // Original addInformation (:65-81). Its descriptions used %d with a String argument, a format error in 1.7.10; NEO's use %s.
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {
        ZirnoxType num = EnumUtil.grabEnumSafely(ZirnoxType.class, MetaHelper.getMeta(stack));
        tooltipComponents.add(Component.translatable("trait.rbmk.depletion", ((int) (getDepletion(stack) * 100000)) / 1000D + "%").withStyle(ChatFormatting.YELLOW));

        String[] loc;
        if(num.breeding) {
            loc = I18nUtil.resolveKeyArray("item.hbmsntm.rod_zirnox.desc_breeding", BobMathUtil.getShortNumber(num.maxLife));
        } else {
            loc = I18nUtil.resolveKeyArray("item.hbmsntm.rod_zirnox.desc", num.heat, BobMathUtil.getShortNumber(num.maxLife));
        }

        for(String s : loc) tooltipComponents.add(Component.literal(s));
    }

    public enum ZirnoxType {
        NATURAL_URANIUM_FUEL(250_000, 30),
        URANIUM_FUEL(200_000, 50),
        TH232(20_000, 0, true),
        THORIUM_FUEL(200_000, 40),
        MOX_FUEL(165_000, 75),
        PLUTONIUM_FUEL(175_000, 65),
        U233_FUEL(150_000, 100),
        U235_FUEL(165_000, 85),
        LES_FUEL(150_000, 150),
        LITHIUM(20_000, 0, true),
        ZFB_MOX(50_000, 35);

        public final int maxLife;
        public final int heat;
        public final boolean breeding;

        ZirnoxType(int life, int heat, boolean breeding) {
            this.maxLife = life;
            this.heat = heat;
            this.breeding = breeding;
        }

        ZirnoxType(int life, int heat) {
            this.maxLife = life;
            this.heat = heat;
            this.breeding = false;
        }
    }
}
