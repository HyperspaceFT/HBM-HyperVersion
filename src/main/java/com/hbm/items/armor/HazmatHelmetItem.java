package com.hbm.items.armor;

import api.hbm.item.IGasMask;
import com.hbm.util.ArmorRegistry.HazardClass;
import com.hbm.util.ArmorUtil;
import net.minecraft.core.Holder;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import org.jetbrains.annotations.Nullable;

import java.util.ArrayList;
import java.util.List;

/**
 * Original ArmorHazmatMask. The worn model (ModelM65 for the red and grey hoods, the standard helmet layer otherwise) and the
 * overlay are drawn by the client-only GasMaskClientExtensions, so this class stays loadable on a dedicated server.
 */
public class HazmatHelmetItem extends HazmatArmorItem implements IGasMask {

    private final boolean m65Model;
    @Nullable
    private final ResourceLocation overlay;

    public HazmatHelmetItem(Holder<ArmorMaterial> material, Properties properties, ResourceLocation wornTexture, boolean m65Model, @Nullable ResourceLocation overlay) {
        super(material, ArmorItem.Type.HELMET, properties, wornTexture);
        this.m65Model = m65Model;
        this.overlay = overlay;
    }

    /** Original ArmorHazmatMask.java:29-39: true for the red and grey hoods */
    public boolean isM65Model() {
        return m65Model;
    }

    /** Original ArmorHazmat.renderHelmetOverlay: full-screen overlay texture, null when none is drawn */
    @Nullable
    public ResourceLocation getOverlay() {
        return overlay;
    }

    // Original ArmorHazmatMask.java:41-44
    @Override
    public ArrayList<HazardClass> getBlacklist(ItemStack stack, LivingEntity entity) {
        return new ArrayList<>(); // full hood has no restrictions
    }

    @Override
    public ItemStack getFilter(ItemStack stack, LivingEntity entity) {
        return ArmorUtil.getGasMaskFilter(entity.level(), stack);
    }

    @Override
    public void installFilter(ItemStack stack, LivingEntity entity, ItemStack filter) {
        ArmorUtil.installGasMaskFilter(entity.level(), stack, filter);
    }

    @Override
    public void damageFilter(ItemStack stack, LivingEntity entity, int damage) {
        ArmorUtil.damageGasMaskFilter(entity.level(), stack, damage);
    }

    @Override
    public boolean isFilterApplicable(ItemStack stack, LivingEntity entity, ItemStack filter) {
        return true;
    }

    // Original ArmorHazmatMask.java:61-66
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag) {
        ArmorUtil.addGasMaskTooltip(stack, context, components, flag);

        super.appendHoverText(stack, context, components, flag);
    }

    // Original ArmorHazmatMask.java:73-93
    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {

        ItemStack stack = player.getItemInHand(hand);

        if(ArmorUtil.ejectGasMaskFilter(this, stack, level, player)) {
            return InteractionResultHolder.sidedSuccess(stack, level.isClientSide());
        }

        return super.use(level, player, hand);
    }
}
