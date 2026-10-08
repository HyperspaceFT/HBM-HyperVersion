package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachinePumpElectricBlockEntity;
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
import net.minecraft.core.Direction;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

/** The electric pump part of the original's RenderPump; only the electric texture is used. */
public class RenderPumpElectric extends BlockEntityRendererNT<MachinePumpElectricBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachinePumpElectricBlockEntity> create(Context context) {
        return new RenderPumpElectric();
    }

    @Override
    public void render(MachinePumpElectricBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);

        RenderContext.translate(0.5F, 0.0F, 0.5F);
        // The original angle table (RenderPump), as the placement directions match the original.
        switch(facing) {
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            default -> { }
        }

        float angle = be.lastRotor + (be.rotor - be.lastRotor) * partialTicks;
        this.renderCommon(angle);
    }

    private void renderCommon(double rot) {
        RenderSystem.disableCull();

        bindTexture(ResourceManager.PUMP_ELECTRIC_TEX);
        ResourceManager.pump.renderPart("Base");

        RenderContext.pushPose();
        RenderContext.translate(0.0F, 2.25F, 0.0F);
        RenderContext.mulPose(Axis.ZP.rotationDegrees((float) (rot - 90D)));
        RenderContext.translate(0.0F, -2.25F, 0.0F);
        ResourceManager.pump.renderPart("Rotor");
        RenderContext.popPose();

        double sin = Math.sin(rot * Math.PI / 180D) * 0.5D - 0.5D;
        double cos = Math.cos(rot * Math.PI / 180D) * 0.5D;
        double ang = Math.acos(cos / 2D);
        double cath = Math.sqrt(1 + (cos * cos) / 2);

        RenderContext.pushPose();
        RenderContext.translate(0.0F, (float) (1 - cath + sin), 0.0F);
        RenderContext.translate(0.0F, 4.75F, 0.0F);
        // The original rotates by the angle about (0, 0, -1), which is the negated angle about +Z.
        RenderContext.mulPose(Axis.ZP.rotationDegrees((float) -(ang * 180D / Math.PI - 90D)));
        RenderContext.translate(0.0F, -4.75F, 0.0F);
        ResourceManager.pump.renderPart("Arms");
        RenderContext.popPose();

        RenderContext.pushPose();
        RenderContext.translate(0.0F, (float) (1 - cath + sin), 0.0F);
        ResourceManager.pump.renderPart("Piston");
        RenderContext.popPose();

        RenderSystem.enableCull();
    }

    @Override
    public AABB getRenderBoundingBox(MachinePumpElectricBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.PUMP_ELECTRIC.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0.0F, -3.0F, 0.0F);
                RenderContext.scale(2.5F, 2.5F, 2.5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                // Unlike the steam engine, the original pump item is not turned.
                RenderPumpElectric.this.renderCommon((System.currentTimeMillis() % 3600) * 0.1D);
            }
        };
    }
}
