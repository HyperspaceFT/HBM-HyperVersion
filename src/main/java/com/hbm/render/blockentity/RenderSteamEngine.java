package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.MachineSteamEngineBlockEntity;
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

public class RenderSteamEngine extends BlockEntityRendererNT<MachineSteamEngineBlockEntity> implements IBEWLRProvider {

    @Override
    public BlockEntityRenderer<MachineSteamEngineBlockEntity> create(Context context) {
        return new RenderSteamEngine();
    }

    @Override
    public void render(MachineSteamEngineBlockEntity be, MultiBufferSource buffer, float partialTicks) {
        Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);

        RenderContext.translate(0.5F, 0.0F, 0.5F);
        // The original angle table (RenderSteamEngine), as the placement directions match the original.
        switch(facing) {
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            default -> { }
        }

        float angle = be.lastRotor + (be.rotor - be.lastRotor) * partialTicks;
        RenderContext.translate(2.0F, 0.0F, 0.0F);
        this.renderCommon(angle);
    }

    private void renderCommon(double rot) {
        RenderSystem.disableCull();

        bindTexture(ResourceManager.STEAM_ENGINE_TEX);
        ResourceManager.steam_engine.renderPart("Base");

        RenderContext.pushPose();
        RenderContext.translate(2.0F, 1.375F, 0.0F);
        RenderContext.mulPose(Axis.ZP.rotationDegrees((float) -rot));
        RenderContext.translate(-2.0F, -1.375F, 0.0F);
        ResourceManager.steam_engine.renderPart("Flywheel");
        RenderContext.popPose();

        RenderContext.pushPose();
        RenderContext.translate(0.0F, 1.375F, -0.5F);
        RenderContext.mulPose(Axis.XP.rotationDegrees((float) (rot * 2D)));
        RenderContext.translate(0.0F, -1.375F, 0.5F);
        ResourceManager.steam_engine.renderPart("Shaft");
        RenderContext.popPose();

        RenderContext.pushPose();
        double sin = Math.sin(rot * Math.PI / 180D) * 0.25D - 0.25D;
        double cos = Math.cos(rot * Math.PI / 180D) * 0.25D;
        double ang = Math.acos(cos / 1.875D);
        RenderContext.translate((float) sin, (float) cos, 0.0F);
        RenderContext.translate(2.25F, 1.375F, 0.0F);
        RenderContext.mulPose(Axis.ZP.rotationDegrees((float) -(ang * 180D / Math.PI - 90D)));
        RenderContext.translate(-2.25F, -1.375F, 0.0F);
        ResourceManager.steam_engine.renderPart("Transmission");
        RenderContext.popPose();

        RenderContext.pushPose();
        double cath = Math.sqrt(3.515625D - (cos * cos) / 2);
        RenderContext.translate((float) (1.875 - cath + sin), 0.0F, 0.0F); //the difference that "1.875 - cath" makes is minuscule but very much noticeable
        ResourceManager.steam_engine.renderPart("Piston");
        RenderContext.popPose();

        RenderSystem.enableCull();
    }

    @Override
    public AABB getRenderBoundingBox(MachineSteamEngineBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.MACHINE_STEAM_ENGINE.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.mulPose(Axis.YN.rotationDegrees(90F));
                RenderContext.translate(0.0F, -1.5F, 0.0F);
                RenderContext.scale(2.0F, 2.0F, 2.0F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
                // The original checks item damage 1 for a stopped rotor, but the steam engine has no such variant.
                RenderSteamEngine.this.renderCommon((System.currentTimeMillis() % 3600) * 0.1D);
            }
        };
    }
}
