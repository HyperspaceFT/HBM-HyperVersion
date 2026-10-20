package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock.LidType;
import com.hbm.main.NuclearTechMod;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.resources.ResourceLocation;

import java.util.HashMap;
import java.util.Map;

/**
 * The columns of RBMKPipedBaseBlock: while the column has no lid, four pipe stubs on top of it, textured &lt;column&gt;_pipe_top on
 * the top and bottom faces and &lt;column&gt;_pipe_side on the sides (original RenderRBMKControl ISBRH :118-129 with
 * RBMKPipedBase.getIcon); with a lid, the lid of RenderRBMKLid instead (the original's :100-116 for the columns that take one).
 */
public class RenderRBMKPiped<T extends RBMKBaseBlockEntity> extends RenderRBMKLid<T> {

    private static final Map<String, ResourceLocation> TEXTURES = new HashMap<>();

    // Original setRenderBounds of the four stubs (:120-127), each 0.125 high.
    private static final float[][] PIPES = new float[][] {
            {0.0625F, 0.0625F, 0.4375F, 0.4375F},
            {0.0625F, 0.5625F, 0.4375F, 0.9375F},
            {0.5625F, 0.5625F, 0.9375F, 0.9375F},
            {0.5625F, 0.0625F, 0.9375F, 0.4375F}
    };
    private static final float PIPE_HEIGHT = 0.125F;

    @Override public BlockEntityRenderer<T> create(Context context) { return new RenderRBMKPiped<>(); }

    private static ResourceLocation texture(String column, String suffix) {
        return TEXTURES.computeIfAbsent(column + suffix, key -> NuclearTechMod.withDefaultNamespace("textures/block/rbmk/" + key + ".png"));
    }

    @Override
    public void render(T be, float partialTicks, PoseStack poseStack, MultiBufferSource buffer, int packedLight, int packedOverlay) {

        if(be.getLevel() == null) return;

        if(be.getLid() != LidType.NONE) {
            super.render(be, partialTicks, poseStack, buffer, packedLight, packedOverlay);
            return;
        }

        String column = textureBase(be);

        // The stubs sit on the block above the column's extra block, as the lid does; lit like the lid.
        int top = columnTop(be);
        int light = LevelRenderer.getLightColor(be.getLevel(), be.getBlockPos().above(top));

        PoseStack.Pose pose = poseStack.last();

        // The level's buffer source ends its shared buffer when a second non-fixed render type is requested, so holding both
        // textures' consumers at once and writing them alternately threw "Not building!" (Goal 24 acceptance D2). Draw every
        // stub's ends with the first type, then every stub's sides with the second, as RenderRBMKLid does.
        VertexConsumer topBuf = buffer.getBuffer(RenderType.entityCutoutNoCull(texture(column, "_pipe_top")));
        for(float[] pipe : PIPES) {
            boxEnds(topBuf, pose, light, packedOverlay, pipe[0], top, pipe[1], pipe[2], top + PIPE_HEIGHT, pipe[3]);
        }

        VertexConsumer sideBuf = buffer.getBuffer(RenderType.entityCutoutNoCull(texture(column, "_pipe_side")));
        for(float[] pipe : PIPES) {
            boxSides(sideBuf, pose, light, packedOverlay, pipe[0], top, pipe[1], pipe[2], top + PIPE_HEIGHT, pipe[3]);
        }
    }

    /**
     * A box with renderStandardBlock's texture mapping: the faces show the part of the icon that the box covers within its block
     * (top and bottom by x/z, the sides by their horizontal coordinate and the height within the block). The ends and the sides
     * are separate methods because each texture is its own render type and must be drawn in its own pass.
     */
    private static void boxEnds(VertexConsumer topBuf, PoseStack.Pose pose, int light, int overlay,
                                float x0, float y0, float z0, float x1, float y1, float z1) {

        quad(topBuf, pose, light, overlay, 0, 1, 0,
                x0, y1, z0, x0, z0,
                x0, y1, z1, x0, z1,
                x1, y1, z1, x1, z1,
                x1, y1, z0, x1, z0);
        quad(topBuf, pose, light, overlay, 0, -1, 0,
                x0, y0, z0, x0, z0,
                x1, y0, z0, x1, z0,
                x1, y0, z1, x1, z1,
                x0, y0, z1, x0, z1);
    }

    private static void boxSides(VertexConsumer sideBuf, PoseStack.Pose pose, int light, int overlay,
                                 float x0, float y0, float z0, float x1, float y1, float z1) {

        float v0 = 1F - (y1 - (float) Math.floor(y0));
        float v1 = 1F - (y0 - (float) Math.floor(y0));

        quad(sideBuf, pose, light, overlay, 0, 0, -1,
                x1, y0, z0, 1F - x1, v1,
                x0, y0, z0, 1F - x0, v1,
                x0, y1, z0, 1F - x0, v0,
                x1, y1, z0, 1F - x1, v0);
        quad(sideBuf, pose, light, overlay, 0, 0, 1,
                x0, y0, z1, x0, v1,
                x1, y0, z1, x1, v1,
                x1, y1, z1, x1, v0,
                x0, y1, z1, x0, v0);
        quad(sideBuf, pose, light, overlay, -1, 0, 0,
                x0, y0, z0, z0, v1,
                x0, y0, z1, z1, v1,
                x0, y1, z1, z1, v0,
                x0, y1, z0, z0, v0);
        quad(sideBuf, pose, light, overlay, 1, 0, 0,
                x1, y0, z1, 1F - z1, v1,
                x1, y0, z0, 1F - z0, v1,
                x1, y1, z0, 1F - z0, v0,
                x1, y1, z1, 1F - z1, v0);
    }

    private static void quad(VertexConsumer buf, PoseStack.Pose pose, int light, int overlay, float nx, float ny, float nz,
                             float x0, float y0, float z0, float u0, float v0,
                             float x1, float y1, float z1, float u1, float v1,
                             float x2, float y2, float z2, float u2, float v2,
                             float x3, float y3, float z3, float u3, float v3) {
        vertex(buf, pose, light, overlay, nx, ny, nz, x0, y0, z0, u0, v0);
        vertex(buf, pose, light, overlay, nx, ny, nz, x1, y1, z1, u1, v1);
        vertex(buf, pose, light, overlay, nx, ny, nz, x2, y2, z2, u2, v2);
        vertex(buf, pose, light, overlay, nx, ny, nz, x3, y3, z3, u3, v3);
    }

    private static void vertex(VertexConsumer buf, PoseStack.Pose pose, int light, int overlay, float nx, float ny, float nz, float x, float y, float z, float u, float v) {
        buf.addVertex(pose, x, y, z).setColor(0xFFFFFFFF).setUv(u, v).setOverlay(overlay).setLight(light).setNormal(pose, nx, ny, nz);
    }
}
