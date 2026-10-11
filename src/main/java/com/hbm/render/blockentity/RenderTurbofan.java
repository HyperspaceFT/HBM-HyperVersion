package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineTurbofanBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

public class RenderTurbofan extends BlockEntityRendererNT<MachineTurbofanBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<MachineTurbofanBlockEntity> create(Context context) { return new RenderTurbofan(); }
    @Override public void render(MachineTurbofanBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.translate(0.5F, 0F, 0.5F);
        switch(be.getBlockState().getValue(DummyableBlock.FACING)) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            default -> { }
        }
        this.bindTexture(ResourceManager.turbofan_tex);
        ResourceManager.turbofan.renderPart("Body");
        RenderContext.pushPose();
        RenderContext.translate(0F, 1.5F, 0F);
        RenderContext.mulPose(Axis.ZN.rotationDegrees(be.lastSpin + (be.spin - be.lastSpin) * partialTicks));
        RenderContext.translate(0F, -1.5F, 0F);
        ResourceManager.turbofan.renderPart("Blades");
        RenderContext.popPose();
        this.bindTexture(be.afterburner == 0 ? ResourceManager.turbofan_back_tex : ResourceManager.turbofan_afterburner_tex);
        ResourceManager.turbofan.renderPart("Afterburner");
    }
    @Override public AABB getRenderBoundingBox(MachineTurbofanBlockEntity be) { return be.getRenderBoundingBox(); }
    @Override public Item getItemForRenderer() { return NtmBlocks.MACHINE_TURBOFAN.asItem(); }
    @Override public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
                RenderContext.scale(2.25F, 2.25F, 2.25F);
            }
            @Override public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderTurbofan.this.bindTexture(ResourceManager.turbofan_tex);
                ResourceManager.turbofan.renderPart("Body");
                ResourceManager.turbofan.renderPart("Blades");
                RenderTurbofan.this.bindTexture(ResourceManager.turbofan_back_tex);
                ResourceManager.turbofan.renderPart("Afterburner");
            }
        };
    }
}
