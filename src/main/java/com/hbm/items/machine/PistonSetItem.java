package com.hbm.items.machine;

import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.trait.FT_Combustible.FuelGrade;
import com.hbm.items.EnumMultiItem;
import com.hbm.items.NtmItems;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import java.util.List;

/** Original ItemPistons efficiency table; the starmetal upgrade is outside this port. */
public class PistonSetItem extends EnumMultiItem {
    public PistonSetItem(Properties properties) { super(properties, Type.class, true, true); }
    public static Type getType(ItemStack stack) {
        if(stack.isEmpty() || !stack.is(NtmItems.PISTON_SET.get())) return null;
        int meta = MetaHelper.getMeta(stack);
        return meta >= 0 && meta < Type.values().length ? Type.values()[meta] : null;
    }
    @Override public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        Type type = getType(stack);
        if(type == null) return;
        tooltip.add(Component.translatable("piston_set.efficiency").withStyle(ChatFormatting.YELLOW));
        for(FuelGrade grade : FuelGrade.values()) tooltip.add(Component.translatable("piston_set.efficiency.grade",
                grade.getLocalizedName(), (int)(type.getEfficiency(grade) * 100)).withStyle(ChatFormatting.YELLOW));
    }
    public enum Type {
        STEEL(1.00, 0.75, 0.25, 0.00, 0.00),
        DURA(0.50, 1.00, 0.90, 0.50, 0.00),
        DESH(0.00, 0.50, 1.00, 0.75, 0.00);
        private final double[] efficiency;
        Type(double... efficiency) { this.efficiency = efficiency; }
        public double getEfficiency(FuelGrade grade) { return grade == null ? 0 : this.efficiency[grade.ordinal()]; }
    }
}
