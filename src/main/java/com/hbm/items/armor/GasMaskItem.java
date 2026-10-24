package com.hbm.items.armor;

import api.hbm.item.IGasMask;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.ArmorRegistry.HazardClass;
import com.hbm.util.ArmorUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.ArmorMaterials;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;

import java.util.ArrayList;
import java.util.List;

/**
 * Original ArmorGasMask. The worn model and the helmet overlay live in the client-only GasMaskClientExtensions,
 * registered from NuclearTechModClient, so this class stays loadable on a dedicated server.
 */
public class GasMaskItem extends ArmorItem implements IGasMask {

    public enum MaskType {
        // Original ArmorGasMask.java:88-104 (worn textures), :64-86 (models) and :107-145 (overlays)
        GAS_MASK("textures/models/gas_mask.png", false, "overlay_gasmask_", false),
        M65("textures/models/model_m65.png", true, "overlay_goggles_", false),
        MONO("textures/models/model_m65_mono.png", true, null, true),
        OLDE("textures/armor/mask_olde.png", true, null, false);

        public final ResourceLocation texture;
        /** true: ModelM65, false: ModelGasMask */
        public final boolean m65Model;
        /** Prefix of the six hbmsntm:textures/misc/<prefix><0..5>.png overlay frames, null when no overlay is drawn */
        public final String overlayPrefix;
        public final boolean halfMask;

        MaskType(String texture, boolean m65Model, String overlayPrefix, boolean halfMask) {
            this.texture = NuclearTechMod.withDefaultNamespace(texture);
            this.m65Model = m65Model;
            this.overlayPrefix = overlayPrefix;
            this.halfMask = halfMask;
        }
    }

    private final MaskType maskType;

    public GasMaskItem(MaskType maskType, Properties properties) {
        super(ArmorMaterials.IRON, ArmorItem.Type.HELMET, properties);
        this.maskType = maskType;
    }

    public MaskType getMaskType() {
        return maskType;
    }

    @Override
    public ResourceLocation getArmorTexture(ItemStack stack, Entity entity, EquipmentSlot slot, ArmorMaterial.Layer layer, boolean innerModel) {
        return maskType.texture;
    }

    // Original ArmorGasMask.java:147-155, a new list on every call
    @Override
    public ArrayList<HazardClass> getBlacklist(ItemStack stack, LivingEntity entity) {
        if(maskType.halfMask) {
            return new ArrayList<>(List.of(HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA));
        } else {
            return new ArrayList<>(List.of(HazardClass.GAS_BLISTERING));
        }
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

    // Original ArmorGasMask.java:172-186
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag) {

        ArmorUtil.addGasMaskTooltip(stack, context, components, flag);

        List<HazardClass> haz = getBlacklist(stack, null);

        if(!haz.isEmpty()) {
            components.add(Component.translatable("hazard.never_protects").withStyle(ChatFormatting.RED));

            for(HazardClass clazz : haz) {
                components.add(Component.literal(" -").append(Component.translatable(clazz.unlocalizedMessage)).withStyle(ChatFormatting.DARK_RED));
            }
        }
    }

    // Original ArmorGasMask.java:193-212: sneaking with a filter installed ejects it instead of equipping the mask
    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {

        ItemStack stack = player.getItemInHand(hand);

        if(ArmorUtil.ejectGasMaskFilter(this, stack, level, player)) {
            return InteractionResultHolder.sidedSuccess(stack, level.isClientSide());
        }

        return super.use(level, player, hand);
    }
}
