package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineStirlingBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.Direction;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

public class RenderStirling extends BlockEntityRendererNT<MachineStirlingBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachineStirlingBlockEntity> create(Context context) {
        return new RenderStirling();
    }

    @Override
    public void render(MachineStirlingBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);

        RenderContext.translate(0.5F, 0.0F, 0.5F);
        switch(facing) {
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            default -> { }
        }

        float rot = be.lastSpin + (be.spin - be.lastSpin) * partialTicks;
        this.renderCommon(rot, be.hasCog);
    }

    private void renderCommon(float rot, boolean hasCog) {
        bindTexture(ResourceManager.STIRLING_TEX);

        ResourceManager.stirling.renderPart("Base");

        if(hasCog) {
            RenderContext.pushPose();
            RenderContext.translate(0.0F, 1.375F, 0.0F);
            RenderContext.mulPose(Axis.ZP.rotationDegrees(-rot));
            RenderContext.translate(0.0F, -1.375F, 0.0F);
            ResourceManager.stirling.renderPart("Cog");
            RenderContext.popPose();
        }

        RenderContext.pushPose();
        RenderContext.translate(0.0F, 1.375F, 0.25F);
        RenderContext.mulPose(Axis.XP.rotationDegrees(rot * 2 + 3));
        RenderContext.translate(0.0F, -1.375F, -0.25F);
        ResourceManager.stirling.renderPart("CogSmall");
        RenderContext.popPose();

        RenderContext.translate((float) (Math.sin(rot * Math.PI / 90D) * 0.25 + 0.125), 0.0F, 0.0F);
        ResourceManager.stirling.renderPart("Piston");
    }

    @Override
    public AABB getRenderBoundingBox(MachineStirlingBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_STIRLING.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0.0F, -1.5F, 0.0F);
                RenderContext.scale(3.25F, 3.25F, 3.25F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
                // Meta 1 is the gearless engine; the plain stack keeps its gear.
                boolean cog = MetaHelper.getMeta(stack) != 1;
                RenderStirling.this.renderCommon(cog ? (System.currentTimeMillis() % 3600) * 0.1F : 0F, cog);
            }
        };
    }
}
