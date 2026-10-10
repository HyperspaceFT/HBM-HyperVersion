package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineMixerBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.main.NuclearTechMod;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

public class RenderMixer extends BlockEntityRendererNT<MachineMixerBlockEntity> implements IBEWLRProvider {

    private static final ResourceLocation FLUID_TEXTURE = NuclearTechMod.withDefaultNamespace("textures/models/white.png");

    @Override public BlockEntityRenderer<MachineMixerBlockEntity> create(Context context) { return new RenderMixer(); }
    @Override public void render(MachineMixerBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        // The original cylindrical mixer does not rotate with placement facing.
        RenderContext.translate(0.5F, 0F, 0.5F);
        this.renderParts(be.prevRotation + (be.rotation - be.prevRotation) * partialTicks);
        long totalFill = 0;
        long totalMax = 0;
        for(FluidTank tank : be.tanks) if(tank.getTankType() != Fluids.NONE) {
            totalFill += tank.getFill();
            totalMax += tank.getMaxFill();
        }
        if(totalFill <= 0 || totalMax <= 0) return;
        int color = be.tanks[2].getTankType().getColor();
        bindTexture(FLUID_TEXTURE);
        RenderContext.pushPose();
        RenderSystem.disableCull();
        RenderSystem.enableBlend();
        RenderSystem.blendFuncSeparate(770, 771, 1, 0);
        RenderSystem.depthMask(false);
        try {
            RenderContext.setColor(((color >> 16) & 255) / 255F, ((color >> 8) & 255) / 255F, (color & 255) / 255F, 0.75F);
            RenderContext.translate(0F, 1F, 0F);
            RenderContext.scale(1F, (float) Math.min(1D, (double) totalFill / totalMax) * 0.99F, 1F);
            RenderContext.translate(0F, -1F, 0F);
            ResourceManager.mixer.renderPart("Fluid");
        } finally {
            RenderContext.setColor(1F, 1F, 1F, 1F);
            RenderSystem.depthMask(true);
            RenderSystem.disableBlend();
            RenderSystem.defaultBlendFunc();
            RenderSystem.enableCull();
            RenderContext.popPose();
        }
    }
    private void renderParts(float rotation) {
        RenderSystem.disableCull();
        try {
            bindTexture(ResourceManager.mixer_tex);
            ResourceManager.mixer.renderPart("Main");
            RenderContext.pushPose();
            try {
                RenderContext.mulPose(Axis.YN.rotationDegrees(rotation));
                ResourceManager.mixer.renderPart("Mixer");
            } finally { RenderContext.popPose(); }
        } finally { RenderSystem.enableCull(); }
    }
    @Override public AABB getRenderBoundingBox(MachineMixerBlockEntity be) { return be.getRenderBoundingBox(); }
    @Override public Item getItemForRenderer() { return NtmBlocks.MACHINE_MIXER.asItem(); }
    @Override public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -5F, 0F);
                RenderContext.scale(5F, 5F, 5F);
            }
            @Override public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
                RenderMixer.this.renderParts(0F);
            }
        };
    }
}
