package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blocks.machine.rbmk.RBMKRodBlock;
import com.hbm.main.ResourceManager;
import com.hbm.render.NtmRenderTypes;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import org.joml.Matrix4f;

/**
 * The fuel channel: the lid like every column (textures rbmk_element_* / rbmk_element_mod_*, original RBMKRod.setBlockTextureName),
 * then the original RenderRBMKFuelChannel (:22-94): the loaded rods, tinted by the rod's colour, in every block of the column, and
 * the Cherenkov glow while the synced flux is above 5. The column body itself is the rbmk_element baked model.
 */
@SuppressWarnings("deprecation") // NtmRenderTypes.GLOW is the existing untextured additive no-cull render type.
public class RenderRBMKRod extends RenderRBMKLid<RBMKRodBlockEntity> {

    @Override public BlockEntityRenderer<RBMKRodBlockEntity> create(Context context) { return new RenderRBMKRod(); }

    @Override
    protected String textureBase(RBMKRodBlockEntity be) {
        return be.getBlockState().getBlock() instanceof RBMKRodBlock rod && rod.moderated ? "rbmk_element_mod" : "rbmk_element";
    }

    @Override
    public void render(RBMKRodBlockEntity be, float partialTicks, PoseStack poseStack, MultiBufferSource buffer, int packedLight, int packedOverlay) {

        super.render(be, partialTicks, poseStack, buffer, packedLight, packedOverlay);

        if(be.getLevel() == null) return;

        boolean hasRod = be.hasRod;
        // fluxQuantity holds the synced lastFluxQuantity on the client (deserialize).
        boolean cherenkov = be.fluxQuantity > 5;
        int color = be.rodColor;

        if(!hasRod && !cherenkov) return;

        // The original's offset + 1: the core and every block above it up to the column's extra block.
        int top = columnTop(be);

        RenderContext.setup(poseStack, packedLight, packedOverlay);
        RenderContext.translate(0.5F, 0F, 0.5F);

        if(hasRod) {
            RenderContext.pushPose();
            bindTexture(ResourceManager.RBMK_ELEMENT_FUEL_TEX);
            RenderContext.setColor(((color & 0xFF0000) >> 16) / 255F, ((color & 0x00FF00) >> 8) / 255F, (color & 0x0000FF) / 255F, 1F);

            for(int j = 0; j < top; j++) {
                ResourceManager.rbmk_element_rods.renderPart("Rods");
                RenderContext.translate(0F, 1F, 0F);
            }

            RenderContext.setColor(1F, 1F, 1F, 1F);
            RenderContext.popPose();
        }

        if(cherenkov) {
            VertexConsumer glow = buffer.getBuffer(NtmRenderTypes.GLOW);
            Matrix4f matrix = RenderContext.poseStack().last().pose();

            for(double j = 0; j <= top - 1; j += 0.25) {
                float y = (float) (0.75 + j);
                glow.addVertex(matrix, -0.5F, y, -0.5F).setColor(0.4F, 0.9F, 1.0F, 0.1F);
                glow.addVertex(matrix, -0.5F, y, 0.5F).setColor(0.4F, 0.9F, 1.0F, 0.1F);
                glow.addVertex(matrix, 0.5F, y, 0.5F).setColor(0.4F, 0.9F, 1.0F, 0.1F);
                glow.addVertex(matrix, 0.5F, y, -0.5F).setColor(0.4F, 0.9F, 1.0F, 0.1F);
            }
        }

        RenderContext.end();
    }
}
