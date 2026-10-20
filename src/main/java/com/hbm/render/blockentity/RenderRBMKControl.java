package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.rbmk.RBMKControlBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity;
import com.hbm.main.ResourceManager;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Block;

/**
 * The control rod columns: the pipe stubs of RenderRBMKPiped, then the original RenderRBMKControlRod (:22-70), the rod head
 * (part Lid of rbmk_rods.obj) raised by the interpolated insertion, textured by the manual rod's colour group or as the automatic rod.
 */
public class RenderRBMKControl extends RenderRBMKPiped<RBMKControlBlockEntity> {

    @Override public BlockEntityRenderer<RBMKControlBlockEntity> create(Context context) { return new RenderRBMKControl(); }

    @Override
    public void render(RBMKControlBlockEntity be, float partialTicks, PoseStack poseStack, MultiBufferSource buffer, int packedLight, int packedOverlay) {

        super.render(be, partialTicks, poseStack, buffer, packedLight, packedOverlay);

        if(be.getLevel() == null) return;

        // As the original: the topmost block of the same kind within 15 above the core, the extra block of a single column.
        Block block = be.getBlockState().getBlock();
        int offset = 1;

        for(int o = 1; o < 16; o++) {

            if(be.getLevel().getBlockState(be.getBlockPos().above(o)).is(block)) {
                offset = o;
            } else {
                break;
            }
        }

        int light = LevelRenderer.getLightColor(be.getLevel(), be.getBlockPos().above(offset + 1));

        ResourceLocation texture = ResourceManager.RBMK_CONTROL_AUTO_TEX;

        if(be instanceof RBMKControlManualBlockEntity crm) {
            if(crm.color == null) texture = ResourceManager.RBMK_CONTROL_TEX;
            else texture = ResourceManager.RBMK_CONTROL_COLOR_TEX[crm.color.ordinal()];
        }

        double level = be.lastLevel + (be.level - be.lastLevel) * partialTicks;

        RenderContext.setup(poseStack, light, packedOverlay);
        RenderContext.translate(0.5F, offset, 0.5F);
        RenderContext.translate(0F, (float) level, 0F);

        bindTexture(texture);
        ResourceManager.rbmk_rods.renderPart("Lid");

        RenderContext.end();
    }
}
