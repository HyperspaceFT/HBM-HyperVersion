package com.hbm.render.entity.item;

import com.hbm.entity.item.MovingPackage;
import com.hbm.main.NuclearTechMod;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;

/**
 * Original RenderMovingPackage.java:19-39: every package looks the same, a small supply crate; the contents are never drawn (they
 * are not synced). The original draws the crate block as a dropped item scaled by 2, 0.0125 lower. NEO has no crate block, so the
 * crate's texture (ModBlocks.java:2173, crate.png) is drawn straight onto a cube; its edge is the package's 0.5-block hitbox and it
 * stands on the entity's position, both to be compared with the original in game.
 */
public class RenderMovingPackage extends EntityRenderer<MovingPackage> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/block/crate.png");
    private static final float HALF = 0.25F;
    private static final float BOTTOM = -0.0125F;

    public RenderMovingPackage(EntityRendererProvider.Context context) {
        super(context);
        this.shadowRadius = 0.0F;
    }

    @Override
    public void render(MovingPackage entity, float entityYaw, float partialTick, PoseStack poseStack, MultiBufferSource buffer, int packedLight) {
        poseStack.pushPose();

        PoseStack.Pose pose = poseStack.last();
        VertexConsumer buf = buffer.getBuffer(RenderType.entitySolid(TEXTURE));
        float lo = BOTTOM;
        float hi = BOTTOM + HALF * 2;

        // up, down
        quad(buf, pose, packedLight, 0, 1, 0, -HALF, hi, -HALF, -HALF, hi, HALF, HALF, hi, HALF, HALF, hi, -HALF);
        quad(buf, pose, packedLight, 0, -1, 0, -HALF, lo, HALF, -HALF, lo, -HALF, HALF, lo, -HALF, HALF, lo, HALF);
        // north, south
        quad(buf, pose, packedLight, 0, 0, -1, HALF, hi, -HALF, HALF, lo, -HALF, -HALF, lo, -HALF, -HALF, hi, -HALF);
        quad(buf, pose, packedLight, 0, 0, 1, -HALF, hi, HALF, -HALF, lo, HALF, HALF, lo, HALF, HALF, hi, HALF);
        // west, east
        quad(buf, pose, packedLight, -1, 0, 0, -HALF, hi, -HALF, -HALF, lo, -HALF, -HALF, lo, HALF, -HALF, hi, HALF);
        quad(buf, pose, packedLight, 1, 0, 0, HALF, hi, HALF, HALF, lo, HALF, HALF, lo, -HALF, HALF, hi, -HALF);

        poseStack.popPose();
        super.render(entity, entityYaw, partialTick, poseStack, buffer, packedLight);
    }

    /** One face with the whole texture: the corners top left, bottom left, bottom right, top right as seen from outside. */
    private static void quad(VertexConsumer buf, PoseStack.Pose pose, int light, float nx, float ny, float nz,
                             float x0, float y0, float z0, float x1, float y1, float z1, float x2, float y2, float z2, float x3, float y3, float z3) {
        vertex(buf, pose, light, nx, ny, nz, x0, y0, z0, 0, 0);
        vertex(buf, pose, light, nx, ny, nz, x1, y1, z1, 0, 1);
        vertex(buf, pose, light, nx, ny, nz, x2, y2, z2, 1, 1);
        vertex(buf, pose, light, nx, ny, nz, x3, y3, z3, 1, 0);
    }

    private static void vertex(VertexConsumer buf, PoseStack.Pose pose, int light, float nx, float ny, float nz, float x, float y, float z, float u, float v) {
        buf.addVertex(pose, x, y, z).setColor(0xFFFFFFFF).setUv(u, v).setOverlay(OverlayTexture.NO_OVERLAY).setLight(light).setNormal(pose, nx, ny, nz);
    }

    @Override
    public ResourceLocation getTextureLocation(MovingPackage entity) {
        return TEXTURE;
    }
}
