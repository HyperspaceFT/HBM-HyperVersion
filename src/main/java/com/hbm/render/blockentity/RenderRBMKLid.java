package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock.LidType;
import com.hbm.main.NuclearTechMod;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.HashMap;
import java.util.Map;

/**
 * The lid of an RBMK column: a 1 x 0.25 x 1 box on top of the column, textured &lt;column&gt;_cover_* (concrete lid) or
 * &lt;column&gt;_glass_* (glass lid). Original RenderRBMKReflector.java:123-136 with RBMKBase.getIcon (:85-93); the column body
 * itself is a plain block model. Like the original, the glass lid is a cutout box, not translucent.
 */
public class RenderRBMKLid<T extends RBMKBaseBlockEntity> extends BlockEntityRendererNT<T> {

    private static final float LID_HEIGHT = 0.25F;
    private static final Map<String, ResourceLocation> TEXTURES = new HashMap<>();

    @Override public BlockEntityRenderer<T> create(Context context) { return new RenderRBMKLid<>(); }

    private static ResourceLocation texture(String column, String suffix) {
        return TEXTURES.computeIfAbsent(column + suffix, key -> NuclearTechMod.withDefaultNamespace("textures/block/rbmk/" + key + ".png"));
    }

    @Override
    public void render(T be, float partialTicks, PoseStack poseStack, MultiBufferSource buffer, int packedLight, int packedOverlay) {

        LidType lid = be.getLid();
        if(lid == LidType.NONE || be.getLevel() == null) return;

        String column = textureBase(be);
        String kind = lid == LidType.GLASS ? "_glass" : "_cover";

        // The lid sits on the extra block at the top of the column; light it with the light of the space it occupies.
        int top = columnTop(be);
        int light = LevelRenderer.getLightColor(be.getLevel(), be.getBlockPos().above(top));

        float y0 = top;
        float y1 = top + LID_HEIGHT;
        // Side faces show the bottom quarter of the texture, as renderStandardBlock does for a 0.25 high box.
        float vTop = 1F - LID_HEIGHT;

        PoseStack.Pose pose = poseStack.last();

        VertexConsumer topBuf = buffer.getBuffer(RenderType.entityCutoutNoCull(texture(column, kind + "_top")));
        quad(topBuf, pose, light, packedOverlay, 0, 1, 0,
                0, y1, 0, 0, 0,
                0, y1, 1, 0, 1,
                1, y1, 1, 1, 1,
                1, y1, 0, 1, 0);
        quad(topBuf, pose, light, packedOverlay, 0, -1, 0,
                0, y0, 0, 0, 0,
                1, y0, 0, 1, 0,
                1, y0, 1, 1, 1,
                0, y0, 1, 0, 1);

        VertexConsumer sideBuf = buffer.getBuffer(RenderType.entityCutoutNoCull(texture(column, kind + "_side")));
        quad(sideBuf, pose, light, packedOverlay, 0, 0, -1,
                1, y0, 0, 0, 1,
                0, y0, 0, 1, 1,
                0, y1, 0, 1, vTop,
                1, y1, 0, 0, vTop);
        quad(sideBuf, pose, light, packedOverlay, 0, 0, 1,
                0, y0, 1, 0, 1,
                1, y0, 1, 1, 1,
                1, y1, 1, 1, vTop,
                0, y1, 1, 0, vTop);
        quad(sideBuf, pose, light, packedOverlay, -1, 0, 0,
                0, y0, 0, 0, 1,
                0, y0, 1, 1, 1,
                0, y1, 1, 1, vTop,
                0, y1, 0, 0, vTop);
        quad(sideBuf, pose, light, packedOverlay, 1, 0, 0,
                1, y0, 1, 0, 1,
                1, y0, 0, 1, 1,
                1, y1, 0, 1, vTop,
                1, y1, 1, 0, vTop);
    }

    /** Base name of the lid textures (&lt;base&gt;_cover_* and &lt;base&gt;_glass_*); the column's registry path by default. */
    protected String textureBase(T be) {
        return BuiltInRegistries.BLOCK.getKey(be.getBlockState().getBlock()).getPath();
    }

    /**
     * Height of the lid above the core: one above the column's extra block, found in the world like the original, which draws the
     * lid on the extra block (RenderRBMKReflector.java:55-66). The dial is not read here: the client's config need not match the
     * server's, nor the height the column was built with.
     */
    protected static int columnTop(RBMKBaseBlockEntity be) {
        Block block = be.getBlockState().getBlock();
        for(int i = 1; i <= 16; i++) {
            BlockState state = be.getLevel().getBlockState(be.getBlockPos().above(i));
            if(!state.is(block) || DummyableBlock.isCore(state)) return i;
            if(DummyableBlock.hasExtra(state)) return i + 1;
        }
        return 17;
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

    @Override
    public AABB getRenderBoundingBox(T be) {
        return be.getRenderBoundingBox();
    }
}
