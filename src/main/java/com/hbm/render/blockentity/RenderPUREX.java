package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachinePUREXBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.hbm.util.BobMathUtil;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.Direction;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

/** Original RenderPUREX.java. The render distance (original 65536 squared) is BlockEntityRendererNT's 256 blocks. */
public class RenderPUREX extends BlockEntityRendererNT<MachinePUREXBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachinePUREXBlockEntity> create(Context context) {
        return new RenderPUREX();
    }

    @Override
    public void render(MachinePUREXBlockEntity be, MultiBufferSource buffer, float partialTicks) {

        RenderContext.translate(0.5F, 0F, 0.5F);
        RenderContext.mulPose(Axis.YP.rotationDegrees(90F));

        Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);
        switch(facing) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
        }

        float anim = BobMathUtil.interp(be.prevAnim, be.anim, partialTicks);

        bindTexture(ResourceManager.PUREX_TEX);
        ResourceManager.purex.renderPart("Base");
        if(be.frame) ResourceManager.purex.renderPart("Frame");

        RenderContext.pushPose();
        RenderContext.translate(1.5F, 1.25F, 0F);
        RenderContext.mulPose(Axis.ZP.rotationDegrees(anim * 45F));
        RenderContext.translate(-1.5F, -1.25F, 0F);
        ResourceManager.purex.renderPart("Fan");
        RenderContext.popPose();

        RenderContext.pushPose();
        RenderContext.translate((float) (BobMathUtil.sps(anim * 0.25F) * 0.5F), 0F, 0F);
        ResourceManager.purex.renderPart("Pump");
        RenderContext.popPose();
    }

    @Override
    public int getPacketLight(int packedLight, MachinePUREXBlockEntity be) {
        if(be.getLevel() != null && be.getBlockState().getBlock() instanceof DummyableBlock dummy) {
            return LevelRenderer.getLightColor(be.getLevel(), be.getBlockPos().above(dummy.getDimensions()[0]));
        }
        return packedLight;
    }

    @Override
    public AABB getRenderBoundingBox(MachinePUREXBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_PUREX.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -2.5F, 0F);
                RenderContext.scale(2.5F, 2.5F, 2.5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.scale(0.75F, 0.75F, 0.75F);
                bindTexture(ResourceManager.PUREX_TEX);
                ResourceManager.purex.renderPart("Base");
                ResourceManager.purex.renderPart("Frame");
                ResourceManager.purex.renderPart("Fan");
                ResourceManager.purex.renderPart("Pump");
            }
        };
    }
}
