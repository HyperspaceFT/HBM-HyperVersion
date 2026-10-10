package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineCompressorBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

public class RenderCompressor extends BlockEntityRendererNT<MachineCompressorBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<MachineCompressorBlockEntity> create(Context context) { return new RenderCompressor(); }
    @Override public void render(MachineCompressorBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        RenderContext.translate(0.5F, 0F, 0.5F);
        switch(be.getBlockState().getValue(DummyableBlock.FACING)) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            default -> { }
        }
        float lift = be.prevPiston + (be.piston - be.prevPiston) * partialTicks;
        float fan = be.prevFanSpin + (be.fanSpin - be.prevFanSpin) * partialTicks;
        this.renderParts(lift * 3F - 3F, fan);
    }
    private void renderParts(float pumpY, float fan) {
        RenderSystem.disableCull();
        try {
            this.bindTexture(ResourceManager.compressor_tex);
            ResourceManager.compressor.renderPart("Compressor");
            RenderContext.pushPose();
            RenderContext.translate(0F, pumpY, 0F);
            ResourceManager.compressor.renderPart("Pump");
            RenderContext.popPose();
            RenderContext.pushPose();
            RenderContext.translate(0F, 1.5F, 0F);
            RenderContext.mulPose(Axis.XP.rotationDegrees(fan));
            RenderContext.translate(0F, -1.5F, 0F);
            ResourceManager.compressor.renderPart("Fan");
            RenderContext.popPose();
        } finally { RenderSystem.enableCull(); }
    }
    @Override public AABB getRenderBoundingBox(MachineCompressorBlockEntity be) { return be.getRenderBoundingBox(); }
    @Override public Item getItemForRenderer() { return NtmBlocks.MACHINE_COMPRESSOR.asItem(); }
    @Override public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -4F, 0F);
                RenderContext.scale(3F, 3F, 3F);
            }
            @Override public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.scale(0.5F, 0.5F, 0.5F);
                double lift = (System.currentTimeMillis() * 0.005D) % 9D;
                if(lift > 3D) lift = 3D - (lift - 3D) / 2D;
                RenderCompressor.this.renderParts((float)-lift, (float)((System.currentTimeMillis() * 0.25D) % 360D));
            }
        };
    }
}
