package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.rbmk.RBMKCraneConsoleBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.FullBright;
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

/**
 * Original RenderCraneConsole (:13-163): the console with its joystick, the heat and enrichment meters and the two lamps, and, once
 * linked, the crane above the reactor (girders, carriage, tube and lift). The view distance is the base's 256 blocks, the original's
 * 65536 squared. The item uses the console parts as the original ItemRenderLibrary entry (:681-692).
 */
public class RenderCraneConsole extends BlockEntityRendererNT<RBMKCraneConsoleBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<RBMKCraneConsoleBlockEntity> create(Context context) { return new RenderCraneConsole(); }

    @Override
    public void render(RBMKCraneConsoleBlockEntity console, MultiBufferSource buffer, float partialTicks) {

        RenderSystem.disableCull();

        RenderContext.pushPose();
        RenderContext.translate(0.5F, 0F, 0.5F);

        // Original metadata switch: 2 (north) 90, 4 (west) 180, 3 (south) 270, 5 (east) 0 degrees.
        int teFacing = 0;
        Direction facing = console.getBlockState().getValue(DummyableBlock.FACING);
        switch(facing) {
            case NORTH -> teFacing = 90;
            case WEST -> teFacing = 180;
            case SOUTH -> teFacing = 270;
            case EAST -> teFacing = 0;
            default -> { }
        }
        RenderContext.mulPose(Axis.YP.rotationDegrees(teFacing));

        RenderContext.translate(0.5F, 0F, 0F);

        bindTexture(ResourceManager.RBMK_CRANE_CONSOLE_TEX);
        ResourceManager.rbmk_crane_console.renderPart("Console_Coonsole");

        RenderContext.pushPose();
        RenderContext.translate(0.75F, 1F, 0F);
        RenderContext.mulPose(Axis.ZP.rotationDegrees((float) (console.lastTiltFront + (console.tiltFront - console.lastTiltFront) * partialTicks)));
        RenderContext.mulPose(Axis.XP.rotationDegrees((float) (console.lastTiltLeft + (console.tiltLeft - console.lastTiltLeft) * partialTicks)));
        RenderContext.translate(-0.75F, -1.015F, 0F);
        ResourceManager.rbmk_crane_console.renderPart("JoyStick");
        RenderContext.popPose();

        RenderContext.pushPose();
        RenderContext.translate(0F, 1.25F, 0.75F);
        double heat = console.loadedHeat;
        RenderContext.mulPose(Axis.XP.rotationDegrees((float) (Math.sin(System.currentTimeMillis() * 0.01 % 360) * 180 / Math.PI * 0.05 + 135 - 270 * heat)));
        RenderContext.translate(0F, -1.25F, -0.75F);
        ResourceManager.rbmk_crane_console.renderPart("Meter1");
        RenderContext.popPose();

        RenderContext.pushPose();
        RenderContext.translate(0F, 1.25F, 0.25F);
        double enrichment = console.loadedEnrichment;
        RenderContext.mulPose(Axis.XP.rotationDegrees((float) (Math.sin(System.currentTimeMillis() * 0.01 % 360) * 180 / Math.PI * 0.05 + 135 - 270 * enrichment)));
        RenderContext.translate(0F, -1.25F, -0.25F);
        ResourceManager.rbmk_crane_console.renderPart("Meter2");
        RenderContext.popPose();

        // The original disables GL_TEXTURE_2D and lighting at lightmap 240 / 240 for the lamps; NEO draws them with the white texture,
        // unlit and full-bright, tinted by the shader colour (as RenderBobble's pellet shine).
        bindTexture(ResourceManager.WHITE_TEX);
        FullBright.enable();
        RenderContext.setLightning(false);

        //loading indicator
        if(console.isCraneLoading()) RenderContext.setColor(0.8F, 0.8F, 0F, 1F);  //is the crane loading? yellow
        else if(console.hasItemLoaded()) RenderContext.setColor(0F, 1F, 0F, 1F);  //is the crane loaded? green
        else RenderContext.setColor(0F, 0.1F, 0F, 1F);                            //is the crane unloaded? off
        ResourceManager.rbmk_crane_console.renderPart("Lamp1");

        //target indicator
        if(console.isAboveValidTarget()) RenderContext.setColor(0F, 1F, 0F, 1F);  //valid? green
        else RenderContext.setColor(1F, 0F, 0F, 1F);                              //not valid? red
        ResourceManager.rbmk_crane_console.renderPart("Lamp2");

        RenderContext.setColor(1F, 1F, 1F, 1F);
        RenderContext.setLightning(true);
        FullBright.disable();

        RenderContext.popPose();

        if(console.setUpCrane) {
            RenderContext.pushPose();

            // The original moves to the core's (x + 0.5, y - 1, z + 0.5) and then by (center - core) + (0, 1, 0).
            RenderContext.translate(
                    (float) (console.centerX - console.getBlockPos().getX() + 0.5D),
                    (float) (console.centerY - console.getBlockPos().getY() + 1 - 1),
                    (float) (console.centerZ - console.getBlockPos().getZ() + 0.5D));
            bindTexture(ResourceManager.RBMK_CRANE_TEX);

            int height = console.height - 6;

            RenderContext.mulPose(Axis.YP.rotationDegrees(teFacing));

            double posX = (console.lastPosFront + (console.posFront - console.lastPosFront) * partialTicks);
            double posZ = (console.lastPosLeft + (console.posLeft - console.lastPosLeft) * partialTicks);
            RenderContext.translate((float) -posX, 0F, (float) posZ);

            int craneRotationOffset = console.craneRotationOffset;
            RenderContext.mulPose(Axis.YP.rotationDegrees(craneRotationOffset));

            RenderContext.pushPose();
            int girderSpan = 0;
            RenderContext.mulPose(Axis.YP.rotationDegrees(-craneRotationOffset));
            switch(craneRotationOffset) {
                case 0 -> {
                    girderSpan = console.spanF + console.spanB + 1;
                    RenderContext.translate((float) (posX + console.spanB), 0F, 0F);
                }
                case 90 -> {
                    girderSpan = console.spanL + console.spanR + 1;
                    RenderContext.translate(0F, 0F, (float) (-posZ - console.spanR));
                }
                case 180 -> {
                    girderSpan = console.spanF + console.spanB + 1;
                    RenderContext.translate((float) (posX - console.spanF), 0F, 0F);
                }
                case 270 -> {
                    girderSpan = console.spanL + console.spanR + 1;
                    RenderContext.translate(0F, 0F, (float) (-posZ + console.spanL));
                }
                default -> { }
            }
            RenderContext.mulPose(Axis.YP.rotationDegrees(craneRotationOffset));

            for(int i = 0; i < girderSpan; i++) {
                ResourceManager.rbmk_crane.renderPart("Girder");
                RenderContext.translate(-1F, 0F, 0F);
            }
            RenderContext.popPose();

            ResourceManager.rbmk_crane.renderPart("Main");

            RenderContext.pushPose();

            for(int i = 0; i < height; i++) {
                ResourceManager.rbmk_crane.renderPart("Tube");
                RenderContext.translate(0F, 1F, 0F);
            }
            RenderContext.translate(0F, -1F, 0F);
            ResourceManager.rbmk_crane.renderPart("Carriage");
            RenderContext.popPose();

            RenderContext.translate(0F, (float) (-3.25D * (1 - (console.lastProgress + (console.progress - console.lastProgress) * partialTicks))), 0F);
            ResourceManager.rbmk_crane.renderPart("Lift");

            RenderContext.popPose();
        }

        RenderSystem.enableCull();
    }

    @Override
    public AABB getRenderBoundingBox(RBMKCraneConsoleBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override public boolean shouldRenderOffScreen(RBMKCraneConsoleBlockEntity be) { return true; }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.RBMK_CRANE_CONSOLE.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -3F, 0F);
                RenderContext.scale(3.5F, 3.5F, 3.5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                bindTexture(ResourceManager.RBMK_CRANE_CONSOLE_TEX);
                ResourceManager.rbmk_crane_console.renderPart("Console_Coonsole");
                ResourceManager.rbmk_crane_console.renderPart("JoyStick");
                ResourceManager.rbmk_crane_console.renderPart("Meter1");
                ResourceManager.rbmk_crane_console.renderPart("Meter2");
            }
        };
    }
}
