package com.hbm.render.item;

import com.hbm.items.armor.GasMaskItem;
import com.hbm.items.armor.HazmatHelmetItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.render.model.armor.ModelGasMask;
import com.hbm.render.model.armor.ModelM65;
import com.hbm.util.ArmorUtil;
import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.client.extensions.common.IClientItemExtensions;

import java.util.HashMap;
import java.util.Map;

/**
 * Client half of the original ArmorGasMask (getArmorModel :64-86, renderHelmetOverlay :107-145), registered for the four
 * gas masks from NuclearTechModClient. Also serves the three hazmat helmets (original ArmorHazmatMask.getArmorModel :29-39,
 * ArmorHazmat.renderHelmetOverlay), which draw the same full-screen quad with one fixed texture.
 */
public class GasMaskClientExtensions implements IClientItemExtensions {

    private static final Map<String, ResourceLocation[]> OVERLAYS = new HashMap<>();

    private ModelGasMask modelGas;
    private ModelM65 modelM65;

    @Override
    public HumanoidModel<?> getHumanoidArmorModel(LivingEntity living, ItemStack stack, EquipmentSlot slot, HumanoidModel<?> original) {

        if(slot != EquipmentSlot.HEAD) return original;

        if(stack.getItem() instanceof HazmatHelmetItem hood) {
            // The yellow hood has no model of its own and keeps the standard helmet layer with its worn texture
            return hood.isM65Model() ? m65(living) : original;
        }

        if(!(stack.getItem() instanceof GasMaskItem mask)) return original;

        if(!mask.getMaskType().m65Model) {
            if(this.modelGas == null) this.modelGas = new ModelGasMask(Minecraft.getInstance().getEntityModels().bakeLayer(ModelGasMask.LAYER));
            return this.modelGas;
        }

        return m65(living);
    }

    private ModelM65 m65(LivingEntity living) {
        if(this.modelM65 == null) this.modelM65 = new ModelM65(Minecraft.getInstance().getEntityModels().bakeLayer(ModelM65.LAYER));
        this.modelM65.filter.visible = !ArmorUtil.getGasMaskFilterRecursively(living.getItemBySlot(EquipmentSlot.HEAD), living).isEmpty();
        return this.modelM65;
    }

    // Called by Gui.renderCameraOverlays in first person while not scoping, as the 1.7.10 helmet overlay hook was.
    // The gas mask frame follows the mask's own wear; the quad covers the screen at z -90 like vanilla's pumpkin overlay.
    @Override
    public void renderHelmetOverlay(ItemStack stack, Player player, GuiGraphics guiGraphics, DeltaTracker deltaTracker) {

        if(stack.getItem() instanceof HazmatHelmetItem hood) {
            ResourceLocation tex = hood.getOverlay();
            if(tex != null) drawOverlay(guiGraphics, tex);
            return;
        }

        if(!(stack.getItem() instanceof GasMaskItem mask)) return;

        String prefix = mask.getMaskType().overlayPrefix;

        if(prefix == null) return;

        int index = (int) ((double) stack.getDamageValue() / (double) stack.getMaxDamage() * 6D);
        ResourceLocation tex = OVERLAYS.computeIfAbsent(prefix, GasMaskClientExtensions::frames)[Math.min(index, 5)];

        drawOverlay(guiGraphics, tex);
    }

    private static void drawOverlay(GuiGraphics guiGraphics, ResourceLocation tex) {
        RenderSystem.disableDepthTest();
        RenderSystem.depthMask(false);
        RenderSystem.enableBlend();
        RenderSystem.blendFuncSeparate(GlStateManager.SourceFactor.SRC_ALPHA, GlStateManager.DestFactor.ONE_MINUS_SRC_ALPHA, GlStateManager.SourceFactor.ONE, GlStateManager.DestFactor.ZERO);
        guiGraphics.setColor(1.0F, 1.0F, 1.0F, 1.0F);
        guiGraphics.blit(tex, 0, 0, -90, 0.0F, 0.0F, guiGraphics.guiWidth(), guiGraphics.guiHeight(), guiGraphics.guiWidth(), guiGraphics.guiHeight());
        RenderSystem.defaultBlendFunc();
        RenderSystem.disableBlend();
        RenderSystem.depthMask(true);
        RenderSystem.enableDepthTest();
        guiGraphics.setColor(1.0F, 1.0F, 1.0F, 1.0F);
    }

    private static ResourceLocation[] frames(String prefix) {
        ResourceLocation[] frames = new ResourceLocation[6];
        for(int i = 0; i < frames.length; i++) {
            frames[i] = NuclearTechMod.withDefaultNamespace("textures/misc/" + prefix + i + ".png");
        }
        return frames;
    }
}
